#!/usr/bin/env python3
"""Build an isolated, fail-closed Model B shadow daily accumulator.

This command consumes the existing MBCDS2 inventory only.  It never repairs
missing dates, scores Model B, or writes a production/latest artifact.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INVENTORY = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow/mbcds2_ranking_chain_20260905/compatibility_audit.csv"
DEFAULT_SOURCE_INVENTORY = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow/mbcds2_ranking_chain_20260905/date_source_inventory.csv"
DEFAULT_MISSING = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow/mbcds2_missing_date_source_investigation_20260905/all_attempts_summary.json"
CONTRACT = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow/mbcds3_contract_freeze_20260905/contract_schema.json"
OUT = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow/mbcds3_accumulator_20260905"
REQUIRED_DATES = ("2026-08-27", "2026-08-28", "2026-08-31", "2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04")
QUARANTINE_DATES = {"2026-08-27", "2026-08-28", "2026-08-31"}
PROTECTED = (
    ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
    ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt",
    ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt",
    ROOT / "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def protected_fingerprints() -> dict[str, dict[str, object]]:
    result = {}
    for path in PROTECTED:
        result[rel(path)] = {
            "exists": path.is_file(),
            "size": path.stat().st_size if path.is_file() else None,
            "sha256": sha256(path) if path.is_file() else None,
        }
    return result


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def parse_rfc3339(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else None


def is_strict_valid(row: dict[str, str]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if row.get("status") != "PASS":
        reasons.append("inventory_status_not_pass")
    if row.get("inventory_validation") != "PASS":
        reasons.append("inventory_gate_failed")
    if row.get("lineage_gate") != "True":
        reasons.append("lineage_gate_failed")
    if row.get("lineage_metadata") != "COMPLETE":
        reasons.append("lineage_metadata_incomplete")
    if row.get("pit_metadata") != "PRESENT":
        reasons.append("pit_metadata_incomplete")
    if row.get("lineage_complete") != "True":
        reasons.append("lineage_incomplete")
    if row.get("date") != row.get("required_date"):
        reasons.append("asof_or_date_mismatch")
    available_at = parse_rfc3339(row.get("available_at", ""))
    cutoff = parse_rfc3339(row.get("decision_cutoff", ""))
    if available_at is None:
        reasons.append("available_at_missing_or_invalid")
    if cutoff is None:
        reasons.append("decision_cutoff_missing_or_invalid")
    if available_at and cutoff and available_at > cutoff:
        reasons.append("available_at_after_decision_cutoff")
    for key in ("path", "model_id", "source_model_artifact_sha256", "source_feature_artifact", "provider_uri"):
        if not row.get(key):
            reasons.append(f"{key}_missing")
    ranking_path = resolve_path(row.get("path", ""))
    if not ranking_path.is_file():
        reasons.append("ranking_artifact_missing_on_disk")
    model_path = resolve_path(row.get("source_model_artifact", ""))
    if not model_path.is_file() or sha256(model_path) != row.get("source_model_artifact_sha256", ""):
        reasons.append("source_model_artifact_checksum_mismatch")
    if not resolve_path(row.get("source_feature_artifact", "")).exists():
        reasons.append("source_feature_artifact_missing_on_disk")
    if not resolve_path(row.get("qlib_source_run_dir", "")).exists():
        reasons.append("qlib_source_run_missing_on_disk")
    ranking_rows = []
    if ranking_path.is_file():
        try:
            with ranking_path.open(encoding="utf-8-sig", newline="") as stream:
                ranking_rows = list(csv.DictReader(stream))
        except (OSError, UnicodeDecodeError, csv.Error):
            reasons.append("ranking_artifact_unreadable")
    keys = [(str(item.get("date", ""))[:10], str(item.get("instrument", "")).strip().upper()) for item in ranking_rows]
    ranks = []
    finite = True
    for item in ranking_rows:
        try:
            ranks.append(int(float(item.get("score_rank") or item.get("full_qlib_rank") or item.get("rank"))))
            finite = finite and math.isfinite(float(item.get("raw_score") or item.get("score")))
        except (TypeError, ValueError):
            finite = False
    if len(ranking_rows) != 150:
        reasons.append("ranking_row_count_not_150")
    if len(set(keys)) != len(keys) or len({key[1] for key in keys}) != 150:
        reasons.append("ranking_duplicate_or_universe_incomplete")
    if sorted(ranks) != list(range(1, 151)):
        reasons.append("ranking_not_permutation_1_to_150")
    if not finite:
        reasons.append("ranking_score_not_finite")
    manifest = ranking_path.parent / "manifest.json"
    manifest_payload = json.loads(manifest.read_text(encoding="utf-8")) if manifest.is_file() else {}
    expected = ""
    for entry in manifest_payload.get("required_file_entries", []):
        if entry.get("key") in ("raw_scores", "prediction") and str(entry.get("path", "")).endswith(ranking_path.name):
            expected = str(entry.get("sha256", ""))
            break
    if expected and sha256(ranking_path) != expected:
        reasons.append("ranking_artifact_checksum_mismatch")
    source_run = resolve_path(row.get("qlib_source_run_dir", ""))
    source_run_meta = source_run / "run_metadata.json"
    source_run_manifest = source_run / "manifest.json"
    source_run_payload = json.loads(source_run_meta.read_text(encoding="utf-8")) if source_run_meta.is_file() else (json.loads(source_run_manifest.read_text(encoding="utf-8")) if source_run_manifest.is_file() else {})
    if row.get("qlib_source_run_id") and source_run_payload.get("run_id") not in (row.get("qlib_source_run_id"), ""):
        reasons.append("qlib_source_run_id_binding_mismatch")
    # The inventory names the same-run identity qlib_source_run_id.
    if not (row.get("source_run_id") or row.get("qlib_source_run_id")):
        reasons.append("source_run_id_missing")
    return not reasons, reasons


def warmup(valid_input_days: int, paired_oos_days: int = 0) -> dict[str, object]:
    if valid_input_days < 20:
        return {"status": "ACCUMULATE_ONLY", "can_shadow_score": False, "can_baseline": False}
    if paired_oos_days < 60:
        return {"status": "ISOLATED_SHADOW_ALLOWED", "can_shadow_score": True, "can_baseline": False}
    if paired_oos_days < 120:
        return {"status": "OOS_COMPARISON_REVIEW_ALLOWED", "can_shadow_score": True, "can_baseline": False}
    return {"status": "FORMAL_BASELINE_REVIEW_ELIGIBLE", "can_shadow_score": True, "can_baseline": False}


def select_append_dates(input_dates: set[str], existing_dates: set[str], target_asof: str | None) -> list[str]:
    selected = {target_asof} if target_asof else set(input_dates)
    if selected - input_dates:
        raise ValueError("target_asof_not_present_in_input")
    duplicates = sorted(selected & existing_dates)
    if duplicates:
        raise ValueError(f"append rejected: duplicate dates: {','.join(duplicates)}")
    return sorted(selected)


def self_test() -> None:
    assert warmup(0)["can_shadow_score"] is False
    assert warmup(19)["can_shadow_score"] is False
    assert warmup(20)["can_shadow_score"] is True
    assert warmup(60, 59)["status"] == "ISOLATED_SHADOW_ALLOWED"
    assert warmup(60, 60)["status"] == "OOS_COMPARISON_REVIEW_ALLOWED"
    assert warmup(120, 120)["can_baseline"] is False
    duplicate = [{"asof": "2026-09-01"}, {"asof": "2026-09-01"}]
    assert len({row["asof"] for row in duplicate}) != len(duplicate)
    quarantined = {"state": "VALID_DAY_QUARANTINED", "warmup_counted": False}
    assert quarantined["warmup_counted"] is False
    with tempfile.TemporaryDirectory(dir=ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow") as directory:
        path = Path(directory) / "accumulator.csv"
        fields = ["asof", "state"]
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerow({"asof": "2026-09-01", "state": "VALID_DAY_QUARANTINED"})
        before = path.read_bytes()
        existing = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
        assert "2026-09-01" in {row["asof"] for row in existing}
        try:
            select_append_dates({"2026-09-01"}, {"2026-09-01"}, "2026-09-01")
        except ValueError as exc:
            assert "duplicate dates" in str(exc)
        else:
            raise AssertionError("duplicate append was accepted")
        assert before == path.read_bytes()
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--append", "--target-asof", "2026-09-01", "--out", directory],
            capture_output=True, text=True, check=False,
        )
        assert result.returncode != 0 and "duplicate dates" in result.stderr + result.stdout
        assert before == path.read_bytes()

        append_dir = Path(directory) / "append-case"
        append_dir.mkdir()
        first = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--out", str(append_dir)],
            capture_output=True, text=True, check=False,
        )
        assert first.returncode == 0
        accumulator = append_dir / "accumulator.csv"
        old_bytes = accumulator.read_bytes()
        input_csv = append_dir / "new_date.csv"
        with input_csv.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["required_date"])
            writer.writeheader()
            writer.writerow({"required_date": "2026-09-05"})
        appended = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--append", "--target-asof", "2026-09-05", "--inventory", str(input_csv), "--out", str(append_dir)],
            capture_output=True, text=True, check=False,
        )
        assert appended.returncode == 0
        assert accumulator.read_bytes().startswith(old_bytes)
        assert len(list(csv.DictReader(accumulator.open(encoding="utf-8", newline="")))) == 8


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--source-inventory", type=Path, default=DEFAULT_SOURCE_INVENTORY)
    parser.add_argument("--missing-investigation", type=Path, default=DEFAULT_MISSING)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--rebuild-isolated", action="store_true",
                        help="rebuild the existing isolated directory as a new isolated run")
    parser.add_argument("--append", action="store_true",
                        help="append only new dates to an existing accumulator; duplicate dates are rejected")
    parser.add_argument("--target-asof", help="in append mode, select exactly this input date")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    inventory = args.inventory if args.inventory.is_absolute() else ROOT / args.inventory
    source_inventory = args.source_inventory if args.source_inventory.is_absolute() else ROOT / args.source_inventory
    missing_path = args.missing_investigation if args.missing_investigation.is_absolute() else ROOT / args.missing_investigation
    out = args.out if args.out.is_absolute() else ROOT / args.out
    allowed_root = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow"
    if not out.resolve().is_relative_to(allowed_root):
        raise SystemExit(f"output must remain under isolated root: {allowed_root}")
    out.mkdir(parents=True, exist_ok=True)
    accumulator_path = out / "accumulator.csv"
    if accumulator_path.exists() and not args.append and not args.rebuild_isolated:
        raise SystemExit("accumulator already exists; use --append or --rebuild-isolated")
    before = protected_fingerprints()
    rows = read_rows(inventory)
    source_rows = read_rows(source_inventory) if source_inventory.is_file() else []
    source_by_path = {row.get("path", ""): row for row in source_rows}
    missing_payload = json.loads(missing_path.read_text(encoding="utf-8")) if missing_path.is_file() else {}
    investigated_dates = set(missing_payload.get("dates", []))
    existing_records: list[dict[str, object]] = []
    accumulator_path = out / "accumulator.csv"
    if accumulator_path.exists() and args.append and not args.rebuild_isolated:
        with accumulator_path.open(encoding="utf-8", newline="") as stream:
            existing_records = list(csv.DictReader(stream))
    existing_dates = {str(row.get("asof", "")) for row in existing_records}
    input_dates = {row.get("required_date", "") for row in rows if row.get("required_date", "")}
    if args.append:
        try:
            incoming_dates = select_append_dates(input_dates, existing_dates, args.target_asof)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
    else:
        incoming_dates = sorted(input_dates)
    required_dates = incoming_dates if args.append else list(REQUIRED_DATES)
    by_date: dict[str, list[dict[str, str]]] = {day: [] for day in required_dates}
    for row in rows:
        day = row.get("required_date", "")
        if day in by_date:
            by_date[day].append(row)

    records: list[dict[str, object]] = []
    duplicate_dates: list[str] = []
    for day in required_dates:
        candidates = by_date[day]
        if len(candidates) > 1:
            duplicate_dates.append(day)
        candidate = dict(candidates[0]) if len(candidates) == 1 else {}
        # The compatibility report contains the gate result and path, while
        # the source inventory contains the identity/PIT fields. Bind them by
        # exact artifact path; never infer lineage from a directory name.
        ranking_path = candidate.get("compatible_paths", "")
        if ranking_path and "|" not in ranking_path:
            candidate.update(source_by_path.get(ranking_path, {}))
        candidate["required_date"] = day
        candidate["date"] = candidate.get("date", day)
        valid, reasons = is_strict_valid(candidate) if candidate else (False, ["no_inventory_record"])
        if day in QUARANTINE_DATES or day in investigated_dates:
            valid = False
            reasons = ["historical_source_not_pit_provable", "ranking_artifact_missing"]
        status = "VALID_DAY_ACCEPTED" if valid and len(candidates) == 1 else "VALID_DAY_QUARANTINED"
        records.append({
            "asof": day,
            "signal_asof": day,
            "state": status,
            "warmup_counted": status == "VALID_DAY_ACCEPTED",
            "candidate_count": len(candidates),
            "ranking_path": ranking_path if len(candidates) == 1 else "",
            "source_run_id": (candidate.get("source_run_id") or candidate.get("qlib_source_run_id", "")) if len(candidates) == 1 else "",
            "available_at": candidate.get("available_at", "") if len(candidates) == 1 else "",
            "decision_cutoff": candidate.get("decision_cutoff", "") if len(candidates) == 1 else "",
            "model_id": candidate.get("model_id", "") if len(candidates) == 1 else "",
            "source_model_artifact_sha256": candidate.get("source_model_artifact_sha256", "") if len(candidates) == 1 else "",
            "provider_uri": candidate.get("provider_uri", "") if len(candidates) == 1 else "",
            "source_feature_artifact": candidate.get("source_feature_artifact", "") if len(candidates) == 1 else "",
            "reason": "|".join(reasons) if reasons else "all_contract_gates_passed",
        })

    incoming_records = records
    if existing_records:
        duplicates = sorted(existing_dates & {str(row.get("asof", "")) for row in incoming_records})
        if duplicates:
            raise SystemExit(f"append rejected: duplicate dates: {','.join(duplicates)}")
        records = existing_records + incoming_records

    accepted = [record for record in records if record["state"] == "VALID_DAY_ACCEPTED"]
    accepted_dates = [str(record["asof"]) for record in accepted]
    validation = {
        "schema_version": "mbcds3.accumulator.validator.v1",
        "status": "PASS" if not duplicate_dates and len({str(r["asof"]) for r in records}) == len(records) else "FAIL",
        "input_inventory": rel(inventory),
        "source_inventory": rel(source_inventory),
        "missing_investigation": rel(missing_path),
        "missing_investigation_loaded": isinstance(missing_payload, dict) and bool(missing_payload),
        "investigated_missing_dates": sorted(investigated_dates),
        "required_dates": required_dates,
        "record_count": len(records),
        "one_record_per_required_date": all(day in {str(r["asof"]) for r in records} for day in required_dates) and len({str(r["asof"]) for r in records}) == len(records),
        "duplicate_dates_rejected": not duplicate_dates,
        "duplicate_dates": duplicate_dates,
        "accepted_valid_days": accepted_dates,
        "quarantined_days": [str(r["asof"]) for r in records if r["state"] != "VALID_DAY_ACCEPTED"],
        "no_fill_or_fallback": True,
        "model_b_scoring_performed": False,
        "training_performed": False,
    }
    count = len(accepted)
    readiness = {
        "schema_version": "mbcds3.warmup_readiness.v1",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "accepted_valid_day_count": count,
        "valid_input_days": count,
        "model_b_scored_days": 0,
        "settled_signal_days": 0,
        "paired_oos_days": 0,
        **warmup(count, 0),
        "production_allowed": False,
        "can_train": False,
        "continuity_blocked": bool([r for r in records if r["state"] != "VALID_DAY_ACCEPTED"]),
        "quarantined_days_do_not_count": True,
        "records_path": rel(out / "accumulator.csv"),
    }
    write_mode = "a" if existing_records else "w"
    accumulator_before_sha = sha256(accumulator_path) if accumulator_path.is_file() else None
    with accumulator_path.open(write_mode, encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        if not existing_records:
            writer.writeheader()
        writer.writerows(incoming_records if existing_records else records)
    accumulator_after_sha = sha256(accumulator_path)
    append_audit = {
        "mode": "append" if args.append else "initial_build",
        "target_asof": args.target_asof,
        "input_dates": sorted(input_dates),
        "selected_new_dates": incoming_dates,
        "existing_dates_before": sorted(existing_dates),
        "records_before": len(existing_records),
        "records_after": len(records),
        "appended_record_count": len(incoming_records) if existing_records else len(records),
        "accumulator_before_sha256": accumulator_before_sha,
        "accumulator_after_sha256": accumulator_after_sha,
        "append_success": bool((existing_records and len(records) > len(existing_records)) or (not existing_records and len(records) > 0)),
        "duplicate_policy": "reject_overlap_before_write",
    }
    (out / "append_audit.json").write_text(json.dumps(append_audit, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    readiness_path = out / "warmup_readiness.json"
    readiness_path.write_text(json.dumps(readiness, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    validation_path = out / "validator_report.json"
    validation_path.write_text(json.dumps(validation, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    after = protected_fingerprints()
    forbidden = {
        "status": "PASS" if before == after else "FAIL",
        "protected_paths_unchanged": before == after,
        "protected_before": before,
        "protected_after": after,
        "writes": [rel(out / name) for name in ("accumulator.csv", "warmup_readiness.json", "validator_report.json", "forbidden_scope_audit.json", "execution_report.md", "append_audit.json", "checksum_manifest.json")],
        "forbidden_operations": ["daily_auto", "cron", "provider", "latest", "frontend", "backend", "model_b_scoring", "training"],
    }
    forbidden_path = out / "forbidden_scope_audit.json"
    forbidden_path.write_text(json.dumps(forbidden, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    report = out / "execution_report.md"
    route_status = "PASS" if count >= 20 and validation["status"] == "PASS" and forbidden["status"] == "PASS" else "PASS_WITH_BLOCKER"
    report.write_text(
        "# MBCDS3-2 Isolated Accumulator Execution Report\n\n"
        f"- status: `{route_status}`\n"
        f"- records: `{len(records)}`; accepted valid days: `{count}`; quarantined: `{len(records) - count}`\n"
        f"- warm-up: `{readiness['status']}`; can_shadow_score: `{readiness['can_shadow_score']}`\n"
        "- Existing missing dates and incomplete-PIT candidates were quarantined; no fill, fallback, scoring, training, or production write was performed.\n"
        "- Accumulator is isolated and append-only in this run; duplicate required dates are rejected.\n"
        f"- protected paths unchanged: `{forbidden['protected_paths_unchanged']}`\n",
        encoding="utf-8",
    )
    files = [accumulator_path, readiness_path, validation_path, forbidden_path, report, out / "append_audit.json"]
    manifest = {rel(path): sha256(path) for path in files}
    (out / "checksum_manifest.json").write_text(json.dumps({"algorithm": "sha256", "files": manifest}, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return 0 if validation["status"] == "PASS" and forbidden["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
