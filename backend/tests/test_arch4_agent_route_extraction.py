from __future__ import annotations


def test_agent_routes_are_registered_on_extracted_blueprint(app) -> None:
    rows = {
        rule.rule: rule.endpoint
        for rule in app.url_map.iter_rules()
        if rule.rule.startswith("/api/tw-stock/agent/")
    }
    assert rows
    assert set(rows) == {
        "/api/tw-stock/agent/context",
        "/api/tw-stock/agent/preview",
        "/api/tw-stock/agent/chat",
        "/api/tw-stock/agent/simple-chat",
    }
    assert all(endpoint.startswith("tw_stock_agent.") for endpoint in rows.values())
    assert all(not endpoint.startswith("tw_stock.") for endpoint in rows.values())
