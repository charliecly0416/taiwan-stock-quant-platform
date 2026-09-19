---
created_at: 2026-06-28
status: work_doc
phase: MTRC4_RESEARCH_CLOSURE_DECISION
parent_phase: MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC
parent_review: docs/tw_portfolio_decision_model/POLICY_MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_REVIEW_CN.md
readonly_only: true
simulation_only: true
diagnostic_only: true
research_only: true
production_allowed: false
model_training_authorized: false
model_inference_authorized: false
model_signal_artifact_authorized: false
order_intent_build_authorized: false
replay_result_build_authorized: false
ledger_build_authorized: false
strategy_tuning_authorized: false
new_candidate_authorized: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
frontend_default_switch_allowed: false
broker_authorized: false
---

# POLICY_MTRC4_RESEARCH_CLOSURE_DECISION_WORK_CN

## 1. 目标

MTRC4 只做 MTRC research-only continuation 的最终收尾判断：

```text
基于 MTRC2_U ReplayResult 与 MTRC3 diagnostic/review，
判断 MTRC 是否关闭、是否保留研究归档、是否允许另开数据质量 follow-up，
并明确不得进入 production readiness。
```

MTRC4 不再跑实验，不再生成任何新的 signal/order/replay/ledger。

## 2. 当前事实

MTRC3 独立审查结论：

```text
verdict = PASS_WITH_MARK_QUALITY_WARNINGS_READY_FOR_MTRC4
```

MTRC3 支持的观察：

```text
final_equity = 2012130218.262249
total_return = 2011.1302182622
max_drawdown = -0.1990237415
positive_month_ratio = 0.8288288288
rolling_20d_positive_ratio = 0.9055319149
rolling_40d_positive_ratio = 0.9238095238
top1_symbol_share = 0.0732851362 pass
top3_symbol_share = 0.1641435559 pass
top1_event_share = 0.0342442911 pass
```

MTRC3 的硬限制：

```text
fallback_ratio = 0.8996056241 fail_research_only
final_date_fallback_ratio = 0.9 fail_research_only
max_mark_lag_days = 469 fail_research_only
baseline_delta_allowed = false
no legal same-signal baseline replay
all returns = same_signal_replay_absolute_diagnostic_only
```

统筹解释：

```text
集中度问题在 MTRC2_U/MTRC3 的 same-signal replay 中已经明显缓解；
但 mark-to-market 质量严重不足，导致巨大收益只能作为 research-only replay observation；
当前证据不能进入 production readiness，也不能解除 MTR5/MTRC research-only 边界。
```

## 3. 必读材料

执行者必须读取：

```text
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC2_U_SAME_SIGNAL_READONLY_REPLAY_BUILD_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_REVIEW_CN.md
data_tw/experiments/policy_mtr_research_only_continuation/mtrc3_extended_concentration_window_diagnostic/manifest.json
data_tw/experiments/policy_mtr_research_only_continuation/mtrc3_extended_concentration_window_diagnostic/summary_diagnostic.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc3_extended_concentration_window_diagnostic/mark_quality_diagnostic.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc3_extended_concentration_window_diagnostic/symbol_concentration_diagnostic.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc3_extended_concentration_window_diagnostic/event_concentration_diagnostic.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc3_extended_concentration_window_diagnostic/validator_report.json
```

允许参考：

```text
docs/tw_portfolio_decision_model/POLICY_MTR5_EXTENDED_OOS_SHADOW_AND_PRODUCTION_READINESS_DIAGNOSTIC_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC2_U_SAME_SIGNAL_READONLY_REPLAY_BUILD_EXECUTION_REPORT_CN.md
```

## 4. 允许输出

允许新增输出目录：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc4_research_closure_decision/
```

必须生成：

```text
manifest.json
closure_decision.csv
evidence_summary.csv
production_blocker_register.csv
research_archive_register.csv
optional_followup_register.csv
forbidden_scope_audit.csv
validator_report.json
closure_findings.md
```

必须生成执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC4_RESEARCH_CLOSURE_DECISION_EXECUTION_REPORT_CN.md
```

