---
created_at: 2026-06-23
status: work_order_for_ral_ed1_r_counterfactual_trace_feasibility_repair
phase: RAL_ED1_R_COUNTERFACTUAL_TRACE_FEASIBILITY_REPAIR
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
coordinator_opinion: docs/tw_portfolio_decision_model/POLICY_RAL_ED1_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
prior_review: docs/tw_portfolio_decision_model/POLICY_RAL_ED1_SCORE_RANK_REGIME_HOLDING_ATTRIBUTION_DIAGNOSTIC_REVIEW_CN.md
prior_execution_report: docs/tw_portfolio_decision_model/POLICY_RAL_ED1_SCORE_RANK_REGIME_HOLDING_ATTRIBUTION_DIAGNOSTIC_EXECUTION_REPORT_CN.md
contract_artifact_root: data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design
prior_artifact_root: data_tw/experiments/explicit_rule_discovery/ral_ed1_attribution_diagnostic
output_root: data_tw/experiments/explicit_rule_discovery/ral_ed1_r_counterfactual_trace_repair
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

# RAL-ED1-R Counterfactual Trace Feasibility Repair 工作文档

## 1. 本轮定位

本轮执行统筹授权的 repair：

```text
RAL-ED1-R: Counterfactual Trace Feasibility Repair
```

本轮不是 RAL-ED2。

本轮目标只回答：

```text
现有 readonly replay / ledger / state 是否能构造 intervention-level counterfactual trace；
如果可以，哪些 probe 能达到 counterfactual_replay_trace；
如果不可以，缺哪些 replay state 字段、ledger 字段或 contract 能力。
```

本轮不回答：

```text
哪个显式规则收益最高；
哪个 threshold 应该被选中；
是否存在 ED2-ready rule；
是否能进入 strict_test；
是否能生产化。
```

## 2. 背景与 Gate

ED1 审查结论为：

```text
STOP_NO_RAL_ED2_READY_HYPOTHESIS
```

阻断原因不是 ED1 执行失败，而是：

```text
counterfactual_replay_trace_rows = 0
candidate_rule_hypothesis_audit.csv 中所有候选 eligible_for_ral_ed2_consideration = False
```

统筹意见明确：

```text
RAL-ED2: not authorized
rule replay / rule selection: not authorized
strict_test: not authorized
model training: not authorized
counterfactual trace feasibility repair: authorized
production/default/order: not authorized
```

因此本轮只修 trace 能力，不跑规则实验。

## 3. 必须读取

执行者必须先读取：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_SCORE_RANK_REGIME_HOLDING_ATTRIBUTION_DIAGNOSTIC_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_SCORE_RANK_REGIME_HOLDING_ATTRIBUTION_DIAGNOSTIC_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_SCORE_RANK_REGIME_HOLDING_ATTRIBUTION_DIAGNOSTIC_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED0_EXPLICIT_RULE_DISCOVERY_CONTRACT_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED0_EXPLICIT_RULE_DISCOVERY_CONTRACT_EXECUTION_REPORT_CN.md
```

必须读取 ED0 contract artifacts：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/action_trace_ledger_schema.json
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/trace_status_policy.md
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/existing_replay_trace_support_audit.csv
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/diagnostic_feature_schema.json
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/multi_trade_gate_design.md
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/validator_design.md
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/golden_sample_design.md
```

