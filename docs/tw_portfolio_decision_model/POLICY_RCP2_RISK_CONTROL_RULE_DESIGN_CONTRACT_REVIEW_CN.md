---
created_at: 2026-06-24
status: rcp2_independent_review
phase: RCP2_RISK_CONTROL_RULE_DESIGN_CONTRACT
work_doc: docs/tw_portfolio_decision_model/POLICY_RCP2_RISK_CONTROL_RULE_DESIGN_CONTRACT_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_RCP2_RISK_CONTROL_RULE_DESIGN_CONTRACT_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/risk_control_policy_2022/rcp2_risk_control_rule_design_contract
verdict: PASS_READY_FOR_RCP3_RISK_CONTROL_REPLAY_SANITY_WORK_DOC
reviewer_role: independent_reviewer
readonly_only: true
simulation_only: true
risk_control_replay_performed_by_reviewer: false
baseline_replay_performed_by_reviewer: false
model_training_performed_by_reviewer: false
strict_test_performed_by_reviewer: false
production_or_provider_change_performed_by_reviewer: false
---

# RCP2 Risk-control Rule Design Contract 独立审查报告

## 1. Verdict

`PASS_READY_FOR_RCP3_RISK_CONTROL_REPLAY_SANITY_WORK_DOC`

RCP2 执行产物满足工作文档要求：必需文件齐全，6 条规则为低维、可解释、预声明的风险控制候选；规则字段、阈值来源、anti-overfit、cash/no-trade、evaluation metric 与 forbidden action 审计均可用于 RCP3 前置审查。

本轮通过不代表规则有效，也不代表可以直接进入生产。RCP2 只证明规则设计合同可审查；RCP3 才允许在统筹授权后做 `downturn validation diagnostic` 口径的 risk-control replay sanity。

RCP3 的硬性前置条件：

```text
在运行任何 risk-control replay 前，必须先完成 market feature coverage / PIT gate。
market_index_close / market_index_ma60 若不能 PIT-safe 覆盖 2022 replay 所需日期，
依赖 market MA 的规则必须 stop 或 repair，不能在 replay 后再发现缺失，
也不能临时用 2022 收益选择替代特征或阈值。
```

## 2. Findings

### Critical

无。

### High

无。

### Medium

1. `feature_availability_contract.csv` 中 `market_index_close` 与 `market_index_ma60` 标为 `partial`。这不阻塞 RCP2，因为 RCP2 只做规则设计合同；但它必须阻塞 RCP3 replay 的直接执行。RCP3 工作文档必须把 market index 数据覆盖、MA 计算口径、`signal_date / available_at` 对齐、缺失处理写成 replay 前置 gate。

2. `RCP2_RULE_03`、`RCP2_RULE_04` 依赖 replay 过程中的历史 NAV / action ledger 状态。这类状态可以 PIT-safe，但 RCP3 必须证明只读取 `signal_date` 当日以前已经形成的组合状态，不得使用最终回放结果、未来 NAV、未来 fee/tax 或事后 drawdown 最低点。

3. `RCP2_RULE_05` 是 accelerated sell，理论上可能增加换手和税费。RCP2 已预声明每日最多一支 accelerated sell，RCP3 必须把该上限、fee/tax gate、turnover gate 作为硬约束，避免风险控制反而放大成本。

### Low

1. 6 条规则中有 4 条依赖 market MA 风险状态，机制上不算无界 grid，但 RCP3 报告需要按规则族分别解释，避免事后把多个 MA 依赖规则当成隐式组合调参。

2. `evaluation_metric_contract.csv` 中 `symbol_date_concentration` baseline 值为 `not_reported`，但已设为 RCP3 hard gate。RCP3 必须补 concentration audit，不能因 baseline 未报告而跳过。

## 3. Mainline Compliance

RCP2 符合主线和工作文档边界：

```text
只做 risk-control rule design contract
不运行 baseline replay
不运行 risk-control replay
不训练模型
不做 strict_test
不修改 registry/default/provider/frontend/Agent/订单链路
不输出 OrderIntent
不输出 target_weight / target_position / quantity_instruction
不使用 2022 收益、2022 grid search、future return 或 label 调阈值
```

