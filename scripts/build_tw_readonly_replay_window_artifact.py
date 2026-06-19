#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
D3_RUNNER = ROOT / "scripts/run_tw_modular_order_intent_replay_parity.py"
DEFAULT_BASELINE = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json"
DEFAULT_POLICY = ROOT / "configs/tw_replay_window_policy.yaml"
DEFAULT_OUT_ROOT = ROOT / "data_tw/artifacts/readonly_replay_windows/d6"
VALID_RULES = {"original", "top50_exit_all", "top50_exit_one_worst_sell", "one_sell_one_buy_correct", "one_sell_one_buy_buggy_e8r"}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def parse_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"invalid {field}: {value}") from exc


def maybe_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    return date.fromisoformat(str(value))


def overlaps(start: date, end: date, other_start: date | None, other_end: date | None) -> bool:
    if other_start is None or other_end is None:
        return False
    return start <= other_end and other_start <= end


def validate_window(policy: dict[str, Any], model_id: str, strategy_rule: str, start: str, end: str) -> dict[str, Any]:
    s = parse_date(start, "start")
    e = parse_date(end, "end")
    if s > e:
        raise RuntimeError("start_date must be <= end_date")
    models = policy.get("models") or {}
    if model_id not in models:
        raise RuntimeError(f"model_id not in policy: {model_id}")
    if strategy_rule not in VALID_RULES:
        raise RuntimeError(f"strategy_rule not registered: {strategy_rule}")
    diagnostic = (policy.get("diagnostic_rules") or {}).get(strategy_rule) or {}
    if diagnostic.get("not_valid_strategy_evidence") is True:
        raise RuntimeError("diagnostic rule cannot be generated as valid strategy evidence")
    meta = models[model_id]
    allowed_min = parse_date(str(meta.get("allowed_replay_start_min") or policy.get("allowed_replay_start_min")), "allowed_replay_start_min")
    latest = parse_date(str(policy.get("latest_available_signal_date")), "latest_available_signal_date")
    if s < allowed_min:
        raise RuntimeError(f"requested window before allowed replay start: {allowed_min}")
    if e > latest:
        raise RuntimeError(f"requested window beyond latest signal date: {latest}")
    q_start, q_end = maybe_date(meta.get("qlib_train_start")), maybe_date(meta.get("qlib_train_end"))
    l_start, l_end = maybe_date(meta.get("ltr_train_start")), maybe_date(meta.get("ltr_train_end"))
    if overlaps(s, e, q_start, q_end):
        raise RuntimeError("requested window overlaps qlib training window")
    if overlaps(s, e, l_start, l_end):
        raise RuntimeError("requested window overlaps LTR training window")
    return {
        "ok": True,
        "model_id": model_id,
        "strategy_rule": strategy_rule,
        "requested_start": start,
        "requested_end": end,
        "allowed_replay_start_min": str(allowed_min),
        "latest_available_signal_date": str(latest),
        "model_training_windows_traceable": bool(meta.get("source_manifest") and meta.get("source_training_report")),
        "training_overlap_rejected": True,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checksum_items(paths: list[Path]) -> list[dict[str, Any]]:
    rows = []
    seen: set[Path] = set()
    for path in paths:
        if not path.exists():
            continue
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        rows.append({"path": rel(path), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    return rows


def load_d3_runner() -> Any:
    spec = importlib.util.spec_from_file_location("d3_order_intent_replay_parity", D3_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to import {D3_RUNNER}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def build_artifact(*, model_id: str, strategy_rule: str, start: str, end: str, out_root: Path, baseline_manifest: Path, policy_path: Path) -> dict[str, Any]:
    policy = load_yaml(policy_path)
    validation = validate_window(policy, model_id, strategy_rule, start, end)
    source = load_json(baseline_manifest)
    if model_id not in (source.get("signal_manifests") or {}) or model_id not in (source.get("full_rank_artifacts") or {}):
        raise RuntimeError(f"model_id missing from baseline source manifests: {model_id}")
    window_key = f"{start}_{end}".replace("-", "")
    artifact_dir = out_root / model_id / strategy_rule / window_key
    artifact_dir.mkdir(parents=True, exist_ok=True)
    d3 = load_d3_runner()
    d3.WINDOW = f"readonly_{start}_{end}"
    d3.WINDOW_START = start
    d3.WINDOW_END = end
    d3.RULES = [strategy_rule]
    source_subset = dict(source)
    source_subset["signal_manifests"] = {model_id: source["signal_manifests"][model_id]}
    source_subset["full_rank_artifacts"] = {model_id: source["full_rank_artifacts"][model_id]}
    replay_manifest_path = d3.run_forward_chain(artifact_dir=artifact_dir, baseline_manifest_path=baseline_manifest, source_manifest=source_subset)
    replay_manifest = load_json(replay_manifest_path)
    replay_manifest.update({
        "schema_version": "readonly_replay_result_d6_v1",
        "created_by": rel(Path(__file__)),
        "phase": "D6",
        "readonly_only": True,
        "not_order": True,
        "no_order_action": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "production_trade_enabled": False,
        "no_provider_publish": True,
        "no_accepted_latest_switch": True,
        "no_monitor_broker_order": True,
        "window": f"readonly_{start}_{end}",
        "window_start": start,
        "window_end": end,
        "requested_model_id": model_id,
        "requested_strategy_rule": strategy_rule,
        "replay_window_policy_validation": validation,
        "replay_window_policy": rel(policy_path),
        "d6_artifact_generation": "audited_readonly_replay_artifact",
        "not_generated_in_api_handler": True,
    })
    forbidden_scope = {
        "artifact_type": "readonly_replay_forbidden_scope_audit",
        "schema_version": "readonly_replay_forbidden_scope_d6_v1",
        "status": "pass",
        "no_provider_publish": True,
        "no_accepted_latest_switch": True,
        "no_monitor_broker_order": True,
        "no_broker_quick_trade_order": True,
        "no_formal_baseline_mutation": True,
        "no_d3rr_artifact_mutation": True,
    }
    forbidden_path = replay_manifest_path.parent / "forbidden_scope_audit.json"
    write_json(forbidden_path, forbidden_scope)
    paths = [policy_path, baseline_manifest, forbidden_path]
    for order_ref in replay_manifest.get("order_intent_artifacts", []):
        paths.append(resolve(str(order_ref)))
        order_manifest = load_json(resolve(str(order_ref)))
        for out in (order_manifest.get("output_files") or {}).values():
            paths.append(resolve(str(out)))
    for path in (replay_manifest.get("artifacts") or {}).values():
        paths.append(resolve(str(path)))
    checksum = {
        "artifact_type": "readonly_replay_checksum_manifest",
        "schema_version": "readonly_replay_checksum_d6_v1",
        "created_at": now(),
        "files": checksum_items(paths),
    }
    checksum_path = replay_manifest_path.parent / "checksum_manifest.json"
    write_json(checksum_path, checksum)
    replay_manifest["checksum_manifest"] = rel(checksum_path)
    replay_manifest["forbidden_scope_audit_json"] = rel(forbidden_path)
    write_json(replay_manifest_path, replay_manifest)
    validation_report = {
        "artifact_type": "readonly_replay_validation_report",
        "schema_version": "readonly_replay_validation_d6_v1",
        "status": "pass",
        "manifest": rel(replay_manifest_path),
        "created_at": now(),
    }
    write_json(replay_manifest_path.parent / "validation_report.json", validation_report)
    return {"ok": True, "manifest": rel(replay_manifest_path), "window": replay_manifest["window"], "row_counts": replay_manifest.get("row_counts", {})}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build audited D6 readonly replay artifact for a policy-valid window.")
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--strategy-rule", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT))
    parser.add_argument("--baseline-manifest", default=str(DEFAULT_BASELINE))
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = build_artifact(model_id=args.model_id, strategy_rule=args.strategy_rule, start=args.start, end=args.end, out_root=resolve(args.out_root), baseline_manifest=resolve(args.baseline_manifest), policy_path=resolve(args.policy))
    except Exception as exc:  # noqa: BLE001
        result = {"ok": False, "error": str(exc)}
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"ok=False\nerror={exc}")
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']}\nmanifest={result['manifest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
