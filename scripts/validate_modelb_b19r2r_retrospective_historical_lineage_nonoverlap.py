#!/usr/bin/env python3
"""Audit temporal and path non-overlap for the B19R2R historical replay."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = (
    ROOT
    / "data_tw/experiments/project_runtime_convergence"
    / "modelb_b19r2r_retrospective_historical_paired_replay_20260918"
)
ORIGINAL_V2 = (
    ROOT
    / "data_tw/experiments/project_runtime_convergence"
    / "modelb_b19r2r_comparative_evaluation_20260916/confirmation_output_v2"
)
PROSPECTIVE_LEDGER_ROOT = ROOT / "data_tw/experiments/modelb_b19r2r_v5_prospective_accumulator"
TRAINING_MANIFEST = (
    ROOT
    / "data_tw/experiments/project_runtime_convergence"
    / "modelb_b19r2r_training_20260916/training_output_v1/TRAINING_MANIFEST.json"
)
RESULT = OUT / "LINEAGE_NONOVERLAP_VALIDATOR_RESULT.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate() -> dict[str, Any]:
    manifest_path = OUT / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    training = json.loads(TRAINING_MANIFEST.read_text(encoding="utf-8"))
    diagnostic = pd.read_csv(OUT / "HISTORICAL_SCORE_OUTCOME_DIAGNOSTIC.csv", dtype={"date": str})
    replay_dates = sorted(diagnostic.date.str[:10].unique().tolist())
    final_refit_end = str(training["final_refit_end"])
    out_resolved = OUT.resolve()
    checks = {
        "training_manifest_hash_matches_bound_source": (
            manifest["source_bindings"]["training_manifest"]["sha256"] == sha256(TRAINING_MANIFEST)
        ),
        "all_replay_dates_strictly_after_final_refit_end": all(day > final_refit_end for day in replay_dates),
        "replay_start_matches_manifest": replay_dates[0] == manifest["date_start"],
        "replay_end_matches_manifest": replay_dates[-1] == manifest["date_end"],
        "replay_date_count_matches_manifest": len(replay_dates) == manifest["date_count"] == 30,
        "output_distinct_from_original_v2_attempt": out_resolved != ORIGINAL_V2.resolve(),
        "output_not_inside_original_v2_attempt": ORIGINAL_V2.resolve() not in out_resolved.parents,
        "output_not_inside_prospective_ledger_root": PROSPECTIVE_LEDGER_ROOT.resolve() not in out_resolved.parents,
        "formal_prospective_claim_false": (
            manifest["prospective_pit_anchor"] is False
            and manifest["untouched_claim"] is False
            and manifest["historical_replay"] is True
        ),
        "prospective_ledger_append_false": manifest["safety"]["prospective_ledger_append"] is False,
        "latest_or_provider_write_false": manifest["safety"]["latest_or_provider_write"] is False,
        "baseline_or_production_change_false": manifest["safety"]["baseline_or_production_change"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("lineage/non-overlap validation failed: " + ", ".join(failed))
    return {
        "schema_version": "modelb.b19r2r.retrospective_historical_lineage_nonoverlap.validator.v1",
        "status": "PASS",
        "checks": checks,
        "final_refit_end": final_refit_end,
        "replay_start": replay_dates[0],
        "replay_end": replay_dates[-1],
        "replay_date_count": len(replay_dates),
        "formal_prospective_claim": False,
        "historical_replay": True,
        "prospective_ledger_append": False,
        "latest_or_provider_write": False,
        "baseline_or_production_change": False,
        "production_allowed": False,
        "manifest_sha256": sha256(manifest_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-result", action="store_true")
    args = parser.parse_args()
    result = validate()
    if args.write_result:
        if RESULT.exists():
            raise RuntimeError("refusing to overwrite lineage/non-overlap validator result")
        RESULT.write_text(json.dumps(result, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        RESULT.chmod(0o600)
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
