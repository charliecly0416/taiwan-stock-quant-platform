---
created_at: 2026-06-22T04:09:21+00:00
status: executed_policy_search
phase: PE1_QLIB_ONLY_SIMULATION_IN_THE_LOOP_POLICY_SEARCH
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PE_EPISODIC_PORTFOLIO_POLICY_MAINLINE_CN.md
work_document: docs/tw_portfolio_decision_model/POLICY_PE0_EPISODIC_POLICY_CONTRACT_DESIGN_REVIEW_CN.md
artifact_root: data_tw/experiments/policy_episode_research/pe1_qlib_only_policy_search
recommendation: PASS_READY_FOR_PE2_STRICT_TEST
readonly_only: true
simulation_only: true
not_order: true
not_target_position: true
not_target_weight: true
not_investment_advice: true
production_allowed: false
no_provider_publish: true
no_accepted_latest_switch: true
no_monitor_write: true
no_broker: true
---

# PE1 Qlib-only Simulation-in-the-loop Policy Search 执行报告

## 1. Scope

本轮严格执行 PE1。只使用 qlib-only signal artifact，在 train/validation 上搜索参数化 episodic policy。未运行 strict_test，未接 frontend / Agent / provider / broker，未输出 target_weight / target_position / quantity / broker order。

## 2. Documents / Contracts / Skills Read

已读取主线、PE0 审查与执行报告、PAV2 route closure、项目宪法、ModelSignal / StrategyRule / OrderIntent / ReplayResult 合同，以及 coordinator / new-model / new-strategy / safety-boundary skills。

## 3. Research Adoption Audit

Research Adoption Audit 见 `manifest.json` 和设计冻结报告。当前 PE1 采用 family A/B/C；Family D deferred，直到 regime features 经 PIT-safe proof。

## 4. Policy Search Space

本轮搜索采用 deterministic grid。候选来自 family C baseline-plus offensive override、family A aggressive rank-capture、family B switch-pair return capture；candidate_k ∈ {50,100,150}。strict_test 不参与候选生成、剪枝或选择。

## 5. Train / Validation Replay

输出文件：

```text
data_tw/experiments/policy_episode_research/pe1_qlib_only_policy_search/train_replay_metrics.csv
data_tw/experiments/policy_episode_research/pe1_qlib_only_policy_search/validation_replay_metrics.csv
```

PE1 仅用 validation 进行 final selection。

## 6. Validation Selection

输出文件：

```text
data_tw/experiments/policy_episode_research/pe1_qlib_only_policy_search/validation_selection_audit.csv
```

selection metric：validation net_return_after_fee_tax first, then participation, then action_count, then drawdown.

## 7. Participation Guardrail

输出文件：

```text
data_tw/experiments/policy_episode_research/pe1_qlib_only_policy_search/participation_audit.csv
```

PE1 不能靠大规模 no_action / 低参与获利。

## 8. Artifact Schema Freeze

EpisodicPolicyConfigArtifact / PolicyTrajectoryDecisionArtifact / PolicyEpisodeEvaluationArtifact schema 已冻结在 PE0 设计中；PE1 只实现并评估 search protocol，不更改 schema 语义。

## 9. Validator 与 Golden Samples

Validator: PASS_PE1_QLIB_ONLY_POLICY_SEARCH_VALIDATION / failed_count=0

Golden: PASS_PE1_GOLDEN_SAMPLES / failed_count=0

## 10. Forbidden Actions Audit

未触发 provider publish、accepted latest switch、monitor write、broker、quick-trade、真实订单、frontend default switch、Agent/OpenAI。

## 11. Strict Test Boundary

strict_test 未运行，且不得用于选择。`strict_test_used_for_selection=false` 已写入 manifest / selection audit。

## 12. Recommendation For Reviewer

```text
PASS_READY_FOR_PE2_STRICT_TEST
```
