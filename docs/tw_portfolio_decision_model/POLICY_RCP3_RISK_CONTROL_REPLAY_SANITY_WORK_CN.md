---
created_at: 2026-06-24
status: work_order_for_rcp3_risk_control_replay_sanity
phase: RCP3_RISK_CONTROL_REPLAY_SANITY
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RCP_RISK_CONTROL_POLICY_2022_DOWNTURN_MAINLINE_CN.md
rcp3a_review: docs/tw_portfolio_decision_model/POLICY_RCP3A_MARKET_FEATURE_COVERAGE_PIT_GATE_REVIEW_CN.md
rcp2_review: docs/tw_portfolio_decision_model/POLICY_RCP2_RISK_CONTROL_RULE_DESIGN_CONTRACT_REVIEW_CN.md
rcp2_artifact_root: data_tw/experiments/risk_control_policy_2022/rcp2_risk_control_rule_design_contract
rcp3a_artifact_root: data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate
baseline_artifact_root: data_tw/experiments/risk_control_policy_2022/rcp1b_diagnostic_baseline_replay_audit
signal_artifact_root: data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract
output_root: data_tw/experiments/risk_control_policy_2022/rcp3_risk_control_replay_sanity
execution_report: docs/tw_portfolio_decision_model/POLICY_RCP3_RISK_CONTROL_REPLAY_SANITY_EXECUTION_REPORT_CN.md
review_report: docs/tw_portfolio_decision_model/POLICY_RCP3_RISK_CONTROL_REPLAY_SANITY_REVIEW_CN.md
risk_control_replay_authorized: true
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

# RCP3 Risk-control Replay Sanity 工作文档

## 1. 本轮定位

本轮执行：

```text
RCP3: Risk-control Replay Sanity
```

目标是在 2022 downturn validation diagnostic 窗口中，只读回放 RCP2 预声明的 6 条风险控制规则，判断是否存在值得继续 closure / future expansion 的风险收益 tradeoff。

本轮允许：

```text
基于 RCP1A diagnostic signal、RCP1B baseline replay accounting、RCP2 frozen rules、RCP3A market feature gate，
运行 2022 diagnostic risk-control replay sanity。
```

本轮不允许：

```text
strict_test
训练模型
新增规则
调阈值
用 2022 结果筛选/改写规则
生产/default/provider/frontend/Agent/订单链路集成
OrderIntent / target_weight / target_position / quantity_instruction
```

