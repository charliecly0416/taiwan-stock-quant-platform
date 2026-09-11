from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
VENDOR_NAME = "quantdinger_tw"
SCRAPLING_CACHE_DIR = ROOT / "data_tw/artifacts/analysis/tradingagents_readonly/_scrapling_cache"
SOURCE_PACKET_STORE_DIR = ROOT / "data_tw/artifacts/analysis/tradingagents_readonly/source_packet_store/packets"
DEFAULT_PRICE_DIRS = (
    ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty",
    ROOT / "data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_r_real_model_a_top50_bridge_coverage_repair/stock_price_bridge",
    ROOT / "data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/stock_price_bridge",
)

NEWS_SOURCE_TYPES = {
    "company_news_release",
    "exchange_announcement",
    "approved_news_article_excerpt",
    "sector_event_note",
}
FUNDAMENTAL_SOURCE_TYPES = {
    "company_filing",
    "financial_report_text",
    "earnings_call_or_investor_meeting_transcript",
}

LOCAL_INSTRUMENT_IDENTITIES = {
    "TW2330": {
        "company_name": "台積電 / Taiwan Semiconductor Manufacturing Co.",
        "sector": "Technology",
        "industry": "Semiconductors",
    },
    "TW2317": {
        "company_name": "鴻海 / Hon Hai Precision Industry Co.",
        "sector": "Technology",
        "industry": "Electronic Manufacturing Services",
    },
    "TW2454": {
        "company_name": "聯發科 / MediaTek Inc.",
        "sector": "Technology",
        "industry": "Semiconductors",
    },
}

INDICATOR_DESCRIPTIONS = {
    "close_50_sma": "50 SMA: medium-term trend indicator based on local adjusted close data.",
    "close_200_sma": "200 SMA: long-term trend benchmark based on local adjusted close data.",
    "close_10_ema": "10 EMA: short-term exponential moving average based on local adjusted close data.",
    "macd": "MACD: momentum indicator computed from local adjusted close data.",
    "macds": "MACD Signal: signal line computed from local adjusted close data.",
    "macdh": "MACD Histogram: MACD minus signal line computed from local adjusted close data.",
    "rsi": "RSI: momentum oscillator computed from local adjusted close data.",
    "boll": "Bollinger Middle: 20-day moving average computed from local adjusted close data.",
    "boll_ub": "Bollinger Upper Band: middle band plus two standard deviations.",
    "boll_lb": "Bollinger Lower Band: middle band minus two standard deviations.",
    "atr": "ATR: average true range computed from local adjusted OHLC data.",
    "vwma": "VWMA: volume-weighted moving average computed from local adjusted close and volume data.",
    "mfi": "MFI: money flow index computed from local adjusted OHLCV data.",
}


def _fail_closed_source_message(
    *,
    source_kind: str,
    requested: str,
    date_context: str | None = None,
) -> str:
    suffix = f" Date context: {date_context}." if date_context else ""
    return (
        f"NO_GROUNDED_LOCAL_SOURCE_AVAILABLE: QuantDinger Taiwan readonly provider "
        f"has no approved local {source_kind} source for {requested}.{suffix} "
        "This is a fail-closed source-grounding sentinel. Do not infer, fabricate, "
        "or replace it with general market knowledge. State that the source is "
        "unavailable and limit the analysis to explicitly grounded tools."
    )


def _packet_date(packet: dict[str, Any]) -> pd.Timestamp | None:
    for key in ("source_published_at", "evidence_asof", "evidence_window_start"):
        value = packet.get(key)
        if value:
            parsed = pd.to_datetime(value, errors="coerce", utc=True)
            if not pd.isna(parsed):
                return parsed.tz_convert(None).normalize()
    return None


def _packet_symbol_id(packet: dict[str, Any]) -> str | None:
    symbol = packet.get("symbol")
    if symbol is None:
        return None
    try:
        return _tw_symbol_id(str(symbol))
    except Exception:
        return None


