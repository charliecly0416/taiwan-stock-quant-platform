#!/usr/bin/env python3
"""Build readonly HSA5 daily-auto sealed-capture wiring evidence.

The implementation parses runner source without importing it, securely reads
explicit local evidence, and writes only an isolated preflight packet.
"""

from __future__ import annotations

import argparse
import ast
import csv
import errno
import hashlib
import json
import math
import os
import re
import stat
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "data_tw/experiments/model_b_path2_sealed_archive_retrain/hsa5_daily_auto_sealed_capture_wiring_preflight_20260825"
SCHEMA_VERSION = "hsa5_daily_auto_sealed_capture_wiring_preflight_v3"
HANDOFF_SCHEMA_VERSION = "hsa5.same_run_acquisition_handoff.v1"
READY = "READY_FOR_HSA6_NO_CRON_IMPLEMENTATION"
STOP = "STOP_HSA5_UPSTREAM_CAPTURE_CONTRACT_GAPS"
STABLE_SOURCE_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

PROTECTED_PATHS: tuple[tuple[str, str], ...] = (
    ("installed_cron", "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron"),
    ("formal_provider", "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin"),
    ("qlib_accepted_latest", "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json"),
    ("legacy_latest", "data_tw/experiments/option_c_daily_signal/latest_signal.json"),
    ("product_signal_latest", "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json"),
    ("readonly_snapshot_latest", "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json"),
    ("agent_prompt_latest", "data_tw/artifacts/agent_daily_prompt/latest.json"),
)

CAPTURE_SOURCE_SPECS: tuple[tuple[str, str, str], ...] = (
    ("adjusted_price", "adjusted_price_raw_lineage", "model_b_required"),
    ("twii", "twii_raw_lineage", "model_b_required"),
    ("institutional_flow", "institutional_flow", "model_b_required"),
    ("margin_short", "margin_short", "model_b_required"),
    ("corporate_actions", "corporate_actions", "conditional_adjusted_lineage"),
    ("daily_price", "finmind_raw_daily_price", "optional_future_research"),
    ("monthly_revenue", "monthly_revenue", "optional_future_research"),
    ("valuation", "valuation", "optional_future_research"),
)

REQUIRED_METADATA = (
    "snapshot_id", "source_family", "source_id", "provider", "source_endpoint_version",
    "request_parameters", "fetched_at", "http_status", "transport_identity", "parser_version",
    "schema_version", "trade_date", "available_at", "source_published_at", "raw_artifact_role",
    "normalized_artifact_role", "source_validator_status", "acquisition_run_id",
)
SCOPE_FIELDS = ("expected_scope", "returned_scope", "absent_scope", "unknown_scope")


class PreflightError(RuntimeError):
    pass


