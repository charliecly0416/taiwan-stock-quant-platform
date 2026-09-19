"""Strategy and research-context compatibility routes extracted from aggregate."""
from __future__ import annotations

from flask import Blueprint

tw_stock_context_bp = Blueprint("tw_stock_context", __name__)


def _legacy(name: str, *args):
    from app.routes import tw_stock

    return getattr(tw_stock, name)(*args)


@tw_stock_context_bp.route("/phase-yz/productization-status", methods=["GET"])
def get_phase_yz_productization_status(): return _legacy("get_phase_yz_productization_status")


@tw_stock_context_bp.route("/current-strategy-context", methods=["GET"])
def get_current_strategy_context(): return _legacy("get_current_strategy_context")


@tw_stock_context_bp.route("/readonly-shadow-exposure", methods=["GET"])
def get_readonly_shadow_exposure(): return _legacy("get_readonly_shadow_exposure")


@tw_stock_context_bp.route("/tradingagents-readonly-analysis/latest", methods=["GET"])
def get_tradingagents_readonly_analysis_latest(): return _legacy("get_tradingagents_readonly_analysis_latest")


@tw_stock_context_bp.route("/tradingagents-readonly-analysis/<run_id>", methods=["GET"])
def get_tradingagents_readonly_analysis_run(run_id: str): return _legacy("get_tradingagents_readonly_analysis_run", run_id)


@tw_stock_context_bp.route("/trend", methods=["GET"])
def get_trend(): return _legacy("get_trend")


@tw_stock_context_bp.route("/trends", methods=["GET"])
def get_trends(): return _legacy("get_trends")


@tw_stock_context_bp.route("/quant/signals/latest", methods=["GET"])
def get_latest_qlib_option_c_signals(): return _legacy("get_latest_qlib_option_c_signals")


@tw_stock_context_bp.route("/quant/signals/rank-changes", methods=["GET"])
def get_qlib_option_c_rank_changes(): return _legacy("get_qlib_option_c_rank_changes")


@tw_stock_context_bp.route("/quant/signals/health", methods=["GET"])
def get_qlib_option_c_signal_health(): return _legacy("get_qlib_option_c_signal_health")


@tw_stock_context_bp.route("/quant/signals/runs", methods=["GET"])
def get_qlib_option_c_signal_runs(): return _legacy("get_qlib_option_c_signal_runs")


@tw_stock_context_bp.route("/quant/signals/runs/<run_id>", methods=["GET"])
def get_qlib_option_c_signal_run_detail(run_id: str): return _legacy("get_qlib_option_c_signal_run_detail", run_id)


@tw_stock_context_bp.route("/cross-analysis/latest", methods=["GET"])
def get_tw_stock_cross_analysis_latest(): return _legacy("get_tw_stock_cross_analysis_latest")


@tw_stock_context_bp.route("/rank-tech-cross/latest", methods=["GET"])
def get_tw_stock_rank_tech_cross_latest(): return _legacy("get_tw_stock_rank_tech_cross_latest")


@tw_stock_context_bp.route("/ltr-readonly-explanation", methods=["GET"])
def get_tw_stock_ltr_readonly_explanation(): return _legacy("get_tw_stock_ltr_readonly_explanation")


@tw_stock_context_bp.route("/ltr-optional-sim-strategies", methods=["GET"])
def get_tw_stock_ltr_optional_sim_strategies(): return _legacy("get_tw_stock_ltr_optional_sim_strategies")


@tw_stock_context_bp.route("/cross-analysis/symbol/<symbol>", methods=["GET"])
def get_tw_stock_cross_analysis_symbol(symbol: str): return _legacy("get_tw_stock_cross_analysis_symbol", symbol)


@tw_stock_context_bp.route("/cross-analysis/history/import-latest", methods=["POST"])
def import_tw_stock_cross_analysis_history_latest(): return _legacy("import_tw_stock_cross_analysis_history_latest")


@tw_stock_context_bp.route("/cross-analysis/history/runs", methods=["GET"])
def get_tw_stock_cross_analysis_history_runs(): return _legacy("get_tw_stock_cross_analysis_history_runs")


@tw_stock_context_bp.route("/cross-analysis/history/signals", methods=["GET"])
def get_tw_stock_cross_analysis_history_signals(): return _legacy("get_tw_stock_cross_analysis_history_signals")


@tw_stock_context_bp.route("/cross-analysis/history/alerts", methods=["GET"])
def get_tw_stock_cross_analysis_history_alerts(): return _legacy("get_tw_stock_cross_analysis_history_alerts")


@tw_stock_context_bp.route("/cross-analysis/reviews", methods=["GET"])
def get_tw_stock_cross_analysis_reviews(): return _legacy("get_tw_stock_cross_analysis_reviews")


@tw_stock_context_bp.route("/cross-analysis/reviews", methods=["PUT"])
def save_tw_stock_cross_analysis_review(): return _legacy("save_tw_stock_cross_analysis_review")
