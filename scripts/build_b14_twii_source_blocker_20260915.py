#!/usr/bin/env python3
"""Readonly TWII schema/publication blocker audit for 2026-09-15."""
from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data_tw/experiments/project_runtime_convergence/modelb_b14_twii_source_blocker_20260915'; OUT.mkdir(parents=True,exist_ok=True)
DECISION_CUTOFF='2026-09-15T14:57:29+00:00'
EXISTING=ROOT/'data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260915_20260915T103002Z/same_run_handoff_artifacts/daily_price'

def sha(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
 return h.hexdigest()
def probe(name,url,params):
 started=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z'); rec={'name':name,'url':url,'params':params,'started_at':started}
 try:
  r=requests.get(url,params=params,timeout=20); raw=OUT/f'{name}.raw'; raw.write_bytes(r.content); ended=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z'); rec.update({'http_status':r.status_code,'response_bytes':len(r.content),'response_sha256':sha(raw),'ended_at':ended,'headers':{k.lower():v for k,v in r.headers.items()},'fetch_after_cutoff':ended>DECISION_CUTOFF})
  try: payload=r.json(); rec['json_shape']='list' if isinstance(payload,list) else sorted(payload.keys()) if isinstance(payload,dict) else type(payload).__name__; rec['returned_dates']=sorted({str(x.get('date') or x.get('日期') or '')[:10] for x in (payload if isinstance(payload,list) else payload.get('data',[]) if isinstance(payload,dict) else []) if isinstance(x,dict)})
  except Exception as e: rec['json_error']=type(e).__name__
  rec['status']='PROBE_CAPTURED'
 except Exception as e: rec.update({'ended_at':datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z'),'status':'REQUEST_FAILED','error':type(e).__name__+': '+str(e)})
 return rec
def main():
 existing=json.loads((EXISTING/'twii.adapter_output.json').read_text()); existing_gaps={'schema_errors':existing.get('schema_errors'),'scope_status':existing.get('scope_status'),'validator_status':existing.get('validator_status'),'target_asof':existing.get('target_asof'),'trade_date':existing.get('trade_date'),'returned_scope':existing.get('returned_scope'),'unknown_scope':existing.get('unknown_scope'),'source_published_at':existing.get('source_published_at'),'available_at':existing.get('available_at'),'fetched_at':existing.get('fetched_at'),'expected_scope':existing.get('expected_scope'),'raw_sha256':sha(EXISTING/'twii.http.raw'),'normalized_sha256':sha(EXISTING/'twii.normalized.json')}
 probes=[probe('twse_openapi','https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX',{'date':'20260915','response':'json'}),probe('twse_public','https://www.twse.com.tw/exchangeReport/MI_INDEX',{'response':'json','date':'20260915','type':'ALLBUT0999'}),probe('finmind_taiex','https://api.finmindtrade.com/api/v4/data',{'dataset':'TaiwanStockPrice','data_id':'TAIEX','start_date':'2026-09-15','end_date':'2026-09-15'})]
 for rec in probes:
  raw=OUT/f"{rec['name']}.raw"; rec['raw_path']=str(raw.relative_to(ROOT)) if raw.exists() else None
 # A candidate normalized record is emitted only for schema inspection; it is not HSA8-bound.
 candidates=[]
 for rec in probes:
  if rec.get('status')!='PROBE_CAPTURED': continue
  raw=OUT/f"{rec['name']}.raw"
  try:
   payload=json.loads(raw.read_text())
   if rec['name']=='finmind_taiex':
    for x in payload.get('data',[]): candidates.append({'source':'finmind_taiex','instrument':x.get('stock_id'),'trade_date':x.get('date'),'close':x.get('close'),'schema_complete':all(k in x for k in ('date','stock_id','close')),'publication_proven':False,'available_at_proven':False})
   elif rec['name']=='twse_public':
    candidates.append({'source':'twse_public','instrument':'TWII','trade_date':'2026-09-15','close':None,'schema_complete':False,'publication_proven':False,'available_at_proven':False,'schema_note':'HTML/table response needs explicit field mapping and source-native publication timestamp'})
  except Exception: pass
 (OUT/'TWII_CANDIDATE_NORMALIZED.json').write_text(json.dumps(candidates,ensure_ascii=False,indent=2)+'\n')
 result={'schema_version':'modelb.b14.twii_source_blocker.v1','run_id':'modelb_b14_twii_source_blocker_20260915','created_at':datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z'),'status':'BLOCKED_PROVIDER_SCHEMA_AND_PUBLICATION_AVAILABILITY_UNPROVEN','decision_cutoff':DECISION_CUTOFF,'existing_adapter':existing_gaps,'official_probes':probes,'candidate_normalized_path':str((OUT/'TWII_CANDIDATE_NORMALIZED.json').relative_to(ROOT)),'field_gaps':['OpenAPI payload date is 1150914/2026-09-14 while target_asof is 2026-09-15','returned_scope=[] and unknown_scope=[TWII]','trade_date missing in adapter output','source_published_at is null','source-native publication/availability timestamp not supplied','fresh probes fetched after decision cutoff, so available_at<=cutoff cannot be proven','TWSE public table and FinMind schemas are not the bound adapter schema'],'strict_handoff_allowed':False,'training_performed':False,'scoring_performed':False,'replay_performed':False,'production_allowed':False,'baseline_admission':False,'no_fallback_or_calendar_cache_stdout':True}
 (OUT/'B14_MANIFEST.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n'); (OUT/'B14_EXECUTION_REPORT_CN.md').write_text('''# B14 TWII source blocker 研究\n\n当前真实 adapter 的 `BLOCKED_PROVIDER_SCHEMA` 来自：目标是 2026-09-15，但 TWSE OpenAPI 响应只有 `1150914`（2026-09-14）；因此 `trade_date` 为空、`returned_scope=[]`、`unknown_scope=[TWII]`。\n\n即使使用网页端点或 FinMind TAIEX 得到 2026-09-15 数值，本轮抓取发生在 14:57:29 决策截止之后，且没有 source-native `source_published_at`/`available_at` 证据，不能证明数据在决策时已经可用。网页端点还需要额外 schema 映射，不能直接冒充现有 HSA8 adapter。\n\n结论：checksum 修复不改变 TWII 的 schema/PIT blocker。未使用旧 calendar、cache、stdout 或 fallback；未训练、未评分、未生成 Model B signal，未写 production/latest/default/baseline。\n'''); checks={'existing_schema_blocked':existing_gaps['validator_status']=='BLOCKED_PROVIDER_SCHEMA','openapi_date_mismatch':'1150914' in probes[0].get('returned_dates',[]),'fresh_finmind_after_cutoff':any(p['name']=='finmind_taiex' and p.get('fetch_after_cutoff') for p in probes),'strict_handoff_false':result['strict_handoff_allowed'] is False,'no_training':result['training_performed'] is False}; (OUT/'B14_VALIDATOR.json').write_text(json.dumps({'schema_version':'modelb.b14.validator.v1','checks':checks,'verdict':'PASS' if all(checks.values()) else 'FAIL'},ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'status':result['status'],'probes':[(p['name'],p['status'],p.get('http_status'),p.get('returned_dates')) for p in probes]}))
if __name__=='__main__': main()
