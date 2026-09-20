from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
import joblib

from tw_stock_strategy import CANONICAL_CONFIG, decide_for_model

from .artifacts import ArtifactRef, ArtifactResolver
from .types import ExecutionContext, WorkflowError


TRACK_CONFIG = Path("configs/readonly_model_tracks.yaml")
MODULAR_REGISTRY = Path("configs/tw_modular_registry.yaml")
MODEL_SIGNAL_REGISTRY_ENTRY = "model_signal.readonly_historical_track_adapter"
REFERENCE_REPLAY_SOURCE = Path("scripts/modelb_b19r2r_prospective_confirmation_v3_template.py")
REFERENCE_REPLAY_FREEZE = Path(
    "data_tw/experiments/project_runtime_convergence/"
    "modelb_b19r2r_comparative_evaluation_20260916/"
    "B19R2R_PROSPECTIVE_CONFIRMATION_V3_REPAIR_FREEZE.json"
)
MODEL_A_SOURCE = Path(
    "data_tw/experiments/project_runtime_convergence/"
    "modelb_b19r2r_pretraining_materialization_20260916/"
    "MODEL_A_FULL_CROSS_SECTION.parquet"
)
MODEL_B_SOURCE = Path(
    "data_tw/experiments/project_runtime_convergence/"
    "modelb_b19r2r_retrospective_historical_paired_replay_20260918/"
    "FINAL_MODEL_B_PREDICTIONS.csv"
)
MODEL_B_ARTIFACT = Path(
    "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_training_20260916/"
    "training_output_v1/MODEL_B_B19R2R_LGBM_RANKER.pkl"
)
MODEL_B_TRAINING_MANIFEST = MODEL_B_ARTIFACT.parent / "TRAINING_MANIFEST.json"
FEATURE_78_SOURCE = Path(
    "data_tw/experiments/project_runtime_convergence/"
    "modelb_b19r2r_pretraining_materialization_20260916/FEATURE_ARTIFACT_78_RAW.parquet"
)
FEATURE_SCHEMA = Path(
    "data_tw/experiments/project_runtime_convergence/"
    "modelb_b2_canonical_pit_features_20260913/FEATURE_SCHEMA.json"
)
FEATURE_MATERIALIZATION_STATE = Path(
    "data_tw/experiments/project_runtime_convergence/"
    "modelb_b19r2r_pretraining_materialization_20260916/B19R2R_INPUT_MATERIALIZATION_STATE.json"
)
FEATURE_PIT_AUDIT = FEATURE_78_SOURCE.parent / "PIT_AUDIT.csv"
FEATURE_FREEZE = FEATURE_78_SOURCE.parent / "B19R2R_PREOUTCOME_FREEZE_AMENDMENT_06.json"
EXECUTION_GRID_SOURCE = Path(
    "data_tw/experiments/project_runtime_convergence/"
    "modelb_b19r2r_pretraining_materialization_20260916/"
    "outcome_materialization_v1/sealed_confirmation/CONFIRMATION_EXECUTION_GRID.parquet"
)
INITIAL_CASH = 1_000_000.0
COMMISSION_RATE = 0.001425
SELL_TAX_RATE = 0.003
LOT_SIZE = 10
TARGET_HOLDINGS = 10
COMPARISON_DATES = (
    "2026-08-13", "2026-08-14", "2026-08-17", "2026-08-18", "2026-08-19",
    "2026-08-20", "2026-08-21", "2026-08-24", "2026-08-25", "2026-08-26",
    "2026-08-27", "2026-08-28", "2026-08-31", "2026-09-01",
)
SKIP_STATUS = "SKIPPED_ZERO_OR_INSUFFICIENT_CASH"
FORBIDDEN_SIGNAL_PREFIXES = ("future_", "forward_return", "label_")
IMPLEMENTATION_SOURCES = (
    Path("tw_stock_strategy/top50_exit_one_worst_sell.py"),
    Path("tw_stock_workflow/dual_track.py"),
)
MODEL_A_ADAPTER_ID = "model_a_passthrough_v1"
B19R2R_ADAPTER_ID = "b19r2r_lambdarank_78f_v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(repo_root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(repo_root.resolve()))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def _write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    _write_json(temporary, payload)
    temporary.replace(path)


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)


def _binding(repo_root: Path, path: Path) -> dict[str, Any]:
    absolute = (repo_root / path).resolve()
    if not absolute.is_file():
        raise WorkflowError(f"dual-track source is missing: {path}")
    return {
        "path": _relative(repo_root, absolute),
        "sha256": _sha256(absolute),
        "bytes": absolute.stat().st_size,
    }


def _load_track_registry(repo_root: Path) -> dict[str, Any]:
    path = (repo_root / TRACK_CONFIG).resolve()
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != "tw.readonly_model_tracks.v1":
        raise WorkflowError("readonly model track registry is invalid")
    tracks = payload.get("tracks")
    if not isinstance(tracks, dict) or payload.get("default_track_id") not in tracks:
        raise WorkflowError("readonly model track registry has no valid default")
    defaults = [key for key, value in tracks.items() if value.get("production_default") is True]
    if defaults != [payload["default_track_id"]]:
        raise WorkflowError("readonly model track registry must have exactly one default")
    return payload


def _track_config(repo_root: Path, track_id: str) -> dict[str, Any]:
    registry = _load_track_registry(repo_root)
    try:
        track = dict(registry["tracks"][track_id])
    except KeyError as exc:
        raise WorkflowError(f"unknown readonly model track: {track_id}") from exc
    required = {
        "adapter_id",
        "display_name",
        "model_id",
        "model_family",
        "metric_method",
        "candidate_rank_policy",
        "workflow_policy",
        "framework_role",
        "governance_status",
        "comparison_selectable",
        "virtual_account_eligible",
        "production_default",
    }
    if set(track) != required or track["framework_role"] != "model_track":
        raise WorkflowError(f"invalid readonly model track config: {track_id}")
    return track


def _resolve_track_adapter(config: dict[str, Any]) -> dict[str, Any]:
    adapter_id = str(config.get("adapter_id") or "")
    spec = TRACK_ADAPTERS.get(adapter_id)
    if spec is None:
        raise WorkflowError(f"unknown readonly model track adapter: {adapter_id}")
    identity = {
        "model_id": config.get("model_id"),
        "model_family": config.get("model_family"),
        "candidate_rank_policy": config.get("candidate_rank_policy"),
    }
    expected = {
        "model_id": spec["model_id"],
        "model_family": spec["model_family"],
        "candidate_rank_policy": spec["candidate_rank_policy"],
    }
    if identity != expected:
        raise WorkflowError(f"readonly model track adapter identity mismatch: {adapter_id}")
    return spec


def _model_signal_registry_entry(repo_root: Path) -> dict[str, Any]:
    registry = yaml.safe_load((repo_root / MODULAR_REGISTRY).read_text(encoding="utf-8")) or {}
    entry = ((registry.get("m2_registry") or {}).get("entries") or {}).get(MODEL_SIGNAL_REGISTRY_ENTRY)
    if not isinstance(entry, dict):
        raise WorkflowError("readonly historical model-track registry entry is missing")
    allowed = set(entry.get("allowed_consumers") or [])
    forbidden = set(entry.get("forbidden_consumers") or [])
    if not (
        {"strategy_rule", "replay_execution", "readonly_comparison"}.issubset(allowed)
        and {"frontend_default", "paper_portfolio", "broker", "order"}.issubset(forbidden)
        and entry.get("production_allowed") is False
    ):
        raise WorkflowError("readonly historical model-track registry boundary is invalid")
    return entry


