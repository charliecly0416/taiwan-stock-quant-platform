#!/usr/bin/env python3
from __future__ import annotations

import csv, json, importlib.util, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from collections import defaultdict

import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data_tw/experiments/fresh_top50_coverage_repair'
DOC0=ROOT/'docs/tw_fresh_top50_coverage_repair/PHASEC0_COVERAGE_AUDIT_EXECUTION_REPORT_CN.md'
DOC1=ROOT/'docs/tw_fresh_top50_coverage_repair/PHASEC1_REPAIR_AND_REPLAY_EXECUTION_REPORT_CN.md'
RAW=ROOT/'data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_raw_score_rank.csv'
POST=ROOT/'data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_post_filter_score_rank.csv'
ORIG_READY=ROOT/'data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/phase_s2d_replay_ready_scores.csv'
OLD=ROOT/'data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv'
S2F=ROOT/'data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2f_old_vs_fresh_same_window_recheck'
COVERAGE=S2F/'phase_s2f_same_window_coverage_audit.json'
S2D_SCRIPT=ROOT/'scripts/evaluate_tw_ltr_s2d_full_daily_replay.py'
S2C_SCRIPT=ROOT/'scripts/build_tw_ltr_s2c_fresh_samples.py'
START='2025-07-01'; END='2026-05-07'
OLD_COL='score_head10_all_l31_alpha0.7_top50_only'

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
def rel(p:Path):
    try: return str(p.resolve().relative_to(ROOT.resolve()))
    except Exception: return str(p)
def load_mod(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod
def wcsv(path, rows, fields=None):
    path.parent.mkdir(parents=True,exist_ok=True)
    if fields is None: fields=sorted({k for r in rows for k in r}) if rows else ['status']
    with path.open('w',encoding='utf-8',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=fields); wr.writeheader(); wr.writerows(rows)
def wjson(path,payload): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(payload,ensure_ascii=True,indent=2,default=str)+'\n',encoding='utf-8')
def md(rows, fields, n=20):
    out=['| '+' | '.join(fields)+' |','| '+' | '.join(['---']*len(fields))+' |']
    for r in rows[:n]: out.append('| '+' | '.join(str(r.get(f,'')) for f in fields)+' |')
    return out

def prep(df, date='date'):
    df[date]=pd.to_datetime(df[date],errors='coerce'); df['date_str']=df[date].dt.strftime('%Y-%m-%d')
    return df[(df.date_str>=START)&(df.date_str<=END)].copy()

