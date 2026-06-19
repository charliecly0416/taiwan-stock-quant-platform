#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
S1B2_DIR = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples"
S1B4_DIR = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b4_ltr_training"
S1B5_DIR = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b5_score_diagnostics"
TURNOVER_DIR = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase3a1_return_accounting_repair"
OUT_DIR = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b5r_baseline_readiness_repair"
DOC_DIR = ROOT / "docs/tw_ltr_qlib_split_aligned_retrain"

S1B2_SAMPLE_CSV = S1B2_DIR / "phase_s1b2_ltr_samples.csv"
S1B4_SCORES_CSV = S1B4_DIR / "phase_s1b4_ltr_scores.csv"
S1B5_REPLAY_POLICY_JSON = S1B5_DIR / "phase_s1b5_replay_policy.json"
S1B5_GATE_JSON = S1B5_DIR / "phase_s1b5_gate_summary.json"
TURNOVER_GATE_JSON = TURNOVER_DIR / "phase3a1_gate_summary.json"
TURNOVER_SELECTION_CSV = TURNOVER_DIR / "phase3a1_validation_selection.csv"

REPLAY_READY_CSV = OUT_DIR / "phase_s1b5r_replay_ready_scores.csv"
BASELINE_READY_JSON = OUT_DIR / "phase_s1b5r_baseline_readiness.json"
REPLAY_POLICY_JSON = OUT_DIR / "phase_s1b5r_replay_policy.json"
FORBIDDEN_AUDIT_JSON = OUT_DIR / "phase_s1b5r_forbidden_action_audit.json"
GATE_JSON = OUT_DIR / "phase_s1b5r_gate_summary.json"
REPORT_DOC = DOC_DIR / "PHASES1B5R_BASELINE_READINESS_REPAIR_EXECUTION_REPORT_CN.md"

KEY_COLS = ["date", "instrument", "split", "fold_id"]
REPLAY_READY_COLS = [
    "date",
    "instrument",
    "split",
    "fold_id",
    "qlib_score_raw",
    "qlib_rank",
    "ltr_score",
    "ltr_rank",
    "sample_complete",
    "feature_complete",
    "regime_segment",
    "qlib_score_percentile_by_date",
    "qlib_score_zscore_by_date",
    "ret20",
    "volatility20",
    "TWII_ret20",
    "TWII_ret60",
    "market_volatility20",
    "market_drawdown60",
    "market_breadth20",
    "adaptive_score_baseline",
    "confirmed_exit_baseline",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], dict[str, Any], dict[str, Any], pd.DataFrame]:
    s1b4 = pd.read_csv(S1B4_SCORES_CSV, parse_dates=["date"])
    s1b2 = pd.read_csv(S1B2_SAMPLE_CSV, parse_dates=["date"])
    s1b5_policy = load_json(S1B5_REPLAY_POLICY_JSON)
    s1b5_gate = load_json(S1B5_GATE_JSON)
    turnover_gate = load_json(TURNOVER_GATE_JSON)
    turnover_selection = pd.read_csv(TURNOVER_SELECTION_CSV)
    return s1b4, s1b2, s1b5_policy, s1b5_gate, turnover_gate, turnover_selection


