---
created_at: 2026-06-24T00:00:00+00:00
status: independent_review
phase: RCPT7C_ADAPTIVE_SCORE_ALIGNED_CLOSURE
reviewer: RCPT7C_ADAPTIVE_SCORE_ALIGNED_CLOSURE
verdict: PASS_RCPT7_CLOSED_READY_FOR_QLIB_LTR_ADAPTATION_DESIGN
production_allowed: false
order_or_target_output_allowed: false
---

# RCPT7C Adaptive-score-aligned Closure 独立审查报告

## 1. 审查结论

```text
PASS_RCPT7_CLOSED_READY_FOR_QLIB_LTR_ADAPTATION_DESIGN
```

本审查确认执行者按 `POLICY_RCPT7C_ADAPTIVE_SCORE_ALIGNED_CLOSURE_WORK_CN.md` 完成了 closure 汇总：未重跑 replay，未修改候选规则或阈值，正确采用 RCPT7B_R 修复后的候选分类，并将 Candidate B 作为唯一 closure-eligible research candidate。

RCPT7 可以 closure，但仅限 research closure。下一步允许进入新的 qlib+LTR adaptation design 合同；当前结论不授权 production/default/provider/frontend/Agent/monitor/order 链路，也不授权任何交易、仓位或数量指令。

## 2. 已审查依据

- `docs/tw_portfolio_decision_model/POLICY_RCPT7C_ADAPTIVE_SCORE_ALIGNED_CLOSURE_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT7C_ADAPTIVE_SCORE_ALIGNED_CLOSURE_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT7_ADAPTIVE_SCORE_ALIGNED_RISK_CONTROL_REPAIR_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT7B_R_BASELINE_EQUIVALENT_CLASSIFICATION_REPAIR_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT7B_ADAPTIVE_SCORE_ALIGNED_REPLAY_REVIEW_CN.md`
- `data_tw/experiments/risk_control_policy_2022/rcpt7c_adaptive_score_aligned_closure/`
- 抽查上游产物：
  - `data_tw/experiments/risk_control_policy_2022/rcpt7b_r_baseline_equivalent_classification_repair/repaired_gate_decision_by_candidate.csv`
  - `data_tw/experiments/risk_control_policy_2022/rcpt7b_r_baseline_equivalent_classification_repair/baseline_equivalence_audit.csv`
  - `data_tw/experiments/risk_control_policy_2022/rcpt7b_r_baseline_equivalent_classification_repair/repaired_candidate_vs_adaptive_baseline.csv`
  - `data_tw/experiments/risk_control_policy_2022/rcpt7b_adaptive_score_aligned_replay/`

## 3. 输出完整性

结论：PASS。

RCPT7C 输出目录存在，且包含工作文档要求的全部文件：

- `manifest.json`
- `final_candidate_decision.csv`
- `final_metric_summary.csv`
- `closure_evidence_index.md`
- `deployment_boundary.md`
- `next_route_recommendation.md`
- `forbidden_action_audit.csv`
- `validator_report.json`

执行报告也已生成：

- `docs/tw_portfolio_decision_model/POLICY_RCPT7C_ADAPTIVE_SCORE_ALIGNED_CLOSURE_EXECUTION_REPORT_CN.md`

## 4. Scope / Replay / Rules / Thresholds

结论：PASS。

证据：

- `manifest.json` 将 scope 标记为 `readonly_closure_summary_only`。
- `scope_guardrails` 中 `replay_rerun_performed=false`、`candidate_rules_changed=false`、`new_candidate_added=false`、`threshold_tuning_performed=false`、`model_training_performed=false`。
- `validator_report.json` 中 `no_replay_rerun`、`no_candidate_rule_change`、`no_new_candidate`、`no_threshold_tuning`、`no_model_training` 全部为 `PASS`。
- `forbidden_action_audit.csv` 对 replay rerun、候选规则变更、新增候选、阈值调优、模型训练、LTR/orthogonal LTR/stacking score read 均为 `PASS_NOT_PRESENT_OR_NOT_PERFORMED`。

未发现 RCPT7C 阶段重跑 replay、修改 Candidate A/B/C、调阈值、训练模型或替换输入 lineage 的证据。

## 5. RCPT7B_R 分类使用

结论：PASS。

RCPT7C 明确使用 RCPT7B_R 修复后的分类源：

```text
data_tw/experiments/risk_control_policy_2022/rcpt7b_r_baseline_equivalent_classification_repair/repaired_gate_decision_by_candidate.csv
```

分类在 RCPT7C 产物中保持一致：