必须读取 ED1 diagnostic artifacts：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed1_attribution_diagnostic/manifest.json
data_tw/experiments/explicit_rule_discovery/ral_ed1_attribution_diagnostic/action_trace_ledger_sample.csv
data_tw/experiments/explicit_rule_discovery/ral_ed1_attribution_diagnostic/trace_support_audit.csv
data_tw/experiments/explicit_rule_discovery/ral_ed1_attribution_diagnostic/counterfactual_delta_attribution_audit.csv
data_tw/experiments/explicit_rule_discovery/ral_ed1_attribution_diagnostic/candidate_rule_hypothesis_audit.csv
data_tw/experiments/explicit_rule_discovery/ral_ed1_attribution_diagnostic/diagnostic_findings.md
data_tw/experiments/explicit_rule_discovery/ral_ed1_attribution_diagnostic/validator_report.json
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
1. 新增一个 readonly repair 脚本，用于审计现有 replay/state 是否能产生 counterfactual trace。
2. 读取 frozen qlib signal、baseline ledger、ED1 diagnostic artifacts、existing replay artifacts。
3. 构造少量 diagnostic_probe_only 的 intervention probe。
4. 输出 counterfactual_trace_sample.csv 与 delta sample。
5. 输出字段可用性、determinism、cost/turnover delta、multi-trade gate feasibility 审计。
6. 如无法构造 counterfactual trace，输出 blocker audit，而不是硬凑 proxy。
```

允许的最小 probe 名称仅限：

```text
block_buy_trace_probe
delay_sell_trace_probe
accelerated_sell_trace_probe
threshold_multi_buy_trace_probe
```

这些 probe 必须标记：

```text
diagnostic_probe_only = true
not_rule_candidate = true
not_selected_by_validation = true
strict_test_used = false
```

## 5. 禁止事项

本轮禁止：

```text
1. RAL-ED2 rule sanity；
2. 规则收益排名；
3. validation 选规则或选 threshold；
4. strict_test；
5. 机器学习 / 深度学习 / 强化学习 / bandit / qlib+LTR；
6. 输出 OrderIntent；
7. 输出 target_weight / target_position / quantity / broker order；
8. provider publish / accepted latest switch；
9. monitor write / frontend default / Agent integration；
10. broker / quick-trade / production strategy switch；
11. 把 derived_proxy 或 summary_level_only 冒充为 counterfactual_replay_trace；
12. 用 summary-level PnL 伪造 action_trace_id 级 delta；
13. 生成 ED2 工作文档或声称任何 probe 是 ED2-ready rule。
```

如果构造 trace 必须依赖 target_weight、target_position、quantity、OrderIntent 或 production strategy 修改，必须停止并报告：

```text
STOP_TRACE_REPAIR_REQUIRES_FORBIDDEN_CONTRACT
```

## 6. 执行任务

### 6.1 Counterfactual trace feasibility design

输出：

```text
counterfactual_trace_feasibility_design.md
```

必须说明：

```text
1. 哪些 replay/state 字段可用于 baseline-vs-intervention 对齐；
2. 哪些字段可 PIT-safe 构造；
3. 哪些字段只能 derived_proxy / summary_level_only；
4. 如何生成 action_trace_id 与 baseline_counterfactual_trace_id；
5. 如何计算 delta_pnl_after_fee_tax_diagnostic；
6. 如何计算 fee_tax_delta_diagnostic 与 turnover_delta_diagnostic；
7. 如何避免输出 forbidden fields；
8. 为什么本轮 probe 不是 rule candidate。
```

### 6.2 Probe manifest

输出：

```text
intervention_probe_manifest.json
```

每个 probe 至少包含：

```text
probe_id
probe_type
diagnostic_probe_only
not_rule_candidate
not_selected_by_validation
allowed_action_type
source_baseline_trace_filter
expected_counterfactual_action
required_state_fields
required_cost_fields
required_turnover_fields
strict_test_used
model_training_run
rule_selection_run
production_allowed
```

注意：

```text
probe_type 只能是 block_buy_trace_probe / delay_sell_trace_probe / accelerated_sell_trace_probe / threshold_multi_buy_trace_probe。
```

### 6.3 Required replay state field audit

输出：

```text
required_replay_state_field_audit.csv
```

至少包含：

```text
probe_id
required_field
source_artifact_or_module
availability_status
pit_safe
can_support_counterfactual_trace
if_missing_blocker
notes
```

必须覆盖：

```text
date
symbol
baseline_action_type
baseline price used
baseline trade notional diagnostic
baseline fee/tax diagnostic
baseline turnover diagnostic
baseline PnL after fee/tax diagnostic
pre-decision cash diagnostic, if available
pre-decision holdings diagnostic, if available
post-intervention state transition diagnostic, if available
score / rank / score_gap / score_zscore
```

### 6.4 Counterfactual trace sample

输出：

```text
counterfactual_trace_sample.csv
```

若可构造，字段必须对齐 ED0 `ActionTraceLedgerArtifact` 的核心字段，并额外包含：

```text
probe_id
diagnostic_probe_only
not_rule_candidate
not_selected_by_validation
counterfactual_construction_method
counterfactual_trace_quality
ineligibility_for_ed2_reason
```

最低要求：

```text
action_trace_id
baseline_counterfactual_trace_id
trace_source
trace_status
date
symbol
baseline_action_type
intervention_action_type
decision_reason_code
score
score_zscore
score_gap
rank
rank_delta
score_delta
holding_age
market_regime
volatility_regime
score_dispersion_regime
price_used
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

