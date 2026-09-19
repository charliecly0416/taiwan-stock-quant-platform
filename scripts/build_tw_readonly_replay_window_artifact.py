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

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
D3_RUNNER = ROOT / "scripts/run_tw_modular_order_intent_replay_parity.py"
DEFAULT_BASELINE = ROOT / (
    "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/"
    "modular_replay_matrix/formal_replay_manifest.json"
)
DEFAULT_POLICY = ROOT / "configs/tw_replay_window_policy.yaml"
DEFAULT_REGISTRY = ROOT / "configs/tw_modular_registry.yaml"
DEFAULT_BASELINE_DESCRIPTOR = ROOT / "configs/active_baseline_descriptor.yaml"
DEFAULT_PRICE_STORE = ROOT / (
    "data_tw/canonical/price_store/tw_equity_daily/"
    "dng2_r_price_market_calendar_20260625/manifest.json"
)
DEFAULT_OUT_ROOT = ROOT / (
    "data_tw/artifacts/readonly_replay_windows/wf2_candidate_model_a"
)
VALID_RULES = {
    "original",
    "top50_exit_all",
    "top50_exit_one_worst_sell",
    "one_sell_one_buy_correct",
    "one_sell_one_buy_buggy_e8r",
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return (
        candidate.resolve() if candidate.is_absolute() else (ROOT / candidate).resolve()
    )


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return payload


def load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"YAML object required: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        + "\n",
        encoding="utf-8",
    )


def parse_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise RuntimeError(f"invalid {field}: {value}") from exc


def maybe_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    return parse_date(str(value), "training window")


def overlaps(
    start: date,
    end: date,
    other_start: date | None,
    other_end: date | None,
) -> bool:
    if other_start is None or other_end is None:
        return False
    return start <= other_end and other_start <= end


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_window(
    policy: dict[str, Any],
    model_id: str,
    strategy_rule: str,
    start: str,
    end: str,
) -> dict[str, Any]:
    start_date = parse_date(start, "start")
    end_date = parse_date(end, "end")
    if start_date > end_date:
        raise RuntimeError("start_date must be <= end_date")
    models = policy.get("models")
    if not isinstance(models, dict) or model_id not in models:
        raise RuntimeError(f"model_id not in policy: {model_id}")
    if strategy_rule not in VALID_RULES:
        raise RuntimeError(f"strategy_rule not registered: {strategy_rule}")
    diagnostic = (policy.get("diagnostic_rules") or {}).get(strategy_rule) or {}
    if diagnostic.get("not_valid_strategy_evidence") is True:
        raise RuntimeError("diagnostic rule cannot be valid strategy evidence")
    meta = models[model_id]
    allowed_min = parse_date(
        str(meta.get("allowed_replay_start_min") or policy["allowed_replay_start_min"]),
        "allowed_replay_start_min",
    )
    latest = parse_date(
        str(policy.get("latest_available_signal_date")),
        "latest_available_signal_date",
    )
    if start_date < allowed_min:
        raise RuntimeError(
            f"requested window before allowed replay start: {allowed_min}"
        )
    if end_date > latest:
        raise RuntimeError(f"requested window beyond latest signal date: {latest}")
    qlib_start = maybe_date(meta.get("qlib_train_start"))
    qlib_end = maybe_date(meta.get("qlib_train_end"))
    ltr_start = maybe_date(meta.get("ltr_train_start"))
    ltr_end = maybe_date(meta.get("ltr_train_end"))
    if overlaps(start_date, end_date, qlib_start, qlib_end):
        raise RuntimeError("requested window overlaps qlib training window")
    if overlaps(start_date, end_date, ltr_start, ltr_end):
        raise RuntimeError("requested window overlaps LTR training window")
    if not meta.get("source_manifest") or not meta.get("source_training_report"):
        raise RuntimeError("model training lineage is incomplete")
    return {
        "ok": True,
        "model_id": model_id,
        "strategy_rule": strategy_rule,
        "requested_start": start,
        "requested_end": end,
        "allowed_replay_start_min": str(allowed_min),
        "latest_available_signal_date": str(latest),
        "model_training_windows_traceable": True,
        "training_overlap_rejected": True,
        "source_manifest": str(meta["source_manifest"]),
        "source_training_report": str(meta["source_training_report"]),
        "qlib_train_start": str(meta.get("qlib_train_start") or ""),
        "qlib_train_end": str(meta.get("qlib_train_end") or ""),
        "ltr_train_start": str(meta.get("ltr_train_start") or ""),
        "ltr_train_end": str(meta.get("ltr_train_end") or ""),
    }


