from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts/validate_tw_daily_orchestrator_m3.py"
GOLDEN_ROOT = ROOT / "data_tw/golden_samples/modular_contracts/m3"
DAILY_SCRIPT = ROOT / "scripts/run_daily_tw_stock_auto_update.py"


def run_validator(*args: str) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), *args, "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.stdout.strip(), proc.stderr
    return proc.returncode, json.loads(proc.stdout)


def test_m3_golden_batch_passes_and_counts_all_samples() -> None:
    code, result = run_validator("--run-golden")
    assert code == 0
    assert result["ok"] is True
    assert result["schema_version"] == "m3.0.0"
    assert result["sample_count"] == 16
    assert {row["contract"] for row in result["results"]} == {
        "daily_orchestrator",
        "run_registry",
        "auto_update",
    }


def test_m3_latest_pointer_state_machine_samples() -> None:
    cases = [
        ("daily_orchestrator/no_new_data_noop_preserves_previous_latest", "readonly_latest_20260616"),
        ("daily_orchestrator/fresh_data_success_validators_passed_updates_readonly_latest", "readonly_latest_20260617"),
        ("daily_orchestrator/validator_failed_preserves_previous_latest", "readonly_latest_20260616"),
        ("daily_orchestrator/module_failed_preserves_previous_latest", "readonly_latest_20260616"),
        ("run_registry/success_records_previous_proposed_committed_checksum", "readonly_latest_20260617"),
    ]
    for rel_sample, expected_committed in cases:
        sample = GOLDEN_ROOT / rel_sample
        contract = rel_sample.split("/", 1)[0]
        code, result = run_validator("--contract", contract, "--artifact-path", str(sample))
        assert code == 0, rel_sample
        assert result["ok"] is True, rel_sample
        assert result["previous_latest"] == "readonly_latest_20260616", rel_sample
        assert result["committed_latest"] == expected_committed, rel_sample
        assert result["latest_pointer_policy"] == "readonly_after_all_validators_pass_keep_previous_on_failure"


def test_m3_negative_samples_fail_with_expected_codes() -> None:
    cases = {
        "daily_orchestrator/forbidden_provider_publish_rejected": "forbidden_action",
        "daily_orchestrator/forbidden_accepted_latest_switch_rejected": "accepted_latest_changed",
        "daily_orchestrator/forbidden_monitor_broker_order_rejected": "forbidden_action",
        "auto_update/forbidden_provider_publish_rejected": "forbidden_action",
        "auto_update/forbidden_accepted_latest_switch_rejected": "accepted_latest_changed",
        "auto_update/forbidden_monitor_broker_order_rejected": "forbidden_action",
    }
    for rel_sample, expected_code in cases.items():
        sample = GOLDEN_ROOT / rel_sample
        contract = rel_sample.split("/", 1)[0]
        code, result = run_validator("--contract", contract, "--artifact-path", str(sample))
        assert code != 0, rel_sample
        assert result["ok"] is False, rel_sample
        assert expected_code in {err["code"] for err in result["errors"]}


def test_m3_daily_auto_update_script_audit_passes_only_when_legacy_path_is_gated() -> None:
    code, result = run_validator("--audit-script", str(DAILY_SCRIPT))
    assert code == 0
    assert result["ok"] is True
    warning_codes = {item["code"] for item in result["warnings"]}
    assert warning_codes == {
        "legacy_provider_publish_path_present",
        "legacy_accepted_latest_path_present",
    }
    audit = result["script_audit"]
    assert audit["has_wait_noop"] is True
    assert audit["has_already_up_to_date_noop"] is True
    assert audit["has_pending_retry"] is True
    assert audit["has_readonly_snapshot_dry_run_default"] is True
    assert audit["readonly_latest_pointer_distinct"] is True
    assert audit["production_provider_refresh_path_present"] is True
    assert audit["production_provider_publish_path_present"] is True
    assert audit["production_accepted_latest_path_present"] is True
    assert audit["legacy_provider_gate_present"] is True
    assert audit["legacy_provider_gate_default_disabled"] is True
    assert audit["legacy_provider_block_guarded"] is True
    assert audit["default_provider_refresh_reachable"] is False
    assert audit["default_provider_publish_reachable"] is False
    assert audit["default_accepted_latest_reachable"] is False
    assert audit["broker_order_patterns_present"] == []
    assert audit["monitor_write_patterns_present"] == []


def test_m3_script_audit_fails_when_provider_paths_are_default_reachable(tmp_path: Path) -> None:
    unsafe_script = tmp_path / "unsafe_daily.py"
    unsafe_script.write_text(
        """
provider_publish_triggered = False
cmd = 'examples/tw/run_option_c_yahoo_scrapling_refresh.py'
publish = 'examples/tw/publish_option_c_yahoo_scrapling_refresh.py'
def publish_accepted_latest(asof):
    return {'ok': True}
payload = {'confirm_accepted_latest_scheduler': True}
if not args.skip_qlib:
    provider_publish_triggered = True
""",
        encoding="utf-8",
    )
    code, result = run_validator("--audit-script", str(unsafe_script))
    assert code != 0
    assert result["ok"] is False
    error_codes = {item["code"] for item in result["errors"]}
    assert {
        "default_provider_refresh_reachable",
        "default_provider_publish_reachable",
        "default_accepted_latest_reachable",
        "legacy_provider_gate_missing",
    }.issubset(error_codes)