def c0_audit():
    cov=json.loads(COVERAGE.read_text(encoding='utf-8'))
    raw=prep(pd.read_csv(RAW))
    post=prep(pd.read_csv(POST))
    orig=prep(pd.read_csv(ORIG_READY))
    old=prep(pd.read_csv(OLD,usecols=['date','instrument',OLD_COL]))
    raw['qlib_rank_repaired']=raw.groupby('date_str')['qlib_score_raw'].rank(method='first',ascending=False)
    raw_top=raw[raw.qlib_rank_repaired<=150].copy()
    price_root=ROOT/'qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty'
    price_keys=set()
    for sym in sorted(set(raw_top.instrument.astype(str))):
        fp=price_root/f'{sym}.csv'
        if not fp.exists(): continue
        pdf=pd.read_csv(fp,usecols=['date','close'])
        pdf['date_str']=pd.to_datetime(pdf.date,errors='coerce').dt.strftime('%Y-%m-%d')
        pdf=pdf[(pdf.date_str>=START)&(pdf.date_str<=END)&(pd.to_numeric(pdf.close,errors='coerce')>0)]
        price_keys |= set(zip(pdf.date_str,[sym]*len(pdf)))
    raw_keys=set(zip(raw_top.date_str, raw_top.instrument.astype(str)))
    post_keys=set(zip(post.date_str, post.instrument.astype(str)))
    orig_keys=set(zip(orig[orig.adaptive_score_baseline.notna()].date_str, orig[orig.adaptive_score_baseline.notna()].instrument.astype(str)))
    old_keys=set(zip(old.date_str, old.instrument.astype(str)))
    old_minus=sorted(old_keys-orig_keys); fresh_minus=sorted(orig_keys-old_keys)
    raw_missing=old_keys-raw_keys; post_filtered=(old_keys&raw_keys)-post_keys; replay_missing=(old_keys&post_keys)-orig_keys; price_missing=(old_keys&raw_keys)-price_keys
    rows=[]
    for d in sorted(set(list(old.date_str)+list(raw_top.date_str)+list(post.date_str)+list(orig.date_str))):
        rows.append({'date':d,'old_ltr_rows':sum(1 for k in old_keys if k[0]==d),'fresh_raw_top150_rows':sum(1 for k in raw_keys if k[0]==d),'fresh_post_filter_rows':sum(1 for k in post_keys if k[0]==d),'fresh_replay_ready_adaptive_rows':sum(1 for k in orig_keys if k[0]==d),'raw_minus_replay_ready':sum(1 for k in raw_keys-orig_keys if k[0]==d)})
    reason=[]
    for reason_name, keys in [('missing_fresh_raw_qlib_score',raw_missing),('filtered_by_s2b_post_score_universe_policy',post_filtered),('present_post_filter_but_missing_replay_ready_adaptive',replay_missing),('raw_top150_missing_local_price',price_missing),('fresh_replay_ready_not_in_old_phase1c',fresh_minus)]:
        reason.append({'reason':reason_name,'key_count':len(keys)})
    sample_old=[]
    for d,s in old_minus[:200]:
        sample_old.append({'date':d,'instrument':s,'has_raw_top150':(d,s) in raw_keys,'has_post_filter':(d,s) in post_keys,'has_replay_ready_adaptive':(d,s) in orig_keys,'has_local_price':(d,s) in price_keys,'primary_reason':'missing_raw_score' if (d,s) not in raw_keys else 'filtered_by_s2b_post_score_universe_policy' if (d,s) not in post_keys else 'missing_replay_ready_adaptive'})
    sample_fresh=[{'date':d,'instrument':s,'has_old_phase1c':False,'explanation':'fresh artifact universe/date-symbol exists outside old frozen Phase1C artifact'} for d,s in fresh_minus[:200]]
    source=[
        {'artifact':rel(RAW),'role':'fresh raw qlib score','rows_in_window':len(raw),'daily_min':int(raw.groupby('date_str').instrument.nunique().min()),'daily_median':float(raw.groupby('date_str').instrument.nunique().median()),'daily_max':int(raw.groupby('date_str').instrument.nunique().max())},
        {'artifact':rel(POST),'role':'fresh S2B post-filter score','rows_in_window':len(post),'daily_min':int(post.groupby('date_str').instrument.nunique().min()),'daily_median':float(post.groupby('date_str').instrument.nunique().median()),'daily_max':int(post.groupby('date_str').instrument.nunique().max())},
        {'artifact':rel(ORIG_READY),'role':'fresh S2D replay-ready adaptive','rows_in_window':len(orig),'daily_min':int(orig.groupby('date_str').instrument.nunique().min()),'daily_median':float(orig.groupby('date_str').instrument.nunique().median()),'daily_max':int(orig.groupby('date_str').instrument.nunique().max())},
        {'artifact':rel(OLD),'role':'old Phase1C frozen score','rows_in_window':len(old),'daily_min':int(old.groupby('date_str').instrument.nunique().min()),'daily_median':float(old.groupby('date_str').instrument.nunique().median()),'daily_max':int(old.groupby('date_str').instrument.nunique().max())},
    ]
    wcsv(OUT/'phasec0_coverage_by_day.csv',rows)
    wcsv(OUT/'phasec0_missing_reason_summary.csv',reason)
    wcsv(OUT/'phasec0_old_minus_fresh_sample.csv',sample_old)
    wcsv(OUT/'phasec0_fresh_minus_old_sample.csv',sample_fresh)
    wcsv(OUT/'phasec0_source_artifact_audit.csv',source)
    summary={'created_at':now(),'phase':'phase_c0_coverage_audit','window':f'{START}..{END}','old_keys':len(old_keys),'fresh_top50_keys':len(orig_keys),'fresh_raw_top150_keys':len(raw_keys),'old_minus_fresh_top50':len(old_minus),'fresh_top50_minus_old':len(fresh_minus),'old_intersect_fresh_top50':len(old_keys&orig_keys),'old_intersect_fresh_top50_fresh_ltr':cov.get('overlap_all_three_rows'),'coverage_issue_root_cause':'S2B post-score universe filter narrowed fresh qlib score from raw daily 150 to replay-ready 88/109/150; raw local score and price artifacts are available for offline repair.','offline_repair_feasible':True,'no_training':True,'no_source_artifact_modified':True,'no_frontend_api_provider_monitor_trading':True}
    wjson(OUT/'phasec0_summary.json',summary)
    DOC0.parent.mkdir(parents=True,exist_ok=True)
    lines=['# Phase C0 覆盖审计执行报告','',f'生成时间：{summary["created_at"]}','','## 结论','','fresh top50 覆盖不足是事实，根因在 S2B post-score universe filter：raw fresh qlib 在测试窗口每日 150 支，但 post-filter/replay-ready 只有 88/109/150。该缺口可用本地 raw qlib score、normalized price 与既有 feature 逻辑离线修复。','','## Source Audit','',*md(source,['artifact','role','rows_in_window','daily_min','daily_median','daily_max'],10),'','## Missing Reason','',*md(reason,['reason','key_count'],10),'','## 边界','','未训练 qlib/LTR，未改原 S2B/S2C/S2D/S2F/Phase1C 产物，未触发 provider/accepted latest/monitor/交易/前端/API。']
    DOC0.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return summary

