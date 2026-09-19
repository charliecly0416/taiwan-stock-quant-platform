#!/usr/bin/env python3
"""ARCH-2B readonly Model A signal / Model B shadow callback parity evidence."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from tw_daily_runtime_stages import (
    build_stage_facade,
    fingerprints_unchanged,
    load_runtime_descriptor,
    protected_fingerprints,
    run_stage_orchestrator,
)
from tw_daily_stage_adapters import (
    build_model_a_signal_callback,
    build_model_b_shadow_callback,
    inspect_model_a_signal_artifact,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/arch2b_signal_shadow_parity_20260912"
MODELA_DIR = ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng9_daily_auto_modela_20260911_20260911T103001Z"
PROTECTED = {
    str(path): ROOT / path
    for path in load_runtime_descriptor().get("protected_latest_paths", {})
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def legacy_signal_observation(signal_dir: Path) -> dict[str, Any]:
    """Legacy read-only contract projection used only for parity comparison."""
    observed = inspect_model_a_signal_artifact(signal_dir)
    return {key: observed.get(key) for key in ("ok", "status", "model_id", "row_count", "signal_checksum", "schema_fields")}


def run_chain(*, model_a_callback, model_b_callback, job_dir: Path) -> dict[str, Any]:
    calls = {name: 0 for name in ("acquisition", "readiness", "signal", "strategy", "artifact_publish", "ops_status")}

    def count(name: str, callback):
        def wrapped(context):
            calls[name] += 1
            return callback(context)
        return wrapped

    def signal_stage(context: Mapping[str, Any]) -> dict[str, Any]:
        model_a = model_a_callback(context)
        model_b = model_b_callback({"model_a_signal": model_a, "job_dir": job_dir})
        # Model B is explicitly non-blocking: Model A readiness controls the
        # strategy chain, while shadow failure remains visible in evidence.
        return {
            "ok": bool(model_a.get("ok")),
            "status": model_a.get("status"),
            "model_a_signal": model_a,
            "model_b_shadow": {**model_b, "non_blocking": True},
        }

    stages = build_stage_facade(
        acquisition=count("acquisition", lambda context: {"ok": True, "status": "READY"}),
        readiness=count("readiness", lambda context: {"ok": True, "status": "READY"}),
        signal=count("signal", signal_stage),
        strategy=count("strategy", lambda context: {"ok": True, "status": "STRATEGY_READONLY_NO_INTENT", "candidate_universe": "model_a_top50_only", "execution_price_mode": "next_open"}),
        artifact_publish=count("artifact_publish", lambda context: {"ok": True, "status": "UNREACHABLE_NO_PUBLISH"}),
        ops_status=count("ops_status", lambda context: {"ok": True, "status": "UNREACHABLE_NO_PUBLISH"}),
    )
    result = run_stage_orchestrator(
        stages,
        context={"asof": "2026-09-11", "job_dir": str(job_dir), "mode": "arch2b_no_publish"},
        protected_paths=PROTECTED,
        publish_precondition=lambda context: {"ok": False, "reason": "arch2b_no_publish"},
        root=ROOT,
    )
    result["stage_calls"] = calls
    result["model_b_non_blocking"] = True
    return result


def callback_matrix() -> dict[str, Any]:
    matrix: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="arch2b-matrix-") as temp:
        temp_root = Path(temp)
        valid_model_a = build_model_a_signal_callback(MODELA_DIR)
        valid_model_b = build_model_b_shadow_callback()
        cases = {
            "model_a_failure": (lambda context: {"ok": False, "status": "BLOCKED_MODEL_A_SIGNAL", "model_b_active_selection": False}, valid_model_b),
            "model_b_failure": (valid_model_a, lambda context: {"ok": False, "status": "BLOCKED_MODEL_B_SHADOW_INPUT", "model_b_active_selection": False, "published": False}),
            "missing_input": (build_model_a_signal_callback(temp_root / "missing"), valid_model_b),
            "schema_mismatch": (build_model_a_signal_callback(temp_root / "bad_schema"), valid_model_b),
        }
        bad = temp_root / "bad_schema"
        bad.mkdir()
        (bad / "manifest.json").write_text(json.dumps({"model_id": "wrong", "status": "READY"}), encoding="utf-8")
        (bad / "signals.csv").write_text("date,instrument\n2026-09-11,TW0000\n", encoding="utf-8")
        for name, (model_a, model_b) in cases.items():
            result = run_chain(model_a_callback=model_a, model_b_callback=model_b, job_dir=temp_root / name)
            calls = result["stage_calls"]
            matrix[name] = {
                "status": result.get("status"),
                "failed_stage": result.get("failed_stage"),
                "model_a_non_blocking": name == "model_b_failure",
                "model_b_active_selection": False,
                "strategy_calls": calls["strategy"],
                "artifact_publish_calls": calls["artifact_publish"],
                "ops_status_calls": calls["ops_status"],
                "continue_after_shadow_failure": name == "model_b_failure" and calls["strategy"] == 1,
            }
    return matrix


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    before = protected_fingerprints(root=ROOT)
    legacy = legacy_signal_observation(MODELA_DIR)
    new = build_model_a_signal_callback(MODELA_DIR)({})
    staging_root = OUT / "job_dir_shadow_stage"
    staging_root.mkdir(parents=True, exist_ok=True)
    chain = run_chain(model_a_callback=build_model_a_signal_callback(MODELA_DIR), model_b_callback=build_model_b_shadow_callback(), job_dir=staging_root)
    staging_files = sorted(str(path.relative_to(OUT)) for path in staging_root.rglob("*") if path.is_file())
    staging_checksums = {name: _sha(OUT / name) for name in staging_files}
    after = protected_fingerprints(root=ROOT)
    parity_keys = ("ok", "status", "model_id", "row_count", "signal_checksum", "schema_fields")
    parity = {key: legacy.get(key) == new.get(key) for key in parity_keys}
    _write(OUT / "ARCH2B_SIGNAL_SCHEMA_STATUS_CHECKSUM_PARITY.json", {"legacy": legacy, "new": {key: new.get(key) for key in parity_keys}, "comparison": parity, "all_equal": all(parity.values())})
    _write(OUT / "ARCH2B_CALLBACK_CHAIN.json", {"chain": chain, "shadow_staging_files": staging_files, "shadow_staging_checksums": staging_checksums, "protected_fingerprint_audit": {"before": before, "after": after, "comparison": fingerprints_unchanged(before, after), "ok": fingerprints_unchanged(before, after)["all_protected_paths_unchanged"], "publish_allowed": False}})
    _write(OUT / "ARCH2B_FAILURE_MATRIX.json", callback_matrix())
    golden = subprocess.run([sys.executable, "scripts/validate_tw_daily_orchestrator_m3.py", "--run-golden", "--json"], cwd=ROOT, text=True, capture_output=True, check=False)
    (OUT / "ARCH2B_M3_GOLDEN_RESULT.json").write_text(golden.stdout, encoding="utf-8")
    validator = subprocess.run([sys.executable, "scripts/validate_arch1_baseline_descriptor.py", "--json"], cwd=ROOT, text=True, capture_output=True, check=False)
    (OUT / "ARCH2B_ARCH1_VALIDATOR_RESULT.json").write_text(validator.stdout, encoding="utf-8")
    tests = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/unit/test_arch2_runtime_stages.py"], cwd=ROOT, text=True, capture_output=True, check=False)
    (OUT / "ARCH2B_FOCUSED_TEST_RESULT.txt").write_text(tests.stdout + tests.stderr, encoding="utf-8")
    _write(OUT / "ARCH2B_EVIDENCE_MANIFEST.json", {"schema_version": "arch2b.signal_shadow_parity.v1", "created_at": datetime.now(timezone.utc).isoformat(), "model_a_signal_source": str(MODELA_DIR.relative_to(ROOT)), "model_b_active": False, "candidate_universe": "model_a_top50_only", "execution_price_mode": "next_open", "files": ["ARCH2B_SIGNAL_SCHEMA_STATUS_CHECKSUM_PARITY.json", "ARCH2B_CALLBACK_CHAIN.json", "ARCH2B_FAILURE_MATRIX.json", "ARCH2B_M3_GOLDEN_RESULT.json", "ARCH2B_ARCH1_VALIDATOR_RESULT.json", "ARCH2B_FOCUSED_TEST_RESULT.txt", "ARCH2B_EVIDENCE_MANIFEST.json"], "protected_paths_unchanged": fingerprints_unchanged(before, after)["all_protected_paths_unchanged"], "m3_golden_command_ok": golden.returncode == 0, "arch1_validator_command_ok": validator.returncode == 0, "focused_tests_command_ok": tests.returncode == 0})
    return 0 if all(parity.values()) and validator.returncode == 0 and golden.returncode == 0 and tests.returncode == 0 and fingerprints_unchanged(before, after)["all_protected_paths_unchanged"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
