---
created_at: 2026-06-23
status: pass_ready_for_ral_ed1_attribution_diagnostic_work
phase_reviewed: RAL_ED0_ACTION_TRACE_LEDGER_AND_RULE_DISCOVERY_CONTRACT
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_RAL_ED0_EXPLICIT_RULE_DISCOVERY_CONTRACT_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design
reviewer_role: independent_reviewer
strict_test_authorized: false
rule_replay_authorized: false
model_training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
---

# RAL-ED0 Explicit Rule Discovery Contract 审查意见

## 1. 审查结论

结论：

```text
PASS_READY_FOR_RAL_ED1_ATTRIBUTION_DIAGNOSTIC_WORK
```

RAL-ED0 执行结果符合 `POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md` 中对第一步合同设计的要求。执行者完成了 Action Trace Ledger schema、trace_status policy、现有 replay 支持边界盘点、diagnostic feature schema、rule hypothesis template、multi-trade gate、rolling OOS / regime validation、no-grid-search policy、validator / golden sample 设计。

本审查不授权：

```text
1. RAL-ED2 rule sanity；
2. strict_test；
3. 模型训练；
4. OrderIntent / target_weight / target_position / quantity / broker order；
5. provider/latest/monitor/frontend/Agent/production 扩权。
```

## 2. 审查依据

已对照主线检查：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED0_EXPLICIT_RULE_DISCOVERY_CONTRACT_EXECUTION_REPORT_CN.md
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/
```

RAL-ED 主线第 7 节要求 ED0 冻结合同和禁止事项，第 13 节要求审查者检查 schema、trace_status、existing replay 支持边界、diagnostic schema、规则模板、multi-trade gates、rolling OOS、no-grid-search、validator/golden samples，以及未训练、未跑规则收益、未 strict_test、无 target/order 字段。

## 3. 关键审查发现

### 3.1 ActionTraceLedgerArtifact schema 通过

`action_trace_ledger_schema.json` 覆盖主线要求的关键粒度：

```text
action_trace_id x date x symbol x intervention_action_type
```

必需字段包含：

```text
action_trace_id
baseline_counterfactual_trace_id
trace_source
trace_status
date
symbol
baseline_action_type
intervention_action_type
decision_reason_code
score / score_zscore / score_gap
rank / rank_delta / score_delta
holding_age
market_regime / volatility_regime / score_dispersion_regime
baseline/intervention cost, turnover, PnL diagnostics
delta_pnl_after_fee_tax_diagnostic
simulation_only = true
readonly_research_only = true
production_allowed = false
```

schema 同时列出 forbidden fields：

```text
future_return
forward_return
label
oracle_action
oracle_return
target_weight
target_position
quantity_instruction
broker_order
quick_trade
```

审查结论：满足 ED0 合同冻结要求。

### 3.2 trace_status policy 通过

`trace_status_policy.md` 和 schema 均显式区分：

```text
native_trace
counterfactual_replay_trace
derived_proxy
summary_level_only
unavailable
```

并明确：

```text
只有 native_trace / counterfactual_replay_trace 可支持进入后续规则实验。
derived_proxy / summary_level_only 只能用于背景诊断，不可作为 RAL-ED2 rule sanity 依据。
```

审查结论：满足主线禁止 proxy 冒充 native trace 的要求。

### 3.3 existing replay 支持边界盘点通过

`existing_replay_trace_support_audit.csv` 没有夸大现有证据能力。关键边界如下：

```text
RAL1-R repaired baseline ledger:
  baseline action rows 与 fee/tax/turnover/PnL diagnostics 支持；
  action_trace_id 与 baseline_counterfactual_trace_id 目前不支持。

RAL2 PBA action symbol daily ledger:
  date/symbol/action_source/action_type mapping 支持；
  active action native trade PnL 不支持，仍主要是 derived_proxy。

PBA2 active overlay replay ledger:
  daily active replay return 支持；
  date/symbol/action trace 不支持，只能 summary_level_only。

PBA3/PBA3-R decision artifacts:
  model decision rows 可用于审计；
  没有 counterfactual trace 前不得作为规则证据。
