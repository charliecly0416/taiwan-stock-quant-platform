"""In-memory TWStock portfolio rule replay for research-only comparison."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from math import floor
from typing import Any, Dict, List, Optional

from app.services.kline import KlineService
from app.services.tw_stock_observation_replay import TWStockObservationReplayService, VARIANTS
from app.services.tw_stock_qlib_option_c import research_only_trading_flags


TAIPEI_TZ = timezone(timedelta(hours=8))


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
        )
        comparison = {}
        requested = VARIANTS if cfg["variant"] == "all" else [cfg["variant"]]
        for variant in requested:
            comparison[variant] = self._replay_variant(variant=variant, daily=observation.get("daily") or [], cfg=cfg)
        return {
            "ok": True,
            "status": "accepted",
            "simulation_only": True,
            "research_signal_not_order": True,
            "replay_type": "portfolio_rule_historical_simulation",
            "persist": False,
            "writes_business_db": False,
            "config": cfg,
            "comparison": comparison,
            "dataQuality": {
                "point_in_time": True,
                "warnings": list(dict.fromkeys(list((observation.get("dataQuality") or {}).get("warnings") or []) + self._comparison_warnings(comparison))),
            },
            "trading": research_only_trading_flags(),
        }

    def _replay_variant(self, *, variant: str, daily: List[Dict[str, Any]], cfg: Dict[str, Any]) -> Dict[str, Any]:
        cash = float(cfg["initialCash"])
        holdings: Dict[str, int] = {}
        curve = []
        actions = []
        fees = 0.0
        warnings: List[str] = []
        peak = cash
        max_drawdown = 0.0
        for day in sorted(daily, key=lambda item: str(item.get("asof") or "")):
            asof = str(day.get("asof") or "")
            items = ((day.get("variants") or {}).get(variant) or {}).get("items") or []
            add_used = 0
            risk_used = 0
            prices = {symbol: self._close_on_or_before(symbol, asof) for symbol in self._symbols_for_day(items, holdings)}
            for symbol, price in prices.items():
                if price is None:
                    warnings.append(f"missing_close:{asof}:{symbol}")
            for item in items:
                symbol = str(item.get("symbol") or "")
                code = str((item.get("decision") or {}).get("code") or "")
                price = prices.get(symbol)
                if price is None:
                    actions.append(self._action(asof, symbol, "historical_skip", 0, None, "历史模拟：价格缺失，跳过。"))
                    continue
                if code == "new_watch" and symbol not in holdings and add_used < cfg["maxAddPerDay"] and len(holdings) < cfg["maxHoldings"]:
                    remaining_slots = max(1, cfg["maxHoldings"] - len(holdings))
                    per_cash = cash / remaining_slots
                    qty = floor(per_cash / price / cfg["lotSize"]) * cfg["lotSize"]
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
            "dataQuality": {"warnings": list(dict.fromkeys(warnings))},
        }

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
            "persist": False,
        }

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
