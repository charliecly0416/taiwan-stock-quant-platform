from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

from flask import Flask

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.routes import tw_stock as tw_stock_route
from app.routes.tw_stock_paper_routes import tw_stock_paper_bp
from app.services.tw_stock_paper_portfolio import TWStockPaperPortfolioService
from app.utils import auth as auth_mod

from test_tw_stock_paper_portfolio_x2 import (
    X2Db,
    _artifact_apply_payload,
    _write_authoritative_artifact,
    price_pending_status,
    price_ready_status,
    seed_account,
    sell_action,
)


class _RouteHarness:
    def __init__(self, tmp_path, monkeypatch, *, status_loader=price_ready_status):
        self.db = X2Db()
        seed_account(self.db)
        self.service = TWStockPaperPortfolioService(
            db_factory=lambda: self.db,
            now_fn=lambda: datetime.fromisoformat("2026-06-18T09:00:00"),
            artifact_root=tmp_path,
            allow_inline_intent=False,
            productization_status_loader=status_loader,
        )
        monkeypatch.setattr(tw_stock_route, "tw_stock_paper_portfolio_service", self.service)
        monkeypatch.setattr(auth_mod, "verify_token", lambda token: {"sub": "u7", "user_id": 7, "role": "user"})
        app = Flask(__name__)
        app.register_blueprint(tw_stock_route.tw_stock_bp, url_prefix="/api/tw-stock")
        app.register_blueprint(tw_stock_paper_bp, url_prefix="/api/tw-stock")
        self.client = app.test_client()
        self.headers = {"Authorization": "Bearer test-token"}
        self.tmp_path = tmp_path

    def artifact_payload(self, *, run_id="run", decision_id="decision-route", key="route-idem", actions=None, epoch=1, account_id="tw_sim_1", state_checksum="sha256:route-state"):
        intent, artifact_path = _write_authoritative_artifact(
            self.tmp_path,
            run_id=run_id,
            decision_id=decision_id,
            account_id=account_id,
            epoch=epoch,
            actions=[sell_action()] if actions is None else actions,
            state_checksum=state_checksum,
        )
        return _artifact_apply_payload(intent, artifact_path, key=key)


def test_paper_portfolio_routes_require_login(tmp_path, monkeypatch):
    harness = _RouteHarness(tmp_path, monkeypatch)
    endpoints = [
        ("GET", "/api/tw-stock/paper-portfolio/state?paper_account_id=tw_sim_1", None),
        ("GET", "/api/tw-stock/paper-portfolio/apply-runs", None),
        ("GET", "/api/tw-stock/paper-portfolio/latest-decision", None),
        ("POST", "/api/tw-stock/paper-portfolio/apply-decision", {}),
        ("POST", "/api/tw-stock/paper-portfolio/reset", {}),
    ]
    for method, url, body in endpoints:
        resp = harness.client.open(url, method=method, json=body)
        assert resp.status_code == 401
        assert resp.get_json()["code"] == 401


def test_paper_portfolio_apply_route_success_and_error_mapping(tmp_path, monkeypatch):
    harness = _RouteHarness(tmp_path, monkeypatch)
    payload = harness.artifact_payload(run_id="ok", decision_id="decision-ok", key="idem-ok")
    payload["paper_only"] = False
    resp = harness.client.post("/api/tw-stock/paper-portfolio/apply-decision", json=payload, headers=harness.headers)
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["code"] == 1
    assert data["data"]["simulation_only"] is True
    assert data["data"]["trading"]["real_orders_enabled"] is False
    assert data["data"]["trading"]["connects_to_broker"] is False
    assert data["data"]["paper_only"] is True
    assert harness.db.apply_runs and '"paper_only": true' in harness.db.apply_runs[0]["request_json"]

    conflict = harness.artifact_payload(run_id="conflict", decision_id="decision-conflict", key="idem-ok", state_checksum="sha256:conflict")
    resp = harness.client.post("/api/tw-stock/paper-portfolio/apply-decision", json=conflict, headers=harness.headers)
    assert resp.status_code == 400
    assert resp.get_json()["data"]["status"] == "idempotency_conflict"



def test_paper_portfolio_apply_route_pending_execution_price_rejected_before_writes(tmp_path, monkeypatch):
    harness = _RouteHarness(tmp_path, monkeypatch, status_loader=price_pending_status)
    payload = harness.artifact_payload(run_id="pending", decision_id="decision-pending", key="idem-pending")
    resp = harness.client.post("/api/tw-stock/paper-portfolio/apply-decision", json=payload, headers=harness.headers)
    data = resp.get_json()["data"]
    assert resp.status_code == 400
    assert data["status"] == "execution_price_unavailable"
    assert data["paper_apply_allowed"] is False
    assert harness.db.apply_runs == []
    assert harness.db.orders == []
    assert harness.db.trades == []
    assert harness.db.audit == []
    assert not any(sql.startswith("CREATE TABLE") or sql.startswith("ALTER TABLE") for sql in harness.db.sql)


