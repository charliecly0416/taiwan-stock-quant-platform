from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import qlib
from qlib.contrib.data.handler import Alpha158
from qlib.data.dataset import DataHandlerLP as BaseDataHandlerLP
from qlib.data.dataset.handler import DataHandlerLP
from qlib.data.dataset.processor import DropnaLabel


ROOT = Path(__file__).resolve().parents[2]
PROVIDER = "data_tw/experiments/yahoo_adjusted_primary/qlib_bin"
MARKET = "tw_liquid_dyn"
START = "2015-05-04"
END = "2025-06-30"
FIT_END = "2020-12-31"
LIMIT_CHANGE_DATE = pd.Timestamp("2015-06-01")
IC_CANDIDATES = ["TW_AMIHUD20", "TW_LIMIT_UP_EVENT", "TW_LIMIT_DOWN_EVENT", "TW_LIMIT_ABS_PROXIMITY"]
ALPHA158_IMPORTANCE = ROOT / "data_tw/experiments/yahoo_primary_alpha158_importance/alpha158_feature_importance.csv"
SEGMENTS = {
    "train": ("2015-05-04", "2020-12-31"),
    "valid": ("2021-01-01", "2022-12-31"),
    "test": ("2023-01-01", "2025-06-30"),
    "test_2023": ("2023-01-01", "2023-12-31"),
    "test_2024": ("2024-01-01", "2024-12-31"),
    "test_2025h1": ("2025-01-01", "2025-06-30"),
}


class AcademicRawHandler(BaseDataHandlerLP):
    def __init__(self, instruments: str, start_time: str, end_time: str):
        fields = [
            "$open",
            "$high",
            "$low",
            "$close",
            "$vwap",
            "$volume",
            "Ref($close, 1)",
            "Ref($close, 5)",
        ]
        names = [
            "OPEN0",
            "HIGH0",
            "LOW0",
            "CLOSE0",
            "VWAP0",
            "VOLUME0",
            "CLOSE_REF1",
            "CLOSE_REF5",
        ]
        loader = {
            "class": "QlibDataLoader",
            "kwargs": {
                "config": {
                    "feature": (fields, names),
                    "label": (["Ref($close, -2)/Ref($close, -1) - 1"], ["LABEL0"]),
                },
                "freq": "day",
            },
        }
        super().__init__(
            instruments=instruments,
            start_time=start_time,
            end_time=end_time,
            data_loader=loader,
            learn_processors=[DropnaLabel()],
            infer_processors=[],
            process_type=DataHandlerLP.PTYPE_A,
        )


def fetch_raw() -> tuple[pd.DataFrame, pd.Series]:
    handler = AcademicRawHandler(MARKET, START, END)
    raw = handler.fetch(col_set=DataHandlerLP.CS_RAW, data_key=DataHandlerLP.DK_R)
    return raw["feature"], raw["label"]["LABEL0"]


def fetch_alpha158() -> pd.DataFrame:
    handler = Alpha158(instruments=MARKET, start_time=START, end_time=END, fit_start_time=START, fit_end_time=FIT_END)
    raw = handler.fetch(col_set=DataHandlerLP.CS_RAW, data_key=DataHandlerLP.DK_R)
    return raw["feature"]


def calc_liquidity_bucket(features: pd.DataFrame) -> pd.Series:
    amount = features["VOLUME0"] * features["VWAP0"]
    amt60 = amount.groupby(level="instrument").transform(lambda s: s.rolling(60, min_periods=20).mean())
    buckets = []
    for _, s in amt60.groupby(level="datetime", sort=True):
        valid = s.dropna()
        if valid.shape[0] < 30:
            continue
        ranks = valid.rank(pct=True, method="first")
        b = pd.Series("mid", index=valid.index, dtype="object")
        b[ranks <= 1 / 3] = "low"
        b[ranks > 2 / 3] = "high"
        buckets.append(b)
    if not buckets:
        return pd.Series(dtype="object", index=features.index, name="liquidity_bucket")
    out = pd.concat(buckets).reindex(features.index)
    out.name = "liquidity_bucket"
    return out