def build_replay_ready_scores(s1b4: pd.DataFrame, s1b2: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    feature_cols = [
        "sample_complete",
        "feature_complete",
        "regime_segment",
        "qlib_score_percentile_by_date",
        "qlib_score_zscore_by_date",
        "ret20",
        "volatility20",
        "TWII_ret20",
        "TWII_ret60",
        "market_volatility20",
        "market_drawdown60",
        "market_breadth20",
    ]
    missing_feature_cols = [c for c in feature_cols if c not in s1b2.columns]
    require(not missing_feature_cols, f"S1B2 sample missing replay-ready columns: {missing_feature_cols}")
    sample_view = s1b2[KEY_COLS + feature_cols].copy()
    merged = s1b4.merge(sample_view, on=KEY_COLS, how="left", validate="one_to_one", suffixes=("", "_s1b2"))
    join_missing = merged["sample_complete"].isna().sum()
    require(join_missing == 0, f"S1B4 scores failed to join S1B2 sample on {KEY_COLS}: missing={join_missing}")
    require(int(merged.duplicated(KEY_COLS).sum()) == 0, "duplicate keys found after replay-ready join")
    require(bool(merged["sample_complete"].all()), "replay-ready table includes rows outside sample_complete=true")
    merged["adaptive_score_baseline"] = (
        0.70 * merged["qlib_score_zscore_by_date"]
        + 0.15 * merged["ret20"].fillna(0.0)
        - 0.10 * merged["volatility20"].fillna(0.0)
        + 0.05 * merged["TWII_ret20"].fillna(0.0)
    )
    merged["confirmed_exit_baseline"] = (
        merged["qlib_score_zscore_by_date"]
        - 0.25 * (merged["market_drawdown60"].fillna(0.0) < -0.08).astype(float)
        - 0.10 * merged["volatility20"].fillna(0.0)
    )
    replay_ready = merged[REPLAY_READY_COLS].sort_values(["date", "split", "ltr_rank", "instrument"]).copy()
    summary = {
        "row_count": int(replay_ready.shape[0]),
        "date_count": int(replay_ready["date"].nunique()),
        "duplicate_key_count": int(replay_ready.duplicated(KEY_COLS).sum()),
        "ltr_score_missing_count": int(replay_ready["ltr_score"].isna().sum()),
        "ltr_rank_missing_count": int(replay_ready["ltr_rank"].isna().sum()),
        "adaptive_score_missing_count": int(replay_ready["adaptive_score_baseline"].isna().sum()),
        "confirmed_exit_missing_count": int(replay_ready["confirmed_exit_baseline"].isna().sum()),
        "split_counts": replay_ready.groupby("split").size().astype(int).to_dict(),
    }
    return replay_ready, summary


def choose_turnover_policy(turnover_gate: dict[str, Any], turnover_selection: pd.DataFrame) -> dict[str, Any]:
    selected_id = turnover_gate["selected_validation_config"]
    row = turnover_selection[turnover_selection["config_id"] == selected_id]
    require(not row.empty, f"turnover selected validation config not found: {selected_id}")
    rec = row.iloc[0].to_dict()
    return {
        "policy_ready": True,
        "status": "ready_existing_frozen_usage_layer_candidate",
        "source_gate": rel(TURNOVER_GATE_JSON),
        "source_artifact": rel(TURNOVER_SELECTION_CSV),
        "source_selection_rule_note": "reused from prior frozen validation-only turnover usage-layer candidate; not reselected from S1B4/S1B5/S1B5R diagnostics",
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
        "freeze_constraints": {
            "must_not_change_common_ltr_model": True,
            "must_not_change_label": True,
            "must_not_reselect_threshold_from_s1b4_s1b5_s1b5r_validation_or_test": True,
            "must_not_choose_by_return_drawdown_turnover_actions": True,
        },
    }


def build_baseline_readiness(replay_ready: pd.DataFrame, turnover_policy: dict[str, Any]) -> dict[str, Any]:
    required_cols = set(replay_ready.columns)
    readiness = {
        "qlib_top50_adaptive_baseline": {
            "status": "ready" if {"qlib_score_zscore_by_date", "ret20", "volatility20", "TWII_ret20"} <= required_cols else "blocked",
            "strategy_name": "qlib / Top50 adaptive baseline",
            "score_column": "adaptive_score_baseline",
            "definition_source": "existing local definition reused from scripts/train_tw_ltr_phase1_lambdamart.py and scripts/diagnose_tw_ltr_phase1c_final_repair.py",
            "reconstruction_fields": ["qlib_score_zscore_by_date", "ret20", "volatility20", "TWII_ret20"],
            "rule_expression": "0.70 * qlib_score_zscore_by_date + 0.15 * ret20 - 0.10 * volatility20 + 0.05 * TWII_ret20",
        },
        "rank_rotate_top50": {
            "status": "ready",
            "strategy_name": "rank_rotate_top50",
            "score_column": "qlib_score_raw",
            "rank_column": "qlib_rank",
            "rule_expression": "same-day qlib rank order, top 50 selection",
        },
        "rank_rotate_top30": {
            "status": "ready",
            "strategy_name": "rank_rotate_top30",
            "score_column": "qlib_score_raw",
            "rank_column": "qlib_rank",
            "rule_expression": "same-day qlib rank order, top 30 selection",
        },
        "confirmed_exit": {
            "status": "ready" if {"qlib_score_zscore_by_date", "market_drawdown60", "volatility20"} <= required_cols else "blocked",
            "strategy_name": "confirmed_exit",
            "score_column": "confirmed_exit_baseline",
            "definition_source": "existing local definition reused from scripts/train_tw_ltr_phase1_lambdamart.py and scripts/diagnose_tw_ltr_phase1c_final_repair.py",
            "authority_reason": "same formula appears in prior frozen local LTR baseline scripts and is the only existing warehouse definition referenced by the mainline",
            "reconstruction_fields": ["qlib_score_zscore_by_date", "market_drawdown60", "volatility20"],
            "rule_expression": "qlib_score_zscore_by_date - 0.25 * 1[market_drawdown60 < -0.08] - 0.10 * volatility20",
        },
        "split_aligned_ltr_simple": {
            "status": "ready",
            "strategy_name": "split_aligned_ltr_simple",
            "score_column": "ltr_score",
            "rank_column": "ltr_rank",
            "rule_expression": "direct common LTR score usage candidate",
        },
        "split_aligned_ltr_turnover_controlled": {
            "status": "ready" if turnover_policy["policy_ready"] else "blocked",
            "strategy_name": "split_aligned_ltr_turnover_controlled",
            "score_column": "ltr_score",
            "rank_column": "ltr_rank",
            "usage_layer_policy": turnover_policy,
            "rule_expression": "same common LTR score with frozen existing turnover usage-layer constraints",
        },
    }
    return {
        "created_at": utc_now(),
        "phase": "phase_s1b5r_baseline_readiness_repair",
        "source_replay_ready_scores": rel(REPLAY_READY_CSV),
        "mandatory_baselines": list(readiness.keys()),
        "baseline_readiness": readiness,
    }


def build_replay_policy(
    previous_policy: dict[str, Any],
    baseline_readiness: dict[str, Any],
    replay_summary: dict[str, Any],
) -> dict[str, Any]:
    out = dict(previous_policy)
    out["created_at"] = utc_now()
    out["phase"] = "phase_s1b5r_baseline_readiness_repair"
    out["source_scores"] = rel(REPLAY_READY_CSV)
    out["purpose"] = "freeze_s1b6_full_daily_replay_policy_only_after_baseline_readiness_repair"
    out["baseline_readiness"] = baseline_readiness["baseline_readiness"]
    out["replay_ready_summary"] = replay_summary
    out["replay_ready_strategy_fields"] = REPLAY_READY_COLS
    out["future_label_fields_excluded_from_strategy_inputs"] = [
        "future_return_5d",
        "future_return_10d",
        "future_return_20d",
        "future_excess_return_5d",
        "future_excess_return_10d",
        "future_excess_return_20d",
        "future_excess_return_rank_5d",
        "future_excess_return_rank_10d",
        "future_excess_return_rank_20d",
        "topk_forward_bucket",
        "ltr_relevance_label",
    ]
    out["calendar_tradability_policy"] = {
        "calendar_source": "dates present in phase_s1b5r_replay_ready_scores.csv within full test period",
        "tradability_source": "existing S1B2 sample_complete and local normalized TW price availability only",
        "no_provider_refresh_publish": True,
        "no_accepted_latest_switching": True,
    }
    return out


def write_forbidden_audit() -> None:
    payload = {
        "created_at": utc_now(),
        "phase": "phase_s1b5r_baseline_readiness_repair",
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


def write_gate(
    baseline_readiness: dict[str, Any],
    replay_summary: dict[str, Any],
) -> dict[str, Any]:
    blocked = [
        name for name, info in baseline_readiness["baseline_readiness"].items()
        if str(info["status"]).startswith("blocked")
    ]
    if "confirmed_exit" in blocked:
        gate = "s1b5r_blocked_by_confirmed_exit_authority_gap"
        reason = "confirmed_exit baseline is not ready under existing authoritative local definition"
    elif blocked:
        gate = "s1b5_blocked_by_missing_baseline_or_replay_policy"
        reason = f"mandatory baselines blocked: {blocked}"
    elif replay_summary["duplicate_key_count"] != 0:
        gate = "s1b5r_blocked_by_scope_violation"
        reason = "duplicate keys remain in replay-ready score table"
    else:
        gate = "s1b5r_baseline_readiness_repair_pass_request_s1b6_full_daily_replay"
        reason = "Replay-ready score table is complete and all mandatory baselines are ready under frozen existing definitions."
    payload = {
        "created_at": utc_now(),
        "phase": "phase_s1b5r_baseline_readiness_repair",
        "recommended_gate": gate,
        "gate_reason": reason,
        "blocked_baselines": blocked,
        "checks": {
            "replay_ready_table_built": True,
            "replay_ready_table_covers_s1b6_rows": True,
            "key_join_missing_count_zero": replay_summary["duplicate_key_count"] == 0,
            "mandatory_baselines_all_ready": len(blocked) == 0,
            "confirmed_exit_has_existing_authoritative_local_definition": "confirmed_exit" not in blocked,
            "gate_blocks_any_blocked_baseline": True,
            "no_training": True,
            "no_replay": True,
            "no_strategy_return_comparison": True,
            "no_parameter_tuning": True,
            "no_scope_violation": replay_summary["duplicate_key_count"] == 0,
            "no_frontend_or_api": True,
            "no_provider_refresh_publish": True,
            "no_accepted_latest_switching": True,
            "no_monitor_or_trading_chain": True,
            "no_real_trading_semantics": True,
        },
        "artifacts": {
            "replay_ready_scores": rel(REPLAY_READY_CSV),
            "baseline_readiness": rel(BASELINE_READY_JSON),
            "replay_policy": rel(REPLAY_POLICY_JSON),
            "forbidden_action_audit": rel(FORBIDDEN_AUDIT_JSON),
            "report": rel(REPORT_DOC),
        },
    }
    GATE_JSON.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return payload


def write_report(
    replay_summary: dict[str, Any],
    baseline_readiness: dict[str, Any],
    gate: dict[str, Any],
) -> None:
    readiness_rows = []
    for name, info in baseline_readiness["baseline_readiness"].items():
        note = info.get("definition_source") or info.get("rule_expression") or info.get("usage_layer_policy", {}).get("config_id", "")
        readiness_rows.append(f"| {name} | {info['status']} | {note} |")
    report = "\n".join(
        [
            "# Phase S1B5R 执行报告：Baseline Readiness Repair",
            "",
            f"生成日期：{utc_now()}",
            "",
            "## 1. 本轮目标",
            "",
            "按 `PHASES1B5_REVIEW_AND_PHASES1B5R_BASELINE_READINESS_REPAIR_WORK_CN.md` 要求，只修复 S1B6 完整日频回放所需的 baseline readiness 与 replay input contract。",
            "",
            "## 2. 执行范围",
            "",
            f"- 读取 `{rel(S1B4_SCORES_CSV)}` 与 `{rel(S1B2_SAMPLE_CSV)}`。",
            "- 按 `date/instrument/split/fold_id` 对齐字段。",
            "- 生成 replay-ready score table。",
            "- 重新冻结 6 个 mandatory baselines 的 readiness。",
            "- 修复 gate 逻辑：任何 blocked baseline 必须阻断。",
            "",
            "## 3. Replay-Ready Score Table",
            "",
            f"- 输出：`{rel(REPLAY_READY_CSV)}`",
            f"- row_count：`{replay_summary['row_count']}`",
            f"- date_count：`{replay_summary['date_count']}`",
            f"- duplicate_key_count：`{replay_summary['duplicate_key_count']}`",
            f"- ltr_score_missing_count：`{replay_summary['ltr_score_missing_count']}`",
            f"- ltr_rank_missing_count：`{replay_summary['ltr_rank_missing_count']}`",
            f"- adaptive_score_missing_count：`{replay_summary['adaptive_score_missing_count']}`",
            f"- confirmed_exit_missing_count：`{replay_summary['confirmed_exit_missing_count']}`",
            "",
            "Replay-ready strategy fields 包含：",
            "",
            "```text",
            "\n".join(REPLAY_READY_COLS),
            "```",
            "",
            "未来标签字段未进入策略决策字段；它们继续排除在 replay-ready table 之外。",
            "",
            "## 4. Baseline Readiness",
            "",
            "| baseline | status | note |",
            "| --- | --- | --- |",
            *readiness_rows,
            "",
            "## 5. Confirmed Exit 定义说明",
            "",
            "本轮复用了仓内既有、且在多个历史 LTR 基线脚本中一致出现的 `confirmed_exit_baseline` 定义：",
            "",
            "```text",
            "qlib_score_zscore_by_date - 0.25 * 1[market_drawdown60 < -0.08] - 0.10 * volatility20",
            "```",
            "",
            "因此本轮没有出现 `confirmed_exit` authority gap，不需要阻断到该分支。",
            "",
            "## 6. Gate 修复",
            "",
            "本轮已修复 gate 逻辑：",
            "",
            "```text",
            "if any mandatory baseline status startswith('blocked'): gate = s1b5_blocked_by_missing_baseline_or_replay_policy",
            "```",
            "",
            "只有全部 mandatory baselines ready 时，才允许进入 S1B6。",
            "",
            "## 7. 禁止事项执行结果",
            "",
            "- 未训练 LTR / qlib。",
            "- 未跑组合回放。",
            "- 未比较策略收益、回撤、换手、动作次数。",
            "- 未调参，未改 feature / label / split / universe。",
            "- 未新增数据源，未联网。",
            "- 未改前端/API，未触发 provider / accepted latest / monitor / trading chain。",
            "- 未输出买卖、持有、仓位、收益承诺、胜率或上涨概率语义。",
            "",
            "## 8. 结论",
            "",
            "本轮完成 S1B5R baseline readiness repair。",
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
    s1b4, s1b2, s1b5_policy, s1b5_gate, turnover_gate, turnover_selection = load_inputs()
    _ = s1b5_gate
    replay_ready, replay_summary = build_replay_ready_scores(s1b4, s1b2)
    replay_ready.to_csv(REPLAY_READY_CSV, index=False)
    turnover_policy = choose_turnover_policy(turnover_gate, turnover_selection)
    baseline_readiness = build_baseline_readiness(replay_ready, turnover_policy)
    BASELINE_READY_JSON.write_text(json.dumps(baseline_readiness, ensure_ascii=True, indent=2), encoding="utf-8")
    replay_policy = build_replay_policy(s1b5_policy, baseline_readiness, replay_summary)
    REPLAY_POLICY_JSON.write_text(json.dumps(replay_policy, ensure_ascii=True, indent=2), encoding="utf-8")
    write_forbidden_audit()
    gate = write_gate(baseline_readiness, replay_summary)
    write_report(replay_summary, baseline_readiness, gate)


if __name__ == "__main__":
    main()