2022 语义保持为：

```text
strict_oos_2022 = false
diagnostic_only = true
semantic_label = downturn_validation_diagnostic_only
```

## 4. Evidence Checked

已读取并审查：

```text
docs/tw_portfolio_decision_model/POLICY_RCP2_RISK_CONTROL_RULE_DESIGN_CONTRACT_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RCP2_RISK_CONTROL_RULE_DESIGN_CONTRACT_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RCP_RISK_CONTROL_POLICY_2022_DOWNTURN_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RCP1B_DIAGNOSTIC_BASELINE_REPLAY_AUDIT_REVIEW_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
```

已审查 RCP2 输出目录下全部必需产物：

```text
manifest.json
risk_control_rule_design_manifest.json
predeclared_rule_candidates.csv
threshold_source_audit.csv
feature_availability_contract.csv
rule_dependency_contract.csv
evaluation_metric_contract.csv
anti_overfit_and_no_2022_mining_audit.csv
cash_no_trade_guardrail_contract.csv
diagnostic_semantics_audit.json
forbidden_action_audit.csv
validator_report.json
diagnostic_findings.md
```

文件齐全，`validator_report.json` 为：

```text
status = PASS
required_files_status = PASS
candidate_rule_count = 6
rule_contract_status = PASS
threshold_source_status = PASS
feature_availability_status = PASS_WITH_RCP3_INDEX_FIELD_AUDIT_REQUIRED
evaluation_metric_status = PASS
anti_overfit_status = PASS
cash_no_trade_guardrail_status = PASS
diagnostic_semantics_status = PASS
forbidden_actions_status = PASS
rcp3_authorizable = true
recommended_next_step = PASS_READY_FOR_RCP3_RISK_CONTROL_REPLAY_SANITY_WORK_DOC
```

## 5. Rule Design Review

RCP2 冻结了 6 条规则：

```text
RCP2_RULE_01 Market MA60 Risk-off Buy Gate
RCP2_RULE_02 Market MA60 Plus Strong Rank Gate
RCP2_RULE_03 Portfolio Drawdown Brake 10pct Cooldown
RCP2_RULE_04 Rolling 20D Turnover Cost Brake
RCP2_RULE_05 Risk-off Weak Holding Accelerated Sell
RCP2_RULE_06 Defensive Holding Continuation
```

规则数量符合 4-8 个的有限候选要求，覆盖 RCP1B 暴露的问题：

```text
深回撤
下跌趋势中持续买入
高 turnover
fee/tax 拖累
弱持仓继续暴露
频繁替换导致的错误再投资
```

每条规则均包含：

```text
allowed_inputs
trigger_definition
action_effect
threshold_values
threshold_source
expected_tradeoff
risk_of_all_cash_or_no_trade
expected_turnover_effect
expected_fee_tax_effect
expected_drawdown_effect
```

阈值来源均为 `fixed_rationale`，未使用：

```text
2022_return_optimized
2022_grid_search
2022_best_threshold_selection
future_return_label
posthoc_drawdown_minimization
```

未发现同一机制过密调参：每个 rule family 的 `grid_size = 1`，候选不是 MA60/MA120/多窗口/多阈值的收益择优组合。

## 6. Feature Availability Gate

`feature_availability_contract.csv` 的处理合理：

```text
candidate_rank / buy_score / holding_rank / current_holdings / holding_days / portfolio_drawdown / rolling_20d_action_count / signal_date
```

均被声明为可由 RCP1A/RCP1B 或 RCP3 replay 状态 PIT-safe 获得。

但：

```text
market_index_close = partial
market_index_ma60 = partial
```

因此 RCP3 不能直接跑 replay。RCP3 必须先输出并通过：

```text
market_feature_coverage_audit.csv
market_feature_pit_audit.csv
market_ma_derivation_contract.json
missing_market_feature_policy.csv
```

最低要求：