def _load_source_packets(
    *,
    symbol: str,
    start_date: str | None,
    end_date: str | None,
    source_types: set[str],
) -> list[dict[str, Any]]:
    if not SOURCE_PACKET_STORE_DIR.exists():
        return []
    tw_symbol = _tw_symbol_id(symbol)
    start = pd.to_datetime(start_date).normalize() if start_date else None
    end = pd.to_datetime(end_date).normalize() if end_date else None
    packets: list[dict[str, Any]] = []
    for path in sorted(SOURCE_PACKET_STORE_DIR.glob("*.json")):
        try:
            packet = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(packet, dict):
            continue
        if _packet_symbol_id(packet) != tw_symbol:
            continue
        if str(packet.get("source_type") or "") not in source_types:
            continue
        excerpt = str(packet.get("approved_excerpt") or "").strip()
        source_ref = str(packet.get("source_ref") or "").strip()
        if not excerpt or not source_ref:
            continue
        packet_day = _packet_date(packet)
        if packet_day is None:
            continue
        if start is not None and packet_day < start:
            continue
        if end is not None and packet_day > end:
            continue
        enriched = dict(packet)
        enriched["_store_path"] = _display_path(path)
        enriched["_packet_day"] = packet_day.strftime("%Y-%m-%d")
        packets.append(enriched)
    packets.sort(key=lambda item: str(item.get("_packet_day") or ""), reverse=True)
    return packets


def _render_source_packets(
    *,
    symbol: str,
    heading: str,
    packets: list[dict[str, Any]],
) -> str:
    lines = [
        f"## {heading} for {_tw_symbol_id(symbol)}",
        "",
        "These are approved local source packets for readonly research grounding only.",
        "Do not infer beyond the approved excerpts. Do not treat this as trading advice.",
        "",
    ]
    for index, packet in enumerate(packets, start=1):
        metadata = packet.get("approved_metadata") if isinstance(packet.get("approved_metadata"), dict) else {}
        usage = packet.get("license_or_usage_boundary") if isinstance(packet.get("license_or_usage_boundary"), dict) else {}
        lines.extend([
            f"### Packet {index}: {packet.get('source_title') or packet.get('evidence_packet_id')}",
            f"- packet_id: {packet.get('evidence_packet_id')}",
            f"- source_type: {packet.get('source_type')}",
            f"- source_ref: {packet.get('source_ref')}",
            f"- source_published_at: {packet.get('source_published_at') or packet.get('evidence_asof')}",
            f"- evidence_asof: {packet.get('evidence_asof')}",
            f"- store_path: {packet.get('_store_path')}",
            f"- approval_id: {metadata.get('approval_id')}",
            f"- usage_class: {usage.get('usage_class')}",
            "",
            "Approved excerpt:",
            str(packet.get("approved_excerpt") or "").strip(),
            "",
        ])
    return "\n".join(lines).strip()


def _raise_no_market_data(symbol: str, canonical: str, detail: str) -> None:
    try:
        from tradingagents.dataflows.symbol_utils import NoMarketDataError  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"No market data for {symbol} ({canonical}): {detail}") from exc
    raise NoMarketDataError(symbol, canonical, detail)


def _tw_symbol_id(symbol: str) -> str:
    clean = str(symbol or "").strip().upper()
    if clean.endswith(".TW") and clean[:-3].isdigit():
        clean = clean[:-3]
    if clean.startswith("TWSE:") and clean[5:].isdigit():
        clean = clean[5:]
    if clean.startswith("TPEX:") and clean[5:].isdigit():
        clean = clean[5:]
    if clean.startswith("TW") and clean[2:].isdigit():
        clean = clean[2:]
    if not clean.isdigit() or len(clean) != 4:
        _raise_no_market_data(symbol, clean, "only 4-digit Taiwan stock symbols are supported by local provider")
    return f"TW{clean}"


