#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow/model_artifact_phase1c_20260905"
PREFLIGHT_ROOT = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow/mbcds0_preflight_20260905"
OUT = PREFLIGHT_ROOT / "independent_review.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    findings = []
    model_gate = read_json(MODEL_ROOT / "gate_summary.json")
    audit = pd.read_csv(MODEL_ROOT / "score_reproduction_audit.csv")
    checksums = read_json(MODEL_ROOT / "checksum_manifest.json")
    readiness = read_json(PREFLIGHT_ROOT / "readiness_report.json")
    protected = read_json(PREFLIGHT_ROOT / "protected_path_fingerprint_audit.json")
    candidate_mode = readiness.get("twii_source_mode") == "explicit_isolated_candidate"

    bad_hashes = [relative for relative, expected in checksums.items() if not (ROOT / relative).is_file() or sha256(ROOT / relative) != expected]
    if bad_hashes:
        findings.append({"severity": "P0", "finding": "model artifact checksum mismatch", "paths": bad_hashes})
    if model_gate.get("score_reproduction_pass") is not True or len(audit) != 4 or not audit["pass"].astype(str).str.lower().isin({"true", "1", "yes"}).all():
        findings.append({"severity": "P0", "finding": "exact Phase1C model reproduction not proven"})
    if int(model_gate.get("joined_rows", 0)) != 152249 or float(model_gate.get("max_abs_diff", 1)) > 1e-12:
        findings.append({"severity": "P0", "finding": "row-level reproduction count/tolerance mismatch", "gate": model_gate})
    expected_blockers = [] if candidate_mode else ["twii_120_session_continuity"]
    if readiness.get("blocking_gates") != expected_blockers:
        findings.append({"severity": "P1", "finding": "unexpected readiness blockers", "blocking_gates": readiness.get("blocking_gates")})
    if candidate_mode:
        if readiness.get("ready_for_shadow_scoring") is not True or readiness.get("decision") != "READY_FOR_MBCDS2_LATEST_SHADOW_SCORE":
            findings.append({"severity": "P0", "finding": "candidate input did not pass readiness"})
        candidate = readiness.get("twii_candidate", {})
        if candidate.get("required_sessions") != 120 or candidate.get("verified_sessions") != 120 or candidate.get("effective_dates_count") != 120:
            findings.append({"severity": "P0", "finding": "candidate effective closure is not 120/120", "candidate": candidate})
        if candidate.get("candidate_duplicate_dates") != 0 or candidate.get("candidate_finite_positive_close_failures") != 0 or not candidate.get("declared_exception"):
            findings.append({"severity": "P0", "finding": "candidate data-quality or exception contract failed", "candidate": candidate})
        blocker = "none; explicit candidate passed MBCDS0 input gates"
    else:
        if readiness.get("ready_for_shadow_scoring") is not False or readiness.get("decision") != "STOP_INPUT_NOT_READY":
            findings.append({"severity": "P0", "finding": "scoring was not stopped on incomplete TWII continuity"})
        if int(readiness.get("missing_twii_sessions", 0)) != 68:
            findings.append({"severity": "P1", "finding": "TWII missing-session evidence changed", "actual": readiness.get("missing_twii_sessions")})
        blocker = "68 missing TWII sessions in required 120-session window"
    if protected.get("unchanged") is not True:
        findings.append({"severity": "P0", "finding": "protected path changed"})

    verdict = ("PASS_CANDIDATE_READY_FOR_MBCDS2" if candidate_mode else "PASS_WITH_EXPECTED_INPUT_BLOCKER") if not findings else "FAIL_NEEDS_REPAIR"
    review = {
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "route": "MBCDS0_MBCDS1_INDEPENDENT_REVIEW",
        "verdict": verdict,
        "findings": findings,
        "model_materialization": "PASS" if not findings else "NOT_ACCEPTED",
        "latest_shadow_scoring": "NOT_EXECUTED_PENDING_EXPLICIT_NEXT_STEP" if candidate_mode else "BLOCKED_NOT_EXECUTED",
        "blocker": blocker,
        "reviewer_decision": "candidate may proceed to MBCDS2 no-publish shadow scoring" if candidate_mode and not findings else "repair immutable continuous TWII input before MBCDS2; do not impute, stale-fill, or substitute another model",
        "production_default_status": "UNCHANGED_NOT_AUTHORIZED",
    }
    OUT.write_text(json.dumps(review, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(review, ensure_ascii=False, indent=2))
    return 0 if not findings else 2


if __name__ == "__main__":
    raise SystemExit(main())
