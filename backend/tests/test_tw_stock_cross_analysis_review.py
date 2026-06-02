"""Tests for TWStock qlib cross-analysis manual reviews."""
from __future__ import annotations

from app.services.tw_stock_cross_analysis_history import TWStockCrossAnalysisHistoryService
from app.services.tw_stock_qlib_option_c import research_only_trading_flags


class ReviewCursor:
    def __init__(self, db):
        self.db = db
        self.result = []
        self.row = None

    def execute(self, sql, params=None):
        params = tuple(params or ())
        compact = " ".join(str(sql).split())
        self.db.sql.append(compact)
        if compact.startswith("CREATE TABLE"):
            self.result = []
            self.row = None
        elif compact.startswith("INSERT INTO qd_tw_cross_analysis_reviews"):
            key = (params[0], params[1], params[2], params[3])
            allowed = {
                "id": self.db.ids.get(key, len(self.db.ids) + 1),
                "user_id": params[0],
                "asof": params[1],
                "symbol": params[2],
                "run_id": params[3],
                "cross_category": params[4],
                "decision_status": params[5],
                "user_note": params[6],
                "updated_at": "2026-06-02T00:00:00",
                "created_at": self.db.reviews.get(key, {}).get("created_at", "2026-06-02T00:00:00"),
            }
            self.db.ids[key] = allowed["id"]
            self.db.reviews[key] = allowed
            self.row = dict(allowed)
            self.result = [dict(allowed)]
        elif "FROM qd_tw_cross_analysis_reviews" in compact:
            rows = list(self.db.reviews.values())
            user_id = params[0]
            rows = [row for row in rows if row["user_id"] == user_id]
            if "asof = ?" in compact:
                rows = [row for row in rows if row["asof"] in params]
            if "run_id = ?" in compact:
                rows = [row for row in rows if row["run_id"] in params]
            if "symbol = ?" in compact:
                rows = [row for row in rows if row["symbol"] in params]
            self.result = [dict(row) for row in rows]
            self.row = self.result[0] if self.result else None
        else:
            self.result = []
            self.row = None

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.result

    def close(self):
        pass


class ReviewDb:
    def __init__(self):
        self.reviews = {}
        self.ids = {}
        self.sql = []
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return ReviewCursor(self)

    def commit(self):
        self.commits += 1


def _service(db):
    return TWStockCrossAnalysisHistoryService(db_factory=lambda: db)


def test_save_review_only_persists_review_status_and_note():
    db = ReviewDb()
    payload = _service(db).save_review(
        user_id=7,
        asof="2026-06-01",
        run_id="option_c_daily_signal_20260601_20260602T090715Z",
        symbol="TW2330",
        cross_category="focus_watch",
        decision_status="watching",
        user_note="人工复盘备注",
    )

    assert payload["ok"] is True
    item = payload["item"]
    assert item["user_id"] == 7
    assert item["symbol"] == "2330"
    assert item["decision_status"] == "watching"
    assert item["user_note"] == "人工复盘备注"
    assert item["trading"]["orders_enabled"] is False
    forbidden_keys = {"order", "orders", "position", "target_weight", "target_position", "broker", "exchange_account"}
    assert forbidden_keys.isdisjoint(item.keys())


def test_save_review_rejects_invalid_decision_status_and_missing_fields():
    db = ReviewDb()
    bad_status = _service(db).save_review(user_id=1, asof="2026-06-01", run_id="r1", symbol="2330", decision_status="buy_now")
    missing = _service(db).save_review(user_id=1, asof="", run_id="r1", symbol="2330", decision_status="pending")

    assert bad_status["ok"] is False
    assert bad_status["status"] == "invalid_decision_status"
    assert missing["ok"] is False
    assert missing["status"] == "missing_required_fields"
    assert db.reviews == {}


