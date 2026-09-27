"""Read-only loader for modular Taiwan strategy snapshot artifacts."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
PUBLISH_ROOT = REPO_ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot"
LATEST_PATH = PUBLISH_ROOT / "latest.json"
ASOF_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


class ReadonlyStrategySnapshotError(Exception):
    """Raised when a readonly snapshot artifact cannot be loaded safely."""

    def __init__(self, status: str, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _resolve_repo_path(path: str) -> Path:
    resolved = (REPO_ROOT / path).resolve()
    if not resolved.is_relative_to(REPO_ROOT.resolve()):
        raise ReadonlyStrategySnapshotError("path_outside_root", f"Path outside repo root: {path}")
    return resolved


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise ReadonlyStrategySnapshotError("missing_artifact", f"Missing readonly artifact: {_rel(path)}")
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _checksum_status(manifest_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    checksum_path = manifest_dir / str(manifest.get("checksum_manifest", ""))
    payload = _load_json(checksum_path)
    rows = []
    files = payload.get("files", [])
    if isinstance(files, dict):
        items = [
            {"path": str(manifest_dir.relative_to(REPO_ROOT) / str(name)), "sha256": value}
            for name, value in files.items()
        ]
    elif isinstance(files, list):
        items = files
    else:
        raise ReadonlyStrategySnapshotError("invalid_checksum_manifest", "checksum_manifest.files must be a list or object")

    for item in items:
        if not isinstance(item, dict):
            raise ReadonlyStrategySnapshotError("invalid_checksum_manifest", "checksum_manifest file entries must be objects")
        path = _resolve_repo_path(str(item.get("path", "")))
        actual = _sha256(path) if path.exists() else ""
        rows.append(
            {
                "path": _rel(path),
                "status": "pass" if actual == item.get("sha256") and bool(actual) else "fail",
            }
        )
    return {
        "ok": all(row["status"] == "pass" for row in rows),
        "checked_file_count": len(rows),
        "self_included": any(str(item.get("path", "")).endswith("checksum_manifest.json") for item in items),
        "manifest": _rel(checksum_path),
    }


def _forbidden_scope_summary(forbidden_scope_audit: dict[str, Any]) -> dict[str, Any]:
    flags = forbidden_scope_audit.get("flags") if isinstance(forbidden_scope_audit.get("flags"), dict) else {}
    return {
        "status": forbidden_scope_audit.get("status"),
        "no_provider_publish": forbidden_scope_audit.get("no_provider_publish") is True
        or flags.get("provider_publish_triggered") is False,
        "no_accepted_latest_switch": forbidden_scope_audit.get("no_accepted_latest_switch") is True
        or (
            flags.get("provider_accepted_latest_switched") is False
            and flags.get("qlib_accepted_latest_switched") is False
            and flags.get("legacy_option_c_latest_signal_switched") is False
        ),
        "no_monitor_broker_order": forbidden_scope_audit.get("no_monitor_broker_order") is True
        or flags.get("monitor_broker_order_triggered") is False,
    }


def _manifest_path_for_asof(asof: str | None) -> tuple[Path, dict[str, Any] | None]:
    if asof:
        if ASOF_PATTERN.fullmatch(asof) is None:
            raise ReadonlyStrategySnapshotError("invalid_asof", "Snapshot asof must be YYYY-MM-DD")
        try:
            date.fromisoformat(asof)
        except ValueError as exc:
            raise ReadonlyStrategySnapshotError("invalid_asof", "Snapshot asof must be a valid calendar date") from exc
        manifest_path = (PUBLISH_ROOT / asof / "manifest.json").resolve()
        if not manifest_path.is_relative_to(PUBLISH_ROOT.resolve()):
            raise ReadonlyStrategySnapshotError("asof_outside_readonly_root", "Snapshot asof is outside readonly snapshot root")
        return manifest_path, None
    latest = _load_json(LATEST_PATH)
    if latest.get("artifact_type") != "readonly_strategy_snapshot_latest_pointer":
        raise ReadonlyStrategySnapshotError("invalid_latest_pointer", "Latest pointer is not a readonly snapshot pointer")
    if latest.get("not_provider_accepted_latest") is not True or latest.get("not_trade_target_latest") is not True:
        raise ReadonlyStrategySnapshotError("unsafe_latest_pointer", "Latest pointer safety flags are not set")
    manifest_path = _resolve_repo_path(str(latest.get("snapshot_manifest", "")))
    if not manifest_path.is_relative_to(PUBLISH_ROOT.resolve()):
        raise ReadonlyStrategySnapshotError("latest_outside_readonly_root", "Latest pointer is outside readonly snapshot root")
    return manifest_path, latest


def load_readonly_strategy_snapshot(asof: str | None = None) -> dict[str, Any]:
    """Load a readonly strategy snapshot without mutating any provider, monitor, or trading state."""
    manifest_path, latest = _manifest_path_for_asof(asof)
    manifest = _load_json(manifest_path)
    manifest_dir = manifest_path.parent
    snapshot = _load_json(manifest_dir / str(manifest.get("snapshot", "")))
    validation_report = _load_json(manifest_dir / str(manifest.get("validation_report", "")))
    forbidden_scope_audit = _load_json(manifest_dir / str(manifest.get("forbidden_scope_audit", "")))
    checksum = _checksum_status(manifest_dir, manifest)

    if manifest.get("artifact_type") != "readonly_strategy_snapshot":
        raise ReadonlyStrategySnapshotError("invalid_artifact_type", "Manifest is not readonly_strategy_snapshot")
    if manifest.get("readonly_only") is not True or snapshot.get("readonly_only") is not True:
        raise ReadonlyStrategySnapshotError("unsafe_snapshot", "Snapshot readonly flag is not true")
    if manifest.get("production_trade_enabled") is not False:
        raise ReadonlyStrategySnapshotError("unsafe_snapshot", "Production trade flag is not false")
    if manifest.get("not_target_position") is not True or snapshot.get("not_target_position") is not True:
        raise ReadonlyStrategySnapshotError("unsafe_snapshot", "Target-position safety flag is not true")
    if not checksum["ok"]:
        raise ReadonlyStrategySnapshotError("checksum_failed", "Readonly snapshot checksum validation failed")

    return {
        "ok": True,
        "schema_version": "readonly_strategy_snapshot_api_r14_v1",
        "asof": manifest.get("asof"),
        "readonly_only": True,
        "not_order": True,
        "no_order_action": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "production_trade_enabled": False,
        "manifest": manifest,
        "snapshot": snapshot,
        "validation": {
            "ok": validation_report.get("status") == "pass",
            "status": validation_report.get("status"),
            "manifest": _rel(manifest_dir / str(manifest.get("validation_report", ""))),
        },
        "checksum": checksum,
        "forbidden_scope_audit": _forbidden_scope_summary(forbidden_scope_audit),
        "latest_pointer": latest,
        "sources": {
            "manifest": _rel(manifest_path),
            "source_shadow_manifest": manifest.get("source_shadow_manifest"),
            "source_signal_manifest": manifest.get("source_signal_manifest"),
            "source_full_rank_manifest": manifest.get("source_full_rank_manifest"),
            "source_strategy_dependency": manifest.get("source_strategy_dependency"),
        },
        "no_write_guarantees": {
            "read_only_http_method": True,
            "reads_static_readonly_snapshot_only": True,
            "does_not_touch_provider_accepted_latest": True,
            "does_not_touch_monitor_or_alerts": True,
            "does_not_touch_broker_or_orders": True,
        },
    }
