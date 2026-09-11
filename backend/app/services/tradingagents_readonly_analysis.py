"""GET-only loader for validated TradingAgents readonly analysis artifacts."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ARTIFACT_ROOT = ROOT / "data_tw/artifacts/analysis/tradingagents_readonly"


class TradingAgentsReadonlyAnalysisError(RuntimeError):
    def __init__(self, status: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise TradingAgentsReadonlyAnalysisError("validator_unavailable", f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _validator() -> ModuleType:
    return _load_module(
        "validate_tradingagents_readonly_analysis_artifact",
        ROOT / "scripts/validate_tradingagents_readonly_analysis_artifact.py",
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise TradingAgentsReadonlyAnalysisError("json_read_failed", f"Failed to read {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise TradingAgentsReadonlyAnalysisError("json_not_object", f"Expected JSON object: {path}")
    return payload


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        raise TradingAgentsReadonlyAnalysisError("text_read_failed", f"Failed to read {path}: {exc}") from exc


def _safe_child(root: Path, name: str) -> Path:
    if not name or "/" in name or "\\" in name or name in {".", ".."}:
        raise TradingAgentsReadonlyAnalysisError("invalid_run_id", f"Invalid run_id: {name!r}")
    candidate = (root / name).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise TradingAgentsReadonlyAnalysisError("path_outside_root", f"Path outside root: {name}") from exc
    return candidate


def _resolve_artifact_dir(*, run_id: str | None, artifact_root: str | Path | None) -> Path:
    root = (Path(artifact_root) if artifact_root is not None else DEFAULT_ARTIFACT_ROOT).resolve()
    if run_id:
        return _safe_child(root, run_id)
    latest = root / "latest.json"
    if latest.exists():
        payload = _read_json(latest)
        artifact_dir = payload.get("artifact_dir")
        if not isinstance(artifact_dir, str) or not artifact_dir:
            raise TradingAgentsReadonlyAnalysisError("latest_missing_artifact_dir", "latest.json missing artifact_dir")
        candidate = Path(artifact_dir)
        if not candidate.is_absolute():
            candidate = root / candidate
        candidate = candidate.resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise TradingAgentsReadonlyAnalysisError("latest_path_outside_root", "latest artifact_dir outside artifact root") from exc
        return candidate
    if root.is_dir() and (root / "manifest.json").exists():
        return root
    raise TradingAgentsReadonlyAnalysisError("latest_missing", f"No latest artifact found under {root}")


def _public_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    blocked = {"input_artifacts", "raw_untrusted_files", "sanitizer_audit"}
    return {key: value for key, value in manifest.items() if key not in blocked}


def _validation_summary(validation: dict[str, Any]) -> dict[str, Any]:
    failed = [
        {"name": _public_check_name(str(check.get("name") or "")), "status": check.get("status")}
        for check in validation.get("checks", [])
        if isinstance(check, dict) and check.get("status") != "pass"
    ]
    return {
        "ok": validation.get("ok") is True,
        "artifact_dir": validation.get("artifact_dir"),
        "check_count": validation.get("check_count"),
        "failed_checks": failed,
    }


def _public_check_name(name: str) -> str:
    lowered = name.lower()
    raw_markers = ("raw_", "raw-tradingagents", "raw_tradingagents", "raw_complete")
    if any(marker in lowered for marker in raw_markers):
        return "review_only_source_file_check"
    return name


def _public_forbidden_audit(forbidden_audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": forbidden_audit.get("ok") is True,
        "checked_files": [
            item
            for item in forbidden_audit.get("checked_files", [])
            if isinstance(item, str) and not item.startswith("raw_")
        ],
        "blocked_terms_found": forbidden_audit.get("blocked_terms_found") or [],
        "forbidden_patterns": forbidden_audit.get("forbidden_patterns") or [],
    }


def load_tradingagents_readonly_analysis(
    *,
    run_id: str | None = None,
    artifact_root: str | Path | None = None,
    include_markdown: bool = False,
) -> dict[str, Any]:
    """Load a validated sanitized TradingAgents analysis artifact without writes."""
    artifact_dir = _resolve_artifact_dir(run_id=run_id, artifact_root=artifact_root).resolve()
    if not artifact_dir.exists() or not artifact_dir.is_dir():
        raise TradingAgentsReadonlyAnalysisError("artifact_missing", f"Artifact directory missing: {artifact_dir}")

    validation = _validator().validate(artifact_dir)
    if not validation.get("ok"):
        return {
            "ok": False,
            "status": "artifact_validation_failed",
            "message": "TradingAgents readonly analysis artifact failed validation",
            "schema_version": "tradingagents_readonly_analysis_api_v1",
            "readonly_only": True,
            "not_order": True,
            "not_target_position": True,
            "not_investment_advice": True,
            "production_trade_enabled": False,
            "artifact_dir": str(artifact_dir),
            "validation": _validation_summary(validation),
        }

    manifest = _read_json(artifact_dir / "manifest.json")
    sanitized_report = _read_json(artifact_dir / "sanitized_report.json")
    forbidden_audit = _read_json(artifact_dir / "forbidden_semantics_audit.json")
    claim_audit = _read_json(artifact_dir / "claim_support_audit.json")
    public_manifest = _public_manifest(manifest)

    payload: dict[str, Any] = {
        "ok": True,
        "status": "pass",
        "schema_version": "tradingagents_readonly_analysis_api_v1",
        "readonly_only": True,
        "not_order": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "production_trade_enabled": False,
        "artifact_dir": str(artifact_dir),
        "run_id": manifest.get("run_id"),
        "signal_asof": manifest.get("signal_asof"),
        "target_date": manifest.get("target_date"),
        "source": manifest.get("source") or {},
        "manifest": public_manifest,
        "sanitized_report": sanitized_report,
        "forbidden_semantics_audit": _public_forbidden_audit(forbidden_audit),
        "claim_support_audit": {
            "ok": claim_audit.get("ok"),
            "claim_count": claim_audit.get("claim_count"),
            "notes": claim_audit.get("notes"),
        },
        "validation": _validation_summary(validation),
        "raw_files_included": False,
        "raw_files_policy": "review_only_source_files_are_not_returned_by_get_api",
    }
    if include_markdown:
        payload["sanitized_report_markdown"] = _read_text(artifact_dir / "sanitized_report.md")
    return payload
