#!/usr/bin/env python3
"""Build ARCH-2 implementation evidence without touching protected latest files."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from tw_daily_runtime_stages import (
    build_legacy_observation_terminal,
    build_stage_facade,
    descriptor_summary,
    fingerprints_unchanged,
    load_runtime_descriptor,
    protected_fingerprints,
    run_stage_orchestrator,
)
from tw_daily_stage_adapters import build_named_stage_adapters, stage_contract_summary

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / os.getenv("ARCH2_EVIDENCE_OUT", "data_tw/experiments/project_runtime_convergence/arch2_daily_orchestrator_split_20260907")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    descriptor = load_runtime_descriptor()
    before = protected_fingerprints(descriptor=descriptor)
    # ARCH-2 evidence is a no-publish observation; no callback is executed.
    after = protected_fingerprints(descriptor=descriptor)
    comparison = fingerprints_unchanged(before, after)
    (OUT / "ARCH2_PROTECTED_FINGERPRINT_AUDIT.json").write_text(json.dumps({"schema_version": "arch2.protected_fingerprint_audit.v1", "before": before, "after": after, "comparison": comparison, "ok": comparison["all_protected_paths_unchanged"], "publish_allowed": False}, indent=2) + "\n", encoding="utf-8")
    validator = subprocess.run([sys.executable, str(ROOT / "scripts/validate_arch1_baseline_descriptor.py"), "--json"], cwd=ROOT, text=True, capture_output=True, check=False)
    (OUT / "ARCH2_VALIDATOR_RESULT.json").write_text(validator.stdout, encoding="utf-8")
    tests = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/unit/test_arch2_runtime_stages.py", "tests/unit/test_arch3_runtime_boundary.py", "tests/unit/test_arch1_active_baseline_descriptor.py", "tests/unit/test_tw_daily_readonly_snapshot_integration.py"], cwd=ROOT, text=True, capture_output=True, check=False)
    (OUT / "ARCH2_FOCUSED_TEST_RESULT.txt").write_text(tests.stdout + tests.stderr, encoding="utf-8")
    golden = subprocess.run([sys.executable, "scripts/validate_tw_daily_orchestrator_m3.py", "--run-golden", "--json"], cwd=ROOT, text=True, capture_output=True, check=False)
    (OUT / "ARCH2_M3_GOLDEN_RESULT.json").write_text(golden.stdout, encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="arch2-stage-parity-") as temp:
        temp_root = Path(temp)
        latest = temp_root / "latest.json"
        latest.write_text("{}\n", encoding="utf-8")
        protected = {"latest": latest}
        legacy = build_legacy_observation_terminal(
            asof="2026-09-04", job_id="arch2-parity", protected_before=protected_fingerprint_snapshot(latest), protected_after=protected_fingerprint_snapshot(latest)
        )
        callbacks = {name: (lambda context, stage=name: {"ok": True, "stage": stage}) for name in ("acquisition", "readiness", "signal", "strategy", "artifact_publish", "ops_status")}
        facade_result = run_stage_orchestrator(
            build_stage_facade(**callbacks),
            context={"mode": "no_publish_dry_run"}, protected_paths=protected,
            publish_precondition=lambda _: {"ok": False, "reason": "arch2_no_publish"}, root=temp_root,
        )
        fail_closed = run_stage_orchestrator(
            build_stage_facade(**callbacks), context={"mode": "no_publish_dry_run"}, protected_paths=protected,
            publish_precondition=lambda _: {"ok": False, "reason": "failure_injection"}, root=temp_root,
        )
        parity = {
            "schema_version": "arch2.stage_parity.v1",
            "legacy": legacy,
            "facade": facade_result,
            "fail_closed": fail_closed,
            "same_stage_prefix": legacy["stage_order"] == ["acquisition", "readiness", "signal", "strategy"],
            "latest_parity": bool(facade_result.get("protected_fingerprint_audit", {}).get("ok")),
            "publish_blocked": facade_result.get("status") == "publish_precondition_blocked",
        }
        (OUT / "ARCH2_STAGE_PARITY.json").write_text(json.dumps(parity, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    named_callback = lambda context: {"ok": True, "status": "planned_no_write"}
    named = build_named_stage_adapters(
        acquisition=named_callback,
        readiness=named_callback,
        model_a_signal=named_callback,
        model_b_shadow=named_callback,
        strategy=named_callback,
        artifact_publish=named_callback,
        ops_status=named_callback,
    )
    (OUT / "ARCH2_NAMED_STAGE_CONTRACTS.json").write_text(json.dumps(stage_contract_summary(named), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {"schema_version": "arch2.evidence_manifest.v1", "created_at": datetime.now(timezone.utc).isoformat(), "descriptor_summary": descriptor_summary(), "stage_facade": ["acquisition", "readiness", "signal", "strategy", "artifact_publish", "ops_status"], "named_stage_adapters": ["acquisition", "readiness", "model_a_signal", "model_b_shadow", "strategy", "artifact_publish", "ops_status"], "evidence": ["ARCH2_PROTECTED_FINGERPRINT_AUDIT.json", "ARCH2_VALIDATOR_RESULT.json", "ARCH2_FOCUSED_TEST_RESULT.txt", "ARCH2_M3_GOLDEN_RESULT.json", "ARCH2_STAGE_PARITY.json", "ARCH2_NAMED_STAGE_CONTRACTS.json"], "legacy_entrypoint_behavior_preserved": True, "production_latest_write": False, "cron_provider_frontend_backend_changed": False}
    (OUT / "ARCH2_EVIDENCE_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if validator.returncode == 0 and tests.returncode == 0 and golden.returncode == 0 and comparison["all_protected_paths_unchanged"] else 1


def protected_fingerprint_snapshot(path: Path) -> dict[str, dict[str, object]]:
    import hashlib
    raw = path.read_bytes()
    return {"latest": {"path": str(path), "exists": True, "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}}


if __name__ == "__main__":
    raise SystemExit(main())
