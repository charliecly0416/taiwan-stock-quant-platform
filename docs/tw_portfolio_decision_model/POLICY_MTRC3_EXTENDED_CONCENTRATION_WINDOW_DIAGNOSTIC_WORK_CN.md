---
created_at: 2026-06-28
status: work_doc
phase: MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC
parent_phase: MTRC2_U_SAME_SIGNAL_READONLY_REPLAY_BUILD
parent_review: docs/tw_portfolio_decision_model/POLICY_MTRC2_U_SAME_SIGNAL_READONLY_REPLAY_BUILD_REVIEW_CN.md
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

# POLICY_MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_WORK_CN

## 1. 目标

MTRC3 只做一件事：

```text
基于 MTRC2_U 已通过审查的 same-signal readonly ReplayResultArtifact，
做 extended concentration / window / mark-quality diagnostic，
判断 MTRC2_U 的高收益是否稳定、是否由少数标的/事件/月份驱动、是否受到 mark-to-market fallback 明显影响。
```

本阶段不生成新的策略、不生成新的 OrderIntent、不生成新的 ReplayResult、不训练模型、不推生产。

## 2. 背景事实

MTRC2_U 审查结论：

```text
verdict = PASS_READY_FOR_MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC
initial_cash = 1000000.000000
final_equity = 2012130218.262249
total_return = 2011.1302182622
max_drawdown = -0.1990237415
action_count = 2332
buy_count = 1171
sell_count = 1161
skipped_action_count = 46
max_holding_count = 10
duplicate_position_count = 0
negative_cash_count = 0
missing_price_count = 10493
final holdings = 10
same-date close mark on final date = 1
latest-prior-close audited fallback on final date = 9
```

审查判断：会计层面未发现明显 bug，但收益只能作为 research-only replay 数值，不能作为 production readiness。

## 3. 必读材料

执行者必须读取：

```text
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC2_U_SAME_SIGNAL_READONLY_REPLAY_BUILD_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC2_U_SAME_SIGNAL_READONLY_REPLAY_BUILD_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC2_U_SAME_SIGNAL_READONLY_REPLAY_BUILD_REVIEW_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
```

允许参考但不得复用输入：

```text
scripts/run_tw_policy_mtr3_robustness_window_regime_and_mechanism_attribution.py
data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution/
```

旧 MTR/MTR2_R/MTR3/E3 只可作为指标定义参考，不得作为 MTRC3 same-signal 诊断输入。

## 4. 固定输入

MTRC3 只能读取以下 MTRC2_U 产物：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_u_same_signal_readonly_replay_build/manifest.json
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_u_same_signal_readonly_replay_build/summary.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_u_same_signal_readonly_replay_build/actions.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_u_same_signal_readonly_replay_build/daily_nav.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_u_same_signal_readonly_replay_build/position_snapshots.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_u_same_signal_readonly_replay_build/skipped_actions.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_u_same_signal_readonly_replay_build/coverage_audit.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_u_same_signal_readonly_replay_build/position_integrity_audit.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_u_same_signal_readonly_replay_build/validator_report.json
```

可读取 MTRC2_S / MTRC2_T_R / MTRC1D manifest 只做 lineage link 校验，不得重新生成任何上游 artifact。

## 5. 必须输出

输出目录：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc3_extended_concentration_window_diagnostic/
```

