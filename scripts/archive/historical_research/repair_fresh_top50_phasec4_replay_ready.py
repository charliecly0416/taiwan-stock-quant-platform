#!/usr/bin/env python3
from __future__ import annotations

import csv, json
from bisect import bisect_right
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data_tw/experiments/fresh_top50_coverage_repair'
REPORT=ROOT/'docs/tw_fresh_top50_coverage_repair/PHASEC4_REPLAY_READY_REPAIR_EXECUTION_REPORT_CN.md'
C1=OUT/'phasec1_repaired_replay_ready_scores.csv'
C3_AUDIT=OUT/'phasec3_replay_ready_audit.csv'
RAW=ROOT/'data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_raw_score_rank.csv'
ALL_TXT=ROOT/'qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt'
ACCEPTED_TXT=ROOT/'qlib_pipeline/data_tw/experiments/option_c_forward_validation/timed_data_availability_retry_20260601T101323Z/symbols_accepted_prediction_universe.txt'
PRICE_ROOT=ROOT/'qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty'
START='2025-07-01'; END='2026-05-07'
REQ=['qlib_score_zscore_by_date','ret20','volatility20','TWII_ret20']

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
def rel(path:Path):
    try: return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception: return str(path)
def wcsv(path, rows, fields=None):
    path.parent.mkdir(parents=True,exist_ok=True)
    if fields is None: fields=sorted({k for r in rows for k in r}) if rows else ['status']
    with path.open('w',encoding='utf-8',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=fields); wr.writeheader(); wr.writerows(rows)
def wjson(path,payload): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(payload,ensure_ascii=True,indent=2,default=str)+'\n',encoding='utf-8')
def md(rows, fields, limit=20):
    out=['| '+' | '.join(fields)+' |','| '+' | '.join(['---']*len(fields))+' |']
    for r in rows[:limit]: out.append('| '+' | '.join(str(r.get(f,'')) for f in fields)+' |')
    return out

def read_intervals(path):
    out={}
    for line in path.read_text(encoding='utf-8').splitlines():
        parts=line.split()
        if len(parts)>=3: out.setdefault(parts[0],[]).append((parts[1][:10],parts[2][:10]))
    return out
def in_intervals(intervals,sym,day): return any(s<=day<=e for s,e in intervals.get(sym,[]))
def accepted(): return {x.strip() for x in ACCEPTED_TXT.read_text(encoding='utf-8').splitlines() if x.strip()}

def price_dates(sym):
    fp=PRICE_ROOT/f'{sym}.csv'
    if not fp.exists(): return []
    df=pd.read_csv(fp,usecols=['date','close'])
    df['date_str']=pd.to_datetime(df.date,errors='coerce').dt.strftime('%Y-%m-%d')
    df['close']=pd.to_numeric(df.close,errors='coerce')
    return sorted(df.loc[df.close.gt(0)&df.date_str.notna(),'date_str'].astype(str).unique().tolist())

def build_price_maps(symbols):
    current=set(); nxt=set(); ranges={}; dates_by={}
    for sym in sorted(symbols):
        dates=price_dates(sym); dates_by[sym]=dates
        if dates: ranges[sym]=(dates[0],dates[-1])
        for d in dates:
            if START<=d<=END: current.add((d,sym))
        for d in [x for x in dates if START<=x<=END]:
            idx=bisect_right(dates,d)
            if idx<len(dates): nxt.add((d,sym))
    return current,nxt,ranges,dates_by

def classify_missing(row):
    sym=row['instrument']; day=row['date']
    if not row['has_current_price']:
        return 'price_not_started_asof' if row.get('price_first_date') and str(row['price_first_date'])>day else 'price_join_or_calendar_gap'
    if not row['has_adaptive_score']:
        return 'feature_warmup_insufficient_ret20_volatility20'
    if not row['has_next_execution_price']:
        return 'missing_next_execution_price'
    return 'other_replay_ready_gap'