def test_reviews_are_scoped_to_user_id():
    db = ReviewDb()
    service = _service(db)
    service.save_review(user_id=1, asof="2026-06-01", run_id="r1", symbol="2330", decision_status="reviewed", user_note="u1")
    service.save_review(user_id=2, asof="2026-06-01", run_id="r1", symbol="2330", decision_status="ignored", user_note="u2")

    user1 = service.reviews(user_id=1, asof="2026-06-01", run_id="r1")
    user2 = service.reviews(user_id=2, asof="2026-06-01", run_id="r1")

    assert user1["count"] == 1
    assert user1["items"][0]["user_note"] == "u1"
    assert user2["items"][0]["user_note"] == "u2"
    assert user1["trading"]["orders_enabled"] is False


def test_review_api_requires_login_and_uses_current_user(client, monkeypatch):
    class FakeReviewService:
        def __init__(self):
            self.save_calls = []
            self.review_calls = []

        def reviews(self, **kwargs):
            self.review_calls.append(kwargs)
            return {"ok": True, "items": [{"user_id": kwargs["user_id"], "symbol": "2330"}], "count": 1, "trading": research_only_trading_flags()}

        def save_review(self, **kwargs):
            self.save_calls.append(kwargs)
            if kwargs.get("decision_status") == "bad":
                return {"ok": False, "status": "invalid_decision_status", "message": "bad", "trading": research_only_trading_flags()}
            return {"ok": True, "status": "saved", "item": {"user_id": kwargs["user_id"], "symbol": kwargs["symbol"], "decision_status": kwargs["decision_status"], "research_signal_not_order": True}, "trading": research_only_trading_flags()}

    from app import utils as app_utils
    from app.routes import tw_stock as tw_stock_route

    fake = FakeReviewService()
    monkeypatch.setattr(tw_stock_route, "cross_analysis_history_service", fake)

    anonymous_get = client.get("/api/tw-stock/cross-analysis/reviews")
    anonymous_put = client.put("/api/tw-stock/cross-analysis/reviews", json={})
    monkeypatch.setattr(app_utils.auth, "verify_token", lambda _raw: {"sub": "tester", "user_id": 9, "role": "user"})
    got = client.get("/api/tw-stock/cross-analysis/reviews?asof=2026-06-01&run_id=r1", headers={"Authorization": "Bearer user-token"})
    saved = client.put(
        "/api/tw-stock/cross-analysis/reviews",
        headers={"Authorization": "Bearer user-token"},
        json={"asof": "2026-06-01", "run_id": "r1", "symbol": "2330", "cross_category": "focus_watch", "decision_status": "watching", "user_note": "note", "target_position": 1},
    )
    invalid = client.put(
        "/api/tw-stock/cross-analysis/reviews",
        headers={"Authorization": "Bearer user-token"},
        json={"asof": "2026-06-01", "run_id": "r1", "symbol": "2330", "decision_status": "bad"},
    )

    assert anonymous_get.status_code == 401
    assert anonymous_put.status_code == 401
    assert got.status_code == 200
    assert saved.status_code == 200
    assert invalid.status_code == 400
    assert fake.review_calls[0]["user_id"] == 9
    assert fake.save_calls[0]["user_id"] == 9
    assert set(fake.save_calls[0].keys()) == {"user_id", "asof", "run_id", "symbol", "cross_category", "decision_status", "user_note"}
    assert saved.get_json()["data"]["trading"]["orders_enabled"] is False


def test_review_schema_and_service_do_not_write_trade_fields():
    import pathlib

    text = pathlib.Path("app/services/tw_stock_cross_analysis_history.py").read_text(encoding="utf-8").lower()
    review_section = text.split("create table if not exists qd_tw_cross_analysis_reviews", 1)[1].split("unique(user_id, asof, symbol, run_id)", 1)[0]
    forbidden = ["order", "position", "target_weight", "target_position", "broker", "exchange_account"]

    assert all(term not in review_section for term in forbidden)
