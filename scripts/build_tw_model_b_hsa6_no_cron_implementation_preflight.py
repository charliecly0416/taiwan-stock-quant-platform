#!/usr/bin/env python3
"""Convert the HSA5U synthetic handoff into isolated HSA4 candidates.

No runtime, cron, provider, latest, network, database, training or replay work
is performed. The default paths are fixed to immutable project evidence roots.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import errno
import getpass
import stat
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
HSA5U_ROOT = ROOT / "data_tw/experiments/model_b_path2_sealed_archive_retrain/hsa5u_synthetic_acquisition_handoff_repair_20260825"
OUTPUT_ROOT = ROOT / "data_tw/experiments/model_b_path2_sealed_archive_retrain/hsa6_no_cron_implementation_preflight_final_20260825"
HSA4_SCRIPT = ROOT / "scripts/build_tw_model_b_hsa4_isolated_daily_sealed_capture.py"
HSA5_SCRIPT = ROOT / "scripts/build_tw_model_b_hsa5_daily_auto_sealed_capture_wiring_preflight.py"
REQUIRED_FAMILIES = ("adjusted_price", "twii", "institutional_flow", "margin_short")
STABLE = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
SCHEMA = "hsa6.no_cron_implementation_preflight.v1"


class HSA6Error(ValueError):
    pass


PROTECTED_RELATIVE_PATHS = (
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


def _secure_file_fingerprint(path: Path) -> dict[str, Any]:
    absolute = _abs(path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    root_flags = flags | getattr(os, "O_DIRECTORY", 0)
    directory_fd = os.open(absolute.anchor, root_flags)
    chain: list[tuple[int, int]] = []
    try:
        root = os.fstat(directory_fd)
        chain.append((root.st_dev, root.st_ino))
        for component in absolute.parts[1:-1]:
            if component in {"", ".", ".."}:
                raise HSA6Error(f"invalid_protected_path:{absolute}")
            next_fd = os.open(component, root_flags, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
            info = os.fstat(directory_fd)
            chain.append((info.st_dev, info.st_ino))
        file_fd = os.open(absolute.name, flags, dir_fd=directory_fd)
    finally:
        os.close(directory_fd)
    before = os.fstat(file_fd)
    if not stat.S_ISREG(before.st_mode):
        os.close(file_fd)
        raise HSA6Error(f"protected_not_regular:{absolute}")
    digest = hashlib.sha256()
    try:
        while chunk := os.read(file_fd, 1024 * 1024):
            digest.update(chunk)
        after = os.fstat(file_fd)
    finally:
        os.close(file_fd)
    identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    if identity != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise HSA6Error(f"protected_file_changed_while_reading:{absolute}")
    verify_dir = os.open(absolute.anchor, root_flags)
    verify_chain: list[tuple[int, int]] = []
    try:
        info = os.fstat(verify_dir)
        verify_chain.append((info.st_dev, info.st_ino))
        for component in absolute.parts[1:-1]:
            next_fd = os.open(component, root_flags, dir_fd=verify_dir)
            os.close(verify_dir)
            verify_dir = next_fd
            info = os.fstat(verify_dir)
            verify_chain.append((info.st_dev, info.st_ino))
        verify_fd = os.open(absolute.name, flags, dir_fd=verify_dir)
        verify = os.fstat(verify_fd)
        os.close(verify_fd)
    finally:
        os.close(verify_dir)
    if tuple(chain) != tuple(verify_chain) or (verify.st_dev, verify.st_ino, verify.st_size, verify.st_mtime_ns) != identity:
        raise HSA6Error(f"protected_locator_changed:{absolute}")
    return {
        "path": os.fspath(absolute), "status": "PRESENT", "type": "regular",
        "device": before.st_dev, "inode": before.st_ino, "size": before.st_size,
        "mtime_ns": before.st_mtime_ns, "sha256": digest.hexdigest(),
        "ancestor_chain": [{"device": d, "inode": i} for d, i in chain],
        "nofollow_openat": True, "fd_identity_stable": True, "locator_revalidated": True,
    }


def _secure_directory_fingerprint(path: Path) -> dict[str, Any]:
    absolute = _abs(path)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    directory_fd = os.open(absolute.anchor, flags)
    chain: list[tuple[int, int]] = []
    try:
        info = os.fstat(directory_fd)
        chain.append((info.st_dev, info.st_ino))
        for component in absolute.parts[1:]:
            next_fd = os.open(component, flags, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
            info = os.fstat(directory_fd)
            chain.append((info.st_dev, info.st_ino))

        def walk(fd: int, prefix: str = "") -> list[dict[str, Any]]:
            rows: list[dict[str, Any]] = []
            for name in sorted(os.listdir(fd)):
                rel = f"{prefix}/{name}" if prefix else name
                item = os.stat(name, dir_fd=fd, follow_symlinks=False)
                row = {"path": rel, "type": "directory" if stat.S_ISDIR(item.st_mode) else "regular" if stat.S_ISREG(item.st_mode) else "other", "device": item.st_dev, "inode": item.st_ino, "size": item.st_size, "mtime_ns": item.st_mtime_ns}
                if stat.S_ISDIR(item.st_mode):
                    child = os.open(name, flags, dir_fd=fd)
                    try:
                        opened = os.fstat(child)
                        if (opened.st_dev, opened.st_ino) != (item.st_dev, item.st_ino):
                            raise HSA6Error(f"protected_tree_locator_changed:{rel}")
                        rows.extend([row, *walk(child, rel)])
                    finally:
                        os.close(child)
                elif stat.S_ISREG(item.st_mode):
                    child = os.open(name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=fd)
                    digest = hashlib.sha256()
                    try:
                        opened = os.fstat(child)
                        while chunk := os.read(child, 1024 * 1024):
                            digest.update(chunk)
                        after = os.fstat(child)
                    finally:
                        os.close(child)
                    if (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) or (opened.st_dev, opened.st_ino) != (item.st_dev, item.st_ino):
                        raise HSA6Error(f"protected_tree_file_changed:{rel}")
                    row["sha256"] = digest.hexdigest()
                if not stat.S_ISDIR(item.st_mode):
                    rows.append(row)
            return rows

        root_before = os.fstat(directory_fd)
        rows = walk(directory_fd)
        root_after = os.fstat(directory_fd)
    finally:
        os.close(directory_fd)
    if (root_before.st_dev, root_before.st_ino, root_before.st_mtime_ns) != (root_after.st_dev, root_after.st_ino, root_after.st_mtime_ns):
        raise HSA6Error(f"protected_directory_changed:{absolute}")
    verify_fd = os.open(absolute.anchor, flags)
    verify_chain: list[tuple[int, int]] = []
    try:
        info = os.fstat(verify_fd)
        verify_chain.append((info.st_dev, info.st_ino))
        for component in absolute.parts[1:]:
            next_fd = os.open(component, flags, dir_fd=verify_fd)
            os.close(verify_fd)
            verify_fd = next_fd
            info = os.fstat(verify_fd)
            verify_chain.append((info.st_dev, info.st_ino))
    finally:
        os.close(verify_fd)
    if tuple(chain) != tuple(verify_chain) or (root_before.st_dev, root_before.st_ino) != (info.st_dev, info.st_ino):
        raise HSA6Error(f"protected_directory_locator_changed:{absolute}")
    payload = _canonical({"rows": rows})
    return {"path": os.fspath(absolute), "status": "PRESENT", "type": "directory", "device": root_before.st_dev, "inode": root_before.st_ino, "entry_count": len(rows), "tree_sha256": hashlib.sha256(payload).hexdigest(), "nofollow_openat": True, "locator_revalidated": True}


def _fingerprint(path: Path, *, allow_inaccessible: bool = False) -> dict[str, Any]:
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return {"path": os.fspath(_abs(path)), "status": "ABSENT", "nofollow_openat": True}
    except PermissionError:
        if allow_inaccessible:
            return {"path": os.fspath(_abs(path)), "status": "INACCESSIBLE", "nofollow_openat": True}
        raise HSA6Error(f"protected_path_inaccessible:{path}")
    if stat.S_ISLNK(info.st_mode):
        raise HSA6Error(f"protected_symlink:{path}")
    try:
        return _secure_file_fingerprint(path) if stat.S_ISREG(info.st_mode) else _secure_directory_fingerprint(path)
    except FileNotFoundError:
        return {"path": os.fspath(_abs(path)), "status": "ABSENT", "nofollow_openat": True}


def _crontab_l_fingerprint() -> dict[str, Any]:
    """Read the current crontab without installing or mutating it."""
    try:
        completed = subprocess.run(
            ["crontab", "-l"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HSA6Error(f"actual_crontab_read_failed:{type(exc).__name__}") from exc
    if completed.returncode != 0:
        raise HSA6Error(f"actual_crontab_read_failed:returncode={completed.returncode}")
    content = bytes(completed.stdout)
    return {
        "path": f"crontab -l ({getpass.getuser()})",
        "source": "crontab-l",
        "status": "PRESENT",
        "size": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "nofollow_openat": True,
        "read_only_subprocess": True,
    }


def _actual_crontab_fingerprint() -> dict[str, Any]:
    # The spool file is an implementation detail and is never an authoritative
    # source for this protected fingerprint.  Always use the read-only command.
    return _crontab_l_fingerprint()


def _protected_fingerprints(project_root: Path, *, allow_inaccessible: bool = False) -> dict[str, dict[str, Any]]:
    paths = {role: project_root / relative for role, relative in PROTECTED_RELATIVE_PATHS}
    result = {role: _fingerprint(path, allow_inaccessible=allow_inaccessible) for role, path in paths.items()}
    result["actual_crontab_locator"] = _actual_crontab_fingerprint()
    return result


def validate_evidence_manifest(root: Path) -> dict[str, Any]:
    """Validate every evidence file except the root manifest itself."""
    root = _abs(root)
    manifest_path = root / "manifest.json"
    payload = _load(manifest_path)
    expected = {
        str(path.relative_to(root)): _sha(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path != manifest_path
    }
    actual = {entry.get("path"): entry.get("sha256") for entry in payload.get("artifacts", [])}
    if actual != expected:
        raise HSA6Error("evidence_manifest_incomplete_or_checksum_mismatch")
    if payload.get("artifact_count") != len(expected):
        raise HSA6Error("evidence_artifact_count_mismatch")
    candidate_manifests = sorted(
        key for key in expected
        if key.startswith("sealed_candidates/") and key.endswith("/manifest.json")
    )
    if len(candidate_manifests) != len(REQUIRED_FAMILIES):
        raise HSA6Error("candidate_manifests_not_covered")
    return {"artifact_count": len(expected), "candidate_manifest_count": len(candidate_manifests), "all_checksums_match": True}


def _abs(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_new(path: Path, payload: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise HSA6Error(f"duplicate_final:{path}")
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise HSA6Error(f"output_parent_invalid:{path.parent}")
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _load(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise HSA6Error(f"invalid_json:{path}") from exc


def _validate_handoff(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    sys.path.insert(0, str(HSA5U_ROOT.parent.parent.parent.parent / "scripts"))
    import build_tw_model_b_hsa5u_synthetic_acquisition_handoff as hsa5u
    manifest_path = root / "same_run_acquisition_handoff_manifest.json"
    inventory_path = root / "source_inventory.json"
    if not manifest_path.is_file() or not inventory_path.is_file():
        raise HSA6Error("missing_handoff_or_inventory")
    manifest = _load(manifest_path)
    inventory = _load(inventory_path)
    try:
        hsa5u.validate_handoff(manifest, inventory=inventory, trusted_root=root)
    except Exception as exc:
        raise HSA6Error(f"handoff_contract_rejected:{exc}") from exc
    sources = manifest.get("sources")
    if len(sources) != len(REQUIRED_FAMILIES) or {s.get("source_family") for s in sources} != set(REQUIRED_FAMILIES):
        raise HSA6Error("unknown_or_incomplete_source_family")
    if len({s.get("source_family") for s in sources}) != len(REQUIRED_FAMILIES):
        raise HSA6Error("duplicate_source_family")
    for source in sources:
        if source.get("source_validator_status") != "PASS":
            raise HSA6Error(f"validator_not_PASS:{source.get('source_family')}")
        if source.get("acquisition_run_id") != manifest.get("acquisition_run_id"):
            raise HSA6Error("handoff_run_identity_mismatch")
        if not source.get("raw_files") or not source.get("normalized_files"):
            raise HSA6Error(f"missing_raw_or_normalized:{source.get('source_family')}")
        for name in (*source["raw_files"], *source["normalized_files"]):
            path = Path(name)
            if not path.is_file() or path.is_symlink():
                raise HSA6Error(f"source_not_regular:{path}")
    return manifest, sorted(sources, key=lambda item: REQUIRED_FAMILIES.index(item["source_family"]))


def _validate_hsa5(root: Path) -> None:
    preflight = _load(root / "hsa5_preflight" / "manifest.json")
    if preflight.get("decision") != "READY_FOR_HSA6_NO_CRON_IMPLEMENTATION":
        raise HSA6Error("hsa5_not_READY")


def _verify_candidate(path: Path, source: Mapping[str, Any], run_id: str) -> dict[str, Any]:
    manifest = _load(path / "manifest.json")
    if manifest.get("source_family") != source["source_family"] or manifest.get("source_id") != source["source_id"]:
        raise HSA6Error("candidate_source_identity_mismatch")
    if manifest.get("snapshot_id") is None or not STABLE.fullmatch(manifest["snapshot_id"]):
        raise HSA6Error("candidate_snapshot_id")
    if manifest.get("append_only") is not True or not manifest.get("isolated"):
        raise HSA6Error("candidate_append_only_or_isolated")
    if manifest.get("scope", {}).get("closure") is not True:
        raise HSA6Error("candidate_scope_closure")
    expected_lineage = {
        "source_family": manifest["source_family"], "source_id": manifest["source_id"],
        "provider": manifest["provider"], "source_endpoint_version": manifest["source_endpoint_version"],
        "trade_date": manifest["trade_date"],
        "files": [{k: e[k] for k in ("family", "sealed_path", "sha256", "size_bytes", "source_device", "source_inode")} for e in manifest["files"]],
    }
    if hashlib.sha256(_canonical(expected_lineage)).hexdigest() != manifest.get("lineage_digest"):
        raise HSA6Error("candidate_lineage_digest")
    if len(manifest["files"]) != len(source["raw_files"]) + len(source["normalized_files"]):
        raise HSA6Error("candidate_file_count")
    for entry in manifest["files"]:
        if _sha(path / entry["sealed_path"]) != entry["sha256"]:
            raise HSA6Error("candidate_checksum")
    return {"snapshot_id": manifest["snapshot_id"], "source_family": source["source_family"], "source_id": source["source_id"], "acquisition_run_id": run_id, "manifest_sha256": _sha(path / "manifest.json")}


def build_preflight(input_root: Path = HSA5U_ROOT, output_root: Path = OUTPUT_ROOT, *, allow_test_output_override: bool = False) -> dict[str, Any]:
    input_root, output_root = _abs(input_root), _abs(output_root)
    if not allow_test_output_override and output_root != _abs(OUTPUT_ROOT):
        raise HSA6Error("output_root_fixed")
    if output_root.exists():
        if any(output_root.iterdir()):
            raise HSA6Error("output_root_must_be_new_empty")
    else:
        output_root.mkdir(parents=True)
    manifest, sources = _validate_handoff(input_root)
    _validate_hsa5(input_root)
    protected_before = _protected_fingerprints(ROOT, allow_inaccessible=allow_test_output_override)
    sys.path.insert(0, str(HSA4_SCRIPT.parent))
    import build_tw_model_b_hsa4_isolated_daily_sealed_capture as hsa4
    candidates: list[dict[str, Any]] = []
    candidates_root = output_root / "sealed_candidates"
    candidates_root.mkdir()
    for source in sources:
        family = source["source_family"]
        snapshot = f"hsa6_{family}_20260825_candidate"
        request = hsa4.CaptureRequest(
            snapshot_id=snapshot, source_family=family, source_id=source["source_id"],
            provider=source["provider"], source_endpoint_version=source["source_endpoint_version"],
            parser_version=source["parser_version"], schema_version=source["schema_version"],
            trade_date=source["trade_date"], source_published_at=source["source_published_at"],
            available_at=source["available_at"], fetched_at=source["fetched_at"],
            http_status=source["http_status"], transport_identity=source["transport_identity"],
            request_parameters=source["request_parameters"], raw_files=[Path(p) for p in source["raw_files"]],
            normalized_files=[Path(p) for p in source["normalized_files"]], expected_scope=source["expected_scope"],
            returned_scope=source["returned_scope"], absent_scope=source["absent_scope"], unknown_scope=source["unknown_scope"],
        )
        candidate = hsa4.build_capture(request, output_root=candidates_root)
        candidates.append(_verify_candidate(candidate, source, manifest["acquisition_run_id"]))
    protected_after = _protected_fingerprints(ROOT, allow_inaccessible=allow_test_output_override)
    protected_unchanged = protected_before == protected_after
    if not protected_unchanged:
        raise HSA6Error("protected_paths_changed")
    protected_evidence = {
        role: {"before": protected_before[role], "after": protected_after[role], "unchanged": protected_before[role] == protected_after[role]}
        for role in protected_before
    }
    report = {"schema_version": SCHEMA, "decision": "PASS_HSA6_NO_CRON_ISOLATED_CANDIDATES", "input_run_id": manifest["acquisition_run_id"], "target_asof": manifest["target_asof"], "required_families": list(REQUIRED_FAMILIES), "candidates": candidates, "runtime_hook_implemented": False, "protected_paths_before_after": protected_evidence, "protected_paths_unchanged": protected_unchanged}
    _write_new(output_root / "validation_report.json", _canonical(report))
    _write_new(output_root / "forbidden_scope_audit.json", _canonical({"schema_version": SCHEMA, "pass": True, "daily_runner_modified": False, "backend_modified": False, "cron_modified": False, "provider_modified": False, "latest_modified": False, "frontend_modified": False, "network_used": False, "database_used": False, "openai_used": False, "training_scoring_replay": False, "protected_paths_before_after": protected_evidence, "protected_paths_unchanged": protected_unchanged, "evidence_authority": "HSA6 secure no-follow fingerprints", "authority": "HSA6 isolated preflight"}))
    report_text = "# HSA6 execution report\n\nVerdict: `PASS_HSA6_NO_CRON_ISOLATED_CANDIDATES`\n\nGenerated one append-only HSA4 candidate per required source family from the validated HSA5U synthetic same-run handoff. No runtime hook, cron, provider, latest, network, DB, training, scoring, or replay operation was performed.\n"
    _write_new(output_root / "execution_report.md", report_text.encode())
    artifacts = []
    for path in sorted(output_root.rglob("*")):
        if path.is_file() and path != output_root / "manifest.json":
            artifacts.append({"path": str(path.relative_to(output_root)), "sha256": _sha(path)})
    final = {"schema_version": SCHEMA, "decision": report["decision"], "acquisition_run_id": manifest["acquisition_run_id"], "target_asof": manifest["target_asof"], "artifacts": artifacts, "artifact_count": len(artifacts), "manifest_excluded_from_own_checksum": True, "manifest_written_last": True}
    _write_new(output_root / "manifest.json", _canonical(final))
    report["evidence_validation"] = validate_evidence_manifest(output_root)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = __import__("argparse").ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=HSA5U_ROOT)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args(argv)
    result = build_preflight(args.input_root, args.output_root)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
