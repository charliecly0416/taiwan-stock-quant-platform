#!/usr/bin/env python3
"""Build one isolated, research-only B19R2R daily shadow signal artifact."""
from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MODEL_A_ID = "e4_frozen_qlib_2018_2022"
MODEL_B_ID = "modelb_b19r2r_lambdarank_exact50_78f_v2"
MODEL_B_SHA256 = "8d31069593cc8a1cc7c6fa7ac4cf50a9e897a76af0ab446ddbc26551fc5e5421"
FEATURE_ORDER_SHA256 = "2e0c169fb7762240aa20bc31ea53ac21b6a69db99dabea2f897421121105f2ca"
MODEL_PATH = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_training_20260916/training_output_v1/MODEL_B_B19R2R_LGBM_RANKER.pkl"
TRAINING_MANIFEST = MODEL_PATH.parent / "TRAINING_MANIFEST.json"
FEATURE_SCHEMA = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b2_canonical_pit_features_20260913/FEATURE_SCHEMA.json"
MODEL_A_HISTORY = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_pretraining_materialization_20260916/MODEL_A_FULL_CROSS_SECTION.parquet"
MODEL_A_SIGNAL_ROOT = ROOT / "data_tw/artifacts/signals" / MODEL_A_ID
MODEL_A_PREDICTION_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal"
TWII_CAPTURE_SCRIPT = ROOT / "scripts/capture_modelb_b19r2r_twii_yahoo_v2.py"
CLEAN_CALENDAR_ANCHOR = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_v4_source_run_20260916/logical_composite_v2/EXTENDED_CLEAN_CALENDAR.txt"
CLEAN_CALENDAR_ANCHOR_SHA256 = "5d2a84976f6fb36a0cef4e998be8ab128365c1c15a48df06322ebc5da35c7b98"
EXCLUDED = {"TW7769"}
FORBIDDEN_TOKENS = ("label", "outcome", "future", "forward_return", "next_open", "next_close", "realized_pnl")
PROTECTED_POINTERS = (
    ROOT / "configs/active_baseline_descriptor.yaml",
    ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
)
PROSPECTIVE_EVENT_ROOT = ROOT / "data_tw/experiments/modelb_b19r2r_v5_prospective_accumulator"
PROSPECTIVE_EVENT_LEDGER = PROSPECTIVE_EVENT_ROOT / "research_shadow_events.jsonl"


class ShadowError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise ShadowError("B19R2R_BLOCKED_TIMEZONE", str(value))
    return value.astimezone(UTC).isoformat(timespec="seconds")


