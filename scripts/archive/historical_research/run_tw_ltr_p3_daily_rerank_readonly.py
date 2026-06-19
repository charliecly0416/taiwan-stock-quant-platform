#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
LATEST_SIGNAL = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json"
SIGNAL_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal"
PRICE_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized"
TWII_PATH = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TWII.csv"
ORTHO_DAILY = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/normalized_feature_daily.csv"
LATEST_ORTHO_DIR = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank"
LATEST_ORTHO_PREFIX = "latest_orthogonal_features_"
O4_MODEL = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_treatment_model.pkl"
O4_WHITELIST = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_feature_whitelist.csv"
OUT = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank"
REPORT = ROOT / "docs/tw_ltr_orthogonal_features_controlled/PHASEP3_DAILY_LTR_RERANK_READONLY_EXECUTION_REPORT_CN.md"


CONTROL_FEATURES = [
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
    "avg_trading_value_20d",
    "volume_stability20",
    "missing_rate20",
    "suspension_proxy",
    "slippage_proxy",
    "TWII_ret20",
    "TWII_ret60",
    "TWII_close_vs_MA60",
    "TWII_close_vs_MA120",
    "market_volatility20",
    "market_drawdown60",
    "market_breadth20",
]

ORTHO_FEATURES = [
    "foreign_net_buy",
    "investment_trust_net_buy",
    "dealer_net_buy",
    "institutional_total_net_buy",
    "foreign_net_buy_roll1",
    "foreign_net_buy_roll3",
    "foreign_net_buy_roll5",
    "foreign_net_buy_roll10",
    "investment_trust_net_buy_roll1",
    "investment_trust_net_buy_roll3",
    "investment_trust_net_buy_roll5",
    "investment_trust_net_buy_roll10",
    "dealer_net_buy_roll1",
    "dealer_net_buy_roll3",
    "dealer_net_buy_roll5",
    "dealer_net_buy_roll10",
    "institutional_total_net_buy_roll1",
    "institutional_total_net_buy_roll3",
    "institutional_total_net_buy_roll5",
    "institutional_total_net_buy_roll10",
    "institutional_total_net_buy_streak",
    "institutional_missing_flag",
    "institutional_delay_flag",
    "institutional_flow_delay_days",
    "institutional_flow_asof_missing_flag",
    "margin_balance",
    "margin_balance_change",
    "short_balance",
    "short_balance_change",
    "margin_balance_change_roll1",
    "margin_balance_change_roll3",
    "margin_balance_change_roll5",
    "margin_balance_change_roll10",
    "short_balance_change_roll1",
    "short_balance_change_roll3",
    "short_balance_change_roll5",
    "short_balance_change_roll10",
    "margin_direction_proxy",
    "short_direction_proxy",
    "margin_short_divergence_proxy",
    "margin_short_missing_flag",
    "margin_short_delay_flag",
    "margin_short_delay_days",
    "margin_short_asof_missing_flag",
]

