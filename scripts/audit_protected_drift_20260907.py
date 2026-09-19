#!/usr/bin/env python3
"""Readonly provenance audit for protected path drift around 2026-09-07."""
from __future__ import annotations
import hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/candidate_binding_20260907/protected_drift_audit_20260907"
DESCRIPTOR = ROOT / "configs/active_baseline_descriptor.yaml"
NORMAL = ROOT / "data_tw/ops/option_c_jobs/option_c_normal_publish_20260907_20260907T123620Z_63d1f740/job.json"
DRYRUN = ROOT / "data_tw/ops/option_c_jobs/option_c_dry_run_20260907_20260907T123614Z_8f6d0254/job.json"
FP = ROOT / "data_tw/experiments/formal_provider_accepted_latest_automation_alignment/fpala4_daily_auto_no_publish_20260907_daily_tw_stock_auto_update_20260907_20260907T123001Z/protected_paths_fingerprint.json"

def fp(rel: str, expected: str | None = None):
    p = ROOT / rel
    if not p.is_file():
        return {"path": rel, "exists": False, "expected_sha256": expected, "current_sha256": None, "match_descriptor": False}
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    st = p.stat()
    return {"path": rel, "exists": True, "size_bytes": st.st_size, "mtime_utc": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(), "expected_sha256": expected, "current_sha256": h, "match_descriptor": h == expected}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d = yaml.safe_load(DESCRIPTOR.read_text())
    protected = [fp(rel, exp) for rel, exp in d.get("protected_latest_paths", {}).items()]
    normal = json.loads(NORMAL.read_text()) if NORMAL.is_file() else None
    dry = json.loads(DRYRUN.read_text()) if DRYRUN.is_file() else None
    fpd = json.loads(FP.read_text()) if FP.is_file() else None
    changed = [x for x in protected if not x["match_descriptor"]]
    provenance = {
        "normal_publish_job": {"path": str(NORMAL.relative_to(ROOT)), "exists": normal is not None, "job_id": normal.get("job_id") if normal else None, "status": normal.get("status") if normal else None, "asof": normal.get("asof") if normal else None, "dry_run_job_id": normal.get("dry_run_job_id") if normal else None, "run_id": (normal.get("runner_output") or {}).get("run_id") if normal else None, "latest_signal_updated": normal.get("latest_signal_updated") if normal else None, "refresh_triggered": normal.get("refresh_triggered") if normal else None, "publish_triggered": normal.get("publish_triggered") if normal else None, "provider_mutation_triggered": normal.get("provider_mutation_triggered") if normal else None},
        "dry_run_job": {"path": str(DRYRUN.relative_to(ROOT)), "exists": dry is not None, "job_id": dry.get("job_id") if dry else None, "status": dry.get("status") if dry else None},
        "fpala4_evidence": {"path": str(FP.relative_to(ROOT)), "exists": fpd is not None, "target_asof": fpd.get("target_asof") if fpd else None, "all_protected_paths_unchanged": fpd.get("all_protected_paths_unchanged") if fpd else None},
    }
    audit = {"audit_id": "protected_drift_audit_20260907", "created_at": "2026-09-07", "scope": "readonly provenance/source audit; no rollback or overwrite", "descriptor": str(DESCRIPTOR.relative_to(ROOT)), "protected_paths": protected, "changed_against_descriptor": changed, "changed_path_count": len(changed), "provenance": provenance, "fpala4_before_after_claim": fpd.get("all_protected_paths_unchanged") if fpd else None, "decision": "STOP_CANDIDATE_BINDING" if changed else "PROCEED_CANDIDATE_BINDING", "reason": "Descriptor fingerprints for qlib accepted latest, calendar and instruments do not match current files; provenance shows a 2026-09-07 normal publish job updated latest and staged provider files. Candidate binding must stop until an authorized baseline fingerprint refresh/review." if changed else "No descriptor drift observed.", "safety": {"rollback": False, "overwrite": False, "provider_publish": False, "latest_write": False, "calendar_write": False, "instruments_write": False, "candidate_binding_write": False, "training": False, "scoring": False, "broker_or_order": False}}
    (OUT / "protected_drift_audit_20260907.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    (OUT / "PROTECTED_DRIFT_EXECUTION_REPORT_CN.md").write_text(f'''# Protected Fingerprint Drift 执行报告\n\n日期：2026-09-07\n范围：只读核对 active descriptor 受保护路径当前指纹，并关联 option_c normal publish、dry-run、daily no-publish 证据。\n\n## 结果\n\n- descriptor 对比发现 `{len(changed)}` 个漂移路径：qlib `latest_signal.json`、formal provider `calendars/day.txt`、`instruments/all.txt`。\n- normal publish evidence：`{provenance["normal_publish_job"]["job_id"]}`，status=`{provenance["normal_publish_job"]["status"]}`，asof=`{provenance["normal_publish_job"]["asof"]}`，`latest_signal_updated=true`；同时声明 provider mutation/publish=false。\n- FPALA4 evidence `{provenance["fpala4_evidence"]["path"]}` 的 before/after 只证明该 job 期间文件未再变化，不代表 descriptor 中旧 fingerprint 仍正确。\n- 决策：`STOP_CANDIDATE_BINDING`。即使来源是正常用户/上游 job 写入，也不能在 drift 未经授权复核时绑定 candidate universe。\n\n## 证据\n\n完整路径、size、mtime、descriptor expected/current SHA256 及 job provenance 见 `protected_drift_audit_20260907.json`。\n\n## 安全边界\n\n本次未回滚、未覆盖、未写 latest/provider/calendar/instruments/cron/default，未修改 candidate binding、shadow ledger 或 baseline，未训练/评分/下单。\n''')
    (OUT / "NEXT_WORK_CN.md").write_text('''# 下一步\n\n1. 由统筹者确认 2026-09-07 normal publish 是否为本主线允许的受控上游变更，并重新捕获 descriptor 及 ARCH-0 至 ARCH-4 protected fingerprints；在此之前保持 STOP。\n2. 建立与当前 latest/calendar/instruments 同一 source run 的 Model A 150-row ranking manifest，再重新验证 Model B top50 candidate binding。\n3. 不得使用旧 descriptor fingerprint、跨 run artifact、synthetic fixture 或历史 replay 解除本阻断；不得回滚或覆盖文件作为“修复”。\n4. 完成独立审查后，才可恢复 candidate binding / prospective shadow accumulation；baseline、自动化默认和生产 publish 仍不变。\n''')
    print(json.dumps({"out": str(OUT), "decision": audit["decision"], "changed_path_count": len(changed), "normal_job": provenance["normal_publish_job"]["job_id"]}, ensure_ascii=False))

if __name__ == "__main__": main()
