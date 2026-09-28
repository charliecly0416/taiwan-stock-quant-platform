from __future__ import annotations

import pickle
from typing import Any

import numpy as np
import pandas as pd

from .config import path
from .models import ModelBlocked


def _instrument(values: pd.Series) -> pd.Series:
    digits = values.astype(str).str.extract(r"(\d+)")[0]
    return "TW" + digits.str.zfill(4)


def _streak(values: pd.Series, signed: bool = False) -> pd.Series:
    output, count, sign = [], 0, 0
    for value in values.fillna(0):
        current = 0 if value == 0 else (1 if value > 0 else -1)
        if not signed:
            count = count + 1 if bool(value) else 0
            output.append(float(count))
        elif current == 0:
            sign, count = 0, 0; output.append(0.0)
        elif current == sign:
            count += 1; output.append(float(sign * count))
        else:
            sign, count = current, 1; output.append(float(sign))
    return pd.Series(output, index=values.index, dtype=float)


def _model_history(config: dict, current: pd.DataFrame, asof: str) -> pd.DataFrame:
    stage = config["model_stages"]["model_a_frozen"]
    target = path(stage["prediction_archive"])
    if target.suffix == ".csv":
        frame = pd.read_csv(target).rename(columns={stage.get("archive_score_column", "score"): "model_a_raw_score"})
        frame = frame[["date", "instrument", "model_a_raw_score"]]
    else:
        with target.open("rb") as handle:
            archive = pickle.load(handle)
        frame = archive.rename("model_a_raw_score").to_frame() if isinstance(archive, pd.Series) else archive.copy()
    if "model_a_raw_score" not in frame:
        frame.columns = ["model_a_raw_score"]
    frame = frame.reset_index().rename(columns={"datetime": "date"})
    frame["date"] = pd.to_datetime(frame.date).dt.date.astype(str)
    frame = frame[frame.date.le(asof)][["date", "instrument", "model_a_raw_score"]]
    now = current[["date", "instrument", "score"]].rename(columns={"score": "model_a_raw_score"})
    frame = pd.concat([frame, now], ignore_index=True).drop_duplicates(["date", "instrument"], keep="last")
    frame["qlib_rank"] = frame.groupby("date").model_a_raw_score.rank(method="first", ascending=False)
    group = frame.groupby("date").model_a_raw_score
    frame["qlib_score_raw"] = frame.model_a_raw_score
    frame["qlib_score_percentile_by_date"] = group.rank(pct=True)
    frame["qlib_score_zscore_by_date"] = (frame.model_a_raw_score - group.transform("mean")) / group.transform("std").replace(0, np.nan)
    frame = frame.sort_values(["instrument", "date"])
    for lag in (1, 3, 5):
        frame[f"rank_change_{lag}d"] = frame.groupby("instrument").qlib_rank.diff(lag)
    for limit in (10, 30, 50):
        frame[f"top{limit}_flag"] = frame.qlib_rank.le(limit).astype(float)
    frame["top30_streak"] = frame.groupby("instrument", group_keys=False).top30_flag.apply(_streak)
    frame["top50_streak"] = frame.groupby("instrument", group_keys=False).top50_flag.apply(_streak)
    return frame[frame.date.eq(asof)]


def _price_features(prices: pd.DataFrame, asof: str) -> tuple[pd.DataFrame, float]:
    frame = prices.rename(columns={"stock_id": "instrument", "Trading_Volume": "volume", "max": "high", "min": "low"}).copy()
    if frame.empty:
        raise ModelBlocked("B19R2R_PRICE_HISTORY_MISSING")
    frame["instrument"] = _instrument(frame.instrument)
    frame["date"] = frame.date.astype(str).str[:10]
    frame = frame[frame.date.le(asof)].sort_values(["instrument", "date"])
    output = []
    for _, rows in frame.groupby("instrument"):
        rows = rows.copy()
        close = pd.to_numeric(rows.close, errors="coerce")
        volume = pd.to_numeric(rows.volume, errors="coerce")
        for window in (5, 10, 20, 60): rows[f"MA{window}"] = close.rolling(window).mean()
        delta = close.diff(); gain = delta.clip(lower=0).rolling(14).mean(); loss = (-delta.clip(upper=0)).rolling(14).mean()
        rows["RSI14"] = (100 - 100 / (1 + gain / loss.replace(0, np.nan))).fillna(50)
        rows["MACD"] = close.ewm(span=12, min_periods=12, adjust=False).mean() - close.ewm(span=26, min_periods=26, adjust=False).mean()
        rows["Bollinger_position"] = ((close - rows.MA20) / (2 * close.rolling(20).std().replace(0, np.nan))).clip(-5, 5)
        daily = close.pct_change(fill_method=None)
        rows["ret20"] = close.pct_change(20, fill_method=None)
        rows["volatility20"] = daily.rolling(20).std()
        rows["volume_ratio20"] = volume / volume.rolling(20).mean().replace(0, np.nan)
        vwap = pd.to_numeric(rows.get("vwap", close), errors="coerce")
        value = volume * vwap
        rows["avg_trading_value_20d"] = value.rolling(20).mean()
        rows["volume_stability20"] = 1 / (1 + volume.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan).rolling(20).std())
        rows["missing_rate20"] = close.isna().astype(float).rolling(20, min_periods=1).mean()
        rows["suspension_proxy"] = (close.isna() | volume.le(0)).astype(float)
        rows["slippage_proxy"] = 1 / np.sqrt(value.where(value > 0))
        rows["_above"] = (close > rows.MA20).astype(float)
        output.append(rows.tail(1))
    latest = pd.concat(output, ignore_index=True)
    breadth = float(latest._above.mean())
    return latest, breadth