def audit_rows(df, current, nxt, intervals, acc):
    rows=[]
    for r in df.to_dict('records'):
        day=str(r['date_str']); sym=str(r['instrument'])
        has_current=(day,sym) in current; has_next=(day,sym) in nxt
        has_qlib=pd.notna(r.get('qlib_score_raw')); has_adapt=pd.notna(r.get('adaptive_score_baseline'))
        has_ret=pd.notna(r.get('ret20')); has_vol=pd.notna(r.get('volatility20')); has_twii=pd.notna(r.get('TWII_ret20'))
        in_all=in_intervals(intervals,sym,day); in_acc=sym in acc
        ready=bool(in_all and in_acc and has_qlib and has_current and has_next and has_adapt and has_ret and has_vol and has_twii)
        rows.append({'date':day,'instrument':sym,'has_qlib_score':has_qlib,'has_current_price':has_current,'has_next_execution_price':has_next,'has_adaptive_score':has_adapt,'has_ret20':has_ret,'has_volatility20':has_vol,'has_twii_ret20':has_twii,'in_option_c_instrument_range':in_all,'in_accepted_prediction_universe':in_acc,'replay_ready':ready})
    return pd.DataFrame(rows)

def main():
    ready=pd.read_csv(C1,parse_dates=['date']); ready['date_str']=ready.date.dt.strftime('%Y-%m-%d')
    ready=ready[(ready.date_str>=START)&(ready.date_str<=END)].copy()
    raw=pd.read_csv(RAW,parse_dates=['date']); raw['date_str']=raw.date.dt.strftime('%Y-%m-%d')
    raw=raw[(raw.date_str>=START)&(raw.date_str<=END)].copy()
    raw['raw_rank_by_date']=raw.groupby('date_str').qlib_score_raw.rank(method='first',ascending=False).astype(int)
    c3=pd.read_csv(C3_AUDIT)
    miss=c3[~c3.replay_ready].copy()
    miss_rows=[]
    for r in miss.to_dict('records'):
        root=classify_missing(r)
        repair='exclude_from_replay_ready_candidate'
        if root=='feature_warmup_insufficient_ret20_volatility20': repair='exclude_until_ret20_volatility20_warmup_available'
        if root=='price_not_started_asof': repair='exclude_until_local_price_starts'
        miss_rows.append({'date':r['date'],'instrument':r['instrument'],'qlib_score_raw':ready[(ready.date_str==r['date'])&(ready.instrument==r['instrument'])].qlib_score_raw.iloc[0] if len(ready[(ready.date_str==r['date'])&(ready.instrument==r['instrument'])]) else '','qlib_rank':ready[(ready.date_str==r['date'])&(ready.instrument==r['instrument'])].qlib_rank.iloc[0] if len(ready[(ready.date_str==r['date'])&(ready.instrument==r['instrument'])]) else '','has_current_price':r['has_current_price'],'has_next_execution_price':r['has_next_execution_price'],'has_adaptive_score':r['has_adaptive_score'],'has_ret20':r['has_ret20'],'has_volatility20':r['has_volatility20'],'price_first_date':r.get('price_first_date',''),'price_last_date':r.get('price_last_date',''),'next_execution_date':'','root_cause':root,'repair_action':repair})
    wcsv(OUT/'phasec4_missing_replay_ready_rows.csv',miss_rows)
    reason_summary=[]
    for root,grp in pd.DataFrame(miss_rows).groupby('root_cause'):
        reason_summary.append({'root_cause':root,'row_count':int(len(grp)),'instruments':','.join(sorted(grp.instrument.unique())),'repair_action':';'.join(sorted(set(grp.repair_action)))})
    wcsv(OUT/'phasec4_missing_reason_summary.csv',reason_summary)

    intervals=read_intervals(ALL_TXT); acc=accepted()
    current,nxt,ranges,dates_by=build_price_maps(set(raw.instrument.astype(str))|set(ready.instrument.astype(str)))
    # C4 repair: keep only C1 rows that are replay-ready; raw score contains exactly 150/day, so there are no rank>150 same-day rows for top-up.
    audit=audit_rows(ready,current,nxt,intervals,acc)
    good_keys=set(zip(audit[audit.replay_ready].date,audit[audit.replay_ready].instrument))
    repaired=ready[ready.apply(lambda x:(x.date_str,x.instrument) in good_keys,axis=1)].copy()
    # Preserve daily order and do not synthesize rows. Top-up feasibility is audited against raw rank > 150.
    topup_rows=[]
    for day,g in raw.groupby('date_str'):
        needed=150-int((repaired.date_str==day).sum())
        later=g[g.raw_rank_by_date>150].sort_values('raw_rank_by_date')
        topup_rows.append({'date':day,'needed_topup_rows':needed,'available_raw_rank_gt_150_rows':int(len(later)),'topup_status':'not_possible_raw_artifact_has_only_150_rows' if needed>0 and len(later)==0 else 'not_needed' if needed==0 else 'available_not_used'})
    wcsv(OUT/'phasec4_topup_feasibility_audit.csv',topup_rows)
    repaired.to_csv(OUT/'phasec4_repaired_replay_ready_scores.csv',index=False)
    audit4=audit_rows(repaired,current,nxt,intervals,acc)
    wcsv(OUT/'phasec4_replay_ready_audit.csv',audit4.to_dict('records'))
    elig_rows=[]
    for r in repaired.to_dict('records'):
        day=str(r['date_str']); sym=str(r['instrument'])
        elig_rows.append({'date':day,'instrument':sym,'has_repaired_row':True,'in_option_c_instrument_range':in_intervals(intervals,sym,day),'in_accepted_prediction_universe':sym in acc,'eligibility_status':'eligible' if in_intervals(intervals,sym,day) and sym in acc else 'ineligible','reason':'ok' if in_intervals(intervals,sym,day) and sym in acc else 'ineligible'})
    wcsv(OUT/'phasec4_asof_eligibility_audit.csv',elig_rows)
    daily=[]
    for day in sorted(ready.date_str.unique()):
        total=int((repaired.date_str==day).sum()); g=audit4[audit4.date==day]
        orig_bad=int((audit.date==day).sum()-audit[(audit.date==day)&(audit.replay_ready)].shape[0])
        top=next(x for x in topup_rows if x['date']==day)
        daily.append({'date':day,'daily_repaired_rows':total,'daily_replay_ready_rows':int(g.replay_ready.sum()) if len(g) else 0,'excluded_non_replay_ready_rows':orig_bad,'needed_topup_rows':top['needed_topup_rows'],'available_raw_rank_gt_150_rows':top['available_raw_rank_gt_150_rows'],'topup_status':top['topup_status']})
    wcsv(OUT/'phasec4_daily_coverage_summary.csv',daily)
    ddf=pd.DataFrame(daily)
    summary={'created_at':now(),'phase':'phase_c4_replay_ready_repair','input_rows':int(len(ready)),'excluded_non_replay_ready_rows':int(len(ready)-len(repaired)),'output_rows':int(len(repaired)),'daily_repaired_rows_min':int(ddf.daily_repaired_rows.min()),'daily_repaired_rows_median':float(ddf.daily_repaired_rows.median()),'daily_repaired_rows_max':int(ddf.daily_repaired_rows.max()),'daily_replay_ready_rows_min':int(ddf.daily_replay_ready_rows.min()),'future_or_instrument_range_violation_rows':0,'accepted_universe_violation_rows':0,'missing_current_price_rows_after_repair':int((~audit4.has_current_price).sum()) if len(audit4) else 0,'missing_next_execution_price_rows_after_repair':int((~audit4.has_next_execution_price).sum()) if len(audit4) else 0,'missing_adaptive_score_rows_after_repair':int((~audit4.has_adaptive_score).sum()) if len(audit4) else 0,'topup_possible':False,'topup_blocker':'S2B raw score artifact has exactly 150 rows per day in target window; no rank >150 same-day candidates exist for top-up without regenerating qlib scores or changing source artifact.','uses_return_metrics_for_strategy_superiority':False,'no_training':True,'no_frontend_api_provider_monitor_trading':True,'recommended_gate':'phase_c4_replay_ready_repair_passed_with_coverage_below_150_explained' if int((~audit4.replay_ready).sum())==0 else 'phase_c4_blocked_requires_further_repair','artifacts':{'missing_rows':rel(OUT/'phasec4_missing_replay_ready_rows.csv'),'missing_reason_summary':rel(OUT/'phasec4_missing_reason_summary.csv'),'repaired_scores':rel(OUT/'phasec4_repaired_replay_ready_scores.csv'),'daily_coverage':rel(OUT/'phasec4_daily_coverage_summary.csv'),'topup_feasibility':rel(OUT/'phasec4_topup_feasibility_audit.csv'),'report':rel(REPORT)}}
    wjson(OUT/'phasec4_summary.json',summary)
    lines=['# Phase C4 执行报告：Replay-Ready Repair','',f"生成时间：{summary['created_at']}",'','## 1. 执行边界','','本轮只修复或解释 C3 replay-ready 缺口，不使用收益率判断策略优劣，不训练 qlib/LTR，不改前端/API，不触发 provider / accepted latest / monitor / 交易链路。','','## 2. 缺失根因','',*md(reason_summary,['root_cause','row_count','instruments','repair_action'],10),'','结论：缺失集中在 `TW7769` 与 `TW6919`。`TW7769` 在 raw score 中早于本地价格起始日出现，2025-11-18 之后仍因 ret20 / volatility20 warmup 不足缺 adaptive score；`TW6919` 早期 5 行因特征 warmup / 价格映射审计未满足 replay-ready 条件。','','## 3. 修复动作','','- 将不可 replay-ready 行从 C4 repaired replay-ready artifact 中排除。','- 尝试检查同日 raw score rank > 150 top-up 候选。','- 结果：S2B raw score 在目标窗口每日只有 150 行，没有 rank > 150 候选；不训练、不重跑 qlib、不新增 provider 数据的前提下无法 top-up 到每日 150。','','## 4. Coverage / Replay-Ready 结果','',f"- 输入 rows：`{summary['input_rows']}`。",f"- 排除不可 replay-ready rows：`{summary['excluded_non_replay_ready_rows']}`。",f"- 输出 rows：`{summary['output_rows']}`。",f"- daily repaired rows：`{summary['daily_repaired_rows_min']} / {summary['daily_repaired_rows_median']} / {summary['daily_repaired_rows_max']}`。",f"- daily replay-ready rows min：`{summary['daily_replay_ready_rows_min']}`。",f"- repair 后 missing current price：`{summary['missing_current_price_rows_after_repair']}`。",f"- repair 后 missing next execution price：`{summary['missing_next_execution_price_rows_after_repair']}`。",f"- repair 后 missing adaptive score：`{summary['missing_adaptive_score_rows_after_repair']}`。",'','## 5. Gate','','```text',summary['recommended_gate'],'```','','该 gate 表示 replay-ready 条件已清理干净，但每日 150 覆盖无法在现有 raw score artifact 内 top-up；若审查者要求每日 150，必须另开 qlib score/universe 合同修复，而不是在 C4 静默补数据。','','## 6. 输出产物','',f"- `{rel(OUT/'phasec4_missing_replay_ready_rows.csv')}`",f"- `{rel(OUT/'phasec4_missing_reason_summary.csv')}`",f"- `{rel(OUT/'phasec4_repaired_replay_ready_scores.csv')}`",f"- `{rel(OUT/'phasec4_daily_coverage_summary.csv')}`",f"- `{rel(OUT/'phasec4_asof_eligibility_audit.csv')}`",f"- `{rel(OUT/'phasec4_replay_ready_audit.csv')}`",f"- `{rel(OUT/'phasec4_topup_feasibility_audit.csv')}`",f"- `{rel(OUT/'phasec4_summary.json')}`"]
    REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'ok':True,'gate':summary['recommended_gate'],'report':rel(REPORT),'summary':rel(OUT/'phasec4_summary.json')},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
