from __future__ import annotations

import json
from pathlib import Path

from scripts import audit_tw_daily_auto_real_scheduled_jobs as audit


def _write_job(root: Path, name: str, *, scope: str, mtime: int) -> None:
    job_dir = root / name
    job_dir.mkdir(parents=True)
    (job_dir / "finmind_stdout.txt").write_text(
        json.dumps(
            {
                "archive": {"count": 1, "date_max": "2026-09-22", "symbols": ["2330"]},
                "institutional_trades": {"count": 0, "date_max": None, "symbols": []},
                "margin_trading": {"count": 0, "date_max": None, "symbols": []},
                "corporate_actions": {"count": 0, "date_max": None, "symbols": []},
                "monthly_revenue": {"count": 0, "date_max": None, "symbols": []},
                "valuation": {"count": 0, "date_max": None, "symbols": []},
                "segment_status": {"daily_price": {"ok": True}},
            }
        ),
        encoding="utf-8",
    )
    (job_dir / "job.json").write_text(
        json.dumps(
            {
                "job_id": name,
                "status": "fresh_data_wait",
                "asof": "2026-09-23" if scope == "daily" else "2026-09-22",
                "finmind_scope": scope,
                "finmind_update_triggered": True,
                "provider_publish_triggered": False,
                "latest_signal_updated": False,
            }
        ),
        encoding="utf-8",
    )
    # The collector sorts by file mtime, so make the intended order explicit.
    path = job_dir / "job.json"
    path.touch()
    import os

    os.utime(path, (mtime, mtime))


def test_collect_jobs_preserves_scope_for_full_run_selection(tmp_path: Path, monkeypatch) -> None:
    _write_job(tmp_path, "daily_tw_stock_auto_update_20260923_run", scope="daily", mtime=200)
    _write_job(tmp_path, "daily_tw_stock_auto_update_20260922_run", scope="full", mtime=100)
    monkeypatch.setattr(audit, "OPS_ROOT", tmp_path)

    rows = audit.collect_jobs(10)

    assert rows[0]["finmind_scope"] == "daily"
    assert rows[1]["finmind_scope"] == "full"
    assert rows[1]["full_orthogonal_refresh_required"] is False

