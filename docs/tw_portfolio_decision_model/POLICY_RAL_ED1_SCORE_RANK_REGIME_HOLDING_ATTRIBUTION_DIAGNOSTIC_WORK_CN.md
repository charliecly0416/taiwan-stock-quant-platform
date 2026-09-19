---
created_at: 2026-06-23
status: work_order_for_ral_ed1_attribution_diagnostic
phase: RAL_ED1_SCORE_RANK_REGIME_HOLDING_ATTRIBUTION_DIAGNOSTIC
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
prior_review: docs/tw_portfolio_decision_model/POLICY_RAL_ED0_EXPLICIT_RULE_DISCOVERY_CONTRACT_REVIEW_CN.md
contract_artifact_root: data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design
output_root: data_tw/experiments/explicit_rule_discovery/ral_ed1_attribution_diagnostic
readonly_only: true
simulation_only: true
rule_replay_authorized: false
model_training_authorized: false
strict_test_authorized: false
production_allowed: false
---

# RAL-ED1 Score / Rank / Regime / Holding Attribution Diagnostic 工作文档

## 1. 本轮目标

本轮执行 RAL-ED 主线第二步：

```text
RAL-ED1: Score / Rank / Regime / Holding Attribution Diagnostic
```

目标是：

```text
不跑新规则；
不训练模型；
不读取或使用 strict_test；
只构建/审计 trace-level attribution；
只做 score / rank / regime / holding / cost 归因诊断；
判断是否存在至少一个值得后续预声明的显式规则假设。
```

本轮成功不代表可以自动进入 RAL-ED2。只有 ED1 输出明确、可审查、trace evidence 至少达到 `counterfactual_replay_trace` 的 candidate hypothesis，且通过审查者审查后，才可由后续工作文档授权 ED2。

## 2. 必须读取

