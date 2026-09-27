#!/usr/bin/env python3
"""Run the consumed B19R2R 30-day window as an isolated historical replay."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import modelb_b19r2r_prospective_confirmation_v3_template as replay_v3
import run_modelb_b19r2r_sealed_confirmation_v2 as v2


ROOT = Path(__file__).resolve().parents[1]
OUT = (
    ROOT
    / "data_tw/experiments/project_runtime_convergence"
    / "modelb_b19r2r_retrospective_historical_paired_replay_20260918"
)
SCOPE = "retrospective_historical_replay_30_day"
RUNNER = Path(__file__)
VALIDATOR = ROOT / "scripts/validate_modelb_b19r2r_retrospective_historical_paired_replay.py"
V3_TEMPLATE = ROOT / "scripts/modelb_b19r2r_prospective_confirmation_v3_template.py"
V3_FREEZE = v2.RUN / "B19R2R_PROSPECTIVE_CONFIRMATION_V3_REPAIR_FREEZE.json"

PROTECTED = (
    ROOT / "configs/active_baseline_descriptor.yaml",
    ROOT / "configs/tw_modular_registry.yaml",
    ROOT / "configs/tw_product_artifact_registry.yaml",
    ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
    ROOT / "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron",
    ROOT / "data_tw/experiments/modelb_b19r2r_v5_prospective_accumulator",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint(path: Path) -> dict[str, Any]:
    if path.is_file():
        return {
            "path": relative(path),
            "kind": "file",
            "exists": True,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
    if path.is_dir():
        files = []
        for child in sorted(item for item in path.rglob("*") if item.is_file()):
            files.append({
                "path": relative(child),
                "bytes": child.stat().st_size,
                "sha256": sha256(child),
            })
        canonical = json.dumps(files, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return {
            "path": relative(path),
            "kind": "directory",
            "exists": True,
            "file_count": len(files),
            "tree_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            "files": files,
        }
    return {"path": relative(path), "kind": "absent", "exists": False}


def protected_fingerprints() -> dict[str, dict[str, Any]]:
    return {relative(path): fingerprint(path) for path in PROTECTED}


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)


def validate_frozen_inputs() -> dict[str, Any]:
    implementation = v2.validate_authorization(require_auth=False)
    for name, item in implementation["source_bindings"].items():
        path = ROOT / item["path"]
        if not path.is_file() or path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            raise RuntimeError(f"historical source binding drift: {name}")
    repair = json.loads(V3_FREEZE.read_text(encoding="utf-8"))
    if repair.get("status") != "FROZEN_TEMPLATE_ONLY_NON_EXECUTABLE_NO_REAL_DATA_BINDING":
        raise RuntimeError("V3 affordability repair freeze status drift")
    template_binding = repair["bindings"]["v3_replay_core_template"]
    if template_binding["path"] != relative(V3_TEMPLATE) or template_binding["sha256"] != sha256(V3_TEMPLATE):
        raise RuntimeError("V3 affordability template binding drift")
    return implementation


def historical_gate_table(
    signals: pd.DataFrame,
    paired: pd.DataFrame,
    nav_by_method: dict[str, pd.DataFrame],
    rank_summary: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    protocol = json.loads(v2.PROTOCOL.read_text(encoding="utf-8"))
    compatibility = paired.copy()
    compatibility["all_actions_executed"] = compatibility[
        "all_emitted_positive_quantity_actions_must_execute"
    ]
    gates, support = v2.build_gate_table(
        protocol,
        compatibility,
        nav_by_method,
        rank_summary,
        signals,
    )
    gates["scope"] = SCOPE.upper()
    gates["baseline_admission_effect"] = "NONE_RETROSPECTIVE_DIAGNOSTIC_ONLY"
    skip_violations = int(paired.skip_audit_integrity_violation_count.sum())
    skip_gate = pd.DataFrame([{
        "gate": "v3_skip_audit_integrity_violation_count",
        "original_gate": "V3_AFFORDABILITY_ENGINEERING_AUDIT",
        "scope": SCOPE.upper(),
        "measured_value": skip_violations,
        "operator": "==",
        "threshold": 0,
        "status": "PASS" if skip_violations == 0 else "FAIL",
        "pass": skip_violations == 0,
        "reason": "resolved skips are zero-quantity and zero-cost" if skip_violations == 0 else "invalid skip row",
        "baseline_admission_effect": "NONE_RETROSPECTIVE_DIAGNOSTIC_ONLY",
    }])
    gates = pd.concat([gates, skip_gate], ignore_index=True)
    for name in ("paired_daily", "monthly"):
        support[name]["scope"] = SCOPE
    support["joint"].update({
        "scope": SCOPE.upper(),
        "historical_threshold_diagnostic_only": True,
        "prospective_confirmation_verdict": False,
        "baseline_admission_decided": False,
        "baseline_onboarding_review_eligible": False,
        "production_allowed": False,
        "v3_skip_audit_integrity_violation_count": skip_violations,
    })
    return gates, support


def build_report(manifest: dict[str, Any], paired: pd.DataFrame, gates: pd.DataFrame) -> str:
    metrics = paired.set_index("method")
    a = metrics.loc["A_ONLY"]
    b = metrics.loc["A_PLUS_B"]
    frozen_joint = gates[gates.gate.eq("all_gates_jointly_required")].iloc[0]
    return f"""# B19R2R retrospective historical paired replay

