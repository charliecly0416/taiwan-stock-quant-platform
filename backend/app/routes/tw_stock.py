"""Read-only Taiwan stock research routes."""
from __future__ import annotations

import json
import os
import time
from datetime import date

from flask import Blueprint, g, jsonify, render_template_string, request

from app.services.tw_stock_trend import TWStockTrendService
from app.services.tw_stock_qlib_option_c import (
    QlibOptionCSignalError,
    QlibOptionCSignalReader,
    QlibOptionCRankChangeReader,
    blocked_payload as qlib_blocked_payload,
    research_only_trading_flags,
)
from app.services.tw_stock_qlib_option_c_ops import option_c_ops_runner
from app.services.tw_stock_qlib_option_c_scheduler import option_c_dry_run_scheduler
from app.services.tw_stock_qlib_option_c_normal_publish import option_c_normal_publish_gate
from app.services.tw_stock_qlib_option_c_accepted_latest_scheduler import option_c_accepted_latest_scheduler
from app.services.tw_stock_qlib_option_c_eod_pipeline import option_c_eod_pipeline
from app.services.tw_stock_qlib_option_c_eod_automation import option_c_eod_automation_scheduler
from app.services.tw_stock_daily_auto_update_status import TWStockDailyAutoUpdateStatusService
from app.services.tw_stock_sim_account import TWStockSimAccountService
from app.services.tw_stock_cross_analysis import TWStockCrossAnalysisService
from app.services.tw_stock_rank_tech_cross import TWStockRankTechCrossService
from app.services.tw_stock_observation_replay import TWStockObservationReplayService
from app.services.tw_stock_portfolio_replay import TWStockPortfolioReplayService
from app.services.tw_stock_cross_analysis_history import TWStockCrossAnalysisHistoryService
from app.services.tw_stock_agent_context import TWStockAgentContextService
from app.services.tw_stock_agent_chat import TWStockAgentChatService
from app.services import tw_stock_monitor as monitor_service
from app.utils.db import get_db_connection
from app.utils.auth import login_required
from app.utils.logger import get_logger

logger = get_logger(__name__)

tw_stock_bp = Blueprint("tw_stock", __name__)
trend_service = TWStockTrendService()
cross_analysis_service = TWStockCrossAnalysisService(trend_service=trend_service)
rank_tech_cross_service = TWStockRankTechCrossService(trend_service=trend_service)
observation_replay_service = TWStockObservationReplayService(rank_tech_service=rank_tech_cross_service)
portfolio_replay_service = TWStockPortfolioReplayService(observation_service=observation_replay_service)
cross_analysis_history_service = TWStockCrossAnalysisHistoryService(cross_service=cross_analysis_service)
tw_stock_agent_service = TWStockAgentContextService(cross_service=cross_analysis_service)
tw_stock_agent_chat_service = TWStockAgentChatService(context_service=tw_stock_agent_service)
daily_auto_update_status_service = TWStockDailyAutoUpdateStatusService()
tw_stock_sim_account_service = TWStockSimAccountService()



def _current_user_id(default: int = 0) -> int:
    try:
        return int(getattr(g, "user_id", default) or default)
    except Exception:
        return int(default)


def _sim_response(payload: dict):
    status = str((payload or {}).get("status") or "")
    http_status = 200
    if status == "not_found":
        http_status = 404
    elif status in {"invalid_initial_cash", "invalid_symbol", "invalid_side", "invalid_quantity", "invalid_lot_size", "unsupported_source_type"}:
        http_status = 400
    return jsonify({"code": 1 if payload.get("ok") else 0, "msg": "success" if payload.get("ok") else payload.get("message", status), "data": payload}), http_status


def _parse_limit() -> int:
    try:
        return max(20, min(int(request.args.get("limit", 120)), 500))
    except Exception:
        return 120



def _parse_bool_arg(*names: str, default: bool = False) -> bool:
    raw = None
    for name in names:
        if request.args.get(name) is not None:
            raw = request.args.get(name)
            break
    if raw is None:
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def _parse_quant_trend_limit() -> int:
    try:
        return max(20, min(int(request.args.get("trendLimit") or request.args.get("trend_limit") or 120), 500))
    except Exception:
        return 120


def _parse_technical_strategies() -> list:
    raw = request.args.get("technicalStrategies") or request.args.get("technical_strategies") or ""
    if not raw:
        return ["ma", "rsi", "macd", "bollinger"]
    valid = {"ma", "rsi", "macd", "bollinger"}
    out = []
    for part in str(raw).split(","):
        item = part.strip().lower()
        if item in valid and item not in out:
            out.append(item)
    return out or ["ma", "rsi", "macd", "bollinger"]

def _parse_as_of():
    raw = (request.args.get("as_of") or request.args.get("asOf") or "").strip()
    if not raw:
        return None
    return date.fromisoformat(raw)


def _current_user_has_option_c_ops_permission() -> bool:
    role = getattr(g, "user_role", "user")
    if role == "admin":
        return True
    try:
        from app.services.user_service import get_user_service

        permissions = get_user_service().get_user_permissions(role)
    except Exception:
        permissions = []
    return "tw_stock_qlib_ops" in permissions or "tw_stock_ops" in permissions


def _require_option_c_ops_permission():
    if _current_user_has_option_c_ops_permission():
        return None
    return jsonify({"code": 403, "msg": "Option C ops admin or tw_stock_qlib_ops permission required", "data": None}), 403



@tw_stock_bp.route("/sim/accounts", methods=["GET"])
@login_required
def list_tw_stock_sim_accounts():
    """List current user's TWStock simulation accounts."""
    payload = tw_stock_sim_account_service.list_accounts(user_id=_current_user_id())
    return _sim_response(payload)


@tw_stock_bp.route("/sim/accounts", methods=["POST"])
@login_required
def create_tw_stock_sim_account():
    """Create a TWStock simulation account; no real securities account is touched."""
    data = _request_json()
    payload = tw_stock_sim_account_service.create_account(
        user_id=_current_user_id(),
        name=data.get("name") or "台股研究模拟账户",
        initial_cash=data.get("initial_cash") or data.get("initialCash") or 1000000,
    )
    return _sim_response(payload)


@tw_stock_bp.route("/sim/accounts/<account_uid>", methods=["GET"])
@login_required
def get_tw_stock_sim_account(account_uid: str):
    """Return one TWStock simulation account with cash, value and return."""
    payload = tw_stock_sim_account_service.get_account(account_uid=account_uid, user_id=_current_user_id())
    return _sim_response(payload)


@tw_stock_bp.route("/sim/accounts/<account_uid>/positions", methods=["GET"])
@login_required
def get_tw_stock_sim_positions(account_uid: str):
    """Return open simulation-only TWStock positions."""
    payload = tw_stock_sim_account_service.positions(account_uid=account_uid, user_id=_current_user_id())
    return _sim_response(payload)


@tw_stock_bp.route("/sim/accounts/<account_uid>/trades", methods=["GET"])
@login_required
def get_tw_stock_sim_trades(account_uid: str):
    """Return simulation-only TWStock fills."""
    try:
        limit = max(1, min(int(request.args.get("limit") or 100), 500))
    except Exception:
        limit = 100
    payload = tw_stock_sim_account_service.trades(account_uid=account_uid, user_id=_current_user_id(), limit=limit)
    return _sim_response(payload)


@tw_stock_bp.route("/sim/orders/draft", methods=["POST"])
@login_required
def draft_tw_stock_sim_order():
    """Create a manual simulation draft using latest archived close as reference."""
    data = _request_json()
    payload = tw_stock_sim_account_service.draft(
        user_id=_current_user_id(),
        account_uid=data.get("account_uid") or data.get("accountUid") or "",
        symbol=data.get("symbol") or "",
        side=data.get("side") or "",
        quantity=data.get("quantity") or data.get("qty") or 0,
        source_type=data.get("source_type") or data.get("sourceType") or "manual",
        source_context=data.get("source_context") or data.get("sourceContext") or {},
    )
    return _sim_response(payload)


@tw_stock_bp.route("/sim/orders/<sim_order_uid>/confirm", methods=["POST"])
@login_required
def confirm_tw_stock_sim_order(sim_order_uid: str):
    """Confirm a manual simulation draft and write a simulation fill."""
    payload = tw_stock_sim_account_service.confirm(user_id=_current_user_id(), sim_order_uid=sim_order_uid)
    return _sim_response(payload)


@tw_stock_bp.route("/sim/orders/<sim_order_uid>/cancel", methods=["POST"])
@login_required
def cancel_tw_stock_sim_order(sim_order_uid: str):
    """Cancel a manual simulation draft."""
    payload = tw_stock_sim_account_service.cancel(user_id=_current_user_id(), sim_order_uid=sim_order_uid)
    return _sim_response(payload)


@tw_stock_bp.route("/trend", methods=["GET"])
def get_trend():
    """Return an explainable read-only trend report for one TWStock symbol."""
    symbol = (request.args.get("symbol") or "").strip()
    if not symbol:
        return jsonify({"code": 0, "msg": "Missing symbol parameter", "data": None}), 400
    try:
        report = trend_service.analyze_symbol(symbol=symbol, limit=_parse_limit(), as_of=_parse_as_of())
        status = 200 if report.get("ok") else 404
        return jsonify({"code": 1 if report.get("ok") else 0, "msg": "success" if report.get("ok") else report.get("error"), "data": report}), status
    except Exception as exc:
        logger.error(f"TWStock trend failed for {symbol}: {exc}", exc_info=True)
        return jsonify({"code": 0, "msg": f"Failed to analyze TWStock trend: {exc}", "data": None}), 500


@tw_stock_bp.route("/trends", methods=["GET"])
def get_trends():
    """Return read-only trend reports for a comma-separated TWStock watchlist."""
    symbols = [part.strip() for part in (request.args.get("symbols") or "").split(",") if part.strip()]
    if not symbols:
        return jsonify({"code": 0, "msg": "Missing symbols parameter", "data": None}), 400
    if len(symbols) > monitor_service.MAX_MONITOR_SYMBOLS:
        return jsonify({"code": 0, "msg": f"Too many symbols; max {monitor_service.MAX_MONITOR_SYMBOLS}", "data": None}), 400
    try:
        limit = _parse_limit()
        as_of = _parse_as_of()
        items = [trend_service.analyze_symbol(symbol=symbol, limit=limit, as_of=as_of) for symbol in symbols]
        ok_items = [item for item in items if item.get("ok")]
        ok_items.sort(key=lambda item: float((item.get("trend") or {}).get("score") or 0.0), reverse=True)
        return jsonify({
            "code": 1,
            "msg": "success",
            "data": {
                "market": "TWStock",
                "count": len(items),
                "ok_count": len(ok_items),
                "items": items,
                "rankings": [{"symbol": item.get("symbol"), "score": (item.get("trend") or {}).get("score"), "label": (item.get("trend") or {}).get("label")} for item in ok_items],
                "trading": {"orders_enabled": False, "note": "Read-only trend watchlist."},
            },
        })
    except Exception as exc:
        logger.error(f"TWStock trends failed: {exc}", exc_info=True)
        return jsonify({"code": 0, "msg": f"Failed to analyze TWStock trends: {exc}", "data": None}), 500


