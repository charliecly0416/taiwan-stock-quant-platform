---
created_at: 2026-06-28
status: review
phase: MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC
verdict: PASS_WITH_MARK_QUALITY_WARNINGS_READY_FOR_MTRC4
readonly_only: true
simulation_only: true
diagnostic_only: true
research_only: true
production_allowed: false
---

# POLICY_MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_REVIEW_CN

## 1. Verdict

```text
PASS_WITH_MARK_QUALITY_WARNINGS_READY_FOR_MTRC4
```

通过含义仅限：

```text
MTRC3 已按合同完成 same-signal research-only concentration / window / mark-quality diagnostic，
可以进入 MTRC4 research closure decision。
```

不含义：

```text
不代表 production readiness；
不解除 MTR5 / MTRC 的 research-only 边界；
不得进入 provider/latest/default/frontend/API/Agent/daily/broker/order；
不得生成 target_weight / target_position；
不得把本阶段收益作为生产收益证据。
```

核心原因：MTRC3 的诊断产物完整，集中度 gate 通过，但 mark-to-market quality 严重失败：

```text
fallback_ratio = 0.8996056241
final_date_fallback_ratio = 0.9
max_mark_lag_days = 469
```

因此下一步只能进入 MTRC4 research closure decision，不能进入 production readiness。

## 2. 审查范围

本审查只检查：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_WORK_CN.md
```

要求下的 MTRC3 执行结果，包括 builder、执行报告和输出目录。

本审查不授权：

```text
新模型训练 / inference / LTR 重算
新 ModelSignalArtifact
新 OrderIntentArtifact
新 ReplayResultArtifact
ledger / attribution ledger
策略调参 / 新候选
生产化、默认切换、accepted latest switch
provider publish / refresh
frontend/API/Agent/daily/production 写入
broker / quick-trade / real order
target_weight / target_position
```

## 3. 读取材料

已读取：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC2_U_SAME_SIGNAL_READONLY_REPLAY_BUILD_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
scripts/build_tw_policy_mtrc3_extended_concentration_window_diagnostic.py
data_tw/experiments/policy_mtr_research_only_continuation/mtrc3_extended_concentration_window_diagnostic/
```

使用技能边界：

```text
coordinator-executor-reviewer-workflow
tw-stock-new-strategy-onboarding
```

## 4. Artifact 与必需输出检查

MTRC3 输出目录存在：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc3_extended_concentration_window_diagnostic/
```

工作文档要求的 18 个输出均存在：

```text
manifest.json
summary_diagnostic.csv
window_return_diagnostic.csv
monthly_return_diagnostic.csv
rolling_return_diagnostic.csv
drawdown_diagnostic.csv
symbol_concentration_diagnostic.csv
event_concentration_diagnostic.csv
action_contribution_diagnostic.csv
mark_quality_diagnostic.csv
mark_fallback_by_symbol.csv
mark_fallback_by_month.csv
skipped_action_diagnostic.csv
turnover_cost_diagnostic.csv
lineage_audit.csv
forbidden_scope_audit.csv
validator_report.json
diagnostic_findings.md
```

`validator_report.json` 显示：

```text
required_output_files_present = true
required_output_fields_present = true
blocking_reasons = []
```

产物类型为 `ResearchOnlyDiagnosticArtifact`，不是 ModelSignal / OrderIntent / ReplayResult / ledger。

## 5. 输入 Lineage 检查

builder 固定读取：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_u_same_signal_readonly_replay_build/
```

并只读取 MTRC2_U 的：

```text
manifest.json
summary.csv
actions.csv
daily_nav.csv
position_snapshots.csv
skipped_actions.csv
coverage_audit.csv
position_integrity_audit.csv
validator_report.json
```

`lineage_audit.csv` 中所有 MTRC2_U 输入文件 present 检查为 pass；MTRC2_U manifest 中的上游链接仅用于 traceability，未重新生成。

`validator_report.json` 中关键检查：

```text
input_replay_artifact_equals_mtrc2_u = true
mtrc2_u_review_passed = true
lineage_links_preserved = true
old_mtr2r_or_e3_not_used_as_input = true
```

审查未发现旧 MTR2_R/E3 replay 被作为 MTRC3 输入使用。