```text
1. 明确指数来源，例如 TAIEX/TWII 或项目内等价市场指数；
2. 覆盖 2022 replay 所需 signal dates；
3. MA60 只使用当日及历史 close，不能使用未来价格；
4. 明确 min_periods 与起始窗口不足处理；
5. 缺失时 block/skip 必须预声明，不能按 replay 结果选择；
6. 不得在 replay 后补选替代特征。
```

## 7. Cash / No-trade Guardrail

`cash_no_trade_guardrail_contract.csv` 足够防止 all-cash/no-trade 伪通过：

```text
min_participation_rate = 0.50
max_average_cash_rate = 0.60
max_no_position_days = 20
all_cash_disallowed = true
sell_only_policy_disallowed = true
no_trade_policy_disallowed = true
minimum_action_count_relative_to_baseline = 0.20
baseline_action_count = 478
```

RCP3 不能只用低回撤通过，必须同时满足 participation、cash、action count、net return、turnover/fee/tax 和 diagnostic semantics gate。

## 8. Evaluation Metric Contract

`evaluation_metric_contract.csv` 冻结清楚，且符合 RCP 主线的风险收益 tradeoff 口径。

RCP3 通过不能依赖单指标，至少必须同时审查：

```text
max_drawdown materially improves
net_return_after_fee_tax deterioration <= 5 percentage points vs baseline
turnover_proxy / fee_and_tax not worse unless net and drawdown both materially improve
participation_rate >= 0.50
average_cash_rate <= 0.60
no_trade_cash_status = PASS
symbol/date concentration = PASS
diagnostic_semantics preserved
```

RCP1B baseline 仍是：

```text
net_return_after_fee_tax = -0.33609220
max_drawdown = -0.42634734
turnover_proxy = 48.45575343
fee_and_tax = 112,926.17
participation_rate = 0.99593496
```

## 9. Forbidden Actions Audit

审查确认 RCP2 及本次审查未执行：

```text
baseline replay
risk-control replay
model training
strict_test
registry/default 修改
provider publish / accepted latest switch
frontend / Agent / monitor integration
broker / quick-trade / real order
OrderIntentArtifact 输出
target_weight / target_position / quantity_instruction 输出
2022 threshold mining
future return / label usage
```

本次审查只新增本审查报告，未修改执行产物。

## 10. Missing Evidence Or Open Questions

RCP2 无需 repair。

RCP3 前必须解决：

```text
1. market_index_close / market_index_ma60 的 PIT-safe 覆盖；
2. MA60 计算口径和缺失处理；
3. RCP3 replay engine 如何仅使用历史 NAV/action ledger 状态；
4. accelerated sell 的每日上限和成本 gate；
5. concentration audit 的具体输出格式。
```

这些不是 RCP2 阻塞项，但必须写入 RCP3 工作文档的前置 gate。

## 11. Next Work Document

授权统筹撰写并进入：

```text
RCP3: Risk-control Replay Sanity
```

RCP3 建议拆成两个子步骤，避免在数据未确认时直接跑 replay：

```text
RCP3A: Market Feature Coverage / PIT Gate
RCP3B: Predeclared Risk-control Replay Sanity
```

RCP3A 只允许做 market feature 覆盖与 PIT 审计；若失败，则 stop 或 repair。

RCP3B 只允许在 RCP3A 通过后，使用 RCP2 预声明的 6 条规则做 diagnostic replay sanity。不得新增规则、删规则、改阈值、按 2022 结果筛规则或调参。

## 12. Command For Coordinator

```text
RCP2 已通过独立审查，verdict = PASS_READY_FOR_RCP3_RISK_CONTROL_REPLAY_SANITY_WORK_DOC。
请撰写 RCP3 工作文档，并把 market feature coverage / PIT gate 放在任何 risk-control replay 之前。
RCP3 不得在 replay 后才发现 market_index_close / market_index_ma60 缺失；
不得用 2022 收益、2022 grid search、future return 或 label 调阈值；
不得训练、strict_test、修改生产链路或输出订单/目标仓位/数量指令。
```
