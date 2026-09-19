---
created_at: 2026-06-22
status: review_pass_ready_for_pe1_with_conditions
phase_reviewed: PE0_EPISODIC_PORTFOLIO_POLICY_CONTRACT_AND_RESEARCH_DESIGN_FREEZE
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PE_EPISODIC_PORTFOLIO_POLICY_MAINLINE_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_PE0_EPISODIC_POLICY_CONTRACT_DESIGN_EXECUTION_REPORT_CN.md
next_phase: PE1_QLIB_ONLY_SIMULATION_IN_THE_LOOP_POLICY_SEARCH
next_work_document_included: true
readonly_only: true
simulation_only: true
production_allowed: false
no_provider_publish: true
no_accepted_latest_switch: true
no_monitor_write: true
no_broker: true
no_frontend_default_switch: true
not_target_position: true
not_target_weight: true
not_order: true
verdict: PASS_READY_FOR_PE1_QLIB_ONLY_POLICY_SEARCH_WITH_CONDITIONS
---

# PE0 Episodic Policy Contract Design 审查报告与 PE1 工作文档

## 1. 审查结论

结论：

```text
PASS_READY_FOR_PE1_QLIB_ONLY_POLICY_SEARCH_WITH_CONDITIONS
```

PE0 执行报告符合 `POLICY_PE_EPISODIC_PORTFOLIO_POLICY_MAINLINE_CN.md` 对 PE0 的核心要求：本轮停留在 contract / research / schema / validator / golden sample / PE1 protocol 设计层，没有训练模型、没有搜索参数、没有 replay 收益结论、没有运行 strict_test，也没有 provider / accepted latest / monitor / frontend default / Agent / broker 扩权。

允许进入下一步：

```text
PE1: Qlib-only Simulation-in-the-loop Policy Search
```

本审查不授权：

```text
PE2 strict_test
PE3 robustness audit
PE4 deep / RL policy research
PE5 qlib + orthogonal LTR adapter
production/default integration
```

## 2. 审查依据

已审查：

```text
docs/tw_portfolio_decision_model/POLICY_PE_EPISODIC_PORTFOLIO_POLICY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PE0_EPISODIC_POLICY_CONTRACT_DESIGN_EXECUTION_REPORT_CN.md
.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md
.agents/skills/tw-stock-safety-boundary-review/SKILL.md
.agents/skills/tw-stock-safety-boundary-review/references/forbidden-actions.md
```

同时按主线要求对照：

```text
PAV2 closure
ModelSignal / StrategyRule / OrderIntent / ReplayResult 合同边界
PE 主线 R1-R9 research adoption 要求
readonly / simulation-only / not-order 安全边界
```

## 3. Findings

### Critical

无。

### High

无。

### Medium

M1. PE1 必须显式禁止运行 strict_test。

PE0 报告中写明 `strict_test 只 final-only`，这与主线总体原则一致；但 PE1 阶段的具体执行规则是：

```text
strict_test 不运行或只在 reviewer 授权的 PE2 执行
```

因此 PE1 执行者不得在本阶段生成 2026-01-01..2026-05-07 的 policy replay、baseline replay、selection audit 或任何 strict_test 指标。PE1 report 可以保留 strict_test window 字段作为合同声明，但 `strict_test_used_for_selection=false`，且不得实际使用 strict_test 数据。

M2. Family D 不应在首轮 PE1 执行中使用，除非另有 PIT-safe 证明并经审查。

主线明确：

```text
Family D 只有在 PE0 证明 regime feature PIT-safe 后才能执行。
```

PE0 报告把 Family D 标为 `only after PIT-safe proof`，但未给出具体 regime feature 清单、available_at 规则、计算窗口、泄漏负例和 validator 证据。因此本轮 PE1 工作文档不授权执行 Family D。PE1 首轮应聚焦 Family A / B / C；Family D 保持 deferred。

M3. PE1 的随机搜索 / CEM 必须有过拟合控制证据。

PE0 允许 deterministic grid / random search / CEM，但 validation 只能作为外层 final selection。PE1 执行报告必须记录：

```text
candidate_count
search_method
random_seed, if any
train pruning rule
validation evaluation count
final selection source
```

若 CEM 或 random search 反复根据 validation 修改搜索空间，应判定为 validation overfit 风险，不能直接进入 PE2。

### Low

L1. PE0 未生成实际 artifact 文件是可接受的。

