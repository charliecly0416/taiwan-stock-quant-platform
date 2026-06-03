#!/usr/bin/env python3
"""Daily unattended Taiwan stock data + qlib Option C update.

This single entrypoint is meant for cron/systemd:
1. Pick the asof date automatically in Asia/Taipei.
2. Update QuantDinger raw Taiwan stock archives from FinMind.
3. Refresh Yahoo/Scrapling adjusted data and rebuild/publish the Option C qlib provider.
4. Publish accepted latest signals for backend/frontend display.

Research-only: no broker connection, no order generation, no positions.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
QLIB = ROOT / "qlib_pipeline"
OPS_ROOT = ROOT / "data_tw/ops/daily_auto_update"
UNIVERSE = QLIB / "data_tw/experiments/option_c_forward_validation/timed_data_availability_retry_20260601T101323Z/symbols_accepted_prediction_universe.txt"
LATEST = QLIB / "data_tw/experiments/option_c_daily_signal/latest_signal.json"
CALENDAR = QLIB / "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt"
PENDING_ASOF = OPS_ROOT / "pending_asof.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def taipei_today() -> str:
    return datetime.now(ZoneInfo("Asia/Taipei")).date().isoformat()


def resolve_asof(explicit_asof: str) -> tuple[str, str]:
    if explicit_asof.strip():
        return explicit_asof.strip(), "explicit"
    pending = read_json(PENDING_ASOF)
    pending_asof = str(pending.get("asof") or "").strip()
    if pending_asof:
        return pending_asof, "pending"
    return taipei_today(), "taipei_today"


def set_pending_asof(asof: str, *, reason: str, job_id: str) -> None:
    write_json(PENDING_ASOF, {
        "asof": asof,
        "reason": reason,
        "job_id": job_id,
        "updated_at": utc_now(),
    })


def clear_pending_asof(asof: str) -> None:
    pending = read_json(PENDING_ASOF)
    if str(pending.get("asof") or "") == asof:
        try:
            PENDING_ASOF.unlink()
        except FileNotFoundError:
            pass


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def run_cmd(argv: list[str], *, cwd: Path, stdout_path: Path, stderr_path: Path, timeout: int) -> dict[str, Any]:
    completed = subprocess.run(
        argv,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    stdout_path.write_text(completed.stdout or "", encoding="utf-8")
    stderr_path.write_text(completed.stderr or "", encoding="utf-8")
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "argv": argv,
        "cwd": str(cwd),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "stdout_tail": (completed.stdout or "")[-3000:],
        "stderr_tail": (completed.stderr or "")[-3000:],
    }


def latest_asof() -> str:
    latest = read_json(LATEST)
    if latest.get("status") == "accepted":
        return str(latest.get("asof") or "")
    return ""


def materialize_symbols(job_dir: Path) -> Path:
    symbols: list[str] = []
    if UNIVERSE.exists():
        for line in UNIVERSE.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue
            code = raw.removeprefix("TW").strip()
            if code and code not in symbols:
                symbols.append(code)
    if not symbols:
        symbols = ["2330", "0050"]
    path = job_dir / "finmind_symbols.txt"
    path.write_text("\n".join(symbols) + "\n", encoding="utf-8")
    return path


def publish_accepted_latest(asof: str) -> dict[str, Any]:
    sys.path.insert(0, str(BACKEND))
    os.environ.setdefault("ENABLE_TW_QLIB_OPTION_C_SCHEDULER", "true")
    os.environ.setdefault("TW_QLIB_OPTION_C_SCHEDULER_MODE", "dry-run-only")
    os.environ.setdefault("ENABLE_TW_QLIB_OPTION_C_NORMAL_PUBLISH", "true")
    os.environ.setdefault("TW_QLIB_OPTION_C_NORMAL_PUBLISH_MODE", "accepted-latest-publish-review")
    os.environ.setdefault("ENABLE_TW_QLIB_OPTION_C_ACCEPTED_LATEST_SCHEDULER", "true")
    os.environ.setdefault("TW_QLIB_OPTION_C_ACCEPTED_LATEST_SCHEDULER_MODE", "accepted-latest-scheduler-review")
    os.environ.setdefault("TW_OPTION_C_OPS_ROOT", str(ROOT / "data_tw/ops/option_c_jobs"))
    os.environ.setdefault("QLIB_TW_OPTION_C_CWD", str(QLIB))
    os.environ.setdefault("TW_QLIB_OPTION_C_CWD", str(QLIB))
    os.environ.setdefault("QLIB_TW_OPTION_C_ROOT", str(QLIB / "data_tw/experiments/option_c_daily_signal"))
    os.environ.setdefault("QLIB_TW_OPTION_C_LATEST_SIGNAL", str(LATEST))
    os.environ.setdefault("TW_QLIB_OPTION_C_LATEST_SIGNAL", str(LATEST))
    os.environ.setdefault("TW_QLIB_OPTION_C_PROVIDER_CALENDAR", str(CALENDAR))
    os.environ.setdefault("TW_QLIB_OPTION_C_EXPECTED_UNIVERSE", str(UNIVERSE))

    from app.services.tw_stock_qlib_option_c_accepted_latest_scheduler import (  # noqa: WPS433
        OptionCAcceptedLatestSchedulerConfig,
        QlibOptionCAcceptedLatestScheduler,
    )
    from app.services.tw_stock_qlib_option_c_normal_publish import (  # noqa: WPS433
        OptionCNormalPublishConfig,
        QlibOptionCNormalPublishGate,
    )
    from app.services.tw_stock_qlib_option_c_scheduler import (  # noqa: WPS433
        OptionCSchedulerConfig,
        QlibOptionCDryRunScheduler,
    )

    scheduler = QlibOptionCAcceptedLatestScheduler(
        config=OptionCAcceptedLatestSchedulerConfig.from_env(),
        dry_run_scheduler=QlibOptionCDryRunScheduler(config=OptionCSchedulerConfig.from_env()),
        normal_publish_gate=QlibOptionCNormalPublishGate(config=OptionCNormalPublishConfig.from_env()),
    )
    return scheduler.tick({"asof": asof, "confirm_accepted_latest_scheduler": True})


def main() -> int:
    parser = argparse.ArgumentParser(description="Run unattended daily TW stock FinMind + Yahoo/Scrapling + qlib update.")
    parser.add_argument("--asof", default="", help="YYYY-MM-DD. Default: Asia/Taipei today.")
    parser.add_argument("--force", action="store_true", help="Run even when latest_signal already has target asof.")
    parser.add_argument("--skip-finmind", action="store_true")
    parser.add_argument("--skip-qlib", action="store_true")
    parser.add_argument("--finmind-scope", choices=["full", "daily"], default=os.getenv("TW_DAILY_AUTO_FINMIND_SCOPE", "full"))
    parser.add_argument("--finmind-lookback-days", type=int, default=int(os.getenv("TW_DAILY_AUTO_FINMIND_LOOKBACK_DAYS", "10")))
    parser.add_argument("--skip-finmind-validate", action="store_true", default=os.getenv("TW_DAILY_AUTO_SKIP_FINMIND_VALIDATE", "true").lower() in {"1", "true", "yes", "on"})
    parser.add_argument("--refresh-timeout", type=float, default=float(os.getenv("TW_DAILY_AUTO_YAHOO_TIMEOUT", "30")))
    parser.add_argument("--refresh-retries", type=int, default=int(os.getenv("TW_DAILY_AUTO_YAHOO_RETRIES", "1")))
    parser.add_argument("--refresh-sleep-seconds", type=float, default=float(os.getenv("TW_DAILY_AUTO_YAHOO_SLEEP_SECONDS", "0.5")))
    parser.add_argument("--max-workers", type=int, default=int(os.getenv("TW_DAILY_AUTO_MAX_WORKERS", "4")))
    parser.add_argument("--proxy", default=os.getenv("TW_DAILY_AUTO_YAHOO_PROXY", ""))
    parser.add_argument("--timeout-seconds", type=int, default=int(os.getenv("TW_DAILY_AUTO_TIMEOUT_SECONDS", "1200")))
    args = parser.parse_args()

    asof, asof_source = resolve_asof(args.asof)
    job_id = f"daily_tw_stock_auto_update_{asof.replace('-', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    job_dir = OPS_ROOT / job_id
    job_dir.mkdir(parents=True, exist_ok=False)
    job: dict[str, Any] = {
        "job_id": job_id,
        "status": "running",
        "asof": asof,
        "asof_source": asof_source,
        "started_at": utc_now(),
        "research_only": True,
        "trading": {"orders_enabled": False, "connects_to_broker": False, "research_signal_not_order": True},
        "latest_before": latest_asof(),
        "finmind_update_triggered": False,
        "yahoo_refresh_triggered": False,
        "provider_publish_triggered": False,
        "latest_signal_updated": False,
    }
    write_json(job_dir / "job.json", job)

    if job["latest_before"] == asof and not args.force:
        clear_pending_asof(asof)
        job.update({"status": "already_up_to_date", "finished_at": utc_now(), "latest_after": job["latest_before"], "pending_asof_cleared": True})
        write_json(job_dir / "job.json", job)
        print(json.dumps(job, ensure_ascii=False, indent=2))
        return 0

    symbols_file = materialize_symbols(job_dir)
    if not args.skip_finmind:
        start = (datetime.strptime(asof, "%Y-%m-%d").date() - timedelta(days=max(1, args.finmind_lookback_days))).isoformat()
        finmind_argv = [
            "python",
            "backend/scripts/update_tw_stock_daily.py",
            "--symbols-file",
            str(symbols_file),
            "--start",
            start,
            "--end",
            asof,
            "--apply",
        ]
        if args.skip_finmind_validate:
            finmind_argv.append("--no-validate")
        if args.finmind_scope == "daily":
            finmind_argv.extend(["--no-corporate-actions", "--no-institutional", "--no-margin", "--no-monthly-revenue", "--no-valuation"])
        job["finmind_update"] = run_cmd(finmind_argv, cwd=ROOT, stdout_path=job_dir / "finmind_stdout.txt", stderr_path=job_dir / "finmind_stderr.txt", timeout=args.timeout_seconds)
        job["finmind_update_triggered"] = True
        if not job["finmind_update"].get("ok"):
            job["finmind_update_warning"] = "FinMind/QuantDinger raw archive did not fully pass; Yahoo/qlib update continues."
        write_json(job_dir / "job.json", job)

    if not args.skip_qlib:
        refresh_job_id = f"option_c_yahoo_scrapling_refresh_{asof.replace('-', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_daily_auto"
        refresh_argv = [
            "python",
            "examples/tw/run_option_c_yahoo_scrapling_refresh.py",
            "--asof",
            asof,
            "--start",
            "2015-01-01",
            "--universe",
            "option_c_accepted_150",
            "--output-root",
            "data_tw/experiments/option_c_ops",
            "--job-id",
            refresh_job_id,
            "--timeout",
            str(args.refresh_timeout),
            "--retries",
            str(args.refresh_retries),
            "--sleep-seconds",
            str(args.refresh_sleep_seconds),
            "--continue-on-error",
            "--suffix",
            "auto",
            "--max-workers",
            str(args.max_workers),
            "--report-path",
            str(job_dir / "refresh_report.md"),
        ]
        if args.proxy.strip():
            idx = refresh_argv.index("--timeout")
            refresh_argv[idx:idx] = ["--proxy", args.proxy.strip()]
        job["refresh_job_id"] = refresh_job_id
        job["yahoo_refresh"] = run_cmd(refresh_argv, cwd=QLIB, stdout_path=job_dir / "refresh_stdout.txt", stderr_path=job_dir / "refresh_stderr.txt", timeout=args.timeout_seconds)
        job["yahoo_refresh_triggered"] = True
        refresh_summary = read_json(QLIB / "data_tw/experiments/option_c_ops" / refresh_job_id / "reports/execution_summary.json")
        job["refresh_summary"] = refresh_summary
        write_json(job_dir / "job.json", job)
        if not job["yahoo_refresh"].get("ok") or refresh_summary.get("status") != "staged_refresh_complete_waiting_for_review":
            set_pending_asof(asof, reason="fresh_data_wait", job_id=job_id)
            job.update({"status": "fresh_data_wait", "message": "Yahoo/Scrapling did not produce complete asof data yet; next scheduled run should retry this same asof even after midnight.", "finished_at": utc_now(), "latest_after": latest_asof(), "pending_asof_set": asof})
            write_json(job_dir / "job.json", job)
            print(json.dumps(job, ensure_ascii=False, indent=2))
            return 2

        publish_job_id = f"option_c_yahoo_scrapling_publish_{asof.replace('-', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_daily_auto"
        publish_argv = [
            "python",
            "examples/tw/publish_option_c_yahoo_scrapling_refresh.py",
            "--job-dir",
            f"data_tw/experiments/option_c_ops/{refresh_job_id}",
            "--asof",
            asof,
            "--mode",
            "publish",
            "--provider-scope",
            "option_c_150",
            "--publish-job-id",
            publish_job_id,
            "--max-workers",
            str(args.max_workers),
            "--report-path",
            str(job_dir / "publish_report.md"),
        ]
        job["publish_job_id"] = publish_job_id
        job["provider_publish"] = run_cmd(publish_argv, cwd=QLIB, stdout_path=job_dir / "publish_stdout.txt", stderr_path=job_dir / "publish_stderr.txt", timeout=args.timeout_seconds)
        job["provider_publish_triggered"] = True
        publish_summary = read_json(QLIB / "data_tw/experiments/option_c_ops" / publish_job_id / "reports/publish_execution_summary.json")
        job["publish_summary"] = publish_summary
        write_json(job_dir / "job.json", job)
        if not job["provider_publish"].get("ok") or publish_summary.get("status") != "publish_complete_waiting_for_review":
            set_pending_asof(asof, reason="provider_publish_failed", job_id=job_id)
            job.update({"status": "provider_publish_failed", "message": "Formal qlib provider publish failed; latest_signal was not updated.", "finished_at": utc_now(), "latest_after": latest_asof(), "pending_asof_set": asof})
            write_json(job_dir / "job.json", job)
            print(json.dumps(job, ensure_ascii=False, indent=2))
            return 3

        accepted = publish_accepted_latest(asof)
        job["accepted_latest"] = accepted
        job["latest_signal_updated"] = bool(accepted.get("latest_signal_updated"))
        if not accepted.get("ok"):
            set_pending_asof(asof, reason="accepted_latest_failed", job_id=job_id)
            job.update({"status": "accepted_latest_failed", "message": accepted.get("message") or accepted.get("status"), "finished_at": utc_now(), "latest_after": latest_asof(), "pending_asof_set": asof})
            write_json(job_dir / "job.json", job)
            print(json.dumps(job, ensure_ascii=False, indent=2))
            return 4

    clear_pending_asof(asof)
    job.update({"status": "daily_auto_update_passed", "finished_at": utc_now(), "latest_after": latest_asof(), "pending_asof_cleared": True})
    write_json(job_dir / "job.json", job)
    print(json.dumps(job, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
