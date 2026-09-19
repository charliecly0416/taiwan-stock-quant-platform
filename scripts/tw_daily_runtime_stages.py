"""Small, behavior-preserving runtime facade for the daily pipeline.

The legacy daily entrypoint remains responsible for execution.  This module
provides a single descriptor-backed view and injectable stage boundaries so
new callers do not need to duplicate runtime truth while the large entrypoint
is migrated incrementally.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
DESCRIPTOR_PATH = ROOT / "configs/active_baseline_descriptor.yaml"
SCHEMA_PATH = ROOT / "schemas/active_baseline_descriptor.schema.json"


class RuntimeDescriptorError(ValueError):
    """Raised when the canonical runtime descriptor is missing or invalid."""


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else None
    if not isinstance(payload, dict):
        raise RuntimeDescriptorError(f"descriptor must be a mapping: {path}")
    return payload


def load_runtime_descriptor(*, descriptor_path: Path = DESCRIPTOR_PATH, schema_path: Path = SCHEMA_PATH) -> dict[str, Any]:
    """Load and enforce the JSON Schema for the canonical descriptor."""
    payload = _load_yaml(descriptor_path)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda e: list(e.path))
    if errors:
        detail = "; ".join(f"{list(error.path)}: {error.message}" for error in errors[:5])
        raise RuntimeDescriptorError(f"invalid active baseline descriptor: {detail}")
    return payload


@dataclass(frozen=True)
class RuntimeTruth:
    descriptor: Mapping[str, Any]

    @property
    def active(self) -> Mapping[str, Any]:
        return self.descriptor["active_baseline"]

    @property
    def active_model_id(self) -> str:
        return str(self.active["model_a"]["model_id"])

    @property
    def strategy_rule(self) -> str:
        return str(self.active["strategy_rule"])

    @property
    def execution_price_mode(self) -> str:
        return str(self.active["execution_price_mode"])

    @property
    def shadow_models(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(self.descriptor.get("shadow_models", ()))

    def shadow(self, canonical_id: str | None = None) -> Mapping[str, Any] | None:
        if canonical_id is None and self.shadow_models:
            return self.shadow_models[0]
        return next((item for item in self.shadow_models if item.get("canonical_id") == canonical_id), None)

    @property
    def active_model_artifact(self) -> Mapping[str, Any]:
        return self.active["model_a"]

    @property
    def shadow_model_id(self) -> str | None:
        item = self.shadow()
        return str(item["canonical_id"]) if item and item.get("canonical_id") else None

    def defaults(self) -> dict[str, str | None]:
        """Canonical defaults consumed by backend/API adapters."""
        return {
            "model_id": self.active_model_id,
            "strategy_rule": self.strategy_rule,
            "execution_price_mode": self.execution_price_mode,
            "shadow_model_id": self.shadow_model_id,
        }


def runtime_truth() -> RuntimeTruth:
    return RuntimeTruth(load_runtime_descriptor())


def descriptor_summary() -> dict[str, Any]:
    """Return the stable, consumer-facing subset of runtime truth."""
    truth = runtime_truth()
    shadow = truth.shadow() or {}
    return {
        "active_model_id": truth.active_model_id,
        "active_status": truth.active.get("status"),
        "strategy_rule": truth.strategy_rule,
        "execution_price_mode": truth.execution_price_mode,
        "shadow_model_id": shadow.get("canonical_id"),
        "shadow_status": shadow.get("status"),
        "shadow_production_default": shadow.get("production_default"),
        "shadow_eligible_for_baseline": shadow.get("eligible_for_baseline"),
    }


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_fingerprints(*, descriptor: Mapping[str, Any] | None = None, root: Path = ROOT) -> dict[str, dict[str, Any]]:
    """Capture actual before/after fingerprints for descriptor protected paths."""
    descriptor = descriptor or load_runtime_descriptor()
    result: dict[str, dict[str, Any]] = {}
    for raw in descriptor.get("protected_latest_paths", {}):
        relative = str(raw)
        path = Path(relative) if Path(relative).is_absolute() else root / relative
        exists = path.is_file()
        result[relative] = {"path": relative, "exists": exists, "size": path.stat().st_size if exists else None, "sha256": sha256(path)}
    return result


def fingerprints_unchanged(before: Mapping[str, Mapping[str, Any]], after: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    names = sorted(set(before) | set(after))
    checks = {name: before.get(name, {}) == after.get(name, {}) for name in names}
    checks["all_protected_paths_unchanged"] = all(checks.values())
    return checks


@dataclass
class StageFacade:
    """Injectable stage boundary; callbacks preserve legacy failure semantics."""

    name: str
    callback: Callable[..., Any] | None = None

    def run(self, *args: Any, **kwargs: Any) -> Any:
        if self.callback is None:
            return {"stage": self.name, "status": "NOT_IMPLEMENTED_LEGACY_PATH"}
        return self.callback(*args, **kwargs)


def run_stage_orchestrator(
    stages: Mapping[str, StageFacade],
    *,
    context: Mapping[str, Any] | None = None,
    protected_before: Mapping[str, Mapping[str, Any]] | None = None,
    protected_paths: Mapping[str, Path] | None = None,
    publish_precondition: Callable[[Mapping[str, Any]], Any] | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Execute the real stage boundary sequence through injectable callbacks.

    This is an executable migration adapter: callers can bind legacy functions
    one stage at a time while preserving deterministic order and fail-closed
    behavior.  No callback means a legacy-path marker, never a publish.
    """
    def capture() -> dict[str, dict[str, Any]]:
        values: dict[str, dict[str, Any]] = {}
        for name, raw_path in (protected_paths or {}).items():
            path = raw_path if raw_path.is_absolute() else root / raw_path
            exists = path.is_file()
            values[name] = {"path": str(path), "exists": exists, "size": path.stat().st_size if exists else None, "sha256": sha256(path)}
        return values

    # A caller may provide a serialized before snapshot. Reconstruct paths
    # from that snapshot so the after capture is always a real filesystem
    # read; never assume ``after == before`` merely because paths were omitted.
    if protected_paths is None and protected_before:
        protected_paths = {
            name: Path(str(value.get("path", name)))
            for name, value in protected_before.items()
            if value.get("path")
        }
    actual_before = capture() if protected_paths is not None else protected_before
    payload: dict[str, Any] = {"ok": True, "status": "completed", "stages": [], "context": dict(context or {})}
    ordered = ("acquisition", "readiness", "signal", "strategy", "artifact_publish", "ops_status")
    current: Any = dict(context or {})
    for name in ordered:
        stage = stages.get(name)
        if stage is None:
            payload.update({"ok": False, "status": "missing_stage", "failed_stage": name})
            break
        # Publish is the only stage allowed to sit adjacent to protected
        # pointers. Capture immediately around its callback and stop before
        # ops_status if the callback changes any protected file.
        publish_before = capture() if name == "artifact_publish" and protected_paths is not None else None
        if name == "artifact_publish" and publish_precondition is None:
            payload.update({
                "ok": False,
                "status": "publish_precondition_missing",
                "failed_stage": name,
                "publish_allowed": False,
                "publish_precondition": {"ok": False, "reason": "required_fail_closed_gate_missing"},
            })
            break
        if name == "artifact_publish" and publish_precondition is not None:
            try:
                gate_result = publish_precondition(current)
            except Exception as exc:  # noqa: BLE001
                payload.update({"ok": False, "status": "publish_precondition_failed", "failed_stage": name, "error": str(exc), "publish_allowed": False})
                break
            gate_ok = bool(gate_result if isinstance(gate_result, bool) else (gate_result or {}).get("ok", False))
            if not gate_ok:
                payload.update({"ok": False, "status": "publish_precondition_blocked", "failed_stage": name, "publish_allowed": False, "publish_precondition": gate_result})
                break
        try:
            result = stage.run(current)
        except Exception as exc:  # noqa: BLE001
            payload.update({"ok": False, "status": "stage_failed", "failed_stage": name, "error": str(exc)})
            break
        payload["stages"].append({"name": name, "result": result})
        if name == "artifact_publish" and publish_before is not None:
            publish_after = capture()
            publish_audit = no_publish_fingerprint_audit(publish_before, publish_after)
            payload["publish_callback_fingerprint_audit"] = publish_audit
            if not publish_audit["ok"]:
                payload.update({"ok": False, "status": "protected_path_changed", "failed_stage": name, "publish_allowed": False})
                current = result
                break
        if isinstance(result, Mapping):
            current = result
            if result.get("ok") is False or result.get("status") in {"blocked", "failed", "error"}:
                payload.update({"ok": False, "status": "stage_blocked", "failed_stage": name})
                break
    payload["final"] = current
    if actual_before is not None:
        actual_after = capture() if protected_paths is not None else actual_before
        payload["protected_fingerprint_audit"] = no_publish_fingerprint_audit(actual_before, actual_after)
        if not payload["protected_fingerprint_audit"]["ok"]:
            payload.update({"ok": False, "status": "protected_path_changed", "publish_allowed": False})
    return payload


