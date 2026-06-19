#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


ROOT = Path(__file__).resolve().parents[1]
S1B4_DIR = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b4_ltr_training"
S1B1_DIR = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores"
TURNOVER_DIR = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase3a1_return_accounting_repair"
OUT_DIR = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b5_score_diagnostics"
DOC_DIR = ROOT / "docs/tw_ltr_qlib_split_aligned_retrain"

LTR_SCORES_CSV = S1B4_DIR / "phase_s1b4_ltr_scores.csv"
LTR_SCORE_SCHEMA_JSON = S1B4_DIR / "phase_s1b4_ltr_score_schema.json"
LTR_METRIC_BY_SPLIT_CSV = S1B4_DIR / "phase_s1b4_metric_by_split.csv"
QLIB_WF_CSV = S1B1_DIR / "phase_s1b1_qlib_wf_scores.csv"
TURNOVER_GATE_JSON = TURNOVER_DIR / "phase3a1_gate_summary.json"
TURNOVER_SELECTION_CSV = TURNOVER_DIR / "phase3a1_validation_selection.csv"

COVERAGE_CSV = OUT_DIR / "phase_s1b5_score_coverage_by_split.csv"
OVERLAP_CSV = OUT_DIR / "phase_s1b5_rank_overlap_summary.csv"
LABEL_DIAG_CSV = OUT_DIR / "phase_s1b5_label_diagnostic_by_split.csv"
REPLAY_POLICY_JSON = OUT_DIR / "phase_s1b5_replay_policy.json"
FORBIDDEN_AUDIT_JSON = OUT_DIR / "phase_s1b5_forbidden_action_audit.json"
GATE_SUMMARY_JSON = OUT_DIR / "phase_s1b5_gate_summary.json"
REPORT_DOC = DOC_DIR / "PHASES1B5_SCORE_DIAGNOSTICS_AND_REPLAY_POLICY_EXECUTION_REPORT_CN.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def mean_spearman(group: pd.DataFrame, x: str, y: str) -> float:
    if group[x].nunique() < 2 or group[y].nunique() < 2:
        return np.nan
    corr = spearmanr(group[x], group[y]).correlation
    return float(corr) if pd.notna(corr) else np.nan


def topk_overlap(group: pd.DataFrame, k: int) -> float:
    ltr = set(group.nsmallest(min(k, group.shape[0]), "ltr_rank")["instrument"])
    qlib = set(group.nsmallest(min(k, group.shape[0]), "qlib_rank")["instrument"])
    denom = float(min(k, max(len(ltr), len(qlib), 1)))
    return float(len(ltr & qlib) / denom) if denom > 0 else 0.0


def topk_jaccard(group: pd.DataFrame, k: int) -> float:
    ltr = set(group.nsmallest(min(k, group.shape[0]), "ltr_rank")["instrument"])
    qlib = set(group.nsmallest(min(k, group.shape[0]), "qlib_rank")["instrument"])
    union = ltr | qlib
    return float(len(ltr & qlib) / len(union)) if union else 0.0


def load_inputs() -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame, pd.DataFrame, dict[str, Any], pd.DataFrame]:
    scores = pd.read_csv(LTR_SCORES_CSV, parse_dates=["date"])
    schema = json.loads(LTR_SCORE_SCHEMA_JSON.read_text(encoding="utf-8"))
    metrics = pd.read_csv(LTR_METRIC_BY_SPLIT_CSV)
    qlib = pd.read_csv(QLIB_WF_CSV, parse_dates=["date"])
    turnover_gate = json.loads(TURNOVER_GATE_JSON.read_text(encoding="utf-8"))
    turnover_selection = pd.read_csv(TURNOVER_SELECTION_CSV)
    return scores, schema, metrics, qlib, turnover_gate, turnover_selection


