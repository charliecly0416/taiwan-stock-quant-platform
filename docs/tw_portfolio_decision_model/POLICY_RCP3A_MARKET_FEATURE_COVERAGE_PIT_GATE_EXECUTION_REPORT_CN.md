---
created_at: 2026-06-24T05:01:50Z
status: rcp3a_execution_report
phase: RCP3A_MARKET_FEATURE_COVERAGE_PIT_GATE
work_doc: docs/tw_portfolio_decision_model/POLICY_RCP3A_MARKET_FEATURE_COVERAGE_PIT_GATE_WORK_CN.md
artifact_root: data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate
recommended_next_step: PASS_READY_FOR_RCP3_RISK_CONTROL_REPLAY_SANITY_WORK_DOC
baseline_replay_performed: false
risk_control_replay_performed: false
model_training_performed: false
strict_test_performed: false
production_or_provider_change_performed: false
---

# RCP3A Market Feature Coverage / PIT Gate 执行报告

## 1. Scope

本轮执行 `RCP3A: Market Feature Coverage / PIT Gate`。

只审计候选 `TWII` 市场指数数据源是否能 PIT-safe 支持 RCP2 规则依赖的：

```text
market_index_close
market_index_ma60
```

已确认非目标：

```text
不运行 baseline replay
不运行 risk-control replay
不训练模型
不做 strict_test
不修改 registry/default/provider/frontend/Agent/订单链路
不输出 OrderIntent / target_weight / target_position / quantity_instruction
不使用 2022 replay 结果选择特征、阈值或替代指数
```

## 2. Documents / Contracts / Skills Read

```text
docs/tw_portfolio_decision_model/POLICY_RCP3A_MARKET_FEATURE_COVERAGE_PIT_GATE_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RCP2_RISK_CONTROL_RULE_DESIGN_CONTRACT_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RCP2_RISK_CONTROL_RULE_DESIGN_CONTRACT_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RCP2_RISK_CONTROL_RULE_DESIGN_CONTRACT_WORK_CN.md
data_tw/experiments/risk_control_policy_2022/rcp2_risk_control_rule_design_contract/predeclared_rule_candidates.csv
data_tw/experiments/risk_control_policy_2022/rcp2_risk_control_rule_design_contract/feature_availability_contract.csv
data_tw/experiments/risk_control_policy_2022/rcp2_risk_control_rule_design_contract/rule_dependency_contract.csv
data_tw/experiments/risk_control_policy_2022/rcp2_risk_control_rule_design_contract/anti_overfit_and_no_2022_mining_audit.csv
data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/diagnostic_model_signal.csv
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
```

使用 workflow skill：`coordinator-executor-reviewer-workflow`。

## 3. Changes Made

生成输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate/
```

已生成全部必需文件：

```text
manifest.json
market_feature_source_inventory.csv
market_feature_coverage_audit.csv
market_feature_pit_audit.csv
market_ma_derivation_contract.json
market_feature_by_signal_date.csv
rule_market_dependency_gate.csv
missing_market_feature_policy.csv
anti_overfit_and_no_2022_feature_selection_audit.csv
diagnostic_semantics_audit.json
forbidden_action_audit.csv
validator_report.json
diagnostic_findings.md
```

## 4. Evidence Produced

核心覆盖结果：

```text
market_source = qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TWII.csv
market_source_window = 2015-01-05..2026-05-21
required_2022_signal_date_count = 246
matched_signal_date_count = 246
missing_signal_date_count = 0
ma60_available_count = 246
ma60_missing_count = 0
coverage_status = PASS
pit_status = PASS
```

MA60 合同：

```text
market_index_ma60 = rolling mean of TWII close over current and previous 59 available market rows
window = 60
min_periods = 60
uses_future_price = false
```

RCP2 market-dependent rules gate：

```text
RCP2_RULE_01 = PASS
RCP2_RULE_02 = PASS
RCP2_RULE_05 = PASS
RCP2_RULE_06 = PASS
```

非 market MA 规则：

```text
RCP2_RULE_03 = NOT_REQUIRED_PASS
RCP2_RULE_04 = NOT_REQUIRED_PASS
```

## 5. Compliance With Mainline

本轮保持 2022 语义为：

```text
strict_oos_2022 = false
diagnostic_only = true
semantic_label = downturn_validation_diagnostic_only
```

没有把 RCP3A 结果表述为 strict OOS / final OOS / independent test。

## 6. Forbidden Actions Audit

本轮未执行：

```text
baseline replay
risk-control replay
model training
strict_test
registry/default 修改
provider publish / accepted latest switch
monitor/frontend/Agent integration
broker/order/quick-trade
OrderIntent 输出
target_weight / target_position / quantity_instruction 输出
2022 replay result feature selection
future return / label usage
```

## 7. Issues / Blockers / Deviations

无阻塞。候选 TWII 数据源通过 coverage / PIT gate。

注意：RCP3 仍只能在审查者通过后进入 `Risk-control Replay Sanity` 工作文档授权范围；RCP3A 通过不授权 strict_test 或生产化。

## 8. Files Changed

```text
data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate/manifest.json
data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate/market_feature_source_inventory.csv
data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate/market_feature_coverage_audit.csv
data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate/market_feature_pit_audit.csv
data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate/market_ma_derivation_contract.json
data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate/market_feature_by_signal_date.csv
data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate/rule_market_dependency_gate.csv
data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate/missing_market_feature_policy.csv
data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate/anti_overfit_and_no_2022_feature_selection_audit.csv
data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate/diagnostic_semantics_audit.json
data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate/forbidden_action_audit.csv
data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate/validator_report.json
data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate/diagnostic_findings.md
docs/tw_portfolio_decision_model/POLICY_RCP3A_MARKET_FEATURE_COVERAGE_PIT_GATE_EXECUTION_REPORT_CN.md
```

## 9. Recommendation For Reviewer

```text
PASS_READY_FOR_RCP3_RISK_CONTROL_REPLAY_SANITY_WORK_DOC
```

若审查通过，下一步只能授权撰写/执行 RCP3 risk-control replay sanity 工作文档；不授权 strict_test 或生产化。
