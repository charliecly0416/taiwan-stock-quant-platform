#!/usr/bin/env python3
"""Phase F0B limited monthly revenue PIT POC.

This script may call the FinMind monthly revenue endpoint after user
authorization. It writes only decision_fundamental/phasef0b_* artifacts. It
does not write providers, materialize qlib data, build F1 samples, train
models, touch frontend/API, monitor, or trading paths.
"""
from __future__ import annotations

import argparse
import csv
import getpass
import hashlib
import json
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data_tw/experiments/decision_fundamental"
DOC_DIR = ROOT / "docs/tw_decision_model_fundamental"

FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"
DATASET = "TaiwanStockMonthRevenue"

RAW_PATH = OUT_DIR / "phasef0b_monthly_revenue_raw_archive.jsonl"
NORMALIZED_PATH = OUT_DIR / "phasef0b_monthly_revenue_normalized_pit.csv"
PIT_SAMPLES_PATH = OUT_DIR / "phasef0b_pit_validation_samples.csv"
COVERAGE_PATH = OUT_DIR / "phasef0b_coverage_summary.json"
GATE_PATH = OUT_DIR / "phasef0b_gate_summary.json"
REPORT_PATH = DOC_DIR / "PHASEF0B_EXECUTION_REPORT_CN.md"

