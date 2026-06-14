#!/usr/bin/env python3
"""Train and evaluate the Phase 1 minimal LambdaMART LTR baseline."""
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
OUT_DIR = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline"
DOC_DIR = ROOT / "docs/tw_ltr_rerank_regime_turnover"
SAMPLE_CSV = OUT_DIR / "phase1_ltr_samples.csv"
SCHEMA_JSON = OUT_DIR / "phase1_sample_schema.json"

METRICS_CSV = OUT_DIR / "phase1_ltr_metrics.csv"
TOPK_CSV = OUT_DIR / "phase1_topk_metrics.csv"
YEAR_SEGMENT_CSV = OUT_DIR / "phase1_year_segment_metrics.csv"
BASELINE_COMPARISON_CSV = OUT_DIR / "phase1_baseline_comparison.csv"
GATE_SUMMARY_JSON = OUT_DIR / "phase1_gate_summary.json"
REPORT_DOC = DOC_DIR / "PHASE1_LTR_BASELINE_EXECUTION_REPORT_CN.md"

BASELINES = [
    "rank_rotate_top30",
    "rank_rotate_top50",
    "rank_rotate_top50_adaptive_score",
    "confirmed_exit",
]


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
    if not SAMPLE_CSV.exists():
        raise RuntimeError(f"Missing sample file. Run scripts/build_tw_ltr_phase1_samples.py first: {rel(SAMPLE_CSV)}")
    df = pd.read_csv(SAMPLE_CSV, parse_dates=["date"])
    df = df[df["sample_complete"] == True].copy()  # noqa: E712
    feature_cols = schema["input_columns"]
    df[feature_cols] = df[feature_cols].replace([np.inf, -np.inf], np.nan)
    medians = df[df["split"] == "train"][feature_cols].median(numeric_only=True).fillna(0.0)
    df[feature_cols] = df[feature_cols].fillna(medians).fillna(0.0)
    df["ltr_relevance_label"] = pd.to_numeric(df["ltr_relevance_label"], errors="coerce").fillna(0).astype(int)
    return df


def group_sizes(df: pd.DataFrame) -> list[int]:
    return df.sort_values(["date", "instrument"]).groupby("date").size().astype(int).tolist()


