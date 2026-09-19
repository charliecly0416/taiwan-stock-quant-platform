---
created_at: 2026-06-23
status: review_complete
phase: CATR2_CANDIDATE_ATPAL_LEDGER_ANALYSIS
mainline_doc: docs/tw_portfolio_decision_model/POLICY_CATR_CANDIDATE_ATPAL_REPLAY_FEASIBILITY_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_CATR2_CANDIDATE_ATPAL_LEDGER_ANALYSIS_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_CATR2_CANDIDATE_ATPAL_LEDGER_ANALYSIS_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/candidate_atpal_replay_feasibility/catr2_candidate_atpal_ledger_analysis
previous_review: docs/tw_portfolio_decision_model/POLICY_CATR1_CANDIDATE_ATPAL_REPLAY_BUILDER_REVIEW_CN.md
verdict: PASS_READY_FOR_COORDINATOR_ROUTE_DECISION
candidate_pass_fail_authorized: false
strict_test_authorized: false
model_training_authorized: false
production_allowed: false
---

# CATR2 Candidate ATPAL Ledger Analysis 审查报告

## 1. 审查结论

```text
PASS_READY_FOR_COORDINATOR_ROUTE_DECISION
```

CATR2 执行结果符合工作文档边界：本轮只分析 CATR1 candidate ATPAL ledgers，用于解释既有 FPA4 candidates 的收益/亏损来源、集中度和 train/validation 不稳定原因。未发现 candidate pass/fail judgement、新增候选、调阈值、strict_test、模型训练、生产/default/order/provider/frontend/Agent 集成或订单语义输出。

这个 PASS 只表示统筹可以基于 CATR2 分析结果做路线决策；不代表任何 candidate 通过，也不授权 strict_test、retest、生产化或继续挖阈值。

## 2. 审查范围

已核查：

```text
docs/tw_portfolio_decision_model/POLICY_CATR_CANDIDATE_ATPAL_REPLAY_FEASIBILITY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_CATR2_CANDIDATE_ATPAL_LEDGER_ANALYSIS_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_CATR2_CANDIDATE_ATPAL_LEDGER_ANALYSIS_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_CATR1_CANDIDATE_ATPAL_REPLAY_BUILDER_REVIEW_CN.md
data_tw/experiments/candidate_atpal_replay_feasibility/catr1_candidate_atpal_replay_builder/
data_tw/experiments/candidate_atpal_replay_feasibility/catr2_candidate_atpal_ledger_analysis/
scripts/build_tw_policy_catr2_candidate_atpal_ledger_analysis.py
```

未运行新分析、未运行 replay、未修改执行产物。

## 3. Artifact 完整性

必需 artifacts 齐全：

```text
manifest.json
source_artifact_manifest.json
candidate_delta_component_analysis.csv
candidate_symbol_date_concentration_analysis.csv
candidate_trade_pnl_distribution_analysis.csv
candidate_lifecycle_pnl_distribution_analysis.csv
candidate_train_validation_failure_attribution.csv
candidate_year_regime_stability_analysis.csv
candidate_research_recommendation_audit.csv
forbidden_consumer_audit.csv
validator_report.json
diagnostic_findings.md
```

核心行数符合 CATR1 的 7 个 candidate-threshold version / 2 个 split 结构：

```text
candidate_delta_component_analysis.csv: 14 data rows
candidate_symbol_date_concentration_analysis.csv: 14 data rows
candidate_trade_pnl_distribution_analysis.csv: 14 data rows
candidate_lifecycle_pnl_distribution_analysis.csv: 14 data rows
candidate_train_validation_failure_attribution.csv: 7 data rows
candidate_year_regime_stability_analysis.csv: 21 data rows
candidate_research_recommendation_audit.csv: 7 data rows
```

`validator_report.json` 显示：

```text
ok = true
status = CATR2_ANALYSIS_READY_FOR_REVIEW
final_recommendation = READY_FOR_REVIEWER_TO_AUDIT_CATR2_ANALYSIS
source_catr1_validator_ok = true
candidate_scope_matches_fpa4 = true
failed_count = 0
```

## 4. 是否只分析 CATR1 Ledgers

通过。

脚本 `scripts/build_tw_policy_catr2_candidate_atpal_ledger_analysis.py` 的主要输入为 CATR1 产物：

```text
candidate_vs_baseline_delta_summary.csv
candidate_trade_level_pnl_ledger.csv
candidate_position_lifecycle_ledger.csv
candidate_symbol_date_pnl_ledger.csv
candidate_action_context_ledger.csv
candidate_concentration_audit.csv
validator_report.json
```

`source_artifact_manifest.json` 还列出 ATPAL2 / FPA4 文件，但其作用是来源记录和基准背景，不构成本轮新增 replay、候选生成或阈值选择。审查未发现脚本执行 candidate replay 或重建策略路径。

