"""Research-only qlib signal history import and alert generation."""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from app.services.tw_stock_cross_analysis import TWStockCrossAnalysisService
from app.services.tw_stock_qlib_option_c import QlibOptionCSignalError, QlibOptionCSignalReader, research_only_trading_flags
from app.utils.db import get_db_connection


HUMAN_ACTION = "人工复盘，不自动交易"
REVIEW_STATUSES = {"pending", "watching", "reviewed", "ignored", "data_issue"}
ALERT_TYPES = {
    "new_top30_entry",
    "new_top50_entry",
    "rank_up",
    "rank_down",
    "dropped_from_top30",
    "dropped_from_top50",
    "consecutive_top30",
    "consecutive_top50",
    "qlib_top30_trend_turn_weak",
    "qlib_top30_data_warning",
}


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS qd_tw_qlib_signal_runs (
    id BIGSERIAL PRIMARY KEY,
    run_id VARCHAR(120) NOT NULL UNIQUE,
    asof DATE NOT NULL,
    status VARCHAR(40) NOT NULL,
    source_root TEXT DEFAULT '',
    run_dir TEXT DEFAULT '',
    recorder_id VARCHAR(80) DEFAULT '',
    provider_uri TEXT DEFAULT '',
    config_path TEXT DEFAULT '',
    prediction_rows INTEGER NOT NULL DEFAULT 0,
    top30_rows INTEGER NOT NULL DEFAULT 0,
    top50_rows INTEGER NOT NULL DEFAULT 0,
    finite_prediction_share DECIMAL(12,8) NOT NULL DEFAULT 0,
    diagnostic_only BOOLEAN NOT NULL DEFAULT TRUE,
    research_signal_not_order BOOLEAN NOT NULL DEFAULT TRUE,
    raw_summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    raw_metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    imported_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tw_qlib_signal_runs_asof ON qd_tw_qlib_signal_runs(asof DESC);

CREATE TABLE IF NOT EXISTS qd_tw_qlib_signals (
    id BIGSERIAL PRIMARY KEY,
    run_id VARCHAR(120) NOT NULL,
    asof DATE NOT NULL,
    instrument VARCHAR(40) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    bucket VARCHAR(20) NOT NULL,
    rank INTEGER NOT NULL,
    score DECIMAL(24,12) NOT NULL,
    source_model_recorder VARCHAR(80) DEFAULT '',
    diagnostic_only BOOLEAN NOT NULL DEFAULT TRUE,
    research_signal_not_order BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(run_id, bucket, instrument),
    UNIQUE(asof, bucket, instrument)
);
CREATE INDEX IF NOT EXISTS idx_tw_qlib_signals_symbol_asof ON qd_tw_qlib_signals(symbol, asof DESC);
CREATE INDEX IF NOT EXISTS idx_tw_qlib_signals_bucket_rank ON qd_tw_qlib_signals(bucket, asof DESC, rank);

CREATE TABLE IF NOT EXISTS qd_tw_qlib_signal_alerts (
    id BIGSERIAL PRIMARY KEY,
    run_id VARCHAR(120) NOT NULL,
    asof DATE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    instrument VARCHAR(40) NOT NULL,
    alert_type VARCHAR(60) NOT NULL,
    old_rank INTEGER,
    new_rank INTEGER,
    old_bucket VARCHAR(20),
    new_bucket VARCHAR(20),
    message TEXT NOT NULL,
    human_action TEXT NOT NULL DEFAULT '人工复盘，不自动交易',
    research_signal_not_order BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(run_id, symbol, alert_type)
);
CREATE INDEX IF NOT EXISTS idx_tw_qlib_signal_alerts_asof ON qd_tw_qlib_signal_alerts(asof DESC);
CREATE INDEX IF NOT EXISTS idx_tw_qlib_signal_alerts_symbol ON qd_tw_qlib_signal_alerts(symbol, asof DESC);

CREATE TABLE IF NOT EXISTS qd_tw_cross_analysis_reviews (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1,
    asof DATE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    run_id VARCHAR(120) NOT NULL,
    cross_category VARCHAR(80) DEFAULT '',
    decision_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    user_note TEXT DEFAULT '',
    updated_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, asof, symbol, run_id)
);
CREATE INDEX IF NOT EXISTS idx_tw_cross_analysis_reviews_user_asof ON qd_tw_cross_analysis_reviews(user_id, asof DESC);
CREATE INDEX IF NOT EXISTS idx_tw_cross_analysis_reviews_symbol ON qd_tw_cross_analysis_reviews(symbol, asof DESC);
"""


class TWStockCrossAnalysisHistoryService:
    """Import validated accepted qlib signals into research history tables."""

    def __init__(
        self,
        *,
        qlib_reader: Optional[Any] = None,
        cross_service: Optional[Any] = None,
        db_factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        self.qlib_reader = qlib_reader or QlibOptionCSignalReader()
        self.cross_service = cross_service or TWStockCrossAnalysisService(qlib_reader=self.qlib_reader)
        self.db_factory = db_factory or get_db_connection

    def import_latest(self, *, confirm_import_qlib_signal_history: bool = False) -> Dict[str, Any]:
        if confirm_import_qlib_signal_history is not True:
            return {
                "ok": False,
                "status": "confirm_required",
                "message": "confirm_import_qlib_signal_history=true is required",
                "trading": research_only_trading_flags(),
            }

        try:
            qlib_payload = self.qlib_reader.latest(bucket="all", enrich_trend=False)
        except QlibOptionCSignalError as exc:
            return {
                "ok": False,
                "status": exc.status,
                "message": exc.message,
                "imported": False,
                "trading": research_only_trading_flags(),
                "warnings": exc.warnings,
            }

        validation = self._validate_import_payload(qlib_payload)
        if not validation["ok"]:
            return validation

        cross_payload = self.cross_service.latest(bucket="top30", limit=120, include_raw_trend=False, max_items=30)
        top30 = list(qlib_payload.get("top30") or [])
        top50 = list(qlib_payload.get("top50") or [])
        all_rows = top30 + top50

        with self.db_factory() as db:
            cur = db.cursor()
            self._ensure_schema(cur)
            previous_rows = self._previous_latest_signals(cur, asof=str(qlib_payload.get("asof") or ""))
            previous_two = self._previous_top_bucket_sets(cur, asof=str(qlib_payload.get("asof") or ""), limit=2)
            self._insert_run(cur, qlib_payload)
            signal_count = self._insert_signals(cur, qlib_payload=qlib_payload, rows=all_rows)
            alerts = self._build_alerts(
                qlib_payload=qlib_payload,
                previous_rows=previous_rows,
                previous_top_sets=previous_two,
                cross_payload=cross_payload if isinstance(cross_payload, dict) else {},
            )
            alert_count = self._insert_alerts(cur, alerts)
            cur.close()
            db.commit()

        return {
            "ok": True,
            "status": "imported",
            "imported": True,
            "run_id": qlib_payload.get("run_id"),
            "asof": qlib_payload.get("asof"),
            "signals": {"attempted": len(all_rows), "inserted_or_existing": signal_count, "top30": len(top30), "top50": len(top50)},
            "alerts": {"attempted": len(alerts), "inserted_or_existing": alert_count, "items": alerts},
            "trading": research_only_trading_flags(),
        }

    def runs(self, *, limit: int = 20) -> Dict[str, Any]:
        with self.db_factory() as db:
            cur = db.cursor()
            self._ensure_schema(cur)
            cur.execute(
                """
                SELECT run_id, asof, status, source_root, run_dir, recorder_id, provider_uri,
                       config_path, prediction_rows, top30_rows, top50_rows,
                       finite_prediction_share, diagnostic_only, research_signal_not_order,
                       raw_summary_json, raw_metadata_json, imported_at
                FROM qd_tw_qlib_signal_runs
                ORDER BY asof DESC, imported_at DESC
                LIMIT ?
                """,
                (self._limit(limit),),
            )
            rows = cur.fetchall() or []
            cur.close()
        return {"ok": True, "items": [self._json_ready(row) for row in rows], "count": len(rows), "trading": research_only_trading_flags()}

    def signals(self, *, run_id: str = "", bucket: str = "", symbol: str = "", limit: int = 100) -> Dict[str, Any]:
        filters = []
        params: List[Any] = []
        if run_id:
            filters.append("run_id = ?")
            params.append(str(run_id))
        if bucket:
            filters.append("bucket = ?")
            params.append(self._normalize_bucket_filter(bucket))
        if symbol:
            filters.append("symbol = ?")
            params.append(self._normalize_symbol(symbol))
        where = "WHERE " + " AND ".join(filters) if filters else ""
        params.append(self._limit(limit, max_value=500))
        with self.db_factory() as db:
            cur = db.cursor()
            self._ensure_schema(cur)
            cur.execute(
                f"""
                SELECT run_id, asof, instrument, symbol, bucket, rank, score,
                       source_model_recorder, diagnostic_only, research_signal_not_order, created_at
                FROM qd_tw_qlib_signals
                {where}
                ORDER BY asof DESC, bucket ASC, rank ASC
                LIMIT ?
                """,
                tuple(params),
            )
            rows = cur.fetchall() or []
            cur.close()
        return {"ok": True, "items": [self._json_ready(row) for row in rows], "count": len(rows), "trading": research_only_trading_flags()}

    def alerts(self, *, run_id: str = "", alert_type: str = "", symbol: str = "", limit: int = 100) -> Dict[str, Any]:
        filters = []
        params: List[Any] = []
        if run_id:
            filters.append("run_id = ?")
            params.append(str(run_id))
        if alert_type:
            clean_type = str(alert_type).strip()
            if clean_type in ALERT_TYPES:
                filters.append("alert_type = ?")
                params.append(clean_type)
        if symbol:
            filters.append("symbol = ?")
            params.append(self._normalize_symbol(symbol))
        where = "WHERE " + " AND ".join(filters) if filters else ""
        params.append(self._limit(limit, max_value=500))
        with self.db_factory() as db:
            cur = db.cursor()
            self._ensure_schema(cur)
            cur.execute(
                f"""
                SELECT run_id, asof, symbol, instrument, alert_type, old_rank, new_rank,
                       old_bucket, new_bucket, message, human_action,
                       research_signal_not_order, created_at
                FROM qd_tw_qlib_signal_alerts
                {where}
                ORDER BY asof DESC, created_at DESC
                LIMIT ?
                """,
                tuple(params),
            )
            rows = cur.fetchall() or []
            cur.close()
        return {"ok": True, "items": [self._json_ready(row) for row in rows], "count": len(rows), "trading": research_only_trading_flags()}


    def reviews(self, *, user_id: int, asof: str = "", run_id: str = "", symbol: str = "", limit: int = 100) -> Dict[str, Any]:
        filters = ["user_id = ?"]
        params: List[Any] = [self._normalize_user_id(user_id)]
        if asof:
            filters.append("asof = ?")
            params.append(str(asof).strip())
        if run_id:
            filters.append("run_id = ?")
            params.append(str(run_id).strip())
        if symbol:
            filters.append("symbol = ?")
            params.append(self._normalize_symbol(symbol))
        params.append(self._limit(limit, max_value=500))
        with self.db_factory() as db:
            cur = db.cursor()
            self._ensure_schema(cur)
            cur.execute(
                f"""
                SELECT id, user_id, asof, symbol, run_id, cross_category,
                       decision_status, user_note, updated_at, created_at
                FROM qd_tw_cross_analysis_reviews
                WHERE {' AND '.join(filters)}
                ORDER BY updated_at DESC, created_at DESC
                LIMIT ?
                """,
                tuple(params),
            )
            rows = cur.fetchall() or []
            cur.close()
        return {"ok": True, "items": [self._review_json_ready(row) for row in rows], "count": len(rows), "trading": research_only_trading_flags()}

    def save_review(
        self,
        *,
        user_id: int,
        asof: str,
        run_id: str,
        symbol: str,
        cross_category: str = "",
        decision_status: str = "pending",
        user_note: str = "",
    ) -> Dict[str, Any]:
        clean_status = str(decision_status or "").strip().lower()
        if clean_status not in REVIEW_STATUSES:
            return {
                "ok": False,
                "status": "invalid_decision_status",
                "message": "decision_status must be one of: pending, watching, reviewed, ignored, data_issue",
                "allowed_statuses": sorted(REVIEW_STATUSES),
                "trading": research_only_trading_flags(),
            }
        clean_asof = str(asof or "").strip()
        clean_run_id = str(run_id or "").strip()[:120]
        clean_symbol = self._normalize_symbol(symbol)
        if not clean_asof or not clean_run_id or not clean_symbol:
            return {"ok": False, "status": "missing_required_fields", "message": "asof, run_id and symbol are required", "trading": research_only_trading_flags()}
        with self.db_factory() as db:
            cur = db.cursor()
            self._ensure_schema(cur)
            cur.execute(
                """
                INSERT INTO qd_tw_cross_analysis_reviews
                    (user_id, asof, symbol, run_id, cross_category, decision_status,
                     user_note, updated_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, NOW(), NOW())
                ON CONFLICT (user_id, asof, symbol, run_id) DO UPDATE SET
                    cross_category = EXCLUDED.cross_category,
                    decision_status = EXCLUDED.decision_status,
                    user_note = EXCLUDED.user_note,
                    updated_at = NOW()
                RETURNING id, user_id, asof, symbol, run_id, cross_category,
                          decision_status, user_note, updated_at, created_at
                """,
                (
                    self._normalize_user_id(user_id),
                    clean_asof,
                    clean_symbol,
                    clean_run_id,
                    str(cross_category or "").strip()[:80],
                    clean_status,
                    str(user_note or "")[:2000],
                ),
            )
            row = cur.fetchone()
            cur.close()
            db.commit()
        return {"ok": True, "status": "saved", "item": self._review_json_ready(row or {}), "trading": research_only_trading_flags()}

    @staticmethod
    def _ensure_schema(cur: Any) -> None:
        cur.execute(SCHEMA_SQL)

    @staticmethod
    def _validate_import_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        summary = payload.get("summary") or {}
        trading = payload.get("trading") or {}
        required = {
            "status": payload.get("status") == "accepted",
            "summary.status": summary.get("status") == "accepted",
            "prediction_rows": int(summary.get("prediction_rows") or 0) == 150,
            "top30_rows": int(summary.get("top30_rows") or 0) == 30,
            "top50_rows": int(summary.get("top50_rows") or 0) == 50,
            "finite_prediction_share": float(summary.get("finite_prediction_share") or 0.0) == 1.0,
            "diagnostic_only": summary.get("diagnostic_only") is True,
            "research_signal_not_order": summary.get("research_signal_not_order") is True and trading.get("research_signal_not_order") is True,
            "top30_count": len(payload.get("top30") or []) == 30,
            "top50_count": len(payload.get("top50") or []) == 50,
        }
        failed = [key for key, ok in required.items() if not ok]
        if failed:
            return {
                "ok": False,
                "status": "import_blocked",
                "message": "latest qlib signal does not satisfy accepted-only import gate",
                "failed_checks": failed,
                "imported": False,
                "trading": research_only_trading_flags(),
            }
        return {"ok": True}

    @staticmethod
    def _insert_run(cur: Any, payload: Dict[str, Any]) -> None:
        summary = payload.get("summary") or {}
        metadata = payload.get("metadata") or {}
        source = payload.get("source") or {}
        cur.execute(
            """
            INSERT INTO qd_tw_qlib_signal_runs
                (run_id, asof, status, source_root, run_dir, recorder_id, provider_uri,
                 config_path, prediction_rows, top30_rows, top50_rows, finite_prediction_share,
                 diagnostic_only, research_signal_not_order, raw_summary_json, raw_metadata_json, imported_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE, TRUE, ?::jsonb, ?::jsonb, NOW())
            ON CONFLICT (run_id) DO UPDATE SET
                asof = EXCLUDED.asof,
                imported_at = NOW()
            """,
            (
                payload.get("run_id"),
                payload.get("asof"),
                payload.get("status"),
                str(source.get("root") or ""),
                str(source.get("run_dir") or ""),
                payload.get("recorder_id") or metadata.get("frozen_recorder") or "",
                str(metadata.get("provider_uri") or ""),
                str(metadata.get("config") or ""),
                int(summary.get("prediction_rows") or 0),
                int(summary.get("top30_rows") or 0),
                int(summary.get("top50_rows") or 0),
                float(summary.get("finite_prediction_share") or 0),
                json.dumps(summary, ensure_ascii=False),
                json.dumps(metadata, ensure_ascii=False),
            ),
        )

    @staticmethod
    def _insert_signals(cur: Any, *, qlib_payload: Dict[str, Any], rows: Iterable[Dict[str, Any]]) -> int:
        count = 0
        for row in rows:
            cur.execute(
                """
                INSERT INTO qd_tw_qlib_signals
                    (run_id, asof, instrument, symbol, bucket, rank, score,
                     source_model_recorder, diagnostic_only, research_signal_not_order, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, TRUE, TRUE, NOW())
                ON CONFLICT DO NOTHING
                """,
                (
                    qlib_payload.get("run_id"),
                    qlib_payload.get("asof"),
                    row.get("instrument"),
                    row.get("symbol"),
                    row.get("bucket"),
                    int(row.get("rank") or 0),
                    float(row.get("qlib_score") if row.get("qlib_score") is not None else row.get("score")),
                    row.get("source_model_recorder") or "",
                ),
            )
            count += 1
        return count

    @staticmethod
    def _insert_alerts(cur: Any, alerts: Sequence[Dict[str, Any]]) -> int:
        count = 0
        for alert in alerts:
            cur.execute(
                """
                INSERT INTO qd_tw_qlib_signal_alerts
                    (run_id, asof, symbol, instrument, alert_type, old_rank, new_rank,
                     old_bucket, new_bucket, message, human_action,
                     research_signal_not_order, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE, NOW())
                ON CONFLICT (run_id, symbol, alert_type) DO NOTHING
                """,
                (
                    alert["run_id"],
                    alert["asof"],
                    alert["symbol"],
                    alert["instrument"],
                    alert["alert_type"],
                    alert.get("old_rank"),
                    alert.get("new_rank"),
                    alert.get("old_bucket"),
                    alert.get("new_bucket"),
                    alert["message"],
                    alert["human_action"],
                ),
            )
            count += 1
        return count

    def _build_alerts(
        self,
        *,
        qlib_payload: Dict[str, Any],
        previous_rows: Sequence[Dict[str, Any]],
        previous_top_sets: Sequence[Dict[str, set]],
        cross_payload: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        current = list(qlib_payload.get("top30") or []) + list(qlib_payload.get("top50") or [])
        current_by_bucket = {(str(row.get("bucket")), str(row.get("instrument"))): row for row in current}
        previous_by_bucket = {(str(row.get("bucket")), str(row.get("instrument"))): row for row in previous_rows}
        previous_top30_symbols = {str(row.get("symbol")) for row in previous_rows if row.get("bucket") == "top30"}
        previous_top50_symbols = {str(row.get("symbol")) for row in previous_rows if row.get("bucket") == "top50"}
        cross_by_symbol = {str(item.get("symbol")): item for item in (cross_payload.get("items") or [])}

        alerts: List[Dict[str, Any]] = []
        for row in current:
            bucket = str(row.get("bucket"))
            symbol = str(row.get("symbol"))
            instrument = str(row.get("instrument"))
            previous_same = previous_by_bucket.get((bucket, instrument))
            previous_top30 = previous_by_bucket.get(("top30", instrument))
            previous_top50 = previous_by_bucket.get(("top50", instrument))
            if bucket == "top30":
                if symbol not in previous_top30_symbols:
                    alerts.append(self._alert(qlib_payload, row, "new_top30_entry", old_rank=(previous_top30 or {}).get("rank"), old_bucket=(previous_top30 or {}).get("bucket")))
                if previous_same:
                    self._append_rank_change(alerts, qlib_payload, row, previous_same)
                if previous_top_sets and all(symbol in item.get("top30", set()) for item in previous_top_sets[:2]):
                    alerts.append(self._alert(qlib_payload, row, "consecutive_top30", old_rank=(previous_same or {}).get("rank"), old_bucket="top30"))
                cross = cross_by_symbol.get(symbol) or {}
                category = str((cross.get("cross") or {}).get("category") or "")
                trend_label = str((cross.get("quantdinger") or {}).get("trend_label") or "")
                if category == "data_review_required":
                    alerts.append(self._alert(qlib_payload, row, "qlib_top30_data_warning"))
                if trend_label in {"downtrend", "pullback"}:
                    alerts.append(self._alert(qlib_payload, row, "qlib_top30_trend_turn_weak"))
            elif bucket == "top50":
                if symbol not in previous_top50_symbols:
                    alerts.append(self._alert(qlib_payload, row, "new_top50_entry", old_rank=(previous_top50 or {}).get("rank"), old_bucket=(previous_top50 or {}).get("bucket")))
                if previous_same:
                    self._append_rank_change(alerts, qlib_payload, row, previous_same)
                if previous_top30 and instrument not in {key[1] for key in current_by_bucket if key[0] == "top30"}:
                    alerts.append(self._alert(qlib_payload, row, "dropped_from_top30", old_rank=previous_top30.get("rank"), old_bucket="top30"))
                if previous_top_sets and all(symbol in item.get("top50", set()) for item in previous_top_sets[:2]):
                    alerts.append(self._alert(qlib_payload, row, "consecutive_top50", old_rank=(previous_same or {}).get("rank"), old_bucket="top50"))

        current_top50_instruments = {str(row.get("instrument")) for row in current}
        for row in previous_rows:
            if row.get("bucket") == "top50" and str(row.get("instrument")) not in current_top50_instruments:
                alerts.append(self._alert(qlib_payload, row, "dropped_from_top50", old_rank=row.get("rank"), new_rank=None, old_bucket="top50", new_bucket=None))

        return self._dedupe_alerts(alerts)

    def _append_rank_change(self, alerts: List[Dict[str, Any]], qlib_payload: Dict[str, Any], row: Dict[str, Any], previous: Dict[str, Any]) -> None:
        old_rank = int(previous.get("rank") or 0)
        new_rank = int(row.get("rank") or 0)
        if old_rank - new_rank >= 10:
            alerts.append(self._alert(qlib_payload, row, "rank_up", old_rank=old_rank, old_bucket=previous.get("bucket")))
        elif new_rank - old_rank >= 10:
            alerts.append(self._alert(qlib_payload, row, "rank_down", old_rank=old_rank, old_bucket=previous.get("bucket")))

    @staticmethod
    def _alert(
        qlib_payload: Dict[str, Any],
        row: Dict[str, Any],
        alert_type: str,
        *,
        old_rank: Any = None,
        new_rank: Any = None,
        old_bucket: Any = None,
        new_bucket: Any = None,
    ) -> Dict[str, Any]:
        final_new_rank = int(row.get("rank") or 0) if new_rank is None and alert_type != "dropped_from_top50" else new_rank
        final_new_bucket = str(row.get("bucket") or "") if new_bucket is None and alert_type != "dropped_from_top50" else new_bucket
        symbol = str(row.get("symbol") or "")
        message = f"{symbol} {alert_type}: qlib 研究榜单变化，仅供人工复盘，不自动交易"
        return {
            "run_id": qlib_payload.get("run_id"),
            "asof": qlib_payload.get("asof"),
            "symbol": symbol,
            "instrument": row.get("instrument"),
            "alert_type": alert_type,
            "old_rank": int(old_rank) if old_rank is not None else None,
            "new_rank": int(final_new_rank) if final_new_rank is not None else None,
            "old_bucket": str(old_bucket) if old_bucket else None,
            "new_bucket": str(final_new_bucket) if final_new_bucket else None,
            "message": message,
            "human_action": HUMAN_ACTION,
            "research_signal_not_order": True,
        }

    @staticmethod
    def _dedupe_alerts(alerts: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        out = []
        for alert in alerts:
            key = (alert.get("run_id"), alert.get("symbol"), alert.get("alert_type"))
            if key in seen:
                continue
            seen.add(key)
            out.append(alert)
        return out

    @staticmethod
    def _previous_latest_signals(cur: Any, *, asof: str) -> List[Dict[str, Any]]:
        cur.execute(
            """
            SELECT run_id, asof, instrument, symbol, bucket, rank, score
            FROM qd_tw_qlib_signals
            WHERE asof = (
                SELECT MAX(asof) FROM qd_tw_qlib_signals WHERE asof < ?
            )
            """,
            (asof,),
        )
        return list(cur.fetchall() or [])

    @staticmethod
    def _previous_top_bucket_sets(cur: Any, *, asof: str, limit: int = 2) -> List[Dict[str, set]]:
        cur.execute(
            """
            SELECT asof, symbol, bucket
            FROM qd_tw_qlib_signals
            WHERE asof IN (
                SELECT DISTINCT asof FROM qd_tw_qlib_signals WHERE asof < ? ORDER BY asof DESC LIMIT ?
            )
            """,
            (asof, limit),
        )
        rows = cur.fetchall() or []
        by_asof: Dict[str, Dict[str, set]] = {}
        for row in rows:
            key = str(row.get("asof"))
            by_asof.setdefault(key, {"top30": set(), "top50": set()})
            if row.get("bucket") in {"top30", "top50"}:
                by_asof[key][str(row.get("bucket"))].add(str(row.get("symbol")))
        return [by_asof[key] for key in sorted(by_asof.keys(), reverse=True)]

    @staticmethod
    def _limit(limit: int, *, max_value: int = 100) -> int:
        try:
            value = int(limit or 20)
        except Exception:
            value = 20
        return max(1, min(value, max_value))

    @staticmethod
    def _normalize_bucket_filter(bucket: str) -> str:
        clean = str(bucket or "").strip().lower()
        return clean if clean in {"top30", "top50"} else ""

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        clean = str(symbol or "").strip().upper()
        if clean.startswith("TW"):
            clean = clean[2:]
        if "." in clean:
            clean = clean.split(".", 1)[0]
        return clean

    @staticmethod
    def _normalize_user_id(user_id: int) -> int:
        try:
            return max(1, int(user_id or 1))
        except Exception:
            return 1

    @staticmethod
    def _review_json_ready(row: Dict[str, Any]) -> Dict[str, Any]:
        out = TWStockCrossAnalysisHistoryService._json_ready(row or {})
        out["trading"] = research_only_trading_flags()
        out["research_signal_not_order"] = True
        return out

    @staticmethod
    def _json_ready(row: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(row)
        for key, value in list(out.items()):
            if hasattr(value, "isoformat"):
                out[key] = value.isoformat()
        return out
