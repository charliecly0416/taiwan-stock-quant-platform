#!/usr/bin/env python3
"""Final Phase 1C conservative LTR repair.

This is the last Stage 2 repair attempt authorized by the user decision doc.
It reuses only the Phase 1 sample, keeps trend_score excluded, adds no new
features or data sources, and selects candidates on validation only.
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
OUT_DIR = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase1c_final_ltr_repair"
DOC_DIR = ROOT / "docs/tw_ltr_rerank_regime_turnover"

SAMPLE_CSV = PHASE1_DIR / "phase1_ltr_samples.csv"
SCHEMA_JSON = PHASE1_DIR / "phase1_sample_schema.json"

VALIDATION_CSV = OUT_DIR / "phase1c_validation_selection.csv"
TEST_CSV = OUT_DIR / "phase1c_independent_test_comparison.csv"
TOPK_CSV = OUT_DIR / "phase1c_topk_preservation_diagnostics.csv"
GATE_JSON = OUT_DIR / "phase1c_gate_summary.json"
DIAGNOSIS_JSON = OUT_DIR / "phase1c_diagnosis_summary.json"
REPORT_DOC = DOC_DIR / "PHASE1C_FINAL_LTR_REPAIR_EXECUTION_REPORT_CN.md"

FORBIDDEN_FEATURES = {
    "institutional_net_buy",
    "margin_balance",
    "short_balance",
    "monthly_revenue_yoy_mom",
    "valuation_PER_PBR",
}

QLIB_FEATURES = [
    "qlib_score_raw",
    "qlib_rank",
    "qlib_score_percentile_by_date",
    "qlib_score_zscore_by_date",
    "rank_change_1d",
    "rank_change_3d",
    "rank_change_5d",
    "top10_flag",
    "top30_flag",
    "top50_flag",
    "top30_streak",
    "top50_streak",
]


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    label_col: str
    feature_mode: str
    num_leaves: int
    learning_rate: float
    n_estimators: int


@dataclass(frozen=True)
class RerankSpec:
    candidate_id: str
    model_id: str
    blend_alpha: float
    preserve_scope: str


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_JSON.read_text(encoding="utf-8"))


def load_sample(schema: dict[str, Any]) -> pd.DataFrame:
    input_features = list(schema["input_columns"])
    if "trend_score" in input_features:
        raise RuntimeError("trend_score is excluded by Phase1C authorization.")
    forbidden = sorted(set(input_features) & FORBIDDEN_FEATURES)
    if forbidden:
        raise RuntimeError(f"Forbidden features found in input list: {forbidden}")

    df = pd.read_csv(SAMPLE_CSV, parse_dates=["date"])
    df = df[df["sample_complete"] == True].copy()  # noqa: E712
    medians = df[df["split"] == "train"][input_features].replace([np.inf, -np.inf], np.nan).median(numeric_only=True).fillna(0.0)
    df[input_features] = df[input_features].replace([np.inf, -np.inf], np.nan).fillna(medians).fillna(0.0)
    df["relevance_10d_top_heavy"] = top_heavy_label(df["future_excess_return_rank_10d"])
    df["relevance_20d_top_heavy"] = top_heavy_label(df["future_excess_return_rank_20d"])
    df["relevance_10d_bucket"] = bucket_label(df["future_excess_return_rank_10d"])
    return add_baseline_scores(df)


def bucket_label(rank: pd.Series) -> pd.Series:
    return np.floor(rank.fillna(0).clip(0, 0.999999) * 5).astype(int).clip(0, 4)


def top_heavy_label(rank: pd.Series) -> pd.Series:
    r = rank.fillna(0)
    return np.select(
        [r >= 0.90, r >= 0.80, r >= 0.70, r >= 0.50],
        [4, 3, 2, 1],
        default=0,
    ).astype(int)


def add_baseline_scores(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["adaptive_score_baseline"] = (
        0.70 * out["qlib_score_zscore_by_date"]
        + 0.15 * out["ret20"].fillna(0.0)
        - 0.10 * out["volatility20"].fillna(0.0)
        + 0.05 * out["TWII_ret20"].fillna(0.0)
    )
    out["confirmed_exit_baseline"] = (
        out["qlib_score_zscore_by_date"]
        - 0.25 * (out["market_drawdown60"].fillna(0.0) < -0.08).astype(float)
        - 0.10 * out["volatility20"].fillna(0.0)
    )
    return out


def feature_columns(schema: dict[str, Any], mode: str) -> list[str]:
    input_features = list(schema["input_columns"])
    if mode == "qlib_only":
        return [feature for feature in QLIB_FEATURES if feature in input_features]
    if mode == "all_whitelist_without_trend_score":
        return input_features
    raise ValueError(f"Unsupported feature mode: {mode}")


def group_sizes(df: pd.DataFrame) -> list[int]:
    return df.sort_values(["date", "instrument"]).groupby("date").size().astype(int).tolist()


def fit_model(df: pd.DataFrame, schema: dict[str, Any], spec: ModelSpec) -> pd.Series:
    features = feature_columns(schema, spec.feature_mode)
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


def apply_rerank(df: pd.DataFrame, model_score_col: str, spec: RerankSpec) -> pd.Series:
    working = df[["date", "instrument", "qlib_score_raw", "qlib_rank", model_score_col]].copy()
    working["qlib_pct"] = pct_rank_by_date(working, "qlib_score_raw")
    working["model_pct"] = pct_rank_by_date(working, model_score_col)
    score = spec.blend_alpha * working["qlib_pct"] + (1.0 - spec.blend_alpha) * working["model_pct"]
    if spec.preserve_scope == "top50_only":
        score = score.where(working["qlib_rank"] <= 50, -1.0 + working["qlib_pct"] * 0.000001)
    elif spec.preserve_scope == "top30_plus_top50":
        score = score.where(working["qlib_rank"] <= 50, -1.0 + working["qlib_pct"] * 0.000001)
        score = score + (working["qlib_rank"] <= 30).astype(float) * 0.05
    elif spec.preserve_scope != "full_universe_blend":
        raise ValueError(f"Unsupported preserve_scope: {spec.preserve_scope}")
    return score


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
    return pd.concat([g.nlargest(min(k, g.shape[0]), score_col) for _, g in df.groupby("date")], ignore_index=True)


def evaluate(df: pd.DataFrame, score_col: str, method: str, split: str) -> dict[str, Any]:
    sub = df[df["split"] == split]
    rank_ic, dates = spearman_by_date(sub, score_col)
    row: dict[str, Any] = {
        "split": split,
        "method": method,
        "score_column": score_col,
        "date_count": int(dates),
        "row_count": int(sub.shape[0]),
        "rank_ic_10d": rank_ic,
        "ndcg_at_10": ndcg_by_date(sub, score_col, 10),
        "ndcg_at_30": ndcg_by_date(sub, score_col, 30),
        "ndcg_at_50": ndcg_by_date(sub, score_col, 50),
    }
    for k in (10, 30, 50):
        selected = topk(sub, score_col, k)
        row[f"top{k}_future_excess_rank_10d"] = float(selected["future_excess_return_rank_10d"].mean())
        row[f"top{k}_mean_relevance_10d"] = float(selected["relevance_10d_bucket"].mean())
    return row


def topk_diagnostics(df: pd.DataFrame, candidate_col: str) -> pd.DataFrame:
    rows = []
    test = df[df["split"] == "independent_test"]
    for k in (10, 30, 50):
        qlib_sets = {day: set(topk(group, "qlib_score_raw", k)["instrument"]) for day, group in test.groupby("date")}
        cand_sets = {day: set(topk(group, candidate_col, k)["instrument"]) for day, group in test.groupby("date")}
        overlaps = []
        for day in sorted(qlib_sets):
            union = qlib_sets[day] | cand_sets[day]
            overlaps.append(len(qlib_sets[day] & cand_sets[day]) / len(union) if union else 0.0)
        rows.append({"metric": f"top{k}_candidate_vs_qlib_jaccard", "value": float(np.mean(overlaps)), "date_count": len(overlaps)})
    return pd.DataFrame(rows)


def model_specs() -> list[ModelSpec]:
    return [
        ModelSpec("head10_all_l15", "relevance_10d_top_heavy", "all_whitelist_without_trend_score", 15, 0.03, 100),
        ModelSpec("head10_all_l31", "relevance_10d_top_heavy", "all_whitelist_without_trend_score", 31, 0.03, 120),
        ModelSpec("head20_all_l15", "relevance_20d_top_heavy", "all_whitelist_without_trend_score", 15, 0.03, 100),
        ModelSpec("head20_all_l31", "relevance_20d_top_heavy", "all_whitelist_without_trend_score", 31, 0.03, 120),
        ModelSpec("head10_qlib_l15", "relevance_10d_top_heavy", "qlib_only", 15, 0.03, 100),
        ModelSpec("bucket10_qlib_l15", "relevance_10d_bucket", "qlib_only", 15, 0.03, 100),
    ]


def rerank_specs(model_id: str) -> list[RerankSpec]:
    specs = []
    for alpha in (0.70, 0.85, 0.93, 0.97):
        for scope in ("top50_only", "top30_plus_top50", "full_universe_blend"):
            specs.append(RerankSpec(f"{model_id}_alpha{alpha}_{scope}", model_id, alpha, scope))
    return specs


def build_candidates(df: pd.DataFrame, schema: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, str]]:
    scored = df.copy()
    model_score_cols: dict[str, str] = {}
    for spec in model_specs():
        col = f"model_score_{spec.model_id}"
        scored[col] = fit_model(scored, schema, spec)
        model_score_cols[spec.model_id] = col
        for rerank in rerank_specs(spec.model_id):
            scored[f"score_{rerank.candidate_id}"] = apply_rerank(scored, col, rerank)
    return scored, model_score_cols


def validation_selection(scored: pd.DataFrame, model_score_cols: dict[str, str]) -> pd.DataFrame:
    rows = []
    for spec in model_specs():
        for rerank in rerank_specs(spec.model_id):
            score_col = f"score_{rerank.candidate_id}"
            row = evaluate(scored, score_col, rerank.candidate_id, "validation")
            row.update(
                {
                    "candidate_id": rerank.candidate_id,
                    "model_id": rerank.model_id,
                    "blend_alpha": rerank.blend_alpha,
                    "preserve_scope": rerank.preserve_scope,
                    "selection_score": row["ndcg_at_30"] + 0.05 * row["top30_future_excess_rank_10d"] + 0.05 * row["rank_ic_10d"],
                }
            )
            rows.append(row)
    return pd.DataFrame(rows).sort_values(["selection_score", "ndcg_at_30", "top30_future_excess_rank_10d"], ascending=False)


def final_comparison(scored: pd.DataFrame, best_candidate: str) -> pd.DataFrame:
    rows = []
    methods = {
        f"phase1c_conservative_{best_candidate}": f"score_{best_candidate}",
        "rank_rotate_top30": "qlib_score_raw",
        "rank_rotate_top50": "qlib_score_raw",
        "rank_rotate_top50_adaptive_score": "adaptive_score_baseline",
        "confirmed_exit": "confirmed_exit_baseline",
    }
    for split in ("validation", "independent_test"):
        for method, col in methods.items():
            rows.append(evaluate(scored, col, method, split))
    return pd.DataFrame(rows)


def segment_check(scored: pd.DataFrame, best_col: str) -> bool:
    test = scored[scored["split"] == "independent_test"]
    wins = 0
    checks = 0
    for _, group in test.groupby("year"):
        if group["date"].nunique() < 20:
            continue
        cand = evaluate(group.assign(split="independent_test"), best_col, "candidate", "independent_test")
        qlib = evaluate(group.assign(split="independent_test"), "qlib_score_raw", "qlib", "independent_test")
        wins += int(cand["ndcg_at_30"] >= qlib["ndcg_at_30"])
        checks += 1
    return checks >= 2 and wins >= 2


def decide_gate(comparison: pd.DataFrame, scored: pd.DataFrame, best_candidate: str) -> tuple[str, str, dict[str, bool]]:
    cand = comparison[
        (comparison["split"] == "independent_test")
        & (comparison["method"] == f"phase1c_conservative_{best_candidate}")
    ].iloc[0]
    qlib = comparison[
        (comparison["split"] == "independent_test")
        & (comparison["method"] == "rank_rotate_top50")
    ].iloc[0]
    conditions = {
        "rank_ic_higher_than_qlib": bool(cand["rank_ic_10d"] > qlib["rank_ic_10d"]),
        "ndcg_at_30_not_lower_than_qlib": bool(cand["ndcg_at_30"] >= qlib["ndcg_at_30"]),
        "top30_future_excess_rank_not_lower_than_qlib": bool(cand["top30_future_excess_rank_10d"] >= qlib["top30_future_excess_rank_10d"]),
        "not_single_year_only": segment_check(scored, f"score_{best_candidate}"),
    }
    if all(conditions.values()):
        return "request_phase2_regime_gating_work", "Phase1C conservative rerank cleared all user-approved final gate conditions.", conditions
    return "stop_ltr_mainline_insufficient_evidence", "Final Phase1C repair did not clear required TopK/NDCG evidence; stop LTR reranker mainline.", conditions


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_report(now: str, gate: dict[str, Any], comparison: pd.DataFrame, validation: pd.DataFrame, topk_diag: pd.DataFrame) -> None:
    test_text = comparison[comparison["split"] == "independent_test"].to_string(index=False)
    val_text = validation.head(10).to_string(index=False)
    diag_text = topk_diag.to_string(index=False)
    REPORT_DOC.write_text(
        f"""# Phase 1C 执行报告：最后一轮保守 LTR 修复

