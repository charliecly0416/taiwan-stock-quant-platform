#!/usr/bin/env python3
"""Contract-first Model B walk-forward runner.

MBOOS1 only authorizes preflight and synthetic orchestration tests.  The real
entry point deliberately has no accepted authorization id until MBOOS2 freezes
one, so it cannot read E2 samples or invoke a model backend in this phase.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import stat
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol, Sequence


ROOT = Path(__file__).resolve().parents[1]
REFREEZE_DIR = ROOT / "data_tw/experiments/existing_model_strategy_baseline_comparison/emsbc_shorter_common_window_refreeze_20260824"
FOLD_PLAN = REFREEZE_DIR / "eligible_fold_plan.csv"
REFREEZE_MANIFEST = REFREEZE_DIR / "refreeze_manifest.json"
MBOOS0_FOLD_PLAN = ROOT / "data_tw/experiments/model_b_full_window_pit_safe_oos/mboos0_20260824/fold_plan.csv"
MBOOS0_COVERAGE = ROOT / "data_tw/experiments/model_b_full_window_pit_safe_oos/mboos0_20260824/coverage_policy.json"
E2_SCHEMA = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_feature_schema.csv"
E2_MANIFEST = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_sample_manifest.json"
E3_MANIFEST = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_training_manifest.json"
REPAIR_OUT_DIR = ROOT / "data_tw/experiments/model_b_full_window_pit_safe_oos/mboos1_r2_final_install_swap_rollback_20260824"
OUT_DIR = REPAIR_OUT_DIR

EXPECTED_FOLD_PLAN_SHA256 = "7705df8906a8180f475bd1bfee96a1defad7845acb61c93b75c39a25de44843f"
EXPECTED_MBOOS0_FOLD_PLAN_SHA256 = "605dc731cfcb267602069ebf8681acbd10cc6a066db715c9cfd512a4fa131c1a"
EXPECTED_FEATURE_HASH = "ab0c0faf2e26bca0cf4edce1f48b57dc8dd6c2b25831719dc6f9b4d497d463bf"
EXPECTED_LINEAGE = "E3"
EXPECTED_SCORE_SOURCE = "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_raw_oos_score_rank_2023_2026.csv"
LABEL_COLUMN = "relevance_10d_top_heavy"
FIXED_MODEL_CONFIG: dict[str, Any] = {
    "model_type": "LightGBM.LGBMRanker",
    "objective": "lambdarank",
    "metric": "ndcg",
    "boosting_type": "gbdt",
    "num_leaves": 31,
    "learning_rate": 0.03,
    "n_estimators": 120,
    "min_child_samples": 40,
    "random_state": 42,
    "n_jobs": 2,
    "verbose": -1,
}

# MBOOS2 must replace this with its independently reviewed exact id.  Empty is
# intentional: no invocation in MBOOS1 can authorize a real E2 read/fit/predict.
MBOOS2_EXACT_AUTHORIZATION_ID = ""

PROTECTED_8 = (
    "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron",
    "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    "data_tw/artifacts/agent_daily_prompt/latest.json",
    "configs/tw_product_artifact_registry.yaml",
    "configs/tw_modular_registry.yaml",
)

SCORE_PAYLOAD_FIELDS = (
    "date",
    "instrument",
    "fold_id",
    "train_start",
    "train_end",
    "validation_start",
    "validation_end",
    "model_sha256",
    "feature_artifact",
    "feature_hash",
    "qlib_artifact",
    "qlib_rank",
    "raw_score",
    "score_rank",
    "signal_asof",
    "available_at",
    "research_only",
    "synthetic",
)
FORBIDDEN_TOKENS = (
    "future_return",
    "future_excess_return",
    "forward_return",
    "label",
    "relevance",
    "realized_pnl",
    "realized_return",
    "private",
    "target_position",
    "target_weight",
    "order_qty",
    "broker",
)


class ContractError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


class InputMode(Enum):
    SYNTHETIC_TINY = "synthetic_tiny"
    STRICT_REAL = "strict_real"


class Backend(Protocol):
    def fit(self, rows: Sequence[Mapping[str, Any]], features: Sequence[str], label: str, groups: Sequence[int], config: Mapping[str, Any]) -> Any: ...
    def predict(self, model: Any, rows: Sequence[Mapping[str, Any]], features: Sequence[str]) -> Sequence[float]: ...
    def model_bytes(self, model: Any) -> bytes: ...


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8"))


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ContractError("MBOOS_E_JSON", f"object required: {path}")
    return value


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _absolute_lexical(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _ensure_directory_no_follow(path: Path) -> None:
    absolute = _absolute_lexical(path)
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        try:
            stat_result = os.lstat(current)
        except FileNotFoundError:
            os.mkdir(current, 0o755)
            stat_result = os.lstat(current)
        if not os.path.isdir(current) or os.path.islink(current):
            raise ContractError("MBOOS_E_OUTPUT_SYMLINK", str(current))


def _open_confined_parent(path: Path, allowed_root: Path) -> tuple[int, int, tuple[int, int], tuple[int, int], str]:
    allowed = _absolute_lexical(allowed_root)
    candidate = _absolute_lexical(path)
    try:
        relative = candidate.relative_to(allowed)
    except ValueError as error:
        raise ContractError("MBOOS_E_OUTPUT_ESCAPE", str(path)) from error
    if not relative.parts or relative.name in {"", ".", ".."}:
        raise ContractError("MBOOS_E_OUTPUT_ESCAPE", str(path))
    _ensure_directory_no_follow(allowed)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    root_fd = os.open(allowed, flags)
    root_stat = os.fstat(root_fd)
    root_identity = (root_stat.st_dev, root_stat.st_ino)
    parent_fd = os.dup(root_fd)
    try:
        for component in relative.parts[:-1]:
            if component in {"", ".", ".."}:
                raise ContractError("MBOOS_E_OUTPUT_ESCAPE", str(path))
            try:
                os.mkdir(component, 0o755, dir_fd=parent_fd)
            except FileExistsError:
                pass
            try:
                next_fd = os.open(component, flags, dir_fd=parent_fd)
            except OSError as error:
                raise ContractError("MBOOS_E_OUTPUT_SYMLINK", f"unsafe parent component: {component}") from error
            os.close(parent_fd)
            parent_fd = next_fd
        parent_stat = os.fstat(parent_fd)
        return root_fd, parent_fd, root_identity, (parent_stat.st_dev, parent_stat.st_ino), relative.name
    except BaseException:
        os.close(parent_fd)
        os.close(root_fd)
        raise


def _assert_bound_directory(path: Path, identity: tuple[int, int], code: str) -> None:
    try:
        stat_result = os.lstat(path)
    except FileNotFoundError as error:
        raise ContractError(code, f"directory replaced: {path}") from error
    if os.path.islink(path) or not os.path.isdir(path) or (stat_result.st_dev, stat_result.st_ino) != identity:
        raise ContractError(code, f"directory identity changed: {path}")


def _entry_identity(name: str, parent_fd: int) -> tuple[int, int, int, int]:
    value = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    return value.st_dev, value.st_ino, value.st_size, value.st_mode


def _unlink_bound(name: str, parent_fd: int, *, missing_ok: bool = True) -> None:
    try:
        os.unlink(name, dir_fd=parent_fd)
    except FileNotFoundError:
        if not missing_ok:
            raise


def _rollback_atomic_install(
    *,
    parent_fd: int,
    name: str,
    temporary: str,
    backup: str | None,
    candidate_identity: tuple[int, int, int, int],
    before_identity: tuple[int, int, int, int] | None,
    before_sha256: str | None,
) -> None:
    cleanup_error: BaseException | None = None
    try:
        try:
            installed_identity = _entry_identity(name, parent_fd)
        except FileNotFoundError:
            installed_identity = None
        if installed_identity == candidate_identity:
            _unlink_bound(name, parent_fd, missing_ok=False)
        elif installed_identity is not None and installed_identity != before_identity:
            raise ContractError("MBOOS_E_OUTPUT_ROLLBACK_TAINT", "final target identity is neither candidate nor before-state")

        if before_identity is not None:
            if backup is None:
                raise ContractError("MBOOS_E_OUTPUT_ROLLBACK_TAINT", "before-state backup is unavailable")
            try:
                current_identity = _entry_identity(name, parent_fd)
            except FileNotFoundError:
                current_identity = None
            if current_identity is None:
                os.replace(backup, name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
                backup = None
            elif current_identity != before_identity:
                raise ContractError("MBOOS_E_OUTPUT_ROLLBACK_TAINT", "before-state target cannot be restored")
        _unlink_bound(temporary, parent_fd)
        if backup is not None:
            _unlink_bound(backup, parent_fd)
        os.fsync(parent_fd)

        try:
            restored_identity = _entry_identity(name, parent_fd)
        except FileNotFoundError:
            restored_identity = None
        if before_identity is None:
            if restored_identity is not None:
                raise ContractError("MBOOS_E_OUTPUT_ROLLBACK_TAINT", "candidate remains after rollback")
        else:
            if restored_identity != before_identity:
                raise ContractError("MBOOS_E_OUTPUT_ROLLBACK_TAINT", "restored target identity mismatch")
            restored_fd = os.open(name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=parent_fd)
            try:
                restored = b""
                while True:
                    chunk = os.read(restored_fd, 1024 * 1024)
                    if not chunk:
                        break
                    restored += chunk
            finally:
                os.close(restored_fd)
            if sha256_bytes(restored) != before_sha256:
                raise ContractError("MBOOS_E_OUTPUT_ROLLBACK_TAINT", "restored target checksum mismatch")
    except BaseException as error:
        cleanup_error = error
        # A transient cleanup failure must not preserve candidate bytes. Retry
        # the bound transaction once before returning the terminal taint error.
        try:
            try:
                retry_identity = _entry_identity(name, parent_fd)
            except FileNotFoundError:
                retry_identity = None
            if retry_identity == candidate_identity:
                _unlink_bound(name, parent_fd, missing_ok=False)
                retry_identity = None
            if before_identity is not None and retry_identity is None and backup is not None:
                os.replace(backup, name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
                backup = None
            _unlink_bound(temporary, parent_fd)
            if backup is not None:
                _unlink_bound(backup, parent_fd)
            os.fsync(parent_fd)
        except BaseException:
            pass
        try:
            os.fsync(parent_fd)
        except OSError:
            pass
    if cleanup_error is not None:
        raise ContractError("MBOOS_E_OUTPUT_ROLLBACK_TAINT", f"identity-bound rollback failed: {cleanup_error}") from cleanup_error


def atomic_write(path: Path, payload: bytes, *, allowed_root: Path) -> None:
    root_fd, parent_fd, root_identity, parent_identity, name = _open_confined_parent(path, allowed_root)
    allowed = _absolute_lexical(allowed_root)
    parent = _absolute_lexical(path).parent
    try:
        try:
            target_stat = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            target_stat = None
        if target_stat is not None and not stat.S_ISREG(target_stat.st_mode):
            code = "MBOOS_E_OUTPUT_SYMLINK" if stat.S_ISLNK(target_stat.st_mode) else "MBOOS_E_OUTPUT_TARGET_TYPE"
            raise ContractError(code, str(path))
        temporary = f".{name}.{os.getpid()}.{os.urandom(8).hex()}.stage"
        backup = f".{name}.{os.getpid()}.{os.urandom(8).hex()}.rollback" if target_stat is not None else None
        before_identity = None if target_stat is None else (target_stat.st_dev, target_stat.st_ino, target_stat.st_size, target_stat.st_mode)
        before_sha256 = None
        if backup is not None:
            os.link(name, backup, src_dir_fd=parent_fd, dst_dir_fd=parent_fd, follow_symlinks=False)
            before_fd = os.open(backup, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=parent_fd)
            try:
                before_payload = b""
                while True:
                    chunk = os.read(before_fd, 1024 * 1024)
                    if not chunk:
                        break
                    before_payload += chunk
            finally:
                os.close(before_fd)
            before_sha256 = sha256_bytes(before_payload)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(temporary, flags, 0o600, dir_fd=parent_fd)
    except BaseException:
        os.close(parent_fd)
        os.close(root_fd)
        raise
    try:
        with os.fdopen(fd, "wb") as handle:
            os.fchmod(handle.fileno(), 0o644)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        candidate_identity = _entry_identity(temporary, parent_fd)
        _assert_bound_directory(allowed, root_identity, "MBOOS_E_OUTPUT_ROOT_REPLACED")
        _assert_bound_directory(parent, parent_identity, "MBOOS_E_OUTPUT_PARENT_REPLACED")
        os.replace(temporary, name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        try:
            _assert_bound_directory(allowed, root_identity, "MBOOS_E_OUTPUT_ROOT_REPLACED")
            _assert_bound_directory(parent, parent_identity, "MBOOS_E_OUTPUT_PARENT_REPLACED")
            if _entry_identity(name, parent_fd) != candidate_identity:
                raise ContractError("MBOOS_E_OUTPUT_FINAL_IDENTITY", "installed target is not the staged candidate")
        except BaseException:
            _rollback_atomic_install(
                parent_fd=parent_fd,
                name=name,
                temporary=temporary,
                backup=backup,
                candidate_identity=candidate_identity,
                before_identity=before_identity,
                before_sha256=before_sha256,
            )
            backup = None
            raise
        os.fsync(parent_fd)
        if backup is not None:
            _unlink_bound(backup, parent_fd, missing_ok=False)
            backup = None
            os.fsync(parent_fd)
    except BaseException:
        try:
            _unlink_bound(temporary, parent_fd)
        except FileNotFoundError:
            pass
        if 'backup' in locals() and backup is not None:
            try:
                _unlink_bound(backup, parent_fd)
            except FileNotFoundError:
                pass
        raise
    finally:
        os.close(parent_fd)
        os.close(root_fd)


def atomic_json(path: Path, value: Any, *, allowed_root: Path) -> None:
    atomic_write(path, (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode(), allowed_root=allowed_root)


def atomic_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str], *, allowed_root: Path) -> None:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(fields), extrasaction="raise", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    atomic_write(path, buffer.getvalue().encode("utf-8"), allowed_root=allowed_root)


def protected_fingerprints() -> dict[str, str]:
    return {relative: sha256_file(ROOT / relative) for relative in PROTECTED_8}


def _parse_day(value: Any, field: str) -> date:
    text = str(value).strip()[:10]
    try:
        return date.fromisoformat(text)
    except ValueError as error:
        raise ContractError("MBOOS_E_DATE", f"{field}={value!r}") from error


def _strict_true(value: Any, field: str) -> None:
    if value not in (True, "true", "True", "1", 1):
        raise ContractError("MBOOS_E_LINEAGE", f"{field} must be true")


def feature_contract() -> tuple[list[str], str]:
    rows = load_csv(E2_SCHEMA)
    if len(rows) != 78 or [int(row["order"]) for row in rows] != list(range(78)):
        raise ContractError("MBOOS_E_FEATURE_COUNT", "ordered feature whitelist must contain exactly 78 rows")
    if any(row["status"] != "training_feature" for row in rows):
        raise ContractError("MBOOS_E_FEATURE_STATUS", "non-training feature in whitelist")
    fields = ["order", "feature", "family", "status"]
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows([{key: row[key] for key in fields} for row in rows])
    semantic_hash = sha256_bytes(buffer.getvalue().encode("utf-8"))
    if semantic_hash != EXPECTED_FEATURE_HASH:
        raise ContractError("MBOOS_E_FEATURE_HASH", semantic_hash)
    names = [row["feature"] for row in rows]
    if len(set(names)) != 78:
        raise ContractError("MBOOS_E_FEATURE_DUPLICATE", "duplicate feature name")
    return names, semantic_hash


def validate_frozen_config(override: Mapping[str, Any] | None = None) -> str:
    e2 = load_json(E2_MANIFEST)
    e3 = load_json(E3_MANIFEST)
    refreeze = load_json(REFREEZE_MANIFEST)
    candidates = (
        e2.get("frozen_contract", {}).get("model_family_params_for_e3"),
        e3.get("model_config"),
        refreeze.get("model_b", {}).get("fixed_parameters"),
    )
    if any(value != FIXED_MODEL_CONFIG for value in candidates):
        raise ContractError("MBOOS_E_MODEL_CONFIG", "E2/E3/refreeze config drift")
    if override is not None and dict(override) != FIXED_MODEL_CONFIG:
        raise ContractError("MBOOS_E_PARAMETER_OVERRIDE", "parameter override/search is forbidden")
    if e3.get("feature_hash") != EXPECTED_FEATURE_HASH or e3.get("feature_count") != 78:
        raise ContractError("MBOOS_E_FEATURE_HASH", "E3 feature identity drift")
    if e2.get("feature_schema", {}).get("feature_hash") != EXPECTED_FEATURE_HASH:
        raise ContractError("MBOOS_E_FEATURE_HASH", "E2 feature identity drift")
    if refreeze.get("model_b", {}).get("lineage") != EXPECTED_LINEAGE:
        raise ContractError("MBOOS_E_LINEAGE", "refreeze lineage drift")
    return canonical_sha256(FIXED_MODEL_CONFIG)


FOLD_FIELDS = (
    "fold_id", "score_start", "score_end", "score_dates", "score_rows", "score_eligible_rows",
    "fit_start", "fit_end", "fit_dates", "fit_rows", "validation_start", "validation_end",
    "validation_dates", "validation_rows", "label_maturity_cutoff", "purge_start", "purge_end",
    "purge_dates", "zero_overlap", "status",
)


def validate_fold_plan(path: Path = FOLD_PLAN) -> list[dict[str, str]]:
    if path == FOLD_PLAN and sha256_file(path) != EXPECTED_FOLD_PLAN_SHA256:
        raise ContractError("MBOOS_E_FOLD_HASH", "refrozen eligible plan changed")
    if sha256_file(MBOOS0_FOLD_PLAN) != EXPECTED_MBOOS0_FOLD_PLAN_SHA256:
        raise ContractError("MBOOS_E_FOLD_SOURCE_HASH", "MBOOS0 plan changed")
    rows = load_csv(path)
    source = {row["fold_id"]: row for row in load_csv(MBOOS0_FOLD_PLAN)}
    if len(rows) != 30 or [row["fold_id"] for row in rows] != [f"MBOOS_F{i:02d}" for i in range(12, 42)]:
        raise ContractError("MBOOS_E_FOLD_COUNT", "expected exact F12..F41 sequence")
    previous_fit_end: date | None = None
    previous_month: tuple[int, int] | None = None
    for row in rows:
        if tuple(row) != FOLD_FIELDS:
            raise ContractError("MBOOS_E_FOLD_SCHEMA", f"field drift in {row.get('fold_id')}")
        original = source.get(row["fold_id"])
        if original is None or any(row[key] != original[key] for key in FOLD_FIELDS if key != "status"):
            raise ContractError("MBOOS_E_FOLD_SOURCE_PARITY", row["fold_id"])
        if row["status"] != "ELIGIBLE" or row["zero_overlap"] != "true":
            raise ContractError("MBOOS_E_FOLD_STATUS", row["fold_id"])
        fit_start, fit_end = _parse_day(row["fit_start"], "fit_start"), _parse_day(row["fit_end"], "fit_end")
        val_start, val_end = _parse_day(row["validation_start"], "validation_start"), _parse_day(row["validation_end"], "validation_end")
        purge_start, purge_end = _parse_day(row["purge_start"], "purge_start"), _parse_day(row["purge_end"], "purge_end")
        score_start, score_end = _parse_day(row["score_start"], "score_start"), _parse_day(row["score_end"], "score_end")
        cutoff = _parse_day(row["label_maturity_cutoff"], "label_maturity_cutoff")
        if row["fit_start"] != "2023-01-03" or int(row["validation_dates"]) != 40 or int(row["purge_dates"]) != 10:
            raise ContractError("MBOOS_E_200_40_10", row["fold_id"])
        if int(row["fit_dates"]) + int(row["validation_dates"]) < 200:
            raise ContractError("MBOOS_E_MATURITY_MINIMUM", row["fold_id"])
        if not (fit_start <= fit_end < val_start <= val_end == cutoff < purge_start <= purge_end < score_start <= score_end):
            raise ContractError("MBOOS_E_OVERLAP", row["fold_id"])
        month = (score_start.year, score_start.month)
        if previous_month is not None:
            expected = (previous_month[0] + (1 if previous_month[1] == 12 else 0), 1 if previous_month[1] == 12 else previous_month[1] + 1)
            if month != expected:
                raise ContractError("MBOOS_E_MONTHLY_FOLD", row["fold_id"])
        if previous_fit_end is not None and fit_end <= previous_fit_end:
            raise ContractError("MBOOS_E_EXPANDING_WINDOW", row["fold_id"])
        previous_fit_end, previous_month = fit_end, month
    if rows[0]["score_start"] != "2023-12-01" or rows[-1]["score_end"] != "2026-05-07":
        raise ContractError("MBOOS_E_COMMON_WINDOW", "common window drift")
    return rows


def validate_input_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    features: Sequence[str],
    fold: Mapping[str, Any],
    split: str,
    trading_dates: Sequence[str],
    mode: InputMode,
) -> list[dict[str, Any]]:
    if split not in {"fit", "validation", "score"}:
        raise ContractError("MBOOS_E_SPLIT", split)
    if not rows:
        raise ContractError("MBOOS_E_EMPTY", split)
    required = {"date", "instrument", "qlib_rank", "institutional_flow_available_at", "margin_short_available_at", *features}
    if split != "score":
        required.add(LABEL_COLUMN)
    missing = required - set(rows[0])
    if missing:
        raise ContractError("MBOOS_E_REQUIRED_COLUMN", ",".join(sorted(missing)))
    if not isinstance(mode, InputMode):
        raise ContractError("MBOOS_E_INPUT_MODE", "explicit InputMode required")
    if mode is InputMode.SYNTHETIC_TINY:
        if not str(fold.get("fold_id", "")).startswith("MBOOS_SYNTHETIC"):
            raise ContractError("MBOOS_E_SYNTHETIC_MODE", "synthetic mode requires synthetic fold identity")
        expected_dates = set(fold.get("synthetic_expected_dates", {}).get(split, ()))
        if not expected_dates:
            raise ContractError("MBOOS_E_SYNTHETIC_MODE", f"missing explicit {split} date set")
    else:
        if str(fold.get("fold_id", "")).startswith("MBOOS_SYNTHETIC"):
            raise ContractError("MBOOS_E_SYNTHETIC_MODE", "synthetic fold cannot enter strict-real mode")
        expected_dates = {
            value for value in trading_dates
            if _parse_day(fold[f"{split}_start"], f"{split}_start") <= _parse_day(value, "calendar") <= _parse_day(fold[f"{split}_end"], f"{split}_end")
        }
        expected_group_count = int(fold[f"{split}_dates"])
        if len(expected_dates) != expected_group_count:
            raise ContractError("MBOOS_E_CALENDAR_CLOSURE", f"{split}: calendar={len(expected_dates)} fold={expected_group_count}")
    date_index = {value: index for index, value in enumerate(trading_dates)}
    keys: set[tuple[str, str]] = set()
    groups: Counter[str] = Counter()
    clean: list[dict[str, Any]] = []
    start = _parse_day(fold[f"{split}_start"] if split != "score" else fold["score_start"], "split_start")
    end = _parse_day(fold[f"{split}_end"] if split != "score" else fold["score_end"], "split_end")
    score_start = _parse_day(fold["score_start"], "score_start")
    cutoff = _parse_day(fold["label_maturity_cutoff"], "label_maturity_cutoff")
    for source in rows:
        row = dict(source)
        day_text = str(row["date"])[:10]
        day = _parse_day(day_text, "date")
        instrument = str(row["instrument"])
        if len(instrument) != 6 or not instrument.startswith("TW") or not instrument[2:].isdigit():
            raise ContractError("MBOOS_E_UNIVERSE", f"instrument={instrument!r}")
        if not (start <= day <= end):
            raise ContractError("MBOOS_E_SPLIT_RANGE", f"{split}:{day_text}")
        key = (day_text, instrument)
        if key in keys:
            raise ContractError("MBOOS_E_DUPLICATE_KEY", repr(key))
        keys.add(key)
        _strict_true(row.get("same_e1_frozen_qlib_score_source"), "same_e1_frozen_qlib_score_source")
        _strict_true(row.get("after_qlib_train_end"), "after_qlib_train_end")
        if row.get("score_source") != EXPECTED_SCORE_SOURCE:
            raise ContractError("MBOOS_E_LINEAGE", "wrong qlib artifact")
        for field in ("institutional_flow_available_at", "margin_short_available_at"):
            if row.get(field) in (None, ""):
                raise ContractError("MBOOS_E_AVAILABILITY_NULL", field)
            if _parse_day(row[field], field) > day:
                raise ContractError("MBOOS_E_AVAILABILITY_LATE", field)
        for feature in features:
            value = row.get(feature)
            try:
                numeric = float(value)
            except (TypeError, ValueError) as error:
                raise ContractError("MBOOS_E_FEATURE_NON_NUMERIC", feature) from error
            if not math.isfinite(numeric):
                raise ContractError("MBOOS_E_FEATURE_NON_FINITE", feature)
            row[feature] = numeric
        try:
            rank = int(row["qlib_rank"])
        except (TypeError, ValueError) as error:
            raise ContractError("MBOOS_E_QLIB_RANK", repr(row["qlib_rank"])) from error
        if rank < 1 or rank > 150:
            raise ContractError("MBOOS_E_UNIVERSE", f"qlib_rank={rank}")
        row["qlib_rank"] = rank
        if split != "score":
            if day_text not in date_index or date_index[day_text] + 10 >= len(trading_dates):
                raise ContractError("MBOOS_E_LABEL_MATURITY", day_text)
            label_available = _parse_day(trading_dates[date_index[day_text] + 10], "label_available")
            if label_available > cutoff or label_available >= score_start:
                raise ContractError("MBOOS_E_LABEL_MATURITY", day_text)
            if row.get(LABEL_COLUMN) in (None, ""):
                raise ContractError("MBOOS_E_LABEL_NULL", day_text)
        groups[day_text] += 1
        projected_fields = ["date", "instrument", "qlib_rank", *features]
        if split != "score":
            projected_fields.append(LABEL_COLUMN)
        clean.append({field: row[field] for field in projected_fields})
    if set(groups) != expected_dates:
        raise ContractError("MBOOS_E_DATE_SET_CLOSURE", f"{split}: missing={sorted(expected_dates - set(groups))} extra={sorted(set(groups) - expected_dates)}")
    if mode is InputMode.STRICT_REAL:
        expected_rows = int(fold[f"{split}_rows"])
        if len(clean) != expected_rows:
            raise ContractError("MBOOS_E_ROW_COUNT_CLOSURE", f"{split}: rows={len(clean)} fold={expected_rows}")
    by_day: dict[str, list[int]] = defaultdict(list)
    for row in clean:
        if row["qlib_rank"] <= 50:
            by_day[str(row["date"])[:10]].append(row["qlib_rank"])
    for day_text in groups:
        if sorted(by_day[day_text]) != list(range(1, 51)):
            raise ContractError("MBOOS_E_INCOMPLETE_TOP50", f"{split}:{day_text}")
    return sorted(clean, key=lambda row: (str(row["date"])[:10], str(row["instrument"])))


def validate_score_payload(
    rows: Sequence[Mapping[str, Any]],
    *,
    fold: Mapping[str, Any],
    expected_dates: Sequence[str],
    expected_model_sha256: str,
    synthetic: bool,
) -> None:
    keys: set[tuple[str, str]] = set()
    by_day: Counter[str] = Counter()
    ranks_by_day: dict[str, list[int]] = defaultdict(list)
    qlib_ranks_by_day: dict[str, list[int]] = defaultdict(list)
    if len(expected_model_sha256) != 64 or any(char not in "0123456789abcdef" for char in expected_model_sha256):
        raise ContractError("MBOOS_E_MODEL_IDENTITY", expected_model_sha256)
    for row in rows:
        if set(row) != set(SCORE_PAYLOAD_FIELDS):
            extra = set(row) - set(SCORE_PAYLOAD_FIELDS)
            if any(any(token in field.lower() for token in FORBIDDEN_TOKENS) for field in extra):
                raise ContractError("MBOOS_E_FORBIDDEN_PAYLOAD_FIELD", ",".join(sorted(extra)))
            raise ContractError("MBOOS_E_PAYLOAD_ALLOWLIST", ",".join(sorted(set(row) ^ set(SCORE_PAYLOAD_FIELDS))))
        key = (str(row["date"]), str(row["instrument"]))
        if key in keys:
            raise ContractError("MBOOS_E_DUPLICATE_KEY", repr(key))
        keys.add(key)
        day_text = str(row["date"])
        by_day[day_text] += 1
        if row["research_only"] is not True or row["synthetic"] is not synthetic:
            raise ContractError("MBOOS_E_SYNTHETIC_MARKER", repr(key))
        if day_text != str(row["signal_asof"]):
            raise ContractError("MBOOS_E_SIGNAL_DATE", repr(key))
        if not (_parse_day(fold["score_start"], "score_start") <= _parse_day(day_text, "date") <= _parse_day(fold["score_end"], "score_end")):
            raise ContractError("MBOOS_E_SPLIT_RANGE", repr(key))
        expected_identity = {
            "fold_id": fold["fold_id"], "train_start": fold["fit_start"], "train_end": fold["fit_end"],
            "validation_start": fold["validation_start"], "validation_end": fold["validation_end"],
            "feature_artifact": str(E2_SCHEMA.relative_to(ROOT)), "feature_hash": EXPECTED_FEATURE_HASH,
            "qlib_artifact": EXPECTED_SCORE_SOURCE, "model_sha256": expected_model_sha256,
        }
        if any(row[field] != value for field, value in expected_identity.items()):
            raise ContractError("MBOOS_E_PAYLOAD_IDENTITY", repr(key))
        try:
            raw_score = float(row["raw_score"])
            score_rank = int(row["score_rank"])
            qlib_rank = int(row["qlib_rank"])
        except (TypeError, ValueError) as error:
            raise ContractError("MBOOS_E_PAYLOAD_NUMERIC", repr(key)) from error
        if not math.isfinite(raw_score):
            raise ContractError("MBOOS_E_PREDICTION", repr(key))
        ranks_by_day[day_text].append(score_rank)
        qlib_ranks_by_day[day_text].append(qlib_rank)
        if _parse_day(row["available_at"], "available_at") > _parse_day(row["signal_asof"], "signal_asof"):
            raise ContractError("MBOOS_E_AVAILABILITY_LATE", repr(key))
    if set(by_day) != set(expected_dates):
        raise ContractError("MBOOS_E_DATE_SET_CLOSURE", "score payload date set")
    if any(count != 50 for count in by_day.values()):
        raise ContractError("MBOOS_E_INCOMPLETE_TOP50", repr(dict(by_day)))
    for day_text in by_day:
        if sorted(ranks_by_day[day_text]) != list(range(1, 51)):
            raise ContractError("MBOOS_E_SCORE_RANK", day_text)
        if sorted(qlib_ranks_by_day[day_text]) != list(range(1, 51)):
            raise ContractError("MBOOS_E_QLIB_RANK", day_text)


def grouped_sizes(rows: Sequence[Mapping[str, Any]]) -> list[int]:
    counts = Counter(str(row["date"])[:10] for row in rows)
    return [counts[key] for key in sorted(counts)]


def project_backend_rows(
    rows: Sequence[Mapping[str, Any]], *, features: Sequence[str], include_label: bool
) -> list[dict[str, Any]]:
    fields = ["date", "instrument", *features]
    if include_label:
        fields.append(LABEL_COLUMN)
    return [{field: row[field] for field in fields} for row in rows]


def run_synthetic_fold(
    *,
    fold: Mapping[str, Any],
    fit_rows: Sequence[Mapping[str, Any]],
    validation_rows: Sequence[Mapping[str, Any]],
    score_rows: Sequence[Mapping[str, Any]],
    trading_dates: Sequence[str],
    features: Sequence[str],
    backend: Backend,
) -> list[dict[str, Any]]:
    fit = validate_input_rows(fit_rows, features=features, fold=fold, split="fit", trading_dates=trading_dates, mode=InputMode.SYNTHETIC_TINY)
    validation = validate_input_rows(validation_rows, features=features, fold=fold, split="validation", trading_dates=trading_dates, mode=InputMode.SYNTHETIC_TINY)
    score = validate_input_rows(score_rows, features=features, fold=fold, split="score", trading_dates=trading_dates, mode=InputMode.SYNTHETIC_TINY)
    if {(r["date"], r["instrument"]) for r in fit} & {(r["date"], r["instrument"]) for r in validation + score}:
        raise ContractError("MBOOS_E_OVERLAP", "row identity overlap")
    fit_backend_rows = project_backend_rows(fit, features=features, include_label=True)
    score_backend_rows = project_backend_rows(score, features=features, include_label=False)
    model = backend.fit(fit_backend_rows, features, LABEL_COLUMN, grouped_sizes(fit), FIXED_MODEL_CONFIG)
    predictions = list(backend.predict(model, score_backend_rows, features))
    if len(predictions) != len(score) or any(not math.isfinite(float(value)) for value in predictions):
        raise ContractError("MBOOS_E_PREDICTION", "invalid prediction vector")
    model_sha = sha256_bytes(backend.model_bytes(model))
    by_day: dict[str, list[tuple[dict[str, Any], float]]] = defaultdict(list)
    for row, prediction in zip(score, predictions):
        if int(row["qlib_rank"]) <= 50:
            by_day[str(row["date"])[:10]].append((row, float(prediction)))
    output: list[dict[str, Any]] = []
    for day_text in sorted(by_day):
        ranked = sorted(by_day[day_text], key=lambda item: (-item[1], int(item[0]["qlib_rank"]), str(item[0]["instrument"])))
        if len(ranked) != 50:
            raise ContractError("MBOOS_E_INCOMPLETE_TOP50", day_text)
        for rank, (row, prediction) in enumerate(ranked, 1):
            output.append({
                "date": day_text,
                "instrument": str(row["instrument"]),
                "fold_id": fold["fold_id"],
                "train_start": fold["fit_start"],
                "train_end": fold["fit_end"],
                "validation_start": fold["validation_start"],
                "validation_end": fold["validation_end"],
                "model_sha256": model_sha,
                "feature_artifact": str(E2_SCHEMA.relative_to(ROOT)),
                "feature_hash": EXPECTED_FEATURE_HASH,
                "qlib_artifact": EXPECTED_SCORE_SOURCE,
                "qlib_rank": int(row["qlib_rank"]),
                "raw_score": prediction,
                "score_rank": rank,
                "signal_asof": day_text,
                "available_at": day_text,
                "research_only": True,
                "synthetic": True,
            })
    validate_score_payload(output, fold=fold, expected_dates=fold["synthetic_expected_dates"]["score"], expected_model_sha256=model_sha, synthetic=True)
    return output


def require_real_authorization(authorization_id: str | None) -> None:
    if not MBOOS2_EXACT_AUTHORIZATION_ID or authorization_id != MBOOS2_EXACT_AUTHORIZATION_ID:
        raise ContractError("MBOOS_E_REAL_AUTHORIZATION", "MBOOS2 exact authorization is not installed")


def preflight(output_dir: Path = OUT_DIR) -> dict[str, Any]:
    if _absolute_lexical(output_dir) != _absolute_lexical(OUT_DIR):
        raise ContractError("MBOOS_E_OUTPUT_ESCAPE", "CLI preflight output must be the exact MBOOS1 evidence directory")
    before = protected_fingerprints()
    folds = validate_fold_plan()
    features, feature_hash = feature_contract()
    config_hash = validate_frozen_config()
    coverage = load_json(MBOOS0_COVERAGE)
    if coverage.get("minimum_mature_training_groups") != 200 or coverage.get("validation", {}).get("groups") != 40:
        raise ContractError("MBOOS_E_200_40_10", "coverage policy drift")
    if coverage.get("label_policy", {}).get("horizon_trading_days") != 10 or coverage.get("label_policy", {}).get("purge_trading_dates_immediately_before_fold") != 10:
        raise ContractError("MBOOS_E_200_40_10", "label/purge policy drift")
    after = protected_fingerprints()
    if before != after:
        raise ContractError("MBOOS_E_PROTECTED_CHANGED", "protected files changed during preflight")
    created_at = utc_now()
    fold_audit = [{
        "fold_id": row["fold_id"],
        "score_start": row["score_start"],
        "score_end": row["score_end"],
        "mature_groups": int(row["fit_dates"]) + int(row["validation_dates"]),
        "fit_groups": int(row["fit_dates"]),
        "validation_groups": int(row["validation_dates"]),
        "purge_dates": int(row["purge_dates"]),
        "zero_overlap": True,
        "source_parity": True,
        "status": "PASS",
    } for row in folds]
    manifest = {
        "schema_version": "mboos1_r2.preflight.v1",
        "created_at": created_at,
        "status": "IMPLEMENTATION_COMPLETE_PENDING_INDEPENDENT_REVIEW",
        "mode": "preflight_no_real_input_read_no_fit_no_predict",
        "common_window": [folds[0]["score_start"], folds[-1]["score_end"]],
        "eligible_folds": len(folds),
        "feature_count": len(features),
        "feature_hash": feature_hash,
        "model_config_sha256": config_hash,
        "model_config": FIXED_MODEL_CONFIG,
        "real_authorization_installed": False,
        "real_e2_payload_read": False,
        "training_performed": False,
        "scoring_performed": False,
        "research_metrics_generated": False,
        "output_allowlist": list(SCORE_PAYLOAD_FIELDS),
        "protected_before": before,
        "protected_after": after,
    }
    synthetic = {
        "schema_version": "mboos1_r2.synthetic_test_evidence.v1",
        "synthetic_only": True,
        "fake_backend_allowed": True,
        "real_research_metrics": False,
        "dedicated_test_command": "python -m pytest -q tests/unit/test_tw_policy_model_b_full_window_oos.py",
        "covered_contracts": ["strict_real_date_group_row_top50_closure", "synthetic_mode_isolation", "backend_exact_projection", "payload_identity", "30_fold", "200_40_10", "maturity", "availability", "fixed_e3", "78_features", "deterministic_tie", "payload_allowlist", "fail_closed", "no_follow_atomic_output", "fd_bound_final_install", "identity_bound_swap_rollback", "terminal_cleanup_taint"],
    }
    forbidden = {
        "schema_version": "mboos1_r2.forbidden_scope_audit.v1",
        "status": "PASS",
        "real_e2_payload_read": False,
        "training_performed": False,
        "scoring_performed": False,
        "replay_performed": False,
        "order_intent_created": False,
        "network_db_openai_accessed": False,
        "provider_qlib_latest_cron_registry_modified": False,
        "frontend_backend_agent_modified": False,
        "protected_8_unchanged": before == after,
        "protected_before_after": before,
    }
    atomic_json(output_dir / "preflight_manifest.json", manifest, allowed_root=output_dir)
    atomic_csv(output_dir / "fold_contract_audit.csv", fold_audit, tuple(fold_audit[0]), allowed_root=output_dir)
    atomic_json(output_dir / "synthetic_test_evidence.json", synthetic, allowed_root=output_dir)
    atomic_json(output_dir / "forbidden_scope_audit.json", forbidden, allowed_root=output_dir)
    report = "\n".join((
        "# MBOOS1_R2 Final Install Swap Rollback Closure Evidence",
        "",
        f"Generated: `{created_at}`",
        "",
        "## Result",
        "",
        "`IMPLEMENTATION_COMPLETE_PENDING_INDEPENDENT_REVIEW`",
        "",
        "- Validated the exact 30-fold F12-F41 plan and source parity.",
        "- Validated expanding monthly 200/40/10 maturity and zero-overlap contract.",
        "- Validated the fixed E3 configuration and ordered 78-feature semantic hash.",
        "- The real-run gate rejected all execution because no MBOOS2 exact authorization is installed.",
        "- No real E2 sample was read; no fit, predict, replay, OrderIntent or research metric ran.",
        "- Atomic outputs are confined to this evidence directory; protected 8 are unchanged.",
        "",
    ))
    atomic_write(output_dir / "execution_report.md", report.encode("utf-8"), allowed_root=output_dir)
    return manifest


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--preflight", action="store_true", help="validate frozen contracts and write MBOOS1 evidence (default)")
    mode.add_argument("--execute-real", action="store_true", help="future MBOOS2-only mode")
    parser.add_argument("--authorization-id")
    parser.add_argument("--model-parameter-override", help="always rejected unless byte-for-byte equal to frozen config")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.execute_real:
        # This is intentionally the first operation in real mode.  In
        # particular, no E2 path is stat'ed or opened before this gate.
        require_real_authorization(args.authorization_id)
        raise ContractError("MBOOS_E_REAL_NOT_IMPLEMENTED", "MBOOS2 execution work order is required")
    if args.model_parameter_override:
        try:
            override = json.loads(args.model_parameter_override)
        except json.JSONDecodeError as error:
            raise ContractError("MBOOS_E_PARAMETER_OVERRIDE", "invalid JSON") from error
        validate_frozen_config(override)
    result = preflight()
    print(json.dumps({"ok": True, "status": result["status"], "output_dir": str(OUT_DIR.relative_to(ROOT))}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as error:
        print(json.dumps({"ok": False, "code": error.code, "error": str(error)}, indent=2))
        raise SystemExit(2)
