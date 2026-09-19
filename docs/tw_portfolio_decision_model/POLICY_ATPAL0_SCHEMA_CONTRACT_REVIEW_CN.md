---
created_at: 2026-06-23
status: pass_ready_for_atpal1_work_doc
phase_reviewed: ATPAL0_SCHEMA_CONTRACT_FREEZE
mainline_doc: docs/tw_portfolio_decision_model/POLICY_ATPAL_ACTION_TRADE_PNL_ATTRIBUTION_LEDGER_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_ATPAL0_SCHEMA_CONTRACT_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_ATPAL0_SCHEMA_CONTRACT_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/action_trade_pnl_attribution_ledger/atpal0_contract
reviewer_role: independent_reviewer
atpal0_passed: true
atpal1_work_doc_authorized: true
atpal2_authorized: false
atpal3_authorized: false
atpal4_authorized: false
strategy_experiment_authorized: false
rule_selection_authorized: false
threshold_selection_authorized: false
strict_test_authorized: false
model_training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
---

# ATPAL0 Schema / Contract Freeze 审查意见

## 1. Verdict

审查结论：

```text
PASS_READY_FOR_ATPAL1_WORK_DOC
```

ATPAL0 已按新主线完成 schema / contract freeze：定义了 ledger table contract、field dictionary、PnL component definition、reconciliation rule contract、forbidden field audit 和 validator。未生成正式账本，未运行 ATPAL1/2/3/4，未跑策略实验、规则选择、阈值选择、strict_test、模型训练或生产链路。

因此允许 reviewer 给出 ATPAL1 Baseline Ledger Builder 工作文档。

## 2. Findings

### Critical

无 blocking finding。

### High

1. ATPAL0 必需产物齐全：

```text
manifest.json
atpal_schema_contract.md
ledger_table_contract.csv
field_dictionary.csv
reconciliation_rule_contract.csv
pnl_component_definition.csv
forbidden_field_audit.csv
validator_report.json
```

2. 四层账本合同已覆盖主线要求：

```text
trade_level_pnl_ledger
position_lifecycle_ledger
position_day_pnl_ledger
symbol_date_pnl_ledger
action_context_ledger
```

并补充了 ATPAL1 所需审计表：

```text
cash_fee_tax_ledger
baseline_summary_reconciliation
nav_reconciliation_audit
fee_tax_turnover_reconciliation_audit
missing_price_audit
forbidden_field_audit
```

3. reconciliation rule contract 覆盖 ATPAL1 必须 gate：

```text
final_equity / net_return reconciliation
fee_and_tax reconciliation
turnover reconciliation
action_count reconciliation
realized + unrealized + cash movement reconciliation
missing_price_count reconciliation
negative_cash_count reconciliation
2025 audited baseline metrics reproduction
```

4. 生产语义边界清楚。`simulated_executed_quantity` 只允许作为 replay diagnostic accounting；`quantity` 被降级为 source replay compatibility alias，推荐 ATPAL 字段为 `simulated_position_quantity`，不得作为 instruction。

5. forbidden audit 覆盖：

```text
target_weight
target_position
quantity_instruction
broker_order
OrderIntent output
provider/latest/monitor/frontend/Agent/production
strict_test
model_training
rule_selection
threshold_selection
validation_mining
future/PnL-as-rule-feature
```

### Medium

1. `pnl_component_definition.csv` 中部分 accounting component 的 sign convention 表述较泛化。ATPAL1 实作时必须在 ledger builder 中用实际 cash/NAV reconciliation 验证符号方向，不能只依赖文字说明。

2. ATPAL0 是 schema-only pass，不代表 ATPAL1 ledger builder 已可自然通过。ATPAL1 的关键风险会在 realized/unrealized/cash movement reconciliation。

### Low

1. `atpal_schema_contract.md` 是简洁版合同，详细字段主要在 CSV 中。ATPAL1 执行者必须以 CSV 字段词典和 reconciliation contract 为准。

## 3. Mainline Compliance

| Requirement | Review |
|---|---|
| 只执行 ATPAL0 schema / contract freeze | pass |
| 不生成正式账本 | pass |
| 不运行 ATPAL1/2/3/4 | pass |
| 四层账本合同定义 | pass |
| field dictionary 覆盖主线字段 | pass |
| PnL component definition 输出 | pass |
| reconciliation rule contract 输出 | pass |
| forbidden field audit 输出 | pass |
| simulated quantity 仅为 diagnostic accounting | pass |
| 禁止 target / broker / quantity instruction | pass |
| 禁止策略实验 / 规则选择 / 阈值选择 | pass |
| 禁止 strict_test / 训练 / 生产 | pass |
| 是否允许写 ATPAL1 工作文档 | pass |

## 4. Evidence Checked

审查了执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_ATPAL0_SCHEMA_CONTRACT_EXECUTION_REPORT_CN.md
```

审查了产物目录：

```text
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal0_contract/
```

审查了生成脚本：

```text
scripts/build_tw_policy_atpal0_schema_contract.py
```

脚本语法检查：

```text
python -m py_compile scripts/build_tw_policy_atpal0_schema_contract.py
```

结果：通过。

## 5. Missing Evidence Or Open Questions

ATPAL0 无需 repair。

ATPAL1 必须实证验证：

```text
1. ledger-derived final equity / net return 是否能复现 replay summary；
2. fee/tax、turnover、action_count 是否能严格对齐；
3. realized + unrealized + cash movement 是否能解释 NAV change；
4. 2025 validation baseline 是否复现已审计指标；
5. symbol-date ledger 是否足以支撑 ATPAL2 concentration audit。
```

## 6. Forbidden Actions Audit

审查未发现越权：

```text
ATPAL1/2/3/4 run = false
strategy_experiment = false
rule_selection = false
threshold_selection = false
strict_test_used = false
model_training_run = false
production_allowed = false
OrderIntent output = false
target_weight/target_position = false
quantity_instruction = false
broker_order = false
```

## 7. Next Work Document

下一步进入 ATPAL1：

```text
docs/tw_portfolio_decision_model/POLICY_ATPAL1_BASELINE_LEDGER_BUILDER_WORK_CN.md
```

ATPAL1 只允许基于可信 baseline replay 生成 train + validation 四层账本和 reconciliation audit。不得进入 ATPAL2/3/4，不得跑新策略，不得选择规则或阈值，不得 strict_test，不得训练模型，不得输出订单或生产字段。
