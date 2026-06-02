# Built-in TWStock read-only backtest templates.
#
# These templates produce IndicatorStrategy code only. They are used for
# historical simulation and never create broker orders or runtime actions.
from __future__ import annotations

from typing import Any, Dict, List


_BUILTIN_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "ma_cross_builtin": {
        "id": "ma_cross_builtin",
        "name": "MA Cross",
        "description": "Long-only moving-average crossover research template for TWStock daily bars.",
        "defaultConfig": {"fastWindow": 5, "slowWindow": 20},
    },
    "rsi_builtin": {
        "id": "rsi_builtin",
        "name": "RSI Reversal",
        "description": "Long-only RSI oversold rebound research template for TWStock daily bars.",
        "defaultConfig": {"period": 14, "oversold": 30, "overbought": 70},
    },
    "macd_builtin": {
        "id": "macd_builtin",
        "name": "MACD Cross",
        "description": "Long-only MACD golden/death cross research template for TWStock daily bars.",
        "defaultConfig": {"fast": 12, "slow": 26, "signal": 9},
    },
    "bollinger_builtin": {
        "id": "bollinger_builtin",
        "name": "Bollinger Mean Reversion",
        "description": "Long-only Bollinger lower-band rebound research template for TWStock daily bars.",
        "defaultConfig": {"period": 20, "stdDev": 2.0},
    },
}

_ALIASES = {
    "ma_cross": "ma_cross_builtin",
    "ma_crossover": "ma_cross_builtin",
    "ma": "ma_cross_builtin",
    "rsi": "rsi_builtin",
    "macd": "macd_builtin",
    "bollinger": "bollinger_builtin",
    "boll": "bollinger_builtin",
}


def _as_int(config: Dict[str, Any], key: str, default: int, *, min_value: int = 1) -> int:
    try:
        value = int(config.get(key, default))
    except Exception:
        value = default
    return max(min_value, value)


def _as_float(config: Dict[str, Any], key: str, default: float, *, min_value: float = 0.0) -> float:
    try:
        value = float(config.get(key, default))
    except Exception:
        value = default
    return max(min_value, value)


def normalize_strategy_id(strategy_id: Any) -> str:
    raw = str(strategy_id or "").strip()
    return _ALIASES.get(raw.lower(), raw)


def list_tw_stock_backtest_templates() -> List[Dict[str, Any]]:
    return [dict(item) for item in _BUILTIN_TEMPLATES.values()]


