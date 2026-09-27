from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT_DIR = ROOT / "data_tw/artifacts/analysis/tradingagents_readonly/tadr13_price_source_verification"
EXPECTED_SYMBOLS = ["2317", "2330", "2454"]
EXPECTED_PRIMARY_WINDOW = {"start": "2026-05-01", "end": "2026-06-10"}
EXPECTED_TRANSITION_WINDOW = {"start": "2025-12-15", "end": "2026-01-15"}
ALLOWED_DOMAINS = {"www.twse.com.tw", "openapi.twse.com.tw", "mops.twse.com.tw"}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def count_lines(path: Path) -> int:
    return sum(1 for _ in path.open("r", encoding="utf-8")) if path.exists() else 0


def add_check(checks: list[dict], name: str, passed: bool, details: str = "", severity: str = "fail") -> None:
    checks.append({"name": name, "status": "pass" if passed else severity, "details": details})


def validate(artifact_dir: Path) -> dict:
    checks: list[dict] = []
    required_files = [
        "price_source_verification_manifest.json",
        "price_scale_gate_report.md",
        "official_price_rows.jsonl",
        "local_price_rows.jsonl",
        "price_row_comparison.csv",
        "corporate_action_context.jsonl",
        "source_access_audit.json",
        "forbidden_actions_audit.json",
    ]
    for filename in required_files:
        add_check(checks, f"required_file:{filename}", (artifact_dir / filename).exists())

    manifest = read_json(artifact_dir / "price_source_verification_manifest.json")
    source_audit = read_json(artifact_dir / "source_access_audit.json")
    forbidden = read_json(artifact_dir / "forbidden_actions_audit.json")

    add_check(checks, "manifest_symbols_exact", sorted(manifest.get("symbols", {}).keys()) == EXPECTED_SYMBOLS)
    add_check(checks, "manifest_primary_window_exact", manifest.get("primary_window") == EXPECTED_PRIMARY_WINDOW)
    add_check(checks, "manifest_transition_window_exact", manifest.get("transition_window") == EXPECTED_TRANSITION_WINDOW)
    add_check(checks, "allowed_domains_exact_or_subset", set(manifest.get("allowed_domains", [])) <= ALLOWED_DOMAINS)

    audits = source_audit.get("audits") if isinstance(source_audit, dict) else []
    audit_hosts = {urlparse(str(item.get("url") or "")).hostname for item in audits}
    add_check(checks, "source_domains_allowlisted", all(host in ALLOWED_DOMAINS for host in audit_hosts if host))
    add_check(checks, "source_audits_present", len(audits) == 12, f"count={len(audits)}")
    add_check(checks, "source_audits_all_ok", all(bool(item.get("ok")) for item in audits), "one or more official source requests failed", severity="stop")

    official_rows = count_lines(artifact_dir / "official_price_rows.jsonl")
    local_rows = count_lines(artifact_dir / "local_price_rows.jsonl")
    comparison_rows = max(0, count_lines(artifact_dir / "price_row_comparison.csv") - 1)
    add_check(checks, "official_rows_nonempty", official_rows > 0, f"official_rows={official_rows}", severity="stop")
    add_check(checks, "local_rows_nonempty", local_rows > 0, f"local_rows={local_rows}")
    add_check(checks, "comparison_rows_present", comparison_rows > 0, f"comparison_rows={comparison_rows}")

    for safety_key in [
        "no_tradingagents_real_run",
        "no_openai_call",
        "no_replay_backtest_oos",
        "no_order_target_sizing_generated",
        "no_production_default_latest_publish",
        "no_provider_latest_read",
        "no_accepted_latest_read",
        "no_prices_csv_read",
        "no_pcom_order_target_sizing_read",
    ]:
        add_check(checks, safety_key, bool(manifest.get(safety_key)) and bool(forbidden.get(safety_key)), severity="stop")

    stop_count = sum(1 for check in checks if check["status"] == "stop")
    fail_count = sum(1 for check in checks if check["status"] == "fail")
    status = "STOP" if stop_count else ("FAIL" if fail_count else "PASS")
    return {
        "ok": status == "PASS",
        "validator_status": status,
        "stop_count": stop_count,
        "fail_count": fail_count,
        "check_count": len(checks),
        "checks": checks,
    }


def main() -> int:
    artifact_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_ARTIFACT_DIR
    result = validate(artifact_dir)
    output_path = artifact_dir / "validator_report.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["validator_status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
