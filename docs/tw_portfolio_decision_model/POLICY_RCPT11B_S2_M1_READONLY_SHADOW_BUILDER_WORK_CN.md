---
created_at: 2026-06-25
status: work_doc
phase: RCPT11B_S2_M1_READONLY_SHADOW_BUILDER
parent_review: docs/tw_portfolio_decision_model/POLICY_RCPT11B_R_M1_SHADOW_INPUT_LINEAGE_BRIDGE_OR_BUILDER_CONTRACT_REVIEW_CN.md
production_allowed: false
order_or_target_output_allowed: false
model_training_authorized: false
replay_authorized: false
threshold_tuning_authorized: false
---

# RCPT11B_S2 M1 Readonly Shadow Builder 工作文档

## 1. 目标

实现一个 M1-only readonly shadow builder，用于把合格的 daily qlib score/rank source artifact 转换为 RCPT11B 可积累的 shadow input。

S2 只构建输入，不执行 replay，不做收益评估，不进入 production proposal。

## 2. 非目标

S2 不授权：

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
使用 LTR rank/score 作为 M1 决策字段
```

## 3. 必读输入

必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT11_M1_EXTENDED_SHADOW_ACCUMULATION_AND_PRODUCTION_BLOCKER_CONTRACT_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT11B_R_M1_SHADOW_INPUT_LINEAGE_BRIDGE_OR_BUILDER_CONTRACT_REVIEW_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt11b_r_m1_shadow_input_lineage_bridge_or_builder_contract/
data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-17_score_snapshot.csv
data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-17_summary.json
data_tw/experiments/option_c_daily_signal/latest_signal.json
```

## 4. 输入选择

优先输入：

```text
data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-17_score_snapshot.csv
```

允许原因：

1. 它包含 `qlib_score`、`qlib_rank`、`qlib_score_raw`；
2. 它包含 `diagnostic_only=True`、`research_signal_not_order=True`、`pit_pass=True`；
3. S2 可以从中抽取 qlib-only 字段。

限制：

1. 不能直接 bridge 原 artifact；
2. 不能使用 `ltr_score` / `ltr_rank`；
3. 输出必须重新写为 M1-only shadow input；
4. 必须输出 lineage bridge audit，说明 LTR 字段被丢弃。

## 5. 必需输出

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt11b_s2_m1_readonly_shadow_builder/
```

必须生成：

```text
manifest.json
m1_readonly_shadow_input.csv
lineage_bridge_audit.csv
field_mapping_audit.csv
fail_close_audit.csv
forbidden_scope_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT11B_S2_M1_READONLY_SHADOW_BUILDER_EXECUTION_REPORT_CN.md
```

脚本建议：

```text
scripts/build_tw_policy_rcpt11b_s2_m1_readonly_shadow_builder.py
```

## 6. 输出字段

`m1_readonly_shadow_input.csv` 只能包含 readonly research/shadow 字段：

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

禁止输出：

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

## 7. Fail-close Gate

以下任何情况必须 fail-close：

1. `qlib_score` / `score` 缺失；
2. `qlib_rank` / `rank` 缺失；
3. `qlib_score_raw` 缺失且无允许 fallback；
4. `diagnostic_only` 不是 True；
5. `research_signal_not_order` 不是 True；
6. `pit_pass` 是 False；
7. 输出包含 LTR 决策字段；
8. 输出包含 action/order/target/quantity/broker 字段；
9. 写出到非隔离目录；
10. 试图修改 production/default/latest/provider/frontend/Agent/monitor/order。

## 8. 允许结论

```text
PASS_READY_FOR_RCPT11B_ACCUMULATION_RERUN
FAIL_CLOSE_NEEDS_SOURCE_OR_BUILDER_REPAIR
STOP_SCOPE_OR_SAFETY_VIOLATION
```

`PASS_READY_FOR_RCPT11B_ACCUMULATION_RERUN` 只授权重新进入 RCPT11B accumulation，不授权 production proposal 或生产接入。
