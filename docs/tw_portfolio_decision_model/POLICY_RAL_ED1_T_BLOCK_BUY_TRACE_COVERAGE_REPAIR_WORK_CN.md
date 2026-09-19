---
created_at: 2026-06-23
status: work_order_for_ral_ed1_t_block_buy_trace_coverage_repair
phase: RAL_ED1_T_BLOCK_BUY_TRACE_COVERAGE_REPAIR
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
coordinator_opinion: docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
prior_review: docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S_BLOCK_BUY_COUNTERFACTUAL_ATTRIBUTION_RERUN_REVIEW_CN.md
prior_execution_report: docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S_BLOCK_BUY_COUNTERFACTUAL_ATTRIBUTION_RERUN_EXECUTION_REPORT_CN.md
source_trace_root: data_tw/experiments/explicit_rule_discovery/ral_ed1_r_counterfactual_trace_repair
prior_attribution_root: data_tw/experiments/explicit_rule_discovery/ral_ed1_s_block_buy_counterfactual_attribution
output_root: data_tw/experiments/explicit_rule_discovery/ral_ed1_t_block_buy_trace_coverage_repair
ral_ed1_s2_authorized: false
ral_ed2_authorized: false
rule_replay_authorized: false
rule_selection_authorized: false
threshold_selection_authorized: false
strict_test_authorized: false
model_training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_weight: true
not_target_position: true
not_quantity: true
---

# RAL-ED1-T Block-buy Trace Coverage Repair 工作文档

## 1. 本轮定位

本轮执行统筹授权的：

```text
RAL-ED1-T: Block-buy Trace Coverage Repair
```

本轮只补齐 `block_buy_trace_probe_v1` 的 counterfactual trace 覆盖，使其覆盖：

```text
rule diagnostic train = 2023-01-01..2024-12-31
rule validation = 2025-01-01..2025-12-31
```

本轮不是：

```text
ED1-S2 attribution rerun
RAL-ED2 rule sanity
规则收益 replay
规则选择 / threshold selection
strict_test
模型训练
生产集成
```

## 2. 背景与 Gate

ED1-S 审查结论为：

```text
STOP_BLOCK_BUY_TRACE_COVERAGE_INSUFFICIENT
```

阻断原因：

```text
source_trace_rows = 120
train_rows = 120
validation_rows = 0
```

统筹判断：当前不是 block-buy 方向被证伪，而是 validation trace 覆盖不足。因此本轮只补 trace 覆盖，不做归因 rerun。

## 3. 必须读取

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S_BLOCK_BUY_COUNTERFACTUAL_ATTRIBUTION_RERUN_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S_BLOCK_BUY_COUNTERFACTUAL_ATTRIBUTION_RERUN_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_R_COUNTERFACTUAL_TRACE_FEASIBILITY_REPAIR_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_R_COUNTERFACTUAL_TRACE_FEASIBILITY_REPAIR_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_T_BLOCK_BUY_TRACE_COVERAGE_REPAIR_WORK_CN.md
```

必须读取：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed1_r_counterfactual_trace_repair/*
data_tw/experiments/explicit_rule_discovery/ral_ed1_s_block_buy_counterfactual_attribution/*
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/action_trace_ledger_schema.json
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/trace_status_policy.md
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/validator_design.md
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/golden_sample_design.md
```

必须参考项目边界合同：

```text
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
```

## 4. 允许范围

允许：

```text
1. 重新生成或扩展 block_buy_trace_probe_v1 的 local counterfactual traces。
2. 读取 repaired baseline ledger 和 frozen qlib signal。
3. 覆盖 2023-2024 diagnostic train 与 2025 validation。
4. 生成 action_trace_id / baseline_counterfactual_trace_id。
5. 生成 local action-level delta_pnl_after_fee_tax_diagnostic。
6. 生成 fee_tax_delta_diagnostic 与 turnover_delta_diagnostic。
7. 生成 coverage、determinism、cost/turnover、trace_status、forbidden audit。
```

生成的 trace 必须保留：