PE0 是设计冻结阶段，主线未要求实际产出 `manifest.json`、validator 程序或 golden sample 文件。实际 artifact 生成应放在 PE1。

## 4. 主线符合性核查

| 核查项 | 结论 | 说明 |
|---|---|---|
| 是否完整覆盖 PE0 范围 | PASS | 只做 schema、validator、golden sample、PE1 protocol 设计 |
| 是否读取主线/PAV2 closure/合同/技能 | PASS | 报告列出主线、PAV2 closure、项目合同与相关 skill |
| Research Adoption Audit | PASS | R1-R9 均包含 adopted / rejected / deferred / risk / PE_mapping |
| Artifact schema | PASS | 三类 artifact 均给出必需字段和 forbidden fields |
| Validator / golden sample 设计 | PASS | 覆盖正例、负例、strict_test selection、future return、target_weight、quantity、broker 等 |
| train / validation / strict_test 分离 | PASS_WITH_CONDITION | PE1 文档必须明确本阶段不运行 strict_test |
| readonly / simulation-only 边界 | PASS | 未见 provider/latest/monitor/frontend/Agent/broker 扩权 |
| return-first 与参与度约束 | PASS | 明确 validation return-first 与 participation/action_count guardrail |
| 是否擅自合并/拆分主线阶段 | PASS | 未越过 PE0；下一步只能 PE1 |

## 5. Forbidden Actions Audit

本轮 PE0 报告未发现以下越界行为：

```text
provider refresh / publish
accepted latest switch
monitor config / scan / alerts write
frontend default switch
Agent / OpenAI integration
broker / quick-trade / order submission
target_position / target_weight / quantity output
strict_test replay
model training
policy parameter search
收益承诺 / 胜率承诺 / 上涨概率承诺
```

PE1 仍必须继续保持：

```text
readonly_only=true
simulation_only=true
production_allowed=false
not_order=true
not_target_position=true
not_target_weight=true
```

## 6. PE1 工作文档

### 6.1 阶段名称

```text
PE1_QLIB_ONLY_SIMULATION_IN_THE_LOOP_POLICY_SEARCH
```

### 6.2 阶段目标

严格按主线执行：

```text
用 qlib-only signal，在 train/validation 上搜索参数化 episode policy。
```

本阶段只回答：

```text
在 frozen qlib-only signal 不增强、不重训的前提下，
Family A/B/C 的 episode-level portfolio policy search
能否在 validation 上 after-fee-tax return 不低于 baseline，
且不靠低参与/no_action 获得表面改善。
```

### 6.3 必须读取

