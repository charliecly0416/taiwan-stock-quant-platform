"""Dynamic, isolated readonly replay task API."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.services.tw_stock_dynamic_replay import DynamicReplayError, create_replay, get_replay, replay_options


tw_stock_dynamic_replay_bp = Blueprint("tw_stock_dynamic_replay", __name__)


@tw_stock_dynamic_replay_bp.route("/readonly-replays/options", methods=["GET"])
def get_readonly_replay_options():
    try:
        return jsonify({"code": 1, "msg": "success", "data": replay_options()})
    except Exception as exc:
        return jsonify({"code": 0, "msg": "readonly replay options unavailable", "data": {"status": "unavailable", "error": str(exc)}}), 503


@tw_stock_dynamic_replay_bp.route("/readonly-replays", methods=["POST"])
def create_readonly_replay():
    try:
        payload = create_replay(request.get_json(silent=True) or {})
        return jsonify({"code": 1, "msg": "accepted", "data": payload}), 202 if payload.get("status") in {"QUEUED", "RUNNING"} else 200
    except DynamicReplayError as exc:
        return jsonify({"code": 0, "msg": exc.message, "data": {"ok": False, "status": exc.status, **exc.details}}), 404 if exc.status == "not_found" else 400


@tw_stock_dynamic_replay_bp.route("/readonly-replays/<run_id>", methods=["GET"])
def get_readonly_replay(run_id: str):
    try:
        return jsonify({"code": 1, "msg": "success", "data": get_replay(run_id)})
    except DynamicReplayError as exc:
        return jsonify({"code": 0, "msg": exc.message, "data": {"ok": False, "status": exc.status, **exc.details}}), 404 if exc.status == "not_found" else 400