@tw_stock_bp.route("/quant/signals/latest", methods=["GET"])
def get_latest_qlib_option_c_signals():
    """Return latest qlib Option C TWStock research-only ranking signals."""
    bucket = (request.args.get("bucket") or "top30").strip().lower()
    enrich_trend = _parse_bool_arg("enrichTrend", "enrich_trend", default=False)
    trend_limit = _parse_quant_trend_limit()
    try:
        payload = QlibOptionCSignalReader().latest(
            bucket=bucket,
            enrich_trend=enrich_trend,
            trend_limit=trend_limit,
            trend_service=trend_service,
        )
        return jsonify({"code": 1, "msg": "success", "data": payload})
    except QlibOptionCSignalError as exc:
        http_status = 400 if exc.status in ("invalid_bucket", "path_outside_root") else 200
        return jsonify({
            "code": 0,
            "msg": exc.message,
            "data": qlib_blocked_payload(exc.status, exc.message, warnings=exc.warnings),
        }), http_status
    except Exception as exc:
        logger.error(f"TWStock qlib Option C signal read failed: {exc}", exc_info=True)
        message = f"Failed to read qlib Option C research signals: {exc}"
        return jsonify({
            "code": 0,
            "msg": message,
            "data": qlib_blocked_payload("read_error", message),
        }), 500


@tw_stock_bp.route("/quant/signals/rank-changes", methods=["GET"])
def get_qlib_option_c_rank_changes():
    """Return read-only latest-vs-previous qlib Option C rank changes."""
    bucket = (request.args.get("bucket") or "top30").strip().lower()
    try:
        lookback = max(2, min(int(request.args.get("lookback") or 10), 60))
    except Exception:
        lookback = 10
    try:
        payload = QlibOptionCRankChangeReader().rank_changes(bucket=bucket, lookback=lookback)
        return jsonify({"code": 1, "msg": "success", "data": payload})
    except QlibOptionCSignalError as exc:
        http_status = 400 if exc.status in ("invalid_bucket", "path_outside_root") else 200
        return jsonify({
            "code": 0,
            "msg": exc.message,
            "data": qlib_blocked_payload(exc.status, exc.message, warnings=exc.warnings),
        }), http_status
    except Exception as exc:
        logger.error(f"TWStock qlib Option C rank changes read failed: {exc}", exc_info=True)
        message = f"Failed to read qlib Option C rank changes: {exc}"
        return jsonify({
            "code": 0,
            "msg": message,
            "data": qlib_blocked_payload("read_error", message),
        }), 500


@tw_stock_bp.route("/quant/signals/health", methods=["GET"])
def get_qlib_option_c_signal_health():
    """Return read-only qlib Option C artifact freshness and availability."""
    try:
        payload = QlibOptionCSignalReader().health()
        return jsonify({"code": 1, "msg": "success", "data": payload})
    except Exception as exc:
        logger.error(f"TWStock qlib Option C health read failed: {exc}", exc_info=True)
        message = f"Failed to read qlib Option C health: {exc}"
        return jsonify({
            "code": 0,
            "msg": message,
            "data": qlib_blocked_payload("read_error", message),
        }), 500


@tw_stock_bp.route("/quant/signals/runs", methods=["GET"])
def get_qlib_option_c_signal_runs():
    """Return read-only qlib Option C historical run metadata."""
    try:
        limit = max(1, min(int(request.args.get("limit") or 20), 100))
    except Exception:
        limit = 20
    status = (request.args.get("status") or "all").strip().lower()
    try:
        payload = QlibOptionCSignalReader().list_runs(limit=limit, status=status)
        return jsonify({"code": 1, "msg": "success", "data": payload})
    except QlibOptionCSignalError as exc:
        http_status = 400 if exc.status in ("invalid_status", "path_outside_root") else 200
        return jsonify({
            "code": 0,
            "msg": exc.message,
            "data": qlib_blocked_payload(exc.status, exc.message, warnings=exc.warnings),
        }), http_status
    except Exception as exc:
        logger.error(f"TWStock qlib Option C run list failed: {exc}", exc_info=True)
        message = f"Failed to read qlib Option C historical runs: {exc}"
        return jsonify({
            "code": 0,
            "msg": message,
            "data": qlib_blocked_payload("read_error", message),
        }), 500


@tw_stock_bp.route("/quant/signals/runs/<run_id>", methods=["GET"])
def get_qlib_option_c_signal_run_detail(run_id: str):
    """Return one read-only qlib Option C historical run detail."""
    bucket = (request.args.get("bucket") or "top30").strip().lower()
    enrich_trend = _parse_bool_arg("enrichTrend", "enrich_trend", default=False)
    trend_limit = _parse_quant_trend_limit()
    try:
        payload = QlibOptionCSignalReader().run_detail(
            run_id,
            bucket=bucket,
            enrich_trend=enrich_trend,
            trend_limit=trend_limit,
            trend_service=trend_service,
        )
        return jsonify({"code": 1, "msg": "success", "data": payload})
    except QlibOptionCSignalError as exc:
        http_status = 400 if exc.status in ("invalid_bucket", "invalid_run_id", "path_outside_root") else 200
        return jsonify({
            "code": 0,
            "msg": exc.message,
            "data": qlib_blocked_payload(exc.status, exc.message, warnings=exc.warnings),
        }), http_status
    except Exception as exc:
        logger.error(f"TWStock qlib Option C run detail failed for {run_id}: {exc}", exc_info=True)
        message = f"Failed to read qlib Option C historical run: {exc}"
        return jsonify({
            "code": 0,
            "msg": message,
            "data": qlib_blocked_payload("read_error", message),
        }), 500


def _parse_cross_max_items(bucket: str) -> int:
    raw = request.args.get("maxItems") or request.args.get("max_items")
    default = 30 if bucket == "top30" else 50
    if raw is None:
        return default
    try:
        return max(1, min(int(raw), 50))
    except Exception:
        return default


@tw_stock_bp.route("/cross-analysis/latest", methods=["GET"])
def get_tw_stock_cross_analysis_latest():
    """Return read-only cross analysis of qlib rankings and raw TWStock trends."""
    bucket = (request.args.get("bucket") or "top30").strip().lower()
    include_raw = _parse_bool_arg("includeRawTrend", "include_raw_trend", default=False)
    try:
        payload = cross_analysis_service.latest(
            bucket=bucket,
            limit=_parse_limit(),
            include_raw_trend=include_raw,
            max_items=_parse_cross_max_items(bucket),
        )
        return jsonify({
            "code": 1 if payload.get("ok") else 0,
            "msg": "success" if payload.get("ok") else payload.get("message", payload.get("status")),
            "data": payload,
        })
    except Exception as exc:
        logger.error(f"TWStock cross analysis latest failed: {exc}", exc_info=True)
        message = f"Failed to read TWStock cross analysis: {exc}"
        return jsonify({
            "code": 0,
            "msg": message,
            "data": {"ok": False, "status": "read_error", "message": message, "items": [], "trading": research_only_trading_flags()},
        }), 500


@tw_stock_bp.route("/rank-tech-cross/latest", methods=["GET"])
def get_tw_stock_rank_tech_cross_latest():
    """Return read-only qlib ranking x QuantDinger trend classification."""
    bucket = (request.args.get("bucket") or "top30").strip().lower()
    try:
        payload = rank_tech_cross_service.latest(
            bucket=bucket,
            limit=_parse_limit(),
            max_items=_parse_cross_max_items(bucket),
            include_technical_strategies=_parse_bool_arg("includeTechnicalStrategies", "include_technical_strategies", default=True),
            technical_strategies=_parse_technical_strategies(),
        )
        return jsonify({
            "code": 1 if payload.get("ok") else 0,
            "msg": "success" if payload.get("ok") else payload.get("message", payload.get("status")),
            "data": payload,
        })
    except Exception as exc:
        logger.error(f"TWStock rank-tech cross latest failed: {exc}", exc_info=True)
        message = f"Failed to read TWStock rank-tech cross classification: {exc}"
        return jsonify({
            "code": 0,
            "msg": message,
            "data": {
                "ok": False,
                "status": "read_error",
                "message": message,
                "simulation_only": True,
                "research_signal_not_order": True,
                "items": [],
                "summary": {
                    "new_watch": 0,
                    "continue_watch": 0,
                    "risk_review": 0,
                    "manual_review": 0,
                    "observe_only": 0,
                    "data_insufficient": 0,
                },
                "trading": research_only_trading_flags(),
            },
        }), 500


@tw_stock_bp.route("/rank-tech-cross/observation-replay", methods=["GET"])
def get_tw_stock_observation_replay():
    """Return observation-only point-in-time research queue comparison."""
    bucket = (request.args.get("bucket") or "top30").strip().lower()
    start_date = (request.args.get("startDate") or request.args.get("start_date") or "").strip()
    end_date = (request.args.get("endDate") or request.args.get("end_date") or "").strip()
    try:
        payload = observation_replay_service.compare(
            start_date=start_date,
            end_date=end_date,
            bucket=bucket,
            max_items=_parse_cross_max_items(bucket),
            technical_strategies=_parse_technical_strategies(),
        )
        return jsonify({
            "code": 1 if payload.get("ok") else 0,
            "msg": "success" if payload.get("ok") else payload.get("message", payload.get("status")),
            "data": payload,
        })
    except Exception as exc:
        logger.error(f"TWStock observation replay failed: {exc}", exc_info=True)
        message = f"Failed to read TWStock observation replay: {exc}"
        return jsonify({
            "code": 0,
            "msg": message,
            "data": {
                "ok": False,
                "status": "read_error",
                "message": message,
                "simulation_only": True,
                "research_signal_not_order": True,
                "replay_type": "observation_only",
                "performance_metrics_included": False,
                "daily": [],
                "comparison": {},
                "trading": research_only_trading_flags(),
            },
        }), 500


