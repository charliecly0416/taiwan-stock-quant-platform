---
created_at: 2026-06-24
status: rcpt0_r_independent_review_completed
phase: RCPT0_R_CANDIDATE_HYPOTHESIS_CONSISTENCY_REPAIR
parent_phase: RCPT0_SCORE_RANK_REGIME_THRESHOLD_DISCOVERY
work_doc: docs/tw_portfolio_decision_model/POLICY_RCPT0_R_CANDIDATE_HYPOTHESIS_CONSISTENCY_REPAIR_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_RCPT0_R_CANDIDATE_HYPOTHESIS_CONSISTENCY_REPAIR_EXECUTION_REPORT_CN.md
prior_independent_review: docs/tw_portfolio_decision_model/POLICY_RCPT0_SCORE_RANK_REGIME_THRESHOLD_DISCOVERY_INDEPENDENT_REVIEW_CN.md
artifact_root: data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery
verdict: PASS_READY_FOR_RCPT1_PIT_SAFE_ADAPTIVE_THRESHOLD_RULE_DESIGN_WORK_DOC
readonly_review: true
policy_replay_performed_by_reviewer: false
risk_control_replay_performed_by_reviewer: false
model_training_performed_by_reviewer: false
strict_test_performed_by_reviewer: false
production_or_order_chain_change_performed_by_reviewer: false
---

# RCPT0-R Candidate Hypothesis Consistency Repair 独立审查报告

## 1. Verdict

`PASS_READY_FOR_RCPT1_PIT_SAFE_ADAPTIVE_THRESHOLD_RULE_DESIGN_WORK_DOC`

本轮 RCPT0-R 已完成要求的窄修复，且未发现 scope 泄漏或生产/订单链路越权。可以进入 RCPT1，但进入含义仅限：

```text
进入 PIT-safe adaptive threshold rule design 工作文档；
不得把 2022 诊断结论直接固化成生产规则；
不得把 H09 等 n<100 观察当成独立硬阈值。
```

## 2. Findings

### Critical

无。

### High

无。

### Medium

无。

### Low

1. `validator_report.json` 中的 `candidate_hypothesis_source_surface_crosscheck` 命名为 source-surface crosscheck，但脚本实现本质上是按 selector 从诊断数据集重算后再核对候选值，而不是逐条读取已落盘 surface CSV 做比较。
这不影响本轮通过，因为：

```text
H01 / H09 等关键候选已与 source surface 成品文件逐项一致；
validator 也已能稳定捕捉候选统计口径、自洽性、小样本降级与 forbidden audit 一致性。
```

后续若继续强化 validator，可再补一层对已落盘 surface CSV 的直接对比，但这不是本轮 gate 阻塞项。

## 3. Review Against Required Checks

### 3.1 H01 一致性

`candidate_threshold_hypotheses.csv` 的 H01 已严格对应：

```text
risk_off AND 0.4 <= raw_score < 0.8
```

证据：

```text
candidate_threshold_hypotheses.csv:
sample_count = 206
mean_future_return_5d = 0.01473884
mean_future_return_20d = 0.02341612
median_future_return_20d = 0.01420901
win_rate_20d = 0.51941748
```

与 `score_04_08_vs_08plus_audit.csv` 中 `market_regime=risk_off, score_bucket=raw_0.4_0.8` 完全一致。

文件证据：

```text
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/candidate_threshold_hypotheses.csv:2
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/score_04_08_vs_08plus_audit.csv:2
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/validator_report.json:10-21
scripts/run_tw_policy_rcpt0_score_rank_regime_threshold_discovery.py:666-680
scripts/run_tw_policy_rcpt0_score_rank_regime_threshold_discovery.py:900-949
```

结论：通过。

### 3.2 H09 及 n<100 候选降级

H09 已被降级为小样本 reference-only，不再可作为 T1 独立硬阈值。

证据：

```text
sample_count = 9
min_sample_gate_status = insufficient
reference_only_due_to_n_lt_100 = True
pit_safe_t1_possible = False
allowed_next_phase = REFERENCE_ONLY_INSUFFICIENT_SAMPLE
```

`pit_safe_candidate_filter.csv` 也同步写明：

```text
filter_decision = reference_only_insufficient_sample
t1_authorizable_after_recheck = False
threshold_can_be_written_as_predeclared_rule = False
```

文件证据：

```text
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/candidate_threshold_hypotheses.csv:10
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/score_04_08_vs_08plus_audit.csv:3
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/pit_safe_candidate_filter.csv:10
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/validator_report.json:123-126
scripts/run_tw_policy_rcpt0_score_rank_regime_threshold_discovery.py:770-781
scripts/run_tw_policy_rcpt0_score_rank_regime_threshold_discovery.py:819-841
```

结论：通过。

### 3.3 forbidden_action_audit 的 label_construction_only 标记

`entry_date_* / entry_open_* / exit_date_* / exit_close_*` 已被统一标记为：

