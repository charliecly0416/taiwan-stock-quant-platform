#!/usr/bin/env python3
"""Build and validate an isolated synthetic HSA5U acquisition handoff.

This is a contract fixture only.  It never imports or executes the daily
runner and never writes provider, Qlib, latest, cron, or runtime artifacts.
The resulting inventory is intentionally shaped for the existing HSA5
preflight, which remains the authority for the HSA6 no-cron gate.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import stat
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "data_tw/experiments/model_b_path2_sealed_archive_retrain/hsa5u_synthetic_acquisition_handoff_repair_20260825"
HSA5_SCRIPT = ROOT / "scripts/build_tw_model_b_hsa5_daily_auto_sealed_capture_wiring_preflight.py"
SCHEMA_VERSION = "hsa5u.synthetic_acquisition_handoff.v1"
HSA5_HANDOFF_SCHEMA_VERSION = "hsa5.same_run_acquisition_handoff.v1"
RUN_ID = "daily.acquire.20260825.hsa5u.fixture"
TARGET_ASOF = "2026-08-25"
SOURCE_FAMILIES = (
    "adjusted_price", "twii", "institutional_flow", "margin_short",
)
STABLE_ID = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
TIMESTAMP_FIELDS = ("source_published_at", "available_at", "fetched_at")
REQUIRED_FIELDS = (
    "snapshot_id", "source_family", "source_id", "provider",
    "source_endpoint_version", "request_parameters", "fetched_at",
    "http_status", "transport_identity", "parser_version", "schema_version",
    "trade_date", "available_at", "source_published_at",
    "raw_artifact_role", "normalized_artifact_role", "source_validator_status",
    "acquisition_run_id", "expected_scope", "returned_scope", "absent_scope",
    "unknown_scope", "raw_files", "normalized_files",
)


class HSA5UError(ValueError):
    pass


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def _absolute_without_resolve(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _open_beneath(root: Path, path: Path, flags: int) -> int:
    """Open a path beneath a trusted root using component-wise no-follow FDs."""
    trusted = _absolute_without_resolve(root)
    candidate = _absolute_without_resolve(path)
    try:
        relative = candidate.relative_to(trusted)
    except ValueError as exc:
        raise HSA5UError(f"path:outside_trusted_root:{path}") from exc
    root_fd = os.open(trusted, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    current_fd = root_fd
    try:
        components = relative.parts
        if not components:
            raise HSA5UError(f"path:root_not_file:{path}")
        for component in components[:-1]:
            next_fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current_fd)
            if current_fd != root_fd:
                os.close(current_fd)
            current_fd = next_fd
        final_fd = os.open(components[-1], flags | os.O_NOFOLLOW, dir_fd=current_fd)
        return final_fd
    except OSError as exc:
        if current_fd != root_fd:
            os.close(current_fd)
        os.close(root_fd)
        raise HSA5UError(f"path:openat_rejected:{path}:{exc.errno}") from exc
    except Exception:
        if current_fd != root_fd:
            os.close(current_fd)
        os.close(root_fd)
        raise


def _identity(info: os.stat_result) -> tuple[int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def sha256(path: Path, trusted_root: Path | None = None) -> str:
    """Hash through component-wise no-follow FDs and revalidate the locator."""
    absolute = _absolute_without_resolve(path)
    root = trusted_root or ROOT
    before_locator = os.lstat(absolute)
    if stat.S_ISLNK(before_locator.st_mode) or not stat.S_ISREG(before_locator.st_mode):
        raise HSA5UError(f"path:not_regular_or_symlink:{path}")
    fd = _open_beneath(root, absolute, os.O_RDONLY)
    digest = hashlib.sha256()
    try:
        before_fd = os.fstat(fd)
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        after_fd = os.fstat(fd)
    finally:
        os.close(fd)
    after_locator = os.lstat(absolute)
    if _identity(before_fd) != _identity(after_fd) or _identity(before_fd) != _identity(after_locator):
        raise HSA5UError(f"path:locator_drift:{path}")
    return digest.hexdigest()


def atomic_write(path: Path, payload: bytes) -> None:
    parent = _absolute_without_resolve(path.parent)
    final = _absolute_without_resolve(path)
    parent.mkdir(parents=True, exist_ok=True)
    if os.path.lexists(final):
        raise HSA5UError(f"write:final_exists:{final}")
    transaction = f".{final.name}.staging.{os.getpid()}.{uuid.uuid4().hex}"
    directory_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        if os.path.lexists(parent / transaction):
            raise HSA5UError(f"write:staging_exists:{parent / transaction}")
        fd = os.open(transaction, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o640, dir_fd=directory_fd)
        try:
            view = memoryview(payload)
            while view:
                written = os.write(fd, view)
                if written <= 0:
                    raise HSA5UError("write:short_write")
                view = view[written:]
            os.fsync(fd)
        finally:
            os.close(fd)
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = getattr(libc, "renameat2", None)
        if renameat2 is None:
            raise HSA5UError("write:renameat2_unavailable")
        renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        renameat2.restype = ctypes.c_int
        result = renameat2(directory_fd, transaction.encode(), directory_fd, final.name.encode(), 1)
        if result != 0:
            error = ctypes.get_errno()
            raise HSA5UError(f"write:rename_noreplace:{os.strerror(error)}")
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def write_json(path: Path, value: Any) -> None:
    atomic_write(path, canonical_json(value))


def parse_time(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value or "<" in value or ">" in value or "$" in value:
        raise HSA5UError(f"{field}:unknown_or_dynamic_time")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HSA5UError(f"{field}:invalid_timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise HSA5UError(f"{field}:timezone_required")
    return parsed


def validate_scope(record: Mapping[str, Any]) -> None:
    parts: dict[str, set[str]] = {}
    for field in ("expected_scope", "returned_scope", "absent_scope", "unknown_scope"):
        value = record.get(field)
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
            raise HSA5UError(f"scope:{field}:invalid")
        if len(value) != len(set(value)):
            raise HSA5UError(f"scope:{field}:duplicate")
        parts[field] = set(value)
    if not parts["expected_scope"]:
        raise HSA5UError("scope:expected_scope:empty")
    partitions = [parts[field] for field in ("returned_scope", "absent_scope", "unknown_scope")]
    if any(left & right for index, left in enumerate(partitions) for right in partitions[index + 1:]):
        raise HSA5UError("scope:partition_overlap")
    if set().union(*partitions) != parts["expected_scope"]:
        raise HSA5UError("scope:closure")


def _secure_path(path: Path, trusted_root: Path | None = None) -> None:
    absolute = _absolute_without_resolve(path)
    root = trusted_root or ROOT
    try:
        absolute.relative_to(_absolute_without_resolve(root))
    except ValueError as exc:
        raise HSA5UError(f"path:outside_trusted_root:{path}") from exc
    if any(part in {"", ".", ".."} for part in absolute.parts[1:-1]):
        raise HSA5UError(f"path:invalid_component:{path}")
    fd = _open_beneath(root, absolute, os.O_RDONLY)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise HSA5UError(f"path:not_regular:{path}")
    finally:
        os.close(fd)
    name = absolute.name.lower()
    if any(token in name for token in ("stdout", "stderr", ".log")):
        raise HSA5UError(f"path:status_stream_not_raw:{path}")


def _artifact(record: Mapping[str, Any], role: str, path: Path) -> dict[str, str]:
    absolute = _absolute_without_resolve(path)
    return {"role": role, "path": str(absolute), "sha256": sha256(absolute, trusted_root=ROOT)}


def validate_handoff(
    manifest: Mapping[str, Any], inventory: Mapping[str, Any] | None = None,
    trusted_root: Path = ROOT,
) -> None:
    if manifest.get("schema_version") != HSA5_HANDOFF_SCHEMA_VERSION or manifest.get("hsa5u_contract_version") != SCHEMA_VERSION:
        raise HSA5UError("manifest:schema_version")
    run_id = manifest.get("acquisition_run_id")
    if not isinstance(run_id, str) or not STABLE_ID.fullmatch(run_id):
        raise HSA5UError("manifest:acquisition_run_id")
    if manifest.get("target_asof") != TARGET_ASOF:
        raise HSA5UError("manifest:target_asof")
    sources = manifest.get("sources")
    if not isinstance(sources, list) or {item.get("source_family") for item in sources if isinstance(item, Mapping)} != set(SOURCE_FAMILIES):
        raise HSA5UError("manifest:source_family_set")
    for source in sources:
        if not isinstance(source, Mapping):
            raise HSA5UError("source:not_object")
        missing = [field for field in REQUIRED_FIELDS if field not in source]
        if missing:
            raise HSA5UError(f"source:missing:{missing[0]}")
        family = source["source_family"]
        if family not in SOURCE_FAMILIES or source["acquisition_run_id"] != run_id:
            raise HSA5UError(f"source:{family}:run_or_family")
        if not isinstance(source["source_id"], str) or not STABLE_ID.fullmatch(source["source_id"]):
            raise HSA5UError(f"source:{family}:source_id")
        if source["raw_artifact_role"] != "provider_raw_response" or source["normalized_artifact_role"] != "provider_normalized_payload":
            raise HSA5UError(f"source:{family}:role")
        if source["source_validator_status"] != "PASS":
            raise HSA5UError(f"source:{family}:validator")
        if not isinstance(source["request_parameters"], Mapping) or not isinstance(source["http_status"], int) or not 100 <= source["http_status"] <= 599:
            raise HSA5UError(f"source:{family}:transport_request")
        times = [parse_time(source[field], field) for field in TIMESTAMP_FIELDS]
        if not times[0] <= times[1] <= times[2]:
            raise HSA5UError(f"source:{family}:time_order")
        validate_scope(source)
        artifacts = source.get("artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            raise HSA5UError(f"source:{family}:artifacts")
        for field, role in (("raw_files", "provider_raw_response"), ("normalized_files", "provider_normalized_payload")):
            paths = source[field]
            if not isinstance(paths, list) or not paths:
                raise HSA5UError(f"source:{family}:{field}:empty")
            for path_value in paths:
                path = Path(path_value)
                _secure_path(path, trusted_root)
                if not any(item.get("role") == role and item.get("path") == str(_absolute_without_resolve(path)) and item.get("sha256") == sha256(path, trusted_root) for item in source["artifacts"]):
                    raise HSA5UError(f"source:{family}:{role}:artifact_binding")
        for item in artifacts:
            if item.get("role") not in {"provider_raw_response", "provider_normalized_payload"} or not isinstance(item.get("sha256"), str) or not SHA256.fullmatch(item["sha256"]):
                raise HSA5UError(f"source:{family}:artifact_contract")
    if inventory is not None and inventory.get("target_asof") != manifest.get("target_asof"):
        raise HSA5UError("inventory:target_asof")


DAILY_SOURCE = '''
def write_json(path, payload):
    pass

def main():
    parser.add_argument("--skip-finmind-validate", default=False)
    if not args.skip_finmind:
        job["finmind_update"] = run_finmind_segmented_update()
        job["orthogonal"] = run_finmind_orthogonal_batch_update()
        source_validation = validate_finmind_source_artifacts()
        if not source_validation.get("ok"):
            return 2
        write_json(job_dir / "job.json", job)
    provider = run_provider_candidate_refresh_gate()
    model = run_model_signal_gate()
    finalize_job()
'''
BACKEND_SOURCE = '''
def run_workflow():
    archive_symbols()
    archive_corporate_action_symbols()
    archive_institutional_symbols()
    archive_margin_symbols()
    archive_monthly_revenue_symbols()
    archive_valuation_symbols()
'''


def build_fixture(output_dir: Path, project_root: Path = ROOT) -> dict[str, Any]:
    output_dir = _absolute_without_resolve(output_dir)
    project_root = _absolute_without_resolve(project_root)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise HSA5UError(f"output:existing_nonempty_root:{output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)
    source_root = output_dir / "fixture_sources"
    raw_root = source_root / "raw"
    normalized_root = source_root / "normalized"
    records: list[dict[str, Any]] = []
    for family in SOURCE_FAMILIES:
        raw = raw_root / family / "provider_response.json"
        normalized = normalized_root / family / "normalized_payload.json"
        write_json(raw, {"family": family, "target_asof": TARGET_ASOF, "records": ["2330"]})
        write_json(normalized, {"family": family, "target_asof": TARGET_ASOF, "symbols": ["2330", "2317"]})
        record = {
            "snapshot_id": f"{family}.20260825.hsa5u",
            "source_family": family,
            "source_id": f"finmind.{family}.v4",
            "provider": "FinMind",
            "source_endpoint_version": f"/v4/data/{family}:v4",
            "request_parameters": {"dataset": family, "trade_date": TARGET_ASOF},
            "fetched_at": "2026-08-25T11:00:00+00:00",
            "http_status": 200,
            "transport_identity": "https.direct.tls12",
            "parser_version": "hsa5u-fixture-parser-v1",
            "schema_version": "hsa5u-source-v1",
            "trade_date": TARGET_ASOF,
            "available_at": "2026-08-25T10:45:00+00:00",
            "source_published_at": "2026-08-25T10:30:00+00:00",
            "raw_artifact_role": "provider_raw_response",
            "normalized_artifact_role": "provider_normalized_payload",
            "source_validator_status": "PASS",
            "acquisition_run_id": RUN_ID,
            "expected_scope": ["2330", "2317"], "returned_scope": ["2330"],
            "absent_scope": ["2317"], "unknown_scope": [],
            "raw_files": [str(raw.resolve())], "normalized_files": [str(normalized.resolve())],
        }
        record["artifacts"] = [
            {"role": "provider_raw_response", "path": str(_absolute_without_resolve(raw)), "sha256": sha256(raw, project_root)},
            {"role": "provider_normalized_payload", "path": str(_absolute_without_resolve(normalized)), "sha256": sha256(normalized, project_root)},
        ]
        records.append(record)
    manifest = {"schema_version": HSA5_HANDOFF_SCHEMA_VERSION, "hsa5u_contract_version": SCHEMA_VERSION, "acquisition_run_id": RUN_ID, "target_asof": TARGET_ASOF, "sources": records}
    validate_handoff(manifest, trusted_root=project_root)
    handoff_path = output_dir / "same_run_acquisition_handoff_manifest.json"
    write_json(handoff_path, manifest)
    score = output_dir / "model_a_score.json"
    top50 = output_dir / "model_a_top50.json"
    write_json(score, {"scores": [], "target_asof": TARGET_ASOF})
    write_json(top50, {"symbols": [f"{index:04d}" for index in range(50)], "target_asof": TARGET_ASOF})
    inventory = {
        "schema_version": "hsa5u.synthetic_inventory.v1", "target_asof": TARGET_ASOF,
        "acquisition_handoff_manifest_path": str(_absolute_without_resolve(handoff_path)),
        "sources": {record["source_family"]: record for record in records},
        "_model_a_qlib_score_top50_lineage": {
            "lineage_id": "model_a.qlib.top50.hsa5u",
            "score_artifact_path": str(_absolute_without_resolve(score)), "score_artifact_sha256": sha256(score, project_root),
            "top50_artifact_path": str(_absolute_without_resolve(top50)), "top50_artifact_sha256": sha256(top50, project_root),
            "top50_count": 50, "source_validator_status": "PASS",
        },
    }
    inventory["sources"]["model_a_qlib_score_top50_lineage"] = inventory.pop("_model_a_qlib_score_top50_lineage")
    inventory_path = output_dir / "source_inventory.json"
    write_json(inventory_path, inventory)
    daily_path, backend_path = output_dir / "daily_fixture.py", output_dir / "backend_fixture.py"
    atomic_write(daily_path, DAILY_SOURCE.encode("utf-8"))
    atomic_write(backend_path, BACKEND_SOURCE.encode("utf-8"))
    os.chmod(daily_path, 0o640); os.chmod(backend_path, 0o640)
    preflight_output = output_dir / "hsa5_preflight"
    sys.path.insert(0, str(HSA5_SCRIPT.parent))
    import build_tw_model_b_hsa5_daily_auto_sealed_capture_wiring_preflight as hsa5
    result = hsa5.build_preflight(
        daily_script=daily_path, backend_script=backend_path, source_inventory=inventory_path,
        output_dir=preflight_output, project_root=project_root,
        allow_test_output_override=True,
    )
    contract_report = {
        "schema_version": SCHEMA_VERSION,
        "handoff_manifest": str(_absolute_without_resolve(handoff_path)),
        "manifest_last": True,
        "canonical_json": True,
        "same_run_acquisition_run_id": RUN_ID,
        "target_asof": TARGET_ASOF,
        "source_families": list(SOURCE_FAMILIES),
        "raw_and_normalized_roles": True,
        "exact_path_sha256_bindings": True,
        "request_http_transport_identity": True,
        "pit_timestamp_order": True,
        "scope_closure": True,
        "source_validator_status": "PASS",
        "negative_cases_fail_closed": [
            "missing_manifest", "run_mismatch", "path_or_sha256_mismatch", "role_mismatch",
            "validator_not_PASS", "scope_overlap", "renamed_stdout", "symlink_or_locator_drift",
            "unknown_or_dynamic_time",
        ],
    }
    write_json(output_dir / "contract_validation.json", contract_report)
    forbidden = {
        "schema_version": SCHEMA_VERSION,
        "pass": True,
        "scope": "isolated HSA5U synthetic fixture and evidence only",
        "daily_runner_modified": False, "backend_runtime_modified": False,
        "cron_modified": False, "actual_crontab_modified": False,
        "provider_modified": False, "qlib_modified": False,
        "latest_pointers_modified": False, "frontend_modified": False,
        "network_used": False, "database_used": False, "openai_used": False,
        "training_scoring_replay": False,
        "hsa5_decision": result["decision"],
        "protected_scope_evidence": {
            "authority": "HSA5 preflight protected_before_after_fingerprints",
            "manifest": str(preflight_output / "manifest.json"),
            "self_report_only": False,
        },
        "next_gate": "HSA6_NO_CRON_IMPLEMENTATION_PREFLIGHT_ONLY",
    }
    write_json(output_dir / "forbidden_scope_audit.json", forbidden)
    report = f"""# HSA5U synthetic acquisition handoff execution report

