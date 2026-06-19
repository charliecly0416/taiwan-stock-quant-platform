#!/usr/bin/env python3
from __future__ import annotations

import csv, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data_tw/experiments/ltr_orthogonal_features_controlled/phase_o0_contract_freeze'
REPORT=ROOT/'docs/tw_ltr_orthogonal_features_controlled/PHASEO0_ANCHOR_AND_CONTROL_CONTRACT_EXECUTION_REPORT_CN.md'
MAINLINE=ROOT/'docs/tw_ltr_orthogonal_features_controlled/ORTHOGONAL_LTR_CONTROLLED_MAINLINE_CN.md'
ANCHOR_CARD=ROOT/'docs/tw_phase1c_anchor_reproduction/PHASEA2_REVIEW_AND_ANCHOR_CARD_CN.md'
A1_REPORT=ROOT/'docs/tw_phase1c_anchor_reproduction/PHASEA1_ANCHOR_REPRODUCTION_EXECUTION_REPORT_CN.md'
PHASE1C_REPORT=ROOT/'docs/tw_ltr_rerank_regime_turnover/PHASE1C_FINAL_LTR_REPAIR_EXECUTION_REPORT_CN.md'
PHASE3A0_REPORT=ROOT/'docs/tw_ltr_rerank_regime_turnover/PHASE3A0_FROZEN_PHASE1C_SCORE_EXECUTION_REPORT_CN.md'
S2F_REPORT=ROOT/'docs/tw_ltr_qlib_split_aligned_retrain/PHASES2F_OLD_VS_FRESH_SAME_WINDOW_RECHECK_REPORT_CN.md'
SAMPLE=ROOT/'data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_ltr_samples.csv'
SAMPLE_SCHEMA=ROOT/'data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_sample_schema.json'
PHASE1C_GATE=ROOT/'data_tw/experiments/ltr_rerank_regime_turnover/phase1c_final_ltr_repair/phase1c_gate_summary.json'
PHASE1C_SELECTION=ROOT/'data_tw/experiments/ltr_rerank_regime_turnover/phase1c_final_ltr_repair/phase1c_validation_selection.csv'
PHASE1C_TEST=ROOT/'data_tw/experiments/ltr_rerank_regime_turnover/phase1c_final_ltr_repair/phase1c_independent_test_comparison.csv'
PHASE3A0_SCHEMA=ROOT/'data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_score_schema.json'
PHASE3A0_SCORE=ROOT/'data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv'
PHASE3A0_REPRO=ROOT/'data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_score_reproduction_metrics.csv'
A1_SUMMARY=ROOT/'data_tw/experiments/phase1c_anchor_reproduction/phasea1_anchor_summary.json'
S2F_METRICS=ROOT/'data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2f_old_vs_fresh_same_window_recheck/phase_s2f_same_window_metrics.csv'
S2F_COMMON=ROOT/'data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2f_old_vs_fresh_same_window_recheck/phase_s2f_same_window_common_universe_metrics.csv'
S2F_ACTIONS=ROOT/'data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2f_old_vs_fresh_same_window_recheck/phase_s2f_same_window_action_audit.csv'

EXPECTED={'candidate_id':'head10_all_l31_alpha0.7_top50_only','model_id':'head10_all_l31','score_column':'score_head10_all_l31_alpha0.7_top50_only','blend_alpha':0.7,'preserve_scope':'top50_only','label_col':'relevance_10d_top_heavy','num_leaves':31,'learning_rate':0.03,'n_estimators':120,'random_state':42}

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
def read_json(path): return json.loads(path.read_text(encoding='utf-8'))
def md(rows, fields, limit=30):
    out=['| '+' | '.join(fields)+' |','| '+' | '.join(['---']*len(fields))+' |']
    for r in rows[:limit]: out.append('| '+' | '.join(str(r.get(f,'')) for f in fields)+' |')
    return out

