"""Read-only replay window index loader for audited TW replay artifacts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
INDEX_ROOT = ROOT / "data_tw/artifacts/readonly_replay_windows/d7"
LATEST_PATH = INDEX_ROOT / "latest.json"
POLICY = ROOT / "configs/tw_replay_window_policy.yaml"



class ReadonlyReplayWindowIndexError(Exception):
    """Raised when the readonly replay window index cannot be loaded safely."""

    def __init__(self, status: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details or {}



def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _clean_allowed_pairs() -> set[tuple[str, str]]:
    policy = _load_yaml(POLICY)
    models = policy.get("models") or {}
    allowed_models = {key for key, value in models.items() if (value or {}).get("production_selectable") is True}
    default_strategy = str(policy.get("default_strategy_rule") or "")
    return {(model_id, default_strategy) for model_id in allowed_models if default_strategy}


def _filter_clean_windows(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    allowed = _clean_allowed_pairs()
    if not allowed:
        return []
    return [entry for entry in entries if (str(entry.get("model_id")), str(entry.get("strategy_rule"))) in allowed]


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def _resolve_repo_path(path: str) -> Path:
    resolved = (ROOT / path).resolve()
    if not resolved.is_relative_to(ROOT.resolve()):
        raise ReadonlyReplayWindowIndexError("path_outside_root", f"Path outside repo root: {path}")
    return resolved


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise ReadonlyReplayWindowIndexError("missing_artifact", f"Missing readonly artifact: {_rel(path)}")
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _checksum_status(manifest_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    checksum_ref = str(manifest.get("checksum_manifest") or (manifest.get("artifacts") or {}).get("checksum_manifest", ""))
    candidate = manifest_dir / checksum_ref
    checksum_path = candidate if candidate.exists() else _resolve_repo_path(checksum_ref)
    payload = _load_json(checksum_path)
    checked = 0
    failed: list[str] = []
    for item in payload.get("files", []):
        path = _resolve_repo_path(str(item.get("path", "")))
        checked += 1
        if not path.exists() or _sha256(path) != item.get("sha256"):
            failed.append(str(item.get("path", "")))
    return {"ok": not failed and checked > 0, "checked_file_count": checked, "failed": failed, "manifest": _rel(checksum_path)}


def _validate_entry(entry: dict[str, Any]) -> dict[str, Any]:
    artifact_path = _resolve_repo_path(str(entry.get("artifact_manifest", "")))
    manifest = _load_json(artifact_path)
    checksum = _checksum_status(artifact_path.parent, manifest)
    if not checksum["ok"]:
        raise ReadonlyReplayWindowIndexError("checksum_failed", "Readonly replay window entry checksum validation failed", {"artifact_manifest": _rel(artifact_path), **checksum})
    return {
        "artifact_type": manifest.get("artifact_type"),
        "schema_version": manifest.get("schema_version"),
        "readonly_only": manifest.get("readonly_only") is True,
        "production_trade_enabled": manifest.get("production_trade_enabled") is False,
        "checksum": checksum,
        "manifest": _rel(artifact_path),
    }


def _entry_allowed_by_clean_policy(entry: dict[str, Any]) -> bool:
    allowed = _clean_allowed_pairs()
    return (str(entry.get("model_id")), str(entry.get("strategy_rule"))) in allowed


def _build_entries(index_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    entries = []
    for entry in index_manifest.get("windows", []):
        if not _entry_allowed_by_clean_policy(entry):
            continue
        validated = _validate_entry(entry)
        entries.append({
            "window_key": entry.get("window_key"),
            "window_type": entry.get("window_type"),
            "display_label": entry.get("display_label"),
            "model_id": entry.get("model_id"),
            "strategy_rule": entry.get("strategy_rule"),
            "start": entry.get("start"),
            "end": entry.get("end"),
            "artifact_manifest": validated["manifest"],
            "artifact_type": validated["artifact_type"],
            "schema_version": validated["schema_version"],
            "readonly_only": validated["readonly_only"],
            "production_trade_enabled": validated["production_trade_enabled"],
            "checksum": validated["checksum"],
            "sources": entry.get("sources") or {},
            "validation": entry.get("validation") or {},
        })
    return entries


def load_readonly_replay_window_index() -> dict[str, Any]:
    """Load the readonly replay window index without mutating runtime state."""
    latest = _load_json(LATEST_PATH)
    if latest.get("artifact_type") != "readonly_replay_window_index_latest_pointer":
        raise ReadonlyReplayWindowIndexError("invalid_latest_pointer", "Latest pointer is not a readonly replay window index pointer")
    if latest.get("readonly_only") is not True or latest.get("production_trade_enabled") is not False:
        raise ReadonlyReplayWindowIndexError("unsafe_latest_pointer", "Latest pointer safety flags are not set")
    manifest_path = _resolve_repo_path(str(latest.get("index_manifest", "")))
    if not manifest_path.is_relative_to(INDEX_ROOT.resolve()):
        raise ReadonlyReplayWindowIndexError("latest_outside_readonly_root", "Latest pointer is outside readonly replay window root")
    index_manifest = _load_json(manifest_path)
    checksum = _checksum_status(manifest_path.parent, index_manifest)
    if not checksum["ok"]:
        raise ReadonlyReplayWindowIndexError("checksum_failed", "Readonly replay window index checksum validation failed", checksum)
    windows = _build_entries(index_manifest)
    return {
        "ok": True,
        "schema_version": "readonly_replay_window_index_d7_v1",
        "readonly_only": True,
        "production_trade_enabled": False,
        "manifest": index_manifest,
        "windows": windows,
        "checksum": checksum,
        "latest_pointer": latest,
        "sources": {"manifest": _rel(manifest_path), "latest": _rel(LATEST_PATH)},
        "no_write_guarantees": {
            "read_only_http_method": True,
            "reads_pre_generated_audited_index_only": True,
            "does_not_generate_replay_on_demand": True,
            "does_not_touch_provider_accepted_latest": True,
            "does_not_touch_monitor_or_alerts": True,
            "does_not_touch_broker_or_orders": True,
            "filters_to_clean_replay_policy": True,
        },
    }


def load_index_entry(*, model_id: str, strategy_rule: str, start: str, end: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return the matching readonly replay window index entry and artifact payload."""
    index = load_readonly_replay_window_index()
    for entry in index.get("windows", []):
        if str(entry.get("model_id")) == model_id and str(entry.get("strategy_rule")) == strategy_rule and str(entry.get("start")) == start and str(entry.get("end")) == end:
            return entry, _load_json(_resolve_repo_path(str(entry["artifact_manifest"])))
    raise ReadonlyReplayWindowIndexError("no_indexed_readonly_replay_window", "Requested replay window is not registered in readonly replay window index", {"requested_model_id": model_id, "requested_strategy_rule": strategy_rule, "requested_start": start, "requested_end": end})
