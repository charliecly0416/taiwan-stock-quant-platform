from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

BASE_MODEL_ID = "e4_frozen_qlib_2018_2022"
MODEL_ID = "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025"
TARGET_ASOF = "2026-06-25"
DEFAULT_RUN_ID = "dng8_modelb_ltr_20260625"

INPUT_BASE = ROOT / "data_tw/canonical/model_inference_input" / MODEL_ID
SCORE_BASE = ROOT / "data_tw/artifacts/score_jobs" / MODEL_ID
CATALOG_VALIDATION_PATH = ROOT / "data_tw/catalog/dng8_modelb_ltr_score_pipeline_validation.json"
EXECUTION_REPORT_PATH = ROOT / "docs/tw_data_governance/DNG8_MODELB_LTR_SCORE_PIPELINE_EXECUTION_REPORT_CN.md"

DNG7_MODELA_SIGNAL_DIR = ROOT / "data_tw/artifacts/signals" / BASE_MODEL_ID / "dng7_modela_20260625"
DNG3_ORTHOGONAL_STORE_DIR = (
    ROOT / "data_tw/canonical/orthogonal_feature_store/daily_orthogonal/dng3_orthogonal_feature_store_20260625"
)
DNG3_READINESS_MATRIX = ROOT / "data_tw/catalog/readiness_matrix/2026-06-25/orthogonal_feature_store.json"
LTR_TRAINING_DIR = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training"
LTR_TRAINING_MANIFEST = LTR_TRAINING_DIR / "phasee3_training_manifest.json"
LTR_MODEL_ARTIFACT = LTR_TRAINING_DIR / "phasee3_ltr_model.pkl"
LTR_FEATURE_IMPORTANCE = LTR_TRAINING_DIR / "phasee3_feature_importance.csv"

BLOCKED_STATUS = "BLOCKED_INPUT_NOT_READY"
FALLBACK_ALLOWED = "qlib_only_if_strategy_contract_allows"

FORBIDDEN_ACTIONS_FALSE = {
    "model_training_triggered": False,
    "model_tuning_triggered": False,
    "model_inference_triggered": False,
    "ltr_model_b_triggered": False,
    "ltr_score_generated": False,
    "model_signal_artifact_generated": False,
    "real_data_fetch_triggered": False,
    "provider_refresh_triggered": False,
    "provider_publish_triggered": False,
    "qlib_accepted_latest_switched": False,
    "readonly_latest_published": False,
    "agent_prompt_published": False,
    "strategy_replay_triggered": False,
    "replay_result_nav_generated": False,
    "broker_order_quick_trade_triggered": False,
    "target_position_or_weight_generated": False,
}