执行者开始 PE1 前必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_PE_EPISODIC_PORTFOLIO_POLICY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PE0_EPISODIC_POLICY_CONTRACT_DESIGN_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PE0_EPISODIC_POLICY_CONTRACT_DESIGN_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_PAV2_ACTION_VALUE_RANKER_REPAIR_REVIEW_AND_ROUTE_CLOSURE_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md
.agents/skills/tw-stock-safety-boundary-review/SKILL.md
```

### 6.4 输入与数据切分

唯一允许的 base signal：

```text
data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json
```

固定窗口：

```text
policy_train_window      = 2023-01-01..2024-12-31
policy_validation_window = 2025-01-01..2025-12-31
policy_strict_test_window = 2026-01-01..2026-05-07
```

PE1 使用规则：

```text
train: 用于参数候选生成、内部 pruning、train replay metrics。
validation: 用于最终 policy/config selection。
strict_test: 本阶段不得运行，不得读取，不得评估，不得选择。
```

### 6.5 允许执行的 policy families

本轮 PE1 首轮允许：

```text
Family A: aggressive rank-capture policy
Family B: switch-pair return capture policy
Family C: baseline-plus offensive override
```

建议优先级：

```text
1. Family C: baseline-plus offensive override
2. Family A: aggressive rank-capture policy
3. Family B: switch-pair return capture policy
```

理由：主线已指出 baseline 的收益来自持续参与和持续换仓，PE1 首轮应优先验证“保留 baseline 参与能力 + 有约束的进攻性覆盖”是否能产生增量，而不是先构造容易退化为 skip/no_action 的替代策略。

本轮不授权：

```text
Family D: regime-conditioned offensive policy
```

除非另行形成 PIT-safe regime feature proof 并经过审查，否则不得使用 Family D。

### 6.6 允许的 search methods

允许：

```text
deterministic grid
random search
cross-entropy method
```

要求：

```text
1. 所有候选参数必须写入 policy_config_candidates.csv。
2. random search / CEM 必须记录 random_seed。
3. CEM 只能用 train replay 做采样分布更新或 pruning。
4. validation 只能作为外层 final selection。
5. 不得根据 validation 结果反复修改参数空间再重跑，除非报告中明确标为 PE1 失败后的 coordinator repair 候选，而不是本轮通过证据。
```

### 6.7 允许输出的 action slate

允许 intent-level action slate：

```text
no_action
keep_baseline_action
sell_k_weak_holdings
buy_k_top_candidates
switch_pairs: sell_i weak holding + buy_j strong candidate
```

OrderIntentArtifact 只能包含 intent：

```text
side = buy/sell/skip
instrument
reason_code
source_policy
```

禁止字段：

```text
quantity
target_position
target_weight
execution_price
execution_date
broker_order_id
cash amount
realized_pnl
future_return
```

### 6.8 必须产出 artifact

artifact 根目录：

```text
data_tw/experiments/policy_episode_research/pe1_qlib_only_policy_search/
```

必须产出：

```text
manifest.json
policy_config_candidates.csv
train_replay_metrics.csv
validation_replay_metrics.csv
validation_selection_audit.csv
participation_audit.csv
forbidden_feature_audit.csv
validator_report.json
golden_samples_report.json
```

建议同时产出：

```text
selected_policy_config.json
selected_policy_trajectory_decisions_train.csv
selected_policy_trajectory_decisions_validation.csv
selected_order_intents_train.jsonl
selected_order_intents_validation.jsonl
train_policy_episode_evaluation.json
validation_policy_episode_evaluation.json
baseline_train_episode_evaluation.json
baseline_validation_episode_evaluation.json
```

注意：不得产出 strict_test replay artifact。

### 6.9 必须通过的 validator / audit

PE1 validator 至少检查：

```text
EpisodicPolicyConfigArtifact schema 完整
PolicyTrajectoryDecisionArtifact schema 完整
PolicyEpisodeEvaluationArtifact schema 完整
forbidden fields 不存在
forbidden actions 不存在
strict_test_used_for_selection=false
train / validation / strict_test 分离
policy_family / policy_parameters / search_method 明确
OrderIntentArtifact 不含 quantity / target_weight / target_position / execution_price / broker 字段
ReplayResultArtifact 是 readonly historical simulation 输出
```

PE1 golden samples 至少覆盖：

```text
positive_config_minimal
positive_trajectory_daily_slate
positive_episode_evaluation
positive_order_intent_buy_sell_skip
positive_readonly_replay_summary
negative_future_return_in_state
negative_target_weight_in_decision
negative_quantity_in_order_intent
negative_execution_price_in_decision
negative_broker_order_in_decision
negative_strict_test_selection
negative_replay_return_as_input
```

### 6.10 PE1 通过条件

全部满足才可建议进入 PE2：

```text
validation policy net_return_after_fee_tax >= validation baseline
validation excess_return >= 0
participation_ratio >= 0.85 of baseline on validation
action_count_ratio >= 0.80 of baseline on validation
policy 不得靠 no_action / 低参与获得表面收益
turnover_ratio <= 2.00 of baseline unless validation excess is clearly positive
max_drawdown must not be catastrophically worse than baseline
validator_report pass
golden_samples_report pass
forbidden_feature_audit pass
strict_test_used_for_selection=false
```

审查者将不接受以下替代通过理由：

```text
低换手优于 baseline
低费用优于 baseline
低回撤优于 baseline
no_action 更多所以亏得少
train 表现好但 validation 低于 baseline
validation 指标略好但参与度塌缩
```

### 6.11 PE1 失败与停止条件

出现任一情况，PE1 不得进入 PE2：

```text
validation policy net_return_after_fee_tax < validation baseline
validation excess_return < 0
participation_ratio < 0.85
action_count_ratio < 0.80
收益来自大规模 no_action / low participation
validator/golden samples 未通过
读取 future_return / label / realized_pnl / future price 作为 feature
使用 strict_test 做选择或评估
输出 target_weight / target_position / quantity / broker order
试图接 provider/latest/monitor/frontend default/Agent/broker
执行 PPO/CQL/IQL/Decision Transformer
```

失败时执行报告 recommendation 只能是：

```text
FAIL_NEEDS_PE1_REPAIR
STOP_OR_REPAIR_WITH_COORDINATOR_DECISION
```

不得自动进入 PE2。

### 6.12 PE1 执行报告路径

执行者必须输出：

```text
docs/tw_portfolio_decision_model/POLICY_PE1_QLIB_ONLY_POLICY_SEARCH_EXECUTION_REPORT_CN.md
```

报告必须包含：

```text
1. Scope 与非目标确认
2. Documents / Contracts / Skills Read
3. Input signal artifact 与数据窗口
4. Policy families 与参数空间
5. Search method、candidate_count、seed、train pruning 规则
6. Baseline train/validation metrics
7. Policy train/validation metrics
8. Validation selection audit
9. Participation / action_count / no_action / turnover audit
10. Forbidden feature / forbidden action audit
11. Validator 与 golden sample 结果
12. Files changed / artifacts produced
13. Recommendation
```

允许的 recommendation：

```text
PASS_READY_FOR_PE2_STRICT_TEST_FINAL_REPLAY
FAIL_NEEDS_PE1_REPAIR
STOP_OR_REPAIR_WITH_COORDINATOR_DECISION
```

只有在 PE1 全部通过条件满足时，才能推荐：

```text
PASS_READY_FOR_PE2_STRICT_TEST_FINAL_REPLAY
```

## 7. 给执行者的 PE1 命令

```text
你是执行者。请严格执行 Policy Episode / Trajectory Portfolio Policy 主线的 PE1：
PE1_QLIB_ONLY_SIMULATION_IN_THE_LOOP_POLICY_SEARCH。

