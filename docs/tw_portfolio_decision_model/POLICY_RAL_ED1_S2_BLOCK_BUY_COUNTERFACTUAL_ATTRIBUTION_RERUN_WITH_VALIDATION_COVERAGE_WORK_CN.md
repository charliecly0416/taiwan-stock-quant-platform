---
created_at: 2026-06-23
status: work_order_for_ral_ed1_s2_block_buy_counterfactual_attribution_rerun_with_validation_coverage
phase: RAL_ED1_S2_BLOCK_BUY_COUNTERFACTUAL_ATTRIBUTION_RERUN_WITH_VALIDATION_COVERAGE
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
coordinator_opinion: docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
prior_review: docs/tw_portfolio_decision_model/POLICY_RAL_ED1_T_BLOCK_BUY_TRACE_COVERAGE_REPAIR_REVIEW_CN.md
prior_execution_report: docs/tw_portfolio_decision_model/POLICY_RAL_ED1_T_BLOCK_BUY_TRACE_COVERAGE_REPAIR_EXECUTION_REPORT_CN.md
source_trace_root: data_tw/experiments/explicit_rule_discovery/ral_ed1_t_block_buy_trace_coverage_repair
prior_failed_attribution_root: data_tw/experiments/explicit_rule_discovery/ral_ed1_s_block_buy_counterfactual_attribution
output_root: data_tw/experiments/explicit_rule_discovery/ral_ed1_s2_block_buy_counterfactual_attribution_with_validation_coverage
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

# RAL-ED1-S2 Block-buy Counterfactual Attribution Rerun With Validation Coverage 工作文档

## 1. 本轮定位

本轮执行 ED1-T 通过后的既定下一步：

```text
RAL-ED1-S2: Block-buy Counterfactual Attribution Rerun With Validation Coverage
```

本轮只允许使用 ED1-T 补齐后的 `block_buy_trace_probe_v1` local counterfactual traces，重跑 block-buy attribution，并判断是否存在可供审查者考虑的低维、可预声明 hypothesis。

本轮不是：

```text
RAL-ED2
规则收益 replay
规则选择
threshold selection
strict_test
模型训练
生产集成
```

## 2. 必须读取

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_T_BLOCK_BUY_TRACE_COVERAGE_REPAIR_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_T_BLOCK_BUY_TRACE_COVERAGE_REPAIR_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_T_BLOCK_BUY_TRACE_COVERAGE_REPAIR_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S_BLOCK_BUY_COUNTERFACTUAL_ATTRIBUTION_RERUN_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S_BLOCK_BUY_COUNTERFACTUAL_ATTRIBUTION_RERUN_REVIEW_CN.md
```

必须读取 ED1-T artifacts：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed1_t_block_buy_trace_coverage_repair/manifest.json
data_tw/experiments/explicit_rule_discovery/ral_ed1_t_block_buy_trace_coverage_repair/source_baseline_ledger_manifest.json
data_tw/experiments/explicit_rule_discovery/ral_ed1_t_block_buy_trace_coverage_repair/block_buy_trace_coverage_audit.csv
data_tw/experiments/explicit_rule_discovery/ral_ed1_t_block_buy_trace_coverage_repair/counterfactual_trace_sample_or_full.csv
data_tw/experiments/explicit_rule_discovery/ral_ed1_t_block_buy_trace_coverage_repair/baseline_vs_intervention_delta_sample_or_full.csv
data_tw/experiments/explicit_rule_discovery/ral_ed1_t_block_buy_trace_coverage_repair/trace_status_audit.csv
data_tw/experiments/explicit_rule_discovery/ral_ed1_t_block_buy_trace_coverage_repair/train_validation_window_audit.csv
data_tw/experiments/explicit_rule_discovery/ral_ed1_t_block_buy_trace_coverage_repair/determinism_audit.csv
data_tw/experiments/explicit_rule_discovery/ral_ed1_t_block_buy_trace_coverage_repair/forbidden_consumer_audit.csv
data_tw/experiments/explicit_rule_discovery/ral_ed1_t_block_buy_trace_coverage_repair/validator_report.json
```

必须参考 ED0 contract：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/action_trace_ledger_schema.json
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/trace_status_policy.md
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/diagnostic_feature_schema.json
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/no_grid_search_policy.md
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/multi_trade_gate_design.md
```

必须参考项目边界合同：

```text
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
```

## 3. 输入与输出

输入 trace root：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed1_t_block_buy_trace_coverage_repair/
```

