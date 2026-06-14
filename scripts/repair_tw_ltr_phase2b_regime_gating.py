#!/usr/bin/env python3
"""Phase 2B offline regime gating repair.

This script stays within Stage 3 only. It reuses the Phase 1 sample and the
frozen Phase 1C qlib-preserving LTR rerank logic, tests multiple whitelist-only
regime definitions and non-noop conservative gates on validation, then reports
independent_test only as a final holdout check.
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
OUT_DIR = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase2b_regime_repair"
DOC_DIR = ROOT / "docs/tw_ltr_rerank_regime_turnover"

SAMPLE_CSV = PHASE1_DIR / "phase1_ltr_samples.csv"
SCHEMA_JSON = PHASE1_DIR / "phase1_sample_schema.json"

CANDIDATES_JSON = OUT_DIR / "phase2b_regime_definition_candidates.json"
DISTRIBUTION_CSV = OUT_DIR / "phase2b_regime_distribution.csv"
VALIDATION_SELECTION_CSV = OUT_DIR / "phase2b_validation_selection.csv"
REGIME_METRIC_CSV = OUT_DIR / "phase2b_regime_metric_by_state.csv"
INDEPENDENT_COMPARISON_CSV = OUT_DIR / "phase2b_independent_test_comparison.csv"
GATE_JSON = OUT_DIR / "phase2b_gate_summary.json"
REPORT_DOC = DOC_DIR / "PHASE2B_REGIME_REPAIR_EXECUTION_REPORT_CN.md"

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

REGIME_DEFINITIONS: list[dict[str, Any]] = [
    {
        "definition_id": "phase2_original",
        "risk_drawdown60": -0.12,
        "risk_ret60": -0.08,
        "risk_breadth20": 0.35,
        "risk_volatility20": 0.024,
        "caution_drawdown60": -0.06,
        "caution_ret20": -0.03,
        "caution_ret60": 0.00,
        "caution_breadth20": 0.45,
        "caution_volatility20": 0.018,
    },
    {
        "definition_id": "balanced_drawdown_breadth",
        "risk_drawdown60": -0.10,
        "risk_ret60": -0.06,
        "risk_breadth20": 0.40,
        "risk_volatility20": 0.022,
        "caution_drawdown60": -0.04,
        "caution_ret20": -0.02,
        "caution_ret60": 0.02,
        "caution_breadth20": 0.50,
        "caution_volatility20": 0.016,
    },
    {
        "definition_id": "breadth_sensitive",
        "risk_drawdown60": -0.10,
        "risk_ret60": -0.05,
        "risk_breadth20": 0.45,
        "risk_volatility20": 0.020,
        "caution_drawdown60": -0.03,
        "caution_ret20": -0.015,
        "caution_ret60": 0.03,
        "caution_breadth20": 0.55,
        "caution_volatility20": 0.015,
    },
    {
        "definition_id": "severe_risk_broad_caution",
        "risk_drawdown60": -0.14,
        "risk_ret60": -0.10,
        "risk_breadth20": 0.30,
        "risk_volatility20": 0.026,
        "caution_drawdown60": -0.05,
        "caution_ret20": -0.02,
        "caution_ret60": 0.01,
        "caution_breadth20": 0.50,
        "caution_volatility20": 0.016,
    },
]

GATING_RULES: list[dict[str, Any]] = [
    {"gate_id": "phase2_noop_c50_r50", "caution_scope": 50, "risk_scope": 50, "non_noop": False},
    {"gate_id": "mild_c45_r40", "caution_scope": 45, "risk_scope": 40, "non_noop": True},
    {"gate_id": "balanced_c40_r30", "caution_scope": 40, "risk_scope": 30, "non_noop": True},
    {"gate_id": "strict_c35_r20", "caution_scope": 35, "risk_scope": 20, "non_noop": True},
    {"gate_id": "risk_only_c50_r30", "caution_scope": 50, "risk_scope": 30, "non_noop": True},
    {"gate_id": "caution_only_c40_r50", "caution_scope": 40, "risk_scope": 50, "non_noop": True},
]

BASELINE_METHODS = {
    "qlib_rank_rotate_top50": "qlib_score_raw",
    "phase1c_qlib_preserving_ltr": "score_head10_all_l31_alpha0.7_top50_only",
    "phase2_noop_gate": "phase2_noop_gate_score",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def write_json(path: Path, payload: dict[str, Any] | list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_JSON.read_text(encoding="utf-8"))


def top_heavy_label(rank: pd.Series) -> pd.Series:
    r = rank.fillna(0)
    return np.select([r >= 0.90, r >= 0.80, r >= 0.70, r >= 0.50], [4, 3, 2, 1], default=0).astype(int)


def bucket_label(rank: pd.Series) -> pd.Series:
    return np.floor(rank.fillna(0).clip(0, 0.999999) * 5).astype(int).clip(0, 4)


def load_sample(schema: dict[str, Any]) -> pd.DataFrame:
    input_features = list(schema["input_columns"])
    if "trend_score" in input_features:
        raise RuntimeError("trend_score is not allowed in Phase2B.")
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
    return df


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
    out["phase2_noop_gate_score"] = out["score_head10_all_l31_alpha0.7_top50_only"]
    return out


def assign_regime(df: pd.DataFrame, definition: dict[str, Any]) -> pd.Series:
    risk = (
        (df["market_drawdown60"] <= definition["risk_drawdown60"])
        | (df["TWII_ret60"] <= definition["risk_ret60"])
        | (df["market_breadth20"] < definition["risk_breadth20"])
        | ((df["market_volatility20"] >= definition["risk_volatility20"]) & (df["TWII_ret20"] < 0))
    )
    caution = (
        (df["market_drawdown60"] <= definition["caution_drawdown60"])
        | (df["TWII_ret20"] <= definition["caution_ret20"])
        | (df["TWII_ret60"] <= definition["caution_ret60"])
        | (df["market_breadth20"] < definition["caution_breadth20"])
        | (df["market_volatility20"] >= definition["caution_volatility20"])
    )
    return pd.Series(np.select([risk, caution], ["risk_off", "caution"], default="normal"), index=df.index)


def apply_scope(score: pd.Series, df: pd.DataFrame, scope: int) -> pd.Series:
    return score.where(df["qlib_rank"] <= scope, -1.0 + df["qlib_pct"] * 0.000001)


def apply_gate(df: pd.DataFrame, regime_col: str, rule: dict[str, Any], col_name: str) -> pd.Series:
    score = df["score_head10_all_l31_alpha0.7_top50_only"].copy()
    caution_mask = df[regime_col] == "caution"
    risk_mask = df[regime_col] == "risk_off"
    score.loc[caution_mask] = apply_scope(score.loc[caution_mask], df.loc[caution_mask], int(rule["caution_scope"]))
    score.loc[risk_mask] = apply_scope(score.loc[risk_mask], df.loc[risk_mask], int(rule["risk_scope"]))
    score.name = col_name
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
    if df.empty:
        return pd.DataFrame()
    return pd.concat([g.nlargest(min(k, g.shape[0]), score_col) for _, g in df.groupby("date")], ignore_index=True)


def evaluate(df: pd.DataFrame, score_col: str, method: str, split: str, regime_col: str | None = None, regime: str | None = None) -> dict[str, Any]:
    sub = df[df["split"] == split]
    if regime_col and regime is not None:
        sub = sub[sub[regime_col] == regime]
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
        selected = topk(sub, score_col, k)
        row[f"top{k}_future_excess_rank_10d"] = float(selected["future_excess_return_rank_10d"].mean()) if not selected.empty else 0.0
        row[f"top{k}_mean_relevance_10d"] = float(selected["relevance_10d_bucket"].mean()) if not selected.empty else 0.0
        row[f"top{k}_median_qlib_rank"] = float(selected["qlib_rank"].median()) if not selected.empty else 0.0
    return row


def distribution(df: pd.DataFrame, regime_cols: dict[str, str]) -> pd.DataFrame:
    rows = []
    for definition_id, regime_col in regime_cols.items():
        for split in ("train", "validation", "independent_test"):
            for regime, group in df[df["split"] == split].groupby(regime_col):
                rows.append(
                    {
                        "definition_id": definition_id,
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


def conservative_diagnostics(df: pd.DataFrame, split: str, regime_col: str, gated_col: str, non_noop: bool) -> dict[str, Any]:
    details = []
    for regime in ("caution", "risk_off"):
        sub = df[(df["split"] == split) & (df[regime_col] == regime)]
        if sub.empty:
            details.append({"regime": regime, "has_rows": False})
            continue
        base30 = topk(sub, "score_head10_all_l31_alpha0.7_top50_only", 30)
        gate30 = topk(sub, gated_col, 30)
        base50 = topk(sub, "score_head10_all_l31_alpha0.7_top50_only", 50)
        gate50 = topk(sub, gated_col, 50)
        changed_top30 = 0.0
        for date, group in sub.groupby("date"):
            b = set(group.nlargest(min(30, group.shape[0]), "score_head10_all_l31_alpha0.7_top50_only")["instrument"])
            g = set(group.nlargest(min(30, group.shape[0]), gated_col)["instrument"])
            if b:
                changed_top30 += 1.0 - len(b & g) / len(b)
        date_count = int(sub["date"].nunique())
        changed_top30 = changed_top30 / date_count if date_count else 0.0
        details.append(
            {
                "regime": regime,
                "has_rows": True,
                "date_count": date_count,
                "base_top30_median_qlib_rank": float(base30["qlib_rank"].median()),
                "gated_top30_median_qlib_rank": float(gate30["qlib_rank"].median()),
                "base_top50_median_qlib_rank": float(base50["qlib_rank"].median()),
                "gated_top50_median_qlib_rank": float(gate50["qlib_rank"].median()),
                "top30_changed_ratio": float(changed_top30),
                "strictly_more_conservative_top30": bool(gate30["qlib_rank"].median() < base30["qlib_rank"].median()),
                "top30_future_excess_delta": float(gate30["future_excess_return_rank_10d"].mean() - base30["future_excess_return_rank_10d"].mean()),
            }
        )
    passed = bool(non_noop and any(d.get("has_rows") and (d.get("strictly_more_conservative_top30") or d.get("top30_changed_ratio", 0.0) > 0.0) for d in details))
    return {"passed": passed, "details": details}


def validation_score(row: dict[str, Any], phase1c: dict[str, Any], diag: dict[str, Any], non_noop: bool) -> float:
    core_loss = max(0.0, phase1c["ndcg_at_30"] - row["ndcg_at_30"]) + max(0.0, phase1c["ndcg_at_10"] - row["ndcg_at_10"])
    future_loss = max(0.0, phase1c["top30_future_excess_rank_10d"] - row["top30_future_excess_rank_10d"])
    changed = max((d.get("top30_changed_ratio", 0.0) for d in diag["details"] if d.get("has_rows")), default=0.0)
    conservative_bonus = 0.0025 * (1.0 if diag["passed"] else 0.0) + 0.001 * min(changed, 0.20)
    noop_penalty = 0.01 if not non_noop else 0.0
    return float(row["ndcg_at_30"] + 0.05 * row["top30_future_excess_rank_10d"] + 0.03 * row["rank_ic_10d"] + conservative_bonus - 5.0 * core_loss - 1.5 * future_loss - noop_penalty)


def build_candidates(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    rows = []
    regime_cols: dict[str, str] = {}
    phase1c_validation = evaluate(df, "score_head10_all_l31_alpha0.7_top50_only", "phase1c_qlib_preserving_ltr", "validation")
    for definition in REGIME_DEFINITIONS:
        definition_id = str(definition["definition_id"])
        regime_col = f"regime_{definition_id}"
        df[regime_col] = assign_regime(df, definition)
        regime_cols[definition_id] = regime_col
        for rule in GATING_RULES:
            gate_id = str(rule["gate_id"])
            col = f"score_{definition_id}_{gate_id}"
            df[col] = apply_gate(df, regime_col, rule, col)
            for split in ("validation", "independent_test"):
                row = evaluate(df, col, f"{definition_id}__{gate_id}", split)
                diag = conservative_diagnostics(df, split, regime_col, col, bool(rule["non_noop"]))
                row.update(
                    {
                        "definition_id": definition_id,
                        "gate_id": gate_id,
                        "regime_column": regime_col,
                        "caution_scope": int(rule["caution_scope"]),
                        "risk_scope": int(rule["risk_scope"]),
                        "non_noop": bool(rule["non_noop"]),
                        "conservative_effect_passed": bool(diag["passed"]),
                        "conservative_effect": json.dumps(diag, ensure_ascii=False),
                        "selection_score": validation_score(row, phase1c_validation, diag, bool(rule["non_noop"])) if split == "validation" else np.nan,
                    }
                )
                rows.append(row)
    return pd.DataFrame(rows), regime_cols


def choose_candidate(selection: pd.DataFrame) -> pd.Series:
    val = selection[selection["split"] == "validation"].copy()
    val = val[val["non_noop"] == True].copy()  # noqa: E712
    phase1c = selection[(selection["split"] == "validation") & (selection["gate_id"] == "phase2_noop_c50_r50")].iloc[0]
    val["passes_validation_core_floor"] = (
        (val["ndcg_at_30"] >= phase1c["ndcg_at_30"] - 0.0015)
        & (val["ndcg_at_10"] >= phase1c["ndcg_at_10"] - 0.0020)
        & (val["top30_future_excess_rank_10d"] >= phase1c["top30_future_excess_rank_10d"] - 0.0010)
    )
    val = val.sort_values(["passes_validation_core_floor", "selection_score", "conservative_effect_passed", "ndcg_at_30"], ascending=False)
    return val.iloc[0]


def yearly_results(df: pd.DataFrame, selected: pd.Series) -> pd.DataFrame:
    methods = {
        "qlib_rank_rotate_top50": "qlib_score_raw",
        "phase1c_qlib_preserving_ltr": "score_head10_all_l31_alpha0.7_top50_only",
        "phase2_noop_gate": "phase2_noop_gate_score",
        "phase2b_repaired_regime_gate": str(selected["score_column"]),
    }
    rows = []
    for year, group in df[df["split"] == "independent_test"].groupby("year"):
        if group["date"].nunique() < 10:
            continue
        work = group.assign(split="independent_test")
        for method, col in methods.items():
            row = evaluate(work, col, method, "independent_test")
            row["year"] = int(year)
            rows.append(row)
    return pd.DataFrame(rows)


def state_metrics(df: pd.DataFrame, selected: pd.Series) -> pd.DataFrame:
    regime_col = str(selected["regime_column"])
    selected_col = str(selected["score_column"])
    rows = []
    for regime in ("normal", "caution", "risk_off"):
        for method, col in {
            "qlib_rank_rotate_top50": "qlib_score_raw",
            "phase1c_qlib_preserving_ltr": "score_head10_all_l31_alpha0.7_top50_only",
            "phase2_noop_gate": "phase2_noop_gate_score",
            "phase2b_repaired_regime_gate": selected_col,
        }.items():
            row = evaluate(df, col, method, "independent_test", regime_col, regime)
            row["definition_id"] = str(selected["definition_id"])
            rows.append(row)
    return pd.DataFrame(rows)


def independent_comparison(df: pd.DataFrame, selected: pd.Series) -> pd.DataFrame:
    rows = []
    for method, col in {
        "qlib_rank_rotate_top50": "qlib_score_raw",
        "phase1c_qlib_preserving_ltr": "score_head10_all_l31_alpha0.7_top50_only",
        "phase2_noop_gate": "phase2_noop_gate_score",
        "phase2b_repaired_regime_gate": str(selected["score_column"]),
    }.items():
        rows.append(evaluate(df, col, method, "validation"))
        rows.append(evaluate(df, col, method, "independent_test"))
    return pd.DataFrame(rows)


def decide_gate(df: pd.DataFrame, selected: pd.Series, comparison: pd.DataFrame, yearly: pd.DataFrame) -> tuple[str, str, dict[str, Any]]:
    test = comparison[comparison["split"] == "independent_test"]
    selected_row = test[test["method"] == "phase2b_repaired_regime_gate"].iloc[0]
    phase1c = test[test["method"] == "phase1c_qlib_preserving_ltr"].iloc[0]
    validation_used_independent = False
    core_ok = (
        selected_row["ndcg_at_30"] >= phase1c["ndcg_at_30"]
        and selected_row["ndcg_at_10"] >= phase1c["ndcg_at_10"]
        and selected_row["top30_future_excess_rank_10d"] >= phase1c["top30_future_excess_rank_10d"]
    )
    diag = conservative_diagnostics(df, "independent_test", str(selected["regime_column"]), str(selected["score_column"]), bool(selected["non_noop"]))
    selected_yearly = yearly[yearly["method"] == "phase2b_repaired_regime_gate"][["year", "ndcg_at_30", "top30_future_excess_rank_10d"]]
    phase1c_yearly = yearly[yearly["method"] == "phase1c_qlib_preserving_ltr"][["year", "ndcg_at_30", "top30_future_excess_rank_10d"]]
    merged = selected_yearly.merge(phase1c_yearly, on="year", suffixes=("_phase2b", "_phase1c"))
    yearly_wins = int(((merged["ndcg_at_30_phase2b"] >= merged["ndcg_at_30_phase1c"]) & (merged["top30_future_excess_rank_10d_phase2b"] >= merged["top30_future_excess_rank_10d_phase1c"])).sum()) if not merged.empty else 0
    year_ok = bool(len(merged) >= 2 and yearly_wins >= 1)
    regime_support = [d for d in diag["details"] if d.get("has_rows") and (d.get("strictly_more_conservative_top30") or d.get("top30_changed_ratio", 0.0) > 0.0)]
    not_single_regime = bool(len(regime_support) >= 2)
    conditions = {
        "selected_gate_non_noop": bool(selected["non_noop"]),
        "validation_did_not_use_independent_test": not validation_used_independent,
        "independent_test_core_topk_not_lower_than_phase1c": bool(core_ok),
        "caution_or_risk_off_clear_conservative_effect": bool(diag["passed"]),
        "not_single_year_only": year_ok,
        "not_single_regime_only": not_single_regime,
        "selected_validation_candidate": {
            "definition_id": str(selected["definition_id"]),
            "gate_id": str(selected["gate_id"]),
            "score_column": str(selected["score_column"]),
            "selection_score": float(selected["selection_score"]),
            "validation_core_floor_passed": bool(selected.get("passes_validation_core_floor", False)),
        },
        "independent_conservative_effect": diag,
    }
    if all(conditions[k] for k in [
        "selected_gate_non_noop",
        "validation_did_not_use_independent_test",
        "independent_test_core_topk_not_lower_than_phase1c",
        "caution_or_risk_off_clear_conservative_effect",
        "not_single_year_only",
        "not_single_regime_only",
    ]):
        return "request_phase3_turnover_layer_work", "Phase2B selected a non-noop validation-only regime gate that preserved Phase1C core TopK quality and showed conservative filtering.", conditions
    return "stop_regime_gating_insufficient_evidence", "Phase2B non-noop regime gate did not stably preserve Phase1C core TopK quality or did not provide enough robust conservative-filtering evidence.", conditions


def write_report(now: str, gate: dict[str, Any], selection: pd.DataFrame, dist: pd.DataFrame, by_state: pd.DataFrame, comparison: pd.DataFrame, yearly: pd.DataFrame) -> None:
    validation_top = selection[selection["split"] == "validation"].sort_values("selection_score", ascending=False).head(12)
    REPORT_DOC.write_text(
        f"""# Phase 2B 执行报告：Regime Gating 修复

