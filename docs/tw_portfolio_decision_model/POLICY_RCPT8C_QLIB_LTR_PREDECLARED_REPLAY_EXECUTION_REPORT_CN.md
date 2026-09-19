---
created_at: 2026-06-25T04:46:01+00:00
phase: RCPT8C_QLIB_LTR_PREDECLARED_REPLAY
artifact_root: data_tw/experiments/risk_control_policy_2022/rcpt8c_qlib_ltr_predeclared_replay
validator_status: PASS
recommended_verdict: PASS_READY_FOR_RCPT8D_CLOSURE
production_allowed: false
order_or_target_output_allowed: false
model_training_performed: false
---

# RCPT8C Qlib+LTR Predeclared Replay 执行报告

## 1. 执行范围

本轮严格按 RCPT8B 冻结合同 replay。只回放 `M1_QLIB_SCORE_COMPONENT_PRIMARY`、`M2_LTR_SCORE_COMPONENT_SECONDARY`、`M3_BLEND_Q70_L30_TERTIARY`，只回放 W1 与 W2。

W1 固定解释为 `2023-2025 train-contaminated integration diagnostic`，不是 strict OOS。W2 固定解释为 `2026-01-02..2026-05-07 narrow strict OOS diagnostic`，不是 production-grade。

未训练模型、未新增 mapping、未改 alpha、未调阈值、未 replay 2022、未 replay 2026-06-17 single-day snapshot、未修改 production/default/provider/frontend/Agent/monitor/order 链路，未输出订单、目标仓位/权重或数量指令。

## 2. W2 关键结果

| mapping | baseline_return | candidate_return | return_capture | baseline_mdd | candidate_mdd | avg_cash | avg_pos | W2 gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| M1_QLIB_SCORE_COMPONENT_PRIMARY | 1.01283847 | 0.99748735 | 0.98484347 | 0.17195656 | 0.17195656 | 0.17006792 | 8.35443038 | PASS |
| M2_LTR_SCORE_COMPONENT_SECONDARY | 0.95320191 | 0.83492037 | 0.87591135 | 0.13675456 | 0.13675456 | 0.19870425 | 7.97468354 | PASS |
| M3_BLEND_Q70_L30_TERTIARY | 1.20165022 | 1.09406396 | 0.91046791 | 0.17425014 | 0.17425014 | 0.13054243 | 8.72151899 | FAIL |

## 3. Gate 结论

- validator status: `PASS`
- recommended verdict: `PASS_READY_FOR_RCPT8D_CLOSURE`
- W2 是 mapping acceptance 的必要窗口；W1 只支持机制诊断，不能救回 W2 失败。

## 4. 输出

输出目录：`data_tw/experiments/risk_control_policy_2022/rcpt8c_qlib_ltr_predeclared_replay`

已生成 manifest、window/candidate/gate 汇总、daily_nav/actions/trigger/cash/fee/concentration 审计、lineage_replay_audit、forbidden_action_audit、validator_report 和 diagnostic_findings。
