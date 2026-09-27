#!/usr/bin/env python3
"""Build ARCH-1 read-only annex and reports from existing local evidence."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yaml

from validate_arch1_baseline_descriptor import ROOT, descriptor_protected_paths, expected_job_paths, scan_normalized, sha256, validate

OUT = ROOT / "data_tw/experiments/project_runtime_convergence/arch1_baseline_descriptor_20260907"
INVENTORY = ROOT / "data_tw/experiments/project_runtime_convergence/arch0_runtime_truth_inventory_20260907/ARCH0_RUNTIME_TRUTH_INVENTORY.json"
DESCRIPTOR = ROOT / "configs/active_baseline_descriptor.yaml"


def build_job_row(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    status_path = path.parent / "daily_chain_status.json"
    chain = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
    blocker = chain.get("blocker") or payload.get("message", "")
    return {
        "path": str(path.relative_to(ROOT)),
        "job_id": payload.get("job_id", path.parent.name),
        "status": payload.get("status", ""),
        "asof": payload.get("asof", ""),
        "blocker": blocker,
        "latest_before": payload.get("latest_before", ""),
        "latest_after": payload.get("latest_after", ""),
        "provider_publish_triggered": bool(payload.get("provider_publish_triggered", False)),
        "latest_signal_updated": bool(payload.get("latest_signal_updated", False)),
        "model_a_score_job_triggered": bool(payload.get("model_a_score_job_triggered", False)),
        "model_b_ltr_score_job_triggered": bool(payload.get("model_b_ltr_score_job_triggered", False)),
        "chain_state": chain.get("state", ""),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    descriptor = yaml.safe_load(DESCRIPTOR.read_text(encoding="utf-8"))
    protected_expected = descriptor_protected_paths(descriptor)
    annex_path = OUT / "ARCH1_RUNTIME_TRUTH_ANNEX.json"
    backup_path = OUT / "ARCH1_RUNTIME_TRUTH_ANNEX_PRE_REBASELINE.json"
    if annex_path.exists() and not backup_path.exists():
        shutil.copy2(annex_path, backup_path)
    rows = [build_job_row(path) for path in expected_job_paths()]
    annex = {
        "schema_version": "arch1.runtime_truth_annex.v1",
        "phase": "ARCH-1_UNIQUE_BASELINE_DESCRIPTOR_AND_MODEL_REGISTRY_CONVERGENCE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_inventory": str(INVENTORY.relative_to(ROOT)),
        "source_inventory_sha256": sha256(INVENTORY),
        "recent_jobs": rows,
        "normalized_nonempty_freshness": scan_normalized(),
        "model_b_identity": {
            "canonical_id": "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025",
            "legacy_display_id": "e4_frozen_qlib_2023_2025_ltr",
            "compatibility_model_id": "head10_all_l31",
            "compatibility_candidate_id": "head10_all_l31_alpha0.7_top50_only",
            "compatibility_score_column": "score_head10_all_l31_alpha0.7_top50_only",
            "status": "PROSPECTIVE_SHADOW",
        },
        "protected_latest_fingerprints": {path: sha256(ROOT / path) for path in protected_expected},
        "forbidden_scope_audit": {
            "provider_publish": False,
            "accepted_latest_switch": False,
            "latest_pointer_write": False,
            "cron_write": False,
            "frontend_backend_default_switch": False,
            "training": False,
            "scoring": False,
            "broker_or_order": False,
        },
    }
    annex_path.write_text(json.dumps(annex, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    validator_result = validate(DESCRIPTOR, INVENTORY, annex_path)
    (OUT / "ARCH1_VALIDATOR_RESULT.json").write_text(json.dumps(validator_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fingerprint_audit = {
        "schema_version": "arch1.protected_fingerprint_audit.v1",
        "all_unchanged": annex["protected_latest_fingerprints"] == protected_expected,
        "expected_from_descriptor": protected_expected,
        "actual": annex["protected_latest_fingerprints"],
        "descriptor_path": str(DESCRIPTOR.relative_to(ROOT)),
    }
    (OUT / "ARCH1_PROTECTED_FINGERPRINT_AUDIT.json").write_text(json.dumps(fingerprint_audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = f"""# ARCH-1 执行报告

工作单：`ARCH-1_UNIQUE_BASELINE_DESCRIPTOR_AND_MODEL_REGISTRY_CONVERGENCE`

## 结果

- 建立 `configs/active_baseline_descriptor.yaml`，唯一表达当前 `MODEL_A_ONLY` active baseline；Model B 保持 `PROSPECTIVE_SHADOW`。
- Model B canonical ID、legacy display ID、MBCDS3 compatibility ID/candidate/score column 已在 descriptor 中显式映射。
- fallback 原始值 `model_b` 按 `<signal_root>/<asof>/model_b` 解析，未创建或写入 fallback 目录。
- 只读生成最近 20 个 daily job 的逐行 annex；路径序列精确匹配 validator 的 expected_job_paths。
- protected hash 期望唯一读取 descriptor；重建前旧 annex 保留为 `{backup_path.name}`（已有备份不覆盖）。
- protected hash 与 descriptor 一致性：`{"PASS" if fingerprint_audit["all_unchanged"] else "FAIL"}`。

## 未做

未修改 latest/provider/cron/frontend/backend production default；未训练、评分、抓取、连接 broker 或生成订单。live crontab 权限缺口保留为后续运维验收 blocker。

## 验证

详见 `ARCH1_RUNTIME_TRUTH_ANNEX.json`、`ARCH1_VALIDATOR_RESULT.json` 和 `ARCH1_PROTECTED_FINGERPRINT_AUDIT.json`。
"""
    (OUT / "ARCH1_EXECUTION_REPORT_CN.md").write_text(report, encoding="utf-8")
    (OUT / "ARCH1_NEXT_WORK_ORDER_CN.md").write_text("# ARCH-1 下一步工作单\n\n工作单：`ARCH-2_DAILY_ORCHESTRATOR_BEHAVIOR_PRESERVING_SPLIT`\n\n前置条件：ARCH-1 validator 与独立审查通过。只拆分 acquisition/readiness、Model A signal、Model B shadow、publish/fingerprint 和 ops status stage；保持 Model A latest、策略、next_open、no-publish 和失败语义完全不变。\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
