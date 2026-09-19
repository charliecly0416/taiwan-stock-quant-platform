---
created_at: 2026-06-24
status: work_doc
phase: RCPT5A_OPTION_A_2021_PIT_FEATURE_REPAIR_DIAGNOSTIC
parent_review: docs/tw_portfolio_decision_model/POLICY_RCPT5_STRICT_OOS_DESIGN_DECISION_REVIEW_CN.md
target_rule: RCPT1_RULE_05
window: 2021_pre_2022_sanity_diagnostic
diagnostic_only: true
strict_oos: false
strict_test_authorized: false
production_allowed: false
model_training_authorized: false
---

# RCPT5A Option A: 2021 PIT Feature Repair + Pre-2022 Diagnostic 工作文档

## 1. 背景

RCPT5 审查通过的路线选择为：

```text
Option A -> Option B(qlib-only) -> Option C fallback -> Option D stop fallback
```

当前授权执行 Option A：

```text
补齐 2021 PIT market feature，
冻结 RCPT1_RULE_05，
做 2021 pre-2022 sanity diagnostic。
```

2021 的语义只能是：

```text
pre-2022 sanity diagnostic
```

不能写成：

```text
strict OOS
final OOS
independent test
```

## 2. 目标

本阶段要回答：

```text
在 2022 候选发现之前的 2021 窗口，
冻结的 RULE_05 是否已经明显失真、过度现金化、费用过高或机制不成立？
```

通过只能说明：

```text
RULE_05 没有在 pre-2022 sanity diagnostic 中提前暴露明显失败。
```

失败则应阻断进入 Option B，除非失败来自可修复的数据覆盖问题，而不是规则机制问题。

## 3. 非目标

本阶段不授权：

```text
1. strict_test；
2. 训练 qlib/LTR/policy 模型；
3. 使用 qlib+LTR；
4. 新增或调整 RULE_05 阈值；
5. 新增 buy-side gate、cash target、score/rank threshold；
6. 使用 2021 replay 结果调规则后重跑；
7. 修改 production/default/provider/frontend/Agent/monitor/order 链路；
8. 输出 OrderIntent、target_weight、target_position、quantity_instruction。
```

## 4. 必读输入

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT5_STRICT_OOS_DESIGN_DECISION_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT5_STRICT_OOS_DESIGN_DECISION_WORK_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt5_strict_oos_design_decision/recommended_route.md
data_tw/experiments/risk_control_policy_2022/rcpt5_strict_oos_design_decision/rule05_frozen_contract.md
data_tw/experiments/risk_control_policy_2022/rcpt5_strict_oos_design_decision/strict_oos_gate_contract.md
data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/diagnostic_model_signal.csv
data_tw/experiments/risk_control_policy_2022/rcpt4_rule05_mechanism_attribution/2021_not_available_audit.json
scripts/run_tw_policy_rcpt2_adaptive_threshold_replay_sanity.py
```

执行者必须参考 RCP3A 的 2022 PIT market feature 产物和实现方式：

```text
data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate/market_feature_by_signal_date.csv
docs/tw_portfolio_decision_model/POLICY_RCP3A_MARKET_FEATURE_COVERAGE_PIT_GATE_EXECUTION_REPORT_CN.md
```

## 5. 允许的数据修复

只允许做：

```text
从既有本地 TWII / market index / normalized price source
按 RCP3A 等价 PIT MA60 derivation contract
生成 2021 signal_date 对应的 market feature。
```

要求：

```text
1. 不下载外部新数据；
2. 不补 2021 之后的未来值；
3. MA60 必须只使用 signal_date 当日及之前数据；
4. 缺值必须审计，不得静默 forward-fill 到不可解释；
5. 输出 feature coverage audit。
```

## 6. RULE_05 冻结要求

必须严格沿用 RCPT5 冻结合同：

```text
risk_off
len(holdings) > 1
rank_change_5d > 0 或 rank_change_3d > 0
not pass_rule03_combined_support
max_early_sell_per_day = 1
```

禁止：

```text
新增 buy-side gate
新增 cash target
调整 score/rank/MA/mid-band/trend/cash/fee 阈值
根据 2021 结果重跑
```

## 7. 输出要求

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt5a_option_a_2021_pit_feature_repair_diagnostic/
```

必须生成：

```text
manifest.json
market_feature_2021_by_signal_date.csv
market_feature_coverage_audit.csv
rule05_2021_replay_summary.csv
rule05_2021_baseline_comparison.csv
rule05_2021_gate_decision.csv
rule05_2021_monthly_comparison.csv
rule05_2021_cash_exposure_audit.csv
rule05_2021_fee_tax_reconciliation.csv
rule05_2021_concentration_audit.csv
rule05_2021_trigger_attribution.csv
diagnostic_semantics_audit.json
forbidden_action_audit.csv
validator_report.json
diagnostic_findings.md
```

可生成 per-rule 子目录，但必须标注为 internal replay ledger only，不得输出 OrderIntent。

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT5A_OPTION_A_2021_PIT_FEATURE_REPAIR_DIAGNOSTIC_EXECUTION_REPORT_CN.md
```

## 8. Gate

本阶段不是 strict OOS gate，但必须做 sanity gate：

必须报告：

```text
net_return_after_fee_tax
gross_return
max_drawdown
participation_rate
average_cash_rate
max_cash_rate
cash > 80% day share
cash > 90% day share
average_holding_count
buy_count / sell_count / action_count
fee_and_tax / commission / tax
turnover_proxy
symbol/month/trigger concentration
future-label forbidden audit
no-retuning audit
```

通过倾向：

```text
1. 不出现 all-cash/no-trade；
2. cash exposure 没有明显失控；
3. fee/tax 没有吞噬主要收益；
4. RULE_05 trigger 可复核；
5. 相对 baseline 没有灾难性退化；
6. 机制归因不集中到单一股票、单一月份或极少数 trigger。
```

失败或停止：

```text
1. 2021 feature repair 无法 PIT-safe 完成；
2. replay 依赖新增外部数据；
3. frozen RULE_05 无法还原；
4. 出现 all-cash/no-trade；
5. 费用、现金或集中度显示机制明显不可泛化；
6. 发现 future leakage、阈值调参或 forbidden action。
```

## 9. 审查者职责

审查者必须判断：

```text
1. 2021 market feature 是否 PIT-safe；
2. 2021 语义是否保持 pre-2022 sanity diagnostic；
3. RULE_05 是否冻结；
4. 是否没有新增阈值/训练/strict_test/生产链路；
5. 结果是否足以进入 Option B qlib-only strict OOS 设计；
6. 如果失败，失败是数据覆盖问题还是机制问题。
```

审查结论只能是：

```text
PASS_READY_FOR_OPTION_B_QLIB_ONLY_STRICT_OOS_WORK_DOC
FAIL_NEEDS_RCPT5A_REPAIR
STOP_RULE05_FAILS_PRE_2022_SANITY
STOP_SCOPE_OR_DIAGNOSTIC_SEMANTICS_VIOLATION
```

## 10. 执行者命令

```text
请执行 RCPT5A Option A。
补齐 2021 PIT market feature，冻结 RULE_05，做 2021 pre-2022 sanity diagnostic。
不得训练、不得 strict_test、不得调阈值、不得生产化、不得输出订单或 target 字段。
```
