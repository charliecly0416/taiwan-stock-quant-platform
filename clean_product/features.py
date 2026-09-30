from __future__ import annotations

from datetime import date
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .artifacts import manifest, sha256, utc_now, write_json
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
    frozen = path(config["model_stages"]["b19r2r_frozen"]["historical_features"])
    frame = pd.read_parquet(frozen, columns=["date", "instrument", "qlib_score_raw", "qlib_rank"])
    frame = frame.rename(columns={"qlib_score_raw": "model_a_raw_score"})
    history = config.get("_shadow_history")
    if history:
        extra = pd.read_parquet(history).rename(columns={"score": "model_a_raw_score", "rank": "qlib_rank"})
        frame = pd.concat([frame, extra[["date", "instrument", "model_a_raw_score", "qlib_rank"]]], ignore_index=True)
    now = current[["date", "instrument", "score", "rank"]].rename(columns={"score": "model_a_raw_score", "rank": "qlib_rank"})
    frame = pd.concat([frame, now], ignore_index=True).drop_duplicates(["date", "instrument"], keep="last")
    frame["date"] = pd.to_datetime(frame.date).dt.date.astype(str)
    frame = frame[frame.date.le(asof)]
    if config.get("_shadow_calendar"):
        frame = frame[frame.date.isin(config["_shadow_calendar"])]
    group = frame.groupby("date").model_a_raw_score
    frame["qlib_score_raw"] = frame.model_a_raw_score
    frame["qlib_score_percentile_by_date"] = group.rank(pct=True)
    frame["qlib_score_zscore_by_date"] = ((frame.model_a_raw_score - group.transform("mean")) / group.transform("std").replace(0, np.nan)).fillna(0.0)
    frame = frame.sort_values(["instrument", "date"])
    for lag in (1, 3, 5):
        frame[f"rank_change_{lag}d"] = frame.groupby("instrument").qlib_rank.diff(lag)
    for limit in (10, 30, 50):
        frame[f"top{limit}_flag"] = frame.qlib_rank.le(limit).astype(float)
    days = sorted(frame.date.unique())
    for limit in (30, 50):
        flag = frame.pivot(index="date", columns="instrument", values=f"top{limit}_flag").reindex(days)
        streak = flag.apply(_streak).stack().rename(f"top{limit}_streak").reset_index()
        frame = frame.merge(streak, on=["date", "instrument"], validate="one_to_one")
    return frame[frame.date.eq(asof)]


def _price_features(prices: pd.DataFrame, asof: str, calendar: list[str] | None = None, breadth_symbols: set | None = None) -> tuple[pd.DataFrame, float]:
    frame = prices.rename(columns={"stock_id": "instrument", "Trading_Volume": "volume", "max": "high", "min": "low"}).copy()
    if frame.empty:
        raise ModelBlocked("B19R2R_PRICE_HISTORY_MISSING")
    frame["instrument"] = _instrument(frame.instrument)
    frame["date"] = frame.date.astype(str).str[:10]
    frame = frame[frame.date.le(asof)]
    frame = frame.sort_values(["instrument", "date"])
    calendar = calendar or sorted(frame.date.unique())
    output = []
    for instrument, rows in frame.groupby("instrument"):
        rows = rows.drop_duplicates("date").set_index("date").reindex(calendar).rename_axis("date").reset_index()
        rows["instrument"] = instrument
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
        rows["suspension_proxy"] = (rows[["open", "high", "low", "close", "volume"]].isna().any(axis=1) | volume.le(0)).astype(float)
        rows["slippage_proxy"] = 1 / np.sqrt(value.where(value > 0))
        rows["_above"] = (close > rows.MA20).astype(float)
        output.append(rows.tail(1))
    latest = pd.concat(output, ignore_index=True)
    breadth_rows = latest if breadth_symbols is None else latest[latest.instrument.isin(breadth_symbols)]
    breadth = float(breadth_rows._above.mean())
    return latest, breadth


