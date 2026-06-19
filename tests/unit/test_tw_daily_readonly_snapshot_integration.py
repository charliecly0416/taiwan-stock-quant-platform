from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import run_daily_tw_stock_auto_update as daily


def write_payload(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def command_result(stdout_path: Path, payload: dict, *, ok: bool = True) -> dict:
    write_payload(stdout_path, payload)
    return {
        "ok": ok,
        "returncode": 0 if ok else 2,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stdout_path.with_suffix(".stderr")),
    }


def test_switch_off_does_not_call_writer(tmp_path: Path) -> None:
    calls = []

    def runner(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("writer must not be called when switch is off")

    result = daily.run_readonly_strategy_snapshot_publish(
        asof="2026-06-16",
        job_dir=tmp_path,
        enabled=False,
        command_runner=runner,
    )

    assert result["enabled"] is False
    assert result["attempted"] is False
    assert result["ok"] is True
    assert calls == []


def test_success_dry_run_calls_writer_and_validator_without_latest_update(tmp_path: Path) -> None:
    calls = []
    manifest = tmp_path / "snapshot" / "manifest.json"
    write_payload(manifest, {"asof": "2026-06-16"})

    def runner(argv, *, cwd, stdout_path, stderr_path, timeout):
        calls.append(argv)
        if "--manifest" in argv:
            return command_result(stdout_path, {"ok": True})
        return command_result(stdout_path, {"ok": True, "manifest": str(manifest)})

    result = daily.run_readonly_strategy_snapshot_publish(
        asof="2026-06-16",
        job_dir=tmp_path / "job",
        enabled=True,
        dry_run=True,
        command_runner=runner,
    )

    assert result["ok"] is True
    assert result["attempted"] is True
    assert result["validator_ok"] is True
    assert result["latest_updated"] is False
    assert len(calls) == 2
    assert "--no-latest" in calls[0]
    assert "--manifest" in calls[1]


def test_success_non_dry_run_updates_latest_after_manifest_validator(monkeypatch, tmp_path: Path) -> None:
    calls = []
    latest_written = []
    manifest = tmp_path / "snapshot" / "manifest.json"
    out_root = tmp_path / "readonly_root"
    write_payload(manifest, {"asof": "2026-06-16"})

    def fake_write_latest(manifest_path: Path, *, out_root: Path):
        latest_written.append((manifest_path, out_root))
        latest = out_root / "latest.json"
        write_payload(latest, {"snapshot_manifest": str(manifest_path)})
        return latest

    def runner(argv, *, cwd, stdout_path, stderr_path, timeout):
        calls.append(argv)
        if "--latest" in argv:
            return command_result(stdout_path, {"ok": True})
        if "--manifest" in argv:
            assert latest_written == []
            return command_result(stdout_path, {"ok": True})
        return command_result(stdout_path, {"ok": True, "manifest": str(manifest)})

    monkeypatch.setattr(daily, "write_readonly_snapshot_latest_pointer", fake_write_latest)
    result = daily.run_readonly_strategy_snapshot_publish(
        asof="2026-06-16",
        job_dir=tmp_path / "job",
        enabled=True,
        dry_run=False,
        out_root=out_root,
        command_runner=runner,
    )

    assert result["ok"] is True
    assert result["latest_updated"] is True
    assert latest_written == [(manifest, out_root)]
    assert "--latest" in calls[-1]


def test_writer_failure_is_isolated_and_skips_validator(tmp_path: Path) -> None:
    calls = []

    def runner(argv, *, cwd, stdout_path, stderr_path, timeout):
        calls.append(argv)
        return command_result(stdout_path, {"ok": False}, ok=False)

    result = daily.run_readonly_strategy_snapshot_publish(
        asof="2026-06-16",
        job_dir=tmp_path,
        enabled=True,
        dry_run=False,
        command_runner=runner,
    )

    assert result["ok"] is False
    assert result["error"] == "readonly snapshot writer failed"
    assert result["latest_updated"] is False
    assert len(calls) == 1


def test_validator_failure_does_not_update_latest(monkeypatch, tmp_path: Path) -> None:
    manifest = tmp_path / "snapshot" / "manifest.json"
    write_payload(manifest, {"asof": "2026-06-16"})

    def fail_if_latest_written(*args, **kwargs):
        raise AssertionError("latest pointer must not be updated after validator failure")

    def runner(argv, *, cwd, stdout_path, stderr_path, timeout):
        if "--manifest" in argv:
            return command_result(stdout_path, {"ok": False}, ok=False)
        return command_result(stdout_path, {"ok": True, "manifest": str(manifest)})

    monkeypatch.setattr(daily, "write_readonly_snapshot_latest_pointer", fail_if_latest_written)
    result = daily.run_readonly_strategy_snapshot_publish(
        asof="2026-06-16",
        job_dir=tmp_path / "job",
        enabled=True,
        dry_run=False,
        command_runner=runner,
    )

    assert result["ok"] is False
    assert result["error"] == "readonly snapshot validator failed"
    assert result["validator_ok"] is False
    assert result["latest_updated"] is False


def test_r16_added_daily_integration_static_scan() -> None:
    source = (ROOT / "scripts/run_daily_tw_stock_auto_update.py").read_text(encoding="utf-8")
    start = source.index("def run_readonly_strategy_snapshot_publish")
    end = source.index("def materialize_symbols")
    block = source[start:end]

    required = [
        "ENABLE_TW_READONLY_STRATEGY_SNAPSHOT_PUBLISH",
        "TW_READONLY_STRATEGY_SNAPSHOT_DRY_RUN",
        "READONLY_PUBLISH_SCRIPT",
        "READONLY_VALIDATE_SCRIPT",
        "--no-latest",
        "write_readonly_snapshot_latest_pointer",
    ]
    forbidden = [
        "quick-trade",
        "quickTrade",
        "/api/broker/",
        "submitOrder",
        "placeOrder",
        "connectBroker",
        "order_action",
        "target_position",
        "target_weight",
        "provider_publish",
        "provider refresh",
        "accepted_latest_switch",
        "saveTwStockMonitorConfig",
        "scanTwStockMonitor",
        "updateTwStockAlert",
    ]

    assert all(marker in source for marker in required)
    assert not [pattern for pattern in forbidden if pattern in block]
