#!/usr/bin/env python3
"""Phase 1B diagnosis and repair attempts for the TW LTR baseline.

This script reuses the Phase 1 local sample only. It does not add features,
read external data, tune on independent_test, run replay, or touch frontend/API,
provider, monitor, database, broker, quick-trade, or orders.
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
OUT_DIR = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase1b_ltr_repair"
DOC_DIR = ROOT / "docs/tw_ltr_rerank_regime_turnover"

SAMPLE_CSV = PHASE1_DIR / "phase1_ltr_samples.csv"
SCHEMA_JSON = PHASE1_DIR / "phase1_sample_schema.json"

DIAGNOSIS_JSON = OUT_DIR / "phase1b_diagnosis_summary.json"
FEATURE_ABLATION_CSV = OUT_DIR / "phase1b_feature_ablation_metrics.csv"
LABEL_WINDOW_CSV = OUT_DIR / "phase1b_label_window_metrics.csv"
MODEL_SELECTION_CSV = OUT_DIR / "phase1b_validation_model_selection.csv"
TEST_COMPARISON_CSV = OUT_DIR / "phase1b_independent_test_comparison.csv"
OVERLAP_STABILITY_CSV = OUT_DIR / "phase1b_topk_overlap_and_stability.csv"
GATE_JSON = OUT_DIR / "phase1b_gate_summary.json"
REPORT_DOC = DOC_DIR / "PHASE1B_LTR_REPAIR_EXECUTION_REPORT_CN.md"

BASELINE_SCORE_COLS = {
    "rank_rotate_top30": "qlib_score_raw",
    "rank_rotate_top50": "qlib_score_raw",
    "rank_rotate_top50_adaptive_score": "adaptive_score_baseline",
    "confirmed_exit": "confirmed_exit_baseline",
}

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
TECHNICAL_FEATURES = [
    "MA5",
    "MA10",
    "MA20",
    "MA60",
    "RSI14",
    "MACD",
    "Bollinger_position",
    "ret20",
    "volatility20",
    "volume_ratio20",
]
LIQUIDITY_FEATURES = [
    "avg_trading_value_20d",
    "volume_stability20",
    "missing_rate20",
    "suspension_proxy",
    "slippage_proxy",
]
MARKET_FEATURES = [
    "TWII_ret20",
    "TWII_ret60",
    "TWII_close_vs_MA60",
    "TWII_close_vs_MA120",
    "market_volatility20",
    "market_drawdown60",
    "market_breadth20",
]


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    label_window: str
    feature_group: str
    num_leaves: int
    learning_rate: float
    n_estimators: int


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_JSON.read_text(encoding="utf-8"))


def feature_sets(input_features: list[str]) -> dict[str, list[str]]:
    sets = {
        "qlib_only": QLIB_FEATURES,
        "qlib_plus_technical": QLIB_FEATURES + TECHNICAL_FEATURES,
        "qlib_plus_liquidity": QLIB_FEATURES + LIQUIDITY_FEATURES,
        "qlib_plus_market": QLIB_FEATURES + MARKET_FEATURES,
        "all_whitelist_without_trend_score": QLIB_FEATURES + TECHNICAL_FEATURES + LIQUIDITY_FEATURES + MARKET_FEATURES,
    }
    allowed = set(input_features)
    return {name: [feature for feature in features if feature in allowed] for name, features in sets.items()}


def add_baseline_scores(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["adaptive_score_baseline"] = (
        0.70 * result["qlib_score_zscore_by_date"]
        + 0.15 * result["ret20"].fillna(0.0)
        - 0.10 * result["volatility20"].fillna(0.0)
        + 0.05 * result["TWII_ret20"].fillna(0.0)
    )
    result["confirmed_exit_baseline"] = (
        result["qlib_score_zscore_by_date"]
        - 0.25 * (result["market_drawdown60"].fillna(0.0) < -0.08).astype(float)
        - 0.10 * result["volatility20"].fillna(0.0)
    )
    return result


def load_sample(schema: dict[str, Any]) -> pd.DataFrame:
    df = pd.read_csv(SAMPLE_CSV, parse_dates=["date"])
    df = df[df["sample_complete"] == True].copy()  # noqa: E712
    input_features = schema["input_columns"]
    train_medians = df[df["split"] == "train"][input_features].replace([np.inf, -np.inf], np.nan).median(numeric_only=True).fillna(0.0)
    df[input_features] = df[input_features].replace([np.inf, -np.inf], np.nan).fillna(train_medians).fillna(0.0)
    for window in ("5d", "10d", "20d"):
        rank_col = f"future_excess_return_rank_{window}"
        df[f"relevance_{window}"] = relevance_from_rank(df[rank_col])
    return add_baseline_scores(df)


def relevance_from_rank(rank: pd.Series) -> pd.Series:
    raw = np.floor(rank.fillna(0.0).clip(0.0, 0.999999) * 5.0)
    return raw.astype(int).clip(0, 4)


def group_sizes(df: pd.DataFrame) -> list[int]:
    return df.sort_values(["date", "instrument"]).groupby("date").size().astype(int).tolist()


def fit_ranker(train: pd.DataFrame, valid: pd.DataFrame, features: list[str], label_col: str, candidate: Candidate) -> lgb.LGBMRanker:
    model = lgb.LGBMRanker(
        objective="lambdarank",
        metric="ndcg",
        boosting_type="gbdt",
        n_estimators=candidate.n_estimators,
        learning_rate=candidate.learning_rate,
        num_leaves=candidate.num_leaves,
        min_child_samples=30,
        random_state=42,
        n_jobs=2,
        verbose=-1,
    )
    model.fit(
        train[features],
        train[label_col],
        group=group_sizes(train),
        eval_set=[(valid[features], valid[label_col])],
        eval_group=[group_sizes(valid)],
        eval_at=[10, 30, 50],
    )
    return model


def spearman_by_date(df: pd.DataFrame, score_col: str, label_col: str = "future_excess_return_rank_10d") -> tuple[float, int]:
    values = []
    for _, group in df.groupby("date"):
        if group[score_col].nunique() < 2 or group[label_col].nunique() < 2:
            continue
        corr = spearmanr(group[score_col], group[label_col]).correlation
        if pd.notna(corr):
            values.append(float(corr))
    return (float(np.mean(values)), len(values)) if values else (0.0, 0)


def ndcg_by_date(df: pd.DataFrame, score_col: str, k: int, label_col: str = "relevance_10d") -> float:
    values = []
    for _, group in df.groupby("date"):
        if group.shape[0] < 2:
            continue
        y_true = group[label_col].to_numpy(dtype=float).reshape(1, -1)
        y_score = group[score_col].to_numpy(dtype=float).reshape(1, -1)
        try:
            values.append(float(ndcg_score(y_true, y_score, k=min(k, group.shape[0]))))
        except Exception:
            continue
    return float(np.mean(values)) if values else 0.0


def topk_summary(df: pd.DataFrame, score_col: str, k: int) -> dict[str, float | int]:
    frames = [group.nlargest(min(k, group.shape[0]), score_col) for _, group in df.groupby("date")]
    top = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return {
        f"top{k}_rows": int(top.shape[0]),
        f"top{k}_future_excess_rank_10d": float(top["future_excess_return_rank_10d"].mean()) if not top.empty else 0.0,
        f"top{k}_mean_relevance_10d": float(top["relevance_10d"].mean()) if not top.empty else 0.0,
    }


def evaluate(df: pd.DataFrame, score_col: str, method: str, split: str) -> dict[str, Any]:
    sub = df[df["split"] == split]
    rank_ic, date_count = spearman_by_date(sub, score_col)
    row = {
        "split": split,
        "method": method,
        "score_column": score_col,
        "date_count": int(date_count),
        "row_count": int(sub.shape[0]),
        "rank_ic_10d": rank_ic,
        "ndcg_at_10": ndcg_by_date(sub, score_col, 10),
        "ndcg_at_30": ndcg_by_date(sub, score_col, 30),
        "ndcg_at_50": ndcg_by_date(sub, score_col, 50),
    }
    for k in (10, 30, 50):
        row.update(topk_summary(sub, score_col, k))
    return row


def train_and_score(df: pd.DataFrame, features: list[str], candidate: Candidate) -> pd.DataFrame:
    label_col = f"relevance_{candidate.label_window}"
    train = df[df["split"] == "train"].sort_values(["date", "instrument"])
    valid = df[df["split"] == "validation"].sort_values(["date", "instrument"])
    model = fit_ranker(train, valid, features, label_col, candidate)
    scored = df.copy()
    scored["repaired_ltr_score"] = model.predict(scored[features])
    return scored


def run_label_window_experiments(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    rows = []
    for window in ("5d", "10d", "20d"):
        candidate = Candidate(f"label_{window}_all_default", window, "all_whitelist_without_trend_score", 31, 0.05, 100)
        scored = train_and_score(df, features, candidate)
        for split in ("validation", "independent_test"):
            row = evaluate(scored, "repaired_ltr_score", candidate.candidate_id, split)
            row["label_window"] = window
            rows.append(row)
    return pd.DataFrame(rows)


def run_feature_ablation(df: pd.DataFrame, sets: dict[str, list[str]]) -> pd.DataFrame:
    rows = []
    for group_name, features in sets.items():
        candidate = Candidate(f"ablation_{group_name}", "10d", group_name, 31, 0.05, 100)
        scored = train_and_score(df, features, candidate)
        for split in ("validation", "independent_test"):
            row = evaluate(scored, "repaired_ltr_score", candidate.candidate_id, split)
            row["feature_group"] = group_name
            row["feature_count"] = len(features)
            rows.append(row)
    return pd.DataFrame(rows)


def validation_candidates(sets: dict[str, list[str]]) -> list[Candidate]:
    rows = []
    idx = 0
    for window in ("5d", "10d", "20d"):
        for group_name in sets:
            for num_leaves, learning_rate, n_estimators in [(15, 0.05, 80), (31, 0.03, 120)]:
                idx += 1
                rows.append(Candidate(f"candidate_{idx:02d}_{window}_{group_name}", window, group_name, num_leaves, learning_rate, n_estimators))
    return rows


def run_validation_selection(df: pd.DataFrame, sets: dict[str, list[str]]) -> tuple[pd.DataFrame, Candidate, pd.DataFrame]:
    rows = []
    scored_by_candidate: dict[str, pd.DataFrame] = {}
    for candidate in validation_candidates(sets):
        features = sets[candidate.feature_group]
        scored = train_and_score(df, features, candidate)
        scored_by_candidate[candidate.candidate_id] = scored
        row = evaluate(scored, "repaired_ltr_score", candidate.candidate_id, "validation")
        row.update(
            {
                "candidate_id": candidate.candidate_id,
                "label_window": candidate.label_window,
                "feature_group": candidate.feature_group,
                "feature_count": len(features),
                "num_leaves": candidate.num_leaves,
                "learning_rate": candidate.learning_rate,
                "n_estimators": candidate.n_estimators,
                "selection_score": row["ndcg_at_30"] + 0.10 * row["rank_ic_10d"],
            }
        )
        rows.append(row)
    table = pd.DataFrame(rows).sort_values(["selection_score", "ndcg_at_30", "rank_ic_10d"], ascending=False)
    best_id = str(table.iloc[0]["candidate_id"])
    best = next(candidate for candidate in validation_candidates(sets) if candidate.candidate_id == best_id)
    return table, best, scored_by_candidate[best_id]


def baseline_comparison(df: pd.DataFrame, repaired: pd.DataFrame, candidate: Candidate) -> pd.DataFrame:
    frames = []
    combined = repaired.copy()
    for split in ("validation", "independent_test"):
        frames.append(evaluate(combined, "repaired_ltr_score", f"repaired_ltr_{candidate.candidate_id}", split))
        for method, col in BASELINE_SCORE_COLS.items():
            frames.append(evaluate(combined, col, method, split))
    return pd.DataFrame(frames)


def topk_sets(df: pd.DataFrame, score_col: str, k: int) -> dict[pd.Timestamp, set[str]]:
    return {
        day: set(group.nlargest(min(k, group.shape[0]), score_col)["instrument"].astype(str).tolist())
        for day, group in df.groupby("date")
    }


def overlap_and_stability(df: pd.DataFrame, repaired_score_col: str = "repaired_ltr_score") -> pd.DataFrame:
    rows = []
    sub = df[df["split"] == "independent_test"].sort_values(["date", "instrument"])
    methods = {"repaired_ltr": repaired_score_col, "qlib": "qlib_score_raw", "adaptive": "adaptive_score_baseline"}
    for k in (10, 30, 50):
        qlib_sets = topk_sets(sub, "qlib_score_raw", k)
        repaired_sets = topk_sets(sub, repaired_score_col, k)
        overlaps = []
        for day in sorted(set(qlib_sets) & set(repaired_sets)):
            union = qlib_sets[day] | repaired_sets[day]
            overlaps.append(len(qlib_sets[day] & repaired_sets[day]) / len(union) if union else 0.0)
        rows.append(
            {
                "split": "independent_test",
                "metric": f"top{k}_repaired_vs_qlib_jaccard_overlap",
                "value": float(np.mean(overlaps)) if overlaps else 0.0,
                "date_count": len(overlaps),
            }
        )
        for method, score_col in methods.items():
            sets = topk_sets(sub, score_col, k)
            ordered = [sets[day] for day in sorted(sets)]
            stabilities = []
            for prev, cur in zip(ordered, ordered[1:]):
                union = prev | cur
                stabilities.append(len(prev & cur) / len(union) if union else 0.0)
            rows.append(
                {
                    "split": "independent_test",
                    "metric": f"top{k}_{method}_day_to_day_jaccard_stability",
                    "value": float(np.mean(stabilities)) if stabilities else 0.0,
                    "date_count": len(stabilities),
                }
            )
    return pd.DataFrame(rows)


def segment_diagnostics(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    test = df[df["split"] == "independent_test"]
    for segment_col in ("year", "regime_segment"):
        for key, group in test.groupby(segment_col):
            repaired = evaluate(group.assign(split="independent_test"), "repaired_ltr_score", "repaired_ltr", "independent_test")
            qlib = evaluate(group.assign(split="independent_test"), "qlib_score_raw", "rank_rotate_top50", "independent_test")
            rows.append(
                {
                    "segment_type": segment_col,
                    "segment_value": str(key),
                    "date_count": repaired["date_count"],
                    "repaired_rank_ic": repaired["rank_ic_10d"],
                    "qlib_rank_ic": qlib["rank_ic_10d"],
                    "repaired_ndcg_at_30": repaired["ndcg_at_30"],
                    "qlib_ndcg_at_30": qlib["ndcg_at_30"],
                    "repaired_top30_future_excess_rank_10d": repaired["top30_future_excess_rank_10d"],
                    "qlib_top30_future_excess_rank_10d": qlib["top30_future_excess_rank_10d"],
                }
            )
    return pd.DataFrame(rows)


def decide_gate(test_comparison: pd.DataFrame, segment_table: pd.DataFrame) -> tuple[str, str]:
    repaired = test_comparison[
        (test_comparison["split"] == "independent_test")
        & (test_comparison["method"].str.startswith("repaired_ltr_"))
    ].iloc[0]
    qlib = test_comparison[
        (test_comparison["split"] == "independent_test")
        & (test_comparison["method"] == "rank_rotate_top50")
    ].iloc[0]
    rank_ok = repaired["rank_ic_10d"] > qlib["rank_ic_10d"]
    ndcg_ok = repaired["ndcg_at_30"] >= qlib["ndcg_at_30"]
    top30_ok = repaired["top30_future_excess_rank_10d"] >= qlib["top30_future_excess_rank_10d"]
    segment_ok = False
    if rank_ok and ndcg_ok and top30_ok:
        year_rows = segment_table[segment_table["segment_type"] == "year"]
        regime_rows = segment_table[segment_table["segment_type"] == "regime_segment"]
        year_ok = (year_rows["repaired_ndcg_at_30"] >= year_rows["qlib_ndcg_at_30"]).sum() >= 2 if len(year_rows) >= 2 else False
        regime_ok = (regime_rows["repaired_ndcg_at_30"] >= regime_rows["qlib_ndcg_at_30"]).sum() >= 2 if len(regime_rows) >= 2 else False
        segment_ok = bool(year_ok or regime_ok)
    if rank_ok and ndcg_ok and top30_ok and segment_ok:
        return "request_phase2_regime_gating_work", "repaired LTR cleared rank_ic, ndcg_at_30, Top30 future excess rank, and was not isolated to one segment"
    if rank_ok or ndcg_ok or top30_ok:
        return "phase1b_ltr_needs_repair", "some repaired LTR signals improved, but Phase1B gate was not fully cleared"
    return "stop_ltr_mainline_insufficient_evidence", "multiple reasonable Phase1B repairs still failed to beat qlib baseline on required TopK evidence"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_report(
    now: str,
    diagnosis: dict[str, Any],
    gate: dict[str, Any],
    test_comparison: pd.DataFrame,
    model_selection: pd.DataFrame,
    overlap: pd.DataFrame,
) -> None:
    test_text = test_comparison[test_comparison["split"] == "independent_test"].to_string(index=False)
    best_text = model_selection.head(8).to_string(index=False)
    overlap_text = overlap.to_string(index=False)
    REPORT_DOC.write_text(
        f"""# Phase 1B 执行报告：LTR Baseline 诊断与修复

