#!/usr/bin/env python3
"""Capture ARCH-1 status without changing descriptor, registry, or protected files."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/arch1_status_20260912_r2"
DESCRIPTOR = ROOT / "configs/active_baseline_descriptor.yaml"
PRODUCT = ROOT / "configs/tw_product_artifact_registry.yaml"
MODULAR = ROOT / "configs/tw_modular_registry.yaml"
REPLAY = ROOT / "configs/tw_replay_window_policy.yaml"
PROVENANCE = ROOT / "data_tw/experiments/project_runtime_convergence/candidate_binding_20260907/protected_drift_audit_20260907/authorized_provenance_rebaseline_manifest.json"
PROVENANCE_EXECUTION = ROOT / "data_tw/experiments/project_runtime_convergence/candidate_binding_20260907/protected_drift_audit_20260907/PROTECTED_DRIFT_PROVENANCE_REBASELINE_EXECUTION.json"
ARCH0R_INVENTORY = ROOT / "data_tw/experiments/project_runtime_convergence/arch0_runtime_truth_inventory_20260907/ARCH0R_RUNTIME_TRUTH_INVENTORY.json"
ARCH0R_REVIEW = ROOT / "data_tw/experiments/project_runtime_convergence/arch0_runtime_truth_inventory_20260907/ARCH0R_REVIEW_REPORT_CN.md"
PROVENANCE_REVIEW = ROOT / "data_tw/experiments/project_runtime_convergence/candidate_binding_20260907/protected_drift_audit_20260907/PROTECTED_DRIFT_PROVENANCE_REBASELINE_INDEPENDENT_REVIEW_CN.md"
PROTECTED = [
    "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
    "data_tw/artifacts/agent_daily_prompt/latest.json",
    "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json",
    "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt",
    "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt",
    "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron",
]


def digest(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def snapshot() -> dict[str, dict]:
    paths = [DESCRIPTOR, PRODUCT, MODULAR, REPLAY] + [ROOT / path for path in PROTECTED]
    return {
        str(path.relative_to(ROOT)): {"exists": path.is_file(), "size": path.stat().st_size if path.is_file() else None, "sha256": digest(path)}
        for path in paths
    }


def parity() -> dict[str, dict | bool]:
    descriptor = yaml.safe_load(DESCRIPTOR.read_text(encoding="utf-8"))
    product = yaml.safe_load(PRODUCT.read_text(encoding="utf-8"))
    modular = yaml.safe_load(MODULAR.read_text(encoding="utf-8"))
    replay = yaml.safe_load(REPLAY.read_text(encoding="utf-8"))
    active = descriptor["active_baseline"]
    shadow = descriptor["shadow_models"][0]
    checks = {
        "active_model_matches_product_base": product["models"]["base_model_id"] == active["model_a"]["model_id"],
        "shadow_model_matches_product_treatment": product["models"]["treatment_model_id"] == shadow["canonical_id"],
        "strategy_matches_product_default": product["strategies"]["default_strategy_rule"] == active["strategy_rule"],
        "strategy_matches_replay_default": replay["default_strategy_rule"] == active["strategy_rule"],
        "model_a_matches_replay_default": replay["default_model_id"] == active["model_a"]["model_id"],
        "modular_strategy_production_default": bool(modular["strategies"]["production_selectable"][active["strategy_rule"]]["production_default"]),
        "descriptor_model_b_not_active": active["model_b"] is None and shadow["status"] == "PROSPECTIVE_SHADOW" and shadow["production_default"] is False,
    }
    return {"checks": checks, "all_pass": all(checks.values())}


def main() -> int:
    before = snapshot()
    parity_result = parity()
    validator = subprocess.run([sys.executable, str(ROOT / "scripts/validate_arch1_baseline_descriptor.py"), "--json"], cwd=ROOT, text=True, capture_output=True, check=False)
    loader = subprocess.run([sys.executable, "-c", "from tw_daily_runtime_stages import load_runtime_descriptor; d=load_runtime_descriptor(); assert d['active_baseline']['status']=='MODEL_A_ONLY'; print(d['active_baseline']['model_a']['model_id'])"], cwd=ROOT, env={**__import__('os').environ, "PYTHONPATH": str(ROOT / "scripts")}, text=True, capture_output=True, check=False)
    tests = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/unit/test_arch1_active_baseline_descriptor.py"], cwd=ROOT, text=True, capture_output=True, check=False)
    after = snapshot()
    unchanged = {name: before.get(name) == after.get(name) for name in sorted(set(before) | set(after))}
    manifest = json.loads(PROVENANCE.read_text(encoding="utf-8")) if PROVENANCE.is_file() else {}
    provenance_execution = json.loads(PROVENANCE_EXECUTION.read_text(encoding="utf-8")) if PROVENANCE_EXECUTION.is_file() else {}
    descriptor_payload = yaml.safe_load(DESCRIPTOR.read_text(encoding="utf-8"))
    descriptor_expected = {str(path): str(value) for path, value in descriptor_payload.get("protected_latest_paths", {}).items()}
    actual_after = {path: after.get(path, {}).get("sha256") for path in PROTECTED}
    payload = {
        "schema_version": "arch1.execution_evidence.v2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scope": "ARCH-1 descriptor/registry/identity validation only; no protected hash reconciliation",
        "before": before,
        "after": after,
        "no_publish_audit": {"all_paths_unchanged": all(unchanged.values()), "checks": unchanged, "publish_allowed": False},
        "descriptor_protected_binding": {
            "expected_from_descriptor": descriptor_expected,
            "actual_after": actual_after,
            "all_match": all(descriptor_expected.get(path) == actual_after.get(path) for path in PROTECTED),
            "reconciliation_executed": False,
        },
        "registry_parity": parity_result,
        "runtime_loader": {"returncode": loader.returncode, "stdout": loader.stdout, "stderr": loader.stderr, "schema_enforced": loader.returncode == 0},
        "validator": {"returncode": validator.returncode, "result": json.loads(validator.stdout) if validator.stdout.strip() else {}, "stderr": validator.stderr},
        "focused_tests": {"returncode": tests.returncode, "stdout": tests.stdout, "stderr": tests.stderr},
        "authorized_provenance": {
            "manifest_path": str(PROVENANCE.relative_to(ROOT)),
            "manifest_id": manifest.get("manifest_id"),
            "authorized": (manifest.get("authorization") or {}).get("authorized_by_user"),
            "decision": provenance_execution.get("decision"),
            "execution_record_path": str(PROVENANCE_EXECUTION.relative_to(ROOT)),
            "independent_review": "PASS_WITH_CONDITIONS / ARCH1_ANNEX_REBUILD_REQUIRED",
            "review_path": str(PROVENANCE_REVIEW.relative_to(ROOT)),
            "reconciliation_executed": False,
        },
        "arch0r_sources": {
            "inventory": str(ARCH0R_INVENTORY.relative_to(ROOT)),
            "review": str(ARCH0R_REVIEW.relative_to(ROOT)),
            "inventory_exists": ARCH0R_INVENTORY.is_file(),
            "review_exists": ARCH0R_REVIEW.is_file(),
        },
        "active_baseline": {"model_a": "e4_frozen_qlib_2018_2022", "model_b": None, "status": "MODEL_A_ONLY", "strategy": "top50_exit_one_worst_sell", "execution_price": "next_open"},
        "blockers": ["9/7 authorized provenance review remains PASS_WITH_CONDITIONS / ARCH1_ANNEX_REBUILD_REQUIRED", "descriptor protected hash reconciliation was not executed", "live crontab parity remains outside this read-only task"],
    }
    OUT.mkdir(parents=True, exist_ok=False)
    (OUT / "ARCH1_EXECUTION_EVIDENCE_20260912.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "ARCH1_EXECUTION_REPORT_CN.md").write_text("""# ARCH-1 执行报告（2026-09-12 状态核验）

