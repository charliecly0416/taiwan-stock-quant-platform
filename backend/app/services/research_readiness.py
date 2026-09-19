"""Cheap, side-effect-free readiness checks for the TW research product."""
from __future__ import annotations

import json
import hashlib
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
MAX_CONTROL_FILE_BYTES = 256 * 1024
MAX_TARGET_FILE_BYTES = 8 * 1024 * 1024
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

CONTROL_FILES = {
    "artifact_registry": "configs/tw_product_artifact_registry.yaml",
    "model_a_latest": "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    "readonly_snapshot_latest": "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    "agent_prompt_latest": "data_tw/artifacts/agent_daily_prompt/latest.json",
}

UNSAFE_RESEARCH_RUNTIME_FLAGS = (
    "AGENT_LIVE_TRADING_ENABLED",
    "ENABLE_PENDING_ORDER_WORKER",
    "ENABLE_PORTFOLIO_MONITOR",
    "ENABLE_TW_STOCK_MONITOR_WORKER",
    "POSITION_SYNC_ENABLED",
    "ENABLE_REFLECTION_WORKER",
    "ENABLE_OFFLINE_AI_CALIBRATION",
    "USDT_PAY_ENABLED",
)


class ReadinessCheckError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def research_runtime_safety() -> dict[str, Any]:
    """Report whether this process matches the readonly research deployment."""
    enabled = [
        name for name in UNSAFE_RESEARCH_RUNTIME_FLAGS
        if str(os.getenv(name, "")).strip().lower() in {"1", "true", "yes", "on"}
    ]
    restore_disabled = str(os.getenv("DISABLE_RESTORE_RUNNING_STRATEGIES", "true")).strip().lower() in {
        "1", "true", "yes", "on",
    }
    ready = not enabled and restore_disabled
    return {
        "ready": ready,
        "code": "ok" if ready else "readonly_runtime_boundary_failed",
        "mode": "readonly_research",
    }


def _read_control(path: Path, *, yaml_file: bool = False) -> dict[str, Any]:
    try:
        if not path.is_file() or path.stat().st_size > MAX_CONTROL_FILE_BYTES:
            raise ReadinessCheckError("missing_or_oversized")
        text = path.read_text(encoding="utf-8")
        payload = yaml.safe_load(text) if yaml_file else json.loads(text)
    except ReadinessCheckError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ReadinessCheckError("unreadable_or_invalid") from exc
    if not isinstance(payload, dict):
        raise ReadinessCheckError("invalid_object")
    return payload


def _repo_target(root: Path, value: Any) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ReadinessCheckError("missing_target")
    target = (root / value).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise ReadinessCheckError("target_outside_repository") from exc
    if not target.is_file():
        raise ReadinessCheckError("target_missing")
    return target


