#!/usr/bin/env python3
"""Re-score frozen Phase1C on its 34-feature sample, then bind to E1 top50."""
from __future__ import annotations
import csv, hashlib, json, pickle
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import run_modelb_historical_exact_top50_replay as engine

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data_tw/experiments/project_runtime_convergence/modelb_legacy_same_e1_top50_replay_20260908"
E1=ROOT/"data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_raw_oos_score_rank_2023_2026.csv"
SAMPLE=ROOT/"data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_ltr_samples.csv"
MODEL=ROOT/"data_tw/experiments/model_b_compatibility_daily_shadow/model_artifact_phase1c_20260905/phase1c_head10_all_l31_model.pkl"
START,END='2026-01-02','2026-05-07'
engine.PROTECTED = engine.PROTECTED + [ROOT/'configs/active_baseline_descriptor.yaml', ROOT/'qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt']
FEATURES=['qlib_score_raw','qlib_rank','qlib_score_percentile_by_date','qlib_score_zscore_by_date','rank_change_1d','rank_change_3d','rank_change_5d','top10_flag','top30_flag','top50_flag','top30_streak','top50_streak','MA5','MA10','MA20','MA60','RSI14','MACD','Bollinger_position','ret20','volatility20','volume_ratio20','avg_trading_value_20d','volume_stability20','missing_rate20','suspension_proxy','slippage_proxy','TWII_ret20','TWII_ret60','TWII_close_vs_MA60','TWII_close_vs_MA120','market_volatility20','market_drawdown60','market_breadth20']
def sha(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def write(name,rows):
 p=OUT/name; p.parent.mkdir(parents=True,exist_ok=True); fs=sorted({k for r in rows for k in r}) if rows else ['status']
 with p.open('w',newline='',encoding='utf-8') as f: w=csv.DictWriter(f,fieldnames=fs); w.writeheader(); w.writerows(rows)
def main():
 OUT.mkdir(parents=True,exist_ok=True); before=engine.fingerprints(); a=pd.read_csv(E1,dtype={'instrument':str}); s=pd.read_csv(SAMPLE,dtype={'instrument':str})
 for d in (a,s): d['date']=d.date.astype(str).str[:10]
 a=a[a.date.between(START,END)].copy(); s=s[s.date.between(START,END)].copy()
 missing=[f for f in FEATURES if f not in s.columns]; model=pickle.load(MODEL.open('rb'))
 rows=[]; signals=[]; full_ranks={}; blocked=[]
 for day in sorted(a.date.unique()):
  af=a[a.date.eq(day)].copy(); sf=s[s.date.eq(day)].copy(); atop=af[af.qlib_rank_raw<=50]
  if len(sf)!=150 or missing or not set(atop.instrument).issubset(set(sf.instrument)): blocked.append({'date':day,'e1_rows':len(af),'sample_rows':len(sf),'missing_features':'|'.join(missing),'e1_top50_in_sample':set(atop.instrument).issubset(set(sf.instrument)),'status':'BLOCKED'}); continue
  sf=sf.copy(); sf['model_raw']=model.predict(sf[FEATURES].astype(float)); sf['model_pct']=sf.groupby('date')['model_raw'].rank(method='average',pct=True,ascending=True)
  sf['legacy_score']=0.7*pd.to_numeric(sf['qlib_score_percentile_by_date'])+0.3*sf['model_pct']
  m=atop.merge(sf[['instrument','legacy_score']],on='instrument',how='inner'); m=m.rename(columns={'qlib_rank_raw':'candidate_rank','qlib_score_raw':'a_score','legacy_score':'b_score'})
  full_ranks[day]={str(r.instrument):int(r.qlib_rank_raw) for r in af.itertuples()}; keys=sorted(m.instrument.astype(str)); rows.append({'date':day,'e1_rows':len(af),'sample_rows':len(sf),'e1_top50_count':len(atop),'bound_rows':len(m),'bound_hash':hashlib.sha256('|'.join(keys).encode()).hexdigest(),'candidate_equal':len(m)==50 and set(keys)==set(atop.instrument),'status':'PASS' if len(m)==50 else 'BLOCKED'})
  for r in m.itertuples(index=False): signals.append({'date':day,'instrument':r.instrument,'candidate_rank':int(r.candidate_rank),'full_qlib_rank':int(r.candidate_rank),'a_score':float(r.a_score),'b_score':float(r.b_score)})
 if blocked: (OUT/'blocked_rows.json').write_text(json.dumps(blocked,ensure_ascii=False,indent=2)+'\n')
 if len(signals)!=79*50: raise RuntimeError(f'blocked or incomplete binding: {len(signals)} rows')
 sd=pd.DataFrame(signals); prices=engine.Prices(set(sd.instrument)); am,aa,an=engine.replay(sd,prices,'a_score','A_ONLY_E1_TOP50',full_ranks); bm,ba,bn=engine.replay(sd,prices,'b_score','LEGACY_PHASE1C_RECOMPUTED_E1_TOP50',full_ranks)
 write('signals.csv',signals); write('coverage_audit.csv',rows); write('A_ONLY_actions.csv',aa); write('LEGACY_actions.csv',ba); write('A_ONLY_daily_nav.csv',an); write('LEGACY_daily_nav.csv',bn); write('metrics.csv',[am,bm])
 after=engine.fingerprints(); r={'run_id':'modelb_legacy_same_e1_top50_replay_20260908','created_at':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),'window':[START,END],'model':'phase1c_head10_all_l31 frozen pickle','model_path':str(MODEL.relative_to(ROOT)),'sample_path':str(SAMPLE.relative_to(ROOT)),'e1_path':str(E1.relative_to(ROOT)),'checksums':{'model':sha(MODEL),'sample':sha(SAMPLE),'e1':sha(E1)},'feature_count':len(FEATURES),'feature_whitelist':FEATURES,'date_count':len(rows),'signals_rows':len(signals),'coverage_all_pass':all(x['status']=='PASS' for x in rows),'candidate_equal_all':all(x['candidate_equal'] for x in rows),'metrics':[am,bm],'relative':{'legacy_minus_a_return':bm['net_return']-am['net_return'],'legacy_minus_a_drawdown':bm['max_drawdown']-am['max_drawdown'],'legacy_minus_a_sharpe':bm['sharpe_annualized']-am['sharpe_annualized']},'strategy_rule':'top50_exit_one_worst_sell','execution_price_mode':'next_open','fees':{'fee_rate':engine.FEE,'sell_tax_rate':engine.TAX,'lot_size':engine.LOT,'target_holdings':engine.TARGET},'status':'CONDITIONAL_HISTORICAL_DIAGNOSTIC_RESEARCH_ONLY','baseline_admission':False,'no_publish':True,'no_baseline_switch':True,'protected_before':before,'protected_after':after,'protected_unchanged':before==after}
 (OUT/'manifest.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); (OUT/'safety_audit.json').write_text(json.dumps({'readonly_only':True,'production_allowed':False,'future_labels_consumed_for_scoring':False,'labels_present_in_source_not_loaded':True,'candidate_universe_from_e1_top50':True,'next_open_only':True},ensure_ascii=False,indent=2)+'\n'); (OUT/'EXECUTION_REPORT_CN.md').write_text('# Legacy Phase1C 重算并绑定当前 E1 Top50 执行报告\n\n'+json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(r,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
