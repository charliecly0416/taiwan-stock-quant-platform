"""Tests for TWStock research-stack verification runner."""
from __future__ import annotations

import json
import sys

from scripts import verify_tw_stock_research_stack as verify


class _Proc:
    def __init__(self, returncode=0, stdout="ok", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_run_verification_defaults_to_pytest_only(monkeypatch):
    calls = []

    def fake_run(cmd, text, capture_output, env=None):
        calls.append({"cmd": cmd, "env": env})
        return _Proc(stdout="45 passed")

    monkeypatch.setattr(verify.subprocess, "run", fake_run)

    report = verify.run_verification()

    assert report["ok"] is True
    assert report["with_page_smoke"] is False
    assert report["orders_enabled"] is False
    assert report["writes_production_data"] is False
    assert report["connects_to_broker"] is False
    assert len(calls) == 1
    assert calls[0]["cmd"][:3] == [sys.executable, "-m", "pytest"]
    assert "backend/tests/test_tw_stock_monitor_safety_audit.py" in calls[0]["cmd"]
    assert "backend/tests/test_tw_stock_backtest.py" in calls[0]["cmd"]
    assert "backend/tests/test_tw_stock_backtest_plan_docs.py" in calls[0]["cmd"]


def test_run_verification_with_page_smoke(monkeypatch):
    calls = []

    def fake_run(cmd, text, capture_output, env=None):
        calls.append({"cmd": cmd, "env": env})
        return _Proc(stdout="ok")

    monkeypatch.setattr(verify.subprocess, "run", fake_run)

    report = verify.run_verification(with_page_smoke=True, screenshot="/tmp/shot.png", tests=["one_test.py"])

    assert report["ok"] is True
    assert report["test_count"] == 1
    assert [step["name"] for step in report["steps"]] == ["pytest", "page_smoke"]
    assert calls[0]["cmd"] == [sys.executable, "-m", "pytest", "one_test.py", "-q"]
    assert calls[1]["cmd"] == [sys.executable, "backend/scripts/check_tw_stock_monitor_page_e2e.py", "--screenshot", "/tmp/shot.png"]
    assert calls[1]["env"]["PYTHONPATH"].startswith("backend")


def test_main_returns_nonzero_on_failure(monkeypatch, capsys):
    monkeypatch.setattr(verify, "run_verification", lambda **kwargs: {"ok": False, "orders_enabled": False})

    rc = verify.main(["--test", "bad_test.py"])

    assert rc == 1
    assert json.loads(capsys.readouterr().out)["orders_enabled"] is False
