---
created_at: 2026-06-23
status: pass_ready_for_review
phase: CATR0_CANDIDATE_REPLAY_FEASIBILITY_CONTRACT
mainline_doc: docs/tw_portfolio_decision_model/POLICY_CATR_CANDIDATE_ATPAL_REPLAY_FEASIBILITY_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_CATR0_CANDIDATE_REPLAY_FEASIBILITY_CONTRACT_WORK_CN.md
artifact_root: data_tw/experiments/candidate_atpal_replay_feasibility/catr0_feasibility_contract
candidate_replay_run: false
candidate_pass_fail_judgement: false
strict_test_used: false
model_training_run: false
production_allowed: false
---

# CATR0 Candidate Replay Feasibility Contract 执行报告

## 1. Scope

- Assigned phase: `CATR0_CANDIDATE_REPLAY_FEASIBILITY_CONTRACT`
- Mainline document: `docs/tw_portfolio_decision_model/POLICY_CATR_CANDIDATE_ATPAL_REPLAY_FEASIBILITY_MAINLINE_CN.md`
- Work document: `docs/tw_portfolio_decision_model/POLICY_CATR0_CANDIDATE_REPLAY_FEASIBILITY_CONTRACT_WORK_CN.md`
- Non-goals confirmed: 未运行 candidate replay；未判断 candidate pass/fail；未做 FPA4 repair；未新增候选；未调阈值；未使用 strict_test；未训练模型；未触碰生产/default/order/provider/frontend/Agent。

## 2. Documents / Contracts / Skills Read

已读取：

```text
docs/tw_portfolio_decision_model/POLICY_CATR_CANDIDATE_ATPAL_REPLAY_FEASIBILITY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_CATR0_CANDIDATE_REPLAY_FEASIBILITY_CONTRACT_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_ATPAL_FINAL_CLOSURE_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_ATPAL_FINAL_COORDINATOR_NEXT_STEP_OPINION_CN.md
docs/tw_portfolio_decision_model/POLICY_ATPAL_ACTION_TRADE_PNL_ATTRIBUTION_LEDGER_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_FPA4_PREDECLARED_FULL_PATH_RULE_SANITY_REVIEW_CN.md
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal3_candidate_adapter_contract/
data_tw/experiments/full_path_action_diagnostic/fpa4_predeclared_full_path_rule_sanity/
scripts/build_tw_policy_ral_fpa4_predeclared_full_path_rule_sanity.py
scripts/run_tw_policy_action_model_pa1.py
```

并按 coordinator-executor-reviewer workflow 执行本轮单阶段工作。

## 3. Changes Made

新增 CATR0 静态 feasibility artifacts：

```text
data_tw/experiments/candidate_atpal_replay_feasibility/catr0_feasibility_contract/manifest.json
data_tw/experiments/candidate_atpal_replay_feasibility/catr0_feasibility_contract/source_artifact_manifest.json
data_tw/experiments/candidate_atpal_replay_feasibility/catr0_feasibility_contract/fpa4_candidate_inventory.csv
data_tw/experiments/candidate_atpal_replay_feasibility/catr0_feasibility_contract/candidate_replay_required_field_audit.csv
data_tw/experiments/candidate_atpal_replay_feasibility/catr0_feasibility_contract/candidate_action_lineage_feasibility_audit.csv
data_tw/experiments/candidate_atpal_replay_feasibility/catr0_feasibility_contract/candidate_atpal_output_contract_audit.csv
data_tw/experiments/candidate_atpal_replay_feasibility/catr0_feasibility_contract/candidate_replay_blocker_audit.csv
data_tw/experiments/candidate_atpal_replay_feasibility/catr0_feasibility_contract/forbidden_consumer_audit.csv
data_tw/experiments/candidate_atpal_replay_feasibility/catr0_feasibility_contract/validator_report.json
data_tw/experiments/candidate_atpal_replay_feasibility/catr0_feasibility_contract/diagnostic_findings.md
```

