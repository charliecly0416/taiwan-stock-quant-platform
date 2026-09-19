---
created_at: 2026-06-25
status: work_doc
phase: RCPT12_MULTI_DAY_M1_SHADOW_ACCUMULATION_AND_BLOCKER_BURN_DOWN
parent_review: docs/tw_portfolio_decision_model/POLICY_RCPT11C_ACCUMULATION_REVIEW_CN.md
production_allowed: false
order_or_target_output_allowed: false
model_training_authorized: false
replay_authorized: false
threshold_tuning_authorized: false
---

# RCPT12 Multi-day M1 Shadow Accumulation And Blocker Burn-down 工作文档

## 1. 目标

RCPT12 目标是把 RCPT11 的单日 shadow accumulation 扩展为多日 M1-only readonly shadow accumulation，并分离：

```text
historical blockers
new-input blockers
```

本轮只做 readonly accumulation / blocker burn-down diagnostic，不做 production proposal。

## 2. 非目标

RCPT12 不授权：

```text
真实 replay
training
threshold tuning
mapping expansion
production/default/provider/latest/frontend/Agent/monitor/order 改动
OrderIntent
target_weight
target_position
quantity_instruction
broker / quick-trade / real order
production proposal
```

## 3. 必读输入

必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT11C_ACCUMULATION_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT11B_S2_M1_READONLY_SHADOW_BUILDER_REVIEW_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt10c_shadow_replay_diagnostic/shadow_replay_daily_evidence.csv
data_tw/experiments/risk_control_policy_2022/rcpt10c_shadow_replay_diagnostic/validator_report.json
data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-15_score_snapshot.csv
data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-15_summary.json
data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-17_score_snapshot.csv
data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-17_summary.json
```

## 4. 输入说明

可用 source days：

```text
2026-06-15
2026-06-17
```

每个 source day 必须按 S2 模式重建 M1-only shadow input：

1. 使用 `qlib_score` / `qlib_rank` / `qlib_score_raw`；
2. 丢弃非 M1 rerank fields；
3. 生成 M1-only readonly rows；
4. 不输出 action/order/target/quantity/broker 字段；
5. 检查 `diagnostic_only=True`、`research_signal_not_order=True`、`pit_pass=True`。

## 5. 必需输出

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/
```

必须输出：

```text
manifest.json
multi_day_m1_shadow_input.csv
multi_day_accumulated_shadow_evidence.csv
source_day_acceptance.csv
historical_vs_new_blocker_burn_down.csv
production_blocker_audit.csv
accumulation_summary.json
forbidden_scope_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT12_MULTI_DAY_M1_SHADOW_ACCUMULATION_AND_BLOCKER_BURN_DOWN_EXECUTION_REPORT_CN.md
```

脚本建议：

```text
scripts/build_tw_policy_rcpt12_multi_day_m1_shadow_accumulation.py
```

## 6. Burn-down 口径

必须分离：

```text
historical_null_metric_blocker_count
new_input_null_metric_blocker_count
new_input_accepted_day_count
new_input_rejected_day_count
new_input_total_rows
```

RCPT10C historical blocker 不得隐藏：

```text
2025-07-14 TW6919
2026-03-02 TW4989
```

但如果 2026-06-15 与 2026-06-17 都没有新 input blocker，可以记录：

```text
new_input_blocker_burn_down_status = CLEAN_FOR_OBSERVED_DAYS
production_gate_status = BLOCKED_BY_HISTORICAL_NULL_METRIC
```

## 7. 允许结论

```text
PASS_MULTI_DAY_SHADOW_ACCUMULATION_CLEAN_BUT_PRODUCTION_BLOCKED
FAIL_CLOSE_NEW_INPUT_BLOCKER_FOUND
STOP_SCOPE_OR_SAFETY_VIOLATION
```

即使第一种 PASS，也只表示多日 shadow input 对观察日干净；不授权 production proposal。