## Classification

- Window: 2026-07-22 through 2026-09-01, 30 trading days.
- Evidence class: retrospective historical replay over already consumed data.
- This is not an untouched or prospective PIT anchor.
- It cannot append a prospective ledger or admit Model B to baseline or production.

## Frozen lineage

- Model A: the same deterministic exact-50 membership and canonical full-rank scores.
- Model B: frozen final B19R2R LightGBM candidate 14, 78 features, 120 trees.
- Replay: reviewed V3 affordability skip semantics; no lower-ranked substitution.
- No retraining, tuning, feature, label, model-weight, strategy, cost, or threshold change.

## Result

| Track | Net return | Max drawdown | Executed buys | Executed sells | Affordability skips |
| --- | ---: | ---: | ---: | ---: | ---: |
| A only | {a.net_return:.10f} | {a.max_drawdown:.10f} | {int(a.buy_count)} | {int(a.sell_count)} | {int(a.skip_count)} |
| A + B | {b.net_return:.10f} | {b.max_drawdown:.10f} | {int(b.buy_count)} | {int(b.sell_count)} | {int(b.skip_count)} |

- Historical after-cost delta B minus A: {b.net_return - a.net_return:.10f}.
- Frozen-threshold historical diagnostic: {frozen_joint.status}; it has no admission effect.
- Protected fingerprints unchanged: {str(manifest['protected_boundary']['unchanged']).lower()}.

## Safety disposition

- historical_replay=true
- prospective_pit_anchor=false
- prospective_ledger_append=false
- latest_or_provider_write=false
- baseline_or_production_change=false
- production_allowed=false