## 2. 必须读取

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RCP3_RISK_CONTROL_REPLAY_SANITY_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RCP3A_MARKET_FEATURE_COVERAGE_PIT_GATE_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RCP2_RISK_CONTROL_RULE_DESIGN_CONTRACT_REVIEW_CN.md
data_tw/experiments/risk_control_policy_2022/rcp2_risk_control_rule_design_contract/predeclared_rule_candidates.csv
data_tw/experiments/risk_control_policy_2022/rcp2_risk_control_rule_design_contract/evaluation_metric_contract.csv
data_tw/experiments/risk_control_policy_2022/rcp2_risk_control_rule_design_contract/cash_no_trade_guardrail_contract.csv
data_tw/experiments/risk_control_policy_2022/rcp2_risk_control_rule_design_contract/anti_overfit_and_no_2022_mining_audit.csv
data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate/market_feature_by_signal_date.csv
data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate/rule_market_dependency_gate.csv
data_tw/experiments/risk_control_policy_2022/rcp1b_diagnostic_baseline_replay_audit/baseline_summary.csv
data_tw/experiments/risk_control_policy_2022/rcp1b_diagnostic_baseline_replay_audit/baseline_nav.csv
data_tw/experiments/risk_control_policy_2022/rcp1b_diagnostic_baseline_replay_audit/baseline_actions.csv
data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/diagnostic_model_signal.csv
```

必须参考合同：

```text
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
```

可复用实现：

```text
scripts/run_tw_policy_action_model_pa1.py
scripts/run_tw_policy_rcp1b_diagnostic_baseline_replay_audit.py
```

但必须明确：复用 replay accounting engine 不代表使用 PA1 训练 policy，不代表输出订单。

## 3. 允许回放的规则

只能回放 RCP2 冻结规则：

```text
RCP2_RULE_01 Market MA60 Risk-off Buy Gate
RCP2_RULE_02 Market MA60 Plus Strong Rank Gate
RCP2_RULE_03 Portfolio Drawdown Brake 10pct Cooldown
RCP2_RULE_04 Rolling 20D Turnover Cost Brake
RCP2_RULE_05 Risk-off Weak Holding Accelerated Sell
RCP2_RULE_06 Defensive Holding Continuation
```

建议逐条独立 replay。若执行者认为需要一个组合规则，只允许做一个预声明组合：

```text
RCP3_COMBO_DEFENSIVE_ALL = RCP2_RULE_01 + RCP2_RULE_03 + RCP2_RULE_04 + RCP2_RULE_06
```

组合不是用于择优，只能作为诊断，不得因为单规则结果临时调整组合。

## 4. 输出目录

所有产物写入：

```text
data_tw/experiments/risk_control_policy_2022/rcp3_risk_control_replay_sanity/
```

执行报告写入：

```text
docs/tw_portfolio_decision_model/POLICY_RCP3_RISK_CONTROL_REPLAY_SANITY_EXECUTION_REPORT_CN.md
```

## 5. 必须输出文件

必须输出：

```text
manifest.json
replay_source_manifest.json
rule_replay_summary.csv
rule_baseline_comparison.csv
rule_gate_decision.csv
risk_metric_summary_by_rule.csv
cash_no_trade_audit_by_rule.csv
turnover_fee_tax_audit_by_rule.csv
action_count_audit_by_rule.csv
concentration_audit_by_rule.csv
diagnostic_semantics_audit.json
anti_overfit_and_no_2022_mining_audit.csv
forbidden_action_audit.csv
validator_report.json
diagnostic_findings.md
```

并且每条 replayed rule 必须输出子目录：

```text
rules/{rule_id}/summary.csv
rules/{rule_id}/nav.csv
rules/{rule_id}/actions.csv
rules/{rule_id}/position_snapshots.csv
rules/{rule_id}/rule_trigger_ledger.csv
rules/{rule_id}/execution_audit.csv
```

## 6. Replay 行为合同

RCP3 的策略行为必须是 simulation-only internal replay action，不得输出订单合同。

规则动作约束：

```text
RCP2_RULE_01:
  risk_off = market_index_close < market_index_ma60
  if risk_off: block new baseline buys; baseline sells still allowed

RCP2_RULE_02:
  if risk_off and candidate_rank > 10: block new baseline buy
  if candidate_rank <= 10: allow baseline buy
  baseline sells still allowed

RCP2_RULE_03:
  if portfolio_drawdown <= -10%: pause new buys for 5 trading days
  baseline sells still allowed

RCP2_RULE_04:
  if rolling_20d_action_count >= 20: skip low-priority replacement buy
  maintain cash/no-trade guardrails

RCP2_RULE_05:
  if risk_off and holding_rank > 75: allow at most one accelerated sell per day
  buy side remains gated by market risk-off condition

RCP2_RULE_06:
  if risk_off and holding_rank <= 75 and holding_days < 20:
    hold instead of baseline replacement sell/buy
  unless rank is very weak by predeclared rule boundary