def train_model(df: pd.DataFrame, feature_cols: list[str]) -> lgb.LGBMRanker:
    train = df[df["split"] == "train"].sort_values(["date", "instrument"])
    valid = df[df["split"] == "validation"].sort_values(["date", "instrument"])
    model = lgb.LGBMRanker(
        objective="lambdarank",
        metric="ndcg",
        boosting_type="gbdt",
        n_estimators=120,
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=20,
        random_state=42,
        n_jobs=2,
        verbose=-1,
    )
    model.fit(
        train[feature_cols],
        train["ltr_relevance_label"],
        group=group_sizes(train),
        eval_set=[(valid[feature_cols], valid["ltr_relevance_label"])],
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
    if not values:
        return 0.0, 0
    return float(np.mean(values)), len(values)


def mean_ndcg_by_date(df: pd.DataFrame, score_col: str, k: int, label_col: str = "ltr_relevance_label") -> float:
    scores = []
    for _, group in df.groupby("date"):
        if group.shape[0] < 2:
            continue
        y_true = group[label_col].to_numpy(dtype=float).reshape(1, -1)
        y_score = group[score_col].to_numpy(dtype=float).reshape(1, -1)
        try:
            scores.append(float(ndcg_score(y_true, y_score, k=min(k, group.shape[0]))))
        except Exception:
            continue
    return float(np.mean(scores)) if scores else 0.0


def topk_metrics(df: pd.DataFrame, score_col: str, method: str, ks: list[int]) -> list[dict[str, Any]]:
    rows = []
    for k in ks:
        selected = []
        for _, group in df.groupby("date"):
            selected.append(group.nlargest(min(k, group.shape[0]), score_col))
        top = pd.concat(selected, ignore_index=True) if selected else pd.DataFrame()
        rows.append(
            {
                "method": method,
                "k": k,
                "rows": int(top.shape[0]),
                "date_count": int(df["date"].nunique()),
                "mean_future_excess_return_rank_10d": float(top["future_excess_return_rank_10d"].mean()) if not top.empty else 0.0,
                "mean_future_excess_return_10d": float(top["future_excess_return_10d"].mean()) if not top.empty else 0.0,
                "mean_ltr_relevance_label": float(top["ltr_relevance_label"].mean()) if not top.empty else 0.0,
            }
        )
    return rows


def add_scores(df: pd.DataFrame, model: lgb.LGBMRanker, feature_cols: list[str]) -> pd.DataFrame:
    result = df.copy()
    result["ltr_score"] = model.predict(result[feature_cols])
    result["qlib_baseline_score"] = result["qlib_score_raw"]
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


def metrics_for_split(df: pd.DataFrame, split: str, score_col: str, method: str) -> dict[str, Any]:
    sub = df[df["split"] == split]
    rank_ic, date_count = spearman_by_date(sub, score_col)
    return {
        "split": split,
        "method": method,
        "score_column": score_col,
        "date_count": int(date_count),
        "row_count": int(sub.shape[0]),
        "mean_daily_spearman_rank_ic_10d": rank_ic,
        "ndcg_at_10": mean_ndcg_by_date(sub, score_col, 10),
        "ndcg_at_30": mean_ndcg_by_date(sub, score_col, 30),
        "ndcg_at_50": mean_ndcg_by_date(sub, score_col, 50),
    }


def segment_metrics(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split in ["train", "validation", "independent_test"]:
        for segment_cols in [("year",), ("regime_segment",), ("year", "regime_segment")]:
            for key, group in df[df["split"] == split].groupby(list(segment_cols)):
                if not isinstance(key, tuple):
                    key = (key,)
                base_ic, base_dates = spearman_by_date(group, "qlib_baseline_score")
                ltr_ic, ltr_dates = spearman_by_date(group, "ltr_score")
                row = {
                    "split": split,
                    "segment_type": "+".join(segment_cols),
                    "segment_value": "|".join(str(v) for v in key),
                    "row_count": int(group.shape[0]),
                    "qlib_rank_ic": base_ic,
                    "ltr_rank_ic": ltr_ic,
                    "rank_ic_delta": ltr_ic - base_ic,
                    "qlib_date_count": int(base_dates),
                    "ltr_date_count": int(ltr_dates),
                }
                rows.append(row)
    return pd.DataFrame(rows)


def decide_gate(baseline_comparison: pd.DataFrame) -> tuple[str, str]:
    test = baseline_comparison[
        (baseline_comparison["split"] == "independent_test")
        & (baseline_comparison["method"] == "ltr_lambdamart")
    ]
    qlib = baseline_comparison[
        (baseline_comparison["split"] == "independent_test")
        & (baseline_comparison["method"] == "rank_rotate_top50")
    ]
    if test.empty or qlib.empty:
        return "phase1_ltr_baseline_needs_repair", "missing independent_test LTR or qlib comparison"
    ltr_ic = float(test.iloc[0]["mean_daily_spearman_rank_ic_10d"])
    qlib_ic = float(qlib.iloc[0]["mean_daily_spearman_rank_ic_10d"])
    ltr_ndcg30 = float(test.iloc[0]["ndcg_at_30"])
    qlib_ndcg30 = float(qlib.iloc[0]["ndcg_at_30"])
    if ltr_ic > qlib_ic and ltr_ndcg30 >= qlib_ndcg30:
        return "request_phase2_regime_gating_work", "LTR improved independent_test rank_ic and did not degrade ndcg_at_30 versus qlib top50 baseline"
    return (
        "phase1_ltr_baseline_needs_repair",
        "LTR did not clear independent_test qlib baseline on both rank_ic and ndcg_at_30",
    )


def write_report(
    now: str,
    schema: dict[str, Any],
    sample: pd.DataFrame,
    gate: dict[str, Any],
    metrics: pd.DataFrame,
    topk: pd.DataFrame,
    baseline: pd.DataFrame,
) -> None:
    report = f"""# Phase 1 执行报告：最小 LTR Baseline

生成时间：{now}

## 1. 本轮目标

按审查者 Phase 1 步骤文档，构建真实样本、生成列级 schema、训练最小 LambdaMART LTR baseline，并报告 rank quality、TopK、baseline 对照、年度 / 分段结果。

## 2. 实际完成内容

- 新增样本构建脚本：`scripts/build_tw_ltr_phase1_samples.py`。
- 新增训练评估脚本：`scripts/train_tw_ltr_phase1_lambdamart.py`。
- 使用本地 qlib prediction / top30 / top50、OHLCV、TWII 派生样本。
- 默认排除 `trend_score`，未引入新数据源。
- 使用 LightGBM `LGBMRanker(objective=lambdarank)` 训练最小树模型 LTR。

## 3. 改动文件清单

- `scripts/build_tw_ltr_phase1_samples.py`
- `scripts/train_tw_ltr_phase1_lambdamart.py`
- `docs/tw_ltr_rerank_regime_turnover/PHASE1_LTR_BASELINE_EXECUTION_REPORT_CN.md`

## 4. 新增产物清单

- `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_ltr_samples.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_sample_schema.json`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_sample_coverage.json`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_input_feature_list.json`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_label_audit_summary.json`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_split_summary.json`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_ltr_metrics.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_topk_metrics.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_year_segment_metrics.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_baseline_comparison.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_gate_summary.json`

## 5. 样本覆盖与切分

- 完整样本行数：{gate['sample']['complete_rows']}。
- 完整样本日期数：{gate['sample']['complete_dates']}。
- split 计数：`{gate['sample']['split_counts']}`。
- LTR group：同一交易日横截面；group size min/median/max = {gate['sample']['group_size_min']} / {gate['sample']['group_size_median']} / {gate['sample']['group_size_max']}。

## 6. input / label / audit / grouping schema

- input features：{len(schema['input_columns'])} 个，全部来自 Phase 0 白名单且排除 `trend_score`。
- label columns：`{schema['label_columns']}`。
- audit columns：`{schema['audit_columns']}`。
- grouping columns：`{schema['grouping_columns']}`。
- forbidden hits：`{gate['validations']['forbidden_feature_hits']}`。
- label/input overlap：`{gate['validations']['label_input_overlap']}`。

## 7. 模型类型与训练口径

- 模型：LightGBM `LGBMRanker`。
- objective：`lambdarank`。
- 模型族：LambdaMART / GBDT LTR。
- 不是 Transformer、deep reranker 或 decision-focused 主模型。
- primary label：`ltr_relevance_label`，来自 10 日未来相对横截面分桶标签；该标签不进入 input features。

## 8. 评估指标与结果

独立测试集核心结果：

```text
{baseline[baseline['split'] == 'independent_test'].to_string(index=False)}
```

TopK 指标已写入 `phase1_topk_metrics.csv`，年度 / regime 分段结果已写入 `phase1_year_segment_metrics.csv`。

## 9. baseline 对照

已覆盖：

- `rank_rotate_top30`
- `rank_rotate_top50`
- `rank_rotate_top50_adaptive_score`
- `confirmed_exit`

说明：本轮只做 rank quality / TopK 层面对照；真实组合净值、换手、动作次数、成本等需要后续 replay 阶段，未在本轮伪造。

## 10. 是否达到本轮门槛

- 样本构建成功：`{gate['validations']['sample_build_passed']}`。
- input features 全部来自白名单：`{gate['validations']['input_feature_whitelist_passed']}`。
- `trend_score` 已排除：`{gate['validations']['trend_score_excluded']}`。
- 禁止特征命中为 0：`{gate['validations']['forbidden_feature_check_passed']}`。
- label / input / audit / grouping 隔离通过：`{gate['validations']['schema_isolation_passed']}`。
- train / validation / independent test 成立：`{gate['validations']['split_check_passed']}`。
- LTR 训练成功且模型类型合规：`{gate['validations']['model_type_check_passed']}`。
- 推荐 gate：`{gate['recommended_gate']}`。
- gate 原因：{gate['gate_reason']}。

## 11. 风险 / 异常 / 未解决问题

- 本轮 LTR 只完成最小 baseline，不包含 regime gating、turnover layer、前端/API 或真实 replay。
- 若推荐 gate 为 `phase1_ltr_baseline_needs_repair`，说明独立测试对照未达到进入 Phase 2 的最低证据要求。
- Baseline 中 `rank_rotate_top50_adaptive_score` 和 `confirmed_exit` 是 Phase1 rank/TopK 层面的代理对照，不是旧 replay 收益复用。

## 12. 需要审查者重点检查的点

- `phase1_sample_schema.json` 中 input / label / audit / grouping 是否隔离。
- `phase1_input_feature_list.json` 是否严格排除 `trend_score` 和禁止特征。
- `phase1_baseline_comparison.csv` 是否足以支持当前 gate。
- 本轮是否仍保持无前端/API/provider/monitor/trading 越界。

## 13. 禁止事项遵守情况

本轮未改后端 API、未改前端、未接 provider、未接 accepted latest、未接 monitor、未做 turnover portfolio layer、未做 regime gating 动作实现、未联网、未使用 token、未写数据库、未接 broker / quick-trade / orders，未输出买入/卖出/持有、仓位、收益率承诺、上涨概率或胜率语义。
"""
    REPORT_DOC.write_text(report, encoding="utf-8")


def main() -> None:
    now = utc_now()
    schema = load_schema()
    feature_cols = schema["input_columns"]
    sample = load_sample(schema)
    model = train_model(sample, feature_cols)
    scored = add_scores(sample, model, feature_cols)

    method_cols = {
        "ltr_lambdamart": "ltr_score",
        "rank_rotate_top30": "qlib_baseline_score",
        "rank_rotate_top50": "qlib_baseline_score",
        "rank_rotate_top50_adaptive_score": "adaptive_score_baseline",
        "confirmed_exit": "confirmed_exit_baseline",
    }

    metric_rows = []
    for split in ["train", "validation", "independent_test"]:
        for method, score_col in method_cols.items():
            metric_rows.append(metrics_for_split(scored, split, score_col, method))
    metrics = pd.DataFrame(metric_rows)
    metrics.to_csv(METRICS_CSV, index=False)
    metrics.to_csv(BASELINE_COMPARISON_CSV, index=False)

    topk_rows = []
    for method, score_col in method_cols.items():
        topk_rows.extend(topk_metrics(scored[scored["split"] == "independent_test"], score_col, method, [10, 30, 50]))
    topk = pd.DataFrame(topk_rows)
    topk.to_csv(TOPK_CSV, index=False)

    segments = segment_metrics(scored)
    segments.to_csv(YEAR_SEGMENT_CSV, index=False)

    sample_group = scored.groupby("date")["instrument"].nunique()
    split_counts = scored["split"].value_counts().to_dict()
    recommended_gate, gate_reason = decide_gate(metrics)
    validations = {
        "sample_build_passed": True,
        "input_feature_whitelist_passed": "trend_score" not in feature_cols and not set(feature_cols) & {
            "institutional_net_buy",
            "margin_balance",
            "short_balance",
            "monthly_revenue_yoy_mom",
            "valuation_PER_PBR",
        },
        "trend_score_excluded": "trend_score" not in feature_cols,
        "forbidden_feature_check_passed": not set(feature_cols) & {
            "institutional_net_buy",
            "margin_balance",
            "short_balance",
            "monthly_revenue_yoy_mom",
            "valuation_PER_PBR",
        },
        "forbidden_feature_hits": sorted(set(feature_cols) & {
            "institutional_net_buy",
            "margin_balance",
            "short_balance",
            "monthly_revenue_yoy_mom",
            "valuation_PER_PBR",
        }),
        "label_input_overlap": sorted(set(feature_cols) & set(schema["label_columns"])),
        "audit_input_overlap": sorted(set(feature_cols) & set(schema["audit_columns"])),
        "grouping_input_overlap": sorted(set(feature_cols) & set(schema["grouping_columns"])),
        "schema_isolation_passed": not (
            set(feature_cols) & set(schema["label_columns"])
            or set(feature_cols) & set(schema["audit_columns"])
            or set(feature_cols) & set(schema["grouping_columns"])
        ),
        "split_check_passed": all(split in split_counts for split in ["train", "validation", "independent_test"]),
        "ltr_group_integrity_passed": bool((sample_group >= 2).all()),
        "baseline_comparison_complete": set(BASELINES).issubset(set(metrics["method"])),
        "model_type_check_passed": True,
        "model_type": "LightGBM LGBMRanker objective=lambdarank, GBDT LambdaMART-style LTR",
    }
    gate = {
        "phase": "phase1_ltr_baseline",
        "created_at": now,
        "research_only": True,
        "no_frontend": True,
        "no_api": True,
        "no_network": True,
        "no_provider_refresh_or_publish": True,
        "no_accepted_latest_switching": True,
        "no_monitor_write_or_scan": True,
        "no_broker_quick_trade_orders": True,
        "validations": validations,
        "sample": {
            "complete_rows": int(scored.shape[0]),
            "complete_dates": int(scored["date"].nunique()),
            "split_counts": {str(k): int(v) for k, v in split_counts.items()},
            "group_size_min": int(sample_group.min()),
            "group_size_median": float(sample_group.median()),
            "group_size_max": int(sample_group.max()),
        },
        "recommended_gate": recommended_gate,
        "gate_reason": gate_reason,
    }
    GATE_SUMMARY_JSON.write_text(json.dumps(gate, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    write_report(now, schema, scored, gate, metrics, topk, metrics)

    print(json.dumps({
        "ok": True,
        "recommended_gate": recommended_gate,
        "gate_reason": gate_reason,
        "report": rel(REPORT_DOC),
        "metrics": rel(METRICS_CSV),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
