---
created_at: 2026-06-25
status: execution_report
phase: RCPT9A_SPLIT_LINEAGE_FEASIBILITY_CONTRACT
validator_status: PASS_READY_FOR_RCPT9B_LINEAGE_BUILD_OR_FORWARD_OOS
production_allowed: false
order_or_target_output_allowed: false
model_training_performed: false
replay_performed: false
---

# RCPT9A Split And Lineage Feasibility Contract 执行报告

## 1. 执行范围

本轮严格执行 RCPT9A，只做更长 strict OOS / retrain-holdout 的可行性合同。

本轮未训练，未 replay，未调阈值，未新增 mapping search，未修改 production/default/provider/frontend/Agent/monitor/order 链路，也未输出 OrderIntent、target_weight、target_position 或 quantity_instruction。

## 2. 已读取输入

已读取：

- `docs/tw_portfolio_decision_model/POLICY_RCPT9_LONGER_STRICT_OOS_RETRAIN_HOLDOUT_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT9A_SPLIT_LINEAGE_FEASIBILITY_CONTRACT_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT8D_QLIB_LTR_ADAPTATION_CLOSURE_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/risk_control_policy_2022/rcpt8d_qlib_ltr_adaptation_closure/`
- `docs/tw_extended_oos_qlib_orthogonal_ltr/EXTENDED_OOS_QLIB_ORTHOGONAL_LTR_MAINLINE_CN.md`
- `docs/tw_extended_oos_qlib_orthogonal_ltr/EXTENDED_OOS_FOUR_MODEL_FOUR_REPLAY_CONSOLIDATED_STATE_CN.md`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/`

## 3. 已评估计划

### A_FORWARD_PAPER_OOS

结论：

```text
FEASIBLE_BUT_TIME_DEPENDENT
```

含义：

```text
冻结 RCPT8 M1/M2，不重训、不调阈值，随着未来 2026+ 每日信号和 PIT 审计自然累积 forward OOS。
```

这是最干净的 fallback，但需要时间。

### B1_2015_2020_Q_2021_LTR_2022_HOLDOUT

结论：

```text
CONCEPTUALLY_FEASIBLE_BUT_HIGH_BUILD_COST
```

优点是 2022 是下跌年；缺点是当前没有现成精确 qlib+LTR artifact，需要重新构建 2021 LTR 与 2022 holdout lineage，PIT/label 还需额外审计。

### B2_SPLIT_ALIGNED_EXISTING_2017_2020_LTR_2021_2022_VAL_2023_2025_HOLDOUT

结论：

```text
FEASIBLE_AS_LONG_HISTORICAL_HOLDOUT_BUT_REQUIRES_MAPPING_ADAPTER
```

证据：

```text
holdout = 2023-01-03..2025-06-30
trading days = 597
S1B2 test labels complete = 89386 / 89386
S1B6R replay zero missing price days
```

限制：

```text
现有 S1 replay 的策略不是 RCPT8 M1/M2；
若采用 B2，需要先做 RCPT8 M1/M2 mapping adapter。
```

### B3_S2A_FRESH_RETRAIN_2017_2024_TRAIN_2025H1_VAL_2025H2_2026_HOLDOUT

结论：

```text
RECOMMENDED_PRIMARY_FEASIBLE_WITH_EXISTING_CONTRACT_EVIDENCE
```

冻结建议：

```text
qlib train = 2017-01-10..2024-12-31
LTR train = 2017-01-10..2024-12-31
validation = 2025-01-01..2025-06-30
strict holdout = 2025-07-01..2026-05-07
```

证据：

```text
S2A common complete fresh test = 2025-07-01..2026-05-07
trading days = 205
instrument_count = 150
score_row_count = 30475
```

该路线比 RCPT8 W2 的 79 天更长，并且有现成 split contract 证据。

## 4. 推荐路线

主推荐：

```text
B3_S2A_FRESH_RETRAIN_2017_2024_TRAIN_2025H1_VAL_2025H2_2026_HOLDOUT
```

fallback：

```text
A_FORWARD_PAPER_OOS
```

secondary：

```text
B2 split-aligned historical holdout
```

不优先 B1，除非用户特别要求优先验证 2022 下跌年。

## 5. RCPT9B 授权建议

RCPT9A 本身不授权训练，但建议下一阶段 RCPT9B 可以在独立审查通过后授权：

```text
按 B3/S2A-style split 构建 fresh qlib+LTR lineage。
```

RCPT9B 必须冻结：

```text
train only: 2017-01-10..2024-12-31
validation diagnostics only: 2025-01-01..2025-06-30
holdout untouched: 2025-07-01..2026-05-07
allowed mappings: M1/M2 only
M3 remains rejected
```

## 6. 输出文件

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt9a_split_lineage_feasibility_contract/
```

已生成：

- `manifest.json`
- `candidate_split_plan.csv`
- `data_coverage_by_window.csv`
- `feature_pit_coverage_by_window.csv`
- `label_feasibility_by_window.csv`
- `contamination_audit_by_plan.csv`
- `recommended_lineage_contract.md`
- `forward_paper_oos_contract.md`
- `gate_contract.md`
- `forbidden_action_audit.csv`
- `validator_report.json`
- `diagnostic_findings.md`

## 7. Validator 结果

```text
PASS_READY_FOR_RCPT9B_LINEAGE_BUILD_OR_FORWARD_OOS
```

## 8. 下一步

建议进入：

```text
RCPT9B_LINEAGE_BUILD
```

默认执行 B3/S2A-style fresh retrain-holdout lineage build；Route A forward paper OOS 可作为并行 fallback。