def build_coverage(scores: pd.DataFrame, qlib: pd.DataFrame) -> pd.DataFrame:
    qlib_keyed = qlib[["date", "instrument", "fold_id"]].copy()
    qlib_keyed["qlib_present"] = 1
    merged = scores.merge(qlib_keyed, on=["date", "instrument", "fold_id"], how="left")
    rows: list[dict[str, Any]] = []
    for split, group in merged.groupby("split"):
        daily_counts = group.groupby("date").size()
        rows.append(
            {
                "split": split,
                "row_count": int(group.shape[0]),
                "date_count": int(group["date"].nunique()),
                "instrument_count": int(group["instrument"].nunique()),
                "qlib_key_match_count": int(group["qlib_present"].fillna(0).sum()),
                "qlib_key_missing_count": int(group["qlib_present"].isna().sum()),
                "ltr_score_missing_count": int(group["ltr_score"].isna().sum()),
                "ltr_rank_missing_count": int(group["ltr_rank"].isna().sum()),
                "qlib_score_missing_count": int(group["qlib_score_raw"].isna().sum()),
                "qlib_rank_missing_count": int(group["qlib_rank"].isna().sum()),
                "duplicate_date_instrument_count": int(group.duplicated(["date", "instrument"]).sum()),
                "daily_count_min": int(daily_counts.min()),
                "daily_count_p50": float(daily_counts.median()),
                "daily_count_max": int(daily_counts.max()),
                "daily_selected_ge_50_days": int((daily_counts >= 50).sum()),
                "daily_selected_lt_50_days": int((daily_counts < 50).sum()),
                "ltr_score_mean": float(group["ltr_score"].mean()),
                "ltr_score_std": float(group["ltr_score"].std(ddof=0)),
                "ltr_rank_min": int(group["ltr_rank"].min()),
                "ltr_rank_max": int(group["ltr_rank"].max()),
            }
        )
    return pd.DataFrame(rows).sort_values("split")


