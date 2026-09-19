---
created_at: 2026-06-23
status: reviewer_next_work_document
phase: RAL1_BASELINE_ACTION_LEDGER_BUILD_AND_PARITY
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ACTION_LEDGER_RULE_ATTRIBUTION_MAINLINE_CN.md
previous_review: docs/tw_portfolio_decision_model/POLICY_RAL0_LEDGER_CONTRACT_MAPPING_REVIEW_CN.md
previous_execution_report: docs/tw_portfolio_decision_model/POLICY_RAL0_LEDGER_CONTRACT_MAPPING_EXECUTION_REPORT_CN.md
ral0_artifact_root: data_tw/experiments/rule_attribution_ledger/ral0_contract_mapping
artifact_root: data_tw/experiments/rule_attribution_ledger/ral1_baseline_action_ledger_parity
strict_test_authorized: false
training_authorized: false
pba_attribution_authorized: false
rule_experiment_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_weight: true
not_target_position: true
not_quantity: true
---

# RAL1 Baseline Action Ledger Build And Parity 工作文档

## 1. 本轮目标

你是执行者。请继续 RAL Action-level Ledger + Rule Attribution 主线的第二步：

```text
RAL1: Baseline Action Ledger Build And Parity
```

本轮只构建 baseline 的 action-level / symbol-level / daily ledger，并证明该 ledger 能 reconciliation 到既有 PBA1 baseline replay。

本轮不是 PBA2/PBA3/PBA-RC attribution，不做新规则，不训练模型，不运行 strict_test。

## 2. 必须读取

执行前必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ACTION_LEDGER_RULE_ATTRIBUTION_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL0_LEDGER_CONTRACT_MAPPING_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL0_LEDGER_CONTRACT_MAPPING_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_MODEL_RESEARCH_ROUTE_CLOSURE_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA1_BASELINE_SNAPSHOT_BUILD_AND_PARITY_REPLAY_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
```

必须使用 RAL0 合同产物：

```text
data_tw/experiments/rule_attribution_ledger/ral0_contract_mapping/
```

必须优先使用：

```text
data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json
data_tw/experiments/baseline_anchored_active_policy/pba1_baseline_snapshot_parity_replay/baseline_action_snapshot_artifact.csv
data_tw/experiments/baseline_anchored_active_policy/pba1_baseline_snapshot_parity_replay/baseline_parity_replay_ledger.csv
data_tw/experiments/baseline_anchored_active_policy/pba1_baseline_snapshot_parity_replay/baseline_parity_metrics.csv
```

如果某个 PBA1 artifact 不存在或字段不足，必须在执行报告中明确写成缺口，不得用外部数据或 strict_test 补齐。

## 3. 授权范围

本轮只允许：

```text
1. 读取 RAL0 schema / inventory / attribution design。
2. 读取 frozen qlib signal 与 PBA1 baseline snapshot / replay ledger。
3. 构建 baseline_action_symbol_daily_ledger.csv。
4. 输出 baseline ledger parity metrics。
5. 输出 daily NAV reconciliation。
6. 输出 symbol PnL reconciliation。
7. 输出 cost / turnover reconciliation。
8. 输出 field-level availability / missing field audit。
9. 输出 forbidden consumer audit。
10. 实现或运行 RAL1 baseline validator / golden samples。
11. 写 RAL1 execution report。
```

本轮不允许：

```text
1. 训练模型、深度学习、强化学习、bandit 或任意 policy。
2. 新增规则或调参。
3. 运行 PBA2/PBA3/PBA3-R/PBA-RC attribution。
4. 运行收益规则实验。
5. 运行或读取 strict_test。
6. 输出 OrderIntent。
7. 输出 target_weight / target_position / quantity / order_size / broker_order。
8. provider publish / accepted latest switch。
9. monitor write / frontend default / Agent recommendation。
10. broker / quick-trade / real order。
11. 修改 production/default 策略。
12. 抓取新外部数据或切换数据源。
```

## 4. 数据窗口

本轮只允许使用 RAL 主线声明的 analysis 窗口：

```text
analysis train = 2023-01-01..2024-12-31
analysis validation = 2025-01-01..2025-12-31
strict_test = 2026-01-01..2026-05-07, declared only, not used
```

输出可以分 train / validation，但不得读取、计算、输出 strict_test 指标。

## 5. 必须输出产物

artifact root：

```text
data_tw/experiments/rule_attribution_ledger/ral1_baseline_action_ledger_parity/
```

必须输出：

```text
manifest.json
baseline_action_symbol_daily_ledger.csv
baseline_ledger_parity_metrics.csv
daily_nav_reconciliation.csv
symbol_pnl_reconciliation.csv
cost_turnover_reconciliation.csv
field_availability_audit.csv
feature_available_at_audit.csv
forbidden_consumer_audit.csv
validator_report.json
golden_samples_report.json
```

必须写执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RAL1_BASELINE_ACTION_LEDGER_BUILD_AND_PARITY_EXECUTION_REPORT_CN.md
```