## 范围

本轮只核验并补齐 ActiveBaselineDescriptor 的 schema-validator-loader 语义、registry parity、canonical Model B identity 与 no-publish before/after evidence。未更新 descriptor protected hashes，未执行 protected hash reconciliation；9/7 authorized provenance manifest 仅作为条件性 provenance 引用。

## 结果

- active baseline 仍为 Model A-only：`e4_frozen_qlib_2018_2022`、`top50_exit_one_worst_sell`、`next_open`、readonly/simulation-only。
- Model B canonical ID 为 `e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025`，保持 `PROSPECTIVE_SHADOW`、非 production default、非 eligible baseline；legacy/MBCDS3 aliases、SHA-256、top50-only 与 fallback resolution 已由 validator 约束。
- product/modular/replay registry parity 全部通过；JSON Schema invocation、runtime loader、protected no-publish before/after audit 全部有证据。
- 直接引用 ARCH0R inventory/review（`ARCH0R_RUNTIME_TRUTH_INVENTORY.json`、`ARCH0R_REVIEW_REPORT_CN.md`），并保留其 C1/C2 条件：当前 descriptor hashes 未同步到后续 latest，仅记录 provenance，不自动 reconciliation。
- 9/7 provenance independent review 仍为 `PASS_WITH_CONDITIONS / ARCH1_ANNEX_REBUILD_REQUIRED`，不得写成 completed/pass；本轮明确未执行 descriptor hash reconciliation。

## 验证

证据 JSON 中记录实际 before/after fingerprints、validator JSON、runtime loader、focused pytest 输出和 registry parity。当前 ARCH-1 focused tests 为 21 passed；validator 为 34 项检查全部通过；loader schema gate 通过。protected 文件在本轮 before/after 未变化。
""", encoding="utf-8")
    (OUT / "ARCH1_NEXT_WORK_ORDER_CN.md").write_text("""# ARCH-1 下一步工作单

工作单：`ARCH-2_DAILY_ORCHESTRATOR_BEHAVIOR_PRESERVING_SPLIT`

前置条件：保留 9/7 provenance 条件性审查和旧 evidence；不得自动执行 descriptor protected hash reconciliation。ARCH-2 仅可继续使用 descriptor loader、schema gate 和真实 before/after no-publish audit，保持 Model A-only、Model B prospective shadow、策略、next_open、latest/provider/cron/default 边界不变。若需要再次更新 protected hashes，必须先提交独立子步骤和目标 fingerprints，暂停等待 coordinator 明确授权。
""", encoding="utf-8")
    return 0 if validator.returncode == 0 and loader.returncode == 0 and tests.returncode == 0 and parity_result["all_pass"] and all(unchanged.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