必须读取：
1. docs/tw_portfolio_decision_model/POLICY_PE_EPISODIC_PORTFOLIO_POLICY_MAINLINE_CN.md
2. docs/tw_portfolio_decision_model/POLICY_PE0_EPISODIC_POLICY_CONTRACT_DESIGN_REVIEW_CN.md
3. docs/tw_portfolio_decision_model/POLICY_PE0_EPISODIC_POLICY_CONTRACT_DESIGN_EXECUTION_REPORT_CN.md
4. docs/tw_portfolio_decision_model/POLICY_PAV2_ACTION_VALUE_RANKER_REPAIR_REVIEW_AND_ROUTE_CLOSURE_CN.md
5. docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
6. docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
7. docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
8. docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
9. docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
10. .agents/skills/coordinator-executor-reviewer-workflow/SKILL.md
11. .agents/skills/tw-stock-safety-boundary-review/SKILL.md

本轮只允许：
- 使用 frozen qlib-only signal；
- 在 train=2023-01-01..2024-12-31 上生成和初筛 policy config；
- 在 validation=2025-01-01..2025-12-31 上做 final config selection；
- 执行 Family A / B / C 的可解释、参数化、离散 intent policy search；
- 产出 PE1 artifact、validator_report、golden_samples_report 和 execution report。

本轮禁止：
- 运行 strict_test；
- 读取 strict_test 指标；
- 用 strict_test 选择参数；
- 执行 Family D，除非另有 PIT-safe proof 并经审查；
- 训练 qlib/LTR 或任何新模型；
- 执行 PPO/CQL/IQL/Decision Transformer；
- 输出 target_position / target_weight / quantity / broker order；
- 接 provider latest / accepted latest / monitor / frontend default / Agent / broker；
- 用低换手、低费用、低回撤替代 validation return-first 通过。

artifact 根目录：
data_tw/experiments/policy_episode_research/pe1_qlib_only_policy_search/

执行报告路径：
docs/tw_portfolio_decision_model/POLICY_PE1_QLIB_ONLY_POLICY_SEARCH_EXECUTION_REPORT_CN.md

若 validation 未超过 baseline 或参与度/action_count guardrail 未通过，必须报告 FAIL_NEEDS_PE1_REPAIR 或 STOP_OR_REPAIR_WITH_COORDINATOR_DECISION，不得进入 PE2。
```

## 8. 最终审查意见

PE0 可以通过。下一步只能执行 PE1，不得擅自合并 PE2 strict_test、PE3 robustness、PE4 deep/RL 或 PE5 LTR adapter。

PE1 的核心审查门槛是：

```text
validation return-first
participation/action_count 防退化
strict_test zero-use
readonly simulation-only
intent-only no-order
```