@tw_stock_bp.route("/rank-tech-cross/portfolio-replay", methods=["POST"])
def run_tw_stock_portfolio_replay():
    """Return in-memory portfolio rule historical simulation; never persists."""
    try:
        payload = portfolio_replay_service.replay(config=_request_json())
        return jsonify({
            "code": 1 if payload.get("ok") else 0,
            "msg": "success" if payload.get("ok") else payload.get("message", payload.get("status")),
            "data": payload,
        })
    except Exception as exc:
        logger.error(f"TWStock portfolio replay failed: {exc}", exc_info=True)
        message = f"Failed to run TWStock portfolio replay: {exc}"
        return jsonify({
            "code": 0,
            "msg": message,
            "data": {
                "ok": False,
                "status": "read_error",
                "message": message,
                "simulation_only": True,
                "research_signal_not_order": True,
                "replay_type": "portfolio_rule_historical_simulation",
                "persist": False,
                "writes_business_db": False,
                "comparison": {},
                "trading": research_only_trading_flags(),
            },
        }), 500


@tw_stock_bp.route("/cross-analysis/symbol/<symbol>", methods=["GET"])
def get_tw_stock_cross_analysis_symbol(symbol: str):
    """Return read-only cross analysis detail for one TWStock symbol."""
    include_raw = _parse_bool_arg("includeRawTrend", "include_raw_trend", default=True)
    try:
        payload = cross_analysis_service.symbol_detail(
            symbol=symbol,
            limit=_parse_limit(),
            include_raw_trend=include_raw,
        )
        return jsonify({
            "code": 1 if payload.get("ok") else 0,
            "msg": "success" if payload.get("ok") else payload.get("status"),
            "data": payload,
        })
    except Exception as exc:
        logger.error(f"TWStock cross analysis symbol failed for {symbol}: {exc}", exc_info=True)
        message = f"Failed to read TWStock cross analysis symbol: {exc}"
        return jsonify({
            "code": 0,
            "msg": message,
            "data": {"ok": False, "status": "read_error", "message": message, "trading": research_only_trading_flags()},
        }), 500


@tw_stock_bp.route("/agent/context", methods=["GET"])
def get_tw_stock_agent_context():
    """Return read-only context available to the TWStock research Agent."""
    try:
        payload = tw_stock_agent_service.context(max_items=request.args.get("maxItems") or request.args.get("max_items") or 10)
        return jsonify({
            "code": 1 if payload.get("ok") else 0,
            "msg": "success" if payload.get("ok") else payload.get("message", payload.get("status")),
            "data": payload,
        })
    except Exception as exc:
        logger.error(f"TWStock Agent context failed: {exc}", exc_info=True)
        message = f"Failed to build TWStock Agent context: {exc}"
        return jsonify({"code": 0, "msg": message, "data": {"ok": False, "status": "read_error", "message": message, "trading": research_only_trading_flags()}}), 500


@tw_stock_bp.route("/agent/preview", methods=["POST"])
def preview_tw_stock_agent_answer():
    """Return deterministic research-only answer preview without calling OpenAI."""
    data = _request_json()
    try:
        payload = tw_stock_agent_service.preview(
            question=data.get("question") or "",
            symbol=data.get("symbol") or "",
            max_items=data.get("maxItems") or data.get("max_items") or 10,
        )
        return jsonify({
            "code": 1 if payload.get("ok") else 0,
            "msg": "success" if payload.get("ok") else payload.get("context_digest", {}).get("status", "preview_unavailable"),
            "data": payload,
        })
    except Exception as exc:
        logger.error(f"TWStock Agent preview failed: {exc}", exc_info=True)
        message = f"Failed to preview TWStock Agent answer: {exc}"
        return jsonify({"code": 0, "msg": message, "data": {"ok": False, "status": "read_error", "message": message, "trading": research_only_trading_flags()}}), 500


@tw_stock_bp.route("/agent/chat", methods=["POST"])
def chat_tw_stock_agent_answer():
    """Return structured TWStock research Agent answer with guarded OpenAI fallback."""
    data = _request_json()
    try:
        payload = tw_stock_agent_chat_service.chat(
            question=data.get("question") or "",
            symbol=data.get("symbol") or "",
            max_items=data.get("maxItems") or data.get("max_items") or 10,
        )
        return jsonify({
            "code": 1 if payload.get("ok") else 0,
            "msg": "success" if payload.get("ok") else "chat_unavailable",
            "data": payload,
        })
    except Exception as exc:
        logger.error(f"TWStock Agent chat failed: {exc}", exc_info=True)
        message = f"Failed to chat with TWStock Agent: {exc}"
        return jsonify({"code": 0, "msg": message, "data": {"ok": False, "status": "read_error", "message": message, "trading": research_only_trading_flags()}}), 500


@tw_stock_bp.route("/cross-analysis/history/import-latest", methods=["POST"])
@login_required
def import_tw_stock_cross_analysis_history_latest():
    """Import latest accepted qlib signal run into research history tables."""
    denied = _require_option_c_ops_permission()
    if denied:
        return denied
    data = _request_json()
    try:
        payload = cross_analysis_history_service.import_latest(
            confirm_import_qlib_signal_history=bool(data.get("confirm_import_qlib_signal_history")),
        )
        status = 200 if payload.get("ok") else 400
        return jsonify({"code": 1 if payload.get("ok") else 0, "msg": "success" if payload.get("ok") else payload.get("message", payload.get("status")), "data": payload}), status
    except Exception as exc:
        logger.error(f"TWStock cross analysis history import failed: {exc}", exc_info=True)
        message = f"Failed to import TWStock qlib signal history: {exc}"
        return jsonify({"code": 0, "msg": message, "data": {"ok": False, "status": "import_error", "message": message, "trading": research_only_trading_flags()}}), 500


@tw_stock_bp.route("/cross-analysis/history/runs", methods=["GET"])
def get_tw_stock_cross_analysis_history_runs():
    """Return imported qlib signal research runs."""
    try:
        payload = cross_analysis_history_service.runs(limit=request.args.get("limit") or 20)
        return jsonify({"code": 1, "msg": "success", "data": payload})
    except Exception as exc:
        logger.error(f"TWStock cross analysis history runs failed: {exc}", exc_info=True)
        return jsonify({"code": 0, "msg": f"Failed to read TWStock qlib signal runs: {exc}", "data": None}), 500


@tw_stock_bp.route("/cross-analysis/history/signals", methods=["GET"])
def get_tw_stock_cross_analysis_history_signals():
    """Return imported qlib signal research rows."""
    try:
        payload = cross_analysis_history_service.signals(
            run_id=(request.args.get("run_id") or request.args.get("runId") or "").strip(),
            bucket=(request.args.get("bucket") or "").strip(),
            symbol=(request.args.get("symbol") or "").strip(),
            limit=request.args.get("limit") or 100,
        )
        return jsonify({"code": 1, "msg": "success", "data": payload})
    except Exception as exc:
        logger.error(f"TWStock cross analysis history signals failed: {exc}", exc_info=True)
        return jsonify({"code": 0, "msg": f"Failed to read TWStock qlib signal rows: {exc}", "data": None}), 500


@tw_stock_bp.route("/cross-analysis/history/alerts", methods=["GET"])
def get_tw_stock_cross_analysis_history_alerts():
    """Return research-only qlib signal history alerts."""
    try:
        payload = cross_analysis_history_service.alerts(
            run_id=(request.args.get("run_id") or request.args.get("runId") or "").strip(),
            alert_type=(request.args.get("alert_type") or request.args.get("alertType") or "").strip(),
            symbol=(request.args.get("symbol") or "").strip(),
            limit=request.args.get("limit") or 100,
        )
        return jsonify({"code": 1, "msg": "success", "data": payload})
    except Exception as exc:
        logger.error(f"TWStock cross analysis history alerts failed: {exc}", exc_info=True)
        return jsonify({"code": 0, "msg": f"Failed to read TWStock qlib signal alerts: {exc}", "data": None}), 500


@tw_stock_bp.route("/cross-analysis/reviews", methods=["GET"])
@login_required
def get_tw_stock_cross_analysis_reviews():
    """Return current user's research-only cross-analysis review states."""
    try:
        payload = cross_analysis_history_service.reviews(
            user_id=getattr(g, "user_id", 1) or 1,
            asof=(request.args.get("asof") or "").strip(),
            run_id=(request.args.get("run_id") or request.args.get("runId") or "").strip(),
            symbol=(request.args.get("symbol") or "").strip(),
            limit=request.args.get("limit") or 100,
        )
        return jsonify({"code": 1, "msg": "success", "data": payload})
    except Exception as exc:
        logger.error(f"TWStock cross analysis reviews get failed: {exc}", exc_info=True)
        return jsonify({"code": 0, "msg": f"Failed to read TWStock cross-analysis reviews: {exc}", "data": None}), 500


@tw_stock_bp.route("/cross-analysis/reviews", methods=["PUT"])
@login_required
def save_tw_stock_cross_analysis_review():
    """Save current user's manual research review status and note only."""
    data = _request_json()
    try:
        payload = cross_analysis_history_service.save_review(
            user_id=getattr(g, "user_id", 1) or 1,
            asof=data.get("asof") or "",
            run_id=data.get("run_id") or data.get("runId") or "",
            symbol=data.get("symbol") or "",
            cross_category=data.get("cross_category") or data.get("crossCategory") or "",
            decision_status=data.get("decision_status") or data.get("decisionStatus") or "pending",
            user_note=data.get("user_note") or data.get("userNote") or "",
        )
        status = 200 if payload.get("ok") else 400
        return jsonify({"code": 1 if payload.get("ok") else 0, "msg": "success" if payload.get("ok") else payload.get("message", payload.get("status")), "data": payload}), status
    except Exception as exc:
        logger.error(f"TWStock cross analysis review save failed: {exc}", exc_info=True)
        return jsonify({"code": 0, "msg": f"Failed to save TWStock cross-analysis review: {exc}", "data": None}), 500


@tw_stock_bp.route("/quant/ops/option-c/dry-run", methods=["POST"])
@login_required
def trigger_qlib_option_c_ops_dry_run():
    """Run the fixed qlib Option C provider dry-run wrapper."""
    denied = _require_option_c_ops_permission()
    if denied:
        return denied
    payload = option_c_ops_runner.trigger_dry_run(_request_json())
    status = str(payload.get("status") or "")
    if status == "conflict":
        http_status = 409
    elif not payload.get("ok") and status == "blocked":
        http_status = 400
    else:
        http_status = 200
    return jsonify({"code": 1 if payload.get("ok") else 0, "msg": "success" if payload.get("ok") else payload.get("message", status), "data": payload}), http_status


