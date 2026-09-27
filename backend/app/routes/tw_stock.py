from __future__ import annotations

from datetime import date
import sys
from pathlib import Path

from flask import Flask, jsonify, request

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from clean_product.config import CONFIG_PATH, load_config  # noqa: E402
from clean_product.data import DataCatalog, DataError  # noqa: E402
from clean_product.orchestrator import run_daily  # noqa: E402
from clean_product.replay import replay  # noqa: E402


def register_tw_stock_routes(app: Flask) -> None:
    @app.get("/api/tw-stock/config")
    def product_config():
        config = load_config(CONFIG_PATH)
        return jsonify({
            "datasets": config.get("datasets", {}),
            "models": config.get("models", {}),
            "strategy": config.get("strategy"),
            "execution": config.get("execution"),
        })

    @app.get("/api/tw-stock/data/<name>")
    def data(name: str):
        try:
            frame = DataCatalog(load_config()).query(name, request.args.get("start"), request.args.get("end"))
        except DataError as exc:
            return jsonify({"status": "error", "message": str(exc)}), 404
        return jsonify({"status": "READY", "dataset": name, "rows": frame.to_dict("records")})

    @app.post("/api/tw-stock/daily")
    def daily():
        body = request.get_json(silent=True) or {}
        try:
            return jsonify(run_daily(body.get("asof") or date.today().isoformat(), dry_run=bool(body.get("dry_run", True))))
        except Exception as exc:
            return jsonify({"status": "BLOCKED", "message": str(exc), "readonly": True}), 422

    @app.get("/api/tw-stock/replay")
    def replay_route():
        start = request.args.get("start")
        end = request.args.get("end")
        model = request.args.get("model", "model_a")
        if not start or not end:
            return jsonify({"status": "error", "message": "start and end are required"}), 400
        try:
            config = load_config()
            frame = DataCatalog(config).query("prices", start, end, allow_fixture=True)
            return jsonify(replay(config, frame, model, start, end))
        except Exception as exc:
            return jsonify({"status": "BLOCKED", "message": str(exc), "readonly": True}), 422