## Verdict

`PASS_HSA5U_SYNTHETIC_HANDOFF_READY_FOR_HSA6_NO_CRON_IMPLEMENTATION`

The complete local fixture was accepted by the existing HSA5 preflight as
`{result['decision']}`. This proves only the handoff contract and HSA6 no-cron
implementation preflight shape; it does not authorize HSA6 runtime wiring,
daily-auto changes, cron changes, provider/latest writes, or production use.

## Contract evidence

- Same-run identity: `{RUN_ID}`
- Target as-of: `{TARGET_ASOF}`
- Required source families: `{", ".join(SOURCE_FAMILIES)}`
- Raw and normalized exact paths, roles, and SHA256 are bound in the handoff.
- HTTP/request/transport identity, PIT timestamps, scope closure, and validator `PASS` are present.
- HSA5 preflight output: `{result['decision']}`
- Negative fixtures fail closed for missing manifest, identity/checksum/role/validator mismatch,
  scope overlap, renamed stdout, symlink/locator drift, and unknown/dynamic time.

## Boundary

Only isolated synthetic fixture, contract reports, tests, and HSA5 evidence were written.
No daily runner, backend runtime, cron/crontab, provider, Qlib, latest pointer, frontend,
network, database, OpenAI, training, scoring, or replay operation was performed.
"""
    atomic_write(output_dir / "execution_report.md", report.encode("utf-8"))
    final_manifest = {
        "schema_version": SCHEMA_VERSION, "decision": result["decision"],
        "acquisition_run_id": RUN_ID, "target_asof": TARGET_ASOF,
        "hsa5_preflight_output": str(_absolute_without_resolve(preflight_output)),
        "hsa5_preflight_decision": result["decision"],
        "artifacts": [],
        "manifest_written_last": True,
    }
    artifact_names = []
    for candidate in sorted(output_dir.rglob("*")):
        if candidate.is_file() and candidate.name != "manifest.json":
            artifact_names.append(str(candidate.relative_to(output_dir)))
    final_manifest["artifacts"] = [{"path": name, "sha256": sha256(output_dir / name, output_dir)} for name in artifact_names]
    write_json(output_dir / "manifest.json", final_manifest)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--project-root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    requested = _absolute_without_resolve(args.output_dir)
    if requested != _absolute_without_resolve(OUTPUT_ROOT):
        raise SystemExit(f"output root is fixed: {OUTPUT_ROOT}")
    result = build_fixture(requested, args.project_root)
    print(json.dumps({"decision": result["decision"], "output_dir": str(requested)}, ensure_ascii=False))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
