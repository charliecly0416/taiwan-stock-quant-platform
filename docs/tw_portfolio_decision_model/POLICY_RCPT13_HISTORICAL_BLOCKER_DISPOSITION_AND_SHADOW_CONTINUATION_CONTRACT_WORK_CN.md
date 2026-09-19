---
created_at: 2026-06-25
status: work_doc
phase: RCPT13_HISTORICAL_BLOCKER_DISPOSITION_AND_SHADOW_CONTINUATION_CONTRACT
parent_review: docs/tw_portfolio_decision_model/POLICY_RCPT12_MULTI_DAY_M1_SHADOW_ACCUMULATION_AND_BLOCKER_BURN_DOWN_REVIEW_CN.md
production_allowed: false
order_or_target_output_allowed: false
model_training_authorized: false
replay_authorized: false
threshold_tuning_authorized: false
historical_evidence_mutation_allowed: false
---

# RCPT13 Historical Blocker Disposition And Shadow Continuation Contract 工作文档

## 1. 目标

RCPT13 只处理 RCPT10C/RCPT11/RCPT12 一直保留的 2 个 historical null metric production blocker：

```text
2025-07-14 TW6919
2026-03-02 TW4989
```

本阶段目标是给出可审查的 disposition：

1. 如果能从既有 readonly frozen artifacts / lineage 中补齐 `score|rank|score_component|qlib_score_raw`，产出 repair evidence；
2. 如果不能补齐，产出 explicit quarantine / exclusion disposition；
3. 无论 repair 还是 quarantine，都必须保留 production gate audit；
4. 同时给出 shadow accumulation continuation plan。

本阶段不是 production proposal，也不允许把 production gate 直接放开。

## 2. 非目标

RCPT13 不授权：

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
修改 RCPT10C/RCPT11/RCPT12 historical evidence 原文件
用猜测值、均值、排名重算、未来数据、外部下载数据补 blocker
```

## 3. 必读输入

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT12_MULTI_DAY_M1_SHADOW_ACCUMULATION_AND_BLOCKER_BURN_DOWN_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT12_MULTI_DAY_M1_SHADOW_ACCUMULATION_AND_BLOCKER_BURN_DOWN_EXECUTION_REPORT_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/validator_report.json
data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/accumulation_summary.json
data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/multi_day_accumulated_shadow_evidence.csv
data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/historical_vs_new_blocker_burn_down.csv
data_tw/experiments/risk_control_policy_2022/rcpt10c_shadow_replay_diagnostic/shadow_replay_daily_evidence.csv
data_tw/experiments/risk_control_policy_2022/rcpt10c_shadow_replay_diagnostic/validator_report.json
```

可选只读搜索范围：

```text
data_tw/experiments/risk_control_policy_2022/
data_tw/experiments/ltr_orthogonal_features_controlled/
data_tw/
docs/tw_portfolio_decision_model/
```

只允许读取本地已有 artifacts，不允许下载新数据。

## 4. Disposition 规则

每个 historical blocker 必须独立分类：

```text
REPAIRED_FROM_EXISTING_ARTIFACT
QUARANTINED_LINEAGE_NOT_RECOVERABLE
STILL_OPEN_INSUFFICIENT_EVIDENCE
```

### 4.1 可接受 repair 的条件

只有同时满足以下条件，才可标记 `REPAIRED_FROM_EXISTING_ARTIFACT`：

1. 找到本地既有 artifact，且 artifact timestamp / path / lineage 可追溯；
2. artifact 对应同一 `date` 与 `symbol`；
3. 可直接读取 `score` 或 `qlib_score`、`rank` 或 `qlib_rank`、`qlib_score_raw`；
4. `score_component` 只能来自同一 artifact 的 qlib/M1 score，或明确等同于 `score`；
5. 不使用未来数据、不重新训练、不重新 replay、不按事后收益补值；
6. 输出 evidence 必须包含 source artifact path、source columns、extracted values、lineage note。

### 4.2 可接受 quarantine 的条件

如果不能满足 repair 条件，必须标记：

```text
QUARANTINED_LINEAGE_NOT_RECOVERABLE
```

并说明：

1. 缺少哪个字段；
2. 搜索了哪些 artifact family；
3. 为什么不能安全补齐；
4. quarantine 对 production gate 的影响。

Quarantine 不是隐藏 blocker。Quarantine 后 production gate 不能直接 PASS，只能是：

```text
BLOCKED_BY_HISTORICAL_QUARANTINE
```

或在后续 coordinator 明确接受 quarantine policy 后，进入单独 production-readiness route。

## 5. 必需输出

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt13_historical_blocker_disposition_and_shadow_continuation_contract/
```

必须输出：

```text
manifest.json
historical_blocker_disposition.csv
historical_blocker_repair_or_quarantine_evidence.csv
post_disposition_production_gate_audit.csv
shadow_accumulation_continuation_plan.md
forbidden_scope_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT13_HISTORICAL_BLOCKER_DISPOSITION_AND_SHADOW_CONTINUATION_CONTRACT_EXECUTION_REPORT_CN.md
```

建议脚本：

```text
scripts/build_tw_policy_rcpt13_historical_blocker_disposition.py
```

## 6. Validator 必须检查

`validator_report.json` 至少包含：

```text
phase
status
blocker_count
repaired_count
quarantined_count
still_open_count
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
input_blocker_scope_gate
disposition_completeness_gate
repair_lineage_gate
quarantine_explicitness_gate
production_gate_not_unblocked_gate
forbidden_scope_gate
historical_evidence_immutability_gate
output_path_isolation_gate
```

## 7. 允许结论

```text
PASS_DISPOSITION_COMPLETE_BUT_PRODUCTION_BLOCKED_OR_CONDITIONAL
FAIL_NEEDS_REPAIR_INCOMPLETE_DISPOSITION
STOP_SCOPE_OR_SAFETY_VIOLATION
```

不允许结论：

```text
PASS_READY_FOR_PRODUCTION
PASS_READY_FOR_ORDER_OUTPUT
```

## 8. 审查者重点

审查者必须独立确认：

1. 只处理两个指定 historical blockers；
2. 没有改 RCPT10C/RCPT11/RCPT12 frozen evidence 原文件；
3. repair 不使用猜测、未来数据、重训、replay、收益反推；
4. quarantine 明确说明为什么不能补；
5. production gate 没有被错误放开；
6. forbidden outputs 中没有 order/action/target/quantity/broker 字段；
7. continuation plan 只是 shadow accumulation plan，不是 production plan。
