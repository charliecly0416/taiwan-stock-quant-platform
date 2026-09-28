#!/usr/bin/env python3
"""Readonly integration gate for the clean Taiwan-stock product."""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app import create_app  # noqa: E402
from clean_product.config import load_config, env_config  # noqa: E402
from clean_product.orchestrator import run_daily  # noqa: E402
from clean_product.replay import replay  # noqa: E402
from clean_product.data import DataCatalog  # noqa: E402


def validate_response(url: str, http: int, payload: dict) -> list[str]:
    """Smoke checks plus numeric invariants; this is not release acceptance."""
    errors = []
    endpoint = url.split("?", 1)[0]
    if http != 200:
        errors.append(f"HTTP {http}")
    if endpoint.startswith("/api/tw-stock/") and payload.get("readonly") is not True:
        errors.append("readonly marker missing")
    expected = {"/api/health": ("healthy",), "/api/ready": ("ready",),
                "/api/tw-stock/config": (None,),
                "/api/tw-stock/operations/latest": ("NO_RUN", "READY")}
    if payload.get("status") not in expected.get(endpoint, ("READY",)):
        errors.append(f"unexpected status {payload.get('status')}: {payload.get('reason', payload.get('message', ''))}")

    def numeric(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

    rows = payload.get("rows") or []
    if endpoint in ("/api/tw-stock/rankings", "/api/tw-stock/cross-analysis"):
        if not rows or [row.get("rank") for row in rows] != list(range(1, len(rows) + 1)):
            errors.append("ranking is empty or non-contiguous")
        if len({row.get("instrument") for row in rows}) != len(rows):
            errors.append("duplicate instruments")
    if endpoint == "/api/tw-stock/cross-analysis":
        if not rows or not all(numeric(row.get(key)) for row in rows for key in ("close", "ma20", "rsi14")):
            errors.append("missing/non-finite technical context")
    if endpoint.startswith("/api/tw-stock/market/"):
        if not rows or not all(numeric(rows[-1].get(key)) for key in ("close", "ma20", "rsi14")):
            errors.append("missing market values")
    if endpoint == "/api/tw-stock/replay" and payload.get("status") == "READY":
        nav = payload.get("nav") or []
        fields = ("initial_cash", "final_nav", "cumulative_return", "max_drawdown", "total_fees", "turnover")
        if not nav or not all(numeric(payload.get(key)) for key in fields):
            errors.append("missing/non-finite replay metrics")
        elif not all(all(numeric(row.get(key)) for key in ("nav", "cash", "market_value")) for row in nav):
            errors.append("non-finite NAV observations")
        else:
            initial = payload["initial_cash"]
            if initial <= 0 or not math.isclose(nav[0]["nav"], initial):
                errors.append("NAV excludes initial capital")
            if not all(math.isclose(row["nav"], row["cash"] + row["market_value"]) for row in nav):
                errors.append("NAV does not reconcile to cash plus market value")
            if initial > 0 and not math.isclose(payload["cumulative_return"], nav[-1]["nav"] / initial - 1, abs_tol=1e-10):
                errors.append("return does not reconcile to NAV")
            peak = initial
            drawdowns = []
            for row in nav:
                peak = max(peak, row["nav"])
                if peak > 0:
                    drawdowns.append(row["nav"] / peak - 1)
            if drawdowns and not math.isclose(payload["max_drawdown"], min(drawdowns), abs_tol=1e-10):
                errors.append("drawdown excludes a capital loss")
            if not math.isclose(payload["final_nav"], nav[-1]["nav"]):
                errors.append("final NAV differs from NAV series")
    return [f"{url}: {error}" for error in errors]


def main() -> int:
    config = load_config()
    failures: list[str] = []
    if config.get("product", {}).get("readonly") is not True:
        failures.append("product.readonly must be true")
    if config.get("models", {}).get("model_a", {}).get("production_allowed") is not True:
        failures.append("Model A must be the allowed baseline")
    if config.get("models", {}).get("model_a_plus_b", {}).get("production_allowed") is not False:
        failures.append("Model A+B must remain shadow-only")
    if config.get("product", {}).get("default_model") != "model_a":
        failures.append("Model A must remain the frontend default")
    if config.get("strategy") != "top50_exit_one_worst_sell" or config.get("execution") != "next_open":
        failures.append("baseline strategy/execution contract changed")

    with tempfile.TemporaryDirectory(prefix="clean-smoke-") as directory:
        isolated = {**config, "data_root": str(Path(directory) / "data"),
                    "artifact_root": str(Path(directory) / "artifacts")}
        config_path = Path(directory) / "product.yaml"
        resolved = env_config(isolated)
        if any(resolved[key].resolve() != Path(isolated[key]).resolve() for key in ('artifact_root', 'data_root')):
            raise ValueError('runtime path overrides conflict with isolated dry-run')
        config_path.write_text(yaml.safe_dump(isolated), encoding="utf-8")
        daily = run_daily("2026-09-25", config_path=config_path, dry_run=True)
        if daily.get("status") != "READY":
            failures.append("dry-run daily baseline is not READY")
        fixture = DataCatalog(isolated).query("prices", "2026-09-24", "2026-09-25", allow_fixture=True)
        replay_result = replay(isolated, {"prices": fixture}, "model_a_plus_b", "2026-09-24", "2026-09-25", fixture=True)
        if replay_result.get("status") != "READY":
            failures.append("fixture replay is not READY")

    app = create_app({'AGENT_REMOTE_DISABLED': True}); app.testing = True
    checks = [
        "/api/health", "/api/ready", "/api/tw-stock/config", "/api/tw-stock/overview",
        "/api/tw-stock/data-status", "/api/tw-stock/operations/latest",
        "/api/tw-stock/rankings?model=model_a&date=2026-09-24&limit=5",
        "/api/tw-stock/strategy?model=model_a&date=2026-09-24",
        "/api/tw-stock/cross-analysis?model=model_a&date=2026-09-24&limit=3",
        "/api/tw-stock/paper?model=model_a&date=2026-09-24",
        "/api/tw-stock/market/2330?start=2026-09-01&end=2026-09-24",
        "/api/tw-stock/agent/context?model=model_a&date=2026-09-24",
        "/api/tw-stock/agent/explain/2330?model=model_a&date=2026-09-24",
        "/api/tw-stock/replay?model=model_a&start=2025-06-23&end=2025-06-30",
    ]
    responses = {}
    with app.test_client() as client:
        for path in checks:
            response = client.get(path)
            payload = response.get_json() or {}
            responses[path] = {"http": response.status_code, "status": payload.get("status")}
            failures.extend(validate_response(path, response.status_code, payload))
        # The comparison workbench may be unavailable while the admitted
        # Model A lane is READY.  B19R2R is explicitly shadow-only and its
        # missing PIT feature date must remain non-blocking for the baseline.
        shadow_compare = "/api/tw-stock/compare?left=model_a&right=model_a_plus_b&date=2026-05-07"
        response = client.get(shadow_compare)
        payload = response.get_json() or {}
        responses[shadow_compare] = {"http": response.status_code,
                                     "status": payload.get("status"),
                                     "reason": payload.get("reason"),
                                     "mainline_blocking": False}
        if response.status_code != 200 or payload.get("status") != "READY" or payload.get("overlap_top50") != 49:
            failures.append(f"{shadow_compare}: verified historical comparison must remain available")
        shadow_path = "/api/tw-stock/paper?model=model_a_plus_b&date=2026-09-24"
        response = client.get(shadow_path)
        payload = response.get_json() or {}
        responses[shadow_path] = {"http": response.status_code, "status": payload.get("status"),
                                  "reason": payload.get("reason"), "expected_status": "BLOCKED"}
        if (response.status_code != 200 or payload.get("status") != "BLOCKED"
                or payload.get("reason") != "MODEL_NOT_ADMITTED_FOR_PAPER_ACCOUNT"
                or "nav" in payload or "positions" in payload):
            failures.append("shadow model reached the paper-account surface")
        chat_path = '/api/tw-stock/agent/simple-chat'
        response = client.post(chat_path, json={'question': '排名第一是谁？', 'date': '2026-09-24'})
        payload = response.get_json() or {}
        responses[chat_path] = {'http': response.status_code, 'status': payload.get('status'),
                                'reason': payload.get('reason'), 'mode': payload.get('mode')}
        failures.extend(validate_response(chat_path, response.status_code, payload))

    report = {"status": "READY" if not failures else "BLOCKED", "scope": "smoke_and_numeric_invariants",
              "release_acceptance": "NOT_EVALUATED", "failures": failures, "responses": responses,
              "readonly": True, "simulation_only": True}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
