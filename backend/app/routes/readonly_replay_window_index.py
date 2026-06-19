"""Readonly replay window index API routes."""
from __future__ import annotations

from flask import Blueprint, jsonify

from app.services.readonly_replay_window_index import ReadonlyReplayWindowIndexError, load_readonly_replay_window_index


readonly_replay_window_index_bp = Blueprint("readonly_replay_window_index", __name__)


@readonly_replay_window_index_bp.route("/readonly-replay-window-index", methods=["GET"])
def get_readonly_replay_window_index():
    try:
        payload = load_readonly_replay_window_index()
        return jsonify({"code": 1, "msg": "success", "data": payload})
    except ReadonlyReplayWindowIndexError as exc:
        status = 404 if exc.status == "missing_artifact" else 400
        return jsonify({"code": 0, "msg": exc.message, "data": {"ok": False, "status": exc.status, **exc.details}}), status
