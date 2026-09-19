"""Replay route group extracted from the TW-stock compatibility aggregate."""
from __future__ import annotations

from flask import Blueprint

tw_stock_replay_bp = Blueprint("tw_stock_replay", __name__)


@tw_stock_replay_bp.route("/rank-tech-cross/observation-replay", methods=["GET"])
def get_tw_stock_observation_replay():
    from app.routes.tw_stock import get_tw_stock_observation_replay as legacy

    return legacy()


@tw_stock_replay_bp.route("/rank-tech-cross/portfolio-replay", methods=["POST"])
def run_tw_stock_portfolio_replay():
    from app.routes.tw_stock import run_tw_stock_portfolio_replay as legacy

    return legacy()
