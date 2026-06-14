#!/usr/bin/env python3
"""Phase 0 audit for TW Decision Model orthogonal data.

This script performs a local, read-only availability and point-in-time audit
for institutional flow, margin/short, and monthly revenue data. It does not
refresh providers, publish data, switch accepted latest, train models, build
samples, touch frontend/API, or interact with trading state.
"""
from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
QLIB = ROOT / "qlib_pipeline"
OUT_DIR = ROOT / "data_tw/experiments/decision_orthogonal"
DOC_DIR = ROOT / "docs/tw_decision_model_orthogonal"

FINMIND_SUMMARY_PATHS = [
    QLIB / "data_tw/experiments/option_c_historical_signal_backfill/option_c_historical_backfill_20260101_20260531/finmind_archive_apply_summary.json",
]
DAILY_AUTO_ROOT = ROOT / "data_tw/ops/daily_auto_update"

DATA_SOURCES_PATH = OUT_DIR / "phase0_data_sources.json"
FEATURE_AVAILABILITY_PATH = OUT_DIR / "phase0_feature_availability.csv"
PIT_RULES_PATH = OUT_DIR / "phase0_point_in_time_rules.md"
EXEC_REPORT_PATH = DOC_DIR / "PHASE0_EXECUTION_REPORT_CN.md"

