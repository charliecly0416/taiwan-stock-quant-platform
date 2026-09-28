"""Yahoo-only staged provider refresh used by the clean daily lane.

The refresh is deliberately run-specific.  It writes normalized CSVs and a
Qlib provider below the daily artifact root, validates as-of coverage, and
returns paths for that run.  The caller may use those paths for Model A; no
formal provider or latest pointer is replaced by this module.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta, timezone
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .config import path


FIELDS = ("open", "high", "low", "close", "volume", "vwap", "factor")
COLUMNS = ("symbol", "date", *FIELDS)


def _epoch(day: str, end: bool = False) -> int:
    value = pd.Timestamp(day).to_pydatetime().replace(tzinfo=timezone.utc)
    if end:
        value += timedelta(days=1)
    return int(value.timestamp())


def _ticker(symbol: str) -> list[str]:
    if symbol == "TWII":
        return ["^TWII"]
    code = symbol.removeprefix("TW")
    return [f"{code}.TW", f"{code}.TWO"]


def _frame(symbol: str, payload: dict[str, Any]) -> pd.DataFrame:
    result = (payload.get("chart", {}).get("result") or [None])[0]
    if not result:
        return pd.DataFrame(columns=COLUMNS)
    timestamps = result.get("timestamp") or []
    quote = (result.get("indicators", {}).get("quote") or [{}])[0]
    adjusted = (result.get("indicators", {}).get("adjclose") or [{}])[0]
    rows = []
    for index, stamp in enumerate(timestamps):
        values = {key: (quote.get(key) or [None] * len(timestamps))[index]
                  for key in ("open", "high", "low", "close", "volume")}
        close_adj = (adjusted.get("adjclose") or [None] * len(timestamps))[index]
        try:
            raw = [float(values[key]) for key in ("open", "high", "low", "close")]
            adj = float(close_adj)
            volume = float(values["volume"] or 0)
        except (TypeError, ValueError):
            continue
        if not all(math.isfinite(value) and value > 0 for value in (*raw, adj)):
            continue
        factor = adj / raw[3]
        if not math.isfinite(factor) or factor <= 0:
            continue
        open_, high, low, close = [value * factor for value in raw]
        rows.append({"symbol": symbol, "date": pd.Timestamp(stamp, unit="s", tz="UTC").date().isoformat(),
                     "open": open_, "high": max(high, open_, close), "low": min(low, open_, close),
                     "close": close, "volume": max(0, volume),
                     "vwap": (open_ + high + low + close) / 4, "factor": factor})
    return pd.DataFrame(rows, columns=COLUMNS).drop_duplicates("date").sort_values("date")


def _fetch(symbol: str, start: str, asof: str, proxy: str) -> pd.DataFrame:
    try:
        from scrapling.fetchers import Fetcher
    except ImportError as exc:  # pragma: no cover - deployment dependency
        raise RuntimeError("scrapling is required for Yahoo provider refresh") from exc
    params = {"period1": str(_epoch(start)), "period2": str(_epoch(asof, end=True)),
              "interval": "1d", "events": "history", "includeAdjustedClose": "true"}
    kwargs = {"proxy": proxy} if proxy else {}
    headers = {"Referer": "https://www.google.com/"}
    for ticker in _ticker(symbol):
        page = Fetcher.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
                           params=params, timeout=45, retries=1, impersonate="chrome",
                           headers=headers, **kwargs)
        if int(page.status) >= 400:
            continue
        frame = _frame(symbol, page.json())
        if not frame.empty:
            return frame
    return pd.DataFrame(columns=COLUMNS)


def market_asof(config: dict, today: str) -> str:
    """Resolve actual index sessions; weekends/holidays do not fabricate dates."""
    start = (date.fromisoformat(today) - timedelta(days=20)).isoformat()
    frame = _fetch("TWII", start, today, str(config.get("provider_refresh", {}).get("proxy", "")))
    days = frame.loc[frame.date.le(today), "date"]
    if days.empty:
        raise RuntimeError("MARKET_CALENDAR_UNAVAILABLE")
    return str(days.max())


def _write_provider(normalized: Path, provider: Path) -> dict[str, Any]:
    files = sorted(normalized.glob("TW*.csv"))
    files = [p for p in files if p.stem != "TWII"]
    # Keep the provider build bounded by the largest single symbol file.  A
    # full Taiwan universe is several million rows; retaining every frame in
    # a dict here can exhaust the daily worker before the binary write starts.
    calendar_values: set[str] = set()
    for filename in files:
        dates = pd.read_csv(filename, usecols=["date"])["date"]
        calendar_values.update(str(value)[:10] for value in dates)
    calendar = sorted(calendar_values)
    if not calendar:
        raise RuntimeError("Yahoo refresh produced no calendar")
    provider.mkdir(parents=True, exist_ok=False)
    (provider / "calendars").mkdir()
    (provider / "features").mkdir()
    (provider / "instruments").mkdir()
    (provider / "calendars/day.txt").write_text("\n".join(calendar) + "\n")
    instrument_rows = []
    positions = {day: index for index, day in enumerate(calendar)}
    for filename in files:
        symbol = filename.stem
        frame = pd.read_csv(filename)
        frame = frame.drop_duplicates("date").sort_values("date")
        first, last = str(frame.date.iloc[0])[:10], str(frame.date.iloc[-1])[:10]
        instrument_rows.append(f"{symbol}\t{first}\t{last}")
        folder = provider / "features" / symbol.lower(); folder.mkdir()
        start, end = positions[first], positions[last]
        lookup = frame.set_index(frame.date.astype(str).str[:10])
        for field in FIELDS:
            values = np.full(end - start + 1, np.nan, dtype="<f4")
            for day, value in lookup[field].items():
                if day in positions and start <= positions[day] <= end:
                    values[positions[day] - start] = float(value)
            np.concatenate((np.asarray([start], dtype="<f4"), values)).tofile(folder / f"{field}.day.bin")
    (provider / "instruments/all.txt").write_text("\n".join(instrument_rows) + "\n")
    return {"calendar_min": calendar[0], "calendar_max": calendar[-1],
            "calendar_count": len(calendar), "symbols": len(files)}


def refresh_yahoo_provider(config: dict, asof: str, run_id: str) -> dict[str, Any]:
    settings = config.get("provider_refresh") or {}
    source = path(settings.get("source_dir", config["model_stages"]["model_a_frozen"].get("selection_prices", "")))
    if not source.is_dir():
        raise RuntimeError(f"provider refresh source missing: {source}")
    symbols = sorted(p.stem for p in source.glob("TW*.csv") if p.stem != "TWII")
    if not symbols:
        raise RuntimeError("provider refresh source has no symbols")
    root = path(config["artifact_root"]) / "provider_runs" / run_id
    normalized = root / "normalized"; provider = root / "provider"
    normalized.mkdir(parents=True, exist_ok=False)
    proxy = str(settings.get("proxy", "http://127.0.0.1:7890"))
    history_start = str(settings.get("start", "2015-01-01"))
    incremental_start = (date.fromisoformat(asof) - timedelta(days=int(settings.get("incremental_days", 45)))).isoformat()

    def refresh(symbol: str) -> tuple[str, bool, str | None]:
        existing_path = source / f"{symbol}.csv"
        existing = pd.read_csv(existing_path) if existing_path.exists() else pd.DataFrame(columns=COLUMNS)
        existing = existing.loc[existing.date.astype(str).le(asof)].copy()
        start = incremental_start if not existing.empty and str(existing.date.max()) >= incremental_start else history_start
        error = None
        try:
            incoming = _fetch(symbol, start, asof, proxy)
            if not existing.empty and not incoming.empty:
                overlap = existing.merge(incoming, on="date", suffixes=("_old", "_new"))
                if not overlap.empty and not np.allclose(overlap.factor_old, overlap.factor_new, rtol=1e-5, atol=1e-8):
                    # Corporate actions revise adjusted history, not only the overlap.
                    incoming = _fetch(symbol, history_start, asof, proxy)
                    if incoming.empty:
                        raise RuntimeError("ADJUSTED_HISTORY_UNAVAILABLE")
                    existing = existing.iloc[:0]
        except Exception as exc:
            incoming = pd.DataFrame(columns=COLUMNS)
            error = type(exc).__name__
        # Avoid concatenating an empty frame: recent symbols can have no
        # existing history, and pandas warns that dtype inference for empty
        # frames will change in a future release.
        parts = [frame for frame in (existing, incoming) if not frame.empty]
        merged = (pd.concat(parts, ignore_index=True)
                  if parts else pd.DataFrame(columns=COLUMNS))
        merged = merged.drop_duplicates(["symbol", "date"], keep="last")
        merged = merged[list(COLUMNS)].sort_values("date").reset_index(drop=True)
        covered = asof in set(merged.date.astype(str))
        if not merged.empty:
            merged.to_csv(normalized / f"{symbol}.csv", index=False)
        # Futures retain their return value: never return an entire price frame.
        return symbol, covered, error

    covered_symbols, errors = [], {}
    with ThreadPoolExecutor(max_workers=int(settings.get("workers", 8))) as executor:
        futures = [executor.submit(refresh, symbol) for symbol in symbols]
        for future in as_completed(futures):
            symbol, covered, error = future.result()
            if covered:
                covered_symbols.append(symbol)
            if error:
                errors[symbol] = error
    coverage = len(covered_symbols) / len(symbols)
    minimum = float(settings.get("minimum_coverage", 0.95))
    if coverage < minimum:
        raise RuntimeError(f"provider refresh coverage {coverage:.3f} below {minimum:.3f}")
    info = _write_provider(normalized, provider)
    return {"status": "READY", "asof": asof, "run_id": run_id, "source_symbols": len(symbols),
            "available_symbols": len(covered_symbols), "coverage": coverage, "fetch_errors": errors, "provider": str(provider),
            "selection_prices": str(normalized), "universe_file": str(provider / "instruments/all.txt"), **info}
