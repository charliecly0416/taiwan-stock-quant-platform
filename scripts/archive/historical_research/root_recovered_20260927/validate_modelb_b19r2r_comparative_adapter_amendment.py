#!/usr/bin/env python3
"""Validate comparative adapter Amendment 01."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_comparative_evaluation_20260916"
BASE = OUT / "B19R2R_COMPARATIVE_FREEZE.json"
AMENDMENT = OUT / "B19R2R_COMPARATIVE_FREEZE_AMENDMENT_01.json"
BUILDER = ROOT / "scripts/build_modelb_b19r2r_comparative_adapter_amendment.py"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if not args.validate:
        raise SystemExit("Select --validate")
    amendment = json.loads(AMENDMENT.read_text(encoding="utf-8"))
    adapter = amendment.get("sole_treatment_adapter", {})
    boundary = amendment.get("boundary_invariants", {})
    checks = {
        "base_hash": amendment["base_freeze"]["sha256"] == sha256(BASE),
        "builder_hash": amendment["implementation_bindings"]["builder"]["sha256"] == sha256(BUILDER),
        "validator_hash": amendment["implementation_bindings"]["validator"]["sha256"] == sha256(Path(__file__)),
        "sole_adapter": adapter.get("alternative_adapter_candidates") == 0,
        "weights": adapter.get("model_b_weight") == 1.0 and adapter.get("model_a_weight") == 0.0,
        "no_transformation_or_search": adapter.get("normalization") == "NONE" and adapter.get("calibration") == "NONE" and adapter.get("post_result_blend_search_allowed") is False,
        "model_a_boundary": boundary.get("same_exact50_universe") is True and boundary.get("candidate_rank_source") == "frozen Model A" and boundary.get("full_qlib_rank_source") == "frozen Model A" and boundary.get("model_b_may_change_universe") is False and boundary.get("model_b_may_change_exit_boundary") is False,
        "no_execution": all(value is False for value in amendment.get("safety_at_close", {}).values()),
    }
    verdict = "PASS" if all(checks.values()) else "HOLD"
    print(json.dumps({"checks": checks, "verdict": verdict}, indent=2, ensure_ascii=False))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
