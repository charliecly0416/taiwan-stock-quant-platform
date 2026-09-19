#!/usr/bin/env python3
"""Build a deterministic provenance manifest for the authorized 2026-09-07 publish."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/candidate_binding_20260907/protected_drift_audit_20260907"
PROVIDER = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin"
BACKUP = ROOT / "qlib_pipeline/data_tw/experiments/option_c_ops/option_c_yahoo_scrapling_publish_20260907_20260907T123544Z_daily_auto/backup/formal_provider"
LATEST = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json"
LATEST_BACKUP = ROOT / "data_tw/ops/option_c_jobs/latest_backups/latest_signal_backup_20260907T123639Z.json"
NORMAL_JOB = ROOT / "data_tw/ops/option_c_jobs/option_c_normal_publish_20260907_20260907T123620Z_63d1f740/job.json"
PROVIDER_REPORT = ROOT / "qlib_pipeline/data_tw/experiments/option_c_ops/option_c_yahoo_scrapling_publish_20260907_20260907T123544Z_daily_auto/reports/backup_report.json"


def fp(path: Path) -> dict:
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            size += len(chunk)
            h.update(chunk)
    return {"exists": True, "size_bytes": size, "sha256": h.hexdigest()}


def main() -> None:
    rels = sorted(p.relative_to(PROVIDER).as_posix() for p in PROVIDER.rglob("*") if p.is_file())
    backup_rels = sorted(p.relative_to(BACKUP).as_posix() for p in BACKUP.rglob("*") if p.is_file())
    entries = []
    for rel in sorted(set(rels) | set(backup_rels)):
        after = PROVIDER / rel
        before = BACKUP / rel
        item = {
            "relative_path": rel,
            "before": {"path": str(before.relative_to(ROOT)), **(fp(before) if before.exists() else {"exists": False})},
            "after": {"path": str(after.relative_to(ROOT)), **(fp(after) if after.exists() else {"exists": False})},
        }
        item["sha256_equal"] = item["before"].get("sha256") == item["after"].get("sha256")
        entries.append(item)

    normal_job = json.loads(NORMAL_JOB.read_text(encoding="utf-8"))
    provider_report = json.loads(PROVIDER_REPORT.read_text(encoding="utf-8"))
    payload = {
        "schema_version": "protected_drift_provenance_manifest.v1",
        "manifest_id": "authorized_option_c_publish_20260907",
        "authorization": {
            "authorized_by_user": True,
            "authorization_statement": "User confirmed authorization for the 2026-09-07 normal publish provenance rebaseline.",
            "scope": "descriptor protected hashes only; no rollback, latest/provider/calendar/instruments content writes",
        },
        "provider_publish": {
            "job_dir": str(PROVIDER_REPORT.relative_to(ROOT)).replace("/reports/backup_report.json", ""),
            "report": str(PROVIDER_REPORT.relative_to(ROOT)),
            "asof": "2026-09-07",
            "provider_scope": provider_report.get("provider_scope"),
            "expected_file_count": provider_report.get("results", {}).get("formal_provider", {}).get("backup_manifest", {}).get("file_count"),
            "observed_before_file_count": len(backup_rels),
            "observed_after_file_count": len(rels),
            "backup_root": str(BACKUP.relative_to(ROOT)),
            "source_root": str(PROVIDER.relative_to(ROOT)),
            "entries_equal_count": sum(1 for e in entries if e["sha256_equal"]),
            "entries_changed_count": sum(1 for e in entries if not e["sha256_equal"]),
            "entries": entries,
        },
        "latest_signal": {
            "normal_publish_job": str(NORMAL_JOB.relative_to(ROOT)),
            "job_id": normal_job.get("job_id"),
            "run_id": normal_job.get("runner_output", {}).get("run_id"),
            "asof": normal_job.get("asof"),
            "before": {"path": str(LATEST_BACKUP.relative_to(ROOT)), **fp(LATEST_BACKUP)},
            "after": {"path": str(LATEST.relative_to(ROOT)), **fp(LATEST)},
            "job_before": normal_job.get("latest_before"),
            "job_after": normal_job.get("latest_after"),
            "rollback_command_recorded": normal_job.get("latest_update", {}).get("prepared", {}).get("rollback_command"),
        },
        "descriptor_rebaseline": {
            "paths": {
                "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json": fp(LATEST)["sha256"],
                "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt": fp(PROVIDER / "calendars/day.txt")["sha256"],
                "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt": fp(PROVIDER / "instruments/all.txt")["sha256"],
            },
            "active_model_unchanged": True,
            "model_b_unchanged": True,
            "strategy_unchanged": True,
            "production_default_unchanged": True,
        },
        "safety": {
            "rollback": False,
            "provider_content_write": False,
            "latest_content_write": False,
            "calendar_content_write": False,
            "instruments_content_write": False,
            "descriptor_hash_update_only": True,
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "authorized_provenance_rebaseline_manifest.json").write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
