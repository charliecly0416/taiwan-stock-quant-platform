from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = "e4_frozen_qlib_2018_2022"
TARGET_ASOF = "2026-06-25"

INPUT_BASE = ROOT / "data_tw/canonical/model_inference_input" / MODEL_ID
SCORE_BASE = ROOT / "data_tw/artifacts/score_jobs" / MODEL_ID
SIGNAL_BASE = ROOT / "data_tw/artifacts/signals" / MODEL_ID
CATALOG_VALIDATION_PATH = ROOT / "data_tw/catalog/dng7_modela_score_pipeline_validation.json"
EXECUTION_REPORT_PATH = ROOT / "docs/tw_data_governance/DNG7_MODELA_SCORE_PIPELINE_EXECUTION_REPORT_CN.md"

READINESS_DASHBOARD = ROOT / "data_tw/catalog/daily_readiness_dashboard.json"
PRICE_MARKET_READINESS = ROOT / "data_tw/catalog/readiness_matrix/2026-06-25/price_market_calendar.json"
PRICE_STORE_DIR = ROOT / "data_tw/canonical/price_store/tw_equity_daily/dng2_r_price_market_calendar_20260625"

QLIB_PIPELINE_ROOT = ROOT / "qlib_pipeline"
QLIB_PROVIDER = QLIB_PIPELINE_ROOT / "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin"
QLIB_NORMALIZED = QLIB_PIPELINE_ROOT / "data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized"
QLIB_DAILY_SIGNAL_SCRIPT = QLIB_PIPELINE_ROOT / "examples/tw/run_option_c_daily_signal_option_c_provider.py"
QLIB_DAILY_SIGNAL_ROOT = QLIB_PIPELINE_ROOT / "data_tw/experiments/option_c_daily_signal"
QLIB_CONFIG = QLIB_PIPELINE_ROOT / "configs/tw_yahoo_primary_alpha158.yaml"
QLIB_UNIVERSE = (
    QLIB_PIPELINE_ROOT
    / "data_tw/experiments/option_c_forward_validation/timed_data_availability_retry_20260601T101323Z/symbols_accepted_prediction_universe.txt"
)
QLIB_MODEL_PATH = QLIB_PIPELINE_ROOT / "mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a/artifacts/params.pkl"
QLIB_RECORDER_PATH = QLIB_PIPELINE_ROOT / "mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a"
E1_TRAINING_MANIFEST = (
    ROOT
    / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_training_manifest.json"
)
E1_MODEL_ALIAS = (
    ROOT
    / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/run/phasee1_frozen_qlib_model.pkl"
)

SIGNAL_FIELDS = [
    "date",
    "instrument",
    "model_name",
    "model_family",
    "candidate_rank",
    "buy_score",
    "raw_score",
    "score_rank",
    "full_qlib_rank",
    "signal_asof",
    "available_at",
    "source_artifact",
    "source_model_artifact",
    "source_feature_artifact",
]

INFERENCE_FIELDS = [
    "date",
    "instrument",
    "model_id",
    "model_family",
    "provider_uri",
    "normalized_source",
    "feature_artifact",
    "source_model_artifact",
    "source_training_manifest",
    "signal_asof",
    "available_at",
    "readiness_status",
]

REQUIRED_PROVIDER_FIELDS = {"open", "high", "low", "close", "volume", "vwap", "factor"}

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

