#!/usr/bin/env python3
"""Research-only Model B diagnostic: separate feature-source and window effects.

The script trains isolated LightGBM rankers in a diagnostic directory. It does
not touch baseline/latest/default artifacts or production state.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import ndcg_score

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_source_window_diagnostic_20260914"
OLD_TRAIN = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_ltr_train_sample_2023_2025.csv"
OLD_TEST = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_ltr_test_sample_2026.csv"
B4_TRAIN = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b4_row_aligned_ltr_samples_20260913/B4_TRAIN_SAMPLE.parquet"
B4_TEST = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b4_row_aligned_ltr_samples_20260913/B4_TEST_SAMPLE.parquet"
B2_SENSITIVITY = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b2_canonical_pit_features_20260913/FEATURE_ARTIFACT_SENSITIVITY.parquet"
E2_LABEL_TRAIN = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_ltr_train_sample_2023_2025.csv"
E2_LABEL_TEST = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_ltr_test_sample_2026.csv"
OLD_PRICE = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
NEW_PRICE = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized"

KEY = ["date", "instrument"]
LABEL = "relevance_10d_top_heavy"
FEATURES = [
    "qlib_score_raw", "qlib_rank", "qlib_score_percentile_by_date", "qlib_score_zscore_by_date",
    "rank_change_1d", "rank_change_3d", "rank_change_5d", "top10_flag", "top30_flag", "top50_flag",
    "top30_streak", "top50_streak", "MA5", "MA10", "MA20", "MA60", "RSI14", "MACD",
    "Bollinger_position", "ret20", "volatility20", "volume_ratio20", "avg_trading_value_20d",
    "volume_stability20", "missing_rate20", "suspension_proxy", "slippage_proxy", "TWII_ret20",
    "TWII_ret60", "TWII_close_vs_MA60", "TWII_close_vs_MA120", "market_volatility20",
    "market_drawdown60", "market_breadth20", "foreign_net_buy", "investment_trust_net_buy",
    "dealer_net_buy", "institutional_total_net_buy", "foreign_net_buy_roll1", "foreign_net_buy_roll3",
    "foreign_net_buy_roll5", "foreign_net_buy_roll10", "investment_trust_net_buy_roll1",
    "investment_trust_net_buy_roll3", "investment_trust_net_buy_roll5", "investment_trust_net_buy_roll10",
    "dealer_net_buy_roll1", "dealer_net_buy_roll3", "dealer_net_buy_roll5", "dealer_net_buy_roll10",
    "institutional_total_net_buy_roll1", "institutional_total_net_buy_roll3", "institutional_total_net_buy_roll5",
    "institutional_total_net_buy_roll10", "institutional_total_net_buy_streak", "institutional_missing_flag",
    "institutional_delay_flag", "institutional_flow_delay_days", "institutional_flow_asof_missing_flag",
    "margin_balance", "margin_balance_change", "short_balance", "short_balance_change",
    "margin_balance_change_roll1", "margin_balance_change_roll3", "margin_balance_change_roll5",
    "margin_balance_change_roll10", "short_balance_change_roll1", "short_balance_change_roll3",
    "short_balance_change_roll5", "short_balance_change_roll10", "margin_direction_proxy",
    "short_direction_proxy", "margin_short_divergence_proxy", "margin_short_missing_flag",
    "margin_short_delay_flag", "margin_short_delay_days", "margin_short_asof_missing_flag",
]
CONTROL = FEATURES[:34]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def metric(frame: pd.DataFrame, score: np.ndarray, name: str) -> dict[str, Any]:
    x = frame[KEY + [LABEL]].copy()
    x["score"] = score
    vals: list[float] = []
    ndcgs = {10: [], 30: [], 50: []}
    for _, g in x.groupby("date", sort=True):
        if len(g) < 2:
            continue
        y = g[LABEL].to_numpy(dtype=float)
        s = g.score.to_numpy(dtype=float)
        rho = spearmanr(s, y).statistic
        if np.isfinite(rho):
            vals.append(float(rho))
        for k in ndcgs:
            ndcgs[k].append(float(ndcg_score(y[None, :], s[None, :], k=min(k, len(g)))))
    return {
        "variant": name,
        "rows": int(len(x)),
        "dates": int(x.date.nunique()),
        "ndcg_at_10": float(np.mean(ndcgs[10])),
        "ndcg_at_30": float(np.mean(ndcgs[30])),
        "ndcg_at_50": float(np.mean(ndcgs[50])),
        "mean_daily_spearman_label": float(np.mean(vals)),
    }


def fit_score(train: pd.DataFrame, test: pd.DataFrame, features: list[str]) -> np.ndarray:
    model = lgb.LGBMRanker(
        objective="lambdarank", metric="ndcg", boosting_type="gbdt", num_leaves=31,
        learning_rate=0.03, n_estimators=120, min_child_samples=40, random_state=42,
        n_jobs=2, verbosity=-1,
    )
    train = train.sort_values(KEY, kind="mergesort")
    test = test.sort_values(KEY, kind="mergesort")
    model.fit(train[features], train[LABEL], group=train.groupby("date", sort=True).size().tolist())
    return model.predict(test[features])


def prep(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    out["instrument"] = out["instrument"].astype(str)
    out = out.dropna(subset=FEATURES + [LABEL]).copy()
    out[FEATURES] = out[FEATURES].astype(float)
    out[LABEL] = out[LABEL].astype(float)
    return out.sort_values(KEY, kind="mergesort").reset_index(drop=True)


def prep_neutral(df: pd.DataFrame) -> pd.DataFrame:
    """Match the historical E3 diagnostic policy: finite numeric coercion + zero fill."""
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    out["instrument"] = out["instrument"].astype(str)
    out[FEATURES] = out[FEATURES].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0).astype(float)
    out[LABEL] = pd.to_numeric(out[LABEL], errors="coerce")
    return out.dropna(subset=[LABEL]).sort_values(KEY, kind="mergesort").reset_index(drop=True)


def source_audit() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for source_name, directory in [("normalized_nonempty", OLD_PRICE), ("option_c_150_normalized", NEW_PRICE)]:
        files = sorted(directory.glob("TW*.csv"))
        lengths, starts, ends = [], [], []
        for path in files:
            d = pd.read_csv(path, usecols=["date", "close", "factor"])
            lengths.append(len(d)); starts.append(str(d.date.min())[:10]); ends.append(str(d.date.max())[:10])
        rows.append({
            "source": source_name, "directory": str(directory.relative_to(ROOT)), "file_count": len(files),
            "total_rows": int(sum(lengths)), "median_rows": float(np.median(lengths)) if lengths else 0,
            "min_date": min(starts) if starts else None, "max_date": max(ends) if ends else None,
            "directory_sha256_manifest": hashlib.sha256("\n".join(f"{p.name},{sha256(p)}" for p in files).encode()).hexdigest(),
        })
    return {"source_inventory": rows}


def compare_values(old: pd.DataFrame, new: pd.DataFrame) -> dict[str, Any]:
    common = old[KEY + FEATURES].merge(new[KEY + FEATURES], on=KEY, suffixes=("_old", "_new"), how="inner")
    stats = []
    for feature in FEATURES:
        a, b = common[f"{feature}_old"].to_numpy(float), common[f"{feature}_new"].to_numpy(float)
        mask = np.isfinite(a) & np.isfinite(b)
        if not mask.any():
            continue
        delta = np.abs(a[mask] - b[mask])
        rel = delta / np.maximum(np.abs(a[mask]), 1e-12)
        stats.append({"feature": feature, "rows": int(mask.sum()), "different_rows": int((delta > 1e-9).sum()), "different_ratio": float((delta > 1e-9).mean()), "median_abs_delta": float(np.median(delta)), "median_relative_delta": float(np.median(rel)), "max_abs_delta": float(delta.max())})
    stats.sort(key=lambda x: x["different_ratio"], reverse=True)
    return {"common_rows": int(len(common)), "common_dates": int(common.date.nunique()), "feature_stats": stats}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    old_train = prep(pd.read_csv(OLD_TRAIN, low_memory=False))
    old_test = prep(pd.read_csv(OLD_TEST, low_memory=False))
    old_train_neutral = prep_neutral(pd.read_csv(OLD_TRAIN, low_memory=False))
    old_test_neutral = prep_neutral(pd.read_csv(OLD_TEST, low_memory=False))
    new_train = prep(pd.read_parquet(B4_TRAIN))
    new_test = prep(pd.read_parquet(B4_TEST))
    labels = pd.concat([
        pd.read_csv(E2_LABEL_TRAIN, usecols=KEY + [LABEL]),
        pd.read_csv(E2_LABEL_TEST, usecols=KEY + [LABEL]),
    ], ignore_index=True)
    labels["date"] = pd.to_datetime(labels["date"]).dt.strftime("%Y-%m-%d")
    sensitivity = pd.read_parquet(B2_SENSITIVITY).merge(labels, on=KEY, how="inner", validate="one_to_one")
    sensitivity = prep_neutral(sensitivity)

    # E3 used 2023-2025; B5 fits 2023-2024 and leaves 2025 as validation.
    old_fit_23_25 = old_train[old_train.date.between("2023-01-01", "2025-12-31")]
    old_fit_23_24 = old_train[old_train.date.between("2023-01-10", "2024-12-17")]
    old_test_2026 = old_test[old_test.date.between("2026-01-02", "2026-05-07")]
    new_fit_23_25 = new_train[new_train.date.between("2023-01-01", "2025-12-31")]
    new_fit_23_24 = new_train[new_train.date.between("2023-01-10", "2024-12-17")]
    new_valid_2025 = new_train[new_train.date.between("2025-01-02", "2025-12-31")]
    new_test_2026 = new_test[new_test.date.between("2026-01-02", "2026-05-07")]

    results = []
    predictions = {}
    cases = [
        ("legacy_features_2023_2025", old_fit_23_25, old_test_2026, FEATURES),
        ("canonical_features_2023_2025", new_fit_23_25, new_test_2026, FEATURES),
        ("legacy_features_2023_2024", old_fit_23_24, old_test_2026, FEATURES),
        ("canonical_features_2023_2024", new_fit_23_24, new_test_2026, FEATURES),
        ("legacy_features_2023_2025_neutral_fill", old_train_neutral[old_train_neutral.date.between("2023-01-01", "2025-12-31")], old_test_neutral[old_test_neutral.date.between("2026-01-02", "2026-05-07")], FEATURES),
        ("canonical_sensitivity_2023_2025_neutral_fill", sensitivity[sensitivity.date.between("2023-01-01", "2025-12-31")], sensitivity[sensitivity.date.between("2026-01-02", "2026-05-07")], FEATURES),
        ("canonical_sensitivity_2023_2024_neutral_fill", sensitivity[sensitivity.date.between("2023-01-10", "2024-12-17")], sensitivity[sensitivity.date.between("2026-01-02", "2026-05-07")], FEATURES),
        ("canonical_control_only_2023_2025", new_fit_23_25, new_test_2026, CONTROL),
        ("canonical_orthogonal_only_2023_2025", new_fit_23_25, new_test_2026, FEATURES[34:]),
    ]
    for name, train, test, feats in cases:
        scores = fit_score(train, test, feats)
        results.append(metric(test, scores, name))
        predictions[name] = pd.DataFrame({"date": test.date.to_numpy(), "instrument": test.instrument.to_numpy(), "score": scores})

    # The current B5 window also has a 2025 validation slice; record it separately.
    valid_scores = fit_score(new_fit_23_24, new_valid_2025, FEATURES)
    results.append(metric(new_valid_2025, valid_scores, "canonical_features_2023_2024_on_2025_validation"))

    old_common = old_test[old_test.date.between("2026-01-02", "2026-05-07")]
    new_common = new_test[new_test.date.between("2026-01-02", "2026-05-07")]
    report = {
        "schema_version": "modelb.source_window_diagnostic.v1",
        "created_at": pd.Timestamp.utcnow().isoformat(),
        "research_only": True, "diagnostic_only": True, "production_allowed": False,
        "inputs": {"old_train": str(OLD_TRAIN.relative_to(ROOT)), "old_test": str(OLD_TEST.relative_to(ROOT)), "b4_train": str(B4_TRAIN.relative_to(ROOT)), "b4_test": str(B4_TEST.relative_to(ROOT))},
        "feature_count": len(FEATURES), "control_feature_count": len(CONTROL), "orthogonal_feature_count": len(FEATURES) - len(CONTROL),
        "source_audit": source_audit(),
        "old_vs_canonical_test_feature_audit": compare_values(old_common, new_common),
        "results": results,
        "coverage": {
            "legacy_complete_test_rows": int(len(old_test)),
            "legacy_neutral_test_rows": int(len(old_test_neutral)),
            "canonical_primary_test_rows": int(len(new_test)),
            "canonical_sensitivity_test_rows": int(len(sensitivity[sensitivity.date.between("2026-01-02", "2026-05-07")])),
            "canonical_sensitivity_train_rows": int(len(sensitivity[sensitivity.date.between("2023-01-01", "2025-12-31")])),
        },
        "interpretation": {
            "window_effect": "Compare legacy_features_2023_2025 against legacy_features_2023_2024.",
            "source_effect": "Compare legacy_features_2023_2025 against canonical_features_2023_2025.",
            "missing_policy_effect": "Compare complete-case variants against *_neutral_fill variants. Historical E3 used zero fill; current B5 primary explicitly excludes incomplete rows.",
            "orthogonal_effect": "Compare canonical_control_only_2023_2025 and canonical_orthogonal_only_2023_2025 against the full canonical model.",
            "label_contract": "All cases use the existing E2/B4 relevance_10d_top_heavy labels; no labels are regenerated in this diagnostic.",
        },
    }
    (OUT / "SOURCE_WINDOW_DIAGNOSTIC.json").write_text(json.dumps(report, indent=2, ensure_ascii=True, default=str) + "\n", encoding="utf-8")
    pd.DataFrame(results).to_csv(OUT / "SOURCE_WINDOW_METRICS.csv", index=False)
    top = report["old_vs_canonical_test_feature_audit"]["feature_stats"][:20]
    lines = ["# Model B 来源与训练窗口诊断", "", "本目录仅用于离线研究，不连接 baseline、latest、default 或生产链路。", "", "## 对照结果", "", "| variant | NDCG@10 | NDCG@30 | NDCG@50 | mean daily Spearman | rows |", "|---|---:|---:|---:|---:|---:|"]
    for r in results:
        lines.append(f"| {r['variant']} | {r['ndcg_at_10']:.6f} | {r['ndcg_at_30']:.6f} | {r['ndcg_at_50']:.6f} | {r['mean_daily_spearman_label']:.6f} | {r['rows']} |")
    lines += ["", "## 共同测试集特征差异最大的字段", "", "| feature | different ratio | median relative delta | max abs delta |", "|---|---:|---:|---:|"]
    for r in top:
        lines.append(f"| {r['feature']} | {r['different_ratio']:.4f} | {r['median_relative_delta']:.6g} | {r['max_abs_delta']:.6g} |")
    lines += ["", "## 口径", "", "- 旧特征来自 `normalized_nonempty`，canonical 特征来自 `option_c_150_normalized`。", "- 旧版 E3 的历史复现使用零填充；当前 B5 primary 使用完整行筛选，缺失行不进入训练。", "- `canonical_sensitivity_*_neutral_fill` 只用于诊断，不代表当前 B5 primary 合同。", "- 旧标签与当前 B4 标签保持不变，仅用于比较特征来源和训练窗口。", "- 该结果不能直接作为 prospective OOS 或 baseline 切换依据。", ""]
    (OUT / "SOURCE_WINDOW_DIAGNOSTIC_CN.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": "PASS", "output": str(OUT.relative_to(ROOT)), "metrics": results}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