FEATURE_COLUMNS = CONTROL_FEATURES + ORTHO_FEATURES


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def wcsv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({k for row in rows for k in row}) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def wjson(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def norm_symbol(raw: Any) -> str:
    text = str(raw or "").strip().upper()
    if not text:
        return text
    return text if text.startswith("TW") else f"TW{text}"


def strip_tw(raw: Any) -> str:
    text = norm_symbol(raw)
    return text[2:] if text.startswith("TW") else text


def streak_count(flags: pd.Series) -> pd.Series:
    values = []
    current = 0
    for raw in flags.fillna(0).astype(int).tolist():
        current = current + 1 if raw else 0
        values.append(current)
    return pd.Series(values, index=flags.index)


def load_latest_signal() -> dict[str, Any]:
    payload = json.loads(LATEST_SIGNAL.read_text(encoding="utf-8"))
    if payload.get("status") != "accepted":
        raise RuntimeError(f"latest signal not accepted: {payload.get('status')}")
    return payload


def accepted_rows(run_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(run_dir / "top50_signals.csv")
    if df.empty:
        raise RuntimeError(f"empty top50 artifact: {run_dir / 'top50_signals.csv'}")
    df["asof"] = pd.to_datetime(df["asof"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["instrument"] = df["instrument"].map(norm_symbol)
    df["symbol"] = df["instrument"].map(strip_tw)
    df["qlib_score"] = pd.to_numeric(df["score"], errors="coerce")
    df["qlib_rank"] = pd.to_numeric(df["rank"], errors="coerce").astype(int)
    return df[["asof", "symbol", "instrument", "qlib_score", "qlib_rank", "source_model_recorder", "diagnostic_only", "research_signal_not_order"]].sort_values(["qlib_rank", "symbol"])


def load_price_frame(symbol: str) -> pd.DataFrame:
    path = PRICE_ROOT / f"{norm_symbol(symbol)}.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").copy()
    for col in ["open", "high", "low", "close", "volume", "vwap"]:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window, min_periods=window).mean()
    loss = (-delta.clip(upper=0)).rolling(window, min_periods=window).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50.0)


def build_price_features(symbols: list[str], asof: str) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for symbol in symbols:
        df = load_price_frame(symbol)
        df = df[df["date"].dt.strftime("%Y-%m-%d") <= asof].copy()
        if df.empty:
            continue
        df["instrument"] = norm_symbol(symbol)
        close = df["close"]
        volume = df["volume"] if "volume" in df else pd.Series(np.nan, index=df.index)
        vwap = df["vwap"] if "vwap" in df else close
        for window in (5, 10, 20, 60):
            df[f"MA{window}"] = close.rolling(window, min_periods=window).mean()
        df["RSI14"] = rsi(close)
        ema12 = close.ewm(span=12, adjust=False, min_periods=12).mean()
        ema26 = close.ewm(span=26, adjust=False, min_periods=26).mean()
        df["MACD"] = ema12 - ema26
        ma20 = close.rolling(20, min_periods=20).mean()
        std20 = close.rolling(20, min_periods=20).std()
        df["Bollinger_position"] = ((close - ma20) / (2 * std20.replace(0, np.nan))).clip(-5, 5)
        df["ret20"] = close.pct_change(20)
        df["volatility20"] = close.pct_change().rolling(20, min_periods=20).std()
        df["volume_ratio20"] = volume / volume.rolling(20, min_periods=20).mean().replace(0, np.nan)
        trading_value = volume * vwap
        df["avg_trading_value_20d"] = trading_value.rolling(20, min_periods=20).mean()
        df["volume_stability20"] = 1.0 / (1.0 + volume.pct_change().rolling(20, min_periods=20).std())
        df["missing_rate20"] = close.isna().astype(int).rolling(20, min_periods=1).mean()
        df["suspension_proxy"] = (volume.fillna(0) <= 0).astype(int)
        df["slippage_proxy"] = (1.0 / np.sqrt(trading_value.replace(0, np.nan))).replace([np.inf, -np.inf], np.nan)
        frames.append(
            df[[
                "date",
                "instrument",
                "close",
                "volume",
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
                "avg_trading_value_20d",
                "volume_stability20",
                "missing_rate20",
                "suspension_proxy",
                "slippage_proxy",
            ]].copy()
        )
    if not frames:
        raise RuntimeError("no price history matched latest top50 symbols")
    out = pd.concat(frames, ignore_index=True)
    out["asof"] = out["date"].dt.strftime("%Y-%m-%d")
    out["symbol"] = out["instrument"].map(strip_tw)
    return out[out["asof"] == asof].copy()


def market_features(asof: str, symbols: list[str]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for symbol in symbols:
        path = TWII_PATH if norm_symbol(symbol) == "TWII" else PRICE_ROOT / f"{norm_symbol(symbol)}.csv"
        if not path.exists():
            continue
        df = pd.read_csv(path, usecols=["date", "close"])
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df = df.dropna(subset=["date"]).sort_values("date")
        df["symbol"] = symbol
        frames.append(df)
    if not frames:
        raise RuntimeError("no market price frames available")
    prices = pd.concat(frames, ignore_index=True)
    prices["date_str"] = prices["date"].dt.strftime("%Y-%m-%d")
    prices = prices[prices["date_str"] <= asof].copy()
    twii = prices[prices["symbol"] == "TWII"].copy().sort_values("date")
    if twii.empty:
        raise RuntimeError("missing TWII history")
    twii["TWII_ret20"] = twii["close"].pct_change(20)
    twii["TWII_ret60"] = twii["close"].pct_change(60)
    ma60 = twii["close"].rolling(60, min_periods=60).mean()
    ma120 = twii["close"].rolling(120, min_periods=120).mean()
    twii["TWII_close_vs_MA60"] = twii["close"] / ma60 - 1
    twii["TWII_close_vs_MA120"] = twii["close"] / ma120 - 1
    twii["market_volatility20"] = twii["close"].pct_change().rolling(20, min_periods=20).std()
    rolling_max60 = twii["close"].rolling(60, min_periods=20).max()
    twii["market_drawdown60"] = twii["close"] / rolling_max60 - 1
    breadth_source = prices[prices["symbol"] != "TWII"].copy()
    breadth_source["MA20"] = breadth_source.groupby("symbol")["close"].transform(lambda s: s.rolling(20, min_periods=20).mean())
    breadth = (
        breadth_source.dropna(subset=["MA20"])
        .assign(above_ma20=lambda x: (x["close"] > x["MA20"]).astype(float))
        .groupby("date_str")["above_ma20"]
        .mean()
        .rename("market_breadth20")
        .reset_index()
    )
    keep = ["date_str", "TWII_ret20", "TWII_ret60", "TWII_close_vs_MA60", "TWII_close_vs_MA120", "market_volatility20", "market_drawdown60"]
    out = twii[keep].merge(breadth, on="date_str", how="left")
    out = out.rename(columns={"date_str": "asof"})
    return out[out["asof"] == asof].copy()


def load_orthogonal_daily(asof: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    latest_path = LATEST_ORTHO_DIR / f"{LATEST_ORTHO_PREFIX}{asof}.csv"
    refresh_status_path = LATEST_ORTHO_DIR / f"{LATEST_ORTHO_PREFIX}{asof}_refresh_status.json"
    if latest_path.exists():
        df = pd.read_csv(latest_path)
        df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
        df["available_at"] = pd.to_datetime(df["available_at"], errors="coerce")
        df["symbol"] = df["symbol"].astype(str).str.upper()
        status = read_json(refresh_status_path) if refresh_status_path.exists() else {}
        status.setdefault("status", "current_or_pit_delayed")
        status.setdefault("latest_feature_table_path", rel(latest_path))
        status.setdefault("latest_feature_table_created_at", status.get("created_at", now()))
        return df, status
    legacy = pd.read_csv(ORTHO_DAILY)
    legacy["trade_date"] = pd.to_datetime(legacy["trade_date"], errors="coerce")
    legacy["available_at"] = pd.to_datetime(legacy["available_at"], errors="coerce")
    legacy["symbol"] = legacy["symbol"].astype(str).str.upper()
    status = {
        "status": "stale_degraded",
        "latest_feature_table_path": rel(ORTHO_DAILY),
        "latest_feature_table_created_at": read_json(LATEST_SIGNAL).get("created_at", now()),
        "stale_feature_families": ["institutional_flow", "margin_short"],
        "institutional_latest_trade_date": str(legacy[legacy["feature_family"] == "institutional_flow"]["trade_date"].max())[:10],
        "institutional_latest_available_at": str(legacy[legacy["feature_family"] == "institutional_flow"]["available_at"].max())[:10],
        "margin_latest_trade_date": str(legacy[legacy["feature_family"] == "margin_short"]["trade_date"].max())[:10],
        "margin_latest_available_at": str(legacy[legacy["feature_family"] == "margin_short"]["available_at"].max())[:10],
    }
    return legacy, status


def asof_join_orthogonal(top50: pd.DataFrame, asof: str) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], dict[str, Any]]:
    features, refresh_status = load_orthogonal_daily(asof)
    asof_ts = pd.Timestamp(asof)
    families = {
        "institutional_flow": [
            "foreign_net_buy",
            "investment_trust_net_buy",
            "dealer_net_buy",
            "institutional_total_net_buy",
            "foreign_net_buy_roll1",
            "foreign_net_buy_roll3",
            "foreign_net_buy_roll5",
            "foreign_net_buy_roll10",
            "investment_trust_net_buy_roll1",
            "investment_trust_net_buy_roll3",
            "investment_trust_net_buy_roll5",
            "investment_trust_net_buy_roll10",
            "dealer_net_buy_roll1",
            "dealer_net_buy_roll3",
            "dealer_net_buy_roll5",
            "dealer_net_buy_roll10",
            "institutional_total_net_buy_roll1",
            "institutional_total_net_buy_roll3",
            "institutional_total_net_buy_roll5",
            "institutional_total_net_buy_roll10",
            "institutional_total_net_buy_streak",
            "institutional_missing_flag",
            "institutional_delay_flag",
        ],
        "margin_short": [
            "margin_balance",
            "margin_balance_change",
            "short_balance",
            "short_balance_change",
            "margin_balance_change_roll1",
            "margin_balance_change_roll3",
            "margin_balance_change_roll5",
            "margin_balance_change_roll10",
            "short_balance_change_roll1",
            "short_balance_change_roll3",
            "short_balance_change_roll5",
            "short_balance_change_roll10",
            "margin_direction_proxy",
            "short_direction_proxy",
            "margin_short_divergence_proxy",
            "margin_short_missing_flag",
            "margin_short_delay_flag",
        ],
    }
    joined = top50.copy()
    audit_rows: list[dict[str, Any]] = []
    pit_violations: list[str] = []
    future_violations: list[str] = []
    for family, cols in families.items():
        feat = features[features["feature_family"] == family].copy()
        feat = feat[feat["available_at"] <= asof_ts].sort_values(["symbol", "available_at"])
        meta_cols = ["trade_date", "available_at", "delay_days", "delay_reason", "available_at_contract", "raw_snapshot_id", "raw_snapshot_path", "lineage_source"]
        feat = feat[["symbol", *meta_cols, *cols]]
        feat = feat.rename(columns={"symbol": "instrument"})
        pieces = []
        for symbol, g in joined.groupby("instrument", sort=False):
            left = g[["asof", "instrument"]].copy()
            left["date"] = pd.to_datetime(left["asof"])
            right = feat[feat["instrument"] == symbol].copy()
            if right.empty:
                out = left.copy()
                for col in cols:
                    out[col] = 0.0
                for col in meta_cols:
                    out[f"{family}_{col}"] = ""
                out[f"{family}_asof_missing_flag"] = 1
            else:
                right = right.rename(columns={c: f"{family}_{c}" for c in meta_cols})
                out = pd.merge_asof(
                    left.sort_values("date"),
                    right.sort_values(f"{family}_available_at"),
                    left_on="date",
                    right_on=f"{family}_available_at",
                    by="instrument",
                    direction="backward",
                    allow_exact_matches=True,
                )
                out = out.drop(columns=["symbol"], errors="ignore")
                for col in cols:
                    out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)
                out[f"{family}_asof_missing_flag"] = out[f"{family}_available_at"].isna().astype(int)
                for col in meta_cols:
                    out[f"{family}_{col}"] = out[f"{family}_{col}"].fillna("")
            if f"{family}_delay_days" not in out.columns and f"{family}_delay_days" in FEATURE_COLUMNS:
                out[f"{family}_delay_days"] = pd.to_numeric(out.get(f"{family}_delay_days", 0), errors="coerce").fillna(0.0)
            out[f"{family}_used_available_at_gt_sample_date"] = pd.to_datetime(out[f"{family}_available_at"], errors="coerce") > out["date"]
            out[f"{family}_used_trade_date_gt_sample_date"] = pd.to_datetime(out[f"{family}_trade_date"], errors="coerce") > out["date"]
            if out[f"{family}_used_available_at_gt_sample_date"].any():
                pit_violations.append(family)
            if out[f"{family}_used_trade_date_gt_sample_date"].any():
                future_violations.append(family)
            pieces.append(out.drop(columns=["date"], errors="ignore"))
        family_join = pd.concat(pieces, ignore_index=True)
        joined = joined.merge(family_join, on=["asof", "instrument"], how="left")
        audit_rows.append(
            {
                "feature_family": family,
                "top50_rows": int(len(joined)),
                "missing_rows": int(joined[f"{family}_asof_missing_flag"].sum()),
                "missing_ratio": float(joined[f"{family}_asof_missing_flag"].mean()),
                "available_at_max": str(pd.to_datetime(joined[f"{family}_available_at"], errors="coerce").max()) if f"{family}_available_at" in joined else "",
                "trade_date_max": str(pd.to_datetime(joined[f"{family}_trade_date"], errors="coerce").max()) if f"{family}_trade_date" in joined else "",
                "used_available_at_gt_sample_date_rows": int(joined[f"{family}_used_available_at_gt_sample_date"].sum()),
                "used_trade_date_gt_sample_date_rows": int(joined[f"{family}_used_trade_date_gt_sample_date"].sum()),
            }
        )
    audit = {
        "available_at_violations": sorted(set(pit_violations)),
        "future_data_violations": sorted(set(future_violations)),
        "missing_feature_count_by_family": {family: int(joined[f"{family}_asof_missing_flag"].sum()) for family in families},
    }
    return joined, pd.DataFrame(audit_rows), audit, refresh_status


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    latest = load_latest_signal()
    run_dir = SIGNAL_ROOT / str(latest["run_dir"]).split("data_tw/experiments/option_c_daily_signal/")[-1]
    top50 = accepted_rows(run_dir)
    asof = str(latest["asof"])[:10]
    if len(top50) != 50:
        raise RuntimeError(f"expected 50 top50 rows, got {len(top50)}")
    if top50["asof"].nunique() != 1 or str(top50["asof"].iloc[0]) != asof:
        raise RuntimeError("latest signal asof mismatch")

    price_symbols = sorted(set(top50["instrument"].tolist()))
    market_symbols = sorted(set(top50["instrument"].tolist()) | {"TWII"})
    price_feat = build_price_features(price_symbols, asof)
    market_feat = market_features(asof, market_symbols)
    daily = top50.merge(price_feat, on=["asof", "instrument", "symbol"], how="left")
    daily = daily.merge(market_feat, on="asof", how="left")

    daily["qlib_score_raw"] = pd.to_numeric(daily["qlib_score"], errors="coerce")
    daily["qlib_rank"] = pd.to_numeric(daily["qlib_rank"], errors="coerce").astype(int)
    daily["qlib_score_percentile_by_date"] = daily["qlib_score_raw"].rank(pct=True, ascending=True)
    qstd = daily["qlib_score_raw"].std()
    qmean = daily["qlib_score_raw"].mean()
    daily["qlib_score_zscore_by_date"] = 0.0 if pd.isna(qstd) or qstd == 0 else (daily["qlib_score_raw"] - qmean) / qstd
    daily["top10_flag"] = (daily["qlib_rank"] <= 10).astype(int)
    daily["top30_flag"] = (daily["qlib_rank"] <= 30).astype(int)
    daily["top50_flag"] = (daily["qlib_rank"] <= 50).astype(int)
    daily = daily.sort_values(["instrument", "asof"])
    for lag in (1, 3, 5):
        daily[f"rank_change_{lag}d"] = daily.groupby("instrument")["qlib_rank"].diff(lag)
    daily["top30_streak"] = daily.groupby("instrument", group_keys=False)["top30_flag"].apply(streak_count)
    daily["top50_streak"] = daily.groupby("instrument", group_keys=False)["top50_flag"].apply(streak_count)
    daily["feature_complete"] = daily[[c for c in CONTROL_FEATURES if c not in {"qlib_score_raw", "qlib_rank"}]].notna().all(axis=1)
    daily["sample_complete"] = daily["feature_complete"]
    daily["year"] = pd.to_datetime(daily["asof"]).dt.year
    daily["split"] = "inference_only"
    daily["regime_segment"] = "inference_only"
    daily["relevance_10d_top_heavy"] = 0

    required_control = [c for c in CONTROL_FEATURES if c not in daily.columns]
    if required_control:
        raise RuntimeError(f"missing control features after local build: {required_control}")

    joined, feature_audit, pit, refresh_status = asof_join_orthogonal(daily, asof)
    joined["feature_available_at_max"] = joined[["institutional_flow_available_at", "margin_short_available_at"]].apply(
        lambda row: max([str(x)[:10] for x in row if str(x) not in {"", "NaT", "NaN"}], default=""), axis=1
    )
    joined["missing_feature_family_count"] = (
        joined["institutional_flow_asof_missing_flag"].fillna(0).astype(int)
        + joined["margin_short_asof_missing_flag"].fillna(0).astype(int)
    )
    joined["pit_pass"] = (
        ~joined["institutional_flow_used_available_at_gt_sample_date"].fillna(False)
        & ~joined["margin_short_used_available_at_gt_sample_date"].fillna(False)
        & ~joined["institutional_flow_used_trade_date_gt_sample_date"].fillna(False)
        & ~joined["margin_short_used_trade_date_gt_sample_date"].fillna(False)
    )

    with O4_MODEL.open("rb") as fh:
        model = pickle.load(fh)
    feature_frame = joined[FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)
    joined["ltr_score"] = model.predict(feature_frame)
    joined["ltr_rank"] = joined["ltr_score"].rank(method="first", ascending=False).astype(int)

    joined["symbol"] = joined["symbol"].astype(str)
    joined["instrument"] = joined["instrument"].astype(str)
    daily_out = joined.sort_values(["ltr_rank", "instrument"]).copy()
    daily_out["feature_available_at_max"] = daily_out["feature_available_at_max"].fillna("")
    daily_out["missing_feature_family_count"] = pd.to_numeric(daily_out["missing_feature_family_count"], errors="coerce").fillna(0).astype(int)
    daily_out["pit_pass"] = daily_out["pit_pass"].fillna(False).astype(bool)

    out_csv = OUT / f"daily_ltr_rerank_{asof}_top50.csv"
    daily_out.to_csv(out_csv, index=False)
    feature_audit.to_csv(OUT / f"daily_ltr_rerank_{asof}_feature_audit.csv", index=False)

    pit_audit = {
        "asof": asof,
        "feature_trade_date_max_by_family": {
            "institutional_flow": str(pd.to_datetime(joined["institutional_flow_trade_date"], errors="coerce").max())[:10],
            "margin_short": str(pd.to_datetime(joined["margin_short_trade_date"], errors="coerce").max())[:10],
        },
        "available_at_max_by_family": {
            "institutional_flow": str(pd.to_datetime(joined["institutional_flow_available_at"], errors="coerce").max())[:10],
            "margin_short": str(pd.to_datetime(joined["margin_short_available_at"], errors="coerce").max())[:10],
        },
        "available_at_violations": pit["available_at_violations"],
        "future_data_violations": pit["future_data_violations"],
        "missing_feature_count_by_family": pit["missing_feature_count_by_family"],
        "pit_pass": not pit["available_at_violations"] and not pit["future_data_violations"],
    }
    stale_feature_families = refresh_status.get("stale_feature_families") or [
        family for family, latest_available_at in pit_audit["available_at_max_by_family"].items()
        if latest_available_at and latest_available_at < asof
    ]
    orthogonal_refresh_status = {
        "status": refresh_status.get("status", "stale_degraded" if stale_feature_families else "current_or_pit_delayed"),
        "source": refresh_status.get("source", "phase_o2_pit_safe_feature_builder.normalized_feature_daily.csv"),
        "latest_feature_table_path": refresh_status.get("latest_feature_table_path", rel(ORTHO_DAILY)),
        "latest_feature_table_created_at": refresh_status.get("latest_feature_table_created_at", now()),
        "institutional_latest_trade_date": refresh_status.get("institutional_latest_trade_date", pit_audit["feature_trade_date_max_by_family"]["institutional_flow"]),
        "institutional_latest_available_at": refresh_status.get("institutional_latest_available_at", pit_audit["available_at_max_by_family"]["institutional_flow"]),
        "margin_latest_trade_date": refresh_status.get("margin_latest_trade_date", pit_audit["feature_trade_date_max_by_family"]["margin_short"]),
        "margin_latest_available_at": refresh_status.get("margin_latest_available_at", pit_audit["available_at_max_by_family"]["margin_short"]),
        "refresh_failed_symbols": refresh_status.get("failed_symbols", []),
        "stale_feature_families": stale_feature_families,
    }
    failure_isolation_audit = {
        "fresh_qlib_default_chain_status": "unchanged",
        "p3_ltr_candidate_status": "ready" if int(daily_out["ltr_score"].notna().sum()) == 50 and pit_audit["pit_pass"] else "degraded",
        "p3_failure_blocks_fresh_qlib": False,
        "accepted_latest_mutated_by_p3": False,
        "provider_mutated_by_p3": False,
        "monitor_mutated_by_p3": False,
        "trading_mutated_by_p3": False,
    }
    summary = {
        "asof": asof,
        "source_qlib_run_id": str(run_dir).split("/")[-1],
        "source_latest_signal_path": rel(LATEST_SIGNAL),
        "model_artifact": rel(O4_MODEL),
        "model_hash": hashlib.sha256(O4_MODEL.read_bytes()).hexdigest(),
        "feature_schema_hash": hashlib.sha256(("|".join(FEATURE_COLUMNS)).encode("utf-8")).hexdigest(),
        "top50_input_count": int(len(top50)),
        "top50_scored_count": int(daily_out["ltr_score"].notna().sum()),
        "top50_missing_score_count": int(daily_out["ltr_score"].isna().sum()),
        "pit_pass": bool(pit_audit["pit_pass"]),
        "available_at_violations": pit_audit["available_at_violations"],
        "future_data_violations": pit_audit["future_data_violations"],
        "status": "ready" if int(daily_out["ltr_score"].notna().sum()) == 50 and pit_audit["pit_pass"] and orthogonal_refresh_status.get("status") == "current_or_pit_delayed" else "degraded",
        "orthogonal_refresh_status": orthogonal_refresh_status,
        "failure_isolation_audit": failure_isolation_audit,
        "reader_ui_boundary": "artifact_only_in_p3r; readonly reader/UI requires a later display phase",
        "trading_disabled_flags": {
            "broker": True,
            "orders": True,
            "quick_trade": True,
            "positions": True,
            "monitor_config": True,
            "monitor_scan": True,
            "alerts": True,
            "accepted_latest_switch": True,
            "provider_publish": True,
            "provider_refresh": True,
            "frontend_api": True,
        },
        "artifacts": {
            "top50": rel(out_csv),
            "feature_audit": rel(OUT / f"daily_ltr_rerank_{asof}_feature_audit.csv"),
            "pit_audit": rel(OUT / f"daily_ltr_rerank_{asof}_pit_audit.json"),
            "summary": rel(OUT / f"daily_ltr_rerank_{asof}_summary.json"),
            "latest": rel(OUT / "daily_ltr_rerank_latest.json"),
            "failure_isolation_audit": rel(OUT / f"daily_ltr_rerank_{asof}_failure_isolation_audit.json"),
            },
    }
    wjson(OUT / f"daily_ltr_rerank_{asof}_pit_audit.json", pit_audit)
    wjson(OUT / f"daily_ltr_rerank_{asof}_orthogonal_refresh_status.json", orthogonal_refresh_status)
    wjson(OUT / f"daily_ltr_rerank_{asof}_failure_isolation_audit.json", failure_isolation_audit)
    wjson(OUT / f"daily_ltr_rerank_{asof}_summary.json", summary)
    wjson(OUT / "daily_ltr_rerank_latest.json", summary)

    inventory_rows = [
        {"artifact": "latest_signal", "path": rel(LATEST_SIGNAL), "status": "read"},
        {"artifact": "top50_input", "path": rel(run_dir / "top50_signals.csv"), "status": "read"},
        {"artifact": "o4_model", "path": rel(O4_MODEL), "status": "read"},
        {"artifact": "o4_whitelist", "path": rel(O4_WHITELIST), "status": "read"},
        {"artifact": "orthogonal_daily", "path": rel(ORTHO_DAILY), "status": "read"},
        {"artifact": "daily_top50_output", "path": rel(out_csv), "status": "write"},
        {"artifact": "feature_audit", "path": rel(OUT / f"daily_ltr_rerank_{asof}_feature_audit.csv"), "status": "write"},
        {"artifact": "pit_audit", "path": rel(OUT / f"daily_ltr_rerank_{asof}_pit_audit.json"), "status": "write"},
        {"artifact": "summary", "path": rel(OUT / f"daily_ltr_rerank_{asof}_summary.json"), "status": "write"},
        {"artifact": "latest_pointer", "path": rel(OUT / "daily_ltr_rerank_latest.json"), "status": "write"},
        {"artifact": "orthogonal_refresh_status", "path": rel(OUT / f"daily_ltr_rerank_{asof}_orthogonal_refresh_status.json"), "status": "write"},
        {"artifact": "failure_isolation_audit", "path": rel(OUT / f"daily_ltr_rerank_{asof}_failure_isolation_audit.json"), "status": "write"},
    ]
    wcsv(OUT / f"daily_ltr_rerank_{asof}_artifact_inventory.csv", inventory_rows, ["artifact", "path", "status"])
    wcsv(OUT / f"daily_ltr_rerank_{asof}_score_snapshot.csv", daily_out[[c for c in ["asof", "symbol", "instrument", "qlib_rank", "qlib_score", "qlib_score_raw", "qlib_score_percentile_by_date", "qlib_score_zscore_by_date", "ltr_score", "ltr_rank", "source_model_recorder", "diagnostic_only", "research_signal_not_order", "feature_available_at_max", "missing_feature_family_count", "pit_pass"] if c in daily_out.columns]].to_dict("records"))

    report_lines = [
        "# Phase P3 执行报告：Daily LTR Rerank Readonly Candidate",
        "",
        f"生成时间：`{now()}`",
        "",
        "## 1. 结论",
        "",
        "- 默认策略仍为 `fresh qlib / rank_rotate_top50_adaptive_score`。",
        "- 本轮只做 frozen O4 模型的 daily scoring / rerank，没有重训。",
        "- LTR candidate 只使用 qlib Top50，未扩大候选池。",
        f"- 当前 asof：`{asof}`，top50 input/scored：`{summary['top50_input_count']}/{summary['top50_scored_count']}`。",
        f"- PIT 结果：`{summary['pit_pass']}`。",
        f"- 当前状态：`{summary['status']}`。",
        "",
        "## 2. 输入",
        "",
        f"- `{rel(LATEST_SIGNAL)}`",
        f"- `{rel(run_dir / 'top50_signals.csv')}`",
        f"- `{rel(O4_MODEL)}`",
        f"- `{rel(O4_WHITELIST)}`",
        f"- `{rel(ORTHO_DAILY)}`",
        "",
        "## 3. 输出",
        "",
        f"- `{rel(out_csv)}`",
        f"- `{rel(OUT / f'daily_ltr_rerank_{asof}_feature_audit.csv')}`",
        f"- `{rel(OUT / f'daily_ltr_rerank_{asof}_pit_audit.json')}`",
        f"- `{rel(OUT / f'daily_ltr_rerank_{asof}_summary.json')}`",
        f"- `{rel(OUT / 'daily_ltr_rerank_latest.json')}`",
        "",
        "## 4. 安全与回归",
        "",
        "- 未触发 broker / orders / quick-trade / positions。",
        "- 未写 monitor config / scan / alerts。",
        "- 未切 accepted latest，未触发 provider publish / refresh。",
        "- 默认 fresh qlib 链路不受影响，仅写本地只读研究 artifact。",
        "",
        "## 5. 风险",
        "",
        "- O2 正交日表当前可用到 `2026-06-10` 的 trade_date / `2026-06-11` 的 available_at，P3 采用 as-of join，不补未来数据。",
        "- 若后续要把这条候选接到展示层，仍应保持只读语义。",
        "",
        "## 6. Gate",
        "",
        "```text",
        "phase_p3_daily_ltr_rerank_readonly_candidate_ready_for_review",
        "```",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "asof": asof, "summary": rel(OUT / f'daily_ltr_rerank_{asof}_summary.json'), "report": rel(REPORT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
