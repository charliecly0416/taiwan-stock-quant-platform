#!/usr/bin/env python3
"""Confirm Phase 2C gate for TW Decision Entry Model v1.

Phase 2C is a closeout confirmation only. It evaluates two predeclared
Phase 2B candidates against baseline_qlib_rank and writes the final pass/archive
decision. It does not train models, add features, refresh data, publish data,
run portfolio replay, touch frontend/API, or interact with trading state.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data_tw/experiments/decision_model/phase2_entry_model_v1"
DOC_DIR = ROOT / "docs/tw_decision_model"

PHASE2_METRICS_PATH = OUT_DIR / "phase2_metrics.csv"
PHASE2B_ABLATION_PATH = OUT_DIR / "phase2b_feature_group_ablation.csv"

GATE_CONFIRMATION_PATH = OUT_DIR / "phase2c_gate_confirmation.csv"
CANDIDATE_COMPARISON_PATH = OUT_DIR / "phase2c_candidate_comparison.csv"
FAILURE_ATTRIBUTION_PATH = OUT_DIR / "phase2c_failure_attribution.csv"
EXEC_REPORT_PATH = DOC_DIR / "PHASE2C_EXECUTION_REPORT_CN.md"

FEATURE_GROUP = "qlib + technical"
BASELINE_MODEL = "baseline_qlib_rank"
CANDIDATE_MODELS = ["ensemble_fixed_trainval", "regression"]
GATE_PARTS = [
    ("main", "test"),
    ("main", "forward"),
    ("sensitivity", "test"),
    ("sensitivity", "forward"),
]
METRICS = [
    "RankIC",
    "NDCG@10",
    "precision@5",
    "top5_excess_return",
    "top10_excess_return",
]
DELTA_COLUMNS = {
    "RankIC": "rankic_delta",
    "NDCG@10": "ndcg10_delta",
    "precision@5": "precision5_delta",
    "top5_excess_return": "top5_delta",
    "top10_excess_return": "top10_delta",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_no rows_"
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---" for _ in cols]) + "|"]
    for _, row in df.iterrows():
        values = []
        for col in cols:
            value = row[col]
            if isinstance(value, float):
                values.append("" if pd.isna(value) else f"{value:.6f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    phase2_metrics = pd.read_csv(PHASE2_METRICS_PATH)
    phase2b_ablation = pd.read_csv(PHASE2B_ABLATION_PATH)
    required_metrics = {"split_name", "split_part", "model", *METRICS}
    missing_phase2 = sorted(required_metrics - set(phase2_metrics.columns))
    missing_ablation = sorted((required_metrics | {"feature_group"}) - set(phase2b_ablation.columns))
    if missing_phase2:
        raise RuntimeError(f"phase2_metrics missing columns: {missing_phase2}")
    if missing_ablation:
        raise RuntimeError(f"phase2b_feature_group_ablation missing columns: {missing_ablation}")
    return phase2_metrics, phase2b_ablation


def build_candidate_comparison(phase2_metrics: pd.DataFrame, phase2b_ablation: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    baseline = phase2_metrics[phase2_metrics["model"].eq(BASELINE_MODEL)].copy()
    candidates = phase2b_ablation[
        phase2b_ablation["feature_group"].eq(FEATURE_GROUP)
        & phase2b_ablation["model"].isin(CANDIDATE_MODELS)
    ].copy()
    for split_name, split_part in GATE_PARTS:
        base_part = baseline[
            baseline["split_name"].eq(split_name)
            & baseline["split_part"].eq(split_part)
        ]
        if len(base_part) != 1:
            raise RuntimeError(f"missing unique baseline row for {split_name}/{split_part}: {len(base_part)}")
        base_row = base_part.iloc[0]
        for model in CANDIDATE_MODELS:
            cand_part = candidates[
                candidates["split_name"].eq(split_name)
                & candidates["split_part"].eq(split_part)
                & candidates["model"].eq(model)
            ]
            if len(cand_part) != 1:
                raise RuntimeError(f"missing unique candidate row for {FEATURE_GROUP}/{model}/{split_name}/{split_part}: {len(cand_part)}")
            cand_row = cand_part.iloc[0]
            row: dict[str, Any] = {
                "feature_group": FEATURE_GROUP,
                "candidate_model": model,
                "baseline_model": BASELINE_MODEL,
                "split_name": split_name,
                "split_part": split_part,
            }
            for metric in METRICS:
                row[f"candidate_{metric}"] = float(cand_row[metric])
                row[f"baseline_{metric}"] = float(base_row[metric])
                row[DELTA_COLUMNS[metric]] = float(cand_row[metric] - base_row[metric])
            rows.append(row)
    return pd.DataFrame(rows)


def build_gate_confirmation(comparison: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    rows: list[dict[str, Any]] = []
    for (feature_group, model), g in comparison.groupby(["feature_group", "candidate_model"], sort=False):
        interval_rows = []
        for _, row in g.iterrows():
            top5_pass = row["top5_delta"] >= 0
            top10_pass = row["top10_delta"] >= 0
            rankic_pass = row["rankic_delta"] >= 0
            ndcg10_pass = row["ndcg10_delta"] >= 0
            precision5_pass = row["precision5_delta"] >= 0
            interval_pass = bool(top5_pass and top10_pass and rankic_pass and ndcg10_pass and precision5_pass)
            interval_rows.append(interval_pass)
            rows.append({
                "feature_group": feature_group,
                "candidate_model": model,
                "baseline_model": BASELINE_MODEL,
                "split_name": row["split_name"],
                "split_part": row["split_part"],
                "rankic_delta": row["rankic_delta"],
                "ndcg10_delta": row["ndcg10_delta"],
                "precision5_delta": row["precision5_delta"],
                "top5_delta": row["top5_delta"],
                "top10_delta": row["top10_delta"],
                "rankic_pass": rankic_pass,
                "ndcg10_pass": ndcg10_pass,
                "precision5_pass": precision5_pass,
                "top5_pass": top5_pass,
                "top10_pass": top10_pass,
                "interval_pass": interval_pass,
                "candidate_pass_phase3_gate": False,
            })
        candidate_pass = bool(len(interval_rows) == len(GATE_PARTS) and all(interval_rows))
        for row in rows:
            if row["feature_group"] == feature_group and row["candidate_model"] == model:
                row["candidate_pass_phase3_gate"] = candidate_pass
    gate = pd.DataFrame(rows)
    pass_phase3_gate = bool(gate.groupby(["feature_group", "candidate_model"])["candidate_pass_phase3_gate"].first().any())
    return gate, pass_phase3_gate


def build_failure_attribution(gate: pd.DataFrame, pass_phase3_gate: bool) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if pass_phase3_gate:
        return pd.DataFrame(rows)
    for _, row in gate.iterrows():
        failed = []
        for col, label in [
            ("top5_pass", "top5_delta_negative"),
            ("top10_pass", "top10_delta_negative"),
            ("rankic_pass", "rankic_delta_negative"),
            ("ndcg10_pass", "ndcg10_delta_negative"),
            ("precision5_pass", "precision5_delta_negative"),
        ]:
            if not bool(row[col]):
                failed.append(label)
        if failed:
            rows.append({
                "feature_group": row["feature_group"],
                "candidate_model": row["candidate_model"],
                "baseline_model": BASELINE_MODEL,
                "split_name": row["split_name"],
                "split_part": row["split_part"],
                "failed_checks": ",".join(failed),
                "rankic_delta": row["rankic_delta"],
                "ndcg10_delta": row["ndcg10_delta"],
                "precision5_delta": row["precision5_delta"],
                "top5_delta": row["top5_delta"],
                "top10_delta": row["top10_delta"],
                "archive_entry_model_v1_failed": True,
                "no_phase2d": True,
            })
    return pd.DataFrame(rows)


def write_report(gate: pd.DataFrame, comparison: pd.DataFrame, failure: pd.DataFrame, pass_phase3_gate: bool) -> None:
    archive_entry_model_v1_failed = not pass_phase3_gate
    title = "# Phase 2C Entry Model v1 归档失败执行报告" if archive_entry_model_v1_failed else "# Phase 2C Entry Model v1 Gate 通过执行报告"
    gate_view = gate[[
        "feature_group",
        "candidate_model",
        "split_name",
        "split_part",
        "top5_delta",
        "top10_delta",
        "rankic_delta",
        "ndcg10_delta",
        "precision5_delta",
        "interval_pass",
        "candidate_pass_phase3_gate",
    ]]
    failure_view = failure[[
        "feature_group",
        "candidate_model",
        "split_name",
        "split_part",
        "failed_checks",
        "top5_delta",
        "top10_delta",
        "rankic_delta",
        "ndcg10_delta",
        "precision5_delta",
    ]] if not failure.empty else failure
    lines = [
        title,
        "",
        "## 1. 执行摘要",
        "",
        f"- 执行日期：`{utc_now()}`",
        "- 执行范围：Phase 2C 最后一次 gate confirmation / closeout。",
        "- 评估候选：`qlib + technical / ensemble_fixed_trainval`、`qlib + technical / regression`。",
        "- 唯一准入基线：`baseline_qlib_rank`。",
        "- 是否新增 feature：否。",
        "- 是否新增数据源、FinMind、2024 回填或数据补齐：否。",
        "- 是否训练新模型、Exit Model、LambdaRank：否。",
        "- 是否做组合回放、前端/API/产品化：否。",
        "- 是否触碰 provider refresh/publish/accepted latest switching：否。",
        "- 是否触碰 broker/orders/quick-trade/target position/monitor config/alerts：否。",
        "",
        "## 2. 固定判断口径",
        "",
        "- 覆盖区间：`main/test`、`main/forward`、`sensitivity/test`、`sensitivity/forward`。",
        "- 通过条件：同一个候选四个区间的 top5/top10 delta 均非负，且 RankIC、NDCG@10、precision@5 不出现负 delta。",
        "- 容忍区间：未使用。",
        "- 不以单一区间或 overall 均值替代逐区间判断。",
        "",
        "## 3. Gate Confirmation",
        "",
        markdown_table(gate_view),
        "",
        "## 4. Candidate Comparison",
        "",
        markdown_table(comparison[[
            "feature_group",
            "candidate_model",
            "split_name",
            "split_part",
            "candidate_top5_excess_return",
            "baseline_top5_excess_return",
            "top5_delta",
            "candidate_top10_excess_return",
            "baseline_top10_excess_return",
            "top10_delta",
        ]]),
        "",
        "## 5. Failure Attribution",
        "",
        markdown_table(failure_view),
        "",
        "## 6. 最终二选一结论",
        "",
        f"- `pass_phase3_gate={str(pass_phase3_gate).lower()}`",
        f"- `archive_entry_model_v1_failed={str(archive_entry_model_v1_failed).lower()}`",
        "- Phase 3 准入：否。" if archive_entry_model_v1_failed else "- Phase 3 准入：可提交审查者复核。",
        "- Phase 2D：不继续。" if archive_entry_model_v1_failed else "- Phase 2D：不需要。",
        "- 后续若要重启 Entry 方向，只能由用户另行确认新研究方向。" if archive_entry_model_v1_failed else "- 后续仍需审查者确认后才能进入 Phase 3。",
        "",
        "## 7. 生成文件",
        "",
        f"- `{rel(GATE_CONFIRMATION_PATH)}`",
        f"- `{rel(CANDIDATE_COMPARISON_PATH)}`",
        f"- `{rel(FAILURE_ATTRIBUTION_PATH)}`",
        f"- `{rel(EXEC_REPORT_PATH)}`",
        "",
    ]
    EXEC_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    phase2_metrics, phase2b_ablation = load_inputs()
    comparison = build_candidate_comparison(phase2_metrics, phase2b_ablation)
    gate, pass_phase3_gate = build_gate_confirmation(comparison)
    failure = build_failure_attribution(gate, pass_phase3_gate)

    comparison.to_csv(CANDIDATE_COMPARISON_PATH, index=False)
    gate.to_csv(GATE_CONFIRMATION_PATH, index=False)
    failure.to_csv(FAILURE_ATTRIBUTION_PATH, index=False)
    write_report(gate, comparison, failure, pass_phase3_gate)

    print(json.dumps({
        "status": "ok",
        "scope": "phase2c_closeout_only",
        "pass_phase3_gate": pass_phase3_gate,
        "archive_entry_model_v1_failed": not pass_phase3_gate,
        "outputs": [
            rel(Path("scripts/confirm_tw_decision_entry_model_phase2c.py")),
            rel(GATE_CONFIRMATION_PATH),
            rel(CANDIDATE_COMPARISON_PATH),
            rel(FAILURE_ATTRIBUTION_PATH),
            rel(EXEC_REPORT_PATH),
        ],
        "safety": {
            "new_features": False,
            "new_data_sources": False,
            "exit_model": False,
            "lambdarank": False,
            "portfolio_replay": False,
            "frontend_api_productization": False,
            "provider_refresh_publish_or_accepted_latest_switch": False,
            "broker_orders_quick_trade_target_positions": False,
            "monitor_config_alerts": False,
        },
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
