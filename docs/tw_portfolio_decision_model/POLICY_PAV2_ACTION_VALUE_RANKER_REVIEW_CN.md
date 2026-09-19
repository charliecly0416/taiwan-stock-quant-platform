---
created_at: 2026-06-21
status: reviewed_fail_needs_pav2_repair
phase: PAV2_ACTION_VALUE_RANKER
reviewed_report: docs/tw_portfolio_decision_model/POLICY_PAV2_ACTION_VALUE_RANKER_EXECUTION_REPORT_CN.md
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PA3_COUNTERFACTUAL_ACTION_SPACE_MAINLINE_CN.md
previous_review: docs/tw_portfolio_decision_model/POLICY_PAV1_COUNTERFACTUAL_ACTION_DATASET_BUILD_REVIEW_CN.md
artifact_root: data_tw/experiments/policy_action_model_research/pav2_action_value_ranker
review_decision: FAIL_NEEDS_PAV2_REPAIR
next_phase: PAV2_ACTION_VALUE_RANKER_REPAIR
next_work_output: docs/tw_portfolio_decision_model/POLICY_PAV2_ACTION_VALUE_RANKER_REPAIR_EXECUTION_REPORT_CN.md
readonly_only: true
simulation_only: true
not_order: true
not_target_position: true
not_investment_advice: true
production_allowed: false
no_pav3: true
no_offline_rl: true
---

# PAV2 Action Value Ranker 审查报告与 Repair 工作文档

## 1. 审查结论

审查结论：

```text
FAIL_NEEDS_PAV2_REPAIR
```

执行者提交的 `docs/tw_portfolio_decision_model/POLICY_PAV2_ACTION_VALUE_RANKER_EXECUTION_REPORT_CN.md` 在合同产物和只读安全边界上基本合格：已输出 ActionValueModelArtifact、ActionSlateDecisionArtifact、OrderIntentArtifact、readonly ReplayResultArtifact、evaluation、validator 和 golden samples；未发现 provider/latest/monitor/broker/frontend/Agent/OpenAI 扩权。

但 PAV2 的核心 return-first 门槛未通过：

```text
strict_test baseline net_return_after_fee_tax = 1.14173800
strict_test policy   net_return_after_fee_tax = 0.46828264
strict_test excess   net_return_after_fee_tax = -0.67345536
```

该结果显著低于 baseline，不满足进入 PAV3 的条件。下一步只能在 PAV2 内做 repair，不得进入：

```text
PAV3_CONSTRAINED_SLATE_POLICY
PAV4_OFFLINE_RL
```

本审查不拆分、不合并、不改名主线阶段；`PAV2_ACTION_VALUE_RANKER_REPAIR` 是 PAV2 内部修复，不是新主线阶段。

## 2. Evidence Checked

| evidence | purpose |
|---|---|
| `docs/tw_portfolio_decision_model/POLICY_PA3_COUNTERFACTUAL_ACTION_SPACE_MAINLINE_CN.md` | PAV2 通过门槛、PAV3 前置条件、停止条件 |
| `docs/tw_portfolio_decision_model/POLICY_PAV1_COUNTERFACTUAL_ACTION_DATASET_BUILD_REVIEW_CN.md` | PAV2 工作要求 |
| `docs/tw_portfolio_decision_model/POLICY_PAV2_ACTION_VALUE_RANKER_EXECUTION_REPORT_CN.md` | PAV2 执行报告 |
| `data_tw/experiments/policy_action_model_research/pav2_action_value_ranker/manifest.json` | ActionValueModelArtifact manifest |
| `data_tw/experiments/policy_action_model_research/pav2_action_value_ranker/validation_selection_audit.csv` | validation-only selection |
| `data_tw/experiments/policy_action_model_research/pav2_action_value_ranker/evaluation/baseline_comparison.csv` | return-first 对比 |
| `data_tw/experiments/policy_action_model_research/pav2_action_value_ranker/evaluation/return_first_metrics.csv` | replay 指标、参与度和 skip 证据 |
| `data_tw/experiments/policy_action_model_research/pav2_action_value_ranker/evaluation/action_type_counts.csv` | selected action type 分布 |
| `data_tw/experiments/policy_action_model_research/pav2_action_value_ranker/evaluation/strict_test_selected_nonzero_action_explanation.csv` | strict_test 逐笔解释 |
| `data_tw/experiments/policy_action_model_research/pav2_action_value_ranker/evaluation/coverage_ood_selected_action_audit.csv` | selected action 是否来自 PAV1 materialized dataset |
| `data_tw/experiments/policy_action_model_research/pav2_action_value_ranker/forbidden_output_audit.csv` | ActionSlateDecision forbidden output |
| `data_tw/experiments/policy_action_model_research/pav2_action_value_ranker/order_intents/policy/strict_test/order_intents.csv` | OrderIntent 只读字段抽查 |
| `data_tw/experiments/policy_action_model_research/pav2_action_value_ranker/replay_result/policy/strict_test/summary.csv` | policy strict_test replay summary |
| `data_tw/experiments/policy_action_model_research/pav2_action_value_ranker/validator_report.json` | PAV2 validator |
| `data_tw/experiments/policy_action_model_research/pav2_action_value_ranker/golden_samples_report.json` | PAV2 golden samples |