def resolve_canonical_source(
    *,
    model_id: str,
    source: dict[str, Any],
    policy: dict[str, Any],
    registry: dict[str, Any],
    baseline_descriptor: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[Path]]:
    production_models = (registry.get("production_models") or {}).get(
        "production_selectable"
    ) or {}
    canonical = production_models.get(model_id)
    if not isinstance(canonical, dict):
        raise RuntimeError("canonical model is not production-selectable in registry")
    active_model = (baseline_descriptor.get("active_baseline") or {}).get(
        "model_a"
    ) or {}
    if active_model.get("model_id") != model_id:
        raise RuntimeError("canonical model does not match active baseline descriptor")
    policy_model = (policy.get("models") or {}).get(model_id) or {}
    training_manifest_ref = str(policy_model.get("source_manifest") or "")
    if (
        not training_manifest_ref
        or canonical.get("source_manifest") != training_manifest_ref
    ):
        raise RuntimeError(
            "canonical registry and replay policy training lineage mismatch"
        )
    training_manifest_path = resolve(training_manifest_ref)
    training_manifest = load_json(training_manifest_path)
    model_path = resolve(str(training_manifest.get("model_path") or ""))
    if (
        rel(model_path) != str(active_model.get("artifact_path"))
        or not model_path.is_file()
        or sha256_file(model_path) != active_model.get("artifact_sha256")
    ):
        raise RuntimeError("canonical frozen model identity does not match E1 lineage")

    signal_manifests = source.get("signal_manifests") or {}
    full_rank_artifacts = source.get("full_rank_artifacts") or {}
    if model_id in signal_manifests and model_id in full_rank_artifacts:
        source_key = model_id
        alias_reason = "canonical source key"
    else:
        deprecated = (registry.get("production_models") or {}).get("deprecated") or {}
        aliases = [
            alias
            for alias, metadata in deprecated.items()
            if isinstance(metadata, dict)
            and metadata.get("reason") == f"legacy id replaced by {model_id}"
            and alias in signal_manifests
            and alias in full_rank_artifacts
        ]
        if len(aliases) != 1:
            raise RuntimeError(
                "canonical source alias requires one explicit registry replacement"
            )
        source_key = aliases[0]
        alias_reason = str(deprecated[source_key]["reason"])

    signal_manifest_path = resolve(str(signal_manifests[source_key]))
    full_rank_manifest_path = resolve(str(full_rank_artifacts[source_key]))
    signal_manifest = load_json(signal_manifest_path)
    full_rank_manifest = load_json(full_rank_manifest_path)
    raw_score_ref = str(training_manifest.get("raw_oos_score_path") or "")
    if not raw_score_ref:
        raise RuntimeError("E1 training manifest has no raw OOS score lineage")
    raw_score_path = resolve(raw_score_ref)
    signal_sources = {
        str(value) for value in signal_manifest.get("source_artifacts") or []
    }
    if (
        signal_manifest.get("artifact_type") != "model_signal"
        or signal_manifest.get("model_name") != source_key
        or raw_score_ref not in signal_sources
        or full_rank_manifest.get("artifact_type") != "full_rank"
        or full_rank_manifest.get("source_artifact") != raw_score_ref
        or full_rank_manifest.get("source_rank_column") != "qlib_rank_raw"
    ):
        raise RuntimeError("legacy source artifacts do not trace to canonical E1 score")
    declared_raw_hash = (signal_manifest.get("input_hashes") or {}).get(raw_score_ref)
    if not raw_score_path.is_file() or declared_raw_hash != sha256_file(raw_score_path):
        raise RuntimeError("canonical E1 score checksum lineage mismatch")

    source_subset = dict(source)
    source_subset["signal_manifests"] = {model_id: str(signal_manifests[source_key])}
    source_subset["full_rank_artifacts"] = {
        model_id: str(full_rank_artifacts[source_key])
    }
    identity = {
        "canonical_model_id": model_id,
        "source_key": source_key,
        "registry_alias_reason": alias_reason,
        "canonical_training_manifest": rel(training_manifest_path),
        "canonical_training_report": str(policy_model["source_training_report"]),
        "canonical_model_artifact": rel(model_path),
        "canonical_model_sha256": sha256_file(model_path),
        "raw_oos_score": rel(raw_score_path),
        "raw_oos_score_sha256": declared_raw_hash,
        "signal_manifest": rel(signal_manifest_path),
        "signal_manifest_sha256": sha256_file(signal_manifest_path),
        "full_rank_manifest": rel(full_rank_manifest_path),
        "full_rank_manifest_sha256": sha256_file(full_rank_manifest_path),
        "identity_adaptation": "explicit_registry_replacement_with_shared_e1_lineage",
    }
    training_report_path = resolve(str(policy_model["source_training_report"]))
    lineage_paths = [
        training_manifest_path,
        training_report_path,
        model_path,
        raw_score_path,
        signal_manifest_path,
        full_rank_manifest_path,
    ]
    lineage_paths.extend(
        resolve(path) for path in (signal_manifest.get("output_files") or {}).values()
    )
    lineage_paths.extend(
        resolve(path)
        for path in (full_rank_manifest.get("output_files") or {}).values()
    )
    return source_subset, identity, lineage_paths