## 6. Window / Monthly / Rolling / Drawdown 抽查

MTRC3 没有合法 baseline replay，因此所有收益字段均应是：

```text
same_signal_replay_absolute_diagnostic_only
```

抽查结果：

```text
final_equity = 2012130218.262249
total_return = 2011.1302182622
max_drawdown = -0.1990237415
positive_month_ratio = 0.8288288288
rolling_20d_worst_return = -0.1981832385, 2025-03-14 to 2025-04-25
rolling_40d_worst_return = -0.1852667883, 2025-02-10 to 2025-04-25
baseline_delta_allowed = false
```

独立从 MTRC2_U `daily_nav.csv` 复算：

```text
final_equity match = true
total_return match = true
daily_nav cash + market_value == equity mismatch rows = 0
monthly positive ratio match = true
rolling 20d / 40d worst windows match = true
```

说明：

```text
positive_month_ratio 以 ret > 0 为正月；
negative_months 字段只列 ret < 0 的月份；
ret == 0 的月份会降低 positive_month_ratio，但不会出现在 negative_months。
```

这个口径可接受，但 MTRC4 若引用 negative month inventory，应同时说明非正月与负月的差异。

## 7. Symbol / Event Concentration 抽查

MTRC3 的 concentration denominator 使用：

```text
symbol denominator = sum(abs(symbol_total_contribution))
event denominator = sum(abs(event_contribution))
```

这符合 work doc 要求，未用 final_equity 稀释集中度。

抽查结果：

```text
symbol_contribution_denominator = 2527971557.476358
top1_symbol_share = 0.0732851362, gate = pass
top3_symbol_share = 0.1641435559, gate = pass
top5_symbol_share = 0.2372999665
event_contribution_denominator = 3978016716.299766
top1_event_share = 0.0342442911, gate = pass
top5_event_share = 0.1246568213
```

独立从 diagnostic CSV 复算 top1/top3/top5 share，与 summary 一致。

限制说明：

```text
realized sell contribution 使用 weighted_average_cost_from_actions_including_commission_sell_proceeds_after_fee_tax；
final unrealized contribution 使用 final_position_snapshots_unrealized_pnl；
因此 concentration 是机制诊断近似，不是新的精确会计账本。
```

该近似足以判断本轮没有 MTR5 那种 top3 symbol share 近乎垄断的问题，但不能单独作为生产收益归因证据。

## 8. Mark Quality 抽查

这是本阶段最重要的限制。

独立从 MTRC2_U `position_snapshots.csv` 复算：

```text
snapshot_row_count = 11664
same_date_close_mark_count = 1171
latest_prior_close_fallback_count = 10493
fallback_ratio = 0.8996056241
final_date = 2026-05-08
final_date_fallback_count = 9
final_date_fallback_ratio = 0.9
max_mark_lag_days = 469
mean_mark_lag_days = 31.8752572016
```

gate 结果：

```text
fallback_ratio_gate = fail_research_only
final_date_fallback_ratio_gate = fail_research_only
max_mark_lag_days_gate = fail_research_only
```

`mark_fallback_by_symbol.csv` 与 `mark_fallback_by_month.csv` 已输出 fallback by symbol/month。大量月份 fallback ratio 约 0.9，说明这不是局部单点问题。

审查判断：

```text
mark-quality fail 不使 MTRC3 诊断合同失败；
但它阻断 production readiness；
MTRC4 必须把 MTRC2_U/MTRC3 的巨大 total_return 归类为 research-only replay 数值，而不是可生产收益证据。
```

## 9. Skipped / Turnover / Cost 检查

`skipped_action_diagnostic.csv` 与 MTRC2_U 一致：

```text
skipped_action_count = 46
insufficient_cash_for_budget_quantity = 23
sell_intent_without_current_holding = 23
```

`turnover_cost_diagnostic.csv` 按月输出：

```text
buy_count
sell_count
buy_notional
sell_notional
turnover_notional
commission
tax
fee_plus_tax
ending_equity
fee_plus_tax_over_ending_equity
```

未发现 skipped action 被静默成交，也未发现缺价成交被隐藏。

## 10. Forbidden Actions Audit

