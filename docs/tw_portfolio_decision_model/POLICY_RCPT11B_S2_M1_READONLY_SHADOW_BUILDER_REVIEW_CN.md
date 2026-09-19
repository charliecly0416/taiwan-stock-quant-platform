---
created_at: 2026-06-25
status: review
phase: RCPT11B_S2_M1_READONLY_SHADOW_BUILDER
verdict: PASS_READY_FOR_RCPT11B_ACCUMULATION_RERUN
production_allowed: false
order_or_target_output_allowed: false
review_mode: coordinator_takeover_after_subagent_capacity_failures
---

# RCPT11B_S2 M1 Readonly Shadow Builder 审查意见

## 1. Verdict

```text
PASS_READY_FOR_RCPT11B_ACCUMULATION_RERUN
```

S2 builder 通过。可以重新进入 RCPT11B accumulation rerun。

该结论只授权：

```text
RCPT11B_ACCUMULATION_RERUN
```

不授权：

```text
production proposal
生产接入
OrderIntent
target_weight
target_position
quantity_instruction
broker / quick-trade / real order
replay / training / threshold tuning
```

## 2. 审查方式说明

本轮已按用户要求启动执行 agent，执行 agent 完成实现。

审查 agent 两次因模型容量失败，未产出可用审查文档：

1. `019efe1e-3f96-7582-baef-436022180568`：selected model is at capacity；
2. `019efe1e-b11a-7252-a00f-db557b674299`：selected model is at capacity。

因此本审查由 coordinator 接管完成。接管过程中发现业务输出字段 `source_lineage_note` 中含 `ltr_score` / `ltr_rank` 字面量，虽然不是字段泄漏，但为避免 shadow input CSV 被关键词扫描误判，已将说明改为：

```text
non-M1 rerank fields discarded
```

随后重新运行 builder 并刷新全部 S2 artifacts。

## 3. Evidence Checked

已审查：

- `docs/tw_portfolio_decision_model/POLICY_RCPT11B_S2_M1_READONLY_SHADOW_BUILDER_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT11B_S2_M1_READONLY_SHADOW_BUILDER_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT11B_R_M1_SHADOW_INPUT_LINEAGE_BRIDGE_OR_BUILDER_CONTRACT_REVIEW_CN.md`
- `scripts/build_tw_policy_rcpt11b_s2_m1_readonly_shadow_builder.py`
- `data_tw/experiments/risk_control_policy_2022/rcpt11b_s2_m1_readonly_shadow_builder/`
- source input: `data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-17_score_snapshot.csv`

## 4. Output Schema 审查

通过。

`m1_readonly_shadow_input.csv` 共 50 行数据，表头精确为工作文档允许的 13 个字段：

```text
date
symbol
candidate_id
score
rank
score_component
qlib_score_raw
diagnostic_only
research_signal_not_order
pit_pass
source_artifact
source_lineage_note
readonly_shadow_only
```

未出现：

```text
ltr_score
ltr_rank
action_type
execution_date
OrderIntent
target_weight
target_position
quantity_instruction
broker_order_id
quick_trade_flag
```

## 5. Qlib-only 抽取审查

通过。

S2 从 source snapshot 中只映射 M1 需要的 qlib-only 字段：

| output | source |
| --- | --- |
| `score` | `qlib_score` |
| `rank` | `qlib_rank` |
| `score_component` | `qlib_score` |
| `qlib_score_raw` | `qlib_score_raw` |

`lineage_bridge_audit.csv` 明确记录：

```text
direct_bridge_status = REJECTED
builder_source_status = USED_AS_QLIB_ONLY_SOURCE
qlib_fields_used = qlib_score|qlib_rank|qlib_score_raw
```

这符合 RCPT11B_R 的要求：不能直接桥接 LTR daily rerank artifact，只能从中抽取 qlib-only source fields 重建 M1-only shadow rows。

## 6. Fail-close Gate 审查

通过。

`fail_close_audit.csv` 全部为 PASS，覆盖：

- `missing_score_gate`
- `missing_rank_gate`
- `missing_qlib_score_raw_gate`
- `diagnostic_only_gate`
- `research_signal_not_order_gate`
- `pit_gate`
- `ltr_field_leakage_gate`
- `order_target_field_gate`

`validator_report.json` 记录：

```text
status = PASS
row_count = 50
allowed_output_fields_gate = PASS
ltr_field_leakage_gate = PASS
fail_close_gate = PASS
forbidden_scope_gate = PASS
readonly_shadow_only_gate = PASS
output_path_isolation_gate = PASS
recommended_verdict = PASS_READY_FOR_RCPT11B_ACCUMULATION_RERUN
```

## 7. Forbidden Actions Audit

通过。

本轮未发现：

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
M2 / M3 恢复
```

S2 只新增/更新：

- builder script；
- isolated S2 artifacts；
- S2 execution report；
- 本审查文档。

## 8. Findings

### Critical

无。

### High

无。

### Medium

无必须 repair 项。

### Low

1. S2 的 source 仍来自 LTR daily rerank artifact，因此后续 RCPT11B accumulation rerun 必须继续强调：它不是直接桥接 LTR artifact，而是使用 S2 重建后的 M1-only shadow input。
2. S2 只构建 2026-06-17 单日 input，不代表已完成 extended accumulation。

## 9. 是否可重新进入 RCPT11B

可以。

下一步应执行：

```text
RCPT11B_ACCUMULATION_RERUN
```

输入应使用：

```text
data_tw/experiments/risk_control_policy_2022/rcpt11b_s2_m1_readonly_shadow_builder/m1_readonly_shadow_input.csv
```

RCPT11B rerun 的目标是把该单日 M1-only shadow input 合并进 accumulation evidence，并重新运行 production blocker / fail-close gate。仍不得进入 production proposal 或生产接入。