输出目录：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed1_s2_block_buy_counterfactual_attribution_with_validation_coverage/
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S2_BLOCK_BUY_COUNTERFACTUAL_ATTRIBUTION_RERUN_WITH_VALIDATION_COVERAGE_EXECUTION_REPORT_CN.md
```

## 4. 允许分析的方向

仅允许分析 block-buy 类 attribution：

```text
score_threshold_buy_filter
score_zscore_buy_filter
score_gap_buy_filter
rank_delta_buy_confirmation
cost_edge_buy_filter
```

仅当 trace 中有可用、非 proxy、非 summary 的 regime 字段时，才允许分析：

```text
high_vol_no_new_buy
risk_off_raise_buy_threshold
```

如果 regime 字段为 `unknown` 或无法从 counterfactual trace 直接支持，必须标记为不可形成 hypothesis。

## 5. 禁止事项

本轮禁止：

```text
1. RAL-ED2 rule sanity；
2. 规则收益 replay；
3. rule selection / threshold selection；
4. validation 反复调阈值；
5. strict_test；
6. 模型训练 / bandit / qlib+LTR；
7. delay_sell / accelerated_sell / threshold_multi_buy / multi_sell；
8. full portfolio allocation / full portfolio path counterfactual；
9. cash replacement path 规则化；
10. 输出 OrderIntent；
11. 输出 target_weight / target_position / quantity / broker order；
12. provider/latest/monitor/frontend/Agent/broker/production 扩权；
13. 把 local action delta 解释为组合级收益；
14. 把 derived_proxy / summary_level_only 混入 hypothesis evidence；
15. 写 RAL-ED2 工作文档。
```

## 6. 执行任务

### 6.1 Source trace manifest

输出：

```text
source_trace_manifest.json
```

必须包含：

```text
source_trace_root
source_trace_file
source_delta_file
source_validator_report
counterfactual_trace_rows
train_rows
validation_rows
allowed_probe_ids
allowed_trace_status
allowed_trace_quality
local_action_delta_only
full_portfolio_path_available
ral_ed2_authorized
rule_replay_authorized
rule_selection_authorized
threshold_selection_authorized
strict_test_authorized
model_training_authorized
production_allowed
```

### 6.2 Coverage gate audit

输出：

```text
block_buy_trace_coverage_audit.csv
```

必须至少包含：

```text
split
row_count
date_count
symbol_count
min_date
max_date
trace_status
trace_quality
coverage_status
coverage_blocker
```

必须明确：

```text
train rows > 0
validation rows > 0
validation 不是单日
validation 不是极少数 symbol
strict_test 未使用
```

### 6.3 Attribution tables

输出：

```text
block_buy_feature_attribution_by_bucket.csv
block_buy_train_validation_direction_audit.csv
block_buy_candidate_hypothesis_audit.csv
```

分析维度只允许来自 trace 中已有字段：

```text
score
score_zscore
score_gap
rank
rank_delta
score_delta
fee_tax_delta_diagnostic
turnover_delta_diagnostic
delta_pnl_after_fee_tax_diagnostic
```

必须分别计算 train 与 validation：

```text
row_count
symbol_count
date_count
mean_delta_pnl_after_fee_tax_diagnostic
median_delta_pnl_after_fee_tax_diagnostic
positive_delta_ratio
mean_fee_tax_delta_diagnostic
mean_turnover_delta_diagnostic
direction_sign
```

不得做阈值搜索。若需要 bucket，只能使用预声明、低维、固定分位或固定方向 bucket，并在 `bucket_policy.md` 中说明。

### 6.4 Candidate hypothesis audit

输出：

```text
block_buy_candidate_hypothesis_audit.csv
```

每个候选必须包含：

```text
hypothesis_id
hypothesis_family
predeclared_condition_text
train_row_count
validation_row_count
train_direction
validation_direction
direction_consistency_status
evidence_trace_status
evidence_trace_quality
local_action_delta_only
full_portfolio_path_available
eligible_for_reviewer_to_consider_ed2_work
ineligibility_reason
```

注意：

```text
eligible_for_reviewer_to_consider_ed2_work = true
```

只表示审查者可以考虑是否写 ED2 工作文档，不表示执行者可直接做 ED2。

### 6.5 Safety and status audits

必须输出：

```text
trace_status_audit.csv
forbidden_consumer_audit.csv
unavailable_field_blocker_audit.csv
diagnostic_findings.md
validator_report.json
```

`forbidden_consumer_audit.csv` 必须覆盖：

```text
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

## 7. 通过条件

ED1-S2 通过只表示：

```text
审查者可以考虑是否存在 ED2 work document 的前置 hypothesis。
```

通过条件：