```text
probe_id = block_buy_trace_probe_v1
trace_status = counterfactual_replay_trace
trace_quality = counterfactual_replay_trace_local_action_delta_not_full_portfolio_path
diagnostic_probe_only = true
not_rule_candidate = true
not_selected_by_validation = true
local_action_delta_only = true
full_portfolio_path_available = false
simulation_only = true
readonly_research_only = true
production_allowed = false
```

## 5. 禁止事项

本轮禁止：

```text
1. ED1-S2 attribution rerun；
2. RAL-ED2 rule sanity；
3. rule replay / rule selection / threshold selection；
4. validation 选阈值；
5. strict_test；
6. 模型训练 / bandit / qlib+LTR；
7. delay_sell / accelerated_sell / threshold_multi_buy / multi_sell；
8. full portfolio path replay；
9. cash replacement path 规则化；
10. 输出 OrderIntent；
11. 输出 target_weight / target_position / quantity / broker order；
12. provider/latest/monitor/frontend/Agent/broker/production 扩权；
13. 把 local action delta 解释成组合级收益。
```

## 6. 执行任务

### 6.1 Source baseline ledger manifest

输出：

```text
source_baseline_ledger_manifest.json
```

至少包含：

```text
source_baseline_ledger
source_signal_artifact
source_prior_trace_root
source_prior_attribution_root
train_window
validation_window
strict_test_window_declared_only
strict_test_used
required_columns
available_columns
missing_columns
row_count_by_split
```

### 6.2 Coverage repair design

输出：

```text
block_buy_trace_coverage_repair_design.md
```

必须说明：

```text
1. 如何从 baseline buy rows 构造 block_buy local counterfactual；
2. 如何覆盖 2023-2024 train 与 2025 validation；
3. 如何保持 PIT-safe；
4. 为什么这是 local action delta，不是 full portfolio path；
5. 为什么不是 rule candidate；
6. 为什么不读取 strict_test；
7. 如何避免 OrderIntent / target / quantity / broker fields。
```

### 6.3 Coverage audit

输出：

```text
block_buy_trace_coverage_audit.csv
```

至少包含：

```text
window
start_date
end_date
row_count
symbol_count
date_count
trace_status
trace_quality
local_action_delta_only
coverage_status
coverage_blocker
```

必须覆盖：

```text
train_2023_2024
validation_2025
strict_test_2026_declared_only_not_used
```

### 6.4 Counterfactual trace output

输出：

```text
counterfactual_trace_sample_or_full.csv
```

字段必须对齐 ED0 ActionTraceLedgerArtifact 核心字段，并额外包含：

```text
probe_id
diagnostic_probe_only
not_rule_candidate
not_selected_by_validation
counterfactual_construction_method
counterfactual_trace_quality
local_action_delta_only
full_portfolio_path_available
ineligibility_for_ed2_reason
```

必须包含：

```text
action_trace_id
baseline_counterfactual_trace_id
trace_source
trace_status
date
symbol
split
baseline_action_type
intervention_action_type
score
score_zscore
score_gap
rank
rank_delta
score_delta
baseline_trade_notional_diagnostic
intervention_trade_notional_diagnostic
baseline_fee_tax_diagnostic
intervention_fee_tax_diagnostic
fee_tax_delta_diagnostic
baseline_turnover_diagnostic
intervention_turnover_diagnostic
turnover_delta_diagnostic
baseline_pnl_after_fee_tax_diagnostic
intervention_pnl_after_fee_tax_diagnostic
delta_pnl_after_fee_tax_diagnostic
attribution_horizon
simulation_only
readonly_research_only
production_allowed
```

### 6.5 Baseline vs intervention delta output

输出：

```text
baseline_vs_intervention_delta_sample_or_full.csv
```

至少包含：

