---
created_at: 2026-06-23
status: work_order_for_rcp1a_diagnostic_signal_adapter_contract
phase: RCP1A_DIAGNOSTIC_SIGNAL_ADAPTER_CONTRACT
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RCP_RISK_CONTROL_POLICY_2022_DOWNTURN_MAINLINE_CN.md
coordinator_decision: docs/tw_portfolio_decision_model/POLICY_RCP0_COORDINATOR_DECISION_ACCEPT_2022_DIAGNOSTIC_CN.md
rcp0_execution_report: docs/tw_portfolio_decision_model/POLICY_RCP0_2015_2020_QLIB_ARTIFACT_DISCOVERY_EXECUTION_REPORT_CN.md
rcp0_review: docs/tw_portfolio_decision_model/POLICY_RCP0_2015_2020_QLIB_ARTIFACT_DISCOVERY_REVIEW_CN.md
input_signal: data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/WF-VAL.csv
input_manifest: data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/WF-VAL.manifest.json
output_root: data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract
execution_report: docs/tw_portfolio_decision_model/POLICY_RCP1A_DIAGNOSTIC_SIGNAL_ADAPTER_CONTRACT_EXECUTION_REPORT_CN.md
review_report: docs/tw_portfolio_decision_model/POLICY_RCP1A_DIAGNOSTIC_SIGNAL_ADAPTER_CONTRACT_REVIEW_CN.md
baseline_replay_authorized: false
risk_control_replay_authorized: false
strict_test_authorized: false
model_training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_weight: true
not_target_position: true
not_quantity_instruction: true
---

# RCP1A Diagnostic Signal Adapter / Contract 工作文档

## 1. 本轮定位

本轮执行：

```text
RCP1A: Diagnostic Signal Adapter / Contract
```

目标是把 RCP0 选中的候选：

```text
C03_S1B1_WF_VAL_2021_2022
```

合同化为后续 RCP1B baseline replay 可以读取的只读诊断信号输入。

本轮只做：

```text
schema mapping
diagnostic-only manifest
coverage and field validation
lineage and forbidden consumer audit
```

本轮不做：

```text
baseline replay
risk-control replay
规则设计
阈值选择
模型训练
strict_test
生产/default/provider/frontend/Agent/订单链路集成
```

## 2. 必须读取

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RCP0_COORDINATOR_DECISION_ACCEPT_2022_DIAGNOSTIC_CN.md
docs/tw_portfolio_decision_model/POLICY_RCP1A_DIAGNOSTIC_SIGNAL_ADAPTER_CONTRACT_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RCP0_2015_2020_QLIB_ARTIFACT_DISCOVERY_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RCP0_2015_2020_QLIB_ARTIFACT_DISCOVERY_REVIEW_CN.md
data_tw/experiments/risk_control_policy_2022/rcp0_artifact_discovery/selected_signal_artifact_contract.json
data_tw/experiments/risk_control_policy_2022/rcp0_artifact_discovery/field_availability_audit.csv
data_tw/experiments/risk_control_policy_2022/rcp0_artifact_discovery/oos_window_audit.csv
```

必须参考合同：

```text
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
```

## 3. 输入

输入信号：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/WF-VAL.csv
```

