from __future__ import annotations

import importlib.util
import io
from pathlib import Path
from urllib.error import HTTPError


ROOT = Path(__file__).resolve().parents[2]


def load_module():
    path = ROOT / "scripts/verify_tw_stock_readonly_deployment.py"
    spec = importlib.util.spec_from_file_location("tw_stock_deployment_acceptance_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_status_probe_accepts_html_405_without_json_decode(monkeypatch):
    module = load_module()

    def denied(*args, **kwargs):
        raise HTTPError("http://test/api/ready", 405, "Method Not Allowed", {}, io.BytesIO(b"<html>405</html>"))

    monkeypatch.setattr(module, "urlopen", denied)
    assert module.request_status("http://test", "/api/ready", method="POST") == 405


def test_verify_requires_every_write_guard_to_return_405(monkeypatch):
    module = load_module()
    payloads = {
        "liveness": {"status": "healthy"},
        "readiness": {
            "ready": True,
            "status": "ready",
            "signal_asof": "2026-09-18",
            "checks": {
                "readonly_runtime_boundary": {
                    "ready": True,
                    "code": "ok",
                    "mode": "readonly_research",
                },
            },
        },
        "context": {"readonly_only": True, "production_trade_enabled": False, "context": {"signal_asof": "2026-09-18", "default_model_id": "e4_frozen_qlib_2018_2022"}},
        "signal_health": {"status": "accepted", "latest": {"asof": "2026-09-18", "accepted_validated": True}, "freshness": {"stale": False}},
        "daily_status": {"latest_status": "accepted", "latest_asof": "2026-09-18", "pending_asof": None},
        "readonly_status": {"all_readonly_guards": True},
        "comparison": {"readonly_only": True, "no_apply": True, "runtime_effect": "none"},
    }
    by_path = {path: payloads[name] for name, path in module.ENDPOINTS.items()}
    monkeypatch.setattr(module, "request_json", lambda base, path, timeout: (200, by_path[path]))
    monkeypatch.setattr(module, "request_status", lambda *args, **kwargs: 405)
    result = module.verify("http://test", "2026-09-18", 1)
    assert result["ok"] is True
    assert result["checks"]["write_methods_rejected"] is True
    assert len(result["write_guard_statuses"]) == 12
