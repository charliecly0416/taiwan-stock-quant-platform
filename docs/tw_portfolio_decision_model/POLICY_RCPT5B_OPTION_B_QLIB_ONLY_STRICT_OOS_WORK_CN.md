---
created_at: 2026-06-24
status: work_doc
phase: RCPT5B_OPTION_B_QLIB_ONLY_STRICT_OOS
parent_review: docs/tw_portfolio_decision_model/POLICY_RCPT5A_OPTION_A_2021_PIT_FEATURE_REPAIR_DIAGNOSTIC_REVIEW_CN.md
target_rule: RCPT1_RULE_05
window: 2023_2025_qlib_only_test_fold
strict_oos_candidate: true
qlib_only: true
ltr_allowed: false
model_training_authorized: false
strict_test_authorized: false
production_allowed: false
---

# RCPT5B Option B: 2023-2025 Qlib-only Strict OOS 工作文档

## 1. 背景

RCPT5A 审查结论：

```text
PASS_READY_FOR_OPTION_B_QLIB_ONLY_STRICT_OOS_WORK_DOC
```

2021 pre-2022 sanity diagnostic 显示：

```text
RULE_05 收益低于 baseline，但最大回撤明显改善；
它是风险控制 tradeoff，不是收益增强证据；
未提前暴露机制失败、all-cash/no-trade、费用漏算或 PIT 问题。
```

因此进入 Option B：

```text
使用 2023-2025 TEST fold 的 qlib-only frozen score/rank，
对冻结 RULE_05 做首个 strict OOS candidate replay。
```

## 2. 目标

本阶段要回答：

```text
在 2023-2025 qlib-only TEST fold 上，
冻结 RULE_05 是否仍能形成可接受的风险控制 tradeoff，
且没有现金、集中度、费用、未来泄漏或训练/选择污染伪通过？
```

本阶段允许称为：

```text
qlib-only strict OOS candidate
```

前提是执行者和审查者确认：

```text
1. 只使用 TEST.csv 的 frozen qlib score/rank；
2. qlib train window 为 2015-05-04..2020-12-31；
3. 2023-2025 没有参与 RULE_05 阈值、规则、policy 或本轮 replay 选择；
4. 不引入 LTR；
5. 不训练、不调阈值、不重跑优化。
```

## 3. 非目标

本阶段不授权：

```text
1. qlib/LTR/policy 模型训练；
2. 使用 qlib+LTR、orthogonal LTR 或任何 LTR score；
3. 修改 RULE_05 阈值或新增规则；
4. 根据 2023-2025 结果调参后重跑；
5. production/default/provider/frontend/Agent/monitor/order 链路改动；
6. OrderIntent、target_weight、target_position、quantity_instruction；
7. broker / quick-trade / real order；
8. 把 2022 或 2021 写成 strict OOS 证据。
```

## 4. 必读输入

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT5A_OPTION_A_2021_PIT_FEATURE_REPAIR_DIAGNOSTIC_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT5_STRICT_OOS_DESIGN_DECISION_REVIEW_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt5_strict_oos_design_decision/recommended_route.md
data_tw/experiments/risk_control_policy_2022/rcpt5_strict_oos_design_decision/rule05_frozen_contract.md
data_tw/experiments/risk_control_policy_2022/rcpt5_strict_oos_design_decision/strict_oos_gate_contract.md
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/TEST.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/TEST.manifest.json
scripts/run_tw_policy_rcpt5a_option_a_2021_pit_feature_repair_diagnostic.py
scripts/run_tw_policy_rcpt2_adaptive_threshold_replay_sanity.py
```

执行者可以复用 RCPT5A/RCPT2 的 replay accounting 逻辑，但必须确保：

```text
1. 输入 signal 来自 TEST.csv qlib-only frozen score/rank；
2. 输出语义是 2023-2025 qlib-only strict OOS candidate；
3. 内部 ledger 只能标注为 accounting ledger，不是订单或持仓建议。
```

## 5. 必做前置审计

执行者必须先生成并通过：

```text
contamination_audit.csv
signal_lineage_audit.json
market_feature_coverage_audit.csv
price_coverage_audit.csv
rule05_freeze_audit.csv
strict_oos_gate_freeze.json
```

### 5.1 污染审计

必须确认：

```text
1. TEST.manifest qlib_train_start/end = 2015-05-04..2020-12-31；
2. TEST score_window = 2023-01-01..2025-06-30；
3. use_frozen_pred = true；
4. training_performed = false；
5. parameter_search_performed = false；
6. 本阶段不读取 LTR score；
7. 本阶段不把 2023-2025 结果用于阈值选择。
```

如果发现 2023-2025 已无法与 LTR/policy/strategy selection 污染隔离，必须停止，不能强行声称 strict OOS。

### 5.2 现金口径冻结

Option B 必须冻结现金口径：

```text
primary_average_cash_rate = mean(cash / equity)
primary_max_cash_rate = max(cash / equity)
aux_cash_to_initial_cash = cash / initial_cash
```

gate 使用 `cash / equity` 作为主口径。`cash / initial_cash` 只用于解释，不得作为通过主口径。

### 5.3 Gate 数值冻结

本阶段预声明 gate：

```text
participation_rate >= 0.90
primary_average_cash_rate <= 0.65
cash_gt_90pct_equity_day_share <= 0.25
average_holding_count >= 2.0
buy_count >= 25% baseline_buy_count
sell_count >= 25% baseline_sell_count
max_drawdown_delta > 0
net_return_delta >= -0.15
fee_tax_delta_abs <= max(0.50 * abs(net_return_delta_cash_value), 0.05 * initial_cash)
top_instrument_benefit_share <= 0.35
top_month_benefit_share <= 0.55
top_trigger_day_benefit_share <= 0.25
```

解释：

```text
RULE_05 是风险控制 tradeoff；
因此允许收益低于 baseline，但 net_return_delta 不能低于 -15 个百分点；
且必须改善 max_drawdown。
```

如果执行者认为某个数值无法从现有 artifact 计算，必须写明并停止，不得临时改 gate。

## 6. RULE_05 冻结合同

必须严格沿用：

```text
risk_off
len(holdings) > 1
rank_change_5d > 0 OR rank_change_3d > 0
not pass_rule03_combined_support
max_early_sell_per_day = 1
```

禁止：

```text
新增 buy-side gate
新增 cash target
调整 score/rank/MA/mid-band/trend/cash/fee 阈值
根据 2023-2025 结果调参后重跑
```

## 7. 输出要求

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt5b_option_b_qlib_only_strict_oos/
```

