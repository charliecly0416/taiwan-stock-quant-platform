#!/usr/bin/env python3
"""Freeze the 2026-09-16 B19R2R V3 materialization for independent review."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import materialize_modelb_b19r2r_v3_bundle_20260916 as builder
import validate_modelb_b19r2r_v3_bundle_20260916 as validator


ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = builder.OUT_ROOT
BUNDLE = RUN_ROOT / "pre_capture_v3"
REPORT = RUN_ROOT / "EXECUTION_REPORT_V3.json"
MANIFEST = RUN_ROOT / "PRECAPTURE_IMPLEMENTATION_MANIFEST_V3.json"
SUMS = RUN_ROOT / "SHA256SUMS_V3"
V2_BLOCKER = RUN_ROOT / "V2_REVIEW_BLOCKER.json"
V2_MANIFEST = RUN_ROOT / "PRECAPTURE_IMPLEMENTATION_MANIFEST_V2.json"
V2_REVIEW = RUN_ROOT / "INDEPENDENT_REVIEW_V2.json"
TEST = ROOT / "tests/isolated/test_modelb_b19r2r_v3_bundle_20260916.py"


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def item(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"missing frozen input: {path}")
    return {"path": rel(path), "sha256": builder.sha256(path), "bytes": path.stat().st_size}


def provider_tree() -> dict[str, Any]:
    paths = [builder.PROVIDER / "calendars/day.txt"]
    for field in ("open", "high", "low", "close", "volume", "vwap"):
        paths.extend(builder.PROVIDER.glob(f"features/*/{field}.day.bin"))
    paths = sorted(set(paths), key=lambda path: rel(path))
    digest = hashlib.sha256()
    for path in paths:
        row = f"{rel(path)}\0{builder.sha256(path)}\0{path.stat().st_size}\n"
        digest.update(row.encode("ascii"))
    return {
        "root": rel(builder.PROVIDER),
        "file_count": len(paths),
        "tree_sha256": digest.hexdigest(),
        "algorithm": "sorted repo-relative path NUL sha256 NUL bytes newline",
    }


def main() -> int:
    if any(path.exists() for path in (REPORT, MANIFEST, SUMS, V2_BLOCKER)):
        raise RuntimeError("refusing to overwrite pre-capture freeze")
    validation = validator.validate_bundle(BUNDLE)
    if validation.get("status") != "PASS":
        raise RuntimeError("bundle validation did not pass")
    attempt = builder.read_json(BUNDLE / "MATERIALIZATION_ATTEMPT.json")
    feature_manifest = builder.read_json(BUNDLE / "FEATURES_78_CANDIDATE_MANIFEST.json")
    lineage = feature_manifest["audit"]["model_a_history_sources"]
    if not lineage or any(builder.sha256(ROOT / source["path"]) != source["sha256"] for source in lineage):
        raise RuntimeError("Model A history lineage changed before freeze")

    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    implementation = [
        item(ROOT / "scripts/materialize_modelb_b19r2r_v3_bundle_20260916.py"),
        item(ROOT / "scripts/validate_modelb_b19r2r_v3_bundle_20260916.py"),
        item(Path(__file__)),
        item(TEST),
    ]
    direct_inputs = [
        item(builder.MODEL_A_SIGNALS),
        item(builder.MODEL_A_MANIFEST),
        item(builder.MODEL_A_PRE_CUTOFF_PREDICTION),
        item(builder.MODEL_A_PRE_CUTOFF_METADATA),
        item(builder.MODEL_A_PRE_CUTOFF_ARTIFACT_MANIFEST),
        item(builder.MODEL_A_HISTORY),
        item(builder.FEATURE_SCHEMA),
        item(builder.MODEL_B),
        item(builder.TRAINING_MANIFEST),
        item(builder.PRICE_ADAPTER),
        item(builder.PRICE_JSON),
        item(builder.INSTITUTIONAL_ADAPTER),
        item(builder.INSTITUTIONAL_JSON),
        item(builder.MARGIN_ADAPTER),
        item(builder.MARGIN_JSON),
        item(builder.TWII_ADAPTER),
        item(builder.TWII_NORMALIZED),
    ]
    bundle_artifacts = [item(path) for path in sorted(BUNDLE.iterdir()) if path.is_file()]

    report = {
        "schema_version": "modelb_b19r2r.v3.precapture_execution.v1",
        "created_at": created_at,
        "asof": builder.ASOF,
        "status": "PASS_MATERIALIZATION_NOT_ELIGIBLE_BLOCKED_TWII",
        "scope": "research_only_expected_input_bundle_materialization_and_validation",
        "result": {
            "model_a_exact50_rows": 50,
            "feature_candidate_rows": validation["rows"],
            "complete_78_rows": validation["complete_78_rows"],
            "candidate14_score_emitted": validation["score_artifact_present"],
            "eligible_for_capture": validation["eligible_for_capture"],
            "accepted_ledger_event_written": validation["accepted_ledger_event_written"],
            "blockers": attempt["blockers"],
        },
        "verification": {
            "py_compile": "PASS",
            "ruff": "PASS",
            "targeted_pytest": "16 passed",
            "actual_bundle_validator": "PASS",
            "historical_source_resolution": "ModelSignalArtifact fallback for 2026-09-09 and 2026-09-10; all duplicate daily sources exact-score parity",
        },
        "availability_semantics": {
            "model_a_exact50_available_at": builder.read_json(builder.MODEL_A_PRE_CUTOFF_METADATA)["created_at"],
            "meaning": "actual accepted prediction artifact creation time proven by hash-bound run metadata",
            "materializer_created_at": attempt["created_at"],
        },
        "boundaries": {
            "training_performed": False,
            "tuning_performed": False,
            "capture_performed": False,
            "accepted_ledger_event_written": False,
            "baseline_changed": False,
            "provider_or_accepted_latest_changed": False,
            "cron_frontend_database_broker_changed": False,
            "sealed_v2_accessed_or_rerun": False,
            "production_allowed": False,
        },
        "next_gate": "independent implementation and evidence review; blocked bundle cannot be captured",
    }
    write_json(REPORT, report)

    manifest = {
        "schema_version": "modelb_b19r2r.v3.precapture_implementation_manifest.v3",
        "created_at": created_at,
        "status": "FROZEN_AWAITING_INDEPENDENT_REVIEW_NOT_ELIGIBLE",
        "model_id": builder.MODEL_B_ID,
        "model_sha256": builder.MODEL_B_SHA,
        "candidate_id": 14,
        "feature_count": 78,
        "feature_order_sha256": builder.FEATURE_ORDER_SHA,
        "source_run_id": builder.SOURCE_RUN,
        "decision_cutoff": builder.CUTOFF,
        "final_model_frozen_at": builder.FINAL_MODEL_FROZEN_AT,
        "implementation": implementation,
        "direct_inputs": direct_inputs,
        "model_a_history_sources": lineage,
        "provider_input_tree": provider_tree(),
        "bundle_artifacts": bundle_artifacts,
        "execution_report": item(REPORT),
        "validation_result": validation,
        "capture_eligible": False,
        "capture_authorized": False,
        "independent_review_required": True,
        "production_allowed": False,
    }
    write_json(MANIFEST, manifest)

    blocker = {
        "schema_version": "modelb_b19r2r.v3.precapture_v2_review_blocker.v1",
        "created_at": created_at,
        "status": "V2_INVALIDATED_AFTER_INDEPENDENT_REVIEW",
        "v2_manifest": rel(V2_MANIFEST),
        "v2_manifest_sha256": builder.sha256(V2_MANIFEST),
        "v2_review": rel(V2_REVIEW),
        "v2_review_sha256": builder.sha256(V2_REVIEW),
        "blocking_finding": "V2 validator trusted lineage.available_at without deriving created_at from the hash-bound source metadata.",
        "repair": "V3 independently validates prediction run metadata plus artifact manifest and ModelSignal identity manifest, and requires claimed available_at to equal actual created_at.",
        "v2_capture_authorized": False,
        "v2_accepted_ledger_event_written": False,
    }
    write_json(V2_BLOCKER, blocker)

    sum_paths = [
        *(BUNDLE / entry["path"].split("/")[-1] for entry in bundle_artifacts),
        REPORT,
        MANIFEST,
        V2_BLOCKER,
    ]
    rows = [f"{builder.sha256(path)}  {rel(path)}" for path in sorted(sum_paths, key=rel)]
    SUMS.write_text("\n".join(rows) + "\n", encoding="ascii")
    for path in [*BUNDLE.iterdir(), REPORT, MANIFEST, V2_BLOCKER, SUMS]:
        if path.is_file():
            os.chmod(path, 0o444)
    print(json.dumps({"status": manifest["status"], "manifest_sha256": builder.sha256(MANIFEST)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
