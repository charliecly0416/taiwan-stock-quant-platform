#!/usr/bin/env python3
"""Build an isolated conditional A/B historical replay artifact.

All requested dates remain in coverage. On dates where E3 lacks an E1-top50
row, both tracks use the exact E1/E3 intersection; no value or universe fill.
"""
from __future__ import annotations

import csv, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

import run_modelb_historical_exact_top50_replay as engine

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_conditional_dual_track_replay_20260908"
START, END = "2026-01-02", "2026-05-07"
E1 = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_raw_oos_score_rank_2023_2026.csv"
E3 = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_test_row_scores_2026.csv"
PROTECTED = engine.PROTECTED

def sha(path: Path) -> str | None:
    if not path.is_file(): return None
    h=hashlib.sha256()
    with path.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()

def fps(): return {str(p.relative_to(ROOT)): {"exists":p.is_file(),"sha256":sha(p)} for p in PROTECTED}

def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields=sorted({k for r in rows for k in r}) if rows else ['status']
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

def load_conditional():
    q=pd.read_csv(E1,dtype={'instrument':str}); e=pd.read_csv(E3,dtype={'instrument':str})
    q['date']=q['date'].astype(str).str[:10]; e['date']=e['date'].astype(str).str[:10]
    q=q[(q.date>=START)&(q.date<=END)].copy(); e=e[(e.date>=START)&(e.date<=END)].copy()
    if q.duplicated(['date','instrument']).any() or e.duplicated(['date','instrument']).any(): raise RuntimeError('duplicate source key')
    q=q.rename(columns={'qlib_rank_raw':'full_qlib_rank','qlib_score_raw':'a_score'})
    bcol='phasee3_extended_oos_ltr_score'
    m=q.merge(e[['date','instrument',bcol]],on=['date','instrument'],how='left',validate='one_to_one').rename(columns={bcol:'b_score'})
    m['full_qlib_rank']=pd.to_numeric(m.full_qlib_rank,errors='coerce'); m['a_score']=pd.to_numeric(m.a_score,errors='coerce'); m['b_score']=pd.to_numeric(m.b_score,errors='coerce')
    rows=[]; coverage=[]; full_ranks={}
    for day,g in m.groupby('date',sort=True):
        g=g.dropna(subset=['full_qlib_rank','a_score']); full_ranks[day]={str(r.instrument):int(r.full_qlib_rank) for r in g.itertuples(index=False)}
        top=g[g.full_qlib_rank<=50].copy(); common=top.dropna(subset=['b_score']).sort_values(['full_qlib_rank','instrument'])
        missing=sorted(set(top.instrument)-set(common.instrument))
        coverage.append({'date':day,'requested':True,'e1_top50_rows':int(len(top)),'e3_join_rows':int(len(common)),'missing_in_e3':','.join(missing),'conditional_status':'FULL_50' if len(common)==50 else ('CONDITIONAL_49' if len(common)==49 else 'BLOCKED') ,'same_candidate_set_for_a_b':True})
        for r in common.itertuples(index=False): rows.append({'date':day,'instrument':r.instrument,'candidate_rank':int(r.full_qlib_rank),'full_qlib_rank':int(r.full_qlib_rank),'a_score':float(r.a_score),'b_score':float(r.b_score)})
    return pd.DataFrame(rows),coverage,full_ranks

def main():
    before=fps(); signals,coverage,full_ranks=load_conditional(); prices=engine.Prices(set(signals.instrument))
    a_m,a_actions,a_nav=engine.replay(signals,prices,'a_score','A_ONLY',full_ranks)
    b_m,b_actions,b_nav=engine.replay(signals,prices,'b_score','A_PLUS_B',full_ranks)
    # Emit a compact standard signal table consumed by both tracks.
    signal_rows=[]
    for r in signals.to_dict('records'):
        signal_rows.append({'date':r['date'],'instrument':r['instrument'],'model_a':engine.MODEL_A,'model_b':engine.MODEL_B,'candidate_rank':r['candidate_rank'],'full_qlib_rank':r['full_qlib_rank'],'a_buy_score':r['a_score'],'b_buy_score':r['b_score'],'signal_asof':r['date'],'available_at':r['date'],'source_model_a':str(E1.relative_to(ROOT)),'source_model_b':str(E3.relative_to(ROOT))})
    after=fps()
    report={'run_id':'modelb_conditional_dual_track_replay_20260908','created_at':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),'window':[START,END],'requested_date_count':len(coverage),'paired_signal_date_count':sum(x['e3_join_rows']>0 for x in coverage),'full_50_date_count':sum(x['conditional_status']=='FULL_50' for x in coverage),'conditional_49_date_count':sum(x['conditional_status']=='CONDITIONAL_49' for x in coverage),'model_a':engine.MODEL_A,'model_b':engine.MODEL_B,'strategy_rule':'top50_exit_one_worst_sell','execution_price_mode':'next_open','execution_config':{'initial_equity':engine.INITIAL,'fee_rate':engine.FEE,'sell_tax_rate':engine.TAX,'lot_size':engine.LOT,'target_holdings':engine.TARGET},'candidate_binding':{'authoritative':'E1 qlib_rank_raw','b_join':'E3 date,instrument only','same_candidate_set_for_a_b':True,'universe_expansion':False,'tw7769_imputed':False},'source_checksums':{'e1':sha(E1),'e3':sha(E3)},'coverage_summary':coverage,'metrics':[a_m,b_m],'relative':{'return_diff_b_minus_a':round(b_m['net_return']-a_m['net_return'],8),'max_drawdown_diff_b_minus_a':round(b_m['max_drawdown']-a_m['max_drawdown'],8),'sharpe_diff_b_minus_a':round(b_m['sharpe_annualized']-a_m['sharpe_annualized'],8),'action_diff_b_minus_a':b_m['action_count']-a_m['action_count'],'fee_tax_diff_b_minus_a':round(b_m['fee_tax']-a_m['fee_tax'],2)},'protected_before':before,'protected_after':after,'protected_unchanged':before==after,'no_publish':True,'no_baseline_switch':True,'no_broker':True}
    write_csv(OUT/'signals.csv',signal_rows); write_csv(OUT/'coverage_audit.csv',coverage); write_csv(OUT/'A_ONLY_actions.csv',a_actions); write_csv(OUT/'A_PLUS_B_actions.csv',b_actions); write_csv(OUT/'A_ONLY_daily_nav.csv',a_nav); write_csv(OUT/'A_PLUS_B_daily_nav.csv',b_nav); write_csv(OUT/'aggregate_metrics.csv',[a_m,b_m])
    (OUT/'manifest.json').write_text(json.dumps(report,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
    (OUT/'safety_audit.json').write_text(json.dumps({'readonly_only':True,'simulation_only':True,'production_allowed':False,'no_value_imputation':True,'no_universe_replacement':True,'future_or_label_fields_consumed':False,'protected_unchanged':before==after},ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
    (OUT/'EXECUTION_REPORT_CN.md').write_text('# Model B 双轨条件轨历史 Replay 执行报告\n\n'+json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'ok':True,'out':str(OUT.relative_to(ROOT)),'requested_dates':len(coverage),'paired_dates':report['paired_signal_date_count'],'conditional_49_dates':report['conditional_49_date_count'],'metrics':report['metrics']},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
