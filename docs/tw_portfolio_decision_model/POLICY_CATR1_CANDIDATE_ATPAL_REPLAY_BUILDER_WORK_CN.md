---
created_at: 2026-06-23
status: coordinator_work_doc
phase: CATR1_CANDIDATE_ATPAL_REPLAY_BUILDER
mainline_doc: docs/tw_portfolio_decision_model/POLICY_CATR_CANDIDATE_ATPAL_REPLAY_FEASIBILITY_MAINLINE_CN.md
previous_review: docs/tw_portfolio_decision_model/POLICY_CATR0_CANDIDATE_REPLAY_FEASIBILITY_CONTRACT_REVIEW_CN.md
artifact_root: data_tw/experiments/candidate_atpal_replay_feasibility/catr1_candidate_atpal_replay_builder
candidate_replay_authorized: true
candidate_pass_fail_authorized: false
strategy_search_authorized: false
threshold_selection_authorized: false
strict_test_authorized: false
model_training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
---

# CATR1 Candidate ATPAL Replay Builder 工作文档

## 1. 授权范围

CATR0 审查结论为：

```text
PASS_READY_FOR_CATR1_WORK_DOC
```

本轮授权 CATR1：

```text
为既有 FPA4 失败候选生成 ATPAL-compatible candidate ledgers。
```

本轮仍然不是策略修复，不允许 candidate pass/fail，不改变 FPA4 原始结论。

