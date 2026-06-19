#!/usr/bin/env python3
"""Build Phase 1A orthogonal POC PIT samples and sanity checks.

Phase 1A is a restricted POC. It reads only Phase 0D cleaned orthogonal
archives, local adjusted prices, and existing local qlib prediction artifacts.
It does not download data, write qlib providers/bins, switch accepted latest,
train models, build Phase 2 rules, touch frontend/API, or interact with trading
state.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
QLIB = ROOT / "qlib_pipeline"
OUT_DIR = ROOT / "data_tw/experiments/decision_orthogonal"
DOC_DIR = ROOT / "docs/tw_decision_model_orthogonal"

PHASE0D_CLEAN_DIR = OUT_DIR / "phase0d_pit_clean"
INSTITUTIONAL_PATH = PHASE0D_CLEAN_DIR / "phase0d_institutional_flow_pit_clean.csv"
MARGIN_PATH = PHASE0D_CLEAN_DIR / "phase0d_margin_short_pit_clean.csv"
PRICE_ROOT = QLIB / "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
SIGNAL_ROOT = QLIB / "data_tw/experiments/option_c_historical_signal_backfill"
DAILY_SIGNAL_ROOT = QLIB / "data_tw/experiments/option_c_daily_signal"
TWII_PATH = PRICE_ROOT / "TWII.csv"

SAMPLES_PATH = OUT_DIR / "phase1a_poc_samples.parquet"
PREVIEW_PATH = OUT_DIR / "phase1a_poc_samples_preview.csv"
SCHEMA_PATH = OUT_DIR / "phase1a_schema.json"
FACTOR_REPORT_PATH = OUT_DIR / "phase1a_factor_increment_report.md"
LEAKAGE_REPORT_PATH = OUT_DIR / "phase1a_leakage_audit_report.md"
METRICS_PATH = OUT_DIR / "phase1a_factor_metrics.csv"
EXEC_REPORT_PATH = DOC_DIR / "PHASE1A_EXECUTION_REPORT_CN.md"

HORIZONS = [5, 10, 20]
ORTHOGONAL_FEATURES = [
    "foreign_net_buy",
    "investment_trust_net_buy",
    "dealer_net_buy",
    "institutional_total_net_buy",
    "institutional_total_net_buy_5d_sum",
    "institutional_total_net_buy_10d_sum",
    "institutional_total_net_buy_20d_sum",
    "foreign_trust_sync_direction",
    "margin_balance_change",
    "short_balance_change",
    "margin_balance_change_5d_sum",
    "margin_balance_change_10d_sum",
    "margin_balance_change_20d_sum",
    "short_balance_change_5d_sum",
    "short_balance_change_10d_sum",
    "short_balance_change_20d_sum",
]
QLIB_FEATURES = ["qlib_score_raw", "qlib_rank", "qlib_score_percentile_by_date", "qlib_score_zscore_by_date"]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def ensure_dirs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)


def parse_date_from_path(path: Path) -> pd.Timestamp | None:
    match = re.search(r"option_c_daily_signal_(\d{8})", str(path))
    if not match:
        return None
    return pd.Timestamp(datetime.strptime(match.group(1), "%Y%m%d")).normalize()


def load_phase0d() -> tuple[pd.DataFrame, pd.DataFrame]:
    inst = pd.read_csv(INSTITUTIONAL_PATH, dtype={"stock_id": str})
    margin = pd.read_csv(MARGIN_PATH, dtype={"stock_id": str})
    for df in [inst, margin]:
        df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
        df["available_at"] = pd.to_datetime(df["available_at"], errors="coerce")
        df["symbol"] = df["symbol"].astype(str)
        if df["available_at"].isna().any():
            raise RuntimeError("Phase 0D cleaned archive still has missing available_at")
    return inst, margin


def add_orthogonal_rolls(inst: pd.DataFrame, margin: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    inst = inst.sort_values(["symbol", "available_at", "trade_date"]).copy()
    margin = margin.sort_values(["symbol", "available_at", "trade_date"]).copy()
    for col in ["foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy", "institutional_total_net_buy"]:
        inst[col] = pd.to_numeric(inst[col], errors="coerce")
    for window in [5, 10, 20]:
        inst[f"institutional_total_net_buy_{window}d_sum"] = (
            inst.groupby("symbol")["institutional_total_net_buy"]
            .rolling(window, min_periods=1)
            .sum()
            .reset_index(level=0, drop=True)
        )
        inst[f"institutional_total_net_buy_{window}d_mean"] = (
            inst.groupby("symbol")["institutional_total_net_buy"]
            .rolling(window, min_periods=1)
            .mean()
            .reset_index(level=0, drop=True)
        )
    inst["foreign_trust_sync_direction"] = np.select(
        [
            (inst["foreign_net_buy"] > 0) & (inst["investment_trust_net_buy"] > 0),
            (inst["foreign_net_buy"] < 0) & (inst["investment_trust_net_buy"] < 0),
        ],
        [1, -1],
        default=0,
    )

    for col in ["margin_balance", "margin_balance_change", "short_balance", "short_balance_change"]:
        margin[col] = pd.to_numeric(margin[col], errors="coerce")
    for window in [5, 10, 20]:
        for col in ["margin_balance_change", "short_balance_change"]:
            margin[f"{col}_{window}d_sum"] = (
                margin.groupby("symbol")[col].rolling(window, min_periods=1).sum().reset_index(level=0, drop=True)
            )
            margin[f"{col}_{window}d_mean"] = (
                margin.groupby("symbol")[col].rolling(window, min_periods=1).mean().reset_index(level=0, drop=True)
            )
    return inst, margin


def prediction_paths(start: pd.Timestamp, end: pd.Timestamp) -> list[Path]:
    paths = [Path(p) for p in glob.glob(str(SIGNAL_ROOT / "*/*/prediction.csv"))]
    paths += [Path(p) for p in glob.glob(str(DAILY_SIGNAL_ROOT / "*/prediction.csv"))]
    out = []
    for path in paths:
        day = parse_date_from_path(path)
        if day is not None and start <= day <= end:
            out.append(path)
    return sorted(set(out))


def load_predictions(symbols: set[str], start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    rows: dict[tuple[pd.Timestamp, str], float] = {}
    paths = prediction_paths(start, end)
    for path in paths:
        try:
            df = pd.read_csv(path, usecols=["datetime", "instrument", "score"])
        except Exception:
            continue
        df["asof"] = pd.to_datetime(df["datetime"], errors="coerce").dt.normalize()
        df["symbol"] = df["instrument"].astype(str)
        df = df[(df["asof"] >= start) & (df["asof"] <= end) & (df["symbol"].isin(symbols))]
        for _, row in df.iterrows():
            score = pd.to_numeric(row["score"], errors="coerce")
            if pd.notna(score):
                rows[(row["asof"], row["symbol"])] = float(score)
    pred = pd.DataFrame(
        [{"asof": asof, "symbol": symbol, "qlib_score_raw": score} for (asof, symbol), score in rows.items()]
    )
    if pred.empty:
        return pred
    pred = pred.sort_values(["asof", "symbol"]).reset_index(drop=True)
    pred["qlib_rank"] = pred.groupby("asof")["qlib_score_raw"].rank(method="first", ascending=False).astype(int)
    grouped = pred.groupby("asof")["qlib_score_raw"]
    pred["qlib_score_percentile_by_date"] = grouped.rank(method="average", pct=True)
    daily_mean = grouped.transform("mean")
    daily_std = grouped.transform("std").replace(0, np.nan)
    pred["qlib_score_zscore_by_date"] = ((pred["qlib_score_raw"] - daily_mean) / daily_std).fillna(0.0)
    pred["top50_flag"] = pred["qlib_rank"] <= 50
    pred["qlib_prediction_path_count"] = len(paths)
    return pred


def load_price(symbol: str) -> pd.DataFrame:
    path = PRICE_ROOT / f"{symbol}.csv"
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, usecols=["date", "close", "volume"])
    except Exception:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
    return df.dropna(subset=["date", "close"]).sort_values("date").reset_index(drop=True)


def add_forward_labels(samples: pd.DataFrame, symbols: set[str]) -> pd.DataFrame:
    price_rows = []
    for symbol in sorted(symbols):
        df = load_price(symbol)
        if df.empty:
            continue
        for horizon in HORIZONS:
            df[f"fwd_{horizon}d_return"] = df["close"].shift(-horizon) / df["close"] - 1.0
            df[f"fwd_{horizon}d_date"] = df["date"].shift(-horizon)
        df["symbol"] = symbol
        price_rows.append(
            df[
                ["symbol", "date", "close", "volume"]
                + [f"fwd_{h}d_return" for h in HORIZONS]
                + [f"fwd_{h}d_date" for h in HORIZONS]
            ]
        )
    prices = pd.concat(price_rows, ignore_index=True) if price_rows else pd.DataFrame()
    if prices.empty:
        raise RuntimeError("no local price rows found for Phase 1A symbols")
    twii = load_price("TWII")
    if twii.empty:
        raise RuntimeError("TWII local price file missing")
    for horizon in HORIZONS:
        twii[f"market_fwd_{horizon}d_return"] = twii["close"].shift(-horizon) / twii["close"] - 1.0
        twii[f"market_fwd_{horizon}d_date"] = twii["date"].shift(-horizon)
    twii = twii[
        ["date"]
        + [f"market_fwd_{h}d_return" for h in HORIZONS]
        + [f"market_fwd_{h}d_date" for h in HORIZONS]
    ]

    out = samples.merge(prices, left_on=["asof", "symbol"], right_on=["date", "symbol"], how="left")
    out = out.merge(twii, left_on="asof", right_on="date", how="left", suffixes=("", "_market"))
    for horizon in HORIZONS:
        out[f"fwd_{horizon}d_excess_return"] = out[f"fwd_{horizon}d_return"] - out[f"market_fwd_{horizon}d_return"]
    return out.drop(columns=[col for col in ["date", "date_market"] if col in out.columns])


def pit_join(base: pd.DataFrame, features: pd.DataFrame, suffix: str) -> pd.DataFrame:
    chunks = []
    right = features.sort_values(["available_at", "trade_date"]).copy()
    for symbol, left_g in base.sort_values(["asof", "symbol"]).groupby("symbol"):
        right_g = right[right["symbol"] == symbol].copy()
        left_g = left_g.sort_values("asof").copy()
        if right_g.empty:
            chunks.append(left_g)
            continue
        merged = pd.merge_asof(
            left_g,
            right_g.sort_values("available_at"),
            left_on="asof",
            right_on="available_at",
            by="symbol",
            direction="backward",
            suffixes=("", suffix),
        )
        chunks.append(merged)
    return pd.concat(chunks, ignore_index=True) if chunks else base


def build_samples(args: argparse.Namespace) -> tuple[pd.DataFrame, dict[str, Any]]:
    inst, margin = load_phase0d()
    inst, margin = add_orthogonal_rolls(inst, margin)
    symbols = set(inst["symbol"]) | set(margin["symbol"])
    start = max(inst["available_at"].min(), margin["available_at"].min(), pd.Timestamp(args.start))
    end = min(inst["available_at"].max(), margin["available_at"].max(), pd.Timestamp(args.end))
    predictions = load_predictions(symbols, start.normalize(), end.normalize())
    if predictions.empty:
        samples = pd.DataFrame()
        return samples, {
            "symbols": len(symbols),
            "phase0d_start": start.strftime("%Y-%m-%d"),
            "phase0d_end": end.strftime("%Y-%m-%d"),
            "qlib_prediction_rows": 0,
            "sample_rows": 0,
            "prediction_paths": len(prediction_paths(start.normalize(), end.normalize())),
        }

    samples = predictions.copy()
    inst_cols = [
        "symbol",
        "trade_date",
        "available_at",
        "foreign_net_buy",
        "investment_trust_net_buy",
        "dealer_net_buy",
        "institutional_total_net_buy",
        "institutional_total_net_buy_5d_sum",
        "institutional_total_net_buy_10d_sum",
        "institutional_total_net_buy_20d_sum",
        "institutional_total_net_buy_5d_mean",
        "institutional_total_net_buy_10d_mean",
        "institutional_total_net_buy_20d_mean",
        "foreign_trust_sync_direction",
        "data_source",
        "raw_snapshot_id",
    ]
    margin_cols = [
        "symbol",
        "trade_date",
        "available_at",
        "margin_balance",
        "margin_balance_change",
        "short_balance",
        "short_balance_change",
        "margin_balance_change_5d_sum",
        "margin_balance_change_10d_sum",
        "margin_balance_change_20d_sum",
        "margin_balance_change_5d_mean",
        "margin_balance_change_10d_mean",
        "margin_balance_change_20d_mean",
        "short_balance_change_5d_sum",
        "short_balance_change_10d_sum",
        "short_balance_change_20d_sum",
        "short_balance_change_5d_mean",
        "short_balance_change_10d_mean",
        "short_balance_change_20d_mean",
        "data_source",
        "raw_snapshot_id",
    ]
    samples = pit_join(samples, inst[inst_cols], "_institutional")
    samples = samples.rename(
        columns={
            "trade_date": "institutional_trade_date",
            "available_at": "institutional_available_at",
            "data_source": "institutional_data_source",
            "raw_snapshot_id": "institutional_raw_snapshot_id",
        }
    )
    samples = pit_join(samples, margin[margin_cols], "_margin")
    samples = samples.rename(
        columns={
            "trade_date": "margin_trade_date",
            "available_at": "margin_available_at",
            "data_source": "margin_data_source",
            "raw_snapshot_id": "margin_raw_snapshot_id",
        }
    )
    samples = add_forward_labels(samples, symbols)
    samples["month"] = samples["asof"].dt.strftime("%Y-%m")
    samples["pit_join_valid"] = (
        samples["institutional_available_at"].notna()
        & samples["margin_available_at"].notna()
        & (samples["institutional_available_at"] <= samples["asof"])
        & (samples["margin_available_at"] <= samples["asof"])
    )
    samples = samples.sort_values(["asof", "qlib_rank", "symbol"]).reset_index(drop=True)
    return samples, {
        "symbols": len(symbols),
        "phase0d_start": start.strftime("%Y-%m-%d"),
        "phase0d_end": end.strftime("%Y-%m-%d"),
        "qlib_prediction_rows": int(len(predictions)),
        "sample_rows": int(len(samples)),
        "prediction_paths": int(predictions["qlib_prediction_path_count"].max()) if not predictions.empty else 0,
    }


def safe_spearman(df: pd.DataFrame, x: str, y: str) -> float:
    sub = df[[x, y]].dropna()
    if len(sub) < 5 or sub[x].nunique() < 2 or sub[y].nunique() < 2:
        return float("nan")
    return float(sub[x].corr(sub[y], method="spearman"))


def rankic_metrics(samples: pd.DataFrame, features: list[str]) -> list[dict[str, Any]]:
    rows = []
    for feature in features + QLIB_FEATURES:
        if feature not in samples.columns:
            continue
        for horizon in HORIZONS:
            label = f"fwd_{horizon}d_excess_return"
            daily_values = []
            for asof, g in samples.groupby("asof"):
                corr = safe_spearman(g, feature, label)
                if math.isfinite(corr):
                    daily_values.append((asof, corr, len(g[[feature, label]].dropna())))
            if daily_values:
                rows.append(
                    {
                        "metric_type": "rankic_spearman_daily_mean",
                        "feature": feature,
                        "label": label,
                        "segment": "all",
                        "month": "all",
                        "n": int(sum(v[2] for v in daily_values)),
                        "valid_periods": len(daily_values),
                        "value": float(np.mean([v[1] for v in daily_values])),
                    }
                )
            for month, g in samples.groupby("month"):
                month_values = []
                for asof, dg in g.groupby("asof"):
                    corr = safe_spearman(dg, feature, label)
                    if math.isfinite(corr):
                        month_values.append((asof, corr, len(dg[[feature, label]].dropna())))
                rows.append(
                    {
                        "metric_type": "rankic_spearman_daily_mean",
                        "feature": feature,
                        "label": label,
                        "segment": "all",
                        "month": month,
                        "n": int(sum(v[2] for v in month_values)),
                        "valid_periods": len(month_values),
                        "value": float(np.mean([v[1] for v in month_values])) if month_values else float("nan"),
                    }
                )
    return rows


def quantile_metrics(samples: pd.DataFrame, features: list[str]) -> list[dict[str, Any]]:
    rows = []
    for feature in features:
        if feature not in samples.columns:
            continue
        for horizon in HORIZONS:
            label = f"fwd_{horizon}d_excess_return"
            sub = samples[[feature, label, "month", "top50_flag"]].dropna()
            if len(sub) < 20 or sub[feature].nunique() < 3:
                continue
            try:
                sub["bucket"] = pd.qcut(sub[feature], q=3, labels=["low", "mid", "high"], duplicates="drop")
            except Exception:
                continue
            for bucket, g in sub.groupby("bucket", observed=True):
                rows.append(
                    {
                        "metric_type": "quantile_mean_return",
                        "feature": feature,
                        "label": label,
                        "segment": f"bucket={bucket}",
                        "month": "all",
                        "n": int(len(g)),
                        "valid_periods": int(g["month"].nunique()),
                        "value": float(g[label].mean()),
                    }
                )
            high = sub[sub["bucket"].astype(str) == "high"]
            low = sub[sub["bucket"].astype(str) == "low"]
            if len(high) and len(low):
                rows.append(
                    {
                        "metric_type": "high_minus_low_mean_return",
                        "feature": feature,
                        "label": label,
                        "segment": "all",
                        "month": "all",
                        "n": int(len(high) + len(low)),
                        "valid_periods": int(sub["month"].nunique()),
                        "value": float(high[label].mean() - low[label].mean()),
                    }
                )
    return rows


def qlib_corr_metrics(samples: pd.DataFrame, features: list[str]) -> list[dict[str, Any]]:
    rows = []
    for feature in features:
        if feature not in samples.columns:
            continue
        for qlib_col in ["qlib_rank", "qlib_score_raw"]:
            rows.append(
                {
                    "metric_type": "feature_vs_qlib_spearman",
                    "feature": feature,
                    "label": qlib_col,
                    "segment": "all",
                    "month": "all",
                    "n": int(len(samples[[feature, qlib_col]].dropna())),
                    "valid_periods": int(samples["asof"].nunique()),
                    "value": safe_spearman(samples, feature, qlib_col),
                }
            )
    return rows


def build_metrics(samples: pd.DataFrame) -> pd.DataFrame:
    features = [f for f in ORTHOGONAL_FEATURES if f in samples.columns]
    rows = []
    rows.extend(rankic_metrics(samples, features))
    rows.extend(quantile_metrics(samples, features))
    rows.extend(qlib_corr_metrics(samples, features))
    metrics = pd.DataFrame(rows)
    return metrics.sort_values(["metric_type", "feature", "label", "month", "segment"]).reset_index(drop=True)


def schema_rows(samples: pd.DataFrame) -> dict[str, Any]:
    fields = []
    for col in samples.columns:
        fields.append(
            {
                "name": col,
                "dtype": str(samples[col].dtype),
                "non_null_count": int(samples[col].notna().sum()),
                "pit_note": "available_at <= asof required" if "available_at" in col else "",
            }
        )
    return {
        "generated_at": utc_now(),
        "grain": "asof + symbol",
        "phase": "phase1a_restricted_poc",
        "fields": fields,
        "labels": [f"fwd_{h}d_excess_return" for h in HORIZONS],
        "forbidden_outputs": {
            "enter_phase2": False,
            "train_model": False,
            "phase1_gate_pass": False,
        },
    }


def leakage_audit(samples: pd.DataFrame, build_info: dict[str, Any]) -> dict[str, Any]:
    if samples.empty:
        return {"status": "fail", "reason": "no_samples", "checks": []}
    checks = []
    inst_bad = int((samples["institutional_available_at"] > samples["asof"]).sum())
    margin_bad = int((samples["margin_available_at"] > samples["asof"]).sum())
    same_day_invisible = int(
        ((samples["institutional_trade_date"] == samples["asof"]) & (samples["institutional_available_at"] > samples["asof"])).sum()
    )
    forward_date_checks = []
    for horizon in HORIZONS:
        date_col = f"fwd_{horizon}d_date"
        label_col = f"fwd_{horizon}d_excess_return"
        valid = samples[label_col].notna()
        bad = int((valid & (samples[date_col] <= samples["asof"])).sum())
        forward_date_checks.append(
            {
                "check": f"fwd_{horizon}d_label_date_gt_asof",
                "bad_rows": bad,
                "pass": bad == 0 and valid.any(),
            }
        )
    checks.extend(
        [
            {"check": "institutional_available_at_lte_asof", "bad_rows": inst_bad, "pass": inst_bad == 0},
            {"check": "margin_available_at_lte_asof", "bad_rows": margin_bad, "pass": margin_bad == 0},
            {"check": "same_day_invisible_orthogonal_not_joined", "bad_rows": same_day_invisible, "pass": same_day_invisible == 0},
            {"check": "qlib_predictions_present", "bad_rows": 0 if build_info["qlib_prediction_rows"] else 1, "pass": build_info["qlib_prediction_rows"] > 0},
        ]
        + forward_date_checks
    )
    status = "pass" if all(item["pass"] for item in checks) else "fail"
    return {"status": status, "checks": checks}


def format_metric(value: Any) -> str:
    try:
        if pd.isna(value):
            return "nan"
        return f"{float(value):.6f}"
    except Exception:
        return str(value)


def md_table(rows: list[dict[str, Any]], cols: list[str]) -> str:
    if not rows:
        return "_no rows_"
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---" for _ in cols]) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(format_metric(row.get(col, "")) for col in cols) + " |")
    return "\n".join(lines)


def conclusion(samples: pd.DataFrame, metrics: pd.DataFrame, audit: dict[str, Any]) -> dict[str, Any]:
    if samples.empty or audit.get("status") != "pass":
        return {
            "request_larger_backfill": False,
            "stop_orthogonal_poc": False,
            "phase1a_incomplete": True,
            "reason": "样本为空或 leakage audit 未通过。",
        }
    rankic = metrics[
        (metrics["metric_type"] == "rankic_spearman_daily_mean")
        & (metrics["month"] == "all")
        & (metrics["feature"].isin(ORTHOGONAL_FEATURES))
        & (metrics["valid_periods"] >= 10)
    ]
    quant = metrics[
        (metrics["metric_type"] == "high_minus_low_mean_return")
        & (metrics["feature"].isin(ORTHOGONAL_FEATURES))
        & (metrics["valid_periods"] >= 3)
    ]
    best_rankic = rankic["value"].abs().max() if not rankic.empty else np.nan
    best_quant = quant["value"].abs().max() if not quant.empty else np.nan
    if (pd.notna(best_rankic) and best_rankic >= 0.03) or (pd.notna(best_quant) and best_quant >= 0.005):
        return {
            "request_larger_backfill": True,
            "stop_orthogonal_poc": False,
            "phase1a_incomplete": False,
            "reason": "POC 有非零 RankIC 或分组差异迹象，但仅覆盖 5 个月/50 档，需要更大范围验证。",
        }
    return {
        "request_larger_backfill": False,
        "stop_orthogonal_poc": True,
        "phase1a_incomplete": False,
        "reason": "当前 POC 未显示足够单因子迹象。",
    }


def write_factor_report(samples: pd.DataFrame, metrics: pd.DataFrame, result: dict[str, Any]) -> None:
    rankic = metrics[(metrics["metric_type"] == "rankic_spearman_daily_mean") & (metrics["month"] == "all")]
    quant = metrics[metrics["metric_type"] == "high_minus_low_mean_return"]
    qlib_corr = metrics[metrics["metric_type"] == "feature_vs_qlib_spearman"]
    lines = [
        "# Phase 1A 单因子 Sanity Check 报告",
        "",
        f"- 样本行数：`{len(samples)}`",
        f"- 月份：`{', '.join(sorted(samples['month'].dropna().unique())) if not samples.empty else ''}`",
        f"- 结论：`{json.dumps(result, ensure_ascii=False)}`",
        "",
        "## RankIC / Spearman 摘要",
        "",
        md_table(
            rankic.sort_values("value", key=lambda s: s.abs(), ascending=False).head(20).to_dict("records"),
            ["feature", "label", "n", "valid_periods", "value"],
        ),
        "",
        "## 分组 High-Low 摘要",
        "",
        md_table(
            quant.sort_values("value", key=lambda s: s.abs(), ascending=False).head(20).to_dict("records"),
            ["feature", "label", "n", "valid_periods", "value"],
        ),
        "",
        "## 与 qlib rank/score 相关性",
        "",
        md_table(
            qlib_corr.sort_values("value", key=lambda s: s.abs(), ascending=False).head(20).to_dict("records"),
            ["feature", "label", "n", "valid_periods", "value"],
        ),
        "",
    ]
    FACTOR_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_leakage_report(samples: pd.DataFrame, audit: dict[str, Any]) -> None:
    lines = [
        "# Phase 1A Leakage Audit 报告",
        "",
        f"- audit_status：`{audit.get('status')}`",
        "- PIT join 规则：仅允许 `available_at <= asof` 的法人筹码与融资融券记录进入样本。",
        "- label 规则：`fwd_5d/10d/20d_excess_return` 均从 `asof` 后第 N 个本地交易日 close 计算，并扣除 TWII 同 horizon return。",
        "- T+1 规则说明：`available_at` 是 conservative visibility proxy，不是官方发布时间声明。",
        "",
        md_table(audit.get("checks", []), ["check", "bad_rows", "pass"]),
        "",
    ]
    LEAKAGE_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def coverage_summary(samples: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    if samples.empty:
        return rows
    for month, g in samples.groupby("month"):
        rows.append(
            {
                "month": month,
                "sample_rows": len(g),
                "symbols": g["symbol"].nunique(),
                "asof_days": g["asof"].nunique(),
                "institutional_available_rate": float(g["institutional_available_at"].notna().mean()),
                "margin_available_rate": float(g["margin_available_at"].notna().mean()),
                "label_5d_non_null_rate": float(g["fwd_5d_excess_return"].notna().mean()),
                "label_10d_non_null_rate": float(g["fwd_10d_excess_return"].notna().mean()),
                "label_20d_non_null_rate": float(g["fwd_20d_excess_return"].notna().mean()),
            }
        )
    return rows


def write_execution_report(
    samples: pd.DataFrame,
    metrics: pd.DataFrame,
    audit: dict[str, Any],
    result: dict[str, Any],
    build_info: dict[str, Any],
) -> None:
    coverage = coverage_summary(samples)
    top_rankic = metrics[
        (metrics["metric_type"] == "rankic_spearman_daily_mean") & (metrics["month"] == "all")
    ].sort_values("value", key=lambda s: s.abs(), ascending=False).head(15)
    qlib_corr = metrics[metrics["metric_type"] == "feature_vs_qlib_spearman"].sort_values(
        "value", key=lambda s: s.abs(), ascending=False
    ).head(15)
    lines = [
        "# Phase 1A POC 样本与单因子 Sanity Check 执行报告",
        "",
        "## 1. 执行范围",
        "",
        f"- 执行日期：`{utc_now()}`",
        "- 阶段目标：构建受限 POC PIT 样本，并对法人筹码、融资融券做单因子 sanity check。",
        "- 本阶段不是完整 Phase1，不允许放行 Phase2。",
        "- 未联网、未重跑 FinMind、未新增数据源、未扩大时间范围或 symbol universe、未启用月营收。",
        "- 未执行：Qlib bin/provider 写入、accepted latest switching、模型训练、规则 baseline、前端/API、broker/orders/quick-trade/target position/target weight。",
        "",
        "## 2. 修改文件",
        "",
        "- 新增 `scripts/build_tw_decision_orthogonal_phase1a_poc_samples.py`。",
        "- 新增 `docs/tw_decision_model_orthogonal/PHASE1A_EXECUTION_REPORT_CN.md`。",
        "",
        "## 3. 生成文件",
        "",
        f"- `{rel(SAMPLES_PATH)}`",
        f"- `{rel(PREVIEW_PATH)}`",
        f"- `{rel(SCHEMA_PATH)}`",
        f"- `{rel(FACTOR_REPORT_PATH)}`",
        f"- `{rel(LEAKAGE_REPORT_PATH)}`",
        f"- `{rel(METRICS_PATH)}`",
        f"- `{rel(EXEC_REPORT_PATH)}`",
        "",
        "## 4. 样本构建规则",
        "",
        "- 样本粒度：`asof + symbol`。",
        "- asof 来自本地既有 qlib prediction artifacts 的 `datetime`。",
        "- symbol 限制为 Phase0D cleaned archive 中的 50 档 POC universe。",
        f"- qlib prediction rows：`{build_info.get('qlib_prediction_rows')}`；sample rows：`{build_info.get('sample_rows')}`。",
        f"- qlib prediction path count in window：`{build_info.get('prediction_paths')}`。",
        "",
        "## 5. PIT Join 规则",
        "",
        "- 法人筹码与融资融券均使用 `available_at <= asof` 的最新可见记录。",
        "- 不允许使用 `trade_date == asof` 且 `available_at > asof` 的记录。",
        "- `available_at = next_trading_day(trade_date)` 是 conservative visibility proxy，不是官方发布时间声明。",
        "",
        "## 6. Label 定义",
        "",
        "- `fwd_5d_excess_return = symbol(asof 后第 5 个交易日 close / asof close - 1) - TWII 同 horizon return`。",
        "- `fwd_10d_excess_return`、`fwd_20d_excess_return` 同理。",
        "- label 从 asof 之后计算，不包含 asof 当日不可见信息。",
        "",
        "## 7. 特征清单",
        "",
        "- qlib：`qlib_score_raw`、`qlib_rank`、`qlib_score_percentile_by_date`、`qlib_score_zscore_by_date`。",
        "- 法人筹码：外资/投信/自营商/合计净买卖超、5/10/20 日 rolling sum/mean、外资投信同步方向。",
        "- 融资融券：融资余额变化、融券余额变化、5/10/20 日 rolling sum/mean。",
        "- 禁止特征：月营收、无 `available_at` 字段、未来窗口特征、任何模型预测分数以外的新训练输出。",
        "",
        "## 8. 覆盖率与缺失率",
        "",
        md_table(
            coverage,
            [
                "month",
                "sample_rows",
                "symbols",
                "asof_days",
                "institutional_available_rate",
                "margin_available_rate",
                "label_5d_non_null_rate",
                "label_10d_non_null_rate",
                "label_20d_non_null_rate",
            ],
        ),
        "",
        "## 9. Leakage Audit 结论",
        "",
        f"- leakage audit status：`{audit.get('status')}`。",
        md_table(audit.get("checks", []), ["check", "bad_rows", "pass"]),
        "",
        "## 10. 单因子/分组 Sanity Check",
        "",
        md_table(top_rankic.to_dict("records"), ["feature", "label", "n", "valid_periods", "value"]),
        "",
        "## 11. 与 qlib rank 的相关性",
        "",
        md_table(qlib_corr.to_dict("records"), ["feature", "label", "n", "valid_periods", "value"]),
        "",
        "## 12. 按月份稳定性",
        "",
        "- 详见 `phase1a_factor_metrics.csv` 中 `month != all` 的 RankIC rows。",
        "- 当前仅 2025-05 到 2025-09 的 POC，不足以证明跨年度稳定性。",
        "",
        "## 13. Phase 1A Gate 结论",
        "",
        f"- `request_larger_backfill={str(result['request_larger_backfill']).lower()}`",
        f"- `stop_orthogonal_poc={str(result['stop_orthogonal_poc']).lower()}`",
        f"- `phase1a_incomplete={str(result['phase1a_incomplete']).lower()}`",
        "- `enter_phase2=false`",
        "- `train_model=false`",
        "- `phase1_gate_pass=false`",
        f"- reason：{result['reason']}",
        "",
        "## 14. 安全边界",
        "",
        "- 禁止联网：未触碰。",
        "- provider refresh/publish：未触碰。",
        "- accepted latest switching：未触碰。",
        "- Qlib bin/provider 写入：未触碰。",
        "- 模型训练：未执行。",
        "- Phase2 规则 baseline：未执行。",
        "- 前端/API：未触碰。",
        "- broker/orders/quick-trade/target position/target weight：未触碰。",
        "- 真实交易建议语义：未生成。",
        "",
        "## 15. 需要审查者或用户确认的问题",
        "",
        "- 若审查者接受 POC 迹象，下一步只能请求用户授权更长历史/更多 symbols backfill；不能直接进入 Phase2。",
        "- 月营收继续 deferred，除非用户另行授权具备发布时间的数据源。",
        "- T+1 conservative visibility proxy 是否可继续用于更大样本，仍需审查者确认。",
        "",
    ]
    EXEC_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_outputs(samples: pd.DataFrame, metrics: pd.DataFrame, audit: dict[str, Any], result: dict[str, Any], build_info: dict[str, Any]) -> None:
    if samples.empty:
        samples.to_csv(PREVIEW_PATH, index=False)
    else:
        try:
            samples.to_parquet(SAMPLES_PATH, index=False)
        except Exception:
            samples.to_pickle(SAMPLES_PATH)
        samples.head(100).to_csv(PREVIEW_PATH, index=False)
    SCHEMA_PATH.write_text(json.dumps(schema_rows(samples), ensure_ascii=False, indent=2), encoding="utf-8")
    metrics.to_csv(METRICS_PATH, index=False)
    write_factor_report(samples, metrics, result)
    write_leakage_report(samples, audit)
    write_execution_report(samples, metrics, audit, result, build_info)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build restricted Phase 1A orthogonal POC samples.")
    parser.add_argument("--start", default="2025-05-01")
    parser.add_argument("--end", default="2025-09-30")
    args = parser.parse_args()
    ensure_dirs()
    samples, build_info = build_samples(args)
    metrics = build_metrics(samples) if not samples.empty else pd.DataFrame(
        columns=["metric_type", "feature", "label", "segment", "month", "n", "valid_periods", "value"]
    )
    audit = leakage_audit(samples, build_info)
    result = conclusion(samples, metrics, audit)
    write_outputs(samples, metrics, audit, result, build_info)
    print(
        json.dumps(
            {
                "status": "ok",
                "scope": "phase1a_restricted_poc_only",
                "sample_rows": int(len(samples)),
                "metric_rows": int(len(metrics)),
                **result,
                "outputs": [
                    rel(SAMPLES_PATH),
                    rel(PREVIEW_PATH),
                    rel(SCHEMA_PATH),
                    rel(FACTOR_REPORT_PATH),
                    rel(LEAKAGE_REPORT_PATH),
                    rel(METRICS_PATH),
                    rel(EXEC_REPORT_PATH),
                ],
                "safety": {
                    "network": False,
                    "finmind_rerun": False,
                    "monthly_revenue": False,
                    "provider_refresh_publish": False,
                    "accepted_latest_switching": False,
                    "qlib_bin_provider_write": False,
                    "model_training": False,
                    "phase2": False,
                    "frontend_api": False,
                    "broker_orders_quick_trade_target_positions": False,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
