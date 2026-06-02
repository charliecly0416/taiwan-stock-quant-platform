/**
 * 交易机器人预置策略脚本模板。
 * 每种机器人类型对应 on_init + on_bar Python 代码，参数由用户在向导中填写后注入顶部变量。
 * 运行时由后端 TradingExecutor 以 ScriptStrategy 方式执行。
 *
 * ctx API (StrategyScriptContext):
 *   ctx.param(name, default)       → 读取/初始化持久化参数
 *   ctx._params[name] = val        → 写入持久化参数
 *   ctx.bars(n)                    → 最近 n 根 K 线（ScriptBar: open/high/low/close/volume）
 *   ctx.position                   → ScriptPosition dict (side/size/entry_price)，bool(pos) 表示有仓位
 *   ctx.balance                    → 当前可用余额（按账户 quote currency 计价: 加密=USDT, 美股=USD, 外汇=账户基础货币）
 *   ctx.buy(price=, amount=)       → 买入信号（amount 为 quote currency 名义金额，后端按 leverage/market_type 换算成 qty/share/lot）
 *   ctx.sell(price=, amount=)      → 卖出信号
 *   ctx.close_position()           → 平仓
 *   ctx.log(msg)                   → 日志
 *
 * 多市场说明：模板逻辑只用 amount=名义金额 + price 接口，后端
 * trading_executor._to_local_qty 会按市场和杠杆换算成实际下单数量，
 * 所以同一个模板既能跑 BTC/USDT 也能跑 TSLA、EUR/USD。模板里的
 * "quote" 字样代表账户基础货币（加密=USDT，美股=USD，外汇=账户币种）。
 */

const TIMEFRAME_MINUTES = {
  '1m': 1, '5m': 5, '15m': 15, '1h': 60, '4h': 240, '1d': 1440
}

const FREQUENCY_MINUTES = {
  hourly: 60, '4h': 240, daily: 1440, weekly: 10080, biweekly: 20160, monthly: 43200
}

