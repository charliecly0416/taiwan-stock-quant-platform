#!/usr/bin/env python3
"""Small read-only FinMind availability audit for orthogonal TW stock data.

This script probes only a small symbol/date window for:
- TaiwanStockInstitutionalInvestorsBuySell
- TaiwanStockMarginPurchaseShortSale
- TaiwanStockMonthRevenue

It does not build model samples, publish providers, switch accepted latest,
touch frontend/API state, or interact with trading paths.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data_tw/experiments/finmind_orthogonal_availability_audit"
DOC_PATH = ROOT / "docs/tw_decision_model_orthogonal/FINMIND_ORTHOGONAL_AVAILABILITY_AUDIT_CN.md"
FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"

DATASETS = {
    "institutional_flow": "TaiwanStockInstitutionalInvestorsBuySell",
    "margin_short": "TaiwanStockMarginPurchaseShortSale",
    "monthly_revenue": "TaiwanStockMonthRevenue",
}

DEFAULT_SYMBOLS = ["2330", "2317", "2454", "2308", "2357", "6290"]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def read_token(args: argparse.Namespace) -> str:
    token = os.getenv("FINMIND_TOKEN") or os.getenv("FINMIND_API_TOKEN")
    if token:
        return token.strip()
    if args.token_stdin:
        return sys.stdin.readline().strip()
    return ""


def strip_symbol(value: str) -> str:
    text = str(value or "").strip().upper()
    if text.startswith("TW"):
        text = text[2:]
    return text


def safe_message(value: Any) -> str:
    text = str(value or "")
    for word in ["Bearer", "FINMIND_TOKEN", "FINMIND_API_TOKEN", "token"]:
        text = text.replace(word, "[redacted]")
    return text[:300]


def request_dataset(dataset: str, symbol: str, start: str, end: str, token: str, timeout: float) -> dict[str, Any]:
    params = {
        "dataset": dataset,
        "data_id": symbol,
        "start_date": start,
        "end_date": end,
    }
    headers = {"User-Agent": "tw-finmind-orthogonal-availability-audit/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        params["token"] = token
    try:
        resp = requests.get(FINMIND_URL, params=params, headers=headers, timeout=timeout)
        try:
            payload = resp.json()
        except Exception:
            payload = {"status": None, "msg": resp.text[:300], "data": []}
        data = payload.get("data") if isinstance(payload, dict) else []
        rows = data if isinstance(data, list) else []
        status = "success" if resp.status_code == 200 and str(payload.get("status")) == "200" else "failed"
        return {
            "status": status,
            "http_status": resp.status_code,
            "finmind_status": payload.get("status") if isinstance(payload, dict) else "",
            "msg": "" if status == "success" else safe_message(payload.get("msg") if isinstance(payload, dict) else ""),
            "rows": rows,
        }
    except Exception as exc:
        return {
            "status": "failed",
            "http_status": "",
            "finmind_status": "",
            "msg": safe_message(f"{type(exc).__name__}: {exc}"),
            "rows": [],
        }


def date_range(rows: list[dict[str, Any]]) -> tuple[str, str]:
    dates = sorted({str(row.get("date") or "")[:10] for row in rows if str(row.get("date") or "").strip()})
    if not dates:
        return "", ""
    return dates[0], dates[-1]


def month_range(rows: list[dict[str, Any]]) -> tuple[str, str]:
    periods = []
    for row in rows:
        year = str(row.get("revenue_year") or "").strip()
        month = str(row.get("revenue_month") or "").strip()
        if year and month:
            periods.append(f"{int(float(year)):04d}-{int(float(month)):02d}")
    periods = sorted(set(periods))
    if not periods:
        return "", ""
    return periods[0], periods[-1]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_report(
    *,
    generated_at: str,
    symbols: list[str],
    start: str,
    end: str,
    summary_rows: list[dict[str, Any]],
    raw_path: Path,
    summary_path: Path,
    field_path: Path,
    token_used: bool,
) -> None:
    by_dataset: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in summary_rows:
        by_dataset[row["category"]].append(row)

    lines = [
        "# FinMind 正交数据小范围可得性审计报告",
        "",
        f"- 生成时间：`{generated_at}`",
        f"- 审计范围：symbols `{','.join(symbols)}`，日期 `{start}` 至 `{end}`。",
        f"- token_used：`{token_used}`",
        "- 执行边界：只读 FinMind API 探测；未构建样本、未训练模型、未写 provider、未 refresh/publish、未 accepted latest switching、未改前端/API、未触碰交易路径。",
        "",
        "## 1. 产物",
        "",
        f"- raw archive：`{rel(raw_path)}`",
        f"- summary：`{rel(summary_path)}`",
        f"- fields：`{rel(field_path)}`",
        "",
        "## 2. 数据集可得性概览",
        "",
        "| 数据集 | 成功请求 | 失败请求 | 总行数 | 覆盖 symbol | 日期/期间范围 | 主要字段 |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]

    for category, rows in by_dataset.items():
        success = sum(1 for row in rows if row["status"] == "success")
        failed = len(rows) - success
        total_rows = sum(int(row["row_count"]) for row in rows)
        symbols_with_rows = sum(1 for row in rows if int(row["row_count"]) > 0)
        first_values = [row["first_date_or_period"] for row in rows if row["first_date_or_period"]]
        last_values = [row["last_date_or_period"] for row in rows if row["last_date_or_period"]]
        fields = sorted({field for row in rows for field in str(row["columns"]).split("|") if field})
        lines.append(
            f"| `{category}` | {success} | {failed} | {total_rows} | {symbols_with_rows}/{len(rows)} | "
            f"{min(first_values) if first_values else ''} ~ {max(last_values) if last_values else ''} | `{', '.join(fields[:12])}` |"
        )

    lines.extend(
        [
            "",
            "## 3. 初步判断",
            "",
            "- 法人筹码和融资融券属于日频盘后数据，若后续进入模型，应采用保守 T+1 可见规则，并按交易日对齐。",
            "- 月营收可以拿到数值和营收年月，但 FinMind 响应通常不提供明确公告日；不能直接把 `date` 或 `create_time` 当作历史公告日。",
            "- 这次审计只证明“能否拿到数据与字段形态”，不证明这些字段已经 PIT-safe，也不证明能提升策略。",
            "- 若后续要进入 Decision Model，下一步应先做 PIT archive 设计：每行必须有 `source_period`、`available_at`、`days_since_last_report`、`raw_snapshot_id`。",
            "",
            "## 4. 风险",
            "",
            "- 若未来扩大到 Top150 或多年历史，普通 token 可能遇到 402 额度限制。",
            "- 月营收需要官方 MOPS/TWSE/TPEx 公告日来源辅助，否则只能用于人工解释或继续暂缓。",
            "- 不建议直接把这些字段接进前端推荐；应先做覆盖率、IC、TopK、策略回放和泄漏审计。",
        ]
    )
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit small FinMind orthogonal data availability.")
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    parser.add_argument("--start", default="2026-05-01")
    parser.add_argument("--end", default="2026-06-12")
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--token-stdin", action="store_true")
    args = parser.parse_args()

    token = read_token(args)
    if not token:
        raise SystemExit("missing FINMIND_TOKEN/FINMIND_API_TOKEN")

    symbols = [strip_symbol(item) for item in args.symbols.split(",") if strip_symbol(item)]
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    generated_at = utc_now()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_path = OUT_DIR / f"finmind_orthogonal_availability_raw_{stamp}.jsonl"
    summary_path = OUT_DIR / f"finmind_orthogonal_availability_summary_{stamp}.csv"
    field_path = OUT_DIR / f"finmind_orthogonal_availability_fields_{stamp}.csv"

    summary_rows: list[dict[str, Any]] = []
    field_rows: list[dict[str, Any]] = []
    with raw_path.open("w", encoding="utf-8") as fh:
        for category, dataset in DATASETS.items():
            for index, symbol in enumerate(symbols, start=1):
                result = request_dataset(dataset, symbol, args.start, args.end, token, args.timeout)
                rows = result["rows"]
                columns = sorted({key for row in rows for key in row.keys()})
                if category == "monthly_revenue":
                    first_value, last_value = month_range(rows)
                else:
                    first_value, last_value = date_range(rows)
                record = {
                    "category": category,
                    "dataset": dataset,
                    "symbol": f"TW{symbol}",
                    "stock_id": symbol,
                    "start_date": args.start,
                    "end_date": args.end,
                    "fetched_at": utc_now(),
                    "status": result["status"],
                    "http_status": result["http_status"],
                    "finmind_status": result["finmind_status"],
                    "row_count": len(rows),
                    "first_date_or_period": first_value,
                    "last_date_or_period": last_value,
                    "columns": "|".join(columns),
                    "error_message": result["msg"],
                }
                summary_rows.append(record)
                for column in columns:
                    field_rows.append({"category": category, "dataset": dataset, "field": column})
                fh.write(json.dumps({**record, "rows": rows}, ensure_ascii=False) + "\n")
                print(f"[{category} {index}/{len(symbols)}] TW{symbol} rows={len(rows)} status={result['status']}", flush=True)
                if args.sleep > 0:
                    time.sleep(args.sleep)

    write_csv(summary_path, summary_rows)
    write_csv(field_path, field_rows)
    write_report(
        generated_at=generated_at,
        symbols=[f"TW{symbol}" for symbol in symbols],
        start=args.start,
        end=args.end,
        summary_rows=summary_rows,
        raw_path=raw_path,
        summary_path=summary_path,
        field_path=field_path,
        token_used=bool(token),
    )

    print(
        json.dumps(
            {
                "status": "ok",
                "symbols": [f"TW{symbol}" for symbol in symbols],
                "datasets": DATASETS,
                "outputs": [rel(raw_path), rel(summary_path), rel(field_path), rel(DOC_PATH)],
                "safety": {
                    "readonly_finmind_probe": True,
                    "build_samples": False,
                    "model_training": False,
                    "provider_write": False,
                    "accepted_latest_switching": False,
                    "frontend_api_change": False,
                    "trading_paths": False,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