The next legal market window is reserved for the real untouched PIT anchor.
"""


def run() -> dict[str, Any]:
    if OUT.exists():
        raise RuntimeError(f"refusing to overwrite historical replay output: {relative(OUT)}")
    if not VALIDATOR.is_file():
        raise RuntimeError(f"missing historical replay validator: {relative(VALIDATOR)}")
    os.umask(0o077)
    OUT.mkdir(parents=True, mode=0o700, exist_ok=False)
    try:
        protected_before = protected_fingerprints()
        write_json(OUT / "PROTECTED_FINGERPRINT_BEFORE.json", protected_before)
        implementation = validate_frozen_inputs()
        freeze = {
            "schema_version": "modelb.b19r2r.retrospective_historical_replay.freeze.v1",
            "status": "FROZEN_BEFORE_HISTORICAL_SOURCE_READ",
            "created_at": utc_now(),
            "run_id": OUT.name,
            "evidence_class": "RETROSPECTIVE_HISTORICAL_REPLAY_ALREADY_CONSUMED_INPUTS",
            "date_start": min(v2.CONFIRMATION_DATES),
            "date_end": max(v2.CONFIRMATION_DATES),
            "date_count": len(v2.CONFIRMATION_DATES),
            "historical_replay": True,
            "prospective_pit_anchor": False,
            "untouched_claim": False,
            "model_a_exact50_unchanged": True,
            "model_b_final_frozen": True,
            "model_b_sha256": sha256(v2.MODEL_B),
            "feature_count": 78,
            "v3_affordability_skip_semantics": True,
            "no_lower_rank_substitution_after_skip": True,
            "no_training_or_tuning": True,
            "no_feature_label_weight_or_threshold_change": True,
            "prospective_ledger_append": False,
            "latest_or_provider_write": False,
            "baseline_or_production_change": False,
            "production_allowed": False,
            "runner": {"path": relative(RUNNER), "sha256": sha256(RUNNER)},
            "validator": {"path": relative(VALIDATOR), "sha256": sha256(VALIDATOR)},
            "v3_template": {"path": relative(V3_TEMPLATE), "sha256": sha256(V3_TEMPLATE)},
            "v3_repair_freeze": {"path": relative(V3_FREEZE), "sha256": sha256(V3_FREEZE)},
        }
        write_json(OUT / "RUN_FREEZE.json", freeze)

        signals, predictions, features, full_ranks, model_a_parity = v2.load_and_score_confirmation()
        rank_daily = v2.rank_metrics(signals)
        rank_daily["scope"] = SCOPE
        rank_summary = v2.summarize_rank_metrics(rank_daily)
        rank_summary["scope"] = SCOPE
        grid = v2.normalize(pd.read_parquet(v2.GRID))
        if (
            len(grid) != 4500
            or grid.date.nunique() != 30
            or grid.duplicated(v2.KEY).any()
            or grid.groupby("date").size().ne(150).any()
            or set(grid.date) != set(v2.CONFIRMATION_DATES)
            or set(grid.role) != {"SEALED_CONFIRMATION"}
            or not np.isfinite(grid[["next_open", "next_close"]].to_numpy(float)).all()
        ):
            raise RuntimeError("historical execution grid shape or finite-price check failed")

        diagnostic = signals[v2.KEY + [
            "model_a_raw_score",
            "model_b_final_raw_score",
            "a_only_score_rank",
            "a_plus_b_score_rank",
            v2.CONT,
            v2.REL,
        ]].copy()
        results: list[dict[str, Any]] = []
        nav_by_method: dict[str, pd.DataFrame] = {}
        artifacts: dict[str, pd.DataFrame] = {
            "FINAL_MODEL_B_PREDICTIONS.csv": predictions,
            "HISTORICAL_SCORE_OUTCOME_DIAGNOSTIC.csv": diagnostic,
            "RANK_METRICS_DAILY.csv": rank_daily,
            "RANK_METRICS_SUMMARY.csv": rank_summary,
        }
        for method, score in (("A_ONLY", "a_only_buy_score"), ("A_PLUS_B", "a_plus_b_buy_score")):
            actions, nav, price_audit, contribution = replay_v3.replay(
                signals,
                grid,
                full_ranks,
                score,
                method,
                SCOPE,
            )
            artifacts[f"{method}_ACTIONS.csv"] = actions
            artifacts[f"{method}_DAILY_NAV.csv"] = nav
            artifacts[f"{method}_PRICE_AUDIT.csv"] = price_audit
            artifacts[f"{method}_CONTRIBUTION.csv"] = contribution
            results.append(replay_v3.summarize(SCOPE, method, actions, nav, contribution))
            nav_by_method[method] = nav

        paired = pd.DataFrame(results).sort_values("method", kind="mergesort").reset_index(drop=True)
        if len(paired) != 2 or paired.duplicated(["scope", "method"]).any():
            raise RuntimeError("historical paired metrics identity failed")
        artifacts["PAIRED_METRICS.csv"] = paired
        gates, support = historical_gate_table(signals, paired, nav_by_method, rank_summary)
        artifacts.update({
            "HISTORICAL_THRESHOLD_DIAGNOSTIC.csv": gates,
            "PAIRED_DAILY_RETURNS.csv": support["paired_daily"],
            "MONTHLY_DIAGNOSTICS.csv": support["monthly"],
            "BOOTSTRAP_MEANS.csv": support["bootstrap_means"],
        })
        for name, frame in artifacts.items():
            path = OUT / name
            frame.to_csv(path, index=False)
            path.chmod(0o600)

        protected_after = protected_fingerprints()
        write_json(OUT / "PROTECTED_FINGERPRINT_AFTER.json", protected_after)
        if protected_before != protected_after:
            raise RuntimeError("protected registry/latest/baseline/ledger boundary drifted")

        source_bindings = {
            name: {
                "path": item["path"],
                "sha256": item["sha256"],
                "bytes": item["bytes"],
                "historical_input": True,
            }
            for name, item in implementation["source_bindings"].items()
        }
        manifest: dict[str, Any] = {
            "schema_version": "modelb.b19r2r.retrospective_historical_paired_replay.v1",
            "status": "PASS_RETROSPECTIVE_HISTORICAL_REPLAY_DIAGNOSTIC_ONLY",
            "created_at": utc_now(),
            "run_id": OUT.name,
            "evidence_class": "RETROSPECTIVE_HISTORICAL_REPLAY_ALREADY_CONSUMED_INPUTS",
            "date_start": min(v2.CONFIRMATION_DATES),
            "date_end": max(v2.CONFIRMATION_DATES),
            "date_count": 30,
            "exact50_rows": len(diagnostic),
            "feature_count": len(features),
            "historical_replay": True,
            "prospective_pit_anchor": False,
            "untouched_claim": False,
            "input_was_previously_read_or_consumed": True,
            "prior_v2_attempt_retried_or_modified": False,
            "v3_affordability_skip_semantics": True,
            "source_bindings": source_bindings,
            "model_a_keyset_source_parity": model_a_parity,
            "historical_threshold_diagnostic": support["joint"],
            "safety": {
                "training_performed": False,
                "tuning_performed": False,
                "feature_label_model_weight_or_threshold_changed": False,
                "prospective_ledger_append": False,
                "latest_or_provider_write": False,
                "baseline_or_production_change": False,
                "production_allowed": False,
            },
            "protected_boundary": {
                "before_path": relative(OUT / "PROTECTED_FINGERPRINT_BEFORE.json"),
                "after_path": relative(OUT / "PROTECTED_FINGERPRINT_AFTER.json"),
                "unchanged": True,
            },
        }
        report = build_report(manifest, paired, gates)
        report_path = OUT / "EXECUTION_REPORT.md"
        report_path.write_text(report, encoding="utf-8")
        report_path.chmod(0o600)
        output_artifacts: dict[str, Any] = {}
        for path in sorted(item for item in OUT.iterdir() if item.is_file()):
            if path.name == "MANIFEST.json":
                continue
            rows = None
            if path.suffix == ".csv":
                rows = sum(1 for _ in path.open("r", encoding="utf-8")) - 1
            output_artifacts[path.name] = {
                "path": relative(path),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
                "rows": rows,
            }
        manifest["artifacts"] = output_artifacts
        write_json(OUT / "MANIFEST.json", manifest)
        return manifest
    except Exception:
        # Preserve the write-once footprint and any evidence already emitted.
        failure = OUT / "EXECUTION_FAILURE.json"
        if not failure.exists():
            write_json(failure, {"status": "FAILED_WRITE_ONCE_NO_RETRY", "failed_at": utc_now()})
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        raise SystemExit("Select --execute")
    manifest = run()
    print(json.dumps({
        "status": manifest["status"],
        "output": relative(OUT),
        "historical_replay": manifest["historical_replay"],
        "prospective_pit_anchor": manifest["prospective_pit_anchor"],
        "protected_unchanged": manifest["protected_boundary"]["unchanged"],
    }, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