def _adapt_model_a(
    repo_root: Path,
    config: dict[str, Any],
    model_a: pd.DataFrame,
    days: list[str],
    source_bindings: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    model_a["candidate_rank"] = model_a["full_qlib_rank"].astype(int)
    model_a["buy_score"] = pd.to_numeric(model_a["model_a_raw_score"], errors="raise")
    model_a["raw_score"] = model_a["buy_score"]
    return model_a, {
        "candidate_boundary_source": "model_a_full_rank_top50",
        "buy_score_source": "model_a_raw_score",
        "exact_top50_preserved": True,
        "source_artifact": source_bindings["model_a_full_cross_section"]["path"],
        "source_feature_artifact": "model_a_frozen_feature_source",
    }


def _adapt_b19r2r(
    repo_root: Path,
    config: dict[str, Any],
    model_a: pd.DataFrame,
    days: list[str],
    source_bindings: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    model_a, _ = _adapt_model_a(repo_root, config, model_a, days, source_bindings)
    schema = json.loads((repo_root / FEATURE_SCHEMA).read_text(encoding="utf-8"))
    feature_order = list(schema.get("feature_order") or [])
    training = json.loads((repo_root / MODEL_B_TRAINING_MANIFEST).read_text(encoding="utf-8"))
    if (
        len(feature_order) != 78
        or training.get("model_id") != config["model_id"]
        or training.get("feature_count") != 78
        or (training.get("artifacts", {}).get("model") or {}).get("sha256") != _sha256(repo_root / MODEL_B_ARTIFACT)
    ):
        raise WorkflowError("frozen Model B identity or feature schema drifted")
    features = pd.read_parquet(
        repo_root / FEATURE_78_SOURCE,
        columns=["date", "instrument", "signal_asof", "available_at", "feature_raw_complete_78", "raw_missing_features", *feature_order],
    )
    features["date"] = features["date"].astype(str).str[:10]
    features["instrument"] = features["instrument"].astype(str)
    features = features[features.date.isin(days)]
    if len(features) != len(COMPARISON_DATES) * 150 or features.duplicated(["date", "instrument"]).any():
        raise WorkflowError("frozen 78-feature confirmation window shape is invalid")
    if not (
        features.signal_asof.astype(str).str[:10].eq(features.date).all()
        and (pd.to_datetime(features.available_at) <= pd.to_datetime(features.date)).all()
    ):
        raise WorkflowError("frozen 78-feature PIT availability is invalid")
    freeze = json.loads((repo_root / FEATURE_FREEZE).read_text(encoding="utf-8"))
    freeze_sources = {item.get("path"): item.get("sha256") for item in freeze.get("source_bindings", [])}
    if freeze_sources.get(FEATURE_78_SOURCE.as_posix()) != _sha256(repo_root / FEATURE_78_SOURCE):
        raise WorkflowError("frozen 78-feature lineage binding is invalid")
    model = joblib.load(repo_root / MODEL_B_ARTIFACT)
    if list(model.booster_.feature_name()) != feature_order or int(model.booster_.num_trees()) != 120:
        raise WorkflowError("frozen Model B structure or feature order drifted")
    model_a = model_a.merge(
        features[["date", "instrument", "feature_raw_complete_78", "raw_missing_features", *feature_order]],
        on=["date", "instrument"], how="left", validate="one_to_one",
    )
    original_top50 = model_a["full_qlib_rank"].le(50)
    scored = original_top50 & model_a["instrument"].ne("TW7769")
    missing = original_top50 & ~scored
    if not model_a.loc[scored, "feature_raw_complete_78"].eq(True).all():
        raise WorkflowError("comparison window contains an incomplete non-TW7769 original Top50 row")
    if not scored.groupby(model_a["date"]).any().all():
        raise WorkflowError("Model B has no scored original Top50 candidates for a day")
    model_a["model_b_final_raw_score"] = np.nan
    model_a.loc[scored, "model_b_final_raw_score"] = model.predict(model_a.loc[scored, feature_order])
    if not np.isfinite(model_a.loc[scored, "model_b_final_raw_score"].to_numpy(float)).all():
        raise WorkflowError("frozen Model B emitted a nonfinite score")
    legacy = pd.read_csv(repo_root / MODEL_B_SOURCE)
    legacy["date"] = legacy["date"].astype(str).str[:10]
    legacy["instrument"] = legacy["instrument"].astype(str)
    parity = model_a.loc[scored, ["date", "instrument", "model_b_final_raw_score"]].merge(
        legacy[["date", "instrument", "model_b_final_raw_score"]],
        on=["date", "instrument"], suffixes=("_rescored", "_legacy"), validate="one_to_one",
    )
    if len(parity) < 600 or not np.allclose(
        parity["model_b_final_raw_score_rescored"], parity["model_b_final_raw_score_legacy"],
        rtol=0.0, atol=1e-15,
    ):
        raise WorkflowError("frozen Model B scorer parity failed")
    model_a.loc[scored, "buy_score"] = model_a.loc[scored, "model_b_final_raw_score"]
    model_a.loc[scored, "raw_score"] = model_a.loc[scored, "model_b_final_raw_score"]
    model_a.loc[missing, "candidate_rank"] = model_a.loc[missing, "full_qlib_rank"] + 150
    source_bindings.update({
        "model_b_artifact": _binding(repo_root, MODEL_B_ARTIFACT),
        "model_b_training_manifest": _binding(repo_root, MODEL_B_TRAINING_MANIFEST),
        "feature_78_source": _binding(repo_root, FEATURE_78_SOURCE),
        "feature_schema": _binding(repo_root, FEATURE_SCHEMA),
        "feature_materialization_state": _binding(repo_root, FEATURE_MATERIALIZATION_STATE),
        "feature_pit_audit": _binding(repo_root, FEATURE_PIT_AUDIT),
        "feature_freeze": _binding(repo_root, FEATURE_FREEZE),
        "legacy_prediction_parity": _binding(repo_root, MODEL_B_SOURCE),
    })
    return model_a, {
        "candidate_boundary_source": "original_model_a_top50_without_replacement",
        "buy_score_source": "frozen_model_b_rescore_on_pit_complete_original_top50",
        "exact_top50_preserved": False,
        "source_artifact": source_bindings["model_b_artifact"]["path"],
        "source_feature_artifact": "frozen_b19r2r_78_feature_bundle",
    }


TRACK_ADAPTERS = {
    MODEL_A_ADAPTER_ID: {
        "model_id": "e4_frozen_qlib_2018_2022",
        "model_family": "qlib",
        "candidate_rank_policy": "full_rank",
        "run_id": "model_a_frozen_complete_20260813_20260901",
        "artifact_path": Path("configs/readonly_model_track_sources"),
        "manifest_path": Path("configs/readonly_model_track_sources/model_a_passthrough_v1.json"),
        "input_paths": (),
        "loader": _adapt_model_a,
    },
    B19R2R_ADAPTER_ID: {
        "model_id": "modelb_b19r2r_lambdarank_exact50_78f_v2",
        "model_family": "ltr",
        "candidate_rank_policy": "original_top50_exclude_tw7769_no_replacement",
        "run_id": "b19r2r_retrospective_complete_20260813_20260901",
        "artifact_path": Path("configs/readonly_model_track_sources"),
        "manifest_path": Path("configs/readonly_model_track_sources/b19r2r_lambdarank_78f_v1.json"),
        "input_paths": (
            MODEL_B_SOURCE,
            MODEL_B_ARTIFACT,
            MODEL_B_TRAINING_MANIFEST,
            FEATURE_78_SOURCE,
            FEATURE_SCHEMA,
            FEATURE_MATERIALIZATION_STATE,
            FEATURE_PIT_AUDIT,
            FEATURE_FREEZE,
        ),
        "loader": _adapt_b19r2r,
    },
}


def _load_frames(repo_root: Path, track_id: str) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], dict[str, Any]]:
    config = _track_config(repo_root, track_id)
    adapter = _resolve_track_adapter(config)
    adapter_id = config["adapter_id"]
    _model_signal_registry_entry(repo_root)
    model_a = pd.read_parquet(repo_root / MODEL_A_SOURCE).copy()
    grid = pd.read_parquet(repo_root / EXECUTION_GRID_SOURCE).copy()
    for frame in (model_a, grid):
        frame["date"] = frame["date"].astype(str).str[:10]
        frame["instrument"] = frame["instrument"].astype(str)
    grid = grid[grid["date"].isin(COMPARISON_DATES)].copy()
    days = sorted(grid["date"].unique().tolist())
    model_a = model_a[model_a["date"].isin(days)].copy()
    if (
        tuple(days) != COMPARISON_DATES
        or len(model_a) != len(COMPARISON_DATES) * 150
        or len(grid) != len(COMPARISON_DATES) * 150
        or model_a.duplicated(["date", "instrument"]).any()
        or grid.duplicated(["date", "instrument"]).any()
        or not model_a.groupby("date").size().eq(150).all()
        or not grid.groupby("date").size().eq(150).all()
    ):
        raise WorkflowError("dual-track frozen Model A or execution-grid shape is invalid")
    source_bindings = {
        "track_registry": _binding(repo_root, TRACK_CONFIG),
        "modular_registry": _binding(repo_root, MODULAR_REGISTRY),
        "adapter_source_manifest": _binding(repo_root, adapter["manifest_path"]),
        "model_a_full_cross_section": _binding(repo_root, MODEL_A_SOURCE),
        "execution_grid": _binding(repo_root, EXECUTION_GRID_SOURCE),
    }
    for path in IMPLEMENTATION_SOURCES:
        source_bindings[f"implementation_{path.stem}"] = _binding(repo_root, path)
    model_a, adapter_metadata = adapter["loader"](
        repo_root, config, model_a, days, source_bindings
    )

    model_a["score_rank"] = (
        model_a.sort_values(
            ["date", "buy_score", "instrument"],
            ascending=[True, False, True],
            kind="mergesort",
        )
        .groupby("date")
        .cumcount()
        .add(1)
        .sort_index()
    )
    model_a["model_name"] = config["model_id"]
    model_a["model_family"] = config["model_family"]
    model_a["source_artifact"] = adapter_metadata["source_artifact"]
    model_a["source_feature_artifact"] = adapter_metadata["source_feature_artifact"]
    columns = [
        "date", "instrument", "model_name", "model_family", "candidate_rank",
        "buy_score", "raw_score", "score_rank", "full_qlib_rank", "signal_asof",
        "available_at", "source_artifact", "source_model_artifact", "source_feature_artifact",
    ]
    return (
        model_a[columns].sort_values(["date", "candidate_rank"]).reset_index(drop=True),
        grid,
        source_bindings,
        adapter_metadata,
    )


