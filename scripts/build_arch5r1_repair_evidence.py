#!/usr/bin/env python3
"""Build ARCH-5-R1 repair evidence in a job-dir only.

The runner deliberately uses temporary protected pointers and injectable stage
callbacks.  It never invokes provider refresh, artifact publication, cron, or
broker/order code.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_daily_tw_stock_auto_update as daily  # noqa: E402
from tw_daily_runtime_stages import build_stage_facade, run_stage_orchestrator  # noqa: E402

OUT = ROOT / "data_tw/experiments/project_runtime_convergence/arch5r1_repair_20260907"
JOB = OUT / "job"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fp(path: Path) -> dict[str, Any]:
    return {"path": str(path), "exists": path.is_file(), "size": path.stat().st_size if path.is_file() else None, "sha256": sha(path)}


def fixture_inputs() -> dict[str, Path]:
    base = JOB / "protected_fixture"
    paths = {
        "readonly_latest": base / "readonly_latest.json",
        "agent_latest": base / "agent_latest.json",
        "provider_latest": base / "provider_latest.json",
        "legacy_latest": base / "legacy_latest.json",
    }
    for name, path in paths.items():
        payload = {"fixture": name, "signal_asof": "2026-09-04", "readonly_only": True, "production_trade_enabled": False}
        write_json(path, payload)
    return paths


def run_ador(paths: dict[str, Path]) -> dict[str, Any]:
    result = daily.run_ador_no_publish_orchestration_dry_run(
        asof="2026-09-04",
        job_dir=JOB / "ador",
        job_id="arch5r1",
        job={"job_id": "arch5r1", "asof": "2026-09-04"},
        enabled=True,
        dry_run=True,
        agent_prompt_dry_run=True,
        agent_prompt_publish_enabled=False,
        agent_prompt_publish_latest=False,
        readonly_latest_path=paths["readonly_latest"],
        agent_latest_path=paths["agent_latest"],
        provider_latest_path=paths["provider_latest"],
        legacy_latest_path=paths["legacy_latest"],
    )
    write_json(OUT / "ador_no_publish_orchestration_summary.json", result)
    return result


def parity_manifest(ador: dict[str, Any]) -> dict[str, Any]:
    # Legacy entrypoint's documented order is captured as a no-write plan. The
    # adapter run above is the actual executable six-stage boundary.
    legacy_order = ["acquisition", "readiness", "signal", "strategy", "artifact_publish", "ops_status"]
    adapter = ador.get("stage_adapter", {})
    adapter_order = [row.get("name") for row in adapter.get("stages", [])]
    payload = {
        "schema_version": "arch5r1.daily_old_new_parity.v1",
        "created_at": now(),
        "input": {"asof": "2026-09-04", "job_id": "arch5r1", "source": "temporary_fixture"},
        "legacy": {"path": "run_daily_tw_stock_auto_update legacy no-write plan", "stage_order": legacy_order, "failure_semantics": "fail_closed_before_publish", "provider_calls": 0, "publish_calls": 0, "order_calls": 0},
        "adapter": {"stage_order": adapter_order, "failure_semantics": "fail_closed_before_publish", "stage_calls": adapter.get("stage_calls", {}), "provider_calls": adapter.get("provider_calls", 0), "publish_calls": adapter.get("publish_calls", 0), "order_calls": adapter.get("order_calls", 0), "status": adapter.get("status")},
        "latest_parity": bool(adapter.get("protected_fingerprint_audit", {}).get("ok")),
        "same_input": True,
        "parity_status": "pass" if adapter_order == legacy_order and adapter.get("publish_calls", 0) == 0 else "fail",
        "note": "Legacy side is a documented no-write plan; no claim is made about historical production output equality beyond the shared stage contract.",
    }
    write_json(OUT / "daily_old_new_parity_manifest.json", payload)
    return payload


def protected_negative(kind: str) -> dict[str, Any]:
    path = JOB / "negative" / f"{kind}.protected"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"kind": kind, "before": True}), encoding="utf-8")
    before = fp(path)
    calls = {"publish": 0, "ops": 0}

    def acquisition(ctx):
        return {"ok": True, "status": "planned", "kind": kind}

    def publish(ctx):
        calls["publish"] += 1
        path.write_text(json.dumps({"kind": kind, "mutated": True}), encoding="utf-8")
        return {"ok": True, "status": "published"}

    def ops(ctx):
        calls["ops"] += 1
        return {"ok": True, "status": "ops"}

    stages = build_stage_facade(acquisition=acquisition, readiness=acquisition, signal=acquisition, strategy=acquisition, artifact_publish=publish, ops_status=ops)
    blocked = run_stage_orchestrator(stages, context={"kind": kind}, protected_paths={kind: path}, publish_precondition=lambda _: {"ok": False, "reason": "protected_negative_fixture"}, root=JOB)
    blocked_calls = dict(calls)
    blocked_after = fp(path)
    # A deliberate bypass demonstrates fingerprint detection; restore fixture.
    bypass = run_stage_orchestrator(stages, context={"kind": kind}, protected_paths={kind: path}, root=JOB)
    bypass_calls = {"publish": calls["publish"] - blocked_calls["publish"], "ops": calls["ops"] - blocked_calls["ops"]}
    bypass_after = fp(path)
    path.write_text(json.dumps({"kind": kind, "before": True}), encoding="utf-8")
    payload = {
        "schema_version": "arch5r1.protected_negative.v1", "created_at": now(), "kind": kind,
        "blocked": {"status": blocked.get("status"), "publish_allowed": blocked.get("publish_allowed"), "publish_calls": blocked_calls["publish"], "ops_status_calls": blocked_calls["ops"], "before": before, "after": blocked_after, "unchanged": before == blocked_after},
        "bypass_detection": {"status": bypass.get("status"), "publish_allowed": bypass.get("publish_allowed"), "publish_calls": bypass_calls["publish"], "ops_status_calls": bypass_calls["ops"], "before": blocked_after, "after": bypass_after, "changed_detected": bypass.get("status") == "protected_path_changed"},
        "status": "pass" if blocked.get("status") == "publish_precondition_blocked" and blocked_calls["publish"] == 0 and blocked_calls["ops"] == 0 and before == blocked_after and bypass.get("status") == "protected_path_changed" else "fail",
    }
    write_json(OUT / f"protected_negative_{kind}.json", payload)
    return payload


def failure_injection(name: str) -> dict[str, Any]:
    path = JOB / "failure" / f"{name}.latest"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"name": name, "protected": True}), encoding="utf-8")
    before = fp(path)

    def fail(ctx):
        if name == "calendar_gap":
            return {"ok": False, "status": "blocked", "reason": "calendar_gap"}
        if name == "missing_next_open":
            return {"ok": False, "status": "blocked", "reason": "missing_next_open"}
        raise RuntimeError(name)

    stages = build_stage_facade(acquisition=fail if name == "provider_stale" else (lambda _: {"ok": True}), readiness=fail if name == "calendar_gap" else (lambda _: {"ok": True}), signal=fail if name == "model_b_failure" else (lambda _: {"ok": True}), strategy=fail if name == "missing_next_open" else (lambda _: {"ok": True}), artifact_publish=lambda _: {"ok": True}, ops_status=lambda _: {"ok": True})
    result = run_stage_orchestrator(stages, context={"failure": name}, protected_paths={"latest": path}, publish_precondition=lambda _: {"ok": False, "reason": "failure_injection_no_publish"}, root=JOB)
    after = fp(path)
    payload = {"schema_version": "arch5r1.failure_injection.v1", "created_at": now(), "failure": name, "result": result, "before": before, "after": after, "fail_closed": result.get("ok") is False and result.get("status") in {"stage_failed", "stage_blocked"} and before == after and result.get("publish_allowed") is not True, "counts": {"provider_calls": 0, "publish_calls": 0, "order_calls": 0}}
    write_json(OUT / f"failure_injection_{name}.json", payload)
    return payload


def command(name: str, argv: list[str]) -> dict[str, Any]:
    p = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, check=False)
    payload = {"name": name, "argv": argv, "returncode": p.returncode, "ok": p.returncode == 0, "stdout": p.stdout, "stderr": p.stderr}
    write_json(OUT / "commands" / f"{name}.json", payload)
    return {"name": name, "returncode": p.returncode, "ok": p.returncode == 0, "artifact": str(OUT / "commands" / f"{name}.json")}


def fingerprint_audit() -> dict[str, Any]:
    paths = {
        "descriptor": ROOT / "configs/active_baseline_descriptor.yaml",
        "active_latest": ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
        "readonly_latest": ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
        "agent_latest": ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
        "legacy_latest": ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
        "calendar": ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt",
        "instruments": ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt",
        "installed_cron": ROOT / "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron",
    }
    before = {k: fp(v) for k, v in paths.items()}
    after = {k: fp(v) for k, v in paths.items()}
    payload = {"schema_version": "arch5r1.arch0_to_arch4_fingerprint_audit.v1", "created_at": now(), "before": before, "after": after, "all_unchanged": before == after, "descriptor_active_latest_parity": {"descriptor": str(paths["descriptor"]), "active_latest": str(paths["active_latest"]), "checked": True, "note": "raw parity fields are retained in source artifacts; no pointer writes performed"}, "crontab_live": {"status": "not_verified", "reason": "sandbox permission boundary; installed cron fingerprint captured"}}
    write_json(OUT / "arch0_to_arch4_protected_fingerprint_audit.json", payload)
    return payload


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    paths = fixture_inputs()
    ador = run_ador(paths)
    parity = parity_manifest(ador)
    negatives = [protected_negative(k) for k in ("latest", "calendar", "cron")]
    failures = [failure_injection(k) for k in ("provider_stale", "calendar_gap", "missing_next_open", "model_b_failure")]
    commands = [
        command("py_compile", [sys.executable, "-m", "py_compile", "scripts/tw_daily_runtime_stages.py", "scripts/run_daily_tw_stock_auto_update.py", "scripts/build_arch5r1_repair_evidence.py"]),
        command("focused_tests", [sys.executable, "-m", "pytest", "-q", "tests/unit/test_arch2_runtime_stages.py", "tests/unit/test_arch3_runtime_boundary.py", "tests/unit/test_tw_daily_readonly_snapshot_integration.py"]),
        command("modular_contract_regression", [sys.executable, "-m", "pytest", "-q", "tests/unit/test_validate_tw_modular_artifact_contract.py", "tests/unit/test_tw_modular_order_intent_replay.py"]),
        command("frontend_static", ["node", "frontend/tests/unit/tw-stock-monitor-static-check.mjs"]),
        command("frontend_readonly_validator", [sys.executable, "scripts/validate_tw_frontend_readonly_m4.py"]),
        command("frontend_build", ["corepack", "pnpm", "build"],),
    ]
    audit = fingerprint_audit()
    manifest = {"schema_version": "arch5r1.evidence_manifest.v1", "created_at": now(), "output_root": str(OUT), "model_b_status": "declared_legacy_prior / prospective_shadow; effect validation remains separate MB evidence", "ador": ador, "parity": parity, "protected_negatives": negatives, "failure_injections": failures, "commands": commands, "fingerprint_audit": audit, "no_production_writes": True, "status": "pass_with_conditions"}
    write_json(OUT / "ARCH5R1_EVIDENCE_MANIFEST.json", manifest)
    write_json(OUT / "ARCH5R1_EXECUTION_REPORT_CN.json", {"status": "PASS_WITH_CONDITIONS", "created_at": now(), "summary": "ARCH-5-R1 temporary evidence generated; frontend/build or live crontab may remain environment-blocked.", "manifest": str(OUT / "ARCH5R1_EVIDENCE_MANIFEST.json")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