def build_overlap(scores: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split, split_df in scores.groupby("split"):
        per_day = []
        for date, group in split_df.groupby("date"):
            per_day.append(
                {
                    "date": date,
                    "spearman_rank_corr": mean_spearman(group, "ltr_rank", "qlib_rank"),
                    "top10_overlap_ratio": topk_overlap(group, 10),
                    "top30_overlap_ratio": topk_overlap(group, 30),
                    "top50_overlap_ratio": topk_overlap(group, 50),
                    "top10_jaccard": topk_jaccard(group, 10),
                    "top30_jaccard": topk_jaccard(group, 30),
                    "top50_jaccard": topk_jaccard(group, 50),
                }
            )
        daily = pd.DataFrame(per_day)
        rows.append(
            {
                "split": split,
                "date_count": int(daily.shape[0]),
                "spearman_rank_corr_mean": float(daily["spearman_rank_corr"].mean()),
                "spearman_rank_corr_median": float(daily["spearman_rank_corr"].median()),
                "top10_overlap_ratio_mean": float(daily["top10_overlap_ratio"].mean()),
                "top30_overlap_ratio_mean": float(daily["top30_overlap_ratio"].mean()),
                "top50_overlap_ratio_mean": float(daily["top50_overlap_ratio"].mean()),
                "top10_jaccard_mean": float(daily["top10_jaccard"].mean()),
                "top30_jaccard_mean": float(daily["top30_jaccard"].mean()),
                "top50_jaccard_mean": float(daily["top50_jaccard"].mean()),
            }
        )
    return pd.DataFrame(rows).sort_values("split")


def topk_audit_metric(split_df: pd.DataFrame, k: int, score_col: str, metric_col: str) -> float:
    selected = []
    for _, group in split_df.groupby("date"):
        selected.append(group.nsmallest(min(k, group.shape[0]), score_col))
    top = pd.concat(selected, ignore_index=True) if selected else pd.DataFrame()
    return float(top[metric_col].mean()) if not top.empty else np.nan


def build_label_diagnostics(scores: pd.DataFrame, metrics: pd.DataFrame) -> pd.DataFrame:
    metric_map = metrics.set_index("split").to_dict(orient="index")
    rows: list[dict[str, Any]] = []
    for split, group in scores.groupby("split"):
        rows.append(
            {
                "split": split,
                "label_mean": float(group["ltr_relevance_label"].mean()),
                "label_std": float(group["ltr_relevance_label"].std(ddof=0)),
                "future_excess_rank_mean": float(group["future_excess_return_rank_10d"].mean()),
                "ltr_top10_label_mean": topk_audit_metric(group, 10, "ltr_rank", "ltr_relevance_label"),
                "ltr_top30_label_mean": topk_audit_metric(group, 30, "ltr_rank", "ltr_relevance_label"),
                "ltr_top50_label_mean": topk_audit_metric(group, 50, "ltr_rank", "ltr_relevance_label"),
                "qlib_top10_label_mean": topk_audit_metric(group, 10, "qlib_rank", "ltr_relevance_label"),
                "qlib_top30_label_mean": topk_audit_metric(group, 30, "qlib_rank", "ltr_relevance_label"),
                "qlib_top50_label_mean": topk_audit_metric(group, 50, "qlib_rank", "ltr_relevance_label"),
                "ltr_top10_future_excess_rank_mean": topk_audit_metric(group, 10, "ltr_rank", "future_excess_return_rank_10d"),
                "ltr_top30_future_excess_rank_mean": topk_audit_metric(group, 30, "ltr_rank", "future_excess_return_rank_10d"),
                "ltr_top50_future_excess_rank_mean": topk_audit_metric(group, 50, "ltr_rank", "future_excess_return_rank_10d"),
                "qlib_top10_future_excess_rank_mean": topk_audit_metric(group, 10, "qlib_rank", "future_excess_return_rank_10d"),
                "qlib_top30_future_excess_rank_mean": topk_audit_metric(group, 30, "qlib_rank", "future_excess_return_rank_10d"),
                "qlib_top50_future_excess_rank_mean": topk_audit_metric(group, 50, "qlib_rank", "future_excess_return_rank_10d"),
                "s1b4_rank_ic_audit_future_excess_rank_10d": float(metric_map[split]["rank_ic_audit_future_excess_rank_10d"]),
                "s1b4_ndcg_at_30": float(metric_map[split]["ndcg_at_30"]),
                "audit_only_not_return_conclusion": True,
            }
        )
    return pd.DataFrame(rows).sort_values("split")


def choose_turnover_policy(turnover_gate: dict[str, Any], turnover_selection: pd.DataFrame) -> dict[str, Any]:
    selected_id = turnover_gate["selected_validation_config"]
    row = turnover_selection[turnover_selection["config_id"] == selected_id]
    if row.empty:
        return {
            "policy_ready": False,
            "status": "turnover_control_policy_not_ready",
            "reason": "selected validation config not found in existing frozen Phase3A1 artifact",
        }
    rec = row.iloc[0].to_dict()
    return {
        "policy_ready": True,
        "status": "existing_frozen_usage_layer_candidate_reused",
        "source_artifact": rel(TURNOVER_SELECTION_CSV),
        "source_gate": rel(TURNOVER_GATE_JSON),
        "source_selection_rule_note": "reused from prior mainline frozen validation-only turnover usage-layer candidate; not selected from S1B4 validation/test diagnostics",
        "candidate_method_name": "split_aligned_ltr_turnover_controlled",
        "base_common_score_source": rel(LTR_SCORES_CSV),
        "return_accounting_contract_for_s1b6": "complete_daily_replay_required_in_s1_split_aligned_mainline",
        "frozen_usage_layer_config": {
            "config_id": rec["config_id"],
            "target_k": int(rec["target_k"]),
            "partial_rebalance": bool(rec["partial_rebalance"]),
            "max_actions_per_window": int(rec["max_actions_per_window"]),
            "min_holding_windows": int(rec["min_holding_windows"]),
            "min_holding_days_equivalent": int(rec["min_holding_days_equivalent"]),
            "confidence_gap": float(rec["confidence_gap"]),
            "score_or_confidence_clipping": float(rec["score_or_confidence_clipping"]),
            "turnover_budget": float(rec["turnover_budget"]),
            "no_trade_buffer": float(rec["no_trade_buffer"]),
        },
        "freeze_constraints": {
            "must_not_change_common_ltr_model": True,
            "must_not_change_label": True,
            "must_not_reselect_threshold_from_s1b4_validation_or_test": True,
            "must_not_choose_by_s1b5_return_drawdown_turnover_actions": True,
        },
    }


def build_replay_policy(scores: pd.DataFrame, turnover_gate: dict[str, Any], turnover_selection: pd.DataFrame) -> dict[str, Any]:
    turnover_policy = choose_turnover_policy(turnover_gate, turnover_selection)
    baseline_readiness = {
        "qlib_top50_adaptive_baseline": {
            "strategy_name": "qlib / Top50 adaptive baseline",
            "status": "blocked_in_current_s1b5_input_contract",
            "reason": "S1B4 score artifact does not include adaptive baseline reconstruction columns such as qlib_score_zscore_by_date, ret20, volatility20, TWII_ret20.",
        },
        "rank_rotate_top50": {
            "strategy_name": "rank_rotate_top50",
            "status": "ready",
            "reason": "directly available from qlib_score_raw / qlib_rank ordering in current score artifact",
        },
        "rank_rotate_top30": {
            "strategy_name": "rank_rotate_top30",
            "status": "ready",
            "reason": "directly available from qlib_score_raw / qlib_rank ordering in current score artifact",
        },
        "confirmed_exit": {
            "strategy_name": "confirmed_exit",
            "status": "blocked_in_current_s1b5_input_contract",
            "reason": "S1B4 score artifact does not include confirmed-exit reconstruction columns such as market_drawdown60 and volatility20-derived baseline fields.",
        },
        "split_aligned_ltr_simple": {
            "strategy_name": "split_aligned_ltr_simple",
            "status": "ready",
            "reason": "direct common LTR score usage candidate from S1B4 score artifact",
        },
        "split_aligned_ltr_turnover_controlled": {
            "strategy_name": "split_aligned_ltr_turnover_controlled",
            "status": "ready" if turnover_policy["policy_ready"] else "blocked",
            "reason": turnover_policy["status"] if turnover_policy["policy_ready"] else turnover_policy["reason"],
        },
    }
    return {
        "created_at": utc_now(),
        "phase": "phase_s1b5_score_diagnostics",
        "source_scores": rel(LTR_SCORES_CSV),
        "source_qlib_scores": rel(QLIB_WF_CSV),
        "source_score_schema": rel(LTR_SCORE_SCHEMA_JSON),
        "replay_execution_in_s1b5": False,
        "purpose": "freeze_s1b6_full_daily_replay_policy_only",
        "strategies_required_for_s1b6": [
            "qlib_top50_adaptive_baseline",
            "rank_rotate_top50",
            "rank_rotate_top30",
            "confirmed_exit",
            "split_aligned_ltr_simple",
            "split_aligned_ltr_turnover_controlled",
        ],
        "baseline_readiness": baseline_readiness,
        "interval_contract": {
            "full_test": "2023-01-01..2025-06-30",
            "yearly": ["2023", "2024", "2025H1"],
            "rolling": ["6m", "12m"],
            "regime": "reuse existing regime_segment from S1B4 audit-only field for readonly segmentation",
        },
        "metrics_contract": [
            "fee_tax_adjusted_net_return",
            "max_drawdown",
            "action_count",
            "buy_count",
            "sell_count",
            "fee_and_tax",
            "turnover_proxy_by_notional_over_avg_equity",
            "relative_return_vs_top50_adaptive",
            "relative_drawdown_vs_top50_adaptive",
            "relative_actions_vs_top50_adaptive",
        ],
        "calendar_tradability_policy": {
            "calendar_source": "dates present in S1B4 common score artifact intersected with full test period",
            "tradability_source": "existing normalized TW price availability already embedded in S1B2 sample_complete and S1B4 scoring rows",
            "no_provider_refresh_publish": True,
            "no_accepted_latest_switching": True,
        },
        "simple_turnover_controlled_policy": {
            "same_common_score": True,
            "same_candidate_level_in_s1b5": True,
            "turnover_controlled_usage_layer_policy": turnover_policy,
        },
        "validation_weak_signal_caveat": {
            "validation_rank_ic_audit": -0.015908,
            "validation_ndcg_at_30": 0.511378,
            "instruction": "must carry this caveat into S1B6 report and must not tune parameters, features, labels, splits, or turnover thresholds from this signal",
        },
    }


def write_forbidden_audit() -> None:
    payload = {
        "created_at": utc_now(),
        "phase": "phase_s1b5_score_diagnostics",
        "forbidden_actions_checked": {
            "ltr_training_executed": False,
            "qlib_training_executed": False,
            "replay_executed": False,
            "strategy_return_comparison_executed": False,
            "parameter_tuning_executed": False,
            "feature_modified": False,
            "label_modified": False,
            "split_modified": False,
            "universe_modified": False,
            "new_data_source_added": False,
            "network_used": False,
            "frontend_or_api_changed": False,
            "provider_refresh_or_publish_triggered": False,
            "accepted_latest_switched": False,
            "monitor_or_trading_chain_triggered": False,
        },
        "semantic_boundary": {
            "buy_sell_instruction": False,
            "hold_instruction": False,
            "target_position": False,
            "target_weight": False,
            "return_promise": False,
            "win_rate_promise": False,
            "probability_semantics": False,
        },
    }
    FORBIDDEN_AUDIT_JSON.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def write_gate(replay_policy: dict[str, Any], coverage: pd.DataFrame, overlap: pd.DataFrame) -> dict[str, Any]:
    blocked = [
        name for name, info in replay_policy["baseline_readiness"].items()
        if info["status"].startswith("blocked")
    ]
    gate = "s1b5_score_diagnostics_and_replay_policy_pass_request_s1b6_full_daily_replay"
    reason = "Score diagnostics complete and S1B6 replay policy frozen with explicit weak-signal caveat and baseline readiness notes."
    if coverage["duplicate_date_instrument_count"].sum() != 0:
        gate = "s1b5_blocked_by_scope_violation"
        reason = "duplicate date/instrument detected in S1B4 score artifact"
    elif overlap.empty:
        gate = "s1b5_blocked_by_missing_baseline_or_replay_policy"
        reason = "rank overlap diagnostics missing"
    payload = {
        "created_at": utc_now(),
        "phase": "phase_s1b5_score_diagnostics",
        "recommended_gate": gate,
        "gate_reason": reason,
        "blocked_baselines_for_s1b6_followup": blocked,
        "checks": {
            "score_diagnostics_complete": True,
            "replay_policy_frozen": True,
            "validation_weak_signal_caveat_explicit": True,
            "no_parameter_tuning": True,
            "no_feature_label_split_universe_modification": True,
            "no_replay_in_s1b5": True,
            "no_strategy_return_comparison_in_s1b5": True,
            "no_frontend_or_api": True,
            "no_provider_refresh_publish": True,
            "no_accepted_latest_switching": True,
            "no_monitor_or_trading_chain": True,
            "no_real_trading_semantics": True,
        },
        "artifacts": {
            "score_coverage_by_split": rel(COVERAGE_CSV),
            "rank_overlap_summary": rel(OVERLAP_CSV),
            "label_diagnostic_by_split": rel(LABEL_DIAG_CSV),
            "replay_policy": rel(REPLAY_POLICY_JSON),
            "forbidden_action_audit": rel(FORBIDDEN_AUDIT_JSON),
            "report": rel(REPORT_DOC),
        },
    }
    GATE_SUMMARY_JSON.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return payload


def write_report(coverage: pd.DataFrame, overlap: pd.DataFrame, label_diag: pd.DataFrame, replay_policy: dict[str, Any], gate: dict[str, Any]) -> None:
    cov_rows = [
        f"| {r.split} | {int(r.row_count)} | {int(r.date_count)} | {int(r.daily_count_min)} | {int(r.daily_count_max)} | {int(r.ltr_score_missing_count)} | {int(r.ltr_rank_missing_count)} | {int(r.duplicate_date_instrument_count)} |"
        for r in coverage.itertuples(index=False)
    ]
    overlap_rows = [
        f"| {r.split} | {r.spearman_rank_corr_mean:.6f} | {r.top10_overlap_ratio_mean:.6f} | {r.top30_overlap_ratio_mean:.6f} | {r.top50_overlap_ratio_mean:.6f} |"
        for r in overlap.itertuples(index=False)
    ]
    label_rows = [
        f"| {r.split} | {r.ltr_top10_label_mean:.6f} | {r.ltr_top30_label_mean:.6f} | {r.ltr_top50_label_mean:.6f} | {r.qlib_top10_label_mean:.6f} | {r.qlib_top30_label_mean:.6f} | {r.qlib_top50_label_mean:.6f} | {r.s1b4_rank_ic_audit_future_excess_rank_10d:.6f} |"
        for r in label_diag.itertuples(index=False)
    ]
    readiness_rows = []
    for name, info in replay_policy["baseline_readiness"].items():
        readiness_rows.append(f"| {name} | {info['status']} | {info['reason']} |")
    turnover_policy = replay_policy["simple_turnover_controlled_policy"]["turnover_controlled_usage_layer_policy"]
    report = "\n".join(
        [
            "# Phase S1B5 执行报告：Score Diagnostics 与 Replay Policy Freeze",
            "",
            f"生成日期：{utc_now()}",
            "",
            "## 1. 本轮目标",
            "",
            "按 `PHASES1B4_REVIEW_AND_PHASES1B5_SCORE_DIAGNOSTICS_WORK_CN.md` 要求，只做 S1B4 common LTR score/rank 的只读质量诊断，并冻结 S1B6 完整日频回放政策。",
            "",
            "## 2. 输入",
            "",
            f"- `{rel(LTR_SCORES_CSV)}`",
            f"- `{rel(LTR_SCORE_SCHEMA_JSON)}`",
            f"- `{rel(LTR_METRIC_BY_SPLIT_CSV)}`",
            f"- `{rel(QLIB_WF_CSV)}`",
            "",
            "## 3. Score Coverage By Split",
            "",
            "| split | row_count | date_count | daily_count_min | daily_count_max | ltr_score_missing | ltr_rank_missing | duplicate_date_instrument |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            *cov_rows,
            "",
            "## 4. Rank Overlap 与相关性",
            "",
            "| split | mean_spearman_rank_corr | top10_overlap | top30_overlap | top50_overlap |",
            "| --- | ---: | ---: | ---: | ---: |",
            *overlap_rows,
            "",
            "## 5. Audit-Only Label Diagnostics",
            "",
            "以下指标只用于 score 质量审计，不代表组合收益、回撤、换手或动作次数结论。",
            "",
            "| split | ltr_top10_label_mean | ltr_top30_label_mean | ltr_top50_label_mean | qlib_top10_label_mean | qlib_top30_label_mean | qlib_top50_label_mean | s1b4_rank_ic_audit |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            *label_rows,
            "",
            "## 6. Validation Weak-Signal Caveat",
            "",
            "- `validation rank_ic_audit = -0.015908`。",
            "- `validation ndcg@30 = 0.511378`。",
            "- 该信号只能如实带入后续 S1B6 报告，不能反向触发调参、改 feature、改 label、改 split、改 universe 或改 turnover 阈值。",
            "",
            "## 7. S1B6 Replay Policy Freeze",
            "",
            "| strategy | readiness | note |",
            "| --- | --- | --- |",
            *readiness_rows,
            "",
            "- full test：`2023-01-01..2025-06-30`",
            "- yearly：`2023`、`2024`、`2025H1`",
            "- rolling：`6m / 12m`",
            "- regime：复用 `regime_segment` 做只读分段",
            "- metrics：`fee_tax_adjusted_net_return`、`max_drawdown`、`action_count`、`buy_count`、`sell_count`、`fee_and_tax`、`turnover_proxy_by_notional_over_avg_equity`、`relative_return_vs_top50_adaptive`、`relative_drawdown_vs_top50_adaptive`、`relative_actions_vs_top50_adaptive`",
            "",
            "## 8. Turnover-Controlled 使用层政策",
            "",
            f"- status：`{turnover_policy['status']}`",
            f"- source gate：`{turnover_policy.get('source_gate', 'n/a')}`",
            f"- source artifact：`{turnover_policy.get('source_artifact', 'n/a')}`",
            f"- reused config：`{turnover_policy.get('frozen_usage_layer_config', {}).get('config_id', 'n/a')}`",
            "- 该政策来自既有冻结主线，不是根据 S1B4 validation/test 诊断临时选出的。",
            "",
            "## 9. 禁止事项执行结果",
            "",
            "- 未训练 LTR。",
            "- 未训练 qlib。",
            "- 未跑组合回放。",
            "- 未比较策略收益。",
            "- 未调参，未改 feature / label / split / universe。",
            "- 未新增数据源，未联网。",
            "- 未改前端/API，未触发 provider / accepted latest / monitor / trading chain。",
            "- 未输出买卖、持有、仓位、收益承诺、胜率或上涨概率语义。",
            "",
            "## 10. 结论",
            "",
            "本轮完成 S1B5 score diagnostics 与 S1B6 replay policy freeze。",
            "",
            "推荐 gate：",
            "",
            "```text",
            gate["recommended_gate"],
            "```",
        ]
    )
    REPORT_DOC.write_text(report + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    scores, schema, metrics, qlib, turnover_gate, turnover_selection = load_inputs()
    coverage = build_coverage(scores, qlib)
    overlap = build_overlap(scores)
    label_diag = build_label_diagnostics(scores, metrics)
    replay_policy = build_replay_policy(scores, turnover_gate, turnover_selection)
    coverage.to_csv(COVERAGE_CSV, index=False)
    overlap.to_csv(OVERLAP_CSV, index=False)
    label_diag.to_csv(LABEL_DIAG_CSV, index=False)
    REPLAY_POLICY_JSON.write_text(json.dumps(replay_policy, ensure_ascii=True, indent=2), encoding="utf-8")
    write_forbidden_audit()
    gate = write_gate(replay_policy, coverage, overlap)
    write_report(coverage, overlap, label_diag, replay_policy, gate)


if __name__ == "__main__":
    main()