执行者必须先读取：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED0_EXPLICIT_RULE_DISCOVERY_CONTRACT_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED0_EXPLICIT_RULE_DISCOVERY_CONTRACT_EXECUTION_REPORT_CN.md
```

必须读取 ED0 合同工件：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/manifest.json
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/action_trace_ledger_schema.json
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/trace_status_policy.md
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/existing_replay_trace_support_audit.csv
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/diagnostic_feature_schema.json
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/explicit_rule_hypothesis_template.md
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/candidate_diagnostic_domains.md
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/multi_trade_gate_design.md
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/rolling_oos_design.md
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/regime_validation_design.md
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/no_grid_search_policy.md
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

## 3. 输入范围

允许读取的既有证据限于 RAL-ED 主线已承认的 readonly research artifacts，例如：

```text
data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json
data_tw/experiments/rule_attribution_ledger/ral1_r_baseline_replay_data_contract_repair/repaired_baseline_action_symbol_daily_ledger.csv
data_tw/experiments/rule_attribution_ledger/ral2_existing_pba_action_attribution/pba_action_symbol_daily_ledger.csv
data_tw/experiments/rule_attribution_ledger/ral2_existing_pba_action_attribution/field_availability_audit.csv
data_tw/experiments/baseline_anchored_active_policy/pba2_rule_calibrated_active_overlay_sanity/active_policy_decision_artifact.csv
data_tw/experiments/baseline_anchored_active_policy/pba2_rule_calibrated_active_overlay_sanity/active_overlay_replay_ledger.csv
data_tw/experiments/baseline_anchored_active_policy/pba3_supervised_bandit_active_policy/active_policy_decision_artifact.csv
data_tw/experiments/baseline_anchored_active_policy/pba3_r_fold_stability_repair/active_policy_decision_artifact.csv
```

如果实际文件缺失、字段不足、或字段无法 PIT-safe 构造，必须在 `trace_support_audit.csv` 和执行报告中说明，不得用推测补齐。

## 4. 执行任务

### 4.1 构建 action trace 样本

输出：

```text
action_trace_ledger_sample.csv
```

要求：

```text
1. 字段对齐 ED0 action_trace_ledger_schema.json；
2. 必须包含 action_trace_id；
3. 必须包含 baseline_counterfactual_trace_id，无法构造时写 unavailable；
4. 必须包含 trace_status；
5. 必须包含 simulation_only=true、readonly_research_only=true、production_allowed=false；
6. 不得包含 forbidden fields。
```

如果只能构造 baseline native trace 或 derived proxy，也必须如实标记，不得冒充 counterfactual replay trace。

### 4.2 生成 trace 支持审计

输出：

```text
trace_support_audit.csv
```

至少包含：

```text
source_artifact
field_or_capability
support_status
trace_status_assigned
eligible_for_rule_hypothesis
notes
```

必须回答：

```text
1. 现有 replay 是否能生成 native action_trace_id？
2. 哪些动作只能 derived_proxy / summary_level_only？
3. 哪些字段不能 PIT-safe 构造？
4. 哪些证据达到 native_trace 或 counterfactual_replay_trace？
5. 哪些证据不得进入 RAL-ED2？
```

### 4.3 生成 counterfactual delta attribution 审计

输出：

```text
counterfactual_delta_attribution_audit.csv
```

至少包含：

```text
action_trace_id
date
symbol
baseline_action_type
intervention_action_type
trace_status
baseline_counterfactual_trace_id
baseline_pnl_after_fee_tax_diagnostic
intervention_pnl_after_fee_tax_diagnostic
delta_pnl_after_fee_tax_diagnostic
fee_tax_delta_diagnostic
turnover_delta_diagnostic
attribution_horizon
eligible_for_hypothesis
ineligibility_reason
```

不得用 summary-level PnL 伪装 date/symbol/action 级 delta。

### 4.4 生成 score / rank / regime / holding / cost 诊断表

必须输出：

```text
score_bucket_return_attribution.csv
score_gap_bucket_attribution.csv
score_zscore_bucket_attribution.csv
rank_delta_attribution.csv
score_delta_attribution.csv
market_regime_action_attribution.csv
volatility_regime_action_attribution.csv
holding_age_sell_attribution.csv
entry_score_hold_attribution.csv
cost_edge_attribution.csv
```

每个诊断表至少包含：

```text
bucket_or_group
date_count
action_count
trace_status_minimum
eligible_trace_count
derived_proxy_count
summary_level_count
baseline_net_return_after_fee_tax
intervention_or_observed_net_return_after_fee_tax
excess_or_delta_return_after_fee_tax
turnover
fee_tax_drag
participation_rate
cash_dominance_rate
active_decision_change_rate
symbol_date_pnl_concentration
status
notes
```

注意：

```text
1. 诊断可以计算 realized outcome 作为 attribution outcome；
2. outcome 不得作为 feature；
3. 不得读取 strict_test；
4. 不得把 2025 validation 反复调成阈值；
5. 不得把低换手、低成本、低回撤替代扣费税后收益。
```

### 4.5 候选假设审计

输出：

```text
candidate_rule_hypothesis_audit.csv
```

每一行是一个候选 hypothesis，不是已授权规则。至少包含：

```text
candidate_id
rule_family
diagnostic_source_tables
evidence_summary
trace_status_minimum
attribution_direction
train_or_subwindow_direction_consistency
predeclared_threshold_candidate
threshold_source
expected_positive_effect
expected_failure_mode
multi_trade_policy_needed
required_gates
eligible_for_ral_ed2_consideration
ineligibility_reason
```

候选必须满足：

```text
1. 低维、可解释；
2. PIT-safe；
3. 不需要 ML/DL/RL/contextual bandit/supervised policy；
4. 不需要 target_weight / target_position / quantity；
5. 不依赖 validation 反复调阈值；
6. 不依赖 strict_test；
7. 不是 no_extra_action；
8. 不是 baseline clone；
9. trace evidence 至少达到 counterfactual_replay_trace 才可标记 eligible。
```

如果所有候选只达到 `derived_proxy` 或 `summary_level_only`，必须标记：

```text
STOP_NO_RAL_ED2_READY_HYPOTHESIS
```

### 4.6 诊断结论

输出：

```text
diagnostic_findings.md
```

必须逐项回答主线 ED1 的 11 个问题：

```text
1. 现有 replay 是否能生成 native action_trace_id？
2. 哪些动作只能 derived_proxy / summary_level_only？
3. score 绝对值或 zscore 与后续净贡献是否单调或分层明显？
4. score gap 小的 baseline buy 是否贡献负收益？
5. rank/score 快速下降是否对应卖出收益改善？
6. rank 下降但 score 仍强的持仓，延后卖是否可能有利？
7. risk_off/high_vol 中 baseline buy 是否集中亏损？
8. holding age 是否影响卖出时点？
9. trade cost 是否能定义最小 score edge？
10. threshold-driven multi-buy/multi-sell 是否可能提高收益，还是主要增加成本？
11. 是否存在至少一个可预声明、低维、非模型化 rule hypothesis？
```

结论只能是以下之一：

```text
READY_FOR_REVIEWER_TO_CONSIDER_RAL_ED2_WORK
STOP_NO_RAL_ED2_READY_HYPOTHESIS
STOP_TRACE_SUPPORT_INSUFFICIENT
STOP_PIT_SAFE_FEATURE_CONSTRUCTION_FAILED
STOP_FORBIDDEN_ACTION_REQUESTED
```

## 5. 必须输出

输出目录：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed1_attribution_diagnostic/
```

必须输出文件：