如果无法生成任何 `counterfactual_replay_trace`，仍必须输出空表头或 blocker rows，并在 `unavailable_field_blocker_audit.csv` 中说明原因。

### 6.5 Baseline vs intervention delta sample

输出：

```text
baseline_vs_intervention_delta_sample.csv
```

至少包含：

```text
probe_id
action_trace_id
baseline_counterfactual_trace_id
date
symbol
baseline_action_type
intervention_action_type
trace_status
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
counterfactual_trace_quality
eligible_for_ed1_s_rerun
ineligibility_reason
```

`eligible_for_ed1_s_rerun` 只表示是否可能用于后续重新做 attribution，不表示 ED2-ready。

### 6.6 Trace status upgrade audit

输出：

```text
trace_status_upgrade_audit.csv
```

至少包含：

```text
source_trace_status
target_trace_status_candidate
probe_id
row_count
upgrade_allowed
upgrade_reason
blocked_reason
review_required_before_use
```

必须明确：

```text
derived_proxy -> counterfactual_replay_trace 不得自动升级；
summary_level_only -> counterfactual_replay_trace 不得升级；
只有实际 baseline-vs-intervention deterministic replay trace 才可标记 counterfactual_replay_trace。
```

### 6.7 Replay determinism audit

输出：

```text
replay_determinism_audit.csv
```

至少包含：

```text
probe_id
determinism_key
input_artifact_hash_or_size
row_count
rerun_required
determinism_status
non_determinism_source
notes
```

如果本轮未实际执行可重复 replay，只能写：

```text
determinism_status = not_testable_design_only
```

不得把 design-only 冒充为 deterministic replay pass。

### 6.8 Cost / turnover delta audit

输出：

```text
cost_turnover_delta_audit.csv
```

至少包含：

```text
probe_id
row_count
fee_tax_delta_available
turnover_delta_available
baseline_cost_available
intervention_cost_available
after_fee_tax_delta_available
status
blocked_reason
```

### 6.9 Multi-trade gate feasibility audit

输出：

```text
multi_trade_gate_feasibility_audit.csv
```

至少包含：

```text
probe_id
multi_trade_relevant
max_buy_count_available
max_sell_count_available
max_total_trade_count_available
max_daily_turnover_available
max_period_turnover_available
max_fee_tax_drag_available
symbol_date_pnl_concentration_available
gate_feasibility_status
blocked_reason
```

只评估 gate feasibility，不得评估 multi-trade rule return。

### 6.10 Unavailable field blocker audit

输出：

```text
unavailable_field_blocker_audit.csv
```

至少包含：

```text
blocker_id
probe_id
missing_field_or_capability
required_for
source_checked
why_missing_blocks_counterfactual_trace
can_continue_without_it
recommended_coordinator_decision
```