输入 manifest：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/WF-VAL.manifest.json
```

输入语义：

```text
qlib train = 2015-05-04..2020-12-31
signal window = 2021-01-01..2022-12-31
2022 semantic = downturn_validation_diagnostic_only
strict_oos_2022 = false
```

## 4. 输出目录

所有产物写入：

```text
data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/
```

执行报告写入：

```text
docs/tw_portfolio_decision_model/POLICY_RCP1A_DIAGNOSTIC_SIGNAL_ADAPTER_CONTRACT_EXECUTION_REPORT_CN.md
```

## 5. 必须输出文件

必须输出：

```text
manifest.json
diagnostic_signal_adapter_manifest.json
diagnostic_model_signal.csv
schema_mapping.csv
coverage_validation.csv
rank_score_validation.csv
lineage_audit.json
diagnostic_semantics_audit.json
forbidden_consumer_audit.csv
validator_report.json
diagnostic_findings.md
```

## 6. diagnostic_model_signal.csv 合同

`diagnostic_model_signal.csv` 必须至少包含：

```text
date
signal_date
instrument
model_id
model_family
signal_type
rank
score
raw_score
source_rank
source_score
source_artifact
train_start
train_end
valid_start
valid_end
strict_oos
diagnostic_only
semantic_label
```

字段映射：

```text
date = source.date
signal_date = source.date
instrument = source.instrument
rank = source.qlib_rank
score = source.qlib_score_raw
raw_score = source.qlib_score_raw
source_rank = source.qlib_rank
source_score = source.qlib_score_raw
model_id = rcp_qllib_20150504_20201231_wf_val_2021_2022_diagnostic
model_family = qlib_lightgbm_alpha158
signal_type = qlib_score_rank
strict_oos = false
diagnostic_only = true
semantic_label = downturn_validation_diagnostic_only
```

不得包含：

```text
target_weight
target_position
quantity_instruction
OrderIntent
broker_order_id
trade_instruction
```

## 7. Validation 要求

`coverage_validation.csv` 至少按年份输出：

```text
year
min_date
max_date
trading_days
rows
avg_symbols_per_day
min_symbols_per_day
max_symbols_per_day
coverage_status
notes
```

`rank_score_validation.csv` 至少检查：

```text
date
row_count
unique_instruments
rank_min
rank_max
rank_duplicate_count
score_missing_count
score_constant_status
validation_status
notes
```

如果存在同日 rank duplicate，必须说明是否阻塞 RCP1B。

## 8. diagnostic_semantics_audit.json

必须明确：

```text
strict_oos_2022: false
diagnostic_only: true
allowed_language:
  - 2022 downturn validation diagnostic
  - non-train downturn diagnostic
forbidden_language:
  - strict OOS
  - final OOS
  - independent test
threshold_mining_on_2022_allowed: false
baseline_replay_allowed_after_pass: true
risk_control_replay_allowed_after_pass: false
```

## 9. validator_report.json

必须包含：

```text
phase
status
pass
input_exists
output_exists
schema_status
coverage_status
rank_score_status
lineage_status
diagnostic_semantics_status
forbidden_actions_status
rcp1b_authorizable
recommended_next_step
```

允许的 `recommended_next_step`：

```text
PASS_READY_FOR_RCP1B_DIAGNOSTIC_BASELINE_REPLAY_AUDIT_WORK_DOC
FAIL_NEEDS_RCP1A_REPAIR
STOP_INPUT_SIGNAL_INVALID
```

## 10. 审查 gate

RCP1A 通过条件：

```text
1. diagnostic_model_signal.csv 生成且可读；
2. schema mapping 明确；
3. 2021/2022 coverage 与 RCP0 一致；
4. rank/score 可用于 baseline replay；
5. semantic 明确标记 diagnostic-only；
6. 未触碰 forbidden actions；
7. validator_report 推荐进入 RCP1B。
```

审查者 verdict 只能为：

```text
PASS_READY_FOR_RCP1B_DIAGNOSTIC_BASELINE_REPLAY_AUDIT_WORK_DOC
FAIL_NEEDS_RCP1A_REPAIR
STOP_INPUT_SIGNAL_INVALID
```

## 11. 第一执行者指令

```text
请按 docs/tw_portfolio_decision_model/POLICY_RCP1A_DIAGNOSTIC_SIGNAL_ADAPTER_CONTRACT_WORK_CN.md 执行 RCP1A。
只做 diagnostic signal adapter / contract / validation，不跑 baseline replay，不跑 risk-control replay，不训练，不 strict_test，不改 registry/default/provider/frontend/Agent/订单链路。
完成后输出 data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/ 下全部必需文件，并提交执行报告。
```

## 12. 第一审查者指令

```text
请按 docs/tw_portfolio_decision_model/POLICY_RCP1A_DIAGNOSTIC_SIGNAL_ADAPTER_CONTRACT_WORK_CN.md 审查 RCP1A 产物。
重点审查 schema、coverage、rank/score、lineage、diagnostic-only 语义、禁止事项与 validator_report。
通过后只授权写 RCP1B diagnostic baseline replay audit 工作文档，不授权 risk-control replay。
```
