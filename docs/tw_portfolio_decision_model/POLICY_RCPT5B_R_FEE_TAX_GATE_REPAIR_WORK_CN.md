---
created_at: 2026-06-24
status: work_doc
phase: RCPT5B_R_FEE_TAX_GATE_REPAIR
parent_review: docs/tw_portfolio_decision_model/POLICY_RCPT5B_OPTION_B_QLIB_ONLY_STRICT_OOS_REVIEW_CN.md
target_rule: RCPT1_RULE_05
window: 2023_2025_qlib_only_test_fold
qlib_only: true
ltr_allowed: false
model_training_authorized: false
strict_test_authorized: false
production_allowed: false
---

# RCPT5B_R Fee/Tax Gate Repair 工作文档

## 1. 背景

RCPT5B 审查结论：

```text
FAIL_RULE05_DOES_NOT_PASS_QLIB_ONLY_STRICT_OOS
```

但审查同时确认：

```text
1. qlib-only strict OOS candidate 语义成立；
2. contamination、PIT market feature、price coverage、RULE_05 freeze、cash/equity 主口径、forbidden action 均通过；
3. RULE_05 在 2023-2025 收益低于 baseline，但 max drawdown 明显改善；
4. 不是 all-cash/no-trade 伪通过；
5. 唯一实质失败项为 fee_tax_delta_abs。
```

失败的具体原因：

```text
预冻结 gate 使用 abs(fee_tax_delta) <= 50000。
RULE_05 total fee/tax 实际低于 baseline 约 70444.68，
但因为使用绝对差，方向有利的费用下降也被判为失败。
```

本轮 repair 的目标是：

```text
只修复 fee/tax gate 的方向性定义，
重新冻结 gate，
复跑同一 2023-2025 qlib-only TEST fold 与同一冻结 RULE_05。
```

不得把 RCPT5B 的失败 retroactively 改判 PASS；必须生成新的 RCPT5B_R 产物和独立审查。

## 2. 目标

回答：

```text
在修复 fee/tax gate 方向性之后，
冻结 RULE_05 是否通过 2023-2025 qlib-only strict OOS candidate gate？
```

## 3. 非目标

本阶段不授权：

```text
1. 修改 RULE_05；
2. 修改 score/rank/MA/mid-band/trend/cash 阈值；
3. 根据 RCPT5B 结果调规则；
4. 使用 LTR、orthogonal LTR、stacking score；
5. 训练 qlib/LTR/policy 模型；
6. production/default/provider/frontend/Agent/monitor/order 链路改动；
7. OrderIntent、target_weight、target_position、quantity_instruction；
8. 对 RCPT5B 原产物事后改判。
```

## 4. 必读输入

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT5B_OPTION_B_QLIB_ONLY_STRICT_OOS_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT5B_OPTION_B_QLIB_ONLY_STRICT_OOS_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT5B_OPTION_B_QLIB_ONLY_STRICT_OOS_REVIEW_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt5b_option_b_qlib_only_strict_oos/strict_oos_gate_freeze.json
data_tw/experiments/risk_control_policy_2022/rcpt5b_option_b_qlib_only_strict_oos/rule05_2023_2025_gate_decision.csv
data_tw/experiments/risk_control_policy_2022/rcpt5b_option_b_qlib_only_strict_oos/rule05_2023_2025_fee_tax_reconciliation.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/TEST.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/TEST.manifest.json
scripts/run_tw_policy_rcpt5b_option_b_qlib_only_strict_oos.py
```

## 5. Repair Scope

只允许修改/新增：

```text
1. RCPT5B_R 专用执行脚本或在新脚本中复用 RCPT5B 逻辑；
2. 新输出目录下的 gate freeze、gate decision、validator、execution report；
3. fee/tax gate 定义。
```

禁止：

```text
1. 修改 RCPT5B 原产物；
2. 修改 TEST.csv / TEST.manifest；
3. 修改 RULE_05 freeze audit 语义；
4. 修改 cash、drawdown、net return、participation、concentration gate 数值；
5. 以任何方式选择性删除失败区间或交易。
```

## 6. 新 Fee/Tax Gate 冻结

新 gate 必须在 replay 前写入：

```text
strict_oos_gate_freeze.json
```

修复后的 fee/tax gate：

```text
fee_tax_delta = rule_fee_and_tax - baseline_fee_and_tax

