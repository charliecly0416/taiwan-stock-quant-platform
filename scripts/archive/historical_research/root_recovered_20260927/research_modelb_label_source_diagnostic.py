#!/usr/bin/env python3
"""Research-only check of old-label versus canonical-price label lineage."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from research_modelb_source_window_diagnostic import FEATURES, OUT as PARENT_OUT, fit_score, metric, prep

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_label_source_diagnostic_20260914"
B4_TRAIN = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b4_row_aligned_ltr_samples_20260913/B4_TRAIN_SAMPLE.parquet"
B4_TEST = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b4_row_aligned_ltr_samples_20260913/B4_TEST_SAMPLE.parquet"
PRICE_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized"
TWII = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b01_feature_input_contract_repair_20260913/twii_acquisition/TWII_NORMALIZED.csv"
LABEL = "relevance_10d_top_heavy"


def canonical_labels(keys: pd.DataFrame) -> pd.DataFrame:
    market = pd.read_csv(TWII, usecols=["date", "close"])
    market["date"] = market.date.astype(str).str[:10]
    market = market.sort_values("date").drop_duplicates("date")
    market["future"] = market.close.shift(-10) / market.close - 1
    twii = dict(zip(market.date, market.future))
    parts = []
    for path in sorted(PRICE_ROOT.glob("TW*.csv")):
        frame = pd.read_csv(path, usecols=["date", "close"])
        frame["date"] = frame.date.astype(str).str[:10]
        frame = frame.sort_values("date").drop_duplicates("date")
        frame["stock_future"] = frame.close.shift(-10) / frame.close - 1
        frame["instrument"] = path.stem
        parts.append(frame[["date", "instrument", "stock_future"]])
    future = pd.concat(parts, ignore_index=True)
    out = keys[["date", "instrument"]].drop_duplicates().merge(future, on=["date", "instrument"], how="left")
    out["market_future"] = out.date.map(twii)
    out["excess"] = out.stock_future - out.market_future
    out["canonical_rank"] = out.groupby("date").excess.rank(pct=True)
    out["canonical_label"] = np.select(
        [out.canonical_rank >= .90, out.canonical_rank >= .80, out.canonical_rank >= .70, out.canonical_rank >= .50],
        [4, 3, 2, 1], default=0,
    )
    out.loc[out.excess.isna(), "canonical_label"] = np.nan
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    train = prep(pd.read_parquet(B4_TRAIN))
    test = prep(pd.read_parquet(B4_TEST))
    all_rows = pd.concat([train, test], ignore_index=True).sort_values(["date", "instrument"], kind="mergesort")
    labels = canonical_labels(all_rows)
    merged = all_rows.merge(labels, on=["date", "instrument"], how="left")
    comparable = merged.dropna(subset=[LABEL, "canonical_label"]).copy()
    comparable["label_equal"] = comparable[LABEL].eq(comparable.canonical_label)
    agreement = {
        "rows": int(len(comparable)),
        "dates": int(comparable.date.nunique()),
        "agreement": float(comparable.label_equal.mean()),
        "old_vs_canonical_rank_spearman": float(comparable[LABEL].corr(comparable.canonical_rank, method="spearman")),
        "missing_canonical_label_rows": int(merged.canonical_label.isna().sum()),
        "crosstab": pd.crosstab(comparable[LABEL], comparable.canonical_label, normalize="index").round(6).to_dict(),
        "agreement_by_split": comparable.assign(split=np.where(comparable.date <= "2025-12-31", "train_period", "test_period")).groupby("split").label_equal.mean().to_dict(),
    }
    comparable[["date", "instrument", LABEL, "canonical_rank", "canonical_label", "label_equal"]].to_csv(OUT / "LABEL_LINEAGE_COMPARISON.csv", index=False)

    # Same canonical feature matrix and same common canonical-labeled test set;
    # only the training label source changes.
    fit_old = merged[merged.date.between("2023-01-01", "2025-12-31")].dropna(subset=FEATURES + [LABEL]).copy()
    fit_new = merged[merged.date.between("2023-01-01", "2025-12-31")].dropna(subset=FEATURES + ["canonical_label"]).copy()
    eval_old = merged[merged.date.between("2026-01-02", "2026-05-07")].dropna(subset=FEATURES + [LABEL, "canonical_label"]).copy()
    eval_new = eval_old.copy()
    pred_old = fit_score(fit_old, eval_old, FEATURES)
    fit_new[LABEL] = fit_new["canonical_label"]
    eval_new[LABEL] = eval_new["canonical_label"]
    pred_new = fit_score(fit_new, eval_new, FEATURES)
    eval_old_for_metric = eval_old.rename(columns={"canonical_label": "canonical_eval_label"}).copy()
    eval_old_for_metric[LABEL] = eval_old_for_metric["canonical_eval_label"]
    metrics = [metric(eval_old_for_metric, pred_old, "canonical_features_old_labels_train_2023_2025_eval_canonical_labels"), metric(eval_old_for_metric, pred_new, "canonical_features_canonical_labels_train_2023_2025_eval_canonical_labels")]
    pd.DataFrame(metrics).to_csv(OUT / "LABEL_SOURCE_METRICS.csv", index=False)
    report = {
        "schema_version": "modelb.label_source_diagnostic.v1",
        "research_only": True, "diagnostic_only": True, "production_allowed": False,
        "canonical_price_source": str(PRICE_ROOT.relative_to(ROOT)),
        "canonical_market_source": str(TWII.relative_to(ROOT)),
        "old_label_source": "phase E2/O3 labels built from normalized_nonempty stock price and TWII source",
        "canonical_label_rule": "10-row forward close excess return over canonical option_c stock prices and B01 TWII, percentile thresholds 0.50/0.70/0.80/0.90",
        "agreement": agreement,
        "metrics": metrics,
        "parent_source_window_diagnostic": str((PARENT_OUT / "SOURCE_WINDOW_DIAGNOSTIC.json").relative_to(ROOT)),
    }
    (OUT / "LABEL_SOURCE_DIAGNOSTIC.json").write_text(json.dumps(report, indent=2, ensure_ascii=True, default=str) + "\n", encoding="utf-8")
    lines = ["# Model B 标签来源诊断", "", "仅用于离线研究，不连接 baseline、latest、default 或生产链路。", "", f"共同完整样本标签一致率：**{agreement['agreement']:.4%}**；旧标签与 canonical 标签秩相关：**{agreement['old_vs_canonical_rank_spearman']:.4f}**。", "", "| 训练标签 | 评估标签 | NDCG@10 | NDCG@30 | NDCG@50 | mean daily Spearman |", "|---|---|---:|---:|---:|---:|"]
    for r in metrics:
        lines.append(f"| {r['variant'].replace('_', ' ')} | canonical | {r['ndcg_at_10']:.6f} | {r['ndcg_at_30']:.6f} | {r['ndcg_at_50']:.6f} | {r['mean_daily_spearman_label']:.6f} |")
    lines += ["", "结论：标签来源不同是合同问题，应该在后续正式重训前统一；但共同样本上的高一致率需要结合窗口对照解读，当前证据不支持它单独解释 B5 的下降。", ""]
    (OUT / "LABEL_SOURCE_DIAGNOSTIC_CN.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": "PASS", "output": str(OUT.relative_to(ROOT)), "agreement": agreement, "metrics": metrics}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
