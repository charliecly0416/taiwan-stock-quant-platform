---
created_at: 2026-06-25
status: execution_report
phase: RCPT9B_REPAIR_COVERAGE_GATE
verdict: PASS_READY_FOR_RCPT9C_PREDECLARED_LONGER_OOS_REPLAY
production_allowed: false
order_or_target_output_allowed: false
model_training_performed: false
replay_performed: false
---

# RCPT9B Repair Coverage Gate 执行报告

## 1. 修复范围

本轮只修复 RCPT9B 审查提出的 coverage gate 语义问题。

未做：

```text
新训练
RCPT9C replay
threshold tuning
new mapping search
production/default/provider/frontend/Agent/monitor/order 修改
OrderIntent / target_weight / target_position / quantity_instruction / broker / quick-trade 输出
```

## 2. 修复内容

修改 `scripts/build_tw_policy_rcpt9b_lineage_build.py`：

1. 为 `feature_label_coverage_audit.csv` 增加硬 gate 阈值；
2. `sample_complete_false_share <= 0.03`；
3. `feature_complete_false_share <= 0.03`；
4. `label_complete_10d_false_share <= 0.0`；
5. 增加 `gate_semantics = hard_gate_for_rcpt9b_lineage_readiness`；
6. `validator_report.json` 的 `feature_label_coverage_pass` 继续读取 coverage audit 的 `status`，不再是无阈值摘要。

## 3. 修复后证据

`data_tw/experiments/risk_control_policy_2022/rcpt9b_lineage_build/feature_label_coverage_audit.csv`：

| split | sample incomplete share | threshold | feature incomplete share | threshold | label incomplete share | threshold | status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| train | 0.027874 | 0.03 | 0.027874 | 0.03 | 0.0 | 0.0 | PASS |
| validation | 0.010926 | 0.03 | 0.010926 | 0.03 | 0.0 | 0.0 | PASS |
| test | 0.006147 | 0.03 | 0.006147 | 0.03 | 0.0 | 0.0 | PASS |

`validator_report.json`：

```text
overall_status = PASS_READY_FOR_RCPT9C_PREDECLARED_LONGER_OOS_REPLAY
feature_label_coverage_pass = true
failed_count = 0
```

## 4. 结论

```text
PASS_READY_FOR_RCPT9C_PREDECLARED_LONGER_OOS_REPLAY
```

RCPT9B 的条件性审查问题已修复，可以进入 RCPT9C predeclared longer OOS replay。
