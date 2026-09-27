#!/usr/bin/env python3
"""Conditional diagnostic replay for the legacy Phase1C compatibility score."""
from __future__ import annotations
import csv, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import run_modelb_historical_exact_top50_replay as engine

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data_tw/experiments/project_runtime_convergence/modelb_legacy_compatibility_intersection_replay_20260908"
E1=ROOT/"data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_raw_oos_score_rank_2023_2026.csv"
OLD=ROOT/"data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv"
START,END='2026-01-02','2026-05-07'; SCORE='score_head10_all_l31_alpha0.7_top50_only'
def sha(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def write(name,rows):
 p=OUT/name; p.parent.mkdir(parents=True,exist_ok=True); fields=sorted({k for r in rows for k in r}) if rows else ['status']
 with p.open('w',newline='',encoding='utf-8') as f: w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 a=pd.read_csv(E1,dtype={'instrument':str}); o=pd.read_csv(OLD,dtype={'instrument':str})
 for d in (a,o): d['date']=d['date'].astype(str).str[:10]
 a=a[a.date.between(START,END)].copy(); o=o[o.date.between(START,END)].copy()
 rows=[]; signals=[]; full_ranks={}
 for day in sorted(set(a.date)&set(o.date)):
  ag=a[a.date.eq(day)].copy(); og=o[o.date.eq(day)].copy(); top=ag[ag.qlib_rank_raw<=50]; old=og[og.qlib_rank<=50]
  inter=top.merge(old[['instrument',SCORE]],on='instrument',how='inner')
  inter=inter.rename(columns={'qlib_rank_raw':'candidate_rank', 'qlib_score_raw':'a_score', SCORE:'b_score'})
  full_ranks[day]={str(r.instrument):int(r.qlib_rank_raw) for r in ag.itertuples()}
  keys=sorted(inter.instrument.astype(str)); rows.append({'date':day,'e1_top50_count':len(top),'old_top50_count':len(old),'intersection_count':len(inter),'e1_only_count':len(set(top.instrument)-set(old.instrument)),'old_only_count':len(set(old.instrument)-set(top.instrument)),'intersection_hash':hashlib.sha256('|'.join(keys).encode()).hexdigest(),'status':'CONDITIONAL_DIAGNOSTIC' if len(inter)>0 else 'BLOCKED'})
  for r in inter.itertuples(index=False): signals.append({'date':day,'instrument':r.instrument,'candidate_rank':int(r.candidate_rank),'full_qlib_rank':int(r.candidate_rank),'a_score':float(r.a_score),'b_score':float(r.b_score)})
 s=pd.DataFrame(signals); prices=engine.Prices(set(s.instrument)); am,aa,an=engine.replay(s,prices,'a_score','A_ONLY_E1_INTERSECTION',full_ranks); bm,ba,bn=engine.replay(s,prices,'b_score','LEGACY_PHASE1C_INTERSECTION',full_ranks)
 write('coverage_audit.csv',rows); write('A_ONLY_actions.csv',aa); write('LEGACY_actions.csv',ba); write('A_ONLY_daily_nav.csv',an); write('LEGACY_daily_nav.csv',bn); write('metrics.csv',[am,bm]); write('signals.csv',signals)
 report={'run_id':'modelb_legacy_compatibility_intersection_replay_20260908','created_at':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),'window':[START,END],'legacy_model':'phase1c_head10_all_l31_compatibility','legacy_score_source':str(OLD.relative_to(ROOT)),'e1_source':str(E1.relative_to(ROOT)),'source_checksums':{'e1':sha(E1),'legacy':sha(OLD)},'date_count':len(rows),'intersection_count_min':min(r['intersection_count'] for r in rows),'intersection_count_max':max(r['intersection_count'] for r in rows),'metrics':[am,bm],'relative':{'legacy_minus_a_return':bm['net_return']-am['net_return'],'legacy_minus_a_drawdown':bm['max_drawdown']-am['max_drawdown'],'legacy_minus_a_sharpe':bm['sharpe_annualized']-am['sharpe_annualized']},'candidate_universe_equal':False,'baseline_admission':False,'classification':'CONDITIONAL_HISTORICAL_DIAGNOSTIC_ONLY','status':'STOP_NONCOMPARABLE_FULL_TOP50','no_publish':True,'no_baseline_switch':True}
 (OUT/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (OUT/'EXECUTION_REPORT_CN.md').write_text('# Legacy Model B compatibility 交集 Replay 执行报告\n\n'+json.dumps(report,ensure_ascii=False,indent=2)+'\n\n旧 Phase1C 与当前 E1 top50 候选集合不一致；本轮仅运行 E1∩旧分数的条件诊断，不能回答完整 Top50 策略优劣，也不能作为 baseline 证据。未修改 latest/provider/cron/default。\n',encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
