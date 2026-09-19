#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "data_tw/experiments/policy_action_model_research/pa1_qlib_only_supervised_utility"
GOLDEN_ROOT = ROOT / "data_tw/golden_samples/policy_action_model_research"
FROZEN_SIGNAL = "data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json"

FORBIDDEN = [
    "future_return",
    "future_excess_return",
    "forward_return",
    "realized_pnl",
    "realized_return",
    "replay_return",
    "next_open",
    "next_close",
    "execution_price",
    "execution_quantity",
    "quantity_to_buy",
    "quantity_to_sell",
    "shares",
    "lots",
    "target_position",
    "target_weight",
    "allocation_weight",
    "broker_order_id",
    "quick_trade",
    "provider_publish_status",
    "accepted_latest_status",
]

POLICY_FORBIDDEN_OUTPUT = [
    "execution_price",
    "execution_quantity",
    "shares",
    "lots",
    "target_position",
    "target_weight",
    "cash",
    "nav",
    "realized_pnl",
    "replay_return",
    "broker_order_id",
    "quick_trade",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except Exception:
        return str(path)


def resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def check(code: str, ok: bool, details: str = "", path: str = "") -> dict[str, Any]:
    return {"code": code, "ok": bool(ok), "status": "pass" if ok else "fail", "details": details, "path": path}


def fields_of(path: Path) -> list[str]:
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        return next(reader, [])


def validate_dataset(manifest_path: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    manifest = load_json(manifest_path)
    outputs = manifest.get("output_files", {})
    required = ["samples", "schema", "feature_audit", "label_audit", "split_audit", "forbidden_field_audit"]
    checks.append(check("dataset_artifact_type", manifest.get("artifact_type") == "PolicyTrainingDatasetArtifact", str(manifest.get("artifact_type")), rel(manifest_path)))
    checks.append(check("dataset_source_signal_frozen_qlib", manifest.get("source_signal_artifact") == FROZEN_SIGNAL, str(manifest.get("source_signal_artifact")), rel(manifest_path)))
    for name in required:
        path = resolve(str(outputs.get(name, "")))
        checks.append(check(f"dataset_required_file_{name}", path.exists(), rel(path), rel(manifest_path)))
    if not checks[-1]["ok"]:
        return checks
    samples_path = resolve(str(outputs.get("samples", "")))
    sample_fields = fields_of(samples_path)
    schema = load_json(resolve(str(outputs.get("schema", ""))))
    inference = set(schema.get("inference_feature_fields", []))
    label_fields = [field for field in sample_fields if field.startswith("label_utility_") or field in {"label_after_fee_tax_return", "label_drawdown_penalty"}]
    checks.append(check("dataset_has_labels_for_all_splits", bool(label_fields), "|".join(label_fields), rel(samples_path)))
    checks.append(check("dataset_label_not_in_inference", not any(field in inference for field in label_fields), "labels excluded from inference_feature_fields", rel(samples_path)))
    forbidden_hits = [field for field in sample_fields if any(token in field for token in FORBIDDEN) and not field.startswith("label_")]
    checks.append(check("dataset_no_forbidden_inference_fields", not forbidden_hits, "|".join(forbidden_hits), rel(samples_path)))
    rows = read_csv(samples_path)
    sample_ids = [row.get("sample_id", "") for row in rows]
    checks.append(check("dataset_sample_id_unique", len(sample_ids) == len(set(sample_ids)), f"rows={len(sample_ids)} unique={len(set(sample_ids))}", rel(samples_path)))
    split_dates = {"train": ("2023-01-03", "2024-12-31"), "validation": ("2025-01-01", "2025-12-31"), "strict_test": ("2026-01-01", "2026-05-07")}
    for split, (start, end) in split_dates.items():
        bad = [row for row in rows if row.get("split") == split and not (start <= row.get("signal_date", "") <= end)]
        checks.append(check(f"dataset_split_boundary_{split}", not bad, f"bad_count={len(bad)}", rel(samples_path)))
    audit_rows = read_csv(resolve(str(outputs.get("forbidden_field_audit", ""))))
    failed = [row for row in audit_rows if row.get("status") == "fail"]
    checks.append(check("dataset_forbidden_audit_pass", not failed, f"failed={len(failed)}", rel(outputs.get("forbidden_field_audit", ""))))
    return checks


def validate_decision(manifest_path: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    manifest = load_json(manifest_path)
    outputs = manifest.get("output_files", {})
    required = ["policy_decisions", "schema", "policy_input_audit", "forbidden_output_audit"]
    checks.append(check("decision_artifact_type", manifest.get("artifact_type") == "PolicyDecisionArtifact", str(manifest.get("artifact_type")), rel(manifest_path)))
    checks.append(check("decision_source_signal_frozen_qlib", manifest.get("source_signal_artifact") == FROZEN_SIGNAL, str(manifest.get("source_signal_artifact")), rel(manifest_path)))
    checks.append(check("decision_readonly", manifest.get("readonly_only") is True and manifest.get("production_allowed") is False, "readonly_only true and production_allowed false", rel(manifest_path)))
    for name in required:
        path = resolve(str(outputs.get(name, "")))
        checks.append(check(f"decision_required_file_{name}", path.exists(), rel(path), rel(manifest_path)))
    decisions_path = resolve(str(outputs.get("policy_decisions", "")))
    if decisions_path.exists():
        fields = fields_of(decisions_path)
        allowed_safety_flags = {"not_target_position", "not_order", "not_investment_advice"}
        forbidden = [field for field in fields if field not in allowed_safety_flags and (field in POLICY_FORBIDDEN_OUTPUT or any(token in field for token in ["target_", "broker", "quick_trade", "execution_quantity"]))]
        checks.append(check("decision_no_order_or_target_fields", not forbidden, "|".join(forbidden), rel(decisions_path)))
        rows = read_csv(decisions_path)
        allowed = {"allow_buy", "block_buy", "allow_sell", "block_sell", "veto_buy", "veto_sell"}
        bad_actions = [row.get("policy_action", "") for row in rows if row.get("policy_action", "") not in allowed]
        checks.append(check("decision_action_domain", not bad_actions, "|".join(sorted(set(bad_actions))), rel(decisions_path)))
        label_fields = [field for field in fields if field.startswith("label_")]
        checks.append(check("decision_no_label_fields", not label_fields, "|".join(label_fields), rel(decisions_path)))
    audit_path = resolve(str(outputs.get("forbidden_output_audit", "")))
    if audit_path.exists():
        failed = [row for row in read_csv(audit_path) if row.get("status") == "fail"]
        checks.append(check("decision_forbidden_output_audit_pass", not failed, f"failed={len(failed)}", rel(audit_path)))
    return checks


def validate_evaluation(manifest_path: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    manifest = load_json(manifest_path)
    outputs = manifest.get("output_files", {})
    checks.append(check("evaluation_artifact_type", manifest.get("artifact_type") == "PolicyEvaluationArtifact", str(manifest.get("artifact_type")), rel(manifest_path)))
    checks.append(check("evaluation_strict_test_not_selection", manifest.get("strict_test_used_for_selection") is False, str(manifest.get("strict_test_used_for_selection")), rel(manifest_path)))
    for name in ["metrics_by_split", "baseline_comparison", "threshold_selection_audit", "reward_ablation_audit", "failure_mode_audit", "forbidden_input_output_audit"]:
        path = resolve(str(outputs.get(name, "")))
        checks.append(check(f"evaluation_required_file_{name}", path.exists(), rel(path), rel(manifest_path)))
    baseline_path = resolve(str(outputs.get("baseline_comparison", "")))
    if baseline_path.exists():
        rows = read_csv(baseline_path)
        splits = {row.get("split") for row in rows}
        checks.append(check("evaluation_baseline_comparison_all_splits", {"train", "validation", "strict_test"}.issubset(splits), "|".join(sorted(splits)), rel(baseline_path)))
    threshold_path = resolve(str(outputs.get("threshold_selection_audit", "")))
    if threshold_path.exists():
        rows = read_csv(threshold_path)
        bad = [row for row in rows if str(row.get("strict_test_used", "")).lower() not in {"false", "0"}]
        checks.append(check("evaluation_no_test_tuning", not bad, f"bad={len(bad)}", rel(threshold_path)))
    forbidden_path = resolve(str(outputs.get("forbidden_input_output_audit", "")))
    if forbidden_path.exists():
        failed = [row for row in read_csv(forbidden_path) if row.get("status") == "fail"]
        checks.append(check("evaluation_forbidden_audit_pass", not failed, f"failed={len(failed)}", rel(forbidden_path)))
    return checks


def validate_replay(manifest_path: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    manifest = load_json(manifest_path)
    outputs = manifest.get("output_files", {})
    checks.append(check("replay_artifact_type", manifest.get("artifact_type") == "ReplayResultArtifact", str(manifest.get("artifact_type")), rel(manifest_path)))
    checks.append(check("replay_readonly", manifest.get("readonly_only") is True and manifest.get("production_allowed") is False, "readonly replay only", rel(manifest_path)))
    for name in ["summary", "actions", "daily_nav", "position_snapshots", "coverage_audit", "position_integrity_audit", "forbidden_field_audit", "execution_audit", "forbidden_action_audit"]:
        path = resolve(str(outputs.get(name, "")))
        checks.append(check(f"replay_required_file_{name}", path.exists(), rel(path), rel(manifest_path)))
    forbidden_path = resolve(str(outputs.get("forbidden_field_audit", "")))
    if forbidden_path.exists():
        failed = [row for row in read_csv(forbidden_path) if row.get("status") == "fail"]
        checks.append(check("replay_forbidden_field_audit_pass", not failed, f"failed={len(failed)}", rel(forbidden_path)))
    return checks


def validate_manifest_tree(root: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    checks.extend(validate_dataset(root / "dataset/manifest.json"))
    checks.extend(validate_decision(root / "policy_decisions/manifest.json"))
    checks.extend(validate_evaluation(root / "evaluation/manifest.json"))
    for split in ["train", "validation", "strict_test"]:
        for kind in ["baseline", "policy"]:
            checks.extend(validate_replay(root / "replays" / kind / split / "manifest.json"))
    registry = ROOT / "configs/policy_action_model_research_registry.yaml"
    checks.append(check("experiment_registry_exists", registry.exists(), rel(registry), rel(registry)))
    return checks


def validate_golden() -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    cases = {
        "dataset_positive_minimal": True,
        "decision_positive_minimal": True,
        "evaluation_positive_minimal": True,
        "dataset_negative_future_return_feature": False,
        "decision_negative_target_weight": False,
        "evaluation_negative_test_threshold_selection": False,
    }
    for case, should_pass in cases.items():
        path = GOLDEN_ROOT / case / "manifest.json"
        checks.append(check(f"golden_exists_{case}", path.exists(), rel(path), rel(path)))
        if not path.exists():
            continue
        artifact_type = load_json(path).get("artifact_type")
        if artifact_type == "PolicyTrainingDatasetArtifact":
            result = validate_dataset(path)
        elif artifact_type == "PolicyDecisionArtifact":
            result = validate_decision(path)
        elif artifact_type == "PolicyEvaluationArtifact":
            result = validate_evaluation(path)
        else:
            result = [check("golden_unknown_artifact_type", False, str(artifact_type), rel(path))]
        passed = all(item["ok"] for item in result)
        checks.append(check(f"golden_expected_{case}", passed is should_pass, f"passed={passed} expected={should_pass}", rel(path)))
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Policy / Action Model PA1 artifacts.")
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--dataset-manifest", default="")
    parser.add_argument("--decision-manifest", default="")
    parser.add_argument("--evaluation-manifest", default="")
    parser.add_argument("--replay-manifest", default="")
    parser.add_argument("--run-golden", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    checks: list[dict[str, Any]] = []
    if args.dataset_manifest:
        checks.extend(validate_dataset(resolve(args.dataset_manifest)))
    if args.decision_manifest:
        checks.extend(validate_decision(resolve(args.decision_manifest)))
    if args.evaluation_manifest:
        checks.extend(validate_evaluation(resolve(args.evaluation_manifest)))
    if args.replay_manifest:
        checks.extend(validate_replay(resolve(args.replay_manifest)))
    if not any([args.dataset_manifest, args.decision_manifest, args.evaluation_manifest, args.replay_manifest]):
        checks.extend(validate_manifest_tree(resolve(args.root)))
    if args.run_golden:
        checks.extend(validate_golden())
    ok = all(item["ok"] for item in checks)
    payload = {
        "ok": ok,
        "status": "PASS_POLICY_ACTION_ARTIFACT_VALIDATION" if ok else "FAIL_POLICY_ACTION_ARTIFACT_VALIDATION",
        "check_count": len(checks),
        "failed_count": sum(1 for item in checks if not item["ok"]),
        "checks": checks,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"ok={str(ok).lower()}")
        print(f"status={payload['status']}")
        for item in checks:
            if not item["ok"]:
                print(f"FAIL {item['code']} {item['details']} {item['path']}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