## 5. Delta Component / Concentration / Train-validation 解释

通过。

`candidate_delta_component_analysis.csv` 对每个 candidate-threshold-split 输出：

```text
baseline_net_return_after_fee_tax
candidate_net_return_after_fee_tax
delta_net_return_after_fee_tax
delta_fee_and_tax
delta_turnover_proxy
component_interpretation
fee_tax_delta_direction
turnover_delta_direction
```

关键诊断与执行报告一致：

```text
C01 rank_lte_25 / rank_lte_50 validation delta = +0.25236201，但 train delta = -0.03672023，且 validation 费用和换手更高。
C02 validation delta = -0.00244208，train 强但 validation 转弱。
C03 validation delta = -0.31069264，train 强但 validation 转弱。
C04 validation delta = -0.01358120，train 强但 validation 转弱。
C05 holding_days_005_019 validation delta = -0.28833930，train 强但 validation 转弱。
C05 holding_days_020_059 validation delta = +0.02334573，train delta = +0.31916291，但 validation 边际较薄。
```

`candidate_symbol_date_concentration_analysis.csv` 提供 symbol-date 集中度：

```text
top1_symbol_date_abs_share
top10_symbol_date_abs_share
top_symbol_date
candidate_concentration_top10_share
baseline_reference_top10_share
candidate_top1_symbol_share
baseline_reference_top1_symbol_share
```

validation 的 candidate top10 symbol-date abs share 多数高于 baseline reference：

```text
C01 validation top10 = 0.0696929997 vs baseline reference 0.0367614345
C02 validation top10 = 0.0732717303 vs baseline reference 0.0367614345
C04 validation top10 = 0.0667864371 vs baseline reference 0.0367614345
C05 holding_days_020_059 validation top10 = 0.0565034420 vs baseline reference 0.0367614345
```

`candidate_train_validation_failure_attribution.csv` 已解释方向反转和 validation top contributor：

```text
C01: train_negative_validation_positive
C02/C03/C04/C05 holding_days_005_019: train_positive_validation_negative
C05 holding_days_020_059: both_positive_but_not_strategy_judgement
```

这些证据足以支持 CATR2 的分析目标：解释正/负 delta 的 component、集中度和 train/validation 差异。

## 6. Recommendation Audit 审查

通过。

`candidate_research_recommendation_audit.csv` 未出现禁用字段：

```text
pass
approved
selected
production_ready
strict_test_ready
```

实际 `research_recommendation` 只使用允许值：

```text
eligible_for_coordinator_discussion_only
close_negative_evidence
```

文件同时保留：

```text
fpa4_original_conclusion_preserved = True
diagnostic_only = True
not_candidate_pass_fail = True
```

因此 recommendation 仍是研究路线建议，不是 candidate 通过/失败判断。

## 7. Forbidden / Scope 审查

通过。

`validator_report.json` 明确：

```text
analysis_only = true
candidate_pass_fail_judgement = false
new_candidate_added = false
threshold_adjustment = false
strict_test_used = false
model_training_run = false
production_allowed = false
order_intent_output = false
target_weight_output = false
target_position_output = false
quantity_instruction_output = false
broker_order_output = false
```

`forbidden_consumer_audit.csv` 对 7 个分析 CSV 的禁用字段检查均为 `not_present`。

额外全文抽查中，禁用词只出现在以下合规上下文：

```text
validator false 字段；
forbidden_consumer_audit 的 not_present 行；
diagnostic_findings.md 的“未执行”边界说明；
not_candidate_pass_fail 诊断标记。
```

未发现订单语义、生产语义或 strict_test ready 语义输出。

## 8. 发现与风险

未发现阻断问题。

剩余风险属于路线决策层面：

```text
1. CATR2 证明已有 ledgers 能解释失败与不稳定，但不证明任何候选值得 retest。
2. C01 validation 正收益较大，但 train 为负，且费用/换手上升，不能作为直接策略证据。
3. C05 holding_days_020_059 train/validation 均为正，但 validation delta 只有 +0.02334573，且存在 symbol-date 集中度风险；最多进入统筹讨论，不能直接推进 strict_test。
4. 多数 candidate 出现 train 强、validation 弱或 validation 负，支持 FPA4 原始失败结论仍应保留。
```

## 9. 最终 Verdict

```text
PASS_READY_FOR_COORDINATOR_ROUTE_DECISION
```

建议统筹下一步在两类路线中选择：

```text
1. 关闭 CATR/FPA candidate policy route，把 CATR2 作为失败归因与负面证据归档。
2. 若仍想继续，只能另开新主线讨论极少数 candidate 的外部约束重审；不得在 CATR2 后自动 strict_test、调阈值或生产化。
```
