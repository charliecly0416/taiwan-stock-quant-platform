---
created_at: 2026-06-23
status: work_order_for_ral_ed2_predeclared_block_buy_rule_sanity
phase: RAL_ED2_PREDECLARED_BLOCK_BUY_RULE_SANITY
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
prior_review: docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S2_BLOCK_BUY_COUNTERFACTUAL_ATTRIBUTION_RERUN_WITH_VALIDATION_COVERAGE_REVIEW_CN.md
prior_execution_report: docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S2_BLOCK_BUY_COUNTERFACTUAL_ATTRIBUTION_RERUN_WITH_VALIDATION_COVERAGE_EXECUTION_REPORT_CN.md
source_attribution_root: data_tw/experiments/explicit_rule_discovery/ral_ed1_s2_block_buy_counterfactual_attribution_with_validation_coverage
source_trace_root: data_tw/experiments/explicit_rule_discovery/ral_ed1_t_block_buy_trace_coverage_repair
output_root: data_tw/experiments/explicit_rule_discovery/ral_ed2_predeclared_block_buy_rule_sanity
strict_test_authorized: false
model_training_authorized: false
provider_publish_authorized: false
accepted_latest_switch_authorized: false
monitor_write_authorized: false
frontend_default_switch_authorized: false
agent_authorized: false
broker_authorized: false
order_intent_authorized: false
target_weight_authorized: false
target_position_authorized: false
quantity_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_investment_advice: true
---

# RAL-ED2 Predeclared Block-buy Rule Sanity 工作文档

## 1. 本轮定位

本轮执行 RAL-ED 主线的：

```text
RAL-ED2: Predeclared Explicit Rule Sanity
```

本轮只测试 ED1-S2 attribution 支持的少量 block-buy 显式规则。目标是判断这些预声明 block-buy 规则在 readonly replay 中是否能在扣费税后收益上超过 baseline，并通过 rolling OOS、参与度、现金、集中度、成本和换手 gate。

本轮不是：

```text
strict_test
模型训练
rule grid search
threshold selection
生产策略切换
订单或 broker 集成
provider/latest/monitor/frontend/Agent 集成
```

## 2. 必须读取

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S2_BLOCK_BUY_COUNTERFACTUAL_ATTRIBUTION_RERUN_WITH_VALIDATION_COVERAGE_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S2_BLOCK_BUY_COUNTERFACTUAL_ATTRIBUTION_RERUN_WITH_VALIDATION_COVERAGE_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S2_BLOCK_BUY_COUNTERFACTUAL_ATTRIBUTION_RERUN_WITH_VALIDATION_COVERAGE_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_T_BLOCK_BUY_TRACE_COVERAGE_REPAIR_REVIEW_CN.md
```

必须读取 source artifacts：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed1_s2_block_buy_counterfactual_attribution_with_validation_coverage/manifest.json
data_tw/experiments/explicit_rule_discovery/ral_ed1_s2_block_buy_counterfactual_attribution_with_validation_coverage/block_buy_candidate_hypothesis_audit.csv
data_tw/experiments/explicit_rule_discovery/ral_ed1_s2_block_buy_counterfactual_attribution_with_validation_coverage/block_buy_train_validation_direction_audit.csv
data_tw/experiments/explicit_rule_discovery/ral_ed1_s2_block_buy_counterfactual_attribution_with_validation_coverage/block_buy_feature_attribution_by_bucket.csv
data_tw/experiments/explicit_rule_discovery/ral_ed1_s2_block_buy_counterfactual_attribution_with_validation_coverage/bucket_policy.md
data_tw/experiments/explicit_rule_discovery/ral_ed1_s2_block_buy_counterfactual_attribution_with_validation_coverage/trace_status_audit.csv
data_tw/experiments/explicit_rule_discovery/ral_ed1_s2_block_buy_counterfactual_attribution_with_validation_coverage/forbidden_consumer_audit.csv
data_tw/experiments/explicit_rule_discovery/ral_ed1_s2_block_buy_counterfactual_attribution_with_validation_coverage/validator_report.json
data_tw/experiments/explicit_rule_discovery/ral_ed1_t_block_buy_trace_coverage_repair/counterfactual_trace_sample_or_full.csv
data_tw/experiments/explicit_rule_discovery/ral_ed1_t_block_buy_trace_coverage_repair/baseline_vs_intervention_delta_sample_or_full.csv
```

必须参考 ED0 contract：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/action_trace_ledger_schema.json
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/explicit_rule_hypothesis_template.md
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/no_grid_search_policy.md
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/rolling_oos_design.md
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/multi_trade_gate_design.md
```

必须参考项目边界合同：

```text
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
```

## 3. 输入与输出

输入：

```text
source_attribution_root =
data_tw/experiments/explicit_rule_discovery/ral_ed1_s2_block_buy_counterfactual_attribution_with_validation_coverage

