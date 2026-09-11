#!/usr/bin/env python3
"""Build an isolated, append-only HSA4 sealed source snapshot.

This utility only consumes explicitly supplied local regular files. It has no
provider, network, latest-pointer, or daily-auto integration.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import math
import os
import re
import secrets
import stat
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data_tw/experiments/model_b_path2_sealed_archive_retrain/hsa4_isolated_daily_sealed_capture"
SNAPSHOT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{7,127}$")
STABLE_SOURCE_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class CaptureError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True)
class CaptureRequest:
    snapshot_id: str
    source_family: str
    source_id: str
    provider: str
    source_endpoint_version: str
    parser_version: str
    schema_version: str
    trade_date: str
    source_published_at: str
    available_at: str
    fetched_at: str
    http_status: int
    transport_identity: str
    request_parameters: Mapping[str, Any]
    raw_files: Sequence[Path]
    normalized_files: Sequence[Path]
    expected_scope: Sequence[str]
    returned_scope: Sequence[str]
    absent_scope: Sequence[str]
    unknown_scope: Sequence[str]


def canonical_json(value: Any) -> bytes:
    _validate_json_value(value)
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _parse_timestamp(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CaptureError("HSA4_E_TIMESTAMP", f"invalid {field}: {value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CaptureError("HSA4_E_TIMESTAMP", f"timezone required for {field}")
    return parsed


def _validate_identifier(value: str, field: str) -> None:
    if not value or len(value) > 256 or any(ord(ch) < 32 for ch in value):
        raise CaptureError("HSA4_E_IDENTITY", f"invalid {field}")


def _validate_json_value(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (bool, str, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CaptureError("HSA4_E_REQUEST_PARAMETERS", f"non-finite number at {path}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise CaptureError("HSA4_E_REQUEST_PARAMETERS", f"non-string key at {path}")
            _validate_json_value(item, f"{path}.{key}")
        return
    raise CaptureError("HSA4_E_REQUEST_PARAMETERS", f"non-JSON value at {path}: {type(value).__name__}")


def validate_request(request: CaptureRequest) -> dict[str, list[str]]:
    if not SNAPSHOT_ID_RE.fullmatch(request.snapshot_id) or request.snapshot_id in {".", ".."}:
        raise CaptureError("HSA4_E_SNAPSHOT_ID", request.snapshot_id)
    for field in ("provider", "source_endpoint_version", "parser_version", "schema_version", "transport_identity"):
        _validate_identifier(getattr(request, field), field)
    for field in ("source_family", "source_id"):
        value = getattr(request, field)
        if len(value) > 128 or not STABLE_SOURCE_ID_RE.fullmatch(value):
            raise CaptureError("HSA4_E_SOURCE_IDENTITY", f"invalid stable {field}: {value}")
    try:
        trade_date = date.fromisoformat(request.trade_date)
    except ValueError as exc:
        raise CaptureError("HSA4_E_TRADE_DATE", request.trade_date) from exc
    published = _parse_timestamp(request.source_published_at, "source_published_at")
    available = _parse_timestamp(request.available_at, "available_at")
    fetched = _parse_timestamp(request.fetched_at, "fetched_at")
    if published > available or available > fetched:
        raise CaptureError("HSA4_E_TIME_ORDER", "source_published_at <= available_at <= fetched_at required")
    if trade_date > fetched.date():
        raise CaptureError("HSA4_E_TIME_ORDER", "trade_date cannot be after fetched_at")
    if not 100 <= request.http_status <= 599:
        raise CaptureError("HSA4_E_HTTP_STATUS", str(request.http_status))
    if not isinstance(request.request_parameters, Mapping):
        raise CaptureError("HSA4_E_REQUEST_PARAMETERS", "JSON object required")
    _validate_json_value(dict(request.request_parameters))
    if not request.raw_files or not request.normalized_files:
        raise CaptureError("HSA4_E_SOURCE_FILES", "at least one raw and normalized file required")

    scopes: dict[str, list[str]] = {}
    for name in ("expected_scope", "returned_scope", "absent_scope", "unknown_scope"):
        values = list(getattr(request, name))
        if any(not value or value.strip() != value or len(value) > 128 for value in values):
            raise CaptureError("HSA4_E_SCOPE_VALUE", name)
        if len(values) != len(set(values)):
            raise CaptureError("HSA4_E_SCOPE_DUPLICATE", name)
        scopes[name] = sorted(values)
    expected = set(scopes["expected_scope"])
    partitions = [set(scopes[name]) for name in ("returned_scope", "absent_scope", "unknown_scope")]
    if not expected:
        raise CaptureError("HSA4_E_SCOPE_EMPTY", "expected_scope")
    if any(partitions[i] & partitions[j] for i in range(3) for j in range(i + 1, 3)):
        raise CaptureError("HSA4_E_SCOPE_OVERLAP", "returned/absent/unknown must be disjoint")
    if set().union(*partitions) != expected:
        raise CaptureError("HSA4_E_SCOPE_CLOSURE", "partitions must exactly equal expected_scope")
    return scopes


def _open_regular_no_follow(path: Path) -> tuple[int, dict[str, Any]]:
    absolute = _absolute(path)
    flags_dir = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    flags_file = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    directory_fd = os.open(absolute.anchor, flags_dir)
    try:
        for component in absolute.parts[1:-1]:
            if component in {"", ".", ".."}:
                raise CaptureError("HSA4_E_SOURCE_PATH", str(path))
            next_fd = os.open(component, flags_dir, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
        file_fd = os.open(absolute.name, flags_file, dir_fd=directory_fd)
    except OSError as exc:
        raise CaptureError("HSA4_E_SOURCE_NOFOLLOW", str(path)) from exc
    finally:
        os.close(directory_fd)
    info = os.fstat(file_fd)
    if not stat.S_ISREG(info.st_mode):
        os.close(file_fd)
        raise CaptureError("HSA4_E_SOURCE_TYPE", str(path))
    return file_fd, {
        "input_path": os.fspath(absolute),
        "source_device": info.st_dev,
        "source_inode": info.st_ino,
        "source_size_bytes": info.st_size,
        "source_mtime_ns": info.st_mtime_ns,
    }


def _open_output_root_no_follow(path: Path) -> tuple[int, tuple[tuple[int, int], ...]]:
    absolute = _absolute(path)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    current_fd = os.open(absolute.anchor, flags)
    identities: list[tuple[int, int]] = []
    for component in absolute.parts[1:]:
        try:
            try:
                next_fd = os.open(component, flags, dir_fd=current_fd)
            except FileNotFoundError:
                os.mkdir(component, 0o750, dir_fd=current_fd)
                os.fsync(current_fd)
                next_fd = os.open(component, flags, dir_fd=current_fd)
        except OSError as exc:
            os.close(current_fd)
            raise CaptureError("HSA4_E_OUTPUT_NOFOLLOW", os.fspath(absolute)) from exc
        os.close(current_fd)
        current_fd = next_fd
        info = os.fstat(current_fd)
        identities.append((info.st_dev, info.st_ino))
    return current_fd, tuple(identities)


def _assert_root_chain(path: Path, expected: tuple[tuple[int, int], ...]) -> None:
    absolute = _absolute(path)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    current_fd = os.open(absolute.anchor, flags)
    try:
        observed: list[tuple[int, int]] = []
        for component in absolute.parts[1:]:
            try:
                next_fd = os.open(component, flags, dir_fd=current_fd)
            except OSError as exc:
                raise CaptureError("HSA4_E_OUTPUT_ROOT_REPLACED", os.fspath(absolute)) from exc
            os.close(current_fd)
            current_fd = next_fd
            info = os.fstat(current_fd)
            observed.append((info.st_dev, info.st_ino))
        if tuple(observed) != expected:
            raise CaptureError("HSA4_E_OUTPUT_ROOT_REPLACED", os.fspath(absolute))
    finally:
        os.close(current_fd)


def _mkdir_at(parent_fd: int, name: str) -> int:
    os.mkdir(name, 0o750, dir_fd=parent_fd)
    return os.open(name, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0), dir_fd=parent_fd)


def _write_file(parent_fd: int, name: str, chunks: Iterable[bytes]) -> tuple[int, str]:
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o640, dir_fd=parent_fd)
    digest = hashlib.sha256()
    size = 0
    try:
        for chunk in chunks:
            if not isinstance(chunk, bytes):
                raise CaptureError("HSA4_E_INTERNAL", "bytes required")
            view = memoryview(chunk)
            while view:
                written = os.write(fd, view)
                view = view[written:]
            digest.update(chunk)
            size += len(chunk)
        os.fsync(fd)
    finally:
        os.close(fd)
    return size, digest.hexdigest()


def _copy_source(source: Path, destination_fd: int, destination_name: str) -> dict[str, Any]:
    source_fd, identity = _open_regular_no_follow(source)
    before = os.fstat(source_fd)
    try:
        def chunks() -> Iterable[bytes]:
            while True:
                chunk = os.read(source_fd, 1024 * 1024)
                if not chunk:
                    return
                yield chunk

        size, digest = _write_file(destination_fd, destination_name, chunks())
        after = os.fstat(source_fd)
    finally:
        os.close(source_fd)
    before_id = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_id = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if before_id != after_id or size != before.st_size:
        raise CaptureError("HSA4_E_SOURCE_CHANGED", str(source))
    return {**identity, "sealed_name": destination_name, "size_bytes": size, "sha256": digest}


def _entry_identity(parent_fd: int, name: str) -> tuple[int, int]:
    info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    return info.st_dev, info.st_ino


def _before_failure_isolation(
    parent_fd: int,
    source_name: str,
    failed_name: str,
    expected_identity: tuple[int, int],
) -> None:
    """Test hook immediately before no-replace failure isolation."""


def _after_failure_isolation_rename(
    parent_fd: int,
    source_name: str,
    failed_name: str,
    expected_identity: tuple[int, int],
) -> None:
    """Test hook after isolation rename and before moved identity validation."""


def _write_failure_marker(
    directory_fd: int,
    *,
    transaction_id: str,
    source_name: str,
    failed_name: str,
    expected_identity: tuple[int, int],
    error: BaseException,
) -> None:
    marker = {
        "schema_version": "hsa4.failed_capture.v1",
        "status": "HSA4_FAILED_CANDIDATE_PRESERVED",
        "transaction_id": transaction_id,
        "source_name": source_name,
        "failed_name": failed_name,
        "expected_device": expected_identity[0],
        "expected_inode": expected_identity[1],
        "error_type": type(error).__name__,
        "error_code": getattr(error, "code", "UNCLASSIFIED"),
        "error": str(error),
        "destructive_cleanup_performed": False,
    }
    _write_file(directory_fd, "failure_marker.json", (canonical_json(marker),))
    os.fsync(directory_fd)


def _isolate_failed_entry(
    parent_fd: int,
    source_name: str,
    expected_identity: tuple[int, int],
    transaction_id: str,
    error: BaseException,
) -> str:
    failed_name = f".hsa4-failed-{transaction_id}"
    _before_failure_isolation(parent_fd, source_name, failed_name, expected_identity)
    try:
        current_identity = _entry_identity(parent_fd, source_name)
    except BaseException as exc:
        raise CaptureError(
            "HSA4_E_FAILURE_ISOLATION_TAINT",
            f"candidate missing before isolation: {source_name}",
        ) from exc
    if current_identity != expected_identity:
        raise CaptureError(
            "HSA4_E_FAILURE_ISOLATION_TAINT",
            f"candidate identity drift before isolation: {source_name}",
        )
    try:
        _rename_noreplace(parent_fd, source_name, failed_name)
    except BaseException as exc:
        raise CaptureError("HSA4_E_FAILURE_ISOLATION_TAINT", f"cannot isolate {source_name}: {exc}") from exc
    _after_failure_isolation_rename(parent_fd, source_name, failed_name, expected_identity)
    try:
        moved_identity = _entry_identity(parent_fd, failed_name)
    except BaseException as exc:
        raise CaptureError("HSA4_E_FAILURE_ISOLATION_TAINT", f"isolated entry vanished: {failed_name}") from exc
    if moved_identity != expected_identity:
        raise CaptureError("HSA4_E_FAILURE_ISOLATION_TAINT", f"isolated identity drift: {failed_name}")
    directory_fd = os.open(
        failed_name,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
        dir_fd=parent_fd,
    )
    try:
        opened = os.fstat(directory_fd)
        if (opened.st_dev, opened.st_ino) != expected_identity:
            raise CaptureError("HSA4_E_FAILURE_ISOLATION_TAINT", f"isolated fd identity drift: {failed_name}")
        try:
            _write_failure_marker(
                directory_fd,
                transaction_id=transaction_id,
                source_name=source_name,
                failed_name=failed_name,
                expected_identity=expected_identity,
                error=error,
            )
        except BaseException:
            # The failed candidate itself is the primary audit evidence. A
            # marker failure must never trigger deletion or restoration.
            pass
    finally:
        os.close(directory_fd)
    os.fsync(parent_fd)
    return failed_name


def _rename_noreplace(parent_fd: int, source: str, destination: str) -> None:
    """Atomically install source without replacing any destination entry."""
    try:
        function = ctypes.CDLL(None, use_errno=True).renameat2
    except AttributeError as exc:
        raise CaptureError("HSA4_E_NOREPLACE_UNAVAILABLE", "libc renameat2 unavailable") from exc
    function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    result = function(parent_fd, os.fsencode(source), parent_fd, os.fsencode(destination), 1)  # RENAME_NOREPLACE
    if result == 0:
        return
    error = ctypes.get_errno()
    if error in {errno.EEXIST, errno.ENOTEMPTY}:
        raise CaptureError("HSA4_E_APPEND_ONLY", destination)
    if error in {errno.ENOSYS, errno.EINVAL, errno.EOPNOTSUPP}:
        raise CaptureError("HSA4_E_NOREPLACE_UNAVAILABLE", os.strerror(error))
    raise CaptureError("HSA4_E_FINAL_INSTALL", os.strerror(error))


def build_capture(request: CaptureRequest, *, output_root: Path = DEFAULT_OUTPUT_ROOT) -> Path:
    scopes = validate_request(request)
    canonical_parameters = json.loads(canonical_json(dict(request.request_parameters)))
    output_root = _absolute(output_root)
    root_fd, root_chain = _open_output_root_no_follow(output_root)
    transaction_id = secrets.token_hex(16)
    stage_name = f".{request.snapshot_id}.stage.{transaction_id}"
    installed = False
    stage_created = False
    stage_identity: tuple[int, int] | None = None
    stage_fd: int | None = None
    try:
        try:
            os.stat(request.snapshot_id, dir_fd=root_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise CaptureError("HSA4_E_APPEND_ONLY", request.snapshot_id)
        try:
            stage_fd = _mkdir_at(root_fd, stage_name)
        except FileExistsError as exc:
            raise CaptureError("HSA4_E_STAGE_EXISTS", stage_name) from exc
        stage_created = True
        stage_info = os.fstat(stage_fd)
        stage_identity = (stage_info.st_dev, stage_info.st_ino)
        raw_fd = _mkdir_at(stage_fd, "raw")
        normalized_fd = _mkdir_at(stage_fd, "normalized")
        try:
            entries: list[dict[str, Any]] = []
            identities: set[tuple[int, int]] = set()
            for family, paths, directory_fd in (
                ("raw", request.raw_files, raw_fd),
                ("normalized", request.normalized_files, normalized_fd),
            ):
                for index, source in enumerate(paths):
                    safe_name = f"{index:04d}_{Path(source).name}"
                    entry = _copy_source(Path(source), directory_fd, safe_name)
                    source_identity = (entry["source_device"], entry["source_inode"])
                    if source_identity in identities:
                        raise CaptureError("HSA4_E_SOURCE_DUPLICATE", str(source))
                    identities.add(source_identity)
                    entries.append({"family": family, "sealed_path": f"{family}/{safe_name}", **entry})
            os.fsync(raw_fd)
            os.fsync(normalized_fd)
        finally:
            os.close(raw_fd)
            os.close(normalized_fd)

        manifest: dict[str, Any] = {
            "schema_version": "hsa4.isolated_daily_sealed_capture.v2",
            "artifact_type": "ModelBSourceSealedSnapshotCandidate",
            "snapshot_id": request.snapshot_id,
            "append_only": True,
            "isolated": True,
            "production_allowed": False,
            "source_family": request.source_family,
            "source_id": request.source_id,
            "provider": request.provider,
            "source_endpoint_version": request.source_endpoint_version,
            "parser_version": request.parser_version,
            "normalized_schema_version": request.schema_version,
            "request_parameters": canonical_parameters,
            "http_status": request.http_status,
            "transport_identity": request.transport_identity,
            "trade_date": request.trade_date,
            "source_published_at": request.source_published_at,
            "available_at": request.available_at,
            "fetched_at": request.fetched_at,
            "scope": {
                **scopes,
                "expected_count": len(scopes["expected_scope"]),
                "returned_count": len(scopes["returned_scope"]),
                "absent_count": len(scopes["absent_scope"]),
                "unknown_count": len(scopes["unknown_scope"]),
                "closure": True,
            },
            "files": entries,
            "file_count": len(entries),
            "lineage_digest": sha256_bytes(canonical_json({
                "source_family": request.source_family,
                "source_id": request.source_id,
                "provider": request.provider,
                "source_endpoint_version": request.source_endpoint_version,
                "trade_date": request.trade_date,
                "files": [
                    {key: entry[key] for key in ("family", "sealed_path", "sha256", "size_bytes", "source_device", "source_inode")}
                    for entry in entries
                ],
            })),
            "manifest_written_last": True,
            "forbidden_scope": {
                "network": False,
                "provider_write": False,
                "latest_write": False,
                "cron_or_daily_auto_write": False,
                "frontend_or_backend_write": False,
                "training_scoring_replay": False,
            },
        }
        manifest_bytes = canonical_json(manifest)
        _write_file(stage_fd, "manifest.json", (manifest_bytes,))
        os.fsync(stage_fd)
        _assert_root_chain(output_root, root_chain)
        _rename_noreplace(root_fd, stage_name, request.snapshot_id)
        installed = True
        os.fsync(root_fd)
        _assert_root_chain(output_root, root_chain)
        final_info = os.stat(request.snapshot_id, dir_fd=root_fd, follow_symlinks=False)
        if not stat.S_ISDIR(final_info.st_mode) or (final_info.st_dev, final_info.st_ino) != stage_identity:
            raise CaptureError("HSA4_E_FINAL_IDENTITY", request.snapshot_id)
        _assert_root_chain(output_root, root_chain)
        return output_root / request.snapshot_id
    except BaseException as exc:
        try:
            if stage_fd is not None:
                os.close(stage_fd)
                stage_fd = None
            if installed or stage_created:
                _isolate_failed_entry(
                    root_fd,
                    request.snapshot_id if installed else stage_name,
                    stage_identity,
                    transaction_id,
                    exc,
                )
        except BaseException as isolation_exc:
            raise CaptureError("HSA4_E_FAILURE_ISOLATION_TAINT", f"{exc}; isolation failed: {isolation_exc}") from isolation_exc
        raise
    finally:
        if stage_fd is not None:
            os.close(stage_fd)
        os.close(root_fd)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--source-family", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--source-endpoint-version", required=True)
    parser.add_argument("--parser-version", required=True)
    parser.add_argument("--schema-version", required=True)
    parser.add_argument("--trade-date", required=True)
    parser.add_argument("--source-published-at", required=True)
    parser.add_argument("--available-at", required=True)
    parser.add_argument("--fetched-at", required=True)
    parser.add_argument("--http-status", required=True, type=int)
    parser.add_argument("--transport-identity", default="local_offline_explicit_files")
    parser.add_argument("--request-parameters-json", default="{}")
    parser.add_argument("--raw-file", action="append", type=Path, required=True)
    parser.add_argument("--normalized-file", action="append", type=Path, required=True)
    parser.add_argument("--expected-instrument", action="append", default=[])
    parser.add_argument("--returned-instrument", action="append", default=[])
    parser.add_argument("--absent-instrument", action="append", default=[])
    parser.add_argument("--unknown-instrument", action="append", default=[])
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if _absolute(args.output_root) != _absolute(DEFAULT_OUTPUT_ROOT):
        raise CaptureError("HSA4_E_OUTPUT_ROOT", "CLI output root must be the isolated HSA4 root")
    try:
        parameters = json.loads(args.request_parameters_json)
    except json.JSONDecodeError as exc:
        raise CaptureError("HSA4_E_REQUEST_PARAMETERS", "invalid JSON") from exc
    request = CaptureRequest(
        snapshot_id=args.snapshot_id,
        source_family=args.source_family,
        source_id=args.source_id,
        provider=args.provider,
        source_endpoint_version=args.source_endpoint_version,
        parser_version=args.parser_version,
        schema_version=args.schema_version,
        trade_date=args.trade_date,
        source_published_at=args.source_published_at,
        available_at=args.available_at,
        fetched_at=args.fetched_at,
        http_status=args.http_status,
        transport_identity=args.transport_identity,
        request_parameters=parameters,
        raw_files=args.raw_file,
        normalized_files=args.normalized_file,
        expected_scope=args.expected_instrument,
        returned_scope=args.returned_instrument,
        absent_scope=args.absent_instrument,
        unknown_scope=args.unknown_instrument,
    )
    output = build_capture(request)
    print(json.dumps({"status": "HSA4_ISOLATED_CAPTURE_CREATED", "path": os.fspath(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