生成时间：{now}

## 1. 本轮目标

根据用户选择的最后一轮 Phase1C，只在 Stage 2 内尝试更贴近头部排序的 label 和 qlib-preserving rerank；若仍不过 gate，则停止 LTR reranker 主线。

## 2. 实际完成内容

- 新增脚本：`scripts/diagnose_tw_ltr_phase1c_final_repair.py`。
- 复用 Phase1 样本，不新增数据源。
- 继续排除 `trend_score`，不新增白名单外特征。
- 尝试 top-heavy label、qlib-only/all-whitelist 模型，以及 top50 内重排 / qlib blend / top30 保护策略。
- 只用 validation 选择候选；independent_test 只做最终检验。

## 3. 新增产物

- `data_tw/experiments/ltr_rerank_regime_turnover/phase1c_final_ltr_repair/phase1c_validation_selection.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1c_final_ltr_repair/phase1c_independent_test_comparison.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1c_final_ltr_repair/phase1c_topk_preservation_diagnostics.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1c_final_ltr_repair/phase1c_gate_summary.json`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1c_final_ltr_repair/phase1c_diagnosis_summary.json`
- `docs/tw_ltr_rerank_regime_turnover/PHASE1C_FINAL_LTR_REPAIR_EXECUTION_REPORT_CN.md`

## 4. validation 选择

```text
{val_text}
```

## 5. independent_test 最终对照

```text
{test_text}
```

## 6. TopK 保守性诊断

```text
{diag_text}
```

## 7. Gate 结论

- 推荐 gate：`{gate['recommended_gate']}`。
- 原因：{gate['gate_reason']}
- 条件：`{gate['required_conditions']}`。

## 8. 风险 / 异常 / 未解决问题

- 这是用户授权的最后一轮 LTR 修复。
- 若 gate 为 `stop_ltr_mainline_insufficient_evidence`，执行者不再继续扩大 LTR 搜索，不进入 Phase2。
- 本轮没有真实组合 replay，不能解释为组合净值、换手、动作次数、成本或可执行动作。

## 9. 禁止事项遵守情况

本轮未新增白名单外特征，未引入 `trend_score`，未引入 forbidden features，未联网，未 provider refresh/publish，未 accepted latest switching，未改 frontend / API / monitor / database，未做 regime gating 动作实现，未做 turnover portfolio layer，未接 broker / quick-trade / orders / target position / target weight，未输出买入、卖出、持有、仓位、收益承诺、上涨概率或胜率语义。
""",
        encoding="utf-8",
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now = utc_now()
    schema = load_schema()
    df = load_sample(schema)
    scored, model_score_cols = build_candidates(df, schema)
    validation = validation_selection(scored, model_score_cols)
    validation.to_csv(VALIDATION_CSV, index=False)
    best = str(validation.iloc[0]["candidate_id"])
    comparison = final_comparison(scored, best)
    comparison.to_csv(TEST_CSV, index=False)
    topk_diag = topk_diagnostics(scored, f"score_{best}")
    topk_diag.to_csv(TOPK_CSV, index=False)
    recommended_gate, gate_reason, conditions = decide_gate(comparison, scored, best)
    gate = {
        "phase": "phase1c_final_ltr_repair",
        "created_at": now,
        "research_only": True,
        "final_ltr_repair_round": True,
        "no_new_data_source": True,
        "no_network": True,
        "no_provider_refresh_or_publish": True,
        "no_accepted_latest_switching": True,
        "no_frontend_or_api": True,
        "no_monitor_database_or_trading": True,
        "trend_score_excluded": True,
        "forbidden_feature_hits": [],
        "best_candidate": best,
        "recommended_gate": recommended_gate,
        "gate_reason": gate_reason,
        "required_conditions": conditions,
    }
    diagnosis = {
        "created_at": now,
        "summary": "Final conservative LTR repair using head-focused labels and qlib-preserving rerank.",
        "best_candidate": best,
        "recommended_gate": recommended_gate,
        "gate_reason": gate_reason,
    }
    write_json(GATE_JSON, gate)
    write_json(DIAGNOSIS_JSON, diagnosis)
    write_report(now, gate, comparison, validation, topk_diag)
    print(json.dumps({"ok": True, "recommended_gate": recommended_gate, "gate_reason": gate_reason, "report": rel(REPORT_DOC)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