@tw_stock_bp.route("/quant/ops/option-c/jobs/<job_id>", methods=["GET"])
def get_qlib_option_c_ops_job(job_id: str):
    """Return one Option C dry-run ops job status and log tails."""
    payload = option_c_ops_runner.get_job(job_id)
    status = 200 if payload.get("ok") or payload.get("status") == "dry_run_failed" else 404
    if payload.get("status") == "invalid_job_id":
        status = 400
    return jsonify({"code": 1 if payload.get("ok") else 0, "msg": "success" if payload.get("ok") else payload.get("message", payload.get("status")), "data": payload}), status


@tw_stock_bp.route("/quant/ops/option-c/jobs/<job_id>/logs", methods=["GET"])
@login_required
def get_qlib_option_c_ops_job_log_tail(job_id: str):
    """Return stdout/stderr tail for one Option C dry-run ops job."""
    denied = _require_option_c_ops_permission()
    if denied:
        return denied
    stream = (request.args.get("stream") or "stdout").strip().lower()
    payload = option_c_ops_runner.log_tail(job_id, stream=stream)
    status = 200 if payload.get("ok") else 400
    if payload.get("status") == "job_not_found":
        status = 404
    return jsonify({"code": 1 if payload.get("ok") else 0, "msg": "success" if payload.get("ok") else payload.get("message", payload.get("status")), "data": payload}), status


@tw_stock_bp.route("/quant/ops/option-c/latest", methods=["GET"])
def get_qlib_option_c_ops_latest():
    """Return latest Option C dry-run ops job without triggering commands."""
    payload = option_c_ops_runner.latest()
    return jsonify({"code": 1, "msg": "success", "data": payload})


@tw_stock_bp.route("/quant/ops/daily-auto-update/status", methods=["GET"])
def get_daily_auto_update_status():
    """Return read-only daily FinMind/Yahoo/qlib auto-update status."""
    payload = daily_auto_update_status_service.status()
    return jsonify({"code": 1, "msg": "success", "data": payload})


@tw_stock_bp.route("/quant/ops/option-c/scheduler", methods=["GET"])
def get_qlib_option_c_scheduler_status():
    """Return disabled-by-default Option C dry-run scheduler status."""
    payload = option_c_dry_run_scheduler.status()
    status = 200 if payload.get("ok") else 400
    return jsonify({"code": 1 if payload.get("ok") else 0, "msg": "success" if payload.get("ok") else "scheduler misconfigured", "data": payload}), status


@tw_stock_bp.route("/quant/ops/option-c/scheduler/tick", methods=["POST"])
@login_required
def tick_qlib_option_c_scheduler():
    """Manually smoke the disabled Option C scheduler through dry-run only."""
    denied = _require_option_c_ops_permission()
    if denied:
        return denied
    payload = option_c_dry_run_scheduler.tick(_request_json())
    status = str(payload.get("status") or "")
    if status == "conflict":
        http_status = 409
    elif not payload.get("ok"):
        http_status = 400
    else:
        http_status = 200
    return jsonify({"code": 1 if payload.get("ok") else 0, "msg": "success" if payload.get("ok") else payload.get("message", status), "data": payload}), http_status


@tw_stock_bp.route("/quant/ops/option-c/accepted-latest-scheduler", methods=["GET"])
def get_qlib_option_c_accepted_latest_scheduler_status():
    """Return disabled-by-default Option C accepted latest scheduler status."""
    payload = option_c_accepted_latest_scheduler.status()
    status = 200 if payload.get("ok") else 400
    return jsonify({"code": 1 if payload.get("ok") else 0, "msg": "success" if payload.get("ok") else "accepted latest scheduler misconfigured", "data": payload}), status


@tw_stock_bp.route("/quant/ops/option-c/accepted-latest-scheduler/tick", methods=["POST"])
@login_required
def tick_qlib_option_c_accepted_latest_scheduler():
    """Manually tick the disabled-by-default accepted latest scheduler skeleton."""
    denied = _require_option_c_ops_permission()
    if denied:
        return denied
    payload = option_c_accepted_latest_scheduler.tick(_request_json())
    status = str(payload.get("status") or "")
    if status == "conflict":
        http_status = 409
    elif not payload.get("ok"):
        http_status = 400
    else:
        http_status = 200
    return jsonify({"code": 1 if payload.get("ok") else 0, "msg": "success" if payload.get("ok") else payload.get("message", status), "data": payload}), http_status


@tw_stock_bp.route("/quant/ops/option-c/eod-pipeline", methods=["GET"])
def get_qlib_option_c_eod_pipeline_status():
    """Return disabled-by-default Option C EOD pipeline status."""
    payload = option_c_eod_pipeline.status()
    status = 200 if payload.get("ok") else 400
    return jsonify({"code": 1 if payload.get("ok") else 0, "msg": "success" if payload.get("ok") else "EOD pipeline misconfigured", "data": payload}), status


@tw_stock_bp.route("/quant/ops/option-c/eod-pipeline/tick", methods=["POST"])
@login_required
def tick_qlib_option_c_eod_pipeline():
    """Manually smoke the disabled-by-default Option C EOD pipeline."""
    denied = _require_option_c_ops_permission()
    if denied:
        return denied
    payload = option_c_eod_pipeline.tick(_request_json())
    status = str(payload.get("status") or "")
    if status == "conflict":
        http_status = 409
    elif not payload.get("ok"):
        http_status = 400
    else:
        http_status = 200
    return jsonify({"code": 1 if payload.get("ok") else 0, "msg": "success" if payload.get("ok") else payload.get("message", status), "data": payload}), http_status


@tw_stock_bp.route("/quant/ops/option-c/eod-automation", methods=["GET"])
def get_qlib_option_c_eod_automation_status():
    """Return disabled-by-default Option C EOD automation scheduler status."""
    payload = option_c_eod_automation_scheduler.status(now=request.args.get("now"))
    status = 200 if payload.get("ok") else 400
    return jsonify({"code": 1 if payload.get("ok") else 0, "msg": "success" if payload.get("ok") else "EOD automation misconfigured", "data": payload}), status


@tw_stock_bp.route("/quant/ops/option-c/eod-automation/tick", methods=["POST"])
@login_required
def tick_qlib_option_c_eod_automation():
    """Manually smoke the disabled-by-default Option C EOD automation scheduler."""
    denied = _require_option_c_ops_permission()
    if denied:
        return denied
    payload = option_c_eod_automation_scheduler.tick(_request_json())
    status = str(payload.get("status") or "")
    if status == "conflict":
        http_status = 409
    elif not payload.get("ok"):
        http_status = 400
    else:
        http_status = 200
    return jsonify({"code": 1 if payload.get("ok") else 0, "msg": "success" if payload.get("ok") else payload.get("message", status), "data": payload}), http_status


@tw_stock_bp.route("/quant/ops/option-c/normal-publish", methods=["POST"])
@login_required
def normal_publish_qlib_option_c_latest():
    """Review-gated Option C normal accepted latest publish endpoint."""
    denied = _require_option_c_ops_permission()
    if denied:
        return denied
    payload = option_c_normal_publish_gate.publish(_request_json())
    status = 200 if payload.get("ok") else 400
    return jsonify({"code": 1 if payload.get("ok") else 0, "msg": "success" if payload.get("ok") else payload.get("message", payload.get("status")), "data": payload}), status


def _request_json() -> dict:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _monitor_user_id(data: dict | None = None) -> int:
    raw = None
    if isinstance(data, dict):
        raw = data.get("user_id") or data.get("userId")
    raw = raw or request.args.get("user_id") or request.args.get("userId") or 1
    try:
        return max(1, int(raw))
    except Exception:
        return 1


def _monitor_name(data: dict | None = None) -> str:
    raw = ""
    if isinstance(data, dict):
        raw = str(data.get("name") or data.get("monitor_name") or data.get("monitorName") or "")
    raw = raw or str(request.args.get("name") or request.args.get("monitor_name") or request.args.get("monitorName") or "")
    clean = raw.strip() or "default"
    return clean[:80]


def _symbols_from_value(value) -> list[str]:
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = str(value or "").split(",")
    out = []
    seen = set()
    for item in raw_items:
        symbol = str(item or "").strip()
        if not symbol:
            continue
        normalized = symbol.upper()
        if normalized not in seen:
            seen.add(normalized)
            out.append(normalized)
    return out[:monitor_service.MAX_MONITOR_SYMBOLS]


def _monitor_config_from_row(row: dict | None, *, user_id: int, name: str) -> dict:
    return monitor_service.monitor_config_from_row(row, user_id=user_id, name=name)


def _default_monitor_config(*, user_id: int, name: str, degraded_reason: str = "") -> dict:
    config = _monitor_config_from_row(None, user_id=user_id, name=name)
    config["persistence_enabled"] = False
    config["degraded"] = True
    if degraded_reason:
        config["degraded_reason"] = degraded_reason[:400]
    return config


def _ephemeral_monitor_scan(config: dict, *, reason: str) -> dict:
    symbols = _symbols_from_value(config.get("symbols"))
    limit_bars = max(20, min(int(config.get("limit_bars") or 120), 500))
    items = [trend_service.analyze_symbol(symbol=symbol, limit=limit_bars) for symbol in symbols]
    return {
        "status": "scanned_ephemeral",
        "monitor_name": str(config.get("name") or "default"),
        "scanned_count": len(items),
        "alert_count": 0,
        "alerts": [],
        "items": items,
        "persistence_enabled": False,
        "degraded": True,
        "degraded_reason": str(reason or "database_unavailable")[:400],
        "trading": {
            "orders_enabled": False,
            "note": "Ephemeral TWStock research scan only; database persistence is unavailable.",
        },
    }


def _alert_from_row(row: dict) -> dict:
    snapshot = row.get("snapshot") or {}
    if isinstance(snapshot, str):
        try:
            snapshot = json.loads(snapshot)
        except Exception:
            snapshot = {}
    return {
        "id": row.get("id"),
        "user_id": row.get("user_id"),
        "monitor_name": row.get("monitor_name"),
        "symbol": row.get("symbol"),
        "alert_type": row.get("alert_type"),
        "severity": row.get("severity"),
        "message": row.get("message"),
        "snapshot": snapshot,
        "is_read": bool(row.get("is_read")),
        "decision_status": row.get("decision_status") or "pending",
        "user_note": row.get("user_note") or "",
        "created_at": row.get("created_at"),
        "acknowledged_at": row.get("acknowledged_at"),
    }