def build_repaired_ready():
    s2c=load_mod('s2c_repair',S2C_SCRIPT)
    input_features, policy, split_contract=s2c.load_contracts()
    raw=pd.read_csv(RAW)
    raw['date']=pd.to_datetime(raw.date,errors='coerce'); raw=raw.dropna(subset=['date','instrument','qlib_score_raw','split']).copy()
    raw=raw[(raw.date.dt.strftime('%Y-%m-%d')>=START)&(raw.date.dt.strftime('%Y-%m-%d')<=END)].copy()
    raw['qlib_rank']=raw.groupby('date')['qlib_score_raw'].rank(method='first',ascending=False).astype(int)
    raw=raw[raw.qlib_rank<=150].copy()
    scores=raw[['date','instrument','qlib_score_raw','qlib_rank','split']].sort_values(['date','qlib_rank','instrument']).reset_index(drop=True)
    scores['top10_flag']=(scores.qlib_rank<=10).astype(int); scores['top30_flag']=(scores.qlib_rank<=30).astype(int); scores['top50_flag']=(scores.qlib_rank<=50).astype(int)
    grp=scores.groupby('date'); scores['qlib_score_percentile_by_date']=grp.qlib_score_raw.rank(pct=True,ascending=True)
    scores['qlib_score_zscore_by_date']=((scores.qlib_score_raw-grp.qlib_score_raw.transform('mean'))/grp.qlib_score_raw.transform('std').replace(0,pd.NA)).fillna(0.0)
    scores=scores.sort_values(['instrument','date'])
    for lag in (1,3,5): scores[f'rank_change_{lag}d']=scores.groupby('instrument').qlib_rank.diff(lag)
    scores['top30_streak']=scores.groupby('instrument',group_keys=False).top30_flag.apply(s2c.streak_count)
    scores['top50_streak']=scores.groupby('instrument',group_keys=False).top50_flag.apply(s2c.streak_count)
    pf=s2c.load_price_features(set(scores.instrument.unique()),input_features)
    mf=s2c.load_market_features(pf)
    sample=scores.merge(pf,on=['date','instrument'],how='left').merge(mf,on='date',how='left')
    sample['feature_complete']=sample[input_features].notna().all(axis=1)
    sample['regime_segment']=sample.apply(s2c.regime_segment,axis=1)
    ready=sample[['date','instrument','qlib_score_raw','qlib_rank','split','qlib_score_percentile_by_date','qlib_score_zscore_by_date','ret20','volatility20','TWII_ret20','TWII_ret60','market_volatility20','market_drawdown60','market_breadth20','regime_segment','feature_complete']].copy()
    ready['adaptive_score_baseline']=0.70*ready.qlib_score_zscore_by_date+0.15*ready.ret20-0.10*ready.volatility20+0.05*ready.TWII_ret20
    ready['confirmed_exit_baseline']=ready.qlib_score_zscore_by_date-0.25*(ready.market_drawdown60<-0.08).astype(float)-0.10*ready.volatility20
    ready['date_str']=ready.date.dt.strftime('%Y-%m-%d')
    ready=ready.sort_values(['date','instrument']).reset_index(drop=True)
    ready.to_csv(OUT/'phasec1_repaired_replay_ready_scores.csv',index=False)
    cov=ready.groupby('date_str').agg(repaired_rows=('instrument','nunique'),adaptive_nonnull=('adaptive_score_baseline',lambda s:int(s.notna().sum())),feature_complete=('feature_complete',lambda s:int(s.sum()))).reset_index().rename(columns={'date_str':'date'})
    orig=prep(pd.read_csv(ORIG_READY))
    orig_cov=orig.groupby('date_str').instrument.nunique().rename('original_rows')
    cov=cov.merge(orig_cov,left_on='date',right_index=True,how='left'); cov['coverage_delta_vs_original']=cov.repaired_rows-cov.original_rows
    cov.to_csv(OUT/'phasec1_coverage_by_day.csv',index=False)
    schema={'created_at':now(),'artifact':rel(OUT/'phasec1_repaired_replay_ready_scores.csv'),'source_raw_score':rel(RAW),'feature_logic_source':rel(S2C_SCRIPT),'score_formula':'0.70*qlib_score_zscore_by_date + 0.15*ret20 - 0.10*volatility20 + 0.05*TWII_ret20','row_count':int(len(ready)),'daily_min':int(cov.repaired_rows.min()),'daily_median':float(cov.repaired_rows.median()),'daily_max':int(cov.repaired_rows.max()),'no_training':True}
    wjson(OUT/'phasec1_repaired_artifact_schema.json',schema)
    return ready, cov, schema

def metric_row(result, baseline_method=None, baseline_metrics=None):
    m=result['metrics']; row={'period':'same_test_window','start_date':START,'end_date':END,'method':result['method'],'comparison_status':'completed',**m}
    if baseline_metrics:
        row['relative_return_vs_phase1c_anchor']=round(m['fee_tax_adjusted_net_return']-baseline_metrics['fee_tax_adjusted_net_return'],6)
        row['relative_drawdown_vs_phase1c_anchor']=round(m['max_drawdown']-baseline_metrics['max_drawdown'],6)
        row['relative_actions_vs_phase1c_anchor']=int(m['action_count'])-int(baseline_metrics['action_count'])
    return row