export const BOT_SCRIPT_TEMPLATES = {

  // ========== 网格交易 ==========
  grid: (params) => `# ---- Grid Trading Bot ----
UPPER     = ${params.upperPrice}
LOWER     = ${params.lowerPrice}
GRIDS     = ${params.gridCount}
AMT       = ${params.amountPerGrid}
MODE      = "${params.gridMode || 'arithmetic'}"
DIRECTION = "${params.gridDirection || 'neutral'}"
REF_PRICE = ${params.referencePrice || 0}
BUDGET    = ${params._initialCapital || 0}

def _build_levels():
    if MODE == "geometric" and LOWER > 0:
        r = (UPPER / LOWER) ** (1.0 / GRIDS)
        return [LOWER * (r ** i) for i in range(GRIDS + 1)]
    step = (UPPER - LOWER) / GRIDS
    return [LOWER + step * i for i in range(GRIDS + 1)]

LEVELS = _build_levels()

def on_init(ctx):
    anchor = REF_PRICE if REF_PRICE > 0 else (LOWER + UPPER) / 2.0
    bp = []
    sp = []
    for i, lv in enumerate(LEVELS):
        if lv < anchor and DIRECTION in ("neutral", "long"):
            bp.append(i)
        elif lv > anchor and DIRECTION in ("neutral", "short"):
            sp.append(i)
    ctx.param("bp", bp)
    ctx.param("sp", sp)
    ctx.param("prev_price", anchor)
    ctx.param("anchor_price", anchor)
    # 分别追踪多头/空头资金占用,防止单边网格无限开仓爆仓
    ctx.param("long_exposure", 0.0)
    ctx.param("short_exposure", 0.0)
    ctx.log("Grid anchor @ %.6f | buy_pending=%d sell_pending=%d [%.6f ~ %.6f]" % (anchor, len(bp), len(sp), LOWER, UPPER))

def on_bar(ctx, bar):
    if ctx.param("waterfall_pause", False):
        return

    price = bar.close
    upper = float(ctx.param("upperPrice", UPPER) or UPPER)
    lower = float(ctx.param("lowerPrice", LOWER) or LOWER)
    if price < lower or price > upper:
        return

    bounds_sig = (round(upper, 8), round(lower, 8), GRIDS, MODE)
    if ctx.param("_bounds_sig") != bounds_sig:
        ctx._params["_bounds_sig"] = bounds_sig
        if MODE == "geometric" and lower > 0:
            r = (upper / lower) ** (1.0 / GRIDS)
            levels = [lower * (r ** i) for i in range(GRIDS + 1)]
        else:
            step = (upper - lower) / GRIDS
            levels = [lower + step * i for i in range(GRIDS + 1)]
        anchor = ctx.param("anchor_price", REF_PRICE if REF_PRICE > 0 else (lower + upper) / 2.0)
        bp, sp = [], []
        for i, lv in enumerate(levels):
            if lv < anchor and DIRECTION in ("neutral", "long"):
                bp.append(i)
            elif lv > anchor and DIRECTION in ("neutral", "short"):
                sp.append(i)
        ctx._params["bp"] = bp
        ctx._params["sp"] = sp

    levels = []
    if MODE == "geometric" and lower > 0:
        r = (upper / lower) ** (1.0 / GRIDS)
        levels = [lower * (r ** i) for i in range(GRIDS + 1)]
    else:
        step = (upper - lower) / GRIDS
        levels = [lower + step * i for i in range(GRIDS + 1)]

    prev_price = ctx.param("prev_price", -1.0)
    anchor = ctx.param("anchor_price", REF_PRICE if REF_PRICE > 0 else (LOWER + UPPER) / 2.0)
    long_exp = ctx.param("long_exposure", 0.0)
    short_exp = ctx.param("short_exposure", 0.0)

    if prev_price < 0:
        prev_price = anchor
        ctx._params["prev_price"] = anchor

    if abs(price - prev_price) < 1e-8:
        return

    bp = set(ctx.param("bp", []))
    sp = set(ctx.param("sp", []))

    for i, lv in enumerate(levels):
        if prev_price > lv >= price and i in bp:
            # BUY: 优先减空头,否则开/加多头(需检查预算)
            if short_exp > 0:
                ctx.buy(price=lv, amount=AMT)
                short_exp = max(0.0, short_exp - AMT)
                bp.discard(i)
                if i + 1 < len(levels):
                    sp.add(i + 1)
                ctx.log("BUY(cover short) grid %d @ %.6f short_exp=%.2f" % (i, lv, short_exp))
            else:
                if BUDGET > 0 and (long_exp + AMT) > BUDGET:
                    ctx.log("Budget cap reached (long_exp=%.2f + %.2f > %.2f), skip BUY grid %d" % (long_exp, AMT, BUDGET, i))
                    continue
                ctx.buy(price=lv, amount=AMT)
                long_exp += AMT
                bp.discard(i)
                if i + 1 < len(levels):
                    sp.add(i + 1)
                ctx.log("BUY(open long) grid %d @ %.6f long_exp=%.2f" % (i, lv, long_exp))
        elif prev_price < lv <= price and i in sp:
            # SELL: 优先减多头,否则开/加空头(需检查预算)
            if long_exp > 0:
                ctx.sell(price=lv, amount=AMT)
                long_exp = max(0.0, long_exp - AMT)
                sp.discard(i)
                if i - 1 >= 0:
                    bp.add(i - 1)
                ctx.log("SELL(reduce long) grid %d @ %.6f long_exp=%.2f" % (i, lv, long_exp))
            else:
                if BUDGET > 0 and (short_exp + AMT) > BUDGET:
                    ctx.log("Budget cap reached (short_exp=%.2f + %.2f > %.2f), skip SELL grid %d" % (short_exp, AMT, BUDGET, i))
                    continue
                ctx.sell(price=lv, amount=AMT)
                short_exp += AMT
                sp.discard(i)
                if i - 1 >= 0:
                    bp.add(i - 1)
                ctx.log("SELL(open short) grid %d @ %.6f short_exp=%.2f" % (i, lv, short_exp))

    ctx._params["bp"] = list(bp)
    ctx._params["sp"] = list(sp)
    ctx._params["prev_price"] = price
    ctx._params["long_exposure"] = long_exp
    ctx._params["short_exposure"] = short_exp
`,

  // ========== 马丁格尔 ==========
  martingale: (params) => `# ---- Martingale Bot ----
import time as _time

INIT_AMT    = ${params.initialAmount}
MULTIPLIER  = ${params.multiplier}
MAX_LAYERS  = ${params.maxLayers}
DROP_PCT    = ${params.priceDropPct} / 100.0
TP_PCT      = ${params.takeProfitPct} / 100.0
SL_PCT      = ${(params.stopLossPct || 0)} / 100.0
DIRECTION   = "${params.direction || 'long'}"
ORDER_WAIT  = 120
BUDGET      = ${params._initialCapital || 0}

# Trailing take-profit (optional). When USE_TRAILING_TP is True the TP_PCT
# above is re-interpreted as the *activation* threshold: profit must first
# break above TP_PCT before peak tracking starts, after which the cycle
# exits as soon as price retraces TP_CB_PCT from the recorded peak.
USE_TRAILING_TP = ${params.trailingTpEnabled ? 'True' : 'False'}
TP_CB_PCT       = ${(params.trailingTpCallbackPct != null ? params.trailingTpCallbackPct : 0)} / 100.0

def on_init(ctx):
    ctx.param("layer", 0)
    ctx.param("last_entry_price", 0.0)
    ctx.param("total_cost", 0.0)
    ctx.param("total_qty", 0.0)
    ctx.param("last_order_ts", 0)
    # Trailing TP state: peak_price tracks best price since cycle start
    # (highest for long, lowest for short); trailing_active flips True once
    # profit breaks above TP_PCT (activation threshold).
    ctx.param("peak_price", 0.0)
    ctx.param("trailing_active", False)

def _reset_state(ctx):
    ctx._params["layer"] = 0
    ctx._params["total_cost"] = 0.0
    ctx._params["total_qty"] = 0.0
    ctx._params["last_entry_price"] = 0.0
    ctx._params["last_order_ts"] = 0
    ctx._params["peak_price"] = 0.0
    ctx._params["trailing_active"] = False

def _budget_ok(cost, amt):
    if BUDGET <= 0:
        return True
    return (cost + amt) <= BUDGET

def on_bar(ctx, bar):
    price = bar.close
    layer      = ctx.param("layer", 0)
    last_entry = ctx.param("last_entry_price", 0.0)
    cost       = ctx.param("total_cost", 0.0)
    qty        = ctx.param("total_qty", 0.0)
    last_ts    = ctx.param("last_order_ts", 0)
    has_pos    = ctx.position and float(ctx.position.get("size", 0)) > 0
    now        = int(_time.time())

    if not has_pos and layer == 0:
        if ctx.param("waterfall_pause", False):
            return
        if not _budget_ok(0, INIT_AMT):
            ctx.log("Budget exhausted (%.2f quote), skip opening" % BUDGET)
            return
        entry_qty = INIT_AMT / price if price > 0 else 0
        if DIRECTION == "long":
            ctx.buy(price=price, amount=INIT_AMT)
            ctx.log("Layer 1: BUY %.2f quote @ %.4f" % (INIT_AMT, price))
        else:
            ctx.sell(price=price, amount=INIT_AMT)
            ctx.log("Layer 1: SELL %.2f quote @ %.4f" % (INIT_AMT, price))
        ctx._params["layer"] = 1
        ctx._params["last_entry_price"] = price
        ctx._params["total_cost"] = INIT_AMT
        ctx._params["total_qty"] = entry_qty
        ctx._params["last_order_ts"] = now
        # Seed trailing state with the entry price so the first peak is
        # never below the entry for longs / above the entry for shorts.
        ctx._params["peak_price"] = price
        ctx._params["trailing_active"] = False
        return

    if not has_pos and layer > 0:
        if last_ts > 0 and (now - last_ts) < ORDER_WAIT:
            return
        ctx.log("Position gone after wait, resetting (layer was %d)" % layer)
        _reset_state(ctx)
        return

    avg_price = cost / qty if qty > 0 else last_entry

    # ---- Trailing peak update (always-on bookkeeping; used only when
    # USE_TRAILING_TP is True). We track peak even before activation so
    # the moment trailing activates we already have an accurate baseline.
    peak_price = ctx.param("peak_price", 0.0)
    if peak_price <= 0:
        peak_price = avg_price if avg_price > 0 else price
    if DIRECTION == "long":
        if price > peak_price:
            peak_price = price
    else:
        if price < peak_price:
            peak_price = price
    ctx._params["peak_price"] = peak_price

    if DIRECTION == "long":
        profit_pct = (price - avg_price) / avg_price if avg_price > 0 else 0.0
        sl_hit     = SL_PCT > 0 and avg_price > 0 and price <= avg_price * (1 - SL_PCT)
        add_hit    = layer < MAX_LAYERS and last_entry > 0 and price <= last_entry * (1 - DROP_PCT)
    else:
        profit_pct = (avg_price - price) / avg_price if avg_price > 0 else 0.0
        sl_hit     = SL_PCT > 0 and avg_price > 0 and price >= avg_price * (1 + SL_PCT)
        add_hit    = layer < MAX_LAYERS and last_entry > 0 and price >= last_entry * (1 + DROP_PCT)

    if USE_TRAILING_TP and avg_price > 0:
        trailing_active = ctx.param("trailing_active", False)

        # Activation: once unrealised profit breaks above TP_PCT, start
        # following the peak. Once flipped on we don't flip it back off
        # within the same cycle (resetting is done in _reset_state).
        if not trailing_active and profit_pct >= TP_PCT:
            trailing_active = True
            ctx._params["trailing_active"] = True
            ctx.log("TRAILING TP ARMED @ %.4f, avg=%.4f, profit=%.2f%%, peak=%.4f"
                    % (price, avg_price, profit_pct * 100, peak_price))

        # Trigger: once armed, exit on retracement from the peak.
        if trailing_active and peak_price > 0:
            if DIRECTION == "long":
                drawdown = (peak_price - price) / peak_price
            else:
                drawdown = (price - peak_price) / peak_price
            if drawdown >= TP_CB_PCT:
                pnl = (price - avg_price) * qty if DIRECTION == "long" else (avg_price - price) * qty
                ctx.log("TRAILING TP EXIT @ %.4f (peak=%.4f, drawdown=%.2f%%), avg=%.4f, PnL=%.2f quote"
                        % (price, peak_price, drawdown * 100, avg_price, pnl))
                ctx.close_position()
                _reset_state(ctx)
                return
        tp_hit = False
    else:
        # Classic fixed take-profit: close immediately on hit.
        tp_hit = profit_pct >= TP_PCT and avg_price > 0

    if tp_hit:
        pnl = (price - avg_price) * qty if DIRECTION == "long" else (avg_price - price) * qty
        ctx.log("TAKE PROFIT @ %.4f, avg=%.4f, PnL=%.2f quote" % (price, avg_price, pnl))
        ctx.close_position()
        _reset_state(ctx)
        return

    if sl_hit:
        pnl = (price - avg_price) * qty if DIRECTION == "long" else (avg_price - price) * qty
        ctx.log("STOP LOSS @ %.4f, avg=%.4f, PnL=%.2f quote" % (price, avg_price, pnl))
        ctx.close_position()
        _reset_state(ctx)
        return

    if add_hit and not ctx.param("waterfall_pause", False):
        amt = INIT_AMT * (MULTIPLIER ** layer)
        if not _budget_ok(cost, amt):
            ctx.log("Budget cap reached (cost=%.2f + amt=%.2f > %.2f quote), skip add layer %d" % (cost, amt, BUDGET, layer + 1))
            return
        add_qty = amt / price if price > 0 else 0
        if DIRECTION == "long":
            ctx.buy(price=price, amount=amt)
            ctx.log("Layer %d: BUY %.2f quote @ %.4f" % (layer + 1, amt, price))
        else:
            ctx.sell(price=price, amount=amt)
            ctx.log("Layer %d: SELL %.2f quote @ %.4f" % (layer + 1, amt, price))
        ctx._params["layer"] = layer + 1
        ctx._params["last_entry_price"] = price
        ctx._params["total_cost"] = cost + amt
        ctx._params["total_qty"] = qty + add_qty
        ctx._params["last_order_ts"] = now
        # Adding a layer doesn't reset trailing armed state — that would be
        # exploitable: a small dip that triggers an add could disarm a
        # trailing exit that was about to fire. We deliberately keep
        # trailing_active and peak_price untouched here.
`,

  // ========== 趋势跟踪 ==========
  trend: (params) => `# ---- Trend Following Bot ----
MA_PERIOD    = ${params.maPeriod}
MA_TYPE      = "${params.maType || 'EMA'}"
CONFIRM_BARS = ${params.confirmBars}
POS_PCT      = ${params.positionPct} / 100.0
DIRECTION    = "${params.direction || 'long'}"

# Trailing take-profit (optional). When USE_TRAILING_TP is True, once
# unrealised profit (vs entry price) crosses TP_ACT_PCT, the bot tracks
# the best price reached and exits the moment the price retraces by
# TP_CB_PCT from that peak — independent of the MA crossback signal.
USE_TRAILING_TP = ${params.trailingTpEnabled ? 'True' : 'False'}
TP_ACT_PCT      = ${(params.trailingTpActivationPct != null ? params.trailingTpActivationPct : 0)} / 100.0
TP_CB_PCT       = ${(params.trailingTpCallbackPct != null ? params.trailingTpCallbackPct : 0)} / 100.0

def _sma(closes):
    if len(closes) < MA_PERIOD:
        return None
    return sum(closes[-MA_PERIOD:]) / MA_PERIOD

def _wma(closes):
    if len(closes) < MA_PERIOD:
        return None
    window = closes[-MA_PERIOD:]
    w = list(range(1, MA_PERIOD + 1))
    return sum(p * wt for p, wt in zip(window, w)) / sum(w)

def on_init(ctx):
    ctx.param("ema_value", 0.0)
    ctx.param("ema_ready", False)
    ctx.param("above_cnt", 0)
    ctx.param("below_cnt", 0)
    # Trailing TP bookkeeping. entry_price is the close at the moment we
    # opened the current position (long or short); peak_price tracks the
    # best price reached since that entry; trailing_active flips True
    # once profit_pct crosses TP_ACT_PCT.
    ctx.param("entry_price", 0.0)
    ctx.param("peak_price", 0.0)
    ctx.param("trailing_active", False)

def _reset_trailing(ctx):
    ctx._params["entry_price"] = 0.0
    ctx._params["peak_price"] = 0.0
    ctx._params["trailing_active"] = False

def on_bar(ctx, bar):
    bars = ctx.bars(MA_PERIOD + 10)
    if len(bars) < MA_PERIOD:
        return

    closes = [b.close for b in bars]
    price = bar.close

    if MA_TYPE == "SMA":
        ma = _sma(closes)
    elif MA_TYPE == "WMA":
        ma = _wma(closes)
    else:
        ema_prev = ctx.param("ema_value", 0.0)
        ema_ok   = ctx.param("ema_ready", False)
        if not ema_ok:
            ma = sum(closes[-MA_PERIOD:]) / MA_PERIOD
            ctx._params["ema_value"] = ma
            ctx._params["ema_ready"] = True
        else:
            alpha = 2.0 / (MA_PERIOD + 1)
            ma = alpha * price + (1 - alpha) * ema_prev
            ctx._params["ema_value"] = ma

    if ma is None or ma <= 0:
        return

    above = ctx.param("above_cnt", 0)
    below = ctx.param("below_cnt", 0)

    if price > ma:
        above += 1
        below = 0
    elif price < ma:
        below += 1
        above = 0
    else:
        above = 0
        below = 0

    ctx._params["above_cnt"] = above
    ctx._params["below_cnt"] = below

    has_pos = ctx.position and float(ctx.position.get("size", 0)) > 0
    side = ctx.position.get("side", "") if has_pos else ""

    # If the position vanished (manual close, SL, etc) while trailing state
    # is still set, clear it so the next open starts fresh.
    if not has_pos and ctx.param("entry_price", 0.0) > 0:
        _reset_trailing(ctx)

    # ---- Trailing TP evaluation (runs before MA-based exit, so a trailing
    # exit can fire even if the MA hasn't crossed back yet — this is the
    # whole point: lock profit on a runaway move).
    if USE_TRAILING_TP and has_pos and side in ("long", "short"):
        entry_price     = ctx.param("entry_price", 0.0)
        peak_price      = ctx.param("peak_price", 0.0)
        trailing_active = ctx.param("trailing_active", False)

        # Backfill entry_price if missing (e.g. bot was created before the
        # trailing-TP upgrade and already had an open position).
        if entry_price <= 0:
            pe = 0.0
            try:
                pe = float(ctx.position.get("entry_price", 0) or 0)
            except Exception:
                pe = 0.0
            entry_price = pe if pe > 0 else price
            ctx._params["entry_price"] = entry_price

        if side == "long":
            if peak_price <= 0 or price > peak_price:
                peak_price = price
            profit_pct = (price - entry_price) / entry_price if entry_price > 0 else 0.0
        else:
            if peak_price <= 0 or price < peak_price:
                peak_price = price
            profit_pct = (entry_price - price) / entry_price if entry_price > 0 else 0.0
        ctx._params["peak_price"] = peak_price

        if not trailing_active and profit_pct >= TP_ACT_PCT:
            trailing_active = True
            ctx._params["trailing_active"] = True
            ctx.log("TRAILING TP ARMED side=%s @ %.6f entry=%.6f profit=%.2f%% peak=%.6f"
                    % (side, price, entry_price, profit_pct * 100, peak_price))

        if trailing_active and peak_price > 0:
            if side == "long":
                drawdown = (peak_price - price) / peak_price
            else:
                drawdown = (price - peak_price) / peak_price
            if drawdown >= TP_CB_PCT:
                ctx.log("TRAILING TP EXIT side=%s @ %.6f (peak=%.6f drawdown=%.2f%%)"
                        % (side, price, peak_price, drawdown * 100))
                ctx.close_position()
                _reset_trailing(ctx)
                return  # don't double-fire on this bar

    if DIRECTION in ("long", "both"):
        if not has_pos and above >= CONFIRM_BARS:
            amt = ctx.balance * POS_PCT
            if amt > 0:
                ctx.buy(price=price, amount=amt)
                ctx.log("LONG @ %.6f, MA=%.6f, above=%d" % (price, ma, above))
                # Seed trailing state for the fresh long.
                ctx._params["entry_price"] = price
                ctx._params["peak_price"] = price
                ctx._params["trailing_active"] = False
        elif has_pos and side == "long" and below >= CONFIRM_BARS:
            ctx.close_position()
            ctx.log("CLOSE LONG @ %.6f, MA=%.6f" % (price, ma))
            _reset_trailing(ctx)

    if DIRECTION in ("short", "both"):
        if not has_pos and below >= CONFIRM_BARS:
            amt = ctx.balance * POS_PCT
            if amt > 0:
                ctx.sell(price=price, amount=amt)
                ctx.log("SHORT @ %.6f, MA=%.6f, below=%d" % (price, ma, below))
                # Seed trailing state for the fresh short.
                ctx._params["entry_price"] = price
                ctx._params["peak_price"] = price
                ctx._params["trailing_active"] = False
        elif has_pos and side == "short" and above >= CONFIRM_BARS:
            ctx.close_position()
            ctx.log("CLOSE SHORT @ %.6f, MA=%.6f" % (price, ma))
            _reset_trailing(ctx)
`,

  // ========== 定投 DCA ==========
  dca: (params, context) => {
    const tf = (context && context.timeframe) || '1h'
    const tfMin = TIMEFRAME_MINUTES[tf] || 60
    const freqMin = params.frequency === 'every_bar' ? tfMin : (FREQUENCY_MINUTES[params.frequency] || 1440)

    return `# ---- DCA (Dollar Cost Averaging) Bot ----
import time as _time

AMT_EACH       = ${params.amountEach}
TOTAL_BUDGET   = ${params.totalBudget || 0}
DIP_BUY        = ${params.dipBuyEnabled ? 'True' : 'False'}
DIP_THRESHOLD  = ${params.dipThreshold || 5} / 100.0
INTERVAL_SEC   = ${freqMin * 60}

def on_init(ctx):
    ctx.param("total_spent", 0.0)
    ctx.param("total_qty", 0.0)
    ctx.param("buy_count", 0)
    ctx.param("last_buy_ts", 0)
    ctx.param("last_buy_price", 0.0)

def on_bar(ctx, bar):
    price       = bar.close
    total_spent = ctx.param("total_spent", 0.0)
    total_qty   = ctx.param("total_qty", 0.0)
    buy_count   = ctx.param("buy_count", 0)
    last_ts     = ctx.param("last_buy_ts", 0)
    last_price  = ctx.param("last_buy_price", 0.0)
    has_pos     = ctx.position and float(ctx.position.get("size", 0)) > 0
    now         = int(_time.time())

    # 若仓位被外部平掉(手动/止损等),重置累计状态以便下一轮 DCA
    if buy_count > 0 and total_qty > 0 and not has_pos:
        ctx.log("DCA position closed externally, resetting stats")
        total_spent = 0.0
        total_qty = 0.0
        buy_count = 0
        last_ts = 0
        last_price = 0.0
        ctx._params["total_spent"] = 0.0
        ctx._params["total_qty"] = 0.0
        ctx._params["buy_count"] = 0
        ctx._params["last_buy_ts"] = 0
        ctx._params["last_buy_price"] = 0.0

    budget_done = TOTAL_BUDGET > 0 and total_spent >= TOTAL_BUDGET
    if budget_done:
        return

    # 使用真实时间戳而非 bar 计数,确保 frequency 与 timeframe 脱耦
    elapsed = now - last_ts
    due = (buy_count == 0) or (elapsed >= INTERVAL_SEC)
    if not due:
        return

    amount = AMT_EACH

    if DIP_BUY and last_price > 0:
        drop = (last_price - price) / last_price
        if drop >= DIP_THRESHOLD:
            amount = AMT_EACH * 2
            ctx.log("DIP detected (%.2f%%), doubling buy" % (drop * 100))

    if TOTAL_BUDGET > 0:
        remaining = TOTAL_BUDGET - total_spent
        if amount > remaining:
            amount = remaining
        if amount <= 0:
            return

    qty = amount / price if price > 0 else 0
    ctx.buy(price=price, amount=amount)
    ctx._params["total_spent"] = total_spent + amount
    ctx._params["total_qty"] = total_qty + qty
    ctx._params["buy_count"] = buy_count + 1
    ctx._params["last_buy_ts"] = now
    ctx._params["last_buy_price"] = price
    ctx.log("DCA #%d: BUY %.2f quote @ %.6f (total: %.2f)" % (buy_count + 1, amount, price, total_spent + amount))
`
  }
}

/**
 * 生成完整的策略脚本代码
 * @param {string} botType - 机器人类型
 * @param {object} params - 策略参数
 * @param {object} context - 额外上下文 { timeframe }
 * @returns {string} Python 策略代码
 */
export function generateBotScript (botType, params, context) {
  const generator = BOT_SCRIPT_TEMPLATES[botType]
  if (!generator) {
    throw new Error(`Unknown bot type: ${botType}`)
  }
  return generator(params, context)
}
