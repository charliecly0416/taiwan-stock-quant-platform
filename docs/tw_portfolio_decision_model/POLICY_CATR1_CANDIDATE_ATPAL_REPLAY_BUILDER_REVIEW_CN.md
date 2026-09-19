---
created_at: 2026-06-23
status: review_complete
phase: CATR1_CANDIDATE_ATPAL_REPLAY_BUILDER
mainline_doc: docs/tw_portfolio_decision_model/POLICY_CATR_CANDIDATE_ATPAL_REPLAY_FEASIBILITY_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_CATR1_CANDIDATE_ATPAL_REPLAY_BUILDER_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_CATR1_CANDIDATE_ATPAL_REPLAY_BUILDER_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/candidate_atpal_replay_feasibility/catr1_candidate_atpal_replay_builder
verdict: PASS_CANDIDATE_ATPAL_LEDGERS_READY_FOR_ANALYSIS
candidate_pass_fail_authorized: false
strict_test_authorized: false
production_allowed: false
---

# CATR1 Candidate ATPAL Replay Builder 审查报告

## 1. 审查结论

```text
PASS_CANDIDATE_ATPAL_LEDGERS_READY_FOR_ANALYSIS
```

执行者完成了 CATR1 授权范围内的工作：只为既有 FPA4 失败候选生成 ATPAL-compatible candidate ledgers，并输出 reconciliation / lineage / forbidden audit。未发现新增候选、调阈值、candidate pass/fail judgement、strict_test、训练或生产化行为。

这个 PASS 只表示 candidate ATPAL ledgers 可进入后续分析；不代表任何 candidate 通过策略 gate，也不改变 FPA4 原始失败结论。

## 2. 审查范围

已核查：

```text
docs/tw_portfolio_decision_model/POLICY_CATR_CANDIDATE_ATPAL_REPLAY_FEASIBILITY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_CATR1_CANDIDATE_ATPAL_REPLAY_BUILDER_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_CATR1_CANDIDATE_ATPAL_REPLAY_BUILDER_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_CATR0_CANDIDATE_REPLAY_FEASIBILITY_CONTRACT_REVIEW_CN.md
data_tw/experiments/candidate_atpal_replay_feasibility/catr0_feasibility_contract/
data_tw/experiments/candidate_atpal_replay_feasibility/catr1_candidate_atpal_replay_builder/
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal3_candidate_adapter_contract/
data_tw/experiments/full_path_action_diagnostic/fpa4_predeclared_full_path_rule_sanity/
scripts/build_tw_policy_catr1_candidate_atpal_replay_builder.py
```

## 3. Artifact 完整性

必需 15 个 artifacts 均存在：

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

核心 ledger 非空：

```text
candidate_replay_summary.csv: 14 rows
candidate_trade_level_pnl_ledger.csv: 7249 rows
candidate_position_lifecycle_ledger.csv: 3689 rows
candidate_position_day_pnl_ledger.csv: 45438 rows
candidate_symbol_date_pnl_ledger.csv: 48998 rows
candidate_action_context_ledger.csv: 9691 rows
```

## 4. Candidate 范围审查

通过。

`candidate_replay_summary.csv` 覆盖 5 个 candidate / 7 个 threshold version / 2 个 split，共 14 行：

```text
FPA4_C01 / rank_lte_25 / train, validation
FPA4_C01 / rank_lte_50 / train, validation
FPA4_C02 / unrealized_gain_large / train, validation
FPA4_C03 / unrealized_loss_large / train, validation
FPA4_C04 / unrealized_gain_large / train, validation
FPA4_C05 / holding_days_005_019 / train, validation
FPA4_C05 / holding_days_020_059 / train, validation
```

该范围与 CATR0 的 `fpa4_candidate_inventory.csv` 一致，未发现新增 candidate 或新增 threshold version。

## 5. Ledger 与 Symbol-date 可用性

通过。

已生成以下五类 candidate ATPAL ledger：

