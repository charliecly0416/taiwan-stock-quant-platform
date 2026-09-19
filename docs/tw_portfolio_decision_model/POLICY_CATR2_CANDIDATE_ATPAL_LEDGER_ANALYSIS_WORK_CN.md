---
created_at: 2026-06-23
status: coordinator_work_doc
phase: CATR2_CANDIDATE_ATPAL_LEDGER_ANALYSIS
mainline_doc: docs/tw_portfolio_decision_model/POLICY_CATR_CANDIDATE_ATPAL_REPLAY_FEASIBILITY_MAINLINE_CN.md
previous_review: docs/tw_portfolio_decision_model/POLICY_CATR1_CANDIDATE_ATPAL_REPLAY_BUILDER_REVIEW_CN.md
artifact_root: data_tw/experiments/candidate_atpal_replay_feasibility/catr2_candidate_atpal_ledger_analysis
candidate_pass_fail_authorized: false
strategy_search_authorized: false
threshold_selection_authorized: false
strict_test_authorized: false
model_training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
---

# CATR2 Candidate ATPAL Ledger Analysis 工作文档

## 1. 授权范围

CATR1 审查结论为：

```text
PASS_CANDIDATE_ATPAL_LEDGERS_READY_FOR_ANALYSIS
```

本轮授权 CATR2：

```text
只分析 CATR1 生成的 candidate ATPAL ledgers，
解释既有 FPA4 candidates 的收益/亏损来源、集中度、train/validation 不稳定原因。
```

本轮不授权 candidate pass/fail，不授权 FPA4 repair，不授权新策略。

## 2. 必读文档与产物

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_CATR_CANDIDATE_ATPAL_REPLAY_FEASIBILITY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_CATR1_CANDIDATE_ATPAL_REPLAY_BUILDER_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_CATR1_CANDIDATE_ATPAL_REPLAY_BUILDER_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_CATR2_CANDIDATE_ATPAL_LEDGER_ANALYSIS_WORK_CN.md
data_tw/experiments/candidate_atpal_replay_feasibility/catr1_candidate_atpal_replay_builder/
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal2_contribution_audit/
data_tw/experiments/full_path_action_diagnostic/fpa4_predeclared_full_path_rule_sanity/
```

## 3. 输出目录

```text
data_tw/experiments/candidate_atpal_replay_feasibility/catr2_candidate_atpal_ledger_analysis/
```

## 4. 必须输出文件

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

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_CATR2_CANDIDATE_ATPAL_LEDGER_ANALYSIS_EXECUTION_REPORT_CN.md
```

## 5. 分析问题

执行者必须回答：

```text
1. 哪些 candidate 的 validation delta 为正，正收益来自哪些 PnL component？
2. 哪些 candidate train 强但 validation 弱，主要由哪些 symbol/date/trade/lifecycle 分布变化解释？
3. candidate 的收益是否比 baseline 更集中？
4. validation 正收益是否依赖少数 symbol-date 或少数 trade？
5. 费用税与换手变化是否解释 candidate delta？
6. 是否有任何 candidate 值得后续单独重审，还是应关闭 CATR/FPA route？
```

注意：

```text
“值得后续重审”不是 candidate pass。
只能写为 research_recommendation，不得写 selected / approved / production_ready。
```

## 6. 推荐分类

`candidate_research_recommendation_audit.csv` 的推荐值只能是：

```text
close_negative_evidence
needs_no_further_action
eligible_for_coordinator_discussion_only
requires_new_mainline_before_any_retest
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
1. candidate pass/fail judgement。
2. FPA4 repair。
3. 改变 FPA4 STOP_NO_PREDECLARED_RULE_SANITY_PASS 结论。
4. 新增候选。
5. 调整阈值。
6. validation mining。
7. strict_test。
8. 模型训练。
9. 生产/default/order/provider/frontend/Agent 集成。
10. OrderIntent output。
11. target_weight / target_position / quantity_instruction / broker_order。
```

## 8. Validator 要求

`validator_report.json` 必须包含：

```text
ok
status
final_recommendation
source_catr1_validator_ok
candidate_scope_matches_fpa4
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
READY_FOR_REVIEWER_TO_AUDIT_CATR2_ANALYSIS
FAIL_CATR2_ANALYSIS_VALIDATOR
STOP_CATR2_SCOPE_VIOLATION
```

## 9. 审查要求

审查者必须检查：

```text
1. 是否只分析 CATR1 ledgers。
2. 是否没有新增候选或调阈值。
3. 是否没有 candidate pass/fail。
4. 是否解释了正/负 delta 的 component、concentration、train/validation 差异。
5. 是否继续保留 FPA4 原始失败结论。
6. 是否未使用 strict_test、训练或生产字段。
```

审查结论只能是：

```text
PASS_READY_FOR_COORDINATOR_ROUTE_DECISION
FAIL_NEEDS_REPAIR
STOP_CATR2_SCOPE_VIOLATION
```

即使 PASS，也只表示统筹可以决定关闭路线或另写新主线；不代表 candidate 通过。