```text
window
probe_id
action_trace_id
baseline_counterfactual_trace_id
date
symbol
baseline_action_type
intervention_action_type
trace_status
trace_quality
baseline_pnl_after_fee_tax_diagnostic
intervention_pnl_after_fee_tax_diagnostic
delta_pnl_after_fee_tax_diagnostic
baseline_fee_tax_diagnostic
intervention_fee_tax_diagnostic
fee_tax_delta_diagnostic
baseline_turnover_diagnostic
intervention_turnover_diagnostic
turnover_delta_diagnostic
deterministic_replay_key
eligible_for_ed1_s2_rerun
ineligibility_for_ed2_reason
```

### 6.6 Train / validation window audit

输出：

```text
train_validation_window_audit.csv
```

必须明确：

```text
train window = 2023-01-01..2024-12-31
validation window = 2025-01-01..2025-12-31
strict_test window = 2026-01-01..2026-05-07, declared only, not used
```

至少包含：

```text
window
start_date
end_date
rows_expected_or_available
rows_generated
date_count
symbol_count
coverage_status
not_used_reason
```

### 6.7 Determinism / cost / blocker / safety audits

输出：

```text
determinism_audit.csv
cost_turnover_delta_audit.csv
unavailable_field_blocker_audit.csv
forbidden_consumer_audit.csv
trace_status_audit.csv
```

`forbidden_consumer_audit.csv` 必须覆盖：

```text
ral_ed1_s2
ral_ed2
rule_return_replay
rule_selection
threshold_selection
strict_test
model_training
OrderIntent_output
target_weight
target_position
quantity
broker_order
provider_publish
accepted_latest_switch
monitor_write
frontend_default_switch
Agent_recommendation
production_default_strategy
```

全部必须为 `not_authorized` / `not_performed` / `not_used` / `not_output`。

### 6.8 Validator and findings

输出：

```text
validator_report.json
diagnostic_findings.md
```

`validator_report.json` 至少检查：

```text
all required files exist
train_rows > 0
validation_rows > 0
validation not single-day only
validation symbol_count sufficient
only block_buy_trace_probe_v1 used
all trace_status = counterfactual_replay_trace
trace_quality = local_action_delta_only disclosed
strict_test_used = false
rule_replay_run = false
rule_selection_run = false
threshold_selection_run = false
model_training_run = false
no OrderIntent / target_weight / target_position / quantity / broker order
production_allowed = false
```

`diagnostic_findings.md` 必须回答：

```text
1. 是否成功生成 2023-2024 train block-buy trace；
2. 是否成功生成 2025 validation block-buy trace；
3. validation rows 是否足够，不是单日/极少数 symbol；
4. 是否保持 local action delta only；
5. 是否没有使用 strict_test；
6. 是否可以进入 ED1-S2 attribution rerun；
7. 如果不能，阻断原因是什么。
```

## 7. 必须输出

