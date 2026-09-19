---
created_at: 2026-06-24
status: rcpt5_independent_review_completed
phase: RCPT5_STRICT_OOS_DESIGN_DECISION_REVIEW
execution_report: docs/tw_portfolio_decision_model/POLICY_RCPT5_STRICT_OOS_DESIGN_DECISION_EXECUTION_REPORT_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_RCPT5_STRICT_OOS_DESIGN_DECISION_WORK_CN.md
parent_review: docs/tw_portfolio_decision_model/POLICY_RCPT4_NARROW_ROBUSTNESS_AND_RULE05_MECHANISM_ATTRIBUTION_REVIEW_CN.md
artifact_root: data_tw/experiments/risk_control_policy_2022/rcpt5_strict_oos_design_decision
verdict: PASS_READY_FOR_COORDINATOR_ROUTE_SELECTION
diagnostic_only: true
strict_oos_executed: false
production_allowed: false
model_training_authorized: false
strict_test_authorized: false
---

# RCPT5 Strict OOS Design Decision 独立审查报告

## 1. Verdict

`PASS_READY_FOR_COORDINATOR_ROUTE_SELECTION`

RCPT5 执行者完成的是 strict OOS / final validation protocol 设计与本地 artifact inventory，没有执行 replay、training、strict_test 或生产链路改动。执行报告和 artifact 对 2022 diagnostic 污染边界处理充分，没有把 2022 写成 strict OOS、final OOS 或 independent test。

建议继续到 coordinator route selection。下一步只能选择/授权后续路线，不得直接进入 production/default/provider/frontend/Agent/monitor/order chain。

## 2. Evidence Reviewed

本审查读取：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT5_STRICT_OOS_DESIGN_DECISION_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT5_STRICT_OOS_DESIGN_DECISION_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT4_NARROW_ROBUSTNESS_AND_RULE05_MECHANISM_ATTRIBUTION_REVIEW_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt5_strict_oos_design_decision/manifest.json
data_tw/experiments/risk_control_policy_2022/rcpt5_strict_oos_design_decision/artifact_inventory.csv
data_tw/experiments/risk_control_policy_2022/rcpt5_strict_oos_design_decision/oos_option_matrix.csv
data_tw/experiments/risk_control_policy_2022/rcpt5_strict_oos_design_decision/rule05_frozen_contract.md
data_tw/experiments/risk_control_policy_2022/rcpt5_strict_oos_design_decision/strict_oos_gate_contract.md
data_tw/experiments/risk_control_policy_2022/rcpt5_strict_oos_design_decision/recommended_route.md
data_tw/experiments/risk_control_policy_2022/rcpt5_strict_oos_design_decision/forbidden_action_audit.csv
data_tw/experiments/risk_control_policy_2022/rcpt5_strict_oos_design_decision/validator_report.json
```

另抽查：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/TEST.manifest.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/WF-VAL.manifest.json
```

## 3. Scope Boundary Check

通过。

`manifest.json` 与 `validator_report.json` 均声明：

```text
strict_oos_executed = false
strict_test_performed = false
new_window_replay_performed = false
model_training_performed = false
production_or_provider_or_frontend_or_agent_or_monitor_or_order_chain_changed = false
order_intent_generated = false
target_weight_generated = false
target_position_generated = false
quantity_instruction_generated = false
```

artifact 目录只包含设计、inventory、gate、推荐路线、forbidden audit 与 validator 文件；没有发现新窗口 replay 输出、训练输出或 strict_test 输出。`forbidden_action_audit.csv` 全部为 `PASS_NOT_PERFORMED`。

## 4. 2022 Diagnostic 污染处理

通过。

执行报告、manifest、inventory、gate 和 recommended route 均把 2022 标为：

```text
downturn_validation_diagnostic_only
```

未发现把 2022 写成 strict OOS、final OOS 或 independent test 的表述。RCPT5 明确承认 RULE_05 已由 2022 diagnostic / attribution / candidate selection 影响，因此 2022 只能作为机制洞察和风险背景，不得进入 final test 证据。

## 5. Option A/B/C/D 审查

通过。

Option A 完整说明了 2021 只能作为 pre-2022 sanity diagnostic，不能称为 final strict OOS；同时识别 2021 signal coverage 存在但 PIT market feature 缺失，需要按 RCP3A 派生 TWII close/MA60 与 market risk-off feature。

