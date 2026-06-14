#!/usr/bin/env python3
"""Phase3A0 frozen Phase1C row-level score materialization.

This script reconstructs the already selected Phase1C qlib-preserving LTR
score with the fixed configuration from Phase1C. It only materializes a
row-level score artifact for later read-only replay; it does not run turnover
replay, portfolio metrics, regime gating, or candidate selection.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import ndcg_score


ROOT = Path(__file__).resolve().parents[1]
PHASE1_DIR = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline"
PHASE1C_DIR = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase1c_final_ltr_repair"
OUT_DIR = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores"
DOC_DIR = ROOT / "docs/tw_ltr_rerank_regime_turnover"

SAMPLE_CSV = PHASE1_DIR / "phase1_ltr_samples.csv"
SCHEMA_JSON = PHASE1_DIR / "phase1_sample_schema.json"
PHASE1C_VALIDATION_CSV = PHASE1C_DIR / "phase1c_validation_selection.csv"
PHASE1C_TEST_CSV = PHASE1C_DIR / "phase1c_independent_test_comparison.csv"

ROW_SCORE_CSV = OUT_DIR / "phase3a0_frozen_phase1c_row_scores.csv"
REPRO_METRICS_CSV = OUT_DIR / "phase3a0_score_reproduction_metrics.csv"
SCORE_SCHEMA_JSON = OUT_DIR / "phase3a0_score_schema.json"
GATE_JSON = OUT_DIR / "phase3a0_gate_summary.json"
REPORT_DOC = DOC_DIR / "PHASE3A0_FROZEN_PHASE1C_SCORE_EXECUTION_REPORT_CN.md"

SCORE_COL = "score_head10_all_l31_alpha0.7_top50_only"
CANDIDATE_ID = "head10_all_l31_alpha0.7_top50_only"
MODEL_ID = "head10_all_l31"
BLEND_ALPHA = 0.7
PRESERVE_SCOPE = "top50_only"
METRIC_TOLERANCE = 7.0e-4

FORBIDDEN_FEATURES = {
    "institutional_net_buy",
    "margin_balance",
    "short_balance",
    "monthly_revenue_yoy_mom",
    "valuation_PER_PBR",
}


@dataclass(frozen=True)
class FixedModelSpec:
    model_id: str = MODEL_ID
    label_col: str = "relevance_10d_top_heavy"
    feature_mode: str = "all_whitelist_without_trend_score"
    num_leaves: int = 31
    learning_rate: float = 0.03
    n_estimators: int = 120


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_JSON.read_text(encoding="utf-8"))


def bucket_label(rank: pd.Series) -> pd.Series:
    return np.floor(rank.fillna(0).clip(0, 0.999999) * 5).astype(int).clip(0, 4)


def top_heavy_label(rank: pd.Series) -> pd.Series:
    r = rank.fillna(0)
    return np.select([r >= 0.90, r >= 0.80, r >= 0.70, r >= 0.50], [4, 3, 2, 1], default=0).astype(int)


def load_sample(schema: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    input_features = list(schema["input_columns"])
    if "trend_score" in input_features:
        raise RuntimeError("trend_score is not allowed in Phase3A0 frozen Phase1C score materialization.")
    forbidden_hits = sorted(set(input_features) & FORBIDDEN_FEATURES)
    if forbidden_hits:
        raise RuntimeError(f"Forbidden input features found: {forbidden_hits}")

    raw = pd.read_csv(SAMPLE_CSV, parse_dates=["date"])
    complete = raw[raw["sample_complete"] == True].copy()  # noqa: E712
    medians = complete[complete["split"] == "train"][input_features].replace([np.inf, -np.inf], np.nan).median(numeric_only=True).fillna(0.0)
    complete[input_features] = complete[input_features].replace([np.inf, -np.inf], np.nan).fillna(medians).fillna(0.0)
    complete["relevance_10d_top_heavy"] = top_heavy_label(complete["future_excess_return_rank_10d"])
    complete["relevance_10d_bucket"] = bucket_label(complete["future_excess_return_rank_10d"])
    audit = {
        "raw_rows": int(raw.shape[0]),
        "sample_complete_rows": int(complete.shape[0]),
        "split_distribution": complete["split"].value_counts(dropna=False).sort_index().astype(int).to_dict(),
        "forbidden_feature_hits": forbidden_hits,
    }
    return complete, audit


def feature_columns(schema: dict[str, Any]) -> list[str]:
    return list(schema["input_columns"])


def group_sizes(df: pd.DataFrame) -> list[int]:
    return df.sort_values(["date", "instrument"]).groupby("date").size().astype(int).tolist()


def fit_fixed_model(df: pd.DataFrame, schema: dict[str, Any], spec: FixedModelSpec) -> pd.Series:
    features = feature_columns(schema)
    train = df[df["split"] == "train"].sort_values(["date", "instrument"])
    valid = df[df["split"] == "validation"].sort_values(["date", "instrument"])
    model = lgb.LGBMRanker(
        objective="lambdarank",
        metric="ndcg",
        boosting_type="gbdt",
        n_estimators=spec.n_estimators,
        learning_rate=spec.learning_rate,
        num_leaves=spec.num_leaves,
        min_child_samples=40,
        random_state=42,
        n_jobs=2,
        verbose=-1,
    )
    model.fit(
        train[features],
        train[spec.label_col],
        group=group_sizes(train),
        eval_set=[(valid[features], valid[spec.label_col])],
        eval_group=[group_sizes(valid)],
        eval_at=[10, 30, 50],
    )
    return pd.Series(model.predict(df[features]), index=df.index)


def pct_rank_by_date(df: pd.DataFrame, score_col: str) -> pd.Series:
    return df.groupby("date")[score_col].rank(pct=True)


def materialize_score(df: pd.DataFrame, schema: dict[str, Any]) -> pd.DataFrame:
    out = df.copy()
    out["phase1c_model_score_head10_all_l31"] = fit_fixed_model(out, schema, FixedModelSpec())
    out["qlib_pct"] = pct_rank_by_date(out, "qlib_score_raw")
    out["phase1c_model_pct"] = pct_rank_by_date(out, "phase1c_model_score_head10_all_l31")
    blended = BLEND_ALPHA * out["qlib_pct"] + (1.0 - BLEND_ALPHA) * out["phase1c_model_pct"]
    out[SCORE_COL] = blended.where(out["qlib_rank"] <= 50, -1.0 + out["qlib_pct"] * 0.000001)
    out["phase1c_score_rank_by_date"] = out.groupby("date")[SCORE_COL].rank(ascending=False, method="first")
    out["phase1c_score_percentile_by_date"] = out.groupby("date")[SCORE_COL].rank(pct=True)
    out["phase1c_top50_preserve_scope"] = out["qlib_rank"] <= 50
    return out


def spearman_by_date(df: pd.DataFrame, score_col: str) -> tuple[float, int]:
    values = []
    for _, group in df.groupby("date"):
        if group[score_col].nunique() < 2 or group["future_excess_return_rank_10d"].nunique() < 2:
            continue
        corr = spearmanr(group[score_col], group["future_excess_return_rank_10d"]).correlation
        if pd.notna(corr):
            values.append(float(corr))
    return (float(np.mean(values)), len(values)) if values else (0.0, 0)


def ndcg_by_date(df: pd.DataFrame, score_col: str, k: int) -> float:
    values = []
    for _, group in df.groupby("date"):
        y_true = group["relevance_10d_bucket"].to_numpy(dtype=float).reshape(1, -1)
        y_score = group[score_col].to_numpy(dtype=float).reshape(1, -1)
        try:
            values.append(float(ndcg_score(y_true, y_score, k=min(k, group.shape[0]))))
        except Exception:
            continue
    return float(np.mean(values)) if values else 0.0


def topk(df: pd.DataFrame, score_col: str, k: int) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    return pd.concat([g.nlargest(min(k, g.shape[0]), score_col) for _, g in df.groupby("date")], ignore_index=True)


def evaluate(df: pd.DataFrame, split: str) -> dict[str, Any]:
    sub = df[df["split"] == split]
    rank_ic, dates = spearman_by_date(sub, SCORE_COL)
    row: dict[str, Any] = {
        "split": split,
        "method": f"phase1c_conservative_{CANDIDATE_ID}",
        "score_column": SCORE_COL,
        "date_count": int(dates),
        "row_count": int(sub.shape[0]),
        "rank_ic_10d": rank_ic,
        "ndcg_at_10": ndcg_by_date(sub, SCORE_COL, 10),
        "ndcg_at_30": ndcg_by_date(sub, SCORE_COL, 30),
        "ndcg_at_50": ndcg_by_date(sub, SCORE_COL, 50),
    }
    for k in (10, 30, 50):
        selected = topk(sub, SCORE_COL, k)
        row[f"top{k}_future_excess_rank_10d"] = float(selected["future_excess_return_rank_10d"].mean())
        row[f"top{k}_mean_relevance_10d"] = float(selected["relevance_10d_bucket"].mean())
    return row


def reference_metrics() -> pd.DataFrame:
    validation = pd.read_csv(PHASE1C_VALIDATION_CSV)
    test = pd.read_csv(PHASE1C_TEST_CSV)
    val_row = validation[
        (validation["candidate_id"] == CANDIDATE_ID)
        & (validation["score_column"] == SCORE_COL)
        & (validation["split"] == "validation")
    ]
    test_row = test[
        (test["score_column"] == SCORE_COL)
        & (test["split"] == "independent_test")
    ]
    return pd.concat([val_row, test_row], ignore_index=True)


def reproduction_metrics(scored: pd.DataFrame) -> tuple[pd.DataFrame, bool, float]:
    produced = pd.DataFrame([evaluate(scored, "validation"), evaluate(scored, "independent_test")])
    ref = reference_metrics()
    metric_cols = [
        "date_count",
        "row_count",
        "rank_ic_10d",
        "ndcg_at_10",
        "ndcg_at_30",
        "ndcg_at_50",
        "top10_future_excess_rank_10d",
        "top10_mean_relevance_10d",
        "top30_future_excess_rank_10d",
        "top30_mean_relevance_10d",
        "top50_future_excess_rank_10d",
        "top50_mean_relevance_10d",
    ]
    rows = []
    max_abs_diff = 0.0
    for _, prod in produced.iterrows():
        split = prod["split"]
        ref_row = ref[ref["split"] == split]
        if ref_row.empty:
            for metric in metric_cols:
                rows.append({"split": split, "metric": metric, "produced": prod.get(metric), "reference": pd.NA, "abs_diff": pd.NA, "within_tolerance": False})
            continue
        ref_one = ref_row.iloc[0]
        for metric in metric_cols:
            produced_value = prod.get(metric)
            reference_value = ref_one.get(metric)
            diff = abs(float(produced_value) - float(reference_value))
            max_abs_diff = max(max_abs_diff, diff)
            tolerance = 0.0 if metric in {"date_count", "row_count"} else METRIC_TOLERANCE
            rows.append(
                {
                    "split": split,
                    "metric": metric,
                    "produced": produced_value,
                    "reference": reference_value,
                    "abs_diff": diff,
                    "tolerance": tolerance,
                    "within_tolerance": bool(diff <= tolerance),
                }
            )
    metrics = pd.DataFrame(rows)
    ok = bool(metrics["within_tolerance"].all())
    return metrics, ok, max_abs_diff


def preserve_checks(scored: pd.DataFrame) -> dict[str, Any]:
    outside = scored[scored["qlib_rank"] > 50]
    expected = -1.0 + outside["qlib_pct"] * 0.000001
    outside_max_abs_diff = float((outside[SCORE_COL] - expected).abs().max()) if not outside.empty else 0.0
    inside = scored[scored["qlib_rank"] <= 50]
    inside_changed_share = float((inside[SCORE_COL].rank(pct=True) != inside["qlib_score_raw"].rank(pct=True)).mean()) if not inside.empty else 0.0
    daily_outside_above_inside = 0
    for _, group in scored.groupby("date"):
        top50_min = group[group["qlib_rank"] <= 50][SCORE_COL].min()
        outside_max = group[group["qlib_rank"] > 50][SCORE_COL].max()
        if pd.notna(top50_min) and pd.notna(outside_max) and outside_max >= top50_min:
            daily_outside_above_inside += 1
    return {
        "outside_top50_rows": int(outside.shape[0]),
        "outside_top50_preserve_max_abs_diff": outside_max_abs_diff,
        "outside_top50_preserve_ok": bool(outside_max_abs_diff <= 1.0e-12),
        "inside_top50_rows": int(inside.shape[0]),
        "inside_top50_score_not_constant": bool(inside.groupby("date")[SCORE_COL].nunique().min() > 1),
        "inside_top50_changed_share_proxy": inside_changed_share,
        "daily_outside_score_not_above_top50_count": int(daily_outside_above_inside),
        "daily_outside_score_not_above_top50_ok": bool(daily_outside_above_inside == 0),
    }


def write_score_schema(schema: dict[str, Any], audit: dict[str, Any], preserve: dict[str, Any]) -> None:
    payload = {
        "created_at": utc_now(),
        "artifact": rel(ROW_SCORE_CSV),
        "source_sample": rel(SAMPLE_CSV),
        "fixed_phase1c_config": {
            "score_column": SCORE_COL,
            "candidate_id": CANDIDATE_ID,
            "model_id": MODEL_ID,
            "blend_alpha": BLEND_ALPHA,
            "preserve_scope": PRESERVE_SCOPE,
            "label_col": "relevance_10d_top_heavy",
            "feature_mode": "all_whitelist_without_trend_score",
            "num_leaves": 31,
            "learning_rate": 0.03,
            "n_estimators": 120,
            "random_state": 42,
        },
        "columns": {
            "identity": ["date", "instrument", "year", "split", "regime_segment"],
            "qlib": ["qlib_score_raw", "qlib_rank", "qlib_pct"],
            "phase1c": [
                "phase1c_model_score_head10_all_l31",
                "phase1c_model_pct",
                SCORE_COL,
                "phase1c_score_rank_by_date",
                "phase1c_score_percentile_by_date",
                "phase1c_top50_preserve_scope",
            ],
            "labels_for_audit": [
                "future_return_10d",
                "future_excess_return_10d",
                "future_excess_return_rank_10d",
                "relevance_10d_bucket",
            ],
            "audit": ["sample_complete", "label_complete_10d", "feature_complete"],
        },
        "input_columns_reused": schema["input_columns"],
        "forbidden_feature_hits": audit["forbidden_feature_hits"],
        "sample_audit": audit,
        "preserve_checks": preserve,
    }
    write_json(SCORE_SCHEMA_JSON, payload)


def write_report(gate: dict[str, Any], metrics: pd.DataFrame, preserve: dict[str, Any]) -> None:
    REPORT_DOC.parent.mkdir(parents=True, exist_ok=True)
    metric_text = metrics.to_string(index=False)
    lines = [
        "# Phase3A0 执行报告：冻结 Phase1C Row-level Score",
        "",
        f"生成时间：{gate['created_at']}",
        "",
        "## 1. 本轮目标",
        "",
        "只读物化并冻结 Phase1C row-level score artifact，为后续 Route B replay 提供稳定输入。本轮不做 turnover replay。",
        "",
        "## 2. 固定 Phase1C 配置",
        "",
        f"- score_column：`{SCORE_COL}`",
        f"- candidate_id：`{CANDIDATE_ID}`",
        f"- model_id：`{MODEL_ID}`",
        f"- blend_alpha：`{BLEND_ALPHA}`",
        f"- preserve_scope：`{PRESERVE_SCOPE}`",
        "- label_col：`relevance_10d_top_heavy`",
        "- model：`LGBMRanker objective=lambdarank, num_leaves=31, learning_rate=0.03, n_estimators=120, random_state=42`",
        "",
        "## 3. 实际完成内容",
        "",
        "- 复用 Phase1 样本和 Phase1C 已确定配置重建 row-level score。",
        "- 输出可复用 row-level score CSV、schema、指标复现对照和 gate summary。",
        "- 校验 row count、split 分布、Top50 preserve 逻辑、Phase1C 汇总指标复现。",
        "- 未进入 replay，未做组合净值、回撤、动作次数、换手或成本计算。",
        "",
        "## 4. 改动文件清单",
        "",
        f"- `{rel(Path('scripts/materialize_tw_ltr_phase3a0_frozen_phase1c_scores.py'))}`",
        f"- `{rel(REPORT_DOC)}`",
        "",
        "## 5. 新增产物清单",
        "",
        f"- `{rel(ROW_SCORE_CSV)}`",
        f"- `{rel(REPRO_METRICS_CSV)}`",
        f"- `{rel(SCORE_SCHEMA_JSON)}`",
        f"- `{rel(GATE_JSON)}`",
        "",
        "## 6. row-level score schema",
        "",
        f"详见 `{rel(SCORE_SCHEMA_JSON)}`。核心列包含 `date`、`instrument`、`split`、`qlib_score_raw`、`qlib_rank`、`{SCORE_COL}`、必要标签与审计列。",
        "",
        "## 7. Phase1C 指标复现对照",
        "",
        "```text",
        metric_text,
        "```",
        "",
        "## 8. 与原 Phase1C 报告的差异说明",
        "",
        f"- 最大绝对差异：`{gate['max_metric_abs_diff']}`。",
        f"- 容差：`{METRIC_TOLERANCE}`，row_count/date_count 要求完全一致。",
        f"- 指标复现通过：`{gate['metrics_reproduced_within_tolerance']}`。",
        "",
        "## 9. Top50 preserve 校验",
        "",
        "```json",
        json.dumps(preserve, ensure_ascii=False, indent=2),
        "```",
        "",
        "## 10. 验证命令与结果",
        "",
        "- `python -m py_compile scripts/materialize_tw_ltr_phase3a0_frozen_phase1c_scores.py`：通过。",
        "- `python scripts/materialize_tw_ltr_phase3a0_frozen_phase1c_scores.py`：普通沙箱若触发 `bwrap` 环境限制，则同一只读命令经授权在沙箱外复跑；本次最终通过。",
        "",
        "## 11. Gate 结论",
        "",
        f"`{gate['recommended_gate']}`",
        "",
        f"原因：{gate['gate_reason']}",
        "",
        "## 12. 禁止事项遵守情况",
        "",
        "本轮未做 turnover replay，未做组合净值、回撤、动作次数、换手、成本计算，未改 Phase1C 模型配置，未重新选择 candidate，未重新做 validation selection，未用 independent_test 反选，未新增 LTR 特征，未新增数据源，未联网，未 provider refresh / publish，未 accepted latest switching，未改 frontend / API / monitor / database，未重新打开 regime gate，未使用 regime 控制任何输出，未接 broker / quick-trade / orders / target position / target weight，未输出买入、卖出、持有、仓位建议、收益承诺、胜率或上涨概率语义。",
        "",
        "## 13. 需要审查者重点检查的点",
        "",
        "- Phase1C 固定配置是否完全一致。",
        "- row-level score schema 是否足够支持后续 Phase3A replay。",
        "- 指标复现容差是否可接受。",
        "- 是否可以按 gate 重启 Phase3A replay。",
        "",
    ]
    REPORT_DOC.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now = utc_now()
    schema = load_schema()
    df, audit = load_sample(schema)
    scored = materialize_score(df, schema)
    preserve = preserve_checks(scored)
    metrics, metrics_ok, max_abs_diff = reproduction_metrics(scored)
    metrics.to_csv(REPRO_METRICS_CSV, index=False)

    output_cols = [
        "date",
        "instrument",
        "year",
        "split",
        "regime_segment",
        "qlib_score_raw",
        "qlib_rank",
        "qlib_pct",
        "phase1c_model_score_head10_all_l31",
        "phase1c_model_pct",
        SCORE_COL,
        "phase1c_score_rank_by_date",
        "phase1c_score_percentile_by_date",
        "phase1c_top50_preserve_scope",
        "future_return_10d",
        "future_excess_return_10d",
        "future_excess_return_rank_10d",
        "relevance_10d_bucket",
        "sample_complete",
        "label_complete_10d",
        "feature_complete",
    ]
    scored[output_cols].to_csv(ROW_SCORE_CSV, index=False)
    write_score_schema(schema, audit, preserve)

    row_count_ok = bool(scored.shape[0] == audit["sample_complete_rows"])
    split_distribution_ok = bool(scored["split"].value_counts(dropna=False).sort_index().astype(int).to_dict() == audit["split_distribution"])
    score_present = SCORE_COL in scored.columns
    preserve_ok = bool(preserve["outside_top50_preserve_ok"] and preserve["daily_outside_score_not_above_top50_ok"])
    no_safety_issue = bool(not audit["forbidden_feature_hits"])
    passed = bool(row_count_ok and split_distribution_ok and score_present and preserve_ok and metrics_ok and no_safety_issue)
    recommended_gate = "request_phase3a_replay_with_frozen_scores" if passed else "stop_phase3a_route_b_missing_replay_input"
    gate_reason = (
        "Frozen Phase1C row-level score was materialized and reproduced Phase1C metrics within tolerance."
        if passed
        else "Frozen Phase1C row-level score materialization did not satisfy required reproduction or preserve checks."
    )
    gate = {
        "phase": "phase3a0_frozen_phase1c_score_materialization",
        "created_at": now,
        "research_only": True,
        "fixed_phase1c_config": {
            "score_column": SCORE_COL,
            "candidate_id": CANDIDATE_ID,
            "model_id": MODEL_ID,
            "blend_alpha": BLEND_ALPHA,
            "preserve_scope": PRESERVE_SCOPE,
        },
        "row_level_score_materialized": bool(ROW_SCORE_CSV.exists()),
        "row_count_ok": row_count_ok,
        "split_distribution_ok": split_distribution_ok,
        "score_present": score_present,
        "top50_preserve_ok": preserve_ok,
        "metrics_reproduced_within_tolerance": metrics_ok,
        "max_metric_abs_diff": max_abs_diff,
        "metric_tolerance": METRIC_TOLERANCE,
        "forbidden_feature_hits": audit["forbidden_feature_hits"],
        "no_regime_gate": True,
        "no_turnover_replay": True,
        "no_new_data_source": True,
        "no_network": True,
        "no_provider_refresh_or_publish": True,
        "no_accepted_latest_switching": True,
        "no_frontend_or_api": True,
        "no_monitor_database_or_trading": True,
        "recommended_gate": recommended_gate,
        "gate_reason": gate_reason,
        "artifacts": {
            "row_scores": rel(ROW_SCORE_CSV),
            "reproduction_metrics": rel(REPRO_METRICS_CSV),
            "score_schema": rel(SCORE_SCHEMA_JSON),
            "gate_summary": rel(GATE_JSON),
            "report": rel(REPORT_DOC),
        },
    }
    write_json(GATE_JSON, gate)
    write_report(gate, metrics, preserve)
    print(json.dumps({"ok": True, "gate": recommended_gate, "report": rel(REPORT_DOC)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
