"""Read-only qlib Option C TWStock research signal reader.

This module consumes local qlib artifacts only. It never executes qlib scripts,
refreshes providers, trains models, creates orders, or touches broker state.
"""
from __future__ import annotations

import csv
import json
import math
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
QLIB_PIPELINE_ROOT = REPO_ROOT / "qlib_pipeline"
from typing import Any, Dict, List, Optional

from app.services.tw_stock_trend import TWStockTrendService

DEFAULT_SIGNAL_ROOT = str(QLIB_PIPELINE_ROOT / "data_tw/experiments/option_c_daily_signal")
ROOT_ENV = "QLIB_TW_OPTION_C_ROOT"
SIGNAL_REL_PREFIX = "data_tw/experiments/option_c_daily_signal"
EXPECTED_RECORDER_ID = "950741cfd5f14ee5a05464fec3e12e0a"
_REQUIRED_CSV_COLUMNS = {
    "asof",
    "instrument",
    "score",
    "rank",
    "source_model_recorder",
    "diagnostic_only",
    "research_signal_not_order",
}
_INSTRUMENT_RE = re.compile(r"^TW([0-9]{2,12})$")
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


class QlibOptionCSignalError(ValueError):
    """Raised when qlib research signal artifacts are missing or invalid."""

    def __init__(self, status: str, message: str, *, warnings: Optional[List[str]] = None) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.warnings = warnings or []


@dataclass(frozen=True)
class QlibOptionCPaths:
    root: Path
    latest: Path
    run_dir: Path
    top30: Path
    top50: Path
    summary: Path
    metadata: Path


def research_only_trading_flags() -> Dict[str, Any]:
    return {
        "orders_enabled": False,
        "connects_to_broker": False,
        "paper_orders_enabled": False,
        "live_trading_enabled": False,
        "quick_trade_enabled": False,
        "writes_orders": False,
        "writes_positions": False,
        "research_signal_not_order": True,
    }


def blocked_payload(status: str, message: str, *, warnings: Optional[List[str]] = None) -> Dict[str, Any]:
    return {
        "ok": False,
        "status": status,
        "message": message,
        "bucket": None,
        "signals": [],
        "top30": [],
        "top50": [],
        "warnings": warnings or [],
        "trading": research_only_trading_flags(),
    }


