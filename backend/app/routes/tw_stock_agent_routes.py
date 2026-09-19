"""Agent route group extracted from the TW-stock compatibility aggregate.

The first extraction deliberately delegates to the existing handler functions
so request/response semantics remain byte-for-byte compatible while ownership
moves to a separately registered blueprint.
"""
from __future__ import annotations

from flask import Blueprint

tw_stock_agent_bp = Blueprint("tw_stock_agent", __name__)


@tw_stock_agent_bp.route("/agent/context", methods=["GET"])
def get_tw_stock_agent_context():
    from app.routes.tw_stock import get_tw_stock_agent_context as legacy

    return legacy()


@tw_stock_agent_bp.route("/agent/preview", methods=["POST"])
def preview_tw_stock_agent_answer():
    from app.routes.tw_stock import preview_tw_stock_agent_answer as legacy

    return legacy()


@tw_stock_agent_bp.route("/agent/chat", methods=["POST"])
def chat_tw_stock_agent_answer():
    from app.routes.tw_stock import chat_tw_stock_agent_answer as legacy

    return legacy()


@tw_stock_agent_bp.route("/agent/simple-chat", methods=["POST"])
def simple_chat_tw_stock_agent_answer():
    from app.routes.tw_stock import simple_chat_tw_stock_agent_answer as legacy

    return legacy()
