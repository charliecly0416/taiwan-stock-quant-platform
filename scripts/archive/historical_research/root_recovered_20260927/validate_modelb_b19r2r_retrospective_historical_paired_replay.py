#!/usr/bin/env python3
"""Validate the isolated B19R2R retrospective historical paired replay."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = (
    ROOT
    / "data_tw/experiments/project_runtime_convergence"
    / "modelb_b19r2r_retrospective_historical_paired_replay_20260918"
)
RESULT = OUT / "VALIDATOR_RESULT.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check(condition: bool, code: str, checks: dict[str, bool]) -> None:
    checks[code] = bool(condition)
    if not condition:
        raise RuntimeError(code)


def validate() -> dict[str, Any]:
    checks: dict[str, bool] = {}
    manifest_path = OUT / "MANIFEST.json"
    check(manifest_path.is_file(), "manifest_exists", checks)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    check(
        manifest.get("status") == "PASS_RETROSPECTIVE_HISTORICAL_REPLAY_DIAGNOSTIC_ONLY",
        "historical_status",
        checks,
    )
    check(manifest.get("historical_replay") is True, "historical_replay_true", checks)
    check(manifest.get("prospective_pit_anchor") is False, "prospective_anchor_false", checks)
    check(manifest.get("untouched_claim") is False, "untouched_claim_false", checks)
    check(
        manifest.get("input_was_previously_read_or_consumed") is True,
        "consumed_input_disclosed",
        checks,
    )
    check(manifest.get("prior_v2_attempt_retried_or_modified") is False, "v2_not_retried", checks)
    safety = manifest.get("safety", {})
    for key in (
        "training_performed",
        "tuning_performed",
        "feature_label_model_weight_or_threshold_changed",
        "prospective_ledger_append",
        "latest_or_provider_write",
        "baseline_or_production_change",
        "production_allowed",
    ):
        check(safety.get(key) is False, f"safety_{key}_false", checks)

    for name, item in manifest.get("source_bindings", {}).items():
        path = ROOT / item["path"]
        check(path.is_file(), f"source_exists_{name}", checks)
        check(path.stat().st_size == item["bytes"], f"source_size_{name}", checks)
        check(sha256(path) == item["sha256"], f"source_hash_{name}", checks)

    for name, item in manifest.get("artifacts", {}).items():
        path = ROOT / item["path"]
        check(path.is_file(), f"artifact_exists_{name}", checks)
        check(path.stat().st_size == item["bytes"], f"artifact_size_{name}", checks)
        check(sha256(path) == item["sha256"], f"artifact_hash_{name}", checks)
        if item.get("rows") is not None:
            rows = sum(1 for _ in path.open("r", encoding="utf-8")) - 1
            check(rows == item["rows"], f"artifact_rows_{name}", checks)

    protected_before = json.loads((OUT / "PROTECTED_FINGERPRINT_BEFORE.json").read_text(encoding="utf-8"))
    protected_after = json.loads((OUT / "PROTECTED_FINGERPRINT_AFTER.json").read_text(encoding="utf-8"))
    check(protected_before == protected_after, "protected_before_after_equal", checks)
    check(manifest["protected_boundary"]["unchanged"] is True, "protected_manifest_unchanged", checks)

    diagnostic = pd.read_csv(OUT / "HISTORICAL_SCORE_OUTCOME_DIAGNOSTIC.csv")
    predictions = pd.read_csv(OUT / "FINAL_MODEL_B_PREDICTIONS.csv")
    check(len(diagnostic) == 1500, "diagnostic_rows_1500", checks)
    check(diagnostic.date.astype(str).nunique() == 30, "diagnostic_dates_30", checks)
    check(not diagnostic.duplicated(["date", "instrument"]).any(), "diagnostic_key_unique", checks)
    check(diagnostic.groupby("date").size().eq(50).all(), "diagnostic_exact50_each_day", checks)
    check(len(predictions) == 1500, "prediction_rows_1500", checks)
    check(
        predictions.merge(
            diagnostic[["date", "instrument", "model_b_final_raw_score"]],
            on=["date", "instrument"],
            validate="one_to_one",
            suffixes=("_prediction", "_diagnostic"),
        ).pipe(
            lambda frame: frame.model_b_final_raw_score_prediction.eq(
                frame.model_b_final_raw_score_diagnostic
            ).all()
        ),
        "prediction_diagnostic_score_exact",
        checks,
    )

    paired = pd.read_csv(OUT / "PAIRED_METRICS.csv").set_index("method")
    check(set(paired.index) == {"A_ONLY", "A_PLUS_B"}, "paired_tracks_exact", checks)
    for method in ("A_ONLY", "A_PLUS_B"):
        nav = pd.read_csv(OUT / f"{method}_DAILY_NAV.csv")
        actions = pd.read_csv(OUT / f"{method}_ACTIONS.csv")
        executed = actions[actions.status.eq("EXECUTED")]
        skipped = actions[actions.status.eq("SKIPPED_ZERO_OR_INSUFFICIENT_CASH")]
        check(len(nav) == 30, f"{method}_nav_30", checks)
        check(nav.pending_count.sum() == 0, f"{method}_pending_zero", checks)
        check(nav.fallback_count.sum() == 0, f"{method}_fallback_zero", checks)
        check(
            (skipped[["quantity", "commission", "sell_tax", "net_pnl"]] == 0).all().all(),
            f"{method}_skip_zero_quantity_and_cost",
            checks,
        )
        check(
            int(paired.loc[method, "skip_count"]) == len(skipped),
            f"{method}_skip_count_recomputed",
            checks,
        )
        check(
            int(paired.loc[method, "action_count"]) == len(executed),
            f"{method}_executed_count_recomputed",
            checks,
        )
        recomputed_return = float(nav.equity.iloc[-1] / 1_000_000.0 - 1.0)
        check(
            math.isclose(recomputed_return, float(paired.loc[method, "net_return"]), abs_tol=1e-12),
            f"{method}_net_return_recomputed",
            checks,
        )

    gates = pd.read_csv(OUT / "HISTORICAL_THRESHOLD_DIAGNOSTIC.csv")
    check(
        gates.baseline_admission_effect.eq("NONE_RETROSPECTIVE_DIAGNOSTIC_ONLY").all(),
        "gate_has_no_admission_effect",
        checks,
    )
    skip_gate = gates[gates.gate.eq("v3_skip_audit_integrity_violation_count")]
    check(len(skip_gate) == 1 and bool(skip_gate.iloc[0]["pass"]), "v3_skip_integrity_gate", checks)
    forbidden_names = {
        "events.jsonl",
        "latest.json",
        "latest_signal.json",
        "prospective_ledger.jsonl",
        "baseline_admission.json",
        "production_publish.json",
    }
    check(not forbidden_names.intersection(path.name for path in OUT.iterdir()), "no_forbidden_output_name", checks)

    return {
        "schema_version": "modelb.b19r2r.retrospective_historical_replay.validator.v1",
        "status": "PASS",
        "output": str(OUT.relative_to(ROOT)),
        "check_count": len(checks),
        "checks": checks,
        "historical_replay": True,
        "prospective_pit_anchor": False,
        "prospective_ledger_append": False,
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
            raise RuntimeError("refusing to overwrite validator result")
        RESULT.write_text(json.dumps(result, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        RESULT.chmod(0o600)
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