def build_tw_stock_builtin_indicator_code(strategy_id: Any, strategy_config: Dict[str, Any] | None = None) -> str:
    """Return safe IndicatorStrategy code for a supported TWStock template."""
    sid = normalize_strategy_id(strategy_id)
    if sid not in _BUILTIN_TEMPLATES:
        allowed = ", ".join(sorted(_BUILTIN_TEMPLATES))
        raise ValueError(f"Unsupported TWStock built-in strategyId: {strategy_id}. Supported: {allowed}")

    root_config = strategy_config or {}
    template_config = root_config.get("template") if isinstance(root_config.get("template"), dict) else {}
    config = {**(_BUILTIN_TEMPLATES[sid].get("defaultConfig") or {}), **template_config}

    if sid == "ma_cross_builtin":
        fast = _as_int(config, "fastWindow", 5, min_value=1)
        slow = _as_int(config, "slowWindow", 20, min_value=2)
        if fast >= slow:
            raise ValueError("ma_cross_builtin requires fastWindow < slowWindow")
        return f'''
my_indicator_name = "TWStock MA Cross Built-in"
my_indicator_description = "Read-only TWStock daily MA crossover historical simulation."
# @strategy entryPct 1
# @strategy tradeDirection long

df = df.copy()
fast = SMA(close, {fast})
slow = SMA(close, {slow})
buy_raw = CROSSOVER(fast, slow)
sell_raw = CROSSUNDER(fast, slow)
df['buy'] = buy_raw.fillna(False).astype(bool)
df['sell'] = sell_raw.fillna(False).astype(bool)
output = {{
    'name': my_indicator_name,
    'plots': [
        {{'name': 'MA{fast}', 'data': fast.fillna(0).tolist(), 'overlay': True}},
        {{'name': 'MA{slow}', 'data': slow.fillna(0).tolist(), 'overlay': True}},
    ],
    'signals': []
}}
'''.strip()

    if sid == "rsi_builtin":
        period = _as_int(config, "period", 14, min_value=2)
        oversold = _as_float(config, "oversold", 30.0, min_value=1.0)
        overbought = _as_float(config, "overbought", 70.0, min_value=1.0)
        if oversold >= overbought:
            raise ValueError("rsi_builtin requires oversold < overbought")
        return f'''
my_indicator_name = "TWStock RSI Built-in"
my_indicator_description = "Read-only TWStock daily RSI reversal historical simulation."
# @strategy entryPct 1
# @strategy tradeDirection long

df = df.copy()
rsi = RSI(close, {period})
buy_raw = (rsi > {oversold}) & (rsi.shift(1) <= {oversold})
sell_raw = (rsi >= {overbought}) & (rsi.shift(1) < {overbought})
df['buy'] = buy_raw.fillna(False).astype(bool)
df['sell'] = sell_raw.fillna(False).astype(bool)
output = {{
    'name': my_indicator_name,
    'plots': [{{'name': 'RSI{period}', 'data': rsi.fillna(50).tolist(), 'overlay': False}}],
    'signals': []
}}
'''.strip()

    if sid == "macd_builtin":
        fast = _as_int(config, "fast", 12, min_value=1)
        slow = _as_int(config, "slow", 26, min_value=2)
        signal = _as_int(config, "signal", 9, min_value=1)
        if fast >= slow:
            raise ValueError("macd_builtin requires fast < slow")
        return f'''
my_indicator_name = "TWStock MACD Built-in"
my_indicator_description = "Read-only TWStock daily MACD cross historical simulation."
# @strategy entryPct 1
# @strategy tradeDirection long

df = df.copy()
macd, macd_signal, macd_hist = MACD(close, {fast}, {slow}, {signal})
buy_raw = CROSSOVER(macd, macd_signal)
sell_raw = CROSSUNDER(macd, macd_signal)
df['buy'] = buy_raw.fillna(False).astype(bool)
df['sell'] = sell_raw.fillna(False).astype(bool)
output = {{
    'name': my_indicator_name,
    'plots': [
        {{'name': 'MACD', 'data': macd.fillna(0).tolist(), 'overlay': False}},
        {{'name': 'Signal', 'data': macd_signal.fillna(0).tolist(), 'overlay': False}},
        {{'name': 'Hist', 'data': macd_hist.fillna(0).tolist(), 'overlay': False}},
    ],
    'signals': []
}}
'''.strip()

    period = _as_int(config, "period", 20, min_value=2)
    std_dev = _as_float(config, "stdDev", 2.0, min_value=0.1)
    return f'''
my_indicator_name = "TWStock Bollinger Built-in"
my_indicator_description = "Read-only TWStock daily Bollinger mean-reversion historical simulation."
# @strategy entryPct 1
# @strategy tradeDirection long

df = df.copy()
upper, middle, lower = BOLL(close, {period}, {std_dev})
buy_raw = (close > lower) & (close.shift(1) <= lower.shift(1))
sell_raw = (close >= middle) & (close.shift(1) < middle.shift(1))
df['buy'] = buy_raw.fillna(False).astype(bool)
df['sell'] = sell_raw.fillna(False).astype(bool)
output = {{
    'name': my_indicator_name,
    'plots': [
        {{'name': 'Upper', 'data': upper.fillna(0).tolist(), 'overlay': True}},
        {{'name': 'Middle', 'data': middle.fillna(0).tolist(), 'overlay': True}},
        {{'name': 'Lower', 'data': lower.fillna(0).tolist(), 'overlay': True}},
    ],
    'signals': []
}}
'''.strip()
