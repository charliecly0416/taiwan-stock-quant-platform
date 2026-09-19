---
created_at: 2026-06-23
status: pass_ready_for_atpal2_work_doc
phase_reviewed: ATPAL1_R_ACTION_CONTEXT_LEDGER_REPAIR
mainline_doc: docs/tw_portfolio_decision_model/POLICY_ATPAL_ACTION_TRADE_PNL_ATTRIBUTION_LEDGER_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_ATPAL1_R_ACTION_CONTEXT_LEDGER_REPAIR_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_ATPAL1_R_ACTION_CONTEXT_LEDGER_REPAIR_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair
reviewer_role: independent_reviewer
atpal1_repair_passed: true
atpal2_work_doc_authorized: true
atpal3_authorized: false
atpal4_authorized: false
strategy_experiment_authorized: false
strict_test_authorized: false
model_training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
---

# ATPAL1-R Action Context Ledger Repair 审查意见

## 1. Verdict

审查结论：

```text
PASS_READY_FOR_ATPAL2_WORK_DOC
```

ATPAL1-R 已修复上一轮两个 blocker：

```text
1. action_context_ledger 与 trade_level_pnl_ledger 的 executed action_trace_id 已 100% 直接连通；
2. sell action 的 holding_days_before / unrealized_return_before 已来自 signal_date pre-action state，覆盖率恢复到合理水平。
```

会计 reconciliation 未被破坏，且未发现 ATPAL2/3/4、策略实验、规则选择、阈值选择、strict_test、训练或生产越权。

因此允许 reviewer 给出 ATPAL2 Contribution / Concentration Audit 工作文档。

## 2. Findings

### Critical

无 blocking finding。

### High

1. action context 与 trade ledger 直接 linkage 通过：

```text
train:
  trade_action_count = 885
  context_executed_action_count = 885
  direct_linked_count = 885
  missing_context_count = 0
  orphan_context_count = 0
  linkage_rate = 1.0

validation:
  trade_action_count = 436
  context_executed_action_count = 436
  direct_linked_count = 436
  missing_context_count = 0
  orphan_context_count = 0
  linkage_rate = 1.0
```

2. sell pre-action state coverage 通过：

```text
train:
  sell_context_count = 438
  holding_days_before_positive = 397
  holding_days_positive_rate = 0.9063926941
  unrealized_return_available_rate = 1.0

validation:
  sell_context_count = 213
  holding_days_before_positive = 197
  holding_days_positive_rate = 0.9248826291
  unrealized_return_available_rate = 1.0
```

3. 抽查 `action_context_ledger.csv` 显示 executed context 的 `action_trace_id` 等于 trade ledger trace id，并新增：

```text
executed_trade_action_trace_id
executed_trade_linked
non_executed_or_skipped_intent
cost_basis_before
mark_price_before_action
pre_state_source
```

4. baseline reconciliation 仍通过：

```text
train net_return_after_fee_tax diff = 0
validation net_return_after_fee_tax diff = 0
validation fee_and_tax diff = 0
validation turnover_proxy diff = 4e-08
action_count diff = 0
missing_price_count diff = 0
negative_cash_count diff = 0
```

5. 2025 validation baseline 指标继续复现：

```text
net_return_after_fee_tax = 0.95376753
net_return_if_liquidated_at_period_end = 0.94512277
fee_and_tax = 146214.73
turnover_proxy = 42.18778217
missing_price_count = 0
negative_cash_count = 0
```

### Medium

1. `orphan_non_executed_context_count` 存在：

```text
train = 31
validation = 14
```

这些被标记为 non-executed / skipped intent，不阻塞 ATPAL1-R 通过；ATPAL2 若使用 action context，应区分 executed 与 non-executed context。

2. ATPAL2 只能对 baseline ledger 做 contribution / concentration audit，不能把 concentration 结果用于策略通过、规则筛选或阈值选择。

### Low

1. repair 输出在新目录，保留了原 ATPAL1 产物目录，便于对比审计。

## 3. Mainline Compliance

| Requirement | Review |
|---|---|
| 仍属于 ATPAL1 repair | pass |
| 不运行 ATPAL2/3/4 | pass |
| 不跑新策略 | pass |
| 不使用 strict_test | pass |
| 不训练模型/不生产集成 | pass |
| action_context pre-state 修复 | pass |
| action_context/trade direct linkage | pass |
| baseline reconciliation 保持通过 | pass |
| forbidden field audit | pass |
| 是否允许写 ATPAL2 工作文档 | pass |

## 4. Evidence Checked

审查了执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_ATPAL1_R_ACTION_CONTEXT_LEDGER_REPAIR_EXECUTION_REPORT_CN.md
```

审查了产物目录：

```text
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair/
```

重点核对：

```text
action_context_ledger.csv
action_context_linkage_audit.csv
action_context_pre_state_audit.csv
trade_level_pnl_ledger.csv
baseline_summary_reconciliation.csv
forbidden_field_audit.csv
validator_report.json
```

审查了生成脚本：

```text
scripts/build_tw_policy_atpal1_r_action_context_repair.py
```

脚本语法检查：

```text
python -m py_compile scripts/build_tw_policy_atpal1_r_action_context_repair.py
```

结果：通过。

## 5. Missing Evidence Or Open Questions

ATPAL1-R 无需继续 repair。

ATPAL2 需要补充的是 contribution / concentration audit：

```text
symbol contribution
date contribution
symbol-date contribution matrix
top contributor audit
trade PnL distribution
position lifecycle distribution
fee/tax contribution
turnover contribution
baseline concentration gate design
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

下一步进入 ATPAL2：

```text
docs/tw_portfolio_decision_model/POLICY_ATPAL2_CONTRIBUTION_AUDIT_WORK_CN.md
```

ATPAL2 只允许基于 ATPAL1-R baseline ledger 做 contribution / concentration audit。不得进入 ATPAL3/4，不得跑新策略，不得做规则选择或阈值选择，不得 strict_test，不得训练模型或触碰生产链路。