def test_paper_portfolio_apply_route_rejects_invalid_stale_not_found_and_artifact_abuse(tmp_path, monkeypatch):
    harness = _RouteHarness(tmp_path, monkeypatch)

    traversal = {
        "paper_account_id": "tw_sim_1",
        "paper_account_epoch": 1,
        "decision_id": "escape",
        "idempotency_key": "escape-key",
        "input_checksum": "sha256:x",
        "paper_order_intent_artifact_path": "../paper_order_intent.json",
        "confirmed_by_user": True,
        "confirm_text": "确认应用到模拟账户",
    }
    resp = harness.client.post("/api/tw-stock/paper-portfolio/apply-decision", json=traversal, headers=harness.headers)
    assert resp.status_code == 400
    assert resp.get_json()["data"]["status"] == "invalid_artifact"

    mismatch = harness.artifact_payload(run_id="mismatch", decision_id="decision-mismatch", key="mismatch-key")
    mismatch["input_checksum"] = "sha256:wrong"
    resp = harness.client.post("/api/tw-stock/paper-portfolio/apply-decision", json=mismatch, headers=harness.headers)
    assert resp.status_code == 400
    assert resp.get_json()["data"]["status"] == "invalid_artifact"

    stale = harness.artifact_payload(run_id="stale", decision_id="decision-stale", key="stale-key", epoch=0, state_checksum="sha256:stale")
    resp = harness.client.post("/api/tw-stock/paper-portfolio/apply-decision", json=stale, headers=harness.headers)
    assert resp.status_code == 400
    assert resp.get_json()["data"]["status"] == "stale_epoch"

    not_found = harness.artifact_payload(run_id="other", decision_id="decision-other", key="other-key", account_id="tw_sim_other", state_checksum="sha256:other")
    resp = harness.client.post("/api/tw-stock/paper-portfolio/apply-decision", json=not_found, headers=harness.headers)
    assert resp.status_code == 404
    assert resp.get_json()["data"]["status"] == "not_found"


def test_paper_portfolio_apply_route_rejects_same_day_different_decision(tmp_path, monkeypatch):
    harness = _RouteHarness(tmp_path, monkeypatch)
    first = harness.artifact_payload(run_id="same-day-a", decision_id="decision-a", key="same-day-a", actions=[])
    second = harness.artifact_payload(run_id="same-day-b", decision_id="decision-b", key="same-day-b", state_checksum="sha256:same-day-b")
    resp = harness.client.post("/api/tw-stock/paper-portfolio/apply-decision", json=first, headers=harness.headers)
    assert resp.status_code == 200
    assert resp.get_json()["data"]["status"] == "no_actions"
    resp = harness.client.post("/api/tw-stock/paper-portfolio/apply-decision", json=second, headers=harness.headers)
    assert resp.status_code == 400
    assert resp.get_json()["data"]["status"] == "same_day_apply_rejected"


def test_paper_portfolio_state_and_apply_runs_route_success(tmp_path, monkeypatch):
    harness = _RouteHarness(tmp_path, monkeypatch)
    resp = harness.client.get("/api/tw-stock/paper-portfolio/state", query_string={"paper_account_id": "tw_sim_1"}, headers=harness.headers)
    assert resp.status_code == 200
    assert resp.get_json()["data"]["simulation_only"] is True
    resp = harness.client.get("/api/tw-stock/paper-portfolio/apply-runs", headers=harness.headers)
    assert resp.status_code == 200
    assert resp.get_json()["data"]["simulation_only"] is True


def test_paper_portfolio_latest_decision_route_is_readonly_and_user_scoped(tmp_path, monkeypatch):
    harness = _RouteHarness(tmp_path, monkeypatch)
    payload = harness.artifact_payload(run_id="latest-route", decision_id="decision-latest-route", key="latest-route-key")
    resp = harness.client.get("/api/tw-stock/paper-portfolio/latest-decision", headers=harness.headers)
    data = resp.get_json()["data"]
    assert resp.status_code == 200
    assert data["ok"] is True
    assert data["decision_id"] == payload["decision_id"]
    assert data["model_track_id"] == "model_a_only"
    assert data["paper_order_intent_artifact_path"] == payload["paper_order_intent_artifact_path"]
    assert data["simulation_only"] is True
    assert data["trading"]["real_orders_enabled"] is False
    assert not harness.db.apply_runs
    assert not harness.db.orders
    assert not harness.db.trades

    blocked = harness.client.get(
        "/api/tw-stock/paper-portfolio/latest-decision",
        query_string={"model_track_id": "model_a_plus_b_b19r2r"},
        headers=harness.headers,
    )
    assert blocked.status_code == 400
    assert blocked.get_json()["data"]["status"] == "model_track_not_allowed"
    assert not harness.db.apply_runs
    assert not harness.db.orders
    assert not harness.db.trades