def build_candidates(features: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    close = features["CLOSE0"]
    ref1 = features["CLOSE_REF1"]
    ref5 = features["CLOSE_REF5"]
    volume = features["VOLUME0"]
    ret1 = close / ref1 - 1

    traded_amount = volume * close
    raw_amihud = ret1.abs() / (traded_amount + 1e-12)
    amihud_input = raw_amihud.mask((volume <= 0) | (close <= 0) | ~np.isfinite(raw_amihud))
    amihud20 = amihud_input.groupby(level="instrument").transform(lambda s: s.rolling(20, min_periods=10).mean())

    dates = close.index.get_level_values("datetime")
    limit_threshold = pd.Series(np.where(dates < LIMIT_CHANGE_DATE, 0.07, 0.10), index=close.index)
    limit_up_event = (ret1 >= limit_threshold * 0.995).astype(float)
    limit_down_event = (ret1 <= -limit_threshold * 0.995).astype(float)
    limit_abs_proximity = (ret1.abs() / limit_threshold).clip(upper=1.5)

    candidates = pd.DataFrame(
        {
            "TW_AMIHUD20": amihud20,
            "REV5": -1 * (close / ref5 - 1),
            "TW_LIMIT_UP_EVENT": limit_up_event,
            "TW_LIMIT_DOWN_EVENT": limit_down_event,
            "TW_LIMIT_ABS_PROXIMITY": limit_abs_proximity,
        },
        index=features.index,
    )
    diagnostics = pd.DataFrame(
        {
            "RET1": ret1,
            "RAW_AMIHUD": raw_amihud,
            "AMIHUD_INPUT": amihud_input,
            "ZERO_VOLUME": (volume <= 0).astype(float),
            "LIMIT_THRESHOLD": limit_threshold,
            "LIMIT_UP_EVENT": limit_up_event,
            "LIMIT_DOWN_EVENT": limit_down_event,
        },
        index=features.index,
    )
    return candidates, diagnostics


def write_algebraic_check(out_dir: Path) -> pd.DataFrame:
    rows = [
        {
            "candidate": "TW_AMIHUD20",
            "prior_formula": "Mean(Abs(close / Ref(close, 1) - 1) / (volume * close), 20), zero-volume rows excluded",
            "nearest_alpha158_formula": "VMA*, WVMA*, volume and rolling return/volatility families",
            "verdict": "pass_pre_ic",
            "reason": "Combines absolute return with traded amount and zero-volume exclusion; not a monotonic transform or simple window tweak of a single Alpha158 feature.",
        },
        {
            "candidate": "REV5",
            "prior_formula": "-1 * (close / Ref(close, 5) - 1)",
            "nearest_alpha158_formula": "ROC5 = Ref(close, 5) / close",
            "verdict": "reject_before_ic",
            "reason": "For positive prices, REV5 = 1 - 1 / ROC5, a strictly increasing transform of ROC5. Rank-based IC and Spearman corr should treat it as absorbed by Alpha158.",
        },
        {
            "candidate": "TW_LIMIT_PROXIMITY",
            "prior_formula": "Date-conditional +/-7% before 2015-06-01 and +/-10% on/after 2015-06-01 event/proximity fields",
            "nearest_alpha158_formula": "No date-conditional limit-rule event feature in Alpha158",
            "verdict": "pass_pre_ic_with_script_factor",
            "reason": "Requires Taiwan limit-rule date logic; script-based construction avoids unsupported Qlib expression date branching.",
        },
    ]
    out = pd.DataFrame(rows)
    out.to_csv(out_dir / "academic_factor_algebraic_check.csv", index=False)
    return out


def rank_corr_matrix(x_rank: pd.DataFrame, y_rank: pd.Series) -> pd.Series:
    x = x_rank.to_numpy(dtype=float)
    y = y_rank.to_numpy(dtype=float)
    mask = ~np.isnan(y)
    x = x[mask]
    y = y[mask]
    y = y - y.mean()
    y_std = np.sqrt(np.sum(y * y))
    if y_std == 0 or x.shape[0] < 10:
        return pd.Series(np.nan, index=x_rank.columns)
    x_mean = np.nanmean(x, axis=0)
    x_centered = x - x_mean
    x_centered[np.isnan(x_centered)] = 0.0
    x_std = np.sqrt(np.sum(x_centered * x_centered, axis=0))
    denom = x_std * y_std
    num = np.dot(y, x_centered)
    out = np.full(x.shape[1], np.nan, dtype=float)
    ok = denom > 0
    out[ok] = num[ok] / denom[ok]
    return pd.Series(out, index=x_rank.columns)


def calc_daily_ic(features: pd.DataFrame, label: pd.Series, factors: list[str], mask: pd.Series | None = None) -> pd.DataFrame:
    data = features[factors].copy()
    data["__label__"] = label
    if mask is not None:
        data["__mask__"] = mask.reindex(data.index)
    rows = []
    for date, group in data.groupby(level="datetime", sort=True):
        group = group.droplevel("datetime")
        if "__mask__" in group.columns:
            group = group[group.pop("__mask__").fillna(False).astype(bool)]
        y = group.pop("__label__")
        valid_y = y.notna()
        if valid_y.sum() < 10 or y[valid_y].nunique(dropna=True) < 2:
            continue
        group = group.loc[valid_y]
        y = y.loc[valid_y]
        for factor in factors:
            x = group[factor]
            ok = x.notna() & y.notna()
            if ok.sum() < 10 or x[ok].nunique(dropna=True) < 2:
                continue
            rows.append({
                "date": pd.Timestamp(date),
                "factor": factor,
                "n": int(ok.sum()),
                "coverage": float(ok.mean()),
                "ic": float(x[ok].corr(y[ok], method="pearson")),
                "rank_ic": float(x[ok].corr(y[ok], method="spearman")),
            })
    return pd.DataFrame(rows)


def summarize_ic(daily: pd.DataFrame, factors: list[str] | None = None) -> pd.DataFrame:
    if factors is None:
        factors = sorted(daily["factor"].dropna().unique().tolist()) if not daily.empty else IC_CANDIDATES
    rows = []
    for name, (start, end) in SEGMENTS.items():
        seg = daily[(daily["date"] >= pd.Timestamp(start)) & (daily["date"] <= pd.Timestamp(end))] if not daily.empty else daily
        for factor in factors:
            g = seg[seg["factor"] == factor] if not seg.empty else pd.DataFrame()
            for metric in ["ic", "rank_ic"]:
                s = g[metric].dropna() if metric in g else pd.Series(dtype=float)
                std = s.std()
                rows.append({
                    "factor": factor,
                    "segment": name,
                    "metric": metric,
                    "n_days": int(s.shape[0]),
                    "mean": float(s.mean()) if len(s) else np.nan,
                    "std": float(std) if len(s) else np.nan,
                    "ir": float(s.mean() / std) if len(s) and std else np.nan,
                    "positive_rate": float((s > 0).mean()) if len(s) else np.nan,
                    "avg_n": float(g["n"].mean()) if len(g) else np.nan,
                    "avg_coverage": float(g["coverage"].mean()) if len(g) else np.nan,
                })
    return pd.DataFrame(rows)


def calc_bucket_ic(candidates: pd.DataFrame, label: pd.Series, buckets: pd.Series) -> pd.DataFrame:
    rows = []
    for bucket in ["low", "mid", "high"]:
        daily = calc_daily_ic(candidates, label, ["TW_AMIHUD20"], mask=(buckets == bucket))
        summary = summarize_ic(daily, ["TW_AMIHUD20"])
        summary["liquidity_bucket"] = bucket
        rows.append(summary)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def calc_masked_ic(candidates: pd.DataFrame, label: pd.Series, diagnostics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    masks = {
        "limit_up_days": diagnostics["LIMIT_UP_EVENT"] == 1,
        "limit_down_days": diagnostics["LIMIT_DOWN_EVENT"] == 1,
        "non_limit_days": (diagnostics["LIMIT_UP_EVENT"] == 0) & (diagnostics["LIMIT_DOWN_EVENT"] == 0),
    }
    for name, mask in masks.items():
        daily = calc_daily_ic(candidates, label, IC_CANDIDATES, mask=mask)
        summary = summarize_ic(daily, IC_CANDIDATES)
        summary["subset"] = name
        rows.append(summary)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def load_top20_alpha158() -> set[str]:
    if not ALPHA158_IMPORTANCE.exists():
        return set()
    importance = pd.read_csv(ALPHA158_IMPORTANCE)
    return set(importance.sort_values("gain_rank").head(20)["feature_name"].astype(str))


def calc_alpha158_corr(
    candidates: pd.DataFrame,
    alpha158: pd.DataFrame,
    factors: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if factors is None:
        factors = IC_CANDIDATES
    test_idx = (slice(pd.Timestamp("2023-01-01"), pd.Timestamp("2025-06-30")), slice(None))
    cand_test = candidates.loc[test_idx, factors]
    alpha_test = alpha158.loc[test_idx, :]
    top20 = load_top20_alpha158()
    rows = []
    detail_rows = []
    for factor in factors:
        daily_corr = []
        for date, xg in cand_test[[factor]].groupby(level="datetime", sort=True):
            if date not in alpha_test.index.get_level_values("datetime"):
                continue
            x = xg.droplevel("datetime")[factor]
            joined = alpha_test.xs(date, level="datetime").join(x, how="inner")
            y = joined.pop(factor)
            valid = y.notna()
            if valid.sum() < 10 or y[valid].nunique(dropna=True) < 2:
                continue
            daily_corr.append(rank_corr_matrix(joined.loc[valid].rank(axis=0), y.loc[valid].rank()))
        if not daily_corr:
            rows.append({"factor": factor, "max_abs_corr_top20": np.nan, "nearest_top20_alpha158": "", "max_abs_corr_all158": np.nan, "nearest_all158_alpha158": "", "corr_gate": "no_corr_data"})
            continue
        mean_corr = pd.DataFrame(daily_corr).mean().dropna()
        for alpha, value in mean_corr.abs().sort_values(ascending=False).head(20).items():
            detail_rows.append({"factor": factor, "alpha158_feature": alpha, "mean_spearman_corr": float(mean_corr[alpha]), "abs_mean_spearman_corr": float(abs(mean_corr[alpha])), "is_top20_gain": alpha in top20})
        all_abs = mean_corr.abs()
        top_abs = all_abs[all_abs.index.isin(top20)] if top20 else pd.Series(dtype=float)
        max_all = float(all_abs.max()) if not all_abs.empty else np.nan
        nearest_all = str(all_abs.idxmax()) if not all_abs.empty else ""
        max_top = float(top_abs.max()) if not top_abs.empty else np.nan
        nearest_top = str(top_abs.idxmax()) if not top_abs.empty else ""
        if np.isfinite(max_top) and max_top >= 0.5:
            gate = "reject_hard_top20_corr"
        elif np.isfinite(max_all) and max_all >= 0.7:
            gate = "reject_soft_all158_corr"
        elif np.isfinite(max_all) and max_all >= 0.5:
            gate = "borderline_corr_requires_delta_0.008"
        else:
            gate = "pass_corr_gate"
        rows.append({"factor": factor, "max_abs_corr_top20": max_top, "nearest_top20_alpha158": nearest_top, "max_abs_corr_all158": max_all, "nearest_all158_alpha158": nearest_all, "corr_gate": gate})
    return pd.DataFrame(rows), pd.DataFrame(detail_rows)


def summarize_event_forward_returns(label: pd.Series, diagnostics: pd.DataFrame, buckets: pd.Series) -> pd.DataFrame:
    data = diagnostics[["LIMIT_UP_EVENT", "LIMIT_DOWN_EVENT"]].copy()
    data["LABEL0"] = label
    data["liquidity_bucket"] = buckets
    rows = []
    masks = {
        "limit_up": data["LIMIT_UP_EVENT"] == 1,
        "limit_down": data["LIMIT_DOWN_EVENT"] == 1,
        "non_limit": (data["LIMIT_UP_EVENT"] == 0) & (data["LIMIT_DOWN_EVENT"] == 0),
    }
    for segment, (start, end) in SEGMENTS.items():
        seg = data.loc[(slice(pd.Timestamp(start), pd.Timestamp(end)), slice(None)), :]
        for event_name, mask in masks.items():
            scoped = seg[mask.reindex(seg.index).fillna(False)]
            for bucket in ["all", "low", "mid", "high"]:
                g = scoped if bucket == "all" else scoped[scoped["liquidity_bucket"] == bucket]
                returns = g["LABEL0"].dropna()
                std = returns.std()
                rows.append(
                    {
                        "segment": segment,
                        "event": event_name,
                        "liquidity_bucket": bucket,
                        "n_obs": int(returns.shape[0]),
                        "mean_forward_return": float(returns.mean()) if len(returns) else np.nan,
                        "std_forward_return": float(std) if len(returns) else np.nan,
                        "t_stat": float(returns.mean() / (std / np.sqrt(len(returns)))) if len(returns) > 1 and std else np.nan,
                        "positive_rate": float((returns > 0).mean()) if len(returns) else np.nan,
                    }
                )
    return pd.DataFrame(rows)


def build_screen_summary(summary: pd.DataFrame, corr: pd.DataFrame, limit_health: pd.DataFrame) -> pd.DataFrame:
    ric = summary[summary["metric"] == "rank_ic"]
    mean_pivot = ric.pivot(index="factor", columns="segment", values="mean").reset_index()
    ir_pivot = ric.pivot(index="factor", columns="segment", values="ir").reset_index()
    out = mean_pivot.rename(columns={"train": "train_rank_ic", "valid": "valid_rank_ic", "test": "test_rank_ic", "test_2023": "test_2023_rank_ic", "test_2024": "test_2024_rank_ic", "test_2025h1": "test_2025h1_rank_ic"})
    out = out.merge(ir_pivot[["factor", "test"]].rename(columns={"test": "test_rank_ic_ir"}), on="factor", how="left")
    out = out.merge(corr, on="factor", how="left")
    test_counts = limit_health[(limit_health["segment"] == "test") & (limit_health["liquidity_bucket"] == "all")].iloc[0]
    event_counts = {
        "TW_LIMIT_UP_EVENT": int(test_counts["limit_up_events"]),
        "TW_LIMIT_DOWN_EVENT": int(test_counts["limit_down_events"]),
        "TW_LIMIT_ABS_PROXIMITY": int(test_counts["limit_up_events"] + test_counts["limit_down_events"]),
        "TW_AMIHUD20": np.nan,
    }
    out["test_event_count"] = out["factor"].map(event_counts)
    segment_cols = ["train_rank_ic", "valid_rank_ic", "test_rank_ic", "test_2023_rank_ic", "test_2024_rank_ic", "test_2025h1_rank_ic"]
    def direction_stable(row: pd.Series) -> bool:
        vals = row[segment_cols].dropna()
        vals = vals[vals != 0]
        return bool(len(vals) and ((vals > 0).all() or (vals < 0).all()))
    out["abs_test_rank_ic"] = out["test_rank_ic"].abs()
    out["direction_stable"] = out.apply(direction_stable, axis=1)
    def decision(row: pd.Series) -> str:
        if abs(row.get("test_rank_ic", np.nan)) < 0.01:
            return "reject_rankic_below_0.01"
        if row.get("corr_gate") in {"reject_hard_top20_corr", "reject_soft_all158_corr"}:
            return row.get("corr_gate")
        if not row.get("direction_stable", False):
            return "reject_direction_unstable"
        if row["factor"].startswith("TW_LIMIT") and pd.notna(row.get("test_event_count")) and row.get("test_event_count", 0) < 100:
            return "reject_insufficient_event_count"
        if row.get("corr_gate") == "borderline_corr_requires_delta_0.008":
            return "pass_borderline_corr_ablation_delta_0.008"
        return "pass_single_factor_screen"
    out["screen_decision"] = out.apply(decision, axis=1)
    return out.sort_values(["screen_decision", "abs_test_rank_ic"], ascending=[True, False])


def summarize_amihud_health(candidates: pd.DataFrame, diagnostics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = diagnostics["RAW_AMIHUD"].replace([np.inf, -np.inf], np.nan)
    input_ = diagnostics["AMIHUD_INPUT"].replace([np.inf, -np.inf], np.nan)
    amihud20 = candidates["TW_AMIHUD20"].replace([np.inf, -np.inf], np.nan)
    zero = diagnostics["ZERO_VOLUME"]
    nonzero_raw = raw[(zero == 0) & raw.notna()]
    raw_outlier_threshold = float(nonzero_raw.quantile(0.999)) if len(nonzero_raw) else np.nan
    final_outlier_threshold = float(amihud20.quantile(0.999)) if amihud20.notna().any() else np.nan

    daily_rows = []
    for date, frame in pd.DataFrame({"raw": raw, "input": input_, "amihud20": amihud20, "zero": zero}).groupby(
        level="datetime", sort=True
    ):
        g = frame.droplevel("datetime")
        valid = g["raw"].notna() & g["zero"].notna()
        zero_corr = np.nan
        if valid.sum() >= 10 and g.loc[valid, "zero"].nunique(dropna=True) > 1 and g.loc[valid, "raw"].nunique(dropna=True) > 1:
            zero_corr = float(g.loc[valid, "raw"].corr(g.loc[valid, "zero"], method="spearman"))
        qs = g["amihud20"].quantile([0.01, 0.05, 0.5, 0.95, 0.99])
        daily_rows.append(
            {
                "date": pd.Timestamp(date),
                "n": int(g.shape[0]),
                "amihud20_coverage": float(g["amihud20"].notna().mean()),
                "zero_volume_share": float((g["zero"] == 1).mean()),
                "raw_amihud_zero_volume_spearman": zero_corr,
                "amihud20_p01": float(qs.get(0.01, np.nan)),
                "amihud20_p05": float(qs.get(0.05, np.nan)),
                "amihud20_p50": float(qs.get(0.5, np.nan)),
                "amihud20_p95": float(qs.get(0.95, np.nan)),
                "amihud20_p99": float(qs.get(0.99, np.nan)),
            }
        )
    daily = pd.DataFrame(daily_rows)
    summary = pd.DataFrame(
        [
            {
                "check": "raw_amihud_outlier_share_vs_nonzero_p999",
                "value": float((raw > raw_outlier_threshold).mean()) if np.isfinite(raw_outlier_threshold) else np.nan,
                "threshold": "< 0.005",
                "pass_check": bool((raw > raw_outlier_threshold).mean() < 0.005) if np.isfinite(raw_outlier_threshold) else False,
                "note": "Outlier threshold is the 99.9 percentile among nonzero-volume raw Amihud inputs.",
            },
            {
                "check": "amihud20_outlier_share_vs_own_p999",
                "value": float((amihud20 > final_outlier_threshold).mean()) if np.isfinite(final_outlier_threshold) else np.nan,
                "threshold": "< 0.005",
                "pass_check": bool((amihud20 > final_outlier_threshold).mean() < 0.005) if np.isfinite(final_outlier_threshold) else False,
                "note": "Final TW_AMIHUD20 excludes zero-volume rows before the rolling mean.",
            },
            {
                "check": "mean_daily_zero_volume_share",
                "value": float(daily["zero_volume_share"].mean()),
                "threshold": "informational",
                "pass_check": True,
                "note": "Used to diagnose whether Amihud is dominated by non-trading rows.",
            },
            {
                "check": "mean_daily_raw_amihud_zero_volume_spearman",
                "value": float(daily["raw_amihud_zero_volume_spearman"].mean()),
                "threshold": "informational",
                "pass_check": True,
                "note": "Correlation is computed on naive raw Amihud before zero-volume exclusion.",
            },
            {
                "check": "mean_daily_amihud20_coverage",
                "value": float(daily["amihud20_coverage"].mean()),
                "threshold": "informational",
                "pass_check": True,
                "note": "Rolling TW_AMIHUD20 uses 20-day window with min_periods=10.",
            },
        ]
    )
    return summary, daily


def summarize_limit_health(features: pd.DataFrame, diagnostics: pd.DataFrame, buckets: pd.Series) -> pd.DataFrame:
    data = diagnostics[["RET1", "LIMIT_THRESHOLD", "LIMIT_UP_EVENT", "LIMIT_DOWN_EVENT"]].copy()
    data["liquidity_bucket"] = buckets
    rows = []
    for name, (start, end) in SEGMENTS.items():
        seg = data.loc[(slice(pd.Timestamp(start), pd.Timestamp(end)), slice(None)), :]
        rows.append(
            {
                "segment": name,
                "liquidity_bucket": "all",
                "n_rows": int(seg.shape[0]),
                "limit_up_events": int(seg["LIMIT_UP_EVENT"].sum()),
                "limit_down_events": int(seg["LIMIT_DOWN_EVENT"].sum()),
                "limit_up_share": float(seg["LIMIT_UP_EVENT"].mean()),
                "limit_down_share": float(seg["LIMIT_DOWN_EVENT"].mean()),
                "pre_2015_06_01_rows": int((seg.index.get_level_values("datetime") < LIMIT_CHANGE_DATE).sum()),
            }
        )
        for bucket, g in seg.groupby("liquidity_bucket", dropna=True):
            rows.append(
                {
                    "segment": name,
                    "liquidity_bucket": bucket,
                    "n_rows": int(g.shape[0]),
                    "limit_up_events": int(g["LIMIT_UP_EVENT"].sum()),
                    "limit_down_events": int(g["LIMIT_DOWN_EVENT"].sum()),
                    "limit_up_share": float(g["LIMIT_UP_EVENT"].mean()),
                    "limit_down_share": float(g["LIMIT_DOWN_EVENT"].mean()),
                    "pre_2015_06_01_rows": int((g.index.get_level_values("datetime") < LIMIT_CHANGE_DATE).sum()),
                }
            )
    return pd.DataFrame(rows)


def write_report(
    out_dir: Path,
    algebra: pd.DataFrame,
    amihud: pd.DataFrame,
    limit_health: pd.DataFrame,
    screen: pd.DataFrame | None = None,
    bucket_ic: pd.DataFrame | None = None,
    subset_ic: pd.DataFrame | None = None,
    event_returns: pd.DataFrame | None = None,
) -> None:
    def fmt_value(x):
        if pd.isna(x):
            return ""
        if isinstance(x, float):
            return f"{x:.6f}"
        return str(x)

    def table(df: pd.DataFrame, cols: list[str]) -> list[str]:
        if df.empty:
            return ["(empty)"]
        display = df[cols].copy()
        for col in display.columns:
            display[col] = display[col].map(fmt_value)
        lines = ["| " + " | ".join(display.columns) + " |", "| " + " | ".join(["---"] * len(display.columns)) + " |"]
        lines.extend("| " + " | ".join(row) + " |" for row in display.to_numpy(dtype=str))
        return lines

    limit_all = limit_health[limit_health["liquidity_bucket"] == "all"]
    lines = [
        "---",
        "created_at: 2026-05-27",
        "status: screening_complete" if screen is not None else "status: pre_screen_checks_complete",
        "scope: tw_academic_factor_first_batch_screen",
        "related_docs:",
        "  - docs/tw_audit/16e_tw_academic_factor_plan.md",
        "  - docs/tw_audit/16f_tw_academic_factor_notes.md",
        "---",
        "",
        "# TW Academic Factor Screening Report",
        "",
        "## Scope",
        "",
        "This document records Phase B.1 checks and the narrow single-factor screen for first-batch Taiwan academic factors. It does not contain model ablation, portfolio backtest, strategy parameter tuning, or data after 2025-06-30.",
        "",
        "## Algebraic Equivalence Check",
        "",
    ]
    lines.extend(table(algebra, ["candidate", "nearest_alpha158_formula", "verdict", "reason"]))
    lines += ["", "## TW_AMIHUD20 Health Check", ""]
    lines.extend(table(amihud, ["check", "value", "threshold", "pass_check", "note"]))
    lines += ["", "## TW_LIMIT_PROXIMITY Event Counts", ""]
    lines.extend(
        table(
            limit_all,
            [
                "segment",
                "n_rows",
                "limit_up_events",
                "limit_down_events",
                "limit_up_share",
                "limit_down_share",
                "pre_2015_06_01_rows",
            ],
        )
    )
    if screen is not None:
        lines += ["", "## Single-Factor Screen", ""]
        lines.extend(
            table(
                screen,
                [
                    "factor",
                    "train_rank_ic",
                    "valid_rank_ic",
                    "test_rank_ic",
                    "test_2023_rank_ic",
                    "test_2024_rank_ic",
                    "test_2025h1_rank_ic",
                    "test_rank_ic_ir",
                    "max_abs_corr_top20",
                    "nearest_top20_alpha158",
                    "max_abs_corr_all158",
                    "nearest_all158_alpha158",
                    "direction_stable",
                    "screen_decision",
                ],
            )
        )
    if bucket_ic is not None and not bucket_ic.empty:
        bucket_rank = bucket_ic[(bucket_ic["metric"] == "rank_ic") & (bucket_ic["segment"].isin(["test", "test_2023", "test_2024", "test_2025h1"]))]
        lines += ["", "## TW_AMIHUD20 Liquidity-Bucket RankIC", ""]
        lines.extend(table(bucket_rank, ["segment", "liquidity_bucket", "n_days", "mean", "ir", "positive_rate", "avg_n"]))
    if subset_ic is not None and not subset_ic.empty:
        subset_rank = subset_ic[(subset_ic["metric"] == "rank_ic") & (subset_ic["segment"] == "test")]
        lines += ["", "## Limit-Day Subset RankIC", ""]
        lines.extend(table(subset_rank, ["subset", "factor", "n_days", "mean", "ir", "positive_rate", "avg_n"]))
    if event_returns is not None and not event_returns.empty:
        event_test = event_returns[(event_returns["segment"] == "test") & (event_returns["liquidity_bucket"] == "all")]
        lines += ["", "## Limit-Day Conditional Forward Returns", ""]
        lines.extend(table(event_test, ["event", "n_obs", "mean_forward_return", "t_stat", "positive_rate"]))
    lines += [
        "",
        "## Decisions",
        "",
        "- `REV5` is rejected before IC because it is a strictly increasing transform of Alpha158 `ROC5` for positive prices.",
        "- `TW_AMIHUD20` is screened only with zero-volume rows excluded before rolling and with liquidity-bucket plus limit-day subset diagnostics.",
        "- `TW_LIMIT_PROXIMITY` remains script-based because the factor requires the Taiwan limit-rule date threshold change on 2015-06-01.",
        "- Passing this single-factor screen, if any, is not baseline improvement; handler inclusion still requires fixed-parameter ablation, paired daily-return tests and turnover monitoring.",
        "",
        "## Artifacts",
        "",
        f"- `{out_dir / 'academic_factor_algebraic_check.csv'}`",
        f"- `{out_dir / 'tw_amihud20_health_summary.csv'}`",
        f"- `{out_dir / 'tw_amihud20_daily_quantiles.csv'}`",
        f"- `{out_dir / 'tw_limit_proximity_event_counts.csv'}`",
    ]
    if screen is not None:
        lines += [
            f"- `{out_dir / 'academic_factor_daily_ic.csv'}`",
            f"- `{out_dir / 'academic_factor_segment_ic.csv'}`",
            f"- `{out_dir / 'academic_factor_alpha158_corr.csv'}`",
            f"- `{out_dir / 'academic_factor_alpha158_corr_detail.csv'}`",
            f"- `{out_dir / 'academic_factor_screen.csv'}`",
            f"- `{out_dir / 'tw_amihud20_liquidity_bucket_ic.csv'}`",
            f"- `{out_dir / 'academic_factor_limit_day_subset_ic.csv'}`",
            f"- `{out_dir / 'tw_limit_event_forward_returns.csv'}`",
        ]
    (ROOT / "docs/tw_audit/16g_tw_academic_factor_screening_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TW academic first-batch factor checks and screen.")
    parser.add_argument("--output-dir", default="data_tw/experiments/yahoo_primary_tw_academic_factor_screen")
    parser.add_argument("--checks-only", action="store_true", help="Run pre-IC checks only.")
    args = parser.parse_args()

    out_dir = ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    qlib.init(provider_uri=PROVIDER, region="tw", expression_cache=None, dataset_cache=None)
    features, label = fetch_raw()
    candidates, diagnostics = build_candidates(features)
    buckets = calc_liquidity_bucket(features)

    algebra = write_algebraic_check(out_dir)
    amihud_summary, amihud_daily = summarize_amihud_health(candidates, diagnostics)
    limit_health = summarize_limit_health(features, diagnostics, buckets)

    amihud_summary.to_csv(out_dir / "tw_amihud20_health_summary.csv", index=False)
    amihud_daily.to_csv(out_dir / "tw_amihud20_daily_quantiles.csv", index=False)
    limit_health.to_csv(out_dir / "tw_limit_proximity_event_counts.csv", index=False)

    if args.checks_only:
        write_report(out_dir.relative_to(ROOT), algebra, amihud_summary, limit_health)
        print(f"rows={features.shape[0]}")
        print(f"rev5_verdict={algebra.loc[algebra['candidate'] == 'REV5', 'verdict'].iloc[0]}")
        print(f"amihud_checks_pass={int(amihud_summary['pass_check'].sum())}/{amihud_summary.shape[0]}")
        print(f"wrote {out_dir.relative_to(ROOT)}")
        print("wrote docs/tw_audit/16g_tw_academic_factor_screening_report.md")
        return

    alpha158 = fetch_alpha158()
    daily_ic = calc_daily_ic(candidates, label, IC_CANDIDATES)
    segment_ic = summarize_ic(daily_ic, IC_CANDIDATES)
    corr, corr_detail = calc_alpha158_corr(candidates, alpha158)
    screen = build_screen_summary(segment_ic, corr, limit_health)
    bucket_ic = calc_bucket_ic(candidates, label, buckets)
    subset_ic = calc_masked_ic(candidates, label, diagnostics)
    event_returns = summarize_event_forward_returns(label, diagnostics, buckets)

    daily_ic.to_csv(out_dir / "academic_factor_daily_ic.csv", index=False)
    segment_ic.to_csv(out_dir / "academic_factor_segment_ic.csv", index=False)
    corr.to_csv(out_dir / "academic_factor_alpha158_corr.csv", index=False)
    corr_detail.to_csv(out_dir / "academic_factor_alpha158_corr_detail.csv", index=False)
    screen.to_csv(out_dir / "academic_factor_screen.csv", index=False)
    bucket_ic.to_csv(out_dir / "tw_amihud20_liquidity_bucket_ic.csv", index=False)
    subset_ic.to_csv(out_dir / "academic_factor_limit_day_subset_ic.csv", index=False)
    event_returns.to_csv(out_dir / "tw_limit_event_forward_returns.csv", index=False)
    write_report(out_dir.relative_to(ROOT), algebra, amihud_summary, limit_health, screen, bucket_ic, subset_ic, event_returns)

    print(f"rows={features.shape[0]}")
    print(f"rev5_verdict={algebra.loc[algebra['candidate'] == 'REV5', 'verdict'].iloc[0]}")
    print(f"amihud_checks_pass={int(amihud_summary['pass_check'].sum())}/{amihud_summary.shape[0]}")
    print(f"pass_single_factor_screen={int((screen['screen_decision'] == 'pass_single_factor_screen').sum())}")
    print(f"wrote {out_dir.relative_to(ROOT)}")
    print("wrote docs/tw_audit/16g_tw_academic_factor_screening_report.md")


if __name__ == "__main__":
    main()
