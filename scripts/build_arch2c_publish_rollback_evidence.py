#!/usr/bin/env python3
"""ARCH-2C staged candidate publish/rollback/fingerprint evidence."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from tw_daily_runtime_stages import fingerprints_unchanged, load_runtime_descriptor, protected_fingerprints
from tw_daily_stage_adapters import (
    build_model_a_signal_callback,
    build_staged_artifact_publish_callback,
    project_legacy_model_a_signal_contract,
    validate_model_a_top50,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/arch2c_publish_rollback_20260912"
MODELA_DIR = ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng9_daily_auto_modela_20260911_20260911T103001Z"


def write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def top50_fixture_matrix() -> dict[str, object]:
    positive = [{"instrument": f"TW{i:04d}", "full_qlib_rank": str(i)} for i in range(1, 51)]
    duplicate_instrument = [dict(row) for row in positive]
    duplicate_instrument[-1]["instrument"] = duplicate_instrument[0]["instrument"]
    duplicate_rank = [dict(row) for row in positive]
    duplicate_rank[-1]["full_qlib_rank"] = "1"
    missing_rank = [dict(row) for row in positive]
    missing_rank[-1]["full_qlib_rank"] = "51"
    return {name: validate_model_a_top50(rows) for name, rows in {"positive": positive, "duplicate_instrument": duplicate_instrument, "duplicate_rank": duplicate_rank, "rank_outside_key_set": missing_rank}.items()}


def publish_matrix() -> dict[str, object]:
    matrix: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix="arch2c-publish-") as temp:
        root = Path(temp)
        candidate = root / "candidate.json"
        rollback = root / "rollback.json"
        candidate.write_text("candidate\n", encoding="utf-8")
        rollback.write_text("rollback\n", encoding="utf-8")
        callback = build_staged_artifact_publish_callback(rollback_source=rollback)
        auth = {"allow_candidate_publish": True, "authorization_id": "ARCH2C_CANDIDATE_ONLY", "publish_mode": "candidate_only"}
        cases = {
            "unauthorized": {"job_dir": str(root), "candidate_path": str(candidate), "authorization": {}},
            "fingerprint_drift": {"job_dir": str(root), "candidate_path": str(candidate), "authorization": auth, "protected_before": {"latest": {"exists": True, "size": 1, "sha256": "a"}}, "protected_after": {"latest": {"exists": True, "size": 2, "sha256": "b"}}},
            "rollback_checksum_mismatch": {"job_dir": str(root), "candidate_path": str(candidate), "authorization": auth, "rollback_checksum": "bad"},
            "authorized_candidate_failure": {"job_dir": str(root), "candidate_path": str(root / "missing.json"), "authorization": auth},
            "authorized_candidate_success": {"job_dir": str(root), "candidate_path": str(candidate), "authorization": auth},
        }
        for name, context in cases.items():
            result = callback(context)
            matrix[name] = {"status": result.get("status"), "ok": result.get("ok"), "publish_allowed": result.get("publish_allowed"), "protected_pointer_write": result.get("protected_pointer_write", False), "manifest_path": result.get("manifest_path", "")}
    return matrix


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    descriptor = load_runtime_descriptor()
    before = protected_fingerprints(descriptor=descriptor, root=ROOT)
    legacy = project_legacy_model_a_signal_contract(MODELA_DIR)
    new = build_model_a_signal_callback(MODELA_DIR)({})
    parity_keys = ("ok", "status", "model_id", "row_count", "signal_checksum", "schema_fields")
    parity = {key: legacy.get(key) == new.get(key) for key in parity_keys}
    write(OUT / "ARCH2C_LEGACY_NEW_SIGNAL_PARITY.json", {"legacy": legacy, "new": {key: new.get(key) for key in parity_keys}, "comparison": parity, "all_equal": all(parity.values())})
    write(OUT / "ARCH2C_TOP50_FIXTURE_MATRIX.json", top50_fixture_matrix())
    write(OUT / "ARCH2C_PUBLISH_FAILURE_MATRIX.json", publish_matrix())
    with tempfile.TemporaryDirectory(prefix="arch2c-stage-") as temp:
        stage = Path(temp)
        candidate = stage / "candidate.json"
        rollback = stage / "rollback.json"
        candidate.write_text("candidate\n", encoding="utf-8")
        rollback.write_text("rollback\n", encoding="utf-8")
        callback = build_staged_artifact_publish_callback(rollback_source=rollback)
        result = callback({"job_dir": str(stage), "candidate_path": str(candidate), "authorization": {"allow_candidate_publish": True, "authorization_id": "ARCH2C_CANDIDATE_ONLY", "publish_mode": "candidate_only"}})
        staged = {str(path.relative_to(stage)): path.read_text(encoding="utf-8") for path in stage.rglob("*") if path.is_file()}
    after = protected_fingerprints(descriptor=descriptor, root=ROOT)
    audit = {"before": before, "after": after, "comparison": fingerprints_unchanged(before, after), "ok": fingerprints_unchanged(before, after)["all_protected_paths_unchanged"], "publish_allowed": False}
    write(OUT / "ARCH2C_STAGED_CANDIDATE_ROLLBACK.json", {"result": result, "staged_files": sorted(staged), "rollback_manifest_present": "candidate_publish/rollback_manifest.json" in staged, "staged_checksum": result.get("candidate_sha256")})
    write(OUT / "ARCH2C_PROTECTED_FINGERPRINT_AUDIT.json", audit)
    golden = subprocess.run([sys.executable, "scripts/validate_tw_daily_orchestrator_m3.py", "--run-golden", "--json"], cwd=ROOT, text=True, capture_output=True, check=False)
    (OUT / "ARCH2C_M3_GOLDEN_RESULT.json").write_text(golden.stdout, encoding="utf-8")
    validator = subprocess.run([sys.executable, "scripts/validate_arch1_baseline_descriptor.py", "--json"], cwd=ROOT, text=True, capture_output=True, check=False)
    (OUT / "ARCH2C_ARCH1_VALIDATOR_RESULT.json").write_text(validator.stdout, encoding="utf-8")
    tests = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/unit/test_arch2_runtime_stages.py"], cwd=ROOT, text=True, capture_output=True, check=False)
    (OUT / "ARCH2C_FOCUSED_TEST_RESULT.txt").write_text(tests.stdout + tests.stderr, encoding="utf-8")
    write(OUT / "ARCH2C_EVIDENCE_MANIFEST.json", {"schema_version": "arch2c.publish_rollback_fingerprint.v1", "created_at": datetime.now(timezone.utc).isoformat(), "files": [path.name for path in sorted(OUT.iterdir()) if path.is_file()], "model_b_active": False, "candidate_universe": "model_a_top50_only", "descriptor_hash_reconciliation_executed": False, "protected_paths_unchanged": audit["ok"], "signal_parity": all(parity.values()), "m3_golden_ok": golden.returncode == 0, "arch1_validator_ok": validator.returncode == 0, "focused_tests_ok": tests.returncode == 0})
    return 0 if all(parity.values()) and audit["ok"] and golden.returncode == 0 and validator.returncode == 0 and tests.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
