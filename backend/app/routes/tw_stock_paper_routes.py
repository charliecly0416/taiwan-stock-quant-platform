"""Simulation-account and paper-portfolio routes extracted from aggregate."""
from __future__ import annotations

from flask import Blueprint

tw_stock_paper_bp = Blueprint("tw_stock_paper", __name__)


def _legacy(name: str, *args):
    from app.routes import tw_stock

    return getattr(tw_stock, name)(*args)


@tw_stock_paper_bp.route("/sim/accounts", methods=["GET"])
def list_tw_stock_sim_accounts(): return _legacy("list_tw_stock_sim_accounts")


@tw_stock_paper_bp.route("/sim/accounts", methods=["POST"])
def create_tw_stock_sim_account(): return _legacy("create_tw_stock_sim_account")


@tw_stock_paper_bp.route("/sim/accounts/<account_uid>", methods=["GET"])
def get_tw_stock_sim_account(account_uid: str): return _legacy("get_tw_stock_sim_account", account_uid)


@tw_stock_paper_bp.route("/sim/accounts/<account_uid>/positions", methods=["GET"])
def get_tw_stock_sim_positions(account_uid: str): return _legacy("get_tw_stock_sim_positions", account_uid)


@tw_stock_paper_bp.route("/sim/accounts/<account_uid>/trades", methods=["GET"])
def get_tw_stock_sim_trades(account_uid: str): return _legacy("get_tw_stock_sim_trades", account_uid)


@tw_stock_paper_bp.route("/sim/orders/draft", methods=["POST"])
def draft_tw_stock_sim_order(): return _legacy("draft_tw_stock_sim_order")


@tw_stock_paper_bp.route("/sim/orders/<sim_order_uid>/confirm", methods=["POST"])
def confirm_tw_stock_sim_order(sim_order_uid: str): return _legacy("confirm_tw_stock_sim_order", sim_order_uid)


@tw_stock_paper_bp.route("/sim/orders/<sim_order_uid>/cancel", methods=["POST"])
def cancel_tw_stock_sim_order(sim_order_uid: str): return _legacy("cancel_tw_stock_sim_order", sim_order_uid)


@tw_stock_paper_bp.route("/paper-portfolio/state", methods=["GET"])
def get_tw_stock_paper_portfolio_state(): return _legacy("get_tw_stock_paper_portfolio_state")


@tw_stock_paper_bp.route("/paper-portfolio/apply-runs", methods=["GET"])
def get_tw_stock_paper_portfolio_apply_runs(): return _legacy("get_tw_stock_paper_portfolio_apply_runs")


@tw_stock_paper_bp.route("/paper-portfolio/latest-decision", methods=["GET"])
def get_tw_stock_paper_portfolio_latest_decision(): return _legacy("get_tw_stock_paper_portfolio_latest_decision")


@tw_stock_paper_bp.route("/paper-portfolio/apply-decision", methods=["POST"])
def apply_tw_stock_paper_portfolio_decision(): return _legacy("apply_tw_stock_paper_portfolio_decision")


@tw_stock_paper_bp.route("/paper-portfolio/reset", methods=["POST"])
def reset_tw_stock_paper_portfolio(): return _legacy("reset_tw_stock_paper_portfolio")
