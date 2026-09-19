---
created_at: 2026-06-25
status: execution_report
phase: RCPT8B_QLIB_LTR_ADAPTATION_RULE_CONTRACT
validator_status: PASS_READY_FOR_RCPT8C_PREDECLARED_REPLAY
production_allowed: false
order_or_target_output_allowed: false
model_training_performed: false
replay_performed: false
---

# RCPT8B Qlib+LTR Adaptation Rule Contract 执行报告

## 1. 执行范围

本轮严格执行 RCPT8 主线中 `RCPT8B: Adaptation Rule Contract` 的要求。

本轮只冻结：

```text
Candidate B qlib+LTR adaptation 定义；
score component mappings；
baseline；
replay windows；
gate；
readonly ledger schema。
```

本轮未 replay，未训练模型，未调阈值，未新增 replay 后 mapping，未修改 production/default/provider/frontend/Agent/monitor/order 链路，也未输出 OrderIntent、target_weight、target_position 或 quantity_instruction。

## 2. 前提

RCPT8A 已通过：

```text
PASS_READY_FOR_RCPT8B_ADAPTATION_RULE_CONTRACT
```

RCPT8B 继承 RCPT8A 的窗口语义：

| window | RCPT8B 语义 |
| --- | --- |
| 2022 | 当前 qlib+LTR lineage unavailable |
| 2023-2025 | LTR train-contaminated integration diagnostic only |
| 2026-01-02..2026-05-07 | narrow strict OOS diagnostic, not production-grade |
| 2026-06-17 | single-day schema/PIT diagnostic only |

## 3. 主 Lineage

冻结主 lineage：

```text
E3_extended_oos_qlib_orthogonal_ltr_scores
```

后续 RCPT8C 只能使用该 lineage 作为主 replay 输入，除非另开合同。

必须使用的核心字段：

```text
date
instrument
qlib_score_raw
qlib_rank
phasee3_extended_oos_ltr_score
phasee3_extended_oos_ltr_rank
```

## 4. Candidate B 冻结定义

候选：

```text
Top50 Adaptive Score + RULE_05 Sell Overlay
```

RCPT8C 中 Candidate B adaptation 必须定义为：

```text
mapping-specific adaptive-score baseline
+ frozen RULE_05 weak-rank-deterioration sell overlay
```

不得修改 RULE_05 逻辑，不得新增候选，不得 replay 后调阈值。

## 5. Score Component Mapping 冻结

只允许三个 mapping：

| mapping | 用途 |
| --- | --- |
| `M1_QLIB_SCORE_COMPONENT_PRIMARY` | 主 mapping，沿用 qlib score component，最接近 RCPT7 |
| `M2_LTR_SCORE_COMPONENT_SECONDARY` | 用 LTR score z-score 替代 qlib score component |
| `M3_BLEND_Q70_L30_TERTIARY` | 固定 blend：70% qlib + 30% LTR，不允许搜索 alpha |

三者已写入：

```text
data_tw/experiments/risk_control_policy_2022/rcpt8b_qlib_ltr_adaptation_rule_contract/score_component_mapping_contract.csv
```

## 6. Baseline 冻结

主 gate baseline：

```text
qlib+LTR adaptive-score baseline without RULE_05 overlay
```

也就是说，RCPT8C 要验证的是：

```text
RULE_05 overlay 是否在同一个 qlib+LTR adaptive baseline 上带来增量风控价值。
```

RCPT7 qlib-only Candidate B 只能作为历史参考，不能作为 RCPT8C 的主 gate baseline。

## 7. Replay Window 冻结

RCPT8C 允许 replay：

```text
W1_2023_2025_TRAIN_CONTAMINATED_INTEGRATION_DIAGNOSTIC
W2_2026_NARROW_STRICT_OOS_DIAGNOSTIC
```

RCPT8C 不允许 replay：

```text
W0_2022_CURRENT_QLIB_LTR_UNAVAILABLE
W3_2026_06_17_DAILY_SCHEMA_ONLY
```

重要限制：

```text
W1 不得称为 strict OOS；
W2 不得称为 production-grade；
W2 是 RCPT8C mapping acceptance 的必要窗口。
```

## 8. Gate 冻结

RCPT8C 至少必须检查：

```text
integration gate
return_capture gate
drawdown gate
participation/all-cash gate
fee/turnover gate
mapping acceptance gate
forbidden action gate
```

关键规则：

```text
return_capture_vs_mapping_specific_adaptive_baseline >= 0.85
ideal >= 0.90
average_cash_rate <= 0.65
cash_gt_90pct_equity_day_share <= 0.25
average_position_count >= 5
```

如果 W2 失败，W1 不能救回，因为 W1 是训练污染 diagnostic。

## 9. Ledger Schema 冻结

RCPT8C replay ledger 只能是 readonly accounting artifact。

明确禁止：

```text
OrderIntent
target_weight
target_position
quantity_instruction
broker_order_id
quick_trade_flag
```

完整 schema 已写入：

```text
data_tw/experiments/risk_control_policy_2022/rcpt8b_qlib_ltr_adaptation_rule_contract/ledger_schema_contract.md
```

## 10. 输出文件

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt8b_qlib_ltr_adaptation_rule_contract/
```

已生成：

- `manifest.json`
- `candidate_b_adaptation_contract.md`
- `score_component_mapping_contract.csv`
- `baseline_contract.csv`
- `replay_window_contract.csv`
- `gate_contract.md`
- `ledger_schema_contract.md`
- `forbidden_action_audit.csv`
- `validator_report.json`

## 11. Validator 结果

```text
PASS_READY_FOR_RCPT8C_PREDECLARED_REPLAY
```

理由：

```text
1. RCPT8A 前提已满足；
2. 主 lineage 已冻结为 E3；
3. 三个 mapping 已冻结，且没有 replay 后搜索；
4. baseline/window/gate/ledger schema 已冻结；
5. 禁止事项审计通过；
6. 可以进入 RCPT8C，但 RCPT8C 必须严格按本合同 replay。
```

## 12. 下一步

建议进入：

```text
RCPT8C_PREDECLARED_QLIB_LTR_REPLAY
```

但 RCPT8C 必须：

```text
1. 只 replay M1/M2/M3；
2. 不新增 mapping；
3. 不调阈值；
4. 不把 W1 称为 strict OOS；
5. 不把 W2 称为 production-grade；
6. 不输出交易/仓位/数量指令；
7. 以 W2 是否通过作为进入 RCPT8D closure 的关键依据。
```
