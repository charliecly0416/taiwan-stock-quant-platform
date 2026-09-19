"""GET-only route for the artifact-backed model/strategy comparison workbench."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.services.readonly_model_strategy_comparison import (
    ReadonlyModelStrategyComparisonError,
    load_readonly_model_strategy_comparison,
)


readonly_model_strategy_comparison_bp = Blueprint("readonly_model_strategy_comparison", __name__)


@readonly_model_strategy_comparison_bp.route("/readonly/model-strategy-comparison", methods=["GET"])
def get_readonly_model_strategy_comparison():
    try:
        payload = load_readonly_model_strategy_comparison(
            model_id=request.args.get("model_id"),
            strategy_id=request.args.get("strategy_id"),
            window_id=request.args.get("window_id"),
        )
        return jsonify({"code": 1, "msg": "success", "data": payload})
    except ReadonlyModelStrategyComparisonError as exc:
        http_status = 404 if exc.status == "missing_artifact" else 400
        return jsonify({"code": 0, "msg": exc.message, "data": {"ok": False, "status": exc.status, **exc.details}}), http_status
