from __future__ import annotations

from scripts.check_tw_project import run_checks


def test_project_health_checks_are_read_only_and_pass() -> None:
    result = run_checks()

    assert result["status"] == "PASS"
    checks = {check["name"]: check for check in result["checks"]}
    assert checks["config_syntax"]["ok"] is True
    assert checks["registered_task_requests"]["ok"] is True
    assert checks["workflow_specs"]["ok"] is True
    assert checks["script_lifecycle"]["ok"] is True
    assert checks["script_lifecycle"]["file_count"] > 0
