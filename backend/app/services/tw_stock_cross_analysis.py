"""Read-only cross analysis for qlib Option C signals and TWStock trends."""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from app.services.tw_stock_qlib_option_c import (
    QlibOptionCSignalError,
    QlibOptionCSignalReader,
    research_only_trading_flags,
)
from app.services.tw_stock_trend import TWStockTrendService


SERIOUS_QUALITY_WARNINGS = {
    "no_daily_bars",
    "data_source_unavailable",
    "stale_daily_bar",
    "latest_bar_in_future",
    "invalid_twstock_symbol",
}
POSITIVE_TRENDS = {"uptrend", "rebound"}
NEGATIVE_TRENDS = {"downtrend", "pullback"}


def blocked_cross_payload(status: str, message: str, *, warnings: Optional[List[str]] = None) -> Dict[str, Any]:
    basis = TWStockCrossAnalysisService.basis_contract()
    return {
        "ok": False,
        "status": status,
        "message": message,
        "qlib": None,
        "items": [],
        "summary": {"category_counts": {}},
        "freshness": {
            "qlib": {"status": status, "asof": None, "run_id": None, "target_horizon": None},
            "quantdinger": {"latest_date_min": None, "latest_date_max": None, "source": basis["quantdinger_source"]},
            "date_gap_days_min": None,
            "date_gap_days_max": None,
            "status": "blocked",
            "warnings": warnings or [message],
        },
        "basis": basis,
        "warnings": warnings or [],
        "trading": research_only_trading_flags(),
    }


