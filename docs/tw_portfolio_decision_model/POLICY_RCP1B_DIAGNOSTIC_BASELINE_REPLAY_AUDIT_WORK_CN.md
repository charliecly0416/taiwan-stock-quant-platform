---
created_at: 2026-06-24
status: work_order_for_rcp1b_diagnostic_baseline_replay_audit
phase: RCP1B_DIAGNOSTIC_BASELINE_REPLAY_AUDIT
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RCP_RISK_CONTROL_POLICY_2022_DOWNTURN_MAINLINE_CN.md
rcp1a_review: docs/tw_portfolio_decision_model/POLICY_RCP1A_DIAGNOSTIC_SIGNAL_ADAPTER_CONTRACT_REVIEW_CN.md
input_signal_manifest: data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/diagnostic_signal_adapter_manifest.json
input_signal: data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/diagnostic_model_signal.csv
output_root: data_tw/experiments/risk_control_policy_2022/rcp1b_diagnostic_baseline_replay_audit
execution_report: docs/tw_portfolio_decision_model/POLICY_RCP1B_DIAGNOSTIC_BASELINE_REPLAY_AUDIT_EXECUTION_REPORT_CN.md
review_report: docs/tw_portfolio_decision_model/POLICY_RCP1B_DIAGNOSTIC_BASELINE_REPLAY_AUDIT_REVIEW_CN.md
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

# RCP1B 2022 Diagnostic Baseline Replay Audit 工作文档

## 1. 本轮定位

本轮执行：

```text
RCP1B: 2022 Diagnostic Baseline Replay Audit
```

目标是基于 RCP1A 已合同化的 diagnostic-only qlib signal，在 2022 下跌年诊断窗口中回放 baseline rule，建立后续 RCP2/RCP3 风险控制研究的对照基线。

本轮只做：

```text
baseline replay audit
signal/price/execution alignment audit
NAV / action / position / fee-tax / turnover accounting audit
risk metric summary
forbidden action audit
```

本轮不做：

```text
risk-control policy
规则设计
阈值选择
2022 threshold mining
模型训练
strict_test
生产/default/provider/frontend/Agent/订单链路集成
```