新增本执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_CATR0_CANDIDATE_REPLAY_FEASIBILITY_CONTRACT_EXECUTION_REPORT_CN.md
```

## 4. Evidence Produced

### 4.1 FPA4 Candidate Inventory

`fpa4_candidate_inventory.csv` 覆盖原始 5 个 candidate / 7 个 threshold version：

```text
FPA4_C01 rank_lte_25
FPA4_C01 rank_lte_50
FPA4_C02 unrealized_gain_large
FPA4_C03 unrealized_loss_large
FPA4_C04 unrealized_gain_large
FPA4_C05 holding_days_005_019
FPA4_C05 holding_days_020_059
```

候选与 FPA4 原始 `predeclared_candidate_manifest.csv` 一致。

### 4.2 Replay Logic Feasibility

静态审计确认：

```text
scripts/build_tw_policy_ral_fpa4_predeclared_full_path_rule_sanity.py
```

包含：

```text
candidate_manifest_rows()
should_intervene()
replay_candidate()
```

并且 `replay_candidate()` 复用 PA1：

```text
baseline_trade_intents
build_day_state
execute_pending
PriceStore
mark_to_market
```

因此既有 FPA4 candidate logic 可复现。CATR1 若获授权，不需要新策略、新阈值或 validation mining，只需要在同一路径中补齐 ATPAL ledger emission。

### 4.3 ATPAL3 Required Field Mapping

`candidate_replay_required_field_audit.csv` 显示：

```text
多数 required fields 可直接从 FPA4/PA1 replay path 映射；
action_trace_id、position_lifecycle_id、symbol-date PnL、cash_before 等需要 CATR1 builder instrumentation；
这些是 ledger emission 工作，不是 CATR0 blocker。
```

### 4.4 Output Contract

`candidate_atpal_output_contract_audit.csv` 确认 CATR1 若获授权应输出：

```text
candidate_trade_level_pnl_ledger.csv
candidate_position_lifecycle_ledger.csv
candidate_position_day_pnl_ledger.csv
candidate_symbol_date_pnl_ledger.csv
candidate_action_context_ledger.csv
candidate_cash_fee_tax_ledger.csv
candidate_summary_reconciliation.csv
candidate_nav_reconciliation_audit.csv
candidate_concentration_audit.csv
candidate_vs_baseline_delta_audit.csv
```

CATR0 未生成上述 ledgers。

## 5. Compliance With Mainline

本轮符合 CATR0 主线：

```text
candidate_replay_run = false
candidate_pass_fail_judgement = false
strict_test_used = false
model_training_run = false
production_allowed = false
order_intent_output = false
target_weight_output = false
target_position_output = false
quantity_instruction_output = false
broker_order_output = false
```

## 6. Forbidden Actions Audit

`forbidden_consumer_audit.csv` 显示所有禁止项均为：

```text
pass_not_allowed_not_present
```

包括：

```text
candidate replay
new strategy replay
candidate pass/fail judgement
FPA4 repair
new candidate
threshold selection
validation mining
strict_test
model training
production/default/order/provider/frontend/Agent
OrderIntent output
target_weight / target_position / quantity_instruction / broker_order
```

## 7. Issues / Blockers / Deviations

未发现阻断 CATR1 的硬 blocker。

但必须强调：

```text
FPA4 现有产物没有真实 candidate trade-level / symbol-date ledger；
不能从 summary 反推 ledger；
CATR1 必须从 replay path 重新生成 ATPAL-compatible candidate ledgers。
```

需要 CATR1 builder 补齐的主要内容：

```text
1. stable action_trace_id；
2. position_lifecycle_id；
3. per-position daily mark-to-market；
4. candidate symbol-date contribution；
5. cash_before / cash_after reconciliation；
6. candidate vs baseline delta audit；
7. candidate concentration audit inputs。
```

这些是执行工作量，不是 feasibility blocker。

## 8. Files Changed

```text
data_tw/experiments/candidate_atpal_replay_feasibility/catr0_feasibility_contract/manifest.json
data_tw/experiments/candidate_atpal_replay_feasibility/catr0_feasibility_contract/source_artifact_manifest.json
data_tw/experiments/candidate_atpal_replay_feasibility/catr0_feasibility_contract/fpa4_candidate_inventory.csv
data_tw/experiments/candidate_atpal_replay_feasibility/catr0_feasibility_contract/candidate_replay_required_field_audit.csv
data_tw/experiments/candidate_atpal_replay_feasibility/catr0_feasibility_contract/candidate_action_lineage_feasibility_audit.csv
data_tw/experiments/candidate_atpal_replay_feasibility/catr0_feasibility_contract/candidate_atpal_output_contract_audit.csv
data_tw/experiments/candidate_atpal_replay_feasibility/catr0_feasibility_contract/candidate_replay_blocker_audit.csv
data_tw/experiments/candidate_atpal_replay_feasibility/catr0_feasibility_contract/forbidden_consumer_audit.csv
data_tw/experiments/candidate_atpal_replay_feasibility/catr0_feasibility_contract/validator_report.json
data_tw/experiments/candidate_atpal_replay_feasibility/catr0_feasibility_contract/diagnostic_findings.md
docs/tw_portfolio_decision_model/POLICY_CATR0_CANDIDATE_REPLAY_FEASIBILITY_CONTRACT_EXECUTION_REPORT_CN.md
```

## 9. Recommendation For Reviewer

建议审查者结论：

```text
PASS_READY_FOR_CATR1_WORK_DOC
```

理由：

```text
CATR0 已证明既有 FPA4 candidate 可以按 ATPAL3 合同进入未来 candidate ATPAL replay builder；
但本轮没有授权也没有执行 candidate replay；
下一步只能由审查者/统筹考虑是否撰写 CATR1 工作文档。
```

最终建议：

```text
READY_FOR_REVIEWER_TO_CONSIDER_CATR1_WORK_DOC
```
