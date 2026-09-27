#!/usr/bin/env python3
"""Read-only lineage and local raw/archive inventory for Model B repair."""
from __future__ import annotations
import csv, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data_tw/experiments/project_runtime_convergence/modelb_conditional_dual_track_replay_repair_20260908"
E1=ROOT/"data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_raw_oos_score_rank_2023_2026.csv"
E2=ROOT/"data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_ltr_test_sample_2026.csv"
E3=ROOT/"data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_test_row_scores_2026.csv"
ARCH=ROOT/"data_tw/experiments/ltr_orthogonal_features_controlled/phase_o1r_coverage_available_at_repair/raw_archive"
def sha(p):
 h=hashlib.sha256()
 if not p.is_file(): return None
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def stat(p): return {'path':str(p.relative_to(ROOT)),'exists':p.is_file(),'size':p.stat().st_size if p.is_file() else None,'mtime_utc':datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat() if p.is_file() else None,'sha256':sha(p)}
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 files=[E1,E2,E3,E1.parent/'phasee1_training_manifest.json',E3.parent/'phasee3_training_manifest.json',E2.parent/'phasee2_sample_manifest.json']
 d1=pd.read_csv(E1,dtype={'instrument':str}); d2=pd.read_csv(E2,dtype={'instrument':str}); d3=pd.read_csv(E3,dtype={'instrument':str})
 for d in (d1,d2,d3): d['date']=d['date'].astype(str).str[:10]
 target=d1[d1.date.between('2026-01-02','2026-05-07')].groupby('date').size()
 e2target=d2[d2.date.between('2026-01-02','2026-05-07')].groupby('date').size()
 e3target=d3[d3.date.between('2026-01-02','2026-05-07')].groupby('date').size()
 coverage=[{'date':day,'e1_rows':int(target.get(day,0)),'e2_rows':int(e2target.get(day,0)),'e3_rows':int(e3target.get(day,0)),'e1_150':int(target.get(day,0))==150,'e2_78_feature_rows_expected':int(e2target.get(day,0))==150,'e3_rows_expected':int(e3target.get(day,0))==150} for day in sorted(target.index)]
 tw=sorted(str(p.relative_to(ROOT)) for p in ARCH.rglob('*TW7769*')) if ARCH.exists() else []
 tw_stats=[]
 for rel in tw:
  p=ROOT/rel; item=stat(p)
  if p.name.endswith('normalized.csv'):
   try:
    x=pd.read_csv(p); item.update({'rows':len(x),'trade_date_min':str(x.trade_date.min()) if 'trade_date' in x else None,'trade_date_max':str(x.trade_date.max()) if 'trade_date' in x else None,'available_at_min':str(x.available_at.min()) if 'available_at' in x else None,'available_at_max':str(x.available_at.max()) if 'available_at' in x else None})
   except Exception as exc: item['parse_error']=str(exc)
  tw_stats.append(item)
 inv={'created_at':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),'status':'BLOCKED','reason':'No shared E1/E2/E3 run_id/source inventory and no explicit decision_cutoff; local raw TW7769 files are not proven same-run inputs','files':[stat(p) for p in files],'coverage':coverage,'tw7769_local_raw_archive_files':tw_stats,'tw7769_raw_archive_count':len(tw_stats),'no_external_get_performed':True,'production_writes':False}
 (OUT/'lineage_inventory.json').write_text(json.dumps(inv,ensure_ascii=False,indent=2)+'\n')
 with (OUT/'source_file_inventory.csv').open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=['path','exists','size','mtime_utc','sha256']); w.writeheader(); w.writerows(inv['files'])
 (OUT/'LINEAGE_INVENTORY_EXECUTION_REPORT_CN.md').write_text('# Model B repair 原始证据获取执行报告\n\n'+json.dumps(inv,ensure_ascii=False,indent=2)+'\n\n结论：现有 E1/E2/E3 manifest 未提供可匹配的 shared run_id/source inventory，decision cutoff 亦未显式落盘；TW7769 虽在本地 raw archive 出现，但无法证明与本 replay 同源，故保持 BLOCKED，不补值、不重写原始 artifact。\n',encoding='utf-8')
 print(json.dumps({'status':inv['status'],'tw7769_raw_archive_count':len(tw),'dates':len(coverage)},ensure_ascii=False))
if __name__=='__main__': main()
