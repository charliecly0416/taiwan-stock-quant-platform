"""Static boundary contract for the consolidated Taiwan-stock API surface.

The existing ``tw_stock`` blueprint remains the compatibility owner during
ARCH-3.  This module provides the explicit route ownership map and method
classification used by focused tests and later blueprint extraction; it does
not register a new endpoint or alter runtime defaults.
"""
from __future__ import annotations

from typing import Any, Iterable


ROUTE_MODULES: dict[str, tuple[str, ...]] = {
    "readonly_model_strategy_comparison": (
        "/api/tw-stock/readonly/model-strategy-comparison",
    ),
    "tw_stock_ops_routes": (
        "/api/tw-stock/quant/ops/",
        "/api/tw-stock/monitor",
        "/api/tw-stock/monitor/",
    ),
    "tw_stock_replay_routes": (
        "/api/tw-stock/readonly-replay-window",
        "/api/tw-stock/readonly-replay-window-index",
        "/api/tw-stock/rank-tech-cross/observation-replay",
        "/api/tw-stock/rank-tech-cross/portfolio-replay",
    ),
    "tw_stock_context_routes": (
        "/api/tw-stock/current-strategy-context",
        "/api/tw-stock/phase-yz/productization-status",
        "/api/tw-stock/readonly-shadow-exposure",
        "/api/tw-stock/readonly-strategy-snapshot",
        "/api/tw-stock/tradingagents-readonly-analysis/",
        "/api/tw-stock/cross-analysis/",
        "/api/tw-stock/rank-tech-cross/",
        "/api/tw-stock/quant/signals/",
        "/api/tw-stock/ltr-readonly-explanation",
        "/api/tw-stock/ltr-optional-sim-strategies",
        "/api/tw-stock/trend",
        "/api/tw-stock/trends",
    ),
    "tw_stock_paper_routes": (
        "/api/tw-stock/paper-portfolio/",
        "/api/tw-stock/sim/",
    ),
    "tw_stock_agent_routes": (
        "/api/tw-stock/agent/",
    ),
}

READONLY_GET_PREFIXES = (
    "/api/tw-stock/readonly/model-strategy-comparison",
    "/api/tw-stock/current-strategy-context",
    "/api/tw-stock/phase-yz/productization-status",
    "/api/tw-stock/readonly-",
    "/api/tw-stock/tradingagents-readonly-analysis/",
    "/api/tw-stock/quant/signals/",
    "/api/tw-stock/cross-analysis/latest",
    "/api/tw-stock/cross-analysis/symbol/",
    "/api/tw-stock/rank-tech-cross/latest",
    "/api/tw-stock/rank-tech-cross/observation-replay",
    "/api/tw-stock/paper-portfolio/state",
    "/api/tw-stock/paper-portfolio/latest-decision",
    "/api/tw-stock/paper-portfolio/apply-runs",
    "/api/tw-stock/agent/context",
    "/api/tw-stock/ltr-readonly-explanation",
    "/api/tw-stock/ltr-optional-sim-strategies",
)

SIMULATION_POST_ROUTES = (
    "/api/tw-stock/rank-tech-cross/portfolio-replay",
    "/api/indicator/backtest",
)

READONLY_EXPLANATION_POST_ROUTES = (
    "/api/tw-stock/agent/preview",
    "/api/tw-stock/agent/chat",
    "/api/tw-stock/agent/simple-chat",
)

ACCOUNT_WRITE_POST_PREFIXES = (
    "/api/tw-stock/paper-portfolio/apply-decision",
    "/api/tw-stock/paper-portfolio/reset",
    "/api/tw-stock/sim/accounts",
    "/api/tw-stock/sim/orders/",
)

BODY_SAFETY_CONTRACT = {
    "readonly_get": ("readonly_only", "not_order", "not_target_position"),
    "readonly_explanation_post": ("readonly_only", "not_order", "not_target_position"),
    "readonly_simulation_post": ("persist=false", "not_order", "not_target_position"),
    "simulation_account_write_post": ("simulation_only", "paper_only", "not_real_order", "not_target_position"),
    "operational_write": ("explicit_permission_or_confirmation",),
}


def route_module(path: str) -> str | None:
    """Return the planned owner for a route without importing route handlers."""
    if path == "/api/indicator/backtest":
        return "tw_stock_replay_routes"
    for module, prefixes in ROUTE_MODULES.items():
        if any(path.startswith(prefix) for prefix in prefixes):
            return module
    return None


def classify_route(path: str, methods: Iterable[str]) -> str:
    """Classify HTTP semantics for static/API contract checks."""
    method_set = {str(method).upper() for method in methods}
    if "GET" in method_set and (
        path.startswith("/api/tw-stock/")
        or any(path.startswith(prefix) for prefix in READONLY_GET_PREFIXES)
    ):
        return "readonly_get"
    if "POST" in method_set and path in SIMULATION_POST_ROUTES:
        return "readonly_simulation_post"
    if "POST" in method_set and path in READONLY_EXPLANATION_POST_ROUTES:
        return "readonly_explanation_post"
    if "POST" in method_set and any(path.startswith(prefix) for prefix in ACCOUNT_WRITE_POST_PREFIXES):
        return "simulation_account_write_post"
    if "POST" in method_set or "PUT" in method_set or "PATCH" in method_set or "DELETE" in method_set:
        return "operational_write"
    return "unclassified"


def snapshot_url_map(rules: Iterable[Any]) -> list[dict[str, Any]]:
    """Produce deterministic route/method/module evidence from Flask rules."""
    rows = []
    for rule in rules:
        path = str(getattr(rule, "rule", ""))
        if not path.startswith("/api/tw-stock") and path != "/api/indicator/backtest":
            continue
        methods = sorted(str(method).upper() for method in getattr(rule, "methods", set()) if method not in {"HEAD", "OPTIONS"})
        rows.append({"path": path, "methods": methods, "module": route_module(path), "classification": classify_route(path, methods)})
    return sorted(rows, key=lambda row: (row["path"], row["methods"]))