必须生成：

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

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_REVIEW_CN.md
```

允许新增 builder：

```text
scripts/build_tw_policy_mtrc3_extended_concentration_window_diagnostic.py
```

builder 只能写 MTRC3 输出目录和执行报告。

## 6. 诊断指标要求

### 6.1 Window / Monthly / Rolling

必须计算：

```text
full window return / max_drawdown
yearly windows
monthly returns
rolling 20 execution-day returns
rolling 40 execution-day returns
positive month ratio
negative month inventory
worst 20d / 40d windows
```

MTRC3 没有合法 baseline replay，因此不得计算 M2-vs-baseline delta。所有收益指标都必须标记为：

```text
same_signal_replay_absolute_diagnostic_only
```

### 6.2 Drawdown

必须识别：

```text
max_drawdown peak_date
max_drawdown trough_date
drawdown_depth
duration_days
top drawdown episodes
```

### 6.3 Symbol / Event Concentration

必须基于 replay action 和 position snapshots 估算：

```text
symbol realized sell PnL contribution
symbol final unrealized PnL contribution
symbol total contribution
top1_symbol_share
top3_symbol_share
top5_symbol_share
top1_event_share
top5_event_share
```

说明：

- realized sell PnL 可用 sell notional minus estimated cost basis。
- final unrealized PnL 可用最终 position_snapshots 的 `unrealized_pnl`。
- 若只能近似，必须在字段中声明 `approximation_method`。
- concentration denominator 必须明确，推荐使用 `sum(abs(symbol_total_contribution))`，不得用 final_equity 逃避集中度。

建议 gate：

```text
top1_symbol_share <= 0.40: pass, <= 0.60: warn, > 0.60: fail_research_only
top3_symbol_share <= 0.70: pass, <= 0.85: warn, > 0.85: fail_research_only
top1_event_share <= 0.30: pass, <= 0.45: warn, > 0.45: fail_research_only
```

### 6.4 Mark Quality / Fallback

必须计算：

```text
same_date_close_mark_count
latest_prior_close_fallback_count
fallback_ratio
fallback_by_symbol
fallback_by_month
max_mark_lag_days
mean_mark_lag_days
final_date_fallback_count
final_date_fallback_ratio
```

如果 `mark_price_date` 与 snapshot `date` 差距过大，必须列出 top lag rows。

建议 gate：

```text
fallback_ratio <= 0.20: pass
fallback_ratio <= 0.50: warn
fallback_ratio > 0.50: fail_research_only
final_date_fallback_ratio <= 0.20: pass
final_date_fallback_ratio <= 0.50: warn
final_date_fallback_ratio > 0.50: fail_research_only
max_mark_lag_days <= 10: pass
max_mark_lag_days <= 30: warn
max_mark_lag_days > 30: fail_research_only
```

### 6.5 Skipped / Cost / Turnover

必须计算：

```text
skipped count by reason
skipped count by year/month
buy/sell count by month
turnover notional by month
commission/tax/fee_plus_tax by month
fee_plus_tax / ending equity
```

## 7. Validator 要求

`validator_report.json` 必须检查：

```text
input_replay_artifact_equals_mtrc2_u
mtrc2_u_review_passed
required_input_files_present
required_output_files_present
summary_matches_mtrc2_u
daily_nav_equity_equals_cash_plus_market_value
actions_quantity_positive_lot_multiple
negative_cash_count_zero
max_holding_count_lte_10
lineage_links_preserved
old_mtr2r_or_e3_not_used_as_input
no_model_training_or_inference
no_order_intent_or_replay_write
no_strategy_tuning_or_candidate_selection
no_provider_latest_default_frontend_api_agent_daily_write
no_broker_order_target_weight_target_position
diagnostic_only_true
production_allowed_false
```

## 8. 允许 verdict

执行者 verdict 只能是：

```text
PASS_READY_FOR_MTRC4_RESEARCH_CLOSURE_DECISION
PASS_WITH_MARK_QUALITY_WARNINGS_READY_FOR_MTRC4
FAIL_NEEDS_MTRC3_REPAIR
STOP_COORDINATOR_DECISION_REQUIRED
```

其中：

- `PASS_READY_FOR_MTRC4_RESEARCH_CLOSURE_DECISION` 要求合同与诊断完整，且 mark-quality / concentration 没有 fail。
- `PASS_WITH_MARK_QUALITY_WARNINGS_READY_FOR_MTRC4` 表示诊断产物完整，但 mark fallback 或 concentration 存在研究限制。
- 任意 forbidden action、输入 lineage 错误、必需输出缺失，应为 `FAIL_NEEDS_MTRC3_REPAIR`。

## 9. 禁止动作

MTRC3 禁止：

```text
训练模型、调参、inference、重算 LTR score
生成或修改 ModelSignalArtifact
生成或修改 OrderIntentArtifact
生成或修改 ReplayResultArtifact
生成 ledger / attribution ledger
新增候选或修改 M2_hold_rank_buffer_100 / rank_buffer=100
根据收益选择参数或调规则
复用旧 MTR2_R/E3 replay 作为输入
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

## 10. 审查者 audit brief

审查者必须独立检查：

```text
1. MTRC3 是否只读取 MTRC2_U ReplayResult；
2. 是否未生成新 replay/order/signal/ledger；
3. 必需输出是否齐全；
4. window/monthly/rolling/drawdown 是否可复算；
5. symbol/event concentration denominator 是否合理；
6. mark_quality 是否覆盖 fallback_ratio、final fallback、lag days；
7. validator 是否覆盖 forbidden actions；
8. verdict 是否与 mark-quality / concentration 事实一致；
9. 是否未授权生产、默认、broker、target_weight/target_position。
```

审查 verdict 只能是：

```text
PASS_READY_FOR_MTRC4_RESEARCH_CLOSURE_DECISION
PASS_WITH_MARK_QUALITY_WARNINGS_READY_FOR_MTRC4
FAIL_NEEDS_MTRC3_REPAIR
STOP_COORDINATOR_DECISION_REQUIRED
```

## 11. 执行命令

```text
请执行 MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC。
只基于 MTRC2_U ReplayResult 生成 research-only diagnostic tables/report；
不得生成新 replay/order/signal/ledger，不得生产接入，不得调参，不得 broker/order，不得 target_weight/target_position。
```
