"""Artifact-backed, GET-only model and strategy comparison catalog."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_ROOT = ROOT / "data_tw/artifacts/readonly_model_strategy_comparison/v1"
LATEST_PATH = ARTIFACT_ROOT / "latest.json"


class ReadonlyModelStrategyComparisonError(Exception):
    """Raised when the static comparison catalog cannot be served safely."""

    def __init__(self, status: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details or {}


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def _resolve_repo_path(value: str) -> Path:
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ReadonlyModelStrategyComparisonError(
            "path_outside_root", "Comparison artifact path is outside the repository", {"path": value}
        )
    return path


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise ReadonlyModelStrategyComparisonError(
            "missing_artifact", "Missing readonly comparison artifact", {"path": _rel(path)}
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReadonlyModelStrategyComparisonError(
            "invalid_artifact", "Readonly comparison artifact is not valid JSON", {"path": _rel(path)}
        ) from exc
    if not isinstance(payload, dict):
        raise ReadonlyModelStrategyComparisonError(
            "invalid_artifact", "Readonly comparison artifact must be a JSON object", {"path": _rel(path)}
        )
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ReadonlyModelStrategyComparisonError(
            "missing_artifact", "Cannot read readonly comparison artifact", {"path": _rel(path)}
        ) from exc
    return digest.hexdigest()


def _require_hash(path: Path, expected: str, *, source_id: str) -> None:
    if not expected or len(expected) != 64:
        raise ReadonlyModelStrategyComparisonError(
            "invalid_checksum", "Comparison source has no valid SHA-256", {"source_id": source_id}
        )
    actual = _sha256(path)
    if actual != expected:
        raise ReadonlyModelStrategyComparisonError(
            "checksum_failed",
            "Readonly comparison source checksum validation failed",
            {"source_id": source_id, "path": _rel(path), "expected": expected, "actual": actual},
        )


def _load_catalog() -> tuple[dict[str, Any], dict[str, Any], dict[str, Path]]:
    pointer = _load_json(LATEST_PATH)
    if pointer.get("artifact_type") != "readonly_model_strategy_comparison_catalog_pointer":
        raise ReadonlyModelStrategyComparisonError("invalid_latest_pointer", "Invalid comparison catalog pointer")
    if not (
        pointer.get("readonly_only") is True
        and pointer.get("no_apply") is True
        and pointer.get("runtime_effect") == "none"
        and pointer.get("production_trade_enabled") is False
    ):
        raise ReadonlyModelStrategyComparisonError("unsafe_latest_pointer", "Comparison pointer safety flags are invalid")

    catalog_path = _resolve_repo_path(str(pointer.get("catalog_path") or ""))
    if not catalog_path.is_relative_to(ARTIFACT_ROOT.resolve()):
        raise ReadonlyModelStrategyComparisonError(
            "catalog_outside_readonly_root", "Comparison catalog is outside its readonly artifact root"
        )
    _require_hash(catalog_path, str(pointer.get("catalog_sha256") or ""), source_id="catalog")
    catalog = _load_json(catalog_path)
    if catalog.get("schema_version") != "readonly_model_strategy_comparison_catalog_v1":
        raise ReadonlyModelStrategyComparisonError("invalid_catalog", "Unsupported comparison catalog schema")
    if not (
        catalog.get("readonly_only") is True
        and catalog.get("no_apply") is True
        and catalog.get("runtime_effect") == "none"
        and catalog.get("production_trade_enabled") is False
    ):
        raise ReadonlyModelStrategyComparisonError("unsafe_catalog", "Comparison catalog safety flags are invalid")

    source_paths: dict[str, Path] = {}
    sources = catalog.get("sources") or {}
    if not isinstance(sources, dict) or not sources:
        raise ReadonlyModelStrategyComparisonError("invalid_catalog", "Comparison catalog has no static sources")
    for source_id, source in sources.items():
        if not isinstance(source, dict):
            raise ReadonlyModelStrategyComparisonError(
                "invalid_catalog", "Comparison source entry is invalid", {"source_id": source_id}
            )
        source_path = _resolve_repo_path(str(source.get("path") or ""))
        if not source_path.exists() or not source_path.is_file():
            raise ReadonlyModelStrategyComparisonError(
                "missing_artifact", "Missing readonly comparison source", {"source_id": source_id, "path": _rel(source_path)}
            )
        _require_hash(source_path, str(source.get("sha256") or ""), source_id=str(source_id))
        source_paths[str(source_id)] = source_path

    manifest = _load_json(source_paths["b19r2r_manifest"])
    validator = _load_json(source_paths["b19r2r_validator"])
    review = _load_json(source_paths["b19r2r_independent_review"])
    legacy_review = _load_json(source_paths["legacy_static_safety_review"])
    manifest_sha256 = str((sources.get("b19r2r_manifest") or {}).get("sha256") or "")
    validator_sha256 = str((sources.get("b19r2r_validator") or {}).get("sha256") or "")
    reviewed_version = review.get("reviewed_version") or {}
    if validator.get("status") != "PASS" or validator.get("historical_replay") is not True:
        raise ReadonlyModelStrategyComparisonError("validator_not_passed", "B19R2R historical replay validator is not PASS")
    if review.get("verdict") != "PASS_WITH_FINDINGS" or (review.get("blocking_findings") or []):
        raise ReadonlyModelStrategyComparisonError("review_not_accepted", "B19R2R independent review is not accepted")
    if not (
        validator.get("manifest_sha256") == manifest_sha256
        and reviewed_version.get("manifest_sha256") == manifest_sha256
        and reviewed_version.get("validator_result_sha256") == validator_sha256
    ):
        raise ReadonlyModelStrategyComparisonError(
            "lineage_binding_failed", "Validator or independent review is not bound to the catalogued B19R2R manifest"
        )
    safety = manifest.get("safety") or {}
    if not (
        manifest.get("historical_replay") is True
        and manifest.get("prospective_pit_anchor") is False
        and safety.get("prospective_ledger_append") is False
        and safety.get("latest_or_provider_write") is False
        and safety.get("baseline_or_production_change") is False
        and safety.get("production_allowed") is False
    ):
        raise ReadonlyModelStrategyComparisonError(
            "unsafe_source_manifest", "B19R2R source manifest does not preserve the readonly historical boundary"
        )
    if not (
        (review.get("disposition") or {}).get("baseline_admission_allowed") is False
        and (review.get("disposition") or {}).get("production_activation_allowed") is False
    ):
        raise ReadonlyModelStrategyComparisonError(
            "unsafe_review_disposition", "Independent review does not prohibit baseline admission and production activation"
        )
    if legacy_review.get("ok") is not True or legacy_review.get("endpoint_get_only") is not True:
        raise ReadonlyModelStrategyComparisonError("legacy_review_not_passed", "Legacy strategy safety review is not PASS")
    return catalog, pointer, source_paths


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    except OSError as exc:
        raise ReadonlyModelStrategyComparisonError(
            "missing_artifact", "Cannot read readonly comparison CSV", {"path": _rel(path)}
        ) from exc


def _float(row: dict[str, str], key: str) -> float | None:
    value = row.get(key)
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _int(row: dict[str, str], key: str) -> int | None:
    value = _float(row, key)
    return int(value) if value is not None else None


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0.0):
        return None
    return numerator / denominator


def _gate_diagnostics(rows: list[dict[str, str]]) -> dict[str, Any]:
    by_gate = {str(row.get("gate")): row for row in rows}

    def item(gate: str) -> dict[str, Any] | None:
        row = by_gate.get(gate)
        if row is None:
            return None
        return {
            "gate": gate,
            "measured_value": _float(row, "measured_value"),
            "operator": row.get("operator"),
            "threshold": _float(row, "threshold"),
            "status": row.get("status"),
            "admission_effect": row.get("baseline_admission_effect"),
        }

    failed = [str(row.get("gate")) for row in rows if row.get("status") == "FAIL"]
    return {
        "joint_status": "FAIL_ALL_JOINT_CONFIRMATION_GATES_AS_HISTORICAL_DIAGNOSTIC",
        "admission_effect": "NONE_RETROSPECTIVE_DIAGNOSTIC_ONLY",
        "bootstrap_95pct_lower_bound": item("confirmation_paired_moving_block_bootstrap_95pct_lower_bound"),
        "negative_twii20_regime_return_delta": item("negative_twii20_regime_return_delta"),
        "concentration": {
            "top5_abs_contribution_share": item("top5_abs_contribution_share"),
            "top5_abs_contribution_share_vs_a_delta": item("top5_abs_contribution_share_vs_a_delta"),
            "abs_contribution_hhi": item("abs_contribution_hhi"),
            "abs_contribution_hhi_vs_a_delta": item("abs_contribution_hhi_vs_a_delta"),
        },
        "failed_gate_ids": failed,
    }


def _metric_result(
    combination: dict[str, Any],
    model: dict[str, Any],
    strategy: dict[str, Any],
    window: dict[str, Any],
    metric_rows: list[dict[str, str]],
    rank_rows: list[dict[str, str]],
) -> dict[str, Any]:
    method = str(combination.get("metric_method") or "")
    metric = next((row for row in metric_rows if row.get("method") == method), None)
    rank = next((row for row in rank_rows if row.get("method") == method), None)
    if metric is None or rank is None:
        raise ReadonlyModelStrategyComparisonError(
            "missing_metric_row", "Static comparison metric row is missing", {"metric_method": method}
        )
    return {
        "combination_id": combination["combination_id"],
        "model_id": model["model_id"],
        "model_display_name": model["display_name"],
        "model_role": model["role"],
        "strategy_id": strategy["strategy_id"],
        "strategy_display_name": strategy["display_name"],
        "window_id": window["window_id"],
        "window": {"start": window["start"], "end": window["end"], "trading_day_count": window["trading_day_count"]},
        "metrics": {
            "final_equity": _float(metric, "final_equity"),
            "net_return": _float(metric, "net_return"),
            "max_drawdown": _float(metric, "max_drawdown"),
            "turnover": _float(metric, "turnover"),
            "buy_count": _int(metric, "buy_count"),
            "sell_count": _int(metric, "sell_count"),
            "action_count": _int(metric, "action_count"),
            "skip_count": _int(metric, "skip_count"),
            "fee_tax": _float(metric, "fee_tax"),
            "top1_abs_contribution_share": _float(metric, "top1_abs_contribution_share"),
            "top5_abs_contribution_share": _float(metric, "top5_abs_contribution_share"),
            "abs_contribution_hhi": _float(metric, "abs_contribution_hhi"),
            "fallback_count": _int(metric, "fallback_count"),
            "pending_count": _int(metric, "pending_count"),
            "mean_rank_ic_continuous": _float(rank, "mean_rank_ic_continuous"),
            "mean_ndcg_at_10": _float(rank, "mean_ndcg_at_10"),
        },
        "status": combination["status"],
        "gate_status": combination["gate_status"],
        "validator_status": combination["validator_status"],
        "independent_review_status": combination["independent_review_status"],
        "historical_replay": True,
        "prospective_pit_anchor": False,
        "no_apply": True,
        "runtime_effect": "none",
    }


def load_readonly_model_strategy_comparison(
    *, model_id: str | None = None, strategy_id: str | None = None, window_id: str | None = None
) -> dict[str, Any]:
    """Return one audited static selection and its same-window comparison peers."""
    catalog, pointer, sources = _load_catalog()
    default = catalog.get("default_selection") or {}
    selected_model_id = model_id or str(default.get("model_id") or "")
    selected_strategy_id = strategy_id or str(default.get("strategy_id") or "")
    selected_window_id = window_id or str(default.get("window_id") or "")

    models = {str(item.get("model_id")): item for item in catalog.get("models", [])}
    strategies = {str(item.get("strategy_id")): item for item in catalog.get("strategies", [])}
    windows = {str(item.get("window_id")): item for item in catalog.get("windows", [])}
    if selected_model_id not in models:
        raise ReadonlyModelStrategyComparisonError("unknown_model", "Model is not present in the audited comparison catalog", {"model_id": selected_model_id})
    if selected_strategy_id not in strategies:
        raise ReadonlyModelStrategyComparisonError("unknown_strategy", "Strategy is not present in the audited comparison catalog", {"strategy_id": selected_strategy_id})
    if selected_window_id not in windows:
        raise ReadonlyModelStrategyComparisonError("unknown_window", "Window is not present in the audited comparison catalog", {"window_id": selected_window_id})
    strategy = strategies[selected_strategy_id]
    if strategy.get("comparison_selectable") is not True:
        raise ReadonlyModelStrategyComparisonError(
            "incompatible_legacy_lineage",
            "Legacy strategy has no audited combination with the selected current model",
            {
                "model_id": selected_model_id,
                "strategy_id": selected_strategy_id,
                "lineage": strategy.get("lineage"),
                "incompatibility_reason": strategy.get("incompatibility_reason"),
            },
        )

    combinations = list(catalog.get("combinations") or [])
    selected_combination = next(
        (
            item
            for item in combinations
            if item.get("model_id") == selected_model_id
            and item.get("strategy_id") == selected_strategy_id
            and item.get("window_id") == selected_window_id
            and item.get("comparison_selectable") is True
        ),
        None,
    )
    if selected_combination is None:
        raise ReadonlyModelStrategyComparisonError(
            "combination_not_audited",
            "No checksum-verified static artifact exists for this model, strategy, and window",
            {"model_id": selected_model_id, "strategy_id": selected_strategy_id, "window_id": selected_window_id},
        )

    metric_rows = _read_csv_rows(sources["paired_metrics"])
    rank_rows = _read_csv_rows(sources["rank_metrics"])
    gate_rows = _read_csv_rows(sources["gate_diagnostics"])
    peers = [
        item
        for item in combinations
        if item.get("strategy_id") == selected_strategy_id
        and item.get("window_id") == selected_window_id
        and item.get("comparison_selectable") is True
    ]
    comparison = [
        _metric_result(item, models[str(item["model_id"])], strategy, windows[selected_window_id], metric_rows, rank_rows)
        for item in peers
    ]
    result = next(item for item in comparison if item["combination_id"] == selected_combination["combination_id"])
    by_model = {item["model_id"]: item for item in comparison}
    a_result = by_model.get("model_a_only")
    ab_result = by_model.get("model_a_plus_b_b19r2r")
    delta = None
    if a_result and ab_result:
        delta = {
            "net_return_b_minus_a": ab_result["metrics"]["net_return"] - a_result["metrics"]["net_return"],
            "max_drawdown_b_minus_a": ab_result["metrics"]["max_drawdown"] - a_result["metrics"]["max_drawdown"],
            "turnover_ratio_b_over_a": _ratio(ab_result["metrics"]["turnover"], a_result["metrics"]["turnover"]),
            "fee_tax_ratio_b_over_a": _ratio(ab_result["metrics"]["fee_tax"], a_result["metrics"]["fee_tax"]),
            "joint_historical_gate": "FAIL_ALL_JOINT_CONFIRMATION_GATES_AS_HISTORICAL_DIAGNOSTIC",
            "admission_effect": "NONE_RETROSPECTIVE_DIAGNOSTIC_ONLY",
        }

    return {
        "ok": True,
        "schema_version": "readonly_model_strategy_comparison_api_v1",
        "readonly_only": True,
        "no_apply": True,
        "runtime_effect": "none",
        "catalog": {
            "models": catalog.get("models", []),
            "strategies": catalog.get("strategies", []),
            "windows": catalog.get("windows", []),
            "combinations": combinations,
        },
        "selected": {
            "model_id": selected_model_id,
            "strategy_id": selected_strategy_id,
            "window_id": selected_window_id,
            "combination_id": selected_combination["combination_id"],
        },
        "result": result,
        "comparison": {"results": comparison, "delta": delta, "diagnostics": _gate_diagnostics(gate_rows)},
        "status": {
            "selection_changes_display_only": True,
            "can_apply": False,
            "baseline_admission_allowed": False,
            "production_activation_allowed": False,
            "prospective_confirmation_passed": False,
            "historical_artifact_validator": "PASS",
            "independent_review": "PASS_WITH_FINDINGS",
        },
        "safety": {
            "http_method": "GET_ONLY",
            "reads_static_checksum_verified_artifacts_only": True,
            "dynamic_replay": False,
            "training_or_tuning": False,
            "paper_portfolio_write": False,
            "runtime_write": False,
            "latest_or_provider_write": False,
            "baseline_or_production_change": False,
            "broker_or_order_write": False,
        },
        "sources": {
            "catalog_pointer": _rel(LATEST_PATH),
            "catalog": str(pointer["catalog_path"]),
            "catalog_sha256": pointer["catalog_sha256"],
            "verified_source_count": len(sources),
        },
    }
