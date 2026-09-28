from __future__ import annotations

from datetime import date
from calendar import monthrange
import json
import sys
from pathlib import Path

from flask import Flask, jsonify, request

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

from clean_product.config import load_config  # noqa: E402
from clean_product.data import DataCatalog, DataError  # noqa: E402
from clean_product.service import ProductService  # noqa: E402


def _error(exc: Exception, status: int = 422):
    return jsonify({"status": "BLOCKED", "message": str(exc), "readonly": True, "simulation_only": True}), status


def _date_range_arg(end: str | None, start: str | None) -> tuple[str, str]:
    """Validate optional market date arguments before entering the service."""
    end_value = end or date.today().isoformat()
    end_date = date.fromisoformat(end_value)
    prior_year = end_date.year - 1
    start_value = start or end_date.replace(
        year=prior_year, day=min(end_date.day, monthrange(prior_year, end_date.month)[1])
    ).isoformat()
    start_date = date.fromisoformat(start_value)
    if start_date > end_date:
        raise ValueError("start must be on or before end")
    return start_value, end_value


def register_tw_stock_routes(app: Flask) -> None:
    @app.before_request
    def validate_research_query():
        if not request.path.startswith("/api/tw-stock/"):
            return None
        try:
            parsed = {}
            for name in ("date", "start", "end"):
                if name in request.args:
                    value = request.args[name]
                    parsed[name] = date.fromisoformat(value)
                    if parsed[name].isoformat() != value:
                        raise ValueError(f"{name} must use YYYY-MM-DD")
            if "start" in parsed and "end" in parsed:
                if parsed["start"] > parsed["end"]:
                    raise ValueError("start must be on or before end")
                if request.path in ("/api/tw-stock/replay", "/api/tw-stock/compare"):
                    if (parsed["end"] - parsed["start"]).days > 730:
                        raise ValueError("replay window cannot exceed 730 calendar days")
            if request.path == "/api/tw-stock/compare" and ("start" in parsed) != ("end" in parsed):
                raise ValueError("comparison replay requires both start and end")
            selected = [request.args[key] for key in ("model", "left", "right") if key in request.args]
            if selected:
                known = load_config().get("models", {})
                for model in selected:
                    if model not in known:
                        raise ValueError(f"unknown model: {model}")
            for name, maximum in (("limit", 150), ("lookback", 60)):
                if name in request.args and not 1 <= int(request.args[name]) <= maximum:
                    raise ValueError(f"{name} must be between 1 and {maximum}")
        except (ValueError, TypeError) as exc:
            return _error(exc)
        return None

    @app.get("/api/tw-stock/config")
    def product_config():
        config = load_config()
        payload = {key: config.get(key) for key in ("product", "datasets", "models", "strategy", "execution", "simulation")}
        payload.update(readonly=True, simulation_only=True)
        return jsonify(payload)

    @app.get("/api/tw-stock/overview")
    def overview():
        try: return jsonify(ProductService().overview())
        except Exception as exc: return _error(exc)

    @app.get("/api/tw-stock/rankings")
    def rankings():
        try:
            limit = int(request.args.get("limit", 50))
            if not 1 <= limit <= 150:
                raise ValueError("limit must be between 1 and 150")
            return jsonify(ProductService().rankings(request.args.get("model", "model_a"), request.args.get("date"), limit))
        except Exception as exc: return _error(exc)

    @app.get("/api/tw-stock/compare")
    def compare():
        try: return jsonify(ProductService().compare(request.args.get("left", "model_a"), request.args.get("right", "model_a_plus_b"), request.args.get("date"), request.args.get("start"), request.args.get("end")))
        except Exception as exc: return _error(exc)

    @app.get("/api/tw-stock/strategy")
    def strategy():
        try: return jsonify(ProductService().strategy(request.args.get("model", "model_a"), request.args.get("date")))
        except Exception as exc: return _error(exc)

    @app.get("/api/tw-stock/ranking-changes")
    def ranking_changes():
        try: return jsonify(ProductService().ranking_changes(request.args.get("model", "model_a"), request.args.get("date"), int(request.args.get("lookback", 1))))
        except Exception as exc: return _error(exc)

    @app.get("/api/tw-stock/cross-analysis")
    def cross_analysis():
        try: return jsonify(ProductService().cross_analysis(request.args.get("model", "model_a"), request.args.get("date"), min(int(request.args.get("limit", 50)), 50)))
        except Exception as exc: return _error(exc)

    @app.get("/api/tw-stock/market/<symbol>")
    def market(symbol: str):
        try:
            start, end = _date_range_arg(request.args.get("end"), request.args.get("start"))
            return jsonify(ProductService().market(symbol, start, end))
        except Exception as exc: return _error(exc)

    @app.get("/api/tw-stock/paper")
    def paper():
        try: return jsonify(ProductService().paper_state(request.args.get("model", "model_a"), request.args.get("date")))
        except Exception as exc: return _error(exc)

    @app.get("/api/tw-stock/agent/context")
    def agent_context():
        try: return jsonify(ProductService().agent_context(request.args.get("model", "model_a"), request.args.get("date")))
        except Exception as exc: return _error(exc)

    @app.get("/api/tw-stock/agent/explain/<symbol>")
    def agent_explain(symbol: str):
        try: return jsonify(ProductService().explain(symbol, request.args.get("model", "model_a"), request.args.get("date")))
        except Exception as exc: return _error(exc)

    @app.post("/api/tw-stock/agent/simple-chat")
    def agent_simple_chat():
        from clean_product.agent import simple_chat
        payload = request.get_json(silent=True)
        if (not isinstance(payload, dict) or set(payload) - {"question", "symbol", "maxItems", "date"}):
            return _error(ValueError("only question, symbol, maxItems and date are accepted"))
        try:
            config = app.config.get('PRODUCT_CONFIG') or load_config()
            service = ProductService(config)
            config = service.config
            if app.config.get('AGENT_REMOTE_DISABLED') is True:
                config = {**config, 'agent': {**config.get('agent', {}), 'remote_enabled': False}}
            asof = payload.get("date") or service.latest_asof()
            if not asof: raise ValueError("no provider trading date available")
            if not isinstance(asof, str) or date.fromisoformat(asof).isoformat() != asof:
                raise ValueError('date must use YYYY-MM-DD')
            return jsonify(simple_chat(config, payload.get("question"), asof,
                                       symbol=payload.get("symbol", ""), max_items=payload.get("maxItems", 5)))
        except (ValueError, TypeError) as exc: return _error(exc)

    @app.get("/api/tw-stock/data-status")
    def data_status():
        return jsonify({"status": "READY", "datasets": DataCatalog(load_config()).status(), "readonly": True, "simulation_only": True})

    @app.get("/api/tw-stock/operations/latest")
    def operations():
        try: return jsonify(ProductService().operations())
        except Exception as exc: return _error(exc)

    @app.get("/api/tw-stock/data/<name>")
    def data(name: str):
        try:
            config = load_config()
            catalog = DataCatalog(config)
            spec = config.get("datasets", {}).get(name, {})
            if spec.get("source") == "qlib_provider":
                frame = catalog.query_local_source(name, request.args.get("start"), request.args.get("end"))
            else:
                frame = catalog.query(name, request.args.get("start"), request.args.get("end"))
        except DataError as exc:
            return _error(exc, 404)
        except (ValueError, OSError) as exc:
            return _error(exc)
        rows = json.loads(frame.to_json(orient="records", date_format="iso"))
        return jsonify({"status": "READY", "dataset": name, "rows": rows, "readonly": True, "simulation_only": True})

    @app.get("/api/tw-stock/replay")
    def replay_route():
        start, end = request.args.get("start"), request.args.get("end")
        if not start or not end: return _error(ValueError("start and end are required"), 400)
        try:
            start_date, end_date = date.fromisoformat(start), date.fromisoformat(end)
            if start_date > end_date:
                raise ValueError("start must be on or before end")
            if (end_date - start_date).days > 730:
                raise ValueError("replay window cannot exceed 730 calendar days")
            return jsonify(ProductService().run_replay(request.args.get("model", "model_a"), start, end))
        except Exception as exc: return _error(exc)
