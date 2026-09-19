---
created_at: 2026-06-23
status: work_order_for_ral_ed1_s_block_buy_counterfactual_attribution_rerun
phase: RAL_ED1_S_BLOCK_BUY_COUNTERFACTUAL_ATTRIBUTION_RERUN
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
coordinator_opinion: docs/tw_portfolio_decision_model/POLICY_RAL_ED1_R_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
prior_review: docs/tw_portfolio_decision_model/POLICY_RAL_ED1_R_COUNTERFACTUAL_TRACE_FEASIBILITY_REPAIR_REVIEW_CN.md
prior_execution_report: docs/tw_portfolio_decision_model/POLICY_RAL_ED1_R_COUNTERFACTUAL_TRACE_FEASIBILITY_REPAIR_EXECUTION_REPORT_CN.md
source_trace_root: data_tw/experiments/explicit_rule_discovery/ral_ed1_r_counterfactual_trace_repair
output_root: data_tw/experiments/explicit_rule_discovery/ral_ed1_s_block_buy_counterfactual_attribution
ral_ed2_authorized: false
rule_replay_authorized: false
rule_selection_authorized: false
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

# RAL-ED1-S Block-buy Counterfactual Attribution Rerun 工作文档

## 1. 本轮定位

本轮执行统筹授权的：

```text
RAL-ED1-S: Block-buy Counterfactual Attribution Rerun
```

本轮不是 RAL-ED2，不是规则实验。

本轮目标只允许：

```text
使用 ED1-R 生成的 block_buy local counterfactual traces，
重跑 score / score gap / zscore / rank / regime / cost attribution，
判断是否存在 block-buy 类、低维、可预声明、非模型化的候选 hypothesis。
```

本轮不允许：

```text
规则收益 replay；
规则排名或 threshold selection；
delay_sell / accelerated_sell / threshold_multi_buy / multi_sell；
full portfolio path counterfactual；
strict_test；
训练模型；
生产化。
```

## 2. 当前授权边界

统筹意见确认：

```text
RAL-ED1-S block-buy counterfactual attribution rerun: authorized
RAL-ED2: not authorized
rule replay / selection: not authorized
strict_test: not authorized
model training: not authorized
production/default/order: not authorized
```

