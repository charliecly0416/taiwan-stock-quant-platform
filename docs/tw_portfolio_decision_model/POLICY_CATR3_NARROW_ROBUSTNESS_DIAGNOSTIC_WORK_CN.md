---
created_at: 2026-06-23
status: coordinator_work_doc
phase: CATR3_NARROW_ROBUSTNESS_DIAGNOSTIC
mainline_doc: docs/tw_portfolio_decision_model/POLICY_CATR_CANDIDATE_ATPAL_REPLAY_FEASIBILITY_MAINLINE_CN.md
route_decision: docs/tw_portfolio_decision_model/POLICY_CATR_FINAL_ROUTE_DECISION_CN.md
previous_review: docs/tw_portfolio_decision_model/POLICY_CATR2_CANDIDATE_ATPAL_LEDGER_ANALYSIS_REVIEW_CN.md
artifact_root: data_tw/experiments/candidate_atpal_replay_feasibility/catr3_narrow_robustness_diagnostic
candidate_pass_fail_authorized: false
new_candidate_authorized: false
threshold_selection_authorized: false
strict_test_authorized: false
model_training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
---

# CATR3 Narrow Robustness Diagnostic 工作文档

## 1. 授权范围

本轮只对 CATR2 后仍可讨论的候选做窄范围 robustness diagnostic：

```text
FPA4_C01 / rank_lte_25
FPA4_C01 / rank_lte_50
FPA4_C05 / holding_days_020_059
```

目标是判断这些候选的正 delta 是否：

```text
1. 过度集中于少数 symbol/date/lifecycle/trade；
2. train/validation 或 yearly pattern 不稳；
3. 费用、换手、单一事件解释占比过高；
4. 仅值得关闭，还是值得未来新主线讨论。
```

本轮不做 candidate pass/fail，不改变 FPA4 失败结论。

## 2. 必读文档与产物

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_CATR_FINAL_ROUTE_DECISION_CN.md
docs/tw_portfolio_decision_model/POLICY_CATR3_NARROW_ROBUSTNESS_DIAGNOSTIC_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_CATR2_CANDIDATE_ATPAL_LEDGER_ANALYSIS_REVIEW_CN.md
data_tw/experiments/candidate_atpal_replay_feasibility/catr1_candidate_atpal_replay_builder/
data_tw/experiments/candidate_atpal_replay_feasibility/catr2_candidate_atpal_ledger_analysis/
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal2_contribution_audit/
```

## 3. 输出目录

```text
data_tw/experiments/candidate_atpal_replay_feasibility/catr3_narrow_robustness_diagnostic/
```

## 4. 必须输出文件

```text
manifest.json
source_artifact_manifest.json
narrow_candidate_inventory.csv
narrow_candidate_symbol_date_stress.csv
narrow_candidate_top_contributor_removal_sensitivity.csv
narrow_candidate_year_split_stability.csv
narrow_candidate_trade_lifecycle_stress.csv
narrow_candidate_cost_turnover_stress.csv
narrow_candidate_route_recommendation.csv
forbidden_consumer_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_CATR3_NARROW_ROBUSTNESS_DIAGNOSTIC_EXECUTION_REPORT_CN.md
```

## 5. 必须回答的问题

执行者必须回答：

```text
1. C01 的 validation 正 delta 是否主要由 TW2408 或少数 symbol-date 驱动？
2. C01 去除 top1 / top3 / top10 symbol-date contribution 后，正 delta 是否仍有意义？
3. C01 train 为负、validation 为正是否显示 regime-specific 而非稳健 edge？
4. C05 holding_days_020_059 的 validation +0.02334573 是否足够分散？
5. C05 去除 top contributors 后是否转负或接近 0？
6. 两类候选是否值得未来新主线讨论，还是应全部关闭？
```

## 6. 推荐值限制

`narrow_candidate_route_recommendation.csv` 的推荐值只能是：

```text
close_all_candidate_policy_route
close_candidate_negative_evidence
eligible_for_new_mainline_discussion_only
needs_external_closure
```

不得出现：

```text
pass
approved
selected
production_ready
strict_test_ready
```

## 7. 禁止事项

严禁：

```text
candidate pass/fail judgement；
FPA4 repair；
改变 FPA4 STOP_NO_PREDECLARED_RULE_SANITY_PASS 结论；
新增候选；
调阈值；
validation mining；
strict_test；
模型训练；
生产/default/order/provider/frontend/Agent 集成；
OrderIntent output；
target_weight / target_position / quantity_instruction / broker_order。
```

## 8. Validator 要求

`validator_report.json` 必须包含：

```text
ok
status
final_recommendation
narrow_scope_only = true
candidate_scope_matches_route_decision = true
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
failed_count
checks
```

推荐 `final_recommendation` 只能是：

```text
READY_FOR_REVIEWER_TO_AUDIT_CATR3_ROBUSTNESS
FAIL_CATR3_VALIDATOR
STOP_CATR3_SCOPE_VIOLATION
```

## 9. 审查要求

审查者必须检查：

```text
1. 是否只覆盖 C01 与 C05 holding_days_020_059。
2. 是否没有新增候选或调阈值。
3. 是否没有 candidate pass/fail。
4. 是否完成 top contributor removal / concentration / yearly stability 分析。
5. 是否没有 strict_test、训练、生产字段。
6. route recommendation 是否只使用允许值。
```

审查结论只能是：

```text
PASS_READY_FOR_FINAL_CATR_CLOSURE_DECISION
FAIL_NEEDS_REPAIR
STOP_CATR3_SCOPE_VIOLATION
```
