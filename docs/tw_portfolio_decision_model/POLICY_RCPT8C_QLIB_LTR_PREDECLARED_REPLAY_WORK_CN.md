---
created_at: 2026-06-25
status: work_doc
phase: RCPT8C_QLIB_LTR_PREDECLARED_REPLAY
parent_mainline: docs/tw_portfolio_decision_model/POLICY_RCPT8_QLIB_LTR_ADAPTATION_DESIGN_MAINLINE_CN.md
parent_contract: data_tw/experiments/risk_control_policy_2022/rcpt8b_qlib_ltr_adaptation_rule_contract/
production_allowed: false
order_or_target_output_allowed: false
model_training_authorized: false
---

# RCPT8C Qlib+LTR Predeclared Replay 工作文档

## 1. 目标

本阶段只按 RCPT8B 冻结合同执行 qlib+LTR adaptation replay。

必须验证：

```text
RCPT7 Candidate B = adaptive-score baseline + RULE_05 sell overlay
```

在 qlib+LTR 输入下是否仍然能保持：

```text
高收益捕获 + 明显回撤改善 + 非 all-cash/no-trade
```

## 2. 必读输入

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT8_QLIB_LTR_ADAPTATION_DESIGN_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT8B_QLIB_LTR_ADAPTATION_RULE_CONTRACT_EXECUTION_REPORT_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt8b_qlib_ltr_adaptation_rule_contract/manifest.json
data_tw/experiments/risk_control_policy_2022/rcpt8b_qlib_ltr_adaptation_rule_contract/candidate_b_adaptation_contract.md
data_tw/experiments/risk_control_policy_2022/rcpt8b_qlib_ltr_adaptation_rule_contract/score_component_mapping_contract.csv
data_tw/experiments/risk_control_policy_2022/rcpt8b_qlib_ltr_adaptation_rule_contract/baseline_contract.csv
data_tw/experiments/risk_control_policy_2022/rcpt8b_qlib_ltr_adaptation_rule_contract/replay_window_contract.csv
data_tw/experiments/risk_control_policy_2022/rcpt8b_qlib_ltr_adaptation_rule_contract/gate_contract.md
data_tw/experiments/risk_control_policy_2022/rcpt8b_qlib_ltr_adaptation_rule_contract/ledger_schema_contract.md
```

主输入 lineage：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_train_row_scores.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_test_row_scores_2026.csv
```

如果 replay 需要价格/ret20/volatility20/TWII_ret20 字段，执行者必须使用已存在的 PIT-safe 来源，并在 `lineage_replay_audit.json` 里说明。

## 3. 冻结范围

只允许 replay：

```text
M1_QLIB_SCORE_COMPONENT_PRIMARY
M2_LTR_SCORE_COMPONENT_SECONDARY
M3_BLEND_Q70_L30_TERTIARY
```

只允许 replay 窗口：

```text
W1_2023_2025_TRAIN_CONTAMINATED_INTEGRATION_DIAGNOSTIC
W2_2026_NARROW_STRICT_OOS_DIAGNOSTIC
```

不得 replay：

```text
2022
2026-06-17 single-day snapshot
```

## 4. 必须比较

每个 mapping/window 必须比较：

```text
baseline:
  mapping-specific adaptive-score baseline without RULE_05

candidate:
  same mapping-specific adaptive-score baseline + frozen RULE_05 sell overlay
```

RCPT7 qlib-only Candidate B 只能作历史 reference，不得作为 gate baseline。

## 5. Gate

RCPT8C 必须执行 RCPT8B `gate_contract.md`。

最重要规则：

```text
W2 是 mapping acceptance 的必要窗口；
W1 不能救回 W2 失败；
W1 不得称为 strict OOS；
W2 不得称为 production-grade。
```

## 6. 输出目录

```text
data_tw/experiments/risk_control_policy_2022/rcpt8c_qlib_ltr_predeclared_replay/
```

必须输出：

```text
manifest.json
window_metric_summary.csv
candidate_vs_qlib_ltr_adaptive_baseline.csv
gate_decision_by_window.csv
gate_decision_by_mapping.csv
daily_nav.csv
actions.csv
trigger_attribution.csv
cash_exposure_audit.csv
fee_turnover_audit.csv
concentration_audit.csv
lineage_replay_audit.json
forbidden_action_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT8C_QLIB_LTR_PREDECLARED_REPLAY_EXECUTION_REPORT_CN.md
```

## 7. 禁止事项

本阶段禁止：

```text
1. 新增 mapping；
2. 改 alpha；
3. 调阈值；
4. 训练模型；
5. 使用非 E3 主 lineage 替代 replay 输入；
6. 把 W1 称为 strict OOS；
7. 把 W2 称为 production-grade；
8. 修改 production/default/provider/frontend/Agent/monitor/order 链路；
9. 输出 OrderIntent、target_weight、target_position、quantity_instruction；
10. broker / quick-trade / real order。
```

## 8. 允许结论

执行报告推荐结论只能是：

```text
PASS_READY_FOR_RCPT8D_CLOSURE
FAIL_NEEDS_RCPT8C_REPAIR
FAIL_NO_MAPPING_PASSES_GATE
STOP_SCOPE_OR_LINEAGE_VIOLATION
```

## 9. Reviewer 审查重点

审查者必须判断：

```text
1. 是否只 replay M1/M2/M3；
2. 是否只 replay W1/W2；
3. 是否没有调阈值或新增 mapping；
4. 是否正确处理 W1/W2 语义；
5. W2 是否至少有一个 mapping 通过全部 gate；
6. 是否没有 all-cash/no-trade 假通过；
7. 是否没有 production/order/target 越权；
8. 是否可以进入 RCPT8D closure。
```