@tw_stock_bp.route("/monitor/config", methods=["GET"])
def get_monitor_config():
    """Return saved TWStock monitor config, or a default config if none exists."""
    user_id = _monitor_user_id()
    name = _monitor_name()
    try:
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                """
                SELECT id, user_id, name, symbols_json, limit_bars, refresh_interval_sec,
                       score_change_threshold, enabled, notes, created_at, updated_at
                FROM qd_tw_stock_monitor_configs
                WHERE user_id = ? AND name = ?
                """,
                (user_id, name),
            )
            row = cur.fetchone()
            cur.close()
        return jsonify({"code": 1, "msg": "success", "data": _monitor_config_from_row(row, user_id=user_id, name=name)})
    except Exception as exc:
        logger.warning(f"TWStock monitor config get degraded to default: {exc}")
        return jsonify({
            "code": 1,
            "msg": "database_unavailable_default_config",
            "data": _default_monitor_config(user_id=user_id, name=name, degraded_reason=str(exc)),
        })


@tw_stock_bp.route("/monitor/config", methods=["POST", "PUT"])
def save_monitor_config():
    """Persist TWStock monitor config. This controls alerts only, never orders."""
    data = _request_json()
    user_id = _monitor_user_id(data)
    name = _monitor_name(data)
    symbols = _symbols_from_value(data.get("symbols") or data.get("symbols_csv") or data.get("symbolsCsv") or "2330,0050,00878")
    if not symbols:
        return jsonify({"code": 0, "msg": "symbols must not be empty", "data": None}), 400
    try:
        limit_bars = max(20, min(int(data.get("limit_bars") or data.get("limit") or 120), 500))
    except Exception:
        limit_bars = 120
    try:
        refresh_interval_sec = max(0, min(int(data.get("refresh_interval_sec") or data.get("interval") or 300), 86400))
    except Exception:
        refresh_interval_sec = 300
    try:
        score_change_threshold = max(0.0, min(float(data.get("score_change_threshold") or data.get("threshold") or 8.0), 100.0))
    except Exception:
        score_change_threshold = 8.0
    enabled = bool(data.get("enabled", False))
    notes = str(data.get("notes") or "")[:2000]
    try:
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                """
                INSERT INTO qd_tw_stock_monitor_configs
                    (user_id, name, symbols_json, limit_bars, refresh_interval_sec,
                     score_change_threshold, enabled, notes, created_at, updated_at)
                VALUES (?, ?, ?::jsonb, ?, ?, ?, ?, ?, NOW(), NOW())
                ON CONFLICT (user_id, name) DO UPDATE SET
                    symbols_json = EXCLUDED.symbols_json,
                    limit_bars = EXCLUDED.limit_bars,
                    refresh_interval_sec = EXCLUDED.refresh_interval_sec,
                    score_change_threshold = EXCLUDED.score_change_threshold,
                    enabled = EXCLUDED.enabled,
                    notes = EXCLUDED.notes,
                    updated_at = NOW()
                RETURNING id, user_id, name, symbols_json, limit_bars, refresh_interval_sec,
                          score_change_threshold, enabled, notes, created_at, updated_at
                """,
                (user_id, name, json.dumps(symbols), limit_bars, refresh_interval_sec, score_change_threshold, enabled, notes),
            )
            row = cur.fetchone()
            cur.close()
            db.commit()
        return jsonify({"code": 1, "msg": "success", "data": _monitor_config_from_row(row, user_id=user_id, name=name)})
    except Exception as exc:
        logger.error(f"TWStock monitor config save failed: {exc}", exc_info=True)
        return jsonify({"code": 0, "msg": f"Failed to save monitor config: {exc}", "data": None}), 500


@tw_stock_bp.route("/monitor/alerts", methods=["GET"])
def get_monitor_alerts():
    """Return TWStock monitor alert history for manual review."""
    user_id = _monitor_user_id()
    name = _monitor_name()
    try:
        limit = max(1, min(int(request.args.get("limit", 50)), 200))
    except Exception:
        limit = 50
    unread_only = str(request.args.get("unread_only") or request.args.get("unreadOnly") or "").lower() in ("1", "true", "yes")
    try:
        with get_db_connection() as db:
            cur = db.cursor()
            if unread_only:
                cur.execute(
                    """
                    SELECT id, user_id, monitor_name, symbol, alert_type, severity, message,
                           snapshot, is_read, decision_status, user_note, created_at, acknowledged_at
                    FROM qd_tw_stock_monitor_alerts
                    WHERE user_id = ? AND monitor_name = ? AND is_read = FALSE
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (user_id, name, limit),
                )
            else:
                cur.execute(
                    """
                    SELECT id, user_id, monitor_name, symbol, alert_type, severity, message,
                           snapshot, is_read, decision_status, user_note, created_at, acknowledged_at
                    FROM qd_tw_stock_monitor_alerts
                    WHERE user_id = ? AND monitor_name = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (user_id, name, limit),
                )
            rows = cur.fetchall() or []
            cur.close()
        return jsonify({"code": 1, "msg": "success", "data": {"items": [_alert_from_row(row) for row in rows], "count": len(rows)}})
    except Exception as exc:
        logger.error(f"TWStock monitor alerts get failed: {exc}", exc_info=True)
        return jsonify({"code": 0, "msg": f"Failed to get monitor alerts: {exc}", "data": None}), 500


@tw_stock_bp.route("/monitor/alerts", methods=["POST"])
def create_monitor_alert():
    """Persist one TWStock monitor alert. This is not a trade decision."""
    data = _request_json()
    user_id = _monitor_user_id(data)
    name = _monitor_name(data)
    symbol = str(data.get("symbol") or "").strip().upper()
    message = str(data.get("message") or "").strip()
    if not symbol or not message:
        return jsonify({"code": 0, "msg": "symbol and message are required", "data": None}), 400
    alert_type = str(data.get("alert_type") or data.get("alertType") or "trend_change").strip()[:40]
    severity = str(data.get("severity") or "info").strip().lower()[:20]
    if severity not in ("info", "warning", "critical"):
        severity = "info"
    snapshot = data.get("snapshot") if isinstance(data.get("snapshot"), dict) else {}
    try:
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                """
                INSERT INTO qd_tw_stock_monitor_alerts
                    (user_id, monitor_name, symbol, alert_type, severity, message, snapshot,
                     is_read, decision_status, user_note, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?::jsonb, FALSE, 'pending', '', NOW())
                RETURNING id, user_id, monitor_name, symbol, alert_type, severity, message,
                          snapshot, is_read, decision_status, user_note, created_at, acknowledged_at
                """,
                (user_id, name, symbol, alert_type, severity, message[:2000], json.dumps(snapshot)),
            )
            row = cur.fetchone()
            cur.close()
            alert = _alert_from_row(row)
            _try_insert_strategy_notification_for_monitor_alert(db, alert=alert)
            db.commit()
        _try_send_monitor_alert_webhook(alert=alert)
        return jsonify({"code": 1, "msg": "success", "data": alert})
    except Exception as exc:
        logger.error(f"TWStock monitor alert create failed: {exc}", exc_info=True)
        return jsonify({"code": 0, "msg": f"Failed to create monitor alert: {exc}", "data": None}), 500


@tw_stock_bp.route("/monitor/alerts/<int:alert_id>", methods=["PUT"])
def update_monitor_alert(alert_id: int):
    """Mark an alert as reviewed and optionally attach the user's manual decision note."""
    data = _request_json()
    user_id = _monitor_user_id(data)
    decision_status = str(data.get("decision_status") or data.get("decisionStatus") or "pending").strip().lower()
    if decision_status not in ("pending", "watch", "acted", "ignored"):
        decision_status = "pending"
    user_note = str(data.get("user_note") or data.get("userNote") or "")[:2000]
    is_read = bool(data.get("is_read", data.get("isRead", True)))
    try:
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                """
                UPDATE qd_tw_stock_monitor_alerts
                SET is_read = ?, decision_status = ?, user_note = ?, acknowledged_at = CASE WHEN ? THEN NOW() ELSE acknowledged_at END
                WHERE id = ? AND user_id = ?
                RETURNING id, user_id, monitor_name, symbol, alert_type, severity, message,
                          snapshot, is_read, decision_status, user_note, created_at, acknowledged_at
                """,
                (is_read, decision_status, user_note, is_read, alert_id, user_id),
            )
            row = cur.fetchone()
            cur.close()
            db.commit()
        if not row:
            return jsonify({"code": 0, "msg": "alert not found", "data": None}), 404
        return jsonify({"code": 1, "msg": "success", "data": _alert_from_row(row)})
    except Exception as exc:
        logger.error(f"TWStock monitor alert update failed: {exc}", exc_info=True)
        return jsonify({"code": 0, "msg": f"Failed to update monitor alert: {exc}", "data": None}), 500


def _insert_monitor_alert(db, *, user_id: int, name: str, symbol: str, alert_type: str, severity: str, message: str, snapshot: dict) -> dict:
    cur = db.cursor()
    cur.execute(
        """
        INSERT INTO qd_tw_stock_monitor_alerts
            (user_id, monitor_name, symbol, alert_type, severity, message, snapshot,
             is_read, decision_status, user_note, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?::jsonb, FALSE, 'pending', '', NOW())
        RETURNING id, user_id, monitor_name, symbol, alert_type, severity, message,
                  snapshot, is_read, decision_status, user_note, created_at, acknowledged_at
        """,
        (user_id, name, symbol, alert_type[:40], severity, message[:2000], json.dumps(snapshot)),
    )
    row = cur.fetchone()
    cur.close()
    alert = _alert_from_row(row)
    _try_insert_strategy_notification_for_monitor_alert(db, alert=alert)
    _try_send_monitor_alert_webhook(alert=alert)
    return alert


def _try_insert_strategy_notification_for_monitor_alert(db, *, alert: dict) -> None:
    savepoint = "tw_stock_monitor_notification"
    try:
        cur = db.cursor()
        cur.execute(f"SAVEPOINT {savepoint}")
        cur.close()
        _insert_strategy_notification_for_monitor_alert(db, alert=alert)
        cur = db.cursor()
        cur.execute(f"RELEASE SAVEPOINT {savepoint}")
        cur.close()
    except Exception as exc:
        try:
            cur = db.cursor()
            cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
            cur.close()
        except Exception:
            pass
        logger.warning(f"TWStock monitor notification insert skipped: {exc}")


def _insert_strategy_notification_for_monitor_alert(db, *, alert: dict) -> None:
    payload = {
        "source": "tw_stock_monitor",
        "alert_id": alert.get("id"),
        "monitor_name": alert.get("monitor_name"),
        "symbol": alert.get("symbol"),
        "alert_type": alert.get("alert_type"),
        "severity": alert.get("severity"),
        "snapshot": alert.get("snapshot") or {},
    }
    cur = db.cursor()
    cur.execute(
        """
        INSERT INTO qd_strategy_notifications
            (user_id, strategy_id, symbol, signal_type, channels, title, message, payload_json, is_read, created_at)
        VALUES (?, NULL, ?, ?, 'browser', ?, ?, ?, 0, NOW())
        """,
        (
            int(alert.get("user_id") or 1),
            str(alert.get("symbol") or "")[:50],
            "tw_stock_monitor",
            "台股趋势提醒",
            str(alert.get("message") or "")[:2000],
            json.dumps(payload, ensure_ascii=False),
        ),
    )
    cur.close()