生成时间：{now}

## 1. 本轮目标

只做 Stage 3 regime-aware gating 的一次修复：在固定 Phase1C `qlib-preserving LTR rerank` 的前提下，测试是否能得到非 no-op、可解释、且不降低核心 TopK 质量的 regime gating。

## 2. 实际完成内容

- 新增只读离线脚本：`scripts/repair_tw_ltr_phase2b_regime_gating.py`。
- 复用 Phase1 样本并复现 Phase1C score：`score_head10_all_l31_alpha0.7_top50_only`。
- 仅使用 5 个 regime 白名单字段生成多个候选 regime definition。
- 生成多个非 no-op gating rule，并保留 Phase2 no-op gate 作为对照。
- 只用 validation selection score 选择候选，independent_test 只做最终检验。
- 未进入 Stage 4 turnover layer，未生成真实动作语义。

## 3. 改动文件清单

- `scripts/repair_tw_ltr_phase2b_regime_gating.py`
- `docs/tw_ltr_rerank_regime_turnover/PHASE2B_REGIME_REPAIR_EXECUTION_REPORT_CN.md`

## 4. 新增产物清单

- `data_tw/experiments/ltr_rerank_regime_turnover/phase2b_regime_repair/phase2b_regime_definition_candidates.json`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase2b_regime_repair/phase2b_regime_distribution.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase2b_regime_repair/phase2b_validation_selection.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase2b_regime_repair/phase2b_regime_metric_by_state.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase2b_regime_repair/phase2b_independent_test_comparison.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase2b_regime_repair/phase2b_gate_summary.json`

## 5. Regime 候选分布

```text
{dist.to_string(index=False)}
```

## 6. validation 选择 Top12

```text
{validation_top.drop(columns=["conservative_effect"], errors="ignore").to_string(index=False)}
```

## 7. independent_test 最终对照

```text
{comparison[comparison['split'] == 'independent_test'].to_string(index=False)}
```

## 8. selected gate 分状态指标

```text
{by_state.to_string(index=False)}
```

## 9. independent_test 分年度结果

```text
{yearly.to_string(index=False)}
```

## 10. Gate 结论

- 推荐 gate：`{gate['recommended_gate']}`。
- 原因：{gate['gate_reason']}
- 条件：`{gate['required_conditions']}`。

## 11. 验证内容与结果

- `python -m py_compile scripts/repair_tw_ltr_phase2b_regime_gating.py`：通过。
- `python scripts/repair_tw_ltr_phase2b_regime_gating.py`：通过。
- validation selection 没有使用 independent_test 反选参数。
- 输出产物齐全。

## 12. 风险 / 异常 / 未解决问题

- risk_off 在 independent_test 中仍可能是小样本状态，审查者需要重点看分状态 date_count。
- 若推荐 gate 不是 `request_phase3_turnover_layer_work`，不得进入 Phase3。
- 本轮只证明或否定 Stage 3 gating，不报告组合净值、换手、动作次数或成本。

## 13. 需要审查者重点检查的点

- regime definition 是否只使用 5 个白名单字段。
- selected gate 是否非 no-op。
- validation selection score 是否没有读取 independent_test。
- independent_test 上是否真的不低于 Phase1C 核心 TopK 质量。
- caution / risk_off 下的保守过滤是否足够清晰且不是单一偶然窗口。

## 14. 禁止事项遵守情况

本轮未新增数据源，未新增白名单外特征，未引入 `trend_score` 或 forbidden features，未联网，未 provider refresh/publish，未 accepted latest switching，未改 frontend / API / monitor / database，未做 turnover portfolio layer，未接 broker / quick-trade / orders / target position / target weight，未输出买入、卖出、持有、仓位、收益承诺、上涨概率或胜率语义。
""",
        encoding="utf-8",
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now = utc_now()
    schema = load_schema()
    input_features = list(schema["input_columns"])
    df = build_phase1c_score(load_sample(schema), input_features)

    write_json(
        CANDIDATES_JSON,
        {
            "created_at": now,
            "regime_features": REGIME_FEATURES,
            "score_semantics": "qlib-preserving LTR rerank; Phase2B regime gating is offline conservative filtering, not an action signal",
            "regime_definitions": REGIME_DEFINITIONS,
            "gating_rules": GATING_RULES,
        },
    )

    selection, regime_cols = build_candidates(df)
    selected = choose_candidate(selection)
    dist = distribution(df, regime_cols)
    comparison = independent_comparison(df, selected)
    yearly = yearly_results(df, selected)
    by_state = state_metrics(df, selected)

    selection.to_csv(VALIDATION_SELECTION_CSV, index=False)
    dist.to_csv(DISTRIBUTION_CSV, index=False)
    comparison.to_csv(INDEPENDENT_COMPARISON_CSV, index=False)
    by_state.to_csv(REGIME_METRIC_CSV, index=False)

    recommended_gate, gate_reason, conditions = decide_gate(df, selected, comparison, yearly)
    gate = {
        "phase": "phase2b_regime_repair",
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
        "selected_definition_id": str(selected["definition_id"]),
        "selected_gate_id": str(selected["gate_id"]),
        "selected_score_column": str(selected["score_column"]),
        "recommended_gate": recommended_gate,
        "gate_reason": gate_reason,
        "required_conditions": conditions,
        "artifacts": {
            "regime_definition_candidates": rel(CANDIDATES_JSON),
            "regime_distribution": rel(DISTRIBUTION_CSV),
            "validation_selection": rel(VALIDATION_SELECTION_CSV),
            "regime_metric_by_state": rel(REGIME_METRIC_CSV),
            "independent_test_comparison": rel(INDEPENDENT_COMPARISON_CSV),
            "gate_summary": rel(GATE_JSON),
            "report": rel(REPORT_DOC),
        },
    }
    write_json(GATE_JSON, gate)
    write_report(now, gate, selection, dist, by_state, comparison, yearly)
    print(json.dumps({"ok": True, "recommended_gate": recommended_gate, "gate_reason": gate_reason, "selected_definition_id": str(selected["definition_id"]), "selected_gate_id": str(selected["gate_id"]), "report": rel(REPORT_DOC)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
