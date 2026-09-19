---
created_at: 2026-06-24
status: research_closure_package_completed
phase: RCPT6_RESEARCH_CLOSURE_PACKAGE
route: RCPT_RISK_CONTROL_THRESHOLD_ROUTE
coordinator_closure: docs/tw_portfolio_decision_model/POLICY_RCPT_RISK_CONTROL_THRESHOLD_ROUTE_COORDINATOR_CLOSURE_CN.md
final_candidate: RCPT1_RULE_05
final_verdict: SUCCESS_AS_QLIB_ONLY_RISK_CONTROL_CANDIDATE
qlib_only: true
ltr_used: false
production_allowed: false
order_or_target_output_allowed: false
---

# RCPT6 Research Closure Package

## 1. Executive Summary

本 research closure package 汇总 RCPT 风险控制阈值路线的最终结论：

```text
RCPT1_RULE_05 是一个 qlib-only risk-control overlay candidate。
```

它通过的证据范围是：

```text
1. 2022 downturn validation diagnostic：候选发现与机制归因；
2. 2021 pre-2022 sanity diagnostic：未提前暴露机制失败；
3. 2023-2025 qlib-only strict OOS candidate：在 repaired fee/tax gate 下通过。
```

最终可接受表述：

```text
RULE_05 在 qlib-only 信号上可作为防守型风险控制候选：
收益低于 baseline，但最大回撤显著改善，费用更低，且通过现金、集中度、PIT、污染和禁区审计。
```

不可接受表述：

```text
1. RULE_05 是收益增强策略；
2. RULE_05 已可生产上线；
3. RULE_05 已在 qlib+LTR 上验证；
4. RULE_05 可输出 OrderIntent / target_weight / target_position / quantity_instruction；
5. RCPT5B 原失败产物可以被事后改判 PASS。
```

## 2. Project Context

本项目当前已有较强 ranking / signal 体系：

```text
1. qlib alpha model；
2. qlib + orthogonal LTR 主线；
3. baseline policy 以模型排名作为主要买卖依据。
```

此前多轮 policy / ML / RL / rule search 表明：

```text
试图在买入侧重新学习或替代 qlib ranking baseline，很难稳定带来收益提升。
```

RCPT 路线转向更窄的问题：

```text
不替代 ranking model；
不重新做 alpha；
只研究在市场 risk-off 时，是否能更早卖出排名恶化的弱持仓，从而降低回撤。
```

因此 RCPT 的目标不是追求最高收益，而是：

```text
降低最大回撤和尾部风险，同时避免 all-cash/no-trade、费用漏算、集中度伪改善和未来泄漏。
```

## 3. Final Candidate Rule

最终候选：

```text
RCPT1_RULE_05
```

冻结规则语义：

```text
risk_off
len(holdings) > 1
rank_change_5d > 0 OR rank_change_3d > 0
not pass_rule03_combined_support
max_early_sell_per_day = 1
```

解释：

```text
当市场处于 risk-off 状态，
且已有持仓排名在 3 日或 5 日维度恶化，
且该持仓不再满足 mid-band / trend support，
则每日最多提前卖出 1 笔弱化持仓。
```

规则边界：

```text
1. sell-side only；
2. 不新增 buy-side gate；
3. 不新增 cash target；
4. 不调整 score/rank/MA/mid-band/trend/cash/fee 阈值；
5. 不使用 realized return / future return / replay PnL 作为策略输入。
```

## 4. Evidence Timeline

### 4.1 2022 Downturn Validation Diagnostic

语义：

```text
diagnostic only
not strict OOS
not final OOS
not independent test
```

结果：

```text
baseline net_return_after_fee_tax = -0.33609220
RULE_05 net_return_after_fee_tax = -0.18603880
net_delta = +0.15005340

baseline max_drawdown = -0.42634734
RULE_05 max_drawdown = -0.22907360
max_drawdown_delta = +0.19727374

accelerated_sell_count = 105
average_cash_rate = 0.57052970
```

解释：

```text
2022 用于发现并解释机制：
risk-off early sell / weak-rank-deterioration 可以减少下跌年回撤。
```

2022 不作为最终通过证据。

### 4.2 2021 Pre-2022 Sanity Diagnostic

语义：

```text
pre-2022 sanity diagnostic
not strict OOS
```

结果：

```text
baseline net_return_after_fee_tax = 0.54760487
RULE_05 net_return_after_fee_tax = 0.47696307
net_delta = -0.07064180

baseline max_drawdown = -0.31695465
RULE_05 max_drawdown = -0.20594562
max_drawdown_delta = +0.11100903

RULE_05 average_cash_rate = 0.49247449
accelerated_sell_count = 36
```

解释：

```text
2021 确认 RULE_05 是防守型 tradeoff：
牺牲部分收益，改善最大回撤。
```

审查结论：

```text
PASS_READY_FOR_OPTION_B_QLIB_ONLY_STRICT_OOS_WORK_DOC
```

### 4.3 2023-2025 Qlib-only Strict OOS Candidate

语义：

```text
qlib-only strict OOS candidate
```

输入约束：

```text
1. 只使用 TEST.csv 的 qlib_score_raw / qlib_rank；
2. qlib train window = 2015-05-04..2020-12-31；
3. score window = 2023-01-01..2025-06-30；
4. use_frozen_pred = true；
5. training_performed = false；
6. parameter_search_performed = false；
7. no LTR / no orthogonal LTR / no stacking score。
```

RCPT5B 原始结果：

```text
FAIL_RULE05_DOES_NOT_PASS_QLIB_ONLY_STRICT_OOS
```

失败原因：