使用的项目技能与边界：

```text
coordinator-executor-reviewer-workflow
tw-stock-new-model-onboarding
tw-stock-new-strategy-onboarding
tw-stock-safety-boundary-review
```

## 3. Findings

### Critical

无。未发现真实交易、broker、quick-trade、provider/latest、monitor、frontend default 或 Agent/OpenAI 扩权。

### High

#### H1. strict_test return-first 明显失败，不能进入 PAV3

`baseline_comparison.csv`：

| split | baseline_return | policy_return | excess | baseline_action_count | policy_action_count |
|---|---:|---:|---:|---:|---:|
| train | 2.41885797 | 2.95068940 | 0.53183143 | 885 | 30 |
| validation | 0.95376753 | 0.92867510 | -0.02509243 | 436 | 26 |
| strict_test | 1.14173800 | 0.46828264 | -0.67345536 | 125 | 12 |

主线 PAV2 通过门槛要求 strict_test 超过或接近 baseline；当前 strict_test 大幅落后，不具备进入 PAV3 的稳定 positive evidence。

#### H2. validation selection 目标与 replay return 不一致，label alpha 未迁移

`validation_selection_audit.csv` 显示 final selection 是：

```text
candidate_topk=50
action_cap=200
model_family=hist_gradient_boosting
target_label=label_relative_return_vs_baseline
validation_selected_label_relative_return_mean=0.0589324879
validation_selected_label_relative_return_sum=14.2616620675
```

但 readonly replay：

```text
validation excess = -0.02509243
strict_test excess = -0.67345536
```

这说明 counterfactual label ranking 在 portfolio execution/replay 层面没有迁移。继续 PAV2 repair 必须把 selection 指标从纯 selected-label advantage 改为 validation replay-aware / execution-feasibility-aware gate，但仍不得使用 strict_test selection。

#### H3. policy 参与度严重不足，主要失败机制是 execution-feasibility / portfolio-state 脱节

`return_first_metrics.csv`：

| split | baseline_action_count | policy_action_count | policy_skip_count | baseline_turnover | policy_turnover |
|---|---:|---:|---:|---:|---:|
| train | 885 | 30 | 567 | 87.37059302 | 4.28531113 |
| validation | 436 | 26 | 266 | 42.18778217 | 2.21300434 |
| strict_test | 125 | 12 | 87 | 12.48286853 | 1.14286243 |

strict_test 选中 79 天动作，但 replay 只形成 12 笔实际成交。当前 top-action ranker 在 rolling portfolio state 下经常不可执行或不能维持 baseline 参与度，这是 PAV2 repair 的首要目标。

### Medium

#### M1. selected action type 偏向 buy_one，缺少持仓完整性约束

strict_test selected action type：

```text
buy_one = 58
switch_pair = 14
keep_baseline_action = 7
sell_one = 0
no_action = 0
```

但实际成交只有 12 笔。大量 `buy_one` 在满仓或状态不匹配时容易被 adapter/replay 跳过。PAV2 repair 应加入 validation-only execution-feasibility guardrail，例如满仓时优先 `switch_pair` / `keep_baseline_action`，未满仓时才允许 `buy_one`；不得直接进入 PAV3 slate。

#### M2. strict_test selected nonzero actions 中存在多笔负 label advantage

`strict_test_selected_nonzero_action_explanation.csv` 抽查显示多笔 selected action 的 `label_relative_return_vs_baseline` 为负，例如：

