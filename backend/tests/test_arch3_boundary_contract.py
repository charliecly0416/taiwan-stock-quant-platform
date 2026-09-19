from __future__ import annotations

from app.routes.tw_stock_boundary_contract import (
    ACCOUNT_WRITE_POST_PREFIXES,
    BODY_SAFETY_CONTRACT,
    READONLY_GET_PREFIXES,
    SIMULATION_POST_ROUTES,
    snapshot_url_map,
    classify_route,
    route_module,
)


def test_tw_stock_route_map_has_explicit_module_and_method_semantics(app) -> None:
    rows = snapshot_url_map(app.url_map.iter_rules())
    assert rows
    tw_rows = [row for row in rows if row["path"].startswith("/api/tw-stock")]
    assert tw_rows
    assert all(row["module"] for row in tw_rows), [row for row in tw_rows if not row["module"]]
    assert all(row["classification"] != "unclassified" for row in tw_rows), [row for row in tw_rows if row["classification"] == "unclassified"]

    for row in tw_rows:
        if row["classification"] == "readonly_get":
            assert row["methods"] == ["GET"], row
        if row["classification"] == "readonly_simulation_post":
            assert row["methods"] == ["POST"], row
        if row["classification"] == "simulation_account_write_post":
            assert "POST" in row["methods"], row


def test_boundary_contract_names_core_surfaces() -> None:
    rows = snapshot_url_map([])
    assert rows == []
    assert "/api/tw-stock/rank-tech-cross/portfolio-replay" in SIMULATION_POST_ROUTES
    assert "/api/indicator/backtest" in SIMULATION_POST_ROUTES
    assert any(prefix.endswith("apply-decision") for prefix in ACCOUNT_WRITE_POST_PREFIXES)
    assert any(prefix.endswith("current-strategy-context") for prefix in READONLY_GET_PREFIXES)
    assert classify_route("/api/tw-stock/agent/simple-chat", ["POST"]) == "readonly_explanation_post"
    assert classify_route("/api/indicator/backtest", ["POST"]) == "readonly_simulation_post"
    assert BODY_SAFETY_CONTRACT["readonly_simulation_post"] == ("persist=false", "not_order", "not_target_position")
    assert "paper_only" in BODY_SAFETY_CONTRACT["simulation_account_write_post"]


def test_model_comparison_is_registered_as_readonly_without_write_exception(client):
    path = "/api/tw-stock/readonly/model-strategy-comparison"
    assert route_module(path) == "readonly_model_strategy_comparison"
    assert classify_route(path, ["GET"]) == "readonly_get"
    assert classify_route(path, ["POST"]) == "operational_write"
    for method in ("post", "put", "patch", "delete"):
        assert getattr(client, method)(path).status_code == 405
