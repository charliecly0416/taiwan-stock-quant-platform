"""Observation-only point-in-time comparison for TWStock research queues.

This service reads accepted qlib signal runs and local daily bars only. It does
not calculate performance metrics, build portfolios, create fills, or write any
business state.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from app.services.tw_stock_qlib_option_c import QlibOptionCSignalReader, research_only_trading_flags
from app.services.tw_stock_rank_tech_cross import SUMMARY_TEMPLATE, TWStockRankTechCrossService


VARIANTS = ["qlib_only", "qlib_plus_trend", "qlib_plus_trend_indicators"]
ZERO_COMPARISON = {
    "new_watch_count": 0,
    "continue_watch_count": 0,
    "risk_review_count": 0,
    "manual_review_count": 0,
    "observe_only_count": 0,
    "data_insufficient_count": 0,
    "item_count": 0,
}


class TWStockObservationReplayService:
    """Compare historical observation queues without performance metrics."""

    def __init__(
        self,
        *,
        qlib_reader: Optional[Any] = None,
        rank_tech_service: Optional[Any] = None,
    ) -> None:
        self.qlib_reader = qlib_reader or QlibOptionCSignalReader()
        self.rank_tech_service = rank_tech_service or TWStockRankTechCrossService(qlib_reader=self.qlib_reader)

    def compare(
        self,
        *,
        start_date: str,
        end_date: str,
        bucket: str = "top30",
        max_items: int = 30,
        technical_strategies: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        start = self._parse_date(start_date, fallback=date.today())
        end = self._parse_date(end_date, fallback=start)
        if end < start:
            start, end = end, start
        normalized_bucket = self._normalize_bucket(bucket)
        normalized_max = self._normalize_max_items(max_items, normalized_bucket)
        strategies = self._normalize_technical_strategies(technical_strategies)
        runs = self._accepted_runs_in_range(start=start, end=end)
        daily = [self._daily_compare(run, bucket=normalized_bucket, max_items=normalized_max, strategies=strategies) for run in runs]
        return {
            "ok": True,
            "status": "accepted",
            "simulation_only": True,
            "research_signal_not_order": True,
            "replay_type": "observation_only",
            "performance_metrics_included": False,
            "range": {"startDate": start.isoformat(), "endDate": end.isoformat(), "runCount": len(daily)},
            "bucket": normalized_bucket,
            "maxItems": normalized_max,
            "technicalStrategies": strategies,
            "comparison": self._comparison_summary(daily),
            "daily": daily,
            "dataQuality": {
                "point_in_time": True,
                "trend_point_in_time": True,
                "technical_point_in_time": True,
                "warnings": self._data_quality_warnings(daily),
            },
            "trading": research_only_trading_flags(),
        }

    def _daily_compare(self, run: Dict[str, Any], *, bucket: str, max_items: int, strategies: List[str]) -> Dict[str, Any]:
        run_id = str(run.get("run_id") or "")
        asof = self._parse_date(str(run.get("asof") or ""), fallback=date.today())
        detail = self.qlib_reader.run_detail(run_id, bucket=bucket, enrich_trend=False)
        warnings: List[str] = []
        if not detail.get("ok"):
            warnings.append("run_detail_blocked")
        rows = self._rows_for_bucket(detail, bucket)[:max_items]
        if not rows:
            warnings.append("empty_run_signals")
        variants = {
            "qlib_only": self._variant_from_rows(rows, asof=asof, mode="qlib_only", strategies=strategies),
            "qlib_plus_trend": self._variant_from_rows(rows, asof=asof, mode="qlib_plus_trend", strategies=strategies),
            "qlib_plus_trend_indicators": self._variant_from_rows(rows, asof=asof, mode="qlib_plus_trend_indicators", strategies=strategies),
        }
        return {"asof": asof.isoformat(), "run_id": run_id, "variants": variants, "warnings": warnings}

    def _variant_from_rows(self, rows: List[Dict[str, Any]], *, asof: date, mode: str, strategies: List[str]) -> Dict[str, Any]:
        items = []
        for row in rows:
            if mode == "qlib_only":
                item = self._qlib_only_item(row)
            else:
                trend = self.rank_tech_service._safe_trend_snapshot(str(row.get("symbol") or ""), trend_limit=120, as_of=asof)
                technical = self.rank_tech_service.technical_status_from_trend(trend)
                if mode == "qlib_plus_trend_indicators":
                    technical = self.rank_tech_service.technical_status_from_trend_and_indicators(
                        symbol=str(row.get("symbol") or ""),
                        trend=trend,
                        limit=120,
                        strategies=strategies,
                        as_of=asof,
                    )
                rank_tier = self.rank_tech_service.rank_tier(row.get("rank"))
                decision = self.rank_tech_service.decision_for(rank_tier=rank_tier, technical_status=str(technical.get("status") or "technical_data_insufficient"))
                item = {
                    "symbol": str(row.get("symbol") or ""),
                    "rank": row.get("rank"),
                    "rankTier": rank_tier,
                    "decision": decision,
                    "technical": technical,
                    "trend": {
                        "label": trend.get("trend_label"),
                        "score": trend.get("trend_score"),
                        "latest_date": trend.get("latest_date"),
                        "warnings": trend.get("quality_warnings") or [],
                    },
                }
            items.append(item)
        return {"summary": self._summary(items), "items": items}

    def _qlib_only_item(self, row: Dict[str, Any]) -> Dict[str, Any]:
        rank_tier = self.rank_tech_service.rank_tier(row.get("rank"))
        if rank_tier == "top10":
            decision = {"code": "new_watch", "label": "新增观察", "priority": "high", "reason": "仅按 qlib Top10 排名进入观察队列。"}
        elif rank_tier == "top30":
            decision = {"code": "continue_watch", "label": "继续观察", "priority": "medium", "reason": "仅按 qlib Top30 排名保留在观察队列。"}
        else:
            decision = {"code": "observe_only", "label": "仅观察", "priority": "low", "reason": "仅按 qlib 扩展排名低优先级观察。"}
        return {
            "symbol": str(row.get("symbol") or ""),
            "rank": row.get("rank"),
            "rankTier": rank_tier,
            "decision": decision,
            "technical": {"status": "not_used", "basis": "qlib_only", "strategies": [], "warnings": []},
            "trend": {"label": None, "score": None, "latest_date": None, "warnings": []},
        }

    def _accepted_runs_in_range(self, *, start: date, end: date) -> List[Dict[str, Any]]:
        payload = self.qlib_reader.list_runs(limit=100, status="accepted")
        runs = []
        for item in payload.get("items") or []:
            asof = self._parse_date(str(item.get("asof") or ""), fallback=None)
            if asof is not None and start <= asof <= end:
                runs.append(item)
        runs.sort(key=lambda item: str(item.get("asof") or ""))
        return runs

    @staticmethod
    def _rows_for_bucket(payload: Dict[str, Any], bucket: str) -> List[Dict[str, Any]]:
        if bucket in {"top30", "top50"}:
            return list(payload.get("signals") or [])
        rows = []
        seen = set()
        for row in list(payload.get("top30") or []) + list(payload.get("top50") or []):
            symbol = str(row.get("symbol") or "")
            if symbol and symbol not in seen:
                seen.add(symbol)
                rows.append(row)
        rows.sort(key=lambda item: int(item.get("rank") or 999999))
        return rows

    @staticmethod
    def _summary(items: List[Dict[str, Any]]) -> Dict[str, int]:
        counts = dict(SUMMARY_TEMPLATE)
        for item in items:
            code = str((item.get("decision") or {}).get("code") or "")
            if code in counts:
                counts[code] += 1
        counts["item_count"] = len(items)
        return counts

    @staticmethod
    def _comparison_summary(daily: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
        comparison = {variant: dict(ZERO_COMPARISON) for variant in VARIANTS}
        for day in daily:
            variants = day.get("variants") or {}
            for variant in VARIANTS:
                summary = (variants.get(variant) or {}).get("summary") or {}
                target = comparison[variant]
                for key in list(SUMMARY_TEMPLATE):
                    target[f"{key}_count"] += int(summary.get(key) or 0)
                target["item_count"] += int(summary.get("item_count") or 0)
        return comparison

    @staticmethod
    def _data_quality_warnings(daily: List[Dict[str, Any]]) -> List[str]:
        warnings = []
        if not daily:
            warnings.append("no_accepted_runs_in_range")
        for day in daily:
            for warning in day.get("warnings") or []:
                text = str(warning)
                if text and text not in warnings:
                    warnings.append(text)
            for variant in (day.get("variants") or {}).values():
                for item in variant.get("items") or []:
                    for warning in ((item.get("technical") or {}).get("warnings") or []):
                        text = str(warning)
                        if text and text not in warnings:
                            warnings.append(text)
        return warnings

    @staticmethod
    def _parse_date(raw: str, *, fallback: Optional[date]) -> Optional[date]:
        try:
            return date.fromisoformat(str(raw or "").strip()[:10])
        except ValueError:
            return fallback

    @staticmethod
    def _normalize_bucket(bucket: str) -> str:
        normalized = str(bucket or "top30").strip().lower()
        return normalized if normalized in {"top30", "top50", "all"} else "top30"

    @staticmethod
    def _normalize_max_items(max_items: int, bucket: str) -> int:
        default = 30 if bucket == "top30" else 50
        try:
            value = int(max_items or default)
        except Exception:
            value = default
        return max(1, min(value, 50))

    @staticmethod
    def _normalize_technical_strategies(strategies: Optional[List[str]]) -> List[str]:
        valid = {"ma", "rsi", "macd", "bollinger"}
        if not strategies:
            return ["ma", "rsi", "macd", "bollinger"]
        out = []
        for raw in strategies:
            item = str(raw or "").strip().lower()
            if item in valid and item not in out:
                out.append(item)
        return out or ["ma", "rsi", "macd", "bollinger"]