def _safe_json_dict(value) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _load_monitor_webhook_targets(user_id: int) -> dict:
    settings = {}
    try:
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute("SELECT notification_settings FROM qd_users WHERE id = ?", (user_id,))
            row = cur.fetchone()
            cur.close()
        settings = _safe_json_dict(row.get("notification_settings") if row else {})
    except Exception as exc:
        logger.warning(f"TWStock monitor webhook settings load skipped: {exc}")

    enabled = str(os.getenv("TW_STOCK_MONITOR_WEBHOOK_ENABLED") or "").strip().lower() in ("1", "true", "yes", "on")
    if settings.get("tw_stock_monitor_webhook_enabled") is True:
        enabled = True

    url = (os.getenv("TW_STOCK_MONITOR_WEBHOOK_URL") or "").strip()
    if not url and enabled:
        url = str(settings.get("tw_stock_monitor_webhook_url") or settings.get("webhook_url") or "").strip()
    if not url:
        return {}

    return {
        "url": url,
        "headers": settings.get("tw_stock_monitor_webhook_headers") or settings.get("webhook_headers"),
        "token": settings.get("tw_stock_monitor_webhook_token") or settings.get("webhook_token"),
        "signing_secret": (
            os.getenv("TW_STOCK_MONITOR_WEBHOOK_SIGNING_SECRET")
            or settings.get("tw_stock_monitor_webhook_signing_secret")
            or settings.get("webhook_signing_secret")
        ),
    }


def _build_monitor_alert_webhook_payload(alert: dict) -> dict:
    snapshot = alert.get("snapshot") or {}
    trend = snapshot.get("trend") if isinstance(snapshot, dict) else {}
    latest = snapshot.get("latest") if isinstance(snapshot, dict) else {}
    return {
        "source": "tw_stock_monitor",
        "event": "tw_stock_monitor_alert",
        "title": "台股趋势提醒",
        "message": str(alert.get("message") or "")[:2000],
        "user_id": int(alert.get("user_id") or 1),
        "monitor_name": alert.get("monitor_name"),
        "alert_id": alert.get("id"),
        "symbol": alert.get("symbol"),
        "alert_type": alert.get("alert_type"),
        "severity": alert.get("severity"),
        "trend": {
            "label": (trend or {}).get("label") if isinstance(trend, dict) else None,
            "score": (trend or {}).get("score") if isinstance(trend, dict) else None,
        },
        "latest": {
            "date": (latest or {}).get("date") if isinstance(latest, dict) else None,
            "close": (latest or {}).get("close") if isinstance(latest, dict) else None,
        },
        "trading": {"orders_enabled": False, "note": "Research-only TWStock monitor alert."},
    }


def _try_send_monitor_alert_webhook(*, alert: dict) -> None:
    targets = _load_monitor_webhook_targets(int(alert.get("user_id") or 1))
    if not targets.get("url"):
        return
    try:
        from app.services.signal_notifier import SignalNotifier

        ok, err = SignalNotifier()._notify_webhook(
            url=targets["url"],
            payload=_build_monitor_alert_webhook_payload(alert),
            headers_override=targets.get("headers"),
            token_override=targets.get("token"),
            signing_secret_override=targets.get("signing_secret"),
        )
        if not ok:
            logger.warning(f"TWStock monitor webhook delivery failed: {err}")
    except Exception as exc:
        logger.warning(f"TWStock monitor webhook delivery skipped: {exc}")


def _load_monitor_config_from_db(user_id: int, name: str) -> dict:
    with get_db_connection() as db:
        cur = db.cursor()
        cur.execute(
            """
            SELECT id, user_id, name, symbols_json, limit_bars, refresh_interval_sec,
                   score_change_threshold, enabled, notes, created_at, updated_at
            FROM qd_tw_stock_monitor_configs
            WHERE user_id = ? AND name = ?
            """,
            (user_id, name),
        )
        row = cur.fetchone()
        cur.close()
    return _monitor_config_from_row(row, user_id=user_id, name=name)


def _warnings_set(report: dict) -> set[str]:
    return monitor_service.warnings_set(report)


def _insert_trend_history(db, *, user_id: int, name: str, symbol: str, report: dict) -> None:
    monitor_service.insert_trend_history(db, user_id=user_id, name=name, symbol=symbol, report=report)


def _trend_history_from_row(row: dict) -> dict:
    warnings = row.get("warnings_json") or []
    if isinstance(warnings, str):
        try:
            warnings = json.loads(warnings)
        except Exception:
            warnings = []
    snapshot = row.get("snapshot") or {}
    if isinstance(snapshot, str):
        try:
            snapshot = json.loads(snapshot)
        except Exception:
            snapshot = {}
    return {
        "id": row.get("id"),
        "user_id": row.get("user_id"),
        "monitor_name": row.get("monitor_name"),
        "symbol": row.get("symbol"),
        "label": row.get("label"),
        "score": float(row.get("score") or 0.0),
        "latest_date": row.get("latest_date") or "",
        "latest_close": float(row.get("latest_close") or 0.0),
        "warnings": warnings if isinstance(warnings, list) else [],
        "snapshot": snapshot,
        "scanned_at": row.get("scanned_at"),
    }


@tw_stock_bp.route("/monitor/history", methods=["GET"])
def get_monitor_history():
    """Return stored TWStock trend score history for charting and manual review."""
    user_id = _monitor_user_id()
    name = _monitor_name()
    symbol = str(request.args.get("symbol") or "").strip().upper()
    if not symbol:
        return jsonify({"code": 0, "msg": "Missing symbol parameter", "data": None}), 400
    try:
        limit = max(1, min(int(request.args.get("limit", 120)), 500))
    except Exception:
        limit = 120
    try:
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                """
                SELECT id, user_id, monitor_name, symbol, label, score, latest_date, latest_close,
                       warnings_json, snapshot, scanned_at
                FROM qd_tw_stock_trend_history
                WHERE user_id = ? AND monitor_name = ? AND symbol = ?
                ORDER BY scanned_at DESC, id DESC
                LIMIT ?
                """,
                (user_id, name, symbol, limit),
            )
            rows = cur.fetchall() or []
            cur.close()
        items = [_trend_history_from_row(row) for row in rows]
        items.reverse()
        return jsonify({
            "code": 1,
            "msg": "success",
            "data": {
                "market": "TWStock",
                "user_id": user_id,
                "monitor_name": name,
                "symbol": symbol,
                "count": len(items),
                "items": items,
                "trading": {"orders_enabled": False, "note": "Trend history is read-only research data."},
            },
        })
    except Exception as exc:
        logger.error(f"TWStock monitor history failed: {exc}", exc_info=True)
        return jsonify({"code": 0, "msg": f"Failed to get monitor history: {exc}", "data": None}), 500


def _build_scan_alerts(symbol: str, report: dict, previous: dict | None, threshold: float) -> list[dict]:
    return monitor_service.build_scan_alerts(symbol, report, previous, threshold)


def _scan_monitor_config(config: dict, *, force: bool = False) -> dict:
    return monitor_service.scan_monitor_config(
        config,
        force=force,
        trend_service=trend_service,
        get_db_connection=get_db_connection,
        insert_alert=_insert_monitor_alert,
    )


@tw_stock_bp.route("/monitor/scan", methods=["POST"])
def scan_monitor():
    """Run a backend TWStock monitor scan and persist alerts. No orders are created."""
    data = _request_json()
    user_id = _monitor_user_id(data)
    name = _monitor_name(data)
    force = bool(data.get("force", False))
    try:
        config = _load_monitor_config_from_db(user_id, name)
        result = _scan_monitor_config(config, force=force)
        return jsonify({"code": 1, "msg": "success", "data": result})
    except Exception as exc:
        logger.warning(f"TWStock monitor scan degraded to ephemeral mode: {exc}")
        config = _default_monitor_config(user_id=user_id, name=name, degraded_reason=str(exc))
        result = _ephemeral_monitor_scan(config, reason=str(exc))
        return jsonify({"code": 1, "msg": "database_unavailable_ephemeral_scan", "data": result})


def _write_scan_log(*, trigger_source: str, status: str, result: dict | None = None, error: str = "", duration_ms: int = 0) -> None:
    monitor_service.write_scan_log(
        get_db_connection=get_db_connection,
        trigger_source=trigger_source,
        status=status,
        result=result,
        error=error,
        duration_ms=duration_ms,
    )


def run_tw_stock_monitor_scan_all(*, force: bool = False, trigger_source: str = "api", write_log: bool = True) -> dict:
    """Scan enabled TWStock monitor configs for API, worker, or cron use. Research-only."""
    return monitor_service.run_scan_all(
        force=force,
        trigger_source=trigger_source,
        write_log=write_log,
        trend_service=trend_service,
        get_db_connection=get_db_connection,
        insert_alert=_insert_monitor_alert,
    )


@tw_stock_bp.route("/monitor/scan-all", methods=["POST"])
def scan_all_monitors():
    """Scan enabled TWStock monitor configs. Intended for cron/manual trigger, not trading."""
    data = _request_json()
    force = bool(data.get("force", False))
    try:
        result = run_tw_stock_monitor_scan_all(force=force, trigger_source="api", write_log=True)
        return jsonify({"code": 1, "msg": "success", "data": result})
    except Exception as exc:
        logger.error(f"TWStock monitor scan-all failed: {exc}", exc_info=True)
        return jsonify({"code": 0, "msg": f"Failed to scan monitors: {exc}", "data": None}), 500