```text
1. ED1-T source validator ok=true；
2. train_rows > 0；
3. validation_rows > 0；
4. validation 覆盖不是单日或极少数 symbol；
5. all evidence trace_status = counterfactual_replay_trace；
6. trace_quality 明确为 local action delta only；
7. train/validation direction audit 已生成；
8. candidate_hypothesis_audit 已生成；
9. 没有 derived_proxy / summary_level_only 冒充；
10. 没有 rule replay / threshold selection / strict_test / training；
11. 没有 OrderIntent / target_weight / target_position / quantity / broker order；
12. validator_report.json ok=true。
```

若没有任何候选满足 train/validation 方向一致或证据质量要求，执行报告必须 STOP，不得推荐 ED2。

## 8. STOP 条件

若出现以下任一情况，必须 STOP：

```text
1. ED1-T source trace 不可读或 validator failed；
2. train 或 validation rows 为 0；
3. validation 覆盖过小，无法支撑方向一致性；
4. trace_status 混入 derived_proxy / summary_level_only；
5. attribution 需要 full portfolio path、现金再配置、quantity 或 target；
6. 执行者做了 rule replay、rule selection、threshold selection 或 ED2；
7. 使用 strict_test；
8. 训练模型或引入新信号；
9. safety audit 出现生产、订单、provider/latest、frontend 或 Agent 扩权；
10. validator_report.json failed_count > 0。
```

失败推荐只能是：

```text
STOP_ED1_T_SOURCE_INVALID
STOP_TRACE_COVERAGE_STILL_INSUFFICIENT
STOP_NO_TRAIN_VALIDATION_DIRECTION_CONSISTENCY
STOP_TRACE_STATUS_MIXED_WITH_PROXY
STOP_ATTRIBUTION_REQUIRES_FORBIDDEN_CONTRACT
STOP_FORBIDDEN_ACTION_REQUESTED
STOP_VALIDATOR_FAILED
```

## 9. 给执行者的命令

```text
你是执行者。请执行 RAL-ED Explicit Rule Discovery 主线的 RAL-ED1-S2 Block-buy Counterfactual Attribution Rerun With Validation Coverage。

必须读取：
1. docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
2. docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
3. docs/tw_portfolio_decision_model/POLICY_RAL_ED1_T_BLOCK_BUY_TRACE_COVERAGE_REPAIR_REVIEW_CN.md
4. docs/tw_portfolio_decision_model/POLICY_RAL_ED1_T_BLOCK_BUY_TRACE_COVERAGE_REPAIR_EXECUTION_REPORT_CN.md
5. docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S2_BLOCK_BUY_COUNTERFACTUAL_ATTRIBUTION_RERUN_WITH_VALIDATION_COVERAGE_WORK_CN.md
6. data_tw/experiments/explicit_rule_discovery/ral_ed1_t_block_buy_trace_coverage_repair/*
7. data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/*

本轮只重跑 block-buy attribution：
- 使用 ED1-T train + validation local traces；
- 生成 coverage gate audit；
- 生成 feature attribution by bucket；
- 生成 train/validation direction audit；
- 生成 candidate hypothesis audit；
- 生成 trace_status / forbidden / unavailable-field audits；
- 写 validator_report.json 和 diagnostic_findings.md；
- 写 execution report。

本轮禁止：
- RAL-ED2；
- rule replay / rule selection / threshold selection；
- validation 调阈值；
- strict_test；
- model training；
- full portfolio path replay；
- OrderIntent / target_weight / target_position / quantity / broker order；
- provider/latest/monitor/frontend/Agent/broker/production 扩权。

输出目录：
data_tw/experiments/explicit_rule_discovery/ral_ed1_s2_block_buy_counterfactual_attribution_with_validation_coverage/

执行报告：
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S2_BLOCK_BUY_COUNTERFACTUAL_ATTRIBUTION_RERUN_WITH_VALIDATION_COVERAGE_EXECUTION_REPORT_CN.md
```

## 10. 给后续审查者的审查口径

审查者必须检查：

```text
1. 是否只做 ED1-S2 attribution rerun；
2. 是否使用 ED1-T 覆盖修复后的 block_buy_trace_probe_v1；
3. train 与 validation coverage gate 是否仍通过；
4. 是否没有 ED2 / rule replay / threshold selection；
5. 是否没有 strict_test、训练、OrderIntent、target/quantity/order；
6. 是否没有 provider/latest/monitor/frontend/Agent/production 扩权；
7. 候选 hypothesis 是否只是 reviewer-consideration，不是 ED2 自动授权；
8. 若无稳定候选，是否 STOP 回统筹。
```