```text
2026-01-02 switch_pair label_relative_return_vs_baseline=-0.0794018595
2026-01-14 switch_pair label_relative_return_vs_baseline=-0.2334838794
2026-02-10 buy_one label_relative_return_vs_baseline=-0.8238626226
2026-03-06 switch_pair label_relative_return_vs_baseline=-0.4516747487
```

PAV2 repair 应增加 validation-only margin / keep-baseline fallback，避免低置信度或负预期动作替代 baseline。

#### M3. coverage/OOD 通过，但不能解释收益失败

`coverage_ood_selected_action_audit.csv` 显示 selected actions 均来自 materialized PAV1 config，OOD 不是本轮失败主因。因此 repair 不应回到 PAV1 扩大 action space，也不应新增 PAV1 topK/cap config；应在 PAV2 selection、guardrail、adapter feasibility 上修。

### Low

#### L1. ReplayResult 中的 quantity/execution_price/cash/NAV 是 replay 合同输出，不是 ActionSlateDecision/OrderIntent 越界

PAV2 报告对此说明清楚。审查抽查 ActionSlateDecision 和 OrderIntent 未发现 forbidden output 字段；ReplayResult 作为历史模拟输出可包含成交和净值字段。

## 4. Mainline Compliance

PAV2 合规点：

```text
1. 使用 PAV1 dataset manifest。
2. 未新增 PAV1 topK/cap config。
3. 只使用 schema 允许的 state_feature_* / action_feature_* / action_type。
4. 输出 ActionValueModelArtifact。
5. 输出 ActionSlateDecisionArtifact。
6. 输出 OrderIntentArtifact。
7. 输出 readonly ReplayResultArtifact。
8. validator_report failed_count=0。
9. golden_samples_report failed_count=0。
10. 未进入 PAV3/PAV4/offline RL。
```

PAV2 不合格点：

```text
1. strict_test return-first 显著低于 baseline。
2. validation label advantage 未迁移到 validation/strict_test replay return。
3. policy participation 过低，skip_count 过高。
4. selected top action 与 rolling portfolio execution feasibility 脱节。
```

因此结论不是 `PASS_READY_FOR_PAV3_CONSTRAINED_SLATE_POLICY`，而是：

```text
FAIL_NEEDS_PAV2_REPAIR
```

## 5. Missing Evidence Or Open Questions

PAV2 repair 需要补充以下证据：

```text
1. validation replay-aware selection audit。
2. execution-feasibility audit：selected action 是否可在当日 rolling portfolio state 执行。
3. participation guardrail audit：policy action_count / baseline_action_count、skip_ratio、turnover_ratio。
4. keep_baseline fallback audit：低置信度、不可执行、负 margin 时是否回退 baseline。
5. strict_test final-only audit：repair 后仍证明 strict_test 未参与选择。
6. repair 前后 baseline_comparison.csv。
```

## 6. Forbidden Actions Audit

审查未发现以下越界行为：

```text
provider publish / accepted latest switch
monitor write / scan / alerts
broker / quick-trade / real order
frontend default recommendation
Agent / OpenAI call
target_position / target_weight in ActionSlateDecision or OrderIntent
quantity / execution_price / broker_order in ActionSlateDecision or OrderIntent
offline RL / online RL / CQL / IQL / BCQ
retrain qlib / LTR
repair 2023-2025 LTR artifact
read qlib/LTR private CSV as strategy input
strict_test used for selection
```

`OrderIntentArtifact` 抽查字段为 intent-only；`ReplayResultArtifact` 中的 execution/cash/NAV 字段属于 readonly historical replay 输出，不构成真实交易行为。

## 7. PAV2 Repair 工作文档

### 7.1 阶段名称

下一步必须严格限定为：

```text
PAV2_ACTION_VALUE_RANKER_REPAIR
```

这是 PAV2 内部修复，不是新主线阶段。不得改为 PAV3，不得合并 PAV3，不得进入 PAV4/offline RL。

### 7.2 Repair 目标

本轮只修复 PAV2 的执行可行性与参与度问题：

```text
1. 保留 PAV1 dataset 和 PAV2 action value ranker 路线。
2. 不新增 PAV1 topK/cap config。
3. 在 validation-only selection 中加入 execution-feasibility / participation guardrail。
4. 加入 keep_baseline fallback，避免不可执行或低置信度动作导致 skip。
5. 使用 validation replay-aware return-first gate 选择最终 policy。
6. strict_test 仍只能 final-only。
```

