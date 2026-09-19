from __future__ import annotations


def test_replay_routes_are_registered_on_extracted_blueprint(app) -> None:
    rows = {
        rule.rule: rule.endpoint
        for rule in app.url_map.iter_rules()
        if rule.rule in {
            "/api/tw-stock/rank-tech-cross/observation-replay",
            "/api/tw-stock/rank-tech-cross/portfolio-replay",
        }
    }
    assert rows
    assert all(endpoint.startswith("tw_stock_replay.") for endpoint in rows.values())


def test_portfolio_replay_extracted_route_preserves_no_persist_flags(app, monkeypatch) -> None:
    from app.routes import tw_stock as legacy

    monkeypatch.setattr(
        legacy.portfolio_replay_service,
        "replay",
        lambda config: {
            "ok": True,
            "persist": False,
            "writes_business_db": False,
            "simulation_only": True,
            "research_signal_not_order": True,
        },
    )
    response = app.test_client().post(
        "/api/tw-stock/rank-tech-cross/portfolio-replay",
        json={"persist": True},
    )
    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["persist"] is False
    assert payload["writes_business_db"] is False
    assert payload["simulation_only"] is True
    assert payload["research_signal_not_order"] is True
