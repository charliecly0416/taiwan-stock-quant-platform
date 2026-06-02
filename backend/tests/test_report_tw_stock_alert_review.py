"""Tests for read-only TWStock alert review reporting."""
from __future__ import annotations

import json

from scripts import report_tw_stock_alert_review as review


def _rows():
    return [
        {
            "id": 2,
            "user_id": 1,
            "monitor_name": "default",
            "symbol": "0050",
            "alert_type": "quality_warning",
            "severity": "warning",
            "message": "0050 data stale",
            "snapshot": json.dumps({"alert_context": {"category": "data_quality", "reason": "new_quality_warning", "human_action": "review data"}}),
            "is_read": False,
            "decision_status": "pending",
            "user_note": "",
            "created_at": "2026-05-25T10:00:00Z",
        },
        {
            "id": 1,
            "user_id": 1,
            "monitor_name": "default",
            "symbol": "2330",
            "alert_type": "score_change",
            "severity": "info",
            "message": "2330 score changed",
            "snapshot": "{}",
            "is_read": True,
            "decision_status": "watch",
            "user_note": "manual note",
            "created_at": "2026-05-25T09:00:00Z",
        },
    ]


def test_normalize_alert_row_uses_context_and_fallback_category():
    first = review.normalize_alert_row(_rows()[0])
    second = review.normalize_alert_row(_rows()[1])

    assert first["category"] == "data_quality"
    assert first["reason"] == "new_quality_warning"
    assert first["human_action"] == "review data"
    assert first["orders_enabled"] is False
    assert second["category"] == "trend_change"


def test_build_alert_review_report_summarizes_manual_review_state():
    alerts = [review.normalize_alert_row(row) for row in _rows()]

    report = review.build_alert_review_report(user_id=1, name="default", limit=100, alerts=alerts)

    assert report["summary"]["alert_count"] == 2
    assert report["summary"]["unread_count"] == 1
    assert report["summary"]["needs_review_count"] == 1
    assert report["summary"]["by_category"] == {"data_quality": 1, "trend_change": 1}
    assert report["summary"]["by_decision_status"] == {"pending": 1, "watch": 1}
    assert report["alerts_created"] == 0
    assert report["notifications_sent"] == 0
    assert report["orders_enabled"] is False
    assert report["writes_production_data"] is False
    assert report["connects_to_broker"] is False


def test_render_markdown_includes_summary_and_table():
    alerts = [review.normalize_alert_row(row) for row in _rows()]
    report = review.build_alert_review_report(alerts=alerts)

    markdown = review.render_markdown(report)

    assert "# TWStock Alert Review Report" in markdown
    assert "needs_review_count: `1`" in markdown
    assert "| 2 | 0050 | data_quality | quality_warning | warning | pending | False | 0050 data stale |" in markdown


def test_load_alerts_reads_rows_and_normalizes():
    class Cursor:
        def execute(self, sql, params):
            self.params = params

        def fetchall(self):
            return _rows()

        def close(self):
            pass

    class Db:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return Cursor()

    alerts = review.load_alerts(user_id=1, name="default", limit=2, db_factory=lambda: Db())

    assert [item["symbol"] for item in alerts] == ["0050", "2330"]
    assert alerts[0]["category"] == "data_quality"


def test_main_prints_json_and_writes_markdown(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(review, "load_alerts", lambda **kwargs: [review.normalize_alert_row(row) for row in _rows()])
    md_path = tmp_path / "alerts.md"

    rc = review.main(["--user-id", "1", "--name", "default", "--limit", "2", "--output-md", str(md_path)])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["by_category"] == {"data_quality": 1, "trend_change": 1}
    assert payload["orders_enabled"] is False
    assert "TWStock Alert Review Report" in md_path.read_text(encoding="utf-8")