```text
field_category = label_construction_only
used_for_ranking = false
used_for_strategy_input = false
status = pass
```

`future_return_*` 与 `future_return_label_available_*` 仍保持 `diagnostic_label_only`，且不进入 ranking / strategy input。

文件证据：

```text
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/forbidden_action_audit.csv:40-63
scripts/run_tw_policy_rcpt0_score_rank_regime_threshold_discovery.py:856-884
scripts/run_tw_policy_rcpt0_score_rank_regime_threshold_discovery.py:937-963
```

结论：通过。

### 3.4 validator 新增检查项并通过

`validator_report.json` 已新增并通过以下核心检查：

```text
candidate_hypothesis_consistency_status = PASS
candidate_hypothesis_source_surface_crosscheck = present
small_sample_hypothesis_status = PASS
forbidden_audit_consistency_status = PASS
recommended_next_step = PASS_READY_FOR_RCPT1_PIT_SAFE_ADAPTIVE_THRESHOLD_RULE_DESIGN_WORK_DOC
```

文件证据：

```text
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/validator_report.json:10-133
scripts/run_tw_policy_rcpt0_score_rank_regime_threshold_discovery.py:900-972
```

结论：通过。

### 3.5 未运行 replay / training / strict_test，未触碰生产或订单链路

已检查工作文档、执行报告、生成脚本与当前相关文件状态，未发现任何本轮越权证据。

执行报告声明：

```text
policy_replay_performed: false
risk_control_replay_performed: false
model_training_performed: false
strict_test_performed: false
production_chain_touched: false
order_chain_touched: false
```

脚本也明确把本轮限定为诊断产物生成与一致性校验，不输出订单、目标仓位或数量指令。

文件证据：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT0_R_CANDIDATE_HYPOTHESIS_CONSISTENCY_REPAIR_WORK_CN.md:1-117
docs/tw_portfolio_decision_model/POLICY_RCPT0_R_CANDIDATE_HYPOTHESIS_CONSISTENCY_REPAIR_EXECUTION_REPORT_CN.md:1-53
scripts/run_tw_policy_rcpt0_score_rank_regime_threshold_discovery.py:24-42
scripts/run_tw_policy_rcpt0_score_rank_regime_threshold_discovery.py:848-858
scripts/run_tw_policy_rcpt0_score_rank_regime_threshold_discovery.py:988-1123
```

结论：通过。

### 3.6 是否可以进入 RCPT1

可以进入 RCPT1，依据如下：

```text
H01 统计口径已修复并与 source surface 对齐；
H09 小样本已明确降级为 reference-only / insufficient；
forbidden_action_audit 不再把 label construction 字段误标成 ranking/strategy input；
validator 已覆盖候选一致性、小样本和 forbidden audit 一致性；
未发生 replay / training / strict_test / 生产链路 / 订单链路越权。
```

但 RCPT1 的边界必须继续保持：

```text
H01/H08 等只能作为 PIT-safe 规则设计候选，仍需 prior-window / walk-forward 方式再确认；
H09 仅可作为 supporting observation，不能写成独立 predeclared hard threshold；
不得把 2022 诊断收益统计直接表述为生产胜率或交易承诺。
```

## 4. Mainline / Safety Boundary Check

本次审查未发现以下违规：

```text
policy replay
risk-control replay
training
strict_test
production/default/provider/frontend/Agent chain modification
order / target_weight / target_position / quantity instruction output
```

本次 verdict 不是 `STOP_SCOPE_OR_LEAKAGE_VIOLATION`，因为当前问题已收敛为诊断产物修复完成后的合规通过状态，未发现已确认的策略输入泄漏或真实执行链路越权。

## 5. Evidence Checked

已读取并核查用户要求的全部材料：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT0_R_CANDIDATE_HYPOTHESIS_CONSISTENCY_REPAIR_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT0_R_CANDIDATE_HYPOTHESIS_CONSISTENCY_REPAIR_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT0_SCORE_RANK_REGIME_THRESHOLD_DISCOVERY_INDEPENDENT_REVIEW_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/candidate_threshold_hypotheses.csv
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/score_04_08_vs_08plus_audit.csv
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/pit_safe_candidate_filter.csv
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/forbidden_action_audit.csv
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/validator_report.json
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/diagnostic_findings.md
scripts/run_tw_policy_rcpt0_score_rank_regime_threshold_discovery.py
```

## 6. Final Authorization Statement

授权结论：

```text
PASS_READY_FOR_RCPT1_PIT_SAFE_ADAPTIVE_THRESHOLD_RULE_DESIGN_WORK_DOC
```

授权范围：

```text
仅授权进入 RCPT1 的 PIT-safe adaptive threshold rule design 文档与研究设计工作；
不授权直接把 RCPT0/RCPT0-R 的 2022 诊断阈值写入生产规则；
不授权任何 replay、training、strict_test、生产链路或订单链路动作。
```