if fee_tax_delta <= 0:
    fee_tax_gate = PASS_COST_NOT_WORSE
else:
    fee_tax_gate = PASS only if fee_tax_delta <= max(0.50 * positive_net_return_improvement_cash_value, 0.05 * initial_cash)
```

其中：

```text
positive_net_return_improvement_cash_value = max(rule_net_return_after_fee_tax - baseline_net_return_after_fee_tax, 0) * initial_cash
```

解释：

```text
1. 成本下降不应因绝对差过大而失败；
2. 成本上升时，必须由正向净收益改善或 5% initial cash 容忍带覆盖；
3. 如果净收益没有改善且成本上升超过 5% initial cash，则失败；
4. fee/tax reconciliation 仍必须报告 commission、tax、buy/sell notional、turnover。
```

除 fee/tax gate 外，其余 gate 维持 RCPT5B 原数值：

```text
participation_rate >= 0.90
primary_average_cash_rate <= 0.65
cash_gt_90pct_equity_day_share <= 0.25
average_holding_count >= 2.0
buy_count >= 25% baseline_buy_count
sell_count >= 25% baseline_sell_count
max_drawdown_delta > 0
net_return_delta >= -0.15
top_instrument_benefit_share <= 0.35
top_month_benefit_share <= 0.55
top_trigger_day_benefit_share <= 0.25
```

现金主口径仍为：

```text
cash / equity
```

## 7. 输出要求

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt5b_r_fee_tax_gate_repair/
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
fee_tax_gate_repair_audit.csv
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

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT5B_R_FEE_TAX_GATE_REPAIR_EXECUTION_REPORT_CN.md
```

## 8. Pass / Fail / Stop

通过条件：

```text
1. 除 fee/tax gate repair 外，其余 RCPT5B gate 均保持原值并通过；
2. 新 fee/tax gate 方向性定义在 replay 前冻结；
3. RULE_05 freeze、qlib-only、contamination、PIT feature、price coverage、cash/equity、forbidden audit 全部通过；
4. 未修改 RCPT5B 原产物，未事后改判；
5. replay 结果通过修复后的全部 gate。
```

失败条件：

```text
1. 修复后仍有 gate 不通过；
2. fee/tax reconciliation 无法解释；
3. 结果仍是现金、集中度或费用伪通过。
```

停止条件：

```text
1. 发现 LTR、训练、调阈值、future leakage、生产/order 越权；
2. 发现 RCPT5B 原产物被篡改；
3. 发现执行者在 repair 中改动 RULE_05 或非 fee/tax gate。
```

## 9. 审查者职责

审查者必须判断：

```text
1. repair 是否只修 fee/tax gate 方向性；
2. 新 gate 是否在 replay 前冻结；
3. 是否没有改 RULE_05、其他 gate、输入数据或 RCPT5B 原产物；
4. fee/tax 下降是否被正确解释为成本不恶化；
5. 结果是否可接受为 qlib-only strict OOS candidate；
6. 是否仍不得生产化或输出订单/target 字段。
```

审查结论只能是：

```text
PASS_QLIB_ONLY_STRICT_OOS_CANDIDATE_ACCEPTED_FOR_COORDINATOR_CLOSURE
FAIL_RULE05_DOES_NOT_PASS_REPAIRED_QLIB_ONLY_STRICT_OOS
FAIL_NEEDS_RCPT5B_R_REPAIR
STOP_SCOPE_OR_GATE_REPAIR_VIOLATION
```

## 10. 执行者命令

```text
请执行 RCPT5B_R Fee/Tax Gate Repair。
只修复 fee/tax gate 方向性并重新冻结 gate，
复跑同一 2023-2025 qlib-only TEST fold 与同一冻结 RULE_05。
不得训练、不得 LTR、不得调规则、不得改 RCPT5B 原产物、不得生产化或输出订单/target 字段。
```