Option B 是当前推荐的首个 strict OOS 候选，但执行者将其限定为 qlib-only frozen TEST score/rank 路线。抽查 `TEST.manifest.json` 显示 score window 为 2023-01-01..2025-06-30、qlib train 为 2015-05-04..2020-12-31、`use_frozen_pred=true`、`training_performed=false`。RCPT5 同时要求执行前审计 2023-2025 是否参与 RULE_05、policy 或 LTR 选择污染，并禁止直接引入 LTR。

Option C 对重建模型切分的原则足够清楚：训练、模型验证、policy design、policy validation、final test 必须预声明，final test 只能触碰一次，且 RCPT5 不授权训练。

Option D 停止路线明确：若 2021 feature repair、2023-2025 strict OOS 或重切分均不可授权，RULE_05 只保留为 2022 diagnostic insight。

## 6. RULE_05 Frozen Contract

通过。

`rule05_frozen_contract.md` 冻结了核心触发语义：

```text
risk_off
len(holdings) > 1
rank_change_5d > 0 或 rank_change_3d > 0
not pass_rule03_combined_support
max_early_sell_per_day = 1
```

合同明确禁止新增 buy-side gate、新增 cash target、调整 score/rank/MA/mid-band/trend/cash/fee 阈值、根据 2021/2022/2023-2025 结果调阈值后重跑、使用 future return label 或 replay return 做策略输入。

保留低风险提示：该合同是从 RCPT3/RCPT4 审查文本还原的设计冻结合同，后续进入执行 work doc 前仍需把 RCPT2 replay 脚本字段和边界实现逐项 hash/签名冻结。当前不阻断 route selection。

## 7. Strict OOS Gate 审查

通过。

`strict_oos_gate_contract.md` 覆盖了防止伪通过的关键维度：

```text
net_return_after_fee_tax
max_drawdown
participation_rate
average_cash_rate / max_cash_rate / high-cash days
holding count / buy_count / sell_count / no_trade_day_count
gross/net return
commission / tax / fee_tax_delta
turnover / buy_notional / sell_notional
top instrument/month/day/trigger benefit share
positive/negative trigger count
subperiod stability
future label and no-retuning controls
```

该 gate 能防止 all-cash/no-trade、长期空仓降回撤、单一股票/月/trigger 集中贡献、费用漏算或税费口径变更等伪通过。

保留非阻断要求：当前 gate 写明现金上限和 net return 容忍带必须在执行前冻结，但尚未给出数值。后续任何 replay/strict OOS work doc 必须先写出 reviewer-signed threshold freeze contract；否则不得执行并声称 strict OOS。

## 8. Forbidden Action Audit

通过。

`forbidden_action_audit.csv` 覆盖并通过：

```text
new_window_replay
model_training
strict_test
new_rule
threshold_tuning
production_default_provider_change
broker_order_quick_trade
order_intent_artifact_output
target_weight_output
target_position_output
quantity_instruction_output
future_return_label_used_for_design
external_data_backfill
claim_2022_strict_oos
frontend_agent_monitor_integration
```

未发现 broker/order/quick-trade、OrderIntent、target_weight、target_position、quantity_instruction 或 provider/frontend/Agent/monitor 链路越界。

## 9. Findings

### Critical

无。

### High

无。

### Medium

无。

### Low

1. strict OOS gate 已要求预冻结现金上限和收益容忍带，但尚未给出数值。下一阶段在执行任何 replay 前必须补成不可变 gate contract。

2. RULE_05 frozen contract 的机制语义足够用于 route selection；执行前仍需核对 RCPT2 replay 脚本字段名、排序方向、daily sell cap 与 fee/tax 实现，并形成 hash 或等价冻结证据。

3. Option B 的 qlib-only strict OOS 可行性是 conditional。若后续污染审计发现 2023-2025 TEST fold 已被 policy/LTR/strategy selection 使用且无法隔离，必须转 Option C 或 Option D。

## 10. Final Decision

RCPT5 可以关闭为：

```text
PASS_READY_FOR_COORDINATOR_ROUTE_SELECTION
```

建议 coordinator 继续，但只继续到路线选择：

```text
Option A -> Option B qlib-only -> Option C fallback -> Option D stop fallback
```

不得直接继续到：

```text
production/default/provider/frontend/Agent/monitor/order chain
OrderIntent
target_weight
target_position
quantity_instruction
2022-result-driven threshold tuning
unreviewed qlib+LTR strict OOS claim
```
