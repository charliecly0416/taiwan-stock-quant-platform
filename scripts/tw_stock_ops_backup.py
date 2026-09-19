#!/usr/bin/env python3
"""Create and verify portable Taiwan-stock product backups.

The default command is a read-only plan. Creation requires --confirm-create.
Restore drill validates bytes and PostgreSQL archive structure without writing
to a database or to the live repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

SCHEMA = "tw_stock_ops_backup.v1"
BACKUP_INPUTS = (
    "configs/active_baseline_descriptor.yaml",
    "configs/tw_modular_registry.yaml",
    "configs/tw_product_artifact_registry.yaml",
    "configs/tw_replay_window_policy.yaml",
    "data_tw/artifacts",
    "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_training_20260916",
    "data_tw/experiments/modelb_b19r2r_v5_prospective_accumulator",
    "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/run/phasee1_frozen_qlib_model.pkl",
    "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_ltr_model.pkl",
    "data_tw/experiments/model_b_compatibility_daily_shadow/model_artifact_phase1c_20260905/phase1c_head10_all_l31_model.pkl",
    "qlib_pipeline/data_tw/experiments/option_c_daily_signal",
    "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin",
    "qlib_pipeline/mlruns",
    "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron",
)
PLAINTEXT_CREDENTIAL_PATTERNS = (
    ("authenticated_postgresql_url", re.compile(rb"postgres(?:ql)?://[^:@/\s]+:[^@/\s]+@", re.IGNORECASE)),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_files(root: Path) -> list[tuple[str, Path]]:
    files: list[tuple[str, Path]] = []
    for relative in BACKUP_INPUTS:
        source = root / relative
        if source.is_file() and not source.is_symlink():
            files.append((relative, source))
        elif source.is_dir() and not source.is_symlink():
            for path in sorted(source.rglob("*")):
                if path.is_file() and not path.is_symlink():
                    files.append((path.relative_to(root).as_posix(), path))
    return files


def plaintext_credential_findings(root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for relative, path in source_files(root):
        try:
            content = path.read_bytes()
        except OSError:
            continue
        for code, pattern in PLAINTEXT_CREDENTIAL_PATTERNS:
            if pattern.search(content):
                findings.append({"path": relative, "code": code})
    return findings


def input_status(root: Path) -> list[dict]:
    result = []
    for relative in BACKUP_INPUTS:
        source = root / relative
        if source.is_symlink():
            state = "symlink_rejected"
        elif source.is_file():
            state = "file"
        elif source.is_dir():
            state = "directory"
        else:
            state = "missing"
        result.append({"path": relative, "state": state, "present": state in {"file", "directory"}})
    return result


def postgres_env(database_url: str) -> dict[str, str]:
    parsed = urlparse(database_url)
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname or not parsed.path.strip("/"):
        raise ValueError("DATABASE_URL must be a PostgreSQL URL with host and database")
    env = os.environ.copy()
    env.pop("DATABASE_URL", None)
    env.update({
        "PGHOST": parsed.hostname,
        "PGPORT": str(parsed.port or 5432),
        "PGDATABASE": unquote(parsed.path.strip("/")),
    })
    if parsed.username:
        env["PGUSER"] = unquote(parsed.username)
    if parsed.password:
        env["PGPASSWORD"] = unquote(parsed.password)
    return env


def backup_plan(root: Path) -> dict:
    files = source_files(root)
    inputs = input_status(root)
    credential_findings = plaintext_credential_findings(root)
    return {
        "schema_version": SCHEMA,
        "mode": "plan",
        "repo_root": str(root),
        "artifact_file_count": len(files),
        "artifact_bytes": sum(path.stat().st_size for _, path in files),
        "required_inputs_complete": all(item["present"] for item in inputs) and not credential_findings,
        "required_inputs": inputs,
        "plaintext_credential_findings": credential_findings,
        "database_url_present": bool(os.getenv("DATABASE_URL", "").strip()),
        "pg_dump_available": bool(shutil.which("pg_dump")),
        "pg_restore_available": bool(shutil.which("pg_restore")),
        "writes_performed": False,
    }


def create_backup(root: Path, output_root: Path, *, skip_database: bool) -> Path:
    plan = backup_plan(root)
    inputs = plan["required_inputs"]
    incomplete = [item["path"] for item in inputs if not item["present"]]
    if incomplete:
        raise RuntimeError("required backup inputs are missing or unsupported: " + ", ".join(incomplete))
    if plan["plaintext_credential_findings"]:
        paths = ", ".join(item["path"] for item in plan["plaintext_credential_findings"])
        raise RuntimeError("plaintext credentials found in backup inputs: " + paths)
    files = source_files(root)
    if not files:
        raise RuntimeError("no managed product artifacts found")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    final = output_root.resolve() / f"tw_stock_ops_{stamp}"
    output_root.mkdir(parents=True, exist_ok=True)
    if final.exists():
        raise FileExistsError(final)
    with tempfile.TemporaryDirectory(prefix=".tw-stock-backup-", dir=output_root) as temporary:
        work = Path(temporary)
        archive = work / "artifacts.tar.gz"
        inventory = []
        with tarfile.open(archive, "w:gz") as bundle:
            for relative, path in files:
                bundle.add(path, arcname=relative, recursive=False)
                inventory.append({"path": relative, "size": path.stat().st_size, "sha256": sha256(path)})
        database = {"included": False}
        if not skip_database:
            url = os.getenv("DATABASE_URL", "").strip()
            pg_dump = shutil.which("pg_dump")
            if not url or not pg_dump:
                raise RuntimeError("DATABASE_URL and pg_dump are required unless --skip-database is explicit")
            dump = work / "database.dump"
            completed = subprocess.run(
                [pg_dump, "--format=custom", "--file", str(dump), "--no-owner", "--no-privileges"],
                env=postgres_env(url), capture_output=True, text=True, timeout=1800, check=False,
            )
            if completed.returncode != 0:
                raise RuntimeError(f"pg_dump failed: {(completed.stderr or '').strip()[-500:]}")
            dump.chmod(0o600)
            database = {"included": True, "file": dump.name, "size": dump.stat().st_size, "sha256": sha256(dump)}
        manifest = {
            "schema_version": SCHEMA,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "database": database,
            "artifacts": {
                "file": archive.name, "size": archive.stat().st_size,
                "sha256": sha256(archive), "inventory": inventory,
            },
            "contains_secrets": bool(database["included"]),
            "contains_sensitive_database_dump": bool(database["included"]),
            "contains_plaintext_credentials": False,
            "sensitive_backup": True,
            "required_inputs_complete": True,
            "required_inputs": [item["path"] for item in inputs],
            "restore_policy": "drill-first; never restore over the live database",
        }
        (work / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        os.chmod(work / "manifest.json", 0o600)
        os.chmod(archive, 0o600)
        Path(temporary).rename(final)
    return final


def drill(backup_dir: Path) -> dict:
    manifest_path = backup_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != SCHEMA:
        raise RuntimeError("unsupported backup manifest")
    archive = backup_dir / str(manifest["artifacts"]["file"])
    if sha256(archive) != manifest["artifacts"]["sha256"]:
        raise RuntimeError("artifact archive checksum mismatch")
    expected = {row["path"]: row for row in manifest["artifacts"]["inventory"]}
    observed: dict[str, dict] = {}
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle.getmembers():
            if not member.isfile() or member.name.startswith("/") or ".." in Path(member.name).parts:
                raise RuntimeError("unsafe or unsupported archive member")
            stream = bundle.extractfile(member)
            digest = hashlib.sha256()
            size = 0
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                size += len(chunk)
                digest.update(chunk)
            observed[member.name] = {"size": size, "sha256": digest.hexdigest()}
    if set(observed) != set(expected) or any(observed[name] != {"size": row["size"], "sha256": row["sha256"]} for name, row in expected.items()):
        raise RuntimeError("artifact inventory mismatch")
    database = manifest.get("database") or {}
    database_ok = not database.get("included")
    if database.get("included"):
        dump = backup_dir / str(database.get("file") or "")
        if not dump.is_file() or sha256(dump) != database.get("sha256"):
            raise RuntimeError("database dump checksum mismatch")
        pg_restore = shutil.which("pg_restore")
        if not pg_restore:
            raise RuntimeError("pg_restore is required for the database archive drill")
        completed = subprocess.run([pg_restore, "--list", str(dump)], capture_output=True, text=True, timeout=120, check=False)
        if completed.returncode != 0:
            raise RuntimeError("pg_restore could not read the database archive")
        database_ok = True
    return {
        "ok": True, "schema_version": SCHEMA, "mode": "archive_integrity_drill",
        "artifact_files_verified": len(observed), "database_archive_verified": database_ok,
        "live_database_writes": False, "live_artifact_writes": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="?", choices=("plan", "create", "drill"), default="plan")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--output-root", default=os.getenv("TW_STOCK_BACKUP_ROOT", "backups/tw_stock_ops"))
    parser.add_argument("--backup-dir")
    parser.add_argument("--skip-database", action="store_true")
    parser.add_argument("--confirm-create", action="store_true")
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    if args.command == "plan":
        result = backup_plan(root)
    elif args.command == "create":
        if not args.confirm_create:
            parser.error("create requires --confirm-create")
        result = {"ok": True, "backup_dir": str(create_backup(root, Path(args.output_root), skip_database=args.skip_database))}
    else:
        if not args.backup_dir:
            parser.error("drill requires --backup-dir")
        result = drill(Path(args.backup_dir).resolve())
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