class TWStockCrossAnalysisService:
    """Combine accepted qlib rankings with read-only raw trend snapshots."""

    def __init__(self, *, qlib_reader: Optional[Any] = None, trend_service: Optional[Any] = None) -> None:
        self.qlib_reader = qlib_reader or QlibOptionCSignalReader()
        self.trend_service = trend_service or TWStockTrendService()

    def latest(
        self,
        *,
        bucket: str = "top30",
        limit: int = 120,
        include_raw_trend: bool = False,
        max_items: Optional[int] = None,
    ) -> Dict[str, Any]:
        normalized_bucket = self._normalize_bucket(bucket)
        normalized_limit = self._normalize_limit(limit)
        normalized_max = self._normalize_max_items(max_items, normalized_bucket)
        try:
            qlib_payload = self.qlib_reader.latest(bucket=normalized_bucket, enrich_trend=False)
        except QlibOptionCSignalError as exc:
            return blocked_cross_payload(exc.status, exc.message, warnings=exc.warnings)

        rows = self._rows_for_bucket(qlib_payload, normalized_bucket)[:normalized_max]
        items = [
            self._item_from_signal(row, qlib_payload=qlib_payload, trend_limit=normalized_limit, include_raw_trend=include_raw_trend)
            for row in rows
        ]
        return {
            "ok": True,
            "status": "accepted",
            "bucket": normalized_bucket,
            "limit": normalized_limit,
            "maxItems": normalized_max,
            "includeRawTrend": include_raw_trend,
            "qlib": self._qlib_summary(qlib_payload),
            "items": items,
            "summary": {"category_counts": self._category_counts(items), "item_count": len(items)},
            "freshness": self._freshness_summary(qlib_payload=qlib_payload, items=items),
            "basis": self.basis_contract(),
            "trading": research_only_trading_flags(),
        }

    def symbol_detail(self, *, symbol: str, limit: int = 120, include_raw_trend: bool = True) -> Dict[str, Any]:
        normalized_limit = self._normalize_limit(limit)
        clean_symbol = self._normalize_symbol(symbol)
        if not clean_symbol:
            trend = self._safe_trend_snapshot(str(symbol or ""), trend_limit=normalized_limit)
            return {
                "ok": False,
                "status": "invalid_twstock_symbol",
                "symbol": str(symbol or "").strip(),
                "qlib": None,
                "item": None,
                "trend": self._trend_summary(trend),
                "rawTrend": trend.get("raw") if include_raw_trend else None,
                "trading": research_only_trading_flags(),
            }

        try:
            qlib_payload = self.qlib_reader.latest(bucket="all", enrich_trend=False)
        except QlibOptionCSignalError as exc:
            return blocked_cross_payload(exc.status, exc.message, warnings=exc.warnings)

        rows = self._rows_for_bucket(qlib_payload, "all")
        match = next((row for row in rows if str(row.get("symbol") or "") == clean_symbol), None)
        if not match:
            trend = self._safe_trend_snapshot(clean_symbol, trend_limit=normalized_limit)
            return {
                "ok": False,
                "status": "not_in_latest_qlib_top50",
                "symbol": clean_symbol,
                "qlib": self._qlib_summary(qlib_payload),
                "item": None,
                "trend": self._trend_summary(trend),
                "rawTrend": trend.get("raw") if include_raw_trend else None,
                "trading": research_only_trading_flags(),
            }

        return {
            "ok": True,
            "status": "accepted",
            "symbol": clean_symbol,
            "qlib": self._qlib_summary(qlib_payload),
            "item": self._item_from_signal(match, qlib_payload=qlib_payload, trend_limit=normalized_limit, include_raw_trend=include_raw_trend),
            "trading": research_only_trading_flags(),
        }

    def _item_from_signal(self, row: Dict[str, Any], *, qlib_payload: Dict[str, Any], trend_limit: int, include_raw_trend: bool) -> Dict[str, Any]:
        symbol = str(row.get("symbol") or "")
        trend = self._safe_trend_snapshot(symbol, trend_limit=trend_limit)
        item = {
            "symbol": symbol,
            "instrument": row.get("instrument"),
            "name": row.get("name") or row.get("symbol_name") or "",
            "qlib": {"bucket": row.get("bucket"), "rank": row.get("rank"), "score": row.get("qlib_score")},
            "quantdinger": self._trend_summary(trend),
            "data_basis": self._data_basis(qlib_payload=qlib_payload, trend=trend),
            "cross": self._classify(row=row, trend=trend),
        }
        if include_raw_trend:
            item["rawTrend"] = trend.get("raw")
        return item

    @staticmethod
    def _normalize_bucket(bucket: str) -> str:
        normalized = str(bucket or "top30").strip().lower()
        return normalized if normalized in {"top30", "top50", "all"} else "top30"

    @staticmethod
    def _normalize_limit(limit: int) -> int:
        try:
            value = int(limit or 120)
        except Exception:
            value = 120
        return max(20, min(value, 500))

    @staticmethod
    def _normalize_max_items(max_items: Optional[int], bucket: str) -> int:
        default = 30 if bucket == "top30" else 50
        if max_items is None:
            return default
        try:
            value = int(max_items)
        except Exception:
            value = default
        return max(1, min(value, 50))

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        clean = str(symbol or "").strip().upper()
        if clean.startswith("TW"):
            clean = clean[2:]
        if "." in clean:
            clean = clean.split(".", 1)[0]
        return clean if clean.isdigit() else ""

    @staticmethod
    def _rows_for_bucket(payload: Dict[str, Any], bucket: str) -> List[Dict[str, Any]]:
        if bucket in {"top30", "top50"}:
            return list(payload.get("signals") or [])
        rows: List[Dict[str, Any]] = []
        seen = set()
        for row in list(payload.get("top30") or []) + list(payload.get("top50") or []):
            symbol = str(row.get("symbol") or "")
            if symbol and symbol not in seen:
                seen.add(symbol)
                rows.append(row)
        rows.sort(key=lambda item: int(item.get("rank") or 999999))
        return rows

    @staticmethod
    def _qlib_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "asof": payload.get("asof"),
            "run_id": payload.get("run_id"),
            "recorder_id": payload.get("recorder_id"),
            "target_horizon": payload.get("target_horizon"),
            "target_date": payload.get("target_date"),
            "signal_semantics": payload.get("signal_semantics"),
            "recommendation_semantics": payload.get("recommendation_semantics"),
            "research_signal_not_order": True,
            "summary": payload.get("summary") or {},
        }

    def _safe_trend_snapshot(self, symbol: str, *, trend_limit: int) -> Dict[str, Any]:
        try:
            raw = self.trend_service.analyze_symbol(symbol=symbol, limit=trend_limit)
        except Exception as exc:
            return {
                "ok": False,
                "trend_label": None,
                "trend_score": None,
                "latest_date": None,
                "quality_warnings": ["trend_service_error"],
                "source": "KlineService:TWStock:1D",
                "error": str(exc),
                "raw": None,
            }
        if not isinstance(raw, dict) or not raw.get("ok"):
            quality = raw.get("quality") if isinstance(raw, dict) else {}
            warnings = quality.get("warnings") if isinstance(quality, dict) else []
            return {
                "ok": False,
                "trend_label": None,
                "trend_score": None,
                "latest_date": quality.get("latest_date") if isinstance(quality, dict) else None,
                "quality_warnings": warnings if isinstance(warnings, list) else [],
                "source": quality.get("source") if isinstance(quality, dict) else "KlineService:TWStock:1D",
                "error": (raw.get("error") if isinstance(raw, dict) else None) or "trend_unavailable",
                "raw": raw if isinstance(raw, dict) else None,
            }
        trend = raw.get("trend") or {}
        latest = raw.get("latest") or {}
        quality = raw.get("quality") or {}
        warnings = quality.get("warnings") or []
        return {
            "ok": True,
            "trend_label": trend.get("label") or "unknown",
            "trend_score": trend.get("score"),
            "latest_date": latest.get("date") or quality.get("latest_date"),
            "quality_warnings": warnings if isinstance(warnings, list) else [],
            "source": quality.get("source") or "KlineService:TWStock:1D",
            "error": None,
            "raw": raw,
        }

    @staticmethod
    def _trend_summary(trend: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "trend_label": trend.get("trend_label"),
            "trend_score": trend.get("trend_score"),
            "latest_date": trend.get("latest_date"),
            "quality_warnings": trend.get("quality_warnings") or [],
            "source": trend.get("source") or "KlineService:TWStock:1D",
            "ok": bool(trend.get("ok")),
            "error": trend.get("error"),
        }

    @staticmethod
    def _data_basis(*, qlib_payload: Dict[str, Any], trend: Dict[str, Any]) -> Dict[str, Any]:
        qlib_asof = str(qlib_payload.get("asof") or "")
        trend_date = trend.get("latest_date")
        gap = None
        aligned = False
        status = "ok"
        try:
            if qlib_asof and trend_date:
                gap = (date.fromisoformat(str(qlib_asof)) - date.fromisoformat(str(trend_date))).days
                aligned = abs(gap) <= 1
        except Exception:
            gap = None
            aligned = False
        if not trend_date:
            status = "quantdinger_raw_unavailable"
        elif not aligned:
            status = "date_gap"
        return {
            "qlib_source": "Yahoo adjusted model signal",
            "quantdinger_source": trend.get("source") or "KlineService:TWStock:1D",
            "qlib_asof": qlib_asof,
            "quantdinger_latest_date": trend_date,
            "date_gap_days": gap,
            "date_aligned": aligned,
            "data_basis_status": status,
            "data_basis_note": "qlib uses Yahoo adjusted model signals; QuantDinger trend uses raw TWStock daily KlineService data.",
        }

    @staticmethod
    def basis_contract() -> Dict[str, Any]:
        return {
            "qlib_source": "Yahoo adjusted model signal",
            "quantdinger_source": "raw TWStock daily KlineService data",
            "note": "qlib score comes from Yahoo adjusted model signals. QuantDinger trend comes from raw daily bars. Adjustments, corporate actions and data-source latency can make the two differ.",
        }

    @staticmethod
    def _freshness_summary(*, qlib_payload: Dict[str, Any], items: List[Dict[str, Any]]) -> Dict[str, Any]:
        qlib = {
            "status": qlib_payload.get("status"),
            "asof": qlib_payload.get("asof"),
            "run_id": qlib_payload.get("run_id"),
            "target_horizon": qlib_payload.get("target_horizon"),
        }
        latest_dates = []
        gaps = []
        sources = []
        warnings: List[str] = []
        for item in items:
            quant = item.get("quantdinger") or {}
            basis = item.get("data_basis") or {}
            latest_date = quant.get("latest_date") or basis.get("quantdinger_latest_date")
            if latest_date:
                latest_dates.append(str(latest_date))
            if basis.get("date_gap_days") is not None:
                gaps.append(int(basis.get("date_gap_days")))
            source = quant.get("source") or basis.get("quantdinger_source")
            if source:
                sources.append(str(source))
            category = (item.get("cross") or {}).get("category")
            if category in {"trend_unavailable", "data_review_required"}:
                warnings.append(str(category))
        latest_min = min(latest_dates) if latest_dates else None
        latest_max = max(latest_dates) if latest_dates else None
        gap_min = min(gaps) if gaps else None
        gap_max = max(gaps) if gaps else None
        if not items:
            status = "unknown"
            warnings.append("no_cross_analysis_items")
        elif latest_min is None or latest_max is None:
            status = "unknown"
            warnings.append("raw_latest_date_unavailable")
        elif gap_min is None or gap_max is None:
            status = "unknown"
            warnings.append("date_gap_unavailable")
        elif max(abs(gap_min), abs(gap_max)) > 1:
            status = "stale"
            warnings.append("qlib_raw_date_gap_gt_1")
        elif qlib_payload.get("target_date") is None:
            status = "historical"
            warnings.append("target_date_unavailable")
        else:
            status = "fresh"
        return {
            "qlib": qlib,
            "quantdinger": {
                "latest_date_min": latest_min,
                "latest_date_max": latest_max,
                "source": ", ".join(sorted(set(sources))) if sources else "raw TWStock daily KlineService data",
            },
            "date_gap_days_min": gap_min,
            "date_gap_days_max": gap_max,
            "status": status,
            "warnings": list(dict.fromkeys(warnings)),
        }

    @staticmethod
    def _classify(*, row: Dict[str, Any], trend: Dict[str, Any]) -> Dict[str, Any]:
        warnings = set(str(item) for item in (trend.get("quality_warnings") or []))
        label = str(trend.get("trend_label") or "unknown")
        bucket = str(row.get("bucket") or "")
        if warnings & SERIOUS_QUALITY_WARNINGS:
            category, alignment, priority = "data_review_required", "blocked", "blocked"
        elif not trend.get("ok"):
            category, alignment, priority = "trend_unavailable", "blocked", "blocked"
        elif bucket == "top30" and label in POSITIVE_TRENDS:
            category, alignment, priority = "focus_watch", "aligned", "high"
        elif bucket == "top30" and label in NEGATIVE_TRENDS:
            category, alignment, priority = "model_trend_divergence", "divergent", "medium"
        elif bucket == "top30":
            category, alignment, priority = "model_watch_trend_neutral", "neutral", "medium"
        elif bucket == "top50" and label in POSITIVE_TRENDS:
            category, alignment, priority = "secondary_watch", "aligned", "medium"
        else:
            category, alignment, priority = "low_priority_watch", "neutral", "low"
        return {
            "category": category,
            "alignment": alignment,
            "priority": priority,
            "summary": TWStockCrossAnalysisService._cross_summary(category=category, label=label, bucket=bucket),
            "human_action": TWStockCrossAnalysisService._human_action(category),
        }

    @staticmethod
    def _cross_summary(*, category: str, label: str, bucket: str) -> str:
        if category == "focus_watch":
            return f"qlib {bucket} 研究排序靠前，raw 趋势为 {label}，适合列入重点观察。"
        if category == "model_trend_divergence":
            return f"qlib {bucket} 研究排序靠前，但 raw 趋势为 {label}，存在数据口径或走势分歧。"
        if category == "model_watch_trend_neutral":
            return f"qlib {bucket} 研究排序靠前，raw 趋势暂偏中性，等待人工复盘。"
        if category == "secondary_watch":
            return f"qlib {bucket} 研究排序在观察范围内，raw 趋势支持二级观察。"
        if category == "data_review_required":
            return "数据质量存在严重提示，先复核数据新鲜度和 K 线质量。"
        if category == "trend_unavailable":
            return "趋势服务不可用，暂不分类为可观察。"
        return f"qlib {bucket} 研究排序在观察范围内，raw 趋势暂未形成强支持。"

    @staticmethod
    def _human_action(category: str) -> str:
        return {
            "focus_watch": "加入重点观察并人工复盘",
            "model_trend_divergence": "模型和 raw 趋势分歧，人工复核数据口径和走势",
            "model_watch_trend_neutral": "保留观察名单，等待趋势或数据口径进一步确认",
            "secondary_watch": "加入二级观察名单并人工复盘",
            "low_priority_watch": "低优先级观察，先不做进一步动作",
            "data_review_required": "先复核数据新鲜度和 K 线质量",
            "trend_unavailable": "趋势服务不可用，暂不分类为可观察",
        }.get(category, "人工复盘")

    @staticmethod
    def _category_counts(items: List[Dict[str, Any]]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for item in items:
            category = str((item.get("cross") or {}).get("category") or "unknown")
            counts[category] = counts.get(category, 0) + 1
        return counts