def _institutional(frame: pd.DataFrame, prior: str) -> pd.DataFrame:
    data = frame.rename(columns={"stock_id": "instrument"}).copy()
    if data.empty:
        raise ModelBlocked("B19R2R_INSTITUTIONAL_HISTORY_MISSING")
    data["instrument"] = _instrument(data.instrument); data["date"] = data.date.astype(str).str[:10]
    data["net"] = pd.to_numeric(data.buy, errors="coerce") - pd.to_numeric(data.sell, errors="coerce")
    label = data.name.astype(str).str.lower()
    data["group"] = np.select([label.str.contains("trust"), label.str.contains("dealer")], ["investment_trust_net_buy", "dealer_net_buy"], default="foreign_net_buy")
    data = data.groupby(["instrument", "date", "group"], as_index=False).net.sum().pivot(index=["instrument", "date"], columns="group", values="net").reset_index()
    for name in ("foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy"):
        if name not in data: data[name] = 0.0
    data["institutional_total_net_buy"] = data[["foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy"]].sum(axis=1)
    data = data.sort_values(["instrument", "date"])
    for name in ("foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy", "institutional_total_net_buy"):
        for window in (1, 3, 5, 10): data[f"{name}_roll{window}"] = data.groupby("instrument")[name].transform(lambda x: x.rolling(window, min_periods=1).sum())
    data["institutional_total_net_buy_streak"] = data.groupby("instrument", group_keys=False).institutional_total_net_buy.apply(_streak, signed=True)
    data["institutional_missing_flag"] = 0.0; data["institutional_delay_flag"] = 0.0; data["institutional_flow_delay_days"] = 0.0; data["institutional_flow_asof_missing_flag"] = 0.0
    return data[data.date.eq(prior)].drop(columns=["date"])


def _margin(frame: pd.DataFrame, prior: str) -> pd.DataFrame:
    data = frame.rename(columns={"stock_id": "instrument", "MarginPurchaseTodayBalance": "margin_balance", "ShortSaleTodayBalance": "short_balance"}).copy()
    if data.empty:
        raise ModelBlocked("B19R2R_MARGIN_HISTORY_MISSING")
    data["instrument"] = _instrument(data.instrument); data["date"] = data.date.astype(str).str[:10]
    data = data.sort_values(["instrument", "date"])
    for name in ("margin_balance", "short_balance"):
        data[name] = pd.to_numeric(data[name], errors="coerce"); data[f"{name}_change"] = data.groupby("instrument")[name].diff()
    for name in ("margin_balance_change", "short_balance_change"):
        for window in (1, 3, 5, 10): data[f"{name}_roll{window}"] = data.groupby("instrument")[name].transform(lambda x: x.rolling(window, min_periods=1).sum())
    data["margin_direction_proxy"] = np.sign(data.margin_balance_change); data["short_direction_proxy"] = np.sign(data.short_balance_change)
    data["margin_short_divergence_proxy"] = data.margin_direction_proxy - data.short_direction_proxy
    data["margin_short_missing_flag"] = 0.0; data["margin_short_delay_flag"] = 0.0; data["margin_short_delay_days"] = 0.0; data["margin_short_asof_missing_flag"] = 0.0
    return data[data.date.eq(prior)].drop(columns=["date"])


def _market(frame: pd.DataFrame, asof: str) -> dict[str, float]:
    data = frame.copy(); data["date"] = data.date.astype(str).str[:10]
    close = pd.to_numeric(data.drop_duplicates("date").sort_values("date").set_index("date").close, errors="coerce")
    close = close[close.index <= asof]
    if len(close) < 120:
        raise ModelBlocked("B19R2R_TWII_HISTORY_MISSING", f"rows={len(close)}")
    return {
        "TWII_ret20": close.pct_change(20).iloc[-1], "TWII_ret60": close.pct_change(60).iloc[-1],
        "TWII_close_vs_MA60": close.iloc[-1] / close.rolling(60).mean().iloc[-1] - 1,
        "TWII_close_vs_MA120": close.iloc[-1] / close.rolling(120).mean().iloc[-1] - 1,
        "market_volatility20": close.pct_change().rolling(20).std().iloc[-1],
        "market_drawdown60": close.iloc[-1] / close.rolling(60).max().iloc[-1] - 1,
    }


def build_b19_features(*, asof: str, model_a: pd.DataFrame, data: dict[str, pd.DataFrame], config: dict, feature_order: list[str]) -> pd.DataFrame:
    prices = data.get("prices", pd.DataFrame())
    dates = sorted(day for day in prices.get("date", pd.Series(dtype=str)).astype(str).unique() if day <= asof)
    if asof not in dates or len(dates) < 2:
        raise ModelBlocked("B19R2R_PRICE_CALENDAR_MISSING", asof)
    prior = dates[-2]
    score = _model_history(config, model_a, asof)
    technical, breadth = _price_features(prices, asof)
    output = model_a.head(50)[["date", "instrument"]].merge(score, on=["date", "instrument"]).merge(technical, on=["date", "instrument"])
    output = output.merge(_institutional(data.get("institutional", pd.DataFrame()), prior), on="instrument", how="left")
    output = output.merge(_margin(data.get("margin", pd.DataFrame()), prior), on="instrument", how="left")
    output["market_breadth20"] = breadth
    for name, value in _market(data.get("twii", pd.DataFrame()), asof).items(): output[name] = value
    return output[["date", "instrument", *feature_order]]