### 6.11 Forbidden consumer audit

输出：

```text
forbidden_consumer_audit.csv
```

必须覆盖：

```text
model_training
rule_return_replay
rule_selection
strict_test
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

每项必须是：

```text
not_performed
not_used
not_output
```

或说明 blocker。

### 6.12 Validator and golden samples

输出：

```text
validator_report.json
golden_samples_report.json
```

`validator_report.json` 至少检查：

```text
all required files exist
required columns exist
trace_status values valid
counterfactual_replay_trace only when construction method is deterministic baseline-vs-intervention replay
no derived_proxy/summary_level_only upgraded without evidence
no forbidden fields
no rule replay / rule selection
no strict_test
no model training
no OrderIntent / target_weight / target_position / quantity / broker order
readonly_research_only true
simulation_only true
production_allowed false
```

`golden_samples_report.json` 至少覆盖：

```text
positive_counterfactual_trace_if_available
negative_proxy_marked_counterfactual
negative_summary_level_delta
negative_missing_baseline_counterfactual_trace_id
negative_missing_delta_pnl
negative_target_field_present
negative_strict_test_used
negative_rule_selection_claim
negative_quantity_or_order_output
```

如果无法生成 positive sample，必须写：

```text
positive_counterfactual_trace_if_available = not_available
reason = <具体 blocker>
```

## 7. 必须输出

输出目录：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed1_r_counterfactual_trace_repair/
```

必须输出文件：

```text
manifest.json
counterfactual_trace_feasibility_design.md
intervention_probe_manifest.json
required_replay_state_field_audit.csv
counterfactual_trace_sample.csv
baseline_vs_intervention_delta_sample.csv
trace_status_upgrade_audit.csv
replay_determinism_audit.csv
cost_turnover_delta_audit.csv
multi_trade_gate_feasibility_audit.csv
unavailable_field_blocker_audit.csv
forbidden_consumer_audit.csv
validator_report.json
golden_samples_report.json
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_R_COUNTERFACTUAL_TRACE_FEASIBILITY_REPAIR_EXECUTION_REPORT_CN.md
```

## 8. 通过条件

RAL-ED1-R 通过只表示 trace 能力可用，不表示规则有效。

通过条件：

```text
1. 至少一种 intervention probe 能生成 counterfactual_replay_trace；
2. trace 能输出 baseline_counterfactual_trace_id；
3. trace 能输出 delta_pnl_after_fee_tax_diagnostic；
4. trace 能输出 fee_tax_delta_diagnostic；
5. trace 能输出 turnover_delta_diagnostic；
6. replay / construction method 可复现并被 determinism audit 说明；
7. trace_status 没有把 proxy/summary 冒充为 counterfactual；
8. no strict_test / no training / no production / no OrderIntent；
9. no target_weight / target_position / quantity / broker order；
10. validator_report.json ok=true。
```

如果通过，执行报告只能推荐：

```text
READY_FOR_REVIEWER_TO_AUDIT_TRACE_FEASIBILITY
```

审查者仍不得直接写 ED2。下一步必须回统筹决定是否授权：

```text
RAL-ED1-S: score/rank/regime attribution rerun with counterfactual traces
```

或新的 ED1 repeat 工作文档。

## 9. 失败 / STOP 条件

若出现以下任一情况，必须 STOP 回统筹：

```text
1. 现有 replay 无法构造 intervention counterfactual trace；
2. 必须引入 target_weight / target_position / quantity / OrderIntent 才能构造 trace；
3. 必须修改 production strategy 或 registry/default 才能构造 trace；
4. delta PnL 只能 summary-level proxy，不能达到 counterfactual_replay_trace；
5. 多买/多卖 probe 无法做成本/换手 gate；
6. 需要读取或使用 strict_test；
7. 需要训练模型；
8. 需要 provider/latest/monitor/frontend/Agent/broker/production 扩权；
9. validator_report.json failed_count > 0；
10. 执行者无法证明 trace_status 升级依据。
```