def _institutional(frame: pd.DataFrame, prior: str, *, asof: str | None = None) -> pd.DataFrame:
    data = frame.rename(columns={"stock_id": "instrument"}).copy()
    if data.empty:
        raise ModelBlocked("B19R2R_INSTITUTIONAL_HISTORY_MISSING")
    data["instrument"] = _instrument(data.instrument); data["date"] = data.date.astype(str).str[:10]
    if asof and "available_at" in data:
        available = pd.to_datetime(data["available_at"], errors="coerce").dt.date
        data = data[available <= date.fromisoformat(asof)].copy()
        if data.empty:
            raise ModelBlocked("B19R2R_INSTITUTIONAL_HISTORY_MISSING")
    data["net"] = pd.to_numeric(data.buy, errors="coerce") - pd.to_numeric(data.sell, errors="coerce")
    labels = {"Foreign_Investor": "foreign_net_buy", "Foreign_Dealer_Self": "foreign_net_buy", "Investment_Trust": "investment_trust_net_buy",
              "Dealer_self": "dealer_net_buy", "Dealer_Hedging": "dealer_net_buy"}
    data["group"] = data.name.map(labels)
    data = data.dropna(subset=["group"])
    metadata = [name for name in ("available_at", "_delay_flag", "_delay_days") if name in data]
    availability = data.groupby(["instrument", "date"])[metadata].max() if metadata else None
    data = data.groupby(["instrument", "date", "group"]).net.sum(min_count=1).unstack("group").reset_index()
    names = ["foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy"]
    for name in names:
        if name not in data: data[name] = np.nan
    data["institutional_total_net_buy"] = data[names].sum(axis=1, min_count=3)
    if availability is not None:
        data = data.merge(availability, on=["instrument", "date"])
    data = data.sort_values(["instrument", "date"])
    for name in ("foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy", "institutional_total_net_buy"):
        for window in (1, 3, 5, 10): data[f"{name}_roll{window}"] = data.groupby("instrument")[name].transform(lambda x: x.rolling(window, min_periods=1).sum())
    data["institutional_total_net_buy_streak"] = data.groupby("instrument", group_keys=False).institutional_total_net_buy.apply(_streak, signed=True)
    invalid = data[names].isna().any(axis=1)
    data["institutional_missing_flag"] = invalid.astype(float)
    data["institutional_flow_asof_missing_flag"] = invalid.astype(float)
    data["institutional_delay_flag"] = data.get("_delay_flag", 0.0)
    data["institutional_flow_delay_days"] = data.get("_delay_days", 0.0)
    if asof and "available_at" in data:
        data = data[data.date.eq(prior)].sort_values(["instrument", "date"]).groupby("instrument", as_index=False).tail(1)
    else:
        data = data[data.date.eq(prior)]
    return data.drop(columns=["date", "available_at"], errors="ignore")


def _margin(frame: pd.DataFrame, prior: str, *, asof: str | None = None) -> pd.DataFrame:
    data = frame.rename(columns={"stock_id": "instrument", "MarginPurchaseTodayBalance": "margin_balance", "ShortSaleTodayBalance": "short_balance"}).copy()
    if data.empty:
        raise ModelBlocked("B19R2R_MARGIN_HISTORY_MISSING")
    data["instrument"] = _instrument(data.instrument); data["date"] = data.date.astype(str).str[:10]
    if asof and "available_at" in data:
        available = pd.to_datetime(data["available_at"], errors="coerce").dt.date
        data = data[available <= date.fromisoformat(asof)].copy()
        if data.empty:
            raise ModelBlocked("B19R2R_MARGIN_HISTORY_MISSING")
    data = data.sort_values(["instrument", "date"])
    for name in ("margin_balance", "short_balance"):
        data[name] = pd.to_numeric(data[name], errors="coerce")
        yesterday = "MarginPurchaseYesterdayBalance" if name == "margin_balance" else "ShortSaleYesterdayBalance"
        data[f"{name}_change"] = data[name] - pd.to_numeric(data.get(yesterday, pd.Series(index=data.index, dtype=float)), errors="coerce")
    if "Note" in data:
        data.loc[data.Note.fillna("").str.strip().eq("OX"), ["margin_balance", "short_balance", "margin_balance_change", "short_balance_change"]] = np.nan
    for name in ("margin_balance_change", "short_balance_change"):
        for window in (1, 3, 5, 10): data[f"{name}_roll{window}"] = data.groupby("instrument")[name].transform(lambda x: x.rolling(window, min_periods=1).sum())
    data["margin_direction_proxy"] = np.sign(data.margin_balance_change); data["short_direction_proxy"] = np.sign(data.short_balance_change)
    data["margin_short_divergence_proxy"] = data.margin_direction_proxy - data.short_direction_proxy
    invalid = data[["margin_balance", "short_balance", "margin_balance_change", "short_balance_change"]].isna().any(axis=1)
    data["margin_short_missing_flag"] = invalid.astype(float)
    data["margin_short_asof_missing_flag"] = invalid.astype(float)
    data["margin_short_delay_flag"] = data.get("_delay_flag", 0.0)
    data["margin_short_delay_days"] = data.get("_delay_days", 0.0)
    if asof and "available_at" in data:
        data = data[data.date.eq(prior)].sort_values(["instrument", "date"]).groupby("instrument", as_index=False).tail(1)
    else:
        data = data[data.date.eq(prior)]
    return data.drop(columns=["date", "available_at"], errors="ignore")


