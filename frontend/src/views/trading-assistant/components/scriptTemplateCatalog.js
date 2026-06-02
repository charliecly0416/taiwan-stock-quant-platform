// Script-strategy template catalog.
//
// Templates `trendFollowing`, `martingale`, `grid` and `dca` were intentionally
// removed because the "Trading Bot" page already offers wizard-based versions
// of the same four strategies (see `views/trading-bot/components/botScriptTemplates.js`).
// Maintaining two parallel implementations doubled the bug surface without
// adding user value. Old strategies that were created with
// `trading_config.script_template_key` set to one of those four keys are
// unaffected — they ship their own copy of the generated Python in
// `qd_strategies_trading.strategy_code` and the i18n labels under
// `trading-assistant.template.*` are kept around for display purposes only.
//
// What stays here are the "stateful" templates that genuinely cannot be
// expressed as a single-indicator signal strategy: trailing stops, scale-in
// ladders, take-profit ladders, multi-indicator combos, etc. These are the
// real reason the script-strategy escape hatch exists.
const TEMPLATE_DEFINITIONS = [
  {
    key: 'meanReversion',
    icon: '🔄',
    code: `"""
Mean Reversion Strategy
Bollinger Bands based: buy at lower band, sell at upper band.
"""

def on_init(ctx):
    ctx.period = ctx.param('period', 20)
    ctx.std_mult = ctx.param('std_mult', 2.0)
    ctx.position_pct = ctx.param('position_pct', 0.5)
    ctx.take_profit_pct = ctx.param('take_profit_pct', 0.03)
    ctx.stop_loss_pct = ctx.param('stop_loss_pct', 0.02)

def on_bar(ctx, bar):
    bars = ctx.bars(ctx.period + 5)
    if len(bars) < ctx.period:
        return

    closes = [b['close'] for b in bars[-ctx.period:]]
    mean = sum(closes) / len(closes)
    std = (sum((c - mean) ** 2 for c in closes) / len(closes)) ** 0.5

    upper = mean + ctx.std_mult * std
    lower = mean - ctx.std_mult * std
    price = bar['close']

    if price <= lower and not ctx.position:
        qty = (ctx.equity * ctx.position_pct) / price
        ctx.buy(price, qty)
        ctx.log(f"BUY at {price:.2f} (below lower band {lower:.2f})")

    elif price >= upper and ctx.position and ctx.position['side'] == 'long':
        ctx.close_position()
        ctx.log(f"SELL at {price:.2f} (above upper band {upper:.2f})")

    elif ctx.position and ctx.position['side'] == 'long':
        entry = ctx.position['entry_price']
        pnl_pct = (price - entry) / entry
        if pnl_pct >= ctx.take_profit_pct or pnl_pct <= -ctx.stop_loss_pct:
            ctx.close_position()
            ctx.log(f"Risk exit at {price:.2f}, pnl={pnl_pct:.2%}")
`,
    params: [
      { name: 'period', type: 'integer', default: 20, min: 2, max: 300, step: 1 },
      { name: 'std_mult', type: 'number', default: 2.0, min: 0.5, max: 6, step: 0.1 },
      { name: 'position_pct', type: 'percent', default: 0.5, min: 0.05, max: 1, step: 0.01 },
      { name: 'take_profit_pct', type: 'percent', default: 0.03, min: 0.001, max: 1, step: 0.001 },
      { name: 'stop_loss_pct', type: 'percent', default: 0.02, min: 0.001, max: 1, step: 0.001 }
    ]
  },
  {
    key: 'breakout',
    icon: '⚡',
    code: `"""
Breakout Strategy
Enter when price breaks key resistance/support with volume confirmation.
"""

def on_init(ctx):
    ctx.lookback = ctx.param('lookback', 20)
    ctx.volume_mult = ctx.param('volume_mult', 1.5)
    ctx.position_pct = ctx.param('position_pct', 0.9)
    ctx.stop_pct = ctx.param('stop_pct', 0.02)
    ctx.take_profit_pct = ctx.param('take_profit_pct', 0.05)

def on_bar(ctx, bar):
    bars = ctx.bars(ctx.lookback + 5)
    if len(bars) < ctx.lookback:
        return

    recent = bars[-ctx.lookback:]
    high = max(b['high'] for b in recent[:-1])
    low = min(b['low'] for b in recent[:-1])
    avg_vol = sum(b['volume'] for b in recent[:-1]) / (len(recent) - 1)
    price = bar['close']
    vol = bar['volume']

    if price > high and vol > avg_vol * ctx.volume_mult and not ctx.position:
        qty = (ctx.equity * ctx.position_pct) / price
        ctx.buy(price, qty)
        ctx.log(f"BREAKOUT BUY at {price:.2f} (prev high: {high:.2f})")

    elif price < low and ctx.position and ctx.position['side'] == 'long':
        ctx.close_position()
        ctx.log(f"BREAK DOWN, close at {price:.2f}")

    if ctx.position and ctx.position['side'] == 'long':
        entry = ctx.position['entry_price']
        pnl_pct = (price - entry) / entry
        if pnl_pct <= -ctx.stop_pct:
            ctx.close_position()
            ctx.log(f"STOP LOSS at {price:.2f}")
        elif pnl_pct >= ctx.take_profit_pct:
            ctx.close_position()
            ctx.log(f"TAKE PROFIT at {price:.2f}")
`,
    params: [
      { name: 'lookback', type: 'integer', default: 20, min: 2, max: 300, step: 1 },
      { name: 'volume_mult', type: 'number', default: 1.5, min: 0.5, max: 10, step: 0.1 },
      { name: 'position_pct', type: 'percent', default: 0.9, min: 0.05, max: 1, step: 0.01 },
      { name: 'stop_pct', type: 'percent', default: 0.02, min: 0.001, max: 1, step: 0.001 },
      { name: 'take_profit_pct', type: 'percent', default: 0.05, min: 0.001, max: 1, step: 0.001 }
    ]
  },
  {
    key: 'rsiMeanReversion',
    icon: '📉',
    code: `"""
RSI mean reversion (long-focused)
Buys when RSI is oversold; exits long when RSI is overbought.
"""

def on_init(ctx):
    ctx.rsi_period = ctx.param('rsi_period', 14)
    ctx.oversold = ctx.param('oversold', 30)
    ctx.overbought = ctx.param('overbought', 70)
    ctx.position_pct = ctx.param('position_pct', 0.5)

def _rsi_simple(closes, period):
    n = len(closes)
    if n < period + 1:
        return None
    gains = 0.0
    losses = 0.0
    for i in range(n - period, n):
        diff = closes[i] - closes[i - 1]
        if diff > 0:
            gains += diff
        else:
            losses -= diff
    if losses == 0:
        return 100.0 if gains > 0 else 50.0
    rs = gains / losses
    return 100.0 - (100.0 / (1.0 + rs))

def on_bar(ctx, bar):
    need = ctx.rsi_period + 3
    bars = ctx.bars(need)
    if len(bars) < need:
        return
    closes = [b['close'] for b in bars]
    r = _rsi_simple(closes, ctx.rsi_period)
    if r is None:
        return
    price = bar['close']
    if r <= ctx.oversold and not ctx.position:
        qty = (ctx.equity * ctx.position_pct) / price
        ctx.buy(price, qty)
        ctx.log(f"RSI BUY r={r:.1f} at {price:.2f}")
    elif r >= ctx.overbought and ctx.position and ctx.position['side'] == 'long':
        ctx.close_position()
        ctx.log(f"RSI SELL r={r:.1f} at {price:.2f}")
`,
    params: [
      { name: 'rsi_period', type: 'integer', default: 14, min: 2, max: 100, step: 1 },
      { name: 'oversold', type: 'number', default: 30, min: 1, max: 50, step: 1 },
      { name: 'overbought', type: 'number', default: 70, min: 50, max: 99, step: 1 },
      { name: 'position_pct', type: 'percent', default: 0.5, min: 0.05, max: 1, step: 0.01 }
    ]
  },
  {
    key: 'macdCross',
    icon: '📊',
    code: `"""
MACD histogram crossover
Enters long when MACD histogram crosses above zero; exits when it crosses below.
"""

def on_init(ctx):
    ctx.macd_fast = ctx.param('macd_fast', 12)
    ctx.macd_slow = ctx.param('macd_slow', 26)
    ctx.macd_signal = ctx.param('macd_signal', 9)
    ctx.position_pct = ctx.param('position_pct', 0.6)

def _ema_series(vals, period):
    k = 2.0 / (period + 1)
    out = []
    e = float(vals[0])
    out.append(e)
    for v in vals[1:]:
        v = float(v)
        e = v * k + e * (1 - k)
        out.append(e)
    return out

def _macd_hist_last_two(closes, fast, slow, sig):
    n = len(closes)
    if n < slow + sig + 2:
        return None, None
    ef = _ema_series(closes, fast)
    es = _ema_series(closes, slow)
    macd = [ef[i] - es[i] for i in range(n)]
    sg = _ema_series(macd, sig)
    hist = [macd[i] - sg[i] for i in range(n)]
    return hist[-2], hist[-1]

def on_bar(ctx, bar):
    need = ctx.macd_slow + ctx.macd_signal + 30
    bars = ctx.bars(need)
    if len(bars) < need:
        return
    closes = [b['close'] for b in bars]
    h0, h1 = _macd_hist_last_two(closes, ctx.macd_fast, ctx.macd_slow, ctx.macd_signal)
    if h0 is None:
        return
    price = bar['close']
    if h0 <= 0 and h1 > 0 and not ctx.position:
        qty = (ctx.equity * ctx.position_pct) / price
        ctx.buy(price, qty)
        ctx.log(f"MACD cross up at {price:.2f}")
    elif h0 >= 0 and h1 < 0 and ctx.position and ctx.position['side'] == 'long':
        ctx.close_position()
        ctx.log(f"MACD cross down at {price:.2f}")
`,
    params: [
      { name: 'macd_fast', type: 'integer', default: 12, min: 2, max: 50, step: 1 },
      { name: 'macd_slow', type: 'integer', default: 26, min: 5, max: 120, step: 1 },
      { name: 'macd_signal', type: 'integer', default: 9, min: 2, max: 50, step: 1 },
      { name: 'position_pct', type: 'percent', default: 0.6, min: 0.05, max: 1, step: 0.01 }
    ]
  },
  {
    key: 'trailingStop',
    icon: '🪤',
    code: `"""
Trailing Stop Strategy
Enter on EMA crossover, manage exits with a hard stop and a trailing stop
that arms only after a minimum profit threshold is reached.
"""

def on_init(ctx):
    ctx.fast_period = ctx.param('fast_period', 10)
    ctx.slow_period = ctx.param('slow_period', 30)
    ctx.position_pct = ctx.param('position_pct', 0.8)
    ctx.hard_stop_pct = ctx.param('hard_stop_pct', 0.025)
    ctx.trailing_stop_pct = ctx.param('trailing_stop_pct', 0.015)
    ctx.trailing_arm_pct = ctx.param('trailing_arm_pct', 0.02)
    ctx.peak_price = 0.0
    ctx.trailing_armed = False

def _ema(values, period):
    k = 2.0 / (period + 1)
    e = float(values[0])
    for v in values[1:]:
        e = float(v) * k + e * (1 - k)
    return e

def on_bar(ctx, bar):
    bars = ctx.bars(ctx.slow_period + 5)
    if len(bars) < ctx.slow_period:
        return
    closes = [b['close'] for b in bars]
    fast = _ema(closes, ctx.fast_period)
    slow = _ema(closes, ctx.slow_period)
    price = bar['close']

    if not ctx.position and fast > slow:
        qty = (ctx.equity * ctx.position_pct) / price
        ctx.buy(price, qty)
        ctx.peak_price = price
        ctx.trailing_armed = False
        ctx.log(f"BUY at {price:.2f}")
        return

    if ctx.position and ctx.position['side'] == 'long':
        entry = ctx.position['entry_price']
        ctx.peak_price = max(ctx.peak_price, price)
        pnl_pct = (price - entry) / entry

        if pnl_pct <= -ctx.hard_stop_pct:
            ctx.close_position()
            ctx.log(f"HARD STOP at {price:.2f} ({pnl_pct*100:.2f}%)")
            return

        if not ctx.trailing_armed and pnl_pct >= ctx.trailing_arm_pct:
            ctx.trailing_armed = True
            ctx.log(f"Trailing armed at {price:.2f}")

        if ctx.trailing_armed:
            trail_stop = ctx.peak_price * (1 - ctx.trailing_stop_pct)
            if price <= trail_stop:
                ctx.close_position()
                ctx.log(f"TRAILING STOP at {price:.2f} (peak {ctx.peak_price:.2f})")
`,
    params: [
      { name: 'fast_period', type: 'integer', default: 10, min: 2, max: 120, step: 1 },
      { name: 'slow_period', type: 'integer', default: 30, min: 5, max: 240, step: 1 },
      { name: 'position_pct', type: 'percent', default: 0.8, min: 0.05, max: 1, step: 0.01 },
      { name: 'hard_stop_pct', type: 'percent', default: 0.025, min: 0.001, max: 0.5, step: 0.001 },
      { name: 'trailing_stop_pct', type: 'percent', default: 0.015, min: 0.001, max: 0.5, step: 0.001 },
      { name: 'trailing_arm_pct', type: 'percent', default: 0.02, min: 0.001, max: 0.5, step: 0.001 }
    ]
  },
  {
    key: 'scaleInOnDip',
    icon: '🪜',
    code: `"""
Scale-in on dip Strategy
Build a position in tranches as price keeps falling below the entry,
then exit with a take-profit measured against the average cost.
"""

def on_init(ctx):
    ctx.entry_pct = ctx.param('entry_pct', 0.25)
    ctx.dip_step_pct = ctx.param('dip_step_pct', 0.02)
    ctx.max_layers = ctx.param('max_layers', 4)
    ctx.take_profit_pct = ctx.param('take_profit_pct', 0.04)
    ctx.hard_stop_pct = ctx.param('hard_stop_pct', 0.10)
    ctx.entry_anchor = 0.0
    ctx.layers = 0
    ctx.avg_cost = 0.0

def _trigger_open(ctx, bar):
    bars = ctx.bars(20)
    if len(bars) < 5:
        return False
    return bar['close'] < bars[-2]['close']

def on_bar(ctx, bar):
    price = bar['close']

    if not ctx.position:
        if _trigger_open(ctx, bar):
            qty = (ctx.equity * ctx.entry_pct) / price
            ctx.buy(price, qty)
            ctx.entry_anchor = price
            ctx.layers = 1
            ctx.avg_cost = price
            ctx.log(f"OPEN layer 1 at {price:.2f}")
        return

    if ctx.position['side'] != 'long':
        return

    entry = ctx.position['entry_price']
    pnl_pct = (price - entry) / entry

    if pnl_pct <= -ctx.hard_stop_pct:
        ctx.close_position()
        ctx.layers = 0
        ctx.log(f"HARD STOP at {price:.2f}")
        return

    next_trigger = ctx.entry_anchor * (1 - ctx.dip_step_pct * ctx.layers)
    if ctx.layers < ctx.max_layers and price <= next_trigger:
        qty = (ctx.equity * ctx.entry_pct) / price
        ctx.buy(price, qty)
        ctx.layers += 1
        ctx.avg_cost = (ctx.avg_cost * (ctx.layers - 1) + price) / ctx.layers
        ctx.log(f"SCALE IN layer {ctx.layers} at {price:.2f}, avg {ctx.avg_cost:.2f}")
        return

    if ctx.avg_cost > 0 and price >= ctx.avg_cost * (1 + ctx.take_profit_pct):
        ctx.close_position()
        ctx.log(f"TAKE PROFIT at {price:.2f} (avg {ctx.avg_cost:.2f})")
        ctx.layers = 0
`,
    params: [
      { name: 'entry_pct', type: 'percent', default: 0.25, min: 0.01, max: 1, step: 0.01 },
      { name: 'dip_step_pct', type: 'percent', default: 0.02, min: 0.001, max: 0.5, step: 0.001 },
      { name: 'max_layers', type: 'integer', default: 4, min: 1, max: 10, step: 1 },
      { name: 'take_profit_pct', type: 'percent', default: 0.04, min: 0.001, max: 1, step: 0.001 },
      { name: 'hard_stop_pct', type: 'percent', default: 0.10, min: 0.005, max: 0.9, step: 0.005 }
    ]
  },
  {
    key: 'takeProfitLadder',
    icon: '🎯',
    code: `"""
Take-Profit Ladder Strategy
Enter on EMA crossover, then partially close the position at three
ascending take-profit levels. A hard stop protects the runner.
"""

def on_init(ctx):
    ctx.fast_period = ctx.param('fast_period', 10)
    ctx.slow_period = ctx.param('slow_period', 30)
    ctx.position_pct = ctx.param('position_pct', 0.9)
    ctx.tp1_pct = ctx.param('tp1_pct', 0.02)
    ctx.tp2_pct = ctx.param('tp2_pct', 0.05)
    ctx.tp3_pct = ctx.param('tp3_pct', 0.10)
    ctx.tp1_close = ctx.param('tp1_close', 0.4)
    ctx.tp2_close = ctx.param('tp2_close', 0.4)
    ctx.hard_stop_pct = ctx.param('hard_stop_pct', 0.03)
    ctx.tp_hits = 0
    ctx.original_qty = 0.0

def _ema(values, period):
    k = 2.0 / (period + 1)
    e = float(values[0])
    for v in values[1:]:
        e = float(v) * k + e * (1 - k)
    return e

def on_bar(ctx, bar):
    bars = ctx.bars(ctx.slow_period + 5)
    if len(bars) < ctx.slow_period:
        return
    closes = [b['close'] for b in bars]
    fast = _ema(closes, ctx.fast_period)
    slow = _ema(closes, ctx.slow_period)
    price = bar['close']

    if not ctx.position and fast > slow:
        qty = (ctx.equity * ctx.position_pct) / price
        ctx.buy(price, qty)
        ctx.original_qty = qty
        ctx.tp_hits = 0
        ctx.log(f"BUY at {price:.2f}, qty {qty:.4f}")
        return

    if not (ctx.position and ctx.position['side'] == 'long'):
        return

    entry = ctx.position['entry_price']
    pnl_pct = (price - entry) / entry

    if pnl_pct <= -ctx.hard_stop_pct:
        ctx.close_position()
        ctx.tp_hits = 0
        ctx.log(f"HARD STOP at {price:.2f}")
        return

    if ctx.tp_hits == 0 and pnl_pct >= ctx.tp1_pct:
        sell_qty = ctx.original_qty * ctx.tp1_close
        ctx.sell(price, sell_qty)
        ctx.tp_hits = 1
        ctx.log(f"TP1 at {price:.2f}, closed {ctx.tp1_close*100:.0f}%")
    elif ctx.tp_hits == 1 and pnl_pct >= ctx.tp2_pct:
        sell_qty = ctx.original_qty * ctx.tp2_close
        ctx.sell(price, sell_qty)
        ctx.tp_hits = 2
        ctx.log(f"TP2 at {price:.2f}, closed {ctx.tp2_close*100:.0f}%")
    elif ctx.tp_hits == 2 and pnl_pct >= ctx.tp3_pct:
        ctx.close_position()
        ctx.tp_hits = 3
        ctx.log(f"TP3 at {price:.2f}, runner closed")
`,
    params: [
      { name: 'fast_period', type: 'integer', default: 10, min: 2, max: 120, step: 1 },
      { name: 'slow_period', type: 'integer', default: 30, min: 5, max: 240, step: 1 },
      { name: 'position_pct', type: 'percent', default: 0.9, min: 0.05, max: 1, step: 0.01 },
      { name: 'tp1_pct', type: 'percent', default: 0.02, min: 0.001, max: 1, step: 0.001 },
      { name: 'tp2_pct', type: 'percent', default: 0.05, min: 0.001, max: 1, step: 0.001 },
      { name: 'tp3_pct', type: 'percent', default: 0.10, min: 0.001, max: 2, step: 0.001 },
      { name: 'tp1_close', type: 'percent', default: 0.4, min: 0.05, max: 1, step: 0.05 },
      { name: 'tp2_close', type: 'percent', default: 0.4, min: 0.05, max: 1, step: 0.05 },
      { name: 'hard_stop_pct', type: 'percent', default: 0.03, min: 0.001, max: 0.5, step: 0.001 }
    ]
  }
]