必须生成：

```text
manifest.json
contamination_audit.csv
signal_lineage_audit.json
market_feature_2023_2025_by_signal_date.csv
market_feature_coverage_audit.csv
price_coverage_audit.csv
rule05_freeze_audit.csv
strict_oos_gate_freeze.json
rule05_2023_2025_replay_summary.csv
rule05_2023_2025_baseline_comparison.csv
rule05_2023_2025_gate_decision.csv
rule05_2023_2025_monthly_comparison.csv
rule05_2023_2025_cash_exposure_audit.csv
rule05_2023_2025_fee_tax_reconciliation.csv
rule05_2023_2025_concentration_audit.csv
rule05_2023_2025_trigger_attribution.csv
diagnostic_semantics_audit.json
forbidden_action_audit.csv
validator_report.json
diagnostic_findings.md
```

可生成：

```text
internal_replay_ledgers_not_order_intent/
```

但该目录下所有交易字段只能是 replay accounting ledger，不得被命名为 OrderIntent 或 real order。

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT5B_OPTION_B_QLIB_ONLY_STRICT_OOS_EXECUTION_REPORT_CN.md
```

## 8. Pass / Fail / Stop

通过条件：

```text
1. contamination audit PASS；
2. market feature 和 price coverage PASS；
3. RULE_05 freeze audit PASS；
4. strict OOS gate freeze 已落盘；
5. max_drawdown 改善；
6. net_return_delta 不低于 -15 个百分点；
7. 现金、参与度、费用、集中度 gate 全部通过；
8. 未发现 future leakage、调阈值、训练、LTR、生产链路或订单输出。
```

失败条件：

```text
1. RULE_05 机制可执行但结果未通过 gate；
2. 收益劣化超过容忍带；
3. 回撤没有改善；
4. 现金/费用/集中度伪通过。
```

停止条件：

```text
1. TEST fold 污染无法隔离；
2. market feature 或 price coverage 无法 PIT-safe 构造；
3. frozen RULE_05 无法还原；
4. 发现 LTR 输入、训练、调参、future leakage 或 production/order 越权。
```

## 9. 审查者职责

审查者必须判断：

```text
1. 是否真的 qlib-only；
2. TEST fold lineage 是否支持 strict OOS candidate；
3. 2023-2025 是否没有被本轮规则/阈值选择污染；
4. PIT market feature 与 price coverage 是否安全；
5. RULE_05 是否冻结；
6. cash/equity 口径是否正确；
7. gate 是否在 replay 前冻结并被严格执行；
8. 结果是否可称为 qlib-only strict OOS candidate pass/fail；
9. 是否没有生产、订单或 target 字段越界。
```

审查结论只能是：

```text
PASS_QLIB_ONLY_STRICT_OOS_CANDIDATE_ACCEPTED_FOR_COORDINATOR_CLOSURE
FAIL_RULE05_DOES_NOT_PASS_QLIB_ONLY_STRICT_OOS
FAIL_NEEDS_RCPT5B_REPAIR
STOP_CONTAMINATION_OR_SCOPE_VIOLATION
```

## 10. 执行者命令

```text
请执行 RCPT5B Option B。
使用 2023-2025 TEST.csv 的 qlib-only frozen score/rank，
冻结 RULE_05 与 strict OOS gate，
做 qlib-only strict OOS candidate replay。
不得训练、不得 LTR、不得调阈值、不得生产化、不得输出订单或 target 字段。
```
