#!/usr/bin/env python3
"""Verify a deployed Taiwan-stock research service through GET-only APIs."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ENDPOINTS = {
    "liveness": "/api/health",
    "readiness": "/api/ready",
    "context": "/api/tw-stock/current-strategy-context",
    "signal_health": "/api/tw-stock/quant/signals/health",
    "daily_status": "/api/tw-stock/quant/ops/daily-auto-update/status",
    "readonly_status": "/api/tw-stock/quant/ops/readonly-status",
    "comparison": "/api/tw-stock/readonly/model-strategy-comparison",
}
WRITE_METHODS = ("POST", "PUT", "PATCH", "DELETE")
WRITE_GUARD_PATHS = (ENDPOINTS["readiness"], ENDPOINTS["context"], ENDPOINTS["comparison"])


def request_json(base_url: str, path: str, *, method: str = "GET", timeout: float = 15.0) -> tuple[int, dict[str, Any]]:
    request = Request(base_url.rstrip("/") + path, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            status = response.status
            body = response.read()
    except HTTPError as exc:
        status = exc.code
        body = exc.read()
    except (OSError, URLError) as exc:
        raise RuntimeError(f"request_failed:{path}:{type(exc).__name__}") from exc
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        if status >= 400:
            return status, {}
        raise RuntimeError(f"invalid_json:{path}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"invalid_object:{path}")
    return status, payload


def request_status(base_url: str, path: str, *, method: str, timeout: float = 15.0) -> int:
    """Return an HTTP status without assuming error responses use JSON."""
    request = Request(base_url.rstrip("/") + path, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status
    except HTTPError as exc:
        return exc.code
    except (OSError, URLError) as exc:
        raise RuntimeError(f"request_failed:{path}:{type(exc).__name__}") from exc


def data(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("data", payload)
    if not isinstance(value, dict):
        raise RuntimeError("invalid_api_envelope")
    return value


def verify(base_url: str, expected_asof: str | None, timeout: float) -> dict[str, Any]:
    responses: dict[str, dict[str, Any]] = {}
    statuses: dict[str, int] = {}
    for name, path in ENDPOINTS.items():
        status, payload = request_json(base_url, path, timeout=timeout)
        if status != 200:
            raise RuntimeError(f"unexpected_http_status:{name}:{status}")
        statuses[name] = status
        responses[name] = data(payload)

    readiness = responses["readiness"]
    context = responses["context"]
    signal_health = responses["signal_health"]
    daily_status = responses["daily_status"]
    readonly_status = responses["readonly_status"]
    comparison = responses["comparison"]
    context_body = context.get("context") if isinstance(context.get("context"), dict) else {}
    latest = signal_health.get("latest") if isinstance(signal_health.get("latest"), dict) else {}
    freshness = signal_health.get("freshness") if isinstance(signal_health.get("freshness"), dict) else {}
    readiness_checks = readiness.get("checks") if isinstance(readiness.get("checks"), dict) else {}
    runtime_boundary = (
        readiness_checks.get("readonly_runtime_boundary")
        if isinstance(readiness_checks.get("readonly_runtime_boundary"), dict)
        else {}
    )
    asofs = {
        "readiness": readiness.get("signal_asof"),
        "context": context_body.get("signal_asof"),
        "signal": latest.get("asof"),
        "daily": daily_status.get("latest_asof"),
    }
    observed_asof = expected_asof or str(asofs["readiness"] or "")
    checks = {
        "liveness": responses["liveness"].get("status") == "healthy",
        "readiness": readiness.get("ready") is True and readiness.get("status") == "ready",
        "readonly_runtime_boundary": (
            runtime_boundary.get("ready") is True
            and runtime_boundary.get("code") == "ok"
            and runtime_boundary.get("mode") == "readonly_research"
        ),
        "same_asof": bool(observed_asof) and all(value == observed_asof for value in asofs.values()),
        "model_a_active": context_body.get("default_model_id") == "e4_frozen_qlib_2018_2022",
        "context_readonly": context.get("readonly_only") is True and context.get("production_trade_enabled") is False,
        "signal_accepted": signal_health.get("status") == "accepted" and latest.get("accepted_validated") is True,
        "signal_fresh": freshness.get("stale") is False,
        "mainline_clear": daily_status.get("latest_status") == "accepted" and not daily_status.get("pending_asof"),
        "ops_readonly": readonly_status.get("all_readonly_guards") is True,
        "comparison_readonly": comparison.get("readonly_only") is True and comparison.get("no_apply") is True and comparison.get("runtime_effect") == "none",
    }
    write_guards: dict[str, int] = {}
    for path in WRITE_GUARD_PATHS:
        for method in WRITE_METHODS:
            status = request_status(base_url, path, method=method, timeout=timeout)
            write_guards[f"{method} {path}"] = status
    checks["write_methods_rejected"] = all(status == 405 for status in write_guards.values())
    ok = all(checks.values())
    return {
        "schema_version": "tw_stock_readonly_deployment_acceptance.v1",
        "ok": ok,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "expected_asof": observed_asof,
        "asofs": asofs,
        "checks": checks,
        "http_statuses": statuses,
        "write_guard_statuses": write_guards,
        "b19r2r_shadow": daily_status.get("b19r2r_shadow"),
        "no_requests_with_write_methods_succeeded": checks["write_methods_rejected"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--expected-asof")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        result = verify(args.base_url, args.expected_asof, args.timeout)
    except RuntimeError as exc:
        result = {
            "schema_version": "tw_stock_readonly_deployment_acceptance.v1",
            "ok": False,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "base_url": args.base_url,
            "error": str(exc),
        }
    encoded = json.dumps(result, ensure_ascii=True, indent=2) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8")
    sys.stdout.write(encoded)
    return 0 if result.get("ok") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
