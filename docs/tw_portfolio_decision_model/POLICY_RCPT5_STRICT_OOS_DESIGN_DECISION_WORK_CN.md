---
created_at: 2026-06-24
status: work_doc
phase: RCPT5_STRICT_OOS_DESIGN_DECISION
parent_review: docs/tw_portfolio_decision_model/POLICY_RCPT4_NARROW_ROBUSTNESS_AND_RULE05_MECHANISM_ATTRIBUTION_REVIEW_CN.md
target_rule: RCPT1_RULE_05
diagnostic_only: true
strict_test_authorized: false
production_allowed: false
model_training_authorized: false
---

# RCPT5 Strict OOS Design Decision 工作文档

## 1. 背景

RCPT4 审查结论：

```text
PASS_READY_FOR_COORDINATOR_DECISION_ON_STRICT_OOS_DESIGN
```

当前事实：

```text
1. RCPT1_RULE_05 在 2022 downturn validation diagnostic 中通过；
2. 改善主要来自 risk-off early sell / weak-rank-deterioration 机制；
3. 2022 不是 strict OOS / final OOS / independent test；
4. 2021 optional diagnostic 暂不可做，因为 PIT market feature artifact 缺 2021 coverage；
5. RULE_05 的现金暴露偏高，且 20d benefit 在 2022-06 与 2022-09 压力段贡献较大。
```

RCPT5 的任务不是执行 strict OOS，也不是生产化，而是设计一份可审查、可执行、不污染 2022 诊断结论的严格验证协议。

## 2. 目标

执行者需要给出：

```text
RULE_05 后续如何做 strict OOS / final validation 的设计决策。
```

必须回答：

```text
1. 可用哪些时间窗口作为真正独立验证？
2. 是否需要重新生成 market feature coverage？
3. 是否需要重新训练 qlib signal model，还是可以使用现有 artifact？
4. RULE_05 的阈值、逻辑、cash guardrail、fee/tax gate 如何冻结？
5. 如何避免 2022 结果继续污染后续验证？
6. 如果没有合格 strict OOS 窗口，应该停止、补数据，还是重建模型切分？
```

## 3. 非目标

本阶段不允许：

```text
1. 执行 strict_test；
2. replay 新窗口；
3. 训练 qlib/LTR/policy 模型；
4. 新增或调 RULE_05 阈值；
5. 根据 2022 结果设计更激进规则；
6. 修改 production/default/provider/frontend/Agent/monitor/order 链路；
7. 输出 OrderIntent、target_weight、target_position、quantity_instruction；
8. 把 2022 写成 strict OOS / final OOS / independent test。
```

