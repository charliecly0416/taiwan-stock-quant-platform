#!/usr/bin/env python3
"""Phase F0C official monthly revenue disclosure source probe.

This is a source redesign probe only. It checks whether official MOPS monthly
revenue pages expose row-level announcement/disclosure dates that can be aligned
with symbol + source_period. It does not backfill the full market, build F1
samples, train models, write providers, materialize qlib data, or touch trading
paths.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data_tw/experiments/decision_fundamental"
DOC_DIR = ROOT / "docs/tw_decision_model_fundamental"

RAW_PATH = OUT_DIR / "phasef0c_official_disclosure_probe_raw.jsonl"
FIELD_INVENTORY_PATH = OUT_DIR / "phasef0c_official_disclosure_field_inventory.csv"
SUMMARY_PATH = OUT_DIR / "phasef0c_source_redesign_summary.json"
REPORT_PATH = DOC_DIR / "PHASEF0C_SOURCE_REDESIGN_EXECUTION_REPORT_CN.md"

MOPS_MONTHLY_REVENUE_URL = "https://mops.twse.com.tw/mops/web/ajax_t21sc03"
F0B_COVERAGE = OUT_DIR / "phasef0b_coverage_summary.json"

ANNOUNCEMENT_PATTERNS = [
    "announcement",
    "announce",
    "disclosure",
    "published",
    "publish",
    "公告",
    "申報",
    "發布",
    "發佈",
]

SECURITY_BLOCK_PATTERNS = [
    "FOR SECURITY REASONS",
    "安全性考量",
    "錯誤代碼",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def roc_year(ad_year: int) -> int:
    return ad_year - 1911


def month_iter(start_ym: str, end_ym: str) -> list[str]:
    start = pd.Period(start_ym, freq="M")
    end = pd.Period(end_ym, freq="M")
    return [str(p) for p in pd.period_range(start, end, freq="M")]


def read_f0b_symbols(limit: int) -> list[str]:
    if F0B_COVERAGE.exists():
        payload = json.loads(F0B_COVERAGE.read_text(encoding="utf-8"))
        symbols = [str(s) for s in payload.get("symbols", []) if str(s).strip()]
        if symbols:
            return symbols[:limit]
    return ["2330", "2317", "2454", "2308", "3008", "3583", "2327", "1216", "1101", "1102"][:limit]


def fetch_mops(source_period: str, market_type: str, timeout: float) -> dict[str, Any]:
    year, month = source_period.split("-")
    params = {
        "encodeURIComponent": "1",
        "step": "1",
        "firstin": "1",
        "off": "1",
        "TYPEK": market_type,
        "year": str(roc_year(int(year))),
        "month": f"{int(month):02d}",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 PhaseF0CResearchOnly/1.0",
        "Referer": "https://mops.twse.com.tw/mops/web/t21sc03",
    }
    response = requests.get(MOPS_MONTHLY_REVENUE_URL, params=params, headers=headers, timeout=timeout)
    text = response.text
    return {
        "source_period": source_period,
        "market_type": market_type,
        "url": response.url,
        "http_status": response.status_code,
        "text": text,
        "text_sha256": sha256(text),
    }


def normalize_col(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).strip()


def read_html_tables(html: str) -> list[pd.DataFrame]:
    try:
        tables = pd.read_html(StringIO(html))
    except Exception:
        return []
    out = []
    for table in tables:
        if table.empty:
            continue
        table = table.copy()
        table.columns = [normalize_col(c) for c in table.columns]
        out.append(table)
    return out


def is_security_blocked(html: str) -> bool:
    return any(pattern in html for pattern in SECURITY_BLOCK_PATTERNS)


def find_revenue_table(tables: list[pd.DataFrame]) -> pd.DataFrame:
    for table in tables:
        cols = set(map(str, table.columns))
        if any("公司代號" in c or "公司代碼" in c for c in cols) and any("營業收入" in c or "營收" in c for c in cols):
            return table
    for table in tables:
        cols = set(map(str, table.columns))
        if any("公司代號" in c or "公司代碼" in c for c in cols):
            return table
    return pd.DataFrame()


def extract_symbols(table: pd.DataFrame, symbols: set[str]) -> list[dict[str, Any]]:
    if table.empty:
        return []
    code_col = None
    for col in table.columns:
        if "公司代號" in str(col) or "公司代碼" in str(col):
            code_col = col
            break
    if code_col is None:
        return []
    rows = []
    for _, row in table.iterrows():
        code = str(row.get(code_col, "")).strip()
        if code in symbols:
            rows.append({str(k): ("" if pd.isna(v) else str(v)) for k, v in row.to_dict().items()})
    return rows


def has_announcement_column(columns: list[str]) -> bool:
    joined = "|".join(columns).lower()
    return any(pattern.lower() in joined for pattern in ANNOUNCEMENT_PATTERNS)


def page_date_candidates(html: str) -> list[str]:
    patterns = [
        r"出表日期[:：]?\s*([0-9]{2,3})年\s*([0-9]{1,2})月\s*([0-9]{1,2})日",
        r"資料日期[:：]?\s*([0-9]{2,3})年\s*([0-9]{1,2})月\s*([0-9]{1,2})日",
    ]
    found = []
    for pattern in patterns:
        for match in re.finditer(pattern, html):
            year = int(match.group(1)) + 1911
            month = int(match.group(2))
            day = int(match.group(3))
            found.append(f"{year:04d}-{month:02d}-{day:02d}")
    return sorted(set(found))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def report_text(summary: dict[str, Any], inventory_rows: list[dict[str, Any]], generated_at: str) -> str:
    lines = [
        "# Phase F0C Source Redesign 执行报告",
        "",
        f"- 生成时间：`{generated_at}`",
        "- 阶段目标：探测官方或可审计月营收公告日期来源，判断是否存在 row-level `announcement_date`。",
        "- 执行范围：MOPS 月营收官方页面少量月份与 F0B 10 个 symbol smoke；只写 `phasef0c_*` 产物。",
        "- 禁止范围执行情况：未接受 FinMind `date/create_time` 为公告日、未 period-only join、未全市场回填、未构建 F1 样本、未做单因子检验、未做规则 baseline、未训练模型、未写 provider、未 refresh/publish、未 accepted latest switching、未 materialize 到 qlib、未前端/API、未 monitor、未交易路径。",
        "",
        "## 1. 修改文件",
        "",
        "- 新增 `scripts/probe_tw_decision_fundamental_phasef0c_official_disclosure.py`",
        "",
        "## 2. 生成文件",
        "",
        f"- `{rel(RAW_PATH)}`",
        f"- `{rel(FIELD_INVENTORY_PATH)}`",
        f"- `{rel(SUMMARY_PATH)}`",
        f"- `{rel(REPORT_PATH)}`",
        "",
        "## 3. 官方源探测结论",
        "",
        f"- official_source_exists：`{summary['official_source_exists']}`",
        f"- probed_pages：`{summary['probed_pages']}`",
        f"- successful_pages：`{summary['successful_pages']}`",
        f"- response_tables_found：`{summary['response_tables_found']}`",
        f"- security_blocked_pages：`{summary['security_blocked_pages']}`",
        f"- row_level_announcement_date_found：`{summary['row_level_announcement_date_found']}`",
        f"- page_level_date_candidates：`{summary['page_level_date_candidates']}`",
        f"- matched_symbol_rows：`{summary['matched_symbol_rows']}`",
        "",
        "## 4. 字段 Inventory 摘要",
        "",
        "| source_period | market_type | http_status | security_blocked | table_found | row_count | matched_symbol_rows | has_row_level_announcement_column | page_date_candidates | columns |",
        "|---|---|---:|---|---|---:|---:|---|---|---|",
    ]
    for row in inventory_rows:
        lines.append(
            f"| {row['source_period']} | {row['market_type']} | {row['http_status']} | {row['security_blocked']} | {row['table_found']} | {row['row_count']} | {row['matched_symbol_rows']} | {row['has_row_level_announcement_column']} | {row['page_date_candidates']} | {row['columns']} |"
        )
    lines.extend(
        [
            "",
            "## 5. PIT 判断",
            "",
            "- MOPS `ajax_t21sc03` 是本阶段按审查文档尝试的官方候选入口，但本环境返回安全拦截页，未验证到有效官方表格。",
            "- 当前探测没有发现 row-level `announcement_date` / `disclosure_date` 字段，也没有发现可用表格列。",
            "- 页面层级日期候选若存在，也不能证明每个 `symbol + source_period` 的 row-level 公告日期。",
            "- 因此当前不能生成可审计 `available_at`，不能进入 F1。",
            "",
            "## 6. 与 FinMind 对齐判断",
            "",
            "- 本次 MOPS 响应被安全拦截，未取得可用于与 FinMind 对齐的官方表格。",
            "- 即使后续取得数值表格，仍必须证明 row-level 公告日期或严格可审计的 `available_at`，否则不足以满足 PIT 样本要求。",
            "",
            "## 7. F0C Gate",
            "",
            f"- recommended_gate：`{summary['recommended_gate']}`",
            f"- gate_reason：{summary['gate_reason']}",
            "",
            "## 8. 安全边界",
            "",
            "- model_training=false",
            "- provider_write=false",
            "- accepted_latest_switching=false",
            "- frontend_api=false",
            "- trading_or_order=false",
            "- monitor_writes=false",
            "- target_position_or_weight=false",
            "- 未输出买入/卖出建议、收益承诺或上涨概率承诺。",
            "",
            "## 9. 风险与待审查问题",
            "",
            "- 本环境 MOPS 官方候选端点返回安全拦截页，当前只能证明该请求路径未取得有效表格，不能证明官方源不存在。",
            "- 如果审查者认为应尝试其他官方下载路径、手动归档、浏览器态请求或 TWSE/TPEx 公开档案，需要另开后续阶段；本阶段没有扩展分支。",
            "- 若必须 row-level announcement_date，当前探测不足以支持 fundamental 主线进入 F1。",
            "- 后续不能通过放宽 PIT 规则或接受 FinMind date proxy 来绕过该结论。",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase F0C official monthly revenue disclosure probe")
    parser.add_argument("--start-month", default="2024-01")
    parser.add_argument("--end-month", default="2026-06")
    parser.add_argument("--probe-months", default="2024-01,2025-01,2026-05")
    parser.add_argument("--max-symbols", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    generated_at = utc_now()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)

    symbols = set(read_f0b_symbols(args.max_symbols))
    requested_months = [m.strip() for m in args.probe_months.split(",") if m.strip()]
    allowed_months = set(month_iter(args.start_month, args.end_month))
    months = [m for m in requested_months if m in allowed_months]
    if not months:
        months = [args.start_month]

    raw_records: list[dict[str, Any]] = []
    inventory_rows: list[dict[str, Any]] = []
    matched_rows_by_page: dict[str, list[dict[str, Any]]] = {}

    for source_period in months:
        for market_type in ["sii", "otc"]:
            try:
                payload = fetch_mops(source_period, market_type, args.timeout)
                blocked = is_security_blocked(payload["text"])
                tables = read_html_tables(payload["text"])
                table = find_revenue_table(tables)
                columns = [str(c) for c in table.columns] if not table.empty else []
                matched = extract_symbols(table, symbols)
                dates = page_date_candidates(payload["text"])
                record = {
                    "generated_at": generated_at,
                    "source": "MOPS",
                    "endpoint": MOPS_MONTHLY_REVENUE_URL,
                    "source_period": source_period,
                    "market_type": market_type,
                    "url": payload["url"],
                    "http_status": payload["http_status"],
                    "text_sha256": payload["text_sha256"],
                    "security_blocked": blocked,
                    "text_excerpt": payload["text"][:5000],
                    "table_count": len(tables),
                    "selected_table_columns": columns,
                    "selected_table_row_count": int(len(table)) if not table.empty else 0,
                    "matched_symbol_rows": matched,
                    "page_date_candidates": dates,
                }
                raw_records.append(record)
                matched_rows_by_page[f"{source_period}:{market_type}"] = matched
                inventory_rows.append(
                    {
                        "source_period": source_period,
                        "market_type": market_type,
                        "source_name": "MOPS monthly revenue",
                        "source_url": payload["url"],
                        "http_status": payload["http_status"],
                        "security_blocked": str(blocked).lower(),
                        "table_found": str(not table.empty).lower(),
                        "row_count": int(len(table)) if not table.empty else 0,
                        "matched_symbol_rows": len(matched),
                        "columns": "|".join(columns),
                        "has_symbol": str(any("公司代號" in c or "公司代碼" in c for c in columns)).lower(),
                        "has_source_period": "true",
                        "has_monthly_revenue": str(any("營業收入" in c or "營收" in c for c in columns)).lower(),
                        "has_row_level_announcement_column": str(has_announcement_column(columns)).lower(),
                        "has_page_level_date_candidate": str(bool(dates)).lower(),
                        "page_date_candidates": "|".join(dates),
                        "can_align_with_finmind_symbol_period": str(bool(matched)).lower(),
                        "pit_join_safe": "false",
                        "notes": (
                            "MOPS response security-blocked; no effective official table validated."
                            if blocked
                            else (
                                "Official monthly revenue table found, but row-level announcement/disclosure date column is not proven."
                                if not has_announcement_column(columns)
                                else "Row-level announcement-like column found; requires reviewer validation."
                            )
                        ),
                    }
                )
            except Exception as exc:
                inventory_rows.append(
                    {
                        "source_period": source_period,
                        "market_type": market_type,
                        "source_name": "MOPS monthly revenue",
                        "source_url": MOPS_MONTHLY_REVENUE_URL,
                        "http_status": "",
                        "security_blocked": "false",
                        "table_found": "false",
                        "row_count": 0,
                        "matched_symbol_rows": 0,
                        "columns": "",
                        "has_symbol": "false",
                        "has_source_period": "true",
                        "has_monthly_revenue": "false",
                        "has_row_level_announcement_column": "false",
                        "has_page_level_date_candidate": "false",
                        "page_date_candidates": "",
                        "can_align_with_finmind_symbol_period": "false",
                        "pit_join_safe": "false",
                        "notes": f"probe_error:{str(exc)[:200]}",
                    }
                )

    with RAW_PATH.open("w", encoding="utf-8") as fh:
        for record in raw_records:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    fields = [
        "source_period",
        "market_type",
        "source_name",
        "source_url",
        "http_status",
        "security_blocked",
        "table_found",
        "row_count",
        "matched_symbol_rows",
        "columns",
        "has_symbol",
        "has_source_period",
        "has_monthly_revenue",
        "has_row_level_announcement_column",
        "has_page_level_date_candidate",
        "page_date_candidates",
        "can_align_with_finmind_symbol_period",
        "pit_join_safe",
        "notes",
    ]
    write_csv(FIELD_INVENTORY_PATH, inventory_rows, fields)

    row_level_found = any(row["has_row_level_announcement_column"] == "true" for row in inventory_rows)
    official_exists = any(row["table_found"] == "true" for row in inventory_rows)
    page_dates = sorted({d for row in inventory_rows for d in str(row["page_date_candidates"]).split("|") if d})
    matched_count = sum(int(row["matched_symbol_rows"]) for row in inventory_rows)
    security_blocked_pages = sum(1 for row in inventory_rows if row.get("security_blocked") == "true")
    if row_level_found:
        gate = "request_phasef0d_official_archive_poc=true"
        reason = "Official source probe found row-level announcement-like columns; reviewer must validate before archive POC."
    elif official_exists:
        gate = "stop_fundamental_mainline_no_pit_source=true"
        reason = "Official MOPS monthly revenue source exists and can expose revenue rows, but this probe found no row-level announcement_date/disclosure_date field; available_at cannot be audited."
    else:
        gate = "phasef0c_needs_user_decision=true"
        if security_blocked_pages:
            reason = "MOPS official candidate endpoint returned security-blocked pages in this environment; no effective official table or row-level announcement date was validated."
        else:
            reason = "Official monthly revenue endpoint could not be validated in this limited probe; user/reviewer must decide whether to attempt another source."
    summary = {
        "generated_at": generated_at,
        "phase": "Phase F0C",
        "network_used": True,
        "downloaded_data": True,
        "raw_probe_written": True,
        "model_training": False,
        "provider_write": False,
        "accepted_latest_switching": False,
        "frontend_api": False,
        "trading_or_order": False,
        "symbols": sorted(symbols),
        "months": months,
        "probed_pages": len(inventory_rows),
        "successful_pages": sum(1 for row in inventory_rows if str(row["http_status"]) == "200"),
        "official_source_exists": official_exists,
        "response_tables_found": sum(1 for row in inventory_rows if row["table_found"] == "true"),
        "security_blocked_pages": security_blocked_pages,
        "row_level_announcement_date_found": row_level_found,
        "page_level_date_candidates": page_dates,
        "matched_symbol_rows": matched_count,
        "can_generate_available_at": False,
        "can_align_with_finmind_symbol_period": matched_count > 0,
        "recommended_gate": gate,
        "gate_reason": reason,
        "forbidden_actions": {
            "accept_finmind_date_as_announcement": False,
            "accept_finmind_create_time_as_announcement": False,
            "period_only_join": False,
            "full_market_backfill": False,
            "f1_sample": False,
            "single_factor_test": False,
            "rule_baseline": False,
            "model_training": False,
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
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(report_text(summary, inventory_rows, generated_at), encoding="utf-8")

    print(f"wrote {rel(RAW_PATH)}")
    print(f"wrote {rel(FIELD_INVENTORY_PATH)}")
    print(f"wrote {rel(SUMMARY_PATH)}")
    print(f"wrote {rel(REPORT_PATH)}")
    print(json.dumps({"recommended_gate": gate, "row_level_announcement_date_found": row_level_found, "matched_symbol_rows": matched_count}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
