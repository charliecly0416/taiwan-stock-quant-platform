#!/usr/bin/env python3
"""Build an explicit, isolated same-run acquisition handoff.

This is an adapter contract for a future acquisition caller.  It does not
discover files, run the daily job, contact providers, or write production.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import stat
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
ISOLATED_ROOT = ROOT / "data_tw/experiments/model_b_path2_sealed_archive_retrain"
SCHEMA = "hsa5.same_run_acquisition_handoff.v1"
REQUIRED = {"adjusted_price", "twii", "institutional_flow", "margin_short"}
# Keep the historical isolated fixture form, and explicitly admit the real
# daily runner identity without allowing uppercase/free-form production IDs.
ID_RE = re.compile(
    r"^(?:[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*|"
    r"daily_tw_stock_auto_update_\d{8}_\d{8}T\d{6}Z)$"
)
MAX_RUN_ID_LENGTH = 128
REAL_DAILY_RUN_ID_RE = re.compile(
    r"^daily_tw_stock_auto_update_(\d{8})_(\d{8}T\d{6}Z)$"
)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
SCOPE_FIELDS = ("expected_scope", "returned_scope", "absent_scope", "unknown_scope")


class HSA8Error(ValueError):
    pass


def _validate_acquisition_run_id(run_id: Any) -> None:
    if not isinstance(run_id, str) or not run_id or len(run_id) > MAX_RUN_ID_LENGTH or not ID_RE.fullmatch(run_id):
        raise HSA8Error("acquisition_run_id:invalid")
    match = REAL_DAILY_RUN_ID_RE.fullmatch(run_id)
    if match is None:
        return
    try:
        date.fromisoformat(match.group(1)[:4] + "-" + match.group(1)[4:6] + "-" + match.group(1)[6:8])
        datetime.strptime(match.group(2), "%Y%m%dT%H%M%SZ")
    except ValueError as exc:
        raise HSA8Error("acquisition_run_id:invalid_real_daily_timestamp") from exc


def _abs(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _open_output_root(path: Path, *, allowed_root: Path | None = None) -> tuple[int, Path, tuple[int, int]]:
    """Create/open an output directory beneath the isolated root, component-wise."""
    root = _abs(allowed_root or ISOLATED_ROOT)
    output = _abs(path)
    try:
        relative = output.relative_to(root)
    except ValueError as exc:
        raise HSA8Error(f"output:outside_isolated_root:{output}") from exc
    if not relative.parts:
        raise HSA8Error("output:isolated_root_itself")
    try:
        root_info = os.lstat(root)
    except OSError as exc:
        raise HSA8Error(f"output:root_unavailable:{root}:{exc.errno}") from exc
    if stat.S_ISLNK(root_info.st_mode) or not stat.S_ISDIR(root_info.st_mode):
        raise HSA8Error("output:isolated_root_not_directory")
    current_path = root
    current_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in relative.parts:
            current_path = current_path / component
            try:
                before = os.lstat(current_path)
            except FileNotFoundError:
                before = None
            except OSError as exc:
                raise HSA8Error(f"output:lstat_failed:{current_path}:{exc.errno}") from exc
            if before is not None and stat.S_ISLNK(before.st_mode):
                raise HSA8Error(f"output:symlink_component:{current_path}")
            try:
                os.mkdir(component, 0o750, dir_fd=current_fd)
            except FileExistsError:
                pass
            next_fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current_fd)
            after = os.lstat(current_path)
            next_info = os.fstat(next_fd)
            if stat.S_ISLNK(after.st_mode) or (next_info.st_dev, next_info.st_ino) != (after.st_dev, after.st_ino):
                os.close(next_fd)
                raise HSA8Error(f"output:component_locator_replaced:{current_path}")
            if before is not None and (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
                os.close(next_fd)
                raise HSA8Error(f"output:component_locator_changed:{current_path}")
            os.close(current_fd)
            current_fd = next_fd
        return current_fd, output, (next_info.st_dev, next_info.st_ino)
    except Exception:
        os.close(current_fd)
        raise


def _validate_output_root(path: Path, *, allowed_root: Path | None = None) -> Path:
    """Validate and securely create/open the dedicated output directory."""
    fd, output, _ = _open_output_root(path, allowed_root=allowed_root)
    os.close(fd)
    return output


def _time(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise HSA8Error(f"{field}:missing")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HSA8Error(f"{field}:invalid") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise HSA8Error(f"{field}:timezone_required")
    return result


def _beneath(root: Path, path: Path) -> tuple[int, Path]:
    root = _abs(root)
    path = _abs(path)
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise HSA8Error(f"path:outside_job_root:{path}") from exc
    if not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
        raise HSA8Error(f"path:invalid:{path}")
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    current = root_fd
    try:
        for component in relative.parts[:-1]:
            nxt = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            if current != root_fd:
                os.close(current)
            current = nxt
        fd = os.open(relative.parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=current)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            os.close(fd)
            raise HSA8Error(f"path:not_regular:{path}")
        return fd, path
    except OSError as exc:
        raise HSA8Error(f"path:secure_open_failed:{path}:{exc.errno}") from exc
    finally:
        if current != root_fd:
            os.close(current)
        os.close(root_fd)


def _digest(root: Path, path: Path) -> str:
    try:
        before = os.lstat(path)
    except OSError as exc:
        raise HSA8Error(f"path:lstat_failed:{path}:{exc.errno}") from exc
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise HSA8Error(f"path:not_regular_no_follow:{path}")
    fd, absolute = _beneath(root, path)
    digest = hashlib.sha256()
    try:
        identity_before = os.fstat(fd)
        while chunk := os.read(fd, 1024 * 1024):
            digest.update(chunk)
        identity_after = os.fstat(fd)
    finally:
        os.close(fd)
    after = os.lstat(absolute)
    identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns)
    if identity(identity_before) != identity(identity_after) or identity(identity_before) != identity(after):
        raise HSA8Error(f"path:locator_drift:{path}")
    return digest.hexdigest()


def _read_bound_json(root: Path, path: Path) -> Mapping[str, Any]:
    fd, absolute = _beneath(root, path)
    try:
        chunks: list[bytes] = []
        while chunk := os.read(fd, 1024 * 1024):
            chunks.append(chunk)
        identity = os.fstat(fd)
        after = os.lstat(absolute)
        if (identity.st_dev, identity.st_ino, identity.st_size, identity.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise HSA8Error(f"path:adapter_output_locator_drift:{absolute}")
    finally:
        os.close(fd)
    try:
        value = json.loads(b"".join(chunks).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HSA8Error(f"adapter_output:invalid_json:{absolute}") from exc
    if not isinstance(value, Mapping):
        raise HSA8Error(f"adapter_output:not_object:{absolute}")
    return value


def _canonical_metadata(source: Mapping[str, Any], raw: list[dict[str, str]], normalized: list[dict[str, str]]) -> dict[str, Any]:
    metadata = {field: source.get(field) for field in (
        "provider", "source_id", "trade_date", "http_status", "pit_status",
        "expected_scope", "returned_scope", "absent_scope", "unknown_scope", "endpoint",
        "request_parameters", "acquisition_run_id", "target_asof",
    )} | {"validator_status": source.get("source_validator_status"), "endpoint_version": source.get("source_endpoint_version"), "raw_files": raw, "normalized_files": normalized}
    if "availability_evidence" in source:
        metadata["availability_evidence"] = source["availability_evidence"]
    return metadata


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _scope(source: Mapping[str, Any]) -> None:
    values: dict[str, set[str]] = {}
    for field in SCOPE_FIELDS:
        raw = source.get(field)
        if not isinstance(raw, list) or any(not isinstance(x, str) or not x.strip() for x in raw):
            raise HSA8Error(f"scope:{field}:invalid")
        if len(raw) != len(set(raw)):
            raise HSA8Error(f"scope:{field}:duplicate")
        values[field] = set(raw)
    if not values["expected_scope"]:
        raise HSA8Error("scope:expected_scope:empty")
    partitions = [values[x] for x in ("returned_scope", "absent_scope", "unknown_scope")]
    if any(partitions[i] & partitions[j] for i in range(3) for j in range(i + 1, 3)):
        raise HSA8Error("scope:partition_overlap")
    if set().union(*partitions) != values["expected_scope"]:
        raise HSA8Error("scope:closure")


def _paths(source: Mapping[str, Any], field: str, role: str, job_root: Path) -> list[dict[str, str]]:
    raw = source.get(field)
    if not isinstance(raw, list) or not raw:
        raise HSA8Error(f"{source.get('source_family')}:{field}:required")
    result = []
    seen: set[str] = set()
    for value in raw:
        if not isinstance(value, str) or not value.strip():
            raise HSA8Error(f"{field}:path_invalid")
        path = Path(value)
        path = path if path.is_absolute() else job_root / path
        absolute = _abs(path)
        key = os.fspath(absolute)
        if key in seen:
            raise HSA8Error(f"{field}:duplicate")
        seen.add(key)
        result.append({"role": role, "path": key, "sha256": _digest(job_root, absolute)})
    return result


def validate_and_build(run_id: str, target_asof: str, sources: Sequence[Mapping[str, Any]], job_root: Path) -> dict[str, Any]:
    _validate_acquisition_run_id(run_id)
    try:
        datetime.fromisoformat(f"{target_asof}T00:00:00+00:00")
    except ValueError as exc:
        raise HSA8Error("target_asof:invalid") from exc
    if not isinstance(sources, Sequence) or isinstance(sources, (str, bytes)):
        raise HSA8Error("sources:not_list")
    families = [item.get("source_family") for item in sources if isinstance(item, Mapping)]
    if len(families) != len(set(families)) or not REQUIRED.issubset(set(families)):
        raise HSA8Error("source_family:required_or_duplicate")
    built = []
    for source in sources:
        if not isinstance(source, Mapping):
            raise HSA8Error("source:not_object")
        adapter_path_value = source.get("adapter_output_path")
        adapter_files_value = source.get("adapter_output_files")
        if not isinstance(adapter_path_value, str) or not adapter_path_value.strip() or not isinstance(adapter_files_value, list) or len(adapter_files_value) != 1 or _abs(Path(str(adapter_files_value[0]))) != _abs(Path(adapter_path_value)):
            raise HSA8Error("adapter_output:required_unique_source_mapping")
        adapter_locator = Path(adapter_path_value)
        adapter_output = _paths({"source_family": source.get("source_family"), "adapter_output_files": [str(adapter_locator)]}, "adapter_output_files", "adapter_output_metadata", job_root)
        adapter_metadata = _read_bound_json(job_root, adapter_locator if adapter_locator.is_absolute() else job_root / adapter_locator)
        required_adapter_fields = ("source_family", "provider", "source_id", "trade_date", "http_status", "validator_status", "pit_status", "expected_scope", "returned_scope", "absent_scope", "unknown_scope", "endpoint", "endpoint_version", "parser_version", "schema_version", "transport_identity", "request_parameters", "acquisition_run_id", "target_asof", "source_published_at", "available_at", "fetched_at", "raw_files", "normalized_files", "canonical_metadata_digest")
        if any(field not in adapter_metadata for field in required_adapter_fields):
            raise HSA8Error("adapter_output:required_field_missing")
        provided_to_adapter = {
            "source_family": "source_family", "provider": "provider", "source_id": "source_id", "trade_date": "trade_date",
            "http_status": "http_status", "source_validator_status": "validator_status", "pit_status": "pit_status",
            "expected_scope": "expected_scope", "returned_scope": "returned_scope", "absent_scope": "absent_scope", "unknown_scope": "unknown_scope",
            "endpoint": "endpoint", "source_endpoint_version": "endpoint_version", "request_parameters": "request_parameters",
            "acquisition_run_id": "acquisition_run_id", "target_asof": "target_asof", "source_published_at": "source_published_at",
            "available_at": "available_at", "fetched_at": "fetched_at",
        }
        for supplied, authoritative in provided_to_adapter.items():
            if supplied in source and source[supplied] is not None and source[supplied] != adapter_metadata[authoritative]:
                raise HSA8Error(f"adapter_output_{supplied}_override_mismatch")
        raw_metadata = adapter_metadata.get("raw_files")
        normalized_metadata = adapter_metadata.get("normalized_files")
        if not isinstance(raw_metadata, list) or not isinstance(normalized_metadata, list):
            raise HSA8Error("adapter_output:artifact_binding_missing")
        for field, metadata in (("raw_files", raw_metadata), ("normalized_files", normalized_metadata)):
            if field in source and source[field] is not None:
                supplied_paths = [str(item) for item in source[field]]
                authoritative_paths = [item.get("path") for item in metadata if isinstance(item, Mapping)]
                if supplied_paths != authoritative_paths:
                    raise HSA8Error(f"adapter_output_{field}_override_mismatch")
        source = {
            "source_family": adapter_metadata["source_family"], "provider": adapter_metadata["provider"],
            "source_id": adapter_metadata["source_id"], "trade_date": adapter_metadata["trade_date"],
            "http_status": adapter_metadata["http_status"], "source_validator_status": adapter_metadata["validator_status"],
            "pit_status": adapter_metadata["pit_status"], "expected_scope": adapter_metadata["expected_scope"],
            "returned_scope": adapter_metadata["returned_scope"], "absent_scope": adapter_metadata["absent_scope"], "unknown_scope": adapter_metadata["unknown_scope"],
            "endpoint": adapter_metadata["endpoint"], "source_endpoint_version": adapter_metadata["endpoint_version"],
            "parser_version": adapter_metadata["parser_version"], "schema_version": adapter_metadata["schema_version"],
            "transport_identity": adapter_metadata["transport_identity"],
            "request_parameters": adapter_metadata["request_parameters"], "acquisition_run_id": adapter_metadata["acquisition_run_id"],
            "target_asof": adapter_metadata["target_asof"], "source_published_at": adapter_metadata["source_published_at"],
            "available_at": adapter_metadata["available_at"], "fetched_at": adapter_metadata["fetched_at"],
            "raw_files": [item.get("path") for item in raw_metadata if isinstance(item, Mapping)],
            "normalized_files": [item.get("path") for item in normalized_metadata if isinstance(item, Mapping)],
            "adapter_output_path": adapter_path_value, "adapter_output_files": [str(adapter_locator)],
        }
        if "availability_evidence" in adapter_metadata:
            source["availability_evidence"] = adapter_metadata["availability_evidence"]
        family = source.get("source_family")
        source_id = source.get("source_id")
        if not isinstance(family, str) or not ID_RE.fullmatch(family):
            raise HSA8Error("source_family:invalid")
        if not isinstance(source_id, str) or not ID_RE.fullmatch(source_id):
            raise HSA8Error(f"{family}:source_id:invalid")
        if source.get("acquisition_run_id") != run_id or source.get("target_asof") != target_asof:
            raise HSA8Error(f"{family}:run_or_asof_mismatch")
        if source.get("source_validator_status") != "PASS":
            raise HSA8Error(f"{family}:validator_not_PASS")
        if source.get("pit_status") != "PASS":
            raise HSA8Error(f"{family}:pit_status_not_PASS")
        for field in ("provider", "source_endpoint_version", "parser_version", "schema_version", "transport_identity", "endpoint"):
            if not isinstance(source.get(field), str) or not source[field].strip():
                raise HSA8Error(f"{family}:{field}:missing")
        if not isinstance(source.get("request_parameters"), Mapping) or not isinstance(source.get("http_status"), int) or not 100 <= source["http_status"] <= 599:
            raise HSA8Error(f"{family}:transport_invalid")
        evidence = source.get("availability_evidence")
        if evidence is not None:
            if not isinstance(evidence, Mapping) or evidence.get("method") != "first_successful_capture":
                raise HSA8Error(f"{family}:availability_evidence_invalid")
            observed_at = _time(evidence.get("observed_at"), f"{family}:availability_evidence.observed_at")
            available = _time(source.get("available_at"), "available_at")
            fetched = _time(source.get("fetched_at"), "fetched_at")
            if source.get("source_published_at") is not None or available != observed_at or not available <= fetched:
                raise HSA8Error(f"{family}:first_capture_time_invalid")
            times = (None, available, fetched)
        else:
            times = [_time(source.get(field), field) for field in ("source_published_at", "available_at", "fetched_at")]
            if not times[0] <= times[1] <= times[2]:
                raise HSA8Error(f"{family}:pit_order")
        trade_date = source.get("trade_date")
        if not isinstance(trade_date, str) or not DATE_RE.fullmatch(trade_date):
            raise HSA8Error(f"{family}:trade_date:strict_yyyy_mm_dd_required")
        try:
            trade_day = date.fromisoformat(trade_date)
            target_day = date.fromisoformat(target_asof)
        except (TypeError, ValueError) as exc:
            raise HSA8Error(f"{family}:trade_date:required_iso_date") from exc
        if trade_day > target_day or trade_day > times[2].date():
            raise HSA8Error(f"{family}:trade_date:after_target_or_fetch")
        _scope(source)
        raw = _paths(source, "raw_files", "provider_raw_response", job_root)
        normalized = _paths(source, "normalized_files", "provider_normalized_payload", job_root)
        adapter_canonical = {field: adapter_metadata.get(field) for field in (
                "provider", "source_id", "trade_date", "http_status", "validator_status", "pit_status",
                "expected_scope", "returned_scope", "absent_scope", "unknown_scope", "endpoint",
                "endpoint_version", "request_parameters", "acquisition_run_id", "target_asof",
                "raw_files", "normalized_files",
            )}
        if "availability_evidence" in adapter_metadata:
            adapter_canonical["availability_evidence"] = adapter_metadata["availability_evidence"]
        expected_canonical = _canonical_metadata(source, raw, normalized)
        if adapter_canonical != expected_canonical:
            raise HSA8Error(f"{family}:adapter_output_canonical_metadata_mismatch")
        if adapter_metadata["canonical_metadata_digest"] != _canonical_digest(adapter_canonical):
            raise HSA8Error(f"{family}:adapter_output_canonical_digest_mismatch")
        built_source = {"snapshot_id": source.get("snapshot_id", f"{family}.{run_id}"), "adapter_output_path": source.get("adapter_output_path", ""), **{k: source[k] for k in ("source_family", "source_id", "target_asof", "trade_date", "provider", "source_endpoint_version", "parser_version", "schema_version", "request_parameters", "http_status", "transport_identity", "source_published_at", "available_at", "fetched_at", "pit_status", "source_validator_status", "acquisition_run_id", *SCOPE_FIELDS)}, "raw_artifact_role": "provider_raw_response", "normalized_artifact_role": "provider_normalized_payload", "raw_files": raw, "normalized_files": normalized, "adapter_output_files": adapter_output, "artifacts": raw + normalized + adapter_output}
        if "availability_evidence" in source:
            built_source["availability_evidence"] = source["availability_evidence"]
        built.append(built_source)
    return {"schema_version": SCHEMA, "acquisition_run_id": run_id, "target_asof": target_asof, "handoff_kind": "real_same_run_acquisition", "isolated": True, "production_allowed": False, "manifest_written_last": True, "sources": built}


def _rename_noreplace(directory: int, source: str, destination: str) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, "renameat2", None)
    if rename is None:
        raise HSA8Error("output:renameat2_unavailable")
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    result = rename(directory, os.fsencode(source), directory, os.fsencode(destination), 1)
    if result != 0:
        raise HSA8Error(f"output:rename_noreplace_failed:{ctypes.get_errno()}")


def _parent_locator_matches(parent_path: Path, parent_fd: int, expected: tuple[int, int]) -> bool:
    try:
        fd_info = os.fstat(parent_fd)
        path_info = os.lstat(parent_path)
    except OSError:
        return False
    return (
        not stat.S_ISLNK(path_info.st_mode)
        and stat.S_ISDIR(path_info.st_mode)
        and (fd_info.st_dev, fd_info.st_ino) == expected
        and (path_info.st_dev, path_info.st_ino) == expected
    )


def _atomic_json(path: Path, payload: Mapping[str, Any], *, allowed_root: Path | None = None) -> None:
    path = _abs(path)
    parent_fd, parent_path, parent_identity = _open_output_root(path.parent, allowed_root=allowed_root)
    if os.path.lexists(path):
        os.close(parent_fd)
        raise HSA8Error("output:final_exists")
    stage_name = f".{path.name}.staging.{os.getpid()}"
    stage = parent_path / stage_name
    try:
        fd = os.open(stage_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o640, dir_fd=parent_fd)
    except OSError as exc:
        os.close(parent_fd)
        raise HSA8Error(f"output:staging_create_failed:{exc.errno}") from exc
    stage_identity = None
    try:
        try:
            data = (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()
            view = memoryview(data)
            while view:
                written = os.write(fd, view)
                if written <= 0:
                    raise HSA8Error("output:short_write")
                view = view[written:]
            os.fsync(fd)
            info = os.fstat(fd)
            stage_identity = (info.st_dev, info.st_ino)
        finally:
            os.close(fd)
    except Exception:
        try:
            os.unlink(stage_name, dir_fd=parent_fd)
        except FileNotFoundError:
            pass
        os.close(parent_fd)
        raise
    renamed = False
    try:
        if not _parent_locator_matches(parent_path, parent_fd, parent_identity):
            raise HSA8Error("output:parent_locator_changed_before_rename")
        _rename_noreplace(parent_fd, stage_name, path.name)
        renamed = True
        final = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
        if (final.st_dev, final.st_ino) != stage_identity:
            raise HSA8Error("output:final_inode_mismatch")
        if not _parent_locator_matches(parent_path, parent_fd, parent_identity):
            raise HSA8Error("output:parent_locator_changed")
        os.fsync(parent_fd)
    except Exception:
        # Only unlink this transaction's staging name; never unlink final.
        try:
            os.unlink(stage_name, dir_fd=parent_fd)
        except FileNotFoundError:
            pass
        # Delete only a final that is still provably owned by this transaction
        # and only while both the parent FD and its path locator are unchanged.
        if renamed and _parent_locator_matches(parent_path, parent_fd, parent_identity):
            try:
                current_final = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
                if (current_final.st_dev, current_final.st_ino) == stage_identity:
                    os.unlink(path.name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
        raise
    finally:
        os.close(parent_fd)


def build_handoff(job_root: Path, run_id: str, target_asof: str, sources: Sequence[Mapping[str, Any]], output_root: Path) -> Path:
    payload = validate_and_build(run_id, target_asof, sources, _abs(job_root))
    output = _validate_output_root(output_root) / "same_run_acquisition_handoff_manifest.json"
    _atomic_json(output, payload)
    return output


def build_runtime_handoff(job_root: Path, run_id: str, target_asof: str, sources: Sequence[Mapping[str, Any]], output_root: Path) -> Path:
    """Build a job-local handoff; the caller must explicitly opt into runtime scope."""
    job_root = _abs(job_root)
    output_root = _abs(output_root)
    try:
        output_root.relative_to(job_root)
    except ValueError as exc:
        raise HSA8Error(f"output:outside_job_root:{output_root}") from exc
    output = _validate_output_root(output_root, allowed_root=job_root) / "same_run_acquisition_handoff_manifest.json"
    payload = validate_and_build(run_id, target_asof, sources, job_root)
    payload["isolated"] = False
    payload["production_allowed"] = False
    _atomic_json(output, payload, allowed_root=job_root)
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-root", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True, help="explicit caller-supplied JSON metadata")
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding="utf-8"))
    build_handoff(args.job_root, request["acquisition_run_id"], request["target_asof"], request["sources"], args.output_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
