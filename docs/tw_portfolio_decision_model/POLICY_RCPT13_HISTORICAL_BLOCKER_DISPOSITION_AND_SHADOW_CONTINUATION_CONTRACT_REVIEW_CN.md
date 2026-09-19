---
created_at: 2026-06-25
status: review
phase: RCPT13_HISTORICAL_BLOCKER_DISPOSITION_AND_SHADOW_CONTINUATION_CONTRACT
executor_report: docs/tw_portfolio_decision_model/POLICY_RCPT13_HISTORICAL_BLOCKER_DISPOSITION_AND_SHADOW_CONTINUATION_CONTRACT_EXECUTION_REPORT_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_RCPT13_HISTORICAL_BLOCKER_DISPOSITION_AND_SHADOW_CONTINUATION_CONTRACT_WORK_CN.md
review_mode: coordinator_manual_review_after_review_subagent_capacity_error
production_allowed: false
---

# RCPT13 Historical Blocker Disposition And Shadow Continuation Contract 审查意见

## 1. Verdict

`PASS_DISPOSITION_COMPLETE_BUT_PRODUCTION_BLOCKED_OR_CONDITIONAL`

RCPT13 执行可以接受：两个 historical blocker 都完成了 disposition，且没有被静默修复或隐藏。

最终处置为：

```text
2025-07-14 TW6919 -> QUARANTINED_LINEAGE_NOT_RECOVERABLE
2026-03-02 TW4989 -> QUARANTINED_LINEAGE_NOT_RECOVERABLE
```

Production gate 仍为：

```text
BLOCKED_BY_HISTORICAL_QUARANTINE
```

因此本轮只关闭 historical blocker disposition，不授权 production proposal 或 production integration。

审查子 agent 因模型容量错误未能产出审查文档；本文件由 coordinator 按同一审查合同手动补审查。

## 2. Findings

### Critical

无。

### High

无生产越权。

两个 blocker 均未满足 contract-complete repair，因此 quarantine 合理。执行者没有把 partial source 强行判为 repaired，这是正确的。

### Medium

找到了 partial exact lineage source：

```text
2025-07-14 TW6919:
  phase_o3_row_aligned_treatment_sample
  qlib_score_raw = 0.0116690638639318
  qlib_rank = 46.0
  qlib_score_percentile_by_date = 0.7

2026-03-02 TW4989:
  phase_o3_row_aligned_treatment_sample
  qlib_score_raw = 0.0909452029469398
  qlib_rank = 9.0
  qlib_score_percentile_by_date = 0.9466666666666668
  phase_o4_controlled_treatment_ltr also has qlib_score_raw and qlib_rank
```

但这些 source 不直接包含 RCPT13 repair 所需的完整字段：

```text
score 或 qlib_score
rank 或 qlib_rank
score_component
qlib_score_raw
```

缺少直接 `score/qlib_score` 与 `score_component`，因此不能标为 `REPAIRED_FROM_EXISTING_ARTIFACT`。

### Low

无。

## 3. Mainline Compliance

通过。

已确认：

```text
blocker_count = 2
repaired_count = 0
quarantined_count = 2
still_open_count = 0
production_gate_status = BLOCKED_BY_HISTORICAL_QUARANTINE
rcpt12_new_input_total_rows = 100
rcpt12_new_input_null_metric_blocker_count = 0
```

`historical_blocker_disposition.csv` 只包含：

```text
2025-07-14 TW6919
2026-03-02 TW4989
```

这符合 RCPT13 scope。

## 4. Evidence Checked

已检查：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT13_HISTORICAL_BLOCKER_DISPOSITION_AND_SHADOW_CONTINUATION_CONTRACT_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT13_HISTORICAL_BLOCKER_DISPOSITION_AND_SHADOW_CONTINUATION_CONTRACT_EXECUTION_REPORT_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt13_historical_blocker_disposition_and_shadow_continuation_contract/validator_report.json
data_tw/experiments/risk_control_policy_2022/rcpt13_historical_blocker_disposition_and_shadow_continuation_contract/historical_blocker_disposition.csv
data_tw/experiments/risk_control_policy_2022/rcpt13_historical_blocker_disposition_and_shadow_continuation_contract/historical_blocker_repair_or_quarantine_evidence.csv
data_tw/experiments/risk_control_policy_2022/rcpt13_historical_blocker_disposition_and_shadow_continuation_contract/post_disposition_production_gate_audit.csv
data_tw/experiments/risk_control_policy_2022/rcpt13_historical_blocker_disposition_and_shadow_continuation_contract/forbidden_scope_audit.csv
data_tw/experiments/risk_control_policy_2022/rcpt13_historical_blocker_disposition_and_shadow_continuation_contract/shadow_accumulation_continuation_plan.md
```

`validator_report.json` 为：

```text
status = PASS
recommended_verdict = PASS_DISPOSITION_COMPLETE_BUT_PRODUCTION_BLOCKED_OR_CONDITIONAL
recommended_next_phase = RCPT14_SHADOW_CONTINUATION_OR_SEPARATE_PRODUCTION_GO_NO_GO_DECISION
```

## 5. Missing Evidence Or Open Questions

缺口 1：quarantine 是否可被 production readiness 接受，仍需单独 route 决策。

当前 quarantine 只是“显式处置且不隐藏风险”，不是 production unlock。

缺口 2：若要把 partial source 转为 repair，需要 coordinator 另行授权 mapping contract，例如明确：

```text
score = qlib_score_percentile_by_date 或 qlib_score_raw
score_component = qlib_score_zscore_by_date 或 qlib_score_raw
```

但这会改变 RCPT13 repair contract，本轮未授权。

## 6. Forbidden Actions Audit

通过。

已确认：

```text
no_replay_execution = PASS
no_model_training = PASS
no_threshold_tuning = PASS
no_mapping_expansion = PASS
no_production_default_latest_provider_write = PASS
no_frontend_agent_monitor_order_write = PASS
no_order_target_quantity_broker_output = PASS
historical_evidence_immutability = PASS
output_path_isolation = PASS
```

执行产物没有授权或输出：

```text
OrderIntent
target_weight
target_position
quantity_instruction
broker / quick-trade / real order
production/default/latest/provider/frontend/Agent/monitor/order changes
```

## 7. Next Work Document

建议下一步不要直接 production。

可选路径：

```text
RCPT14A_SHADOW_CONTINUATION_LONGER_ACCUMULATION
```

继续积累 M1-only readonly shadow input，把 RCPT13 quarantine 作为显式 historical disposition 保留在 production gate audit 中。

或：

```text
RCPT14B_QUARANTINE_ACCEPTANCE_GO_NO_GO_CONTRACT
```

专门审查是否可以在 production readiness route 中接受这两个 historical quarantine。该路线仍不得直接生成 order/target/broker，也不得改 production/default/latest/provider。

当前更稳妥建议：

```text
先做 RCPT14A，再决定是否需要 RCPT14B。
```

原因是 RCPT12 只有两个新增观察日，shadow accumulation 仍短；即使 historical quarantine 被显式处置，也还缺少更长观察窗口。

## 8. Command For Executor Or Coordinator

如继续，coordinator 应写 RCPT14A work doc：

```text
请基于 RCPT13 审查结论启动 RCPT14A_SHADOW_CONTINUATION_LONGER_ACCUMULATION。保持 readonly M1-only shadow accumulation，保留 RCPT13 historical quarantine gate，不做 replay/training/tuning/production/default/latest/provider/frontend/Agent/monitor/order 改动，不输出 order/target/quantity/broker。
```
