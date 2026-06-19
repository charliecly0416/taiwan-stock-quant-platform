#!/usr/bin/env python3
"""Daily unattended Taiwan stock data + qlib Option C update.

This single entrypoint is meant for cron/systemd:
1. Pick the asof date automatically in Asia/Taipei.
2. Update QuantDinger raw Taiwan stock archives from FinMind.
3. In the default M3 contract path, skip legacy Yahoo/Scrapling provider refresh/publish.
4. Optionally run legacy provider publish/latest only behind an explicit non-default gate.

Research-only: no broker connection, no order generation, no positions.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import traceback
from datetime import datetime, time, timedelta, timezone
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
READONLY_SNAPSHOT_ROOT = ROOT / "data_tw/artifacts/publish/readonly_strategy_snapshot"
READONLY_DAILY_INTEGRATION_AUDIT = READONLY_SNAPSHOT_ROOT / "daily_integration_audit.json"
READONLY_PUBLISH_SCRIPT = ROOT / "scripts/publish_tw_modular_readonly_snapshot.py"
READONLY_VALIDATE_SCRIPT = ROOT / "scripts/validate_tw_modular_readonly_snapshot.py"
READONLY_DEFAULT_TIMEOUT_SECONDS = 300


def load_local_env() -> None:
    """Load root/backend .env for cron without overriding explicit env."""
    for env_path in (ROOT / ".env", BACKEND / ".env"):
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not key or key in os.environ:
                continue
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            os.environ[key] = value


load_local_env()
PYTHON = os.getenv("TW_DAILY_AUTO_PYTHON", sys.executable)
TAIPEI = ZoneInfo("Asia/Taipei")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def taipei_today() -> str:
    return taipei_now().date().isoformat()


def taipei_now() -> datetime:
    return datetime.now(TAIPEI).replace(microsecond=0)


def parse_hhmm(raw: str) -> time:
    try:
        parsed = datetime.strptime(raw.strip(), "%H:%M")
    except ValueError as exc:
        raise ValueError(f"Invalid HH:MM time: {raw!r}") from exc
    return parsed.time()


def should_wait_before_pull(
    *,
    asof: str,
    asof_source: str,
    now_taipei: datetime,
    today_earliest_time: time,
    force: bool,
) -> tuple[bool, str]:
    if force:
        return False, ""
    if asof_source != "taipei_today":
        return False, ""
    today = now_taipei.date()
    if asof != today.isoformat():
        return False, ""
    if today.weekday() >= 5:
        return True, "weekend_no_pending_wait"
    if now_taipei.time() < today_earliest_time:
        return True, "today_data_window_wait"
    return False, ""


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


def rel_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def resolve_path(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def parse_json_stdout(command_result: dict[str, Any]) -> dict[str, Any]:
    raw_path = str(command_result.get("stdout_path") or "").strip()
    if not raw_path:
        return {}
    stdout_path = Path(raw_path)
    if not stdout_path.exists():
        return {}
    try:
        return json.loads(stdout_path.read_text(encoding="utf-8"))
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


def write_readonly_snapshot_latest_pointer(manifest_path: Path, *, out_root: Path = READONLY_SNAPSHOT_ROOT) -> Path:
    manifest = read_json(manifest_path)
    latest_path = out_root / "latest.json"
    write_json(
        latest_path,
        {
            "artifact_type": "readonly_strategy_snapshot_latest_pointer",
            "schema_version": "readonly_strategy_snapshot_latest_r13_v1",
            "asof": str(manifest.get("asof") or ""),
            "readonly_only": True,
            "production_trade_enabled": False,
            "snapshot_manifest": rel_path(manifest_path),
            "created_at": utc_now(),
            "created_by": "scripts/run_daily_tw_stock_auto_update.py",
            "not_provider_accepted_latest": True,
            "not_trade_target_latest": True,
        },
    )
    return latest_path


def run_readonly_strategy_snapshot_publish(
    *,
    asof: str,
    job_dir: Path,
    enabled: bool | None = None,
    dry_run: bool | None = None,
    out_root: Path = READONLY_SNAPSHOT_ROOT,
    timeout_seconds: int | None = None,
    command_runner=run_cmd,
) -> dict[str, Any]:
    enabled = env_flag("ENABLE_TW_READONLY_STRATEGY_SNAPSHOT_PUBLISH", False) if enabled is None else enabled
    dry_run = env_flag("TW_READONLY_STRATEGY_SNAPSHOT_DRY_RUN", True) if dry_run is None else dry_run
    result: dict[str, Any] = {
        "enabled": bool(enabled),
        "attempted": False,
        "ok": True,
        "dry_run": bool(dry_run),
        "manifest": "",
        "latest_updated": False,
        "validator_ok": False,
        "error": "",
    }
    if not enabled:
        return result

    result["attempted"] = True
    timeout = int(timeout_seconds or os.getenv("TW_READONLY_STRATEGY_SNAPSHOT_TIMEOUT_SECONDS", str(READONLY_DEFAULT_TIMEOUT_SECONDS)))
    publish_stdout = job_dir / "readonly_snapshot_publish_stdout.txt"
    publish_stderr = job_dir / "readonly_snapshot_publish_stderr.txt"
    publish_argv = [
        PYTHON,
        str(READONLY_PUBLISH_SCRIPT.relative_to(ROOT)),
        "--out-root",
        str(out_root),
        "--no-latest",
        "--json",
    ]
    publish_result = command_runner(
        publish_argv,
        cwd=ROOT,
        stdout_path=publish_stdout,
        stderr_path=publish_stderr,
        timeout=timeout,
    )
    result["publish"] = publish_result
    publish_payload = parse_json_stdout(publish_result)
    result["publish_payload"] = publish_payload
    manifest = str(publish_payload.get("manifest") or "")
    result["manifest"] = manifest
    if not publish_result.get("ok") or not publish_payload.get("ok") or not manifest:
        result.update({"ok": False, "error": "readonly snapshot writer failed"})
        return result

    validate_stdout = job_dir / "readonly_snapshot_validate_stdout.txt"
    validate_stderr = job_dir / "readonly_snapshot_validate_stderr.txt"
    validate_argv = [
        PYTHON,
        str(READONLY_VALIDATE_SCRIPT.relative_to(ROOT)),
        "--manifest",
        manifest,
        "--json",
    ]
    validate_result = command_runner(
        validate_argv,
        cwd=ROOT,
        stdout_path=validate_stdout,
        stderr_path=validate_stderr,
        timeout=timeout,
    )
    validate_payload = parse_json_stdout(validate_result)
    result["validator"] = validate_result
    result["validator_payload"] = validate_payload
    result["validator_ok"] = bool(validate_result.get("ok") and validate_payload.get("ok"))
    if not result["validator_ok"]:
        result.update({"ok": False, "error": "readonly snapshot validator failed"})
        return result

    if dry_run:
        return result

    latest_path = write_readonly_snapshot_latest_pointer(resolve_path(manifest), out_root=out_root)
    result["latest"] = rel_path(latest_path)
    result["latest_updated"] = True
    latest_stdout = job_dir / "readonly_snapshot_latest_validate_stdout.txt"
    latest_stderr = job_dir / "readonly_snapshot_latest_validate_stderr.txt"
    latest_validate_result = command_runner(
        [PYTHON, str(READONLY_VALIDATE_SCRIPT.relative_to(ROOT)), "--latest", "--json"],
        cwd=ROOT,
        stdout_path=latest_stdout,
        stderr_path=latest_stderr,
        timeout=timeout,
    )
    result["latest_validator"] = latest_validate_result
    result["latest_validator_payload"] = parse_json_stdout(latest_validate_result)
    if not latest_validate_result.get("ok"):
        result.update({"ok": False, "error": "readonly snapshot latest pointer validation failed"})
    return result


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
    os.environ.setdefault("TW_QLIB_OPTION_C_PYTHON", PYTHON)

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
    parser.add_argument(
        "--enable-legacy-provider-publish",
        action="store_true",
        default=env_flag("TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH", False),
        help="Explicit non-default legacy gate for Yahoo/Scrapling refresh, provider publish, and accepted latest switching.",
    )
    parser.add_argument("--finmind-scope", choices=["full", "daily"], default=os.getenv("TW_DAILY_AUTO_FINMIND_SCOPE", "full"))
    parser.add_argument("--finmind-lookback-days", type=int, default=int(os.getenv("TW_DAILY_AUTO_FINMIND_LOOKBACK_DAYS", "260")), help="FinMind TaiwanStockPrice archive lookback. Default 260d to keep qlib Top30/50 trend samples above 120 daily bars.")
    parser.add_argument("--skip-finmind-validate", action="store_true", default=os.getenv("TW_DAILY_AUTO_SKIP_FINMIND_VALIDATE", "true").lower() in {"1", "true", "yes", "on"})
    parser.add_argument("--refresh-timeout", type=float, default=float(os.getenv("TW_DAILY_AUTO_YAHOO_TIMEOUT", "30")))
    parser.add_argument("--refresh-retries", type=int, default=int(os.getenv("TW_DAILY_AUTO_YAHOO_RETRIES", "1")))
    parser.add_argument("--refresh-sleep-seconds", type=float, default=float(os.getenv("TW_DAILY_AUTO_YAHOO_SLEEP_SECONDS", "0.5")))
    parser.add_argument("--max-workers", type=int, default=int(os.getenv("TW_DAILY_AUTO_MAX_WORKERS", "4")))
    parser.add_argument("--proxy", default=os.getenv("TW_DAILY_AUTO_YAHOO_PROXY", ""))
    parser.add_argument("--timeout-seconds", type=int, default=int(os.getenv("TW_DAILY_AUTO_TIMEOUT_SECONDS", "1200")))
    parser.add_argument(
        "--today-earliest-time",
        default=os.getenv("TW_DAILY_AUTO_TODAY_EARLIEST_TIME", "18:00"),
        help="Earliest Asia/Taipei HH:MM time to pull same-day data when no pending asof exists.",
    )
    args = parser.parse_args()

    today_earliest_time = parse_hhmm(args.today_earliest_time)
    now_taipei = taipei_now()
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
        "python_executable": PYTHON,
        "taipei_now": now_taipei.isoformat(),
        "today_earliest_time": today_earliest_time.strftime("%H:%M"),
        "finmind_update_triggered": False,
        "finmind_lookback_days": int(args.finmind_lookback_days),
        "finmind_history_goal": "cover option_c_accepted_150 with enough daily bars for 120-bar cross-analysis trend samples",
        "yahoo_refresh_triggered": False,
        "provider_publish_triggered": False,
        "latest_signal_updated": False,
        "m3_contract_mode": "legacy_provider_publish_enabled" if args.enable_legacy_provider_publish else "readonly_orchestrator_default",
        "legacy_provider_publish_enabled": bool(args.enable_legacy_provider_publish),
        "legacy_provider_refresh_default_reachable": False,
        "legacy_provider_publish_default_reachable": False,
        "legacy_accepted_latest_default_reachable": False,
    }
    write_json(job_dir / "job.json", job)

    if job["latest_before"] == asof and not args.force:
        clear_pending_asof(asof)
        job.update({"status": "already_up_to_date", "finished_at": utc_now(), "latest_after": job["latest_before"], "pending_asof_cleared": True})
        write_json(job_dir / "job.json", job)
        print(json.dumps(job, ensure_ascii=False, indent=2))
        return 0

    should_wait, wait_status = should_wait_before_pull(
        asof=asof,
        asof_source=asof_source,
        now_taipei=now_taipei,
        today_earliest_time=today_earliest_time,
        force=args.force,
    )
    if should_wait:
        message = (
            "No pending asof exists and the resolved target is today; same-day data pulls wait until the configured Asia/Taipei data window."
            if wait_status == "today_data_window_wait"
            else "No pending asof exists and the resolved target is a weekend date; no data pull was started."
        )
        job.update({
            "status": wait_status,
            "message": message,
            "finished_at": utc_now(),
            "latest_after": job["latest_before"],
            "today_data_window_open": False,
        })
        write_json(job_dir / "job.json", job)
        print(json.dumps(job, ensure_ascii=False, indent=2))
        return 0

    job["today_data_window_open"] = True
    write_json(job_dir / "job.json", job)

    symbols_file = materialize_symbols(job_dir)
    if not args.skip_finmind:
        start = (datetime.strptime(asof, "%Y-%m-%d").date() - timedelta(days=max(1, args.finmind_lookback_days))).isoformat()
        finmind_argv = [
            PYTHON,
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

    if not args.skip_qlib and not args.enable_legacy_provider_publish:
        job["qlib_legacy_provider_path_skipped"] = True
        job["qlib_legacy_provider_skip_reason"] = "m3_readonly_orchestrator_default_requires_explicit_enable_legacy_provider_publish"
        write_json(job_dir / "job.json", job)

    if not args.skip_qlib and args.enable_legacy_provider_publish:
        refresh_job_id = f"option_c_yahoo_scrapling_refresh_{asof.replace('-', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_daily_auto"
        refresh_argv = [
            PYTHON,
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
            PYTHON,
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

        try:
            accepted = publish_accepted_latest(asof)
        except Exception as exc:  # Keep the target asof retryable if the final accepted-latest stage crashes.
            set_pending_asof(asof, reason="accepted_latest_exception", job_id=job_id)
            job["accepted_latest_exception"] = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback_tail": traceback.format_exc()[-4000:],
            }
            job.update({
                "status": "accepted_latest_exception",
                "message": str(exc),
                "finished_at": utc_now(),
                "latest_after": latest_asof(),
                "pending_asof_set": asof,
            })
            write_json(job_dir / "job.json", job)
            print(json.dumps(job, ensure_ascii=False, indent=2))
            return 4
        job["accepted_latest"] = accepted
        job["latest_signal_updated"] = bool(accepted.get("latest_signal_updated"))
        if not accepted.get("ok"):
            set_pending_asof(asof, reason="accepted_latest_failed", job_id=job_id)
            job.update({"status": "accepted_latest_failed", "message": accepted.get("message") or accepted.get("status"), "finished_at": utc_now(), "latest_after": latest_asof(), "pending_asof_set": asof})
            write_json(job_dir / "job.json", job)
            print(json.dumps(job, ensure_ascii=False, indent=2))
            return 4

    clear_pending_asof(asof)
    readonly_snapshot = run_readonly_strategy_snapshot_publish(asof=asof, job_dir=job_dir)
    job["readonly_snapshot"] = readonly_snapshot
    if readonly_snapshot.get("attempted"):
        write_json(READONLY_DAILY_INTEGRATION_AUDIT, {"job_id": job_id, "asof": asof, "created_at": utc_now(), **readonly_snapshot})
    if readonly_snapshot.get("attempted") and not readonly_snapshot.get("ok"):
        job["readonly_snapshot_warning"] = readonly_snapshot.get("error") or "readonly snapshot publish failed"
    job.update({"status": "daily_auto_update_passed", "finished_at": utc_now(), "latest_after": latest_asof(), "pending_asof_cleared": True})
    write_json(job_dir / "job.json", job)
    print(json.dumps(job, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
