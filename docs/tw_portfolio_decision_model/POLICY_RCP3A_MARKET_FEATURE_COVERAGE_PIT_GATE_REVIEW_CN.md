---
created_at: 2026-06-24
status: rcp3a_independent_review
phase: RCP3A_MARKET_FEATURE_COVERAGE_PIT_GATE
work_doc: docs/tw_portfolio_decision_model/POLICY_RCP3A_MARKET_FEATURE_COVERAGE_PIT_GATE_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_RCP3A_MARKET_FEATURE_COVERAGE_PIT_GATE_EXECUTION_REPORT_CN.md
prior_review: docs/tw_portfolio_decision_model/POLICY_RCP2_RISK_CONTROL_RULE_DESIGN_CONTRACT_REVIEW_CN.md
artifact_root: data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate
verdict: PASS_READY_FOR_RCP3_RISK_CONTROL_REPLAY_SANITY_WORK_DOC
reviewer_role: independent_reviewer
readonly_review: true
baseline_replay_performed_by_reviewer: false
risk_control_replay_performed_by_reviewer: false
model_training_performed_by_reviewer: false
strict_test_performed_by_reviewer: false
production_or_order_chain_change_performed_by_reviewer: false
---

# RCP3A Market Feature Coverage / PIT Gate 独立审查报告

## 1. Verdict

`PASS_READY_FOR_RCP3_RISK_CONTROL_REPLAY_SANITY_WORK_DOC`

RCP3A 执行产物满足工作文档要求。`TWII.csv` 源真实存在且可读，字段 `date / close` 可用；RCP1A 2022 signal dates 覆盖为 246/246；`market_index_ma60` 口径为当日及过去 59 个可用市场行的 rolling mean，`min_periods = 60`，未发现未来价格、2022 replay 结果选特征或阈值挖掘。

本结论只授权进入 RCP3 risk-control replay sanity 工作文档；不授权 strict_test、生产化、provider/default 切换、frontend/Agent 集成或任何订单链路输出。

## 2. 必需文件审查

RCP3A 输出目录下必需文件齐全：

```text
manifest.json
market_feature_source_inventory.csv
market_feature_coverage_audit.csv
market_feature_pit_audit.csv
market_ma_derivation_contract.json
market_feature_by_signal_date.csv
rule_market_dependency_gate.csv
missing_market_feature_policy.csv
anti_overfit_and_no_2022_feature_selection_audit.csv
diagnostic_semantics_audit.json
forbidden_action_audit.csv
validator_report.json
diagnostic_findings.md
```

`validator_report.json` 为 `status = PASS`、`pass = true`、`rcp3_replay_authorizable = true`、`repair_required = false`，推荐下一步为：

```text
PASS_READY_FOR_RCP3_RISK_CONTROL_REPLAY_SANITY_WORK_DOC
```

## 3. Market Source 审查

市场指数源：

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TWII.csv
```

审查结果：

```text
exists = True
readable = True
row_count = 2771
source_window = 2015-01-05..2026-05-21
date_column = date
close_column = close
close_numeric = True
close_missing_count = 0
close_nonpositive_count = 0
```

源文件前几行实际包含 `symbol,date,open,high,low,close,volume,vwap,factor`，符合本轮需要的 `date / close` 字段。

## 4. Coverage / MA60 / PIT 审查

执行产物记录：

```text
required_window = 2022-01-03..2022-12-30
required_signal_date_count = 246
matched_signal_date_count = 246
missing_signal_date_count = 0
ma60_available_count = 246
ma60_missing_count = 0
coverage_status = PASS
```

我用只读复算抽查 RCP1A signal dates、TWII exact join 和 MA60：

```text
signal_dates_2022 = 246
unique_feat_dates = 246
twii_matches = 246
feat_rows = 246
feature_available_all = True
pit_safe_all = True
ma60_null_recalc = 0
close_max_abs_diff = 0.0
ma60_max_abs_diff = 1.8189894035458565e-12
risk_off_count_feat = 174
```

`ma60_max_abs_diff` 仅为浮点精度误差。`market_feature_by_signal_date.csv` 每个 2022 signal_date 都有 `feature_available = True`、`pit_safe = True`，且 `ma60_observation_count = 60`。

MA60 合同明确：

```text
market_index_ma60 = rolling_mean(market_index_close, window=60, min_periods=60)
uses_current_day_close = true
uses_previous_available_market_rows = 59
uses_future_price = false
calendar_policy = use available TWII market rows; exact signal_date join required for 2022 replay dates
```

该口径符合工作文档要求：使用当日和历史 close，不使用未来价格。

## 5. Rule Dependency Gate 审查

`rule_market_dependency_gate.csv` 正确覆盖 RCP2 的 6 条规则：

```text
RCP2_RULE_01 = PASS, can_enter_rcp3_replay = True
RCP2_RULE_02 = PASS, can_enter_rcp3_replay = True
RCP2_RULE_03 = NOT_REQUIRED_PASS, can_enter_rcp3_replay = True
RCP2_RULE_04 = NOT_REQUIRED_PASS, can_enter_rcp3_replay = True
RCP2_RULE_05 = PASS, can_enter_rcp3_replay = True
RCP2_RULE_06 = PASS, can_enter_rcp3_replay = True
```

其中 RCP2_RULE_01/02/05/06 依赖 `market_index_close / market_index_ma60`，本轮 market feature gate 通过后可进入 RCP3 工作文档授权范围。RCP2_RULE_03/04 不依赖市场 MA，`NOT_REQUIRED_PASS` 处理正确。

## 6. Missing Policy / Anti-overfit 审查

缺失策略已在 replay 前预声明：

```text
source_file_missing -> block all market-dependent rules before RCP3 replay
missing_close_on_signal_date -> block market-dependent rules; no future nearest-date fill
ma60_insufficient_history -> block market-dependent rules for 2022 replay dates
nonpositive_close -> block market-dependent rules and require source repair
```

未发现允许未来补值、事后选择替代指数、按 2022 replay 结果选择特征或调整 MA 窗口的口径。

`anti_overfit_and_no_2022_feature_selection_audit.csv` 显示：

```text
candidate_market_source_predeclared = PASS
ma_window_predeclared = PASS
no_replay_or_return_mining = PASS
missing_policy_predeclared = PASS
```

## 7. Forbidden Actions 审查

`forbidden_action_audit.csv` 和执行报告一致，未发现越权动作：

```text
baseline_replay = False
risk_control_replay = False
model_training = False
strict_test = False
registry_default_change = False
provider_publish_or_accepted_latest_switch = False
frontend_agent_monitor_integration = False
broker_order_quick_trade = False
OrderIntent_output = False
target_weight_output = False
target_position_output = False
quantity_instruction_output = False
2022_replay_result_feature_selection = False
future_return_or_label_usage = False
```

2022 语义保持为：

```text
strict_oos_2022 = false
diagnostic_only = true
semantic_label = downturn_validation_diagnostic_only
```

## 8. RCP3 前置提醒

RCP3 可以进入 risk-control replay sanity 工作文档，但仍需保持以下限制：

```text
1. RCP3 仍是 2022 downturn validation diagnostic，不是 strict OOS / final OOS。
2. RCP3 只能回放 RCP2 已冻结规则，不得用 2022 结果新增规则、换指数、换 MA 窗口或调阈值。
3. RCP3 必须继续审计 cash/no-trade、fee/tax、turnover、drawdown、concentration 和 action ledger。
4. RCP3 通过也不自动授权 strict_test 或生产化。
```