class QlibOptionCSignalReader:
    """Read and validate qlib Option C latest accepted research signals."""

    def __init__(self, root: Optional[str] = None) -> None:
        raw_root = root or os.getenv(ROOT_ENV) or DEFAULT_SIGNAL_ROOT
        self.root = Path(raw_root).expanduser().resolve(strict=False)

    def latest(
        self,
        *,
        bucket: str = "top30",
        enrich_trend: bool = False,
        trend_limit: int = 120,
        trend_service: Optional[Any] = None,
    ) -> Dict[str, Any]:
        bucket = self._normalize_bucket(bucket)
        normalized_trend_limit = self._normalize_trend_limit(trend_limit)

        paths, latest_doc = self._load_latest_and_paths()
        summary = self._load_json(paths.summary, "missing_signal_summary")
        metadata = self._load_json(paths.metadata, "missing_run_metadata")
        warnings = self._validate_documents(paths=paths, latest_doc=latest_doc, summary=summary, metadata=metadata)
        asof = str(latest_doc.get("asof") or summary.get("asof") or metadata.get("asof") or "")
        top30 = self._read_csv(paths.top30, bucket="top30", asof=asof)
        top50 = self._read_csv(paths.top50, bucket="top50", asof=asof)
        self._validate_row_counts(summary=summary, top30=top30, top50=top50)

        run_id = str(metadata.get("run_id"))
        recorder_id = EXPECTED_RECORDER_ID

        target_date = self._derive_target_date(asof, metadata=metadata, summary=summary)
        payload: Dict[str, Any] = {
            "ok": True,
            "status": "accepted",
            "asof": asof,
            "target_horizon": "next_trading_day_research_ranking",
            "target_date": target_date,
            "signal_semantics": "research_only_cross_sectional_ranking",
            "recommendation_semantics": "watchlist_not_trade_advice",
            "run_id": run_id,
            "recorder_id": recorder_id,
            "bucket": bucket,
            "source": {
                "latest_signal": str(paths.latest.relative_to(self.root)),
                "run_dir": str(paths.run_dir.relative_to(self.root)),
                "top30_signals": str(paths.top30.relative_to(self.root)),
                "top50_signals": str(paths.top50.relative_to(self.root)),
                "signal_summary": str(paths.summary.relative_to(self.root)),
                "run_metadata": str(paths.metadata.relative_to(self.root)),
            },
            "summary": self._public_summary(summary),
            "metadata": {
                "status": metadata.get("status"),
                "asof": metadata.get("asof"),
                "config": metadata.get("config"),
                "provider_uri": metadata.get("provider_uri"),
                "market": metadata.get("market"),
                "benchmark": metadata.get("benchmark"),
                "frozen_recorder": metadata.get("frozen_recorder"),
                "dry_run": metadata.get("dry_run"),
                "allow_refresh": metadata.get("allow_refresh"),
            },
            "trading": research_only_trading_flags(),
            "warnings": warnings,
            "enrichTrend": {
                "enabled": bool(enrich_trend),
                "requested": bool(enrich_trend),
                "trendLimit": normalized_trend_limit if enrich_trend else None,
            },
        }
        selected_rows = None
        if bucket == "top30":
            selected_rows = top30
            if enrich_trend:
                selected_rows = self._enrich_rows_with_trend(selected_rows, trend_limit=normalized_trend_limit, trend_service=trend_service)
            payload["signals"] = selected_rows
            payload["top30_count"] = len(top30)
            payload["top50_count"] = len(top50)
        elif bucket == "top50":
            selected_rows = top50
            if enrich_trend:
                selected_rows = self._enrich_rows_with_trend(selected_rows, trend_limit=normalized_trend_limit, trend_service=trend_service)
            payload["signals"] = selected_rows
            payload["top30_count"] = len(top30)
            payload["top50_count"] = len(top50)
        else:
            if enrich_trend:
                top30 = self._enrich_rows_with_trend(top30, trend_limit=normalized_trend_limit, trend_service=trend_service)
                top50 = self._enrich_rows_with_trend(top50, trend_limit=normalized_trend_limit, trend_service=trend_service)
            payload["top30"] = top30
            payload["top50"] = top50
            payload["top30_count"] = len(top30)
            payload["top50_count"] = len(top50)
        return payload


    def _derive_target_date(self, asof: str, *, metadata: Dict[str, Any], summary: Dict[str, Any]) -> Optional[str]:
        for key in ("target_date", "next_trading_day", "target_trading_date"):
            raw = metadata.get(key) or summary.get(key)
            if raw:
                return str(raw)
        return None


    def list_runs(self, *, limit: int = 20, status: str = "all") -> Dict[str, Any]:
        normalized_status = self._normalize_run_status_filter(status)
        normalized_limit = self._normalize_run_limit(limit)
        items: List[Dict[str, Any]] = []
        if not self.root.exists():
            return {"items": [], "count": 0, "limit": normalized_limit, "status": normalized_status, "trading": research_only_trading_flags()}

        for child in self.root.iterdir():
            if not child.name.startswith("option_c_daily_signal_") or not child.is_dir():
                continue
            try:
                run_dir = self._run_dir_for_id(child.name)
                item = self._run_list_item(run_dir)
            except QlibOptionCSignalError as exc:
                item = {
                    "run_id": child.name,
                    "status": exc.status,
                    "asof": None,
                    "created_at": None,
                    "accepted_validated": False,
                    "warnings": exc.warnings or [exc.message],
                    "trading": research_only_trading_flags(),
                }
            if self._run_matches_status(item, normalized_status):
                items.append(item)

        items.sort(key=lambda item: str(item.get("created_at") or item.get("asof") or item.get("run_id") or ""), reverse=True)
        items = items[:normalized_limit]
        return {
            "items": items,
            "count": len(items),
            "limit": normalized_limit,
            "status": normalized_status,
            "trading": research_only_trading_flags(),
        }

    def health(self, *, now: Optional[datetime] = None, recent_limit: int = 20) -> Dict[str, Any]:
        """Return read-only artifact freshness and availability status.

        Health validates JSON metadata only. It does not read full signal CSVs,
        refresh qlib providers, run qlib scripts, or write state.
        """
        current_date = self._current_utc_date(now)
        runs_payload = self.list_runs(limit=recent_limit, status="all")
        runs_summary = self._summarize_runs(runs_payload.get("items") or [])
        data_warnings: List[str] = []

        latest = {
            "exists": False,
            "asof": None,
            "run_id": None,
            "created_at": None,
            "accepted_validated": False,
            "warnings": [],
        }
        freshness = {
            "current_utc_date": current_date.isoformat(),
            "asof_age_days": None,
            "created_age_hours": None,
            "stale": True,
            "stale_reason": "missing_latest_signal",
        }
        status = "missing_latest_signal"
        ok = False

        try:
            paths, latest_doc = self._load_latest_and_paths()
            summary = self._load_json(paths.summary, "missing_signal_summary")
            metadata = self._load_json(paths.metadata, "missing_run_metadata")
            latest_status = str(summary.get("status") or metadata.get("status") or "unknown")
            warnings = self._collect_run_warnings(summary=summary, metadata=metadata)
            accepted_validated = False
            validation_error = ""
            if latest_status == "accepted" and metadata.get("status") == "accepted":
                try:
                    validation_warnings = self._validate_documents(paths=paths, latest_doc=latest_doc, summary=summary, metadata=metadata)
                    warnings.extend([warning for warning in validation_warnings if warning not in warnings])
                    accepted_validated = True
                except QlibOptionCSignalError as exc:
                    latest_status = exc.status
                    validation_error = exc.message
                    warnings.extend(exc.warnings or [exc.message])
            else:
                validation_error = "latest artifact is not accepted"

            asof = str(latest_doc.get("asof") or summary.get("asof") or metadata.get("asof") or "")
            created_at = str(metadata.get("created_at") or latest_doc.get("created_at") or summary.get("created_at") or "")
            run_id = str(metadata.get("run_id") or paths.run_dir.name)
            latest = {
                "exists": True,
                "asof": asof or None,
                "run_id": run_id or None,
                "created_at": created_at or None,
                "accepted_validated": accepted_validated,
                "warnings": list(dict.fromkeys(warnings)),
            }
            freshness = self._freshness_payload(
                current_date=current_date,
                asof=asof,
                created_at=created_at,
                status=latest_status,
                accepted_validated=accepted_validated,
                validation_error=validation_error,
            )
            status = latest_status
            ok = latest_status == "accepted" and accepted_validated and not freshness["stale"]
        except QlibOptionCSignalError as exc:
            status = exc.status
            latest["warnings"] = list(dict.fromkeys(exc.warnings or [exc.message]))
            freshness["stale_reason"] = exc.status

        if latest.get("asof") and self._has_newer_wait_state(runs_payload.get("items") or [], str(latest["asof"])):
            data_warnings.append("fresh_data_wait_state_present")
            if not freshness.get("stale"):
                freshness["stale"] = True
                freshness["stale_reason"] = "fresh_data_wait_state_present"
            ok = False

        return {
            "ok": ok,
            "status": status,
            "latest": latest,
            "freshness": freshness,
            "runs": runs_summary,
            "dataAvailability": {
                "trend_data_dependency": "TWStock local daily bars",
                "backtest_data_dependency": "qd_tw_stock_daily_bars",
                "warnings": data_warnings,
            },
            "trading": research_only_trading_flags(),
        }

    def run_detail(
        self,
        run_id: str,
        *,
        bucket: str = "top30",
        enrich_trend: bool = False,
        trend_limit: int = 120,
        trend_service: Optional[Any] = None,
    ) -> Dict[str, Any]:
        bucket = self._normalize_bucket(bucket)
        normalized_trend_limit = self._normalize_trend_limit(trend_limit)
        paths, latest_doc = self._paths_for_run_id(run_id)
        summary = self._load_json(paths.summary, "missing_signal_summary")
        metadata = self._load_json(paths.metadata, "missing_run_metadata")
        status = str(summary.get("status") or metadata.get("status") or "unknown")

        if status != "accepted" or metadata.get("status") != "accepted":
            return {
                "ok": False,
                "status": status,
                "message": "historical qlib run is not an accepted signal run",
                "asof": summary.get("asof") or metadata.get("asof"),
                "run_id": paths.run_dir.name,
                "bucket": bucket,
                "signals": [],
                "top30": [],
                "top50": [],
                "summary": self._public_summary(summary),
                "metadata": self._public_metadata(metadata),
                "warnings": self._collect_run_warnings(summary=summary, metadata=metadata),
                "trading": research_only_trading_flags(),
                "enrichTrend": {
                    "enabled": False,
                    "requested": bool(enrich_trend),
                    "trendLimit": normalized_trend_limit if enrich_trend else None,
                },
            }

        warnings = self._validate_documents(paths=paths, latest_doc=latest_doc, summary=summary, metadata=metadata)
        asof = str(summary.get("asof") or metadata.get("asof") or "")
        top30 = self._read_csv(paths.top30, bucket="top30", asof=asof)
        top50 = self._read_csv(paths.top50, bucket="top50", asof=asof)
        self._validate_row_counts(summary=summary, top30=top30, top50=top50)

        payload: Dict[str, Any] = {
            "ok": True,
            "status": "accepted",
            "asof": asof,
            "run_id": paths.run_dir.name,
            "recorder_id": EXPECTED_RECORDER_ID,
            "bucket": bucket,
            "source": {
                "run_dir": str(paths.run_dir.relative_to(self.root)),
                "top30_signals": str(paths.top30.relative_to(self.root)),
                "top50_signals": str(paths.top50.relative_to(self.root)),
                "signal_summary": str(paths.summary.relative_to(self.root)),
                "run_metadata": str(paths.metadata.relative_to(self.root)),
            },
            "summary": self._public_summary(summary),
            "metadata": self._public_metadata(metadata),
            "trading": research_only_trading_flags(),
            "warnings": warnings,
            "enrichTrend": {
                "enabled": bool(enrich_trend),
                "requested": bool(enrich_trend),
                "trendLimit": normalized_trend_limit if enrich_trend else None,
            },
        }
        if bucket == "top30":
            rows = self._enrich_rows_with_trend(top30, trend_limit=normalized_trend_limit, trend_service=trend_service) if enrich_trend else top30
            payload["signals"] = rows
        elif bucket == "top50":
            rows = self._enrich_rows_with_trend(top50, trend_limit=normalized_trend_limit, trend_service=trend_service) if enrich_trend else top50
            payload["signals"] = rows
        else:
            if enrich_trend:
                top30 = self._enrich_rows_with_trend(top30, trend_limit=normalized_trend_limit, trend_service=trend_service)
                top50 = self._enrich_rows_with_trend(top50, trend_limit=normalized_trend_limit, trend_service=trend_service)
            payload["top30"] = top30
            payload["top50"] = top50
        payload["top30_count"] = len(top30)
        payload["top50_count"] = len(top50)
        return payload

    @staticmethod
    def _normalize_bucket(bucket: str) -> str:
        normalized = str(bucket or "top30").strip().lower()
        if normalized not in {"top30", "top50", "all"}:
            raise QlibOptionCSignalError("invalid_bucket", "bucket must be one of: top30, top50, all")
        return normalized

    @staticmethod
    def _normalize_trend_limit(trend_limit: int) -> int:
        try:
            value = int(trend_limit or 120)
        except Exception:
            value = 120
        return max(20, min(value, 500))

    def _enrich_rows_with_trend(self, rows: List[Dict[str, Any]], *, trend_limit: int, trend_service: Optional[Any] = None) -> List[Dict[str, Any]]:
        service = trend_service or TWStockTrendService()
        enriched = []
        for row in rows:
            item = dict(row)
            item["trend"] = self._trend_snapshot(service, symbol=str(row.get("symbol") or ""), trend_limit=trend_limit)
            enriched.append(item)
        return enriched

    @staticmethod
    def _trend_snapshot(trend_service: Any, *, symbol: str, trend_limit: int) -> Dict[str, Any]:
        try:
            report = trend_service.analyze_symbol(symbol=symbol, limit=trend_limit)
            if not isinstance(report, dict) or not report.get("ok"):
                quality = report.get("quality") if isinstance(report, dict) else {}
                warnings = quality.get("warnings") if isinstance(quality, dict) else []
                return {
                    "ok": False,
                    "trend_label": None,
                    "trend_score": None,
                    "latest_close": None,
                    "latest_date": None,
                    "quality_warnings": warnings if isinstance(warnings, list) else [],
                    "error": (report.get("error") if isinstance(report, dict) else None) or "trend_unavailable",
                }
            trend = report.get("trend") or {}
            latest = report.get("latest") or {}
            quality = report.get("quality") or {}
            warnings = quality.get("warnings") or []
            return {
                "ok": True,
                "trend_label": trend.get("label"),
                "trend_score": trend.get("score"),
                "latest_close": latest.get("close"),
                "latest_date": latest.get("date") or quality.get("latest_date"),
                "quality_warnings": warnings if isinstance(warnings, list) else [],
            }
        except Exception as exc:
            return {
                "ok": False,
                "trend_label": None,
                "trend_score": None,
                "latest_close": None,
                "latest_date": None,
                "quality_warnings": ["trend_service_error"],
                "error": str(exc),
            }

    def _load_latest_and_paths(self) -> tuple[QlibOptionCPaths, Dict[str, Any]]:
        latest_path = self._safe_child("latest_signal.json")
        if not latest_path.exists():
            raise QlibOptionCSignalError("missing_latest_signal", f"latest_signal.json not found under {self.root}")
        latest_doc = self._load_json(latest_path, "missing_latest_signal")
        for key in ("asof", "run_dir", "top30_signals", "top50_signals"):
            if not latest_doc.get(key):
                raise QlibOptionCSignalError("blocked_validation_failed", f"latest_signal.json missing required field: {key}")
        self._require_true(latest_doc, "diagnostic_only", "latest_signal")
        self._require_true(latest_doc, "research_signal_not_order", "latest_signal")

        run_dir = self._safe_child(str(latest_doc["run_dir"]))
        paths = QlibOptionCPaths(
            root=self.root,
            latest=latest_path,
            run_dir=run_dir,
            top30=self._safe_child(str(latest_doc["top30_signals"])),
            top50=self._safe_child(str(latest_doc["top50_signals"])),
            summary=self._safe_child(str(Path(str(latest_doc["run_dir"])) / "signal_summary.json")),
            metadata=self._safe_child(str(Path(str(latest_doc["run_dir"])) / "run_metadata.json")),
        )
        return paths, latest_doc


    @staticmethod
    def _normalize_run_limit(limit: int) -> int:
        try:
            value = int(limit or 20)
        except Exception:
            value = 20
        return max(1, min(value, 100))

    @staticmethod
    def _normalize_run_status_filter(status: str) -> str:
        normalized = str(status or "all").strip().lower()
        if normalized not in {"all", "accepted", "blocked", "wait_state"}:
            raise QlibOptionCSignalError("invalid_status", "status must be one of: all, accepted, blocked, wait_state")
        return normalized

    @staticmethod
    def _validate_run_id(run_id: str) -> str:
        clean = str(run_id or "").strip()
        if not clean or not _RUN_ID_RE.match(clean) or clean in {".", ".."}:
            raise QlibOptionCSignalError("invalid_run_id", "run_id contains unsafe characters")
        if not clean.startswith("option_c_daily_signal_"):
            raise QlibOptionCSignalError("invalid_run_id", "run_id must identify an Option C daily signal run")
        return clean

    def _run_dir_for_id(self, run_id: str) -> Path:
        clean = self._validate_run_id(run_id)
        run_dir = self._safe_child(clean)
        if run_dir.is_symlink():
            raise QlibOptionCSignalError("path_outside_root", "run_dir symlink is not allowed")
        if not run_dir.exists() or not run_dir.is_dir():
            raise QlibOptionCSignalError("missing_run", f"qlib run not found: {clean}")
        return run_dir

    def _paths_for_run_id(self, run_id: str) -> tuple[QlibOptionCPaths, Dict[str, Any]]:
        run_dir = self._run_dir_for_id(run_id)
        relative_run = str(run_dir.relative_to(self.root))
        latest_doc = {
            "run_dir": relative_run,
            "top30_signals": str(Path(relative_run) / "top30_signals.csv"),
            "top50_signals": str(Path(relative_run) / "top50_signals.csv"),
        }
        paths = QlibOptionCPaths(
            root=self.root,
            latest=self._safe_child("latest_signal.json"),
            run_dir=run_dir,
            top30=self._safe_child(str(Path(relative_run) / "top30_signals.csv")),
            top50=self._safe_child(str(Path(relative_run) / "top50_signals.csv")),
            summary=self._safe_child(str(Path(relative_run) / "signal_summary.json")),
            metadata=self._safe_child(str(Path(relative_run) / "run_metadata.json")),
        )
        try:
            summary = self._load_json(paths.summary, "missing_signal_summary")
            metadata = self._load_json(paths.metadata, "missing_run_metadata")
            latest_doc["asof"] = summary.get("asof") or metadata.get("asof")
            latest_doc["diagnostic_only"] = summary.get("diagnostic_only")
            latest_doc["research_signal_not_order"] = summary.get("research_signal_not_order")
        except QlibOptionCSignalError:
            pass
        return paths, latest_doc

    def _run_list_item(self, run_dir: Path) -> Dict[str, Any]:
        paths, latest_doc = self._paths_for_run_id(run_dir.name)
        summary = self._load_json(paths.summary, "missing_signal_summary")
        metadata = self._load_json(paths.metadata, "missing_run_metadata")
        status = str(summary.get("status") or metadata.get("status") or "unknown")
        warnings = self._collect_run_warnings(summary=summary, metadata=metadata)
        accepted_validated = False
        if status == "accepted" and metadata.get("status") == "accepted":
            try:
                validation_warnings = self._validate_documents(paths=paths, latest_doc=latest_doc, summary=summary, metadata=metadata)
                warnings.extend([warning for warning in validation_warnings if warning not in warnings])
                accepted_validated = True
            except QlibOptionCSignalError as exc:
                status = exc.status
                warnings.extend(exc.warnings or [exc.message])
        return {
            "run_id": run_dir.name,
            "asof": summary.get("asof") or metadata.get("asof"),
            "status": status,
            "created_at": metadata.get("created_at") or summary.get("created_at"),
            "prediction_rows": summary.get("prediction_rows"),
            "top30_rows": summary.get("top30_rows"),
            "top50_rows": summary.get("top50_rows"),
            "recorder_id": metadata.get("frozen_recorder") or summary.get("recorder_id") or summary.get("source_model_recorder"),
            "diagnostic_only": summary.get("diagnostic_only"),
            "research_signal_not_order": summary.get("research_signal_not_order"),
            "accepted_validated": accepted_validated,
            "warnings": list(dict.fromkeys(warnings)),
            "trading": research_only_trading_flags(),
        }

    @staticmethod
    def _run_matches_status(item: Dict[str, Any], status_filter: str) -> bool:
        if status_filter == "all":
            return True
        status = str(item.get("status") or "")
        if status_filter == "accepted":
            return status == "accepted" and item.get("accepted_validated") is True
        if status_filter == "wait_state":
            return status.startswith("wait_state")
        if status_filter == "blocked":
            return status.startswith("blocked") or status in {"invalid_run_id", "path_outside_root", "missing_signal_summary", "missing_run_metadata"}
        return False

    @staticmethod
    def _current_utc_date(now: Optional[datetime]) -> date:
        if now is None:
            return datetime.now(timezone.utc).date()
        if now.tzinfo is None:
            return now.date()
        return now.astimezone(timezone.utc).date()

    @staticmethod
    def _parse_iso_datetime(raw: str) -> Optional[datetime]:
        text = str(raw or "").strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _parse_iso_date(raw: str) -> Optional[date]:
        try:
            return date.fromisoformat(str(raw or "").strip())
        except ValueError:
            return None

    def _freshness_payload(
        self,
        *,
        current_date: date,
        asof: str,
        created_at: str,
        status: str,
        accepted_validated: bool,
        validation_error: str,
    ) -> Dict[str, Any]:
        warnings: List[str] = []
        asof_date = self._parse_iso_date(asof)
        asof_age_days = None
        if asof_date is None:
            warnings.append("invalid_asof_date")
        else:
            asof_age_days = max(0, (current_date - asof_date).days)

        created_dt = self._parse_iso_datetime(created_at)
        created_age_hours = None
        if created_at and created_dt is None:
            warnings.append("invalid_created_at")
        elif created_dt is not None:
            current_dt = datetime.combine(current_date, datetime.min.time(), tzinfo=timezone.utc)
            created_age_hours = round(max(0.0, (current_dt - created_dt).total_seconds() / 3600.0), 2)

        stale = False
        stale_reason = ""
        if status != "accepted":
            stale = True
            stale_reason = "latest_not_accepted"
        elif not accepted_validated:
            stale = True
            stale_reason = "latest_not_validated"
        elif asof_age_days is None:
            stale = True
            stale_reason = "invalid_asof_date"
        elif asof_age_days > 3:
            stale = True
            stale_reason = "asof_age_gt_3"

        payload = {
            "current_utc_date": current_date.isoformat(),
            "asof_age_days": asof_age_days,
            "created_age_hours": created_age_hours,
            "stale": stale,
            "stale_reason": stale_reason,
        }
        if warnings:
            payload["warnings"] = warnings
        if validation_error and stale_reason in {"latest_not_accepted", "latest_not_validated"}:
            payload["validation_error"] = validation_error
        return payload

    @staticmethod
    def _summarize_runs(items: List[Dict[str, Any]]) -> Dict[str, Any]:
        summary = {"total_scanned": len(items), "accepted": 0, "wait_state": 0, "blocked": 0, "other": 0}
        for item in items:
            status = str(item.get("status") or "")
            if status == "accepted" and item.get("accepted_validated") is True:
                summary["accepted"] += 1
            elif status.startswith("wait_state"):
                summary["wait_state"] += 1
            elif status.startswith("blocked") or status in {"invalid_run_id", "path_outside_root", "missing_signal_summary", "missing_run_metadata"}:
                summary["blocked"] += 1
            else:
                summary["other"] += 1
        return summary

    @staticmethod
    def _has_newer_wait_state(items: List[Dict[str, Any]], latest_asof: str) -> bool:
        latest_date = QlibOptionCSignalReader._parse_iso_date(latest_asof)
        if latest_date is None:
            return False
        for item in items:
            status = str(item.get("status") or "")
            if not status.startswith("wait_state"):
                continue
            item_date = QlibOptionCSignalReader._parse_iso_date(str(item.get("asof") or ""))
            if item_date is not None and item_date > latest_date:
                return True
        return False

    @staticmethod
    def _collect_run_warnings(*, summary: Dict[str, Any], metadata: Dict[str, Any]) -> List[str]:
        warnings: List[str] = []
        for source in (summary, metadata):
            raw = source.get("warnings")
            if isinstance(raw, list):
                warnings.extend(str(item) for item in raw if item)
        reason = summary.get("reason") or metadata.get("reason") or summary.get("message") or metadata.get("message")
        if reason:
            warnings.append(str(reason))
        return list(dict.fromkeys(warnings))

    def _safe_child(self, raw: str) -> Path:
        normalized_raw = self._normalize_artifact_relative_path(str(raw or ""))
        path = Path(normalized_raw)
        if path.is_absolute():
            candidate = path.resolve(strict=False)
        else:
            candidate = (self.root / path).resolve(strict=False)
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise QlibOptionCSignalError("path_outside_root", f"qlib artifact path escapes root: {raw}") from exc
        return candidate

    @staticmethod
    def _normalize_artifact_relative_path(raw: str) -> str:
        clean = str(raw or "").strip()
        prefix = SIGNAL_REL_PREFIX + "/"
        if clean == SIGNAL_REL_PREFIX:
            return "."
        if clean.startswith(prefix):
            return clean[len(prefix):]
        return clean

    @staticmethod
    def _load_json(path: Path, missing_status: str) -> Dict[str, Any]:
        if not path.exists():
            raise QlibOptionCSignalError(missing_status, f"required qlib artifact is missing: {path}")
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception as exc:
            raise QlibOptionCSignalError("read_error", f"failed to read JSON artifact {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise QlibOptionCSignalError("blocked_validation_failed", f"JSON artifact must be an object: {path}")
        return data

    @staticmethod
    def _require_true(doc: Dict[str, Any], key: str, label: str) -> None:
        if doc.get(key) is not True:
            raise QlibOptionCSignalError("blocked_validation_failed", f"{label}.{key} must be true")

    @staticmethod
    def _require_false(doc: Dict[str, Any], key: str, label: str) -> None:
        if doc.get(key) is not False:
            raise QlibOptionCSignalError("blocked_validation_failed", f"{label}.{key} must be false")

    def _validate_documents(self, *, paths: QlibOptionCPaths, latest_doc: Dict[str, Any], summary: Dict[str, Any], metadata: Dict[str, Any]) -> List[str]:
        if summary.get("status") != "accepted":
            raise QlibOptionCSignalError(str(summary.get("status") or "blocked_validation_failed"), "signal_summary.status must be accepted")
        if metadata.get("status") != "accepted":
            raise QlibOptionCSignalError(str(metadata.get("status") or "blocked_validation_failed"), "run_metadata.status must be accepted")
        if str(metadata.get("frozen_recorder") or "") != EXPECTED_RECORDER_ID:
            raise QlibOptionCSignalError("blocked_validation_failed", "run_metadata.frozen_recorder does not match the frozen Option C recorder")
        run_id = str(metadata.get("run_id") or "")
        if not run_id or paths.run_dir.name != run_id:
            raise QlibOptionCSignalError("blocked_validation_failed", "latest_signal.run_dir must match run_metadata.run_id")
        self._require_path_under(paths.top30, paths.run_dir, "latest_signal.top30_signals")
        self._require_path_under(paths.top50, paths.run_dir, "latest_signal.top50_signals")
        self._validate_summary_paths(summary=summary, paths=paths)
        self._validate_summary_recorder(summary)
        if summary.get("prediction_rows") != 150:
            raise QlibOptionCSignalError("blocked_validation_failed", "signal_summary.prediction_rows must be 150")
        if summary.get("top30_rows") != 30:
            raise QlibOptionCSignalError("blocked_validation_failed", "signal_summary.top30_rows must be 30")
        if summary.get("top50_rows") != 50:
            raise QlibOptionCSignalError("blocked_validation_failed", "signal_summary.top50_rows must be 50")
        if float(summary.get("finite_prediction_share") or 0) != 1.0:
            raise QlibOptionCSignalError("blocked_validation_failed", "signal_summary.finite_prediction_share must be 1.0")
        self._require_true(summary, "diagnostic_only", "signal_summary")
        self._require_true(summary, "research_signal_not_order", "signal_summary")
        for key in ("paper_trading_started", "live_trading_started", "target_trades_generated", "executable_orders_generated"):
            self._require_false(summary, key, "signal_summary")
        for key in (
            "paper_trading_started",
            "live_trading_started",
            "target_trades_generated",
            "executable_orders_generated",
            "model_retraining_performed",
            "model_tuning_performed",
            "provider_switch_performed",
            "FinMind_fallback_used",
            "mixed_provider_fill_used",
        ):
            self._require_false(metadata, key, "run_metadata")
        if str(latest_doc.get("asof")) != str(summary.get("asof")) or str(summary.get("asof")) != str(metadata.get("asof")):
            raise QlibOptionCSignalError("blocked_validation_failed", "latest, summary and metadata asof fields must match")
        warnings: List[str] = []
        if "diagnostic_only" not in metadata or "research_signal_not_order" not in metadata:
            warnings.append("run_metadata_missing_research_only_flags_verified_by_latest_and_summary")
        elif metadata.get("diagnostic_only") is not True or metadata.get("research_signal_not_order") is not True:
            raise QlibOptionCSignalError("blocked_validation_failed", "run_metadata research-only flags must be true when present")
        return warnings

    def _read_csv(self, path: Path, *, bucket: str, asof: str) -> List[Dict[str, Any]]:
        if not path.exists():
            raise QlibOptionCSignalError("missing_signal_csv", f"required qlib CSV is missing: {path}")
        try:
            with path.open("r", encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh)
                fieldnames = set(reader.fieldnames or [])
                missing = sorted(_REQUIRED_CSV_COLUMNS - fieldnames)
                if missing:
                    raise QlibOptionCSignalError("blocked_validation_failed", f"{bucket} CSV missing columns: {', '.join(missing)}")
                rows = [self._normalize_row(row, bucket=bucket, row_number=i + 2, asof=asof) for i, row in enumerate(reader)]
        except QlibOptionCSignalError:
            raise
        except Exception as exc:
            raise QlibOptionCSignalError("read_error", f"failed to read CSV artifact {path}: {exc}") from exc
        return rows

    @staticmethod
    def _csv_bool(value: Any) -> bool:
        return str(value).strip().lower() in {"true", "1", "yes"}

    def _normalize_row(self, row: Dict[str, Any], *, bucket: str, row_number: int, asof: str) -> Dict[str, Any]:
        if not self._csv_bool(row.get("diagnostic_only")):
            raise QlibOptionCSignalError("blocked_validation_failed", f"{bucket} row {row_number} diagnostic_only must be true")
        if not self._csv_bool(row.get("research_signal_not_order")):
            raise QlibOptionCSignalError("blocked_validation_failed", f"{bucket} row {row_number} research_signal_not_order must be true")
        row_asof = str(row.get("asof") or "").strip()
        if row_asof != asof:
            raise QlibOptionCSignalError("blocked_validation_failed", f"{bucket} row {row_number} asof must match accepted run asof")
        recorder = str(row.get("source_model_recorder") or "").strip()
        if recorder != EXPECTED_RECORDER_ID:
            raise QlibOptionCSignalError("blocked_validation_failed", f"{bucket} row {row_number} source_model_recorder does not match frozen Option C recorder")
        instrument = str(row.get("instrument") or "").strip().upper()
        match = _INSTRUMENT_RE.match(instrument)
        if not match:
            raise QlibOptionCSignalError("blocked_validation_failed", f"{bucket} row {row_number} instrument must match TW + digits")
        try:
            rank = int(str(row.get("rank") or "").strip())
        except Exception as exc:
            raise QlibOptionCSignalError("blocked_validation_failed", f"{bucket} row {row_number} rank must be a positive integer") from exc
        if rank <= 0:
            raise QlibOptionCSignalError("blocked_validation_failed", f"{bucket} row {row_number} rank must be positive")
        try:
            qlib_score = float(str(row.get("score") or "").strip())
        except Exception as exc:
            raise QlibOptionCSignalError("blocked_validation_failed", f"{bucket} row {row_number} score must be finite") from exc
        if not math.isfinite(qlib_score):
            raise QlibOptionCSignalError("blocked_validation_failed", f"{bucket} row {row_number} score must be finite")
        return {
            "asof": row_asof,
            "instrument": instrument,
            "symbol": match.group(1),
            "qlib_score": qlib_score,
            "rank": rank,
            "bucket": bucket,
            "source_model_recorder": recorder,
            "diagnostic_only": True,
            "research_signal_not_order": True,
        }

    @staticmethod
    def _validate_row_counts(*, summary: Dict[str, Any], top30: List[Dict[str, Any]], top50: List[Dict[str, Any]]) -> None:
        if len(top30) != int(summary.get("top30_rows") or -1):
            raise QlibOptionCSignalError("blocked_validation_failed", "top30 CSV row count does not match signal_summary.top30_rows")
        if len(top50) != int(summary.get("top50_rows") or -1):
            raise QlibOptionCSignalError("blocked_validation_failed", "top50 CSV row count does not match signal_summary.top50_rows")
        QlibOptionCSignalReader._validate_rank_sequence(top30, expected=30, bucket="top30")
        QlibOptionCSignalReader._validate_rank_sequence(top50, expected=50, bucket="top50")

    @staticmethod
    def _validate_rank_sequence(rows: List[Dict[str, Any]], *, expected: int, bucket: str) -> None:
        ranks = [int(row.get("rank") or 0) for row in rows]
        expected_ranks = set(range(1, expected + 1))
        if len(ranks) != expected or set(ranks) != expected_ranks:
            raise QlibOptionCSignalError("blocked_validation_failed", f"{bucket} ranks must be exactly 1..{expected} without duplicates")

    @staticmethod
    def _require_path_under(path: Path, parent: Path, label: str) -> None:
        try:
            path.relative_to(parent)
        except ValueError as exc:
            raise QlibOptionCSignalError("blocked_validation_failed", f"{label} must be under latest_signal.run_dir") from exc

    def _validate_summary_paths(self, *, summary: Dict[str, Any], paths: QlibOptionCPaths) -> None:
        expected = {"top30_path": paths.top30, "top50_path": paths.top50}
        for key, expected_path in expected.items():
            if key not in summary or not summary.get(key):
                continue
            actual = self._safe_child(str(summary[key]))
            if actual != expected_path:
                raise QlibOptionCSignalError("blocked_validation_failed", f"signal_summary.{key} must match latest_signal artifact path")

    @staticmethod
    def _validate_summary_recorder(summary: Dict[str, Any]) -> None:
        for key in ("recorder_id", "source_model_recorder", "frozen_recorder", "model_recorder"):
            if key in summary and str(summary.get(key) or "") != EXPECTED_RECORDER_ID:
                raise QlibOptionCSignalError("blocked_validation_failed", f"signal_summary.{key} does not match the frozen Option C recorder")

    @staticmethod
    def _public_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
        allowed = {
            "status",
            "asof",
            "prediction_rows",
            "top30_rows",
            "top50_rows",
            "finite_prediction_share",
            "score_distribution",
            "top30_path",
            "top50_path",
            "diagnostic_only",
            "research_signal_not_order",
            "paper_trading_started",
            "live_trading_started",
            "target_trades_generated",
            "executable_orders_generated",
        }
        return {key: summary.get(key) for key in allowed if key in summary}


    @staticmethod
    def _public_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
        allowed = {
            "run_id",
            "status",
            "asof",
            "created_at",
            "config",
            "provider_uri",
            "market",
            "benchmark",
            "frozen_recorder",
            "dry_run",
            "allow_refresh",
            "diagnostic_only",
            "research_signal_not_order",
        }
        return {key: metadata.get(key) for key in allowed if key in metadata}