```

如果实现某条规则需要字段缺失或语义不清，执行者必须将该规则标记为 `NOT_REPLAYED_REQUIRES_REPAIR`，不得临时改规则。

## 7. 通过 Gate

候选规则不能只靠单一指标通过。`rule_gate_decision.csv` 必须逐条输出：

```text
rule_id
net_return_gate
max_drawdown_gate
turnover_gate
fee_tax_gate
cash_no_trade_gate
participation_gate
concentration_gate
diagnostic_semantics_gate
overall_gate
decision
notes
```

最低标准来自 RCP2：

```text
max_drawdown improvement >= 5 percentage points OR relative improvement >= 15%
net_return_after_fee_tax deterioration <= 5 percentage points vs baseline
participation_rate >= 0.50
average_cash_rate <= 0.60
turnover_proxy / fee_and_tax not worse unless net and drawdown both materially improve
no all-cash / no no-trade
symbol/date concentration pass
diagnostic semantics preserved
```

允许的 `decision`：

```text
PASS_CANDIDATE_FOR_RCP4_CLOSURE_REVIEW
FAIL_NO_RISK_REWARD_TRADEOFF
FAIL_CASH_OR_NO_TRADE
FAIL_COST_OR_TURNOVER
FAIL_IMPLEMENTATION_OR_DATA
NOT_REPLAYED_REQUIRES_REPAIR
```

## 8. validator_report.json

必须包含：

```text
phase
status
pass
required_files_status
rcp3a_gate_status
replayed_rule_count
not_replayed_rule_count
best_gate_decision
any_rule_pass
cash_no_trade_status
concentration_status
diagnostic_semantics_status
anti_overfit_status
forbidden_actions_status
rcp4_authorizable
repair_required
recommended_next_step
```

允许的 `recommended_next_step`：

```text
PASS_READY_FOR_RCP4_CLOSURE_DECISION_WORK_DOC
FAIL_NEEDS_RCP3_REPAIR
STOP_NO_RULE_HAS_RISK_REWARD_TRADEOFF
```

## 9. 禁止事项

本轮禁止：

```text
strict_test
模型训练
新增规则或阈值
用 2022 结果选择规则/调阈值/换特征
provider publish / accepted latest switch
frontend / Agent / monitor 集成
broker / quick-trade / real order
OrderIntentArtifact
target_weight
target_position
quantity_instruction
把 actions.csv 解释为真实订单建议
```

## 10. 审查 Gate

审查者 verdict 只能为：

```text
PASS_READY_FOR_RCP4_CLOSURE_DECISION_WORK_DOC
FAIL_NEEDS_RCP3_REPAIR
STOP_NO_RULE_HAS_RISK_REWARD_TRADEOFF
STOP_REPLAY_SCOPE_VIOLATION
```

审查重点：

```text
1. 是否只回放 RCP2 冻结规则；
2. 是否使用 RCP3A 已通过市场特征；
3. 是否没有 2022 调参/新增规则；
4. replay accounting 是否和 RCP1B baseline 可比；
5. 规则结果是否通过多指标 gate；
6. actions 是否只是 internal replay ledger，不是订单；
7. 是否未触碰生产链路。
```

## 11. 第一执行者指令

```text
请按 docs/tw_portfolio_decision_model/POLICY_RCP3_RISK_CONTROL_REPLAY_SANITY_WORK_CN.md 执行 RCP3。
只回放 RCP2 预声明规则，使用 RCP3A 已通过的 TWII MA60 market feature gate。
不得 strict_test，不得训练，不得新增或调规则，不得用 2022 结果筛选/改阈值，不得改生产链路或输出订单/目标仓位/数量指令。
完成后输出 data_tw/experiments/risk_control_policy_2022/rcp3_risk_control_replay_sanity/ 下全部必需文件，并提交执行报告。
```

## 12. 第一审查者指令

```text
请按 docs/tw_portfolio_decision_model/POLICY_RCP3_RISK_CONTROL_REPLAY_SANITY_WORK_CN.md 审查 RCP3 产物。
重点审查 replay scope、rule gate、cash/no-trade、fee/tax、turnover、concentration、diagnostic-only 语义和 forbidden actions。
通过后只授权 RCP4 closure decision，不授权 strict_test 或生产化。
```