source_trace_root =
data_tw/experiments/explicit_rule_discovery/ral_ed1_t_block_buy_trace_coverage_repair
```

输出目录：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed2_predeclared_block_buy_rule_sanity/
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ED2_PREDECLARED_BLOCK_BUY_RULE_SANITY_EXECUTION_REPORT_CN.md
```

## 4. 预声明候选规则

本轮最多测试 6 个 rule candidates。所有规则只能在 baseline buy candidate 出现时执行：

```text
baseline_action_type = buy_candidate or buy
intervention_action_type = block_buy
allowed_action_types = ["block_buy"]
```

预声明候选：

| rule_id | rule_family | ED1-S2 evidence | predeclared threshold versions |
|---|---|---|---|
| ed2_block_buy_score_zscore_gt_1 | score_zscore_buy_filter | z_gt_1, train 274 / validation 151, same_positive_direction | zscore > 1.0; zscore > rolling_train_75pct |
| ed2_block_buy_score_zscore_0_to_1 | score_zscore_buy_filter | z_0_1, train 108 / validation 43, same_positive_direction | 0 <= zscore < 1.0; rolling_train_50pct <= zscore < rolling_train_75pct |
| ed2_block_buy_score_gap_high | score_gap_buy_filter | gap_q4_high, train 98 / validation 69, same_positive_direction | score_gap >= rolling_train_75pct; score_gap >= rolling_train_90pct |
| ed2_block_buy_score_gap_mid_high | score_gap_buy_filter | gap_q3, train 115 / validation 52, same_positive_direction | rolling_train_50pct <= score_gap < rolling_train_75pct; score_gap >= rolling_train_50pct |
| ed2_block_buy_cost_edge_high | cost_edge_buy_filter | cost_edge_q3/q4, train 201 / validation 134, same_positive_direction | cost_edge_proxy >= rolling_train_75pct; cost_edge_proxy >= rolling_train_50pct |
| ed2_block_buy_rank_delta_deterioration | rank_delta_buy_confirmation | rank_deteriorate_1_10 / gt10, train 356 / validation 157, same_positive_direction | rank_delta > 1; rank_delta > 10 |

阈值规则：

```text
1. 固定阈值可以直接使用；
2. rolling_train_* 阈值只能由当前 rolling fold 的 train window 计算；
3. 不得用 2025 validation 或 rolling validation/test window 反推阈值；
4. 若某阈值无法 PIT-safe 计算，必须 mark skipped，不得替换为临时阈值；
5. 不得新增第 7 个 candidate；
6. 不得为任一 candidate 新增第 3 个 threshold version。
```

## 5. 交易和组合限制

本轮是 readonly rule sanity replay。必须预声明：

```text
max_buy_count_per_day = baseline buy count capped by block-buy rule only
max_sell_count_per_day = baseline sell count unchanged
max_total_trade_count_per_day = baseline total trade count or lower
max_daily_turnover = baseline daily turnover or lower
max_period_turnover = baseline period turnover or lower
max_fee_tax_drag = baseline fee_tax_drag or lower
minimum_active_decision_change_rate = report-only, must not be zero
cash_dominance_gate = fail if excess return mainly comes from staying in cash
participation_gate = fail if participation collapses to no-trade
symbol/date pnl concentration gate = fail if one symbol/date dominates excess
```

本轮不得生成：

```text
OrderIntent
target_weight
target_position
quantity
broker_order
```

如 replay engine 内部需要 shares/notional 进行只读核算，只能作为 diagnostic replay internal 字段，不得输出为 order/target/quantity artifact。

## 6. Rolling OOS 设计

必须使用 rolling OOS，不得只用单一 2025 validation 冒充。

最小设计：

```text
coverage = 2023-01-01..2025-12-31
train_window = 12 months
validation_or_test_window = next 3 months
step = 3 months
strict_test = 2026-01-01..2026-05-07 declared only, not used
```

如果数据不足，输出：

```text
rolling_oos_insufficient_data
```

并 STOP，不得改用单窗口 validation 通过。

## 7. 必须输出

输出目录必须包含：

```text
manifest.json
source_artifact_manifest.json
predeclared_rule_candidate_manifest.csv
threshold_source_audit.csv
readonly_rule_replay_result.csv
baseline_vs_rule_replay_comparison.csv
rolling_oos_result.csv
participation_cash_dominance_audit.csv
turnover_cost_gate_audit.csv
active_decision_change_audit.csv
symbol_date_pnl_concentration_audit.csv
baseline_clone_no_trade_audit.csv
forbidden_consumer_audit.csv
strict_test_boundary_audit.csv
diagnostic_findings.md
validator_report.json
```

## 8. Validator 要求

`validator_report.json` 至少检查：