```

审查结论：盘点诚实，且已经为 ED1 的 trace_status 审计留下明确边界。

### 3.4 diagnostic feature schema 通过

`diagnostic_feature_schema.json` 覆盖：

```text
score_strength
rank_score_change
market_regime
holding_state
cost_turnover
```

并明确 PIT-safe 来源与 forbidden features：

```text
future_return
forward_return
future_excess_return
label
oracle_action
oracle_return
same_day_unavailable_data
strict_test_metric
post_decision_realized_pnl_as_feature
```

审查结论：满足 ED1 attribution diagnostic 的输入约束。ED1 执行者仍必须在实际构造时逐字段验证 PIT-safe，不能只继承设计声明。

### 3.5 rule hypothesis template 与 no-grid-search 通过

`explicit_rule_hypothesis_template.md` 要求候选规则写明：

```text
rule_id
rule_family
source_ral_ed1_evidence
trace_status_minimum
predeclared_thresholds
expected_positive_effect
expected_failure_mode
multi_trade_policy
participation/cash/clone/change-rate/concentration/cost gates
forbidden outputs
```

`no_grid_search_policy.md` 明确：

```text
RAL-ED2 最多 6 个 rule candidates；
每个 rule candidate 最多 2 个预声明阈值版本；
不得 validation-mined threshold；
不得用 strict_test 选阈值。
```

审查结论：足以阻止事后编规则和无界阈值搜索。

### 3.6 multi-trade gate 与 rolling OOS / regime validation 通过

`multi_trade_gate_design.md` 覆盖：

```text
max_buy_count_per_day
max_sell_count_per_day
max_total_trade_count_per_day
max_daily_turnover
max_period_turnover
max_fee_tax_drag
minimum_score_edge_vs_cost
cash_dominance_gate
participation_gate
active_decision_change_rate_gate
symbol/date pnl concentration gate
```

`rolling_oos_design.md` 明确最小设计：

```text
train window = 12 months
validation/test window = next 3 months
step = 3 months
coverage = 2023-2025
```

`regime_validation_design.md` 覆盖：

```text
market_regime
volatility_regime
score_dispersion_regime
baseline_state
action_context
```

审查结论：满足主线对多买/多卖约束、rolling OOS 和 regime-isolated validation 的设计要求。

### 3.7 validator / golden samples 通过

`validator_design.md` 覆盖 ED0 合同文件存在性、schema 语义、future ED1/ED2 检查项。

`golden_sample_design.md` 覆盖 positive 与 negative cases，包括：

```text
native trace
counterfactual block buy
rule hypothesis template
multi-trade gate
missing action_trace_id
proxy marked native
summary-only rule ready
target fields present
grid search thresholds
strict_test used
cash/no-trade success
missing multi-trade gate
```

审查结论：negative cases 覆盖主线主要风险。

## 4. 禁止事项审查

执行报告与 `forbidden_consumer_audit.csv` 显示：

```text
model_training = not_performed
rule_return_replay = not_performed
strict_test = not_used
OrderIntent_output = not_output
target_weight = not_output
target_position = not_output
quantity = not_output
broker_order = not_output
provider_publish = not_performed
accepted_latest_switch = not_performed
monitor_write = not_performed
frontend_default_switch = not_performed
Agent_recommendation = not_performed
production_default_strategy = not_performed
```

审查结论：未发现 ED0 越界行为。

## 5. 发现项

### Critical

无。

### Major

无。

### Minor / ED1 注意项

1. ED1 可以构建 `action_trace_ledger_sample.csv` 和诊断表，但不得把 `derived_proxy` / `summary_level_only` 候选提升为 ED2-ready hypothesis。
2. ED1 必须将 `action_trace_id` 缺失、counterfactual 缺失、字段只能 proxy 构造等情况显式写入 `trace_support_audit.csv`。
3. ED1 不得为了补 counterfactual 而输出 OrderIntent、target_weight、target_position、quantity 或 broker/order 字段。
4. ED1 的候选规则审计只能回答“是否存在可预声明 hypothesis”，不得执行 rule return replay。

## 6. 下一步 Gate

允许进入：

```text
RAL-ED1: Score / Rank / Regime / Holding Attribution Diagnostic
```

ED1 只允许：

```text
1. 构建/审计 trace-level attribution diagnostic；
2. 输出 score/rank/regime/holding/cost 诊断表；
3. 产出 candidate_rule_hypothesis_audit.csv；
4. 写 diagnostic_findings.md；
5. 判断是否存在至少一个低维、可预声明、非模型化、非 baseline-clone、非 no_extra_action 的 hypothesis。
```

ED1 不允许：

```text
1. 跑 RAL-ED2 rule sanity；
2. 跑规则收益回放；
3. 训练任何模型；
4. 使用 strict_test；
5. 输出 OrderIntent / target_weight / target_position / quantity / broker order；
6. provider/latest/monitor/frontend/Agent/production 扩权。
```

如果 ED1 没有找到满足主线条件的明确 hypothesis，必须 STOP 回统筹，不得进入 RAL-ED2。
