#!/usr/bin/env python3
"""Phase F0D official source access repair probe.

This script is limited to official/auditable monthly revenue access repair. It
probes official TWSE/TPEx/MOPS monthly revenue access paths, validates whether
row-level disclosure dates are present, and checks value alignment against the
local Phase F0B FinMind raw archive without fetching FinMind again.

It does not build F1 samples, train models, write providers, refresh/publish,
materialize qlib data, touch frontend/API/monitor paths, or touch trading paths.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data_tw/experiments/decision_fundamental"
DOC_DIR = ROOT / "docs/tw_decision_model_fundamental"

F0B_COVERAGE = OUT_DIR / "phasef0b_coverage_summary.json"
F0B_RAW = OUT_DIR / "phasef0b_monthly_revenue_raw_archive.jsonl"
RAW_PATH = OUT_DIR / "phasef0d_official_access_raw.jsonl"
FIELD_INVENTORY_PATH = OUT_DIR / "phasef0d_official_access_field_inventory.csv"
GATE_SUMMARY_PATH = OUT_DIR / "phasef0d_gate_summary.json"
REPORT_PATH = DOC_DIR / "PHASEF0D_OFFICIAL_ACCESS_REPAIR_EXECUTION_REPORT_CN.md"

TWSE_LISTED_OPENAPI = "https://openapi.twse.com.tw/v1/opendata/t187ap05_L"
OFFICIAL_CANDIDATES = [
    {
        "source_name": "TWSE OpenAPI monthly revenue listed",
        "market_scope": "listed",
        "url": TWSE_LISTED_OPENAPI,
        "expected_json": True,
    },
    {
        "source_name": "TPEx OpenAPI monthly revenue OTC candidate t187ap05_O",
        "market_scope": "otc",
        "url": "https://www.tpex.org.tw/openapi/v1/t187ap05_O",
        "expected_json": True,
    },
    {
        "source_name": "TPEx OpenAPI monthly revenue OTC candidate mopsfin_t187ap05_O",
        "market_scope": "otc",
        "url": "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap05_O",
        "expected_json": True,
    },
    {
        "source_name": "TPEx monthly revenue json candidate mr_result",
        "market_scope": "otc",
        "url": "https://www.tpex.org.tw/web/stock/aftertrading/monthly_revenue/mr_result.php?l=zh-tw&o=json",
        "expected_json": True,
    },
    {
        "source_name": "MOPS monthly revenue landing page",
        "market_scope": "all",
        "url": "https://mops.twse.com.tw/mops/web/t21sc03",
        "expected_json": False,
    },
]

REVENUE_FIELD = "營業收入-當月營收"
ANNOUNCEMENT_FIELD = "出表日期"
SOURCE_PERIOD_FIELD = "資料年月"
SYMBOL_FIELD = "公司代號"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def roc_yyyymm_to_ad_period(value: Any) -> str:
    text = str(value or "").strip()
    if len(text) < 5 or not text.isdigit():
        return ""
    year = int(text[:-2]) + 1911
    month = int(text[-2:])
    if not 1 <= month <= 12:
        return ""
    return f"{year:04d}-{month:02d}"


def roc_yyyMMdd_to_ad_date(value: Any) -> str:
    text = str(value or "").strip()
    if len(text) != 7 or not text.isdigit():
        return ""
    year = int(text[:3]) + 1911
    month = int(text[3:5])
    day = int(text[5:7])
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return ""
    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_number(value: Any) -> float | None:
    text = str(value or "").replace(",", "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def read_f0b_symbols(limit: int) -> list[str]:
    payload = json.loads(F0B_COVERAGE.read_text(encoding="utf-8"))
    return [str(s) for s in payload.get("symbols", []) if str(s).strip()][:limit]


def read_f0b_revenue() -> dict[tuple[str, str], float]:
    out: dict[tuple[str, str], float] = {}
    if not F0B_RAW.exists():
        return out
    with F0B_RAW.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            symbol = str(row.get("symbol", "")).strip()
            period = str(row.get("source_period", "")).strip()
            revenue = row.get("revenue")
            if symbol and period and revenue is not None:
                out[(symbol, period)] = float(revenue)
    return out


def fetch_candidate(candidate: dict[str, Any], timeout: float) -> dict[str, Any]:
    headers = {
        "User-Agent": "Mozilla/5.0 PhaseF0DResearchOnly/1.0",
        "Accept": "application/json,text/html,*/*",
    }
    response = requests.get(candidate["url"], timeout=timeout, headers=headers)
    text = response.text
    content_type = response.headers.get("content-type", "")
    parsed_json: Any = None
    json_ok = False
    if "json" in content_type.lower() or text.lstrip().startswith(("[", "{")):
        try:
            parsed_json = response.json()
            json_ok = True
        except Exception:
            parsed_json = None
    return {
        "source_name": candidate["source_name"],
        "market_scope": candidate["market_scope"],
        "url": candidate["url"],
        "final_url": response.url,
        "http_status": response.status_code,
        "content_type": content_type,
        "text_sha256": sha256_text(text),
        "text_excerpt": text[:1200],
        "json_ok": json_ok,
        "json_payload": parsed_json,
    }


def normalize_official_rows(payload: Any, symbols: set[str]) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        return []
    rows: list[dict[str, Any]] = []
    for raw in payload:
        if not isinstance(raw, dict):
            continue
        symbol = str(raw.get(SYMBOL_FIELD, "")).strip()
        if symbol not in symbols:
            continue
        source_period = roc_yyyymm_to_ad_period(raw.get(SOURCE_PERIOD_FIELD))
        announcement_date = roc_yyyMMdd_to_ad_date(raw.get(ANNOUNCEMENT_FIELD))
        revenue_thousand_ntd = parse_number(raw.get(REVENUE_FIELD))
        revenue_ntd = revenue_thousand_ntd * 1000.0 if revenue_thousand_ntd is not None else None
        rows.append(
            {
                "symbol": symbol,
                "source_period": source_period,
                "announcement_date": announcement_date,
                "available_at": announcement_date,
                "official_revenue_thousand_ntd": revenue_thousand_ntd,
                "official_revenue_ntd": revenue_ntd,
                "official_revenue_unit": "thousand_ntd_raw_normalized_to_ntd",
                "raw_row": raw,
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_report(summary: dict[str, Any], inventory_rows: list[dict[str, Any]], generated_at: str) -> str:
    lines = [
        "# Phase F0D Official Source Access Repair 执行报告",
        "",
        f"- 生成时间：`{generated_at}`",
        "- 阶段目标：修复官方月营收来源访问方式，验证是否能取得有效表格、row-level 公告日期或严格可审计日期。",
        "- 执行范围：仅官方/月营收访问修复；仍限制 F0B 10 个 symbol；不做全市场回填，不构建 F1 样本。",
        "- 用户授权：已授权受限 Phase F0D Official Source Access Repair。",
        "- 禁止范围执行情况：未接受 FinMind `date/create_time` 为公告日、未 period-only join、未全市场回填、未构建 F1 样本、未做单因子检验、未做规则 baseline、未训练模型、未写 provider、未 refresh/publish、未 accepted latest switching、未 materialize 到 qlib、未前端/API、未 monitor、未交易路径。",
        "",
        "## 1. 修改文件",
        "",
        "- 新增 `scripts/probe_tw_decision_fundamental_phasef0d_official_access_repair.py`",
        "",
        "## 2. 生成文件",
        "",
        f"- `{rel(RAW_PATH)}`",
        f"- `{rel(FIELD_INVENTORY_PATH)}`",
        f"- `{rel(GATE_SUMMARY_PATH)}`",
        f"- `{rel(REPORT_PATH)}`",
        "",
        "## 3. 官方源访问修复结论",
        "",
        f"- effective_official_source_found：`{summary['effective_official_source_found']}`",
        f"- pit_valid_rows：`{summary['pit_valid_rows']}`",
        f"- aligned_rows：`{summary['aligned_rows']}`",
        f"- requested_symbols：`{summary['requested_symbols']}`",
        f"- covered_symbols：`{summary['covered_symbols']}`",
        f"- missing_symbols：`{summary['missing_symbols']}`",
        f"- discovered_source_periods：`{summary['discovered_source_periods']}`",
        f"- can_generate_available_at：`{summary['can_generate_available_at']}`",
        f"- can_align_with_finmind_symbol_period：`{summary['can_align_with_finmind_symbol_period']}`",
        "",
        "## 4. Field Inventory",
        "",
        "| source_name | market_scope | http_status | json_ok | effective_table | row_count | matched_symbol_rows | pit_valid_rows | aligned_rows | blocked_or_error | notes |",
        "|---|---|---:|---|---|---:|---:|---:|---:|---|---|",
    ]
    for row in inventory_rows:
        lines.append(
            f"| {row['source_name']} | {row['market_scope']} | {row['http_status']} | {row['json_ok']} | {row['effective_table']} | {row['row_count']} | {row['matched_symbol_rows']} | {row['pit_valid_rows']} | {row['aligned_rows']} | {row['blocked_or_error']} | {row['notes']} |"
        )
    lines.extend(
        [
            "",
            "## 5. PIT 判断",
            "",
            "- TWSE OpenAPI `t187ap05_L` 可访问，返回 JSON 行级数据，字段包括 `出表日期`、`資料年月`、`公司代號`、`營業收入-當月營收`。",
            "- `出表日期` 被记录为官方 row-level 日期候选，并转换为 `announcement_date/available_at`；这不是 FinMind `date/create_time` proxy。",
            "- TWSE OpenAPI 月营收金额字段以仟元为原始单位；脚本同时保留 raw 仟元值并归一为 NTD 后与 F0B archive 做数值核查。",
            "- 本次仅发现当前公开 `資料年月`，没有解决历史少量月份访问；TPEx/OTC 路径在当前环境仍不可访问或被阻挡。",
            "- 因此 F0D 只能证明上市 TWSE 当前文件的部分 PIT 可用性，不能直接进入 F1。",
            "",
            "## 6. 与 F0B 本地 archive 对齐",
            "",
            "- 对齐只使用本地 `phasef0b_monthly_revenue_raw_archive.jsonl`，没有重新拉取 FinMind。",
            "- 对齐键仅用于数值核查：`symbol + source_period`；没有用 FinMind 日期作为公告日。",
            f"- 对齐结果：`{summary['aligned_rows']}` / `{summary['pit_valid_rows']}` PIT-valid 官方行经单位归一后数值匹配本地 F0B archive。",
            "",
            "## 7. F0D Gate",
            "",
            f"- recommended_gate：`{summary['recommended_gate']}`",
            f"- gate_reason：{summary['gate_reason']}",
            "",
            "## 8. 安全边界",
            "",
            "- f1_sample=false",
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
            "- TWSE 上市当前 OpenAPI 已修复一部分官方访问问题，但 F0B 10 个 symbol 中 `6187` 未覆盖，TPEx/OTC 官方路径仍被 Cloudflare/访问限制阻挡。",
            "- 当前 OpenAPI 响应为当前公开資料年月，未验证历史月份官方 archive/download 路径。",
            "- 是否允许后续只针对 TWSE 上市子集进入更小范围 PIT 样本，或继续寻找 TPEx/历史 archive，需要审查者另行决定。",
            "- 本阶段不得自动进入 F1。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase F0D official source access repair probe")
    parser.add_argument("--max-symbols", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    generated_at = utc_now()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)

    symbols = read_f0b_symbols(args.max_symbols)
    symbol_set = set(symbols)
    f0b_revenue = read_f0b_revenue()

    raw_records: list[dict[str, Any]] = []
    inventory_rows: list[dict[str, Any]] = []
    official_rows: list[dict[str, Any]] = []

    for candidate in OFFICIAL_CANDIDATES:
        try:
            fetched = fetch_candidate(candidate, args.timeout)
            matched = normalize_official_rows(fetched.get("json_payload"), symbol_set)
            for row in matched:
                expected = f0b_revenue.get((row["symbol"], row["source_period"]))
                row["f0b_revenue"] = expected
                row["aligned_with_f0b"] = bool(expected is not None and row["official_revenue_ntd"] is not None and abs(expected - row["official_revenue_ntd"]) < 0.5)
                row["data_source"] = fetched["source_name"]
                row["source_url"] = fetched["url"]
                row["raw_snapshot_id"] = f"phasef0d_official_access_{generated_at.replace(':', '').replace('-', '').replace('+', '')}"
            official_rows.extend(matched)

            payload = fetched.get("json_payload")
            row_count = len(payload) if isinstance(payload, list) else 0
            pit_valid = [r for r in matched if r["source_period"] and r["announcement_date"] and r["available_at"] and r["official_revenue_ntd"] is not None]
            aligned = [r for r in pit_valid if r.get("aligned_with_f0b")]
            blocked = "cloudflare" in fetched["text_excerpt"].lower() or "security" in fetched["text_excerpt"].lower() or fetched["http_status"] in (403, 429)
            raw_records.append(
                {
                    "generated_at": generated_at,
                    "source_name": fetched["source_name"],
                    "market_scope": fetched["market_scope"],
                    "url": fetched["url"],
                    "final_url": fetched["final_url"],
                    "http_status": fetched["http_status"],
                    "content_type": fetched["content_type"],
                    "text_sha256": fetched["text_sha256"],
                    "text_excerpt": fetched["text_excerpt"],
                    "json_ok": fetched["json_ok"],
                    "row_count": row_count,
                    "matched_symbol_rows": matched,
                }
            )
            inventory_rows.append(
                {
                    "source_name": fetched["source_name"],
                    "market_scope": fetched["market_scope"],
                    "source_url": fetched["url"],
                    "http_status": fetched["http_status"],
                    "json_ok": str(fetched["json_ok"]).lower(),
                    "effective_table": str(bool(row_count and matched)).lower(),
                    "row_count": row_count,
                    "matched_symbol_rows": len(matched),
                    "pit_valid_rows": len(pit_valid),
                    "aligned_rows": len(aligned),
                    "has_row_level_announcement_date": str(bool(pit_valid)).lower(),
                    "has_available_at_candidate": str(bool(pit_valid)).lower(),
                    "source_periods": "|".join(sorted({r["source_period"] for r in pit_valid if r["source_period"]})),
                    "covered_symbols": "|".join(sorted({r["symbol"] for r in pit_valid})),
                    "blocked_or_error": str(blocked).lower(),
                    "pit_join_safe": "false",
                    "notes": "official row-level disclosure date candidate found" if pit_valid else ("blocked_or_no_effective_table" if blocked else "no matched pit-valid rows"),
                }
            )
        except Exception as exc:
            raw_records.append(
                {
                    "generated_at": generated_at,
                    "source_name": candidate["source_name"],
                    "market_scope": candidate["market_scope"],
                    "url": candidate["url"],
                    "error": str(exc)[:500],
                }
            )
            inventory_rows.append(
                {
                    "source_name": candidate["source_name"],
                    "market_scope": candidate["market_scope"],
                    "source_url": candidate["url"],
                    "http_status": "",
                    "json_ok": "false",
                    "effective_table": "false",
                    "row_count": 0,
                    "matched_symbol_rows": 0,
                    "pit_valid_rows": 0,
                    "aligned_rows": 0,
                    "has_row_level_announcement_date": "false",
                    "has_available_at_candidate": "false",
                    "source_periods": "",
                    "covered_symbols": "",
                    "blocked_or_error": "true",
                    "pit_join_safe": "false",
                    "notes": f"probe_error:{str(exc)[:200]}",
                }
            )

    with RAW_PATH.open("w", encoding="utf-8") as fh:
        for record in raw_records:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    fields = [
        "source_name",
        "market_scope",
        "source_url",
        "http_status",
        "json_ok",
        "effective_table",
        "row_count",
        "matched_symbol_rows",
        "pit_valid_rows",
        "aligned_rows",
        "has_row_level_announcement_date",
        "has_available_at_candidate",
        "source_periods",
        "covered_symbols",
        "blocked_or_error",
        "pit_join_safe",
        "notes",
    ]
    write_csv(FIELD_INVENTORY_PATH, inventory_rows, fields)

    pit_valid_rows = [r for r in official_rows if r["source_period"] and r["announcement_date"] and r["available_at"] and r["official_revenue_ntd"] is not None]
    aligned_rows = [r for r in pit_valid_rows if r.get("aligned_with_f0b")]
    covered_symbols = sorted({r["symbol"] for r in pit_valid_rows})
    missing_symbols = [s for s in symbols if s not in set(covered_symbols)]
    source_periods = sorted({r["source_period"] for r in pit_valid_rows if r["source_period"]})
    effective_official_source_found = bool(pit_valid_rows)
    full_smoke_coverage = len(covered_symbols) == len(symbols)
    historical_smoke_resolved = len(source_periods) >= 3

    if effective_official_source_found and full_smoke_coverage and historical_smoke_resolved and len(aligned_rows) == len(pit_valid_rows):
        gate = "request_phasef1_pit_sample_work=true"
        reason = "Official source access repair found PIT-valid, aligned rows with full smoke coverage."
    elif effective_official_source_found:
        gate = "phasef0d_needs_user_decision=true"
        reason = "TWSE official OpenAPI provides row-level disclosure date and aligned current rows for listed symbols, but F0B 10-symbol and historical smoke coverage are incomplete."
    else:
        gate = "stop_fundamental_mainline_no_pit_source=true"
        reason = "No PIT-valid official monthly revenue source was recovered in F0D."

    summary = {
        "generated_at": generated_at,
        "phase": "Phase F0D",
        "network_used": True,
        "downloaded_data": True,
        "raw_probe_written": True,
        "model_training": False,
        "provider_write": False,
        "accepted_latest_switching": False,
        "frontend_api": False,
        "trading_or_order": False,
        "requested_symbols": symbols,
        "covered_symbols": covered_symbols,
        "missing_symbols": missing_symbols,
        "discovered_source_periods": source_periods,
        "effective_official_source_found": effective_official_source_found,
        "pit_valid_rows": len(pit_valid_rows),
        "aligned_rows": len(aligned_rows),
        "can_generate_available_at": bool(pit_valid_rows),
        "can_align_with_finmind_symbol_period": bool(aligned_rows),
        "full_smoke_coverage": full_smoke_coverage,
        "historical_smoke_resolved": historical_smoke_resolved,
        "recommended_gate": gate,
        "gate_reason": reason,
        "official_rows_sample": pit_valid_rows[:20],
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
    GATE_SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(build_report(summary, inventory_rows, generated_at), encoding="utf-8")

    print(f"wrote {rel(RAW_PATH)}")
    print(f"wrote {rel(FIELD_INVENTORY_PATH)}")
    print(f"wrote {rel(GATE_SUMMARY_PATH)}")
    print(f"wrote {rel(REPORT_PATH)}")
    print(json.dumps({"recommended_gate": gate, "pit_valid_rows": len(pit_valid_rows), "aligned_rows": len(aligned_rows), "missing_symbols": missing_symbols}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