def load_d3_runner() -> Any:
    spec = importlib.util.spec_from_file_location(
        "d3_order_intent_replay_parity", D3_RUNNER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to import {D3_RUNNER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def checksum_items(paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        if not resolved.is_file():
            raise RuntimeError(f"required checksum input is missing: {path}")
        seen.add(resolved)
        rows.append(
            {
                "path": rel(resolved),
                "sha256": sha256_file(resolved),
                "bytes": resolved.stat().st_size,
            }
        )
    return sorted(rows, key=lambda row: row["path"])


def _guard_candidate_root(out_root: Path) -> None:
    protected = [
        ROOT / "data_tw/artifacts/readonly_replay_windows/d6",
        ROOT / "data_tw/artifacts/readonly_replay_windows/d7",
    ]
    resolved = out_root.resolve()
    for path in protected:
        try:
            resolved.relative_to(path.resolve())
        except ValueError:
            continue
        raise RuntimeError(
            f"candidate output must not write protected path: {rel(path)}"
        )


def build_artifact(
    *,
    model_id: str,
    strategy_rule: str,
    start: str,
    end: str,
    out_root: Path,
    baseline_manifest: Path,
    policy_path: Path,
    registry_path: Path = DEFAULT_REGISTRY,
    baseline_descriptor_path: Path = DEFAULT_BASELINE_DESCRIPTOR,
    price_store_manifest_path: Path = DEFAULT_PRICE_STORE,
) -> dict[str, Any]:
    _guard_candidate_root(out_root)
    policy = load_yaml(policy_path)
    registry = load_yaml(registry_path)
    descriptor = load_yaml(baseline_descriptor_path)
    validation = validate_window(policy, model_id, strategy_rule, start, end)
    source = load_json(baseline_manifest)
    source_subset, source_identity, lineage_paths = resolve_canonical_source(
        model_id=model_id,
        source=source,
        policy=policy,
        registry=registry,
        baseline_descriptor=descriptor,
    )
    price_store = load_json(price_store_manifest_path)
    if (
        price_store.get("artifact_type") != "price_store"
        or price_store.get("readonly_only") is not True
        or price_store.get("no_provider_publish") is not True
        or price_store.get("no_accepted_latest_switch") is not True
        or str(price_store.get("date_min")) > start
        or str(price_store.get("date_max")) < end
    ):
        raise RuntimeError("canonical price store is not valid for requested window")

    identity_payload = {
        "model_id": model_id,
        "strategy_rule": strategy_rule,
        "start": start,
        "end": end,
        "execution_price_mode": "next_open",
        "baseline_manifest_sha256": sha256_file(baseline_manifest),
        "policy_sha256": sha256_file(policy_path),
        "registry_sha256": sha256_file(registry_path),
        "baseline_descriptor_sha256": sha256_file(baseline_descriptor_path),
        "price_store_manifest_sha256": sha256_file(price_store_manifest_path),
        "source_identity": source_identity,
    }
    identity_sha = canonical_sha256(identity_payload)
    run_id = f"wf2a_{identity_sha[:24]}"
    window_key = f"{start}_{end}".replace("-", "")
    artifact_dir = (out_root / model_id / strategy_rule / window_key / run_id).resolve()
    if artifact_dir.exists() and any(artifact_dir.iterdir()):
        raise RuntimeError(f"candidate artifact already exists: {artifact_dir}")
    artifact_dir.mkdir(parents=True, exist_ok=True)

    d3 = load_d3_runner()
    d3.WINDOW = f"readonly_{start}_{end}"
    d3.WINDOW_START = start
    d3.WINDOW_END = end
    d3.RULES = [strategy_rule]
    replay_manifest_path = d3.run_forward_chain(
        artifact_dir=artifact_dir,
        baseline_manifest_path=baseline_manifest,
        source_manifest=source_subset,
        price_store_manifest_path=price_store_manifest_path,
        execution_price_mode="next_open",
    )
    replay_manifest = load_json(replay_manifest_path)
    order_refs = [
        resolve(path) for path in replay_manifest.get("order_intent_artifacts", [])
    ]
    if len(order_refs) != 1:
        raise RuntimeError(
            "single-model/single-strategy candidate requires one OrderIntent"
        )
    order_manifest = load_json(order_refs[0])
    order_intents_path = resolve(
        str((order_manifest.get("output_files") or {}).get("order_intents") or "")
    )
    order_intents = pd.read_csv(order_intents_path)
    actions_path = resolve(str(replay_manifest["artifacts"]["actions"]))
    actions = pd.read_csv(actions_path)
    active_actions = actions[
        actions["action"].isin(["historical_add", "historical_risk_reduce"])
    ]
    if order_intents.empty or active_actions.empty:
        raise RuntimeError(
            "candidate replay must contain OrderIntent and active actions"
        )

    source_audit_path = replay_manifest_path.parent / "source_identity_audit.json"
    write_json(
        source_audit_path,
        {
            "artifact_type": "canonical_model_source_identity_audit",
            "schema_version": "wf2a_source_identity_v1",
            "status": "pass",
            **source_identity,
        },
    )
    replay_manifest["artifacts"]["source_identity_audit"] = rel(source_audit_path)
    replay_manifest.update(
        {
            "schema_version": "readonly_replay_result_wf2a_v1",
            "run_id": run_id,
            "status": "CANDIDATE_HOLD",
            "asof": end,
            "created_by": rel(Path(__file__)),
            "phase": "WF-2A",
            "readonly_only": True,
            "simulation_only": True,
            "not_order": True,
            "no_order_action": True,
            "not_target_position": True,
            "not_investment_advice": True,
            "production_trade_enabled": False,
            "no_provider_publish": True,
            "no_accepted_latest_switch": True,
            "no_monitor_broker_order": True,
            "no_training": True,
            "no_score_recompute": True,
            "window": {"name": "2026_ytd", "start": start, "end": end},
            "window_start": start,
            "window_end": end,
            "model_id": model_id,
            "requested_model_id": model_id,
            "strategy_rule": strategy_rule,
            "requested_strategy_rule": strategy_rule,
            "execution_price_mode": "next_open",
            "replay_window_policy_validation": validation,
            "replay_window_policy": rel(policy_path),
            "model_source_identity": source_identity,
            "model_registry": rel(registry_path),
            "baseline_descriptor": rel(baseline_descriptor_path),
            "canonical_price_store_manifest": rel(price_store_manifest_path),
            "not_generated_in_api_handler": True,
            "product_index_admission": False,
            "candidate_hold_reason": (
                "requires independent review before D7 index admission"
            ),
            "identity_sha256": identity_sha,
            "identity_payload": identity_payload,
        }
    )
    checksum_path = replay_manifest_path.parent / "checksum_manifest.json"
    replay_manifest["checksum_manifest"] = rel(checksum_path)
    checksum_paths = [
        policy_path,
        registry_path,
        baseline_descriptor_path,
        baseline_manifest,
        price_store_manifest_path,
        resolve(str(price_store["prices_path"])),
        source_audit_path,
        *lineage_paths,
        *[resolve(path) for path in replay_manifest["artifacts"].values()],
    ]
    for order_ref in order_refs:
        checksum_paths.append(order_ref)
        order_manifest = load_json(order_ref)
        checksum_paths.extend(
            resolve(path)
            for path in (order_manifest.get("output_files") or {}).values()
        )
    replay_manifest["checksum_required_files"] = sorted(
        {rel(replay_manifest_path), *(rel(path) for path in checksum_paths)}
    )
    write_json(replay_manifest_path, replay_manifest)
    checksum = {
        "artifact_type": "readonly_replay_checksum_manifest",
        "schema_version": "readonly_replay_checksum_wf2a_v1",
        "created_at": now(),
        "run_id": run_id,
        "files": checksum_items([replay_manifest_path, *checksum_paths]),
    }
    write_json(checksum_path, checksum)
    return {
        "ok": True,
        "status": "CANDIDATE_HOLD",
        "product_index_admission": False,
        "manifest": rel(replay_manifest_path),
        "run_id": run_id,
        "row_counts": replay_manifest.get("row_counts", {}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a contract-complete readonly ReplayResult candidate."
    )
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--strategy-rule", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT))
    parser.add_argument("--baseline-manifest", default=str(DEFAULT_BASELINE))
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument(
        "--baseline-descriptor", default=str(DEFAULT_BASELINE_DESCRIPTOR)
    )
    parser.add_argument("--price-store", default=str(DEFAULT_PRICE_STORE))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = build_artifact(
            model_id=args.model_id,
            strategy_rule=args.strategy_rule,
            start=args.start,
            end=args.end,
            out_root=resolve(args.out_root),
            baseline_manifest=resolve(args.baseline_manifest),
            policy_path=resolve(args.policy),
            registry_path=resolve(args.registry),
            baseline_descriptor_path=resolve(args.baseline_descriptor),
            price_store_manifest_path=resolve(args.price_store),
        )
    except Exception as exc:  # noqa: BLE001
        result = {"ok": False, "error": str(exc)}
        print(
            json.dumps(result, ensure_ascii=False, indent=2)
            if args.json
            else f"ok=False\nerror={exc}"
        )
        return 2
    print(
        json.dumps(result, ensure_ascii=False, indent=2)
        if args.json
        else f"ok={result['ok']}\nmanifest={result['manifest']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
