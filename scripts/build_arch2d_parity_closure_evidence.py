#!/usr/bin/env python3
"""ARCH-2D no-publish terminal parity and failure-matrix evidence."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from tw_daily_runtime_stages import (
    build_stage_facade,
    fingerprints_unchanged,
    load_runtime_descriptor,
    protected_fingerprints,
    run_no_publish_terminal_orchestrator,
)
from tw_daily_stage_adapters import build_staged_artifact_publish_callback, validate_model_a_top50

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/arch2d_parity_closure_20260912"


def write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def top50_failure_matrix() -> dict[str, object]:
    base = [{"instrument": f"TW{i:04d}", "full_qlib_rank": str(i)} for i in range(1, 51)]
    cases = {
        "positive_50": base,
        "short_49": base[:-1],
        "long_51": base + [{"instrument": "TW0051", "full_qlib_rank": "51"}],
        "missing_rank": [dict(row) for row in base],
        "duplicate_instrument": [dict(row) for row in base],
        "duplicate_rank": [dict(row) for row in base],
        "rank_outside_1_50": [dict(row) for row in base],
    }
    cases["missing_rank"][0].pop("full_qlib_rank")
    cases["duplicate_instrument"][-1]["instrument"] = cases["duplicate_instrument"][0]["instrument"]
    cases["duplicate_rank"][-1]["full_qlib_rank"] = "1"
    cases["rank_outside_1_50"][-1]["full_qlib_rank"] = "51"
    return {name: validate_model_a_top50(rows) for name, rows in cases.items()}


def publish_path_failure_matrix() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="arch2d-publish-path-") as temp:
        root = Path(temp)
        job = root / "job"
        outside = root / "outside.json"
        candidate = job / "candidate.json"
        rollback = root / "rollback.json"
        job.mkdir()
        outside.write_text("outside\n", encoding="utf-8")
        candidate.write_text("candidate\n", encoding="utf-8")
        rollback.write_text("rollback\n", encoding="utf-8")
        auth = {"allow_candidate_publish": True, "authorization_id": "ARCH2D_CANDIDATE_ONLY", "publish_mode": "candidate_only"}
        callback = build_staged_artifact_publish_callback(rollback_source=rollback)
        cases = {
            "candidate_path_outside_job_dir": {"job_dir": str(job), "candidate_path": str(outside), "authorization": auth},
            "missing_rollback_source": {"job_dir": str(job), "candidate_path": str(candidate), "authorization": auth, "rollback_checksum": "missing"},
            "rollback_checksum_drift": {"job_dir": str(job), "candidate_path": str(candidate), "authorization": auth, "rollback_checksum": "drift"},
        }
        out = {}
        for name, context in cases.items():
            if name == "missing_rollback_source":
                callback = build_staged_artifact_publish_callback(rollback_source=root / "missing-rollback.json")
            else:
                callback = build_staged_artifact_publish_callback(rollback_source=rollback)
            result = callback(context)
            out[name] = {"status": result.get("status"), "ok": result.get("ok"), "protected_pointer_write": result.get("protected_pointer_write", False), "publish_allowed": result.get("publish_allowed", False)}
        return out


def terminal_parity() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="arch2d-terminal-") as temp:
        root = Path(temp)
        latest = root / "latest.json"
        latest.write_text("latest\n", encoding="utf-8")
        callbacks = {name: (lambda context, stage=name: {"ok": True, "status": "READY", "stage": stage}) for name in ("acquisition", "readiness", "signal", "strategy", "artifact_publish", "ops_status")}
        result = run_no_publish_terminal_orchestrator(build_stage_facade(**callbacks), asof="2026-09-12", job_id="arch2d", protected_paths={"latest": latest}, root=root)
        return result


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    descriptor = load_runtime_descriptor()
    before = protected_fingerprints(descriptor=descriptor, root=ROOT)
    write(OUT / "ARCH2D_TOP50_FAILURE_MATRIX.json", top50_failure_matrix())
    write(OUT / "ARCH2D_PUBLISH_PATH_FAILURE_MATRIX.json", publish_path_failure_matrix())
    write(OUT / "ARCH2D_TERMINAL_PARITY.json", terminal_parity())
    commands = {
        "arch2b": [sys.executable, "scripts/build_arch2b_signal_shadow_parity_evidence.py"],
        "arch2c": [sys.executable, "scripts/build_arch2c_publish_rollback_evidence.py"],
        "m3": [sys.executable, "scripts/validate_tw_daily_orchestrator_m3.py", "--run-golden", "--json"],
        "arch1": [sys.executable, "scripts/validate_arch1_baseline_descriptor.py", "--json"],
        "focused": [sys.executable, "-m", "pytest", "-q", "tests/unit/test_arch2_runtime_stages.py"],
    }
    command_results = {}
    for name, command in commands.items():
        proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        command_results[name] = {"returncode": proc.returncode, "ok": proc.returncode == 0, "stdout_tail": proc.stdout[-1000:], "stderr_tail": proc.stderr[-1000:]}
    write(OUT / "ARCH2D_REGRESSION_COMMANDS.json", command_results)
    after = protected_fingerprints(descriptor=descriptor, root=ROOT)
    audit = {"before": before, "after": after, "comparison": fingerprints_unchanged(before, after), "ok": fingerprints_unchanged(before, after)["all_protected_paths_unchanged"], "publish_allowed": False}
    write(OUT / "ARCH2D_PROTECTED_FINGERPRINT_AUDIT.json", audit)
    top = json.loads((OUT / "ARCH2D_TOP50_FAILURE_MATRIX.json").read_text())
    terminal = json.loads((OUT / "ARCH2D_TERMINAL_PARITY.json").read_text())
    matrix_ok = top["positive_50"]["ok"] and all(not top[name]["ok"] for name in top if name != "positive_50")
    write(OUT / "ARCH2D_EVIDENCE_MANIFEST.json", {"schema_version": "arch2d.parity_closure.v1", "created_at": datetime.now(timezone.utc).isoformat(), "files": [path.name for path in sorted(OUT.iterdir()) if path.is_file()], "top50_matrix_ok": matrix_ok, "terminal_parity_ok": terminal.get("ok"), "regression_commands_ok": all(item["ok"] for item in command_results.values()), "protected_paths_unchanged": audit["ok"], "descriptor_hash_reconciliation_executed": False, "model_b_active": False})
    return 0 if matrix_ok and terminal.get("ok") and all(item["ok"] for item in command_results.values()) and audit["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