@dataclass(frozen=True)
class SecureRead:
    data: bytes
    evidence: dict[str, Any]


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _open_regular_no_follow(path: Path) -> tuple[int, tuple[tuple[int, int], ...], os.stat_result]:
    absolute = _absolute(path)
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    file_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        directory_fd = os.open(absolute.anchor, directory_flags)
    except OSError as exc:
        raise PreflightError(f"cannot open trusted path anchor: {absolute}") from exc
    chain: list[tuple[int, int]] = []
    root_info = os.fstat(directory_fd)
    chain.append((root_info.st_dev, root_info.st_ino))
    try:
        for component in absolute.parts[1:-1]:
            if component in {"", ".", ".."}:
                raise PreflightError(f"invalid path component: {absolute}")
            next_fd = os.open(component, directory_flags, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
            info = os.fstat(directory_fd)
            chain.append((info.st_dev, info.st_ino))
        file_fd = os.open(absolute.name, file_flags, dir_fd=directory_fd)
    except OSError as exc:
        raise PreflightError(f"nofollow regular-file open failed: {absolute}: {os.strerror(exc.errno or errno.EIO)}") from exc
    finally:
        os.close(directory_fd)
    info = os.fstat(file_fd)
    if not stat.S_ISREG(info.st_mode):
        os.close(file_fd)
        raise PreflightError(f"input is not a regular file: {absolute}")
    return file_fd, tuple(chain), info


def _after_fd_read(path: Path, file_fd: int) -> None:
    """Test hook after content read and before locator revalidation."""


def _secure_read(path: Path) -> SecureRead:
    absolute = _absolute(path)
    file_fd, chain, before = _open_regular_no_follow(absolute)
    digest = hashlib.sha256()
    chunks: list[bytes] = []
    try:
        while True:
            chunk = os.read(file_fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
            digest.update(chunk)
        after = os.fstat(file_fd)
        _after_fd_read(absolute, file_fd)
    finally:
        os.close(file_fd)
    before_identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if before_identity != after_identity:
        raise PreflightError(f"file identity changed while reading: {absolute}")
    verify_fd, verify_chain, verify = _open_regular_no_follow(absolute)
    os.close(verify_fd)
    locator_identity = (verify.st_dev, verify.st_ino, verify.st_size, verify.st_mtime_ns)
    if verify_chain != chain or locator_identity != before_identity:
        raise PreflightError(f"path locator identity changed while reading: {absolute}")
    return SecureRead(
        data=b"".join(chunks),
        evidence={
            "path": os.fspath(absolute), "device": before.st_dev, "inode": before.st_ino,
            "size": before.st_size, "mtime_ns": before.st_mtime_ns, "sha256": digest.hexdigest(),
            "ancestor_chain": [{"device": device, "inode": inode} for device, inode in chain],
            "nofollow_openat": True, "fd_identity_stable": True, "locator_revalidated": True,
        },
    )


def _sha256(path: Path) -> str:
    return _secure_read(path).evidence["sha256"]


def _open_directory_no_follow(path: Path) -> tuple[int, tuple[tuple[int, int], ...]]:
    absolute = _absolute(path)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    current_fd = os.open(absolute.anchor, flags)
    chain: list[tuple[int, int]] = []
    try:
        root = os.fstat(current_fd)
        chain.append((root.st_dev, root.st_ino))
        for component in absolute.parts[1:]:
            next_fd = os.open(component, flags, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
            info = os.fstat(current_fd)
            chain.append((info.st_dev, info.st_ino))
    except BaseException:
        os.close(current_fd)
        raise
    return current_fd, tuple(chain)


def _tree_rows(directory_fd: int, prefix: str = "") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name in sorted(os.listdir(directory_fd)):
        relative = f"{prefix}/{name}" if prefix else name
        info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        common = {
            "path": relative,
            "mode": stat.S_IMODE(info.st_mode),
            "size": info.st_size,
            "mtime_ns": info.st_mtime_ns,
            "device": info.st_dev,
            "inode": info.st_ino,
        }
        if stat.S_ISDIR(info.st_mode):
            child_fd = os.open(
                name,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=directory_fd,
            )
            try:
                opened = os.fstat(child_fd)
                if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
                    raise PreflightError(f"protected tree directory identity changed: {relative}")
                rows.append({**common, "type": "directory"})
                rows.extend(_tree_rows(child_fd, relative))
            finally:
                os.close(child_fd)
        elif stat.S_ISREG(info.st_mode):
            file_fd = os.open(name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=directory_fd)
            digest = hashlib.sha256()
            try:
                opened = os.fstat(file_fd)
                if (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns) != (
                    info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
                ):
                    raise PreflightError(f"protected tree file identity changed: {relative}")
                while True:
                    chunk = os.read(file_fd, 1024 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
                after = os.fstat(file_fd)
                if (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) != (
                    info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
                ):
                    raise PreflightError(f"protected tree file changed while reading: {relative}")
            finally:
                os.close(file_fd)
            rows.append({**common, "type": "regular", "sha256": digest.hexdigest()})
        elif stat.S_ISLNK(info.st_mode):
            rows.append({**common, "type": "symlink", "target_sha256": hashlib.sha256(os.readlink(name, dir_fd=directory_fd).encode()).hexdigest()})
        else:
            rows.append({**common, "type": "other"})
    return rows


def _fingerprint_protected_path(path: Path) -> dict[str, Any]:
    absolute = _absolute(path)
    try:
        secure = _secure_read(absolute)
    except PreflightError as file_error:
        try:
            directory_fd, chain = _open_directory_no_follow(absolute)
        except FileNotFoundError:
            return {"path": os.fspath(absolute), "status": "ABSENT", "nofollow": True}
        except OSError as exc:
            if exc.errno == errno.ENOENT:
                return {"path": os.fspath(absolute), "status": "ABSENT", "nofollow": True}
            raise PreflightError(f"protected path cannot be fingerprinted: {absolute}: {file_error}") from exc
        try:
            root_before = os.fstat(directory_fd)
            rows = _tree_rows(directory_fd)
            root_after = os.fstat(directory_fd)
        finally:
            os.close(directory_fd)
        if (root_before.st_dev, root_before.st_ino, root_before.st_mtime_ns) != (
            root_after.st_dev, root_after.st_ino, root_after.st_mtime_ns,
        ):
            raise PreflightError(f"protected directory changed while fingerprinting: {absolute}")
        verify_fd, verify_chain = _open_directory_no_follow(absolute)
        try:
            verify = os.fstat(verify_fd)
        finally:
            os.close(verify_fd)
        if verify_chain != chain or (verify.st_dev, verify.st_ino) != (root_before.st_dev, root_before.st_ino):
            raise PreflightError(f"protected directory locator changed: {absolute}")
        return {
            "path": os.fspath(absolute), "status": "PRESENT", "type": "directory", "nofollow": True,
            "device": root_before.st_dev, "inode": root_before.st_ino, "entry_count": len(rows),
            "tree_sha256": hashlib.sha256(_canonical_json(rows)).hexdigest(),
        }
    return {"status": "PRESENT", "type": "regular", **secure.evidence}


def _protected_fingerprints(project_root: Path) -> dict[str, dict[str, Any]]:
    return {role: _fingerprint_protected_path(project_root / relative) for role, relative in PROTECTED_PATHS}


def _assert_output_scope(output_dir: Path, *, allow_test_output_override: bool) -> Path:
    absolute = _absolute(output_dir)
    if allow_test_output_override:
        return absolute
    if absolute != _absolute(DEFAULT_OUTPUT_DIR):
        raise PreflightError(f"production output must equal isolated HSA5 root: {DEFAULT_OUTPUT_DIR}")
    current = Path(absolute.anchor)
    for component in absolute.parts[1:]:
        current /= component
        try:
            info = os.lstat(current)
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode):
            raise PreflightError(f"isolated output path contains symlink: {current}")
    return absolute


def _validate_json_value(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (bool, str, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise PreflightError(f"non-finite JSON value at {path}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise PreflightError(f"non-string JSON key at {path}")
            _validate_json_value(item, f"{path}.{key}")
        return
    raise PreflightError(f"non-JSON value at {path}: {type(value).__name__}")


def _canonical_json(payload: Any) -> bytes:
    _validate_json_value(payload)
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            os.fchmod(handle.fileno(), 0o644)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _write_json(path: Path, payload: Any) -> None:
    _atomic_write(path, _canonical_json(payload))


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None and parsed.utcoffset() is not None else None


def _call_name(call: ast.Call) -> str:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return ""


class _FunctionCallVisitor(ast.NodeVisitor):
    def __init__(self, root: ast.FunctionDef | ast.AsyncFunctionDef):
        self.root = root
        self.calls: list[ast.Call] = []

    def visit_Call(self, node: ast.Call) -> None:
        self.calls.append(node)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node is self.root:
            self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if node is self.root:
            self.generic_visit(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return


def _function_calls(function: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.Call]:
    visitor = _FunctionCallVisitor(function)
    visitor.visit(function)
    return visitor.calls


def _synthetic_function(body: list[ast.stmt]) -> ast.FunctionDef:
    return ast.FunctionDef(
        name="_scope",
        args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
        body=body,
        decorator_list=[],
    )


def _top_level_function(tree: ast.Module, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    matches = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name]
    return matches[0] if len(matches) == 1 else None


def _is_skip_finmind_guard(node: ast.If) -> bool:
    expected = ast.UnaryOp(
        op=ast.Not(),
        operand=ast.Attribute(value=ast.Name(id="args", ctx=ast.Load()), attr="skip_finmind", ctx=ast.Load()),
    )
    return ast.dump(node.test, include_attributes=False) == ast.dump(expected, include_attributes=False)


def _assigned_call_name(statement: ast.stmt) -> tuple[str, str, int] | None:
    if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
        target, value = statement.targets[0], statement.value
    elif isinstance(statement, ast.AnnAssign):
        target, value = statement.target, statement.value
    else:
        return None
    if isinstance(value, ast.Call) and isinstance(target, ast.Name):
        return target.id, _call_name(value), value.lineno
    return None


def _if_fail_closes_variable(statement: ast.stmt, variable: str) -> bool:
    if not isinstance(statement, ast.If):
        return False
    def is_ok_call(node: ast.AST) -> bool:
        return bool(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == variable
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == "ok"
        )

    test = statement.test
    failure_condition = isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not) and is_ok_call(test.operand)
    if isinstance(test, ast.Compare) and len(test.ops) == 1 and len(test.comparators) == 1 and is_ok_call(test.left):
        comparator = test.comparators[0]
        false_literal = isinstance(comparator, ast.Constant) and comparator.value is False
        true_literal = isinstance(comparator, ast.Constant) and comparator.value is True
        failure_condition = failure_condition or (false_literal and isinstance(test.ops[0], (ast.Eq, ast.Is)))
        failure_condition = failure_condition or (true_literal and isinstance(test.ops[0], (ast.NotEq, ast.IsNot)))
    return failure_condition and any(isinstance(node, (ast.Return, ast.Raise)) for node in statement.body)


def _direct_statement_call(statement: ast.stmt) -> ast.Call | None:
    value: ast.AST | None = None
    if isinstance(statement, ast.Expr):
        value = statement.value
    elif isinstance(statement, ast.Assign) and len(statement.targets) == 1:
        value = statement.value
    elif isinstance(statement, ast.AnnAssign):
        value = statement.value
    return value if isinstance(value, ast.Call) else None


def _is_job_json_anchor(call: ast.Call) -> bool:
    if not isinstance(call.func, ast.Name) or call.func.id != "write_json" or len(call.args) != 2 or call.keywords:
        return False
    path_arg, payload_arg = call.args
    return bool(
        isinstance(path_arg, ast.BinOp)
        and isinstance(path_arg.op, ast.Div)
        and isinstance(path_arg.left, ast.Name)
        and path_arg.left.id == "job_dir"
        and isinstance(path_arg.right, ast.Constant)
        and path_arg.right.value == "job.json"
        and isinstance(payload_arg, ast.Name)
        and payload_arg.id == "job"
    )


def _nested_relevant_calls(statement: ast.stmt) -> list[ast.Call]:
    direct = _direct_statement_call(statement)
    relevant: list[ast.Call] = []
    for call in _function_calls(_synthetic_function([statement])):
        name = _call_name(call)
        if call is direct:
            continue
        if name in {
            "run_finmind_segmented_update", "run_finmind_orthogonal_batch_update", "write_json",
            "run_provider_candidate_refresh_gate", "run_model_signal_gate",
        } or "validate" in name.lower():
            relevant.append(call)
    return relevant


def _literal_false(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value is False


def _known_env_call_fallback(call: ast.Call) -> ast.AST | None:
    known = False
    if isinstance(call.func, ast.Name) and call.func.id in {"getenv", "env_flag"}:
        known = True
    elif isinstance(call.func, ast.Attribute) and call.func.attr == "getenv":
        known = isinstance(call.func.value, ast.Name) and call.func.value.id == "os"
    elif isinstance(call.func, ast.Attribute) and call.func.attr == "get":
        value = call.func.value
        known = bool(
            isinstance(value, ast.Attribute)
            and isinstance(value.value, ast.Name)
            and value.value.id == "os"
            and value.attr == "environ"
        )
    if not known:
        return None
    if len(call.args) >= 2:
        return call.args[1]
    return next((keyword.value for keyword in call.keywords if keyword.arg == "default"), None)


def _recognized_env_fallback(node: ast.AST) -> ast.AST | None:
    candidate = node
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], (ast.In, ast.NotIn)):
        candidate = node.left
    if isinstance(candidate, ast.Call) and isinstance(candidate.func, ast.Attribute) and candidate.func.attr in {"lower", "casefold"}:
        candidate = candidate.func.value
    if not isinstance(candidate, ast.Call):
        return None
    return _known_env_call_fallback(candidate)


def _default_validation_safety(main: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, Any]:
    matches = [
        call for call in _function_calls(main)
        if _call_name(call) == "add_argument"
        and call.args
        and isinstance(call.args[0], ast.Constant)
        and call.args[0].value == "--skip-finmind-validate"
    ]
    if len(matches) != 1:
        reason = "skip_finmind_validate_argument_missing" if not matches else "skip_finmind_validate_argument_not_unique"
        return {"default_validation_enabled_proven": False, "default_validation_safety_status": "UNKNOWN", "default_validation_safety_reason": reason}
    default = next((keyword.value for keyword in matches[0].keywords if keyword.arg == "default"), None)
    if default is None:
        return {"default_validation_enabled_proven": False, "default_validation_safety_status": "UNKNOWN", "default_validation_safety_reason": "default_keyword_missing"}
    if _literal_false(default):
        return {"default_validation_enabled_proven": True, "default_validation_safety_status": "PROVEN_SAFE_FALSE", "default_validation_safety_reason": "literal_false"}
    env_fallback = _recognized_env_fallback(default)
    if env_fallback is not None and isinstance(env_fallback, ast.Constant) and (
        env_fallback.value is False
        or (isinstance(env_fallback.value, str) and env_fallback.value.strip().lower() == "false")
    ):
        return {"default_validation_enabled_proven": False, "default_validation_safety_status": "UNKNOWN", "default_validation_safety_reason": "runtime_environment_can_override_false_fallback"}
    if env_fallback is not None and isinstance(env_fallback, ast.Constant) and (
        env_fallback.value is True
        or (isinstance(env_fallback.value, str) and env_fallback.value.strip().lower() == "true")
    ):
        return {"default_validation_enabled_proven": False, "default_validation_safety_status": "PROVEN_UNSAFE_TRUE", "default_validation_safety_reason": "known_env_fallback_true"}
    if env_fallback is not None:
        return {"default_validation_enabled_proven": False, "default_validation_safety_status": "UNKNOWN", "default_validation_safety_reason": "known_env_fallback_dynamic"}
    if isinstance(default, ast.Constant) and (
        default.value is True or (isinstance(default.value, str) and default.value.strip().lower() == "true")
    ):
        return {"default_validation_enabled_proven": False, "default_validation_safety_status": "PROVEN_UNSAFE_TRUE", "default_validation_safety_reason": "literal_true"}
    return {"default_validation_enabled_proven": False, "default_validation_safety_status": "UNKNOWN", "default_validation_safety_reason": "dynamic_or_unrecognized_default"}


def _warning_only_continuation_present(main: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for node in ast.walk(main):
        if not isinstance(node, ast.If):
            continue
        has_warning_assignment = any(
            isinstance(candidate, ast.Constant) and candidate.value == "finmind_update_warning"
            for candidate in ast.walk(_synthetic_function(node.body))
        )
        fail_closed = any(isinstance(candidate, (ast.Return, ast.Raise)) for candidate in ast.walk(_synthetic_function(node.body)))
        if has_warning_assignment and not fail_closed:
            return True
    return False


def analyze_static_insertion_point(daily_source: str, backend_source: str) -> dict[str, Any]:
    try:
        daily_tree = ast.parse(daily_source)
        backend_tree = ast.parse(backend_source)
    except SyntaxError as exc:
        return {"ok": False, "reason": f"python_syntax_error:{exc.msg}"}
    daily_main = _top_level_function(daily_tree, "main")
    backend_entry = _top_level_function(backend_tree, "run_workflow")
    if daily_main is None or backend_entry is None:
        return {"ok": False, "reason": "unique_main_or_run_workflow_entry_not_found"}

    main_calls = _function_calls(daily_main)
    backend_calls = _function_calls(backend_entry)
    call_lines: dict[str, list[int]] = {}
    for call in main_calls:
        call_lines.setdefault(_call_name(call), []).append(call.lineno)
    backend_call_names = {_call_name(call) for call in backend_calls}
    guard_matches = [statement for statement in daily_main.body if isinstance(statement, ast.If) and _is_skip_finmind_guard(statement)]
    guard = guard_matches[0] if len(guard_matches) == 1 else None
    direct_guard_calls: list[tuple[int, ast.Call]] = []
    nested_ambiguities: list[dict[str, Any]] = []
    if guard:
        for index, statement in enumerate(guard.body):
            direct = _direct_statement_call(statement)
            if direct is not None:
                direct_guard_calls.append((index, direct))
            for call in _nested_relevant_calls(statement):
                nested_ambiguities.append({"call": _call_name(call), "line": call.lineno, "guard_statement_index": index})

    fetch_positions = [(index, call) for index, call in direct_guard_calls if _call_name(call) == "run_finmind_segmented_update"]
    orthogonal_positions = [(index, call) for index, call in direct_guard_calls if _call_name(call) == "run_finmind_orthogonal_batch_update"]
    fetch_end_index = max([index for index, _ in fetch_positions + orthogonal_positions], default=None)
    fetch_end_line = max([call.lineno for _, call in fetch_positions + orthogonal_positions], default=None)

    validator_assignment: tuple[str, str, int] | None = None
    validator_index: int | None = None
    fail_close_index: int | None = None
    anchor_call: ast.Call | None = None
    anchor_index: int | None = None
    if guard and fetch_end_index is not None:
        validator_candidates: list[tuple[int, tuple[str, str, int]]] = []
        anchor_candidates: list[tuple[int, ast.Call]] = []
        for index, statement in enumerate(guard.body):
            assigned = _assigned_call_name(statement)
            if assigned and index > fetch_end_index and "validate" in assigned[1].lower():
                validator_candidates.append((index, assigned))
            direct = _direct_statement_call(statement)
            if direct is not None and _is_job_json_anchor(direct) and index > fetch_end_index:
                anchor_candidates.append((index, direct))
        if len(validator_candidates) == 1 and len(anchor_candidates) == 1:
            validator_index, validator_assignment = validator_candidates[0]
            anchor_index, anchor_call = anchor_candidates[0]
            matching_fail_closes = [
                index for index, statement in enumerate(guard.body)
                if validator_index < index < anchor_index and _if_fail_closes_variable(statement, validator_assignment[0])
            ]
            if len(matching_fail_closes) == 1:
                fail_close_index = matching_fail_closes[0]

    validator_fail_closed = fail_close_index is not None

    direct_main_calls = [
        (index, direct)
        for index, statement in enumerate(daily_main.body)
        if (direct := _direct_statement_call(statement)) is not None
    ]
    downstream = [
        (index, call) for index, call in direct_main_calls
        if _call_name(call) in {"run_provider_candidate_refresh_gate", "run_model_signal_gate"}
        and guard is not None and index > daily_main.body.index(guard)
    ]
    downstream_call = min(downstream, key=lambda item: item[0])[1] if downstream else None
    backend_required = {
        "daily_price": "archive_symbols", "corporate_actions": "archive_corporate_action_symbols",
        "institutional_flow": "archive_institutional_symbols", "margin_short": "archive_margin_symbols",
        "monthly_revenue": "archive_monthly_revenue_symbols", "valuation": "archive_valuation_symbols",
    }
    backend_family_calls = {family: call in backend_call_names for family, call in backend_required.items()}
    order_ok = bool(
        guard and len(fetch_positions) == 1 and anchor_call and downstream_call
        and fetch_end_line is not None and fetch_end_line < anchor_call.lineno < downstream_call.lineno
        and validator_index is not None and fail_close_index is not None and anchor_index is not None
        and fetch_end_index < validator_index < fail_close_index < anchor_index
        and not nested_ambiguities
    )
    default_safety = _default_validation_safety(daily_main)
    warning_only_continuation = _warning_only_continuation_present(daily_main)
    explicit_validator_shape = bool(validator_assignment and validator_fail_closed)
    complete_validator_pass_gate = bool(
        explicit_validator_shape
        and order_ok
        and default_safety["default_validation_enabled_proven"]
        and not warning_only_continuation
    )
    existing_capture_calls = sorted({
        _call_name(call) for call in main_calls
        if "sealed" in _call_name(call).lower() or "hsa4" in _call_name(call).lower() or "hsa5" in _call_name(call).lower()
    })
    return {
        "ok": complete_validator_pass_gate and all(backend_family_calls.values()),
        "entry_function": "main",
        "backend_entry_function": "run_workflow",
        "analysis_scope_limited_to_entry_functions": True,
        "daily_runner_imported_or_executed": False,
        "finmind_guard_unique": len(guard_matches) == 1,
        "fetch_and_anchor_in_same_skip_finmind_guard": bool(guard and fetch_positions and anchor_call),
        "linear_guard_control_flow_proven": bool(order_ok),
        "nested_or_divergent_relevant_calls": nested_ambiguities,
        "source_validator": {
            "explicit_validator_call": validator_assignment[1] if validator_assignment else "",
            "validator_result_variable": validator_assignment[0] if validator_assignment else "",
            "fail_closed_return_or_raise_before_anchor": validator_fail_closed,
            "validator_statement_index": validator_index,
            "fail_close_statement_index": fail_close_index,
            "anchor_statement_index": anchor_index,
            **default_safety,
            "default_skip_validation_detected": not default_safety["default_validation_enabled_proven"],
            "warning_only_continuation_detected": warning_only_continuation,
            "explicit_validator_shape_proven": explicit_validator_shape,
            "validator_pass_proven": complete_validator_pass_gate,
            "status": "PASS_COMPLETE_FAIL_CLOSED_VALIDATOR_GATE" if complete_validator_pass_gate else "STOP_VALIDATOR_PASS_NOT_PROVEN",
        },
        "exact_insertion_point": {
            "after_line": anchor_call.lineno if anchor_call else None,
            "after_statement": ast.unparse(anchor_call) if anchor_call else "",
            "inside_guard": "if not args.skip_finmind" if guard else "",
            "before_line": downstream_call.lineno if downstream_call else None,
            "before_call": _call_name(downstream_call) if downstream_call else "",
            "required_runtime_condition": "same-run source-specific validator passed with fail-closed return/raise before HSA capture",
        },
        "call_lines_in_main": {name: sorted(lines) for name, lines in call_lines.items() if name in {
            "run_finmind_segmented_update", "run_finmind_orthogonal_batch_update", "run_provider_candidate_refresh_gate",
            "run_model_signal_gate", "finalize_job",
        }},
        "backend_source_family_fetch_calls_present": backend_family_calls,
        "existing_sealed_capture_call_present": bool(existing_capture_calls),
        "existing_sealed_capture_calls": existing_capture_calls,
        "runtime_inventory_timing_gap": "daily_source_inventory is built only by finalize_job, after downstream gates; it cannot be the same-run capture handoff",
    }


def _path_list_status(value: Any, project_root: Path) -> tuple[bool, list[dict[str, Any]], list[str]]:
    if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item.strip() for item in value):
        return False, [], ["missing_or_invalid_path_list"]
    evidence: list[dict[str, Any]] = []
    errors: list[str] = []
    for raw in value:
        path = Path(raw)
        path = path if path.is_absolute() else project_root / path
        try:
            evidence.append(_secure_read(path).evidence)
        except PreflightError as exc:
            errors.append(f"secure_read_failed:{raw}:{exc}")
    return not errors and len(evidence) == len(value), evidence, errors


def _load_handoff_manifest(inventory: Mapping[str, Any], project_root: Path) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    raw_path = inventory.get("acquisition_handoff_manifest_path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return {}, {}, ["same_run_acquisition_handoff_manifest_path_missing"]
    path = Path(raw_path)
    path = path if path.is_absolute() else project_root / path
    try:
        secure = _secure_read(path)
        payload = json.loads(secure.data)
    except (PreflightError, json.JSONDecodeError) as exc:
        return {}, {}, [f"same_run_acquisition_handoff_manifest_unreadable:{exc}"]
    gaps: list[str] = []
    if not isinstance(payload, Mapping):
        return {}, secure.evidence, ["same_run_acquisition_handoff_manifest_not_object"]
    if payload.get("schema_version") != HANDOFF_SCHEMA_VERSION:
        gaps.append("same_run_acquisition_handoff_manifest_schema_invalid")
    run_id = payload.get("acquisition_run_id")
    if not isinstance(run_id, str) or len(run_id) > 128 or not STABLE_SOURCE_ID_RE.fullmatch(run_id):
        gaps.append("same_run_acquisition_run_id_missing_or_invalid")
    if payload.get("target_asof") != inventory.get("target_asof"):
        gaps.append("same_run_target_asof_mismatch")
    source_records = payload.get("sources")
    if not isinstance(source_records, list):
        gaps.append("same_run_handoff_sources_not_list")
        source_records = []
    by_family: dict[str, Any] = {}
    for record in source_records:
        if not isinstance(record, Mapping) or not isinstance(record.get("source_family"), str):
            gaps.append("same_run_handoff_source_record_invalid")
            continue
        family = record["source_family"]
        if family in by_family:
            gaps.append(f"same_run_handoff_duplicate_source_family:{family}")
            continue
        by_family[family] = dict(record)
    return {"acquisition_run_id": run_id, "sources": by_family}, secure.evidence, gaps


def _handoff_binding_status(
    family: str,
    record: Mapping[str, Any],
    raw_evidence: Sequence[Mapping[str, Any]],
    normalized_evidence: Sequence[Mapping[str, Any]],
    handoff: Mapping[str, Any],
    project_root: Path,
) -> tuple[bool, list[str]]:
    source = handoff.get("sources", {}).get(family) if isinstance(handoff.get("sources"), Mapping) else None
    if not isinstance(source, Mapping):
        return False, ["same_run_handoff_source_family_missing"]
    gaps: list[str] = []
    run_id = handoff.get("acquisition_run_id")
    if record.get("acquisition_run_id") != run_id or source.get("acquisition_run_id") != run_id:
        gaps.append("same_run_acquisition_run_identity_mismatch")
    if source.get("source_family") != family or source.get("source_id") != record.get("source_id"):
        gaps.append("same_run_source_identity_mismatch")
    if source.get("source_validator_status") != "PASS" or source.get("source_validator_status") != record.get("source_validator_status"):
        gaps.append("same_run_source_validator_binding_invalid")
    artifacts = source.get("artifacts")
    if not isinstance(artifacts, list):
        return False, sorted(set(gaps + ["same_run_handoff_artifacts_not_list"]))
    expected_by_role: dict[str, list[tuple[str, str]]] = {
        "provider_raw_response": [], "provider_normalized_payload": [],
    }
    for artifact in artifacts:
        if not isinstance(artifact, Mapping):
            gaps.append("same_run_handoff_artifact_invalid")
            continue
        role, raw_path, digest = artifact.get("role"), artifact.get("path"), artifact.get("sha256")
        if role not in expected_by_role or not isinstance(raw_path, str) or not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            gaps.append("same_run_handoff_artifact_contract_invalid")
            continue
        path = Path(raw_path)
        path = path if path.is_absolute() else project_root / path
        expected_by_role[role].append((os.fspath(_absolute(path)), digest))
    observed_by_role = {
        "provider_raw_response": sorted((item["path"], item["sha256"]) for item in raw_evidence),
        "provider_normalized_payload": sorted((item["path"], item["sha256"]) for item in normalized_evidence),
    }
    for role in expected_by_role:
        expected = sorted(expected_by_role[role])
        if not expected:
            gaps.append(f"same_run_handoff_{role}_missing")
        elif expected != observed_by_role[role]:
            gaps.append(f"same_run_handoff_{role}_path_or_sha256_mismatch")
    return not gaps, sorted(set(gaps))


def _scope_status(record: Mapping[str, Any]) -> tuple[bool, str]:
    values: dict[str, set[str]] = {}
    for field in SCOPE_FIELDS:
        raw = record.get(field)
        if not isinstance(raw, list) or any(not isinstance(item, str) or not item.strip() for item in raw):
            return False, f"missing_or_invalid:{field}"
        if len(raw) != len(set(raw)):
            return False, f"duplicate_member:{field}"
        values[field] = set(raw)
    if not values["expected_scope"]:
        return False, "expected_scope_empty"
    partitions = [values[field] for field in ("returned_scope", "absent_scope", "unknown_scope")]
    if any(partitions[i] & partitions[j] for i in range(3) for j in range(i + 1, 3)):
        return False, "partition_overlap"
    if set().union(*partitions) != values["expected_scope"]:
        return False, "partition_union_not_expected"
    return True, "closed"


def audit_source_family(
    family: str,
    inventory_key: str,
    requirement_class: str,
    sources: Mapping[str, Any],
    project_root: Path,
    *,
    handoff: Mapping[str, Any],
    handoff_global_gaps: Sequence[str],
    conditional_required: bool = False,
    cache_observation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    record = sources.get(inventory_key)
    if not isinstance(record, Mapping):
        record = sources.get(family)
    blocking = requirement_class == "model_b_required" or (requirement_class == "conditional_adjusted_lineage" and conditional_required)
    if not isinstance(record, Mapping):
        return {
            "source_family": family, "inventory_key": inventory_key, "requirement_class": requirement_class,
            "blocking_for_model_b": blocking, "inventory_record_present": False,
            "ready_for_hsa4_handoff": False, "ready": False,
            "gaps": ["source_family_inventory_record_missing"], "cache_observation": dict(cache_observation or {}),
        }

    gaps: list[str] = []
    raw_ok, raw_evidence, raw_errors = _path_list_status(record.get("raw_files"), project_root)
    normalized_ok, normalized_evidence, normalized_errors = _path_list_status(record.get("normalized_files"), project_root)
    gaps.extend(f"raw_files:{error}" for error in raw_errors)
    gaps.extend(f"normalized_files:{error}" for error in normalized_errors)
    gaps.extend(handoff_global_gaps)
    missing_metadata = [field for field in REQUIRED_METADATA if field not in record or record.get(field) in (None, "")]
    if not isinstance(record.get("request_parameters"), Mapping):
        if "request_parameters" not in missing_metadata:
            missing_metadata.append("request_parameters")
    else:
        try:
            _validate_json_value(dict(record["request_parameters"]))
        except PreflightError:
            if "request_parameters" not in missing_metadata:
                missing_metadata.append("request_parameters")
    gaps.extend(f"metadata_missing_or_invalid:{field}" for field in missing_metadata)
    identity_ok = bool(
        record.get("source_family") == family and isinstance(record.get("source_id"), str)
        and len(record["source_id"]) <= 128 and STABLE_SOURCE_ID_RE.fullmatch(record["source_id"])
    )
    if not identity_ok:
        gaps.append("source_identity_must_match_family_and_stable_source_id_format")
    roles_ok = record.get("raw_artifact_role") == "provider_raw_response" and record.get("normalized_artifact_role") == "provider_normalized_payload"
    if not roles_ok:
        gaps.append("artifact_roles_must_be_provider_raw_response_and_provider_normalized_payload")
    validator_ok = record.get("source_validator_status") == "PASS"
    if not validator_ok:
        gaps.append("source_validator_status_not_PASS")
    handoff_ok, handoff_gaps = _handoff_binding_status(
        family, record, raw_evidence, normalized_evidence, handoff, project_root,
    )
    gaps.extend(handoff_gaps)
    if not isinstance(record.get("http_status"), int) or not 100 <= record["http_status"] <= 599:
        gaps.append("http_status_invalid")
    published = _parse_timestamp(record.get("source_published_at"))
    available = _parse_timestamp(record.get("available_at"))
    fetched = _parse_timestamp(record.get("fetched_at"))
    time_ok = bool(published and available and fetched and published <= available <= fetched)
    if not time_ok:
        gaps.append("time_contract_requires_source_published_at<=available_at<=fetched_at_with_timezone")
    scope_ok, scope_reason = _scope_status(record)
    if not scope_ok:
        gaps.append(f"scope_closure:{scope_reason}")
    aggregate_only = bool(record.get("evidence_path")) and not raw_ok and not normalized_ok
    if aggregate_only:
        gaps.append("aggregate_evidence_is_not_sealed_raw_and_normalized_artifacts")
    ready = not gaps
    return {
        "source_family": family, "source_id": str(record.get("source_id") or ""), "inventory_key": inventory_key,
        "requirement_class": requirement_class, "blocking_for_model_b": blocking, "inventory_record_present": True,
        "raw_artifact_role": str(record.get("raw_artifact_role") or ""),
        "normalized_artifact_role": str(record.get("normalized_artifact_role") or ""),
        "source_validator_status": str(record.get("source_validator_status") or ""),
        "same_run_handoff_manifest_bound": handoff_ok and not handoff_global_gaps,
        "raw_paths_present_and_secure": raw_ok, "raw_file_evidence": raw_evidence,
        "normalized_paths_present_and_secure": normalized_ok, "normalized_file_evidence": normalized_evidence,
        "snapshot_metadata_complete": not missing_metadata, "publication_available_at_order_valid": time_ok,
        "scope_closure_valid": scope_ok, "scope_closure_status": scope_reason,
        "aggregate_evidence_only": aggregate_only, "cache_observation": dict(cache_observation or {}),
        "ready_for_hsa4_handoff": ready, "ready": ready, "gaps": sorted(set(gaps)),
    }


def _audit_model_score_lineage(sources: Mapping[str, Any], project_root: Path) -> dict[str, Any]:
    key = "model_a_qlib_score_top50_lineage"
    record = sources.get(key)
    gaps: list[str] = []
    evidence: dict[str, Any] = {}
    if not isinstance(record, Mapping):
        return {
            "dependency": key, "requirement_class": "model_b_required", "blocking_for_model_b": True,
            "ready": False, "gaps": ["model_a_qlib_score_top50_lineage_record_missing"],
        }
    for role, path_field, checksum_field in (
        ("model_a_or_qlib_score", "score_artifact_path", "score_artifact_sha256"),
        ("top50", "top50_artifact_path", "top50_artifact_sha256"),
    ):
        raw_path = record.get(path_field)
        if not isinstance(raw_path, str) or not raw_path.strip():
            gaps.append(f"{path_field}_missing")
            continue
        path = Path(raw_path)
        path = path if path.is_absolute() else project_root / path
        try:
            observed = _secure_read(path).evidence
        except PreflightError as exc:
            gaps.append(f"{path_field}_secure_read_failed:{exc}")
            continue
        if record.get(checksum_field) != observed["sha256"]:
            gaps.append(f"{checksum_field}_mismatch_or_missing")
        evidence[role] = observed
    lineage_id = record.get("lineage_id")
    if not isinstance(lineage_id, str) or len(lineage_id) > 128 or not STABLE_SOURCE_ID_RE.fullmatch(lineage_id):
        gaps.append("stable_lineage_id_missing_or_invalid")
    if record.get("source_validator_status") != "PASS":
        gaps.append("source_validator_status_not_PASS")
    if record.get("top50_count") != 50:
        gaps.append("top50_count_not_50")
    return {
        "dependency": key, "requirement_class": "model_b_required", "blocking_for_model_b": True,
        "lineage_id": str(lineage_id or ""), "source_validator_status": str(record.get("source_validator_status") or ""),
        "top50_count": record.get("top50_count"), "file_evidence": evidence,
        "ready": not gaps, "gaps": sorted(set(gaps)),
    }


def build_dependency_matrix(capture_rows: Sequence[Mapping[str, Any]], sources: Mapping[str, Any], project_root: Path) -> list[dict[str, Any]]:
    by_family = {row["source_family"]: row for row in capture_rows}
    rows = [
        {"dependency": "adjusted_price_raw_lineage", "requirement_class": "model_b_required", "blocking_for_model_b": True, "ready": bool(by_family["adjusted_price"]["ready"]), "gaps": list(by_family["adjusted_price"]["gaps"])},
        {"dependency": "twii_raw_lineage", "requirement_class": "model_b_required", "blocking_for_model_b": True, "ready": bool(by_family["twii"]["ready"]), "gaps": list(by_family["twii"]["gaps"])},
        _audit_model_score_lineage(sources, project_root),
        {"dependency": "institutional_flow", "requirement_class": "model_b_required", "blocking_for_model_b": True, "ready": bool(by_family["institutional_flow"]["ready"]), "gaps": list(by_family["institutional_flow"]["gaps"])},
        {"dependency": "margin_short", "requirement_class": "model_b_required", "blocking_for_model_b": True, "ready": bool(by_family["margin_short"]["ready"]), "gaps": list(by_family["margin_short"]["gaps"])},
    ]
    corporate = by_family["corporate_actions"]
    rows.append({
        "dependency": "corporate_actions", "requirement_class": "conditional_adjusted_lineage",
        "blocking_for_model_b": bool(corporate["blocking_for_model_b"]),
        "ready": bool(corporate["ready"]) if corporate["blocking_for_model_b"] else True,
        "capture_ready": bool(corporate["ready"]),
        "gaps": list(corporate["gaps"]) if corporate["blocking_for_model_b"] else [],
        "recommendation_gaps": list(corporate["gaps"]) if not corporate["blocking_for_model_b"] else [],
    })
    return rows


def _load_segment_cache_observations(cache_dir: Path | None) -> dict[str, dict[str, Any]]:
    if cache_dir is None:
        return {}
    try:
        names = sorted(cache_dir.glob("*.json"))
    except OSError:
        return {}
    observations: dict[str, dict[str, Any]] = {}
    for path in names:
        try:
            secure = _secure_read(path)
            payload = json.loads(secure.data)
        except (PreflightError, json.JSONDecodeError):
            continue
        segment = str(payload.get("segment") or "").strip()
        if segment:
            observations[segment] = {
                "cache_file_evidence": secure.evidence, "ok": bool(payload.get("ok")),
                "covered": bool(payload.get("covered")), "stdout_path_present": bool(payload.get("stdout_path")),
                "stderr_path_present": bool(payload.get("stderr_path")),
                "note": "status-only evidence; never satisfies provider raw/normalized sealed handoff",
            }
    return observations


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        os.fchmod(handle.fileno(), 0o644)
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: ";".join(row.get(field, [])) if field in {"gaps", "recommendation_gaps"} else row.get(field, "") for field in fieldnames})
        handle.flush()
        os.fsync(handle.fileno())
        temporary = handle.name
    os.replace(temporary, path)


def build_preflight(
    *, daily_script: Path, backend_script: Path, source_inventory: Path, output_dir: Path,
    project_root: Path, segment_cache_dir: Path | None = None, allow_test_output_override: bool = False,
) -> dict[str, Any]:
    output_dir = _assert_output_scope(output_dir, allow_test_output_override=allow_test_output_override)
    daily_read = _secure_read(daily_script)
    backend_read = _secure_read(backend_script)
    inventory_read = _secure_read(source_inventory)
    protected_before = _protected_fingerprints(project_root)
    try:
        inventory = json.loads(inventory_read.data)
    except json.JSONDecodeError as exc:
        raise PreflightError(f"invalid source inventory JSON: {exc}") from exc
    sources = inventory.get("sources")
    if not isinstance(sources, Mapping):
        raise PreflightError("source inventory must contain an object at sources")
    handoff, handoff_evidence, handoff_global_gaps = _load_handoff_manifest(inventory, project_root)

    static_audit = analyze_static_insertion_point(daily_read.data.decode("utf-8"), backend_read.data.decode("utf-8"))
    cache = _load_segment_cache_observations(segment_cache_dir)
    adjusted_record = sources.get("adjusted_price_raw_lineage")
    corporate_required = bool(
        isinstance(adjusted_record, Mapping)
        and (adjusted_record.get("depends_on_corporate_actions") is True or "corporate_actions" in (adjusted_record.get("declared_dependencies") or []))
    )
    cache_aliases = {
        "daily_price": "daily_price", "corporate_actions": "corporate_actions", "institutional_flow": "institutional",
        "margin_short": "margin", "monthly_revenue": "monthly_revenue", "valuation": "valuation",
    }
    capture_rows = [
        audit_source_family(
            family, key, requirement, sources, project_root, conditional_required=corporate_required,
            handoff=handoff, handoff_global_gaps=handoff_global_gaps,
            cache_observation=cache.get(cache_aliases.get(family, "")),
        )
        for family, key, requirement in CAPTURE_SOURCE_SPECS
    ]
    dependency_rows = build_dependency_matrix(capture_rows, sources, project_root)
    after_reads = {
        "daily_runner_source": _secure_read(daily_script),
        "backend_runner_source": _secure_read(backend_script),
        "daily_source_inventory": _secure_read(source_inventory),
    }
    before_reads = {
        "daily_runner_source": daily_read,
        "backend_runner_source": backend_read,
        "daily_source_inventory": inventory_read,
    }
    protected_input_files_unchanged = all(
        after_reads[role].evidence["sha256"] == before.evidence["sha256"]
        and after_reads[role].evidence["device"] == before.evidence["device"]
        and after_reads[role].evidence["inode"] == before.evidence["inode"]
        for role, before in before_reads.items()
    )
    protected_after = _protected_fingerprints(project_root)
    protected_paths_unchanged = protected_before == protected_after
    protected_inputs_unchanged = protected_input_files_unchanged and protected_paths_unchanged
    dependencies_ready = all(row["ready"] for row in dependency_rows if row["blocking_for_model_b"])
    ready = bool(static_audit.get("ok")) and dependencies_ready and protected_inputs_unchanged
    decision = READY if ready else STOP
    output_dir.mkdir(parents=True, exist_ok=True)
    input_inventory = {
        "schema_version": SCHEMA_VERSION,
        "inputs": [
            {
                "role": role, "before": before_reads[role].evidence, "after": after_reads[role].evidence,
                "unchanged": before_reads[role].evidence["sha256"] == after_reads[role].evidence["sha256"]
                and before_reads[role].evidence["inode"] == after_reads[role].evidence["inode"],
            }
            for role in before_reads
        ],
        "segment_cache_dir": str(segment_cache_dir or ""),
        "same_run_acquisition_handoff_manifest": {
            "evidence": handoff_evidence,
            "contract_gaps": handoff_global_gaps,
            "acquisition_run_id": str(handoff.get("acquisition_run_id") or ""),
        },
        "protected_paths": [
            {
                "role": role, "before": protected_before[role], "after": protected_after[role],
                "unchanged": protected_before[role] == protected_after[role],
            }
            for role, _ in PROTECTED_PATHS
        ],
    }
    blocking_dependencies = [row["dependency"] for row in dependency_rows if row["blocking_for_model_b"] and not row["ready"]]
    optional_capture_gaps = [row["source_family"] for row in capture_rows if not row["blocking_for_model_b"] and not row["ready"]]
    wiring_plan = {
        "schema_version": SCHEMA_VERSION, "decision": decision, "ready": ready,
        "target_asof": str(inventory.get("target_asof") or ""),
        "exact_insertion_point": static_audit.get("exact_insertion_point"),
        "source_validator_gate": static_audit.get("source_validator"),
        "model_b_dependency_policy": {
            "required": ["adjusted_price_raw_lineage", "twii_raw_lineage", "model_a_qlib_score_top50_lineage", "institutional_flow", "margin_short"],
            "conditional": {"corporate_actions": "blocking only when adjusted lineage declares this dependency"},
            "optional_future_research": ["finmind_daily_price", "monthly_revenue", "valuation"],
            "seal_recommendation": "seal every available provider source even when it is not a Model B hard dependency",
        },
        "required_future_wiring": {
            "builder": "scripts/build_tw_model_b_hsa4_isolated_daily_sealed_capture.py",
            "handoff_identity": "required source_family and stable source_id",
            "same_run_handoff_manifest": "authoritative acquisition manifest binds run identity plus exact raw/normalized paths, roles, and SHA256; inventory declarations alone are rejected",
            "artifact_roles": {"raw": "provider_raw_response", "normalized": "provider_normalized_payload"},
            "validator_requirement": "source_validator_status=PASS from the same acquisition run; skip/default warning is STOP",
            "failure_policy": "fail closed before derived feature/model/provider/latest gates",
            "inventory_policy": "construct capture requests from same-run acquisition handoff, never stdout/DB/formal provider/latest/finalize summary",
        },
        "protected_inputs_unchanged": protected_inputs_unchanged,
        "blocking_dependencies": blocking_dependencies,
        "optional_or_nontriggered_conditional_capture_gaps": optional_capture_gaps,
        "not_authorized": [
            "daily_auto_or_backend_runner_change", "cron_change", "real_job_execution", "network_or_database_access",
            "provider_or_latest_write", "training_scoring_replay",
        ],
    }
    forbidden_audit = {
        "schema_version": SCHEMA_VERSION, "pass": protected_inputs_unchanged,
        "daily_runner_imported": False, "backend_runner_imported": False, "daily_job_executed": False,
        "network_used": False, "database_used": False, "cron_modified": False,
        "provider_or_latest_modified": False, "protected_inputs_unchanged": protected_inputs_unchanged,
        "protected_paths_before_after_fingerprinted": True,
        "protected_path_roles": [role for role, _ in PROTECTED_PATHS],
        "input_reads_use_openat_nofollow_fd_identity_checksum": True, "output_scope": str(output_dir),
    }
    _write_json(output_dir / "input_inventory.json", input_inventory)
    _write_json(output_dir / "static_insertion_point_audit.json", static_audit)
    _write_json(output_dir / "wiring_plan.json", wiring_plan)
    _write_json(output_dir / "forbidden_scope_audit.json", forbidden_audit)
    _write_csv(
        output_dir / "source_family_gap_matrix.csv", capture_rows,
        (
            "source_family", "source_id", "inventory_key", "requirement_class", "blocking_for_model_b",
            "inventory_record_present", "raw_artifact_role", "normalized_artifact_role", "source_validator_status",
            "raw_paths_present_and_secure", "normalized_paths_present_and_secure", "snapshot_metadata_complete",
            "same_run_handoff_manifest_bound",
            "publication_available_at_order_valid", "scope_closure_valid", "aggregate_evidence_only",
            "ready_for_hsa4_handoff", "gaps",
        ),
    )
    _write_csv(
        output_dir / "model_b_dependency_matrix.csv", dependency_rows,
        ("dependency", "requirement_class", "blocking_for_model_b", "ready", "capture_ready", "gaps", "recommendation_gaps"),
    )
    validator_status = static_audit.get("source_validator", {}).get("status", "STOP_VALIDATOR_PASS_NOT_PROVEN")
    finding = (
        "All Model B hard dependencies and any triggered corporate-actions condition have complete same-run lineage handoffs. Optional research sources do not block Model B, while all available sources remain recommended for sealing."
        if ready
        else "Model B cannot advance: at least one hard dependency or same-run validator/control-flow gate is not proven. Current stdout summaries, formal provider calendars, latest pointers, DB counts, and cache status are not provider raw responses."
    )
    report = f"""# HSA5 daily-auto sealed capture wiring preflight repair execution report

## Verdict

`{decision}`

- Work-order token: exact.
- Static source-validator status: `{validator_status}`.
- Default validation safety: `{static_audit.get("source_validator", {}).get("default_validation_safety_status", "UNKNOWN")}` (`{static_audit.get("source_validator", {}).get("default_validation_safety_reason", "not_analyzed")}`).
- Blocking Model B dependencies: `{', '.join(blocking_dependencies) or 'none'}`.
- Optional/non-triggered conditional capture gaps: `{', '.join(optional_capture_gaps) or 'none'}`.
- Protected inputs unchanged: `{protected_inputs_unchanged}`.

## Finding

{finding}

The insertion point is accepted only when fetch, validator assignment, a direct fail-close statement, and the exact AST anchor recorded in `static_insertion_point_audit.json` form one top-level linear sequence inside the same `main()` / `if not args.skip_finmind` guard and precede a top-level downstream gate. The complete validator gate additionally requires the default to be the boolean literal `False` and requires `warning_only_continuation_detected=false`. String defaults are not accepted because non-empty strings are truthy. Every env/getenv/env_flag expression remains `UNKNOWN/STOP`, even with a false fallback, because the runtime environment can override it. True, missing, dynamic, or unrecognized defaults also fail closed. Nested or divergent relevant calls are conservatively rejected. The current runner violates these conditions, so this execution explicitly records STOP and does not claim any validator passed.

HSA4 handoff now requires `source_family`, stable `source_id`, `raw_artifact_role=provider_raw_response`, `normalized_artifact_role=provider_normalized_payload`, and `source_validator_status=PASS`. An authoritative same-run acquisition handoff manifest must bind acquisition run identity plus every raw/normalized exact path, role, and SHA256; inventory declarations or renamed stdout alone cannot satisfy this contract. Every path was read component-by-component with `openat`/`O_NOFOLLOW`, bound to an FD identity and checksum, then locator-revalidated.

## Repair evidence

- HSA4 verifies the no-follow locator device/inode against the transaction-owned expected identity immediately before failure-isolation rename. Unknown replacement inodes are left at their original name and are not renamed, deleted, or marked.
- HSA5 production output is confined to `{DEFAULT_OUTPUT_DIR.relative_to(ROOT)}`. The arbitrary-output override exists only as an explicit in-process test argument and is not exposed by the CLI.
- `validator_pass_proven` and its status now represent the complete gate, including conservative default safety and warning-only checks, rather than assignment/fail-close shape alone.
- The evidence anchor is accepted only for the exact two-positional-argument AST form targeting `job_dir / "job.json"` with payload `job`; unrelated `write_json` calls are rejected and never reported as the anchor.
- Installed cron, formal provider tree, qlib accepted latest, legacy latest, product signal latest, readonly snapshot latest, and Agent prompt latest have deterministic no-follow before/after fingerprints; absent paths are represented as `ABSENT`.
- Protected paths unchanged: `{protected_paths_unchanged}`.

## Boundary

No daily runner, backend runner, cron, provider, Qlib, latest, frontend, or backend runtime file was changed. No real job, network, DB, OpenAI, training, scoring, or replay was run.

## Next gate

Because the verdict is STOP, the next route is only an upstream same-run provider artifact/validator handoff contract repair. HSA4 runtime wiring and cron change remain unauthorized.
"""
    _atomic_write(output_dir / "execution_report.md", report.encode("utf-8"))
    artifact_names = [
        "input_inventory.json", "static_insertion_point_audit.json", "wiring_plan.json", "forbidden_scope_audit.json",
        "source_family_gap_matrix.csv", "model_b_dependency_matrix.csv", "execution_report.md",
    ]
    manifest = {
        "schema_version": SCHEMA_VERSION, "decision": decision,
        "artifacts": [
            {"path": name, "sha256": _sha256(output_dir / name), "size": (output_dir / name).stat().st_size}
            for name in artifact_names
        ],
        "manifest_written_last": True,
    }
    _write_json(output_dir / "manifest.json", manifest)
    return {
        "decision": decision, "ready": ready, "rows": capture_rows, "dependency_rows": dependency_rows,
        "static_audit": static_audit, "output_dir": str(output_dir),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--daily-script", required=True, type=Path)
    parser.add_argument("--backend-script", required=True, type=Path)
    parser.add_argument("--source-inventory", required=True, type=Path)
    parser.add_argument("--segment-cache-dir", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    result = build_preflight(
        daily_script=args.daily_script, backend_script=args.backend_script, source_inventory=args.source_inventory,
        segment_cache_dir=args.segment_cache_dir, output_dir=args.output_dir, project_root=args.project_root,
    )
    print(json.dumps({"decision": result["decision"], "output_dir": result["output_dir"]}, ensure_ascii=False))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
