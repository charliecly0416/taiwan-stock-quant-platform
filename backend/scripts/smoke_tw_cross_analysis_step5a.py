"""Smoke test Phase 5A TWStock qlib cross-analysis history/review on PostgreSQL."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("SECRET_KEY", "step5a-smoke-secret")
os.environ.setdefault("SKIP_AUTO_MIGRATE", "true")
os.environ.setdefault("CACHE_ENABLED", "false")
os.environ.setdefault("ENABLE_PENDING_ORDER_WORKER", "false")
os.environ.setdefault("ENABLE_PORTFOLIO_MONITOR", "false")
os.environ.setdefault("ENABLE_TW_STOCK_MONITOR_WORKER", "false")
os.environ.setdefault("DISABLE_RESTORE_RUNNING_STRATEGIES", "true")
os.environ.setdefault("POSITION_SYNC_ENABLED", "false")
os.environ.setdefault("USDT_PAY_ENABLED", "false")

from app import create_app  # noqa: E402
from app.utils.db import get_db_connection, is_postgres_available  # noqa: E402
from app.services.tw_stock_qlib_option_c import research_only_trading_flags  # noqa: E402


ADMIN_HEADERS = {"Authorization": "Bearer step5a-admin", "Content-Type": "application/json"}
USER_HEADERS = {"Authorization": "Bearer step5a-user", "Content-Type": "application/json"}
SMOKE_USER_ID = 909005


def patch_auth() -> None:
    import app.utils.auth as auth_utils

    def fake_verify_token(raw: str):
        if raw == "step5a-admin":
            return {"sub": "step5a-admin", "user_id": 1, "role": "admin"}
        if raw == "step5a-user":
            return {"sub": "step5a-user", "user_id": SMOKE_USER_ID, "role": "user"}
        return None

    auth_utils.verify_token = fake_verify_token


def cleanup_review(*, asof: str, run_id: str, symbol: str) -> int:
    with get_db_connection() as db:
        cur = db.cursor()
        cur.execute(
            """
            DELETE FROM qd_tw_cross_analysis_reviews
            WHERE user_id = ? AND asof = ? AND run_id = ? AND symbol = ?
            """,
            (SMOKE_USER_ID, asof, run_id, symbol),
        )
        deleted = getattr(cur, "rowcount", None)
        cur.close()
        db.commit()
    return int(deleted or 0)


def main() -> int:
    if not os.getenv("DATABASE_URL"):
        print(json.dumps({"ok": False, "status": "missing_database_url"}, ensure_ascii=False))
        return 2
    if not is_postgres_available():
        print(json.dumps({"ok": False, "status": "postgres_unavailable"}, ensure_ascii=False))
        return 2

    patch_auth()
    app = create_app("testing")
    app.config["TESTING"] = True
    client = app.test_client()

    anonymous = client.post("/api/tw-stock/cross-analysis/history/import-latest", json={})
    user_denied = client.post(
        "/api/tw-stock/cross-analysis/history/import-latest",
        headers=USER_HEADERS,
        json={"confirm_import_qlib_signal_history": True},
    )
    imported_resp = client.post(
        "/api/tw-stock/cross-analysis/history/import-latest",
        headers=ADMIN_HEADERS,
        json={"confirm_import_qlib_signal_history": True},
    )
    imported = imported_resp.get_json() or {}
    imported_data = imported.get("data") or {}
    if imported_resp.status_code != 200 or not imported_data.get("ok"):
        print(json.dumps({"ok": False, "status": "import_failed", "http_status": imported_resp.status_code, "payload": imported}, ensure_ascii=False))
        return 3

    run_id = str(imported_data.get("run_id") or "")
    asof = str(imported_data.get("asof") or "")
    signals_resp = client.get(f"/api/tw-stock/cross-analysis/history/signals?run_id={run_id}&limit=200")
    alerts_resp = client.get(f"/api/tw-stock/cross-analysis/history/alerts?run_id={run_id}&limit=200")
    runs_resp = client.get("/api/tw-stock/cross-analysis/history/runs?limit=5")
    signals = (signals_resp.get_json() or {}).get("data") or {}
    alerts = (alerts_resp.get_json() or {}).get("data") or {}
    runs = (runs_resp.get_json() or {}).get("data") or {}
    first_signal = (signals.get("items") or [{}])[0]
    symbol = str(first_signal.get("symbol") or "2330")

    review_payload = {
        "asof": asof,
        "run_id": run_id,
        "symbol": symbol,
        "cross_category": "step5a_smoke",
        "decision_status": "reviewed",
        "user_note": "Step 5A PostgreSQL smoke; safe to clean.",
        "target_position": 999,
    }
    review_put_resp = client.put("/api/tw-stock/cross-analysis/reviews", headers=USER_HEADERS, json=review_payload)
    review_get_resp = client.get(
        f"/api/tw-stock/cross-analysis/reviews?asof={asof}&run_id={run_id}&symbol={symbol}&limit=5",
        headers=USER_HEADERS,
    )
    review_put = review_put_resp.get_json() or {}
    review_get = review_get_resp.get_json() or {}
    cleaned_reviews = cleanup_review(asof=asof, run_id=run_id, symbol=symbol)

    out = {
        "ok": True,
        "database_url": os.getenv("DATABASE_URL"),
        "anonymous_import_status": anonymous.status_code,
        "user_import_status": user_denied.status_code,
        "admin_import_status": imported_resp.status_code,
        "run_id": run_id,
        "asof": asof,
        "signals_count": signals.get("count"),
        "alerts_count": alerts.get("count"),
        "runs_count": runs.get("count"),
        "review_put_status": review_put_resp.status_code,
        "review_get_status": review_get_resp.status_code,
        "review_get_count": (review_get.get("data") or {}).get("count"),
        "review_item_keys": sorted(((review_put.get("data") or {}).get("item") or {}).keys()),
        "cleaned_reviews": cleaned_reviews,
        "trading": research_only_trading_flags(),
    }
    print(json.dumps(out, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
