---
created_at: 2026-06-25
status: work_doc
phase: RCPT9B_LINEAGE_BUILD
parent_mainline: docs/tw_portfolio_decision_model/POLICY_RCPT9_LONGER_STRICT_OOS_RETRAIN_HOLDOUT_MAINLINE_CN.md
parent_contract: docs/tw_portfolio_decision_model/POLICY_RCPT9A_SPLIT_LINEAGE_FEASIBILITY_CONTRACT_EXECUTION_REPORT_CN.md
production_allowed: false
order_or_target_output_allowed: false
model_training_authorized: conditional_existing_lineage_packaging_preferred
replay_authorized: false
---

# RCPT9B Lineage Build 工作文档

## 1. 目标

本阶段构建或合同化 RCPT9A 推荐的 B3/S2A-style fresh retrain-holdout lineage。

优先级：

```text
1. 若现有 S2B/S2C fresh qlib+LTR lineage 已满足 RCPT9A split，则复用并包装为 RCPT9B lineage package；
2. 只有缺少关键产物时，才允许最小补建；
3. 本阶段不得执行 RCPT9C replay。
```

## 2. 必读输入

```text
docs/tw_portfolio_decision_model/POLICY_RCPT9_LONGER_STRICT_OOS_RETRAIN_HOLDOUT_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT9A_SPLIT_LINEAGE_FEASIBILITY_CONTRACT_EXECUTION_REPORT_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt9a_split_lineage_feasibility_contract/
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2a_fresh_retrain_contract/
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/
```

## 3. 冻结 Split

RCPT9B lineage 必须冻结：

```text
train only: 2017-01-10..2024-12-31
validation diagnostics only: 2025-01-01..2025-06-30
holdout untouched: 2025-07-01..2026-05-07
```

允许 mappings：

```text
M1_QLIB_SCORE_COMPONENT_PRIMARY
M2_LTR_SCORE_COMPONENT_SECONDARY
```

禁止：

```text
M3
new mappings
alpha search
threshold tuning
holdout feedback
```

## 4. 输出目录

```text
data_tw/experiments/risk_control_policy_2022/rcpt9b_lineage_build/
```

必须生成：

```text
manifest.json
lineage_artifact_inventory.csv
split_purity_audit.csv
score_schema_audit.csv
feature_label_coverage_audit.csv
holdout_readiness_audit.csv
mapping_input_contract.csv
lineage_reuse_or_build_decision.md
forbidden_action_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT9B_LINEAGE_BUILD_EXECUTION_REPORT_CN.md
```

## 5. 必须审计

必须确认：

```text
1. S2B fresh qlib model/score 是否存在；
2. S2C fresh LTR model/score 是否存在；
3. split 是否符合 RCPT9A B3；
4. holdout 是否未用于 qlib/LTR 训练、调参、early stopping、mapping/gate 选择；
5. holdout score 是否覆盖 2025-07-01..2026-05-07；
6. score schema 是否支持 M1/M2；
7. feature/label coverage 是否足以进入 RCPT9C；
8. 是否没有 replay、生产、订单、target 越权。
```

## 6. 禁止事项

本阶段禁止：

```text
RCPT9C replay
threshold tuning
new mapping search
production/default/provider/frontend/Agent/monitor/order changes
OrderIntent
target_weight
target_position
quantity_instruction
broker / quick-trade / real order
```

## 7. 允许结论

执行报告推荐结论只能是：

```text
PASS_READY_FOR_RCPT9C_PREDECLARED_LONGER_OOS_REPLAY
FAIL_NEEDS_RCPT9B_REPAIR
STOP_NO_VALID_FRESH_RETRAIN_HOLDOUT_LINEAGE
STOP_SCOPE_OR_FORBIDDEN_ACTION_VIOLATION
```

## 8. Reviewer 审查重点

审查者必须判断：

```text
1. 是否优先复用现有 S2B/S2C lineage，避免不必要重训；
2. 若有训练，是否完全符合 RCPT9A split；
3. holdout 是否 untouched；
4. score schema 是否支持 M1/M2；
5. 是否没有 replay 或生产/订单/target 越权；
6. 是否可以进入 RCPT9C。
```
