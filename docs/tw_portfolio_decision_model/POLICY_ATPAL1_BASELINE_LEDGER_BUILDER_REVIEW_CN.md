---
created_at: 2026-06-23
status: fail_needs_atpal1_action_context_repair
phase_reviewed: ATPAL1_BASELINE_LEDGER_BUILDER
mainline_doc: docs/tw_portfolio_decision_model/POLICY_ATPAL_ACTION_TRADE_PNL_ATTRIBUTION_LEDGER_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_ATPAL1_BASELINE_LEDGER_BUILDER_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_ATPAL1_BASELINE_LEDGER_BUILDER_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_baseline_ledger
reviewer_role: independent_reviewer
atpal1_reconciliation_passed: true
atpal1_action_context_passed: false
atpal2_authorized: false
atpal3_authorized: false
atpal4_authorized: false
strategy_experiment_authorized: false
strict_test_authorized: false
model_training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
---

# ATPAL1 Baseline Ledger Builder 审查意见

## 1. Verdict

审查结论：

```text
FAIL_NEEDS_ATPAL1_ACTION_CONTEXT_REPAIR
```

本轮 ATPAL1 的 replay summary reconciliation、fee/tax、turnover、action_count、missing price、negative cash 等主会计指标均通过，且未发现策略实验、strict_test、训练或生产越权。

但 `action_context_ledger.csv` 未满足 ATPAL 主线对 action 前状态的合同要求：sell action 的 `holding_days_before` / `unrealized_return_before` 几乎全部为空或 0，且 `action_trace_id` 与 trade ledger 不可直接连通。ATPAL 是 action / trade PnL attribution ledger，action context 层不能缺失或失真。

因此不能进入 ATPAL2，必须先做 ATPAL1 repair。

## 2. Findings

### Critical

1. `action_context_ledger.csv` 的 sell pre-action holding context 系统性失真。

审查统计：

```text
action_context rows = 1366
sell context rows = 654
sell rows with holding_days_before > 0 = 2
sell rows with unrealized_return_before != 0 = 85
```

分 split：

```text
train sell rows = 439
train holding_days_before > 0 = 1

validation sell rows = 215
validation holding_days_before > 0 = 1
```

对于 baseline sell action，绝大多数卖出都应发生在已有持仓上；`holding_days_before` 几乎全为 0 不可信。这说明 action context 不是按 signal_date 的 pre-action portfolio state 构建。

2. `action_trace_id` 无法直接把 `action_context_ledger` 连到 `trade_level_pnl_ledger`。

审查统计：

```text
trade action_trace_id count = 1321
context action_trace_id count = 1366
direct intersection = 0
```

虽然可以用 `(split, signal_date/date, instrument, action_type)` 间接匹配 1321 个 executed trade key，但主线要求 action / trade / PnL attribution ledger 支持明确映射。当前 `action_trace_id` 命名不一致会削弱后续 candidate/action attribution。

### High

1. 会计 reconciliation 本身通过：

```text
train net_return_after_fee_tax diff = 0
validation net_return_after_fee_tax diff = 0
validation fee_and_tax diff = 0
validation turnover_proxy diff = 4e-08
action_count diff = 0
missing_price_count diff = 0
negative_cash_count diff = 0
```

2. 2025 validation baseline 指标复现：

```text
net_return_after_fee_tax = 0.95376753
net_return_if_liquidated_at_period_end = 0.94512277
fee_and_tax = 146214.73
turnover_proxy = 42.18778217
missing_price_count = 0
negative_cash_count = 0
```

3. ledger row counts 符合执行报告：

```text
trade_level_pnl_ledger = 1321
position_lifecycle_ledger = 670
position_day_pnl_ledger = 6093
symbol_date_pnl_ledger = 6744
action_context_ledger = 1366
cash_fee_tax_ledger = 723
```

4. lifecycle 引用完整：

```text
trade lifecycle ids missing in lifecycle ledger = 0
position_day lifecycle ids missing in lifecycle ledger = 0
```

### Medium

1. `symbol_date_pnl_ledger.csv` 已能提供 symbol-date contribution 基础，但 action context 失真会影响后续 action-space attribution 和 ATPAL3 candidate adapter 复用。因此不能带着该缺陷进入 ATPAL2。

2. validator 当前没有检查：

```text
sell_context_holding_days_before_nonzero_coverage
sell_context_unrealized_return_before_coverage
action_trace_id_direct_linkage_between_context_and_trade
action_context_built_from_pre_action_state
```

这导致 `validator_report.json` 通过过宽。

### Low

1. `quantity` 字段未作为 instruction 输出；使用的是 `simulated_executed_quantity` / `simulated_position_quantity`，符合 ATPAL0 边界。

## 3. Mainline Compliance

| Requirement | Review |
|---|---|
| 只执行 ATPAL1 baseline ledger | pass |
| 不运行 ATPAL2/3/4 | pass |
| 不使用 strict_test | pass |
| 不做策略实验/规则选择/阈值选择 | pass |
| 不训练模型/不生产集成 | pass |
| trade ledger built | pass |
| position lifecycle ledger built | pass |
| position day ledger built | pass |
| symbol-date ledger built | pass |
| action context ledger built | fail: content invalid for sell pre-action state |
| baseline reconciliation | pass |
| fee/tax turnover reconciliation | pass |
| action trace linkage | fail: no direct action_trace_id intersection |
| 是否可进入 ATPAL2 | fail, 不允许 |

## 4. Evidence Checked

审查了执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_ATPAL1_BASELINE_LEDGER_BUILDER_EXECUTION_REPORT_CN.md
```

审查了产物目录：

```text
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_baseline_ledger/
```

重点核对：

```text
trade_level_pnl_ledger.csv
position_lifecycle_ledger.csv
position_day_pnl_ledger.csv
symbol_date_pnl_ledger.csv
action_context_ledger.csv
cash_fee_tax_ledger.csv
baseline_summary_reconciliation.csv
nav_reconciliation_audit.csv
fee_tax_turnover_reconciliation_audit.csv
missing_price_audit.csv
forbidden_field_audit.csv
validator_report.json
manifest.json
```

审查了生成脚本：

```text
scripts/build_tw_policy_atpal1_baseline_ledger.py
```

脚本语法检查：

```text
python -m py_compile scripts/build_tw_policy_atpal1_baseline_ledger.py
```

结果：通过。

## 5. Missing Evidence Or Open Questions

必须补 ATPAL1 repair：

```text
1. action_context_ledger 必须从每个 signal_date 的 pre-action portfolio state 构建；
2. sell action 的 holding_days_before / unrealized_return_before 必须反映卖出前持仓；
3. action_context_ledger 与 trade_level_pnl_ledger 必须有直接可追溯 linkage；
4. validator 必须新增 action context coverage / linkage checks；
5. 修复后重新输出 ATPAL1 ledger 与 execution report。
```

## 6. Forbidden Actions Audit

审查未发现越权：

```text
ATPAL2/3/4 run = false
strategy_experiment_run = false
rule_selection_run = false
threshold_selection_run = false
strict_test_used = false
model_training_run = false
production_allowed = false
OrderIntent output = false
target_weight/target_position = false
quantity_instruction = false
broker_order = false
```

## 7. Next Work Document

下一步仍是 ATPAL1 repair，不是 ATPAL2：

```text
docs/tw_portfolio_decision_model/POLICY_ATPAL1_R_ACTION_CONTEXT_LEDGER_REPAIR_WORK_CN.md
```
