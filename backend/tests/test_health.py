"""Test health endpoint."""


def test_health_endpoint(client):
    """GET /api/health should return 200."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None


def test_readiness_endpoint_reports_ready_dependencies(client, monkeypatch):
    from app.routes import health

    monkeypatch.setattr(health, "is_postgres_available", lambda: True)
    monkeypatch.setattr(health, "research_readiness", lambda: {
        "ready": True, "status": "ready", "checked_at": "2026-09-18T00:00:00Z",
        "signal_asof": "2026-09-18", "checks": [], "side_effects": "none",
    })
    response = client.get("/api/ready")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ready"] is True
    assert payload["checks"]["database"]["ready"] is True
    assert payload["checks"]["research_artifact_contract"]["ready"] is True


def test_readiness_endpoint_returns_503_without_hiding_failed_check(client, monkeypatch):
    from app.routes import health

    monkeypatch.setattr(health, "is_postgres_available", lambda: False)
    monkeypatch.setattr(health, "research_readiness", lambda: {
        "ready": False, "status": "not_ready", "checked_at": "2026-09-18T00:00:00Z",
        "signal_asof": None, "checks": [], "side_effects": "none",
    })
    response = client.get("/api/ready")
    payload = response.get_json()
    assert response.status_code == 503
    assert payload["ready"] is False
    assert payload["checks"]["database"]["code"] == "database_unavailable"
    assert payload["checks"]["research_artifact_contract"]["ready"] is False
