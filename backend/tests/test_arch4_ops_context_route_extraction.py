from __future__ import annotations

from app.routes.tw_stock_boundary_contract import classify_route


def _rules(app, prefixes):
    return [rule for rule in app.url_map.iter_rules() if any(rule.rule.startswith(prefix) for prefix in prefixes)]


def test_ops_routes_are_registered_on_extracted_blueprint(app) -> None:
    rows = _rules(app, ("/api/tw-stock/quant/ops/", "/api/tw-stock/monitor"))
    assert len(rows) == 25
    assert all(rule.endpoint.startswith("tw_stock_ops.") for rule in rows)


def test_context_routes_are_registered_on_extracted_blueprint(app) -> None:
    prefixes = (
        "/api/tw-stock/phase-yz/",
        "/api/tw-stock/current-strategy-context",
        "/api/tw-stock/readonly-shadow-exposure",
        "/api/tw-stock/tradingagents-readonly-analysis/",
        "/api/tw-stock/trend",
        "/api/tw-stock/trends",
        "/api/tw-stock/quant/signals/",
        "/api/tw-stock/cross-analysis/",
        "/api/tw-stock/rank-tech-cross/latest",
        "/api/tw-stock/ltr-readonly-explanation",
        "/api/tw-stock/ltr-optional-sim-strategies",
    )
    rows = _rules(app, prefixes)
    assert len(rows) == 23
    assert all(rule.endpoint.startswith("tw_stock_context.") for rule in rows)


def test_context_mutation_routes_keep_non_simulation_classification(app) -> None:
    rows = [
        rule for rule in app.url_map.iter_rules()
        if rule.rule in {
            "/api/tw-stock/cross-analysis/history/import-latest",
            "/api/tw-stock/cross-analysis/reviews",
        }
    ]
    assert len(rows) == 3
    writes = [rule for rule in rows if any(m in {"POST", "PUT", "PATCH", "DELETE"} for m in rule.methods)]
    assert len(writes) == 2
    assert all(
        classify_route(rule.rule, [m for m in rule.methods if m not in {"HEAD", "OPTIONS"}]) == "operational_write"
        for rule in writes
    )