FORBIDDEN_ACTIONS_FALSE = {
    "model_training_triggered": False,
    "model_tuning_triggered": False,
    "ltr_model_b_triggered": False,
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

CONTAINED_FORBIDDEN_PATH_PARTS = {
    "latest",
    "catalog",
    "publish",
    "published",
    "accepted_latest",
    "readonly",
    "agent",
    "agent_daily_prompt",
    "monitor",
    "broker",
    "order",
    "target_position",
    "target_weight",
    "target_output",
}
CONTAINED_FORBIDDEN_OUTPUT_FRAGMENTS = (
    "data_tw/canonical/",
    "data_tw/artifacts/",
    "data_tw/catalog/",
    "docs/tw_data_governance/",
)


@dataclass(frozen=True)
class ModelARuntimeConfig:
    target_asof: str
    provider_root: Path
    normalized_root: Path
    output_root: Path
    no_publish: bool
    no_catalog: bool
    no_latest: bool
    no_target_output: bool
    allow_real_execution: bool = False

    @property
    def payload_root(self) -> Path:
        return self.output_root / "planned_future_outputs"

    def model_inference_input_dir(self, run_id: str) -> Path:
        return self.payload_root / "model_inference_input" / MODEL_ID / run_id

    def score_job_dir(self, run_id: str) -> Path:
        return self.payload_root / "score_job" / MODEL_ID / run_id

    def model_signal_dir(self, run_id: str) -> Path:
        return self.payload_root / "model_signal_artifact" / MODEL_ID / run_id

    def qlib_run_dir(self, run_id: str) -> Path:
        return self.payload_root / "qlib_scoring_runs" / run_id

    def pipeline_validation_path(self, run_id: str) -> Path:
        return self.payload_root / "score_pipeline_validation" / run_id / "validation.json"

    def execution_report_path(self, run_id: str) -> Path:
        return self.payload_root / "score_pipeline_report" / run_id / "execution_report.md"

    def runtime_paths(self, run_id: str) -> dict[str, Path]:
        input_dir = self.model_inference_input_dir(run_id)
        score_dir = self.score_job_dir(run_id)
        signal_dir = self.model_signal_dir(run_id)
        qlib_dir = self.qlib_run_dir(run_id)
        return {
            "model_inference_input_dir": input_dir,
            "model_inference_input_manifest": input_dir / "manifest.json",
            "model_inference_input_frame": input_dir / "inference_frame.csv",
            "score_job_dir": score_dir,
            "score_job_manifest": score_dir / "manifest.json",
            "score_job_raw_scores": score_dir / "raw_scores.csv",
            "model_signal_dir": signal_dir,
            "model_signal_manifest": signal_dir / "manifest.json",
            "model_signal_signals": signal_dir / "signals.csv",
            "qlib_run_dir": qlib_dir,
            "qlib_prediction": qlib_dir / "prediction.csv",
            "pipeline_validation": self.pipeline_validation_path(run_id),
            "execution_report": self.execution_report_path(run_id),
        }


def resolve_runtime_path(path: Path | str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    return p.resolve(strict=False)


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def contained_path_forbidden_reason(path: Path) -> str | None:
    rel_text = rel(path).replace("\\", "/")
    lowered_parts = {part.lower() for part in path.parts}
    for part in sorted(CONTAINED_FORBIDDEN_PATH_PARTS):
        if part in lowered_parts:
            return f"forbidden_path_part:{part}"
    for fragment in CONTAINED_FORBIDDEN_OUTPUT_FRAGMENTS:
        if fragment in rel_text:
            return f"forbidden_path_fragment:{fragment.rstrip('/')}"
    return None


def make_modela_runtime_config(
    *,
    target_asof: str,
    provider_root: Path | str,
    normalized_root: Path | str,
    output_root: Path | str,
    no_publish: bool,
    no_catalog: bool,
    no_latest: bool,
    no_target_output: bool,
    allow_real_execution: bool = False,
) -> ModelARuntimeConfig:
    return ModelARuntimeConfig(
        target_asof=target_asof,
        provider_root=resolve_runtime_path(provider_root),
        normalized_root=resolve_runtime_path(normalized_root),
        output_root=resolve_runtime_path(output_root),
        no_publish=no_publish,
        no_catalog=no_catalog,
        no_latest=no_latest,
        no_target_output=no_target_output,
        allow_real_execution=allow_real_execution,
    )


def validate_modela_runtime_config(config: ModelARuntimeConfig, *, run_id: str = "planned") -> dict[str, Any]:
    errors: list[str] = []
    for name in ("no_publish", "no_catalog", "no_latest", "no_target_output"):
        if getattr(config, name) is not True:
            errors.append(f"required_safety_flag_missing:{name}")
    if not config.provider_root.exists():
        errors.append("provider_root_missing")
    if not (config.provider_root / "calendars/day.txt").exists():
        errors.append("provider_calendar_missing")
    if not (config.provider_root / "features").exists():
        errors.append("provider_features_missing")
    if not config.normalized_root.exists():
        errors.append("normalized_root_missing")
    normalized_count = len(list(config.normalized_root.glob("TW*.csv"))) if config.normalized_root.exists() else 0
    if normalized_count and normalized_count != 150:
        errors.append(f"normalized_csv_count_not_150:{normalized_count}")
    for key, path in config.runtime_paths(run_id).items():
        if not is_relative_to(path, config.output_root):
            errors.append(f"runtime_path_not_under_output_root:{key}")
        reason = contained_path_forbidden_reason(path)
        if reason:
            errors.append(f"runtime_path_{key}_{reason}")
    for key, path in {
        "output_root": config.output_root,
        "payload_root": config.payload_root,
    }.items():
        reason = contained_path_forbidden_reason(path)
        if reason:
            errors.append(f"{key}_{reason}")
    return {
        "schema_version": "modela.contained_runtime_config.v1",
        "created_at": utc_now(),
        "status": "pass" if not errors else "fail",
        "target_asof": config.target_asof,
        "provider_root": rel(config.provider_root),
        "normalized_root": rel(config.normalized_root),
        "output_root": rel(config.output_root),
        "payload_root": rel(config.payload_root),
        "normalized_csv_count": normalized_count,
        "safety_flags": {
            "no_publish": config.no_publish,
            "no_catalog": config.no_catalog,
            "no_latest": config.no_latest,
            "no_target_output": config.no_target_output,
            "allow_real_execution": config.allow_real_execution,
        },
        "runtime_paths": {key: rel(path) for key, path in config.runtime_paths(run_id).items()},
        "real_execution_default_reachable": config.allow_real_execution,
        "errors": errors,
    }


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_run_id(asof: str = TARGET_ASOF) -> str:
    return f"dng7_modela_{asof.replace('-', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return str(p.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(p)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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


def load_universe(provider_root: Path | None = None) -> list[str]:
    if provider_root is None:
        if not QLIB_UNIVERSE.exists():
            return []
        values = [line.strip().upper() for line in QLIB_UNIVERSE.read_text(encoding="utf-8").splitlines() if line.strip()]
        return sorted(values)
    instruments = provider_root / "instruments/all.txt"
    if not instruments.exists():
        return []
    values = [line.split()[0].strip().upper() for line in instruments.read_text(encoding="utf-8").splitlines() if line.strip()]
    return sorted(values)


def provider_calendar_max(provider_root: Path | None = None) -> str | None:
    path = (provider_root or QLIB_PROVIDER) / "calendars/day.txt"
    if not path.exists():
        return None
    rows = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return max(rows) if rows else None


def normalized_symbol_summary(asof: str, symbols: list[str], normalized_root: Path | None = None) -> dict[str, Any]:
    normalized_root = normalized_root or QLIB_NORMALIZED
    rows: list[dict[str, Any]] = []
    missing_files: list[str] = []
    missing_asof: list[str] = []
    for symbol in symbols:
        path = normalized_root / f"{symbol}.csv"
        if not path.exists():
            missing_files.append(symbol)
            continue
        try:
            dates = pd.read_csv(path, usecols=["date"])["date"].astype(str)
        except Exception:
            missing_files.append(symbol)
            continue
        date_max = str(dates.max()) if not dates.empty else ""
        has_asof = bool((dates == asof).any())
        if not has_asof:
            missing_asof.append(symbol)
        rows.append({"instrument": symbol, "date_max": date_max, "has_asof": has_asof})
    frame = pd.DataFrame(rows)
    return {
        "symbols_expected": len(symbols),
        "symbols_found": len(rows),
        "symbols_with_asof": int(frame["has_asof"].sum()) if not frame.empty else 0,
        "min_date_max": str(frame["date_max"].min()) if not frame.empty else "",
        "max_date_max": str(frame["date_max"].max()) if not frame.empty else "",
        "missing_files": missing_files,
        "missing_asof": missing_asof,
    }


def provider_field_inventory(symbols: list[str], provider_root: Path | None = None) -> dict[str, Any]:
    provider_root = provider_root or QLIB_PROVIDER
    counts = {field: 0 for field in sorted(REQUIRED_PROVIDER_FIELDS)}
    unexpected: set[str] = set()
    missing_symbols: list[str] = []
    for symbol in symbols:
        feature_dir = provider_root / "features" / symbol.lower()
        if not feature_dir.exists():
            missing_symbols.append(symbol)
            continue
        fields = {p.name.split(".")[0] for p in feature_dir.glob("*.day.bin")}
        for field in fields:
            if field in counts:
                counts[field] += 1
            else:
                unexpected.add(field)
    return {
        "expected_field_counts": counts,
        "unexpected_fields": sorted(unexpected),
        "missing_feature_symbols": missing_symbols,
        "status": "pass"
        if not unexpected and not missing_symbols and all(v == len(symbols) for v in counts.values())
        else "fail",
    }


def forbidden_columns(columns: list[str]) -> list[str]:
    out = []
    for col in columns:
        lowered = col.lower()
        if lowered in FORBIDDEN_EXACT_FIELDS or any(lowered.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
            out.append(col)
    return sorted(out)


def parse_run_json(stdout: str) -> dict[str, Any]:
    match = re.search(r'(\{\s*"run_id"\s*:.*\})\s*$', stdout, flags=re.S)
    if not match:
        raise ValueError("could not parse qlib run JSON from stdout")
    return json.loads(match.group(1))


def to_float(value: Any) -> float | None:
    try:
        number = float(value)
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def file_entry(path: Path, key: str, required: bool = True) -> dict[str, Any]:
    return {
        "key": key,
        "path": rel(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() and path.is_file() else None,
        "sha256": sha256_file(path) if path.exists() and path.is_file() else None,
        "required": required,
    }


def validate_signal_frame(signals: pd.DataFrame, target_asof: str) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    missing = sorted(set(SIGNAL_FIELDS) - set(signals.columns))
    if missing:
        errors.append(f"missing_signal_fields:{','.join(missing)}")
    forbidden = forbidden_columns(list(signals.columns))
    if forbidden:
        errors.append(f"forbidden_signal_fields:{','.join(forbidden)}")
    duplicate_count = int(signals.duplicated(["date", "instrument"]).sum()) if {"date", "instrument"} <= set(signals.columns) else -1
    if duplicate_count:
        errors.append(f"duplicate_date_instrument:{duplicate_count}")
    if "date" in signals.columns:
        dates = sorted(str(x) for x in signals["date"].dropna().unique())
        if dates != [target_asof]:
            errors.append(f"signal_date_not_target:{dates}")
    for field in ["candidate_rank", "buy_score", "raw_score", "score_rank", "full_qlib_rank"]:
        if field in signals.columns and pd.to_numeric(signals[field], errors="coerce").isna().any():
            errors.append(f"non_numeric_signal_field:{field}")
    if {"available_at", "signal_asof"} <= set(signals.columns):
        bad_available = signals[pd.to_datetime(signals["available_at"], errors="coerce") > pd.to_datetime(signals["signal_asof"], errors="coerce")]
        if not bad_available.empty:
            errors.append(f"available_at_after_signal_asof:{len(bad_available)}")
    summary = {
        "row_count": int(len(signals)),
        "duplicate_key_count": duplicate_count,
        "date_min": str(signals["date"].min()) if "date" in signals.columns and len(signals) else "",
        "date_max": str(signals["date"].max()) if "date" in signals.columns and len(signals) else "",
        "instrument_count": int(signals["instrument"].nunique()) if "instrument" in signals.columns else 0,
        "forbidden_columns": forbidden,
    }
    return errors, summary