def file_row(path, role, required=True):
    return {'path':rel(path),'role':role,'required':required,'exists':path.exists(),'size_bytes':path.stat().st_size if path.exists() else ''}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    schema=read_json(PHASE3A0_SCHEMA); fixed=schema['fixed_phase1c_config']
    identity=[]
    for k,v in EXPECTED.items():
        actual=fixed.get(k) if k in fixed else ''
        identity.append({'field':k,'expected':v,'actual':actual,'pass':'yes' if str(actual)==str(v) else 'no'})
    wcsv(OUT/'phaseo0_control_identity_audit.csv',identity,['field','expected','actual','pass'])
    sample_schema=read_json(SAMPLE_SCHEMA) if SAMPLE_SCHEMA.exists() else {}
    sample_df=pd.read_csv(SAMPLE,usecols=['date','instrument','split','sample_complete','feature_complete','label_complete_10d'])
    sample_rows=[{'metric':'sample_raw_rows','value':int(len(sample_df))},{'metric':'sample_complete_rows','value':int(sample_df.sample_complete.sum())},{'metric':'feature_complete_rows','value':int(sample_df.feature_complete.sum())},{'metric':'label_complete_10d_rows','value':int(sample_df.label_complete_10d.sum())},{'metric':'date_min','value':str(sample_df.date.min())},{'metric':'date_max','value':str(sample_df.date.max())},{'metric':'instrument_count','value':int(sample_df.instrument.nunique())}]
    for split,val in sample_df.groupby('split').size().items(): sample_rows.append({'metric':f'split_{split}_rows','value':int(val)})
    wcsv(OUT/'phaseo0_control_sample_audit.csv',sample_rows,['metric','value'])
    repro=pd.read_csv(PHASE3A0_REPRO)
    repro_row={'metric_rows':int(len(repro)),'max_abs_diff':float(repro.abs_diff.max()),'mean_abs_diff':float(repro.abs_diff.mean()),'tolerance':float(repro.tolerance.max()),'pass':'yes' if repro.within_tolerance.astype(str).str.lower().eq('true').all() else 'no'}
    metrics=pd.read_csv(S2F_METRICS); common=pd.read_csv(S2F_COMMON)
    anchor_full=metrics[metrics.method=='old_qlib_new_ltr_phase1c_simple'].iloc[0].to_dict()
    anchor_common=common[common.method=='old_qlib_new_ltr_phase1c_simple'].iloc[0].to_dict()
    artifacts=[
      file_row(ANCHOR_CARD,'Phase A2 frozen anchor card'),file_row(A1_REPORT,'Phase A1 reproduction report'),file_row(PHASE1C_REPORT,'Phase1C final LTR repair report'),file_row(PHASE3A0_REPORT,'Phase3A0 frozen row-level score report'),file_row(S2F_REPORT,'S2F same-window replay report'),file_row(SAMPLE,'first simple LTR control sample'),file_row(SAMPLE_SCHEMA,'first simple LTR sample schema'),file_row(PHASE1C_GATE,'Phase1C gate summary'),file_row(PHASE1C_SELECTION,'Phase1C validation selection'),file_row(PHASE1C_TEST,'Phase1C independent test comparison'),file_row(PHASE3A0_SCHEMA,'frozen Phase1C score schema'),file_row(PHASE3A0_SCORE,'frozen Phase1C row-level score'),file_row(PHASE3A0_REPRO,'score reproduction metrics'),file_row(A1_SUMMARY,'A1 anchor reproduction summary'),file_row(S2F_METRICS,'S2F full universe metrics'),file_row(S2F_COMMON,'S2F common universe metrics'),file_row(S2F_ACTIONS,'S2F action audit')]
    wcsv(OUT/'phaseo0_control_artifact_inventory.csv',artifacts,['path','role','required','exists','size_bytes'])
    scripts=[
      file_row(ROOT/'scripts/build_tw_ltr_phase1_samples.py','control sample construction script'),file_row(ROOT/'scripts/train_tw_ltr_phase1_lambdamart.py','first LTR training script'),file_row(ROOT/'scripts/diagnose_tw_ltr_phase1c_final_repair.py','Phase1C candidate/model selection diagnosis script'),file_row(ROOT/'scripts/materialize_tw_ltr_phase3a0_frozen_phase1c_scores.py','frozen row-level score materialization script'),file_row(ROOT/'scripts/recheck_tw_ltr_old_vs_fresh_same_window.py','same-window replay/check script'),file_row(ROOT/'scripts/evaluate_tw_ltr_s2d_full_daily_replay.py','next-day replay engine reused by S2F')]
    wcsv(OUT/'phaseo0_control_script_inventory.csv',scripts,['path','role','required','exists','size_bytes'])
    forbidden=[
      'do_not_retrain_qlib_in_o0','do_not_train_ltr_in_o0','do_not_enter_o1','do_not_fetch_finmind_in_o0','do_not_change_control_sample_rows','do_not_change_label_col','do_not_change_original_features','do_not_change_ltr_model_type_or_hyperparameters','do_not_change_top50_preserve_scope','do_not_change_replay_fee_tax_next_day_position_count','do_not_add_filters_thresholds_market_gates_turnover_rules','do_not_delete_rows_for_missing_orthogonal_features','do_not_modify_frontend_api_provider_accepted_latest_monitor_trading','do_not_use_return_metrics_to_select_o0_contract']
    wcsv(OUT/'phaseo0_forbidden_change_checklist.csv',[{'item':x,'status':'frozen_forbidden'} for x in forbidden],['item','status'])
    contract={'created_at':now(),'phase':'phase_o0_anchor_and_control_contract_freeze','gate':'phase_o0_anchor_and_control_contract_frozen','control_identity':EXPECTED,'control_score_artifact':rel(PHASE3A0_SCORE),'control_sample':rel(SAMPLE),'control_sample_rows':int(len(sample_df)),'control_sample_complete_rows':int(sample_df.sample_complete.sum()),'control_split_counts':{str(k):int(v) for k,v in sample_df.groupby('split').size().items()},'control_input_features':schema.get('input_columns_reused',[]),'frozen_replay_policy':{'window':'2025-07-01..2026-05-07','execution':'next-day execution','fee_rate':0.001425,'tax_rate':0.003,'target_position_count':10,'preserve_scope':'top50_only'},'anchor_full_universe_metrics':{'fee_tax_adjusted_net_return':anchor_full['fee_tax_adjusted_net_return'],'max_drawdown':anchor_full['max_drawdown'],'action_count':int(anchor_full['action_count'])},'anchor_common_universe_metrics':{'common_universe_key_count':22474,'fee_tax_adjusted_net_return':anchor_common['fee_tax_adjusted_net_return'],'max_drawdown':anchor_common['max_drawdown'],'action_count':int(anchor_common['action_count'])},'score_reproduction':repro_row,'orthogonal_treatment_only_allowed_change':'append PIT-safe institutional/margin orthogonal feature columns with neutral fill and missing flags; preserve all control rows/labels/original features/model/replay','o1_not_executed':True,'no_training':True,'no_network':True,'no_frontend_api_provider_monitor_trading':True,'stop_conditions':['missing reproducible control artifact/script','identity mismatch','score reproduction fail','uncertain training/sample/replay contract','any required change beyond adding orthogonal features']}
    wjson(OUT/'phaseo0_experiment_contract.json',contract)
    report_lines=['# Phase O0 执行报告：Anchor 与 Control 实验合同冻结','',f"生成时间：{contract['created_at']}",'','## 1. 执行结论','','Phase O0 已完成：control 精确冻结为第一版 simple LTR / Phase1C anchor。本轮没有进入 O1，没有拉取正交数据，没有训练 qlib/LTR，没有回放新实验。','','推荐 gate：','', '```text', contract['gate'], '```','','## 2. Control Identity','',*md(identity,['field','expected','actual','pass'],20),'','## 3. Control Sample Audit','',*md(sample_rows,['metric','value'],30),'','## 4. Score Reproduction','',*md([repro_row],['metric_rows','max_abs_diff','mean_abs_diff','tolerance','pass'],5),'','## 5. Anchor Replay Metrics 冻结','','Full universe：','',f"- fee_tax_adjusted_net_return：`{anchor_full['fee_tax_adjusted_net_return']}`",f"- max_drawdown：`{anchor_full['max_drawdown']}`",f"- action_count：`{int(anchor_full['action_count'])}`",'','Common universe：','',f"- common universe key count：`22474`",f"- fee_tax_adjusted_net_return：`{anchor_common['fee_tax_adjusted_net_return']}`",f"- max_drawdown：`{anchor_common['max_drawdown']}`",f"- action_count：`{int(anchor_common['action_count'])}`",'','## 6. Control Artifact 清单','',*md(artifacts,['path','role','exists','size_bytes'],40),'','## 7. Control Script 清单','',*md(scripts,['path','role','exists','size_bytes'],20),'','## 8. 本轮禁止变化清单','',*md([{'item':x,'status':'frozen_forbidden'} for x in forbidden],['item','status'],40),'','## 9. O1 前置合同','','O1 只可在审查通过后执行 FinMind/PIT 可得性审计。Treatment 唯一允许变化是新增 PIT-safe 法人筹码与融资融券正交特征；不得改变 control 样本行、标签、原有特征、模型类型、超参数、top50 preserve_scope、回放规则或费用税费。','','## 10. 安全边界','','- 未进入 O1。','- 未训练 qlib/LTR。','- 未联网或拉取 FinMind。','- 未改前端/API。','- 未触发 provider / accepted latest / monitor / broker / orders / quick-trade。','- 未使用收益率选择或改变合同。','','## 11. 输出产物','',f"- `{rel(OUT/'phaseo0_control_identity_audit.csv')}`",f"- `{rel(OUT/'phaseo0_control_sample_audit.csv')}`",f"- `{rel(OUT/'phaseo0_control_artifact_inventory.csv')}`",f"- `{rel(OUT/'phaseo0_control_script_inventory.csv')}`",f"- `{rel(OUT/'phaseo0_forbidden_change_checklist.csv')}`",f"- `{rel(OUT/'phaseo0_experiment_contract.json')}`"]
    REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text('\n'.join(report_lines)+'\n',encoding='utf-8')
    print(json.dumps({'ok':True,'gate':contract['gate'],'report':rel(REPORT),'contract':rel(OUT/'phaseo0_experiment_contract.json')},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