function escapeForRegExp (value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function toPythonLiteral (value) {
  if (typeof value === 'boolean') {
    return value ? 'True' : 'False'
  }
  if (typeof value === 'number') {
    return Number.isFinite(value) ? String(value) : '0'
  }
  if (value === null || value === undefined) {
    return 'None'
  }
  return `'${String(value).replace(/\\/g, '\\\\').replace(/'/g, "\\'")}'`
}

export const SCRIPT_TEMPLATE_CATALOG = TEMPLATE_DEFINITIONS

export function getScriptTemplateByKey (key) {
  return TEMPLATE_DEFINITIONS.find(item => item.key === key) || null
}

export function buildTemplateParamValues (templateOrKey, overrides = {}) {
  const template = typeof templateOrKey === 'string' ? getScriptTemplateByKey(templateOrKey) : templateOrKey
  if (!template) return {}
  return template.params.reduce((acc, param) => {
    acc[param.name] = Object.prototype.hasOwnProperty.call(overrides, param.name)
      ? overrides[param.name]
      : param.default
    return acc
  }, {})
}

export function buildTemplateCode (templateOrKey, overrides = {}) {
  const template = typeof templateOrKey === 'string' ? getScriptTemplateByKey(templateOrKey) : templateOrKey
  if (!template) return ''
  const values = buildTemplateParamValues(template, overrides)
  return template.params.reduce((code, param) => {
    const literal = toPythonLiteral(values[param.name])
    const pattern = new RegExp(`(ctx\\.param\\(['"]${escapeForRegExp(param.name)}['"],\\s*)([^\\)]+)(\\))`)
    return code.replace(pattern, `$1${literal}$3`)
  }, template.code)
}