def _market(frame: pd.DataFrame, asof: str, calendar: list[str] | None = None) -> dict[str, float]:
    data = frame.copy(); data["date"] = data.date.astype(str).str[:10]
    close = pd.to_numeric(data.drop_duplicates("date").sort_values("date").set_index("date").close, errors="coerce")
    close = close[close.index <= asof]
    if calendar is not None:
        close = close.reindex(calendar)
    if close.empty or close.index[-1] != asof or close.tail(120).isna().any():
        raise ModelBlocked("B19R2R_TWII_STALE_OR_GAPPED")
    if len(close) < 120:
        raise ModelBlocked("B19R2R_TWII_HISTORY_MISSING", f"rows={len(close)}")
    return {
        "TWII_ret20": close.pct_change(20, fill_method=None).iloc[-1], "TWII_ret60": close.pct_change(60, fill_method=None).iloc[-1],
        "TWII_close_vs_MA60": close.iloc[-1] / close.rolling(60).mean().iloc[-1] - 1,
        "TWII_close_vs_MA120": close.iloc[-1] / close.rolling(120).mean().iloc[-1] - 1,
        "market_volatility20": close.pct_change(fill_method=None).rolling(20).std().iloc[-1],
        "market_drawdown60": close.iloc[-1] / close.rolling(60).max().iloc[-1] - 1,
    }


def build_b19_features(*, asof: str, model_a: pd.DataFrame, data: dict[str, pd.DataFrame], config: dict, feature_order: list[str]) -> pd.DataFrame:
    prices = data.get("prices", pd.DataFrame())
    dates = data.get("__calendar") or sorted(day for day in prices.get("date", pd.Series(dtype=str)).astype(str).unique() if day <= asof)
    if asof not in dates or len(dates) < 2:
        raise ModelBlocked("B19R2R_PRICE_CALENDAR_MISSING", asof)
    prior = dates[-2]
    score = _model_history(config, model_a, asof)
    from .config import trading_days
    calendar = data.get("__calendar") or [day for day in trading_days(config) if dates[0] <= day <= asof] or dates
    breadth_symbols = set(pd.read_parquet(path(config["model_stages"]["b19r2r_frozen"]["historical_features"]), columns=["instrument"]).instrument.unique())
    technical, breadth = _price_features(prices, asof, calendar, breadth_symbols)
    exact = model_a.sort_values("rank").head(50)
    exact = exact[~exact.instrument.isin(config["model_stages"]["b19r2r_frozen"].get("exclude", []))]
    output = exact[["date", "instrument"]].merge(score, on=["date", "instrument"]).merge(technical, on=["date", "instrument"])
    output = output.merge(_institutional(data.get("institutional", pd.DataFrame()), prior, asof=asof), on="instrument", how="left")
    output = output.merge(_margin(data.get("margin", pd.DataFrame()), prior, asof=asof), on="instrument", how="left")
    output["market_breadth20"] = breadth
    for name, value in _market(data.get("twii", pd.DataFrame()), asof, calendar).items(): output[name] = value
    if len(output) != len(exact) or set(output.instrument) != set(exact.instrument):
        raise ModelBlocked("B19R2R_EXACT50_KEY_MISMATCH")
    return output[["date", "instrument", *feature_order]]


def validate_b19_inputs(*, asof: str, data: dict[str, pd.DataFrame], config: dict) -> str:
    """Validate the source dates that can be used for a same-day B19R2R run.

    The model uses the previous market session for delayed FinMind flows.  A
    source that only has old rows must therefore block the shadow lane instead
    of silently producing a feature row from stale data.
    """
    prices = data.get("prices", pd.DataFrame())
    if prices.empty or "date" not in prices:
        raise ModelBlocked("B19R2R_PRICE_HISTORY_MISSING")
    price_dates = data.get("__calendar") or sorted({str(value)[:10] for value in prices["date"].dropna() if str(value)[:10] <= asof})
    if asof not in price_dates or len(price_dates) < 2:
        raise ModelBlocked("B19R2R_PRICE_CALENDAR_MISSING", asof)
    prior = price_dates[-2]
    for name in ("institutional", "margin", "twii"):
        frame = data.get(name, pd.DataFrame())
        if frame.empty or "date" not in frame:
            raise ModelBlocked(f"B19R2R_{name.upper()}_HISTORY_MISSING")
        dates = pd.to_datetime(frame["date"], errors="coerce").dt.date
        if dates.isna().any():
            raise ModelBlocked(f"B19R2R_{name.upper()}_DATE_INVALID")
        spec = (config.get("datasets") or {}).get(name, {})
        lag_days = int(spec.get("lag_days", 0)) if isinstance(spec, dict) else int(getattr(spec, "lag_days", 0))
        latest_allowed = prior if lag_days > 0 else asof
        usable = dates[dates <= date.fromisoformat(latest_allowed)]
        if usable.empty or max(usable).isoformat() < latest_allowed:
            latest = max(usable).isoformat() if not usable.empty else max(dates).isoformat()
            raise ModelBlocked(f"B19R2R_{name.upper()}_STALE", f"{latest}<{prior}")
    return prior