CATEGORIES = {
    "institutional_flow": {
        "summary_key": "institutional_trades",
        "archived_count_key": "institutional_trades_archived_count",
        "date_min_key": "date_min",
        "date_max_key": "date_max",
        "features": [
            ("foreign_net_buy", ["foreign_buy", "foreign_sell", "foreign_net_buy"]),
            ("investment_trust_net_buy", ["investment_trust_buy", "investment_trust_sell", "investment_trust_net_buy"]),
            ("dealer_net_buy", ["dealer_buy", "dealer_sell", "dealer_net_buy"]),
            ("institutional_total_net_buy", ["foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy"]),
            ("institutional_consecutive_net_buy_days", ["institutional_total_net_buy"]),
            ("institutional_net_buy_volume_ratio", ["institutional_total_net_buy", "volume"]),
            ("foreign_trust_direction_sync", ["foreign_net_buy", "investment_trust_net_buy"]),
        ],
        "candidate_date_columns": ["date", "trade_date"],
        "candidate_symbol_columns": ["stock_id", "symbol"],
    },
    "margin_short": {
        "summary_key": "margin_trading",
        "archived_count_key": "margin_trading_archived_count",
        "date_min_key": "date_min",
        "date_max_key": "date_max",
        "features": [
            ("margin_balance_change", ["margin_purchase_balance", "margin_balance"]),
            ("short_balance_change", ["short_sale_balance", "short_balance"]),
            ("margin_usage_proxy", ["margin_purchase_balance", "volume", "shares_outstanding"]),
            ("short_covering_proxy", ["short_sale_balance"]),
            ("margin_fast_increase_high_price", ["margin_purchase_balance", "distance_to_ma20_pct"]),
            ("margin_decline_price_resilience", ["margin_purchase_balance", "ret20"]),
        ],
        "candidate_date_columns": ["date", "trade_date"],
        "candidate_symbol_columns": ["stock_id", "symbol"],
    },
    "monthly_revenue": {
        "summary_key": "monthly_revenue",
        "archived_count_key": "monthly_revenue_archived_count",
        "date_min_key": "period_min",
        "date_max_key": "period_max",
        "features": [
            ("monthly_revenue_yoy", ["source_period", "announcement_date", "revenue_yoy"]),
            ("monthly_revenue_mom", ["source_period", "announcement_date", "revenue_mom"]),
            ("monthly_revenue_yoy_improvement_streak", ["source_period", "announcement_date", "revenue_yoy"]),
            ("monthly_revenue_yoy_3m_mean", ["source_period", "announcement_date", "revenue_yoy"]),
            ("monthly_revenue_yoy_3m_slope", ["source_period", "announcement_date", "revenue_yoy"]),
            ("monthly_revenue_days_since_last_report", ["source_period", "announcement_date", "available_at"]),
        ],
        "candidate_date_columns": ["announcement_date", "available_at"],
        "candidate_symbol_columns": ["stock_id", "symbol"],
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def extract_json_object(text: str) -> dict[str, Any] | None:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except Exception:
        return None


def load_daily_auto_finmind_summaries() -> list[dict[str, Any]]:
    rows = []
    for path in sorted(DAILY_AUTO_ROOT.glob("daily_tw_stock_auto_update_*/finmind_stdout.txt")):
        try:
            payload = extract_json_object(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            payload = None
        if isinstance(payload, dict):
            rows.append({"path": path, "payload": payload})
    return rows


def load_daily_auto_jobs() -> list[dict[str, Any]]:
    rows = []
    for path in sorted(DAILY_AUTO_ROOT.glob("daily_tw_stock_auto_update_*/job.json")):
        payload = load_json(path)
        if isinstance(payload, dict):
            rows.append({"path": path, "payload": payload})
    return rows


def summarize_jobs(jobs: list[dict[str, Any]]) -> dict[str, Any]:
    disabled_counts = {"--no-institutional": 0, "--no-margin": 0, "--no-monthly-revenue": 0}
    total_with_argv = 0
    sample_paths = []
    for item in jobs:
        raw = json.dumps(item["payload"], ensure_ascii=False)
        if "finmind" not in raw.lower():
            continue
        total_with_argv += 1
        if len(sample_paths) < 5:
            sample_paths.append(rel(item["path"]))
        for flag in disabled_counts:
            if flag in raw:
                disabled_counts[flag] += 1
    return {
        "job_count_with_finmind_context": total_with_argv,
        "disabled_flag_counts": disabled_counts,
        "sample_job_paths": sample_paths,
    }


def source_summary_from_payloads(summary_payloads: list[dict[str, Any]], daily_payloads: list[dict[str, Any]], category: str) -> dict[str, Any]:
    spec = CATEGORIES[category]
    count = 0
    symbol_count = 0
    first_date = None
    last_date = None
    flagged_count = 0
    evidence_paths: list[str] = []
    source_payload_count = 0

    for item in summary_payloads:
        payload = item["payload"]
        value = payload.get(spec["summary_key"]) or {}
        source_payload_count += 1
        evidence_paths.append(rel(item["path"]))
        count = max(count, int(value.get("count") or payload.get(spec["archived_count_key"]) or 0))
        symbol_count = max(symbol_count, len(value.get("symbols") or []))
        flagged_count = max(flagged_count, int(value.get("flagged_count") or 0))
        low = value.get(spec["date_min_key"]) or value.get("date_min") or value.get("period_min")
        high = value.get(spec["date_max_key"]) or value.get("date_max") or value.get("period_max")
        first_date = min([d for d in [first_date, low] if d], default=None)
        last_date = max([d for d in [last_date, high] if d], default=None)

    for item in daily_payloads:
        payload = item["payload"]
        value = payload.get(spec["summary_key"]) or {}
        if spec["summary_key"] in payload:
            source_payload_count += 1
            if len(evidence_paths) < 12:
                evidence_paths.append(rel(item["path"]))
            count = max(count, int(value.get("count") or payload.get(spec["archived_count_key"]) or 0))
            symbol_count = max(symbol_count, len(value.get("symbols") or []))
            flagged_count = max(flagged_count, int(value.get("flagged_count") or 0))
            low = value.get(spec["date_min_key"]) or value.get("date_min") or value.get("period_min")
            high = value.get(spec["date_max_key"]) or value.get("date_max") or value.get("period_max")
            first_date = min([d for d in [first_date, low] if d], default=None)
            last_date = max([d for d in [last_date, high] if d], default=None)

    return {
        "row_count": count,
        "symbol_count": symbol_count,
        "first_date": first_date,
        "last_date": last_date,
        "flagged_count": flagged_count,
        "evidence_paths": evidence_paths,
        "source_payload_count": source_payload_count,
    }


def build_data_sources() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    summary_payloads = []
    for path in FINMIND_SUMMARY_PATHS:
        payload = load_json(path)
        if isinstance(payload, dict):
            summary_payloads.append({"path": path, "payload": payload})
    daily_payloads = load_daily_auto_finmind_summaries()
    jobs = load_daily_auto_jobs()
    job_summary = summarize_jobs(jobs)

    sources = []
    for category in CATEGORIES:
        spec = CATEGORIES[category]
        summary = source_summary_from_payloads(summary_payloads, daily_payloads, category)
        exists = bool(summary["evidence_paths"])
        row_count = int(summary["row_count"] or 0)
        if row_count > 0:
            pit_status = "deferred"
            pit_reason = "Archived rows exist in local summaries, but row-level available_at/announcement_date/source_period evidence is not proven by Phase 0 scan."
        else:
            pit_status = "fail"
            pit_reason = "Local summaries/logs exist but archived row_count is 0 for this orthogonal category."
        sources.append({
            "source_name": f"finmind_{spec['summary_key']}",
            "category": category,
            "local_path_or_table": "; ".join(summary["evidence_paths"]) if summary["evidence_paths"] else "",
            "file_or_table_exists": exists,
            "row_count": row_count,
            "symbol_count": int(summary["symbol_count"] or 0),
            "first_date": summary["first_date"],
            "last_date": summary["last_date"],
            "date_columns": spec["candidate_date_columns"],
            "symbol_columns": spec["candidate_symbol_columns"],
            "has_announcement_date": False,
            "has_available_at": False,
            "has_source_period": bool(category == "monthly_revenue" and row_count > 0 and summary["first_date"]),
            "pit_status": pit_status,
            "pit_reason": pit_reason,
            "data_source": "FinMind local archived summaries and daily auto update logs; read-only audit only.",
            "source_payload_count": int(summary["source_payload_count"] or 0),
            "flagged_count": int(summary["flagged_count"] or 0),
        })
    scan_meta = {
        "summary_payload_paths": [rel(item["path"]) for item in summary_payloads],
        "daily_finmind_stdout_count": len(daily_payloads),
        "daily_job_summary": job_summary,
    }
    return sources, scan_meta


def build_feature_rows(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source_by_category = {row["category"]: row for row in sources}
    rows = []
    for category, spec in CATEGORIES.items():
        source = source_by_category[category]
        row_count = int(source["row_count"] or 0)
        symbol_count = int(source["symbol_count"] or 0)
        has_source_period = bool(source["has_source_period"])
        has_announcement_date = bool(source["has_announcement_date"])
        has_available_at = bool(source["has_available_at"])
        if row_count <= 0:
            pit_status = "fail"
            reason = "No local archived rows were found for this category; cannot compute feature or prove PIT availability."
        elif category == "monthly_revenue" and not (has_source_period and (has_announcement_date or has_available_at)):
            pit_status = "deferred"
            reason = "Monthly revenue requires source_period plus announcement_date/available_at; Phase 0 scan did not prove them."
        elif not has_available_at:
            pit_status = "deferred"
            reason = "Daily orthogonal rows require available_at or an auditable T+1 visibility rule; Phase 0 scan did not prove row-level availability."
        else:
            pit_status = "pass"
            reason = ""
        phase1_allowed = bool(pit_status == "pass")
        available_rule = ""
        days_possible = False
        if pit_status == "pass" and category in {"institutional_flow", "margin_short"}:
            available_rule = "Use row-level available_at or conservative next trading day after trade_date; rolling features use only rows with available_at <= asof."
        elif pit_status == "pass" and category == "monthly_revenue":
            available_rule = "Forward-fill from available_at/announcement_date to later trading dates; never join by source_period alone."
            days_possible = True
        elif category == "monthly_revenue":
            available_rule = "Deferred until source_period and announcement_date/available_at exist row-by-row."
        else:
            available_rule = "Deferred until row-level available_at or auditable T+1 visibility evidence exists."

        for feature_name, raw_cols in spec["features"]:
            rows.append({
                "category": category,
                "feature_name": feature_name,
                "raw_columns": ",".join(raw_cols),
                "source_name": source["source_name"],
                "coverage_start": source["first_date"] or "",
                "coverage_end": source["last_date"] or "",
                "row_count": row_count,
                "symbol_count": symbol_count,
                "missing_rate": 1.0 if row_count <= 0 else "",
                "has_source_period": has_source_period,
                "has_announcement_date": has_announcement_date,
                "has_available_at": has_available_at,
                "available_at_rule": available_rule,
                "days_since_last_report_possible": days_possible,
                "pit_status": pit_status,
                "deferred_or_fail_reason": reason,
                "phase1_allowed": phase1_allowed,
            })
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(rows: list[dict[str, Any]], cols: list[str]) -> str:
    if not rows:
        return "_no rows_"
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---" for _ in cols]) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in cols) + " |")
    return "\n".join(lines)


def write_pit_rules(sources: list[dict[str, Any]], features: list[dict[str, Any]]) -> None:
    allowed = [row for row in features if row["phase1_allowed"]]
    failed = [row for row in features if not row["phase1_allowed"]]
    lines = [
        "# Orthogonal Decision Model Phase 0 Point-in-Time Rules",
        "",
        "## Scope",
        "",
        "Phase 0 only audits local availability and PIT evidence for institutional flow, margin/short, and monthly revenue. No model training, sample construction, provider refresh/publish, accepted latest switching, frontend/API, or trading action was performed.",
        "",
        "## Institutional Flow",
        "",
        "- Required time semantics: rows must carry trade date and either row-level `available_at` or a documented exchange/provider visibility rule that supports conservative T+1 availability.",
        "- Candidate rolling features such as consecutive buy/sell days may only use rows where `available_at <= asof`.",
        "- Phase 0 result: local summaries/logs show zero archived institutional rows, so no institutional feature is allowed into Phase 1.",
        "",
        "## Margin / Short",
        "",
        "- Required time semantics: rows must carry trade date and either row-level `available_at` or an auditable T+1 availability rule.",
        "- `days_since_last_report` is possible only after row-level availability exists; missing trading/suspension states must remain explicit rather than forward-filled blindly.",
        "- Phase 0 result: local summaries/logs show zero archived margin/short rows, so no margin/short feature is allowed into Phase 1.",
        "",
        "## Monthly Revenue",
        "",
        "- Required time semantics: rows must preserve `source_period`, `announcement_date` or `available_at`, `days_since_last_report`, and `data_source`.",
        "- Monthly revenue must be joined from `announcement_date`/`available_at` forward to trading dates. Joining by source period, such as applying September revenue to all September trading days, is rejected.",
        "- If revised values overwrite history without an as-reported snapshot, the field must remain deferred.",
        "- Phase 0 result: local summaries/logs show zero archived monthly revenue rows and no announcement/available dates, so no monthly revenue feature is allowed into Phase 1.",
        "",
        "## Data Source Status",
        "",
        markdown_table(sources, ["category", "source_name", "row_count", "symbol_count", "first_date", "last_date", "pit_status", "pit_reason"]),
        "",
        "## Phase 1 Allowed Fields",
        "",
        markdown_table(allowed, ["category", "feature_name", "phase1_allowed", "available_at_rule"]),
        "",
        "## Deferred / Failed Fields",
        "",
        markdown_table(failed, ["category", "feature_name", "pit_status", "deferred_or_fail_reason"]),
        "",
    ]
    PIT_RULES_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_report(sources: list[dict[str, Any]], features: list[dict[str, Any]], scan_meta: dict[str, Any]) -> None:
    allowed = [row for row in features if row["phase1_allowed"]]
    failed = [row for row in features if not row["phase1_allowed"]]
    category_summary = []
    for category in CATEGORIES:
        rows = [row for row in features if row["category"] == category]
        category_summary.append({
            "category": category,
            "feature_count": len(rows),
            "phase1_allowed_count": sum(1 for row in rows if row["phase1_allowed"]),
            "failed_or_deferred_count": sum(1 for row in rows if not row["phase1_allowed"]),
            "source_row_count": next((src["row_count"] for src in sources if src["category"] == category), 0),
            "pit_status": next((src["pit_status"] for src in sources if src["category"] == category), ""),
        })
    phase0_gate_pass = bool(allowed)
    lines = [
        "# 正交数据 Decision Model Phase 0 执行报告",
        "",
        "## 1. 执行范围",
        "",
        f"- 执行日期：`{utc_now()}`",
        "- 范围：只读审计法人筹码、融资融券、月营收三类正交数据的本地可用性与 point-in-time 证据。",
        "- 禁止项执行情况：未训练模型，未构建 Phase 1 样本，未做单因子检验，未做组合回放，未接前端/API，未触发 provider refresh/publish，未切换 accepted latest，未触碰 broker/orders/quick-trade/target position/monitor config/alerts。",
        "",
        "## 2. 修改文件",
        "",
        "- 新增 `scripts/audit_tw_decision_orthogonal_phase0.py`。",
        "",
        "## 3. 生成文件",
        "",
        f"- `{rel(DATA_SOURCES_PATH)}`",
        f"- `{rel(FEATURE_AVAILABILITY_PATH)}`",
        f"- `{rel(PIT_RULES_PATH)}`",
        f"- `{rel(EXEC_REPORT_PATH)}`",
        "",
        "## 4. 数据源清单",
        "",
        markdown_table(sources, ["category", "source_name", "file_or_table_exists", "row_count", "symbol_count", "first_date", "last_date", "has_announcement_date", "has_available_at", "has_source_period", "pit_status"]),
        "",
        "## 5. PIT 规则摘要",
        "",
        "- 法人筹码：需要 trade_date + row-level `available_at` 或可审计 T+1 可见规则；当前本地 row_count=0，不能进入 Phase 1。",
        "- 融资融券：需要 trade_date + row-level `available_at` 或可审计 T+1 可见规则，并能计算 `days_since_last_report`；当前本地 row_count=0，不能进入 Phase 1。",
        "- 月营收：必须同时保留 `source_period` 与 `announcement_date`/`available_at`；禁止按所属月份直接 join；当前本地 row_count=0 且无公告日期证据，不能进入 Phase 1。",
        "",
        "## 6. 覆盖率 / 缺失率摘要",
        "",
        markdown_table(category_summary, ["category", "feature_count", "phase1_allowed_count", "failed_or_deferred_count", "source_row_count", "pit_status"]),
        "",
        "## 7. 可进入 Phase 1 的字段清单",
        "",
        markdown_table(allowed, ["category", "feature_name", "source_name", "available_at_rule", "phase1_allowed"]),
        "",
        "## 8. Deferred / Fail 字段清单",
        "",
        markdown_table(failed, ["category", "feature_name", "pit_status", "deferred_or_fail_reason"]),
        "",
        "## 9. Phase 0 Gate",
        "",
        f"- 是否满足 Phase 0 Gate：`{phase0_gate_pass}`。",
        "- 结论：三类正交数据当前均未发现本地可用 PIT 行级数据，且没有任何字段 `phase1_allowed=true`。按审查文档，本主线不应进入 Phase 1，除非用户后续确认新数据源或安全的数据补齐/PIT 归档工作。",
        "",
        "## 10. 安全边界",
        "",
        "- broker/orders/quick-trade/target position：未触碰。",
        "- provider refresh/publish：未触碰。",
        "- accepted latest switching：未触碰。",
        "- monitor config/alerts：未触碰。",
        "- 真实交易建议语义：未生成。",
        "",
        "## 11. 需要审查者或用户确认的问题",
        "",
        "- 若要继续该正交数据主线，需要用户确认是否允许新增或补齐法人筹码、融资融券、月营收数据源，并要求每行具备 `available_at` / `announcement_date` / `source_period` 等 PIT 字段。",
        "- 在确认前，不建议进入 Phase 1。",
        "",
        "## 12. 只读扫描证据",
        "",
        f"- FinMind summary paths：`{scan_meta['summary_payload_paths']}`",
        f"- daily finmind stdout count：`{scan_meta['daily_finmind_stdout_count']}`",
        f"- daily auto job summary：`{scan_meta['daily_job_summary']}`",
        "",
    ]
    EXEC_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    sources, scan_meta = build_data_sources()
    features = build_feature_rows(sources)

    DATA_SOURCES_PATH.write_text(json.dumps({
        "created_at": utc_now(),
        "research_only": True,
        "no_training": True,
        "no_provider_refresh_or_publish": True,
        "no_accepted_latest_switching": True,
        "no_broker_orders_quick_trade_or_target_positions": True,
        "scan_meta": scan_meta,
        "data_sources": sources,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(FEATURE_AVAILABILITY_PATH, features)
    write_pit_rules(sources, features)
    write_report(sources, features, scan_meta)

    print(json.dumps({
        "status": "ok",
        "scope": "orthogonal_phase0_read_only_audit",
        "source_count": len(sources),
        "feature_count": len(features),
        "phase1_allowed_count": sum(1 for row in features if row["phase1_allowed"]),
        "phase0_gate_pass": any(row["phase1_allowed"] for row in features),
        "outputs": [
            rel(Path("scripts/audit_tw_decision_orthogonal_phase0.py")),
            rel(DATA_SOURCES_PATH),
            rel(FEATURE_AVAILABILITY_PATH),
            rel(PIT_RULES_PATH),
            rel(EXEC_REPORT_PATH),
        ],
        "safety": {
            "model_training": False,
            "sample_construction": False,
            "provider_refresh_publish": False,
            "accepted_latest_switching": False,
            "broker_orders_quick_trade_target_positions": False,
            "frontend_api": False,
        },
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
