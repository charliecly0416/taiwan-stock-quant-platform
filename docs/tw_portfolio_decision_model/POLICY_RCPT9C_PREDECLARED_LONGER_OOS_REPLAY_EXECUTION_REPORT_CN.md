---
created_at: 2026-06-25T05:32:28+00:00
phase: RCPT9C_PREDECLARED_LONGER_OOS_REPLAY
artifact_root: data_tw/experiments/risk_control_policy_2022/rcpt9c_predeclared_longer_oos_replay
validator_status: PASS
recommended_verdict: PASS_READY_FOR_RCPT9D_CLOSURE
production_allowed: false
order_or_target_output_allowed: false
model_training_performed: false
---

# RCPT9C Predeclared Longer OOS Replay 执行报告

## 1. 执行范围

本轮只 replay RCPT9B lineage package 冻结的 holdout：`2025-07-01..2026-05-07`。

只允许 M1/M2；M3 未 replay。未训练模型、未新增 mapping、未调阈值、未修改生产/default/provider/frontend/Agent/monitor/order 链路，未输出订单、目标仓位/权重或数量指令。

## 2. Holdout 关键结果

| mapping | baseline_return | candidate_return | return_capture | baseline_mdd | candidate_mdd | avg_cash | avg_pos | gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| M1_QLIB_SCORE_COMPONENT_PRIMARY | 2.27529371 | 2.5612863 | 1.1256948 | 0.14126266 | 0.14126266 | 0.06759263 | 9.37560976 | PASS |
| M2_LTR_SCORE_COMPONENT_SECONDARY | 2.20020279 | 2.05899812 | 0.93582197 | 0.15547466 | 0.15597963 | 0.08157253 | 9.19512195 | FAIL |

## 3. Gate 结论

- validator status: `PASS`
- recommended verdict: `PASS_READY_FOR_RCPT9D_CLOSURE`
- RCPT9C 结论只用于 RCPT9D closure，不代表 production 授权。
