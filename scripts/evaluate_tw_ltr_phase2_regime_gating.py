#!/usr/bin/env python3
"""Phase 2 offline regime-aware gating evaluation.

Only uses the Phase 1 sample, the frozen Phase 1C qlib-preserving LTR rerank
logic, and the five regime whitelist fields. It does not create actions, run a
portfolio/turnover layer, touch frontend/API/provider/monitor/trading paths, or
add data sources/features.
"""
from __future__ import annotations

import json
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
OUT_DIR = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase2_regime_gating"
DOC_DIR = ROOT / "docs/tw_ltr_rerank_regime_turnover"

SAMPLE_CSV = PHASE1_DIR / "phase1_ltr_samples.csv"
SCHEMA_JSON = PHASE1_DIR / "phase1_sample_schema.json"

REGIME_DEF_JSON = OUT_DIR / "phase2_regime_definition.json"
REGIME_DISTRIBUTION_CSV = OUT_DIR / "phase2_regime_distribution.csv"
REGIME_METRIC_CSV = OUT_DIR / "phase2_regime_metric_by_state.csv"
THRESHOLD_GRID_CSV = OUT_DIR / "phase2_gating_threshold_grid.csv"
COMPARISON_CSV = OUT_DIR / "phase2_baseline_vs_regime_gated_comparison.csv"
GATE_JSON = OUT_DIR / "phase2_gate_summary.json"
REPORT_DOC = DOC_DIR / "PHASE2_REGIME_GATING_EXECUTION_REPORT_CN.md"

REGIME_FEATURES = [
    "TWII_ret20",
    "TWII_ret60",
    "market_drawdown60",
    "market_volatility20",
    "market_breadth20",
]

FORBIDDEN_FEATURES = {
    "institutional_net_buy",
    "margin_balance",
    "short_balance",
    "monthly_revenue_yoy_mom",
    "valuation_PER_PBR",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_JSON.read_text(encoding="utf-8"))


def top_heavy_label(rank: pd.Series) -> pd.Series:
    r = rank.fillna(0)
    return np.select([r >= 0.90, r >= 0.80, r >= 0.70, r >= 0.50], [4, 3, 2, 1], default=0).astype(int)


def bucket_label(rank: pd.Series) -> pd.Series:
    return np.floor(rank.fillna(0).clip(0, 0.999999) * 5).astype(int).clip(0, 4)


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


def load_sample(schema: dict[str, Any]) -> pd.DataFrame:
    input_features = list(schema["input_columns"])
    if "trend_score" in input_features:
        raise RuntimeError("trend_score is not allowed in Phase2.")
    forbidden_hits = sorted(set(input_features) & FORBIDDEN_FEATURES)
    if forbidden_hits:
        raise RuntimeError(f"Forbidden input features found: {forbidden_hits}")
    missing_regime = [feature for feature in REGIME_FEATURES if feature not in input_features]
    if missing_regime:
        raise RuntimeError(f"Missing regime whitelist features in sample: {missing_regime}")

    df = pd.read_csv(SAMPLE_CSV, parse_dates=["date"])
    df = df[df["sample_complete"] == True].copy()  # noqa: E712
    medians = df[df["split"] == "train"][input_features].replace([np.inf, -np.inf], np.nan).median(numeric_only=True).fillna(0.0)
    df[input_features] = df[input_features].replace([np.inf, -np.inf], np.nan).fillna(medians).fillna(0.0)
    df["relevance_10d_bucket"] = bucket_label(df["future_excess_return_rank_10d"])
    df["relevance_10d_top_heavy"] = top_heavy_label(df["future_excess_return_rank_10d"])
    return add_baseline_scores(df)


def group_sizes(df: pd.DataFrame) -> list[int]:
    return df.sort_values(["date", "instrument"]).groupby("date").size().astype(int).tolist()


def fit_phase1c_model(df: pd.DataFrame, features: list[str]) -> pd.Series:
    train = df[df["split"] == "train"].sort_values(["date", "instrument"])
    valid = df[df["split"] == "validation"].sort_values(["date", "instrument"])
    model = lgb.LGBMRanker(
        objective="lambdarank",
        metric="ndcg",
        boosting_type="gbdt",
        n_estimators=120,
        learning_rate=0.03,
        num_leaves=31,
        min_child_samples=40,
        random_state=42,
        n_jobs=2,
        verbose=-1,
    )
    model.fit(
        train[features],
        train["relevance_10d_top_heavy"],
        group=group_sizes(train),
        eval_set=[(valid[features], valid["relevance_10d_top_heavy"])],
        eval_group=[group_sizes(valid)],
        eval_at=[10, 30, 50],
    )
    return pd.Series(model.predict(df[features]), index=df.index)


