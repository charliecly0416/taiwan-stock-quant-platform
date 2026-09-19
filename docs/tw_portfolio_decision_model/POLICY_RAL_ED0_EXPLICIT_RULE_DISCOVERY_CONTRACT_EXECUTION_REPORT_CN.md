---
created_at: 2026-06-23
status: executed_ral_ed0_contract_design_ready_for_review
phase: RAL_ED0_ACTION_TRACE_LEDGER_AND_RULE_DISCOVERY_CONTRACT
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
artifact_root: data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design
training_run: false
rule_replay_run: false
strict_test_used: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_investment_advice: true
---

# RAL-ED0 Explicit Rule Discovery Contract 执行报告

## 1. Scope

本轮执行 RAL-ED 主线第一步：

```text
RAL-ED0: Action Trace Ledger And Rule Discovery Contract
```

本轮只做合同设计和现有 replay trace 支持盘点：

```text
1. 定义 ActionTraceLedgerArtifact schema。
2. 盘点现有 replay 是否支持 action_trace_id / baseline counterfactual trace。
3. 定义 native / counterfactual / proxy / summary / unavailable 的 trace_status policy。
4. 定义 score / rank / market / holding / cost diagnostic schema。
5. 定义 explicit rule hypothesis template。
6. 定义 candidate diagnostic domains。
7. 定义 threshold-driven multi-buy/multi-sell gates。
8. 定义 rolling OOS / regime validation 设计。
9. 定义 no-grid-search policy。
10. 设计 validator / golden samples。
```

确认非目标：

```text
未跑规则收益
未训练模型
未运行或读取 strict_test
未输出 OrderIntent
未输出 target_weight / target_position / quantity / broker order
未做 provider/latest/monitor/frontend/Agent/broker/production 扩权
```

## 2. Documents / Contracts / Skills Read

使用的 workflow skill：

```text
coordinator-executor-reviewer-workflow
```

已读取主线和前序结论：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_POLICY_RESEARCH_EXTERNAL_CLOSURE_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL2_EXISTING_PBA_ACTION_ATTRIBUTION_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ACTION_LEDGER_RULE_ATTRIBUTION_MAINLINE_CN.md
```

已读取项目与模块合同：

```text
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
```

现有 replay / attribution artifact 表头审计：

```text
data_tw/experiments/rule_attribution_ledger/ral1_r_baseline_replay_data_contract_repair/repaired_baseline_action_symbol_daily_ledger.csv
data_tw/experiments/rule_attribution_ledger/ral2_existing_pba_action_attribution/pba_action_symbol_daily_ledger.csv
data_tw/experiments/baseline_anchored_active_policy/pba2_rule_calibrated_active_overlay_sanity/active_policy_decision_artifact.csv
data_tw/experiments/baseline_anchored_active_policy/pba2_rule_calibrated_active_overlay_sanity/active_overlay_replay_ledger.csv
data_tw/experiments/baseline_anchored_active_policy/pba3_supervised_bandit_active_policy/active_policy_decision_artifact.csv
data_tw/experiments/baseline_anchored_active_policy/pba3_r_fold_stability_repair/active_policy_decision_artifact.csv
data_tw/experiments/rule_attribution_ledger/ral2_existing_pba_action_attribution/field_availability_audit.csv
```

## 3. Changes Made

新增 artifact root：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/
```

新增文件：

```text
manifest.json
action_trace_ledger_schema.json
trace_status_policy.md
existing_replay_trace_support_audit.csv
diagnostic_feature_schema.json
explicit_rule_hypothesis_template.md
candidate_diagnostic_domains.md
multi_trade_gate_design.md
rolling_oos_design.md
regime_validation_design.md
no_grid_search_policy.md
forbidden_consumer_audit.csv
validator_design.md
golden_sample_design.md
```

新增执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ED0_EXPLICIT_RULE_DISCOVERY_CONTRACT_EXECUTION_REPORT_CN.md
```

未修改策略、模型、回放、前端、API、registry 或 production 配置。

## 4. Evidence Produced

### 4.1 ActionTraceLedgerArtifact Schema

`action_trace_ledger_schema.json` 定义：

```text
primary_key = action_trace_id x date x symbol x intervention_action_type
baseline_counterfactual_trace_id required
trace_status required
simulation_only = true
readonly_research_only = true
production_allowed = false
```

关键字段覆盖：

```text
score / score_zscore / score_gap
rank / rank_delta / score_delta
holding_age
market_regime / volatility_regime / score_dispersion_regime
baseline/intervention trade notional
baseline/intervention fee tax
turnover delta
baseline/intervention PnL after fee tax
delta PnL after fee tax
attribution_horizon
```

### 4.2 Trace Status Policy

`trace_status_policy.md` 明确定义：

```text
native_trace
counterfactual_replay_trace
derived_proxy
summary_level_only
unavailable
```

并明确：

```text
只有 native_trace / counterfactual_replay_trace 可支持进入 RAL-ED2。
derived_proxy / summary_level_only 只能作为背景诊断，不可作为 rule sanity 依据。
```

### 4.3 Existing Replay Trace Support Audit

`existing_replay_trace_support_audit.csv` 结论：

```text
RAL1-R repaired baseline ledger:
  baseline action rows and cost/turnover/PnL diagnostics supported as native baseline trace;
  action_trace_id and baseline_counterfactual_trace_id not currently supported.

RAL2 PBA action symbol daily ledger:
  date/symbol/action_source/action_type mapping supported;
  active action native trade PnL not supported;
  many active changed rows remain derived proxy or partial reconciliation.

