#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
S1_GATE = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6r_accounting_repair/phase_s1b6r_gate_summary.json"
S1_FULL = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6r_accounting_repair/phase_s1b6r_strategy_metrics_full_test.csv"
S2D_GATE = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/phase_s2d_gate_summary.json"
S2D_STRATEGY = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/phase_s2d_replay_metrics_by_strategy.csv"
S2D_SEGMENT = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/phase_s2d_replay_metrics_by_segment.csv"
S2D_ROLLING = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/phase_s2d_rolling_6m_metrics.csv"
S2D_COVERAGE = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/phase_s2d_strategy_input_coverage_audit.json"
OUT_DIR = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2e_fresh_retrain_conclusion"
DOC = ROOT / "docs/tw_ltr_qlib_split_aligned_retrain/PHASES2E_FRESH_RETRAIN_CONCLUSION_EXECUTION_REPORT_CN.md"

EVIDENCE_JSON = OUT_DIR / "phase_s2e_s1_s2_evidence_summary.json"
DECISION_MATRIX_CSV = OUT_DIR / "phase_s2e_default_candidate_decision_matrix.csv"
LTR_NOTE_JSON = OUT_DIR / "phase_s2e_ltr_positioning_note.json"
FORBIDDEN_JSON = OUT_DIR / "phase_s2e_forbidden_action_audit.json"
GATE_JSON = OUT_DIR / "phase_s2e_gate_summary.json"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def wjson(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def wcsv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    s1_gate = load_json(S1_GATE)
    s2d_gate = load_json(S2D_GATE)
    coverage = load_json(S2D_COVERAGE)
    s1_full = pd.read_csv(S1_FULL)
    s2d_strategy = pd.read_csv(S2D_STRATEGY)
    s2d_segment = pd.read_csv(S2D_SEGMENT)
    s2d_rolling = pd.read_csv(S2D_ROLLING)

    validation = s2d_strategy[(s2d_strategy["split"] == "validation") & (s2d_strategy["segment_type"] == "full")].copy()
    test = s2d_strategy[(s2d_strategy["split"] == "test") & (s2d_strategy["segment_type"] == "full")].copy()
    h2 = s2d_segment[(s2d_segment["split"] == "test") & (s2d_segment["segment_type"] == "year_segment") & (s2d_segment["segment_name"] == "2025H2")].copy()
    ytd = s2d_segment[(s2d_segment["split"] == "test") & (s2d_segment["segment_type"] == "year_segment") & (s2d_segment["segment_name"] == "2026YTD_to_2026-05-07")].copy()
    regime_small = s2d_segment[s2d_segment["comparison_status"] == "sample_too_small"].copy()

    fresh_top50_val = validation[validation["method"] == "fresh_qlib_top50_adaptive_baseline"].iloc[0]
    fresh_top50_test = test[test["method"] == "fresh_qlib_top50_adaptive_baseline"].iloc[0]
    fresh_confirmed_test = test[test["method"] == "fresh_confirmed_exit"].iloc[0]
    ltr_simple_test = test[test["method"] == "fresh_ltr_simple"].iloc[0]
    ltr_tc_test = test[test["method"] == "fresh_ltr_turnover_controlled"].iloc[0]
    ltr_simple_val = validation[validation["method"] == "fresh_ltr_simple"].iloc[0]
    ltr_tc_val = validation[validation["method"] == "fresh_ltr_turnover_controlled"].iloc[0]

    evidence = {
        "created_at": now(),
        "phase": "phase_s2e_fresh_retrain_conclusion",
        "mainline_relation": {
            "s1_role": "old_window_split_aligned_method_validation",
            "s2_role": "fresh_retrain_current_usability_validation",
            "s1_supports_ltr_method_continue": True,
            "s2_must_not_reuse_s1_win_as_fresh_default_evidence": True,
        },
        "source_artifacts": {
            "s1_gate": rel(S1_GATE),
            "s1_full_test_metrics": rel(S1_FULL),
            "s2d_gate": rel(S2D_GATE),
            "s2d_replay_metrics_by_strategy": rel(S2D_STRATEGY),
            "s2d_replay_metrics_by_segment": rel(S2D_SEGMENT),
            "s2d_rolling_6m_metrics": rel(S2D_ROLLING),
            "s2d_coverage_audit": rel(S2D_COVERAGE),
        },
        "s1_summary": {
            "review_status": "method_supported_to_enter_s2",
            "gate_note": s1_gate.get("recommended_gate", ""),
            "interpretation": "S1 only established that LTR had enough old-window method evidence to continue into fresh retrain validation; it did not establish fresh default eligibility.",
        },
        "s2_validation_full": validation[[
            "method",
            "fee_tax_adjusted_net_return",
            "max_drawdown",
            "action_count",
            "relative_return_vs_fresh_top50_adaptive",
            "relative_drawdown_vs_fresh_top50_adaptive",
            "relative_actions_vs_fresh_top50_adaptive",
        ]].to_dict("records"),
        "s2_test_full": test[[
            "method",
            "fee_tax_adjusted_net_return",
            "max_drawdown",
            "action_count",
            "relative_return_vs_fresh_top50_adaptive",
            "relative_drawdown_vs_fresh_top50_adaptive",
            "relative_actions_vs_fresh_top50_adaptive",
        ]].to_dict("records"),
        "s2_year_segments": {
            "2025H2": h2[[
                "method",
                "fee_tax_adjusted_net_return",
                "max_drawdown",
                "action_count",
                "relative_return_vs_fresh_top50_adaptive",
            ]].to_dict("records"),
            "2026YTD_to_2026-05-07": ytd[[
                "method",
                "fee_tax_adjusted_net_return",
                "max_drawdown",
                "action_count",
                "relative_return_vs_fresh_top50_adaptive",
            ]].to_dict("records"),
        },
        "s2_rolling_6m_note": {
            "window_count": int(s2d_rolling["segment_name"].nunique()),
            "ltr_turnover_controlled_has_some_positive_windows": bool(
                ((s2d_rolling["method"] == "fresh_ltr_turnover_controlled")
                & (s2d_rolling["relative_return_vs_fresh_top50_adaptive"] > 0)).any()
            ),
            "instruction": "rolling windows are supportive secondary diagnostics only; they cannot override full validation/test default-candidate evidence.",
        },
        "regime_caveat": {
            "sample_too_small_row_count": int(regime_small.shape[0]),
            "must_not_overinterpret_small_regime_segments": True,
        },
        "coverage_caveat": {
            "validation_ltr_rows_total": int(coverage["split_summary"]["validation"]["ltr_rows_total"]),
            "validation_qlib_rows_total": int(coverage["split_summary"]["validation"]["qlib_rows_total"]),
            "test_ltr_rows_total": int(coverage["split_summary"]["test"]["ltr_rows_total"]),
            "test_qlib_rows_total": int(coverage["split_summary"]["test"]["qlib_rows_total"]),
            "score_coverage_differences_disclosed": True,
        },
    }
    wjson(EVIDENCE_JSON, evidence)

    matrix_rows = [
        {
            "candidate_group": "fresh_qlib_top50_adaptive_baseline",
            "default_candidate_status": "supported",
            "validation_evidence": "validation_full_top_reference",
            "test_evidence": "strong_full_test_reference",
            "tradeoff_note": "balanced baseline; no extra turnover constraint required",
            "allowed_next_positioning": "default_research_candidate",
        },
        {
            "candidate_group": "fresh_confirmed_exit",
            "default_candidate_status": "supported_with_same_family",
            "validation_evidence": "below_top50_on_validation",
            "test_evidence": "slightly_above_top50_on_full_test",
            "tradeoff_note": "same qlib family candidate; evidence supports keeping within qlib/top50 family, not promoting LTR",
            "allowed_next_positioning": "same_family_research_candidate",
        },
        {
            "candidate_group": "fresh_rank_rotate_top50",
            "default_candidate_status": "not_preferred_vs_top50_adaptive",
            "validation_evidence": "below_top50",
            "test_evidence": "below_top50",
            "tradeoff_note": "simple rank rotate remains weaker than adaptive baseline in full evidence",
            "allowed_next_positioning": "secondary_baseline_only",
        },
        {
            "candidate_group": "fresh_ltr_simple",
            "default_candidate_status": "not_supported",
            "validation_evidence": "lower_return_and_worse_drawdown_than_top50",
            "test_evidence": "lower_return_and_worse_drawdown_than_top50",
            "tradeoff_note": "must not be described as fresh default candidate",
            "allowed_next_positioning": "research_only_not_default",
        },
        {
            "candidate_group": "fresh_ltr_turnover_controlled",
            "default_candidate_status": "not_auto_supported",
            "validation_evidence": "much_lower_actions_but lower_return_and_worse_drawdown_than_top50",
            "test_evidence": "much_lower_actions_but lower_return_and_worse_drawdown_than_top50",
            "tradeoff_note": "may be kept as low-action research candidate; cannot be auto-selected without user tradeoff acceptance",
            "allowed_next_positioning": "low_action_research_candidate_only",
        },
    ]
    wcsv(
        DECISION_MATRIX_CSV,
        matrix_rows,
        [
            "candidate_group",
            "default_candidate_status",
            "validation_evidence",
            "test_evidence",
            "tradeoff_note",
            "allowed_next_positioning",
        ],
    )

    ltr_note = {
        "created_at": now(),
        "phase": "phase_s2e_fresh_retrain_conclusion",
        "fresh_ltr_simple": {
            "default_supported": False,
            "reason": "full validation and full test are both below fresh qlib top50 adaptive in return and worse in drawdown",
            "must_not_claim": [
                "better_return",
                "better_stability",
                "fresh_default_supported",
            ],
        },
        "fresh_ltr_turnover_controlled": {
            "default_supported": False,
            "low_action_tradeoff_exists": True,
            "tradeoff_summary": {
                "validation_action_count": int(ltr_tc_val["action_count"]),
                "validation_relative_return_vs_top50": float(ltr_tc_val["relative_return_vs_fresh_top50_adaptive"]),
                "validation_relative_drawdown_vs_top50": float(ltr_tc_val["relative_drawdown_vs_fresh_top50_adaptive"]),
                "test_action_count": int(ltr_tc_test["action_count"]),
                "test_relative_return_vs_top50": float(ltr_tc_test["relative_return_vs_fresh_top50_adaptive"]),
                "test_relative_drawdown_vs_top50": float(ltr_tc_test["relative_drawdown_vs_fresh_top50_adaptive"]),
            },
            "positioning": "keep_as_low_action_research_candidate_only",
            "must_not_claim": [
                "better_return",
                "better_drawdown",
                "auto_selected_default",
            ],
        },
    }
    wjson(LTR_NOTE_JSON, ltr_note)

    forbidden = {
        "created_at": now(),
        "phase": "phase_s2e_fresh_retrain_conclusion",
        "no_new_training_or_replay": True,
        "no_parameter_search": True,
        "no_new_strategy_variant": True,
        "no_provider_refresh_publish": True,
        "no_accepted_latest_switching": True,
        "no_frontend_or_api": True,
        "no_monitor_or_trading_chain": True,
        "no_broker_quick_trade_orders": True,
        "no_target_position_or_target_weight": True,
        "no_return_or_winrate_or_probability_promise": True,
    }
    wjson(FORBIDDEN_JSON, forbidden)

    gate = {
        "created_at": now(),
        "phase": "phase_s2e_fresh_retrain_conclusion",
        "recommended_gate": "fresh_retrain_qlib_or_top50_default_supported",
        "s1_s2_relationship_explained": True,
        "validation_and_test_evidence_summarized": True,
        "default_candidate_gate_is_one_of_mainline_allowed_gates": True,
        "ltr_not_overclaimed": True,
        "low_turnover_tradeoff_not_auto_selected": True,
        "no_new_training_or_replay": True,
        "no_parameter_search": True,
        "no_new_strategy_variant": True,
        "no_provider_refresh_publish": True,
        "no_accepted_latest_switching": True,
        "no_frontend_or_api": True,
        "no_monitor_or_trading_chain": True,
        "decision_reason": (
            "S1 supported continuing LTR method validation, but S2 fresh retrain validation/test do not support LTR as the fresh default. "
            "Current evidence supports staying within the qlib/top50 family as the default research direction."
        ),
        "artifacts": {
            "s1_s2_evidence_summary": rel(EVIDENCE_JSON),
            "default_candidate_decision_matrix": rel(DECISION_MATRIX_CSV),
            "ltr_positioning_note": rel(LTR_NOTE_JSON),
            "forbidden_action_audit": rel(FORBIDDEN_JSON),
            "report": rel(DOC),
        },
    }
    wjson(GATE_JSON, gate)

    report_lines = [
        "# Phase S2E 执行报告：Fresh Retrain Conclusion",
        "",
        f"生成日期：{gate['created_at']}",
        "",
        "## 1. 本轮目标",
        "",
        "只基于 S1 与 S2D 既有证据，给出 fresh retrain 研究结论 gate，并明确 LTR 与 qlib/top50 家族的当前定位。",
        "",
        "## 2. S1 与 S2 的关系",
        "",
        "- S1 的作用：验证旧窗口下 LTR 方法是否值得继续进入 fresh retrain。",
        "- S2 的作用：验证当前 fresh retrain 场景下谁更适合作为默认研究候选。",
        "- 结论边界：不能把 S1 的方法有效性包装成 S2 的 fresh 默认资格。",
        "",
        "## 3. Full Validation / Full Test 结论",
        "",
        f"- fresh top50 adaptive validation net_return: `{float(fresh_top50_val['fee_tax_adjusted_net_return']):.6f}`",
        f"- fresh LTR simple validation relative_return_vs_top50: `{float(ltr_simple_val['relative_return_vs_fresh_top50_adaptive']):.6f}`",
        f"- fresh LTR turnover-controlled validation relative_return_vs_top50: `{float(ltr_tc_val['relative_return_vs_fresh_top50_adaptive']):.6f}`",
        f"- fresh top50 adaptive test net_return: `{float(fresh_top50_test['fee_tax_adjusted_net_return']):.6f}`",
        f"- fresh confirmed_exit test relative_return_vs_top50: `{float(fresh_confirmed_test['relative_return_vs_fresh_top50_adaptive']):.6f}`",
        f"- fresh LTR simple test relative_return_vs_top50: `{float(ltr_simple_test['relative_return_vs_fresh_top50_adaptive']):.6f}`",
        f"- fresh LTR turnover-controlled test relative_return_vs_top50: `{float(ltr_tc_test['relative_return_vs_fresh_top50_adaptive']):.6f}`",
        "",
        "解释：validation 与 full test 都不支持把 LTR 设为 fresh 默认；`fresh_confirmed_exit` 在 full test 略高于 top50 adaptive，但仍属于 qlib/top50 同家族证据，不构成 LTR default 支持。",
        "",
        "## 4. LTR 定位",
        "",
        "- `fresh_ltr_simple`：不支持默认。",
        "- `fresh_ltr_turnover_controlled`：可保留为低动作研究候选，但不能自动当作默认；它是收益/回撤换低动作的 tradeoff，不应由执行者自动替用户选择。",
        "",
        "## 5. Rolling / Regime Caveat",
        "",
        f"- rolling 6m window count: `{int(s2d_rolling['segment_name'].nunique())}`",
        f"- regime `sample_too_small` rows: `{int(regime_small.shape[0])}`",
        "- 部分 rolling/regime 窗口可为 LTR turnover-controlled 提供局部正信号，但不能覆盖 full validation/full test 的默认候选结论。",
        "",
        "## 6. 研究结论",
        "",
        "当前主线研究结论应为：",
        "",
        "```text",
        "fresh_retrain_qlib_or_top50_default_supported",
        "```",
        "",
        "这表示：当前更合理的 fresh 默认研究方向仍是 qlib/top50 家族；LTR 保留为研究候选，而不是默认候选。",
        "",
        "## 7. 主要产物",
        "",
        f"- `{rel(EVIDENCE_JSON)}`",
        f"- `{rel(DECISION_MATRIX_CSV)}`",
        f"- `{rel(LTR_NOTE_JSON)}`",
        f"- `{rel(FORBIDDEN_JSON)}`",
        f"- `{rel(GATE_JSON)}`",
    ]
    DOC.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "gate": gate["recommended_gate"], "report": rel(DOC)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