## 4. 必读输入

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RCP_RISK_CONTROL_POLICY_2022_DOWNTURN_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT3_CLOSURE_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT4_NARROW_ROBUSTNESS_AND_RULE05_MECHANISM_ATTRIBUTION_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT4_NARROW_ROBUSTNESS_AND_RULE05_MECHANISM_ATTRIBUTION_REVIEW_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt4_rule05_mechanism_attribution/manifest.json
data_tw/experiments/risk_control_policy_2022/rcpt4_rule05_mechanism_attribution/validator_report.json
data_tw/experiments/risk_control_policy_2022/rcpt4_rule05_mechanism_attribution/2021_not_available_audit.json
data_tw/experiments/risk_control_policy_2022/rcpt4_rule05_mechanism_attribution/rule05_mechanism_summary.csv
data_tw/experiments/risk_control_policy_2022/rcpt4_rule05_mechanism_attribution/rule05_subperiod_stability.csv
data_tw/experiments/risk_control_policy_2022/rcpt4_rule05_mechanism_attribution/rule05_cash_exposure_attribution.csv
data_tw/experiments/risk_control_policy_2022/rcpt4_rule05_mechanism_attribution/rule05_fee_tax_reconciliation.csv
```

执行者还应盘点本地已有的 signal/model/price/market feature artifact，但只做 inventory，不做训练或 replay。

## 5. 设计要求

执行者必须提出至少三种可选路线，并给出推荐优先级：

### Option A：补齐 2021 market feature，做 2021 pre-2022 diagnostic

要求说明：

```text
1. 2021 是否能作为 pre-2022 sanity，不可称 final strict OOS；
2. 需要补齐哪些 PIT market features；
3. 如何保持 RULE_05 冻结；
4. 通过/失败如何影响是否进入更严格验证。
```

### Option B：使用 2023-2025 作为 strict OOS，但需处理模型训练污染

要求说明：

```text
1. 现有 2023-2025 是否被 LTR/其他模型训练或选择污染；
2. 如果只使用 2015-2020 qlib signal，是否可以形成 RULE_05 的 strict OOS replay；
3. 若需要 qlib+LTR，是否必须重新切分训练窗口；
4. 该路线的成本、风险、可信度。
```

### Option C：重建模型切分，保留独立 downturn / post-design window

要求说明：

```text
1. 如何重新训练 qlib/LTR，留出 policy validation/test；
2. 哪些年份用于 model train、policy design、policy validation、final test；
3. 成本是否值得；
4. 何时才授权训练。
```

可选补充：

```text
Option D：如果没有合格 OOS，先停止 RULE_05 验证并只保留为 2022 diagnostic insight。
```

## 6. 必须冻结的 RULE_05 合同

执行者必须写清楚后续验证中 RULE_05 的冻结合同：

```text
1. risk_off 定义；
2. rank_change_3d / rank_change_5d 方向；
3. failed mid-band/trend support 条件；
4. max_early_sell_per_day = 1；
5. 不新增 buy-side gate；
6. 不新增 cash target；
7. 不调 score/rank/MA 阈值；
8. fee/tax accounting 与 RCPT2/RCPT4 保持一致。
```

如果执行者发现上述合同无法从现有产物完整还原，应标记为 blocker，不得自行补规则。

## 7. Strict OOS Gate 预声明

执行者必须为后续真正验证预声明 gate：

```text
1. net_return_after_fee_tax 不得显著劣化；
2. max_drawdown 必须改善；
3. participation_rate 不得崩；
4. average_cash_rate 必须有上限；
5. fee/tax delta 必须可接受；
6. sell-side benefit 不得集中于单一股票、单一月份、少数 trigger；
7. 不得出现 all-cash/no-trade；
8. 不得使用 future return label 做策略输入；
9. 不得基于验证结果调阈值后再重跑。
```

## 8. 输出要求

执行者必须新增：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT5_STRICT_OOS_DESIGN_DECISION_EXECUTION_REPORT_CN.md
```

建议生成辅助 artifact 目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt5_strict_oos_design_decision/
```

至少包含：

```text
manifest.json
artifact_inventory.csv
oos_option_matrix.csv
rule05_frozen_contract.md
strict_oos_gate_contract.md
recommended_route.md
forbidden_action_audit.csv
validator_report.json
```

## 9. 审查者职责

审查者必须判断：

```text
1. 执行者是否只是做设计决策，没有执行 replay/training/strict_test；
2. 是否完整处理 2022 diagnostic 污染问题；
3. 是否明确 2021/2023-2025/重切分路线的可行性与风险；
4. RULE_05 冻结合同是否足够明确；
5. strict OOS gate 是否能防止现金、防御、集中度、费用伪通过；
6. 推荐路线是否合理。
```

审查结论只能是：

```text
PASS_READY_FOR_COORDINATOR_ROUTE_SELECTION
FAIL_NEEDS_RCPT5_REPAIR
STOP_NO_VALID_STRICT_OOS_DESIGN_AVAILABLE
STOP_SCOPE_OR_FORBIDDEN_ACTION_VIOLATION
```

## 10. 执行者命令

```text
请执行 RCPT5_STRICT_OOS_DESIGN_DECISION。
只做 strict OOS / final validation protocol 设计，不做任何 replay、训练、strict_test 或生产改动。
输出执行报告和 required artifacts。
```

## 11. 审查者命令

```text
请独立审查 RCPT5 执行报告和 artifacts。
重点判断推荐 strict OOS 设计是否能避免 2022 diagnostic 污染，
是否冻结 RULE_05，是否有足够 gate 防止现金/集中度/费用伪通过。
```