生成时间：{now}

## 1. 本轮目标

只诊断并尝试修复 Phase1 LTR baseline 在 independent_test 上 rank IC 改善但 TopK / NDCG 输给 qlib baseline 的问题；不进入 Phase2。

## 2. 实际完成内容

- 新增脚本：`scripts/diagnose_tw_ltr_phase1b_repair.py`。
- 复用 Phase1 样本：`phase1_ltr_baseline/phase1_ltr_samples.csv`。
- 对 5d / 10d / 20d label window 做小范围对照。
- 对 qlib-only、qlib+technical、qlib+liquidity、qlib+market、all whitelist 做 feature group ablation。
- 只用 train / validation 做轻量参数与模型选择。
- 最后对选中模型做 independent_test 对照。
- 检查 LTR 与 qlib TopK overlap 和日间名单稳定性。

## 3. 改动文件清单

- `scripts/diagnose_tw_ltr_phase1b_repair.py`
- `docs/tw_ltr_rerank_regime_turnover/PHASE1B_LTR_REPAIR_EXECUTION_REPORT_CN.md`

## 4. 新增产物清单

- `data_tw/experiments/ltr_rerank_regime_turnover/phase1b_ltr_repair/phase1b_diagnosis_summary.json`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1b_ltr_repair/phase1b_feature_ablation_metrics.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1b_ltr_repair/phase1b_label_window_metrics.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1b_ltr_repair/phase1b_validation_model_selection.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1b_ltr_repair/phase1b_independent_test_comparison.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1b_ltr_repair/phase1b_topk_overlap_and_stability.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1b_ltr_repair/phase1b_gate_summary.json`

## 5. 诊断结论

- Phase1 的主要问题不是整体排序完全失效，而是 TopK 头部集中度不足。
- validation 上可选模型仍能提升 NDCG，但 independent_test 上 qlib 头部排序更稳。
- repaired LTR 与 qlib 的 TopK overlap / day-to-day stability 见下表，说明 LTR 对头部名单有明显重排，但未转化为更好的 independent_test TopK 质量。

```text
{overlap_text}
```

## 6. validation 模型选择

只基于 validation 的 selection_score = NDCG@30 + 0.10 * rank_ic_10d 选择模型，未用 independent_test 调参。

```text
{best_text}
```

## 7. independent_test 对照

```text
{test_text}
```

## 8. Gate 结论

- 推荐 gate：`{gate['recommended_gate']}`。
- gate 原因：{gate['gate_reason']}。
- rank IC 条件：`{gate['required_conditions']['rank_ic_higher_than_qlib']}`。
- NDCG@30 条件：`{gate['required_conditions']['ndcg_at_30_not_lower_than_qlib']}`。
- Top30 future excess rank 条件：`{gate['required_conditions']['top30_future_excess_rank_not_lower_than_qlib']}`。
- 非单一 segment 条件：`{gate['required_conditions']['not_single_segment_only']}`。

## 9. 风险 / 异常 / 未解决问题

- 本轮没有新增数据、没有新增白名单外特征，`trend_score` 仍排除。
- 本轮没有真实组合 replay，因此不解释为组合净值、换手、动作次数、成本或可执行动作结论。
- 如果审查者认为 rank IC 改善但 TopK 不改善仍可推进，需要用户明确放宽 gate；执行者本轮未自行放宽。

## 10. 需要审查者重点检查的点

- 是否认可 validation-only 模型选择流程。
- 是否认可 repaired LTR 的 gate 判定。
- `phase1b_independent_test_comparison.csv` 是否显示仍无法满足 Phase2 前置证据。
- 是否存在越界特征、越权数据源或真实交易语义。

## 11. 禁止事项遵守情况

本轮未新增白名单外特征，未引入 `trend_score`，未引入 forbidden features，未联网，未 provider refresh/publish，未 accepted latest switching，未改 frontend / API / monitor / database，未做 regime gating 动作实现，未做 turnover portfolio layer，未接 broker / quick-trade / orders / target position / target weight，未输出买入、卖出、持有、仓位、收益承诺、上涨概率或胜率语义。
""",
        encoding="utf-8",
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now = utc_now()
    schema = load_schema()
    input_features = list(schema["input_columns"])
    if "trend_score" in input_features:
        raise RuntimeError("trend_score is not allowed in Phase1B unless separately proven PIT-safe; aborting.")
    forbidden_hits = sorted(set(input_features) & FORBIDDEN_FEATURES)
    if forbidden_hits:
        raise RuntimeError(f"Forbidden features in input list: {forbidden_hits}")

    df = load_sample(schema)
    sets = feature_sets(input_features)

    label_window = run_label_window_experiments(df, sets["all_whitelist_without_trend_score"])
    label_window.to_csv(LABEL_WINDOW_CSV, index=False)

    ablation = run_feature_ablation(df, sets)
    ablation.to_csv(FEATURE_ABLATION_CSV, index=False)

    model_selection, best_candidate, best_scored = run_validation_selection(df, sets)
    model_selection.to_csv(MODEL_SELECTION_CSV, index=False)

    test_comparison = baseline_comparison(df, best_scored, best_candidate)
    test_comparison.to_csv(TEST_COMPARISON_CSV, index=False)

    overlap = overlap_and_stability(best_scored)
    overlap.to_csv(OVERLAP_STABILITY_CSV, index=False)

    segment_table = segment_diagnostics(best_scored)
    segment_path = OUT_DIR / "phase1b_year_regime_diagnostics.csv"
    segment_table.to_csv(segment_path, index=False)

    recommended_gate, gate_reason = decide_gate(test_comparison, segment_table)
    repaired = test_comparison[
        (test_comparison["split"] == "independent_test")
        & (test_comparison["method"].str.startswith("repaired_ltr_"))
    ].iloc[0]
    qlib = test_comparison[
        (test_comparison["split"] == "independent_test")
        & (test_comparison["method"] == "rank_rotate_top50")
    ].iloc[0]
    segment_ndcg_wins = int((segment_table["repaired_ndcg_at_30"] >= segment_table["qlib_ndcg_at_30"]).sum())
    gate = {
        "phase": "phase1b_ltr_repair",
        "created_at": now,
        "research_only": True,
        "no_new_data_source": True,
        "no_network": True,
        "no_provider_refresh_or_publish": True,
        "no_accepted_latest_switching": True,
        "no_frontend_or_api": True,
        "no_monitor_database_or_trading": True,
        "trend_score_excluded": "trend_score" not in input_features,
        "forbidden_feature_hits": forbidden_hits,
        "best_candidate": best_candidate.__dict__,
        "recommended_gate": recommended_gate,
        "gate_reason": gate_reason,
        "required_conditions": {
            "rank_ic_higher_than_qlib": bool(repaired["rank_ic_10d"] > qlib["rank_ic_10d"]),
            "ndcg_at_30_not_lower_than_qlib": bool(repaired["ndcg_at_30"] >= qlib["ndcg_at_30"]),
            "top30_future_excess_rank_not_lower_than_qlib": bool(repaired["top30_future_excess_rank_10d"] >= qlib["top30_future_excess_rank_10d"]),
            "not_single_segment_only": bool(segment_ndcg_wins >= 2),
        },
        "independent_test_repaired": repaired.to_dict(),
        "independent_test_qlib_top50": qlib.to_dict(),
        "artifacts": {
            "diagnosis_summary": rel(DIAGNOSIS_JSON),
            "feature_ablation": rel(FEATURE_ABLATION_CSV),
            "label_window": rel(LABEL_WINDOW_CSV),
            "validation_model_selection": rel(MODEL_SELECTION_CSV),
            "independent_test_comparison": rel(TEST_COMPARISON_CSV),
            "topk_overlap_and_stability": rel(OVERLAP_STABILITY_CSV),
            "year_regime_diagnostics": rel(segment_path),
            "gate_summary": rel(GATE_JSON),
            "report": rel(REPORT_DOC),
        },
    }
    diagnosis = {
        "created_at": now,
        "phase1_problem": "Phase1 LTR improved independent_test rank IC but underperformed qlib on TopK/NDCG.",
        "diagnosis": [
            "Broad cross-sectional ordering can improve while top buckets degrade; Phase1B therefore focuses on NDCG@30 and Top30 future excess rank.",
            "Validation-only model selection found a repaired candidate, but independent_test gate decides whether evidence is sufficient.",
            "TopK overlap/stability metrics quantify whether repaired LTR is replacing qlib head names without better head quality.",
        ],
        "best_candidate": best_candidate.__dict__,
        "input_feature_count": len(input_features),
        "trend_score_excluded": "trend_score" not in input_features,
        "forbidden_feature_hits": forbidden_hits,
        "recommended_gate": recommended_gate,
        "gate_reason": gate_reason,
    }
    write_json(DIAGNOSIS_JSON, diagnosis)
    write_json(GATE_JSON, gate)
    write_report(now, diagnosis, gate, test_comparison, model_selection, overlap)

    print(json.dumps({"ok": True, "recommended_gate": recommended_gate, "gate_reason": gate_reason, "report": rel(REPORT_DOC)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