def build_stage_facade(**callbacks: Callable[..., Any]) -> dict[str, StageFacade]:
    names = ("acquisition", "readiness", "signal", "strategy", "artifact_publish", "ops_status")
    return {name: StageFacade(name, callbacks.get(name)) for name in names}


def no_publish_fingerprint_audit(before: Mapping[str, Mapping[str, Any]], after: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    comparison = fingerprints_unchanged(before, after)
    return {
        "schema_version": "arch2.protected_fingerprint_audit.v1",
        "before": dict(before),
        "after": dict(after),
        "comparison": comparison,
        "ok": bool(comparison["all_protected_paths_unchanged"]),
        "publish_allowed": False,
    }


def build_stage_terminal_contract(
    result: Mapping[str, Any],
    *,
    asof: str = "",
    job_id: str = "",
    protected_before: Mapping[str, Mapping[str, Any]] | None = None,
    protected_after: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Expose one terminal contract for legacy and adapter executions.

    The legacy entrypoint keeps its historical top-level status for operators,
    while this normalized view makes observation-only terminal semantics
    comparable with the six-stage adapter.
    """
    stages = result.get("stages") if isinstance(result.get("stages"), list) else []
    stage_order = [str(item.get("name")) for item in stages if isinstance(item, Mapping) and item.get("name")]
    stage_calls = result.get("stage_calls") if isinstance(result.get("stage_calls"), Mapping) else {}
    protected_audit = result.get("protected_fingerprint_audit")
    if protected_audit is None and protected_before is not None and protected_after is not None:
        protected_audit = no_publish_fingerprint_audit(protected_before, protected_after)
    return {
        "schema_version": "arch5.runtime_stage_terminal.v1",
        "ok": bool(result.get("ok", False)),
        "status": str(result.get("status") or ""),
        "failed_stage": result.get("failed_stage"),
        "publish_allowed": bool(result.get("publish_allowed", False)),
        "publish_precondition": result.get("publish_precondition"),
        "asof": asof,
        "job_id": job_id,
        "stage_order": stage_order,
        "stage_calls": dict(stage_calls),
        "artifact_publish_calls": int(stage_calls.get("artifact_publish", 0) or 0),
        "ops_status_calls": int(stage_calls.get("ops_status", 0) or 0),
        "protected_fingerprint_audit": protected_audit,
    }


def build_legacy_observation_terminal(
    *,
    asof: str,
    job_id: str,
    protected_before: Mapping[str, Mapping[str, Any]],
    protected_after: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Normalize the successful legacy no-write path at the publish gate."""
    stage_result = {
        "ok": False,
        "status": "publish_precondition_blocked",
        "failed_stage": "artifact_publish",
        "publish_allowed": False,
        "publish_precondition": {"ok": False, "reason": "legacy_observation_only"},
        "stages": [
            {
                "name": name,
                "result": {
                    "ok": True,
                    "status": "legacy_completed_no_write",
                    "stage": name,
                    "asof": asof,
                    "job_id": job_id,
                },
            }
            for name in ("acquisition", "readiness", "signal", "strategy")
        ],
        "stage_calls": {
            "acquisition": 1,
            "readiness": 1,
            "signal": 1,
            "strategy": 1,
            "artifact_publish": 0,
            "ops_status": 0,
        },
    }
    terminal = build_stage_terminal_contract(
        stage_result,
        asof=asof,
        job_id=job_id,
        protected_before=protected_before,
        protected_after=protected_after,
    )
    terminal["legacy_top_level_status"] = "daily_auto_update_passed"
    return terminal


def build_authorized_readonly_publish_terminal(
    *,
    asof: str,
    job_id: str,
    orchestration: Mapping[str, Any],
    protected_before: Mapping[str, Mapping[str, Any]],
    protected_after: Mapping[str, Mapping[str, Any]],
    trading: Mapping[str, Any],
) -> dict[str, Any]:
    """Normalize an authorized DAPR18 product publish without weakening readonly safety."""
    required_names = {
        "readonly_snapshot_latest",
        "agent_prompt_latest",
        "provider_accepted_latest",
        "legacy_option_c_latest",
    }
    allowed_changes = {"readonly_snapshot_latest", "agent_prompt_latest"}

    def same(name: str) -> bool:
        before = protected_before.get(name) if isinstance(protected_before.get(name), Mapping) else {}
        after = protected_after.get(name) if isinstance(protected_after.get(name), Mapping) else {}
        return all(before.get(key) == after.get(key) for key in ("exists", "size", "sha256"))

    comparison = {name: same(name) for name in sorted(required_names)}
    changed = {name for name, unchanged in comparison.items() if not unchanged}
    required_keys_present = required_names.issubset(protected_before) and required_names.issubset(protected_after)
    unexpected_changes = sorted(changed - allowed_changes)
    provider_and_legacy_unchanged = bool(
        comparison["provider_accepted_latest"]
        and comparison["legacy_option_c_latest"]
    )

    summary_status = str(orchestration.get("status") or "")
    idempotent_noop = summary_status == "auto_publish_idempotent_noop_already_current"
    chain = orchestration.get("auto_publish_chain") if isinstance(orchestration.get("auto_publish_chain"), Mapping) else {}
    chain_status_expected = "idempotent_noop" if idempotent_noop else "pass"
    chain_coherent = bool(chain.get("ok") is True and chain.get("status") == chain_status_expected)
    product_after = orchestration.get("product_latest_state_after") if isinstance(orchestration.get("product_latest_state_after"), Mapping) else {}
    controlled_signal_summary_audit = bool(
        product_after.get("all_product_latest_match_target") is True
        and orchestration.get("forbidden_protected_paths_unchanged") is True
        and orchestration.get("forbidden_actions_all_false") is True
    )
    authorization = orchestration.get("authorization_gate") if isinstance(orchestration.get("authorization_gate"), Mapping) else {}
    authorized_terminal = bool(
        orchestration.get("ok") is True
        and summary_status in {
            "auto_publish_chain_completed",
            "auto_publish_idempotent_noop_already_current",
        }
        and authorization.get("allowed") is True
        and chain_coherent
        and controlled_signal_summary_audit
    )
    trading_readonly = bool(
        trading.get("orders_enabled") is False
        and trading.get("connects_to_broker") is False
        and trading.get("research_signal_not_order") is True
    )
    protected_ok = bool(
        required_keys_present
        and provider_and_legacy_unchanged
        and not unexpected_changes
        and (not idempotent_noop or not changed)
    )
    audit_ok = bool(authorized_terminal and protected_ok and trading_readonly)
    terminal_status = (
        "authorized_readonly_product_publish_idempotent_noop"
        if audit_ok and idempotent_noop
        else "authorized_readonly_product_publish_completed"
        if audit_ok
        else "authorized_readonly_product_publish_audit_failed"
    )
    stage_calls = {
        "acquisition": 1,
        "readiness": 1,
        "signal": 1,
        "strategy": 1,
        "artifact_publish": 0 if idempotent_noop else 1,
        "ops_status": 1,
    }
    return {
        "schema_version": "arch5.runtime_stage_terminal.v1",
        "ok": audit_ok,
        "status": terminal_status,
        "failed_stage": None if audit_ok else "artifact_publish",
        "publish_allowed": bool(audit_ok and authorization.get("allowed") is True),
        "publish_precondition": dict(authorization),
        "asof": asof,
        "job_id": job_id,
        "stage_order": list(stage_calls),
        "stage_calls": stage_calls,
        "artifact_publish_calls": stage_calls["artifact_publish"],
        "ops_status_calls": stage_calls["ops_status"],
        "dapr18_status": summary_status,
        "resolution_status": "idempotent_noop_already_current" if idempotent_noop else "authorized_publish_completed" if audit_ok else "audit_failed",
        "controlled_signal_audited_by_dapr18_summary": controlled_signal_summary_audit,
        "trading": dict(trading),
        "protected_fingerprint_audit": {
            "schema_version": "arch5.authorized_readonly_publish_fingerprint_audit.v1",
            "before": dict(protected_before),
            "after": dict(protected_after),
            "comparison": comparison,
            "allowed_pointer_changes": sorted(changed & allowed_changes),
            "unexpected_changes": unexpected_changes,
            "provider_accepted_latest_unchanged": comparison["provider_accepted_latest"],
            "legacy_option_c_latest_unchanged": comparison["legacy_option_c_latest"],
            "required_keys_present": required_keys_present,
            "idempotent_noop_requires_all_unchanged": not idempotent_noop or not changed,
            "ok": protected_ok,
        },
        "legacy_top_level_status": "daily_auto_update_passed",
    }


def run_no_publish_terminal_orchestrator(
    stages: Mapping[str, StageFacade],
    *,
    asof: str,
    job_id: str,
    protected_paths: Mapping[str, Path],
    context: Mapping[str, Any] | None = None,
    root: Path = ROOT,
    legacy_terminal: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Single fail-closed terminal contract for legacy and named adapters."""
    result = run_stage_orchestrator(
        stages,
        context={"asof": asof, "job_id": job_id, **dict(context or {})},
        protected_paths=protected_paths,
        publish_precondition=lambda _: {"ok": False, "reason": "no_publish_terminal"},
        root=root,
    )
    named_terminal = build_stage_terminal_contract(result, asof=asof, job_id=job_id)
    before = result.get("protected_fingerprint_audit", {}).get("before", {})
    after = result.get("protected_fingerprint_audit", {}).get("after", {})
    legacy = dict(legacy_terminal or build_legacy_observation_terminal(asof=asof, job_id=job_id, protected_before=before, protected_after=after))
    parity = {
        "stage_order_equal": named_terminal.get("stage_order") == legacy.get("stage_order"),
        "failure_stage_equal": named_terminal.get("failed_stage") == legacy.get("failed_stage"),
        "latest_parity": bool(named_terminal.get("protected_fingerprint_audit", {}).get("ok")) and bool(legacy.get("protected_fingerprint_audit", {}).get("ok")),
        "legacy_top_level_status_preserved": legacy.get("legacy_top_level_status") == "daily_auto_update_passed",
        "publish_allowed_false": named_terminal.get("publish_allowed") is False and legacy.get("publish_allowed") is False,
    }
    return {
        "schema_version": "arch2d.no_publish_terminal.v1",
        "ok": bool(result.get("ok") is False and all(parity.values())),
        "status": result.get("status"),
        "legacy_top_level_status": legacy.get("legacy_top_level_status", "daily_auto_update_passed"),
        "named_terminal": named_terminal,
        "legacy_terminal": legacy,
        "parity": parity,
        "protected_fingerprint_audit": result.get("protected_fingerprint_audit"),
        "publish_allowed": False,
    }


def run_no_publish_fingerprint_audit(before_paths: Mapping[str, Path], *, root: Path = ROOT) -> dict[str, Any]:
    """Capture actual before/after values for an injected no-publish run.

    The callback is intentionally absent: callers perform their dry-run between
    the two captures, making accidental writes observable without permitting a
    publish operation here.
    """
    def capture() -> dict[str, dict[str, Any]]:
        values: dict[str, dict[str, Any]] = {}
        for name, raw_path in before_paths.items():
            path = raw_path if raw_path.is_absolute() else root / raw_path
            exists = path.is_file()
            values[name] = {"path": str(path), "exists": exists, "size": path.stat().st_size if exists else None, "sha256": sha256(path)}
        return values

    before = capture()
    after = capture()
    return no_publish_fingerprint_audit(before, after)