## 6. Baseline Ledger 要求

`baseline_action_symbol_daily_ledger.csv` 必须遵守 RAL0 schema：

```text
artifact_type = ActionSymbolDailyLedgerArtifact
schema_version = ral_action_symbol_daily_ledger_v1
粒度 = date x symbol x action_source x action_type
```

每行至少必须包含：

```text
date
symbol
action_source
action_type
baseline_action_type
policy_or_rule_action_type
rank
score
holding_before_diagnostic
holding_after_diagnostic
cash_before_diagnostic
cash_after_diagnostic
turnover_contribution
fee_contribution
sell_tax_contribution
gross_pnl_contribution
realized_pnl_contribution
unrealized_pnl_contribution
net_pnl_after_fee_tax_contribution
nav_contribution
holding_age
reason_code
source_signal_artifact
source_replay_artifact
missing_field_status
simulation_only
readonly_research_only
production_allowed
```

baseline ledger 中：

```text
action_source 必须等于 baseline。
policy_or_rule_action_type 应为空值语义或 no_extra_action，但不得被解释为 active edge。
diagnostic shares/notional 字段若输出，必须只用于 replay reconstruction，不得映射为 OrderIntent quantity。
```

## 7. PnL / Cost / Turnover Attribution 口径

RAL1 必须明确每个贡献字段的来源：

```text
native
derived_proxy
not_available_in_current_replay
requires_future_data_contract
```

必须输出 `field_availability_audit.csv`，至少包含：

```text
field
availability_status
source_artifact
derivation_method
can_reconcile_to_replay
used_for_primary_metric
notes
```

严禁：

```text
1. 把缺失的 PnL/cost/turnover/cash/price/shares/notional 默认填 0 后标为 native。
2. 把 portfolio-level net_return 直接平均或按行数分配成 symbol PnL 后标为 native。
3. 把 gross_return 当 primary。
4. 用 cash/no-trade 或低成本低换手替代 net return parity。
```

如果只能做 proxy attribution，必须明确写入：

```text
derived_proxy
```

并说明 proxy 是否足以通过 RAL1。若不足以 reconciliation，必须 STOP。

## 8. Reconciliation 要求

`daily_nav_reconciliation.csv` 至少包含：

```text
date
split
pba1_cash_before
pba1_cash_after
pba1_daily_net_return_after_fee_tax
ral1_net_pnl_after_fee_tax_sum
pba1_equity_or_nav
ral1_reconstructed_equity_or_nav
absolute_diff
relative_diff
status
```

`cost_turnover_reconciliation.csv` 至少包含：

```text
date
split
pba1_fee
ral1_fee_sum
pba1_sell_tax
ral1_sell_tax_sum
pba1_turnover
ral1_turnover_sum
fee_diff
sell_tax_diff
turnover_diff
status
```

`symbol_pnl_reconciliation.csv` 至少包含：

```text
split
symbol
gross_pnl_sum
realized_pnl_sum
unrealized_pnl_sum
net_pnl_after_fee_tax_sum
availability_status
source_or_derivation
status
```

