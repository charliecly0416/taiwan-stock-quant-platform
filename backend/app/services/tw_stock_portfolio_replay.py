"""In-memory TWStock portfolio rule replay for research-only comparison."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from math import floor
from typing import Any, Dict, List, Optional

from app.services.kline import KlineService
from app.services.tw_stock_observation_replay import TWStockObservationReplayService, VARIANTS
from app.services.tw_stock_qlib_option_c import research_only_trading_flags


TAIPEI_TZ = timezone(timedelta(hours=8))

POLICY_PROFILES = {
    "direct_rank": {
        "label": "直接跟排名",
        "description": "高排名直接进入历史模拟观察，作为追涨基线。",
    },
    "position_filter": {
        "label": "加入追高过滤",
        "description": "高排名但过热时不新增，偏高时降低优先级。",
    },
    "pullback_entry": {
        "label": "等回调再观察",
        "description": "排名和趋势支持后，优先等价格位置合理或靠近均线。",
    },
    "confirmed_exit": {
        "label": "连续转弱才复盘",
        "description": "不因单日排名波动退出，连续转弱后才做风险复盘。",
    },
    "rank_rotate_top30": {
        "label": "跌出 Top30 轮动",
        "description": "持仓跌出 Top30 时卖出排名最低的一支，再从 Top10 最高排名补一支。",
    },
    "rank_rotate_top50": {
        "label": "跌出 Top50 轮动",
        "description": "持仓跌出 Top50 时才卖出排名最低的一支，再从 Top10 最高排名补一支。",
    },
    "rank_rotate_top30_adaptive_score": {
        "label": "Top30 自适应 score",
        "description": "继承 Top30 轮动；正常市况不干预，谨慎/下跌市况只从 qlib score 0.04-0.08 的 Top10 候选补仓。",
    },
    "rank_rotate_top50_adaptive_score": {
        "label": "Top50 自适应 score",
        "description": "继承 Top50 轮动；正常市况不干预，谨慎/下跌市况只从 qlib score 0.04-0.08 的 Top10 候选补仓。",
    },
    "rank_rotate_top50_adaptive_score_risk_control": {
        "label": "Top50 自适应 score + 风控",
        "description": "继承 Top50 自适应 score；市场谨慎/下跌且组合回撤超过 8% 时暂停补仓，恢复后再补。",
    },
}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


class TWStockPortfolioReplayService:
    """Replay observation rules in memory without writing business state."""

    def __init__(self, *, observation_service: Optional[Any] = None, kline_service: Optional[Any] = None) -> None:
        self.observation_service = observation_service or TWStockObservationReplayService()
        self.kline_service = kline_service or KlineService()

    def replay(self, *, config: Dict[str, Any]) -> Dict[str, Any]:
        cfg = self._normalize_config(config or {})
        observation = self.observation_service.compare(
            start_date=cfg["startDate"],
            end_date=cfg["endDate"],
            bucket=cfg["bucket"],
            max_items=cfg["maxItems"],
            technical_strategies=cfg["technicalStrategies"],
            signal_root=cfg.get("signalRoot"),
        )
        comparison = {}
        daily = observation.get("daily") or []
        requested = VARIANTS if cfg["variant"] == "all" else [cfg["variant"]]
        for variant in requested:
            comparison[variant] = self._replay_variant(variant=variant, daily=daily, cfg=cfg)
        strategy_comparison = self._strategy_comparison(daily=daily, cfg=cfg)
        return {
            "ok": True,
            "status": "accepted",
            "simulation_only": True,
            "research_signal_not_order": True,
            "replay_type": "portfolio_rule_historical_simulation",
            "persist": False,
            "writes_business_db": False,
            "config": cfg,
            "source": observation.get("source") or {},
            "execution": {
                "mode": cfg["executionMode"],
                "label": self._execution_mode_label(cfg["executionMode"]),
                "lookahead_guard": cfg["executionMode"] == "next_trading_day_close",
            },
            "comparison": comparison,
            "strategyComparison": strategy_comparison,
            "dataQuality": {
                "point_in_time": True,
                "warnings": list(dict.fromkeys(list((observation.get("dataQuality") or {}).get("warnings") or []) + self._comparison_warnings(comparison))),
            },
            "trading": research_only_trading_flags(),
        }

    def _strategy_comparison(self, *, daily: List[Dict[str, Any]], cfg: Dict[str, Any]) -> Dict[str, Any]:
        policy_variants = {
            "rank_rotate_top30": "qlib_only",
            "rank_rotate_top50": "qlib_only",
            "rank_rotate_top50_adaptive_score": "qlib_only",
            "rank_rotate_top50_adaptive_score_risk_control": "qlib_only",
            "confirmed_exit": "qlib_plus_trend_position_risk",
        }
        return {
            key: self._replay_variant(variant=variant, daily=daily, cfg=cfg, policy=key)
            for key, variant in policy_variants.items()
        }

    def _replay_variant(self, *, variant: str, daily: List[Dict[str, Any]], cfg: Dict[str, Any], policy: str = "position_filter") -> Dict[str, Any]:
        cash = float(cfg["initialCash"])
        holdings: Dict[str, int] = {}
        curve = []
        actions = []
        fees = 0.0
        warnings: List[str] = []
        position_risk_summary = {"blocked_overheated_adds": 0, "deprioritized_elevated_adds": 0, "risk_review_events": 0}
        adaptive_policies = {"rank_rotate_top30_adaptive_score", "rank_rotate_top50_adaptive_score", "rank_rotate_top50_adaptive_score_risk_control"}
        risk_control_policies = {"rank_rotate_top50_adaptive_score_risk_control"}
        adaptive_score_summary = {"enabled": policy in adaptive_policies, "normal_days": 0, "caution_days": 0, "blocked_adds": 0}
        portfolio_risk_summary = {"enabled": policy in risk_control_policies, "pause_days": 0, "blocked_adds": 0, "trigger": "market_caution_or_severe_and_portfolio_drawdown_below_8pct" if policy in risk_control_policies else "disabled"}
        risk_paused = False
        weak_streaks: Dict[str, int] = {}
        peak = cash
        max_drawdown = 0.0
        for day in sorted(daily, key=lambda item: str(item.get("asof") or "")):
            asof = str(day.get("asof") or "")
            items = ((day.get("variants") or {}).get(variant) or {}).get("items") or []
            add_used = 0
            risk_used = 0
            prices = {symbol: self._execution_price(symbol, asof, cfg["executionMode"]) for symbol in self._symbols_for_day(items, holdings)}
            for symbol, price in prices.items():
                if price is None:
                    warnings.append(f"missing_close:{asof}:{symbol}")
            if policy in {"rank_rotate_top30", "rank_rotate_top50", "rank_rotate_top30_adaptive_score", "rank_rotate_top50_adaptive_score", "rank_rotate_top50_adaptive_score_risk_control"}:
                pre_equity = cash + sum(qty * (prices.get(symbol) or 0.0) for symbol, qty in holdings.items())
                pre_drawdown = (pre_equity / peak - 1.0) if peak > 0 else 0.0
                market_state = str((self._market_regime(asof) or {}).get("state") or "normal")
                if policy in risk_control_policies and market_state != "normal" and pre_drawdown <= -0.08:
                    risk_paused = True
                elif policy in risk_control_policies and (market_state == "normal" or pre_drawdown >= -0.04):
                    risk_paused = False
                rotation = self._apply_rank_rotation_policy(
                    asof=asof,
                    items=items,
                    prices=prices,
                    holdings=holdings,
                    cash=cash,
                    cfg=cfg,
                    policy=policy,
                    adaptive_score_summary=adaptive_score_summary,
                    portfolio_risk_summary=portfolio_risk_summary,
                    risk_paused=risk_paused,
                )
                cash = rotation["cash"]
                fees += rotation["fees"]
                actions.extend(rotation["actions"])
                equity = cash + sum(qty * (prices.get(symbol) or 0.0) for symbol, qty in holdings.items())
                peak = max(peak, equity)
                max_drawdown = min(max_drawdown, (equity / peak - 1.0) if peak > 0 else 0.0)
                curve.append({"date": asof, "equity": round(equity, 2), "cash": round(cash, 2), "holdingCount": len(holdings), "simulation_only": True})
                continue
            for item in items:
                symbol = str(item.get("symbol") or "")
                decision_code = str((item.get("decision") or {}).get("code") or "")
                action_code = str((item.get("actionPlan") or {}).get("code") or "")
                risk_payload = item.get("positionRisk") or (item.get("technical") or {}).get("positionRisk") or {}
                risk_status = str((risk_payload or {}).get("status") or "")
                technical_status = str((item.get("technical") or {}).get("status") or "")
                if decision_code == "risk_review" or action_code == "risk_review" or technical_status == "technical_weak":
                    weak_streaks[symbol] = weak_streaks.get(symbol, 0) + 1
                else:
                    weak_streaks[symbol] = 0
                code = self._code_for_policy(
                    policy=policy,
                    action_code=action_code,
                    decision_code=decision_code,
                    risk=risk_payload if isinstance(risk_payload, dict) else {},
                    weak_streak=weak_streaks.get(symbol, 0),
                )
                if risk_status == "overheated":
                    if code == "new_watch":
                        position_risk_summary["blocked_overheated_adds"] += 1
                        code = "manual_review"
                    elif code in {"manual_review", "risk_review"}:
                        position_risk_summary["risk_review_events"] += 1
                elif risk_status == "elevated" and code == "new_watch":
                    position_risk_summary["deprioritized_elevated_adds"] += 1
                price = prices.get(symbol)
                if price is None:
                    actions.append(self._action(asof, symbol, "historical_skip", 0, None, "历史模拟：价格缺失，跳过。"))
                    continue
                if code == "new_watch" and symbol not in holdings and add_used < cfg["maxAddPerDay"] and len(holdings) < cfg["maxHoldings"]:
                    remaining_slots = max(1, cfg["maxHoldings"] - len(holdings))
                    per_cash = cash / remaining_slots
                    qty = self._affordable_lot_quantity(per_cash, price, cfg)
                    cost = qty * price
                    fee = cost * cfg["feeRate"]
                    if qty > 0 and cash >= cost + fee:
                        cash -= cost + fee
                        fees += fee
                        holdings[symbol] = holdings.get(symbol, 0) + int(qty)
                        add_used += 1
                        actions.append(self._action(asof, symbol, "historical_add", int(qty), price, "历史模拟：new_watch 且组合仍有现金与名额。"))
                    else:
                        actions.append(self._action(asof, symbol, "historical_skip", 0, price, "历史模拟：现金不足或数量不足，跳过。"))
                elif code == "risk_review" and symbol in holdings and risk_used < cfg["maxRiskActionPerDay"]:
                    qty = holdings.pop(symbol)
                    proceeds = qty * price
                    fee_tax = proceeds * (cfg["feeRate"] + cfg["sellTaxRate"])
                    cash += proceeds - fee_tax
                    fees += fee_tax
                    risk_used += 1
                    actions.append(self._action(asof, symbol, "historical_risk_reduce", int(qty), price, "历史模拟：进入风险复盘，降低该历史模拟持有。"))
                elif code == "manual_review":
                    actions.append(self._action(asof, symbol, "historical_skip", 0, price, "历史模拟：人工复核，不自动动作。"))
                elif code == "data_insufficient":
                    actions.append(self._action(asof, symbol, "historical_skip", 0, price, "历史模拟：数据不足，不自动动作。"))
                else:
                    actions.append(self._action(asof, symbol, "historical_hold" if symbol in holdings else "historical_skip", 0, price, "历史模拟：观察队列保持。"))
            equity = cash + sum(qty * (prices.get(symbol) or 0.0) for symbol, qty in holdings.items())
            peak = max(peak, equity)
            max_drawdown = min(max_drawdown, (equity / peak - 1.0) if peak > 0 else 0.0)
            curve.append({"date": asof, "equity": round(equity, 2), "cash": round(cash, 2), "holdingCount": len(holdings), "simulation_only": True})
        final_equity = curve[-1]["equity"] if curve else cash
        return {
            "profile": {"key": policy, **POLICY_PROFILES.get(policy, {"label": policy, "description": ""})},
            "metrics": {
                "totalReturn": round(final_equity / cfg["initialCash"] - 1.0, 6) if cfg["initialCash"] > 0 else 0.0,
                "maxDrawdown": round(max_drawdown, 6),
                "actionCount": len([item for item in actions if item["action"] in {"historical_add", "historical_risk_reduce"}]),
                "addActionCount": len([item for item in actions if item["action"] == "historical_add"]),
                "riskActionCount": len([item for item in actions if item["action"] == "historical_risk_reduce"]),
                "feeAndTax": round(fees, 2),
                "finalEquity": round(final_equity, 2),
            },
            "equityCurve": curve,
            "historicalActions": actions,
            "positionRiskSummary": position_risk_summary,
            "adaptiveScoreSummary": adaptive_score_summary,
            "portfolioRiskSummary": portfolio_risk_summary,
            "dataQuality": {"warnings": list(dict.fromkeys(warnings))},
        }

    def _apply_rank_rotation_policy(self, *, asof: str, items: List[Dict[str, Any]], prices: Dict[str, Optional[float]], holdings: Dict[str, int], cash: float, cfg: Dict[str, Any], policy: str, adaptive_score_summary: Optional[Dict[str, Any]] = None, portfolio_risk_summary: Optional[Dict[str, Any]] = None, risk_paused: bool = False) -> Dict[str, Any]:
        threshold = 30 if "top30" in policy else 50
        ranks = self._rank_map(items)
        actions: List[Dict[str, Any]] = []
        fees = 0.0

        sell_symbol = self._rank_rotation_sell_symbol(holdings=holdings, ranks=ranks, threshold=threshold)
        if sell_symbol:
            price = prices.get(sell_symbol)
            if price is None:
                actions.append(self._action(asof, sell_symbol, "historical_skip", 0, None, f"历史模拟：持仓跌出 Top{threshold} 但价格缺失，跳过卖出。"))
            else:
                qty = holdings.pop(sell_symbol, 0)
                proceeds = qty * price
                fee_tax = proceeds * (cfg["feeRate"] + cfg["sellTaxRate"])
                cash += proceeds - fee_tax
                fees += fee_tax
                actions.append(self._action(asof, sell_symbol, "historical_risk_reduce", int(qty), price, f"历史模拟：跌出 Top{threshold}，卖出当前持仓中排名最低的一支。"))

        buy_item = None
        blocked_candidates = 0
        for candidate in self._rank_rotation_buy_candidates(items=items, holdings=holdings):
            decision = self._adaptive_score_buy_decision(candidate, asof=asof, policy=policy)
            if adaptive_score_summary is not None:
                if decision["market_state"] == "normal":
                    adaptive_score_summary["normal_days"] += 1
                elif decision["market_state"] != "unavailable":
                    adaptive_score_summary["caution_days"] += 1
            if decision["allowed"]:
                buy_item = candidate
                break
            blocked_candidates += 1
            if adaptive_score_summary is not None:
                adaptive_score_summary["blocked_adds"] += 1
            actions.append(self._action(asof, str(candidate.get("symbol") or ""), "historical_skip", 0, prices.get(str(candidate.get("symbol") or "")), decision["reason"]))
        if risk_paused:
            if buy_item and len(holdings) < cfg["maxHoldings"]:
                if portfolio_risk_summary is not None:
                    portfolio_risk_summary["pause_days"] += 1
                    portfolio_risk_summary["blocked_adds"] += 1
                actions.append(self._action(asof, str(buy_item.get("symbol") or ""), "historical_skip", 0, prices.get(str(buy_item.get("symbol") or "")), "历史模拟：市场谨慎/下跌且组合回撤超过 8%，风控暂停补仓。"))
            buy_item = None
        if buy_item and len(holdings) < cfg["maxHoldings"]:
            symbol = str(buy_item.get("symbol") or "")
            price = prices.get(symbol)
            if price is None:
                actions.append(self._action(asof, symbol, "historical_skip", 0, None, "历史模拟：Top10 候选价格缺失，跳过买入。"))
            else:
                remaining_slots = max(1, cfg["maxHoldings"] - len(holdings))
                per_cash = cash / remaining_slots
                qty = self._affordable_lot_quantity(per_cash, price, cfg)
                cost = qty * price
                fee = cost * cfg["feeRate"]
                if qty > 0 and cash >= cost + fee:
                    cash -= cost + fee
                    fees += fee
                    holdings[symbol] = holdings.get(symbol, 0) + int(qty)
                    actions.append(self._action(asof, symbol, "historical_add", int(qty), price, "历史模拟：从当天 Top10 选择最高排名且未持有的一支补入。"))
                else:
                    actions.append(self._action(asof, symbol, "historical_skip", 0, price, "历史模拟：现金不足或数量不足，跳过买入。"))
        elif not actions or blocked_candidates:
            actions.append(self._action(asof, "", "historical_hold", 0, None, f"历史模拟：无可补入 Top10 候选，或候选未通过 Top{threshold} 自适应 score 过滤。"))

        return {"cash": cash, "fees": fees, "actions": actions}

    @staticmethod
    def _affordable_lot_quantity(cash_budget: float, price: float, cfg: Dict[str, Any]) -> int:
        gross_unit = price * (1.0 + cfg["feeRate"])
        if gross_unit <= 0:
            return 0
        return floor(cash_budget / gross_unit / cfg["lotSize"]) * cfg["lotSize"]

    @staticmethod
    def _rank_map(items: List[Dict[str, Any]]) -> Dict[str, int]:
        ranks: Dict[str, int] = {}
        for item in items:
            symbol = str(item.get("symbol") or "")
            if not symbol:
                continue
            try:
                rank = int(item.get("rank") or 999999)
            except Exception:
                rank = 999999
            ranks[symbol] = rank
        return ranks

    @staticmethod
    def _rank_rotation_sell_symbol(*, holdings: Dict[str, int], ranks: Dict[str, int], threshold: int) -> Optional[str]:
        candidates = []
        for symbol in holdings:
            rank = ranks.get(symbol, 999999)
            if rank > threshold:
                candidates.append((rank, symbol))
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return candidates[0][1]

    @staticmethod
    def _rank_rotation_buy_item(*, items: List[Dict[str, Any]], holdings: Dict[str, int]) -> Optional[Dict[str, Any]]:
        candidates = []
        for item in items:
            symbol = str(item.get("symbol") or "")
            if not symbol or symbol in holdings:
                continue
            try:
                rank = int(item.get("rank") or 999999)
            except Exception:
                rank = 999999
            if rank <= 10:
                candidates.append((rank, symbol, item))
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], item[1]))
        return candidates[0][2]

    @staticmethod
    def _rank_rotation_buy_candidates(*, items: List[Dict[str, Any]], holdings: Dict[str, int]) -> List[Dict[str, Any]]:
        candidates = []
        for item in items:
            symbol = str(item.get("symbol") or "")
            if not symbol or symbol in holdings:
                continue
            try:
                rank = int(item.get("rank") or 999999)
            except Exception:
                rank = 999999
            if rank <= 10:
                candidates.append((rank, symbol, item))
        candidates.sort(key=lambda item: (item[0], item[1]))
        return [item[2] for item in candidates]

    def _adaptive_score_buy_decision(self, item: Dict[str, Any], *, asof: str, policy: str) -> Dict[str, Any]:
        if policy not in {"rank_rotate_top30_adaptive_score", "rank_rotate_top50_adaptive_score", "rank_rotate_top50_adaptive_score_risk_control"}:
            return {"allowed": True, "market_state": "disabled", "reason": "历史模拟：未启用自适应 score 过滤。"}
        market = self._market_regime(asof)
        state = market.get("state") or "normal"
        if state == "normal":
            return {"allowed": True, "market_state": state, "reason": "历史模拟：正常/牛市不干预原轮动策略。"}
        score = self._qlib_score(item)
        if score is None:
            return {"allowed": True, "market_state": state, "reason": "历史模拟：缺少 qlib score，保留原轮动策略避免误拦截。"}
        if 0.04 <= score <= 0.08:
            return {"allowed": True, "market_state": state, "reason": "历史模拟：谨慎/下跌市况，qlib score 位于 0.04-0.08 校准区间。"}
        return {"allowed": False, "market_state": state, "reason": f"历史模拟：谨慎/下跌市况，qlib score {score:.4f} 不在 0.04-0.08 校准区间，跳过补仓。"}

    @staticmethod
    def _qlib_score(item: Dict[str, Any]) -> Optional[float]:
        raw = item.get("score")
        if raw is None and isinstance(item.get("qlib"), dict):
            raw = (item.get("qlib") or {}).get("score")
        if raw is None:
            return None
        try:
            return float(raw)
        except Exception:
            return None

    def _market_regime(self, asof: str) -> Dict[str, Any]:
        rows = self._market_bars(asof)
        closes = [_safe_float(row.get("close"), 0.0) for row in rows if _safe_float(row.get("close"), 0.0) > 0]
        if len(closes) < 120:
            return {"state": "normal", "warnings": ["market_history_below_120"]}
        close = closes[-1]
        ma60 = sum(closes[-60:]) / 60.0
        ma120 = sum(closes[-120:]) / 120.0
        ret20 = close / closes[-21] - 1.0 if len(closes) > 20 and closes[-21] > 0 else 0.0
        ret60 = close / closes[-61] - 1.0 if len(closes) > 60 and closes[-61] > 0 else 0.0
        long_up = close > ma120 and ma60 > ma120 and ret60 > 0
        if long_up:
            state = "normal"
        elif (close < ma120 and ret20 < -0.08) or ret60 < -0.15:
            state = "severe"
        elif (close < ma60 and ma60 < ma120) or ret20 < -0.06 or ret60 < -0.10:
            state = "caution"
        else:
            state = "normal"
        return {"state": state, "close": round(close, 4), "ma60": round(ma60, 4), "ma120": round(ma120, 4), "ret20": round(ret20, 6), "ret60": round(ret60, 6), "warnings": []}

    def _market_bars(self, asof: str) -> List[Dict[str, Any]]:
        asof_date = self._parse_date(asof)
        for symbol in ("TWII", "II"):
            rows = self.kline_service.get_kline("TWStock", symbol, "1D", 500) or []
            bars = []
            for row in rows:
                row_date = self._bar_date(row)
                if row_date and asof_date and row_date <= asof_date and _safe_float(row.get("close"), 0.0) > 0:
                    bars.append(row)
            bars.sort(key=lambda row: self._bar_date(row) or date.min)
            if bars:
                return bars[-500:]
        return []

    @staticmethod
    def _code_from_research_step(*, action_code: str, decision_code: str) -> str:
        if action_code == "simulate_watch":
            return "new_watch"
        if action_code == "risk_review":
            return "risk_review"
        if action_code == "chasing_review":
            return "manual_review"
        if action_code in {"wait_pullback", "continue_observe"}:
            return "continue_watch"
        if action_code == "data_review":
            return "data_insufficient"
        return decision_code

    @staticmethod
    def _code_for_policy(*, policy: str, action_code: str, decision_code: str, risk: Dict[str, Any], weak_streak: int) -> str:
        risk_status = str((risk or {}).get("status") or "")
        metrics = (risk or {}).get("metrics") or {}
        distance_ma20 = metrics.get("distance_ma20_pct")
        try:
            distance_ma20_value = abs(float(distance_ma20)) if distance_ma20 is not None else None
        except Exception:
            distance_ma20_value = None

        if policy == "direct_rank":
            return decision_code
        if policy == "confirmed_exit":
            base = TWStockPortfolioReplayService._code_from_research_step(action_code=action_code, decision_code=decision_code)
            if base == "risk_review" and weak_streak < 3:
                return "continue_watch"
            return base
        if policy == "pullback_entry":
            if action_code == "simulate_watch" and risk_status == "reasonable" and (distance_ma20_value is None or distance_ma20_value <= 5.0):
                return "new_watch"
            if action_code == "risk_review":
                return "risk_review"
            if action_code == "data_review":
                return "data_insufficient"
            return "continue_watch"
        return TWStockPortfolioReplayService._code_from_research_step(action_code=action_code, decision_code=decision_code)

    def _execution_price(self, symbol: str, asof: str, mode: str) -> Optional[float]:
        if mode == "same_day_close":
            return self._close_on_or_before(symbol, asof)
        return self._next_close_after(symbol, asof)

    def _close_on_or_before(self, symbol: str, asof: str) -> Optional[float]:
        rows = self.kline_service.get_kline("TWStock", symbol, "1D", 500) or []
        asof_date = self._parse_date(asof)
        candidates = []
        for row in rows:
            row_date = self._bar_date(row)
            close = _safe_float(row.get("close"), 0.0)
            if row_date and asof_date and row_date <= asof_date and close > 0:
                candidates.append((row_date, close))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0])
        return candidates[-1][1]

    def _next_close_after(self, symbol: str, asof: str) -> Optional[float]:
        rows = self.kline_service.get_kline("TWStock", symbol, "1D", 500) or []
        asof_date = self._parse_date(asof)
        candidates = []
        for row in rows:
            row_date = self._bar_date(row)
            close = _safe_float(row.get("close"), 0.0)
            if row_date and asof_date and row_date > asof_date and close > 0:
                candidates.append((row_date, close))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0])
        return candidates[0][1]

    @staticmethod
    def _symbols_for_day(items: List[Dict[str, Any]], holdings: Dict[str, int]) -> List[str]:
        symbols = list(holdings)
        for item in items:
            symbol = str(item.get("symbol") or "")
            if symbol and symbol not in symbols:
                symbols.append(symbol)
        return symbols

    @staticmethod
    def _action(asof: str, symbol: str, action: str, quantity: int, price: Optional[float], reason: str) -> Dict[str, Any]:
        return {
            "date": asof,
            "symbol": symbol,
            "action": action,
            "quantity": int(quantity or 0),
            "price": round(float(price), 4) if price is not None else None,
            "reason": reason,
            "simulation_only": True,
        }

    @staticmethod
    def _comparison_warnings(comparison: Dict[str, Any]) -> List[str]:
        warnings: List[str] = []
        for payload in comparison.values():
            warnings.extend((payload.get("dataQuality") or {}).get("warnings") or [])
        return warnings

    @staticmethod
    def _normalize_config(raw: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "startDate": str(raw.get("startDate") or raw.get("start_date") or ""),
            "endDate": str(raw.get("endDate") or raw.get("end_date") or ""),
            "initialCash": max(1000.0, _safe_float(raw.get("initialCash") or raw.get("initial_cash") or 1000000.0, 1000000.0)),
            "bucket": str(raw.get("bucket") or "top30").strip().lower() if str(raw.get("bucket") or "top30").strip().lower() in {"top30", "top50", "all"} else "top30",
            "maxItems": max(1, min(int(raw.get("maxItems") or raw.get("max_items") or 30), 50)),
            "maxAddPerDay": max(0, min(int(raw.get("maxAddPerDay") or raw.get("max_add_per_day") or 1), 10)),
            "maxRiskActionPerDay": max(0, min(int(raw.get("maxRiskActionPerDay") or raw.get("max_risk_action_per_day") or 1), 10)),
            "maxHoldings": max(1, min(int(raw.get("maxHoldings") or raw.get("max_holdings") or 10), 50)),
            "lotSize": max(1, int(raw.get("lotSize") or raw.get("lot_size") or 10)),
            "feeRate": max(0.0, _safe_float(raw.get("feeRate") or raw.get("fee_rate") or 0.001425, 0.001425)),
            "sellTaxRate": max(0.0, _safe_float(raw.get("sellTaxRate") or raw.get("sell_tax_rate") or 0.003, 0.003)),
            "profile": str(raw.get("profile") or "balanced"),
            "variant": str(raw.get("variant") or "all") if str(raw.get("variant") or "all") in set(VARIANTS + ["all"]) else "all",
            "technicalStrategies": raw.get("technicalStrategies") or raw.get("technical_strategies") or ["ma", "rsi", "macd", "bollinger"],
            "signalRoot": TWStockPortfolioReplayService._normalize_signal_root(raw.get("signalRoot") or raw.get("signal_root")),
            "executionMode": TWStockPortfolioReplayService._normalize_execution_mode(raw.get("executionMode") or raw.get("execution_mode") or "next_trading_day_close"),
            "persist": False,
        }


    @staticmethod
    def _normalize_execution_mode(raw: Any) -> str:
        value = str(raw or "next_trading_day_close").strip().lower()
        return value if value in {"next_trading_day_close", "same_day_close"} else "next_trading_day_close"

    @staticmethod
    def _execution_mode_label(mode: str) -> str:
        if mode == "same_day_close":
            return "信号日收盘价（仅用于兼容旧结果）"
        return "下一交易日收盘价（避免同日未来函数）"

    @staticmethod
    def _normalize_signal_root(raw: Any) -> Optional[str]:
        text = str(raw or "").strip()
        return text or None

    @staticmethod
    def _parse_date(raw: str) -> Optional[date]:
        try:
            return date.fromisoformat(str(raw or "")[:10])
        except ValueError:
            return None

    @staticmethod
    def _bar_date(row: Dict[str, Any]) -> Optional[date]:
        raw = row.get("date") or row.get("trade_date") or row.get("latest_date")
        if raw:
            return TWStockPortfolioReplayService._parse_date(str(raw))
        ts = int(_safe_float(row.get("time"), 0.0))
        if ts <= 0:
            return None
        return datetime.fromtimestamp(ts, TAIPEI_TZ).date()