PBA2/PBA3/PBA3-R decision artifacts:
  decision reason/model/rule rows exist;
  separated from native active trade PnL ledger.

PBA2 active overlay replay ledger:
  daily active replay return exists;
  date/symbol/action trace not available.
```

因此 RAL-ED1 必须诚实标记 trace status，不能把 RAL2 proxy 当 native trace。

### 4.4 Diagnostic Feature Schema

`diagnostic_feature_schema.json` 覆盖：

```text
score_strength
rank_score_change
market_regime
holding_state
cost_turnover
```

并禁止：

```text
future_return
forward_return
label
oracle_action
strict_test_metric
post_decision_realized_pnl_as_feature
```

### 4.5 Rule Template / Domains / Gates

`explicit_rule_hypothesis_template.md` 要求每个规则候选必须声明：

```text
rule_id
rule_family
source_ral_ed1_evidence
trace_status_minimum
predeclared_thresholds
expected_positive_effect
expected_failure_mode
multi_trade_policy
participation/cash/clone/change-rate/concentration/cost gates
forbidden outputs
```

`candidate_diagnostic_domains.md` 覆盖：

```text
score strength
rank and score change
market and regime
holding state
cost and turnover friction
```

`multi_trade_gate_design.md` 定义 threshold-driven multi-buy/multi-sell 必须预声明：

```text
max_buy_count_per_day
max_sell_count_per_day
max_total_trade_count_per_day
max_daily_turnover
max_period_turnover
max_fee_tax_drag
minimum_score_edge_vs_cost
cash dominance gate
participation gate
active decision change rate gate
symbol/date pnl concentration gate
```

### 4.6 Rolling OOS / Regime / No-grid

`rolling_oos_design.md` 定义最小设计：

```text
train window = 12 months
validation/test window = next 3 months
step = 3 months
coverage = 2023-2025
```

如果数据不足，必须报告：

```text
rolling_oos_insufficient_data
```

`regime_validation_design.md` 要求覆盖：

```text
market_regime
volatility_regime
score_dispersion_regime
baseline_state
action_context
```

`no_grid_search_policy.md` 明确：

```text
RAL-ED2 最多 6 个 rule candidates；
每个最多 2 个预声明阈值版本；
不得通过 validation 无界调阈值；
不得使用 strict_test 选阈值。
```

### 4.7 Validator / Golden Samples

`validator_design.md` 定义 RAL-ED0 / RAL-ED1 / RAL-ED2 validator 检查项。

`golden_sample_design.md` 定义 positive / negative cases，覆盖：

```text
native trace
counterfactual block buy
rule hypothesis template
multi-trade gate
missing action_trace_id
proxy marked native
summary-only rule ready
target fields present
grid search thresholds
strict_test used
cash/no-trade success
missing multi-trade gate
```

## 5. Compliance With Mainline

对照 RAL-ED0 要求：

| Requirement | Status |
|---|---|
| 读取主线、closure report、RAL2 review | pass |
| 定义 ActionTraceLedgerArtifact schema | pass |
| 盘点现有 replay trace 支持 | pass |
| 定义 trace_status policy | pass |
| 定义 score/rank/market/holding/cost diagnostic schema | pass |
| 定义 rule hypothesis template | pass |
| 定义 candidate diagnostic domains | pass |
| 定义 multi-buy/multi-sell gates | pass |
| 定义 rolling OOS / regime validation | pass |
| 定义 no-grid-search policy | pass |
| 定义 validator / golden samples | pass |
| 不跑规则收益 | pass |
| 不训练模型 | pass |
| 不 strict_test | pass |
| 不输出 OrderIntent / target fields / broker order | pass |

## 6. Forbidden Actions Audit

`forbidden_consumer_audit.csv` 确认：

```text
model_training = not_performed
rule_return_replay = not_performed
strict_test = not_used
OrderIntent_output = not_output
target_weight = not_output
target_position = not_output
quantity = not_output
broker_order = not_output
provider_publish = not_performed
accepted_latest_switch = not_performed
monitor_write = not_performed
frontend_default_switch = not_performed
Agent_recommendation = not_performed
production_default_strategy = not_performed
```

报告中出现的 target_weight / target_position / quantity / broker order 均为 forbidden label，不是建议、输出或授权。

## 7. Issues / Blockers / Deviations

无执行偏离。

已识别的设计限制：

```text
1. 当前 RAL1-R ledger 支持 baseline native economics，但缺 action_trace_id。
2. 当前 RAL2 ledger 支持 date/symbol/action mapping，但 active action native PnL 多数仍是 derived proxy。
3. PBA2/PBA3/PBA3-R decision artifact 与 replay economic ledger 分离。
4. PBA2 active overlay replay ledger 只有 daily summary，不能直接提供 date/symbol/action trace。
```

这些限制已写入 `existing_replay_trace_support_audit.csv`，并通过 `trace_status_policy.md` 阻止 proxy 证据进入 RAL-ED2。

## 8. Files Changed

新增：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ED0_EXPLICIT_RULE_DISCOVERY_CONTRACT_EXECUTION_REPORT_CN.md
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
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/forbidden_consumer_audit.csv
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/validator_design.md
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/golden_sample_design.md
```

## 9. Recommendation For Reviewer

推荐审查结论：

```text
PASS_READY_FOR_REVIEWER_TO_AUDIT_RAL_ED0_CONTRACT
```

如果审查通过，审查者可据此编写 RAL-ED1 attribution diagnostic 工作文档。若审查认为 action trace contract 或 PIT-safe diagnostic schema 仍不清楚，应 STOP 回统筹，而不是进入 RAL-ED1。