```text
all required files exist
source ED1-S2 validator ok=true
candidate_count <= 6
threshold_versions_per_candidate <= 2
threshold_source not validation-mined
rolling_oos_result exists
validation net_return_after_fee_tax compared with baseline
rolling_oos average excess computed
participation gate computed
cash dominance gate computed
active decision change gate computed
symbol/date concentration gate computed
turnover/cost gate computed
baseline clone/no-trade gate computed
strict_test_used=false
model_training_run=false
no OrderIntent / target_weight / target_position / quantity / broker_order output
provider/latest/monitor/frontend/Agent/production not performed
```

## 9. 通过条件

RAL-ED2 通过必须同时满足：

```text
1. 至少一个预声明 rule candidate 的 validation net_return_after_fee_tax > baseline；
2. rolling OOS average excess > 0；
3. train/validation direction 不明显反转；
4. participation gate pass；
5. cash dominance gate pass；
6. active decision change rate pass；
7. not baseline clone；
8. not no-trade / cash-only；
9. symbol/date PnL concentration pass；
10. cost/turnover not pathological；
11. strict_test_used=false；
12. validator_report.json ok=true。
```

通过后只能推荐：

```text
READY_FOR_COORDINATOR_TO_CONSIDER_RAL_ED3_FINAL_ONLY_STRICT_TEST_WORK
```

不得自动 strict_test。

## 10. STOP 条件

若出现以下任一情况，必须 STOP：

```text
1. source ED1-S2 validator failed；
2. 需要 validation-mined threshold；
3. candidate_count > 6；
4. 任一 candidate threshold versions > 2；
5. 无法 rolling OOS；
6. validation net_return_after_fee_tax 未超过 baseline；
7. rolling OOS average excess <= 0；
8. excess 主要来自 cash/no-trade；
9. baseline clone 或 active decision change 太低；
10. 单日/单股 PnL 集中；
11. 成本/换手 pathological；
12. 使用 strict_test；
13. 训练模型或引入新信号；
14. 输出订单、target、quantity 或 broker 字段；
15. 触碰 provider/latest/monitor/frontend/Agent/production。
```

失败推荐只能是：

```text
STOP_NO_PREDECLARED_RULE_BEATS_BASELINE
STOP_ROLLING_OOS_FAILED
STOP_VALIDATION_MINED_THRESHOLD
STOP_CASH_OR_NO_TRADE_DOMINANCE
STOP_BASELINE_CLONE
STOP_CONCENTRATION_FAILED
STOP_COST_TURNOVER_FAILED
STOP_FORBIDDEN_ACTION_REQUESTED
STOP_VALIDATOR_FAILED
```

## 11. 给执行者的命令

```text
你是执行者。请执行 RAL-ED Explicit Rule Discovery 主线的 RAL-ED2 Predeclared Block-buy Rule Sanity。

必须读取：
1. docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
2. docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S2_BLOCK_BUY_COUNTERFACTUAL_ATTRIBUTION_RERUN_WITH_VALIDATION_COVERAGE_REVIEW_CN.md
3. docs/tw_portfolio_decision_model/POLICY_RAL_ED2_PREDECLARED_BLOCK_BUY_RULE_SANITY_WORK_CN.md
4. data_tw/experiments/explicit_rule_discovery/ral_ed1_s2_block_buy_counterfactual_attribution_with_validation_coverage/*
5. data_tw/experiments/explicit_rule_discovery/ral_ed1_t_block_buy_trace_coverage_repair/*
6. data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/*

本轮只做 readonly RAL-ED2 block-buy rule sanity：
- 使用本文档预声明的最多 6 个 block-buy candidates；
- 每个 candidate 最多 2 个阈值版本；
- 阈值必须 fixed 或 rolling train-only；
- 跑 validation net_return_after_fee_tax vs baseline；
- 跑 rolling OOS；
- 跑 participation / cash dominance / active decision / concentration / turnover cost / clone gates；
- 生成所有 audit、validator_report.json、diagnostic_findings.md；
- 写执行报告。

本轮禁止：
- strict_test；
- model training；
- rule grid search / validation threshold selection；
- OrderIntent / target_weight / target_position / quantity / broker order；
- provider/latest/monitor/frontend/Agent/broker/production 扩权。

输出目录：
data_tw/experiments/explicit_rule_discovery/ral_ed2_predeclared_block_buy_rule_sanity/

执行报告：
docs/tw_portfolio_decision_model/POLICY_RAL_ED2_PREDECLARED_BLOCK_BUY_RULE_SANITY_EXECUTION_REPORT_CN.md
```

## 12. 给后续审查者的审查口径

审查者必须检查：

```text
1. 是否只测试本文档预声明候选；
2. 是否没有 validation-mined threshold；
3. 是否真正做 rolling OOS；
4. 是否用 net_return_after_fee_tax > baseline，而不是 local delta 或 gross return；
5. 是否通过 participation、cash dominance、active decision、concentration、cost/turnover、clone gate；
6. 是否没有 strict_test、训练、订单、target/quantity/broker、provider/latest/monitor/frontend/Agent/production；
7. 若通过，是否只建议统筹考虑 ED3 final-only strict_test，不得自动进入 strict_test。
```