def _write_child_manifest(
    repo_root: Path,
    directory: Path,
    manifest: dict[str, Any],
    files: list[Path],
) -> Path:
    manifest["files"] = {
        path.stem: {
            "path": _relative(repo_root, path),
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in files
    }
    path = directory / "manifest.json"
    _write_json(path, manifest)
    return path


def _materialize_signal_artifact(
    repo_root: Path,
    track_root: Path,
    track_id: str,
    track: dict[str, Any],
    signals: pd.DataFrame,
    source_bindings: dict[str, Any],
    adapter_metadata: dict[str, Any],
    created_at: str,
) -> Path:
    directory = track_root / "model_signal"
    directory.mkdir(parents=True, exist_ok=False)
    signal_path = directory / "signals.csv"
    signals.to_csv(signal_path, index=False)
    schema_path = directory / "schema.json"
    _write_json(schema_path, {"schema_version": "model_signal_contract_v1", "columns": list(signals.columns)})
    coverage_path = directory / "coverage_audit.csv"
    _write_csv(coverage_path, [{
        "date_start": signals.date.min(), "date_end": signals.date.max(),
        "trading_day_count": signals.date.nunique(), "row_count": len(signals),
        "rows_per_day": 150, "duplicate_key_count": 0, "status": "PASS",
    }], ["date_start", "date_end", "trading_day_count", "row_count", "rows_per_day", "duplicate_key_count", "status"])
    forbidden_path = directory / "forbidden_field_audit.csv"
    forbidden = [column for column in signals if column.startswith(FORBIDDEN_SIGNAL_PREFIXES)]
    _write_csv(forbidden_path, [{"forbidden_field_count": len(forbidden), "status": "PASS" if not forbidden else "FAIL"}], ["forbidden_field_count", "status"])
    mapping_path = directory / "legacy_mapping_audit.csv"
    _write_csv(mapping_path, [{
        "track_id": track_id,
        "adapter_id": track["adapter_id"],
        "candidate_boundary_source": adapter_metadata["candidate_boundary_source"],
        "buy_score_source": adapter_metadata["buy_score_source"],
        "exact_top50_preserved": adapter_metadata["exact_top50_preserved"],
        "status": "PASS",
    }], ["track_id", "adapter_id", "candidate_boundary_source", "buy_score_source", "exact_top50_preserved", "status"])
    return _write_child_manifest(repo_root, directory, {
        "artifact_type": "ModelSignalArtifact",
        "schema_version": "model_signal_contract_v1.dual_track",
        "registry_entry": MODEL_SIGNAL_REGISTRY_ENTRY,
        "model_id": track["model_id"],
        "model_name": track["model_id"],
        "model_family": track["model_family"],
        "track_id": track_id,
        "adapter_id": track["adapter_id"],
        "run_id": f"dual_track_{track_id}_20260813_20260901",
        "asof": str(signals.date.max()),
        "created_at": created_at,
        "status": "READY",
        "row_count": len(signals),
        "candidate_boundary": "model_a_exact_top50",
        "source_bindings": source_bindings,
        "readonly_only": True,
        "production_allowed": False,
        "no_latest": True,
    }, [signal_path, schema_path, coverage_path, forbidden_path, mapping_path])


def _reference_replay_module(repo_root: Path) -> Any:
    source = (repo_root / REFERENCE_REPLAY_SOURCE).resolve()
    freeze = json.loads((repo_root / REFERENCE_REPLAY_FREEZE).read_text(encoding="utf-8"))
    binding = (freeze.get("bindings") or {}).get("v3_replay_core_template") or {}
    if (
        freeze.get("status") != "FROZEN_TEMPLATE_ONLY_NON_EXECUTABLE_NO_REAL_DATA_BINDING"
        or binding.get("path") != REFERENCE_REPLAY_SOURCE.as_posix()
        or binding.get("sha256") != _sha256(source)
    ):
        raise WorkflowError("independent Model A replay freeze binding is invalid")
    spec = importlib.util.spec_from_file_location("tw_stock_reference_replay", source)
    if spec is None or spec.loader is None:
        raise WorkflowError("independent Model A replay implementation cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_model_a_reference_parity(
    repo_root: Path,
    track_root: Path,
    signals: pd.DataFrame,
    grid: pd.DataFrame,
    replay_manifest_path: Path,
) -> Path:
    reference = _reference_replay_module(repo_root)
    if not (
        reference.INITIAL == INITIAL_CASH
        and reference.FEE == COMMISSION_RATE
        and reference.TAX == SELL_TAX_RATE
        and reference.LOT == LOT_SIZE
        and reference.TARGET == TARGET_HOLDINGS
    ):
        raise WorkflowError("independent Model A replay constants do not match")

    candidates = signals[signals.candidate_rank.le(50)].copy()
    reference_actions, reference_nav, _, reference_contribution = reference.replay(
        candidates,
        grid,
        signals[["date", "instrument", "full_qlib_rank"]],
        "buy_score",
        "A_ONLY",
        "readonly_dual_track_complete_feature_14_day",
    )
    reference_summary = reference.summarize(
        "readonly_dual_track_complete_feature_14_day",
        "A_ONLY",
        reference_actions,
        reference_nav,
        reference_contribution,
    )

    replay_manifest = json.loads(replay_manifest_path.read_text(encoding="utf-8"))
    files = replay_manifest["files"]
    actual_actions = pd.read_csv(repo_root / files["actions"]["path"])
    actual_nav = pd.read_csv(repo_root / files["daily_nav"]["path"])
    actual_metrics = json.loads((repo_root / files["metrics"]["path"]).read_text(encoding="utf-8"))

    action_keys = ["signal_date", "execution_date", "instrument", "action", "quantity", "status"]
    action_numeric = ["execution_price", "commission", "sell_tax", "net_pnl"]
    actual_action_view = actual_actions[action_keys + action_numeric].sort_values(action_keys).reset_index(drop=True)
    reference_action_view = reference_actions[action_keys + action_numeric].sort_values(action_keys).reset_index(drop=True)
    nav_keys = ["signal_date", "date", "holding_count"]
    nav_numeric = ["cash", "market_value", "equity", "daily_return", "drawdown"]
    actual_nav_view = actual_nav[nav_keys + nav_numeric].sort_values(nav_keys).reset_index(drop=True)
    reference_nav_view = reference_nav[nav_keys + nav_numeric].sort_values(nav_keys).reset_index(drop=True)
    summary_fields = [
        "final_equity", "net_return", "max_drawdown", "turnover", "buy_count",
        "sell_count", "action_count", "commission", "sell_tax", "fee_tax",
        "fallback_count", "pending_count",
    ]
    checks = {
        "action_row_set": actual_action_view[action_keys].equals(reference_action_view[action_keys]),
        "action_numeric_values": np.allclose(
            actual_action_view[action_numeric].to_numpy(float),
            reference_action_view[action_numeric].to_numpy(float),
            rtol=0.0,
            atol=1e-9,
        ),
        "daily_nav_row_set": actual_nav_view[nav_keys].equals(reference_nav_view[nav_keys]),
        "daily_nav_numeric_values": np.allclose(
            actual_nav_view[nav_numeric].to_numpy(float),
            reference_nav_view[nav_numeric].to_numpy(float),
            rtol=0.0,
            atol=1e-9,
        ),
        "summary_metrics": all(
            math.isclose(float(actual_metrics[field]), float(reference_summary[field]), rel_tol=0.0, abs_tol=1e-9)
            for field in summary_fields
        ),
    }
    checks = {key: bool(value) for key, value in checks.items()}
    report = {
        "artifact_type": "IndependentReplayParityReport",
        "schema_version": "tw.independent_replay_parity.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "track_id": "model_a_only",
        "window_id": "b19r2r_retrospective_complete_20260813_20260901",
        "reference_implementation": _binding(repo_root, REFERENCE_REPLAY_SOURCE),
        "reference_freeze": _binding(repo_root, REFERENCE_REPLAY_FREEZE),
        "replay_manifest": {
            "path": _relative(repo_root, replay_manifest_path),
            "sha256": _sha256(replay_manifest_path),
        },
        "checks": checks,
        "tolerance": {"rtol": 0.0, "atol": 1e-9},
        "action_count": len(actual_action_view),
        "nav_day_count": len(actual_nav_view),
    }
    report_path = track_root / "independent_replay_parity.json"
    _write_json(report_path, report)
    if report["status"] != "PASS":
        failed = ", ".join(key for key, value in checks.items() if not value)
        raise WorkflowError(f"independent Model A replay parity failed: {failed}")
    return report_path


def _resolve_buy(cash: float, holding_count: int, price: float) -> tuple[int, float, float]:
    allocation = cash / max(1, TARGET_HOLDINGS - holding_count)
    quantity = int(allocation // (price * (1 + COMMISSION_RATE) * LOT_SIZE)) * LOT_SIZE
    commission = quantity * price * COMMISSION_RATE
    total = quantity * price + commission
    if quantity <= 0 or total > cash:
        return 0, 0.0, 0.0
    return quantity, commission, total


def _materialize_decision_and_replay(
    repo_root: Path,
    track_root: Path,
    track_id: str,
    track: dict[str, Any],
    signals: pd.DataFrame,
    grid: pd.DataFrame,
    signal_manifest_path: Path,
    created_at: str,
) -> tuple[Path, Path, dict[str, Any]]:
    order_dir = track_root / "order_intent"
    replay_dir = track_root / "replay_result"
    order_dir.mkdir(parents=True, exist_ok=False)
    replay_dir.mkdir(parents=True, exist_ok=False)
    grid_lookup = grid.set_index(["date", "instrument"])
    holdings: dict[str, int] = {}
    basis: dict[str, float] = {}
    cash = INITIAL_CASH
    intent_rows: list[dict[str, Any]] = []
    decision_rows: list[dict[str, Any]] = []
    action_rows: list[dict[str, Any]] = []
    nav_rows: list[dict[str, Any]] = []
    snapshot_rows: list[dict[str, Any]] = []
    signal_manifest_rel = _relative(repo_root, signal_manifest_path)

    for day, day_signals in signals.groupby("date", sort=True):
        portfolio = [{
            "asof_date": day,
            "instrument": instrument,
            "quantity": quantity,
            "cost_basis": basis[instrument] / quantity,
            "current_holding_flag": True,
        } for instrument, quantity in sorted(holdings.items())]
        decision = decide_for_model(
            day_signals.to_dict("records"),
            portfolio,
            CANONICAL_CONFIG,
            model_id=track["model_id"],
            model_family=track["model_family"],
            candidate_rank_policy=track["candidate_rank_policy"],
        )
        day_intents: list[dict[str, Any]] = []
        for index, intent in enumerate(decision.intents):
            row = {
                "order_intent_row_id": f"{day}:{index:03d}",
                "signal_date": intent.signal_date,
                "instrument": intent.instrument,
                "intent_action": intent.intent_action,
                "intent_reason": intent.intent_reason,
                "strategy_rule": intent.strategy_rule,
                "candidate_rank": intent.candidate_rank,
                "buy_rank": intent.buy_rank,
                "full_qlib_rank": intent.full_qlib_rank,
                "max_buy_count": decision.max_buy_count,
                "max_sell_count": decision.max_sell_count,
                "model_name": intent.model_name,
                "signal_artifact": signal_manifest_rel,
                "current_holding_flag": intent.current_holding_flag,
                "target_holding_count": decision.target_holding_count,
                "candidate_k": decision.candidate_k,
                "readonly_only": True,
                "not_order": True,
            }
            intent_rows.append(row)
            day_intents.append(row)
        decision_rows.append({
            "signal_date": day,
            "sell": "|".join(decision.sell),
            "buy": "|".join(decision.buy),
            "hold_count": len(decision.hold),
            "buy_count": len(decision.buy),
            "sell_count": len(decision.sell),
            "status": "PASS",
        })

        execution_dates = set(grid.loc[grid.date.eq(day), "next_trade_date"].astype(str).str[:10])
        if len(execution_dates) != 1:
            raise WorkflowError(f"execution grid has no unique next trade date: {day}")
        execution_date = next(iter(execution_dates))
        executed_count = 0
        skip_count = 0
        for intent in day_intents:
            if intent["intent_action"] not in {"buy", "sell"}:
                continue
            price = float(grid_lookup.loc[(day, intent["instrument"]), "next_open"])
            if not math.isfinite(price) or price <= 0:
                raise WorkflowError(f"invalid next-open price: {day} {intent['instrument']}")
            symbol = intent["instrument"]
            action = intent["intent_action"]
            status = "EXECUTED"
            if action == "sell":
                quantity = holdings.pop(symbol)
                old_basis = basis.pop(symbol)
                commission = quantity * price * COMMISSION_RATE
                tax = quantity * price * SELL_TAX_RATE
                cash += quantity * price - commission - tax
                net_pnl = quantity * price - old_basis - commission - tax
            else:
                quantity, commission, total = _resolve_buy(cash, len(holdings), price)
                tax = 0.0
                if quantity == 0:
                    status = SKIP_STATUS
                    net_pnl = 0.0
                    skip_count += 1
                else:
                    cash -= total
                    holdings[symbol] = quantity
                    basis[symbol] = quantity * price
                    net_pnl = -commission
            if status == "EXECUTED":
                executed_count += 1
            action_rows.append({
                "signal_date": day,
                "execution_date": execution_date,
                "instrument": symbol,
                "action": action,
                "quantity": quantity,
                "execution_price": price,
                "commission": commission,
                "tax": tax,
                "sell_tax": tax,
                "fee_and_tax": commission + tax,
                "cash_after": cash,
                "position_after": holdings.get(symbol, 0),
                "net_pnl": net_pnl,
                "status": status,
                "intent_reason": intent["intent_reason"],
                "strategy_rule": intent["strategy_rule"],
                "model_name": track["model_id"],
                "order_intent_artifact": _relative(repo_root, order_dir / "manifest.json"),
                "order_intent_row_id": intent["order_intent_row_id"],
            })
        market_value = 0.0
        for symbol, quantity in sorted(holdings.items()):
            close = float(grid_lookup.loc[(day, symbol), "next_close"])
            value = quantity * close
            market_value += value
            snapshot_rows.append({
                "date": execution_date,
                "instrument": symbol,
                "quantity": quantity,
                "cost_basis": basis[symbol] / quantity,
                "mark_price": close,
                "market_value": value,
                "unrealized_pnl": value - basis[symbol],
                "strategy_rule": CANONICAL_CONFIG["strategy_rule"],
                "model_name": track["model_id"],
            })
        nav_rows.append({
            "signal_date": day,
            "date": execution_date,
            "cash": cash,
            "market_value": market_value,
            "equity": cash + market_value,
            "holding_count": len(holdings),
            "missing_price_count": 0,
            "decision_count": sum(row["intent_action"] in {"buy", "sell"} for row in day_intents),
            "emitted_action_count": executed_count,
            "executed_action_count": executed_count,
            "skip_count": skip_count,
            "pending_count": 0,
            "fallback_count": 0,
        })

    nav = pd.DataFrame(nav_rows)
    nav["daily_return"] = nav.equity.pct_change().fillna(nav.equity.iloc[0] / INITIAL_CASH - 1)
    peaks = np.maximum.accumulate(np.r_[INITIAL_CASH, nav.equity.to_numpy(float)])[1:]
    nav["drawdown"] = nav.equity.to_numpy(float) / peaks - 1.0
    actions = pd.DataFrame(action_rows)
    contribution_rows = []
    for symbol in sorted(set(actions.instrument).union(holdings)):
        action_pnl = float(actions.loc[actions.instrument.eq(symbol), "net_pnl"].sum())
        unrealized = 0.0
        if symbol in holdings:
            close = float(grid_lookup.loc[(signals.date.max(), symbol), "next_close"])
            unrealized = holdings[symbol] * close - basis[symbol]
        contribution_rows.append({
            "instrument": symbol,
            "action_net_pnl": action_pnl,
            "terminal_unrealized_pnl": unrealized,
            "total_contribution": action_pnl + unrealized,
        })
    contribution = pd.DataFrame(contribution_rows)
    if not math.isclose(
        float(contribution.total_contribution.sum()),
        float(nav.equity.iloc[-1] - INITIAL_CASH),
        abs_tol=1e-6,
    ):
        raise WorkflowError("replay contribution does not reconcile")
    executed = actions[actions.status.eq("EXECUTED")]
    skipped = actions[actions.status.eq(SKIP_STATUS)]
    abs_contribution = contribution.total_contribution.abs()
    denominator = float(abs_contribution.sum())
    shares = abs_contribution / denominator if denominator > 0 else pd.Series(dtype=float)
    metrics = {
        "scope": "readonly_dual_track_complete_feature_14_day",
        "method": track["metric_method"],
        "final_equity": float(nav.equity.iloc[-1]),
        "net_return": float(nav.equity.iloc[-1] / INITIAL_CASH - 1),
        "max_drawdown": float(nav.drawdown.min()),
        "turnover": float((executed.quantity * executed.execution_price).sum() / INITIAL_CASH),
        "buy_count": int(len(executed[executed.action.eq("buy")])),
        "sell_count": int(len(executed[executed.action.eq("sell")])),
        "action_count": int(len(executed)),
        "skip_count": int(len(skipped)),
        "decision_count": int(nav.decision_count.sum()),
        "commission": float(executed.commission.sum()),
        "sell_tax": float(executed.sell_tax.sum()),
        "fee_tax": float(executed.fee_and_tax.sum()),
        "top1_abs_contribution_share": float(shares.nlargest(1).sum()) if len(shares) else None,
        "top5_abs_contribution_share": float(shares.nlargest(5).sum()) if len(shares) else None,
        "abs_contribution_hhi": float((shares**2).sum()) if len(shares) else None,
        "fallback_count": int(nav.fallback_count.sum()),
        "pending_count": int(nav.pending_count.sum()),
    }

    intent_path = order_dir / "order_intents.csv"
    intent_fields = list(intent_rows[0])
    _write_csv(intent_path, intent_rows, intent_fields)
    order_schema = order_dir / "schema.json"
    _write_json(order_schema, {"schema_version": "order_intent_contract_v1", "columns": intent_fields})
    decision_path = order_dir / "strategy_decision_audit.csv"
    _write_csv(decision_path, decision_rows, list(decision_rows[0]))
    order_forbidden = order_dir / "forbidden_action_audit.json"
    _write_json(order_forbidden, {
        "status": "PASS", "not_order": True, "target_position_generated": False,
        "broker_or_quick_trade_triggered": False,
    })
    order_manifest = _write_child_manifest(repo_root, order_dir, {
        "artifact_type": "OrderIntentArtifact",
        "schema_version": "order_intent_contract_v1.dual_track",
        "model_id": track["model_id"],
        "model_name": track["model_id"],
        "model_family": track["model_family"],
        "track_id": track_id,
        "strategy_rule": CANONICAL_CONFIG["strategy_rule"],
        "run_id": f"dual_track_{track_id}_20260813_20260901",
        "asof": str(signals.date.max()),
        "created_at": created_at,
        "status": "READY",
        "signal_artifact": signal_manifest_rel,
        "order_intent_count": len(intent_rows),
        "readonly_only": True,
        "not_order": True,
        "production_allowed": False,
    }, [intent_path, order_schema, decision_path, order_forbidden])

    summary_path = replay_dir / "summary.csv"
    summary_row = {
        "window": "b19r2r_complete_14d",
        "model_name": track["model_id"],
        "model_family": track["model_family"],
        "strategy_rule": CANONICAL_CONFIG["strategy_rule"],
        "start_date": signals.date.min(),
        "end_date": signals.date.max(),
        "initial_cash": INITIAL_CASH,
        "fee_and_tax": metrics["fee_tax"],
        "final_equity": metrics["final_equity"],
        "total_return": metrics["net_return"],
        "max_drawdown": metrics["max_drawdown"],
        "action_count": metrics["action_count"],
        "buy_count": metrics["buy_count"],
        "sell_count": metrics["sell_count"],
        "skipped_action_count": metrics["skip_count"],
        "max_holding_count": int(nav.holding_count.max()),
        "duplicate_position_count": 0,
        "negative_cash_count": int(nav.cash.lt(0).sum()),
        "missing_price_count": int(nav.missing_price_count.sum()),
        "diagnostic_only": track["governance_status"] != "active_baseline",
    }
    _write_csv(summary_path, [summary_row], list(summary_row))
    actions_path = replay_dir / "actions.csv"
    actions.to_csv(actions_path, index=False)
    nav_path = replay_dir / "daily_nav.csv"
    nav.to_csv(nav_path, index=False)
    snapshots_path = replay_dir / "position_snapshots.csv"
    pd.DataFrame(snapshot_rows).to_csv(snapshots_path, index=False)
    contribution_path = replay_dir / "contribution.csv"
    contribution.to_csv(contribution_path, index=False)
    metrics_path = replay_dir / "metrics.json"
    _write_json(metrics_path, metrics)
    coverage_path = replay_dir / "coverage_audit.csv"
    _write_csv(coverage_path, [{
        "audit_name": "window_coverage", "requested_start_date": signals.date.min(),
        "requested_end_date": signals.date.max(), "actual_start_date": signals.date.min(),
        "actual_end_date": signals.date.max(), "trading_day_count": signals.date.nunique(),
        "signal_day_count": signals.date.nunique(), "price_day_count": grid.date.nunique(),
        "missing_signal_day_count": 0, "missing_price_day_count": 0,
        "status": "PASS", "details": "complete frozen 14-day shared window",
    }], ["audit_name", "requested_start_date", "requested_end_date", "actual_start_date", "actual_end_date", "trading_day_count", "signal_day_count", "price_day_count", "missing_signal_day_count", "missing_price_day_count", "status", "details"])
    integrity_path = replay_dir / "position_integrity_audit.csv"
    _write_csv(integrity_path, [{
        "audit_name": "portfolio_integrity", "date": signals.date.max(), "instrument": "ALL",
        "status": "PASS", "value": 0, "threshold": 0,
        "details": "no duplicate positions, negative cash, or invalid active quantity",
    }], ["audit_name", "date", "instrument", "status", "value", "threshold", "details"])
    forbidden_path = replay_dir / "forbidden_field_audit.csv"
    _write_csv(forbidden_path, [{
        "audit_name": "strategy_ranking_boundary", "artifact": "ReplayResultArtifact",
        "field_name": "future_or_execution_input", "field_category": "forbidden_strategy_input",
        "present": False, "used_for_ranking": False, "status": "PASS",
        "details": "replay consumed only OrderIntentArtifact and frozen execution grid",
    }], ["audit_name", "artifact", "field_name", "field_category", "present", "used_for_ranking", "status", "details"])
    execution_path = replay_dir / "execution_audit.csv"
    _write_csv(execution_path, [{
        "audit_name": "next_open_execution", "status": "PASS", "value": len(actions),
        "threshold": len(actions), "details": "all actions trace to next-open grid rows",
    }], ["audit_name", "status", "value", "threshold", "details"])
    replay_forbidden = replay_dir / "forbidden_action_audit.json"
    _write_json(replay_forbidden, {
        "status": "PASS", "training_or_tuning": False, "provider_or_latest_write": False,
        "paper_portfolio_write": False, "broker_or_order_write": False,
    })
    replay_manifest = _write_child_manifest(repo_root, replay_dir, {
        "artifact_type": "ReplayResultArtifact",
        "schema_version": "replay_result_contract_v1.dual_track",
        "model_id": track["model_id"],
        "model_name": track["model_id"],
        "model_family": track["model_family"],
        "track_id": track_id,
        "strategy_rule": CANONICAL_CONFIG["strategy_rule"],
        "run_id": f"dual_track_{track_id}_20260813_20260901",
        "asof": str(signals.date.max()),
        "created_at": created_at,
        "status": "READY",
        "order_intent_artifact": _relative(repo_root, order_manifest),
        "execution_price_mode": "next_open",
        "mark_price_mode": "next_close",
        "readonly_only": True,
        "no_apply": True,
        "production_allowed": False,
    }, [summary_path, actions_path, nav_path, snapshots_path, contribution_path, metrics_path, coverage_path, integrity_path, forbidden_path, execution_path, replay_forbidden])
    return order_manifest, replay_manifest, metrics


def validate_track_bundle(repo_root: Path, track_manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(track_manifest_path.read_text(encoding="utf-8"))
    track = _track_config(repo_root, str(manifest.get("track_id") or ""))
    _resolve_track_adapter(track)
    adapter_id = track["adapter_id"]
    checks: dict[str, bool] = {}
    checks["artifact_type"] = manifest.get("artifact_type") == "ReadonlyModelTrackArtifact"
    checks["readonly_boundary"] = (
        manifest.get("readonly_only") is True
        and manifest.get("no_apply") is True
        and manifest.get("production_allowed") is False
    )
    checks["track_identity"] = (
        manifest.get("model_id") == track["model_id"]
        and manifest.get("model_family") == track["model_family"]
        and manifest.get("adapter_id") == adapter_id
    )
    registry_entry = _model_signal_registry_entry(repo_root)
    checks["registered_model_signal_route"] = (
        registry_entry.get("production_allowed") is False
        and "strategy_rule" in registry_entry.get("allowed_consumers", [])
        and "replay_execution" in registry_entry.get("allowed_consumers", [])
    )
    for name, item in manifest.get("source_bindings", {}).items():
        path = repo_root / item["path"]
        checks[f"source_{name}"] = path.is_file() and _sha256(path) == item["sha256"] and path.stat().st_size == item["bytes"]
    child_manifests: dict[str, dict[str, Any]] = {}
    for name, item in manifest.get("artifacts", {}).items():
        path = repo_root / item["path"]
        checks[f"manifest_{name}"] = path.is_file() and _sha256(path) == item["sha256"]
        if path.is_file():
            child = json.loads(path.read_text(encoding="utf-8"))
            child_manifests[name] = child
            for file_name, file_item in child.get("files", {}).items():
                child_path = repo_root / file_item["path"]
                checks[f"{name}_{file_name}"] = child_path.is_file() and _sha256(child_path) == file_item["sha256"] and child_path.stat().st_size == file_item["bytes"]
    required_children = {"model_signal", "order_intent", "replay_result"}
    checks["required_child_artifacts"] = set(child_manifests) == required_children
    if required_children.issubset(child_manifests):
        checks["model_signal_registry_binding"] = (
            child_manifests["model_signal"].get("registry_entry") == MODEL_SIGNAL_REGISTRY_ENTRY
        )
        checks["model_signal_adapter_binding"] = (
            child_manifests["model_signal"].get("adapter_id") == adapter_id
        )
        signals = pd.read_csv(repo_root / child_manifests["model_signal"]["files"]["signals"]["path"])
        intents = pd.read_csv(repo_root / child_manifests["order_intent"]["files"]["order_intents"]["path"])
        actions = pd.read_csv(repo_root / child_manifests["replay_result"]["files"]["actions"]["path"])
        nav = pd.read_csv(repo_root / child_manifests["replay_result"]["files"]["daily_nav"]["path"])
        checks["signals_expected_window"] = (
            len(signals) == len(COMPARISON_DATES) * 150
            and tuple(sorted(signals.date.astype(str).unique())) == COMPARISON_DATES
        )
        checks["signals_unique"] = not signals.duplicated(["date", "instrument"]).any()
        checks["candidate_rank_unique_daily"] = not signals.duplicated(["date", "candidate_rank"]).any()
        actual_top50 = signals[signals.candidate_rank.le(50)][["date", "instrument"]]
        model_a = pd.read_parquet(repo_root / MODEL_A_SOURCE)
        model_a["date"] = model_a.date.astype(str).str[:10]
        original_top50 = model_a[model_a.date.isin(signals.date.astype(str).unique()) & model_a.full_qlib_rank.le(50)]
        original_keys = set(map(tuple, original_top50[["date", "instrument"]].to_numpy()))
        actual_keys = set(map(tuple, actual_top50.to_numpy()))
        if adapter_id == MODEL_A_ADAPTER_ID:
            checks["original_top50_no_replacement"] = actual_keys == original_keys
        elif adapter_id == B19R2R_ADAPTER_ID:
            schema = json.loads((repo_root / FEATURE_SCHEMA).read_text(encoding="utf-8"))
            feature_order = list(schema["feature_order"])
            features = pd.read_parquet(
                repo_root / FEATURE_78_SOURCE,
                columns=["date", "instrument", "feature_raw_complete_78", *feature_order],
            )
            features["date"] = features.date.astype(str).str[:10]
            features["instrument"] = features.instrument.astype(str)
            expected_keys = {
                key for key in original_keys
                if key[1] != "TW7769"
            }
            checks["original_top50_no_replacement"] = actual_keys == expected_keys
            expected_features = features.merge(
                pd.DataFrame(sorted(expected_keys), columns=["date", "instrument"]),
                on=["date", "instrument"], how="inner", validate="one_to_one",
            )
            checks["non_tw7769_top50_features_complete"] = (
                len(expected_features) == len(expected_keys)
                and bool(expected_features.feature_raw_complete_78.all())
            )
            tw6919_expected = {key for key in expected_keys if key[1] == "TW6919"}
            checks["tw6919_complete_rows_scored"] = bool(tw6919_expected) and tw6919_expected.issubset(actual_keys)
        signal_scores = signals[["date", "instrument", "raw_score", "candidate_rank"]].merge(
            model_a[["date", "instrument", "model_a_raw_score"]],
            on=["date", "instrument"],
            how="left",
            validate="one_to_one",
        )
        if adapter_id == MODEL_A_ADAPTER_ID:
            checks["model_a_score_binding"] = np.allclose(
                signal_scores.raw_score,
                signal_scores.model_a_raw_score,
                rtol=0.0,
                atol=1e-15,
            )
        elif adapter_id == B19R2R_ADAPTER_ID:
            top50_scores = signal_scores[signal_scores.candidate_rank.le(50)].merge(
                features[["date", "instrument", *feature_order]],
                on=["date", "instrument"], how="left", validate="one_to_one",
            )
            model = joblib.load(repo_root / MODEL_B_ARTIFACT)
            expected_scores = model.predict(top50_scores[feature_order])
            checks["model_b_score_binding"] = np.allclose(
                top50_scores.raw_score,
                expected_scores,
                rtol=0.0,
                atol=1e-15,
            )
            checks["excluded_original_top50_not_replaced"] = not bool(actual_keys - original_keys)
        checks["daily_action_limits"] = intents[intents.intent_action.isin(["buy", "sell"])].groupby(["signal_date", "intent_action"]).size().le(1).all()
        checks["action_lineage"] = set(actions.order_intent_row_id).issubset(set(intents.order_intent_row_id))
        checks["next_day_execution"] = (pd.to_datetime(actions.execution_date) > pd.to_datetime(actions.signal_date)).all()
        checks["portfolio_integrity"] = nav.cash.ge(-1e-8).all() and nav.holding_count.le(TARGET_HOLDINGS).all()
    if adapter_id == MODEL_A_ADAPTER_ID:
        parity_item = (manifest.get("validation_evidence") or {}).get("reference_replay_parity") or {}
        parity_path = repo_root / str(parity_item.get("path") or "")
        checks["reference_replay_parity_file"] = (
            parity_path.is_file() and _sha256(parity_path) == parity_item.get("sha256")
        )
        if parity_path.is_file():
            parity = json.loads(parity_path.read_text(encoding="utf-8"))
            reference_binding = parity.get("reference_implementation") or {}
            freeze_binding = parity.get("reference_freeze") or {}
            reference_path = repo_root / str(reference_binding.get("path") or "")
            freeze_path = repo_root / str(freeze_binding.get("path") or "")
            checks["reference_replay_parity_pass"] = (
                parity.get("status") == "PASS"
                and all((parity.get("checks") or {}).values())
                and reference_path == (repo_root / REFERENCE_REPLAY_SOURCE).resolve()
                and reference_path.is_file()
                and _sha256(reference_path) == reference_binding.get("sha256")
                and freeze_path == (repo_root / REFERENCE_REPLAY_FREEZE).resolve()
                and freeze_path.is_file()
                and _sha256(freeze_path) == freeze_binding.get("sha256")
            )
    checks = {key: bool(value) for key, value in checks.items()}
    if not all(checks.values()):
        failed = sorted(key for key, value in checks.items() if not value)
        raise WorkflowError(f"dual-track artifact validation failed: {', '.join(failed)}")
    return {"status": "PASS", "check_count": len(checks), "checks": checks}


def build_track_bundle(
    repo_root: Path,
    workspace: Path,
    track_id: str,
    created_at: str,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    workspace = workspace.resolve()
    try:
        workspace.relative_to(repo_root)
    except ValueError as exc:
        raise WorkflowError("dual-track workspace must be inside the repository") from exc
    track = _track_config(repo_root, track_id)
    track_root = workspace / "artifacts" / track_id
    track_manifest_path = track_root / "track_manifest.json"
    if track_manifest_path.is_file():
        validation = validate_track_bundle(repo_root, track_manifest_path)
        return {
            "track_id": track_id,
            "track_manifest": _relative(repo_root, track_manifest_path),
            "track_manifest_sha256": _sha256(track_manifest_path),
            "validation": validation,
            "reused": True,
        }
    if track_root.exists():
        raise WorkflowError(f"partial dual-track output already exists: {track_root}")
    track_root.mkdir(parents=True)
    signals, grid, source_bindings, adapter_metadata = _load_frames(repo_root, track_id)
    signal_manifest = _materialize_signal_artifact(
        repo_root,
        track_root,
        track_id,
        track,
        signals,
        source_bindings,
        adapter_metadata,
        created_at,
    )
    order_manifest, replay_manifest, metrics = _materialize_decision_and_replay(
        repo_root, track_root, track_id, track, signals, grid, signal_manifest, created_at
    )
    validation_evidence: dict[str, dict[str, str]] = {}
    if track["adapter_id"] == MODEL_A_ADAPTER_ID:
        parity_path = _build_model_a_reference_parity(
            repo_root, track_root, signals, grid, replay_manifest
        )
        validation_evidence["reference_replay_parity"] = {
            "path": _relative(repo_root, parity_path),
            "sha256": _sha256(parity_path),
        }
    track_manifest = {
        "artifact_type": "ReadonlyModelTrackArtifact",
        "schema_version": "tw.readonly_model_track.v1",
        "track_id": track_id,
        "model_id": track["model_id"],
        "model_family": track["model_family"],
        "adapter_id": track["adapter_id"],
        "asof": str(signals.date.max()),
        "run_id": f"dual_track_{track_id}_20260813_20260901",
        "status": "READY",
        "created_at": created_at,
        "framework_role": "model_track",
        "governance_status": track["governance_status"],
        "workflow_policy": track["workflow_policy"],
        "readonly_only": True,
        "no_apply": True,
        "runtime_effect": "none",
        "production_allowed": False,
        "source_bindings": source_bindings,
        "artifacts": {
            name: {"path": _relative(repo_root, path), "sha256": _sha256(path)}
            for name, path in {
                "model_signal": signal_manifest,
                "order_intent": order_manifest,
                "replay_result": replay_manifest,
            }.items()
        },
        "validation_evidence": validation_evidence,
        "metrics": metrics,
    }
    _write_json(track_manifest_path, track_manifest)
    validation = validate_track_bundle(repo_root, track_manifest_path)
    validation_path = track_root / "validation_report.json"
    _write_json(validation_path, validation)
    return {
        "track_id": track_id,
        "track_manifest": _relative(repo_root, track_manifest_path),
        "track_manifest_sha256": _sha256(track_manifest_path),
        "validation": validation,
        "reused": False,
    }


def _track_input_ref(repo_root: Path, track_id: str) -> ArtifactRef:
    track = _track_config(repo_root, track_id)
    adapter = _resolve_track_adapter(track)
    adapter_id = track["adapter_id"]
    paths = [
        TRACK_CONFIG,
        MODULAR_REGISTRY,
        MODEL_A_SOURCE,
        EXECUTION_GRID_SOURCE,
        REFERENCE_REPLAY_SOURCE,
        REFERENCE_REPLAY_FREEZE,
        *IMPLEMENTATION_SOURCES,
    ]
    paths.extend(adapter["input_paths"])
    metadata = {path.as_posix(): _binding(repo_root, path) for path in paths}
    manifest = repo_root / adapter["manifest_path"]
    return ArtifactRef(
        adapter_id=f"readonly_model_track.{adapter_id}",
        artifact_type="readonly_model_track_source_bundle",
        model_id=track["model_id"],
        asof="2026-09-01",
        status="FROZEN",
        run_id=adapter["run_id"],
        path=_relative(repo_root, repo_root / adapter["artifact_path"]),
        manifest_path=_relative(repo_root, manifest),
        manifest_sha256=_sha256(manifest),
        metadata=metadata,
    )


def _comparison_rows(repo_root: Path, outputs: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    comparisons: list[dict[str, Any]] = []
    boundary_audit: list[dict[str, Any]] = []
    for track_id, output in outputs.items():
        method = _track_config(repo_root, track_id)["metric_method"]
        track_manifest = json.loads((repo_root / outputs[track_id]["track_manifest"]).read_text(encoding="utf-8"))
        row = dict(track_manifest["metrics"])
        comparisons.append(row)
        signal_manifest = json.loads(
            (repo_root / track_manifest["artifacts"]["model_signal"]["path"]).read_text(encoding="utf-8")
        )
        signals = pd.read_csv(repo_root / signal_manifest["files"]["signals"]["path"])
        eligible = signals[signals.candidate_rank.le(50)]
        excluded = signals[signals.full_qlib_rank.le(50) & signals.candidate_rank.gt(50)]
        tw7769_count = int(excluded.instrument.eq("TW7769").sum())
        boundary_audit.append({
            "track_id": track_id,
            "method": method,
            "audit": "original_model_a_top50_no_replacement",
            "eligible_row_count": len(eligible),
            "minimum_daily_eligible_count": int(eligible.groupby("date").size().min()),
            "maximum_daily_eligible_count": int(eligible.groupby("date").size().max()),
            "excluded_original_top50_row_count": len(excluded),
            "tw7769_policy_exclusion_count": tw7769_count,
            "feature_incomplete_exclusion_count": len(excluded) - tw7769_count,
            "excluded_symbols": "|".join(sorted(excluded.instrument.unique())),
            "status": "PASS",
        })
    return comparisons, boundary_audit


def build_comparison_bundle(
    repo_root: Path,
    workspace: Path,
    outputs: dict[str, dict[str, Any]],
    created_at: str,
    *,
    latest_root: Path | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    workspace = workspace.resolve()
    workspace.mkdir(parents=True, exist_ok=False)
    latest_root = (latest_root or workspace).resolve()
    if "model_a_only" not in outputs:
        raise WorkflowError("comparison requires the registered Model A track")
    for output in outputs.values():
        validate_track_bundle(repo_root, repo_root / output["track_manifest"])
    comparison_rows, boundary_rows = _comparison_rows(repo_root, outputs)
    comparison_path = workspace / "comparison.csv"
    boundary_path = workspace / "track_boundary_audit.csv"
    rank_path = workspace / "rank_metrics.csv"
    gate_path = workspace / "gate_diagnostics.csv"
    _write_csv(comparison_path, comparison_rows, list(comparison_rows[0]))
    _write_csv(boundary_path, boundary_rows, list(boundary_rows[0]))
    _write_csv(rank_path, [
        {"method": _track_config(repo_root, track_id)["metric_method"], "mean_rank_ic_continuous": "", "mean_ndcg_at_10": ""}
        for track_id in outputs
    ], ["method", "mean_rank_ic_continuous", "mean_ndcg_at_10"])
    _write_csv(gate_path, [], ["gate", "measured_value", "operator", "threshold", "status", "baseline_admission_effect"])
    registry = _load_track_registry(repo_root)
    source_paths = {
        "paired_metrics": comparison_path,
        "track_boundary_audit": boundary_path,
        "rank_metrics": rank_path,
        "gate_diagnostics": gate_path,
    }
    for track_id, output in outputs.items():
        source_paths[f"{track_id}_track_manifest"] = repo_root / output["track_manifest"]
        track_manifest = json.loads((repo_root / output["track_manifest"]).read_text(encoding="utf-8"))
        for evidence_id, evidence in (track_manifest.get("validation_evidence") or {}).items():
            source_paths[f"{track_id}_{evidence_id}"] = repo_root / evidence["path"]
    sources = {
        key: {"path": _relative(repo_root, path), "sha256": _sha256(path)}
        for key, path in source_paths.items()
    }
    models = []
    for track_id, track in registry["tracks"].items():
        models.append({
            "model_id": track_id,
            "display_name": track["display_name"],
            "canonical_model_id": track["model_id"],
            "framework_role": "model_track",
            "role": "active_baseline" if track["governance_status"] == "active_baseline" else "research_challenger",
            "governance_status": track["governance_status"],
            "workflow_policy": track["workflow_policy"],
            "comparison_selectable": track["comparison_selectable"],
            "virtual_account_eligible": track["virtual_account_eligible"],
            "production_default": track["production_default"],
        })
    combinations = []
    for track_id, output in outputs.items():
        track = registry["tracks"][track_id]
        method = track["metric_method"]
        track_manifest = json.loads((repo_root / outputs[track_id]["track_manifest"]).read_text(encoding="utf-8"))
        combinations.append({
            "combination_id": f"{track_id}__top50_exit_one_worst_sell__b19r2r_complete_14d",
            "model_id": track_id,
            "strategy_id": "top50_exit_one_worst_sell",
            "window_id": "b19r2r_retrospective_complete_20260813_20260901",
            "metric_method": method,
            "status": "ACTIVE_BASELINE_HISTORICAL_VIEW" if track["production_default"] else "RESEARCH_CANDIDATE_HISTORICAL_VIEW",
            "gate_status": "BASELINE_DESCRIPTOR_ACTIVE_MODEL_A_ONLY" if track["production_default"] else "NOT_EVALUATED_FOR_ORIGINAL_TOP50_NO_REPLACEMENT",
            "validator_status": "PASS",
            "independent_review_status": "PENDING_REVIEW",
            "comparison_selectable": True,
            "no_apply": True,
            "artifacts": track_manifest["artifacts"],
        })
    legacy_catalog_path = repo_root / "data_tw/artifacts/readonly_model_strategy_comparison/v1/catalog.json"
    legacy_strategies: list[dict[str, Any]] = []
    if legacy_catalog_path.is_file():
        legacy_catalog = json.loads(legacy_catalog_path.read_text(encoding="utf-8"))
        legacy_strategies = [
            item
            for item in legacy_catalog.get("strategies", [])
            if item.get("comparison_selectable") is False
        ]
    catalog = {
        "artifact_type": "readonly_model_strategy_comparison_catalog",
        "schema_version": "readonly_model_strategy_comparison_catalog_v3",
        "created_at": created_at,
        "readonly_only": True,
        "no_apply": True,
        "runtime_effect": "none",
        "production_trade_enabled": False,
        "default_selection": {
            "model_id": registry["default_track_id"],
            "strategy_id": "top50_exit_one_worst_sell",
            "window_id": "b19r2r_retrospective_complete_20260813_20260901",
        },
        "virtual_account_policy": registry["virtual_account_policy"],
        "models": models,
        "strategies": [{
            "strategy_id": "top50_exit_one_worst_sell",
            "display_name": "Top 50 / exit one worst",
            "lineage": "standard_dual_track_pipeline",
            "status": "AUDITED_SHARED_STRATEGY",
            "comparison_selectable": True,
            "compatible_model_ids": list(registry["tracks"]),
        }, *legacy_strategies],
        "windows": [{
            "window_id": "b19r2r_retrospective_complete_20260813_20260901",
            "display_name": "B19R2R complete-feature historical replay (14 days)",
            "start": "2026-08-13", "end": "2026-09-01", "trading_day_count": 14,
            "evidence_class": "RETROSPECTIVE_HISTORICAL_REPLAY_ALREADY_CONSUMED_INPUTS",
            "selection_policy": "longest_contiguous_tail_with_complete_78f_for_all_original_top50_except_tw7769",
            "prospective_pit_anchor": False, "untouched_claim": False,
        }],
        "combinations": combinations,
        "unavailable_tracks": {
            track_id: {"status": "challenger_unavailable", "reason": "track_run_not_succeeded"}
            for track_id in registry["tracks"]
            if track_id not in outputs and track_id != "model_a_only"
        },
        "sources": sources,
    }
    catalog_path = workspace / "catalog.json"
    _write_json(catalog_path, catalog)
    pointer = {
        "artifact_type": "readonly_model_strategy_comparison_catalog_pointer",
        "schema_version": "readonly_model_strategy_comparison_pointer_v3",
        "catalog_path": _relative(repo_root, catalog_path),
        "catalog_sha256": _sha256(catalog_path),
        "readonly_only": True, "no_apply": True, "runtime_effect": "none",
        "production_trade_enabled": False,
    }
    immutable_pointer_path = workspace / "latest.json"
    _write_json(immutable_pointer_path, pointer)
    pointer_path = latest_root / "latest.json"
    _write_json_atomic(pointer_path, pointer)
    return {
        "catalog": _relative(repo_root, catalog_path),
        "catalog_sha256": _sha256(catalog_path),
        "latest": _relative(repo_root, pointer_path),
        "catalog_latest": _relative(repo_root, immutable_pointer_path),
        "boundary_status": "PASS",
    }


class ReadonlyModelTrackExecution:
    required_permissions = frozenset({"artifact.read", "readonly.comparison.write"})

    def __init__(self, repo_root: Path, track_id: str) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.track_id = track_id
        self.module_id = f"readonly_model_track.{track_id}"

    def resolve_artifact_inputs(self, context: ExecutionContext, config: dict[str, Any], resolver: ArtifactResolver) -> list[ArtifactRef]:
        return [_track_input_ref(self.repo_root, self.track_id)]

    def execute(self, context: ExecutionContext, config: dict[str, Any], inputs: dict[str, dict[str, Any]], resolver: ArtifactResolver) -> dict[str, Any]:
        if config != {"track_id": self.track_id}:
            raise WorkflowError(f"workflow track config is not fixed: {self.track_id}")
        return build_track_bundle(self.repo_root, context.workspace, self.track_id, context.decision_cutoff)

    def validate_cached_output(self, context: ExecutionContext, config: dict[str, Any], output: dict[str, Any], resolver: ArtifactResolver) -> None:
        if output.get("track_id") != self.track_id:
            raise WorkflowError("cached model-track identity changed")
        path = self.repo_root / str(output.get("track_manifest") or "")
        validate_track_bundle(self.repo_root, path)
        if _sha256(path) != output.get("track_manifest_sha256"):
            raise WorkflowError("cached model-track manifest checksum changed")


class ReadonlyModelTrackComparison:
    module_id = "readonly_model_track.compare"
    required_permissions = frozenset({"artifact.read", "readonly.comparison.write"})

    def __init__(self, repo_root: Path, module_id: str = "readonly_model_track.compare") -> None:
        self.repo_root = Path(repo_root).resolve()
        self.module_id = module_id

    def resolve_artifact_inputs(self, context: ExecutionContext, config: dict[str, Any], resolver: ArtifactResolver) -> list[Any]:
        return []

    def execute(self, context: ExecutionContext, config: dict[str, Any], inputs: dict[str, dict[str, Any]], resolver: ArtifactResolver) -> dict[str, Any]:
        configured = config.get("track_ids") if set(config) == {"track_ids"} else None
        registered = _load_track_registry(self.repo_root)["tracks"]
        if not isinstance(configured, list) or not configured or any(track_id not in registered for track_id in configured):
            raise WorkflowError("comparison track set is not registered")
        outputs = {
            str(value["track_id"]): value
            for value in inputs.values()
            if isinstance(value, dict) and value.get("track_id") in configured
        }
        if set(outputs) != set(configured):
            raise WorkflowError("comparison did not receive every configured track")
        catalog_id = "model_a_only" if self.module_id == "readonly_model_track.catalog" else "paired"
        return build_comparison_bundle(
            self.repo_root,
            context.workspace / "catalogs" / catalog_id,
            outputs,
            context.decision_cutoff,
            latest_root=context.workspace,
        )

    def validate_cached_output(self, context: ExecutionContext, config: dict[str, Any], output: dict[str, Any], resolver: ArtifactResolver) -> None:
        catalog = self.repo_root / str(output.get("catalog") or "")
        if not catalog.is_file() or _sha256(catalog) != output.get("catalog_sha256"):
            raise WorkflowError("cached comparison catalog changed")
        payload = json.loads(catalog.read_text(encoding="utf-8"))
        for source in payload.get("sources", {}).values():
            path = self.repo_root / source["path"]
            if not path.is_file() or _sha256(path) != source["sha256"]:
                raise WorkflowError("cached comparison source changed")
