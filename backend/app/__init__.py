from __future__ import annotations

from pathlib import Path
import sys

from flask import Flask, jsonify, send_from_directory, abort
from flask_cors import CORS

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(config or {})
    CORS(app, origins="*")

    @app.get("/api/health")
    def health():
        return jsonify({"status": "healthy", "product": "tw-stock-clean", "readonly": True})

    @app.get("/api/ready")
    def ready():
        from clean_product.service import ProductService
        try:
            result = ProductService().readiness()
        except Exception as exc:
            result = {"ready": False, "status": "blocked", "readonly": True, "simulation_only": True,
                      "reasons": [f"CONFIGURATION_UNAVAILABLE: {type(exc).__name__}"]}
        return jsonify(result), 200 if result["ready"] else 503

    from .routes.tw_stock import register_tw_stock_routes
    register_tw_stock_routes(app)
    from .routes.paper import register_paper_routes
    register_paper_routes(app)

    # One production WSGI entrypoint serves the built UI and the API.
    @app.get('/')
    @app.get('/<path:filename>')
    def frontend(filename='index.html'):
        if filename.startswith('api/'):
            abort(404)
        directory = ROOT / 'frontend' / 'dist'
        if filename in ('tw-stock-monitor', 'tw-stock-monitor/'):
            filename = 'index.html'
        response = send_from_directory(directory, filename)
        response.headers['Cache-Control'] = ('public, max-age=31536000, immutable'
                                             if filename.startswith('assets/') else 'no-cache')
        return response
    return app
