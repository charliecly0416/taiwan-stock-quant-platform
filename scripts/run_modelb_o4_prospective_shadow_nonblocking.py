#!/usr/bin/env python3
"""Run the strict O4 prospective shadow as an isolated nonblocking adapter.

This adapter owns orchestration only.  The 78-feature bridge, scorer, and
ledger contract remain in ``build_modelb_o4_prospective_shadow.py``.
Missing inputs and scorer failures become terminal job evidence and return
success to the daily orchestrator so Model A remains unaffected.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_modelb_o4_prospective_shadow.py"
VALIDATOR = ROOT / "scripts/validate_modelb_o4_prospective_shadow.py"
DEFAULT_LEDGER = ROOT / "data_tw/experiments/project_runtime_convergence/o4_prospective_shadow_ledger/observations.csv"
PROTECTED = (
    ROOT / "configs/active_baseline_descriptor.yaml",
    ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    ROOT / "data_tw/artifacts/agent_daily_prompt/latest.json",
    ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt",
    ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt",
    ROOT / "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron",
)


def fingerprint() -> dict[str, Any]:
    result = {}
    for path in PROTECTED:
        result[str(path.relative_to(ROOT))] = {
            "exists": path.exists(),
            "size": path.stat().st_size if path.is_file() else None,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None,
        }
    return result


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def terminal(job_dir: Path, *, status: str, asof: str, reason: str, before: dict[str, Any], **extra: Any) -> dict[str, Any]:
    after = fingerprint()
    payload = {
        "schema_version": "o4.prospective_shadow_nonblocking.v1",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "asof": asof,
        "reason": reason,
        "no_publish": True,
        "no_baseline_switch": True,
        "model_a_nonblocking": True,
        "protected_before": before,
        "protected_after": after,
        "protected_unchanged": before == after,
        **extra,
    }
    write_json(job_dir / "o4_prospective_shadow_status.json", payload)
    return payload


def run(args: argparse.Namespace) -> dict[str, Any]:
    job_dir = args.job_dir.resolve()
    before = fingerprint()
    output_dir = (Path(args.output_dir) if args.output_dir else (ROOT / "data_tw/experiments/project_runtime_convergence" / f"o4_prospective_bridge_{args.asof}" / "shadow_observation")).expanduser().resolve()
    ledger = (Path(args.ledger) if args.ledger else DEFAULT_LEDGER).expanduser().resolve()
    required = {
        "daily_price_adapter": args.daily_price_adapter,
        "institutional_adapter": args.institutional_adapter,
        "margin_adapter": args.margin_adapter,
        "twii_raw": args.twii_raw,
        "twii_capture": args.twii_capture,
        "calendar": args.calendar,
    }
    missing = [name for name, value in required.items() if not value or not Path(value).exists()]
    if len(args.model_a_signals) != 6 or any(not Path(value).exists() for value in args.model_a_signals):
        missing.append("model_a_signals_six_sessions")
    if missing:
        return terminal(job_dir, status="BLOCKED_SOURCE_NOT_READY_NONBLOCKING", asof=args.asof, reason="required O4 inputs are missing or not six immutable Model A sessions", before=before, missing_inputs=missing, output_dir=rel(output_dir), ledger=rel(ledger))
    if not output_dir.resolve().is_relative_to((ROOT / "data_tw/experiments").resolve()) or not ledger.resolve().is_relative_to((ROOT / "data_tw/experiments").resolve()):
        return terminal(job_dir, status="STOP_PATH_OUTSIDE_ISOLATED_ROOT_NONBLOCKING", asof=args.asof, reason="O4 output and ledger must remain under data_tw/experiments", before=before)
    command = [
        sys.executable, str(BUILDER), "--asof", args.asof, "--source-run-id", args.source_run_id,
        "--decision-cutoff", args.decision_cutoff,
    ]
    for signal in args.model_a_signals:
        command.extend(["--model-a-signals", signal])
    for key in ("daily_price_adapter", "institutional_adapter", "margin_adapter", "twii_raw", "twii_capture", "calendar"):
        command.extend([f"--{key.replace('_', '-')}", required[key]])
    command.extend(["--output-dir", str(output_dir), "--ledger", str(ledger), "--json"])
    try:
        completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    except Exception as exc:
        return terminal(job_dir, status="STOP_SCORER_EXCEPTION_NONBLOCKING", asof=args.asof, reason=str(exc), before=before, command=command)
    if completed.returncode != 0:
        return terminal(job_dir, status="STOP_SCORER_FAILED_NONBLOCKING", asof=args.asof, reason="O4 builder returned non-zero", before=before, command=command, returncode=completed.returncode, stdout_tail=completed.stdout[-4000:], stderr_tail=completed.stderr[-4000:])
    validation_command = [sys.executable, str(VALIDATOR), "--artifact-dir", str(output_dir), "--ledger", str(ledger), "--json"]
    validation = subprocess.run(validation_command, cwd=ROOT, text=True, capture_output=True, check=False)
    if validation.returncode != 0:
        return terminal(job_dir, status="STOP_VALIDATOR_FAILED_NONBLOCKING", asof=args.asof, reason="O4 validator rejected builder output", before=before, command=command, validation_command=validation_command, returncode=validation.returncode, validator_stdout_tail=validation.stdout[-4000:], validator_stderr_tail=validation.stderr[-4000:])
    return terminal(job_dir, status="O4_VALIDATED_OBSERVATION_NONBLOCKING", asof=args.asof, reason="strict O4 builder and independent validator completed", before=before, command=command, validation_command=validation_command, output_dir=rel(output_dir), ledger=rel(ledger), stdout_tail=completed.stdout[-4000:], validator_stdout_tail=validation.stdout[-4000:])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asof", required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--decision-cutoff", required=True)
    parser.add_argument("--job-dir", required=True, type=Path)
    parser.add_argument("--model-a-signals", action="append", default=[])
    parser.add_argument("--daily-price-adapter", default="")
    parser.add_argument("--institutional-adapter", default="")
    parser.add_argument("--margin-adapter", default="")
    parser.add_argument("--twii-raw", default="")
    parser.add_argument("--twii-capture", default="")
    parser.add_argument("--calendar", default="")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--ledger", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = run(args)
    if args.json:
        print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
