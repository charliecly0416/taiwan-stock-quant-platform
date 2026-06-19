#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_D3RR_MANIFEST = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T062610Z/manifest.json"
DEFAULT_POLICY = ROOT / "configs/tw_replay_window_policy.yaml"
DEFAULT_OUT_DIR = ROOT / "data_tw/artifacts/readonly_standard_artifact_index/d4"


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checksum_items(paths: list[Path]) -> list[dict[str, Any]]:
    items = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved in seen or not path.exists():
            continue
        seen.add(resolved)
        items.append({"path": rel(path), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    return items


def build_index(*, d3rr_manifest_path: Path, policy_path: Path, out_dir: Path) -> dict[str, Any]:
    d3rr_manifest = load_json(d3rr_manifest_path)
    replay_manifest_path = resolve(str(d3rr_manifest["order_intent_replay_manifest"]))
    replay_manifest = load_json(replay_manifest_path)
    policy = load_yaml(policy_path)
    order_paths = [resolve(str(path)) for path in replay_manifest.get("order_intent_artifacts", [])]
    artifact_paths = [d3rr_manifest_path, replay_manifest_path, policy_path, *order_paths]
    for path in (d3rr_manifest.get("artifacts") or {}).values():
        artifact_paths.append(resolve(str(path)))
    for path in (replay_manifest.get("artifacts") or {}).values():
        artifact_paths.append(resolve(str(path)))
    checksum_manifest = {
        "artifact_type": "readonly_standard_artifact_index_checksum",
        "schema_version": "readonly_standard_artifact_index_checksum_d4_v1",
        "created_at": now(),
        "files": checksum_items(artifact_paths),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "checksum_manifest.json", checksum_manifest)
    manifest = {
        "artifact_type": "readonly_standard_artifact_index",
        "schema_version": "readonly_standard_artifact_index_d4_v1",
        "created_at": now(),
        "created_by": rel(Path(__file__)),
        "phase": "D4",
        "readonly_only": True,
        "not_order": True,
        "not_investment_advice": True,
        "not_target_position": True,
        "production_trade_enabled": False,
        "no_order_action": True,
        "no_provider_publish": True,
        "no_accepted_latest_switch": True,
        "no_monitor_broker_order": True,
        "fixed_window_only": policy.get("fixed_window_only") is True,
        "user_selectable_range_enabled": policy.get("user_selectable_range_enabled") is True,
        "available_window_metadata_only": policy.get("available_window_metadata_only") is True,
        "window": d3rr_manifest.get("window"),
        "window_start": d3rr_manifest.get("window_start"),
        "window_end": d3rr_manifest.get("window_end"),
        "order_intent_replay_parity_manifest": rel(d3rr_manifest_path),
        "order_intent_replay_result_manifest": rel(replay_manifest_path),
        "order_intent_artifact_manifests": [rel(path) for path in order_paths],
        "order_intent_artifact_count": len(order_paths),
        "baseline_manifest": d3rr_manifest.get("baseline_manifest"),
        "rules_present": d3rr_manifest.get("rules_present", []),
        "methods_present": d3rr_manifest.get("methods_present", []),
        "diagnostic_rule": d3rr_manifest.get("diagnostic_rule"),
        "diagnostic_rule_only_for_parity": d3rr_manifest.get("diagnostic_rule_only_for_parity") is True,
        "diagnostic_rule_not_valid_strategy_evidence": d3rr_manifest.get("diagnostic_rule_not_valid_strategy_evidence") is True,
        "parity_status": d3rr_manifest.get("parity_status"),
        "row_counts": d3rr_manifest.get("row_counts", {}),
        "replay_result_row_counts": replay_manifest.get("row_counts", {}),
        "generated_by": replay_manifest.get("generated_by"),
        "decision_source": replay_manifest.get("decision_source"),
        "execution_input_source": replay_manifest.get("execution_input_source"),
        "not_copied_from_legacy_replay": replay_manifest.get("not_copied_from_legacy_replay") is True,
        "legacy_replay_used_only_for_parity": replay_manifest.get("legacy_replay_used_only_for_parity") is True,
        "outputs_recomputed_checksum_not_legacy_copy": replay_manifest.get("outputs_recomputed_checksum_not_legacy_copy") is True,
        "replay_window_policy_metadata": {
            "policy_path": rel(policy_path),
            "policy_version": policy.get("policy_version"),
            "fixed_window": policy.get("fixed_window"),
            "allowed_replay_start_min": policy.get("allowed_replay_start_min"),
            "latest_available_signal_date": policy.get("latest_available_signal_date"),
            "allowed_replay_end_policy": policy.get("allowed_replay_end_policy"),
            "disallow_training_overlap": policy.get("disallow_training_overlap") is True,
            "disallow_future_beyond_signal": policy.get("disallow_future_beyond_signal") is True,
            "model_count": len(policy.get("models") or {}),
            "models": sorted((policy.get("models") or {}).keys()),
            "diagnostic_rules": policy.get("diagnostic_rules", {}),
        },
        "artifacts": {
            "checksum_manifest": rel(out_dir / "checksum_manifest.json"),
            "replay_window_policy": rel(policy_path),
        },
    }
    write_json(out_dir / "manifest.json", manifest)
    latest = {
        "artifact_type": "readonly_standard_artifact_index_latest_pointer",
        "schema_version": "readonly_standard_artifact_index_latest_d4_v1",
        "created_at": now(),
        "readonly_only": True,
        "production_trade_enabled": False,
        "not_provider_accepted_latest": True,
        "not_trade_target_latest": True,
        "standard_artifact_index_manifest": rel(out_dir / "manifest.json"),
    }
    write_json(out_dir / "latest.json", latest)
    return {"ok": True, "manifest": rel(out_dir / "manifest.json"), "latest": rel(out_dir / "latest.json"), "order_intent_artifact_count": len(order_paths), "window": manifest["window"]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build D4 readonly standard artifact index from audited D3RR artifacts.")
    parser.add_argument("--d3rr-manifest", default=str(DEFAULT_D3RR_MANIFEST))
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = build_index(d3rr_manifest_path=resolve(args.d3rr_manifest), policy_path=resolve(args.policy), out_dir=resolve(args.out_dir))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']}")
        print(f"manifest={result['manifest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