| candidate | RCPT7B_R 修复后分类 | RCPT7C closure eligible |
| --- | --- | --- |
| Candidate A | `FAIL_RETURN_CAPTURE` | false |
| Candidate B | `PASS_NON_BASELINE_EQUIVALENT` | true |
| Candidate C | `BASELINE_EQUIVALENT_NO_OP` | false |

抽查 `baseline_equivalence_audit.csv` 显示 Candidate C 在 2021、2022、2023-2025 三个窗口均为 `window_baseline_equivalent=True`；Candidate B 三个窗口均非 baseline-equivalent。RCPT7C 对该分类的继承正确。

## 6. Candidate B Closure Eligibility

结论：PASS。

Candidate B 是唯一 closure-eligible 候选。关键证据与 RCPT7B_R 一致：

- 2023-01-03 至 2025-06-30 qlib-only TEST fold strict OOS candidate 中，Candidate B `return_capture=0.96060850`。
- Candidate B max drawdown severity 为 `0.36230989`，adaptive baseline 为 `0.56426863`。
- Candidate B average cash rate 为 `0.30328641`，cash > 90% equity day share 为 `0.01675042`。
- Candidate B fee/tax 为 `448162.35`，比 adaptive baseline 低 `42683.84`。
- RCPT7C 文档将 Candidate B 表述为少量牺牲收益、换取更低回撤的 research candidate，而不是收益增强策略或生产策略。

该结论符合 RCPT7 主线要求的 tradeoff：在强 adaptive baseline 基础上，保留大部分收益，同时改善回撤。

## 7. Candidate C 处理

结论：PASS。

RCPT7C 没有把 Candidate C 包装为提升：

- `final_candidate_decision.csv` 将 Candidate C 标记为 `EXCLUDE_BASELINE_EQUIVALENT_NO_OP`。
- `final_metric_summary.csv` 在三个窗口均说明 Candidate C 与 adaptive baseline 等价或为 no-op。
- `closure_evidence_index.md` 明确 Candidate C 因为在收益、回撤、现金、动作、费用和 trigger behavior 上完全匹配 adaptive baseline 而被排除。
- `forbidden_action_audit.csv` 中 `candidate_c_improvement_claim=False` 且状态为 `PASS_NOT_PRESENT_OR_NOT_PERFORMED`。

因此 RCPT7 closure 不依赖 Candidate C。

## 8. Window 语义

结论：PASS。

RCPT7C 正确区分窗口语义：

- 2022 被标记为 `downturn diagnostic not strict OOS`。
- 2023-2025 被标记为 `qlib-only TEST fold strict OOS candidate 2023-01-03 to 2025-06-30 not full 2025 calendar year`。
- `deployment_boundary.md` 和 `validator_report.json` 均明确不得声称完整 2025 calendar-year 结果。

未发现把 2022 表述为 strict OOS，或把 2023-2025 表述为完整 2025 自然年的证据。

## 9. Production / Order / Target 边界

结论：PASS。

RCPT7C 没有 production/default/provider/frontend/Agent/monitor/order 越权：

- `manifest.json` 中 `production_default_provider_frontend_agent_monitor_order_chain_changed=false`。
- `deployment_boundary.md` 明确 `No deployment is authorized`，且 Candidate B 不得进入 default provider、frontend、Agent、monitor、broker、quick-trade 或 order chain。
- `forbidden_action_audit.csv` 中 production chain change、trade/position sizing artifact、broker/quick-trade connection 均为 False。

关键词抽查 `OrderIntent`、`target_weight`、`target_position`、`quantity_instruction`、broker、quick-trade、order、production-ready 等命中均处于否定声明、安全边界或 forbidden audit 语境，未发现实际交易意图、目标仓位、目标权重或数量指令产物。

## 10. Final Verdict 与下一步

结论：PASS。

执行报告 final verdict：

```text
PASS_AS_RESEARCH_CANDIDATE_READY_FOR_QLIB_LTR_ADAPTATION_DESIGN
```

该 verdict 属于 RCPT7C 工作文档允许值。审查结论对应为：

```text
PASS_RCPT7_CLOSED_READY_FOR_QLIB_LTR_ADAPTATION_DESIGN
```

下一步路线正确限定为：

```text
qlib+LTR adaptation design only under a new contract
```

不允许直接生产化。后续若进入 qlib+LTR adaptation design，必须另开合同，冻结 signal lineage、窗口和 gates；在读取或使用 LTR-family score 前重新授权；任何生产接入必须另做 replay、验收和安全审查。

## 11. Final Verdict

```text
PASS_RCPT7_CLOSED_READY_FOR_QLIB_LTR_ADAPTATION_DESIGN
```
