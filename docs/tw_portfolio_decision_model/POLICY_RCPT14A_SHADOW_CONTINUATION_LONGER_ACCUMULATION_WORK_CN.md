---
created_at: 2026-06-25
status: work_doc
phase: RCPT14A_SHADOW_CONTINUATION_LONGER_ACCUMULATION
parent_review: docs/tw_portfolio_decision_model/POLICY_RCPT13_HISTORICAL_BLOCKER_DISPOSITION_AND_SHADOW_CONTINUATION_CONTRACT_REVIEW_CN.md
production_allowed: false
order_or_target_output_allowed: false
model_training_authorized: false
replay_authorized: false
threshold_tuning_authorized: false
---

# RCPT14A Shadow Continuation Longer Accumulation 工作文档

## 1. 目标

RCPT14A 目标是延续 RCPT12 的 M1-only readonly shadow accumulation，并把 RCPT13 的 historical quarantine gate 纳入累计证据。

本阶段必须先做 source-day discovery：

1. 搜索本地 `daily_ltr_rerank_*_score_snapshot.csv`；
2. 识别 RCPT12 已接受 source days：`2026-06-15`, `2026-06-17`；
3. 若存在新增 source days，则按 RCPT12 S2-style M1-only builder 追加；
4. 若不存在新增 source days，不得伪造更长窗口，必须输出 no-new-day continuation audit；
5. 无论是否有新增 source day，都必须保留 RCPT13 quarantine gate。

## 2. 非目标

RCPT14A 不授权：

```text
真实 replay
training
threshold tuning
mapping expansion
production/default/latest/provider/frontend/Agent/monitor/order 改动
OrderIntent
target_weight
target_position
quantity_instruction
broker / quick-trade / real order
修改 RCPT10C/RCPT11/RCPT12/RCPT13 frozen evidence 原文件
下载新数据
伪造或复制 source day 以制造更长窗口
```

## 3. 必读输入

必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT13_HISTORICAL_BLOCKER_DISPOSITION_AND_SHADOW_CONTINUATION_CONTRACT_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT13_HISTORICAL_BLOCKER_DISPOSITION_AND_SHADOW_CONTINUATION_CONTRACT_EXECUTION_REPORT_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt13_historical_blocker_disposition_and_shadow_continuation_contract/validator_report.json
data_tw/experiments/risk_control_policy_2022/rcpt13_historical_blocker_disposition_and_shadow_continuation_contract/historical_blocker_disposition.csv
data_tw/experiments/risk_control_policy_2022/rcpt13_historical_blocker_disposition_and_shadow_continuation_contract/post_disposition_production_gate_audit.csv
data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/validator_report.json
data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/multi_day_m1_shadow_input.csv
data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/multi_day_accumulated_shadow_evidence.csv
data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/
```

## 4. 输出目录与必需产物

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt14a_shadow_continuation_longer_accumulation/
```

必须输出：

```text
manifest.json
source_day_discovery.csv
new_source_day_acceptance.csv
continued_shadow_input.csv
continued_accumulated_shadow_evidence.csv
historical_quarantine_gate_audit.csv
continuation_status.csv
forbidden_scope_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT14A_SHADOW_CONTINUATION_LONGER_ACCUMULATION_EXECUTION_REPORT_CN.md
```

建议脚本：

```text
scripts/build_tw_policy_rcpt14a_shadow_continuation.py
```

## 5. Source Day 规则

已接受 source days 来自 RCPT12：

```text
2026-06-15
2026-06-17
```

新增 source day 必须满足：

1. 文件名匹配 `daily_ltr_rerank_YYYY-MM-DD_score_snapshot.csv`；
2. 不在 RCPT12 accepted days 中；
3. 只用 `qlib_score` / `qlib_rank` / `qlib_score_raw` 重建 M1-only shadow input；
4. 丢弃非 M1 rerank fields；
5. `diagnostic_only=True`、`research_signal_not_order=True`、`pit_pass=True`、`readonly_shadow_only=True`；
6. 不输出 action/order/target/quantity/broker 字段。

如果没有新增 source day，必须：

```text
new_source_day_count = 0
continuation_status = NO_NEW_SOURCE_DAYS_AVAILABLE
production_gate_status = BLOCKED_BY_HISTORICAL_QUARANTINE_AND_INSUFFICIENT_ACCUMULATION
```

## 6. Validator 必须检查

`validator_report.json` 至少包含：

```text
phase
status
discovered_source_day_count
rcpt12_accepted_source_day_count
new_source_day_count
new_source_day_accepted_count
continued_daily_rows
rcpt13_quarantined_count
production_gate_status
production_allowed
order_or_target_output_allowed
replay_performed
model_training_performed
threshold_tuning_performed
production_chain_modified
historical_evidence_mutation_performed
recommended_verdict
recommended_next_phase
gate_statuses
```

必需 gates：

```text
source_day_discovery_gate
no_duplicate_source_day_gate
m1_only_shadow_input_gate
rcpt13_quarantine_visibility_gate
production_gate_not_unblocked_gate
forbidden_scope_gate
historical_evidence_immutability_gate
output_path_isolation_gate
```

## 7. 允许结论

```text
PASS_CONTINUATION_ACCUMULATED_MORE_DAYS_BUT_PRODUCTION_BLOCKED
PASS_CONTINUATION_AUDIT_COMPLETE_NO_NEW_DAYS_PRODUCTION_BLOCKED
FAIL_NEEDS_REPAIR_SOURCE_DAY_OR_FORBIDDEN_SCOPE
STOP_SCOPE_OR_SAFETY_VIOLATION
```

不允许：

```text
PASS_READY_FOR_PRODUCTION
PASS_READY_FOR_ORDER_OUTPUT
```

## 8. 审查者重点

审查者必须确认：

1. 是否真实发现新增 source days；
2. 若没有新增 source days，执行者是否没有伪造或重复计数；
3. RCPT13 quarantine 是否仍可见；
4. production gate 是否没有被放开；
5. 是否没有 replay/training/tuning/production/order 输出；
6. frozen evidence 是否没有被修改。
