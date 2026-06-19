"""Unified read-only current strategy context for TW stock frontend modules."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from app.services.phase_yz3_productization_status import load_yz3_productization_status, resolve_latest_yz_signal_asof
from app.services.readonly_strategy_snapshot import ReadonlyStrategySnapshotError, load_readonly_strategy_snapshot
from app.services.tw_stock_artifact_registry import registry_get, registry_path


ROOT = Path(__file__).resolve().parents[3]
SIGNAL_ROOT = registry_path("artifacts", "signal_root")
YZ2_ROOT = registry_path("artifacts", "yz2_feature_root")
YZ2R_ROOT = registry_path("artifacts", "yz2r_execution_price_readiness_root")
READONLY_STRATEGY_LATEST = registry_path("artifacts", "readonly_strategy_latest")
MODEL_A = str(registry_get("models", "base_model_id"))
MODEL_B = str(registry_get("models", "treatment_model_id"))
LEGACY_DISPLAY_MODEL_B = str(registry_get("models", "treatment_display_model_id", default=MODEL_B))
DEFAULT_STRATEGY = str(registry_get("strategies", "default_strategy_rule"))
MODEL_A_SUBDIR = str(registry_get("artifacts", "model_a_subdir", default="model_a"))
MODEL_B_PREFERRED_SUBDIR = str(registry_get("artifacts", "model_b_preferred_subdir", default="model_b_yz2"))
MODEL_B_FALLBACK_SUBDIR = str(registry_get("artifacts", "model_b_fallback_subdir", default="model_b"))


class CurrentStrategyContextError(Exception):
    """Raised when the current strategy context cannot be loaded."""

    def __init__(self, status: str, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise CurrentStrategyContextError("missing_artifact", f"Missing artifact: {_rel(path)}")
    return json.loads(path.read_text(encoding="utf-8"))


def _optional_json(path: Path) -> dict[str, Any]:
    try:
        return _load_json(path)
    except Exception:
        return {}


def _manifest_signal_path(manifest_path: Path) -> Path:
    manifest = _load_json(manifest_path)
    files = manifest.get("files") or {}
    return manifest_path.parent / str(files.get("signals") or "signals.csv")


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise CurrentStrategyContextError("missing_artifact", f"Missing CSV artifact: {_rel(path)}")
    with path.open("r", encoding="utf-8", newline="") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def _num(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _int(value: Any, default: int | None = None) -> int | None:
    parsed = _num(value, None)
    if parsed is None:
        return default
    return int(parsed)


def _sort_by_rank(rows: list[dict[str, Any]], rank_field: str) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: (_int(row.get(rank_field), 999999), str(row.get("instrument") or row.get("symbol") or "")))


def _model_a_manifest(signal_asof: str) -> Path:
    return SIGNAL_ROOT / signal_asof / MODEL_A_SUBDIR / "manifest.json"


def _model_b_manifest(signal_asof: str) -> Path:
    preferred = SIGNAL_ROOT / signal_asof / MODEL_B_PREFERRED_SUBDIR / "manifest.json"
    fallback = SIGNAL_ROOT / signal_asof / MODEL_B_FALLBACK_SUBDIR / "manifest.json"
    return preferred if preferred.exists() else fallback


def _ranking_payload(signal_asof: str) -> dict[str, Any]:
    model_a_manifest = _model_a_manifest(signal_asof)
    model_b_manifest = _model_b_manifest(signal_asof)
    if not model_a_manifest.exists():
        raise CurrentStrategyContextError("missing_model_a", f"Missing Model A manifest for {signal_asof}")
    if not model_b_manifest.exists():
        raise CurrentStrategyContextError("missing_model_b", f"Missing Model B manifest for {signal_asof}")

    model_a = _load_json(model_a_manifest)
    model_b = _load_json(model_b_manifest)
    model_a_rows = _read_csv_rows(_manifest_signal_path(model_a_manifest))
    model_b_rows = _read_csv_rows(_manifest_signal_path(model_b_manifest))
    model_a_by_symbol = {str(row.get("instrument") or ""): row for row in model_a_rows}

    ltr_rows = []
    for row in _sort_by_rank(model_b_rows, "score_rank"):
        symbol = str(row.get("instrument") or "")
        qlib = model_a_by_symbol.get(symbol, {})
        item = {
            "instrument": symbol,
            "symbol": symbol,
            "signal_asof": row.get("signal_asof") or signal_asof,
            "available_at": row.get("available_at") or row.get("signal_asof") or signal_asof,
            "ltr_score_rank": _int(row.get("score_rank")),
            "ltr_buy_score": _num(row.get("buy_score")),
            "ltr_raw_score": _num(row.get("raw_score")),
            "qlib_candidate_rank": _int(row.get("candidate_rank")),
            "qlib_full_rank": _int(row.get("full_qlib_rank")),
            "qlib_score_rank": _int(qlib.get("score_rank") or qlib.get("full_qlib_rank") or row.get("full_qlib_rank")),
            "qlib_buy_score": _num(qlib.get("buy_score") or qlib.get("raw_score")),
            "qlib_raw_score": _num(qlib.get("raw_score")),
            "in_qlib_top50": (_int(row.get("full_qlib_rank"), 999999) or 999999) <= 50,
            "source_model_signal": _rel(model_b_manifest),
            "source_base_qlib_signal": _rel(model_a_manifest),
        }
        ltr_rows.append(item)

    qlib_rows = []
    for row in _sort_by_rank(model_a_rows, "full_qlib_rank"):
        rank = _int(row.get("full_qlib_rank"))
        qlib_rows.append({
            "instrument": row.get("instrument"),
            "symbol": row.get("instrument"),
            "signal_asof": row.get("signal_asof") or signal_asof,
            "available_at": row.get("available_at") or row.get("signal_asof") or signal_asof,
            "qlib_full_rank": rank,
            "qlib_score_rank": _int(row.get("score_rank") or rank),
            "qlib_candidate_rank": _int(row.get("candidate_rank")),
            "qlib_buy_score": _num(row.get("buy_score")),
            "qlib_raw_score": _num(row.get("raw_score")),
            "in_qlib_top50": (rank or 999999) <= 50,
            "source_base_qlib_signal": _rel(model_a_manifest),
        })

    return {
        "signal_asof": signal_asof,
        "model_a": {
            "model_id": model_a.get("model_id") or MODEL_A,
            "manifest": _rel(model_a_manifest),
            "row_count": model_a.get("row_count"),
            "signals": _rel(_manifest_signal_path(model_a_manifest)),
        },
        "model_b": {
            "model_id": model_b.get("model_id") or MODEL_B,
            "display_model_id": LEGACY_DISPLAY_MODEL_B,
            "manifest": _rel(model_b_manifest),
            "row_count": model_b.get("row_count"),
            "signals": _rel(_manifest_signal_path(model_b_manifest)),
            "source_feature_artifact": model_b.get("source_feature_artifact"),
            "source_model_artifact": model_b.get("source_model_artifact"),
        },
        "ltr_top50": ltr_rows,
        "ltr_top10": ltr_rows[:10],
        "qlib_top150": qlib_rows,
        "qlib_top50": qlib_rows[:50],
        "field_contract": {
            "ltr_score_rank": "rank after orthogonal LTR rerank within qlib top50; lower is better",
            "qlib_candidate_rank": "base qlib rank inside top50 before LTR rerank",
            "qlib_full_rank": "base qlib rank across the 150-stock production universe",
            "buy_score": "LTR modules should use ltr_buy_score; raw qlib modules should use qlib_buy_score",
        },
    }


def _snapshot_summary() -> dict[str, Any]:
    try:
        payload = load_readonly_strategy_snapshot()
        snapshot = payload.get("snapshot") or {}
        return {
            "ok": True,
            "asof": snapshot.get("asof") or payload.get("asof"),
            "signal_asof": snapshot.get("signal_asof") or snapshot.get("data_asof"),
            "target_date": snapshot.get("target_date") or snapshot.get("asof"),
            "model_id": snapshot.get("canonical_model_id") or snapshot.get("model_id"),
            "display_model_id": snapshot.get("model_id"),
            "strategy_rule": snapshot.get("strategy_rule"),
            "top_candidates": snapshot.get("top_candidates") or [],
            "exit_candidates": snapshot.get("exit_candidates") or [],
            "manifest": (payload.get("sources") or {}).get("manifest"),
            "latest_pointer": payload.get("latest_pointer"),
            "validation": payload.get("validation"),
            "checksum": payload.get("checksum"),
        }
    except ReadonlyStrategySnapshotError as exc:
        return {"ok": False, "status": exc.status, "message": exc.message, "latest": _rel(READONLY_STRATEGY_LATEST)}


def _asof_status(context_signal_asof: str, payloads: dict[str, Any]) -> dict[str, Any]:
    checks = []
    for name, payload in payloads.items():
        if not payload.get("ok"):
            checks.append({"name": name, "status": "missing", "details": payload.get("message") or payload.get("status") or "not available"})
            continue
        candidate = payload.get("signal_asof") or payload.get("data_asof") or payload.get("run_asof")
        checks.append({
            "name": name,
            "status": "pass" if candidate == context_signal_asof else "stale_or_mismatch",
            "expected_signal_asof": context_signal_asof,
            "actual_asof": candidate,
        })
    return {
        "status": "pass" if all(row["status"] == "pass" for row in checks) else "mixed",
        "checks": checks,
    }


def load_current_strategy_context(signal_asof: str | None = None) -> dict[str, Any]:
    """Load one read-only context that frontend modules can share."""
    resolved_signal_asof = resolve_latest_yz_signal_asof(signal_asof)
    if not resolved_signal_asof:
        raise CurrentStrategyContextError("missing_signal_asof", "No YZ strict E4 signal artifact is available")

    rankings = _ranking_payload(resolved_signal_asof)
    productization = load_yz3_productization_status(signal_asof=resolved_signal_asof)
    snapshot = _snapshot_summary()
    yz2_feature_manifest = YZ2_ROOT / resolved_signal_asof / "manifest.json"
    yz2r_manifest = YZ2R_ROOT / resolved_signal_asof / "manifest.json"
    context_asof = snapshot.get("asof") if snapshot.get("ok") and snapshot.get("signal_asof") == resolved_signal_asof else resolved_signal_asof
    target_date = snapshot.get("target_date") if snapshot.get("ok") and snapshot.get("signal_asof") == resolved_signal_asof else productization.get("execution_price_readiness", {}).get("target_next_trading_day")

    audit_payloads = {
        "readonly_strategy_snapshot": snapshot,
        "phase_yz_productization": {"ok": productization.get("ok"), "signal_asof": productization.get("signal_asof")},
    }
    asof_audit = _asof_status(resolved_signal_asof, audit_payloads)
    return {
        "ok": True,
        "schema_version": "tw_current_strategy_context_v1",
        "readonly_only": True,
        "not_order": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "production_trade_enabled": False,
        "context": {
            "context_asof": context_asof,
            "display_asof": context_asof,
            "signal_asof": resolved_signal_asof,
            "target_date": target_date or "",
            "default_model_id": MODEL_B,
            "display_model_id": LEGACY_DISPLAY_MODEL_B,
            "base_model_id": MODEL_A,
            "strategy_rule": DEFAULT_STRATEGY,
            "ranking_source": "ltr_rerank_within_qlib_top50",
            "candidate_boundary": "qlib_top50",
            "execution_price_mode": "next_open",
        },
        "rankings": rankings,
        "strategy_snapshot": snapshot,
        "productization_status": productization,
        "paper_portfolio_context": {
            "apply_allowed": productization.get("paper_apply_allowed") is True,
            "blocked_reason": productization.get("paper_apply_blocked_reason") or "",
            "execution_price_readiness": productization.get("execution_price_readiness") or {},
            "source_status": "phase_yz_productization_status",
        },
        "source_manifests": {
            "model_a": rankings["model_a"]["manifest"],
            "model_b": rankings["model_b"]["manifest"],
            "orthogonal_feature_package": _rel(yz2_feature_manifest) if yz2_feature_manifest.exists() else "",
            "execution_price_readiness": _rel(yz2r_manifest) if yz2r_manifest.exists() else "",
            "readonly_strategy_snapshot": snapshot.get("manifest") or "",
        },
        "consistency_audit": {
            "asof_alignment": asof_audit,
            "frontend_guidance": {
                "primary_context_source": "this endpoint",
                "use_ltr_for_strategy_snapshot": True,
                "use_qlib_top50_for_base_model_views": True,
                "legacy_daily_readonly_latest_removed": True,
            },
        },
        "no_write_guarantees": {
            "read_only_http_method": True,
            "reads_static_artifacts_only": True,
            "does_not_touch_provider_accepted_latest": True,
            "does_not_touch_qlib_accepted_latest": True,
            "does_not_touch_monitor_or_alerts": True,
            "does_not_touch_broker_or_orders": True,
        },
    }