EXPLICIT_ANNOUNCEMENT_KEYS = [
    "announcement_date",
    "announce_date",
    "disclosure_date",
    "published_date",
    "publish_date",
    "公告日期",
    "申報日期",
    "發布日期",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def strip_symbol(symbol: str) -> str:
    text = str(symbol or "").strip().upper()
    if text.startswith("TW"):
        text = text[2:]
    return text


def read_token(args: argparse.Namespace) -> str:
    token = os.getenv("FINMIND_TOKEN") or os.getenv("FINMIND_API_TOKEN")
    if token:
        return token.strip()
    if args.token_stdin:
        if sys.stdin.isatty():
            return getpass.getpass("FINMIND token: ").strip()
        return sys.stdin.readline().strip()
    return ""


def default_symbols(max_symbols: int) -> list[str]:
    fixed = ["2330", "2317", "2454", "2308", "3008", "3583", "2327", "1216", "1101", "1102"]
    preview = OUT_DIR.parent / "decision_orthogonal/phase1b_repaired_full_samples_preview.csv"
    found: list[str] = []
    if preview.exists():
        try:
            df = pd.read_csv(preview, usecols=["symbol", "qlib_rank"], nrows=5000)
            df = df.sort_values("qlib_rank")
            for value in df["symbol"].astype(str):
                sym = strip_symbol(value)
                if sym and sym not in found:
                    found.append(sym)
        except Exception:
            found = []
    merged = []
    for sym in found + fixed:
        if sym and sym not in merged:
            merged.append(sym)
    return merged[:max_symbols]


def request_finmind(symbol: str, start: str, end: str, token: str, timeout: float) -> dict[str, Any]:
    params: dict[str, Any] = {
        "dataset": DATASET,
        "data_id": symbol,
        "start_date": start,
        "end_date": end,
    }
    if token:
        params["token"] = token
    resp = requests.get(FINMIND_URL, params=params, timeout=timeout)
    payload: dict[str, Any]
    try:
        payload = resp.json()
    except Exception as exc:
        payload = {"status": resp.status_code, "msg": f"json_parse_error:{exc}", "data": []}
    return {
        "http_status": resp.status_code,
        "finmind_status": payload.get("status"),
        "msg": payload.get("msg") or payload.get("message") or "",
        "data": payload.get("data") if isinstance(payload.get("data"), list) else [],
        "columns": sorted(payload.get("data")[0].keys()) if isinstance(payload.get("data"), list) and payload.get("data") else [],
    }


def to_number(value: Any) -> float | None:
    text = str(value or "").replace(",", "").strip()
    if text in ("", "-", "--", "None", "nan"):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def to_source_period(row: dict[str, Any]) -> str:
    year = to_number(row.get("revenue_year"))
    month = to_number(row.get("revenue_month"))
    if year and month:
        return f"{int(year):04d}-{int(month):02d}"
    raw_period = str(row.get("revenue_period") or row.get("period") or "").strip()
    if raw_period:
        return raw_period[:7]
    return ""


def explicit_announcement_date(row: dict[str, Any]) -> str:
    for key in EXPLICIT_ANNOUNCEMENT_KEYS:
        value = str(row.get(key) or "").strip()
        if value:
            return value[:10]
    return ""


def provider_date_candidate(row: dict[str, Any]) -> str:
    return str(row.get("date") or row.get("report_date") or "").strip()[:10]


def available_at_from_announcement(value: str) -> str:
    if not value:
        return ""
    # Conservative POC rule: use next calendar day. A trading-calendar version
    # is deferred to F1/F0B repair if reviewer accepts the source semantics.
    ts = pd.Timestamp(value) + pd.Timedelta(days=1)
    return ts.strftime("%Y-%m-%d")


def payload_hash(row: dict[str, Any]) -> str:
    text = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_report(
    *,
    generated_at: str,
    symbols: list[str],
    raw_rows: list[dict[str, Any]],
    normalized_rows: list[dict[str, Any]],
    status_rows: list[dict[str, Any]],
    coverage: dict[str, Any],
    gate: dict[str, Any],
) -> str:
    explicit_cols = sorted({c for row in status_rows for c in str(row.get("columns", "")).split("|") if c})
    return f"""# Phase F0B Monthly Revenue POC 执行报告

- 生成时间：`{generated_at}`
- 阶段目标：受限验证月营收候选源是否提供 row-level `announcement_date` 或等价披露日期，并验证能否形成独立 raw archive / normalized PIT。
- 执行范围：FinMind `{DATASET}` 小范围 POC，时间 `2024-01-01` 至 `2026-06-11`，symbols `{','.join(symbols)}`。
- 禁止范围执行情况：未拉估值/财报、未全市场回填、未构建 F1 样本、未做单因子检验、未做规则 baseline、未训练模型、未写 provider、未 refresh/publish、未 accepted latest switching、未 materialize 到 qlib、未前端/API、未 monitor、未交易路径。

## 1. 修改文件

- 新增 `scripts/build_tw_decision_fundamental_phasef0b_monthly_revenue_poc.py`

## 2. 生成文件

- `{rel(RAW_PATH)}`
- `{rel(NORMALIZED_PATH)}`
- `{rel(PIT_SAMPLES_PATH)}`
- `{rel(COVERAGE_PATH)}`
- `{rel(GATE_PATH)}`
- `{rel(REPORT_PATH)}`

## 3. 数据来源

- 数据源：FinMind `{DATASET}`。
- token_used：`{coverage['token_used']}`。
- network_used=true。
- raw archive 独立写入 `data_tw/experiments/decision_fundamental/phasef0b_*`，未写 provider。

## 4. 字段探测结果

- FinMind 响应字段合集：`{explicit_cols}`。
- explicit announcement field found：`{coverage['explicit_announcement_field_found']}`。
- provider date candidate field found：`{coverage['provider_date_candidate_field_found']}`。
- 说明：`date` / `report_date` 仅记录为 provider candidate，未直接等同官方公告日；若没有明确公告/披露字段，strict PIT-valid rows 保持 0。

## 5. PIT 处理

- strict PIT 规则：只有明确 `announcement_date` / 等价公告字段存在时，才生成 normalized PIT 行。
- `available_at` POC 规则：`announcement_date + 1 calendar day`；该规则仍需后续审查，当前不进入 F1。
- period-only join：未使用，且明确禁止。
- raw rows 全量保留 `source_period`、`raw_snapshot_id`、`data_source`、`raw_payload_hash`。

## 6. 覆盖率 / 缺失率

- request_count：`{coverage['request_count']}`
- success_count：`{coverage['success_count']}`
- raw_row_count：`{coverage['raw_row_count']}`
- normalized_pit_row_count：`{coverage['normalized_pit_row_count']}`
- symbol_count_with_raw_rows：`{coverage['symbol_count_with_raw_rows']}`
- source_period_count：`{coverage['source_period_count']}`
- missing_announcement_date_count：`{coverage['missing_announcement_date_count']}`
- missing_available_at_count：`{coverage['missing_available_at_count']}`
- excluded_reason_counts：`{coverage['excluded_reason_counts']}`

## 7. F0B Gate

- recommended_gate：`{gate['recommended_gate']}`
- gate_reason：{gate['gate_reason']}

## 8. 安全边界

- model_training=false
- provider_write=false
- accepted_latest_switching=false
- frontend_api=false
- trading_or_order=false
- monitor_writes=false
- target_position_or_weight=false
- 未输出买入/卖出建议、收益承诺或上涨概率承诺。

## 9. 风险与待审查问题

- 若审查者不接受 FinMind `date` 作为公告/披露日期，则本次 POC 不具备进入 F1 的 PIT 证据。
- 若需要官方 MOPS/TWSE disclosure date，建议下一步走 source redesign，而不是用 provider `date` proxy。
- 当前没有生成 F1 样本，也没有计算任何收益标签或因子效果。
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase F0B monthly revenue PIT POC")
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default="2026-06-11")
    parser.add_argument("--symbols", default="")
    parser.add_argument("--max-symbols", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument("--token-stdin", action="store_true")
    args = parser.parse_args()

    generated_at = utc_now()
    snapshot_id = "phasef0b_monthly_revenue_" + generated_at.replace(":", "").replace("-", "").replace("+00:00", "Z")
    token = read_token(args)
    symbols = [strip_symbol(s) for s in args.symbols.split(",") if s.strip()] if args.symbols else default_symbols(args.max_symbols)
    symbols = symbols[: args.max_symbols]
    if not symbols:
        raise SystemExit("no symbols selected")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)

    raw_rows: list[dict[str, Any]] = []
    normalized_rows: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    status_rows: list[dict[str, Any]] = []
    excluded_reasons: Counter[str] = Counter()
    all_columns: set[str] = set()

    for symbol in symbols:
        try:
            result = request_finmind(symbol, args.start, args.end, token, args.timeout)
            data = result["data"]
            status = "success" if result["http_status"] == 200 and data else "empty_or_failed"
            status_rows.append(
                {
                    "symbol": symbol,
                    "status": status,
                    "http_status": result["http_status"],
                    "finmind_status": result["finmind_status"],
                    "row_count": len(data),
                    "msg": str(result["msg"])[:200],
                    "columns": "|".join(result["columns"]),
                }
            )
            all_columns.update(result["columns"])
            for row in data:
                if not isinstance(row, dict):
                    continue
                source_period = to_source_period(row)
                announcement = explicit_announcement_date(row)
                candidate = provider_date_candidate(row)
                available_at = available_at_from_announcement(announcement)
                revenue = to_number(row.get("revenue"))
                quality_flags = []
                if not source_period:
                    quality_flags.append("missing_source_period")
                if not announcement:
                    quality_flags.append("missing_explicit_announcement_date")
                if not available_at:
                    quality_flags.append("missing_available_at")
                if candidate and not announcement:
                    quality_flags.append("provider_date_candidate_not_accepted_as_announcement")
                raw = {
                    "symbol": strip_symbol(row.get("stock_id") or symbol),
                    "source_period": source_period,
                    "announcement_date": announcement,
                    "provider_date_candidate": candidate,
                    "available_at": available_at,
                    "revenue": revenue,
                    "yoy": to_number(row.get("yoy") or row.get("YoY")),
                    "mom": to_number(row.get("mom") or row.get("MoM")),
                    "data_source": f"FinMind:{DATASET}",
                    "raw_snapshot_id": snapshot_id,
                    "ingested_at": generated_at,
                    "source_url_or_dataset": DATASET,
                    "revision_flag": "initial",
                    "raw_payload_hash": payload_hash(row),
                    "quality_flags": ",".join(quality_flags),
                    "raw_json": json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                }
                raw_rows.append(raw)
                if announcement and available_at and source_period:
                    normalized = {k: raw[k] for k in [
                        "symbol",
                        "source_period",
                        "announcement_date",
                        "available_at",
                        "revenue",
                        "yoy",
                        "mom",
                        "data_source",
                        "raw_snapshot_id",
                        "ingested_at",
                        "source_url_or_dataset",
                        "revision_flag",
                    ]}
                    normalized["days_since_last_report"] = ""
                    normalized["quality_flags"] = raw["quality_flags"]
                    normalized_rows.append(normalized)
                else:
                    if not announcement:
                        excluded_reasons["missing_explicit_announcement_date"] += 1
                    elif not available_at:
                        excluded_reasons["missing_available_at"] += 1
                    elif not source_period:
                        excluded_reasons["missing_source_period"] += 1
        except Exception as exc:
            status_rows.append(
                {
                    "symbol": symbol,
                    "status": "error",
                    "http_status": "",
                    "finmind_status": "",
                    "row_count": 0,
                    "msg": str(exc)[:200],
                    "columns": "",
                }
            )
        if args.sleep:
            time.sleep(args.sleep)

    with RAW_PATH.open("w", encoding="utf-8") as fh:
        for row in raw_rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    normalized_fields = [
        "symbol",
        "source_period",
        "announcement_date",
        "available_at",
        "revenue",
        "yoy",
        "mom",
        "data_source",
        "raw_snapshot_id",
        "ingested_at",
        "source_url_or_dataset",
        "revision_flag",
        "days_since_last_report",
        "quality_flags",
    ]
    write_rows(NORMALIZED_PATH, normalized_rows, normalized_fields)

    for row in raw_rows[:20]:
        validation_rows.append(
            {
                "symbol": row["symbol"],
                "source_period": row["source_period"],
                "announcement_date": row["announcement_date"],
                "provider_date_candidate": row["provider_date_candidate"],
                "available_at": row["available_at"],
                "visible_at_asof": bool(row["announcement_date"] and row["available_at"]),
                "validation_result": "pass" if row["announcement_date"] and row["available_at"] else "fail",
                "validation_note": "strict PIT requires explicit announcement/disclosure field; provider date candidate is not accepted automatically",
            }
        )
    write_rows(
        PIT_SAMPLES_PATH,
        validation_rows,
        [
            "symbol",
            "source_period",
            "announcement_date",
            "provider_date_candidate",
            "available_at",
            "visible_at_asof",
            "validation_result",
            "validation_note",
        ],
    )

    coverage = {
        "generated_at": generated_at,
        "network_used": True,
        "token_used": bool(token),
        "downloaded_data": True,
        "raw_archive_written": True,
        "model_training": False,
        "provider_write": False,
        "accepted_latest_switching": False,
        "frontend_api": False,
        "trading_or_order": False,
        "dataset": DATASET,
        "start": args.start,
        "end": args.end,
        "symbols": symbols,
        "request_count": len(symbols),
        "success_count": sum(1 for row in status_rows if row["status"] == "success"),
        "status_rows": status_rows,
        "response_columns": sorted(all_columns),
        "explicit_announcement_field_found": bool(set(EXPLICIT_ANNOUNCEMENT_KEYS) & all_columns),
        "provider_date_candidate_field_found": bool({"date", "report_date"} & all_columns),
        "raw_row_count": len(raw_rows),
        "normalized_pit_row_count": len(normalized_rows),
        "symbol_count_with_raw_rows": len({row["symbol"] for row in raw_rows}),
        "source_period_count": len({row["source_period"] for row in raw_rows if row["source_period"]}),
        "missing_announcement_date_count": sum(1 for row in raw_rows if not row["announcement_date"]),
        "missing_available_at_count": sum(1 for row in raw_rows if not row["available_at"]),
        "excluded_reason_counts": dict(excluded_reasons),
    }
    COVERAGE_PATH.write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if normalized_rows:
        recommended_gate = "request_phasef1_pit_sample_work=true"
        gate_reason = "FinMind response included explicit announcement/disclosure fields and normalized PIT rows were generated."
    elif raw_rows and coverage["provider_date_candidate_field_found"]:
        recommended_gate = "phasef0b_needs_source_redesign=true"
        gate_reason = "FinMind returned monthly revenue rows and a provider date candidate, but no explicit announcement/disclosure field was found; strict PIT-valid rows remain 0."
    else:
        recommended_gate = "stop_fundamental_mainline_no_pit_source=true"
        gate_reason = "No usable monthly revenue rows with announcement_date/available_at evidence were found."
    gate = {
        "generated_at": generated_at,
        "recommended_gate": recommended_gate,
        "gate_reason": gate_reason,
        "phasef1_allowed": recommended_gate == "request_phasef1_pit_sample_work=true",
        "model_training_allowed": False,
        "provider_write_allowed": False,
        "accepted_latest_switching_allowed": False,
        "frontend_api_allowed": False,
        "trading_or_order_allowed": False,
        "raw_row_count": len(raw_rows),
        "normalized_pit_row_count": len(normalized_rows),
        "strict_pit_valid": bool(normalized_rows),
        "period_only_join_used": False,
        "forbidden_actions": {
            "valuation_or_financial_statement": False,
            "full_market_backfill": False,
            "f1_sample": False,
            "single_factor_test": False,
            "rule_baseline": False,
            "model_training": False,
            "risk_filter_model": False,
            "provider_write": False,
            "provider_refresh_publish": False,
            "accepted_latest_switching": False,
            "qlib_materialize": False,
            "frontend_api": False,
            "monitor_writes": False,
            "trading_actions": False,
            "target_position_or_weight": False,
        },
    }
    GATE_PATH.write_text(json.dumps(gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(
        build_report(
            generated_at=generated_at,
            symbols=symbols,
            raw_rows=raw_rows,
            normalized_rows=normalized_rows,
            status_rows=status_rows,
            coverage=coverage,
            gate=gate,
        ),
        encoding="utf-8",
    )

    print(f"wrote {rel(RAW_PATH)}")
    print(f"wrote {rel(NORMALIZED_PATH)}")
    print(f"wrote {rel(PIT_SAMPLES_PATH)}")
    print(f"wrote {rel(COVERAGE_PATH)}")
    print(f"wrote {rel(GATE_PATH)}")
    print(f"wrote {rel(REPORT_PATH)}")
    print(json.dumps({"recommended_gate": recommended_gate, "raw_rows": len(raw_rows), "normalized_pit_rows": len(normalized_rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