ED1-S 只能使用以下来源：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed1_r_counterfactual_trace_repair/counterfactual_trace_sample.csv
data_tw/experiments/explicit_rule_discovery/ral_ed1_r_counterfactual_trace_repair/baseline_vs_intervention_delta_sample.csv
data_tw/experiments/explicit_rule_discovery/ral_ed1_r_counterfactual_trace_repair/trace_status_upgrade_audit.csv
data_tw/experiments/explicit_rule_discovery/ral_ed1_r_counterfactual_trace_repair/replay_determinism_audit.csv
data_tw/experiments/explicit_rule_discovery/ral_ed1_r_counterfactual_trace_repair/validator_report.json
data_tw/experiments/explicit_rule_discovery/ral_ed1_attribution_diagnostic/*
```

ED1-R trace 的质量限制必须保留：

```text
counterfactual_replay_trace_local_action_delta_not_full_portfolio_path
```

不得把它解释为：

```text
full portfolio path replay；
组合级收益提升；
rolling OOS 通过；
ED2-ready rule；
strict_test-ready rule。
```

## 3. 必须读取

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_R_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_R_COUNTERFACTUAL_TRACE_FEASIBILITY_REPAIR_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_R_COUNTERFACTUAL_TRACE_FEASIBILITY_REPAIR_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S_BLOCK_BUY_COUNTERFACTUAL_ATTRIBUTION_RERUN_WORK_CN.md
```

必须读取 ED1-R artifacts：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed1_r_counterfactual_trace_repair/manifest.json
data_tw/experiments/explicit_rule_discovery/ral_ed1_r_counterfactual_trace_repair/counterfactual_trace_sample.csv
data_tw/experiments/explicit_rule_discovery/ral_ed1_r_counterfactual_trace_repair/baseline_vs_intervention_delta_sample.csv
data_tw/experiments/explicit_rule_discovery/ral_ed1_r_counterfactual_trace_repair/trace_status_upgrade_audit.csv
data_tw/experiments/explicit_rule_discovery/ral_ed1_r_counterfactual_trace_repair/replay_determinism_audit.csv
data_tw/experiments/explicit_rule_discovery/ral_ed1_r_counterfactual_trace_repair/cost_turnover_delta_audit.csv
data_tw/experiments/explicit_rule_discovery/ral_ed1_r_counterfactual_trace_repair/validator_report.json
data_tw/experiments/explicit_rule_discovery/ral_ed1_r_counterfactual_trace_repair/forbidden_consumer_audit.csv
```

必须参考 ED0 / ED1 contract 和 diagnostic artifacts：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/action_trace_ledger_schema.json
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/trace_status_policy.md
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/diagnostic_feature_schema.json
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/no_grid_search_policy.md
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/multi_trade_gate_design.md
data_tw/experiments/explicit_rule_discovery/ral_ed1_attribution_diagnostic/diagnostic_findings.md
data_tw/experiments/explicit_rule_discovery/ral_ed1_attribution_diagnostic/trace_support_audit.csv
```

必须参考项目边界合同：

```text
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
```

## 4. 允许分析的方向

仅允许分析 block-buy 类 attribution：

```text
score_threshold_buy_filter
score_zscore_buy_filter
score_gap_buy_filter
rank_delta_buy_confirmation
cost_edge_buy_filter
high_vol_no_new_buy, only if block_buy trace exists by regime
risk_off_raise_buy_threshold, only if block_buy trace exists by regime
```

其中 `high_vol_no_new_buy` / `risk_off_raise_buy_threshold` 必须满足：

```text
trace rows contain usable regime fields；
trace_status remains counterfactual_replay_trace；
regime attribution 不依赖 proxy/summary；
```

如果 regime 字段是 `unknown` 或只有 proxy/summary，不得形成 regime hypothesis。

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
9. 输出 OrderIntent；
10. 输出 target_weight / target_position / quantity / broker order；
11. provider/latest/monitor/frontend/Agent/broker/production 扩权；
12. 把 local action delta 解释为组合级收益；
13. 把 derived_proxy / summary_level_only 混入 hypothesis evidence；
14. 写 ED2 工作文档。
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
allowed_probe_ids
allowed_trace_status
allowed_trace_quality
local_action_delta_only
full_portfolio_path_available
ral_ed2_authorized
rule_replay_authorized
rule_selection_authorized
strict_test_authorized
model_training_authorized
production_allowed
```

必须满足：

```text
allowed_probe_ids = ["block_buy_trace_probe_v1"]
allowed_trace_status = ["counterfactual_replay_trace"]
local_action_delta_only = true
full_portfolio_path_available = false
ral_ed2_authorized = false
```

### 6.2 Block-buy trace coverage audit

输出：

```text
block_buy_trace_coverage_audit.csv
```

至少包含：

```text
split
date_count
row_count
symbol_count
trace_status
trace_quality
min_date
max_date
baseline_action_type_set
intervention_action_type_set
coverage_status
coverage_blocker
```

必须检查：

```text
1. 是否存在 train rows；
2. 是否存在 validation rows；
3. 是否只有单一时间段；
4. 是否只有少数股票/日期；
5. 是否所有 rows 都是 counterfactual_replay_trace；
6. 是否全为 block_buy；
7. trace_quality 是否都是 local action delta。
```

如果没有 validation rows 或覆盖不足，必须在后续 audit 中标记：

```text
validation_coverage_insufficient
```

不得用单一 train/subwindow 冒充 train/validation 一致性。

### 6.3 Block-buy delta attribution tables

必须输出：

```text
score_bucket_block_buy_delta_attribution.csv
score_gap_block_buy_delta_attribution.csv
score_zscore_block_buy_delta_attribution.csv
rank_delta_block_buy_delta_attribution.csv
score_delta_block_buy_delta_attribution.csv
regime_block_buy_delta_attribution.csv
cost_edge_block_buy_delta_attribution.csv
```

每张表至少包含：

```text
bucket_or_group
split
date_count
row_count
symbol_count
trace_status_minimum
counterfactual_trace_count
local_action_delta_only
baseline_pnl_after_fee_tax_sum
intervention_pnl_after_fee_tax_sum
delta_pnl_after_fee_tax_sum
baseline_fee_tax_sum
intervention_fee_tax_sum
fee_tax_delta_sum
baseline_turnover_sum
intervention_turnover_sum
turnover_delta_sum
positive_delta_rate
negative_delta_rate
symbol_date_delta_concentration
status
notes
```

分桶要求：

```text
score bucket: quantile or fixed diagnostic bins, must disclose method
score_gap bucket: quantile or missing bucket
score_zscore bucket: z_lt_-1 / z_-1_0 / z_0_1 / z_gt_1 / missing
rank_delta bucket: improve / stable / deteriorate / missing
score_delta bucket: drop / stable / rise / missing
regime bucket: only if non-unknown trace regime fields exist
cost_edge bucket: diagnostic score/cost relation, not rule threshold
```

注意：

```text
1. 可以汇总 delta_pnl_after_fee_tax_diagnostic；
2. 不得把汇总结果解释为完整组合收益；
3. 不得从 validation 选择阈值；
4. 不得输出 buy/sell advice；
5. 不得生成策略或 OrderIntent。
```

### 6.4 Train / validation direction audit

输出：

```text
train_validation_direction_audit.csv
```

至少包含：

```text
diagnostic_dimension
candidate_pattern
train_row_count
validation_row_count
train_delta_sum
validation_delta_sum
train_positive_delta_rate
validation_positive_delta_rate
direction_consistency_status
coverage_status
failure_reason
eligible_for_hypothesis_consideration
```

规则：

```text
如果 validation_row_count = 0，则 coverage_status = validation_coverage_insufficient。
如果 train/validation 方向反转，则 direction_consistency_status = direction_reversal。
如果只有单一 subwindow，则 eligible_for_hypothesis_consideration = false。
```

### 6.5 Candidate block-buy rule hypothesis audit

输出：

```text
candidate_block_buy_rule_hypothesis_audit.csv
```

每行是候选 hypothesis，不是规则实验。至少包含：

```text
candidate_id
rule_family
diagnostic_source_tables
evidence_summary
trace_status_minimum
trace_quality
local_action_delta_only
coverage_status
train_validation_direction_status
predeclared_threshold_candidate
threshold_source
expected_positive_effect
expected_failure_mode
requires_full_portfolio_path
requires_model
requires_target_or_quantity
eligible_for_reviewer_to_consider_ed2_work
ineligibility_reason
```

候选 family 只能来自：

```text
score_threshold_buy_filter
score_zscore_buy_filter
score_gap_buy_filter
rank_delta_buy_confirmation
cost_edge_buy_filter
high_vol_no_new_buy
risk_off_raise_buy_threshold
```

`eligible_for_reviewer_to_consider_ed2_work = true` 必须同时满足：

```text
1. evidence trace_status 全部为 counterfactual_replay_trace；
2. 证据只来自 block_buy_trace_probe_v1；
3. train/validation 或足够 subwindow 方向不明显反转；
4. 覆盖不集中于少数日期/股票；
5. hypothesis 低维、可预声明；
6. 不需要模型；
7. 不需要 target_weight / target_position / quantity；
8. 不需要 full portfolio path 才能定义初始 block-buy-only sanity；
9. 不是 baseline clone；
10. 不是 no_extra_action；
11. 没有 threshold selection / validation-mined threshold。
```

如果任何条件不满足，必须标记 false 并写明原因。

### 6.6 Trace status audit

输出：

```text
trace_status_audit.csv
```

至少包含：

```text
source_file
trace_status
trace_quality
probe_id
row_count
allowed_for_ed1_s
allowed_for_candidate_hypothesis
blocked_reason
```

必须明确：

```text
counterfactual_replay_trace_local_action_delta_not_full_portfolio_path 可用于 ED1-S attribution；
不得直接用于 ED2 full-path return claims；
derived_proxy / summary_level_only 不可用于 candidate hypothesis evidence。
```

### 6.7 Forbidden consumer audit

输出：

```text
forbidden_consumer_audit.csv
```

必须覆盖：

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

全部必须为：

```text
not_performed
not_used
not_output
not_authorized
```

或写明 STOP blocker。

### 6.8 Validator report

输出：

```text
validator_report.json
```

至少检查：

```text
all required files exist
required columns exist
only block_buy_trace_probe_v1 used
all evidence trace_status = counterfactual_replay_trace
trace_quality = local_action_delta_not_full_portfolio_path disclosed
source trace row count matches ED1-R source
coverage audit generated
train/validation coverage status reported
candidate hypothesis audit generated
no derived_proxy / summary_level_only in candidate evidence
no rule replay / rule selection / threshold selection
no strict_test
no model training
no OrderIntent / target_weight / target_position / quantity / broker order
readonly_only true
simulation_only true
production_allowed false
```

### 6.9 Diagnostic findings

输出：

```text
diagnostic_findings.md
```

必须逐项回答：

```text
1. block_buy local counterfactual delta 在 train/validation 或 subwindow 上方向是否一致？
2. 低 score / 低 score zscore / 小 score gap 的 baseline buy 是否存在负 delta？
3. rank_delta 或 score_delta 是否能解释哪些 baseline buy 应被 block？
4. risk_off / high_vol 中 block_buy delta 是否更好？
5. fee_tax_delta / turnover_delta 是否足以解释 block_buy 的收益来源？
6. 是否存在一个低维、预声明、非模型化、非 baseline-clone 的 block-buy rule hypothesis？
7. 该 hypothesis 是否只依赖 counterfactual_replay_trace，而不是 proxy/summary？
8. 是否存在 coverage / concentration / local-action-only 限制，阻止进入 ED2？
```

结论只能是以下之一：

```text
READY_FOR_REVIEWER_TO_CONSIDER_BLOCK_BUY_ONLY_ED2_WORK
STOP_BLOCK_BUY_TRACE_COVERAGE_INSUFFICIENT
STOP_NO_CLEAR_BLOCK_BUY_HYPOTHESIS
STOP_DIRECTION_REVERSAL_OR_CONCENTRATION
STOP_TRACE_STATUS_MIXED_WITH_PROXY
STOP_FORBIDDEN_ACTION_REQUESTED
```

## 7. 必须输出

输出目录：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed1_s_block_buy_counterfactual_attribution/
```

必须输出文件：

```text
manifest.json
source_trace_manifest.json
block_buy_trace_coverage_audit.csv
score_bucket_block_buy_delta_attribution.csv
score_gap_block_buy_delta_attribution.csv
score_zscore_block_buy_delta_attribution.csv
rank_delta_block_buy_delta_attribution.csv
score_delta_block_buy_delta_attribution.csv
regime_block_buy_delta_attribution.csv
cost_edge_block_buy_delta_attribution.csv
train_validation_direction_audit.csv
candidate_block_buy_rule_hypothesis_audit.csv
trace_status_audit.csv
forbidden_consumer_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S_BLOCK_BUY_COUNTERFACTUAL_ATTRIBUTION_RERUN_EXECUTION_REPORT_CN.md
```

## 8. 通过条件

ED1-S 通过不是指规则已验证，而是指审查者可以考虑写 block-buy-only ED2 工作文档。

通过条件：

```text
1. 至少一个 block-buy hypothesis 有 clear counterfactual delta evidence；
2. evidence trace_status 全部为 counterfactual_replay_trace；
3. evidence 只来自 block_buy_trace_probe_v1；
4. train/validation 或足够 subwindow 方向不明显反转；
5. 覆盖不集中于少数日期/股票；
6. hypothesis 可预声明、低维、不需要模型；
7. hypothesis 不依赖 no_extra_action / baseline clone；
8. hypothesis 不需要 target_weight / target_position / quantity；
9. hypothesis 不需要 full portfolio path 才能定义初始 block-buy-only sanity；
10. no strict_test / no training / no production / no OrderIntent；
11. validator_report.json ok=true。
```

如果通过，执行报告只能推荐：

```text
READY_FOR_REVIEWER_TO_CONSIDER_BLOCK_BUY_ONLY_ED2_WORK
```

注意：这仍不自动授权 ED2。必须由审查者另行审查并写 block-buy-only ED2 工作文档，且不得包含 delay_sell / multi-buy / multi-sell / strict_test。

## 9. 失败 / STOP 条件

若出现以下任一情况，必须 STOP：

```text
1. block_buy trace 覆盖不足；
2. validation rows 不存在且无法做足够 subwindow 方向检查；
3. score/score_gap/zscore/rank/regime 无明确方向；
4. train/validation 或 subwindow 方向反转；
5. positive signal 集中于少数日期/股票；
6. hypothesis 需要 validation 反复调阈值；
7. evidence 混入 derived_proxy / summary_level_only；
8. hypothesis 需要 full portfolio path 才能定义；
9. 执行者请求 rule replay / rule selection / strict_test / training / production；
10. 执行者输出 target_weight / target_position / quantity / OrderIntent / broker order；
11. validator_report.json failed_count > 0。
```

失败时执行报告必须推荐以下之一：

```text
STOP_BLOCK_BUY_TRACE_COVERAGE_INSUFFICIENT
STOP_NO_CLEAR_BLOCK_BUY_HYPOTHESIS
STOP_DIRECTION_REVERSAL_OR_CONCENTRATION
STOP_TRACE_STATUS_MIXED_WITH_PROXY
STOP_FORBIDDEN_ACTION_REQUESTED
STOP_VALIDATOR_FAILED
```

## 10. 给执行者的命令

```text
你是执行者。请执行 RAL-ED Explicit Rule Discovery 主线的 RAL-ED1-S Block-buy Counterfactual Attribution Rerun。

必须读取：
1. docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
2. docs/tw_portfolio_decision_model/POLICY_RAL_ED1_R_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
3. docs/tw_portfolio_decision_model/POLICY_RAL_ED1_R_COUNTERFACTUAL_TRACE_FEASIBILITY_REPAIR_REVIEW_CN.md
4. docs/tw_portfolio_decision_model/POLICY_RAL_ED1_R_COUNTERFACTUAL_TRACE_FEASIBILITY_REPAIR_EXECUTION_REPORT_CN.md
5. docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S_BLOCK_BUY_COUNTERFACTUAL_ATTRIBUTION_RERUN_WORK_CN.md
6. data_tw/experiments/explicit_rule_discovery/ral_ed1_r_counterfactual_trace_repair/*
7. data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/*
8. data_tw/experiments/explicit_rule_discovery/ral_ed1_attribution_diagnostic/*

本轮只做 block-buy counterfactual attribution rerun：
- 读取 ED1-R block_buy_trace_probe_v1 local counterfactual traces；
- 生成 source_trace_manifest.json；
- 生成 block_buy_trace_coverage_audit.csv；
- 生成 score / score_gap / zscore / rank_delta / score_delta / regime / cost attribution tables；
- 生成 train_validation_direction_audit.csv；
- 生成 candidate_block_buy_rule_hypothesis_audit.csv；
- 生成 trace_status_audit.csv；
- 生成 forbidden_consumer_audit.csv；
- 生成 validator_report.json；
- 写 diagnostic_findings.md；
- 写 execution report。

本轮禁止：
- RAL-ED2 rule sanity；
- 规则收益 replay / rule selection / threshold selection；
- delay_sell / accelerated_sell / threshold_multi_buy / multi_sell；
- strict_test；
- 模型训练；
- 输出 OrderIntent；
- 输出 target_weight / target_position / quantity / broker order；
- provider/latest/monitor/frontend/Agent/broker/production 扩权；
- 把 local action delta 解释为 full portfolio path。

输出目录：
data_tw/experiments/explicit_rule_discovery/ral_ed1_s_block_buy_counterfactual_attribution/

执行报告：
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S_BLOCK_BUY_COUNTERFACTUAL_ATTRIBUTION_RERUN_EXECUTION_REPORT_CN.md
```

## 11. 给后续审查者的审查口径

审查者必须检查：

```text
1. 是否只使用 block_buy_trace_probe_v1；
2. 是否所有 hypothesis evidence 都是 counterfactual_replay_trace；
3. 是否保留 local_action_delta_only 限制；
4. 是否没有 rule replay / rule selection / threshold selection；
5. 是否没有 delay_sell / accelerated_sell / multi-buy / multi-sell；
6. 是否没有 strict_test、训练、OrderIntent、target/quantity/order；
7. train/validation 或 subwindow 方向是否足够；
8. 是否存在日期/股票集中；
9. candidate hypothesis 是否真的低维、可预声明、非模型化；
10. 如通过，是否只考虑 block-buy-only ED2 工作文档，不得扩展到其他规则族。
```