def _resolve_price_file(symbol: str) -> Path:
    tw_symbol = _tw_symbol_id(symbol)
    for directory in DEFAULT_PRICE_DIRS:
        candidate = directory / f"{tw_symbol}.csv"
        if candidate.exists():
            return candidate
    searched = ", ".join(str(path.relative_to(ROOT)) for path in DEFAULT_PRICE_DIRS)
    _raise_no_market_data(symbol, tw_symbol, f"local normalized CSV not found in: {searched}")
    raise AssertionError("unreachable")


def _import_scrapling_fetcher():
    try:
        from scrapling.fetchers import Fetcher  # type: ignore  # noqa: WPS433

        return Fetcher
    except ImportError:
        local_checkout = Path.home() / "Scrapling"
        if local_checkout.exists() and str(local_checkout) not in sys.path:
            sys.path.insert(0, str(local_checkout))
        from scrapling.fetchers import Fetcher  # type: ignore  # noqa: WPS433

        return Fetcher


def _yahoo_ticker(symbol: str) -> str:
    return _tw_symbol_id(symbol)[2:] + ".TW"


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _scrapling_yahoo_chart_ohlcv(symbol: str, start_date: str | None, end_date: str) -> pd.DataFrame:
    end = pd.to_datetime(end_date)
    start = pd.to_datetime(start_date) if start_date else end - pd.DateOffset(years=5)
    period1 = int(start.normalize().tz_localize("UTC").timestamp())
    period2 = int((end.normalize() + pd.Timedelta(days=1)).tz_localize("UTC").timestamp())
    ticker = _yahoo_ticker(symbol)
    params = {
        "period1": period1,
        "period2": period2,
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "true",
    }
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?{urlencode(params)}"
    SCRAPLING_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = SCRAPLING_CACHE_DIR / f"{_tw_symbol_id(symbol)}_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.json"

    if cache_file.exists():
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
    else:
        Fetcher = _import_scrapling_fetcher()
        try:
            page = Fetcher.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 QuantDinger/TradingAgents-Scrapling-Yahoo"},
                timeout=20,
                retries=1,
                impersonate="chrome",
            )
        except Exception as exc:  # noqa: BLE001
            _raise_no_market_data(symbol, _tw_symbol_id(symbol), f"Yahoo chart Scrapling request failed: {exc}")
        status_code = int(getattr(page, "status", 0) or getattr(page, "status_code", 0) or 0)
        if status_code and status_code != 200:
            _raise_no_market_data(symbol, _tw_symbol_id(symbol), f"Yahoo chart Scrapling HTTP {status_code}")
        try:
            payload = page.json()
        except Exception as exc:  # noqa: BLE001
            _raise_no_market_data(symbol, _tw_symbol_id(symbol), f"Yahoo chart Scrapling JSON parse failed: {exc}")
        if not isinstance(payload, dict):
            _raise_no_market_data(symbol, _tw_symbol_id(symbol), "Yahoo chart Scrapling returned non-object JSON")
        cache_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    result = (((payload.get("chart") or {}).get("result") or [None])[0] or {})
    timestamps = result.get("timestamp") or []
    quote = (((result.get("indicators") or {}).get("quote") or [None])[0] or {})
    adjclose = (((result.get("indicators") or {}).get("adjclose") or [None])[0] or {}).get("adjclose") or []
    if not timestamps:
        error = ((payload.get("chart") or {}).get("error") or {}).get("description")
        _raise_no_market_data(symbol, _tw_symbol_id(symbol), f"Yahoo chart Scrapling returned no rows: {error or 'unknown'}")

    rows = []
    for index, ts in enumerate(timestamps):
        row = {
            "Date": pd.to_datetime(int(ts), unit="s", utc=True).tz_convert(None).strftime("%Y-%m-%d"),
            "Open": (quote.get("open") or [None] * len(timestamps))[index],
            "High": (quote.get("high") or [None] * len(timestamps))[index],
            "Low": (quote.get("low") or [None] * len(timestamps))[index],
            "Close": (quote.get("close") or [None] * len(timestamps))[index],
            "Adj Close": adjclose[index] if index < len(adjclose) else None,
            "Volume": (quote.get("volume") or [None] * len(timestamps))[index],
        }
        rows.append(row)
    df = pd.DataFrame(rows)
    for column in ["Open", "High", "Low", "Close", "Adj Close", "Volume"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df["Adj Close"] = df["Adj Close"].fillna(df["Close"])
    df["Volume"] = df["Volume"].fillna(0)
    if df.empty:
        _raise_no_market_data(symbol, _tw_symbol_id(symbol), "Yahoo chart Scrapling rows had no usable OHLC data")
    df.attrs["source"] = f"Yahoo chart via Scrapling runtime cache: {_display_path(cache_file)}"
    return df[["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]].reset_index(drop=True)


def _local_ohlcv(
    symbol: str,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    max_stale_days: int = 10,
) -> pd.DataFrame:
    price_file = _resolve_price_file(symbol)
    source = pd.read_csv(price_file)
    if source.empty:
        _raise_no_market_data(symbol, _tw_symbol_id(symbol), f"empty local CSV: {price_file}")

    rename = {
        "date": "Date",
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
        "adj_close": "Adj Close",
        "adjclose": "Adj Close",
    }
    source = source.rename(columns={key: value for key, value in rename.items() if key in source.columns})
    required = ["Date", "Open", "High", "Low", "Close", "Volume"]
    missing = [column for column in required if column not in source.columns]
    if missing:
        _raise_no_market_data(symbol, _tw_symbol_id(symbol), f"missing required columns {missing} in {price_file}")

    df = source[required + (["Adj Close"] if "Adj Close" in source.columns else [])].copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    for column in ["Open", "High", "Low", "Close", "Volume"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df["Volume"] = df["Volume"].fillna(0)
    if "Adj Close" not in df.columns:
        df["Adj Close"] = df["Close"]
    else:
        df["Adj Close"] = pd.to_numeric(df["Adj Close"], errors="coerce").fillna(df["Close"])
    df = df.sort_values("Date")

    if start_date:
        df = df[df["Date"] >= pd.to_datetime(start_date)]
    fallback_reason = ""
    if end_date:
        cutoff = pd.to_datetime(end_date)
        df = df[df["Date"] <= cutoff]
        if not df.empty:
            latest = df["Date"].max().normalize()
            stale_days = (cutoff.normalize() - latest).days
            if stale_days > max_stale_days:
                fallback_reason = f"latest local row is {latest.date()}, {stale_days} days before requested {cutoff.date()}"

    if df.empty:
        fallback_reason = f"no local rows in requested range {start_date} to {end_date}"
    if fallback_reason and end_date:
        df = _scrapling_yahoo_chart_ohlcv(symbol, start_date, end_date)
    elif fallback_reason:
        _raise_no_market_data(symbol, _tw_symbol_id(symbol), fallback_reason)

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    result = df[["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]].reset_index(drop=True)
    result.attrs["source"] = df.attrs.get("source") or "QuantDinger local Yahoo/Scrapling normalized artifact"
    return result


def load_local_ohlcv(symbol: str, curr_date: str) -> pd.DataFrame:
    """TradingAgents stockstats-compatible OHLCV loader backed by local artifacts."""
    df = _local_ohlcv(symbol, end_date=curr_date)
    return df[["Date", "Open", "High", "Low", "Close", "Volume"]].copy()


def get_stock_data(symbol: str, start_date: str, end_date: str) -> str:
    """Return Yahoo-style CSV text from local Yahoo/Scrapling normalized data."""
    datetime.strptime(start_date, "%Y-%m-%d")
    datetime.strptime(end_date, "%Y-%m-%d")
    df = _local_ohlcv(symbol, start_date=start_date, end_date=end_date)
    rounded = df.copy()
    for column in ["Open", "High", "Low", "Close", "Adj Close"]:
        rounded[column] = rounded[column].round(2)

    label = _tw_symbol_id(symbol)
    header = f"# Stock data for {label} (from {symbol}) from {start_date} to {end_date}\n"
    header += f"# Total records: {len(rounded)}\n"
    header += f"# Data source: {rounded.attrs.get('source') or 'QuantDinger local Yahoo/Scrapling normalized artifact'}\n"
    header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    return header + rounded.to_csv(index=False)


def _indicator_frame(symbol: str, curr_date: str) -> pd.DataFrame:
    from stockstats import wrap

    df = load_local_ohlcv(symbol, curr_date)
    wrapped = wrap(df.copy())
    wrapped["Date"] = pd.to_datetime(wrapped["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    return wrapped


def get_indicators(symbol: str, indicator: str, curr_date: str, look_back_days: int) -> str:
    """Return TradingAgents-compatible indicator text from local OHLCV."""
    if indicator not in INDICATOR_DESCRIPTIONS:
        raise ValueError(f"Indicator {indicator} is not supported. Choose from: {list(INDICATOR_DESCRIPTIONS)}")
    end = pd.to_datetime(curr_date)
    start = end - pd.Timedelta(days=int(look_back_days))
    frame = _indicator_frame(symbol, curr_date)
    frame[indicator]  # trigger stockstats calculation
    values = {
        row["Date"]: row[indicator]
        for _, row in frame[["Date", indicator]].dropna(subset=["Date"]).iterrows()
    }

    lines = []
    current = end
    while current >= start:
        date_str = current.strftime("%Y-%m-%d")
        value = values.get(date_str, "N/A: Not a trading day (weekend or holiday)")
        if pd.isna(value):
            value = "N/A"
        lines.append(f"{date_str}: {value}")
        current -= pd.Timedelta(days=1)

    return (
        f"## {indicator} values from {start.strftime('%Y-%m-%d')} to {curr_date}:\n\n"
        + "\n".join(lines)
        + "\n\n"
        + INDICATOR_DESCRIPTIONS[indicator]
    )


def get_verified_market_snapshot(symbol: str, curr_date: str, look_back_days: int = 30) -> str:
    """Safe snapshot tool for TradingAgents market analyst."""
    try:
        from tradingagents.dataflows.market_data_validator import build_verified_market_snapshot  # type: ignore

        return build_verified_market_snapshot(symbol, curr_date, look_back_days)
    except Exception as exc:  # noqa: BLE001
        return (
            f"NO_DATA_AVAILABLE: verified market snapshot unavailable for {symbol} "
            f"on {curr_date} from QuantDinger local/Scrapling provider ({exc}). "
            "Do not estimate or fabricate OHLCV, indicator values, support/resistance, "
            "or exact percentage moves."
        )


def get_news(symbol: str, start_date: str, end_date: str) -> str:
    """Return approved local source packets or fail closed."""
    datetime.strptime(start_date, "%Y-%m-%d")
    datetime.strptime(end_date, "%Y-%m-%d")
    packets = _load_source_packets(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        source_types=NEWS_SOURCE_TYPES,
    )
    if packets:
        return _render_source_packets(
            symbol=symbol,
            heading=f"Approved company/exchange/news source packets from {start_date} to {end_date}",
            packets=packets,
        )
    return _fail_closed_source_message(
        source_kind="company/exchange news",
        requested=_tw_symbol_id(symbol),
        date_context=f"{start_date} to {end_date}",
    )


def get_global_news(curr_date: str, look_back_days: int | None = None, limit: int | None = None) -> str:
    """Fail-closed macro/global news hook for readonly TradingAgents runs."""
    datetime.strptime(curr_date, "%Y-%m-%d")
    return _fail_closed_source_message(
        source_kind="global or macro news",
        requested=f"curr_date={curr_date}, look_back_days={look_back_days}, limit={limit}",
    )


def get_insider_transactions(symbol: str) -> str:
    """Fail-closed insider-transaction hook; Taiwan local source is not approved."""
    return _fail_closed_source_message(
        source_kind="insider transaction",
        requested=_tw_symbol_id(symbol),
    )


def get_macro_indicators(indicator: str, curr_date: str, look_back_days: int | None = None) -> str:
    """Fail-closed macro hook; avoids unapproved FRED dependency in readonly runs."""
    datetime.strptime(curr_date, "%Y-%m-%d")
    return _fail_closed_source_message(
        source_kind="macro indicator",
        requested=str(indicator or "unknown"),
        date_context=f"curr_date={curr_date}, look_back_days={look_back_days}",
    )


def get_prediction_markets(topic: str, limit: int | None = None) -> str:
    """Fail-closed prediction-market hook; avoids unapproved live Polymarket calls."""
    return _fail_closed_source_message(
        source_kind="prediction market",
        requested=f"topic={topic}, limit={limit}",
    )


def get_fundamentals(symbol: str, curr_date: str | None = None) -> str:
    """Return approved local fundamental packets or fail closed."""
    if curr_date:
        datetime.strptime(curr_date, "%Y-%m-%d")
    packets = _load_source_packets(
        symbol=symbol,
        start_date=None,
        end_date=curr_date,
        source_types=FUNDAMENTAL_SOURCE_TYPES,
    )
    if packets:
        return _render_source_packets(
            symbol=symbol,
            heading="Approved fundamental source packets",
            packets=packets,
        )
    return _fail_closed_source_message(
        source_kind="fundamental filing",
        requested=_tw_symbol_id(symbol),
        date_context=curr_date,
    )


def get_balance_sheet(symbol: str, freq: str = "quarterly", curr_date: str | None = None) -> str:
    """Fail-closed balance sheet hook until a PIT Taiwan filing source is approved."""
    if curr_date:
        datetime.strptime(curr_date, "%Y-%m-%d")
    return _fail_closed_source_message(
        source_kind="balance sheet",
        requested=f"{_tw_symbol_id(symbol)}, freq={freq}",
        date_context=curr_date,
    )


def get_cashflow(symbol: str, freq: str = "quarterly", curr_date: str | None = None) -> str:
    """Fail-closed cashflow hook until a PIT Taiwan filing source is approved."""
    if curr_date:
        datetime.strptime(curr_date, "%Y-%m-%d")
    return _fail_closed_source_message(
        source_kind="cashflow statement",
        requested=f"{_tw_symbol_id(symbol)}, freq={freq}",
        date_context=curr_date,
    )


def get_income_statement(symbol: str, freq: str = "quarterly", curr_date: str | None = None) -> str:
    """Fail-closed income statement hook until a PIT Taiwan filing source is approved."""
    if curr_date:
        datetime.strptime(curr_date, "%Y-%m-%d")
    return _fail_closed_source_message(
        source_kind="income statement",
        requested=f"{_tw_symbol_id(symbol)}, freq={freq}",
        date_context=curr_date,
    )


def resolve_local_instrument_identity(ticker: str) -> dict[str, str]:
    tw_symbol = _tw_symbol_id(ticker)
    identity = {
        "company_name": tw_symbol,
        "exchange": "TWSE/TPEX local normalized universe",
        "quote_type": "EQUITY",
    }
    identity.update(LOCAL_INSTRUMENT_IDENTITIES.get(tw_symbol, {}))
    return identity


def _local_fetch_returns(self: Any, ticker: str, trade_date: str, holding_days: int = 5, benchmark: str = "SPY"):
    try:
        df = _local_ohlcv(
            ticker,
            start_date=trade_date,
            end_date=(pd.to_datetime(trade_date) + pd.Timedelta(days=holding_days + 10)).strftime("%Y-%m-%d"),
            max_stale_days=holding_days + 10,
        )
        if len(df) < 2:
            return None, None, None
        actual_days = min(int(holding_days), len(df) - 1)
        raw = float((df["Close"].iloc[actual_days] - df["Close"].iloc[0]) / df["Close"].iloc[0])

        bench_df = _local_ohlcv(
            benchmark,
            start_date=trade_date,
            end_date=(pd.to_datetime(trade_date) + pd.Timedelta(days=actual_days + 10)).strftime("%Y-%m-%d"),
            max_stale_days=actual_days + 10,
        )
        if len(bench_df) <= actual_days:
            return None, None, None
        bench_ret = float((bench_df["Close"].iloc[actual_days] - bench_df["Close"].iloc[0]) / bench_df["Close"].iloc[0])
        return raw, raw - bench_ret, actual_days
    except Exception:
        return None, None, None


def install_tradingagents_local_data_provider() -> dict[str, Any]:
    """Install local market-data hooks into vendored TradingAgents at runtime."""
    import tradingagents.dataflows.interface as interface  # type: ignore
    import tradingagents.dataflows.market_data_validator as market_data_validator  # type: ignore
    import tradingagents.dataflows.stockstats_utils as stockstats_utils  # type: ignore

    interface.VENDOR_METHODS.setdefault("get_stock_data", {})[VENDOR_NAME] = get_stock_data
    interface.VENDOR_METHODS.setdefault("get_indicators", {})[VENDOR_NAME] = get_indicators
    interface.VENDOR_METHODS.setdefault("get_news", {})[VENDOR_NAME] = get_news
    interface.VENDOR_METHODS.setdefault("get_global_news", {})[VENDOR_NAME] = get_global_news
    interface.VENDOR_METHODS.setdefault("get_insider_transactions", {})[VENDOR_NAME] = get_insider_transactions
    interface.VENDOR_METHODS.setdefault("get_macro_indicators", {})[VENDOR_NAME] = get_macro_indicators
    interface.VENDOR_METHODS.setdefault("get_prediction_markets", {})[VENDOR_NAME] = get_prediction_markets
    interface.VENDOR_METHODS.setdefault("get_fundamentals", {})[VENDOR_NAME] = get_fundamentals
    interface.VENDOR_METHODS.setdefault("get_balance_sheet", {})[VENDOR_NAME] = get_balance_sheet
    interface.VENDOR_METHODS.setdefault("get_cashflow", {})[VENDOR_NAME] = get_cashflow
    interface.VENDOR_METHODS.setdefault("get_income_statement", {})[VENDOR_NAME] = get_income_statement
    stockstats_utils.load_ohlcv = load_local_ohlcv
    market_data_validator.load_ohlcv = load_local_ohlcv

    try:
        import tradingagents.agents.utils.agent_utils as agent_utils  # type: ignore

        agent_utils.resolve_instrument_identity = resolve_local_instrument_identity
        agent_utils.get_verified_market_snapshot = get_verified_market_snapshot
    except Exception:
        pass
    try:
        import tradingagents.agents.utils.market_data_validation_tools as validation_tools  # type: ignore

        validation_tools.get_verified_market_snapshot = get_verified_market_snapshot
    except Exception:
        pass
    try:
        import tradingagents.graph.trading_graph as trading_graph  # type: ignore

        trading_graph.resolve_instrument_identity = resolve_local_instrument_identity
        trading_graph.get_verified_market_snapshot = get_verified_market_snapshot
        trading_graph.TradingAgentsGraph._fetch_returns = _local_fetch_returns
    except Exception:
        pass

    return {
        "vendor": VENDOR_NAME,
        "stock_data": interface.VENDOR_METHODS["get_stock_data"].get(VENDOR_NAME) is get_stock_data,
        "indicators": interface.VENDOR_METHODS["get_indicators"].get(VENDOR_NAME) is get_indicators,
        "news": interface.VENDOR_METHODS["get_news"].get(VENDOR_NAME) is get_news,
        "global_news": interface.VENDOR_METHODS["get_global_news"].get(VENDOR_NAME) is get_global_news,
        "macro_indicators": interface.VENDOR_METHODS["get_macro_indicators"].get(VENDOR_NAME) is get_macro_indicators,
        "prediction_markets": interface.VENDOR_METHODS["get_prediction_markets"].get(VENDOR_NAME) is get_prediction_markets,
        "fundamentals": interface.VENDOR_METHODS["get_fundamentals"].get(VENDOR_NAME) is get_fundamentals,
        "local_price_dirs": [str(path.relative_to(ROOT)) for path in DEFAULT_PRICE_DIRS],
    }