### 7.3 必读文件

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_PA3_COUNTERFACTUAL_ACTION_SPACE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PAV1_COUNTERFACTUAL_ACTION_DATASET_BUILD_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PAV2_ACTION_VALUE_RANKER_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_PAV2_ACTION_VALUE_RANKER_REVIEW_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
.agents/skills/tw-stock-new-model-onboarding/SKILL.md
.agents/skills/tw-stock-new-strategy-onboarding/SKILL.md
.agents/skills/tw-stock-safety-boundary-review/SKILL.md
.agents/skills/tw-stock-safety-boundary-review/references/forbidden-actions.md
```

### 7.4 允许修改范围

允许在 PAV2 内修改：

```text
scripts/run_tw_policy_pav2_action_value_ranker.py
data_tw/experiments/policy_action_model_research/pav2_action_value_ranker_repair/
docs/tw_portfolio_decision_model/POLICY_PAV2_ACTION_VALUE_RANKER_REPAIR_EXECUTION_REPORT_CN.md
```

输出目录建议使用新目录，避免覆盖首轮失败证据：

```text
data_tw/experiments/policy_action_model_research/pav2_action_value_ranker_repair/
```

不得修改 PAV1 dataset，不得重写历史 PAV2 失败目录。

### 7.5 必须实现的 repair controls

#### 7.5.1 Execution-feasibility filter

在 selected action 转 OrderIntent 前，必须基于 rolling policy portfolio state 判断：

```text
buy_one: only executable when portfolio has capacity and instrument not already held
sell_one: only executable when instrument_sell is currently held
switch_pair: executable only when instrument_sell currently held and instrument_buy not held
keep_baseline_action: executable if baseline intent exists and passes same readonly checks
no_action: always executable
```

不可执行动作必须：

```text
fallback to keep_baseline_action if available
else fallback to no_action
```

必须输出：

```text
evaluation/execution_feasibility_audit.csv
```

字段至少包含：

```text
signal_date
split
selected_action_id_before_guardrail
selected_action_id_after_guardrail
action_type_before
action_type_after
feasible_before
fallback_reason
portfolio_holding_count
instrument_buy_currently_held
instrument_sell_currently_held
baseline_available
status
```

#### 7.5.2 Participation guardrail

必须在 validation 上选择参与度约束：

```text
policy_action_count / baseline_action_count
policy_turnover_proxy / baseline_turnover_proxy
skip_count / selected_day_count
```

建议 validation gate：

```text
participation_ratio >= 0.80
skip_ratio <= 0.25
turnover_ratio >= 0.50
```

执行者可在 validation 上调整阈值，但必须说明理由；strict_test 不得参与阈值选择。

必须输出：

```text
evaluation/participation_guardrail_audit.csv
```

#### 7.5.3 Keep-baseline fallback / margin gate

必须增加 validation-only margin gate：

```text
if top policy_score is below validation-selected margin
or predicted advantage <= validation-selected threshold
or action infeasible
then select keep_baseline_action if present
else no_action
```

目标是避免低置信度动作强行替换 baseline，并保持参与度。

必须输出：

```text
evaluation/keep_baseline_fallback_audit.csv
```

#### 7.5.4 Validation replay-aware selection

repair 后 selection 不能只看 label advantage。必须用 validation readonly replay 的 return-first 指标选择最终 policy：

```text
primary: validation net_return_after_fee_tax / excess_vs_baseline
secondary: participation_ratio
tertiary: selected label advantage
diagnostic: rank IC / AUC / feature importance
```

必须输出：

```text
validation_selection_audit.csv
evaluation/validation_replay_selection_audit.csv
```

### 7.6 必须保留的 PAV2 边界

Repair 仍然必须：

```text
1. 只使用 PAV1 materialized configs: (50,200), (100,500), (150,1000)。
2. 只使用 PAV1 schema allow-list inference features。
3. 不使用 label_* / future_* / replay_return / realized_pnl 作为 model inference feature。
4. 不使用 strict_test 做模型、阈值、topK/cap、margin、fallback policy selection。
5. 输出 ActionValueModelArtifact、ActionSlateDecisionArtifact、OrderIntentArtifact、ReplayResultArtifact。
6. 输出 validator_report 和 golden_samples_report。
```

### 7.7 Repair 通过条件

PAV2 repair 通过必须满足：

```text
1. validation replay return-first 不低于 baseline，或有明确可接受 tradeoff。
2. strict_test net_return_after_fee_tax >= baseline，preferred。
3. 若 strict_test 未超过 baseline，必须至少 not materially below baseline，并有清楚的 coordinator-approved tradeoff；否则不得进入 PAV3。
4. participation_ratio、skip_ratio、turnover_ratio 不再显示低参与失败。
5. selected actions 不主要来自 infeasible/OOD/low-support actions。
6. no forbidden output fields。
7. strict_test_final_only audit pass。
```

若 repair 后 strict_test 仍明显低于 baseline，或 validation alpha 仍不迁移，应给出：

```text
STOP_DO_NOT_CONTINUE
```

或请求统筹决定是否终止 counterfactual action value route。不得继续无界调参。

### 7.8 Repair 禁止事项

PAV2 repair 不授权：

```text
PAV3 constrained slate policy
PAV4 offline RL
online RL
CQL / IQL / BCQ / Decision Transformer
新增 PAV1 dataset config
重训 qlib / LTR
修 2023-2025 LTR artifact
读取 qlib/LTR private CSV 作为策略输入
把 portfolio_decision_optimizer_v1 动作当标签
用 future/replay/realized pnl 作为 inference feature
用 strict_test 做 selection
输出 target_position / target_weight / quantity / cash allocation / broker order in ActionSlateDecision or OrderIntent
provider publish / accepted latest switch
monitor write / scan / alerts
broker / quick-trade / real order
frontend default recommendation
Agent / OpenAI 调用
```

### 7.9 Repair 执行报告格式

执行者输出：

```text
docs/tw_portfolio_decision_model/POLICY_PAV2_ACTION_VALUE_RANKER_REPAIR_EXECUTION_REPORT_CN.md
```

建议结构：

```markdown
# PAV2 Action Value Ranker Repair 执行报告