`forbidden_scope_audit.csv` 全部为 pass。审查未发现以下行为：

```text
model_training
model_inference
ltr_score_recompute
model_signal_artifact_write
order_intent_artifact_write
replay_result_artifact_write
ledger_build
strategy_tuning
new_candidate_selection
old_mtr2r_or_e3_replay_input
formal_price_store_write
registry_config_default_write
provider_refresh_or_publish
accepted_latest_switch
frontend_api_agent_daily_production_write
broker_order_quick_trade_real_order
target_weight_instruction
target_position_instruction
quantity_instruction_outside_replay_result
production_readiness_claim
```

说明：本阶段产物中出现 `quantity`、`cash`、`NAV/equity` 等 replay 诊断字段是读取 MTRC2_U ReplayResult 并做诊断所需，不是 OrderIntent 或生产输入，不违反本阶段边界。

## 11. Findings

### Critical

无。

### High

无合同失败项。

但 mark-quality 是生产阻断项：

```text
fallback_ratio = 0.8996056241
final_date_fallback_ratio = 0.9
max_mark_lag_days = 469
```

这意味着 MTRC3 的收益、回撤、月度收益和最终权益都受到大量 latest-prior-close fallback 影响。即使会计公式本身可复算，这组结果也不能作为 production readiness 证据。

### Medium

`negative_months` 只列 ret < 0 的月份，而 `positive_month_ratio` 把 ret == 0 的月份也算作非正月。该口径不影响 validator，但 MTRC4 做 closure 时应避免把 negative_months 误读为全部非正月份。

### Low

contribution / concentration 使用加权平均成本近似，适合作为集中度诊断，不应被表述为精确 action-level PnL ledger。

## 12. Mainline Compliance

MTRC3 符合 research-only continuation 主线：

```text
readonly_only = true
simulation_only = true
diagnostic_only = true
research_only = true
production_allowed = false
```

它没有尝试解除 MTR5 blocker，也没有进入 MTR6/production readiness proposal。

## 13. Missing Evidence Or Open Questions

无需要 repair 的缺失证据。

保留给 MTRC4 的 closure 问题：

```text
1. 是否因 mark-quality fail 将 MTRC route 正式关闭为 research-only；
2. 是否需要另开数据质量/mark-to-market 修复路线，而不是继续策略研究；
3. 是否只把 concentration pass 作为“没有集中度垄断”的研究观察，而不作为生产候选放行；
4. 是否需要明确区分 negative months 与 non-positive months。
```

## 14. Next Work Document

下一步只允许：

```text
MTRC4_RESEARCH_CLOSURE_DECISION
```

MTRC4 目标：

```text
基于 MTRC2_U + MTRC3，形成 research-only continuation 的 closure decision。
```

MTRC4 必须判断：

```text
1. MTRC clean same-signal replay 是否已经足以说明集中度问题缓解；
2. mark-quality fail 是否使本路线不能进入 production readiness；
3. 巨大 total_return 是否只能作为 research-only replay observation；
4. 是否关闭 MTRC 机制迁移路线，或仅允许另开数据质量/mark refresh 路线；
5. 是否明确禁止把 MTRC3 输出接入 frontend/API/Agent/daily/default；
6. 是否保留 MTRC2_U/MTRC3 artifacts 作为研究归档。
```

MTRC4 禁止：

```text
新增 replay / signal / order intent / ledger
训练 / inference / LTR 重算
调参 / 选择新候选
provider/latest/default/frontend/API/Agent/daily 写入
broker / order / target_weight / target_position
production readiness claim
```

允许 verdict 建议：

```text
KEEP_RESEARCH_ONLY_CLOSE_MTRC
KEEP_RESEARCH_ONLY_WITH_DATA_QUALITY_FOLLOWUP
STOP_COORDINATOR_DECISION_REQUIRED
```

## 15. Command For Coordinator

```text
请进入 MTRC4_RESEARCH_CLOSURE_DECISION。
只基于 MTRC2_U ReplayResult 与 MTRC3 diagnostic/review 做 research-only closure；
不得生成新 replay/order/signal/ledger，不得调参，不得训练/inference，不得生产接入。
重点结论必须说明 concentration 已缓解但 mark-quality fail 阻断 production readiness。
```