def pct_rank_by_date(df: pd.DataFrame, score_col: str) -> pd.Series:
    return df.groupby("date")[score_col].rank(pct=True)


def build_phase1c_score(df: pd.DataFrame, input_features: list[str]) -> pd.DataFrame:
    out = df.copy()
    out["phase1c_model_score"] = fit_phase1c_model(out, input_features)
    out["qlib_pct"] = pct_rank_by_date(out, "qlib_score_raw")
    out["phase1c_model_pct"] = pct_rank_by_date(out, "phase1c_model_score")
    blended = 0.70 * out["qlib_pct"] + 0.30 * out["phase1c_model_pct"]
    out["score_head10_all_l31_alpha0.7_top50_only"] = blended.where(
        out["qlib_rank"] <= 50,
        -1.0 + out["qlib_pct"] * 0.000001,
    )
    return out


def assign_regime(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    risk = (
        (out["market_drawdown60"] <= -0.12)
        | (out["TWII_ret60"] <= -0.08)
        | (out["market_breadth20"] < 0.35)
        | ((out["market_volatility20"] >= 0.024) & (out["TWII_ret20"] < 0))
    )
    caution = (
        (out["market_drawdown60"] <= -0.06)
        | (out["TWII_ret20"] <= -0.03)
        | (out["TWII_ret60"] <= 0)
        | (out["market_breadth20"] < 0.45)
        | (out["market_volatility20"] >= 0.018)
    )
    out["phase2_regime"] = np.select([risk, caution], ["risk_off", "caution"], default="normal")
    return out


def apply_scope(score: pd.Series, df: pd.DataFrame, scope: int) -> pd.Series:
    return score.where(df["qlib_rank"] <= scope, -1.0 + df["qlib_pct"] * 0.000001)


def apply_regime_gate(df: pd.DataFrame, caution_scope: int, risk_scope: int, risk_penalty: float) -> pd.Series:
    score = df["score_head10_all_l31_alpha0.7_top50_only"].copy()
    caution_mask = df["phase2_regime"] == "caution"
    risk_mask = df["phase2_regime"] == "risk_off"
    score.loc[caution_mask] = apply_scope(score.loc[caution_mask], df.loc[caution_mask], caution_scope)
    score.loc[risk_mask] = apply_scope(score.loc[risk_mask], df.loc[risk_mask], risk_scope) - risk_penalty
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


def evaluate(df: pd.DataFrame, score_col: str, method: str, split: str, regime: str | None = None) -> dict[str, Any]:
    sub = df[df["split"] == split]
    if regime is not None:
        sub = sub[sub["phase2_regime"] == regime]
    rank_ic, dates = spearman_by_date(sub, score_col)
    row: dict[str, Any] = {
        "split": split,
        "regime": regime or "all",
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
        selected = topk(sub, score_col, k) if not sub.empty else pd.DataFrame()
        row[f"top{k}_future_excess_rank_10d"] = float(selected["future_excess_return_rank_10d"].mean()) if not selected.empty else 0.0
        row[f"top{k}_mean_relevance_10d"] = float(selected["relevance_10d_bucket"].mean()) if not selected.empty else 0.0
        row[f"top{k}_median_qlib_rank"] = float(selected["qlib_rank"].median()) if not selected.empty else 0.0
    return row


def distribution(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split in ("train", "validation", "independent_test"):
        for regime, group in df[df["split"] == split].groupby("phase2_regime"):
            rows.append(
                {
                    "split": split,
                    "regime": regime,
                    "date_count": int(group["date"].nunique()),
                    "row_count": int(group.shape[0]),
                    "mean_TWII_ret20": float(group["TWII_ret20"].mean()),
                    "mean_TWII_ret60": float(group["TWII_ret60"].mean()),
                    "mean_market_drawdown60": float(group["market_drawdown60"].mean()),
                    "mean_market_volatility20": float(group["market_volatility20"].mean()),
                    "mean_market_breadth20": float(group["market_breadth20"].mean()),
                }
            )
    return pd.DataFrame(rows)


def baseline_rows(df: pd.DataFrame) -> pd.DataFrame:
    methods = {
        "qlib_rank_rotate_top50": "qlib_score_raw",
        "phase1c_qlib_preserving_ltr": "score_head10_all_l31_alpha0.7_top50_only",
        "rank_rotate_top50_adaptive_score": "adaptive_score_baseline",
        "confirmed_exit": "confirmed_exit_baseline",
    }
    rows = []
    for split in ("validation", "independent_test"):
        for method, col in methods.items():
            rows.append(evaluate(df, col, method, split))
    return pd.DataFrame(rows)


def grid_search(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for caution_scope in (50, 40, 30):
        for risk_scope in (50, 40, 30, 20):
            for risk_penalty in (0.0, 0.02, 0.05):
                col = f"gate_c{caution_scope}_r{risk_scope}_p{str(risk_penalty).replace('.', '')}"
                df[col] = apply_regime_gate(df, caution_scope, risk_scope, risk_penalty)
                for split in ("validation", "independent_test"):
                    row = evaluate(df, col, f"regime_gate_c{caution_scope}_r{risk_scope}_p{risk_penalty}", split)
                    row.update(
                        {
                            "caution_scope": caution_scope,
                            "risk_scope": risk_scope,
                            "risk_penalty": risk_penalty,
                            "selection_score": row["ndcg_at_30"] + 0.05 * row["top30_future_excess_rank_10d"] + 0.03 * row["rank_ic_10d"],
                        }
                    )
                    rows.append(row)
    return pd.DataFrame(rows)


def choose_grid(grid: pd.DataFrame) -> pd.Series:
    val = grid[grid["split"] == "validation"].copy()
    base_ndcg = float(val[val["method"].str.contains("c50_r50_p0.0", regex=False)]["ndcg_at_30"].max()) if not val.empty else 0.0
    val["passes_phase1c_core"] = val["ndcg_at_30"] >= base_ndcg
    selected = val.sort_values(["passes_phase1c_core", "selection_score", "top30_future_excess_rank_10d"], ascending=False).iloc[0]
    return selected


def year_results(df: pd.DataFrame, score_col: str, method: str) -> pd.DataFrame:
    rows = []
    test = df[df["split"] == "independent_test"]
    for year, group in test.groupby("year"):
        if group["date"].nunique() < 10:
            continue
        row = evaluate(group.assign(split="independent_test"), score_col, method, "independent_test")
        row["year"] = int(year)
        rows.append(row)
    return pd.DataFrame(rows)


def conservative_effect(df: pd.DataFrame, gated_col: str, selected_method: str) -> dict[str, Any]:
    rows = []
    has_non_noop_gate = selected_method != "regime_gate_c50_r50_p0.0"
    for regime in ("caution", "risk_off"):
        test = df[(df["split"] == "independent_test") & (df["phase2_regime"] == regime)]
        if test.empty:
            rows.append({"regime": regime, "has_rows": False})
            continue
        base_top30 = topk(test, "score_head10_all_l31_alpha0.7_top50_only", 30)
        gated_top30 = topk(test, gated_col, 30)
        rows.append(
            {
                "regime": regime,
                "has_rows": True,
                "date_count": int(test["date"].nunique()),
                "base_top30_median_qlib_rank": float(base_top30["qlib_rank"].median()),
                "gated_top30_median_qlib_rank": float(gated_top30["qlib_rank"].median()),
                "base_top30_future_excess_rank_10d": float(base_top30["future_excess_return_rank_10d"].mean()),
                "gated_top30_future_excess_rank_10d": float(gated_top30["future_excess_return_rank_10d"].mean()),
                "strictly_more_conservative_top30": bool(gated_top30["qlib_rank"].median() < base_top30["qlib_rank"].median()),
            }
        )
    passed = has_non_noop_gate and any(row.get("has_rows") and row["strictly_more_conservative_top30"] for row in rows)
    return {"passed": bool(passed), "has_non_noop_gate": bool(has_non_noop_gate), "details": rows}


def decide_gate(df: pd.DataFrame, comparison: pd.DataFrame, selected_method: str, selected_col: str) -> tuple[str, str, dict[str, Any]]:
    test = comparison[comparison["split"] == "independent_test"]
    gated = test[test["method"] == selected_method].iloc[0]
    phase1c = test[test["method"] == "phase1c_qlib_preserving_ltr"].iloc[0]
    core_ok = (
        gated["ndcg_at_30"] >= phase1c["ndcg_at_30"]
        and gated["top30_future_excess_rank_10d"] >= phase1c["top30_future_excess_rank_10d"]
        and gated["ndcg_at_10"] >= phase1c["ndcg_at_10"]
    )
    effect = conservative_effect(df, selected_col, selected_method)
    yearly = year_results(df, selected_col, selected_method)
    phase1c_yearly = year_results(df, "score_head10_all_l31_alpha0.7_top50_only", "phase1c")
    if not yearly.empty and not phase1c_yearly.empty:
        merged = yearly[["year", "ndcg_at_30"]].merge(
            phase1c_yearly[["year", "ndcg_at_30"]],
            on="year",
            suffixes=("_gated", "_phase1c"),
        )
        year_ok = int((merged["ndcg_at_30_gated"] >= merged["ndcg_at_30_phase1c"]).sum()) >= 1 and len(merged) >= 1
    else:
        year_ok = False
    conditions = {
        "core_topk_not_lower_than_phase1c": bool(core_ok),
        "caution_or_risk_off_conservative_effect": bool(effect["passed"]),
        "not_single_year_only": bool(year_ok),
        "conservative_effect": effect,
    }
    if all([conditions["core_topk_not_lower_than_phase1c"], conditions["caution_or_risk_off_conservative_effect"], conditions["not_single_year_only"]]):
        return "request_phase3_turnover_layer_work", "Regime-gated rerank preserved Phase1C TopK quality and showed conservative filtering in non-normal regimes.", conditions
    if conditions["caution_or_risk_off_conservative_effect"]:
        return "phase2_regime_gating_needs_repair", "Regime gating has partial evidence but did not clear all Phase2 gate conditions.", conditions
    return "stop_regime_gating_insufficient_evidence", "Regime gating did not provide incremental explanation or stability over Phase1C.", conditions


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_report(now: str, gate: dict[str, Any], comparison: pd.DataFrame, by_state: pd.DataFrame, grid: pd.DataFrame, distribution_df: pd.DataFrame, yearly: pd.DataFrame) -> None:
    test_text = comparison[comparison["split"] == "independent_test"].to_string(index=False)
    state_text = by_state.to_string(index=False)
    grid_text = grid[grid["split"] == "validation"].sort_values("selection_score", ascending=False).head(10).to_string(index=False)
    dist_text = distribution_df.to_string(index=False)
    yearly_text = yearly.to_string(index=False)
    REPORT_DOC.write_text(
        f"""# Phase 2 执行报告：Regime-aware Gating 最小离线评估

生成时间：{now}

## 1. 本轮目标

只做 Stage 3 regime-aware gating 的最小离线实现与评估，验证 `qlib baseline + qlib-preserving LTR rerank` 在 normal / caution / risk_off 下是否需要不同保守阈值。

## 2. 实际完成内容

- 新增只读离线脚本：`scripts/evaluate_tw_ltr_phase2_regime_gating.py`。
- 复用 Phase1 样本。
- 复现 Phase1C 冻结的 `qlib-preserving LTR rerank`：`score_head10_all_l31_alpha0.7_top50_only`。
- 仅使用 5 个 regime 白名单字段生成 3 态。
- 只做阈值 / 过滤 / 候选保守程度评估；未生成真实动作指令，未做 turnover layer。

## 3. 改动文件清单

- `scripts/evaluate_tw_ltr_phase2_regime_gating.py`
- `docs/tw_ltr_rerank_regime_turnover/PHASE2_REGIME_GATING_EXECUTION_REPORT_CN.md`

## 4. 新增产物清单

- `data_tw/experiments/ltr_rerank_regime_turnover/phase2_regime_gating/phase2_regime_definition.json`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase2_regime_gating/phase2_regime_distribution.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase2_regime_gating/phase2_regime_metric_by_state.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase2_regime_gating/phase2_gating_threshold_grid.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase2_regime_gating/phase2_baseline_vs_regime_gated_comparison.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase2_regime_gating/phase2_gate_summary.json`

## 5. Regime 分布

```text
{dist_text}
```

## 6. Regime 分状态指标

```text
{state_text}
```

## 7. validation 阈值网格 Top10

```text
{grid_text}
```

## 8. independent_test 最终对照

```text
{test_text}
```

## 9. independent_test 分年度结果

```text
{yearly_text}
```

## 10. Gate 结论

- 推荐 gate：`{gate['recommended_gate']}`。
- 原因：{gate['gate_reason']}
- 条件：`{gate['required_conditions']}`。

## 11. 风险 / 异常 / 未解决问题

- 本轮不是 turnover layer，不报告组合净值、换手、动作次数或成本。
- Regime 不是买卖信号、收益预测或概率预测，只是离线研究排序的保守过滤状态。
- 若 gate 未通过，不得强行进入 Phase3。
- validation 选择出的最优配置为 `{gate['selected_validation_method']}`，这是 Phase1C 等价的 no-op gating；因此不能把它解释为已经证明需要不同 regime 阈值。

## 12. 需要审查者重点检查的点

- Regime 定义是否只使用主文档 5 个白名单字段。
- Phase1C score 是否保持 `qlib-preserving LTR rerank` 语义。
- 阈值选择是否只基于 validation。
- 是否存在真实动作、前端/API/provider/monitor/trading 越界。

## 13. 禁止事项遵守情况

本轮未新增数据源，未新增白名单外特征，未引入 `trend_score` 或 forbidden features，未联网，未 provider refresh/publish，未 accepted latest switching，未改 frontend / API / monitor / database，未做 turnover portfolio layer，未接 broker / quick-trade / orders / target position / target weight，未输出买入、卖出、持有、仓位、收益承诺、上涨概率或胜率语义。
""",
        encoding="utf-8",
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now = utc_now()
    schema = load_schema()
    input_features = list(schema["input_columns"])
    df = load_sample(schema)
    df = build_phase1c_score(df, input_features)
    df = assign_regime(df)

    regime_def = {
        "created_at": now,
        "regime_features": REGIME_FEATURES,
        "states": ["normal", "caution", "risk_off"],
        "risk_off_rule": "market_drawdown60 <= -0.12 OR TWII_ret60 <= -0.08 OR market_breadth20 < 0.35 OR (market_volatility20 >= 0.024 AND TWII_ret20 < 0)",
        "caution_rule": "not risk_off AND (market_drawdown60 <= -0.06 OR TWII_ret20 <= -0.03 OR TWII_ret60 <= 0 OR market_breadth20 < 0.45 OR market_volatility20 >= 0.018)",
        "normal_rule": "otherwise",
        "score_semantics": "qlib-preserving LTR rerank; regime gating is offline conservative filtering, not an action signal",
    }
    write_json(REGIME_DEF_JSON, regime_def)

    dist = distribution(df)
    dist.to_csv(REGIME_DISTRIBUTION_CSV, index=False)

    base = baseline_rows(df)
    grid = grid_search(df)
    grid.to_csv(THRESHOLD_GRID_CSV, index=False)
    selected = choose_grid(grid)
    selected_col = str(selected["score_column"])
    selected_method = str(selected["method"])

    comparison_rows = base.to_dict("records")
    for split in ("validation", "independent_test"):
        comparison_rows.append(evaluate(df, selected_col, selected_method, split))
    comparison = pd.DataFrame(comparison_rows)
    comparison.to_csv(COMPARISON_CSV, index=False)

    state_rows = []
    for regime in ("normal", "caution", "risk_off"):
        for method, col in {
            "qlib_rank_rotate_top50": "qlib_score_raw",
            "phase1c_qlib_preserving_ltr": "score_head10_all_l31_alpha0.7_top50_only",
            selected_method: selected_col,
        }.items():
            state_rows.append(evaluate(df, col, method, "independent_test", regime))
    by_state = pd.DataFrame(state_rows)
    by_state.to_csv(REGIME_METRIC_CSV, index=False)

    yearly = pd.concat(
        [
            year_results(df, "qlib_score_raw", "qlib_rank_rotate_top50"),
            year_results(df, "score_head10_all_l31_alpha0.7_top50_only", "phase1c_qlib_preserving_ltr"),
            year_results(df, selected_col, selected_method),
        ],
        ignore_index=True,
    )

    recommended_gate, gate_reason, conditions = decide_gate(df, comparison, selected_method, selected_col)
    gate = {
        "phase": "phase2_regime_gating",
        "created_at": now,
        "research_only": True,
        "no_new_data_source": True,
        "no_network": True,
        "no_provider_refresh_or_publish": True,
        "no_accepted_latest_switching": True,
        "no_frontend_or_api": True,
        "no_monitor_database_or_trading": True,
        "no_turnover_layer": True,
        "regime_features": REGIME_FEATURES,
        "phase1c_score": "score_head10_all_l31_alpha0.7_top50_only",
        "selected_validation_method": selected_method,
        "selected_score_column": selected_col,
        "recommended_gate": recommended_gate,
        "gate_reason": gate_reason,
        "required_conditions": conditions,
        "artifacts": {
            "regime_definition": rel(REGIME_DEF_JSON),
            "regime_distribution": rel(REGIME_DISTRIBUTION_CSV),
            "regime_metric_by_state": rel(REGIME_METRIC_CSV),
            "threshold_grid": rel(THRESHOLD_GRID_CSV),
            "comparison": rel(COMPARISON_CSV),
            "gate_summary": rel(GATE_JSON),
            "report": rel(REPORT_DOC),
        },
    }
    write_json(GATE_JSON, gate)
    write_report(now, gate, comparison, by_state, grid, dist, yearly)
    print(json.dumps({"ok": True, "recommended_gate": recommended_gate, "gate_reason": gate_reason, "report": rel(REPORT_DOC)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