def _mapping(value: Any, code: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReadinessCheckError(code)
    return value


def _sha256(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_TARGET_FILE_BYTES:
            raise ReadinessCheckError("target_oversized")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except ReadinessCheckError:
        raise
    except OSError as exc:
        raise ReadinessCheckError("target_unreadable") from exc


def _bounded_bytes(path: Path) -> bytes:
    try:
        if not path.is_file() or path.stat().st_size > MAX_TARGET_FILE_BYTES:
            raise ReadinessCheckError("target_missing_or_oversized")
        return path.read_bytes()
    except ReadinessCheckError:
        raise
    except OSError as exc:
        raise ReadinessCheckError("target_unreadable") from exc


def _require_sha256(path: Path, expected: Any) -> None:
    value = str(expected or "")
    if not re.fullmatch(r"[0-9a-f]{64}", value) or _sha256(path) != value:
        raise ReadinessCheckError("target_checksum_failed")


def _artifact_member(root: Path, artifact_dir: Path, value: Any) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ReadinessCheckError("missing_artifact_member")
    target = (artifact_dir / value).resolve()
    try:
        target.relative_to(artifact_dir.resolve())
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise ReadinessCheckError("artifact_member_outside_directory") from exc
    if not target.is_file():
        raise ReadinessCheckError("artifact_member_missing")
    return target


def _asof(payload: dict[str, Any]) -> str:
    value = str(payload.get("signal_asof") or payload.get("asof") or "")
    if not DATE_RE.fullmatch(value):
        raise ReadinessCheckError("invalid_signal_asof")
    return value


def _check_registry(payload: dict[str, Any]) -> str:
    models = _mapping(payload.get("models"), "registry_contract_failed")
    strategies = _mapping(payload.get("strategies"), "registry_contract_failed")
    if (
        payload.get("schema_version") != "tw_product_artifact_registry_v1"
        or payload.get("readonly_only") is not True
        or not str(models.get("base_model_id") or "")
        or not str(strategies.get("default_strategy_rule") or "")
    ):
        raise ReadinessCheckError("registry_contract_failed")
    return str(models["base_model_id"])


def _check_model_a(root: Path, payload: dict[str, Any], model_id: str) -> str:
    if not (
        payload.get("artifact_type") == "controlled_model_signal_latest_pointer"
        and payload.get("readonly_only") is True
        and payload.get("production_trade_enabled") is False
        and payload.get("model_id") == model_id
    ):
        raise ReadinessCheckError("model_a_pointer_contract_failed")
    artifact_dir = _repo_target(root, str(payload.get("canonical_artifact_dir") or "") + "/manifest.json").parent
    manifest = _repo_target(root, payload.get("canonical_manifest"))
    signals = _repo_target(root, payload.get("canonical_signals"))
    if manifest.parent != artifact_dir or signals.parent != artifact_dir:
        raise ReadinessCheckError("model_a_target_binding_failed")
    _require_sha256(manifest, payload.get("canonical_manifest_sha256"))
    _require_sha256(signals, payload.get("canonical_signals_sha256"))
    signal_asof = _asof(payload)
    manifest_payload = _read_control(manifest)
    if not (
        manifest_payload.get("artifact_type") == "ModelSignalArtifact"
        and manifest_payload.get("model_id") == model_id
        and manifest_payload.get("status") == "READY"
        and _asof(manifest_payload) == signal_asof
    ):
        raise ReadinessCheckError("model_a_manifest_contract_failed")
    return signal_asof


def _check_snapshot(root: Path, payload: dict[str, Any], expected_asof: str) -> None:
    if not (
        payload.get("artifact_type") == "readonly_strategy_snapshot_latest_pointer"
        and payload.get("readonly_only") is True
        and payload.get("production_trade_enabled") is False
        and payload.get("not_trade_target_latest") is True
        and _asof(payload) == expected_asof
        and payload.get("source_signal_latest") == CONTROL_FILES["model_a_latest"]
    ):
        raise ReadinessCheckError("snapshot_pointer_contract_failed")
    manifest_path = _repo_target(root, payload.get("snapshot_manifest"))
    _require_sha256(manifest_path, payload.get("planned_manifest_payload_sha256"))
    _require_sha256(root / CONTROL_FILES["model_a_latest"], payload.get("source_signal_latest_sha256"))
    manifest = _read_control(manifest_path)
    if not (
        manifest.get("artifact_type") == "readonly_strategy_snapshot"
        and manifest.get("readonly_only") is True
        and manifest.get("production_trade_enabled") is False
        and manifest.get("no_order_action") is True
        and _asof(manifest) == expected_asof
        and manifest.get("source_signal_latest") == CONTROL_FILES["model_a_latest"]
    ):
        raise ReadinessCheckError("snapshot_manifest_contract_failed")
    artifact_dir = manifest_path.parent
    checksum_manifest = _read_control(_artifact_member(root, artifact_dir, manifest.get("checksum_manifest")))
    checksums = _mapping(checksum_manifest.get("files"), "snapshot_checksum_manifest_failed")
    _require_sha256(manifest_path, checksums.get(manifest_path.name))
    for field in ("snapshot", "validation_report", "forbidden_scope_audit"):
        member = _artifact_member(root, artifact_dir, manifest.get(field))
        _require_sha256(member, checksums.get(member.name))
    validation = _read_control(_artifact_member(root, artifact_dir, manifest.get("validation_report")))
    forbidden = _read_control(_artifact_member(root, artifact_dir, manifest.get("forbidden_scope_audit")))
    if not (
        validation.get("status") == "pass"
        and validation.get("readonly_snapshot_validator_ok") is True
        and validation.get("checksum_ok") is True
        and forbidden.get("status") == "pass"
        and forbidden.get("all_forbidden_false") is True
    ):
        raise ReadinessCheckError("snapshot_validation_failed")


def _check_agent(root: Path, payload: dict[str, Any], expected_asof: str) -> None:
    if not (
        payload.get("artifact_type") == "tw_agent_daily_prompt_latest"
        and payload.get("readonly_only") is True
        and payload.get("production_trade_enabled") is False
        and _asof(payload) == expected_asof
        and payload.get("source_readonly_snapshot_latest") == CONTROL_FILES["readonly_snapshot_latest"]
    ):
        raise ReadinessCheckError("agent_pointer_contract_failed")
    artifact_dir = (root / str(payload.get("artifact_dir") or "")).resolve()
    manifest = _repo_target(root, payload.get("manifest"))
    if manifest.parent != artifact_dir:
        raise ReadinessCheckError("agent_target_binding_failed")
    manifest_payload = _read_control(manifest)
    context_bytes = _bounded_bytes(artifact_dir / "prompt_context.json")
    prompt_bytes = _bounded_bytes(artifact_dir / "prompt_text.md")
    checksum = "sha256:" + hashlib.sha256(context_bytes + b"\n" + prompt_bytes).hexdigest()
    validation = manifest_payload.get("validation")
    if not (
        manifest_payload.get("artifact_type") == "tw_agent_daily_prompt"
        and manifest_payload.get("readonly_only") is True
        and manifest_payload.get("not_order") is True
        and manifest_payload.get("not_target_position") is True
        and manifest_payload.get("production_trade_enabled") is False
        and _asof(manifest_payload) == expected_asof
        and isinstance(validation, dict)
        and validation.get("ok") is True
        and validation.get("asof_alignment") == "pass"
        and validation.get("forbidden_action_audit") == "pass"
        and validation.get("source_gate") == "pass"
        and payload.get("checksum") == manifest_payload.get("checksum") == checksum
    ):
        raise ReadinessCheckError("agent_manifest_contract_failed")


def research_readiness(*, repo_root: str | Path | None = None) -> dict[str, Any]:
    """Validate local control-plane artifacts without network, DB, or writes."""
    root = Path(repo_root or REPO_ROOT).resolve()
    checks: list[dict[str, Any]] = []
    documents: dict[str, dict[str, Any]] = {}
    for name, relative in CONTROL_FILES.items():
        try:
            documents[name] = _read_control(root / relative, yaml_file=name == "artifact_registry")
            checks.append({"name": name, "ready": True, "code": "ok"})
        except ReadinessCheckError as exc:
            checks.append({"name": name, "ready": False, "code": exc.code})

    signal_asof = None
    contract_checks = (
        ("registry_contract", lambda: _check_registry(documents["artifact_registry"])),
        ("model_a_contract", lambda: _check_model_a(root, documents["model_a_latest"], _check_registry(documents["artifact_registry"]))),
    )
    values: dict[str, Any] = {}
    for name, check in contract_checks:
        try:
            values[name] = check()
            checks.append({"name": name, "ready": True, "code": "ok"})
        except (KeyError, ReadinessCheckError) as exc:
            code = exc.code if isinstance(exc, ReadinessCheckError) else "dependency_unavailable"
            checks.append({"name": name, "ready": False, "code": code})
    signal_asof = values.get("model_a_contract")
    for name, check in (
        ("snapshot_contract", lambda: _check_snapshot(root, documents["readonly_snapshot_latest"], signal_asof)),
        ("agent_contract", lambda: _check_agent(root, documents["agent_prompt_latest"], signal_asof)),
    ):
        try:
            if not signal_asof:
                raise ReadinessCheckError("dependency_unavailable")
            check()
            checks.append({"name": name, "ready": True, "code": "ok"})
        except (KeyError, ReadinessCheckError) as exc:
            code = exc.code if isinstance(exc, ReadinessCheckError) else "dependency_unavailable"
            checks.append({"name": name, "ready": False, "code": code})

    ready = all(item["ready"] for item in checks)
    return {
        "schema_version": "tw_research_readiness_v1",
        "ready": ready,
        "status": "ready" if ready else "not_ready",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "signal_asof": signal_asof if ready else None,
        "checks": checks,
        "scope": "local_readonly_control_plane",
        "external_dependencies_checked": False,
        "side_effects": "none",
    }