## 2. 必须读取

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RCP_RISK_CONTROL_POLICY_2022_DOWNTURN_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RCP1A_DIAGNOSTIC_SIGNAL_ADAPTER_CONTRACT_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RCP1A_DIAGNOSTIC_SIGNAL_ADAPTER_CONTRACT_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RCP1A_DIAGNOSTIC_SIGNAL_ADAPTER_CONTRACT_REVIEW_CN.md
data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/diagnostic_signal_adapter_manifest.json
data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/validator_report.json
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
```

可以复用既有 readonly replay accounting 代码，但必须在报告中说明复用路径和输入替换。

## 3. 输入

输入信号：

```text
data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/diagnostic_model_signal.csv
```

输入信号必须映射为 replay engine 所需字段：

```text
candidate_rank = rank
buy_score = score
raw_score = raw_score
score_rank = rank
full_qlib_rank = rank
signal_asof = signal_date
available_at = signal_date
```

回放窗口：

```text
2022-01-01..2022-12-31
```

实际信号覆盖由输入决定，预期：

```text
2022-01-03..2022-12-30
```

baseline rule：

```text
top50_exit_one_worst_sell
```

执行价口径：

```text
next open
```

若缺失 next open：

```text
必须 skip / audit，不得 fallback 到 next_close、signal close、0、空值、上一日价格或手写价格。
```

## 4. 输出目录

所有产物写入：

```text
data_tw/experiments/risk_control_policy_2022/rcp1b_diagnostic_baseline_replay_audit/
```

执行报告写入：

```text
docs/tw_portfolio_decision_model/POLICY_RCP1B_DIAGNOSTIC_BASELINE_REPLAY_AUDIT_EXECUTION_REPORT_CN.md
```

## 5. 必须输出文件

必须输出：

```text
manifest.json
baseline_replay_source_manifest.json
baseline_summary.csv
baseline_nav.csv
baseline_actions.csv
baseline_position_snapshots.csv
coverage_audit.csv
price_alignment_audit.csv
execution_audit.csv
fee_tax_turnover_audit.csv
risk_metric_summary.csv
cash_no_trade_audit.csv
diagnostic_semantics_audit.json
forbidden_consumer_audit.csv
validator_report.json
diagnostic_findings.md
```

## 6. 指标要求

`baseline_summary.csv` 至少包含：

```text
window
model_id
model_family
strategy_rule
start_date
end_date
initial_cash
final_equity
net_return_after_fee_tax
gross_return
max_drawdown
action_count
buy_count
sell_count
skipped_action_count
turnover_proxy
fee_and_tax
max_holding_count
negative_cash_count
missing_price_count
diagnostic_only
strict_oos
semantic_label
```

`risk_metric_summary.csv` 至少包含：

```text
net_return_after_fee_tax
gross_return
max_drawdown
drawdown_duration
worst_month_return
monthly_win_rate
downside_volatility
calmar_like_ratio
average_cash_rate
max_cash_rate
participation_rate
average_holding_count
max_holding_count
action_count
buy_count
sell_count
turnover_proxy
fee_and_tax
```

## 7. 审计要求

必须审计：

```text
1. RCP1A adapter validator pass；
2. 2022 signal coverage；
3. price next_open alignment；
4. execution_date > signal_date；
5. fee/tax/turnover 非负且可解释；
6. no all-cash / no-trade 伪基线；
7. negative cash count；
8. forbidden fields/actions；
9. diagnostic-only 语义。
```

## 8. validator_report.json

必须包含：

```text
phase
status
pass
rcp1a_validator_pass
input_signal_exists
baseline_replay_completed
summary_status
coverage_status
price_alignment_status
execution_status
fee_tax_turnover_status
cash_no_trade_status
diagnostic_semantics_status
forbidden_actions_status
risk_control_replay_performed
strict_test_performed
model_training_performed
rcp2_authorizable
recommended_next_step
```

允许的 `recommended_next_step`：

```text
PASS_READY_FOR_RCP2_RISK_CONTROL_RULE_DESIGN_CONTRACT_WORK_DOC
FAIL_NEEDS_RCP1B_REPAIR
STOP_BASELINE_REPLAY_INVALID
```

## 9. 审查 gate

RCP1B 通过条件：

```text
1. RCP1A validator pass；
2. baseline replay 成功完成；
3. 输出全部必需文件；
4. coverage / price alignment / execution / fee-tax / cash-no-trade audit 通过；
5. 2022 仍被标记为 diagnostic-only；
6. 未触碰 forbidden actions；
7. validator_report 推荐进入 RCP2。
```

RCP1B 通过只授权进入 RCP2 rule design contract，不授权直接运行 risk-control replay。

## 10. 第一执行者指令

```text
请按 docs/tw_portfolio_decision_model/POLICY_RCP1B_DIAGNOSTIC_BASELINE_REPLAY_AUDIT_WORK_CN.md 执行 RCP1B。
只做 2022 diagnostic baseline replay audit，不做 risk-control policy，不训练，不 strict_test，不改 registry/default/provider/frontend/Agent/订单链路。
完成后输出 data_tw/experiments/risk_control_policy_2022/rcp1b_diagnostic_baseline_replay_audit/ 下全部必需文件，并提交执行报告。
```

## 11. 第一审查者指令

```text
请按 docs/tw_portfolio_decision_model/POLICY_RCP1B_DIAGNOSTIC_BASELINE_REPLAY_AUDIT_WORK_CN.md 审查 RCP1B 产物。
重点审查 baseline replay 是否消费 RCP1A adapter、会计与价格对齐是否可信、是否仍是 diagnostic-only、是否未越权进入 risk-control replay。
通过后只授权写 RCP2 risk-control rule design contract 工作文档。
```