## 1. Scope
## 2. Documents / Contracts / Skills Read
## 3. Failure Root Cause From Initial PAV2
## 4. Repair Controls Implemented
## 5. Validation-only Selection And Guardrails
## 6. ActionValueModelArtifact
## 7. ActionSlateDecisionArtifact
## 8. Execution-feasibility / Participation / Keep-baseline Audits
## 9. OrderIntentArtifact
## 10. Readonly ReplayResultArtifact
## 11. Return-first Evaluation
## 12. Strict Test Final-only Audit
## 13. Validator And Golden Samples
## 14. Forbidden Actions Audit
## 15. Issues / Stop Conditions
## 16. Files Changed
## 17. Recommendation For Reviewer
```

推荐结论只能使用：

```text
PASS_READY_FOR_PAV3_CONSTRAINED_SLATE_POLICY
FAIL_NEEDS_PAV2_REPAIR
STOP_DO_NOT_CONTINUE
```

## 8. Command For Executor

```text
你是执行者。请执行 PAV2_ACTION_VALUE_RANKER_REPAIR。

必须读取：
- docs/tw_portfolio_decision_model/POLICY_PA3_COUNTERFACTUAL_ACTION_SPACE_MAINLINE_CN.md
- docs/tw_portfolio_decision_model/POLICY_PAV2_ACTION_VALUE_RANKER_EXECUTION_REPORT_CN.md
- docs/tw_portfolio_decision_model/POLICY_PAV2_ACTION_VALUE_RANKER_REVIEW_CN.md
- docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
- docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
- docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
- docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
- docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
- docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
- .agents/skills/tw-stock-new-model-onboarding/SKILL.md
- .agents/skills/tw-stock-new-strategy-onboarding/SKILL.md
- .agents/skills/tw-stock-safety-boundary-review/SKILL.md

本轮只在 PAV2 内 repair，不进入 PAV3/PAV4。

修复重点：
1. execution-feasibility filter。
2. participation guardrail。
3. keep_baseline fallback / margin gate。
4. validation replay-aware return-first selection。
5. strict_test final-only。

不得新增 PAV1 config，不得重训 qlib/LTR，不得 offline RL，不得 provider/latest/monitor/broker/frontend default/Agent/OpenAI，不得在 ActionSlateDecision 或 OrderIntent 输出 target_weight/target_position/quantity/order。

输出：
docs/tw_portfolio_decision_model/POLICY_PAV2_ACTION_VALUE_RANKER_REPAIR_EXECUTION_REPORT_CN.md
```
