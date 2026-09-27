from __future__ import annotations

from pathlib import Path
import sys

from flask import Flask, jsonify
from flask_cors import CORS

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app, origins="*")

    @app.get("/api/health")
    def health():
        return jsonify({"status": "healthy", "product": "tw-stock-clean", "readonly": True})

    @app.get("/api/ready")
    def ready():
        return jsonify({"ready": True, "status": "ready", "readonly": True, "simulation_only": True})

    from app.routes.tw_stock import register_tw_stock_routes
    register_tw_stock_routes(app)
    return app