FORBIDDEN_EXACT_FIELDS = {
    "relevance_10d_top_heavy",
    "ltr_relevance_label",
    "realized_pnl",
    "realized_return",
    "action",
    "holding",
    "position",
    "target_position",
    "target_weight",
    "order_qty",
    "execution_price",
    "execution_date",
    "broker_order_id",
}
FORBIDDEN_PREFIXES = ("future_return_", "future_excess_return_", "forward_return_", "label_")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return str(p.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(p)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_entry(path: Path, key: str, required: bool = True) -> dict[str, Any]:
    return {
        "key": key,
        "path": rel(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() and path.is_file() else None,
        "sha256": sha256_file(path) if path.exists() and path.is_file() else None,
        "required": required,
    }


def count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        next(reader, None)
        return sum(1 for _ in reader)


def csv_columns(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        return next(reader, [])


def forbidden_columns(columns: list[str]) -> list[str]:
    out = []
    for col in columns:
        lowered = col.lower()
        if lowered in FORBIDDEN_EXACT_FIELDS or any(lowered.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
            out.append(col)
    return sorted(out)


def collect_modela_readiness(asof: str) -> dict[str, Any]:
    manifest_path = DNG7_MODELA_SIGNAL_DIR / "manifest.json"
    signals_path = DNG7_MODELA_SIGNAL_DIR / "signals.csv"
    manifest = read_json(manifest_path) if manifest_path.exists() else {}
    row_count = count_csv_rows(signals_path)
    errors: list[str] = []
    if manifest.get("status") != "READY":
        errors.append(f"dng7_modela_signal_not_ready:{manifest.get('status')}")
    if manifest.get("score_status") != "SCORED_ASOF_TARGET":
        errors.append(f"dng7_modela_score_status_not_target:{manifest.get('score_status')}")
    if manifest.get("asof") != asof:
        errors.append(f"dng7_modela_asof_mismatch:{manifest.get('asof')}")
    if row_count != 150:
        errors.append(f"dng7_modela_signal_row_count_not_150:{row_count}")
    return {
        "dependency": "DNG7 Model A qlib signal",
        "status": "READY" if not errors else "BLOCKED",
        "can_continue": not errors,
        "path": rel(DNG7_MODELA_SIGNAL_DIR),
        "manifest_path": rel(manifest_path),
        "signals_path": rel(signals_path),
        "row_count": row_count,
        "model_id": manifest.get("model_id"),
        "score_status": manifest.get("score_status"),
        "errors": errors,
    }


def collect_orthogonal_readiness(asof: str) -> dict[str, Any]:
    readiness = read_json(DNG3_READINESS_MATRIX) if DNG3_READINESS_MATRIX.exists() else {}
    manifest_path = DNG3_ORTHOGONAL_STORE_DIR / "manifest.json"
    manifest = read_json(manifest_path) if manifest_path.exists() else {}
    blocking = readiness.get("blocking_datasets") or manifest.get("blocking_datasets") or []
    errors: list[str] = []
    if readiness.get("asof") != asof:
        errors.append(f"dng3_readiness_asof_mismatch:{readiness.get('asof')}")
    if readiness.get("can_continue_to_model_b_ltr") is not True:
        errors.append("dng3_can_continue_to_model_b_ltr_false")
    if manifest.get("status") != "READY":
        errors.append(f"orthogonal_feature_store_not_ready:{manifest.get('status')}")
    if blocking:
        errors.append("orthogonal_blocking_datasets:" + ",".join(blocking))
    return {
        "dependency": "DNG3 canonical orthogonal feature store",
        "status": manifest.get("status", "MISSING"),
        "can_continue_to_model_b_ltr": readiness.get("can_continue_to_model_b_ltr"),
        "can_continue_to_model_score": readiness.get("can_continue_to_model_score"),
        "blocking_datasets": blocking,
        "external_source_repair_required": readiness.get("external_source_repair_required"),
        "path": rel(DNG3_ORTHOGONAL_STORE_DIR),
        "manifest_path": rel(manifest_path),
        "readiness_matrix_path": rel(DNG3_READINESS_MATRIX),
        "dependencies": readiness.get("dependencies", []),
        "errors": errors,
    }


def collect_ltr_artifact_readiness() -> dict[str, Any]:
    manifest = read_json(LTR_TRAINING_MANIFEST) if LTR_TRAINING_MANIFEST.exists() else {}
    errors: list[str] = []
    if not LTR_MODEL_ARTIFACT.exists():
        errors.append("ltr_model_artifact_missing")
    if not LTR_TRAINING_MANIFEST.exists():
        errors.append("ltr_training_manifest_missing")
    if not LTR_FEATURE_IMPORTANCE.exists():
        errors.append("ltr_feature_importance_missing")
    if manifest.get("no_2026_training_tuning_or_selection") is not True:
        errors.append("ltr_training_manifest_no_2026_training_tuning_flag_missing")
    return {
        "dependency": "phase E3 LTR trained artifact metadata",
        "status": "READY" if not errors else "BLOCKED",
        "model_artifact": rel(LTR_MODEL_ARTIFACT),
        "model_artifact_sha256": sha256_file(LTR_MODEL_ARTIFACT) if LTR_MODEL_ARTIFACT.exists() else "",
        "training_manifest": rel(LTR_TRAINING_MANIFEST),
        "feature_importance": rel(LTR_FEATURE_IMPORTANCE),
        "feature_count": manifest.get("feature_count"),
        "feature_hash": manifest.get("feature_hash"),
        "train_period": manifest.get("train_period"),
        "test_period": manifest.get("test_period"),
        "future_replay_boundary": manifest.get("future_replay_boundary"),
        "errors": errors,
    }
