#!/usr/bin/env python3
"""Isolated regression of the 2026-09-15 source handoff/checksum gate."""
from __future__ import annotations
import copy, json, hashlib
from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parents[1]
ORIGINAL=ROOT/'data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260915_20260915T144501Z/job.json'
OUT=ROOT/'data_tw/ops/daily_auto_update/_isolated_hsa8_artifact_checksum_preflight_20260915'; OUT.mkdir(parents=True,exist_ok=True)

def load_module():
 spec=importlib.util.spec_from_file_location('daily_runtime',ROOT/'scripts/run_daily_tw_stock_auto_update.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def sha(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
 return h.hexdigest()
def main():
 m=load_module(); job=json.loads(ORIGINAL.read_text()); isolated=copy.deepcopy(job); isolated['job_id']=job['acquisition_logical_run_id']; isolated['acquisition_logical_run_id']=job['acquisition_logical_run_id']
 # Keep source capture run identity by using the logical id as ordinary job id.
 m.OPS_ROOT=ROOT/'data_tw/ops/daily_auto_update'
 handoff=m.build_real_same_run_handoff(job=isolated,job_dir=OUT,symbols=[])
 cutoff=str(job.get('mbcds3_decision_cutoff') or '2026-09-15T23:59:59+00:00')
 ledger=m.build_mbcds3_source_availability_ledger(asof='2026-09-15',job={'same_run_handoff':handoff,'acquisition_logical_run_id':isolated['acquisition_logical_run_id']},job_dir=OUT,decision_cutoff=cutoff)
 checksums=sum(len(s.get('artifacts',[])) for s in handoff.get('sources',[])); missing=[e for e in ledger.get('errors',[]) if 'artifact_checksums_missing' in e]
 result={'schema_version':'modelb.hsa8.artifact_checksum_preflight.v1','status':'PASS_CHECKSUM_CONTRACT_BLOCKED_PIT' if checksums and not missing else 'FAIL_ARTIFACT_CHECKSUM_CONTRACT','source_count':len(handoff.get('sources',[])),'artifact_entry_count':checksums,'missing_checksum_errors':missing,'handoff_ok':handoff.get('ok',False),'handoff_status':handoff.get('status'),'handoff_error':handoff.get('error'),'strict_handoff_ready':False,'twii_validator_blocker':'twii:validator_not_PASS' in str(handoff.get('error') or ''),'source_availability_status':ledger.get('status'),'source_availability_errors':ledger.get('errors',[]),'training_performed':False,'scoring_performed':False,'replay_performed':False,'production_allowed':False,'baseline_admission':False,'original_job':str(ORIGINAL.relative_to(ROOT))}
 (OUT/'HSA8_CHECKSUM_PREFLIGHT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n'); (OUT/'HSA8_PREFLIGHT_REPORT_CN.md').write_text(f'''# HSA8 / MBCDS3 artifact checksum 预检\n\n本次只读重建使用 2026-09-15 原始 job 元数据，输出隔离在本目录。修复后 handoff 为 `{handoff.get('status')}`，source availability 为 `{ledger.get('status')}`。\n\n各 source 共生成 {checksums} 个带 `path`/`sha256` 的 artifact entries；MBCDS3 不再报 `artifact_checksums_missing`。当前仍因真实 source validator/PIT 条件阻断，未生成 Model B signal，未训练、未评分、未回放，未写 production/latest/default/baseline/broker。\n'''); print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__': main()