`baseline_ledger_parity_metrics.csv` 至少包含：

```text
split
start_date
end_date
daily_nav_reconciliation_status
net_pnl_reconciliation_status
fee_reconciliation_status
sell_tax_reconciliation_status
turnover_reconciliation_status
symbol_pnl_reconstruction_status
overall_status
```

通过条件：

```text
overall_status = pass
```

如果 daily NAV path、fee、sell_tax、turnover、net PnL 无法 reconcile，必须 STOP，不得进入 RAL2。

## 9. Available-at / PIT Audit

`feature_available_at_audit.csv` 必须覆盖 baseline ledger 使用的全部输入：

```text
rank
score
baseline_action_type
holding_before_diagnostic
holding_after_diagnostic
holding_age
cash
price input if used
cost model input if used
turnover input if used
```

必须证明：

```text
1. 没有 future_return。
2. 没有 label。
3. 没有 future price。
4. 没有 realized_pnl as feature。
5. 没有 strict_test metric。
6. 没有 validation metric used for rule/model selection。
```

## 10. Validator / Golden Samples

RAL1 必须输出 `validator_report.json`，至少检查：

```text
required fields exist
primary key no duplicates
enum fields valid
simulation_only=true
readonly_research_only=true
production_allowed=false
strict_test_used=false
training_run=false
forbidden fields absent
missing numeric contribution fields are not silently filled with zero
daily NAV reconciliation pass
fee/sell_tax/turnover reconciliation pass
no OrderIntent/quantity/target fields
```

RAL1 必须输出 `golden_samples_report.json`，至少覆盖：

```text
positive_baseline_buy_row
positive_baseline_sell_row_or_sell_candidate_row
positive_baseline_hold_row
negative_forbidden_quantity_field
negative_production_allowed_true
negative_missing_pnl_filled_zero_as_native
negative_strict_test_source
negative_duplicate_primary_key
```

## 11. Forbidden Consumer Audit

`forbidden_consumer_audit.csv` 必须确认以下字段或消费者没有进入 ledger / manifest / validator output 的可消费语义：

```text
target_weight
target_position
quantity
order_size
broker_order
production_order_id
broker_order_id
quick_trade
provider_publish_status
accepted_latest_status
monitor_config_write_status
frontend_default_switch
agent_recommendation
future_return
forward_return
label
```

这些词只允许作为 forbidden audit label 或报告中的禁止项出现。

## 12. 执行报告要求

执行报告必须明确回答：

```text
1. RAL1 是否只构建 baseline ledger。
2. ledger 粒度是否为 date x symbol x action_source x action_type。
3. baseline ledger 是否能 reconcile 到 PBA1 replay daily NAV path。
4. fee / sell tax / turnover 是否能 reconcile。
5. symbol-level PnL 是 native、derived_proxy，还是无法安全还原。
6. 是否存在缺失字段被默认填 0 的情况。
7. 是否没有训练、没有 strict_test、没有新规则、没有 PBA attribution。
8. 是否没有 OrderIntent / target_weight / target_position / quantity。
9. 是否允许进入 RAL2。
```

## 13. 停止条件

出现以下任一情况必须 STOP 回到统筹：

```text
1. baseline_action_symbol_daily_ledger.csv 无法按 RAL0 schema 生成。
2. daily NAV path 无法 reconcile 到 PBA1 replay。
3. fee / sell_tax / turnover 无法 reconcile。
4. net_pnl_after_fee_tax_contribution 无法形成可审计口径。
5. 关键 PnL/cost/turnover 字段只能靠伪造或无依据分摊。
6. 需要 strict_test 才能补齐字段。
7. 执行者请求训练、规则实验、PBA attribution 或 production。
```

## 14. 下一步 Gate

只有 RAL1 审查通过后，才允许由审查者另行撰写：

```text
RAL2: Action Attribution For Existing PBA Evidence
```

RAL1 执行报告不得自行授权 RAL2。