@tw_stock_bp.route("/monitor/scan-logs", methods=["GET"])
def get_monitor_scan_logs():
    """Return recent TWStock monitor scan logs for deployment visibility."""
    try:
        limit = max(1, min(int(request.args.get("limit", 20)), 100))
    except Exception:
        limit = 20
    try:
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                """
                SELECT id, trigger_source, status, monitor_count, scanned_count, alert_count,
                       error, result_summary, duration_ms, created_at
                FROM qd_tw_stock_monitor_scan_logs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cur.fetchall() or []
            cur.close()
        items = []
        for row in rows:
            summary = row.get("result_summary") or {}
            if isinstance(summary, str):
                try:
                    summary = json.loads(summary)
                except Exception:
                    summary = {}
            items.append({
                "id": row.get("id"),
                "trigger_source": row.get("trigger_source"),
                "status": row.get("status"),
                "monitor_count": row.get("monitor_count"),
                "scanned_count": row.get("scanned_count"),
                "alert_count": row.get("alert_count"),
                "error": row.get("error") or "",
                "result_summary": summary,
                "duration_ms": row.get("duration_ms"),
                "created_at": row.get("created_at"),
            })
        return jsonify({"code": 1, "msg": "success", "data": {"items": items, "count": len(items), "health": monitor_service.summarize_scan_health(items)}})
    except Exception as exc:
        logger.error(f"TWStock monitor scan logs failed: {exc}", exc_info=True)
        return jsonify({"code": 0, "msg": f"Failed to get monitor scan logs: {exc}", "data": None}), 500


TW_STOCK_MONITOR_HTML = """
<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>台股趨勢監控</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --line: #d9dde5;
      --text: #17202a;
      --muted: #667085;
      --accent: #176b87;
      --accent-2: #b35c1e;
      --good: #176b3a;
      --warn: #9a6700;
      --bad: #b42318;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      letter-spacing: 0;
    }
    header {
      padding: 20px 24px 14px;
      border-bottom: 1px solid var(--line);
      background: #ffffff;
    }
    h1 { margin: 0 0 6px; font-size: 24px; font-weight: 700; }
    .subtitle { margin: 0; color: var(--muted); font-size: 14px; }
    main { padding: 18px 24px 28px; max-width: 1280px; margin: 0 auto; }
    .toolbar {
      display: grid;
      grid-template-columns: minmax(260px, 1fr) 120px 150px 140px auto;
      gap: 10px;
      align-items: end;
      margin-bottom: 16px;
    }
    label { display: grid; gap: 6px; color: var(--muted); font-size: 12px; font-weight: 600; }
    input, select, button {
      height: 38px;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--text);
      padding: 0 10px;
      font-size: 14px;
      border-radius: 6px;
    }
    button { cursor: pointer; font-weight: 700; }
    button.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
    button.ghost { background: #fff; }
    .statusbar {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      margin-bottom: 16px;
      color: var(--muted);
      font-size: 13px;
    }
    .pill {
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 4px 9px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      white-space: nowrap;
    }
    .pill.good { color: var(--good); border-color: #b8dfc7; }
    .pill.warn { color: var(--warn); border-color: #ead08a; }
    .pill.bad { color: var(--bad); border-color: #f3b8b3; }
    .grid { display: grid; grid-template-columns: 1fr; gap: 10px; }
    .row {
      display: grid;
      grid-template-columns: 92px 96px 90px 120px repeat(5, minmax(86px, 1fr)) 180px;
      gap: 8px;
      align-items: center;
      min-height: 56px;
      padding: 10px 12px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }
    .head { min-height: 34px; color: var(--muted); font-size: 12px; font-weight: 700; background: transparent; border-color: transparent; padding-top: 0; padding-bottom: 0; }
    .symbol { font-size: 16px; font-weight: 750; }
    .score { font-size: 20px; font-weight: 800; color: var(--accent); }
    .label { font-weight: 700; }
    .small { color: var(--muted); font-size: 12px; line-height: 1.35; overflow-wrap: anywhere; }
    .right { text-align: right; }
    .alertbox {
      display: none;
      margin-bottom: 14px;
      padding: 10px 12px;
      border: 1px solid #ead08a;
      background: #fff8df;
      color: #6f4f00;
      border-radius: 8px;
      font-size: 13px;
    }
    .alertbox.visible { display: block; }
    .panel {
      margin-bottom: 14px;
      padding: 12px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }
    .panel-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      margin-bottom: 10px;
    }
    .panel-title { font-size: 15px; font-weight: 800; }
    .panel-tools { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
    .mini-select { height: 32px; min-width: 110px; }
    #trendChart { width: 100%; height: 180px; display: block; border: 1px solid var(--line); border-radius: 6px; background: #fbfcfd; }
    .alert-line { display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: center; padding: 6px 0; border-top: 1px solid #ead08a; }
    .alert-line:first-child { border-top: 0; }
    .alert-actions { display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end; }
    .alert-actions button { height: 28px; padding: 0 8px; font-size: 12px; }
    @media (max-width: 980px) {
      main { padding: 14px; }
      .toolbar { grid-template-columns: 1fr 1fr; }
      .row { grid-template-columns: 1fr 1fr; align-items: start; }
      .head { display: none; }
      .right { text-align: left; }
      .row > div::before { display: block; color: var(--muted); font-size: 11px; margin-bottom: 2px; }
      .row > div:nth-child(1)::before { content: "代碼"; }
      .row > div:nth-child(2)::before { content: "趨勢"; }
      .row > div:nth-child(3)::before { content: "分數"; }
      .row > div:nth-child(4)::before { content: "最新"; }
      .row > div:nth-child(5)::before { content: "5日"; }
      .row > div:nth-child(6)::before { content: "20日"; }
      .row > div:nth-child(7)::before { content: "60日"; }
      .row > div:nth-child(8)::before { content: "均線"; }
      .row > div:nth-child(9)::before { content: "量比/波動"; }
      .row > div:nth-child(10)::before { content: "品質"; }
    }
  </style>
</head>
<body>
  <header>
    <h1>台股趨勢監控</h1>
    <p class="subtitle">自動刷新與提醒只用於研究判斷；買賣決策由你手動完成。</p>
  </header>
  <main>
    <section class="toolbar" aria-label="monitor controls">
      <label>觀察列表
        <input id="symbols" value="2330,0050,00878" spellcheck="false" autocomplete="off">
      </label>
      <label>日線數
        <input id="limit" type="number" min="20" max="500" step="10" value="120">
      </label>
      <label>刷新頻率
        <select id="interval">
          <option value="0">手動</option>
          <option value="60">1 分鐘</option>
          <option value="300">5 分鐘</option>
          <option value="900">15 分鐘</option>
        </select>
      </label>
      <label>分數變化提醒
        <input id="threshold" type="number" min="1" max="50" step="1" value="8">
      </label>
      <div style="display:flex; gap:8px; flex-wrap:wrap">
        <button class="primary" id="refresh">刷新</button>
        <button class="ghost" id="toggle">啟動監控</button>
        <button class="ghost" id="serverScan">後端掃描</button>
      </div>
    </section>
    <div id="alerts" class="alertbox"></div>
    <section class="panel" aria-label="trend history chart">
      <div class="panel-head">
        <div>
          <div class="panel-title">趨勢分數曲線</div>
          <div id="trendMeta" class="small">等待後端掃描累積歷史</div>
        </div>
        <div class="panel-tools">
          <select id="chartSymbol" class="mini-select" aria-label="chart symbol"></select>
          <button class="ghost" id="loadTrendHistory">載入曲線</button>
        </div>
      </div>
      <canvas id="trendChart" width="980" height="180"></canvas>
    </section>
    <section class="panel" aria-label="alert review">
      <div class="panel-head">
        <div>
          <div class="panel-title">提醒與人工備註</div>
          <div class="small">提醒只供研究復盤，按鈕只更新備註狀態。</div>
        </div>
        <div class="panel-tools">
          <select id="alertFilter" class="mini-select" aria-label="alert filter">
            <option value="all">全部提醒</option>
            <option value="unread">未讀提醒</option>
          </select>
          <button class="ghost" id="reloadAlerts">重新載入</button>
        </div>
      </div>
      <div id="history" class="alertbox"></div>
    </section>
    <div class="statusbar">
      <span id="state" class="pill">待刷新</span>
      <span id="updated" class="pill">尚未取得資料</span>
      <span class="pill">只讀：不下單</span>
    </div>
    <section class="grid" id="grid" aria-live="polite">
      <div class="row head">
        <div>代碼</div><div>趨勢</div><div class="right">分數</div><div>最新</div><div class="right">5日</div><div class="right">20日</div><div class="right">60日</div><div>均線</div><div>量比/波動</div><div>品質</div>
      </div>
    </section>
  </main>
  <script>
    const $ = (id) => document.getElementById(id);
    const state = { timer: null, running: false, previous: new Map(), monitorName: "default", lastItems: [] };
    const fmtPct = (v) => v === null || v === undefined ? "-" : `${(Number(v) * 100).toFixed(2)}%`;
    const fmtNum = (v, d = 2) => v === null || v === undefined ? "-" : Number(v).toFixed(d);
    const setState = (text, cls = "") => { const el = $("state"); el.className = `pill ${cls}`; el.textContent = text; };

    async function api(path, options = {}) {
      const res = await fetch(path, options);
      const body = await res.json();
      if (!res.ok || body.code !== 1) throw new Error(body.msg || `HTTP ${res.status}`);
      return body.data;
    }

    function currentConfigPayload() {
      return {
        name: state.monitorName,
        symbols: $("symbols").value.split(",").map((s) => s.trim()).filter(Boolean),
        limit_bars: Number($("limit").value || 120),
        refresh_interval_sec: Number($("interval").value || 0),
        score_change_threshold: Number($("threshold").value || 8),
        enabled: state.running,
      };
    }

    function persistLocal() {
      localStorage.setItem("twStockMonitor", JSON.stringify({
        symbols: $("symbols").value,
        limit: $("limit").value,
        interval: $("interval").value,
        threshold: $("threshold").value,
      }));
    }

    async function persistRemote() {
      persistLocal();
      try {
        await api("/api/tw-stock/monitor/config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(currentConfigPayload()),
        });
      } catch (e) {
        setState(`本地已保存，後端保存失敗：${e.message}`, "warn");
      }
    }

    async function restore() {
      try {
        const saved = JSON.parse(localStorage.getItem("twStockMonitor") || "{}");
        for (const key of ["symbols", "limit", "interval", "threshold"]) if (saved[key]) $(key).value = saved[key];
      } catch (_) {}
      try {
        const cfg = await api("/api/tw-stock/monitor/config");
        if (Array.isArray(cfg.symbols) && cfg.symbols.length) $("symbols").value = cfg.symbols.join(",");
        if (cfg.limit_bars) $("limit").value = cfg.limit_bars;
        if (cfg.refresh_interval_sec !== undefined) $("interval").value = cfg.refresh_interval_sec;
        if (cfg.score_change_threshold !== undefined) $("threshold").value = cfg.score_change_threshold;
        state.running = Boolean(cfg.enabled);
        $("toggle").textContent = state.running ? "停止監控" : "啟動監控";
      } catch (e) {
        setState(`使用本地配置：${e.message}`, "warn");
      }
    }

    async function recordAlert(item, alertType, message, severity = "info") {
      try {
        await api("/api/tw-stock/monitor/alerts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: state.monitorName,
            symbol: item.symbol,
            alert_type: alertType,
            severity,
            message,
            snapshot: item,
          }),
        });
      } catch (_) {}
    }

    async function detectAlerts(items) {
      const threshold = Number($("threshold").value || 8);
      const messages = [];
      for (const item of items) {
        if (!item.ok) continue;
        const prev = state.previous.get(item.symbol);
        const score = Number(item.trend?.score || 0);
        const label = item.trend?.label || "unknown";
        if (prev) {
          if (prev.label !== label) {
            const msg = `${item.symbol} 趨勢由 ${prev.label} 變為 ${label}`;
            messages.push(msg);
            await recordAlert(item, "label_change", msg, "warning");
          }
          if (Math.abs(score - prev.score) >= threshold) {
            const msg = `${item.symbol} 分數變化 ${prev.score.toFixed(2)} → ${score.toFixed(2)}`;
            messages.push(msg);
            await recordAlert(item, "score_change", msg, "info");
          }
        }
        if ((item.quality?.warnings || []).length) {
          const msg = `${item.symbol} 資料品質提示：${item.quality.warnings.join(", ")}`;
          messages.push(msg);
          await recordAlert(item, "quality_warning", msg, "warning");
        }
        state.previous.set(item.symbol, { score, label });
      }
      const box = $("alerts");
      box.textContent = messages.join("；");
      box.className = messages.length ? "alertbox visible" : "alertbox";
      if (messages.length) loadHistory().catch(() => {});
    }

    function updateSymbolOptions(items) {
      const select = $("chartSymbol");
      const current = select.value;
      const symbols = (items || []).filter((item) => item.ok).map((item) => item.symbol);
      select.innerHTML = symbols.map((symbol) => `<option value="${symbol}">${symbol}</option>`).join("");
      if (symbols.includes(current)) select.value = current;
      else if (symbols.length) select.value = symbols[0];
    }

    function drawTrendChart(items) {
      const canvas = $("trendChart");
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      const width = canvas.width;
      const height = canvas.height;
      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = "#fbfcfd";
      ctx.fillRect(0, 0, width, height);
      ctx.strokeStyle = "#d9dde5";
      ctx.lineWidth = 1;
      for (const y of [20, 90, 160]) { ctx.beginPath(); ctx.moveTo(36, y); ctx.lineTo(width - 12, y); ctx.stroke(); }
      ctx.fillStyle = "#667085";
      ctx.font = "12px sans-serif";
      ctx.fillText("100", 6, 24);
      ctx.fillText("50", 12, 94);
      ctx.fillText("0", 18, 164);
      if (!items.length) {
        ctx.fillText("尚無趨勢歷史；請先執行後端掃描。", 48, 96);
        return;
      }
      const usableW = width - 56;
      const xFor = (idx) => 40 + (items.length === 1 ? usableW / 2 : idx * usableW / (items.length - 1));
      const yFor = (score) => 164 - Math.max(0, Math.min(100, Number(score || 0))) * 1.44;
      ctx.strokeStyle = "#176b87";
      ctx.lineWidth = 2;
      ctx.beginPath();
      items.forEach((item, idx) => {
        const x = xFor(idx);
        const y = yFor(item.score);
        if (idx === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      });
      ctx.stroke();
      ctx.fillStyle = "#b35c1e";
      items.forEach((item, idx) => {
        const x = xFor(idx);
        const y = yFor(item.score);
        ctx.beginPath();
        ctx.arc(x, y, 3.5, 0, Math.PI * 2);
        ctx.fill();
      });
      const latest = items[items.length - 1];
      ctx.fillStyle = "#17202a";
      ctx.fillText(`${latest.latest_date || "-"} · ${latest.label || "unknown"} · ${Number(latest.score || 0).toFixed(2)}`, 48, 18);
    }

    async function loadTrendHistory() {
      const symbol = $("chartSymbol").value || ($("symbols").value.split(",").map((s) => s.trim()).filter(Boolean)[0] || "");
      const meta = $("trendMeta");
      if (!symbol) { meta.textContent = "請先輸入觀察列表"; drawTrendChart([]); return; }
      try {
        const data = await api(`/api/tw-stock/monitor/history?symbol=${encodeURIComponent(symbol)}&limit=120&monitor_name=${encodeURIComponent(state.monitorName)}`);
        const items = data.items || [];
        drawTrendChart(items);
        meta.textContent = items.length ? `${symbol} 共 ${items.length} 個歷史點，最新 ${items[items.length - 1].latest_date || "-"}` : `${symbol} 尚無歷史點，請先執行後端掃描`;
      } catch (e) {
        meta.textContent = `曲線載入失敗：${e.message}`;
        drawTrendChart([]);
      }
    }

    async function loadHistory() {
      const unreadOnly = $("alertFilter")?.value === "unread";
      const data = await api(`/api/tw-stock/monitor/alerts?limit=8${unreadOnly ? "&unread_only=true" : ""}`);
      const items = data.items || [];
      const box = $("history");
      if (!items.length) { box.className = "alertbox visible"; box.textContent = unreadOnly ? "沒有未讀提醒" : "目前沒有提醒"; return; }
      box.className = "alertbox visible";
      box.innerHTML = items.map((item) => `
        <div class="alert-line">
          <span>${item.symbol} · ${item.message} · ${item.decision_status || "pending"} · ${new Date(item.created_at).toLocaleString()}</span>
          <span class="alert-actions">
            <button class="ghost" data-alert-id="${item.id}" data-status="watch">觀察</button>
            <button class="ghost" data-alert-id="${item.id}" data-status="ignored">忽略</button>
            <button class="ghost" data-alert-id="${item.id}" data-status="acted">已處理</button>
          </span>
        </div>
      `).join("");
      box.querySelectorAll("button[data-alert-id]").forEach((btn) => btn.addEventListener("click", async () => {
        const status = btn.dataset.status || "watch";
        await api(`/api/tw-stock/monitor/alerts/${btn.dataset.alertId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ is_read: true, decision_status: status, user_note: `manual ${status}` }),
        });
        loadHistory().catch(() => {});
      }));
    }

    function render(items) {
      state.lastItems = items || [];
      updateSymbolOptions(state.lastItems);
      const grid = $("grid");
      grid.querySelectorAll(".data").forEach((node) => node.remove());
      for (const item of items) {
        const row = document.createElement("div");
        row.className = "row data";
        const warnings = item.quality?.warnings || [];
        const qualityClass = warnings.length ? "warn" : "good";
        row.innerHTML = `
          <div><div class="symbol">${item.symbol || "-"}</div><div class="small">${item.exchange || "TWSE"}</div></div>
          <div><span class="label">${item.trend?.label || item.error || "unknown"}</span><div class="small">${item.trend?.summary || "無資料"}</div></div>
          <div class="score right">${fmtNum(item.trend?.score, 2)}</div>
          <div><div>${item.latest?.date || item.quality?.latest_date || "-"}</div><div class="small">收 ${fmtNum(item.latest?.close, 2)}</div></div>
          <div class="right">${fmtPct(item.returns?.ret_5d)}</div>
          <div class="right">${fmtPct(item.returns?.ret_20d)}</div>
          <div class="right">${fmtPct(item.returns?.ret_60d)}</div>
          <div class="small">MA20 ${fmtNum(item.moving_averages?.ma20, 2)}<br>MA60 ${fmtNum(item.moving_averages?.ma60, 2)}</div>
          <div class="small">量比 ${fmtNum(item.volume?.ratio_to_avg20, 2)}<br>波動 ${fmtPct(item.risk?.volatility_20d_annualized)}</div>
          <div><span class="pill ${qualityClass}">${warnings.length ? "需檢查" : "正常"}</span><div class="small">${warnings.join(", ") || `stale ${item.quality?.stale_days ?? "-"} 天`}</div></div>
        `;
        grid.appendChild(row);
      }
    }

    async function refresh() {
      persistLocal();
      const symbols = $("symbols").value.trim();
      const limit = $("limit").value || "120";
      if (!symbols) { setState("請輸入觀察列表", "bad"); return; }
      setState("刷新中");
      const res = await fetch(`/api/tw-stock/trends?symbols=${encodeURIComponent(symbols)}&limit=${encodeURIComponent(limit)}`);
      const body = await res.json();
      if (!res.ok || body.code !== 1) throw new Error(body.msg || `HTTP ${res.status}`);
      const items = body.data?.items || [];
      render(items);
      await detectAlerts(items);
      loadTrendHistory().catch(() => {});
      $("updated").textContent = `更新 ${new Date().toLocaleString()}`;
      setState(state.running ? "監控中" : "已刷新", state.running ? "good" : "");
    }

    function schedule() {
      if (state.timer) clearInterval(state.timer);
      const seconds = Number($("interval").value || 0);
      if (state.running && seconds > 0) state.timer = setInterval(() => refresh().catch((e) => setState(e.message, "bad")), seconds * 1000);
    }

    $("refresh").addEventListener("click", () => { persistRemote().finally(() => refresh().catch((e) => setState(e.message, "bad"))); });
    $("serverScan").addEventListener("click", async () => {
      try {
        await persistRemote();
        setState("後端掃描中");
        const result = await api("/api/tw-stock/monitor/scan", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: state.monitorName, force: true }),
        });
        setState(`後端掃描完成：${result.alert_count || 0} 則提醒`, "good");
        await loadHistory();
        if (result.items) render(result.items);
        await loadTrendHistory();
      } catch (e) {
        setState(e.message, "bad");
      }
    });
    $("loadTrendHistory").addEventListener("click", () => loadTrendHistory().catch((e) => setState(e.message, "bad")));
    $("chartSymbol").addEventListener("change", () => loadTrendHistory().catch((e) => setState(e.message, "bad")));
    $("reloadAlerts").addEventListener("click", () => loadHistory().catch((e) => setState(e.message, "bad")));
    $("alertFilter").addEventListener("change", () => loadHistory().catch((e) => setState(e.message, "bad")));
    $("toggle").addEventListener("click", () => {
      state.running = !state.running;
      $("toggle").textContent = state.running ? "停止監控" : "啟動監控";
      schedule();
      persistRemote().finally(() => refresh().catch((e) => setState(e.message, "bad")));
    });
    for (const id of ["symbols", "limit", "interval", "threshold"]) $(id).addEventListener("change", () => { persistRemote(); schedule(); });
    restore().then(() => { schedule(); refresh().catch((e) => setState(e.message, "bad")); loadHistory().catch(() => {}); loadTrendHistory().catch(() => {}); });
  </script>
</body>
</html>
"""


@tw_stock_bp.route("/monitor", methods=["GET"])
def monitor_page():
    """Return a local read-only TWStock trend monitoring page."""
    return render_template_string(TW_STOCK_MONITOR_HTML)