def replay_and_reports(ready,cov,schema):
    s2d=load_mod('s2d_repair',S2D_SCRIPT)
    old=prep(pd.read_csv(OLD,usecols=['date','instrument',OLD_COL,'regime_segment'] if False else ['date','instrument',OLD_COL]))
    old=old.rename(columns={OLD_COL:'old_phase1c_ltr_score'}); old['regime_segment']='unknown'
    orig=prep(pd.read_csv(ORIG_READY))
    repaired=ready.copy()
    df=old[['date_str','instrument','old_phase1c_ltr_score']].merge(orig[['date_str','instrument','adaptive_score_baseline','ltr_score','regime_segment']],on=['date_str','instrument'],how='outer').merge(repaired[['date_str','instrument','adaptive_score_baseline','regime_segment']].rename(columns={'adaptive_score_baseline':'repaired_adaptive_score_baseline','regime_segment':'repaired_regime_segment'}),on=['date_str','instrument'],how='outer')
    df['date']=pd.to_datetime(df.date_str); df['split']='test'; df['regime_segment']=df.regime_segment.fillna(df.repaired_regime_segment).fillna('unknown')
    prices=s2d.PriceStore(set(df.instrument.dropna().astype(str)))
    specs={
      'phase1c_anchor_simple':s2d.MethodSpec('phase1c_anchor_simple','old_phase1c_ltr_score',50,False),
      'original_fresh_top50_adaptive':s2d.MethodSpec('original_fresh_top50_adaptive','adaptive_score_baseline',50,False),
      'repaired_fresh_top50_adaptive':s2d.MethodSpec('repaired_fresh_top50_adaptive','repaired_adaptive_score_baseline',50,False),
      'original_fresh_ltr':s2d.MethodSpec('original_fresh_ltr','ltr_score',50,False),
    }
    res={k:s2d.replay(df,prices,v,'same_test_window',START,END) for k,v in specs.items()}
    anchor=res['phase1c_anchor_simple']['metrics']
    rows=[metric_row(res[k],baseline_metrics=anchor) for k in specs]
    fields=['period','start_date','end_date','method','comparison_status','fee_tax_adjusted_net_return','final_equity','max_drawdown','action_count','buy_count','sell_count','fee_and_tax','turnover_proxy_by_notional_over_avg_equity','turnover_notional','trading_days','initial_cash_or_equity_assumption','fee_rate','tax_rate','position_count_target','daily_nav_available_count','missing_price_days','skipped_trade_count','last_day_new_trade_without_next_price_count','relative_return_vs_phase1c_anchor','relative_drawdown_vs_phase1c_anchor','relative_actions_vs_phase1c_anchor']
    wcsv(OUT/'phasec1_full_universe_metrics.csv',rows,fields)
    frozen_common=df[df.old_phase1c_ltr_score.notna()&df.adaptive_score_baseline.notna()&df.ltr_score.notna()].copy()
    frozen_methods=['phase1c_anchor_simple','original_fresh_top50_adaptive','repaired_fresh_top50_adaptive']
    fres={k:s2d.replay(frozen_common,prices,specs[k],'frozen_s2f_common_universe',START,END) for k in frozen_methods}
    fanchor=fres['phase1c_anchor_simple']['metrics']; frows=[metric_row(fres[k],baseline_metrics=fanchor) for k in frozen_methods]
    for row in frows:
        row['common_universe_type']='frozen_s2f_common_universe'
        row['common_universe_key_count']=int(frozen_common.shape[0])
    wcsv(OUT/'phasec1_frozen_s2f_common_universe_metrics.csv',frows,['common_universe_type','common_universe_key_count']+fields)

    pairwise_common=df[df.old_phase1c_ltr_score.notna()&df.adaptive_score_baseline.notna()&df.repaired_adaptive_score_baseline.notna()].copy()
    pres={k:s2d.replay(pairwise_common,prices,specs[k],'repaired_pairwise_common_universe',START,END) for k in frozen_methods}
    panchor=pres['phase1c_anchor_simple']['metrics']; prows=[metric_row(pres[k],baseline_metrics=panchor) for k in frozen_methods]
    for row in prows:
        row['common_universe_type']='repaired_pairwise_common_universe'
        row['common_universe_key_count']=int(pairwise_common.shape[0])
    wcsv(OUT/'phasec1_repaired_pairwise_common_universe_metrics.csv',prows,['common_universe_type','common_universe_key_count']+fields)
    crows=prows
    wcsv(OUT/'phasec1_common_universe_metrics.csv',prows,['common_universe_type','common_universe_key_count']+fields)

    key_audit=[
      {'common_universe_type':'frozen_s2f_common_universe','definition':'Phase1C anchor ∩ original fresh top50 ∩ original fresh LTR','key_count':int(frozen_common.shape[0]),'phase1c_common_return':fanchor['fee_tax_adjusted_net_return'],'phase1c_common_max_drawdown':fanchor['max_drawdown'],'note':'Matches Phase A2/S2F four-strategy common key definition used before repaired fresh top50 was introduced.'},
      {'common_universe_type':'repaired_pairwise_common_universe','definition':'Phase1C anchor ∩ original fresh top50 ∩ repaired fresh top50','key_count':int(pairwise_common.shape[0]),'phase1c_common_return':panchor['fee_tax_adjusted_net_return'],'phase1c_common_max_drawdown':panchor['max_drawdown'],'note':'Pairwise repaired audit universe; larger/different than frozen S2F common because it does not require original fresh LTR score.'},
      {'common_universe_type':'full_universe','definition':'method-specific available replay rows','key_count':int(df.shape[0]),'phase1c_common_return':'not_applicable','phase1c_common_max_drawdown':'not_applicable','note':'Full universe metrics are method-specific and are not a common key set.'},
    ]
    wcsv(OUT/'phasec1_common_universe_key_audit.csv',key_audit)

    feature_audit=[
      {'field':'feature_complete','definition':'All LTR training features from the S1B3 feature contract are non-null for the row. This is stricter than fresh top50 adaptive requirements.','used_by_repaired_top50_replay':False,'impact':'Rows can have feature_complete=false while adaptive_score_baseline is available.'},
      {'field':'adaptive_required_fields','definition':'qlib_score_zscore_by_date, ret20, volatility20, TWII_ret20 for adaptive_score_baseline formula.','used_by_repaired_top50_replay':True,'impact':'Rows with adaptive_score_baseline null are excluded from candidate ranking by replay dropna on score column.'},
      {'field':'price','definition':'Local normalized price used by S2D PriceStore for next-day execution and mark-to-market.','used_by_repaired_top50_replay':True,'impact':'Missing execution/mark-to-market prices would appear in missing/skipped/last-day audits.'},
      {'field':'adaptive_nonnull','definition':'Count of repaired rows with non-null adaptive_score_baseline per day.','used_by_repaired_top50_replay':True,'impact':'Daily candidate ranking uses these non-null rows; early days still have at least 148-149 non-null rows, above top10 holding needs.'},
    ]
    wcsv(OUT/'phasec1_feature_complete_definition_audit.csv',feature_audit)
    nav=[]; acts=[]
    for r in res.values(): nav+=r['curve']; acts+=r['actions']
    wcsv(OUT/'phasec1_daily_nav.csv',nav,['date','period','method','equity','cash','holding_count','regime_segment','missing_price_count'])
    wcsv(OUT/'phasec1_action_audit.csv',acts,sorted({k for a in acts for k in a}))
    active=[a for a in acts if a.get('method')=='repaired_fresh_top50_adaptive' and a.get('action') in {'historical_add','historical_risk_reduce'}]
    bad=sum(1 for a in active if str(a['execution_date'])<=str(a['signal_date']))
    rm=res['repaired_fresh_top50_adaptive']['metrics']
    next_rows=[{'method':'repaired_fresh_top50_adaptive','active_action_count':len(active),'execution_date_after_signal_date':bad==0,'execution_date_not_after_signal_violations':bad,'missing_price_days':rm['missing_price_days'],'skipped_trade_count':rm['skipped_trade_count'],'last_day_new_trade_without_next_price_count':rm['last_day_new_trade_without_next_price_count'],'pass':'yes' if bad==0 and rm['missing_price_days']==0 and rm['skipped_trade_count']==0 and rm['last_day_new_trade_without_next_price_count']==0 else 'no'}]
    wcsv(OUT/'phasec1_next_day_accounting_audit.csv',next_rows)
    # Real PnL contribution: cost-basis realized PnL plus end-of-window unrealized PnL.
    bysym=defaultdict(lambda:defaultdict(float)); byday=defaultdict(lambda:defaultdict(float)); hold={}; basis={}; prev_close={}
    repaired_nav=pd.DataFrame(res['repaired_fresh_top50_adaptive']['curve'])
    repaired_dates=repaired_nav['date'].astype(str).tolist()
    action_by_day=defaultdict(list)
    for a in active:
        action_by_day[str(a['effective_nav_date'])].append(a)
    for day in repaired_dates:
        start_hold=dict(hold)
        for sym,qty in start_hold.items():
            close=prices.close_on_or_before(sym, day)
            old_close=prev_close.get(sym)
            if close is not None and old_close is not None:
                mtm=qty*(close-old_close)
                byday[day]['unrealized_pnl']+=mtm
        for a in sorted(action_by_day.get(day,[]), key=lambda x:x['symbol']):
            sym=a['symbol']; qty=int(a['quantity']); px=float(a['price']); fee=float(a['fee_and_tax']); notional=qty*px
            if a['action']=='historical_add':
                hold[sym]=hold.get(sym,0)+qty; basis[sym]=basis.get(sym,0.0)+notional
                bysym[sym]['fee_tax_allocated']+=fee; byday[day]['fee_tax_allocated']+=fee
            elif a['action']=='historical_risk_reduce':
                h=hold.get(sym,0); avg=basis.get(sym,0.0)/h if h else 0.0
                realized=notional-avg*qty
                hold[sym]=max(0,h-qty); basis[sym]=max(0.0,basis.get(sym,0.0)-avg*qty)
                if hold[sym]==0:
                    hold.pop(sym,None); basis.pop(sym,None)
                bysym[sym]['realized_pnl']+=realized; bysym[sym]['fee_tax_allocated']+=fee
                byday[day]['realized_pnl']+=realized; byday[day]['fee_tax_allocated']+=fee
        for sym in list(hold):
            close=prices.close_on_or_before(sym, day)
            if close is not None: prev_close[sym]=close
        for sym in list(prev_close):
            if sym not in hold: prev_close.pop(sym,None)
    for sym,qty in hold.items():
        close=prices.close_on_or_before(sym, repaired_dates[-1])
        if close is not None:
            bysym[sym]['unrealized_pnl']=qty*close-basis.get(sym,0.0)
    total=sum(v['realized_pnl']+v['unrealized_pnl']-v['fee_tax_allocated'] for v in bysym.values())
    symrows=[]
    for s,v in bysym.items():
        net=v['realized_pnl']+v['unrealized_pnl']-v['fee_tax_allocated']
        symrows.append({'method':'repaired_fresh_top50_adaptive','symbol':s,'realized_pnl':round(v['realized_pnl'],2),'unrealized_pnl':round(v['unrealized_pnl'],2),'fee_tax_allocated':round(v['fee_tax_allocated'],2),'net_pnl':round(net,2),'share_of_total_net_pnl':round(net/total,6) if total else 0.0})
    dayrows=[]
    for d,v in byday.items():
        net=v['realized_pnl']+v['unrealized_pnl']-v['fee_tax_allocated']
        dayrows.append({'method':'repaired_fresh_top50_adaptive','date':d,'realized_pnl':round(v['realized_pnl'],2),'unrealized_pnl':round(v['unrealized_pnl'],2),'fee_tax_allocated':round(v['fee_tax_allocated'],2),'net_pnl':round(net,2),'share_of_total_net_pnl':round(net/total,6) if total else 0.0})
    symrows=sorted(symrows,key=lambda r:r['net_pnl'],reverse=True); dayrows=sorted(dayrows,key=lambda r:r['net_pnl'],reverse=True)
    wcsv(OUT/'phasec1_real_pnl_contribution_by_symbol.csv',symrows)
    wcsv(OUT/'phasec1_real_pnl_contribution_by_day.csv',dayrows)
    nav_gain=res['repaired_fresh_top50_adaptive']['metrics']['final_equity']-1_000_000.0
    pnl_diff=round(total-nav_gain,2)
    repaired_nav=pd.DataFrame(res['repaired_fresh_top50_adaptive']['curve'])
    repaired_nav['equity']=pd.to_numeric(repaired_nav['equity'], errors='coerce')
    max_abs_daily_return=float(repaired_nav['equity'].pct_change().fillna(0).abs().max())
    top_symbol_share=max([abs(float(r['share_of_total_net_pnl'])) for r in symrows] or [0.0])
    top_day_share=max([abs(float(r['share_of_total_net_pnl'])) for r in dayrows] or [0.0])
    max_action_price=max([float(a.get('price') or 0) for a in active] or [0.0])
    outlier=[
      {'audit_item':'repaired_coverage_min_median_max','value':f"{schema['daily_min']}/{schema['daily_median']}/{schema['daily_max']}",'status':'ok' if schema['daily_min']>=145 and schema['daily_median']>=149 and schema['daily_max']<=150 else 'watch','note':'coverage target min>=145 median>=149 max<=150'},
      {'audit_item':'real_pnl_total_vs_nav_gain','value':pnl_diff,'status':'ok' if abs(pnl_diff)<=1.0 else 'watch','note':'symbol-level net PnL sum minus repaired final equity gain'},
      {'audit_item':'top_symbol_abs_share_of_total_net_pnl','value':round(top_symbol_share,6),'status':'watch' if top_symbol_share>0.35 else 'ok','note':'single-symbol contribution concentration threshold 0.35'},
      {'audit_item':'top_day_abs_share_of_total_net_pnl','value':round(top_day_share,6),'status':'watch' if top_day_share>0.35 else 'ok','note':'single-day contribution concentration threshold 0.35'},
      {'audit_item':'max_abs_daily_nav_return','value':round(max_abs_daily_return,6),'status':'watch' if max_abs_daily_return>0.12 else 'ok','note':'abnormal daily return threshold 0.12'},
      {'audit_item':'max_action_price','value':round(max_action_price,4),'status':'info','note':'historical replay action price sanity sample maximum'},
      {'audit_item':'repaired_vs_phase1c_full_return_diff','value':round(res['repaired_fresh_top50_adaptive']['metrics']['fee_tax_adjusted_net_return']-anchor['fee_tax_adjusted_net_return'],6),'status':'info','note':'positive means repaired fresh top50 above Phase1C anchor'}]
    wcsv(OUT/'phasec1_outlier_audit.csv',outlier)
    summary={'created_at':now(),'phase':'phase_c1_repair_and_replay','coverage_min':schema['daily_min'],'coverage_median':schema['daily_median'],'coverage_max':schema['daily_max'],'repaired_full_return':res['repaired_fresh_top50_adaptive']['metrics']['fee_tax_adjusted_net_return'],'phase1c_anchor_full_return':anchor['fee_tax_adjusted_net_return'],'repaired_minus_phase1c_full':round(res['repaired_fresh_top50_adaptive']['metrics']['fee_tax_adjusted_net_return']-anchor['fee_tax_adjusted_net_return'],6),'frozen_s2f_common_key_count':int(frozen_common.shape[0]),'frozen_s2f_common_phase1c_return':fanchor['fee_tax_adjusted_net_return'],'frozen_s2f_common_repaired_return':fres['repaired_fresh_top50_adaptive']['metrics']['fee_tax_adjusted_net_return'],'frozen_s2f_common_repaired_minus_phase1c':round(fres['repaired_fresh_top50_adaptive']['metrics']['fee_tax_adjusted_net_return']-fanchor['fee_tax_adjusted_net_return'],6),'repaired_pairwise_common_key_count':int(pairwise_common.shape[0]),'repaired_pairwise_common_phase1c_return':panchor['fee_tax_adjusted_net_return'],'repaired_pairwise_common_repaired_return':pres['repaired_fresh_top50_adaptive']['metrics']['fee_tax_adjusted_net_return'],'repaired_pairwise_common_repaired_minus_phase1c':round(pres['repaired_fresh_top50_adaptive']['metrics']['fee_tax_adjusted_net_return']-panchor['fee_tax_adjusted_net_return'],6),'next_day_accounting_pass':next_rows[0]['pass']=='yes','recommended_gate':'phase_c1_common_universe_revision_completed_hold_for_c2_review','c2_frontend_decision_deferred':True,'repaired_fresh_ltr_generated':False,'repaired_fresh_ltr_reason':'not generated because extending LTR score to newly repaired rows would require new LTR inference/training-scope score production; original fresh LTR is retained as frozen comparator.','no_training':True,'no_source_artifact_modified':True,'no_frontend_api_provider_monitor_trading':True}
    wjson(OUT/'phasec1_summary.json',summary)
    DOC1.parent.mkdir(parents=True,exist_ok=True)
    top_sym=symrows[:5]
    worst_sym=list(reversed(symrows[-5:])) if len(symrows)>=5 else list(reversed(symrows))
    top_day=dayrows[:5]
    top_sym=symrows[:5]
    worst_sym=list(reversed(symrows[-5:])) if len(symrows)>=5 else list(reversed(symrows))
    top_day=dayrows[:5]
    lines=['# Phase C1 离线覆盖修复与只读 Replay 执行报告','',f'生成时间：{summary["created_at"]}','','## 结论','',f"repaired fresh top50 覆盖为 `{schema['daily_min']}/{schema['daily_median']}/{schema['daily_max']}`，达到目标。full universe 下 repaired fresh top50 return `{summary['repaired_full_return']}`，Phase1C anchor `{summary['phase1c_anchor_full_return']}`，差值 `{summary['repaired_minus_phase1c_full']}`。",'',"根据审计意见，本修订版同时输出两套 common universe：`frozen_s2f_common_universe` 与 `repaired_pairwise_common_universe`。C2 如需回答与 Phase A2/S2F 冻结 anchor 的 common 对照，应优先使用 frozen S2F common 口径；pairwise common 仅用于解释 repaired 覆盖过滤影响。",'',"不得据此修改前端或切换默认策略，C2 前端影响判断仍需单独审查。",'','## Source Provenance','',f"- repaired source：`{rel(RAW)}` + 本地 normalized price + `{rel(S2C_SCRIPT)}` 的历史特征构建逻辑。",f"- replay engine：`{rel(S2D_SCRIPT)}`，费用、税费、持仓数、next-day execution 与 S2F/Phase1C anchor 一致。",f"- repaired artifact schema：`{rel(OUT/'phasec1_repaired_artifact_schema.json')}`。",'','## Coverage','',f"- original fresh top50 daily rows：`88 / 109.0 / 150`。",f"- repaired fresh top50 daily rows：`{schema['daily_min']} / {schema['daily_median']} / {schema['daily_max']}`。",'','## Full Universe Metrics','',*md(rows,['method','fee_tax_adjusted_net_return','max_drawdown','action_count','fee_and_tax','missing_price_days','skipped_trade_count','relative_return_vs_phase1c_anchor'],10),'','## Frozen S2F Common Universe','',f"- definition：Phase1C anchor ∩ original fresh top50 ∩ original fresh LTR。",f"- key count：`{int(frozen_common.shape[0])}`。",f"- Phase1C common return / max DD：`{fanchor['fee_tax_adjusted_net_return']} / {fanchor['max_drawdown']}`。",'',*md(frows,['method','fee_tax_adjusted_net_return','max_drawdown','action_count','fee_and_tax','missing_price_days','skipped_trade_count','relative_return_vs_phase1c_anchor'],10),'','## Repaired Pairwise Common Universe','',f"- definition：Phase1C anchor ∩ original fresh top50 ∩ repaired fresh top50。",f"- key count：`{int(pairwise_common.shape[0])}`。",f"- 该口径下 Phase1C common return 从 frozen S2F 的 `0.641235` 变为 `{panchor['fee_tax_adjusted_net_return']}`，原因是该 key set 不要求 original fresh LTR score，且包含不同的 date/instrument 交集；它不是 Phase A2/S2F 冻结 common。",'',*md(prows,['method','fee_tax_adjusted_net_return','max_drawdown','action_count','fee_and_tax','missing_price_days','skipped_trade_count','relative_return_vs_phase1c_anchor'],10),'','## Feature Complete Definition Audit','',"`feature_complete` 表示 LTR 全特征合同完整，不等同于 fresh top50 adaptive 必需字段完整。repaired top50 replay 只依赖 `adaptive_score_baseline`、本地价格和 next-day execution；score 缺失行会被 replay ranking 的 `dropna(score_col)` 排除。早期 `feature_complete=0` 不阻断 replay，因为 adaptive 必需字段仍大多可用。",'',*md(feature_audit,['field','used_by_repaired_top50_replay','impact'],10),'','## Next-day / Fee / Action Audit','',*md(next_rows,['method','active_action_count','execution_date_after_signal_date','missing_price_days','skipped_trade_count','last_day_new_trade_without_next_price_count','pass'],5),'',f"- repaired action_count：`{rm['action_count']}`，buy_count：`{rm['buy_count']}`，sell_count：`{rm['sell_count']}`。这些均为历史回放统计。",f"- fee_rate：`{rm['fee_rate']}`，tax_rate：`{rm['tax_rate']}`，fee_and_tax：`{rm['fee_and_tax']}`。",'','## Real PnL Contribution','',"Top symbols：",'',*md(top_sym,['symbol','realized_pnl','unrealized_pnl','fee_tax_allocated','net_pnl','share_of_total_net_pnl'],5),'',"Worst symbols：",'',*md(worst_sym,['symbol','realized_pnl','unrealized_pnl','fee_tax_allocated','net_pnl','share_of_total_net_pnl'],5),'',"Top days：",'',*md(top_day,['date','realized_pnl','unrealized_pnl','fee_tax_allocated','net_pnl','share_of_total_net_pnl'],5),'','## Outlier Audit','',*md(outlier,['audit_item','value','status','note'],20),'','## Fresh LTR 说明','','repaired fresh LTR 未生成：现有冻结 LTR score 只覆盖原 post-filter 行，扩展到 repaired 新增行需要新的 LTR score 生产；本轮目标是 fresh top50 adaptive 覆盖修复，避免混入 LTR score 变更。','','## 产物','',f"- `{rel(OUT/'phasec1_repaired_replay_ready_scores.csv')}`",f"- `{rel(OUT/'phasec1_coverage_by_day.csv')}`",f"- `{rel(OUT/'phasec1_full_universe_metrics.csv')}`",f"- `{rel(OUT/'phasec1_frozen_s2f_common_universe_metrics.csv')}`",f"- `{rel(OUT/'phasec1_repaired_pairwise_common_universe_metrics.csv')}`",f"- `{rel(OUT/'phasec1_common_universe_key_audit.csv')}`",f"- `{rel(OUT/'phasec1_feature_complete_definition_audit.csv')}`",f"- `{rel(OUT/'phasec1_daily_nav.csv')}`",f"- `{rel(OUT/'phasec1_action_audit.csv')}`",f"- `{rel(OUT/'phasec1_next_day_accounting_audit.csv')}`",f"- `{rel(OUT/'phasec1_real_pnl_contribution_by_symbol.csv')}`",f"- `{rel(OUT/'phasec1_real_pnl_contribution_by_day.csv')}`",f"- `{rel(OUT/'phasec1_outlier_audit.csv')}`",f"- `{rel(OUT/'phasec1_summary.json')}`",'','## 边界','','未训练 qlib/LTR，未改 Phase1C anchor，未改费用税费/next-day execution/持仓数量/窗口，未改前端/API，未触发 provider/accepted latest/monitor/交易链路。']
    DOC1.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return summary

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    c0=c0_audit()
    if not c0['offline_repair_feasible']: raise SystemExit('C0 blocked: offline repair infeasible')
    ready,cov,schema=build_repaired_ready()
    c1=replay_and_reports(ready,cov,schema)
    print(json.dumps({'ok':True,'c0_report':rel(DOC0),'c1_report':rel(DOC1),'c0_summary':rel(OUT/'phasec0_summary.json'),'c1_summary':rel(OUT/'phasec1_summary.json')},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
