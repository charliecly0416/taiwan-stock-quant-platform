"""Readonly Taiwan strategy snapshot API routes."""
from __future__ import annotations

from flask import Blueprint, jsonify

from app.services.readonly_strategy_snapshot import (
    ReadonlyStrategySnapshotError,
    load_readonly_strategy_snapshot,
)


readonly_strategy_snapshot_bp = Blueprint("readonly_strategy_snapshot", __name__)


@readonly_strategy_snapshot_bp.route("/readonly-strategy-snapshot", methods=["GET"])
def get_latest_readonly_strategy_snapshot():
    """Return the latest readonly modular strategy snapshot."""
    try:
        payload = load_readonly_strategy_snapshot()
        return jsonify({"code": 1, "msg": "success", "data": payload})
    except ReadonlyStrategySnapshotError as exc:
        status = 404 if exc.status == "missing_artifact" else 400
        return jsonify({"code": 0, "msg": exc.message, "data": {"ok": False, "status": exc.status}}), status


@readonly_strategy_snapshot_bp.route("/readonly-strategy-snapshot/<asof>", methods=["GET"])
def get_readonly_strategy_snapshot_by_asof(asof: str):
    """Return a readonly modular strategy snapshot by as-of date."""
    try:
        payload = load_readonly_strategy_snapshot(asof=asof)
        return jsonify({"code": 1, "msg": "success", "data": payload})
    except ReadonlyStrategySnapshotError as exc:
        status = 404 if exc.status == "missing_artifact" else 400
        return jsonify({"code": 0, "msg": exc.message, "data": {"ok": False, "status": exc.status}}), status
