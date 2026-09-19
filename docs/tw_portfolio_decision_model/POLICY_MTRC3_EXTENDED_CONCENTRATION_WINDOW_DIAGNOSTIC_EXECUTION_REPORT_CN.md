# POLICY_MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_EXECUTION_REPORT_CN

生成时间：2026-06-28T17:05:02+00:00

## 1. Scope

本阶段只基于 MTRC2_U 已审查通过的 ReplayResultArtifact 生成 research-only extended concentration / window / mark-quality diagnostic。

未训练模型，未 inference，未重算 LTR，未生成或修改 ModelSignal / OrderIntent / ReplayResult / ledger，未调参，未新增候选，未写 provider/latest/default/frontend/API/Agent/daily/production，未 broker/order，未生成 target_weight / target_position / quantity instruction。

## 2. Inputs

- MTRC2_U ReplayResult manifest：`data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_u_same_signal_readonly_replay_build/manifest.json`
- MTRC2_U summary/actions/daily_nav/position_snapshots/skipped/audits/validator
- 父审查：`docs/tw_portfolio_decision_model/POLICY_MTRC2_U_SAME_SIGNAL_READONLY_REPLAY_BUILD_REVIEW_CN.md`

未读取旧 MTR2_R/E3 replay 作为输入。

## 3. Outputs

输出目录：`data_tw/experiments/policy_mtr_research_only_continuation/mtrc3_extended_concentration_window_diagnostic/`

生成文件：

```text
manifest.json
summary_diagnostic.csv
window_return_diagnostic.csv
monthly_return_diagnostic.csv
rolling_return_diagnostic.csv
drawdown_diagnostic.csv
symbol_concentration_diagnostic.csv
event_concentration_diagnostic.csv
action_contribution_diagnostic.csv
mark_quality_diagnostic.csv
mark_fallback_by_symbol.csv
mark_fallback_by_month.csv
skipped_action_diagnostic.csv
turnover_cost_diagnostic.csv
lineage_audit.csv
forbidden_scope_audit.csv
validator_report.json
diagnostic_findings.md
```

## 4. Core Metrics

```text
verdict = PASS_WITH_MARK_QUALITY_WARNINGS_READY_FOR_MTRC4
final_equity = 2012130218.262249
total_return = 2011.1302182622
max_drawdown = -0.1990237415
positive_month_ratio = 0.8288288288
negative_months = 2018-06;2018-11;2019-05;2020-03;2020-08;2022-03;2022-04;2022-05;2022-07;2022-10;2022-11;2025-03;2025-04;2025-11;2026-05
rolling_20d_worst_return = -0.1981832385
rolling_40d_worst_return = -0.1852667883
top1_symbol_share = 0.0732851362 (pass)
top3_symbol_share = 0.1641435559 (pass)
top5_symbol_share = 0.2372999665
top1_event_share = 0.0342442911 (pass)
top5_event_share = 0.1246568213
fallback_ratio = 0.8996056241 (fail_research_only)
final_date_fallback_ratio = 0.9 (fail_research_only)
max_mark_lag_days = 469 (fail_research_only)
mean_mark_lag_days = 31.8752572016
skipped_action_count = 46
missing_price_count = 10493
```

## 5. Validator

```text
blocking_reasons = []
required_output_files_present = True
required_output_fields_present = True
input_replay_artifact_equals_mtrc2_u = True
mtrc2_u_review_passed = True
old_mtr2r_or_e3_not_used_as_input = True
no_model_training_or_inference = True
no_order_intent_or_replay_write = True
no_broker_order_target_weight_target_position = True
diagnostic_only_true = True
production_allowed_false = True
```

## 6. Interpretation

MTRC3 不能计算 baseline delta，所有收益都是 same-signal replay absolute diagnostic。

本次诊断完整生成，但 mark-quality / concentration 存在研究限制，因此若 verdict 为 `PASS_WITH_MARK_QUALITY_WARNINGS_READY_FOR_MTRC4`，含义是可以进入 MTRC4 closure decision，而不是可以进入 production readiness。

## 7. Verification

```text
python -m py_compile scripts/build_tw_policy_mtrc3_extended_concentration_window_diagnostic.py
python scripts/build_tw_policy_mtrc3_extended_concentration_window_diagnostic.py
```