def derive_available_at(*, asof: str, data: dict[str, pd.DataFrame], config: dict) -> None:
    """Attach a conservative availability timestamp to live source frames.

    FinMind rows carry trade dates but no trustworthy publication timestamp in
    the public response.  The registered lag policy therefore maps delayed
    families to the next price session; the feature join can only consume rows
    whose derived availability is at or before the decision date.
    """
    prices = data.get("prices", pd.DataFrame())
    if prices.empty or "date" not in prices:
        return
    calendar = data.get("__calendar") or sorted({str(value)[:10] for value in prices["date"].dropna()})
    next_session = {day: calendar[index + 1] for index, day in enumerate(calendar[:-1])}
    for name in ("institutional", "margin", "twii"):
        frame = data.get(name)
        if frame is None or frame.empty or "date" not in frame:
            continue
        item = frame.copy()
        lag = int((config.get("datasets", {}).get(name, {}) or {}).get("lag_days", 0))
        derived = item["date"].astype(str).str[:10].map(next_session if lag > 0 else lambda value: value)
        if "available_at" in item:
            item["available_at"] = item["available_at"].where(item["available_at"].notna(), derived)
        else:
            item["available_at"] = derived
        expected = pd.to_datetime(derived, errors="coerce")
        observed = pd.to_datetime(item["available_at"], errors="coerce")
        item["_delay_days"] = (observed - expected).dt.days
        item["_delay_flag"] = observed.ne(expected).astype(float)
        data[name] = item


def write_b19_feature_artifact(*, frame: pd.DataFrame, asof: str, config: dict,
                               feature_order: list[str], run_id: str) -> dict[str, Any]:
    """Persist one immutable, current-date feature delta for a daily release."""
    if len(feature_order) != 78 or len(set(feature_order)) != 78:
        raise ModelBlocked("B19R2R_FEATURE_SCHEMA_INVALID")
    expected = {"date", "instrument", *feature_order}
    missing = sorted(expected - set(frame.columns))
    if missing:
        raise ModelBlocked("B19R2R_FEATURE_COLUMNS_MISSING", ",".join(missing[:8]))
    output = frame[["date", "instrument", *feature_order]].copy()
    output["date"] = output["date"].astype(str).str[:10]
    output["instrument"] = output["instrument"].astype(str)
    values = output[feature_order].apply(pd.to_numeric, errors="coerce")
    bad = [name for name in feature_order if not np.isfinite(values[name].to_numpy(dtype=float)).all()]
    if bad:
        raise ModelBlocked("B19R2R_INCOMPLETE_78F", ",".join(bad[:8]))
    output[feature_order] = values.astype(float)
    if output.empty:
        raise ModelBlocked("B19R2R_FEATURE_EMPTY")
    if output.duplicated(["date", "instrument"]).any() or not output.date.eq(asof).all():
        raise ModelBlocked("B19R2R_FEATURE_KEY_INVALID")
    output = output.assign(feature_raw_complete_78=True, raw_missing_features="", available_at=asof)
    root = Path(config["artifact_root"]) / "shadow_features" / asof
    root.mkdir(parents=True, exist_ok=True)
    target = root / "FEATURE_ARTIFACT_DELTA.parquet"
    if target.exists():
        raise ModelBlocked("B19R2R_FEATURE_ALREADY_EXISTS")
    temporary = target.with_suffix(f".{run_id}.tmp.parquet")
    output.to_parquet(temporary, index=False)
    temporary.replace(target)
    payload = manifest(
        artifact_type="FeatureArtifact", status="READY", asof=asof, run_id=run_id,
        files={"features": target}, feature_count=len(feature_order), row_count=len(output),
        feature_order=feature_order, feature_raw_complete_78=True, available_at=asof,
        role="shadow", production_allowed=False, mainline_blocking=False,
        availability_policy="next_market_session", availability_is_derived=True,
        captured_at=utc_now(), source_inputs=config.get("_shadow_sources", {}),
    )
    write_json(root / "manifest.json", payload)
    return {"path": str(target), "sha256": sha256(target), "manifest": str(root / "manifest.json"),
            "rows": len(output), "asof": asof, "status": "READY"}