```text
fee_tax_delta_abs gate 使用绝对差；
RULE_05 费用低于 baseline 约 70444.52，
但方向有利的费用下降也被绝对差阻断。
```

RCPT5B_R 修复：

```text
只修复 fee/tax gate 方向性；
不改 RULE_05；
不改输入；
不改其他 gate；
不改 RCPT5B 原产物；
重新冻结 gate 后复跑。
```

修复后最终结果：

```text
baseline net_return_after_fee_tax = 0.41214390
RULE_05 net_return_after_fee_tax = 0.31759959
net_delta = -0.09454431

baseline max_drawdown = -0.55905450
RULE_05 max_drawdown = -0.35800856
max_drawdown_delta = +0.20104594

baseline fee_and_tax = 509542.18
RULE_05 fee_and_tax = 439097.66
fee_tax_delta = -70444.52

participation_rate = 0.99832496
primary_average_cash_rate = 0.30471485
cash_gt_90pct_equity_day_share = 0.01340034
average_holding_count = 6.94304858
accelerated_sell_count = 111
```

审查结论：

```text
PASS_QLIB_ONLY_STRICT_OOS_CANDIDATE_ACCEPTED_FOR_COORDINATOR_CLOSURE
```

## 5. Gate Summary

RCPT5B_R repaired gate 全部通过：

```text
contamination_audit = PASS
market_feature_coverage = PASS
price_coverage = PASS
rule05_freeze = PASS
forbidden_action = PASS
participation_rate = PASS
primary_average_cash_rate = PASS
cash_gt_90pct_equity_day_share = PASS
average_holding_count = PASS
buy_count_vs_baseline = PASS
sell_count_vs_baseline = PASS
max_drawdown_delta = PASS
net_return_delta = PASS
fee_tax_directional = PASS
top_instrument_benefit_share = PASS
top_month_benefit_share = PASS
top_trigger_day_benefit_share = PASS
```

关键 gate 数值：

```text
participation_rate = 0.99832496 >= 0.90
primary_average_cash_rate = 0.30471485 <= 0.65
cash_gt_90pct_equity_day_share = 0.01340034 <= 0.25
average_holding_count = 6.94304858 >= 2.0
max_drawdown_delta = +0.20104594 > 0
net_return_delta = -0.09454431 >= -0.15
fee_tax_delta = -70444.52 -> PASS_COST_NOT_WORSE
top_instrument_benefit_share = 0.10009952 <= 0.35
top_month_benefit_share = 0.16946431 <= 0.55
top_trigger_day_benefit_share = 0.08113996 <= 0.25
```

## 6. What The Result Means

本路线支持：

```text
RULE_05 是 qlib-only 风险控制候选。
```

它的价值在于：

```text
1. 明显降低最大回撤；
2. 不靠 all-cash/no-trade 伪通过；
3. 不靠单一股票、单一月份、少数 trigger 集中贡献；
4. 没有费用漏算，且最终费用低于 baseline；
5. 不替代 ranking model，只修正 risk-off 下弱持仓退出时机。
```

它不支持：

```text
1. 收益超过 baseline；
2. qlib+LTR 上也必然成立；
3. 生产默认策略切换；
4. 真实订单或目标仓位输出；
5. 更激进的阈值调参。
```

## 7. Safety Boundary

本 closure package 明确保留以下禁区：

```text
production/default/provider change = not authorized
frontend/Agent/monitor/order integration = not authorized
broker / quick-trade / real order = not authorized
OrderIntent output = not authorized
target_weight output = not authorized
target_position output = not authorized
quantity_instruction output = not authorized
model training = not performed
LTR / orthogonal LTR / stacking score = not used
threshold tuning = not performed
```

内部 replay ledger 只能称为：

```text
readonly replay accounting ledger
```

不能称为：

```text
order intent
position target
target weight
broker instruction
real trade recommendation
```

## 8. Deliverables

核心文档：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT_RISK_CONTROL_THRESHOLD_ROUTE_COORDINATOR_CLOSURE_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT6_RESEARCH_CLOSURE_PACKAGE_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT5B_R_FEE_TAX_GATE_REPAIR_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT5B_R_FEE_TAX_GATE_REPAIR_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT5A_OPTION_A_2021_PIT_FEATURE_REPAIR_DIAGNOSTIC_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT4_NARROW_ROBUSTNESS_AND_RULE05_MECHANISM_ATTRIBUTION_REVIEW_CN.md
```

核心产物目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt5b_r_fee_tax_gate_repair/
data_tw/experiments/risk_control_policy_2022/rcpt5a_option_a_2021_pit_feature_repair_diagnostic/
data_tw/experiments/risk_control_policy_2022/rcpt4_rule05_mechanism_attribution/
data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity/
```

## 9. Recommendation

推荐状态：

```text
Archive RCPT as completed qlib-only risk-control research route.
```

推荐下一步有两个互斥方向：

```text
1. 如果目标是研究闭环：到此关闭 RCPT 路线。
2. 如果目标是服务当前 qlib+正交 LTR 主线：另开 RCPT_LTR_ADAPTATION_DESIGN。
```

不推荐：

```text
1. 直接生产化；
2. 直接把 RULE_05 套到 qlib+LTR；
3. 为了追回收益继续调阈值；
4. 把 risk-control candidate 改写成 return-enhancement policy。
```

## 10. Final Closure

RCPT6 final status：

```text
COMPLETED_RESEARCH_CLOSURE_PACKAGE
```

最终路线结论：

```text
RULE_05 is accepted as a qlib-only risk-control overlay candidate,
with improved drawdown and lower costs at the expense of lower net return.
```