输出目录：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed1_t_block_buy_trace_coverage_repair/
```

必须输出：

```text
manifest.json
source_baseline_ledger_manifest.json
block_buy_trace_coverage_repair_design.md
block_buy_trace_coverage_audit.csv
counterfactual_trace_sample_or_full.csv
baseline_vs_intervention_delta_sample_or_full.csv
trace_status_audit.csv
train_validation_window_audit.csv
determinism_audit.csv
cost_turnover_delta_audit.csv
unavailable_field_blocker_audit.csv
forbidden_consumer_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_T_BLOCK_BUY_TRACE_COVERAGE_REPAIR_EXECUTION_REPORT_CN.md
```

## 8. 通过条件

ED1-T 通过只表示可以考虑重跑 ED1-S2 attribution，不表示规则有效。

通过条件：

```text
1. train_rows > 0；
2. validation_rows > 0；
3. validation 覆盖不是单日或极少数 symbol 的偶然样本；
4. trace_status 全部为 counterfactual_replay_trace；
5. trace_quality 明确为 local action delta only；
6. deterministic replay key 可重复；
7. delta_pnl_after_fee_tax_diagnostic、fee_tax_delta_diagnostic、turnover_delta_diagnostic 完整；
8. 没有 derived_proxy / summary_level_only 冒充；
9. 没有 rule replay / threshold selection / strict_test / training；
10. 没有 OrderIntent / target_weight / target_position / quantity / broker order；
11. validator_report.json ok=true。
```

如果通过，执行报告只能推荐：

```text
READY_FOR_REVIEWER_TO_CONSIDER_RAL_ED1_S2_ATTRIBUTION_RERUN_WORK
```

不得推荐 ED2。

## 9. STOP 条件

若出现以下任一情况，必须 STOP：

```text
1. 无法生成 2025 validation block-buy trace；
2. validation rows 过少，无法支撑方向一致性；
3. 生成 validation trace 需要 full portfolio path、现金再配置、quantity 或 target；
4. 必须引入 qlib+LTR、模型训练或新信号；
5. 执行者试图做规则回测、阈值选择或 ED2；
6. trace 中混入 proxy/summary；
7. safety audit 出现生产、订单、provider/latest、frontend 或 Agent 扩权；
8. validator_report.json failed_count > 0。
```

失败推荐只能是：

```text
STOP_VALIDATION_TRACE_NOT_AVAILABLE
STOP_VALIDATION_TRACE_COVERAGE_TOO_SMALL
STOP_TRACE_REPAIR_REQUIRES_FORBIDDEN_CONTRACT
STOP_TRACE_STATUS_MIXED_WITH_PROXY
STOP_FORBIDDEN_ACTION_REQUESTED
STOP_VALIDATOR_FAILED
```

## 10. 给执行者的命令

```text
你是执行者。请执行 RAL-ED Explicit Rule Discovery 主线的 RAL-ED1-T Block-buy Trace Coverage Repair。

必须读取：
1. docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
2. docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
3. docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S_BLOCK_BUY_COUNTERFACTUAL_ATTRIBUTION_RERUN_REVIEW_CN.md
4. docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S_BLOCK_BUY_COUNTERFACTUAL_ATTRIBUTION_RERUN_EXECUTION_REPORT_CN.md
5. docs/tw_portfolio_decision_model/POLICY_RAL_ED1_T_BLOCK_BUY_TRACE_COVERAGE_REPAIR_WORK_CN.md
6. data_tw/experiments/explicit_rule_discovery/ral_ed1_r_counterfactual_trace_repair/*
7. data_tw/experiments/explicit_rule_discovery/ral_ed1_s_block_buy_counterfactual_attribution/*
8. data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/*

本轮只补齐 block_buy_trace_probe_v1 trace 覆盖：
- 生成 train + validation block-buy local counterfactual traces；
- 生成 coverage audit；
- 生成 train_validation_window_audit；
- 生成 determinism / cost_turnover / trace_status / forbidden audits；
- 写 validator_report.json 和 diagnostic_findings.md；
- 写 execution report。

本轮禁止：
- ED1-S2 attribution rerun；
- RAL-ED2；
- rule replay / rule selection / threshold selection；
- strict_test；
- model training；
- delay_sell / accelerated_sell / threshold_multi_buy / multi_sell；
- full portfolio path replay；
- OrderIntent / target_weight / target_position / quantity / broker order；
- provider/latest/monitor/frontend/Agent/broker/production 扩权。

输出目录：
data_tw/experiments/explicit_rule_discovery/ral_ed1_t_block_buy_trace_coverage_repair/

执行报告：
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_T_BLOCK_BUY_TRACE_COVERAGE_REPAIR_EXECUTION_REPORT_CN.md
```

## 11. 给后续审查者的审查口径

审查者必须检查：

```text
1. 是否只补 block-buy trace coverage；
2. 是否没有做 ED1-S2 attribution rerun；
3. 是否没有做 ED2 / rule replay / threshold selection；
4. train 与 validation rows 是否都 > 0；
5. validation 覆盖是否不是单日/极少数 symbol；
6. trace_status 是否全为 counterfactual_replay_trace；
7. trace_quality 是否保留 local_action_delta_only；
8. 是否没有 strict_test、训练、OrderIntent、target/quantity/order；
9. 如果通过，是否只考虑 ED1-S2 工作文档，不得直接进入 ED2。
```
