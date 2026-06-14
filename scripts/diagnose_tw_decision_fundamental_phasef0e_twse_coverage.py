#!/usr/bin/env python3
"""Phase F0E TWSE-only coverage and historical availability diagnosis.

Scope is deliberately narrow:
- TWSE listed monthly revenue official OpenAPI / official-download candidates only.
- Symbol-level coverage diagnostics against existing qlib/Option-C historical Top50/Top150 artifacts.
- No F1 sample construction, no factor tests, no models, no provider writes, no qlib materialization.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data_tw/experiments/decision_fundamental"
DOC_DIR = ROOT / "docs/tw_decision_model_fundamental"

INVENTORY_PATH = OUT_DIR / "phasef0e_twse_official_coverage_inventory.csv"
SYMBOL_COVERAGE_PATH = OUT_DIR / "phasef0e_twse_symbol_coverage.csv"
GATE_SUMMARY_PATH = OUT_DIR / "phasef0e_gate_summary.json"
REPORT_PATH = DOC_DIR / "PHASEF0E_TWSE_COVERAGE_EXECUTION_REPORT_CN.md"

TWSE_OPENAPI = "https://openapi.twse.com.tw/v1/opendata/t187ap05_L"
CALENDAR_PATH = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt"
REPAIRED_SAMPLE_PATH = ROOT / "data_tw/experiments/decision_orthogonal/phase1b_repaired_full_samples.parquet"
PRED_FAST_DIR = ROOT / "qlib_pipeline/data_tw/experiments/option_c_historical_signal_backfill/option_c_historical_backfill_20230101_20231231_pred_fast"

SYMBOL_FIELD = "公司代號"
SOURCE_PERIOD_FIELD = "資料年月"
ANNOUNCEMENT_FIELD = "出表日期"
REVENUE_FIELD = "營業收入-當月營收"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def normalize_symbol(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text.startswith("TW"):
        text = text[2:]
    return text


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


def read_calendar() -> list[str]:
    if not CALENDAR_PATH.exists():
        return []
    return [line.strip() for line in CALENDAR_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def next_trading_day(date_text: str, calendar: list[str]) -> str:
    if not date_text or not calendar:
        return ""
    for day in calendar:
        if day > date_text:
            return day
    return ""


def fetch_json(url: str, timeout: float, params: dict[str, str] | None = None) -> dict[str, Any]:
    headers = {"User-Agent": "Mozilla/5.0 PhaseF0EResearchOnly/1.0", "Accept": "application/json,text/html,*/*"}
    response = requests.get(url, params=params or {}, headers=headers, timeout=timeout)
    text = response.text
    json_ok = False
    payload: Any = None
    try:
        payload = response.json()
        json_ok = True
    except Exception:
        payload = None
    return {
        "url": response.url,
        "http_status": response.status_code,
        "content_type": response.headers.get("content-type", ""),
        "text_sha256": sha256_text(text),
        "text_excerpt": text[:800],
        "json_ok": json_ok,
        "payload": payload,
    }


def summarize_twse_payload(payload: Any, calendar: list[str]) -> dict[str, Any]:
    if not isinstance(payload, list):
        return {
            "row_count": 0,
            "source_periods": [],
            "announcement_dates": [],
            "symbol_count": 0,
            "twse_symbols": set(),
            "has_required_fields": False,
            "sample_available_at_next_trading_day": "",
        }
    source_periods: set[str] = set()
    announcement_dates: set[str] = set()
    symbols: set[str] = set()
    has_required = False
    for row in payload:
        if not isinstance(row, dict):
            continue
        symbol = normalize_symbol(row.get(SYMBOL_FIELD))
        period = roc_yyyymm_to_ad_period(row.get(SOURCE_PERIOD_FIELD))
        announce = roc_yyyMMdd_to_ad_date(row.get(ANNOUNCEMENT_FIELD))
        if symbol:
            symbols.add(symbol)
        if period:
            source_periods.add(period)
        if announce:
            announcement_dates.add(announce)
        if all(k in row for k in [SYMBOL_FIELD, SOURCE_PERIOD_FIELD, ANNOUNCEMENT_FIELD, REVENUE_FIELD]):
            has_required = True
    first_announce = sorted(announcement_dates)[0] if announcement_dates else ""
    return {
        "row_count": len(payload),
        "source_periods": sorted(source_periods),
        "announcement_dates": sorted(announcement_dates),
        "symbol_count": len(symbols),
        "twse_symbols": symbols,
        "has_required_fields": has_required,
        "sample_available_at_next_trading_day": next_trading_day(first_announce, calendar),
    }


def official_probe_rows(timeout: float, calendar: list[str]) -> tuple[list[dict[str, Any]], set[str]]:
    probes = [
        ("base_current", None),
        ("param_date_current_ad", {"date": "202604"}),
        ("param_date_prev_ad", {"date": "202603"}),
        ("param_yyyymm_prev_ad", {"yyyymm": "202603"}),
        ("param_roc_year_month_prev", {"year": "115", "month": "03"}),
    ]
    rows: list[dict[str, Any]] = []
    base_periods: list[str] = []
    base_hash = ""
    current_symbols: set[str] = set()
    for probe_name, params in probes:
        fetched = fetch_json(TWSE_OPENAPI, timeout=timeout, params=params)
        summary = summarize_twse_payload(fetched["payload"], calendar)
        if probe_name == "base_current":
            base_periods = summary["source_periods"]
            base_hash = fetched["text_sha256"]
            current_symbols = set(summary["twse_symbols"])
        same_as_base = bool(base_hash and fetched["text_sha256"] == base_hash and probe_name != "base_current")
        proves_history = bool(probe_name != "base_current" and summary["source_periods"] and summary["source_periods"] != base_periods and not same_as_base)
        rows.append(
            {
                "probe_name": probe_name,
                "source_name": "TWSE OpenAPI listed monthly revenue",
                "request_url": fetched["url"],
                "http_status": fetched["http_status"],
                "json_ok": str(fetched["json_ok"]).lower(),
                "row_count": summary["row_count"],
                "symbol_count": summary["symbol_count"],
                "source_periods": "|".join(summary["source_periods"]),
                "announcement_dates": "|".join(summary["announcement_dates"]),
                "has_required_fields": str(summary["has_required_fields"]).lower(),
                "sample_available_at_next_trading_day": summary["sample_available_at_next_trading_day"],
                "same_payload_as_base": str(same_as_base).lower(),
                "proves_historical_access": str(proves_history).lower(),
                "text_sha256": fetched["text_sha256"],
                "notes": "current official file" if probe_name == "base_current" else ("parameter ignored or same current payload" if same_as_base else ("historical period candidate" if proves_history else "no historical period proven")),
            }
        )
    return rows, current_symbols


def collect_repaired_sample_symbols() -> list[dict[str, Any]]:
    if not REPAIRED_SAMPLE_PATH.exists():
        return []
    cols = ["asof", "symbol", "qlib_rank", "top50_flag", "top150_flag"]
    df = pd.read_parquet(REPAIRED_SAMPLE_PATH, columns=cols)
    rows: list[dict[str, Any]] = []
    for universe_name, flag_col in [("phase1b_repaired_full_top50", "top50_flag"), ("phase1b_repaired_full_top150", "top150_flag")]:
        sub = df[df[flag_col].astype(bool)].copy()
        for symbol, g in sub.groupby(sub["symbol"].map(normalize_symbol)):
            rows.append(
                {
                    "universe_name": universe_name,
                    "symbol": symbol,
                    "source_artifact": rel(REPAIRED_SAMPLE_PATH),
                    "first_asof": str(g["asof"].min()),
                    "last_asof": str(g["asof"].max()),
                    "row_count": int(len(g)),
                    "rank_min": int(g["qlib_rank"].min()) if "qlib_rank" in g else "",
                    "rank_max": int(g["qlib_rank"].max()) if "qlib_rank" in g else "",
                }
            )
    return rows


def collect_pred_fast_symbols(max_files: int | None = None) -> list[dict[str, Any]]:
    if not PRED_FAST_DIR.exists():
        return []
    files = sorted(PRED_FAST_DIR.glob("*/prediction.csv"))
    if max_files:
        files = files[:max_files]
    stats: dict[tuple[str, str], dict[str, Any]] = {}
    for path in files:
        try:
            df = pd.read_csv(path, usecols=["asof", "instrument", "rank"])
        except Exception:
            continue
        for universe_name, sub in [("pred_fast_2023_top50", df[df["rank"] <= 50]), ("pred_fast_2023_top150", df[df["rank"] <= 150])]:
            for _, row in sub.iterrows():
                symbol = normalize_symbol(row["instrument"])
                key = (universe_name, symbol)
                item = stats.setdefault(
                    key,
                    {
                        "universe_name": universe_name,
                        "symbol": symbol,
                        "source_artifact": rel(PRED_FAST_DIR),
                        "first_asof": str(row["asof"]),
                        "last_asof": str(row["asof"]),
                        "row_count": 0,
                        "rank_min": int(row["rank"]),
                        "rank_max": int(row["rank"]),
                    },
                )
                item["row_count"] += 1
                item["first_asof"] = min(item["first_asof"], str(row["asof"]))
                item["last_asof"] = max(item["last_asof"], str(row["asof"]))
                item["rank_min"] = min(item["rank_min"], int(row["rank"]))
                item["rank_max"] = max(item["rank_max"], int(row["rank"]))
    return list(stats.values())


def symbol_coverage_rows(current_twse_symbols: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    symbol_rows = collect_repaired_sample_symbols() + collect_pred_fast_symbols()
    out_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    by_universe: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in symbol_rows:
        by_universe[row["universe_name"]].append(row)
    for universe, rows in sorted(by_universe.items()):
        unique_symbols = {r["symbol"] for r in rows}
        covered_symbols = {s for s in unique_symbols if s in current_twse_symbols}
        total_rows = sum(int(r["row_count"]) for r in rows)
        covered_rows = sum(int(r["row_count"]) for r in rows if r["symbol"] in current_twse_symbols)
        for r in sorted(rows, key=lambda x: x["symbol"]):
            is_covered = r["symbol"] in current_twse_symbols
            out_rows.append(
                {
                    **r,
                    "twse_listed_current_covered": str(is_covered).lower(),
                    "coverage_basis": "current TWSE OpenAPI t187ap05_L symbol set",
                }
            )
        summary_rows.append(
            {
                "universe_name": universe,
                "source_artifact_count": len({r["source_artifact"] for r in rows}),
                "unique_symbols": len(unique_symbols),
                "twse_covered_symbols": len(covered_symbols),
                "missing_symbols": len(unique_symbols - covered_symbols),
                "unique_symbol_coverage_ratio": len(covered_symbols) / len(unique_symbols) if unique_symbols else 0.0,
                "row_count": total_rows,
                "twse_covered_rows": covered_rows,
                "row_weighted_coverage_ratio": covered_rows / total_rows if total_rows else 0.0,
                "first_asof": min(r["first_asof"] for r in rows) if rows else "",
                "last_asof": max(r["last_asof"] for r in rows) if rows else "",
                "sample_missing_symbols": "|".join(sorted(list(unique_symbols - covered_symbols))[:50]),
            }
        )
    return out_rows, summary_rows


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_report(summary: dict[str, Any], inventory_rows: list[dict[str, Any]], coverage_summary: list[dict[str, Any]], generated_at: str) -> str:
    lines = [
        "# Phase F0E TWSE-only Coverage Diagnosis 执行报告",
        "",
        f"- 生成时间：`{generated_at}`",
        "- 阶段目标：只评估 TWSE-only 官方月营收覆盖和历史可得性，不构建样本、不训练模型、不写 provider。",
        "- 执行范围：TWSE listed monthly revenue OpenAPI / official download candidate；本地 qlib Top50/Top150 历史 symbol 覆盖率统计。",
        "- 禁止范围执行情况：未追 TPEx/OTC、未接受 FinMind `date/create_time` 为公告日、未 period-only join、未构建 F1 样本、未做单因子检验、未做规则 baseline、未训练模型、未写 provider、未 refresh/publish、未 accepted latest switching、未 materialize 到 qlib、未前端/API、未 monitor、未交易路径。",
        "",
        "## 1. 修改文件",
        "",
        "- 新增 `scripts/diagnose_tw_decision_fundamental_phasef0e_twse_coverage.py`",
        "",
        "## 2. 生成文件",
        "",
        f"- `{rel(INVENTORY_PATH)}`",
        f"- `{rel(SYMBOL_COVERAGE_PATH)}`",
        f"- `{rel(GATE_SUMMARY_PATH)}`",
        f"- `{rel(REPORT_PATH)}`",
        "",
        "## 3. TWSE 官方源历史可得性",
        "",
        f"- current_source_periods：`{summary['current_source_periods']}`",
        f"- current_announcement_dates：`{summary['current_announcement_dates']}`",
        f"- current_twse_symbol_count：`{summary['current_twse_symbol_count']}`",
        f"- historical_access_proven：`{summary['historical_access_proven']}`",
        f"- official_row_level_announcement_date：`{summary['official_row_level_announcement_date']}`",
        "",
        "| probe_name | http_status | json_ok | row_count | source_periods | announcement_dates | same_payload_as_base | proves_historical_access | notes |",
        "|---|---:|---|---:|---|---|---|---|---|",
    ]
    for row in inventory_rows:
        lines.append(
            f"| {row['probe_name']} | {row['http_status']} | {row['json_ok']} | {row['row_count']} | {row['source_periods']} | {row['announcement_dates']} | {row['same_payload_as_base']} | {row['proves_historical_access']} | {row['notes']} |"
        )
    lines.extend(
        [
            "",
            "## 4. TWSE-only Symbol 覆盖率",
            "",
            "| universe_name | unique_symbols | twse_covered_symbols | unique_symbol_coverage_ratio | row_count | twse_covered_rows | row_weighted_coverage_ratio | first_asof | last_asof |",
            "|---|---:|---:|---:|---:|---:|---:|---|---|",
        ]
    )
    for row in coverage_summary:
        lines.append(
            f"| {row['universe_name']} | {row['unique_symbols']} | {row['twse_covered_symbols']} | {row['unique_symbol_coverage_ratio']:.4f} | {row['row_count']} | {row['twse_covered_rows']} | {row['row_weighted_coverage_ratio']:.4f} | {row['first_asof']} | {row['last_asof']} |"
        )
    lines.extend(
        [
            "",
            "## 5. available_at 处理建议",
            "",
            "- F0E 不构建样本，因此没有实际写入样本级 `available_at`。",
            "- 若后续进入 F1，建议采用保守规则：`available_at = next_trading_day(announcement_date)`，避免无法证明公告时点在当日交易前可见时产生泄漏。",
            f"- 当前 TWSE 文件示例：announcement_date=`{summary['sample_announcement_date']}`，next_trading_day=`{summary['sample_available_at_next_trading_day']}`。",
            "",
            "## 6. F0E Gate",
            "",
            f"- recommended_gate：`{summary['recommended_gate']}`",
            f"- gate_reason：{summary['gate_reason']}",
            "",
            "## 7. 安全边界",
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
            "## 8. 风险与待审查问题",
            "",
            "- TWSE 当前 OpenAPI 只证明当前公开 source_period 可得；参数化 smoke 未证明历史月份可得。",
            "- Top50/Top150 覆盖率对 TWSE-only 子集并非为 100%，排除非上市 symbol 会减少历史 ranking 样本面。",
            "- 在没有连续多个 official source_period 前，不满足进入 F1 的最低条件。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase F0E TWSE-only coverage diagnosis")
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    generated_at = utc_now()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)

    calendar = read_calendar()
    inventory_rows, current_twse_symbols = official_probe_rows(args.timeout, calendar)
    symbol_rows, coverage_summary = symbol_coverage_rows(current_twse_symbols)

    inventory_fields = [
        "probe_name",
        "source_name",
        "request_url",
        "http_status",
        "json_ok",
        "row_count",
        "symbol_count",
        "source_periods",
        "announcement_dates",
        "has_required_fields",
        "sample_available_at_next_trading_day",
        "same_payload_as_base",
        "proves_historical_access",
        "text_sha256",
        "notes",
    ]
    write_csv(INVENTORY_PATH, inventory_rows, inventory_fields)

    symbol_fields = [
        "universe_name",
        "symbol",
        "source_artifact",
        "first_asof",
        "last_asof",
        "row_count",
        "rank_min",
        "rank_max",
        "twse_listed_current_covered",
        "coverage_basis",
    ]
    write_csv(SYMBOL_COVERAGE_PATH, symbol_rows, symbol_fields)

    base = next((row for row in inventory_rows if row["probe_name"] == "base_current"), {})
    current_source_periods = [p for p in str(base.get("source_periods", "")).split("|") if p]
    current_announcement_dates = [d for d in str(base.get("announcement_dates", "")).split("|") if d]
    historical_access_proven = any(row["proves_historical_access"] == "true" for row in inventory_rows)
    official_row_level = bool(base.get("has_required_fields") == "true" and current_announcement_dates)
    min_unique_coverage = min((row["unique_symbol_coverage_ratio"] for row in coverage_summary), default=0.0)
    min_row_coverage = min((row["row_weighted_coverage_ratio"] for row in coverage_summary), default=0.0)

    if historical_access_proven and official_row_level and min_unique_coverage >= 0.8 and min_row_coverage >= 0.8:
        gate = "request_phasef1_twse_only_pit_sample_work=true"
        reason = "TWSE-only coverage and historical official access appear sufficient for a reviewer-scoped F1 proposal."
    elif not historical_access_proven:
        gate = "stop_fundamental_mainline_insufficient_coverage=true"
        reason = "TWSE OpenAPI exposes only the current source_period in this smoke; parameterized historical access was not proven, so a PIT archive cannot be formed."
    else:
        gate = "phasef0e_needs_user_decision=true"
        reason = "Historical access has partial evidence but coverage or availability remains insufficient for automatic F1 authorization."

    summary = {
        "generated_at": generated_at,
        "phase": "Phase F0E",
        "network_used": True,
        "downloaded_data": True,
        "model_training": False,
        "provider_write": False,
        "accepted_latest_switching": False,
        "frontend_api": False,
        "trading_or_order": False,
        "current_source_periods": current_source_periods,
        "current_announcement_dates": current_announcement_dates,
        "sample_announcement_date": current_announcement_dates[0] if current_announcement_dates else "",
        "sample_available_at_next_trading_day": base.get("sample_available_at_next_trading_day", ""),
        "current_twse_symbol_count": len(current_twse_symbols),
        "historical_access_proven": historical_access_proven,
        "official_row_level_announcement_date": official_row_level,
        "coverage_summary": coverage_summary,
        "min_unique_symbol_coverage_ratio": min_unique_coverage,
        "min_row_weighted_coverage_ratio": min_row_coverage,
        "recommended_gate": gate,
        "gate_reason": reason,
        "forbidden_actions": {
            "pursue_tpex_otc_repair": False,
            "accept_finmind_date_as_announcement": False,
            "accept_finmind_create_time_as_announcement": False,
            "period_only_join": False,
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
    REPORT_PATH.write_text(build_report(summary, inventory_rows, coverage_summary, generated_at), encoding="utf-8")

    print(f"wrote {rel(INVENTORY_PATH)}")
    print(f"wrote {rel(SYMBOL_COVERAGE_PATH)}")
    print(f"wrote {rel(GATE_SUMMARY_PATH)}")
    print(f"wrote {rel(REPORT_PATH)}")
    print(json.dumps({"recommended_gate": gate, "historical_access_proven": historical_access_proven, "current_source_periods": current_source_periods, "coverage_universes": len(coverage_summary)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
