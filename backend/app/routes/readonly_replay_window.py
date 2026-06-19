"""Readonly TW replay window query API routes."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.services.readonly_replay_window import ReadonlyReplayWindowError, default_replay_model_id, default_replay_strategy_rule, load_readonly_replay_window


readonly_replay_window_bp = Blueprint("readonly_replay_window", __name__)


@readonly_replay_window_bp.route("/readonly-replay-window", methods=["GET"])
def get_readonly_replay_window():
    """Return an audited readonly replay window after backend policy validation."""
    try:
        payload = load_readonly_replay_window(
            model_id=str(request.args.get("model_id") or default_replay_model_id()),
            strategy_rule=str(request.args.get("strategy_rule") or default_replay_strategy_rule()),
            start=str(request.args.get("start", "2026-01-01")),
            end=str(request.args.get("end", "2026-05-07")),
        )
        return jsonify({"code": 1, "msg": "success", "data": payload})
    except ReadonlyReplayWindowError as exc:
        status = 404 if exc.status in {"missing_artifact", "no_audited_replay_artifact_for_window"} else 400
        return jsonify({"code": 0, "msg": exc.message, "data": {"ok": False, "status": exc.status, **exc.details}}), status
