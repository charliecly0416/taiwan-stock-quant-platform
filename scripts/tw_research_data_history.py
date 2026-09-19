#!/usr/bin/env python3
"""Materialize a small, append-only index of daily research data assets.

The module deliberately references existing Model A artifacts instead of copying
them.  A validated B19R2R shadow is copied out of the disposable daily job tree
because its feature and signal files are small and useful for later replay.
"""
from __future__ import annotations

import csv
import fcntl
import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


MODEL_A_ID = "e4_frozen_qlib_2018_2022"
MODEL_B_ID = "modelb_b19r2r_lambdarank_exact50_78f_v2"
MODEL_B_REQUIRED_FILES = (
    "manifest.json",
    "validator_report.json",
    "features_78.csv",
    "signals.csv",
    "schema.json",
    "coverage_audit.csv",
    "forbidden_field_audit.csv",
    "legacy_mapping_audit.csv",
    "provider_input_inventory.json",
)
MODEL_B_DECLARED_FILES = tuple(
    name for name in MODEL_B_REQUIRED_FILES if name not in {"manifest.json", "validator_report.json"}
)


class HistoryError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def validate_asof(value: str) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise HistoryError(f"invalid canonical asof: {value}")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise HistoryError(f"invalid canonical asof: {value}") from exc
    if parsed.isoformat() != value:
        raise HistoryError(f"invalid canonical asof: {value}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_temp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(raw_temp)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(_canonical_json(payload))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HistoryError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise HistoryError(f"JSON object required: {path}")
    return value


def resolve_repo_path(repo_root: Path, raw: str | Path) -> Path:
    path = Path(raw)
    resolved = (path if path.is_absolute() else repo_root / path).resolve()
    root = repo_root.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise HistoryError(f"artifact path is outside repository: {raw}") from exc
    return resolved


def relative_path(repo_root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path.resolve())


def file_record(repo_root: Path, path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise HistoryError(f"required file missing: {path}")
    return {
        "path": relative_path(repo_root, path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def _validate_common_artifact(
    repo_root: Path,
    artifact_dir: Path,
    *,
    asof: str,
    artifact_type: str,
    required_data_file: str,
) -> dict[str, Any]:
    manifest_path = artifact_dir / "manifest.json"
    validator_path = artifact_dir / "validator_report.json"
    manifest = read_json(manifest_path)
    validator = read_json(validator_path)
    if manifest.get("artifact_type") != artifact_type:
        raise HistoryError(f"unexpected artifact type at {artifact_dir}")
    if manifest.get("model_id") != MODEL_A_ID:
        raise HistoryError(f"unexpected Model A identity at {artifact_dir}")
    if manifest.get("asof") != asof or manifest.get("status") != "READY":
        raise HistoryError(f"Model A artifact is not READY for {asof}: {artifact_dir}")
    if validator.get("ok") is not True or validator.get("status") != "PASS":
        raise HistoryError(f"Model A validator did not pass: {artifact_dir}")
    records = {
        name: file_record(repo_root, artifact_dir / name)
        for name in ("manifest.json", "validator_report.json", required_data_file)
    }
    return {
        "artifact_type": artifact_type,
        "path": relative_path(repo_root, artifact_dir),
        "run_id": str(manifest.get("run_id") or artifact_dir.name),
        "created_at": str(manifest.get("created_at") or ""),
        "source_acquisition_run_id": str(manifest.get("source_acquisition_run_id") or ""),
        "decision_cutoff": str(manifest.get("decision_cutoff") or ""),
        "files": records,
    }


def _model_a_path_candidates(
    repo_root: Path,
    job: dict[str, Any],
    asof: str,
    model_b_dir: Path | None,
) -> list[tuple[Path, Path]]:
    gate = job.get("model_signal_gate") if isinstance(job.get("model_signal_gate"), dict) else {}
    summary = gate.get("summary") if isinstance(gate.get("summary"), dict) else {}
    signal_raw = str(summary.get("model_a_signal_path") or "").strip()
    input_raw = str(summary.get("model_a_inference_input_path") or "").strip()

    if not signal_raw and model_b_dir is not None and (model_b_dir / "manifest.json").is_file():
        b_manifest = read_json(model_b_dir / "manifest.json")
        signal_raw = str(b_manifest.get("source_model_a_artifact") or "").strip()
    if signal_raw and not input_raw:
        signal_dir = resolve_repo_path(repo_root, signal_raw)
        input_raw = str(
            repo_root
            / "data_tw/canonical/model_inference_input"
            / MODEL_A_ID
            / signal_dir.name
        )
    if signal_raw and input_raw:
        return [(resolve_repo_path(repo_root, input_raw), resolve_repo_path(repo_root, signal_raw))]

    signal_root = repo_root / "data_tw/artifacts/signals" / MODEL_A_ID
    discovered: list[tuple[str, Path]] = []
    latest_pointer = signal_root / "latest.json"
    if latest_pointer.is_file():
        latest = read_json(latest_pointer)
        if latest.get("asof") == asof and latest.get("model_id") == MODEL_A_ID:
            raw = str(latest.get("canonical_artifact_dir") or latest.get("source_artifact_dir") or "").strip()
            if raw:
                candidate = resolve_repo_path(repo_root, raw)
                discovered.append((str(latest.get("created_at") or ""), candidate))
    if signal_root.is_dir():
        for manifest_path in signal_root.glob("*/manifest.json"):
            try:
                manifest = read_json(manifest_path)
            except HistoryError:
                continue
            if (
                manifest.get("artifact_type") == "ModelSignalArtifact"
                and manifest.get("model_id") == MODEL_A_ID
                and manifest.get("asof") == asof
                and manifest.get("status") == "READY"
            ):
                discovered.append((str(manifest.get("created_at") or ""), manifest_path.parent))

    unique: dict[str, tuple[str, Path]] = {}
    for created_at, signal_dir in discovered:
        unique[str(signal_dir.resolve())] = (created_at, signal_dir)
    candidates = []
    for _, signal_dir in sorted(unique.values(), key=lambda item: (item[0], str(item[1])), reverse=True):
        input_dir = repo_root / "data_tw/canonical/model_inference_input" / MODEL_A_ID / signal_dir.name
        candidates.append((input_dir, signal_dir))
    return candidates


def validate_model_a(repo_root: Path, job: dict[str, Any], asof: str, model_b_dir: Path | None = None) -> dict[str, Any] | None:
    candidates = _model_a_path_candidates(repo_root, job, asof, model_b_dir)
    if not candidates:
        return None
    errors: list[str] = []
    for input_dir, signal_dir in candidates:
        try:
            inference = _validate_common_artifact(
                repo_root,
                input_dir,
                asof=asof,
                artifact_type="ModelInferenceInput",
                required_data_file="inference_frame.csv",
            )
            signal = _validate_common_artifact(
                repo_root,
                signal_dir,
                asof=asof,
                artifact_type="ModelSignalArtifact",
                required_data_file="signals.csv",
            )
            if inference["run_id"] != signal["run_id"]:
                raise HistoryError("Model A inference and signal run_id do not match")
            return {
                "status": "READY",
                "model_id": MODEL_A_ID,
                "asof": asof,
                "inference_input": inference,
                "signal": signal,
                "storage_policy": "REFERENCE_EXISTING_CANONICAL_ARTIFACTS",
            }
        except HistoryError as exc:
            errors.append(str(exc))
    raise HistoryError("no validated Model A artifact pair found: " + " | ".join(errors))


def _declared_hash(manifest: dict[str, Any], name: str) -> str:
    files = manifest.get("files") if isinstance(manifest.get("files"), dict) else {}
    entry = files.get(name)
    return str(entry.get("sha256") or "") if isinstance(entry, dict) else ""


def validate_model_b(repo_root: Path, artifact_dir: Path, *, asof: str, model_a_signal_path: str) -> dict[str, Any]:
    manifest = read_json(artifact_dir / "manifest.json")
    validator = read_json(artifact_dir / "validator_report.json")
    errors: list[str] = []
    if manifest.get("model_id") != MODEL_B_ID:
        errors.append("unexpected model_id")
    if manifest.get("asof") != asof or manifest.get("status") != "READY_RESEARCH_SHADOW":
        errors.append("artifact is not READY_RESEARCH_SHADOW for target asof")
    if manifest.get("feature_count") != 78:
        errors.append("feature_count must equal 78")
    if manifest.get("production_allowed") is not False or manifest.get("no_apply") is not True:
        errors.append("research-only safety flags are invalid")
    if manifest.get("no_latest_write") is not True or manifest.get("no_provider_write") is not True:
        errors.append("latest/provider write guards are invalid")
    if manifest.get("tw7769_excluded") is not True or manifest.get("tw7769_substitution_performed") is not False:
        errors.append("TW7769 exclusion policy is invalid")
    if manifest.get("protected_unchanged") is not True:
        errors.append("protected pointers were not proven unchanged")
    if validator.get("ok") is not True or validator.get("status") != "PASS":
        errors.append("validator did not pass")
    declared_model_a = str(manifest.get("source_model_a_artifact") or "")
    if declared_model_a != model_a_signal_path:
        errors.append("Model B is not bound to the indexed Model A signal")

    file_records: dict[str, Any] = {}
    for name in MODEL_B_REQUIRED_FILES:
        path = artifact_dir / name
        if not path.is_file():
            errors.append(f"missing required file: {name}")
            continue
        record = file_record(repo_root, path)
        declared = _declared_hash(manifest, name)
        if name in MODEL_B_DECLARED_FILES and not declared:
            errors.append(f"declared checksum missing: {name}")
        elif declared != record["sha256"] and declared:
            errors.append(f"declared checksum mismatch: {name}")
        file_records[name] = record

    features_path = artifact_dir / "features_78.csv"
    signals_path = artifact_dir / "signals.csv"
    if features_path.is_file():
        with features_path.open("r", encoding="utf-8", newline="") as handle:
            header = next(csv.reader(handle), [])
        if len(header) != 80 or header[:2] != ["date", "instrument"]:
            errors.append("features_78.csv must contain date, instrument, and exactly 78 features")
    if signals_path.is_file():
        with signals_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if any(str(row.get("instrument") or "").replace("TW", "") == "7769" for row in rows):
            errors.append("signals.csv contains excluded TW7769")
    if errors:
        raise HistoryError("; ".join(errors))

    identity = {
        "model_id": MODEL_B_ID,
        "asof": asof,
        "source_acquisition_run_id": str(manifest.get("source_acquisition_run_id") or ""),
        "decision_cutoff": str(manifest.get("decision_cutoff") or ""),
        "file_sha256": {name: record["sha256"] for name, record in sorted(file_records.items())},
    }
    digest = hashlib.sha256(_canonical_json(identity)).hexdigest()
    return {
        "status": "READY_RESEARCH_SHADOW",
        "model_id": MODEL_B_ID,
        "asof": asof,
        "source_path": relative_path(repo_root, artifact_dir),
        "source_acquisition_run_id": identity["source_acquisition_run_id"],
        "decision_cutoff": identity["decision_cutoff"],
        "model_a_signal_path": model_a_signal_path,
        "content_sha256": digest,
        "files": file_records,
        "production_allowed": False,
        "no_apply": True,
    }


def _discover_model_b(repo_root: Path, job: dict[str, Any]) -> Path | None:
    shadow = job.get("b19r2r_daily_shadow") if isinstance(job.get("b19r2r_daily_shadow"), dict) else {}
    if shadow.get("shadow_ok") is not True:
        return None
    raw = str(shadow.get("output_dir") or "").strip()
    return resolve_repo_path(repo_root, raw) if raw else None


def copy_model_b_history(
    repo_root: Path,
    source_dir: Path,
    validated: dict[str, Any],
    canonical_history_root: Path,
) -> dict[str, Any]:
    digest = str(validated["content_sha256"])
    target = canonical_history_root / MODEL_B_ID / str(validated["asof"]) / digest[:16]
    if target.exists():
        history_record = read_json(target / "history_record.json")
        if history_record.get("content_sha256") != digest:
            raise HistoryError(f"immutable Model B history conflict: {target}")
        for name in MODEL_B_REQUIRED_FILES:
            expected = str((history_record.get("files") or {}).get(name, {}).get("sha256") or "")
            if not expected or sha256_file(target / name) != expected:
                raise HistoryError(f"immutable Model B history checksum mismatch: {target / name}")
        return {**validated, "history_path": relative_path(repo_root, target), "materialization": "IDEMPOTENT_NOOP"}

    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{digest[:16]}.", dir=target.parent))
    try:
        for name in MODEL_B_REQUIRED_FILES:
            shutil.copy2(source_dir / name, staging / name)
            expected = str(validated["files"][name]["sha256"])
            actual = sha256_file(staging / name)
            if actual != expected:
                raise HistoryError(f"staged Model B checksum mismatch: {name}")
        history_record = {
            "schema_version": "tw.research_history.model_b.v1",
            "created_at": utc_now(),
            "content_sha256": digest,
            "source_path": validated["source_path"],
            "asof": validated["asof"],
            "model_id": MODEL_B_ID,
            "production_allowed": False,
            "no_apply": True,
            "files": {
                name: {
                    "path": relative_path(repo_root, target / name),
                    "size_bytes": (staging / name).stat().st_size,
                    "sha256": sha256_file(staging / name),
                }
                for name in MODEL_B_REQUIRED_FILES
            },
        }
        atomic_write_json(staging / "history_record.json", history_record)
        os.replace(staging, target)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return {**validated, "history_path": relative_path(repo_root, target), "materialization": "CREATED"}


def _load_index(index_path: Path) -> dict[str, Any]:
    if not index_path.exists():
        return {"schema_version": "tw.research_data_history.index.v1", "days": {}}
    value = read_json(index_path)
    if value.get("schema_version") != "tw.research_data_history.index.v1" or not isinstance(value.get("days"), dict):
        raise HistoryError(f"unsupported research history index: {index_path}")
    for asof, entry in value["days"].items():
        validate_asof(str(asof))
        if not isinstance(entry, dict) or entry.get("asof") != asof:
            raise HistoryError(f"invalid research history day entry: {asof}")
    return value


def materialize_daily_research_history(
    *,
    repo_root: Path,
    asof: str,
    job_id: str,
    job: dict[str, Any],
    job_dir: Path,
    catalog_root: Path | None = None,
    canonical_history_root: Path | None = None,
    model_b_dir: Path | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    result: dict[str, Any] = {
        "schema_version": "tw.research_data_history.materialization.v1",
        "enabled": True,
        "attempted": True,
        "asof": asof,
        "job_id": job_id,
        "mainline_blocking": False,
        "production_allowed": False,
        "no_apply": True,
        "latest_before": "",
        "latest_after": "",
        "warnings": [],
    }
    try:
        validate_asof(asof)
        if not re.fullmatch(r"[A-Za-z0-9._-]+", job_id):
            raise HistoryError(f"invalid job_id: {job_id}")
        catalog_root = (catalog_root or repo_root / "data_tw/catalog/research_data_history").resolve()
        canonical_history_root = (canonical_history_root or repo_root / "data_tw/canonical/research_history").resolve()
        model_b_dir = resolve_repo_path(repo_root, model_b_dir) if model_b_dir is not None else _discover_model_b(repo_root, job)
        model_a = validate_model_a(repo_root, job, asof, model_b_dir)
        if model_a is None:
            return {**result, "ok": True, "status": "SKIPPED_NO_ACCEPTED_ASSET"}

        model_b = None
        if model_b_dir is not None:
            try:
                validated_b = validate_model_b(
                    repo_root,
                    model_b_dir,
                    asof=asof,
                    model_a_signal_path=model_a["signal"]["path"],
                )
                canonical_history_root.mkdir(parents=True, exist_ok=True)
                with (canonical_history_root / ".materialize.lock").open("a+b") as history_lock:
                    fcntl.flock(history_lock.fileno(), fcntl.LOCK_EX)
                    model_b = copy_model_b_history(repo_root, model_b_dir, validated_b, canonical_history_root)
            except Exception as exc:
                result["warnings"].append(f"model_b_not_materialized: {type(exc).__name__}: {exc}")

        manifest = {
            "schema_version": "tw.research_data_history.day.v1",
            "created_at": utc_now(),
            "asof": asof,
            "job_id": job_id,
            "source_job_path": relative_path(repo_root, job_dir),
            "status": "READY_MODELA_MODELB" if model_b else "READY_MODELA_ONLY",
            "model_a": model_a,
            "model_b": model_b,
            "warnings": result["warnings"],
            "mainline_blocking": False,
            "production_allowed": False,
            "no_apply": True,
            "retention_class": "PIN_WHILE_REFERENCED",
        }

        catalog_root.mkdir(parents=True, exist_ok=True)
        lock_path = catalog_root / ".index.lock"
        with lock_path.open("a+b") as lock_handle:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
            index_path = catalog_root / "index.json"
            latest_path = catalog_root / "latest.json"
            index = _load_index(index_path)
            latest_before = ""
            if latest_path.exists():
                latest_before = str(read_json(latest_path).get("asof") or "")
            result["latest_before"] = latest_before

            previous_day = index["days"].get(asof)
            previous_model_b = previous_day.get("model_b") if isinstance(previous_day, dict) else None
            same_model_a_binding = bool(
                isinstance(previous_model_b, dict)
                and previous_model_b.get("model_a_signal_path") == model_a["signal"]["path"]
            )
            if model_b is None and same_model_a_binding:
                manifest["model_b"] = previous_model_b
                manifest["status"] = "READY_MODELA_MODELB"
                manifest["model_b_retained_from_previous_observation"] = True

            manifest_path = catalog_root / asof / f"{job_id}.json"
            atomic_write_json(manifest_path, manifest)
            day = {
                "asof": asof,
                "manifest_path": relative_path(repo_root, manifest_path),
                "status": manifest["status"],
                "model_a": model_a,
                "model_b": manifest["model_b"],
                "updated_at": utc_now(),
            }
            if manifest.get("model_b_retained_from_previous_observation"):
                day["model_b_retained_from_previous_observation"] = True
            index["days"][asof] = day
            index["updated_at"] = utc_now()
            index["available_from"] = min(index["days"])
            index["available_to"] = max(index["days"])
            index["day_count"] = len(index["days"])
            atomic_write_json(index_path, index)

            latest_asof = max(index["days"])
            latest = {
                "schema_version": "tw.research_data_history.latest.v1",
                "updated_at": utc_now(),
                **index["days"][latest_asof],
            }
            atomic_write_json(latest_path, latest)
            result["latest_after"] = latest_asof

        return {
            **result,
            "ok": True,
            "status": manifest["status"],
            "manifest_path": relative_path(repo_root, manifest_path),
            "index_path": relative_path(repo_root, index_path),
            "latest_path": relative_path(repo_root, latest_path),
            "model_a": model_a,
            "model_b": manifest["model_b"],
            "model_b_retained_from_previous_observation": bool(
                manifest.get("model_b_retained_from_previous_observation")
            ),
        }
    except Exception as exc:
        return {
            **result,
            "ok": False,
            "status": "ERROR_NONBLOCKING",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