```text
candidate_trade_level_pnl_ledger.csv
candidate_position_lifecycle_ledger.csv
candidate_position_day_pnl_ledger.csv
candidate_symbol_date_pnl_ledger.csv
candidate_action_context_ledger.csv
```

`candidate_symbol_date_pnl_ledger.csv` 不是空壳文件：

```text
rows = 48998
candidate-threshold-split pairs = 14
unique dates = 721
unique symbols = 140
nonzero net_symbol_date_contribution rows = 47351
```

因此 `candidate_symbol_date_available = true` 有实质证据支持。

## 6. Reconciliation 审查

通过。

`candidate_reconciliation_audit.csv` 共 98 行，即：

```text
14 candidate-threshold-split pairs * 7 metrics
```

每个 pair 检查：

```text
action_count
fee_and_tax
turnover_proxy
final_equity
net_return_after_fee_tax
missing_price_count
negative_cash_count
```

审查结果：

```text
status 全部为 pass
absolute_diff 全部为 0
failed cells = 0
validator_report.json: reconciliation_pass = true
validator_report.json: failed_count = 0
```

这说明 ledger-derived value 与 replay summary 在 CATR1 要求的核对项上完全一致。

## 7. Lineage 审查

通过。

`candidate_lineage_audit.csv` 显示 7 个 threshold version 均满足：

```text
candidate_in_fpa4_inventory = true
lineage_status = pass
decision_logic_source = scripts/build_tw_policy_ral_fpa4_predeclared_full_path_rule_sanity.py::should_intervene
replay_engine_source = scripts/run_tw_policy_action_model_pa1.py compatible local instrumented replay
not_candidate_pass_fail = true
```

脚本 `scripts/build_tw_policy_catr1_candidate_atpal_replay_builder.py` 也明确从 FPA4 的 `candidate_manifest_rows`、`should_intervene` 和 PA1 replay 组件构建，不是另起新策略逻辑。

## 8. Forbidden / Scope 审查

通过。

`validator_report.json` 明确：

```text
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
```

`forbidden_consumer_audit.csv` 共 15 项，均为：

```text
pass_not_allowed_not_present
```

额外抽查 CSV 列名，未发现以下禁用字段：

```text
OrderIntent
target_weight
target_position
quantity_instruction
broker_order
```

注意：`candidate_trade_level_pnl_ledger.csv` 中存在 `simulated_executed_quantity`，这是 CATR1 工作文档允许的 replay accounting 字段，不是 `quantity_instruction`，不构成订单语义输出。

## 9. 对收益字段的解释

`candidate_vs_baseline_delta_summary.csv` 包含 candidate 与 baseline 的收益、费用、换手 delta。例如 validation 中部分 candidate delta 为正，部分为负。

但这些字段均处于：

```text
diagnostic_only = true
not_candidate_pass_fail = true
```

且文件未出现 `candidate_pass`、`selected`、`approved`、`production_ready` 等字段。因此本轮没有做 candidate 通过/失败判断，也没有选择策略。

## 10. 发现与风险

未发现阻断问题。

剩余风险是分析层面的，不是 CATR1 执行合规问题：

```text
1. CATR1 只是把 FPA4 candidate replay 账本补齐，不证明 candidate 可泛化。
2. 既有 FPA4 失败结论仍有效，除非后续有单独授权的 analysis phase 重新审查 trade / symbol-date / concentration 证据。
3. 后续若进入分析阶段，必须继续禁止阈值重选、validation mining 和 strict_test 自动推进。
```

## 11. 最终 Verdict

```text
PASS_CANDIDATE_ATPAL_LEDGERS_READY_FOR_ANALYSIS
```

建议下一步由统筹决定是否撰写 `CATR2 Candidate ATPAL Ledger Analysis` 工作文档。CATR2 若启动，应只分析 CATR1 账本解释为什么 FPA4 candidate 失败或是否存在可预声明的低维现象；不得直接做新策略、调阈值、strict_test、训练或生产集成。