失败时执行报告必须推荐以下之一：

```text
STOP_COUNTERFACTUAL_TRACE_NOT_FEASIBLE_WITH_CURRENT_REPLAY
STOP_TRACE_REPAIR_REQUIRES_FORBIDDEN_CONTRACT
STOP_TRACE_REPAIR_ONLY_PROXY_OR_SUMMARY_AVAILABLE
STOP_TRACE_REPAIR_VALIDATOR_FAILED
```

## 10. 给执行者的命令

```text
你是执行者。请执行 RAL-ED Explicit Rule Discovery 主线的 RAL-ED1-R Counterfactual Trace Feasibility Repair。

必须读取：
1. docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
2. docs/tw_portfolio_decision_model/POLICY_RAL_ED1_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
3. docs/tw_portfolio_decision_model/POLICY_RAL_ED1_SCORE_RANK_REGIME_HOLDING_ATTRIBUTION_DIAGNOSTIC_REVIEW_CN.md
4. docs/tw_portfolio_decision_model/POLICY_RAL_ED1_SCORE_RANK_REGIME_HOLDING_ATTRIBUTION_DIAGNOSTIC_EXECUTION_REPORT_CN.md
5. docs/tw_portfolio_decision_model/POLICY_RAL_ED1_R_COUNTERFACTUAL_TRACE_FEASIBILITY_REPAIR_WORK_CN.md
6. data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/*
7. data_tw/experiments/explicit_rule_discovery/ral_ed1_attribution_diagnostic/*

本轮只做 counterfactual trace feasibility / minimal repair：
- 设计 counterfactual trace feasibility；
- 定义 diagnostic_probe_only intervention probes；
- 审计 required replay state fields；
- 尝试构造 counterfactual_trace_sample.csv；
- 生成 baseline_vs_intervention_delta_sample.csv；
- 生成 trace_status_upgrade_audit.csv；
- 生成 replay_determinism_audit.csv；
- 生成 cost_turnover_delta_audit.csv；
- 生成 multi_trade_gate_feasibility_audit.csv；
- 生成 unavailable_field_blocker_audit.csv；
- 生成 forbidden_consumer_audit.csv；
- 生成 validator_report.json 与 golden_samples_report.json；
- 写 execution report。

本轮禁止：
- RAL-ED2 rule sanity；
- 规则收益 replay / rule selection；
- validation 选阈值；
- strict_test；
- 训练模型；
- 输出 OrderIntent；
- 输出 target_weight / target_position / quantity / broker order；
- provider/latest/monitor/frontend/Agent/broker/production 扩权；
- 把 proxy/summary 冒充 counterfactual_replay_trace。

输出目录：
data_tw/experiments/explicit_rule_discovery/ral_ed1_r_counterfactual_trace_repair/

执行报告：
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_R_COUNTERFACTUAL_TRACE_FEASIBILITY_REPAIR_EXECUTION_REPORT_CN.md
```

## 11. 给后续审查者的审查口径

审查者必须检查：

```text
1. 是否严格限定在 ED1-R trace feasibility；
2. 是否没有提前执行 ED2；
3. probe 是否全部标记 diagnostic_probe_only / not_rule_candidate；
4. 是否没有 rule return replay / rule selection；
5. counterfactual_replay_trace 是否有 deterministic baseline-vs-intervention 依据；
6. derived_proxy / summary_level_only 是否未被升级；
7. delta_pnl / fee_tax_delta / turnover_delta 是否 action_trace_id 级；
8. multi-trade gate 是否只是 feasibility audit；
9. 是否没有 strict_test、训练、OrderIntent、target/quantity/order；
10. 如果 repair 通过，是否仍然只回统筹考虑 ED1-S 或 ED1 repeat，而不是 ED2。
```