```text
action_trace_ledger_sample.csv
trace_support_audit.csv
counterfactual_delta_attribution_audit.csv
score_bucket_return_attribution.csv
score_gap_bucket_attribution.csv
score_zscore_bucket_attribution.csv
rank_delta_attribution.csv
score_delta_attribution.csv
market_regime_action_attribution.csv
volatility_regime_action_attribution.csv
holding_age_sell_attribution.csv
entry_score_hold_attribution.csv
cost_edge_attribution.csv
candidate_rule_hypothesis_audit.csv
diagnostic_findings.md
validator_report.json
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_SCORE_RANK_REGIME_HOLDING_ATTRIBUTION_DIAGNOSTIC_EXECUTION_REPORT_CN.md
```

## 6. Validator 要求

`validator_report.json` 至少检查：

```text
all required diagnostic tables exist
required columns exist
trace_status counts reported
no forbidden fields
no future return / label / strict_test fields used as features
candidate_rule_hypothesis_audit generated
no rule replay executed
no model training
no target_weight / target_position / quantity / broker order
simulation_only true
readonly_research_only true
production_allowed false
```

如果未实现正式 validator，也必须用可复核的脚本或表头审计生成 `validator_report.json`，并在执行报告中列出验证方式。

## 7. 禁止事项

本轮禁止：

```text
1. 跑规则收益；
2. 训练模型；
3. 运行或读取 strict_test；
4. 输出 OrderIntent；
5. 输出 target_weight / target_position / quantity / broker order；
6. provider publish / accepted latest switch；
7. monitor write / frontend default / Agent integration；
8. broker / quick-trade / production strategy switch；
9. 把 derived_proxy 或 summary_level_only 标为 native_trace；
10. 把 validation-mined threshold 写成预声明阈值；
11. 用 cash/no-trade、baseline clone、低换手、低回撤替代扣费税后收益。
```

## 8. 通过条件

ED1 通过必须满足：

```text
1. 所有必需输出存在；
2. trace_status 审计完整；
3. diagnostic features PIT-safe；
4. 没有 strict_test、训练、规则回放、target/order 字段；
5. 至少一个候选 hypothesis 满足：
   attribution evidence clear；
   train/validation 或 subwindow 方向不明显反转；
   trace evidence 至少达到 counterfactual_replay_trace；
   非 no_extra_action；
   非 baseline clone；
   可预声明；
   不需要 ML 模型；
   不需要 target_weight / quantity。
```

如果第 5 条不满足，ED1 仍可作为诊断完成，但审查结论必须是 STOP，不得进入 RAL-ED2。

## 9. 给执行者的命令

```text
你是执行者。请执行 RAL-ED Explicit Rule Discovery 主线 RAL-ED1。

必须读取：
1. docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
2. docs/tw_portfolio_decision_model/POLICY_RAL_ED0_EXPLICIT_RULE_DISCOVERY_CONTRACT_REVIEW_CN.md
3. docs/tw_portfolio_decision_model/POLICY_RAL_ED0_EXPLICIT_RULE_DISCOVERY_CONTRACT_EXECUTION_REPORT_CN.md
4. data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/*

本轮只做 attribution diagnostic：
- 构建 action_trace_ledger_sample.csv；
- 生成 trace_support_audit.csv；
- 生成 counterfactual_delta_attribution_audit.csv；
- 生成 score/rank/regime/holding/cost attribution tables；
- 生成 candidate_rule_hypothesis_audit.csv；
- 写 diagnostic_findings.md；
- 写 validator_report.json；
- 写 ED1 execution report。

本轮禁止：
- 跑规则收益；
- 训练模型；
- 运行或读取 strict_test；
- 输出 OrderIntent；
- 输出 target_weight / target_position / quantity / broker order；
- provider/latest/monitor/frontend/Agent/broker/production 扩权；
- 把 proxy/summary 冒充 native/counterfactual trace。

输出目录：
data_tw/experiments/explicit_rule_discovery/ral_ed1_attribution_diagnostic/

执行报告：
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_SCORE_RANK_REGIME_HOLDING_ATTRIBUTION_DIAGNOSTIC_EXECUTION_REPORT_CN.md
```

## 10. 给审查者的审查口径

ED1 审查者必须检查：

```text
1. 是否严格遵守 ED1，不得提前执行 ED2；
2. trace_status 是否诚实，proxy/summary 是否未被提升；
3. diagnostic features 是否 PIT-safe；
4. 所有 attribution 表是否存在且字段完整；
5. candidate_rule_hypothesis_audit 是否只标记证据充分的候选；
6. 是否有至少一个 counterfactual_replay_trace 以上证据支持的候选；
7. 是否没有 strict_test、训练、规则回放；
8. 是否没有 target_weight / target_position / quantity / OrderIntent；
9. multi-trade 相关候选是否已有成本、换手、交易数 gate；
10. 如果无明确 hypothesis，是否 STOP 回统筹。
```
