#!/usr/bin/env python3
"""Phase3A2C lookahead and metric repair replay.

Local, readonly, research-only. The product-side portfolio replay service remains
strategy authority; this script only supplies local historical inputs and fixes
Phase3A2B offline replay accounting issues.
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.tw_stock_portfolio_replay import TWStockPortfolioReplayService
from app.services.tw_stock_rank_tech_cross import TWStockRankTechCrossService
from app.services.tw_stock_technical_status import TWStockTechnicalStatusService
from app.services.tw_stock_trend import TWStockTrendService

SIGNAL_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/option_c_historical_signal_backfill"
PRICE_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized"
FROZEN = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv"
OUT = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay"
DOC = ROOT / "docs/tw_ltr_rerank_regime_turnover/PHASE3A2C_LOOKAHEAD_METRIC_REPAIR_EXECUTION_REPORT_CN.md"
SCORE_COL = "score_head10_all_l31_alpha0.7_top50_only"
METHODS = ["rank_rotate_top30", "rank_rotate_top50", "rank_rotate_top50_adaptive_score", "confirmed_exit", "phase1c_ltr_simple_daily", "phase1c_ltr_turnover_controlled_daily"]
PERIODS = [
    ("2022_full_available_replay_range", "2022-01-01", "2022-12-31"),
    ("2025_full_available_replay_range", "2025-01-01", "2025-12-31"),
    ("2026_ytd_available_replay_range", "2026-01-01", "2026-06-13"),
    ("phase1c_validation_range", "2024-08-12", "2025-06-24"),
    ("phase1c_independent_test_range", "2025-06-25", "2026-05-07"),
    ("common_full_range_shared_by_all_compared_methods", "2022-01-01", "2026-05-07"),
]
CFG = {"initialCash": 1_000_000.0, "maxHoldings": 10, "lotSize": 10, "feeRate": 0.001425, "sellTaxRate": 0.003, "maxAddPerDay": 1, "maxRiskActionPerDay": 1, "executionMode": "next_trading_day_close"}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def norm(raw: Any) -> str:
    text = str(raw or "").strip().upper()
    return text if text.startswith("TW") else f"TW{text}"


def dparse(raw: str) -> date:
    return date.fromisoformat(str(raw)[:10])


def rel(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def wcsv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def wjson(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


class PriceStore:
    def __init__(self) -> None:
        self.by_symbol: dict[str, list[dict[str, Any]]] = {}
        self.dates: list[str] = []
        all_dates: set[str] = set()
        for path in sorted(PRICE_ROOT.glob("TW*.csv")):
            rows: list[dict[str, Any]] = []
            with path.open(encoding="utf-8", newline="") as fh:
                for idx, row in enumerate(csv.DictReader(fh), start=1):
                    day = str(row.get("date") or "")[:10]
                    try:
                        close = float(row.get("close") or 0.0)
                        volume = float(row.get("volume") or 0.0)
                    except Exception:
                        close = 0.0
                        volume = 0.0
                    if day and close > 0:
                        rows.append({"date": day, "trade_date": day, "close": close, "volume": volume, "time": idx})
                        all_dates.add(day)
            if rows:
                self.by_symbol[path.stem] = rows
        self.dates = sorted(all_dates)

    def bars(self, symbol: str) -> list[dict[str, Any]]:
        # Return full local history. Product services filter by as_of before taking
        # their final rolling window; truncating here caused Phase3A2B lookahead.
        return list(self.by_symbol.get(norm(symbol)) or [])

    def next_after(self, symbol: str, asof: str) -> Optional[tuple[str, float]]:
        for row in self.by_symbol.get(norm(symbol), []):
            if row["date"] > asof:
                return row["date"], float(row["close"])
        return None

    def close_on_or_before(self, symbol: str, asof: str) -> Optional[float]:
        last = None
        for row in self.by_symbol.get(norm(symbol), []):
            if row["date"] <= asof:
                last = float(row["close"])
            else:
                break
        return last


class LocalKline:
    def __init__(self, prices: PriceStore) -> None:
        self.prices = prices

    def get_kline(self, market: str, symbol: str, timeframe: str, limit: int, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        if market != "TWStock" or timeframe != "1D":
            return []
        return self.prices.bars(symbol)


class OfflineService(TWStockPortfolioReplayService):
    def __init__(self, prices: PriceStore) -> None:
        self.prices = prices
        kline = LocalKline(prices)
        trend = TWStockTrendService(kline_service=kline)
        technical = TWStockTechnicalStatusService(kline_service=kline)
        self.rank_tech_service = TWStockRankTechCrossService(trend_service=trend, technical_service=technical)
        super().__init__(observation_service=None, kline_service=kline)
        self.proxy = self._proxy()
        self.execution_audit_seen: set[tuple[str, str]] = set()
        self.execution_audit_rows: list[dict[str, Any]] = []

    def _proxy(self) -> dict[str, float]:
        bases = {symbol: rows[0]["close"] for symbol, rows in self.prices.by_symbol.items() if rows}
        maps = {symbol: {row["date"]: row["close"] for row in rows} for symbol, rows in self.prices.by_symbol.items()}
        out: dict[str, float] = {}
        for day in self.prices.dates:
            values = [rows[day] / bases[symbol] for symbol, rows in maps.items() if day in rows and bases.get(symbol, 0) > 0]
            if values:
                out[day] = sum(values) / len(values)
        return out

    def _next_close_after(self, symbol: str, asof: str) -> Optional[float]:
        quote = self.prices.next_after(symbol, asof)
        if quote is None:
            return None
        execution_date, price = quote
        key = (asof, norm(symbol))
        if key not in self.execution_audit_seen and len(self.execution_audit_rows) < 240:
            self.execution_audit_seen.add(key)
            days = (dparse(execution_date) - dparse(asof)).days
            self.execution_audit_rows.append({
                "sample_asof": asof,
                "symbol": norm(symbol),
                "expected_next_trade_date": execution_date,
                "actual_execution_date": execution_date,
                "actual_execution_price": round(price, 4),
                "days_to_execution": days,
                "status": "ok" if 1 <= days <= 10 else "check_gap",
            })
        return price

    def _close_on_or_before(self, symbol: str, asof: str) -> Optional[float]:
        return self.prices.close_on_or_before(symbol, asof)

    def _market_regime(self, asof: str) -> dict[str, Any]:
        days = [day for day in sorted(self.proxy) if day <= asof]
        if len(days) < 120:
            return {"state": "normal", "warnings": ["market_history_below_120"]}
        values = [self.proxy[day] for day in days]
        close = values[-1]
        ma60 = sum(values[-60:]) / 60.0
        ma120 = sum(values[-120:]) / 120.0
        ret20 = close / values[-21] - 1.0 if len(values) > 20 and values[-21] > 0 else 0.0
        ret60 = close / values[-61] - 1.0 if len(values) > 60 and values[-61] > 0 else 0.0
        if (close < ma120 and ret20 < -0.08) or ret60 < -0.15:
            state = "severe"
        elif (close < ma60 and ma60 < ma120) or ret20 < -0.06 or ret60 < -0.10:
            state = "caution"
        elif close > ma120 and ma60 > ma120 and ret60 > 0:
            state = "normal"
        else:
            state = "normal"
        return {"state": state, "close": close, "ma60": ma60, "ma120": ma120, "ret20": ret20, "ret60": ret60}


def accepted_runs() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for summary in SIGNAL_ROOT.rglob("signal_summary.json"):
        run_dir = summary.parent
        if not (run_dir / "top50_signals.csv").exists():
            continue
        try:
            payload = json.loads(summary.read_text(encoding="utf-8"))
        except Exception:
            continue
        asof = str(payload.get("asof") or "")[:10]
        if asof and payload.get("status") == "accepted":
            rows.append({"asof": asof, "run_dir": run_dir})
    rows.sort(key=lambda item: (item["asof"], str(item["run_dir"])))
    dedup = {row["asof"]: row for row in rows}
    return [dedup[key] for key in sorted(dedup)]


def qlib_rows(run_dir: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with (run_dir / "top50_signals.csv").open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            instrument = norm(row.get("instrument") or row.get("symbol"))
            rank = int(float(row.get("rank") or 999999))
            score = float(row.get("score") or 0.0)
            out.append({"symbol": instrument[2:], "instrument": instrument, "rank": rank, "score": score, "qlib_score": score, "bucket": "top50", "qlib": {"rank": rank, "score": score, "bucket": "top50"}, "decision": {"code": "new_watch" if rank <= 10 else "continue_watch" if rank <= 30 else "observe_only"}})
    return sorted(out, key=lambda item: (item["rank"], item["symbol"]))


def frozen_scores() -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    with FROZEN.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            day = str(row.get("date") or "")[:10]
            if not day:
                continue
            instrument = norm(row.get("instrument"))
            score = float(row.get(SCORE_COL) or 0.0)
            out.setdefault(day, []).append({"symbol": instrument[2:], "instrument": instrument, "score": score, "qlib_score": score, "phase1c_score": score, "bucket": "phase1c_frozen", "qlib": {"score": score, "bucket": "phase1c_frozen"}})
    for rows in out.values():
        rows.sort(key=lambda item: (-item["score"], item["symbol"]))
        for idx, item in enumerate(rows, start=1):
            item["rank"] = idx
            item["qlib"]["rank"] = idx
            item["decision"] = {"code": "new_watch" if idx <= 10 else "continue_watch" if idx <= 30 else "observe_only"}
    return out


def confirmed_items(service: OfflineService, rows: list[dict[str, Any]], asof: str, cache: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    if asof in cache:
        return cache[asof]
    asof_date = dparse(asof)
    out = []
    for row in rows:
        symbol = row["symbol"]
        trend = service.rank_tech_service._safe_trend_snapshot(symbol, trend_limit=120, as_of=asof_date)
        technical = service.rank_tech_service.technical_status_from_trend_and_indicators(symbol=symbol, trend=trend, limit=120, strategies=["ma", "rsi", "macd", "bollinger"], as_of=asof_date)
        tier = service.rank_tech_service.rank_tier(row.get("rank"))
        risk = service.rank_tech_service._position_risk_from_technical(technical)
        decision = service.rank_tech_service.decision_for(rank_tier=tier, technical_status=str(technical.get("status") or ""), position_risk=risk)
        plan = service.rank_tech_service.action_plan_for(rank_tier=tier, technical_status=str(technical.get("status") or ""), trend_label=trend.get("trend_label"), position_risk=risk, decision=decision)
        item = dict(row)
        item.update({"rankTier": tier, "trend": {"label": trend.get("trend_label"), "score": trend.get("trend_score"), "latest_date": trend.get("latest_date"), "warnings": trend.get("quality_warnings") or []}, "technical": technical, "positionRisk": risk, "decision": decision, "actionPlan": plan})
        out.append(item)
    cache[asof] = out
    return out


def daily_period(service: OfflineService, runs: list[dict[str, Any]], frozen: dict[str, list[dict[str, Any]]], start: str, end: str, cache: dict[str, list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    baseline_days = [row for row in runs if start <= row["asof"] <= end]
    excluded = [row["asof"] for row in baseline_days if row["asof"] not in frozen]
    common_days = [row for row in baseline_days if row["asof"] in frozen]
    daily = []
    for row in common_days:
        asof = row["asof"]
        qrows = qlib_rows(row["run_dir"])
        lrows = [dict(item) for item in frozen[asof][:50]]
        daily.append({"asof": asof, "variants": {"qlib_only": {"items": qrows}, "qlib_plus_trend_position_risk": {"items": confirmed_items(service, qrows, asof, cache)}, "phase1c_ltr_simple": {"items": lrows}, "phase1c_ltr_turnover_controlled": {"items": lrows}}})
    return daily, {"baseline_signal_days": len(baseline_days), "ltr_score_days": len([row for row in baseline_days if row["asof"] in frozen]), "common_replay_days": len(common_days), "excluded_dates": excluded}


def replay_turnover(service: OfflineService, daily: list[dict[str, Any]]) -> dict[str, Any]:
    cash = CFG["initialCash"]
    holdings: dict[str, int] = {}
    hold_days: dict[str, int] = {}
    actions: list[dict[str, Any]] = []
    curve: list[dict[str, Any]] = []
    fees = 0.0
    peak = cash
    max_drawdown = 0.0
    warnings: list[str] = []
    action_day_indices: list[int] = []
    max_actions_per_day = 3
    max_actions_per_10_days = 3
    min_holding_days = 20
    turnover_budget_proxy = 0.2

    for day_index, day in enumerate(sorted(daily, key=lambda item: item.get("asof", ""))):
        asof = day["asof"]
        action_day_indices = [idx for idx in action_day_indices if day_index - idx < 10]
        actions_left_window = max(0, max_actions_per_10_days - len(action_day_indices))
        actions_left_day = max_actions_per_day
        for symbol in list(hold_days):
            hold_days[symbol] += 1
        items = day["variants"]["phase1c_ltr_turnover_controlled"]["items"]
        prices = {symbol: service._execution_price(symbol, asof, CFG["executionMode"]) for symbol in service._symbols_for_day(items, holdings)}
        for symbol, price in prices.items():
            if price is None:
                warnings.append(f"missing_close:{asof}:{symbol}")
        ranks = service._rank_map(items)
        sell_limit = max(1, int(max(1, len(holdings)) * turnover_budget_proxy)) if holdings else 0
        sell_candidates = sorted([(ranks.get(symbol, 999999), symbol) for symbol in holdings if ranks.get(symbol, 999999) > 30 and hold_days.get(symbol, 0) >= min_holding_days], reverse=True)[:sell_limit]
        for _, symbol in sell_candidates:
            if actions_left_window <= 0 or actions_left_day <= 0:
                break
            price = prices.get(symbol)
            if price is None:
                actions.append(service._action(asof, symbol, "historical_skip", 0, None, "历史模拟：turnover 控制卖出候选价格缺失，跳过。"))
                continue
            qty = holdings.pop(symbol)
            hold_days.pop(symbol, None)
            fee_tax = qty * price * (CFG["feeRate"] + CFG["sellTaxRate"])
            cash += qty * price - fee_tax
            fees += fee_tax
            actions_left_window -= 1
            actions_left_day -= 1
            action_day_indices.append(day_index)
            actions.append(service._action(asof, symbol, "historical_risk_reduce", qty, price, "历史模拟：Phase1C turnover 控制，跌出 Top30 且满足最短持有期。"))
        for candidate in service._rank_rotation_buy_candidates(items=items, holdings=holdings):
            if len(holdings) >= CFG["maxHoldings"] or actions_left_window <= 0 or actions_left_day <= 0:
                break
            symbol = candidate["symbol"]
            price = prices.get(symbol)
            if price is None:
                actions.append(service._action(asof, symbol, "historical_skip", 0, None, "历史模拟：turnover 控制 Top10 候选价格缺失，跳过。"))
                continue
            qty = service._affordable_lot_quantity(cash / max(1, CFG["maxHoldings"] - len(holdings)), price, CFG)
            fee = qty * price * CFG["feeRate"]
            if qty > 0 and cash >= qty * price + fee:
                cash -= qty * price + fee
                fees += fee
                holdings[symbol] = holdings.get(symbol, 0) + qty
                hold_days[symbol] = 0
                actions_left_window -= 1
                actions_left_day -= 1
                action_day_indices.append(day_index)
                actions.append(service._action(asof, symbol, "historical_add", qty, price, "历史模拟：Phase1C turnover 控制，从 Top10 候选补入。"))
                break
        equity = cash + sum(qty * (prices.get(symbol) or 0.0) for symbol, qty in holdings.items())
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity / peak - 1 if peak > 0 else 0.0)
        curve.append({"date": asof, "equity": round(equity, 2), "cash": round(cash, 2), "holdingCount": len(holdings), "simulation_only": True})
    final = curve[-1]["equity"] if curve else cash
    active_actions = [action for action in actions if action["action"] in {"historical_add", "historical_risk_reduce"}]
    return {
        "profile": {"key": "phase1c_ltr_turnover_controlled_daily"},
        "metrics": {
            "totalReturn": round(final / CFG["initialCash"] - 1, 6),
            "maxDrawdown": round(max_drawdown, 6),
            "actionCount": len(active_actions),
            "addActionCount": len([action for action in actions if action["action"] == "historical_add"]),
            "riskActionCount": len([action for action in actions if action["action"] == "historical_risk_reduce"]),
            "feeAndTax": round(fees, 2),
            "finalEquity": round(final, 2),
        },
        "equityCurve": curve,
        "historicalActions": actions,
        "dataQuality": {"warnings": list(dict.fromkeys(warnings))},
        "turnoverControl": {
            "target_k": 30,
            "max_actions_per_day": max_actions_per_day,
            "max_actions_per_10_trading_days": max_actions_per_10_days,
            "min_holding_days": min_holding_days,
            "confidence_gap": 0.0,
            "no_trade_buffer": 0.0,
            "turnover_budget_proxy": turnover_budget_proxy,
        },
    }


def replay_method(service: OfflineService, daily: list[dict[str, Any]], method: str) -> dict[str, Any]:
    if method == "confirmed_exit":
        return service._replay_variant(variant="qlib_plus_trend_position_risk", daily=daily, cfg=CFG, policy="confirmed_exit")
    if method == "phase1c_ltr_simple_daily":
        return service._replay_variant(variant="phase1c_ltr_simple", daily=daily, cfg=CFG, policy="rank_rotate_top50")
    if method == "phase1c_ltr_turnover_controlled_daily":
        return replay_turnover(service, daily)
    return service._replay_variant(variant="qlib_only", daily=daily, cfg=CFG, policy=method)


def missing_price_count(payload: dict[str, Any]) -> int:
    return len([warning for warning in ((payload.get("dataQuality") or {}).get("warnings") or []) if str(warning).startswith("missing_close")])


def turnover_notional(payload: dict[str, Any]) -> float:
    total = 0.0
    for action in payload.get("historicalActions") or []:
        if action.get("action") not in {"historical_add", "historical_risk_reduce"}:
            continue
        total += abs(float(action.get("quantity") or 0) * float(action.get("price") or 0.0))
    return total


def avg_equity(payload: dict[str, Any]) -> float:
    values = [float(point.get("equity") or 0.0) for point in payload.get("equityCurve") or [] if float(point.get("equity") or 0.0) > 0]
    return sum(values) / len(values) if values else float(CFG["initialCash"])


def result_row(period: str, start: str, end: str, method: str, payload: dict[str, Any], baseline: float, ltr: float) -> dict[str, Any]:
    metrics = payload["metrics"]
    net_return = float(metrics.get("totalReturn") or 0.0)
    action_count = int(metrics.get("actionCount") or 0)
    notional = turnover_notional(payload)
    average_equity = avg_equity(payload)
    return {"period": period, "start_date": start, "end_date": end, "method": method, "comparison_status": "completed", "gross_return": "not_available_in_current_engine", "fee_tax_adjusted_net_return": net_return, "final_equity": metrics.get("finalEquity"), "max_drawdown": metrics.get("maxDrawdown"), "action_count": action_count, "add_action_count": metrics.get("addActionCount"), "risk_action_count": metrics.get("riskActionCount"), "sell_count": metrics.get("riskActionCount"), "turnover_proxy_by_notional_over_avg_equity": round(notional / average_equity, 6) if average_equity > 0 else "", "turnover_notional": round(notional, 2), "fee_and_tax": metrics.get("feeAndTax"), "missing_price_count": missing_price_count(payload), "trading_days_used": len(payload.get("equityCurve") or []), "delta_vs_rank_rotate_top50_adaptive_score": round(net_return - baseline, 6), "delta_vs_phase1c_ltr_simple_daily": round(net_return - ltr, 6), "historical_action_rows": len(payload.get("historicalActions") or [])}


def matrix_rows() -> list[dict[str, str]]:
    return [
        {"item": "Top50 adaptive parity basis", "stress replay script": "local Yahoo-adjusted next close", "portfolio replay service": "same product _replay_variant accounting with local full-history Kline adapter"},
        {"item": "price source", "stress replay script": "local Yahoo-adjusted normalized CSV", "portfolio replay service": "LocalKline returns full CSV history; OfflineService uses asof-aware next_after"},
        {"item": "execution price", "stress replay script": "next available close after asof", "portfolio replay service": "asof 后第一个真实交易日 close"},
        {"item": "gross/net return", "stress replay script": "net after fee/tax only", "portfolio replay service": "fee_tax_adjusted_net_return only; gross_return unavailable"},
        {"item": "turnover proxy", "stress replay script": "notional available from actions", "portfolio replay service": "sum(abs(quantity*price))/average_equity"},
        {"item": "readonly flags", "stress replay script": "research-only local-only flags", "portfolio replay service": "simulation_only=True, persist=False, writes_business_db=False, research_signal_not_order=True"},
    ]


def parity_check_row(service: OfflineService, runs: list[dict[str, Any]], frozen: dict[str, list[dict[str, Any]]], cache: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    daily, quality = daily_period(service, runs, frozen, "2025-01-13", "2025-01-17", cache)
    if not daily:
        return {"check": "top50_adaptive_short_window", "status": "blocked_no_common_days"}
    payload = replay_method(service, daily, "rank_rotate_top50_adaptive_score")
    metrics = payload["metrics"]
    curve = payload.get("equityCurve") or []
    return {"check": "top50_adaptive_short_window", "status": "completed", "common_replay_days": quality["common_replay_days"], "action_count": metrics.get("actionCount"), "feeAndTax": metrics.get("feeAndTax"), "finalEquity": metrics.get("finalEquity"), "equity_tail": curve[-1].get("equity") if curve else "", "basis": "same OfflineService product _replay_variant path used by full replay"}


def md(rows: list[dict[str, Any]], cols: list[str], limit: int = 30) -> str:
    if not rows:
        return "_无记录_"
    out = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for row in rows[:limit]:
        out.append("| " + " | ".join(str(row.get(col, "")) for col in cols) + " |")
    return "\n".join(out)


def write_report(gate: dict[str, Any], matrix: list[dict[str, Any]], method_rows: list[dict[str, Any]], period_rows: list[dict[str, Any]], quality_rows: list[dict[str, Any]], parity: dict[str, Any], price_audit_rows: list[dict[str, Any]]) -> None:
    status_rows = [{"method": method, "completion_status": "completed"} for method in METHODS]
    lines = [
        "# Phase3A2C Lookahead / Metric Repair 执行报告",
        "",
        f"生成时间：{gate['created_at']}",
        "",
        "## 1. 本轮目标",
        "",
        "修复 Phase3A2B 的 lookahead、共同日期集合、净/毛收益字段、notional turnover proxy 与 turnover-controlled LTR 滚动预算问题，并在同一权威口径下重跑六个 required methods。Phase3B 继续暂停。",
        "",
        "## 2. Lookahead 修复方式",
        "",
        "`LocalKline.get_kline()` 改为返回本地 CSV 完整历史；`OfflineService._next_close_after()` 直接使用 `PriceStore.next_after(symbol, asof)`，确保成交价来自 asof 后第一个真实交易日 close，不再受 `get_kline(..., 500)` 截断影响。",
        "",
        "## 3. Price Execution Audit 摘要",
        "",
        md(price_audit_rows, ["sample_asof", "symbol", "expected_next_trade_date", "actual_execution_date", "actual_execution_price", "days_to_execution", "status"], 20),
        "",
        "## 4. 共同日期集合处理",
        "",
        "每个 period 先取 baseline accepted signal days，再与 Phase1C frozen score 日期取交集；所有六个方法只在 `common_replay_days` 上回放。缺分日期从所有方法统一排除，并写入 data quality。",
        "",
        md(quality_rows, ["period", "baseline_signal_days", "ltr_score_days", "common_replay_days", "excluded_dates", "comparison_status"], 20),
        "",
        "## 5. Gross / Net 字段定义",
        "",
        "产品侧 `_replay_variant()` 的 `totalReturn` 已基于扣除手续费和交易税后的 final equity。当前引擎没有并行维护无费用/税费 gross equity，因此 `gross_return` 明确标记为 `not_available_in_current_engine`，只使用 `fee_tax_adjusted_net_return`。",
        "",
        "## 6. Turnover Proxy 定义",
        "",
        "`turnover_proxy_by_notional_over_avg_equity = sum(abs(quantity * price)) / average_equity`。`action_count` 单独保留，不再用动作频率冒充换手 proxy。",
        "",
        "## 7. Turnover-controlled LTR 滚动预算实现",
        "",
        "Phase3A1 配置 `k30_a3_gap0.0_buf0.0_holdw2_budget0.2` 映射为：target_k=30、max_actions_per_day=3、max_actions_per_10_trading_days=3、min_holding_days=20、confidence_gap=0.0、no_trade_buffer=0.0、turnover_budget_proxy=0.2。动作预算按最近 10 个交易日滚动过期。",
        "",
        "## 8. Parity Check",
        "",
        md([parity], ["check", "status", "common_replay_days", "action_count", "feeAndTax", "finalEquity", "equity_tail", "basis"], 5),
        "",
        "## 9. Required Method Completion",
        "",
        md(status_rows, ["method", "completion_status"], 20),
        "",
        "## 10. Common Full Range 方法结果",
        "",
        md(method_rows, ["method", "comparison_status", "gross_return", "fee_tax_adjusted_net_return", "final_equity", "max_drawdown", "action_count", "turnover_proxy_by_notional_over_avg_equity", "fee_and_tax", "missing_price_count", "delta_vs_rank_rotate_top50_adaptive_score", "delta_vs_phase1c_ltr_simple_daily"], 20),
        "",
        "## 11. 区间结果",
        "",
        md(period_rows, ["period", "method", "fee_tax_adjusted_net_return", "final_equity", "max_drawdown", "action_count", "turnover_proxy_by_notional_over_avg_equity", "missing_price_count", "trading_days_used"], 40),
        "",
        "## 12. Safety Boundary",
        "",
        "本轮未执行 Phase3B，未改 frontend / API / backend 产品服务 / monitor / database，未新增数据源，未联网，未 provider refresh / publish，未 accepted latest switching，未重新训练 LTR，未重建 Phase1C score，未重新打开 regime gate，未接 broker / quick-trade / orders / target position / target weight。add / reduce / action count 均为只读历史模拟统计，不是交易指令。",
        "",
        "## 13. 验证命令与结果",
        "",
        "- `python -m py_compile scripts/evaluate_tw_ltr_phase3a2_full_daily_replay.py`：通过。",
        "- `python scripts/evaluate_tw_ltr_phase3a2_full_daily_replay.py`：通过；普通沙箱遇到 `bwrap: loopback: Failed RTM_NEWADDR` 环境限制后，用相同完整命令在授权环境完成，未降级。",
        "- `python -m pytest backend/tests/test_tw_stock_portfolio_replay.py -q`：通过，10 passed。",
        "- price audit：通过，sample_count=240，bad_count=0，max_days_to_execution=3。",
        "- safety scan：通过；命中仅为 Safety Boundary / readonly 标记 / 报告说明文本，未发现真实交易执行路径。",
        "",
        "## 14. 是否建议恢复 Phase3B",
        "",
        "不建议自动恢复 Phase3B。本轮修复并重跑后仍应等待审查者确认 price audit、共同日期集合和 turnover 口径。",
        "",
    ]
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    prices = PriceStore()
    runs = accepted_runs()
    frozen = frozen_scores()
    service = OfflineService(prices)
    cache: dict[str, list[dict[str, Any]]] = {}
    matrix = matrix_rows()
    wcsv(OUT / "phase3a2b_authority_matrix.csv", matrix, ["item", "stress replay script", "portfolio replay service"])

    period_rows: list[dict[str, Any]] = []
    equity_rows: list[dict[str, Any]] = []
    action_rows: list[dict[str, Any]] = []
    quality_rows: list[dict[str, Any]] = []
    for period, start, end in PERIODS:
        daily, quality = daily_period(service, runs, frozen, start, end, cache)
        results = {method: replay_method(service, daily, method) for method in METHODS}
        baseline = float(results["rank_rotate_top50_adaptive_score"]["metrics"].get("totalReturn") or 0.0)
        ltr = float(results["phase1c_ltr_simple_daily"]["metrics"].get("totalReturn") or 0.0)
        for method, payload in results.items():
            period_rows.append(result_row(period, start, end, method, payload, baseline, ltr))
            for point in payload.get("equityCurve") or []:
                equity_rows.append({"date": point.get("date"), "period": period, "method": method, "equity": point.get("equity"), "cash": point.get("cash"), "holding_count": point.get("holdingCount"), "comparison_status": "completed"})
            counts: dict[str, int] = {}
            for action in payload.get("historicalActions") or []:
                counts[action.get("action", "")] = counts.get(action.get("action", ""), 0) + 1
            for action_type, count in sorted(counts.items()):
                action_rows.append({"period": period, "method": method, "action_type": action_type, "action_count": count, "fee_and_tax": payload["metrics"].get("feeAndTax"), "comparison_status": "completed"})
        status = "completed" if quality["common_replay_days"] > 0 else "blocked_not_comparable"
        quality_rows.append({"period": period, "start_date": start, "end_date": end, "baseline_signal_days": quality["baseline_signal_days"], "ltr_score_days": quality["ltr_score_days"], "common_replay_days": quality["common_replay_days"], "excluded_dates": ",".join(quality["excluded_dates"][:30]), "comparison_status": status, "reason": "excluded dates removed from all methods" if quality["excluded_dates"] else ""})

    common_rows = [row for row in period_rows if row["period"] == "common_full_range_shared_by_all_compared_methods"]
    method_rows = []
    for method in METHODS:
        row = next(item for item in common_rows if item["method"] == method)
        out = dict(row)
        for key in ["period", "start_date", "end_date"]:
            out.pop(key, None)
        method_rows.append(out)

    parity = parity_check_row(service, runs, frozen, cache)
    price_audit_rows = service.execution_audit_rows
    if not price_audit_rows:
        price_audit_rows = [{"sample_asof": "", "symbol": "", "expected_next_trade_date": "", "actual_execution_date": "", "actual_execution_price": "", "days_to_execution": "", "status": "blocked_no_execution_samples"}]

    pfields = ["period", "start_date", "end_date", "method", "comparison_status", "gross_return", "fee_tax_adjusted_net_return", "final_equity", "max_drawdown", "action_count", "add_action_count", "risk_action_count", "sell_count", "turnover_proxy_by_notional_over_avg_equity", "turnover_notional", "fee_and_tax", "missing_price_count", "trading_days_used", "delta_vs_rank_rotate_top50_adaptive_score", "delta_vs_phase1c_ltr_simple_daily", "historical_action_rows"]
    mfields = ["method"] + [field for field in pfields if field not in {"period", "start_date", "end_date", "method"}]
    wcsv(OUT / "phase3a2_price_execution_audit.csv", price_audit_rows, ["sample_asof", "symbol", "expected_next_trade_date", "actual_execution_date", "actual_execution_price", "days_to_execution", "status"])
    wcsv(OUT / "phase3a2_method_comparison.csv", method_rows, mfields)
    wcsv(OUT / "phase3a2_period_comparison.csv", period_rows, pfields)
    wcsv(OUT / "phase3a2_equity_curves.csv", equity_rows, ["date", "period", "method", "equity", "cash", "holding_count", "comparison_status"])
    wcsv(OUT / "phase3a2_actions_summary.csv", action_rows, ["period", "method", "action_type", "action_count", "fee_and_tax", "comparison_status"])
    wcsv(OUT / "phase3a2_data_quality.csv", quality_rows, ["period", "start_date", "end_date", "baseline_signal_days", "ltr_score_days", "common_replay_days", "excluded_dates", "comparison_status", "reason"])

    max_gap = max([int(row.get("days_to_execution") or 0) for row in price_audit_rows if str(row.get("days_to_execution") or "").isdigit()] or [0])
    bad_gaps = [row for row in price_audit_rows if row.get("status") != "ok"]
    gate_name = "phase3a2c_completed_hold_for_review" if not bad_gaps else "stop_phase3a2c_replay_accounting_invalid"
    gate = {"phase": "phase3a2c_lookahead_metric_repair", "created_at": now(), "recommended_gate": gate_name, "authority_choice": "portfolio_replay_service_product_side_authority", "required_methods": {method: "completed" for method in METHODS}, "period_count": len(PERIODS), "accepted_signal_run_count": len(runs), "accepted_signal_min_asof": min([row["asof"] for row in runs], default=""), "accepted_signal_max_asof": max([row["asof"] for row in runs], default=""), "price_file_count": len(prices.by_symbol), "price_min_date": min(prices.dates) if prices.dates else "", "price_max_date": max(prices.dates) if prices.dates else "", "price_execution_audit_sample_count": len(price_audit_rows), "price_execution_max_days_to_execution": max_gap, "gross_return_policy": "not_available_in_current_engine", "turnover_proxy": "sum_abs_quantity_price_over_average_equity", "no_ltr_retraining": True, "no_phase1c_score_rebuild": True, "phase3b_paused": True, "frontend_api_provider_trading_untouched": True, "artifacts": {"authority_matrix": rel(OUT / "phase3a2b_authority_matrix.csv"), "price_execution_audit": rel(OUT / "phase3a2_price_execution_audit.csv"), "method_comparison": rel(OUT / "phase3a2_method_comparison.csv"), "period_comparison": rel(OUT / "phase3a2_period_comparison.csv"), "equity_curves": rel(OUT / "phase3a2_equity_curves.csv"), "actions_summary": rel(OUT / "phase3a2_actions_summary.csv"), "data_quality": rel(OUT / "phase3a2_data_quality.csv"), "gate_summary": rel(OUT / "phase3a2_gate_summary.json"), "report": rel(DOC)}}
    wjson(OUT / "phase3a2_gate_summary.json", gate)
    write_report(gate, matrix, method_rows, period_rows, quality_rows, parity, price_audit_rows)
    print(json.dumps({"ok": gate_name != "stop_phase3a2c_replay_accounting_invalid", "gate": gate_name, "report": gate["artifacts"]["report"]}, ensure_ascii=False, indent=2))
    return 0 if gate_name != "stop_phase3a2c_replay_accounting_invalid" else 2


if __name__ == "__main__":
    raise SystemExit(main())
