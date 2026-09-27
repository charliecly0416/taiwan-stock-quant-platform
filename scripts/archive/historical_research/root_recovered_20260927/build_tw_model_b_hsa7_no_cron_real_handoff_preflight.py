#!/usr/bin/env python3
"""Read-only inspection of real daily jobs for a same-run sealed handoff."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OPS_ROOT = ROOT / "data_tw/ops/daily_auto_update"
OUTPUT_ROOT = ROOT / "data_tw/experiments/model_b_path2_sealed_archive_retrain/hsa7o_r2_real_handoff_reobservation_20260826_rerun2"
DAILY_SCRIPT = ROOT / "scripts/run_daily_tw_stock_auto_update.py"
BACKEND_SCRIPT = ROOT / "backend/run.py"
STOP = "STOP_HSA7_REAL_HANDOFF_MISSING_OR_INVALID"
SCHEMA = "hsa7.no_cron_real_handoff_preflight.v1"
HANDOFF_SCHEMA_VERSION = "hsa5.same_run_acquisition_handoff.v1"
STABLE_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DAILY_JOB_NAME_RE = re.compile(r"^daily_tw_stock_auto_update_\d{8}_\d{8}T\d{6}Z$")
HANDOFF_NAME = "same_run_acquisition_handoff_manifest.json"
REQUIRED = ("adjusted_price", "twii", "institutional_flow", "margin_short")
PROTECTED = (
    ("daily_runner", "scripts/run_daily_tw_stock_auto_update.py"),
    ("backend_runner", "backend/run.py"),
    ("installed_cron", "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron"),
    ("formal_provider", "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin"),
    ("qlib_accepted_latest", "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json"),
    ("legacy_latest", "data_tw/experiments/option_c_daily_signal/latest_signal.json"),
    ("product_signal_latest", "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json"),
    ("readonly_snapshot_latest", "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json"),
    ("agent_prompt_latest", "data_tw/artifacts/agent_daily_prompt/latest.json"),
    ("frontend_runtime", "frontend/src"),
)


class HSA7Error(RuntimeError):
    pass


class HSA7DiscoveryError(HSA7Error):
    def __init__(self, message: str, summaries: list[dict[str, Any]]):
        super().__init__(message)
        self.summaries = summaries


def _abs(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def _secure_read(path: Path) -> tuple[bytes, dict[str, Any]]:
    p = _abs(path)
    if p.is_symlink():
        raise HSA7Error(f"symlink_input:{p}")
    parts = p.parts
    fd = os.open(p.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    chain = [(os.fstat(fd).st_dev, os.fstat(fd).st_ino)]
    try:
        for component in parts[1:-1]:
            nxt = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = nxt
            info = os.fstat(fd); chain.append((info.st_dev, info.st_ino))
        file_fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
    finally:
        os.close(fd)
    before = os.fstat(file_fd)
    if not stat.S_ISREG(before.st_mode):
        os.close(file_fd); raise HSA7Error(f"not_regular:{p}")
    chunks = []
    digest = hashlib.sha256()
    try:
        while chunk := os.read(file_fd, 1024 * 1024):
            chunks.append(chunk); digest.update(chunk)
        after = os.fstat(file_fd)
    finally:
        os.close(file_fd)
    identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    if identity != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise HSA7Error(f"changed_while_reading:{p}")
    # Re-open the locator to detect replacement after the FD read.
    verify_fd, verify_chain = _open_regular_locator(p)
    verify = os.fstat(verify_fd); os.close(verify_fd)
    if tuple(chain) != tuple(verify_chain) or identity != (verify.st_dev, verify.st_ino, verify.st_size, verify.st_mtime_ns):
        raise HSA7Error(f"locator_changed:{p}")
    return b"".join(chunks), {"path": str(p), "sha256": digest.hexdigest(), "size": before.st_size, "inode": before.st_ino, "device": before.st_dev, "mtime_ns": before.st_mtime_ns, "nofollow_openat": True, "fd_identity_stable": True, "locator_revalidated": True}


def _open_regular_locator(p: Path):
    fd = os.open(p.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW); chain = [(os.fstat(fd).st_dev, os.fstat(fd).st_ino)]
    try:
        for component in p.parts[1:-1]:
            nxt = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd); os.close(fd); fd = nxt
            info = os.fstat(fd); chain.append((info.st_dev, info.st_ino))
        return os.open(p.parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd), tuple(chain)
    finally:
        os.close(fd)


def _fingerprint(path: Path) -> dict[str, Any]:
    p = _abs(path)
    try: info = os.lstat(p)
    except FileNotFoundError: return {"path": str(p), "status": "ABSENT"}
    if stat.S_ISLNK(info.st_mode): raise HSA7Error(f"protected_symlink:{p}")
    if stat.S_ISREG(info.st_mode): return {"path": str(p), "status": "PRESENT", **_secure_read(p)[1]}
    # Reuse HSA6's hardened tree fingerprint for protected directories and crontab.
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_tw_model_b_hsa6_no_cron_implementation_preflight as hsa6
    return hsa6._fingerprint(p)


def _crontab():
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_tw_model_b_hsa6_no_cron_implementation_preflight as hsa6
    return hsa6._actual_crontab_fingerprint()


def _protected() -> dict[str, Any]:
    result = {role: _fingerprint(ROOT / rel) for role, rel in PROTECTED}
    result["actual_crontab_locator"] = _crontab()
    return result


def _directory_identity(path: Path) -> tuple[int, int]:
    """Open each directory component without following symlinks and recheck its locator."""
    p = _abs(path)
    fd = os.open(p.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in p.parts[1:]:
            nxt = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = nxt
        before = os.fstat(fd)
        if not stat.S_ISDIR(before.st_mode): raise HSA7Error(f"not_directory:{p}")
        identity = (before.st_dev, before.st_ino)
    finally:
        os.close(fd)
    after = os.lstat(p)
    if stat.S_ISLNK(after.st_mode) or (after.st_dev, after.st_ino) != identity:
        raise HSA7Error(f"directory_locator_changed:{p}")
    return identity


def _real_job_dirs() -> list[Path]:
    if OPS_ROOT.is_symlink() or not OPS_ROOT.is_dir(): raise HSA7Error("ops_root_invalid")
    _directory_identity(OPS_ROOT)
    found = []
    errors: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    with os.scandir(OPS_ROOT) as entries:
        for entry in entries:
            directory = Path(entry.path)
            name = entry.name.lower()
            if not DAILY_JOB_NAME_RE.fullmatch(entry.name): continue
            if entry.is_symlink():
                errors.append({"job_dir": str(directory), "discovery_error": "symlink_job_directory"})
                continue
            if not entry.is_dir(follow_symlinks=False): continue
            try:
                _directory_identity(directory)
                # Secure file reads below perform FD identity and locator revalidation.
                job_raw, _ = _secure_read(directory / "job.json")
                job_payload = json.loads(job_raw)
            except (OSError, HSA7Error, json.JSONDecodeError) as exc:
                summaries.append({"job_dir": str(directory), "discovery_status": "quarantined", "classification": "legacy_incomplete/quarantined", "discovery_error": f"{type(exc).__name__}:{exc}"})
                continue
            try:
                _directory_identity(directory)
                inventory_raw, _ = _secure_read(directory / "daily_source_inventory.json")
                inventory = json.loads(inventory_raw)
                found.append(directory)
                summaries.append({"job_dir": str(directory), "discovery_status": "OK", "job": {"job_id": job_payload.get("job_id"), "status": job_payload.get("status"), "asof": job_payload.get("asof"), "finished_at": job_payload.get("finished_at")}, "inventory": {"target_asof": inventory.get("target_asof"), "source_count": inventory.get("source_count")}})
            except (OSError, HSA7Error, json.JSONDecodeError) as exc:
                summaries.append({"job_dir": str(directory), "discovery_status": "legacy_incomplete", "classification": "legacy_incomplete/quarantined", "job": {"job_id": job_payload.get("job_id"), "asof": job_payload.get("asof")}, "discovery_error": f"{type(exc).__name__}:{exc}"})
    summaries.sort(key=lambda item: Path(item["job_dir"]).name, reverse=True)
    strict_names = sorted((item.name for item in os.scandir(OPS_ROOT) if not item.is_symlink() and item.is_dir(follow_symlinks=False) and DAILY_JOB_NAME_RE.fullmatch(item.name)), reverse=True)
    latest_name = str(OPS_ROOT / strict_names[0]) if strict_names else None
    latest_errors = [item for item in summaries if item.get("job_dir") == latest_name and item.get("discovery_status") != "OK"]
    if latest_errors:
        raise HSA7DiscoveryError("job_discovery_error", summaries + errors)
    return sorted(found, key=lambda p: p.name, reverse=True)


def _handoff_candidates(job: Path) -> list[Path]:
    result = []
    _directory_identity(job)
    stack = [job]
    while stack:
        root_path = stack.pop()
        _directory_identity(root_path)
        with os.scandir(root_path) as entries:
            entries = sorted(entries, key=lambda item: item.name)
            dirs, files = [], []
            for entry in entries:
                if entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False): dirs.append(entry)
                elif entry.is_file(follow_symlinks=False): files.append(entry.name)
        # A real job must never adopt an embedded fixture/evidence tree.
        for entry in reversed(dirs):
            child = Path(entry.path)
            relative = child.relative_to(job)
            if not any(part.lower() in {"hsa", "synthetic", "sealed_archive_retrain"} for part in relative.parts):
                _directory_identity(child)
                stack.append(child)
        if any(part.lower() in {"hsa", "synthetic", "sealed_archive_retrain"} for part in root_path.relative_to(job).parts):
            continue
        if HANDOFF_NAME in files:
            candidate = root_path / HANDOFF_NAME
            _secure_read(candidate)
            result.append(candidate)
    _directory_identity(job)
    return result


def _legacy_incomplete_summaries() -> list[dict[str, Any]]:
    """Return historical strict-name jobs missing inventory without making them blockers."""
    summaries = []
    with os.scandir(OPS_ROOT) as entries:
        for entry in entries:
            if entry.is_symlink() or not entry.is_dir(follow_symlinks=False) or not DAILY_JOB_NAME_RE.fullmatch(entry.name):
                continue
            directory = Path(entry.path)
            job_payload = None
            try:
                job_raw, _ = _secure_read(directory / "job.json")
                job_payload = json.loads(job_raw)
                _secure_read(directory / "daily_source_inventory.json")
            except FileNotFoundError:
                if not isinstance(job_payload, dict):
                    continue
                summaries.append({"job_dir": str(directory), "discovery_status": "legacy_incomplete", "classification": "legacy_incomplete/quarantined", "job": {"job_id": job_payload.get("job_id"), "asof": job_payload.get("asof")}, "discovery_error": "daily_source_inventory_missing"})
            except (OSError, HSA7Error, json.JSONDecodeError):
                continue
    return summaries


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value or value.endswith("Z"):
        # Z is accepted only after explicit UTC conversion below.
        if not isinstance(value, str) or not value:
            return None
        value = value[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None and parsed.utcoffset() is not None else None


def _scope_status(source: dict[str, Any], family: str) -> list[str]:
    gaps: list[str] = []
    sets: dict[str, set[str]] = {}
    for field in ("expected_scope", "returned_scope", "absent_scope", "unknown_scope"):
        value = source.get(field)
        if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
            gaps.append(f"{family}:scope_invalid:{field}")
            continue
        if len(value) != len(set(value)):
            gaps.append(f"{family}:scope_duplicate:{field}")
        sets[field] = set(value)
    if len(sets) == 4:
        partitions = [sets[field] for field in ("returned_scope", "absent_scope", "unknown_scope")]
        if any(partitions[i] & partitions[j] for i in range(3) for j in range(i + 1, 3)):
            gaps.append(f"{family}:scope_partition_overlap")
        if not sets["expected_scope"] or set().union(*partitions) != sets["expected_scope"]:
            gaps.append(f"{family}:scope_union_not_expected")
    return gaps


def _validate_artifacts(source: dict[str, Any], family: str, job: Path, run_id: str) -> list[str]:
    gaps: list[str] = []
    job_abs = _abs(job)
    records: dict[str, list[dict[str, Any]]] = {}
    for key, role in (("raw_files", "provider_raw_response"), ("normalized_files", "provider_normalized_payload")):
        values = source.get(key)
        if not isinstance(values, list) or not values:
            gaps.append(f"{family}:missing:{key}"); continue
        records[key] = []
        for item in values:
            if not isinstance(item, dict) or item.get("role") != role:
                gaps.append(f"{family}:invalid_role:{key}"); continue
            path_value, digest = item.get("path"), item.get("sha256")
            if not isinstance(path_value, str) or not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
                gaps.append(f"{family}:invalid_path_or_sha256:{key}"); continue
            exact = _abs(Path(path_value))
            try:
                rel = exact.relative_to(job_abs)
            except ValueError:
                gaps.append(f"{family}:path_outside_job:{key}"); continue
            if any(part in ("", ".", "..") for part in rel.parts):
                gaps.append(f"{family}:path_escape:{key}"); continue
            if any(part.lower() in {"hsa", "synthetic", "sealed_archive_retrain"} for part in rel.parts):
                gaps.append(f"{family}:path_in_excluded_tree:{key}"); continue
            try:
                _, actual = _secure_read(exact)
            except (OSError, HSA7Error) as exc:
                gaps.append(f"{family}:unreadable:{key}:{type(exc).__name__}"); continue
            if actual["sha256"] != digest:
                gaps.append(f"{family}:sha256_mismatch:{key}")
            records[key].append({"path": str(exact), "sha256": digest})
    if records.get("raw_files") and records.get("normalized_files"):
        for key in ("raw_files", "normalized_files"):
            for item in records[key]:
                if source.get("acquisition_run_id") != run_id:
                    gaps.append(f"{family}:artifact_run_binding_invalid:{key}")
                if source.get("source_family") != family or not STABLE_ID_RE.fullmatch(str(source.get("source_id", ""))):
                    gaps.append(f"{family}:artifact_source_binding_invalid:{key}")
    return gaps


def _validate_handoff(path: Path, job: Path, job_payload: dict[str, Any]) -> dict[str, Any]:
    raw, evidence = _secure_read(path); payload = json.loads(raw)
    gaps = []
    if not isinstance(payload, dict): gaps.append("manifest_not_object")
    if payload.get("schema_version") != HANDOFF_SCHEMA_VERSION: gaps.append("schema_version_invalid")
    run_id = payload.get("acquisition_run_id")
    if not isinstance(run_id, str) or not STABLE_ID_RE.fullmatch(run_id): gaps.append("run_id_invalid")
    if run_id != job_payload.get("job_id"): gaps.append("run_identity_mismatch")
    target_asof = payload.get("target_asof")
    if not isinstance(target_asof, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", target_asof): gaps.append("target_asof_invalid")
    if target_asof != job_payload.get("asof"): gaps.append("target_asof_mismatch")
    sources = payload.get("sources")
    if not isinstance(sources, list): sources = []; gaps.append("sources_missing")
    families = [s.get("source_family") for s in sources if isinstance(s, dict)]
    for family in REQUIRED:
        matches = [s for s in sources if isinstance(s, dict) and s.get("source_family") == family]
        if len(matches) != 1: gaps.append(f"source_family:{family}:count={len(matches)}"); continue
        s = matches[0]
        required_fields = ("source_id", "acquisition_run_id", "provider", "request_parameters", "raw_artifact_role", "normalized_artifact_role", "source_validator_status", "source_published_at", "available_at", "fetched_at", "expected_scope", "returned_scope", "absent_scope", "unknown_scope")
        for field in required_fields:
            if field not in s or s.get(field) is None or s.get(field) == "": gaps.append(f"{family}:missing:{field}")
        if s.get("acquisition_run_id") != run_id: gaps.append(f"{family}:run_identity_mismatch")
        if not isinstance(s.get("source_id"), str) or not STABLE_ID_RE.fullmatch(s.get("source_id", "")): gaps.append(f"{family}:source_id_invalid")
        if s.get("raw_artifact_role") != "provider_raw_response": gaps.append(f"{family}:raw_artifact_role_invalid")
        if s.get("normalized_artifact_role") != "provider_normalized_payload": gaps.append(f"{family}:normalized_artifact_role_invalid")
        if s.get("source_validator_status") != "PASS": gaps.append(f"{family}:validator_not_PASS")
        published, available, fetched = (_parse_timestamp(s.get(field)) for field in ("source_published_at", "available_at", "fetched_at"))
        if not (published and available and fetched and published <= available <= fetched): gaps.append(f"{family}:pit_time_order_invalid")
        gaps.extend(_scope_status(s, family))
        gaps.extend(_validate_artifacts(s, family, job, run_id if isinstance(run_id, str) else ""))
    return {"path": str(path), "evidence": evidence, "schema_version": payload.get("schema_version"), "run_id": payload.get("acquisition_run_id"), "target_asof": payload.get("target_asof"), "families": sorted(set(families)), "gaps": sorted(set(gaps)), "valid": not gaps}


def _write_new(path: Path, payload: bytes):
    if path.exists() or path.is_symlink(): raise HSA7Error(f"duplicate_output:{path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as f: f.write(payload); f.flush(); os.fsync(f.fileno())


def _write_manifest(output_root: Path, decision: str):
    root_manifest = output_root / "manifest.json"
    artifacts = [{"path": str(p.relative_to(output_root)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(output_root.rglob("*")) if p.is_file() and p != root_manifest]
    _write_new(output_root / "manifest.json", _canonical({"schema_version": SCHEMA, "decision": decision, "artifact_count": len(artifacts), "artifacts": artifacts, "manifest_written_last": True}))


def _write_discovery_stop_evidence(output_root: Path, summaries: list[dict[str, Any]], error: str, *, protected_before: dict[str, Any] | None = None, protected_after: dict[str, Any] | None = None, protected_error: str | None = None):
    gaps = ["job_discovery_error", "authoritative_same_run_handoff_not_validated"]
    if protected_error:
        gaps.extend(("protected_fingerprint_failed", "actual_crontab_read_failed"))
    asofs = [item.get("job", {}).get("asof") for item in summaries if isinstance(item.get("job"), dict) and isinstance(item.get("job", {}).get("asof"), str)]
    latest_asof = max(asofs) if asofs else None
    _write_new(output_root / "real_job_inventory.json", _canonical({"schema_version": SCHEMA, "scan_aborted": True, "stopped_before_handoff_validation": True, "reason": "job_discovery_error", "error": error, "jobs": summaries}))
    _write_new(output_root / "handoff_gap_matrix.json", _canonical({"schema_version": SCHEMA, "decision": STOP, "latest_real_asof": latest_asof, "gaps": sorted(set(gaps))}))
    _write_new(output_root / "protected_paths_fingerprint.json", _canonical({"before": protected_before if protected_before is not None else {"status": "ERROR", "error": protected_error}, "after": protected_after, "unchanged": bool(protected_before is not None and protected_after is not None and protected_before == protected_after), "fail_closed": True}))
    _write_new(output_root / "forbidden_scope_audit.json", _canonical({"schema_version": SCHEMA, "pass": False, "protected_fingerprint_complete": False if protected_error else True, "actual_crontab_source": "crontab -l", "actual_crontab_error": protected_error, "discovery_error": error, "cron_modified": False, "daily_runner_modified": False, "provider_modified": False, "latest_modified": False, "network_used": False, "database_used": False, "openai_used": False, "training_scoring_replay": False}))
    _write_new(output_root / "execution_report.md", (f"# HSA7O-R2 execution report\n\nVerdict: `{STOP}`\n\nStopped before handoff validation because job discovery failed: `{error}`. Read-only job summaries were retained; no discovery error was treated as a missing job and no handoff candidate was validated. Protected fingerprint error: `{protected_error or 'none'}`. No runtime or production operation was performed.\n").encode())
    _write_manifest(output_root, STOP)
    return {"decision": STOP, "latest_real_asof": latest_asof, "gaps": sorted(set(gaps))}


def build_preflight(output_root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    output_root = _abs(output_root)
    if output_root.exists() and any(output_root.iterdir()): raise HSA7Error("output_root_must_be_new_empty")
    output_root.mkdir(parents=True, exist_ok=True)
    try:
        before = _protected()
    except Exception as exc:
        # A protected fingerprint failure is itself evidence. Never continue by
        # treating an unreadable crontab as absent or unchanged.
        error = f"{type(exc).__name__}:{exc}"
        # Job discovery is still read-only and useful for the STOP report; it
        # does not weaken the protected-path gate or claim fingerprints passed.
        job_summaries = []
        try:
            discovered_jobs = _real_job_dirs()
        except HSA7DiscoveryError as discovery_error:
            job_summaries.extend(discovery_error.summaries)
            discovered_jobs = []
        for job in discovered_jobs:
            try:
                job_raw, job_evidence = _secure_read(job / "job.json")
                inventory_raw, inventory_evidence = _secure_read(job / "daily_source_inventory.json")
                job_payload, inventory = json.loads(job_raw), json.loads(inventory_raw)
                job_summaries.append({"job_dir": str(job), "job": {"job_id": job_payload.get("job_id"), "status": job_payload.get("status"), "asof": job_payload.get("asof"), "finished_at": job_payload.get("finished_at")}, "inventory": {"target_asof": inventory.get("target_asof"), "source_count": inventory.get("source_count"), "source_keys": sorted((inventory.get("sources") or {}).keys())}, "job_evidence": job_evidence, "inventory_evidence": inventory_evidence, "handoff_candidates": [{"path": str(p)} for p in _handoff_candidates(job)]})
            except (OSError, HSA7Error, json.JSONDecodeError) as read_error:
                job_summaries.append({"job_dir": str(job), "read_error": f"{type(read_error).__name__}:{read_error}"})
        discovered_asofs = [item.get("job", {}).get("asof") for item in job_summaries if isinstance(item.get("job"), dict) and isinstance(item.get("job", {}).get("asof"), str)]
        latest_asof = max(discovered_asofs) if discovered_asofs else None
        gaps = ["protected_fingerprint_failed", "actual_crontab_read_failed", "authoritative_same_run_handoff_not_validated"]
        if any("discovery_error" in item for item in job_summaries): gaps.append("job_discovery_error")
        _write_new(output_root / "real_job_inventory.json", _canonical({"schema_version": SCHEMA, "scan_aborted": True, "stopped_before_handoff_validation": True, "reason": "protected_fingerprint_failed", "error": error, "jobs": job_summaries}))
        _write_new(output_root / "handoff_gap_matrix.json", _canonical({"schema_version": SCHEMA, "decision": STOP, "latest_real_asof": latest_asof, "gaps": gaps}))
        _write_new(output_root / "protected_paths_fingerprint.json", _canonical({"before": {"status": "ERROR", "error": error}, "after": None, "unchanged": False, "fail_closed": True}))
        _write_new(output_root / "forbidden_scope_audit.json", _canonical({"schema_version": SCHEMA, "pass": False, "protected_fingerprint_complete": False, "actual_crontab_source": "crontab -l", "actual_crontab_error": error, "cron_modified": False, "daily_runner_modified": False, "provider_modified": False, "latest_modified": False, "network_used": False, "database_used": False, "openai_used": False, "training_scoring_replay": False}))
        _write_new(output_root / "execution_report.md", f"# HSA7O-R2 execution report\n\nVerdict: `{STOP}`\n\nStopped before handoff validation because protected fingerprint acquisition failed: `{error}`. A read-only job summary scan was allowed; discovery errors were retained and were not treated as missing jobs. No handoff candidate was validated. The actual crontab was accessed only through read-only `crontab -l`; failure was not treated as ABSENT. No runtime or production operation was performed.\n".encode())
        _write_manifest(output_root, STOP)
        return {"decision": STOP, "latest_real_asof": latest_asof, "gaps": gaps}
    try:
        jobs = _real_job_dirs()
    except HSA7DiscoveryError as discovery_error:
        try:
            after = _protected()
            protected_error = None
        except Exception as exc:
            after = None
            protected_error = f"{type(exc).__name__}:{exc}"
        return _write_discovery_stop_evidence(output_root, discovery_error.summaries, str(discovery_error), protected_before=before, protected_after=after, protected_error=protected_error)
    rows = _legacy_incomplete_summaries()
    for job in jobs:
        try:
            job_raw, job_evidence = _secure_read(job / "job.json"); inv_raw, inv_evidence = _secure_read(job / "daily_source_inventory.json")
            job_payload = json.loads(job_raw); inventory = json.loads(inv_raw)
            candidates = _handoff_candidates(job)
            handoffs = [_validate_handoff(p, job, job_payload) for p in candidates]
            rows.append({"job_dir": str(job), "discovery_status": "OK", "job": {"job_id": job_payload.get("job_id"), "status": job_payload.get("status"), "asof": job_payload.get("asof"), "finished_at": job_payload.get("finished_at")}, "inventory": {"target_asof": inventory.get("target_asof"), "schema_version": inventory.get("schema_version"), "source_count": inventory.get("source_count"), "source_keys": sorted((inventory.get("sources") or {}).keys())}, "job_evidence": job_evidence, "inventory_evidence": inv_evidence, "handoff_candidates": handoffs, "excluded_aggregate_as_raw": True})
        except (OSError, HSA7Error, json.JSONDecodeError) as exc:
            rows.append({"job_dir": str(job), "read_error": f"{type(exc).__name__}:{exc}"})
    after = _protected(); unchanged = before == after
    rows.sort(key=lambda item: Path(item["job_dir"]).name, reverse=True)
    latest = rows[0] if rows else None
    valid = bool(latest and any(h.get("valid") for h in latest.get("handoff_candidates", [])))
    gaps = [] if valid else ["authoritative_same_run_handoff_missing_or_invalid", "daily_source_inventory_is_aggregate_only", "stdout_stderr_cache_not_raw_handoff"]
    hsa5_dir = output_root / "hsa5_real_inventory_preflight"
    hsa5_result = None
    try:
        sys.path.insert(0, str(ROOT / "scripts")); import build_tw_model_b_hsa5_daily_auto_sealed_capture_wiring_preflight as hsa5
        hsa5_result = hsa5.build_preflight(daily_script=DAILY_SCRIPT, backend_script=BACKEND_SCRIPT, source_inventory=Path(latest["job_dir"]) / "daily_source_inventory.json" if latest else OPS_ROOT / "missing.json", output_dir=hsa5_dir, project_root=ROOT, allow_test_output_override=True)
    except Exception as exc: hsa5_result = {"decision": "STOP_HSA5_PREFLIGHT_ERROR", "error": f"{type(exc).__name__}:{exc}"}
    decision = "READY_FOR_HSA8_NO_CRON_REAL_HANDOFF" if valid and unchanged and hsa5_result and hsa5_result.get("decision", "").startswith("READY") else STOP
    report = {"schema_version": SCHEMA, "decision": decision, "latest_real_job": latest, "recent_real_jobs": rows, "latest_real_asof": (latest or {}).get("job", {}).get("asof"), "gaps": gaps, "hsa5_preflight": {"decision": hsa5_result.get("decision") if hsa5_result else None, "output_dir": str(hsa5_dir)}, "protected_paths_unchanged": unchanged}
    _write_new(output_root / "real_job_inventory.json", _canonical({"schema_version": SCHEMA, "jobs": rows, "scan_policy": "job.json+daily_source_inventory; synthetic excluded"}))
    _write_new(output_root / "handoff_gap_matrix.json", _canonical({"schema_version": SCHEMA, "decision": decision, "latest_real_asof": report["latest_real_asof"], "gaps": gaps, "required_families": list(REQUIRED)}))
    _write_new(output_root / "protected_paths_fingerprint.json", _canonical({"before": before, "after": after, "unchanged": unchanged}))
    _write_new(output_root / "forbidden_scope_audit.json", _canonical({"schema_version": SCHEMA, "pass": unchanged, "daily_runner_modified": False, "backend_modified": False, "cron_modified": False, "provider_modified": False, "latest_modified": False, "frontend_modified": False, "network_used": False, "database_used": False, "openai_used": False, "training_scoring_replay": False, "actual_crontab_source": "crontab -l"}))
    classifications = {status: sum(1 for item in rows if item.get("discovery_status") == status) for status in ("OK", "legacy_incomplete", "quarantined")}
    _write_new(output_root / "execution_report.md", (f"# HSA7O-R3 execution report\n\nVerdict: `{decision}`\n\nLatest real job: `{report['latest_real_asof']}`.\n\nClassifications: `{json.dumps(classifications, sort_keys=True)}`. Historical incomplete candidates are retained as `legacy_incomplete/quarantined` and do not block the latest observation.\n\nGaps: `{', '.join(gaps) or 'none'}`.\n\nThe scan was read-only. Inventory/stdout/cache were not treated as raw handoff. HSA5 preflight result: `{hsa5_result.get('decision') if hsa5_result else 'unknown'}`.\n\nNo daily/provider/cron/latest/frontend/backend/network/DB/OpenAI/training/scoring/replay operation was performed.\n").encode())
    _write_manifest(output_root, decision)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(); parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    result = build_preflight(parser.parse_args(argv).output_root); print(json.dumps({"decision": result["decision"], "latest_real_asof": result["latest_real_asof"], "gaps": result["gaps"]}, ensure_ascii=False)); return 0 if result["decision"].startswith("READY") else 2


if __name__ == "__main__": raise SystemExit(main())