## 2. 必读文档与产物

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_CATR_CANDIDATE_ATPAL_REPLAY_FEASIBILITY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_CATR0_CANDIDATE_REPLAY_FEASIBILITY_CONTRACT_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_CATR0_CANDIDATE_REPLAY_FEASIBILITY_CONTRACT_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_CATR1_CANDIDATE_ATPAL_REPLAY_BUILDER_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_ATPAL_ACTION_TRADE_PNL_ATTRIBUTION_LEDGER_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_FPA4_PREDECLARED_FULL_PATH_RULE_SANITY_REVIEW_CN.md
data_tw/experiments/candidate_atpal_replay_feasibility/catr0_feasibility_contract/
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair/
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal2_contribution_audit/
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal3_candidate_adapter_contract/
data_tw/experiments/full_path_action_diagnostic/fpa4_predeclared_full_path_rule_sanity/
scripts/build_tw_policy_ral_fpa4_predeclared_full_path_rule_sanity.py
scripts/run_tw_policy_action_model_pa1.py
```

## 3. 输出目录

```text
data_tw/experiments/candidate_atpal_replay_feasibility/catr1_candidate_atpal_replay_builder/
```

## 4. 必须输出文件

```text
manifest.json
source_artifact_manifest.json
candidate_replay_summary.csv
candidate_trade_level_pnl_ledger.csv
candidate_position_lifecycle_ledger.csv
candidate_position_day_pnl_ledger.csv
candidate_symbol_date_pnl_ledger.csv
candidate_action_context_ledger.csv
candidate_vs_baseline_delta_summary.csv
candidate_concentration_audit.csv
candidate_reconciliation_audit.csv
candidate_lineage_audit.csv
forbidden_consumer_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_CATR1_CANDIDATE_ATPAL_REPLAY_BUILDER_EXECUTION_REPORT_CN.md
```

## 5. Candidate 范围

只能覆盖既有 FPA4 原始候选：

```text
FPA4_C01 / rank_lte_25
FPA4_C01 / rank_lte_50
FPA4_C02 / unrealized_gain_large
FPA4_C03 / unrealized_loss_large
FPA4_C04 / unrealized_gain_large
FPA4_C05 / holding_days_005_019
FPA4_C05 / holding_days_020_059
```

不得新增 candidate，不得新增 threshold version。

## 6. 允许执行什么

允许：

```text
1. 复用 FPA4 candidate decision logic。
2. 复用 PA1 readonly replay path。
3. 生成 candidate trade / position / symbol-date / action-context ledgers。
4. 对齐 baseline ATPAL1-R ledger。
5. 计算 candidate-vs-baseline delta summary。
6. 计算 candidate concentration metrics。
7. 计算 reconciliation audit。
```

注意：

```text
candidate replay 是只读 simulation replay；
candidate_id 是 diagnostic research id；
PnL 字段是 attribution label；
simulated_executed_quantity 只允许作为 replay accounting。
```

## 7. 禁止事项

严禁：

```text
1. candidate pass/fail judgement。
2. FPA4 repair。
3. 改变 STOP_NO_PREDECLARED_RULE_SANITY_PASS 结论。
4. 新增候选。
5. 调整阈值。
6. validation mining。
7. strict_test。
8. 模型训练。
9. 生产/default/order/provider/frontend/Agent 集成。
10. OrderIntent output。
11. target_weight / target_position / quantity_instruction / broker_order。
```

`candidate_replay_summary.csv` 可以包含收益、成本、换手、集中度指标，但字段不得命名为 `candidate_pass`、`selected`、`approved`、`production_ready`。

## 8. Reconciliation 要求

每个 candidate / threshold / split 必须检查：

```text
1. trade action_count 与 replay summary 一致；
2. fee/tax sum 与 replay summary 一致；
3. turnover_proxy 可由 trade ledger 复算；
4. final_equity / net_return 可由 NAV 或 position-day ledger reconciliation；
5. missing_price_count 与 replay summary 一致；
6. negative_cash_count 与 replay summary 一致；
7. candidate_id / action_trace_id 可对齐。
```

如果无法完整 reconciliation，必须在 `candidate_reconciliation_audit.csv` 标记 fail，并在 `validator_report.json` failed_count 中体现。

## 9. Concentration 要求

`candidate_concentration_audit.csv` 必须至少包含：

```text
candidate_id
threshold_version
split
top1_symbol_contribution_share
top3_symbol_contribution_share
top1_date_contribution_share
top5_date_contribution_share
top1_symbol_date_contribution_share
top10_symbol_date_contribution_share
contribution_hhi
positive_contribution_symbol_count
negative_contribution_symbol_count
top_abs_trade_share
top_abs_lifecycle_share
fee_tax_share_of_total_abs_contribution
turnover_proxy
baseline_reference_top1_symbol_contribution_share
baseline_reference_top10_symbol_date_contribution_share
diagnostic_only
not_candidate_pass_fail
```

本轮只输出指标，不做通过/失败判断。

## 10. Validator 要求

`validator_report.json` 必须包含：

```text
ok
status
final_recommendation
candidate_replay_run = true
candidate_scope_matches_fpa4 = true
new_candidate_added = false
threshold_adjustment = false
candidate_pass_fail_judgement = false
strict_test_used = false
model_training_run = false
production_allowed = false
order_intent_output = false
target_weight_output = false
target_position_output = false
quantity_instruction_output = false
broker_order_output = false
reconciliation_pass
candidate_symbol_date_available
failed_count
checks
```

推荐 `final_recommendation` 只能是：

```text
READY_FOR_REVIEWER_TO_AUDIT_CANDIDATE_ATPAL_LEDGERS
FAIL_CATR1_RECONCILIATION
FAIL_CATR1_SCOPE_OR_FORBIDDEN_ACTION
```

## 11. 审查要求

审查者必须检查：

```text
1. 是否只覆盖原 FPA4 candidates。
2. 是否生成 candidate trade / position / symbol-date / action-context ledgers。
3. 是否存在真实 candidate symbol-date attribution。
4. 是否与 baseline ATPAL ledger 可对齐。
5. 是否 reconciliation 通过。
6. 是否未做 candidate pass/fail。
7. 是否未新增候选或调阈值。
8. 是否未使用 strict_test、训练或生产字段。
```

审查结论只能是：

```text
PASS_CANDIDATE_ATPAL_LEDGERS_READY_FOR_ANALYSIS
FAIL_NEEDS_REPAIR
STOP_CATR1_SCOPE_VIOLATION
```

即使 PASS，也不代表任何 candidate 通过策略 gate；只代表 candidate ATPAL ledgers 可用于后续统筹分析。