必须生成审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC4_RESEARCH_CLOSURE_DECISION_REVIEW_CN.md
```

允许新增 builder：

```text
scripts/build_tw_policy_mtrc4_research_closure_decision.py
```

builder 只能写 MTRC4 输出目录和执行报告。

## 5. Closure 决策要求

`closure_decision.csv` 必须给出一个最终 decision：

```text
KEEP_RESEARCH_ONLY_WITH_DATA_QUALITY_FOLLOWUP
KEEP_RESEARCH_ONLY_CLOSE_MTRC
STOP_COORDINATOR_DECISION_REQUIRED
```

推荐决策：

```text
KEEP_RESEARCH_ONLY_WITH_DATA_QUALITY_FOLLOWUP
```

理由：

- same-signal long-window replay 的 concentration gate 通过，说明旧 MTR5 的 top3 concentration 阻断在这条 clean replay 中缓解；
- mark-quality gate 严重失败，不能进入 production readiness；
- 没有合法 same-signal baseline delta，不能证明相对 baseline 的生产提升；
- 当前路线应归档为 research-only，若继续，应另开数据质量/mark-to-market refresh follow-up，而不是继续策略调参。

## 6. Evidence Summary 要求

`evidence_summary.csv` 至少包含：

```text
evidence_id
source_artifact
metric
value
gate
interpretation
production_effect
```

必须覆盖：

```text
same_signal_replay_generated
accounting_sanity_passed
total_return_absolute_observation
max_drawdown
positive_month_ratio
rolling_20d_positive_ratio
rolling_40d_positive_ratio
top1_symbol_share
top3_symbol_share
top1_event_share
fallback_ratio
final_date_fallback_ratio
max_mark_lag_days
baseline_delta_allowed
forbidden_scope_pass
```

## 7. Production Blocker Register 要求

`production_blocker_register.csv` 必须至少列出：

```text
mark_quality_fallback_ratio_fail
final_date_mark_quality_fail
max_mark_lag_days_fail
no_legal_same_signal_baseline_delta
absolute_return_not_production_evidence
research_only_lineage_not_default_artifact
no_frontend_api_agent_daily_default_authorization
```

每个 blocker 必须有：

```text
blocker_id
severity
evidence
effect
disposition
required_to_clear
```

## 8. Research Archive / Follow-up 要求

`research_archive_register.csv` 必须记录 MTRC 需要保留的核心 artifact：

```text
MTRC1D broad full-rank signal
MTRC2_S same-signal OrderIntent
MTRC2_T_R price bridge
MTRC2_U ReplayResult
MTRC3 diagnostic
MTRC4 closure decision
```

`optional_followup_register.csv` 只能列 optional follow-up，不得自动授权：

```text
PRICE_MARK_TO_MARKET_QUALITY_REPAIR
SAME_SIGNAL_BASELINE_REPLAY_IF_LEGAL_INPUT_EXISTS
DATA_COVERAGE_REFRESH_FOR_RESEARCH_REPLAY
```

每个 follow-up 必须声明：

```text
requires_new_user_authorization = true
production_allowed = false
```

## 9. Validator 要求

`validator_report.json` 必须检查：

```text
mtrc3_review_passed
decision_is_allowed
required_output_files_present
evidence_summary_contains_required_metrics
production_blockers_include_mark_quality
research_archive_register_complete
optional_followups_are_not_authorized
no_new_signal_order_replay_ledger
no_model_training_or_inference
no_strategy_tuning_or_candidate_selection
no_provider_latest_default_frontend_api_agent_daily_write
no_broker_order_target_weight_target_position
production_allowed_false
research_only_true
```

## 10. 禁止动作

MTRC4 禁止：

```text
训练模型、调参、inference、重算 LTR score
生成或修改 ModelSignalArtifact
生成或修改 OrderIntentArtifact
生成或修改 ReplayResultArtifact
生成 ledger / attribution ledger
新增候选或修改 M2_hold_rank_buffer_100 / rank_buffer=100
根据收益选择参数或调规则
复用旧 MTR2_R/E3 replay 作为输入生成新结论
写正式 PriceStore
写 registry/config/default
provider refresh / publish
accepted latest switch
写 frontend/API/Agent/daily/production
broker / quick-trade / real order
target_weight / target_position / quantity instruction
解除 MTR5 blocker
宣称 production readiness
```

## 11. 审查者 audit brief

审查者必须检查：

```text
1. MTRC4 是否只做 closure，不做新实验；
2. closure decision 是否与 MTRC3 证据一致；
3. 是否明确 concentration 缓解但 mark-quality fail 阻断 production readiness；
4. 是否列出 production blockers；
5. optional follow-up 是否只是建议而非授权；
6. 是否未写 production/default/latest/provider/frontend/API/Agent/daily；
7. 是否未 broker/order/target_weight/target_position；
8. 是否未训练/inference/调参/新候选。
```

允许审查 verdict：

```text
PASS_MTRC_RESEARCH_ROUTE_CLOSED
PASS_MTRC_RESEARCH_ROUTE_CLOSED_WITH_OPTIONAL_DATA_QUALITY_FOLLOWUP
FAIL_NEEDS_MTRC4_REPAIR
STOP_COORDINATOR_DECISION_REQUIRED
```

## 12. 执行命令

```text
请执行 MTRC4_RESEARCH_CLOSURE_DECISION。
只基于 MTRC2_U ReplayResult 与 MTRC3 diagnostic/review 做 research-only closure；
不得生成新 replay/order/signal/ledger，不得训练/inference，不得调参，不得生产接入。
重点结论必须说明 concentration 已缓解但 mark-quality fail 阻断 production readiness。
```
