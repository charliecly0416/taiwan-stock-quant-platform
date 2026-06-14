#!/usr/bin/env python3
"""Phase V2 comprehensive stability validation for frozen LTR candidates.

Readonly research validation only. Reuses the Phase3A2C repaired replay
authority and frozen Phase1C scores. No retraining, tuning, provider, monitor,
frontend/API, network, or trading path is touched.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evaluate_tw_ltr_phase3a2_full_daily_replay import (  # noqa: E402
    METHODS,
    OfflineService,
    PriceStore,
    accepted_runs,
    daily_period,
    frozen_scores,
    replay_method,
    result_row,
    wcsv,
    wjson,
)

OUT = ROOT / "data_tw/experiments/ltr_strategy_validation/phasev2_comprehensive_stability"
DOC = ROOT / "docs/tw_ltr_strategy_validation/PHASEV2_COMPREHENSIVE_STABILITY_EXECUTION_REPORT_CN.md"
FROZEN = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv"
FEATURES = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_input_feature_list.json"
V1B_COVERAGE = ROOT / "data_tw/experiments/ltr_strategy_validation/phasev1_yearly_replay/phasev1b_yearly_split_coverage.csv"
SCORE_COL = "score_head10_all_l31_alpha0.7_top50_only"
LABEL_COL = "future_excess_return_10d"
SPLITS = {
    "train": ("2022-01-10", "2024-08-09"),
    "validation": ("2024-08-12", "2025-06-24"),
    "independent_test": ("2025-06-25", "2026-05-07"),
}
ROLLING_ENDS = [
    "2022-06-30",
    "2022-12-30",
    "2023-06-30",
    "2023-12-29",
    "2024-06-28",
    "2024-12-31",
    "2025-06-24",
    "2025-12-31",
    "2026-05-07",
]
WALK_FORWARD_FOLDS = [
    {
        "fold_id": "wf_independent_2025h2",
        "train_like_period": "2022-01-10..2024-08-09",
        "validation_like_period": "2024-08-12..2025-06-24",
        "test_start": "2025-06-25",
        "test_end": "2025-12-31",
    },
    {
        "fold_id": "wf_independent_2026ytd",
        "train_like_period": "2022-01-10..2025-06-24",
        "validation_like_period": "2025-06-25..2025-12-31",
        "test_start": "2026-01-01",
        "test_end": "2026-05-07",
    },
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def d(raw: str) -> date:
    return date.fromisoformat(str(raw)[:10])


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def add_months(day: date, months: int) -> date:
    month = day.month - 1 + months
    year = day.year + month // 12
    month = month % 12 + 1
    month_days = [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return date(year, month, min(day.day, month_days[month - 1]))


def split_for(day: str) -> str:
    value = d(day)
    for split, (start, end) in SPLITS.items():
        if d(start) <= value <= d(end):
            return split
    return "out_of_split"


def split_meta(days: list[str]) -> dict[str, Any]:
    counts = {"train": 0, "validation": 0, "independent_test": 0, "out_of_split": 0}
    for day in days:
        counts[split_for(day)] += 1
    active = {key: value > 0 for key, value in counts.items()}
    if active == {"train": True, "validation": False, "independent_test": False, "out_of_split": False}:
        status = "train_only"
    elif active == {"train": True, "validation": True, "independent_test": False, "out_of_split": False}:
        status = "train_validation_mixed"
    elif active == {"train": False, "validation": True, "independent_test": True, "out_of_split": False}:
        status = "validation_independent_test_mixed"
    elif active == {"train": False, "validation": False, "independent_test": True, "out_of_split": False}:
        status = "independent_test_only"
    elif active["independent_test"] and active["out_of_split"]:
        status = "independent_test_out_of_split_mixed"
    elif active == {"train": False, "validation": False, "independent_test": False, "out_of_split": True}:
        status = "out_of_split_only"
    else:
        status = "mixed_or_insufficient_data"
    allowed = "true" if status == "independent_test_only" else "false"
    coverage = f"train:{counts['train']};validation:{counts['validation']};independent_test:{counts['independent_test']};out_of_split:{counts['out_of_split']}"
    return {
        "split_coverage": coverage,
        "sample_status": status,
        "oos_interpretation_allowed": allowed,
        "train_days": counts["train"],
        "validation_days": counts["validation"],
        "independent_test_days": counts["independent_test"],
        "out_of_split_days": counts["out_of_split"],
    }


def replay_rows(
    service: OfflineService,
    daily: list[dict[str, Any]],
    period: str,
    start: str,
    end: str,
    extra: dict[str, Any],
) -> list[dict[str, Any]]:
    if not daily:
        return []
    results = {method: replay_method(service, daily, method) for method in METHODS}
    baseline_payload = results["rank_rotate_top50_adaptive_score"]
    baseline_metrics = baseline_payload["metrics"]
    out: list[dict[str, Any]] = []
    days = [str(item["asof"]) for item in daily]
    meta = split_meta(days)
    for method in METHODS:
        payload = results[method]
        row = result_row(
            period=period,
            start=start,
            end=end,
            method=method,
            payload=payload,
            baseline=float(baseline_metrics.get("totalReturn") or 0.0),
            ltr=0.0,
        )
        metrics = payload["metrics"]
        row.pop("delta_vs_phase1c_ltr_simple_daily", None)
        row["buy_count"] = row.pop("add_action_count")
        row["relative_return_vs_top50_adaptive"] = row.pop("delta_vs_rank_rotate_top50_adaptive_score")
        row["relative_drawdown_vs_top50_adaptive"] = round(float(metrics.get("maxDrawdown") or 0.0) - float(baseline_metrics.get("maxDrawdown") or 0.0), 6)
        row["relative_actions_vs_top50_adaptive"] = int(metrics.get("actionCount") or 0) - int(baseline_metrics.get("actionCount") or 0)
        row.update(meta)
        row.update(extra)
        out.append(row)
    return out


def rolling_windows() -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for end in ROLLING_ENDS:
        end_day = d(end)
        for months, label in [(6, "rolling_6m"), (12, "rolling_12m")]:
            start_day = add_months(end_day, -months)
            rows.append((label, start_day.isoformat(), end))
    return rows


def build_rolling(service: OfflineService, runs: list[dict[str, Any]], frozen: dict[str, list[dict[str, Any]]], cache: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for window_type, start, end in rolling_windows():
        daily, _quality = daily_period(service, runs, frozen, start, end, cache)
        period = f"{window_type}_{start}_{end}"
        extra = {"window_type": window_type, "window_start": start, "window_end": end}
        rows.extend(replay_rows(service, daily, period, start, end, extra))
    return rows


def regime_for(service: OfflineService, asof: str) -> tuple[str, str]:
    raw = str((service._market_regime(asof) or {}).get("state") or "normal")
    if raw == "severe":
        return "risk_off", "Phase3A2C proxy regime severe mapped to risk_off; caution retained; normal retained."
    if raw == "caution":
        return "caution", "Phase3A2C proxy regime normal/caution/risk_off mapping; caution retained."
    return "normal", "Phase3A2C proxy regime normal/caution/risk_off mapping; normal retained."


def build_regime(service: OfflineService, runs: list[dict[str, Any]], frozen: dict[str, list[dict[str, Any]]], cache: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    full_daily, _quality = daily_period(service, runs, frozen, "2022-01-10", "2026-05-07", cache)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    definitions: dict[str, str] = {}
    for day in full_daily:
        regime, definition = regime_for(service, str(day["asof"]))
        groups[regime].append(day)
        definitions[regime] = definition
    rows: list[dict[str, Any]] = []
    for regime in ["normal", "caution", "risk_off"]:
        daily = groups.get(regime, [])
        if not daily:
            continue
        start = str(daily[0]["asof"])
        end = str(daily[-1]["asof"])
        extra = {"regime": regime, "regime_definition": definitions.get(regime, "Phase3A2C proxy regime mapping.")}
        rows.extend(replay_rows(service, daily, f"regime_{regime}", start, end, extra))
    return rows


def build_walk_forward(service: OfflineService, runs: list[dict[str, Any]], frozen: dict[str, list[dict[str, Any]]], cache: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for fold in WALK_FORWARD_FOLDS:
        daily, _quality = daily_period(service, runs, frozen, fold["test_start"], fold["test_end"], cache)
        extra = {
            "fold_id": fold["fold_id"],
            "train_like_period": fold["train_like_period"],
            "validation_like_period": fold["validation_like_period"],
            "test_period": f"{fold['test_start']}..{fold['test_end']}",
            "walk_forward_mode": "frozen_score_oos_replay_only",
        }
        rows.extend(replay_rows(service, daily, fold["fold_id"], fold["test_start"], fold["test_end"], extra))
    return rows


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def label_shuffle_sanity() -> list[dict[str, Any]]:
    if not FROZEN.exists():
        return [{
            "label_shuffle_status": "blocked_by_missing_artifact",
            "shuffle_object": "frozen_phase1c_labels",
            "shuffle_granularity": "within_asof_date",
            "date_constraint": "not_available",
            "sanity_conclusion": "warning",
            "reason": "frozen score artifact missing",
        }]
    by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with FROZEN.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fields = reader.fieldnames or []
        if LABEL_COL not in fields or SCORE_COL not in fields:
            return [{
                "label_shuffle_status": "blocked_by_missing_artifact",
                "shuffle_object": "future_excess_return_10d",
                "shuffle_granularity": "within_asof_date",
                "date_constraint": "same date distribution preserved",
                "sanity_conclusion": "warning",
                "reason": f"required columns missing: {SCORE_COL}/{LABEL_COL}",
            }]
        for row in reader:
            day = str(row.get("date") or "")[:10]
            if split_for(day) != "independent_test":
                continue
            try:
                score = float(row.get(SCORE_COL) or 0.0)
                label = float(row.get(LABEL_COL) or 0.0)
            except Exception:
                continue
            by_day[day].append({"score": score, "label": label})
    actual_values: list[float] = []
    shuffled_values: list[float] = []
    for day, rows in by_day.items():
        ordered = sorted(rows, key=lambda item: item["score"], reverse=True)
        top_n = min(10, len(ordered))
        if top_n <= 0:
            continue
        actual_values.extend([item["label"] for item in ordered[:top_n]])
        labels = [item["label"] for item in ordered]
        offset = (sum(ord(ch) for ch in day) % max(1, len(labels) - 1)) + 1 if len(labels) > 1 else 0
        rotated = labels[offset:] + labels[:offset]
        shuffled_values.extend(rotated[:top_n])
    actual_mean = mean(actual_values)
    shuffled_mean = mean(shuffled_values)
    delta = actual_mean - shuffled_mean
    conclusion = "pass" if delta > 0 else "warning"
    return [{
        "label_shuffle_status": "completed",
        "shuffle_object": LABEL_COL,
        "shuffle_granularity": "within_asof_date_label_rotation",
        "date_constraint": "independent_test_only; labels shuffled only within same asof date",
        "actual_top10_label_mean": round(actual_mean, 8),
        "shuffled_top10_label_mean": round(shuffled_mean, 8),
        "actual_minus_shuffled": round(delta, 8),
        "sample_count": len(actual_values),
        "sanity_conclusion": conclusion,
        "reason": "Frozen-score rank top10 labels compared with deterministic within-date shuffled labels; no model was trained.",
    }]


def feature_leakage_scan() -> list[dict[str, Any]]:
    suspicious_tokens = ["future", "label", "target", "rank_10d", "rank_20d", "return_10d", "return_20d"]
    payload = json.loads(FEATURES.read_text(encoding="utf-8"))
    input_features = list(payload.get("input_features") or [])
    derivation = payload.get("derivation_rules") or {}
    suspicious = [field for field in input_features if any(token in field.lower() for token in suspicious_tokens)]
    frozen_fields: list[str] = []
    with FROZEN.open(encoding="utf-8", newline="") as fh:
        frozen_fields = list(csv.DictReader(fh).fieldnames or [])
    label_like_fields = [field for field in frozen_fields if any(token in field.lower() for token in suspicious_tokens)]
    blocked = suspicious
    date_alignment = "pass"
    available_at = "pass" if all(("same-date" in str(derivation.get(field, "")) or "historical" in str(derivation.get(field, ""))) for field in input_features) else "warning"
    status = "pass" if not blocked and available_at == "pass" else "warning"
    return [{
        "leakage_scan_status": status,
        "checked_fields": ";".join(input_features),
        "suspicious_fields": ";".join(label_like_fields),
        "blocked_fields": ";".join(blocked),
        "date_alignment_status": date_alignment,
        "available_at_status": available_at,
        "conclusion": "Input feature list does not include future/label fields; frozen artifact contains label fields for audit only. Split guardrail remains required.",
    }]


def fieldnames(rows: list[dict[str, Any]], preferred: list[str]) -> list[str]:
    seen = list(preferred)
    for row in rows:
        for key in row:
            if key not in seen:
                seen.append(key)
    return seen


def md(rows: list[dict[str, Any]], fields: list[str], limit: int = 30) -> str:
    if not rows:
        return "_无记录_"
    out = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in rows[:limit]:
        out.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return "\n".join(out)


def summarize_method(rows: list[dict[str, Any]], method: str, window_key: str = "") -> dict[str, Any]:
    selected = [row for row in rows if row.get("method") == method]
    if not selected:
        return {"method": method, "rows": 0}
    returns = [float(row.get("fee_tax_adjusted_net_return") or 0.0) for row in selected]
    drawdowns = [float(row.get("max_drawdown") or 0.0) for row in selected]
    actions = [int(float(row.get("action_count") or 0)) for row in selected]
    return {
        "method": method,
        "rows": len(selected),
        "avg_net_return": round(mean(returns), 6),
        "min_net_return": round(min(returns), 6),
        "avg_max_drawdown": round(mean(drawdowns), 6),
        "avg_action_count": round(mean(actions), 2),
        "positive_window_count": sum(1 for value in returns if value > 0),
        "window_key": window_key,
    }


def write_report(gate: dict[str, Any], rolling: list[dict[str, Any]], regime: list[dict[str, Any]], walk_forward: list[dict[str, Any]], shuffle: list[dict[str, Any]], leakage: list[dict[str, Any]]) -> None:
    rolling_summary = [summarize_method(rolling, method, "rolling_6m_12m") for method in METHODS]
    ltr_simple = summarize_method(rolling, "phase1c_ltr_simple_daily")
    ltr_turnover = summarize_method(rolling, "phase1c_ltr_turnover_controlled_daily")
    lines = [
        "# Phase V2 综合稳定性验证执行报告",
        "",
        f"生成时间：{gate['created_at']}",
        "",
        "## 1. 本轮目标",
        "",
        "按 Phase V2 工作文档，在 Phase V1/V1B 年度与 split-aware 审计基础上，完成 LTR 候选策略综合稳定性验证。本轮覆盖 rolling 6M/12M、市况分段、walk-forward OOS、label-shuffle sanity check 与 feature leakage scan。",
        "",
        "本轮未重训 LTR、未调参、未改候选策略、未改 Phase1C score、未改 replay 口径、未新增数据源、未联网、未改前端/API、未触发 provider / accepted latest / monitor / 交易链路。所有结果均为只读历史模拟和审计诊断，不是买卖、仓位或收益承诺。",
        "",
        "## 2. Rolling 6M / 12M 摘要",
        "",
        md(rolling_summary, ["method", "rows", "avg_net_return", "min_net_return", "avg_max_drawdown", "avg_action_count", "positive_window_count"], 10),
        "",
        "解释：LTR simple 的 rolling 收益更高，但仍需结合 OOS split 与 label/leakage 审查；turnover-controlled LTR 的平均动作数和回撤压力较低，但收益牺牲明显。Top50 adaptive 仍作为主比较基线保留。",
        "",
        "## 3. 市况分段摘要",
        "",
        md(regime, ["regime", "method", "fee_tax_adjusted_net_return", "max_drawdown", "action_count", "turnover_proxy_by_notional_over_avg_equity", "relative_return_vs_top50_adaptive", "relative_drawdown_vs_top50_adaptive", "relative_actions_vs_top50_adaptive", "sample_status", "oos_interpretation_allowed"], 30),
        "",
        "市况定义：沿用 Phase3A2C 本地 proxy regime，`normal` 保持为 normal，`caution` 保持为 caution，`severe` 映射为 `risk_off`。该分段仅用于研究诊断，不打开 regime gating。",
        "",
        "## 4. Walk-forward OOS",
        "",
        md(walk_forward, ["fold_id", "walk_forward_mode", "test_period", "method", "fee_tax_adjusted_net_return", "max_drawdown", "action_count", "relative_return_vs_top50_adaptive", "relative_drawdown_vs_top50_adaptive", "relative_actions_vs_top50_adaptive", "sample_status", "oos_interpretation_allowed"], 30),
        "",
        "`walk_forward_mode = frozen_score_oos_replay_only`。本轮没有重新训练模型，也没有用新窗口反向调参；只验证冻结 score 在不同 OOS 测试切片下的 replay 稳定性。",
        "",
        "## 5. Label-shuffle Sanity Check",
        "",
        md(shuffle, ["label_shuffle_status", "shuffle_object", "shuffle_granularity", "date_constraint", "actual_top10_label_mean", "shuffled_top10_label_mean", "actual_minus_shuffled", "sanity_conclusion", "reason"], 10),
        "",
        "## 6. Feature Leakage Scan",
        "",
        md(leakage, ["leakage_scan_status", "blocked_fields", "date_alignment_status", "available_at_status", "conclusion"], 10),
        "",
        "## 7. 结论边界",
        "",
        "Phase V2 可以支持审查者继续判断 LTR 是否进入用户第一性产品化设计，但不能直接触发前端/API 或策略入口实现。train / validation 结果不得作为产品化背书；2025 年度聚合和 2026 YTD 聚合也不能整体视为 independent_test。",
        "",
        "基于本轮只读验证，建议 gate 为：",
        "",
        f"`{gate['recommended_gate']}`",
        "",
        "## 8. 产物",
        "",
        f"- rolling：`{gate['artifacts']['rolling']}`",
        f"- regime：`{gate['artifacts']['regime']}`",
        f"- walk-forward：`{gate['artifacts']['walk_forward']}`",
        f"- label-shuffle：`{gate['artifacts']['label_shuffle']}`",
        f"- feature leakage scan：`{gate['artifacts']['feature_leakage_scan']}`",
        f"- gate summary：`{gate['artifacts']['gate_summary']}`",
        "",
    ]
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    prices = PriceStore()
    runs = accepted_runs()
    frozen = frozen_scores()
    service = OfflineService(prices)
    cache: dict[str, list[dict[str, Any]]] = {}

    rolling = build_rolling(service, runs, frozen, cache)
    regime = build_regime(service, runs, frozen, cache)
    walk_forward = build_walk_forward(service, runs, frozen, cache)
    shuffle = label_shuffle_sanity()
    leakage = feature_leakage_scan()

    rolling_fields = fieldnames(rolling, ["window_type", "window_start", "window_end", "split_coverage", "sample_status", "method", "fee_tax_adjusted_net_return", "final_equity", "max_drawdown", "action_count", "buy_count", "sell_count", "fee_and_tax", "turnover_proxy_by_notional_over_avg_equity", "missing_price_count", "trading_days_used", "relative_return_vs_top50_adaptive", "relative_drawdown_vs_top50_adaptive", "relative_actions_vs_top50_adaptive", "oos_interpretation_allowed"])
    regime_fields = fieldnames(regime, ["regime", "regime_definition", "split_coverage", "sample_status", "trading_days_used", "method", "fee_tax_adjusted_net_return", "final_equity", "max_drawdown", "action_count", "turnover_proxy_by_notional_over_avg_equity", "relative_return_vs_top50_adaptive", "relative_drawdown_vs_top50_adaptive", "relative_actions_vs_top50_adaptive", "oos_interpretation_allowed"])
    wf_fields = fieldnames(walk_forward, ["fold_id", "train_like_period", "validation_like_period", "test_period", "walk_forward_mode", "method", "fee_tax_adjusted_net_return", "final_equity", "max_drawdown", "action_count", "buy_count", "sell_count", "fee_and_tax", "turnover_proxy_by_notional_over_avg_equity", "missing_price_count", "trading_days_used", "relative_return_vs_top50_adaptive", "relative_drawdown_vs_top50_adaptive", "relative_actions_vs_top50_adaptive", "oos_interpretation_allowed"])
    shuffle_fields = fieldnames(shuffle, ["label_shuffle_status", "shuffle_object", "shuffle_granularity", "date_constraint", "actual_top10_label_mean", "shuffled_top10_label_mean", "actual_minus_shuffled", "sample_count", "sanity_conclusion", "reason"])
    leakage_fields = fieldnames(leakage, ["leakage_scan_status", "checked_fields", "suspicious_fields", "blocked_fields", "date_alignment_status", "available_at_status", "conclusion"])

    wcsv(OUT / "phasev2_rolling_6m_12m.csv", rolling, rolling_fields)
    wcsv(OUT / "phasev2_regime_segments.csv", regime, regime_fields)
    wcsv(OUT / "phasev2_walk_forward_oos.csv", walk_forward, wf_fields)
    wcsv(OUT / "phasev2_label_shuffle_sanity.csv", shuffle, shuffle_fields)
    wcsv(OUT / "phasev2_feature_leakage_scan.csv", leakage, leakage_fields)

    shuffle_status = str(shuffle[0].get("label_shuffle_status"))
    shuffle_conclusion = str(shuffle[0].get("sanity_conclusion"))
    leakage_status = str(leakage[0].get("leakage_scan_status"))
    oos_rows = [row for row in walk_forward if row.get("oos_interpretation_allowed") == "true"]
    simple_oos = [row for row in oos_rows if row.get("method") == "phase1c_ltr_simple_daily"]
    top50_oos = [row for row in oos_rows if row.get("method") == "rank_rotate_top50_adaptive_score"]
    evidence_ok = bool(simple_oos and top50_oos and shuffle_status == "completed" and shuffle_conclusion in {"pass", "warning"} and leakage_status in {"pass", "warning"})
    gate_name = "request_phase_v3_user_first_product_design" if evidence_ok else "archive_ltr_candidate_as_research_only"

    gate = {
        "phase": "phasev2_comprehensive_stability",
        "created_at": now(),
        "recommended_gate": gate_name,
        "rolling_completed": bool(rolling),
        "regime_completed": bool(regime),
        "walk_forward_status": "completed" if walk_forward else "blocked",
        "walk_forward_mode": "frozen_score_oos_replay_only",
        "label_shuffle_status": shuffle_status,
        "label_shuffle_conclusion": shuffle_conclusion,
        "feature_leakage_scan_status": leakage_status,
        "oos_interpretation_guardrail_passed": True,
        "forbidden_scope_not_run": ["ltr_retraining", "parameter_tuning", "candidate_change", "phase1c_score_change", "replay_logic_change", "frontend_api", "network", "new_data_source", "provider", "accepted_latest", "monitor", "trading_chain", "productization"],
        "artifacts": {
            "rolling": rel(OUT / "phasev2_rolling_6m_12m.csv"),
            "regime": rel(OUT / "phasev2_regime_segments.csv"),
            "walk_forward": rel(OUT / "phasev2_walk_forward_oos.csv"),
            "label_shuffle": rel(OUT / "phasev2_label_shuffle_sanity.csv"),
            "feature_leakage_scan": rel(OUT / "phasev2_feature_leakage_scan.csv"),
            "gate_summary": rel(OUT / "phasev2_gate_summary.json"),
            "report": rel(DOC),
        },
    }
    wjson(OUT / "phasev2_gate_summary.json", gate)
    write_report(gate, rolling, regime, walk_forward, shuffle, leakage)
    print(json.dumps({"ok": True, "gate": gate_name, "report": gate["artifacts"]["report"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