def parse_time(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ShadowError("B19R2R_BLOCKED_TIME", str(value)) from exc
    if parsed.tzinfo is None:
        raise ShadowError("B19R2R_BLOCKED_TIMEZONE", str(value))
    return parsed.astimezone(UTC)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def resolve_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ShadowError("B19R2R_BLOCKED_JSON", str(path)) from exc
    if not isinstance(payload, dict):
        raise ShadowError("B19R2R_BLOCKED_JSON_OBJECT", str(path))
    return payload


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def canonical_hash(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def append_prospective_event(output_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    """Append one idempotent settlement-pending event outside protected pointers.

    This is deliberately separate from the Model A/latest chain.  A repeated
    invocation for the same asof and source run is a no-op; a conflicting
    artifact is quarantined instead of replacing the first observation.
    """
    manifest_path = output_dir / "manifest.json"
    manifest_sha = sha256(manifest_path)
    signal_sha = sha256(output_dir / "signals.csv")
    event_key = f"{manifest.get('asof', '')}|{manifest.get('source_acquisition_run_id', '')}"
    body = {
        "schema_version": "modelb_b19r2r.v5.prospective_event.v1",
        "event_type": "SIGNAL_CAPTURED",
        "status": "settlement_pending",
        "event_key": event_key,
        "asof": manifest.get("asof"),
        "source_acquisition_run_id": manifest.get("source_acquisition_run_id"),
        "decision_cutoff": manifest.get("decision_cutoff"),
        "model_a_id": MODEL_A_ID,
        "model_b_id": MODEL_B_ID,
        "signal_artifact": rel(output_dir / "signals.csv"),
        "signal_artifact_sha256": signal_sha,
        "manifest": rel(manifest_path),
        "manifest_sha256": manifest_sha,
        "candidate_count": int(manifest.get("row_count") or 0),
        "tw7769_excluded": manifest.get("tw7769_excluded") is True,
        "production_allowed": False,
        "no_apply": True,
        "baseline_unchanged": True,
        "settlement_required": True,
    }
    output_event = {
        **body,
        "ledger": rel(PROSPECTIVE_EVENT_LEDGER),
        "append_only": True,
    }
    write_json(output_dir / "prospective_event.json", output_event)
    if manifest.get("retrospective_fixture") is True:
        return {**output_event, "status": "SKIPPED_RETROSPECTIVE_FIXTURE", "changed": False}

    PROSPECTIVE_EVENT_ROOT.mkdir(parents=True, exist_ok=True)
    lock_path = PROSPECTIVE_EVENT_LEDGER.with_suffix(".lock")
    with lock_path.open("a+", encoding="utf-8") as lock_stream:
        fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX)
        try:
            events: list[dict[str, Any]] = []
            if PROSPECTIVE_EVENT_LEDGER.exists():
                for line in PROSPECTIVE_EVENT_LEDGER.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        events.append(json.loads(line))
            existing = next((item for item in events if item.get("event_key") == event_key), None)
            if existing is not None:
                if existing.get("manifest_sha256") == manifest_sha and existing.get("signal_artifact_sha256") == signal_sha:
                    result = {**existing, "status": "IDEMPOTENT_NOOP", "changed": False}
                else:
                    quarantine = PROSPECTIVE_EVENT_ROOT / "quarantine" / f"{manifest.get('asof', 'unknown')}.{manifest_sha}.json"
                    quarantine.parent.mkdir(parents=True, exist_ok=True)
                    write_json(quarantine, {"status": "CONFLICTING_SOURCE_QUARANTINED", **output_event, "observed_existing_manifest_sha256": existing.get("manifest_sha256")})
                    result = {**output_event, "status": "CONFLICTING_SOURCE_QUARANTINED", "changed": False, "quarantine": rel(quarantine)}
            else:
                previous = events[-1].get("event_hash") if events else "GENESIS"
                committed = {**body, "created_at": iso(utc_now()), "previous_event_hash": previous}
                event = {**committed, "event_hash": canonical_hash(committed)}
                with PROSPECTIVE_EVENT_LEDGER.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(event, ensure_ascii=True, sort_keys=True) + "\n")
                result = {**event, "status": "APPENDED", "changed": True}
        finally:
            fcntl.flock(lock_stream.fileno(), fcntl.LOCK_UN)
    write_json(output_dir / "prospective_event.json", result)
    return result


def pointer_fingerprints() -> dict[str, str | None]:
    return {rel(path): sha256(path) if path.is_file() else None for path in PROTECTED_POINTERS}


def normalize_symbol(value: Any) -> str:
    symbol = str(value).strip().upper()
    return symbol if symbol.startswith("TW") else f"TW{symbol}"


def forbidden_columns(columns: list[str]) -> list[str]:
    return sorted(column for column in columns if any(token in column.lower() for token in FORBIDDEN_TOKENS))


def feature_order() -> list[str]:
    values = list(read_json(FEATURE_SCHEMA).get("feature_order") or [])
    digest = hashlib.sha256(json.dumps(values, separators=(",", ":")).encode()).hexdigest()
    if len(values) != 78 or digest != FEATURE_ORDER_SHA256:
        raise ShadowError("B19R2R_BLOCKED_FEATURE_ORDER", digest)
    return values


def next_weekday_open(asof: str) -> datetime:
    day = date.fromisoformat(asof) + timedelta(days=1)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return datetime.fromisoformat(f"{day.isoformat()}T01:00:00+00:00")


def validate_capture_window(asof: str, decision_cutoff: str, next_open: str, *, retrospective_fixture: bool = False) -> tuple[datetime, datetime]:
    cutoff = parse_time(decision_cutoff)
    next_session = parse_time(next_open)
    close = datetime.fromisoformat(f"{asof}T05:30:00+00:00")
    if cutoff < close:
        raise ShadowError("B19R2R_BLOCKED_BEFORE_CLOSE", decision_cutoff)
    if cutoff >= next_session:
        raise ShadowError("B19R2R_BLOCKED_AFTER_NEXT_OPEN", decision_cutoff)
    if not retrospective_fixture and utc_now() >= next_session:
        raise ShadowError("B19R2R_BLOCKED_AFTER_NEXT_OPEN", iso(utc_now()))
    return cutoff, next_session


def _path_values(values: Any) -> list[Path]:
    result: list[Path] = []
    for item in values if isinstance(values, list) else []:
        value = item.get("path") if isinstance(item, dict) else item
        if str(value or "").strip():
            result.append(resolve_path(str(value)))
    return result


def _verify_source_artifacts(source: dict[str, Any], paths: list[Path]) -> None:
    evidence = {
        str(resolve_path(str(item.get("path")))): str(item.get("sha256") or "")
        for item in source.get("artifacts", [])
        if isinstance(item, dict) and item.get("path")
    }
    for path in paths:
        if not path.is_file():
            raise ShadowError("B19R2R_BLOCKED_SOURCE_FILE", str(path))
        expected = evidence.get(str(path.resolve()))
        if not expected or expected != sha256(path):
            raise ShadowError("B19R2R_BLOCKED_SOURCE_HASH", str(path))


def validate_hsa_children(handoff_path: Path, asof: str, source_run_id: str, cutoff: datetime) -> dict[str, Path]:
    handoff = read_json(handoff_path)
    sources = handoff.get("sources")
    if not isinstance(sources, list):
        raise ShadowError("B19R2R_BLOCKED_HANDOFF_SOURCES", str(handoff_path))
    selected: dict[str, Path] = {}
    for family in ("adjusted_price", "institutional_flow", "margin_short"):
        matches = [item for item in sources if isinstance(item, dict) and item.get("source_family") == family]
        if len(matches) != 1:
            raise ShadowError("B19R2R_BLOCKED_HANDOFF_CHILD", family)
        source = matches[0]
        absent = {normalize_symbol(item) for item in source.get("absent_scope", [])}
        unknown = {normalize_symbol(item) for item in source.get("unknown_scope", [])}
        if (
            source.get("acquisition_run_id") != source_run_id
            or source.get("target_asof") != asof
            or source.get("pit_status") != "PASS"
            or source.get("source_validator_status") != "PASS"
            or (absent | unknown) - EXCLUDED
            or parse_time(source.get("available_at")) > cutoff
        ):
            raise ShadowError("B19R2R_BLOCKED_HANDOFF_CHILD_CONTRACT", family)
        normalized = _path_values(source.get("normalized_files"))
        adapter = _path_values(source.get("adapter_output_files"))
        if len(normalized) != 1 or len(adapter) != 1:
            raise ShadowError("B19R2R_BLOCKED_HANDOFF_CHILD_PATHS", family)
        _verify_source_artifacts(source, [*normalized, *adapter])
        adapter_payload = read_json(adapter[0])
        if (
            adapter_payload.get("acquisition_run_id") != source_run_id
            or adapter_payload.get("target_asof") != asof
            or adapter_payload.get("pit_status") != "PASS"
            or adapter_payload.get("validator_status") != "PASS"
        ):
            raise ShadowError("B19R2R_BLOCKED_ADAPTER_CONTRACT", family)
        selected[family] = normalized[0]
    return selected


def _validate_yahoo_twii(
    manifest_path: Path,
    csv_path: Path,
    asof: str,
    source_run_id: str,
    cutoff: datetime,
    next_open: datetime,
) -> Path:
    manifest = read_json(manifest_path)
    artifact = (manifest.get("artifacts") or {}).get("normalized_csv") or {}
    implementation = manifest.get("implementation") or {}
    if (
        manifest.get("schema_version") != "modelb_b19r2r.yahoo_twii_dual_interval_capture.v2"
        or manifest.get("target_asof") != asof
        or manifest.get("acquisition_run_id") != source_run_id
        or manifest.get("source_id") != "yahoo.finance.chart.^TWII.dual_interval.v2"
        or manifest.get("provider") != "Yahoo Finance"
        or manifest.get("pit_status") != "PASS"
        or manifest.get("validator_status") not in {"PASS", "PASS_CANDIDATE_AWAITING_INDEPENDENT_REVIEW"}
        or manifest.get("production_allowed") is not False
        or parse_time(manifest.get("available_at")) > cutoff
        or parse_time(manifest.get("available_at")) >= next_open
        or artifact.get("sha256") != sha256(csv_path)
        or resolve_path(str(implementation.get("path") or "")) != TWII_CAPTURE_SCRIPT
        or implementation.get("sha256") != sha256(TWII_CAPTURE_SCRIPT)
    ):
        raise ShadowError("B19R2R_BLOCKED_TWII_CONTRACT", str(manifest_path))
    frame = pd.read_csv(csv_path)
    if len(frame[frame["date"].astype(str).eq(asof)]) != 1:
        raise ShadowError("B19R2R_BLOCKED_TWII_TARGET", asof)
    return csv_path


def select_or_capture_yahoo_twii(
    *,
    output_dir: Path,
    handoff_path: Path,
    asof: str,
    source_run_id: str,
    cutoff: datetime,
    next_open: datetime,
    explicit_csv: Path | None = None,
    explicit_manifest: Path | None = None,
) -> Path:
    if explicit_csv is not None or explicit_manifest is not None:
        if explicit_csv is None or explicit_manifest is None:
            raise ShadowError("B19R2R_BLOCKED_TWII_EXPLICIT_PAIR")
        return _validate_yahoo_twii(
            explicit_manifest,
            explicit_csv,
            asof,
            source_run_id,
            cutoff,
            next_open,
        )

    handoff = read_json(handoff_path)
    for source in handoff.get("sources", []):
        if not isinstance(source, dict) or source.get("source_family") != "twii" or source.get("provider") != "Yahoo Finance":
            continue
        adapter_paths = _path_values(source.get("adapter_output_files"))
        normalized_paths = _path_values(source.get("normalized_files"))
        if len(adapter_paths) != 1 or len(normalized_paths) != 1:
            continue
        adapter = read_json(adapter_paths[0])
        fallback = adapter.get("fallback") if isinstance(adapter.get("fallback"), dict) else {}
        manifest_value = fallback.get("manifest")
        if manifest_value:
            return _validate_yahoo_twii(
                resolve_path(str(manifest_value)),
                normalized_paths[0],
                asof,
                source_run_id,
                cutoff,
                next_open,
            )

    capture_dir = output_dir / "yahoo_twii"
    env = os.environ.copy()
    env.update({
        "B19YTWII_RESEARCH_ROOT": str(output_dir),
        "B19YTWII_TARGET_ASOF": asof,
        "B19YTWII_ACQUISITION_RUN_ID": source_run_id,
        "B19YTWII_SESSION_CLOSE_UTC": f"{asof}T05:30:00+00:00",
        "B19YTWII_NEXT_OPEN_UTC": iso(next_open),
    })
    completed = subprocess.run(
        [sys.executable, str(TWII_CAPTURE_SCRIPT), "--output", str(capture_dir)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    (output_dir / "yahoo_twii_capture.stdout.txt").write_text(completed.stdout or "", encoding="utf-8")
    (output_dir / "yahoo_twii_capture.stderr.txt").write_text(completed.stderr or "", encoding="utf-8")
    if completed.returncode != 0:
        raise ShadowError("B19R2R_BLOCKED_TWII_CAPTURE", (completed.stderr or completed.stdout)[-1000:])
    return _validate_yahoo_twii(
        capture_dir / "TWII_CAPTURE_MANIFEST.json",
        capture_dir / "TWII_NORMALIZED.csv",
        asof,
        source_run_id,
        cutoff,
        next_open,
    )


def validate_model_a(signal_dir: Path, asof: str, source_run_id: str, cutoff: datetime) -> tuple[pd.DataFrame, dict[str, Any]]:
    manifest = read_json(signal_dir / "manifest.json")
    validator = read_json(signal_dir / "validator_report.json")
    manifest_cutoff = str(manifest.get("decision_cutoff") or "").strip()
    cutoff_matches = (
        parse_time(manifest_cutoff) == cutoff
        if manifest_cutoff
        else parse_time(manifest.get("created_at")) <= cutoff
    )
    if (
        manifest.get("artifact_type") != "ModelSignalArtifact"
        or manifest.get("model_id") != MODEL_A_ID
        or manifest.get("asof") != asof
        or manifest.get("status") != "READY"
        or int(manifest.get("row_count") or 0) != 150
        or manifest.get("source_acquisition_run_id") != source_run_id
        or not cutoff_matches
        or validator.get("ok") is not True
    ):
        raise ShadowError("B19R2R_BLOCKED_MODELA_CONTRACT", str(signal_dir))
    signals = pd.read_csv(signal_dir / "signals.csv")
    required = {"date", "instrument", "candidate_rank", "raw_score", "full_qlib_rank"}
    if not required.issubset(signals) or len(signals) != 150 or signals.instrument.duplicated().any():
        raise ShadowError("B19R2R_BLOCKED_MODELA_SCOPE", str(signal_dir))
    signals["instrument"] = signals.instrument.map(normalize_symbol)
    for field in ("candidate_rank", "raw_score", "full_qlib_rank"):
        signals[field] = pd.to_numeric(signals[field], errors="coerce")
    if not np.isfinite(signals[["candidate_rank", "raw_score", "full_qlib_rank"]].to_numpy(float)).all():
        raise ShadowError("B19R2R_BLOCKED_MODELA_NONFINITE")
    exact = signals[signals.candidate_rank.le(50)].copy().sort_values(["candidate_rank", "instrument"], kind="mergesort")
    if len(exact) != 50 or exact.candidate_rank.astype(int).tolist() != list(range(1, 51)):
        raise ShadowError("B19R2R_BLOCKED_MODELA_EXACT50")
    exact = exact[~exact.instrument.isin(EXCLUDED)].copy()
    return exact, manifest


def _validated_history_frame(path: Path, cutoff: datetime) -> tuple[pd.DataFrame, str] | None:
    manifest_path = path.parent / "manifest.json"
    if not manifest_path.is_file():
        return None
    manifest = read_json(manifest_path)
    try:
        created = parse_time(manifest.get("created_at"))
    except ShadowError:
        return None
    if (
        manifest.get("model_id") != MODEL_A_ID
        or manifest.get("status") != "READY"
        or int(manifest.get("row_count") or 0) != 150
        or created > cutoff
    ):
        return None
    frame = pd.read_csv(path, usecols=["date", "instrument", "raw_score", "full_qlib_rank"])
    frame["date"] = frame.date.astype(str).str[:10]
    frame["instrument"] = frame.instrument.map(normalize_symbol)
    if len(frame) != 150 or frame.instrument.duplicated().any():
        return None
    return frame.rename(columns={"raw_score": "model_a_raw_score"}), sha256(path)


def _validated_prediction_frame(path: Path, cutoff: datetime) -> tuple[pd.DataFrame, str] | None:
    artifact_path = path.parent / "artifact_manifest.json"
    metadata_path = path.parent / "run_metadata.json"
    if not artifact_path.is_file() or not metadata_path.is_file():
        return None
    artifact = read_json(artifact_path)
    metadata = read_json(metadata_path)
    entry = next((item for item in artifact.get("entries", []) if isinstance(item, dict) and item.get("key") == "prediction"), None)
    try:
        created = parse_time(metadata.get("created_at"))
    except ShadowError:
        return None
    if (
        artifact.get("status") != "accepted"
        or metadata.get("status") != "accepted"
        or artifact.get("run_id") != metadata.get("run_id")
        or not isinstance(entry, dict)
        or entry.get("sha256") != sha256(path)
        or created > cutoff
    ):
        return None
    frame = pd.read_csv(path)
    if not {"datetime", "instrument", "score"}.issubset(frame) or len(frame) != 150:
        return None
    frame["date"] = frame.datetime.astype(str).str[:10]
    frame["instrument"] = frame.instrument.map(normalize_symbol)
    frame["model_a_raw_score"] = pd.to_numeric(frame.score, errors="coerce")
    frame = frame.sort_values(["model_a_raw_score", "instrument"], ascending=[False, True], kind="mergesort")
    frame["full_qlib_rank"] = np.arange(1, 151)
    if frame.instrument.duplicated().any() or not np.isfinite(frame.model_a_raw_score.to_numpy(float)).all():
        return None
    return frame[["date", "instrument", "model_a_raw_score", "full_qlib_rank"]], sha256(path)


def model_a_history(current_dir: Path, asof: str, cutoff: datetime) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    historical = pd.read_parquet(MODEL_A_HISTORY, columns=["date", "instrument", "model_a_raw_score", "full_qlib_rank"])
    historical["date"] = historical.date.astype(str).str[:10]
    historical["instrument"] = historical.instrument.map(normalize_symbol)
    max_frozen = str(historical.date.max())
    by_day: dict[str, list[tuple[pd.DataFrame, str, Path]]] = {}
    for path in MODEL_A_SIGNAL_ROOT.glob("*/signals.csv"):
        parsed = _validated_history_frame(path, cutoff)
        if parsed is None:
            continue
        frame, digest = parsed
        day = str(frame.date.iloc[0])
        if max_frozen < day <= asof:
            by_day.setdefault(day, []).append((frame.sort_values("instrument").reset_index(drop=True), digest, path))
    for path in MODEL_A_PREDICTION_ROOT.glob("option_c_daily_signal_*/prediction.csv"):
        parsed = _validated_prediction_frame(path, cutoff)
        if parsed is None:
            continue
        frame, digest = parsed
        day = str(frame.date.iloc[0])
        if max_frozen < day <= asof:
            by_day.setdefault(day, []).append((frame.sort_values("instrument").reset_index(drop=True), digest, path))
    current_path = current_dir / "signals.csv"
    if asof not in by_day or all(path.resolve() != current_path.resolve() for _, _, path in by_day[asof]):
        parsed = _validated_history_frame(current_path, cutoff)
        if parsed is None:
            raise ShadowError("B19R2R_BLOCKED_MODELA_HISTORY_CURRENT")
        frame, digest = parsed
        by_day.setdefault(asof, []).append((frame.sort_values("instrument").reset_index(drop=True), digest, current_path))
    additions: list[pd.DataFrame] = []
    lineage: list[dict[str, str]] = []
    for day in sorted(by_day):
        candidates = by_day[day]
        reference = candidates[0][0]
        for candidate, _, path in candidates[1:]:
            if reference.instrument.tolist() != candidate.instrument.tolist() or not np.array_equal(reference.model_a_raw_score.to_numpy(), candidate.model_a_raw_score.to_numpy()):
                raise ShadowError("B19R2R_BLOCKED_MODELA_HISTORY_DRIFT", f"{day}:{path}")
        additions.append(reference)
        lineage.extend({"date": day, "path": rel(path), "sha256": digest} for _, digest, path in candidates)
    if asof not in by_day:
        raise ShadowError("B19R2R_BLOCKED_MODELA_HISTORY", asof)
    return pd.concat([historical, *additions], ignore_index=True), lineage


def positive_streak(values: pd.Series) -> pd.Series:
    result: list[float] = []
    count = 0
    for value in values.fillna(0).astype(int):
        count = count + 1 if value else 0
        result.append(float(count))
    return pd.Series(result, index=values.index, dtype=float)


def signed_streak(values: pd.Series) -> pd.Series:
    result: list[float] = []
    sign = count = 0
    for value in values:
        current = 0 if pd.isna(value) or value == 0 else (1 if value > 0 else -1)
        if current == 0:
            sign = count = 0
        elif current == sign:
            count += 1
        else:
            sign, count = current, 1
        result.append(float(sign * count))
    return pd.Series(result, index=values.index, dtype=float)


def rsi14(close: pd.Series) -> tuple[pd.Series, pd.Series]:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).rolling(14, min_periods=14).mean()
    ready = delta.rolling(14, min_periods=14).count().eq(14) & close.notna()
    value = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    return value.mask(ready & loss.eq(0), 50.0).where(ready), ready


def load_records(path: Path) -> pd.DataFrame:
    records = read_json(path).get("records")
    if not isinstance(records, list) or not records:
        raise ShadowError("B19R2R_BLOCKED_NORMALIZED_RECORDS", str(path))
    frame = pd.DataFrame(records)
    blocked = forbidden_columns(frame.columns.astype(str).tolist())
    if blocked or not {"trade_date", "symbol"}.issubset(frame):
        raise ShadowError("B19R2R_BLOCKED_NORMALIZED_SCHEMA", f"{path}:{blocked}")
    frame["date"] = frame.trade_date.astype(str).str[:10]
    frame["instrument"] = frame.symbol.map(normalize_symbol)
    return frame


def score_features(history: pd.DataFrame, asof: str) -> pd.DataFrame:
    scores = history.sort_values(["instrument", "date"], kind="mergesort").copy()
    scores["qlib_score_raw"] = pd.to_numeric(scores.model_a_raw_score, errors="coerce")
    scores["qlib_rank"] = pd.to_numeric(scores.full_qlib_rank, errors="coerce")
    group = scores.groupby("date", sort=False).qlib_score_raw
    scores["qlib_score_percentile_by_date"] = group.rank(pct=True, method="average", ascending=True)
    scores["qlib_score_zscore_by_date"] = (scores.qlib_score_raw - group.transform("mean")) / group.transform(lambda values: values.std(ddof=1)).replace(0, np.nan)
    for lag in (1, 3, 5):
        scores[f"rank_change_{lag}d"] = scores.groupby("instrument").qlib_rank.diff(lag)
    for threshold in (10, 30, 50):
        scores[f"top{threshold}_flag"] = scores.qlib_rank.le(threshold).astype(float)
    scores["top30_streak"] = scores.groupby("instrument", group_keys=False).top30_flag.apply(positive_streak)
    scores["top50_streak"] = scores.groupby("instrument", group_keys=False).top50_flag.apply(positive_streak)
    return scores[scores.date.eq(asof)].copy()


def decode_field(provider: Path, symbol: str, field: str, calendar: list[str]) -> np.ndarray:
    values = np.fromfile(provider / "features" / symbol.lower() / f"{field}.day.bin", dtype="<f4")
    if len(values) < 2:
        raise ShadowError("B19R2R_BLOCKED_PROVIDER_FIELD", f"{symbol}:{field}")
    expanded = np.full(len(calendar), np.nan)
    start = int(values[0])
    expanded[start:start + len(values) - 1] = values[1:]
    return expanded


def clean_calendar(actual_dates: list[str], asof: str) -> list[str]:
    if sha256(CLEAN_CALENDAR_ANCHOR) != CLEAN_CALENDAR_ANCHOR_SHA256:
        raise ShadowError("B19R2R_BLOCKED_CALENDAR_ANCHOR_HASH")
    anchor = [line.strip()[:10] for line in CLEAN_CALENDAR_ANCHOR.read_text(encoding="ascii").splitlines() if line.strip()]
    anchor_max = anchor[-1]
    appended = [day for day in actual_dates if anchor_max < day <= asof]
    calendar = [day for day in anchor if day <= asof] + sorted(set(appended))
    if not calendar or calendar != sorted(set(calendar)) or calendar[-1] != asof:
        raise ShadowError("B19R2R_BLOCKED_CLEAN_CALENDAR", asof)
    return calendar


def price_features(provider: Path, actual_dates: list[str], asof: str) -> tuple[pd.DataFrame, float, dict[str, Any]]:
    calendar_path = provider / "calendars/day.txt"
    source_calendar = [line.strip()[:10] for line in calendar_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not source_calendar or source_calendar[-1] != asof:
        raise ShadowError("B19R2R_BLOCKED_PROVIDER_SNAPSHOT_ASOF", str(provider))
    actual_set = set(actual_dates)
    frames: list[pd.DataFrame] = []
    fingerprints: list[dict[str, Any]] = []
    for directory in sorted(path for path in (provider / "features").iterdir() if path.is_dir()):
        symbol = directory.name.upper()
        for field in ("open", "high", "low", "close", "volume", "vwap"):
            path = directory / f"{field}.day.bin"
            fingerprints.append({"instrument": symbol, "field": field, "path": rel(path), "sha256": sha256(path), "bytes": path.stat().st_size})
        decoded = {field: decode_field(provider, symbol, field, source_calendar) for field in ("open", "high", "low", "close", "volume", "vwap")}
        raw = pd.DataFrame({"date": source_calendar, "instrument": symbol, **decoded})
        raw = raw[raw.date.isin(actual_set)].sort_values("date").reset_index(drop=True)
        close, volume = raw.close, raw.volume
        for window in (5, 10, 20, 60):
            raw[f"MA{window}"] = close.rolling(window, min_periods=window).mean()
        raw["RSI14"], raw["_rsi_ready"] = rsi14(close)
        raw["MACD"] = close.ewm(span=12, adjust=False, min_periods=12).mean() - close.ewm(span=26, adjust=False, min_periods=26).mean()
        raw["Bollinger_position"] = ((close - raw.MA20) / (2 * close.rolling(20, min_periods=20).std(ddof=1).replace(0, np.nan))).clip(-5, 5)
        daily_return = close.pct_change(fill_method=None)
        raw["ret20"] = close.pct_change(20, fill_method=None)
        raw["volatility20"] = daily_return.rolling(20, min_periods=20).std(ddof=1)
        raw["volume_ratio20"] = volume / volume.rolling(20, min_periods=20).mean().replace(0, np.nan)
        value = volume * raw.vwap
        raw["avg_trading_value_20d"] = value.rolling(20, min_periods=20).mean()
        raw["volume_stability20"] = 1 / (1 + volume.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan).rolling(20, min_periods=20).std(ddof=1))
        raw["missing_rate20"] = close.isna().astype(float).rolling(20, min_periods=1).mean()
        raw["suspension_proxy"] = (raw[["open", "high", "low", "close", "volume"]].isna().any(axis=1) | volume.le(0)).astype(float)
        raw["slippage_proxy"] = 1 / np.sqrt(value.where(value > 0))
        raw["_breadth_above"] = (close.notna() & raw.MA20.notna() & close.gt(raw.MA20)).astype(float)
        frames.append(raw[raw.date.eq(asof)])
    grid = pd.concat(frames, ignore_index=True)
    columns = ["MA5", "MA10", "MA20", "MA60", "RSI14", "MACD", "Bollinger_position", "ret20", "volatility20", "volume_ratio20", "avg_trading_value_20d", "volume_stability20", "missing_rate20", "suspension_proxy", "slippage_proxy", "_rsi_ready"]
    inventory = {
        "schema_version": "modelb_b19r2r.provider_input_inventory.v1",
        "provider_snapshot": rel(provider),
        "provider_calendar": {"path": rel(calendar_path), "sha256": sha256(calendar_path), "bytes": calendar_path.stat().st_size, "max_date": source_calendar[-1]},
        "clean_calendar_anchor": {"path": rel(CLEAN_CALENDAR_ANCHOR), "sha256": CLEAN_CALENDAR_ANCHOR_SHA256},
        "field_file_count": len(fingerprints),
        "field_files": fingerprints,
    }
    return grid[["date", "instrument", *columns]], float(grid._breadth_above.mean()), inventory


def orthogonal_features(price_records: pd.DataFrame, institutional_path: Path, margin_path: Path, asof: str) -> pd.DataFrame:
    dates = sorted(price_records.date.unique())
    if asof not in dates or dates.index(asof) == 0:
        raise ShadowError("B19R2R_BLOCKED_PRICE_CALENDAR", asof)
    prior = dates[dates.index(asof) - 1]
    institutional = load_records(institutional_path).sort_values(["instrument", "date"])
    for column in ("foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy"):
        institutional[column] = pd.to_numeric(institutional[column], errors="coerce")
    institutional["institutional_total_net_buy"] = institutional[["foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy"]].sum(axis=1, min_count=3)
    for column in ("foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy", "institutional_total_net_buy"):
        for window in (1, 3, 5, 10):
            institutional[f"{column}_roll{window}"] = institutional.groupby("instrument")[column].transform(lambda values: values.rolling(window, min_periods=1).sum())
    institutional["institutional_total_net_buy_streak"] = institutional.groupby("instrument", group_keys=False).institutional_total_net_buy.apply(signed_streak)
    institutional["institutional_missing_flag"] = institutional[["foreign_net_buy", "investment_trust_net_buy", "dealer_net_buy"]].isna().any(axis=1).astype(float)
    institutional["institutional_delay_flag"] = 0.0
    institutional["institutional_flow_delay_days"] = 0.0
    institutional["institutional_flow_asof_missing_flag"] = 0.0

    margin = load_records(margin_path).sort_values(["instrument", "date"])
    margin["margin_balance"] = pd.to_numeric(margin.margin_purchase_today_balance, errors="coerce")
    margin["margin_balance_change"] = margin.margin_balance - pd.to_numeric(margin.margin_purchase_yesterday_balance, errors="coerce")
    margin["short_balance"] = pd.to_numeric(margin.short_sale_today_balance, errors="coerce")
    margin["short_balance_change"] = margin.short_balance - pd.to_numeric(margin.short_sale_yesterday_balance, errors="coerce")
    for column in ("margin_balance_change", "short_balance_change"):
        for window in (1, 3, 5, 10):
            margin[f"{column}_roll{window}"] = margin.groupby("instrument")[column].transform(lambda values: values.rolling(window, min_periods=1).sum())
    margin["margin_direction_proxy"] = np.sign(margin.margin_balance_change)
    margin["short_direction_proxy"] = np.sign(margin.short_balance_change)
    margin["margin_short_divergence_proxy"] = margin.margin_direction_proxy - margin.short_direction_proxy
    margin["margin_short_missing_flag"] = margin[["margin_balance", "margin_balance_change", "short_balance", "short_balance_change"]].isna().any(axis=1).astype(float)
    margin["margin_short_delay_flag"] = 0.0
    margin["margin_short_delay_days"] = 0.0
    margin["margin_short_asof_missing_flag"] = 0.0
    order = feature_order()
    inst_columns = [item for item in order if item.startswith(("foreign_", "investment_trust_", "dealer_", "institutional_"))]
    margin_columns = [item for item in order if item.startswith(("margin_", "short_"))]
    return institutional[institutional.date.eq(prior)][["instrument", *inst_columns]].merge(
        margin[margin.date.eq(prior)][["instrument", *margin_columns]], on="instrument", how="outer", validate="one_to_one"
    )


def twii_features(path: Path, calendar: list[str], asof: str) -> dict[str, float]:
    frame = pd.read_csv(path, usecols=["date", "close"])
    frame["date"] = frame.date.astype(str).str[:10]
    aligned = frame.drop_duplicates("date", keep="last").set_index("date").reindex(calendar)
    close = pd.to_numeric(aligned.close, errors="coerce")
    if asof not in aligned.index or close.tail(120).isna().any():
        raise ShadowError("B19R2R_BLOCKED_TWII_HISTORY", asof)
    result = {
        "TWII_ret20": close.pct_change(20, fill_method=None).iloc[-1],
        "TWII_ret60": close.pct_change(60, fill_method=None).iloc[-1],
        "TWII_close_vs_MA60": close.iloc[-1] / close.rolling(60, min_periods=60).mean().iloc[-1] - 1,
        "TWII_close_vs_MA120": close.iloc[-1] / close.rolling(120, min_periods=120).mean().iloc[-1] - 1,
        "market_volatility20": close.pct_change(fill_method=None).rolling(20, min_periods=20).std(ddof=1).iloc[-1],
        "market_drawdown60": close.iloc[-1] / close.rolling(60, min_periods=20).max().iloc[-1] - 1,
    }
    if not np.isfinite(np.asarray(list(result.values()), dtype=float)).all():
        raise ShadowError("B19R2R_BLOCKED_TWII_FEATURES")
    return {key: float(value) for key, value in result.items()}


def require_keys(expected: pd.DataFrame, actual: pd.DataFrame, keys: list[str], label: str) -> None:
    left = set(map(tuple, expected[keys].itertuples(index=False, name=None)))
    right_rows = actual[keys]
    right = set(map(tuple, right_rows.itertuples(index=False, name=None)))
    if right_rows.duplicated().any() or left != right:
        raise ShadowError("B19R2R_BLOCKED_FEATURE_KEYS", label)


def build_features(
    *, exact: pd.DataFrame, history: pd.DataFrame, provider: Path, price_path: Path,
    institutional_path: Path, margin_path: Path, twii_path: Path, asof: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    price_records = load_records(price_path)
    calendar = clean_calendar(sorted(day for day in price_records.date.unique() if day <= asof), asof)
    score = score_features(history, asof)
    price, breadth, provider_inventory = price_features(provider, calendar, asof)
    orthogonal = orthogonal_features(price_records, institutional_path, margin_path, asof)
    market = twii_features(twii_path, calendar, asof)
    expected = exact[["date", "instrument"]]
    score = score.merge(expected, on=["date", "instrument"], how="inner", validate="one_to_one")
    price = price.merge(expected, on=["date", "instrument"], how="inner", validate="one_to_one")
    orthogonal = orthogonal.merge(expected[["instrument"]], on="instrument", how="inner", validate="one_to_one")
    require_keys(expected, score, ["date", "instrument"], "model_a_history")
    require_keys(expected, price, ["date", "instrument"], "price")
    require_keys(expected[["instrument"]], orthogonal, ["instrument"], "orthogonal")
    output = expected.merge(score, on=["date", "instrument"], validate="one_to_one")
    output = output.merge(price, on=["date", "instrument"], validate="one_to_one")
    output = output.merge(orthogonal, on="instrument", validate="one_to_one")
    output["market_breadth20"] = breadth
    for key, value in market.items():
        output[key] = value
    order = feature_order()
    numeric = output[order].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(numeric.to_numpy(float)).all() or not output["_rsi_ready"].fillna(False).all():
        missing = [name for name in order if not np.isfinite(numeric[name].to_numpy(float)).all()]
        raise ShadowError("B19R2R_BLOCKED_INCOMPLETE_78F", "|".join(missing))
    output[order] = numeric
    return output[["date", "instrument", *order]], provider_inventory


def load_frozen_model() -> tuple[Any, list[str]]:
    manifest = read_json(TRAINING_MANIFEST)
    if (
        sha256(MODEL_PATH) != MODEL_B_SHA256
        or manifest.get("model_id") != MODEL_B_ID
        or int(manifest.get("feature_count") or 0) != 78
        or int(manifest.get("selected_candidate_id") or -1) != 14
    ):
        raise ShadowError("B19R2R_BLOCKED_MODEL_IDENTITY")
    model = joblib.load(MODEL_PATH)
    order = list(model.booster_.feature_name())
    if order != feature_order():
        raise ShadowError("B19R2R_BLOCKED_MODEL_FEATURE_ORDER")
    return model, order


def emit_artifact(
    *, output_dir: Path, asof: str, exact: pd.DataFrame, features: pd.DataFrame,
    model_a_dir: Path, source_run_id: str, source_paths: dict[str, Path], twii_path: Path,
    history_lineage: list[dict[str, str]], decision_cutoff: str, protected_before: dict[str, str | None],
    provider_inventory: dict[str, Any], retrospective_fixture: bool = False,
) -> dict[str, Any]:
    model, order = load_frozen_model()
    scores = np.asarray(model.predict(features[order]), dtype=float)
    if len(scores) != len(exact) or not np.isfinite(scores).all():
        raise ShadowError("B19R2R_BLOCKED_SCORE_OUTPUT")
    available_at = iso(utc_now())
    signals = exact[["date", "instrument", "candidate_rank", "full_qlib_rank"]].copy()
    signals["model_name"] = MODEL_B_ID
    signals["model_family"] = "ltr"
    signals["buy_score"] = scores
    signals["raw_score"] = scores
    rank_order = signals.sort_values(["buy_score", "instrument"], ascending=[False, True], kind="mergesort").index
    signals["score_rank"] = pd.Series(np.arange(1, len(signals) + 1), index=rank_order).reindex(signals.index).astype(int)
    signals["signal_asof"] = asof
    signals["available_at"] = available_at
    signals["source_artifact"] = rel(model_a_dir)
    signals["source_model_artifact"] = rel(MODEL_PATH)
    signals["source_feature_artifact"] = rel(output_dir / "features_78.csv")
    columns = ["date", "instrument", "model_name", "model_family", "candidate_rank", "buy_score", "raw_score", "score_rank", "full_qlib_rank", "signal_asof", "available_at", "source_artifact", "source_model_artifact", "source_feature_artifact"]
    signals = signals[columns].sort_values(["score_rank", "instrument"], kind="mergesort")
    features.to_csv(output_dir / "features_78.csv", index=False)
    signals.to_csv(output_dir / "signals.csv", index=False)
    pd.DataFrame([{"asof": asof, "model_a_exact50_rows": 50, "excluded_tw7769_rows": 50 - len(exact), "signal_rows": len(signals), "finite_78_rows": len(features)}]).to_csv(output_dir / "coverage_audit.csv", index=False)
    pd.DataFrame([{"forbidden_field": value, "present": False} for value in FORBIDDEN_TOKENS]).to_csv(output_dir / "forbidden_field_audit.csv", index=False)
    pd.DataFrame([
        {"target_field": "candidate_rank", "source": "same_day_model_a.candidate_rank", "parity": True},
        {"target_field": "full_qlib_rank", "source": "same_day_model_a.full_qlib_rank", "parity": True},
        {"target_field": "buy_score", "source": "b19r2r_frozen_model.predict", "parity": True},
    ]).to_csv(output_dir / "legacy_mapping_audit.csv", index=False)
    schema = {"artifact_type": "model_signal", "schema_version": "model_signal_contract_v1.b19r2r_shadow", "required_fields": columns, "primary_key": ["date", "instrument"], "feature_count": 78, "feature_order_sha256": FEATURE_ORDER_SHA256, "extensions": {"schema_version": "model_signal_extension_v1", "fields": {}}}
    write_json(output_dir / "schema.json", schema)
    write_json(output_dir / "provider_input_inventory.json", provider_inventory)
    protected_after = pointer_fingerprints()
    if protected_after != protected_before:
        raise ShadowError("B19R2R_BLOCKED_PROTECTED_POINTER_DRIFT")
    files = {name: {"path": name, "sha256": sha256(output_dir / name)} for name in ("signals.csv", "features_78.csv", "schema.json", "coverage_audit.csv", "forbidden_field_audit.csv", "legacy_mapping_audit.csv", "provider_input_inventory.json")}
    output_files = {
        "signals": rel(output_dir / "signals.csv"),
        "schema": rel(output_dir / "schema.json"),
        "coverage_audit": rel(output_dir / "coverage_audit.csv"),
        "forbidden_field_audit": rel(output_dir / "forbidden_field_audit.csv"),
        "legacy_mapping_audit": rel(output_dir / "legacy_mapping_audit.csv"),
        "provider_input_inventory": rel(output_dir / "provider_input_inventory.json"),
        "features_78": rel(output_dir / "features_78.csv"),
    }
    manifest = {
        "artifact_type": "model_signal",
        "artifact_contract": "ModelSignalArtifact",
        "artifact_name": MODEL_B_ID,
        "schema_version": "model_signal_contract_v1.b19r2r_shadow",
        "contract_version": "MODEL_SIGNAL_CONTRACT_CN.md@2026-06-16",
        "status": "READY_RETROSPECTIVE_FIXTURE" if retrospective_fixture else "READY_RESEARCH_SHADOW",
        "model_id": MODEL_B_ID,
        "model_name": MODEL_B_ID,
        "model_family": "ltr",
        "asof": asof,
        "signal_asof": asof,
        "created_at": available_at,
        "decision_cutoff": decision_cutoff,
        "row_count": len(signals),
        "duplicate_key_count": 0,
        "quality_status": "pass",
        "window": {"start": asof, "end": asof},
        "model_a_exact50_rows": 50,
        "tw7769_excluded": True,
        "tw7769_substitution_performed": False,
        "source_acquisition_run_id": source_run_id,
        "source_model_a_artifact": rel(model_a_dir),
        "source_model_artifact": rel(MODEL_PATH),
        "model_sha256": MODEL_B_SHA256,
        "feature_count": 78,
        "feature_order_sha256": FEATURE_ORDER_SHA256,
        "source_artifacts": {key: {"path": rel(path), "sha256": sha256(path)} for key, path in source_paths.items()} | {"twii_yahoo": {"path": rel(twii_path), "sha256": sha256(twii_path)}},
        "model_a_history_lineage": history_lineage,
        "files": files,
        "output_files": output_files,
        "extensions": {"schema_version": "model_signal_extension_v1", "fields": {}},
        "capabilities": {"candidate_universe": "model_a_exact50_minus_explicit_exclusions", "buy_ordering": "b19r2r_lambdarank", "full_rank_source": "model_a"},
        "asof_policy": {"signal_asof": "same_day_model_a", "available_at": "post_close_before_next_session_open", "retrospective_fixture": retrospective_fixture},
        "retrospective_fixture": retrospective_fixture,
        "research_only": True,
        "production_allowed": False,
        "no_apply": True,
        "allowed_consumers": ["research", "readonly_comparison", "prospective_shadow"],
        "forbidden_consumers": ["production_default", "provider_latest", "readonly_default", "agent_default", "paper_portfolio", "broker", "order"],
        "no_latest_write": True,
        "no_provider_write": True,
        "no_baseline_switch": True,
        "no_strategy_or_replay_triggered": True,
        "protected_before": protected_before,
        "protected_after": protected_after,
        "protected_unchanged": True,
    }
    write_json(output_dir / "manifest.json", manifest)
    return manifest


def validate_artifact(output_dir: Path, exact: pd.DataFrame) -> dict[str, Any]:
    manifest = read_json(output_dir / "manifest.json")
    signals = pd.read_csv(output_dir / "signals.csv")
    errors: list[str] = []
    required = set(read_json(output_dir / "schema.json").get("required_fields") or [])
    if not required.issubset(signals):
        errors.append("required_fields_missing")
    if signals[["date", "instrument"]].duplicated().any():
        errors.append("duplicate_key")
    if set(signals.instrument) != set(exact.instrument):
        errors.append("model_a_exact50_minus_exclusion_mismatch")
    parity = signals.set_index("instrument")[["candidate_rank", "full_qlib_rank"]].sort_index()
    expected = exact.set_index("instrument")[["candidate_rank", "full_qlib_rank"]].sort_index()
    if not parity.equals(expected.astype(parity.dtypes.to_dict())):
        errors.append("model_a_rank_parity_failed")
    if "TW7769" in set(signals.instrument):
        errors.append("tw7769_present")
    if forbidden_columns(signals.columns.astype(str).tolist()):
        errors.append("forbidden_fields_present")
    if manifest.get("production_allowed") is not False or manifest.get("no_apply") is not True:
        errors.append("research_boundary_failed")
    if manifest.get("protected_unchanged") is not True or pointer_fingerprints() != manifest.get("protected_after"):
        errors.append("protected_pointer_drift")
    for value in manifest.get("files", {}).values():
        path = output_dir / str(value.get("path") or "")
        if not path.is_file() or sha256(path) != value.get("sha256"):
            errors.append(f"file_hash_failed:{path.name}")
    report = {"schema_version": "modelb_b19r2r.daily_shadow.validator.v1", "status": "PASS" if not errors else "FAIL", "ok": not errors, "asof": manifest.get("asof"), "row_count": len(signals), "errors": errors, "production_allowed": False, "no_apply": True}
    write_json(output_dir / "validator_report.json", report)
    return report


def write_blocker(output_dir: Path, asof: str, error: ShadowError, protected_before: dict[str, str | None]) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    protected_after = pointer_fingerprints()
    payload = {
        "schema_version": "modelb_b19r2r.daily_shadow.blocker.v1",
        "status": error.code,
        "ok": False,
        "asof": asof,
        "error_code": error.code,
        "detail": error.detail,
        "research_only": True,
        "production_allowed": False,
        "no_apply": True,
        "mainline_blocking": False,
        "no_latest_write": True,
        "no_provider_write": True,
        "protected_before": protected_before,
        "protected_after": protected_after,
        "protected_unchanged": protected_before == protected_after,
    }
    write_json(output_dir / "blocker.json", payload)
    write_json(output_dir / "manifest.json", {**payload, "artifact_type": "ModelSignalArtifact", "row_count": 0})
    write_json(output_dir / "validator_report.json", {"schema_version": "modelb_b19r2r.daily_shadow.validator.v1", "status": "BLOCKED", "ok": False, "asof": asof, "errors": [error.code], "production_allowed": False, "no_apply": True})
    return payload


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = resolve_path(args.output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ShadowError("B19R2R_BLOCKED_NO_OVERWRITE", str(output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)
    protected_before = pointer_fingerprints()
    cutoff, next_open = validate_capture_window(
        args.asof,
        args.decision_cutoff,
        args.next_session_open,
        retrospective_fixture=bool(args.retrospective_fixture),
    )
    source_paths = validate_hsa_children(resolve_path(args.handoff_validation), args.asof, args.source_acquisition_run_id, cutoff)
    model_a_dir = resolve_path(args.model_a_signal_dir)
    exact, model_a_manifest = validate_model_a(model_a_dir, args.asof, args.source_acquisition_run_id, cutoff)
    twii_path = select_or_capture_yahoo_twii(
        output_dir=output_dir,
        handoff_path=resolve_path(args.handoff_validation),
        asof=args.asof,
        source_run_id=args.source_acquisition_run_id,
        cutoff=cutoff,
        next_open=next_open,
        explicit_csv=resolve_path(args.twii_csv) if args.twii_csv else None,
        explicit_manifest=resolve_path(args.twii_manifest) if args.twii_manifest else None,
    )
    history, lineage = model_a_history(model_a_dir, args.asof, cutoff)
    provider = resolve_path(args.provider_snapshot)
    provider_text = str(provider.resolve())
    if (
        not (provider / "calendars/day.txt").is_file()
        or "option_c_yahoo_scrapling_publish_" not in provider_text
        or not provider_text.endswith("/tmp/formal_provider_rebuild")
    ):
        raise ShadowError("B19R2R_BLOCKED_IMMUTABLE_PROVIDER_SNAPSHOT", str(provider))
    features, provider_inventory = build_features(
        exact=exact,
        history=history,
        provider=provider,
        price_path=source_paths["adjusted_price"],
        institutional_path=source_paths["institutional_flow"],
        margin_path=source_paths["margin_short"],
        twii_path=twii_path,
        asof=args.asof,
    )
    manifest = emit_artifact(
        output_dir=output_dir,
        asof=args.asof,
        exact=exact,
        features=features,
        model_a_dir=model_a_dir,
        source_run_id=args.source_acquisition_run_id,
        source_paths=source_paths,
        twii_path=twii_path,
        history_lineage=lineage,
        decision_cutoff=args.decision_cutoff,
        protected_before=protected_before,
        provider_inventory=provider_inventory,
        retrospective_fixture=bool(args.retrospective_fixture),
    )
    validation = validate_artifact(output_dir, exact)
    if not validation["ok"]:
        raise ShadowError("B19R2R_BLOCKED_VALIDATOR", "|".join(validation["errors"]))
    prospective_event = append_prospective_event(output_dir, manifest)
    return {"ok": True, "status": manifest["status"], "asof": args.asof, "artifact_dir": rel(output_dir), "manifest_path": rel(output_dir / "manifest.json"), "validator_path": rel(output_dir / "validator_report.json"), "signal_path": rel(output_dir / "signals.csv"), "row_count": manifest["row_count"], "production_allowed": False, "no_apply": True, "prospective_event": prospective_event}


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--asof", required=True)
    value.add_argument("--output-dir", required=True)
    value.add_argument("--model-a-signal-dir", required=True)
    value.add_argument("--handoff-validation", required=True)
    value.add_argument("--source-acquisition-run-id", required=True)
    value.add_argument("--provider-snapshot", required=True)
    value.add_argument("--decision-cutoff", required=True)
    value.add_argument("--next-session-open", default="")
    value.add_argument("--twii-csv", default="")
    value.add_argument("--twii-manifest", default="")
    value.add_argument("--retrospective-fixture", action="store_true")
    value.add_argument("--json", action="store_true")
    return value


def main() -> int:
    args = parser().parse_args()
    if not args.next_session_open:
        args.next_session_open = iso(next_weekday_open(args.asof))
    output_dir = resolve_path(args.output_dir)
    before = pointer_fingerprints()
    try:
        result = run(args)
    except ShadowError as exc:
        result = write_blocker(output_dir, args.asof, exc, before)
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
        return 2
    except Exception as exc:
        result = write_blocker(output_dir, args.asof, ShadowError("B19R2R_BLOCKED_UNEXPECTED", f"{type(exc).__name__}:{exc}"), before)
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
