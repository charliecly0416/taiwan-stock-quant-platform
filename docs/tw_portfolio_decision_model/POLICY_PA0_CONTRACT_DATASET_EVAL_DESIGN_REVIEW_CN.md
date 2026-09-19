---
created_at: 2026-06-21
status: reviewed_pass_ready_for_pa1_supervised_utility_dataset
phase: POLICY_PA0_CONTRACT_DATASET_EVAL_DESIGN
reviewed_report: docs/tw_portfolio_decision_model/POLICY_PA0_CONTRACT_DATASET_EVAL_DESIGN_EXECUTION_REPORT_CN.md
mainline_doc: docs/tw_portfolio_decision_model/PHASE_POLICY_ACTION_MODEL_RESEARCH_MAINLINE_CN.md
review_decision: PASS_READY_FOR_PA1_SUPERVISED_UTILITY_DATASET
next_work: POLICY_PA1_QLIB_ONLY_SUPERVISED_UTILITY
base_signal_first: frozen_qlib_2018_2022
signal_artifact: data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json
readonly_only: true
simulation_only: true
not_order: true
not_target_position: true
not_investment_advice: true
production_allowed: false
---

# Policy / Action Model Research PA0 审查意见与 PA1 工作文档

## 1. 审查结论

审查结论：

```text
PASS_READY_FOR_PA1_SUPERVISED_UTILITY_DATASET
```

执行者提交的 `docs/tw_portfolio_decision_model/POLICY_PA0_CONTRACT_DATASET_EVAL_DESIGN_EXECUTION_REPORT_CN.md` 符合 PA0 目标：本轮只完成合同、数据集、评估、validator、golden samples 和 Research Adoption Audit 的设计冻结，没有训练、没有 replay、没有调参、没有直接进入 contextual bandit / offline RL，也没有默认化、provider publish、accepted latest switch、monitor write、broker/order 或 target position/weight 输出。

允许按主线文档进入下一阶段：

```text
PA1: qlib-only supervised utility model
```

PA1 必须完整遵守主线文档定义的 PA1 范围和顺序约束：构造 policy dataset、训练简单 supervised utility model、只用 validation 选择阈值、strict_test 只做一次最终评估、输出 PolicyDecisionArtifact 与 readonly replay。审查者不得另行拆分、合并或改名主线阶段。

## 2. 审查依据

本次审查对照以下文件：

| 文件 | 审查用途 |
|---|---|
| `docs/tw_portfolio_decision_model/PHASE_POLICY_ACTION_MODEL_RESEARCH_MAINLINE_CN.md` | PA0 通过条件、PA1 入口、return-first、禁止项 |
| `docs/tw_portfolio_decision_model/POLICY_PA0_CONTRACT_DATASET_EVAL_DESIGN_EXECUTION_REPORT_CN.md` | 执行者 PA0 报告 |
| `docs/tw_portfolio_decision_model/PHASEP_BRANCH_B_CLOSURE_REVIEW_CN.md` | 旧 P 分支关闭边界、旧动作不得作为标签 |
| `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md` | 模块边界、只读与交易安全红线 |
| `docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md` | 新模型/策略必须先合同化、registry、validator、golden sample |
| `docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md` | frozen qlib 标准信号入口与 forbidden fields |
| `docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md` | `ext_*` 扩展规则 |
| `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md` | StrategyRule 输入/输出边界 |
| `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md` | OrderIntent 非订单、非成交、非仓位边界 |
| `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md` | ReplayResult 只读回放边界 |
| `docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md` | 新模型 reviewer 检查点 |
| `docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md` | 新策略 reviewer 检查点 |
| `.agents/skills/tw-stock-new-model-onboarding/SKILL.md` | 新模型接入边界 |
| `.agents/skills/tw-stock-new-strategy-onboarding/SKILL.md` | 新策略/OrderIntent/replay 边界 |
| `.agents/skills/tw-stock-safety-boundary-review/SKILL.md` | readonly 与 forbidden action 边界 |

## 3. PA0 符合性审查

### 3.1 范围符合

执行报告声明并保持：

```text
training_executed=false
replay_executed=false
rl_executed=false
readonly_only=true
simulation_only=true
production_allowed=false
```

审查判断：通过。

本轮只新增 PA0 设计文档，没有脚本、artifact、模型训练、readonly replay 或产品链路变更。符合主线对 PA0 的要求。

### 3.2 固定 qlib-only source signal

执行报告固定第一阶段输入为：

```text
data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json
model_family = qlib
policy_research_window = 2023-01-03 到 2026-05-07
```

审查判断：通过。

该选择符合主线的 qlib-only first 原则，避免 2023-2025 LTR training-window strict OOS 争议。

### 3.3 Policy train / validation / strict_test 切分

执行报告采用：

| split | start | end |
|---|---|---|
| train | 2023-01-03 | 2024-12-31 |
| validation | 2025-01-01 | 2025-12-31 |
| strict_test | 2026-01-01 | 2026-05-07 |

并声明 strict_test 不得用于调整 reward、threshold、action space、feature set、holding horizon 或 baseline consumer。

审查判断：通过。

PA1 报告必须继续明确区分：

```text
strict_test
validation
engineering_diagnostic
training_window_result
```

### 3.4 Artifact 设计

执行报告设计了：

```text
PolicyTrainingDatasetArtifact
PolicyDecisionArtifact
PolicyEvaluationArtifact
```

并为三类 artifact 定义了 manifest、schema、required files、forbidden audit 与 output 字段边界。

审查判断：通过。

关键点符合主线：

```text
ModelSignalArtifact
  -> PolicyTrainingDatasetArtifact
  -> PolicyDecisionArtifact
  -> StrategyRule adapter
  -> OrderIntentArtifact
  -> ReplayResultArtifact
```

`PolicyDecisionArtifact` 被限定为 diagnostic / readonly filter signal，没有直接写 OrderIntent 或 ReplayResult，也没有输出成交、仓位、数量、现金、broker/order 字段。

### 3.5 State / Action / Reward 设计

执行报告的 state feature v0、binary allow/block action space、R0/R1/R2 reward ablation 符合主线。

审查判断：通过。

重点通过项：

```text
1. inference feature 只允许 as-of 可得字段。
2. 第一版动作空间优先 binary allow_buy/block_buy、allow_sell/block_sell。
3. 禁止 target_weight、target_position、shares、lots、execution_quantity、cash allocation、broker order。
4. reward/label 只用于训练与评估，不得进入 inference。
5. return-first 被写为 primary objective。
```

### 3.6 Validator / Golden Samples / Forbidden Audit

执行报告设计了统一 validator：

```text
scripts/validate_tw_policy_action_model_artifacts.py
```

并给出 dataset / decision / evaluation 三类 artifact 的检查项、JSON 输出、阻断状态，以及 positive / negative golden samples。

审查判断：通过。

这满足 PA0 阻断项中“没有 validator / golden sample 设计则失败”的要求。

### 3.7 Research Adoption Audit

执行报告完成了 FinRL、EIIE/PVM、Moody & Saffell、LinUCB、CQL、IQL、BCQ、Decision Transformer、DeepPocket、risk/cost-aware literature 的五列审计：

```text
adopted / rejected / deferred / risk / PA_mapping
```

审查判断：通过。

该节不是简单列论文名，已明确：

```text
PA1 先 supervised utility
PA2 才 contextual bandit
PA3 才 offline RL
PA4 才考虑 LTR adapter / graph extension
```

符合主线“不直接 RL”的要求。

## 4. Findings

### Critical

无。

### High

无。

### Medium

#### M1. `label_utility_*` 的 split 语义需要在 PA1 中收紧

执行报告中 `samples.csv` 字段表把 `label_utility_*` 写为：

```text
train dataset only
```

这个表达容易被后续执行者误读为 validation / strict_test 不计算 label。PA1 需要 validation 做 threshold/reward selection，也需要 strict_test 做最终评价，因此 validation/test 可以有 label/reward 结果，但必须满足：

```text
1. label 只用于训练/evaluation/threshold audit。
2. label 不进入 policy inference feature。
3. validation label 只能用于选择阈值、reward ablation 和模型版本。
4. strict_test label 只能用于最终一次评估，不得反向调参。
5. label_leakage_audit 必须逐字段说明用途。
```

PA1 必须把字段语义修正为：

```text
label_utility_* = dataset label namespace, may exist for train/validation/strict_test evaluation,
                  never allowed in inference feature or PolicyDecisionArtifact.
```

这不是 PA0 阻断项，但必须在 PA1 的 dataset schema / validator / golden samples 中修正。

#### M2. 新增 policy artifact 能力需要登记 registry 或等价实验登记

执行报告设计了新的 policy artifact 和 validator，但 PA0 尚未要求实际落 registry。

审查判断：PA0 可接受；PA1 必须补齐。

依据 `NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md`，新增能力必须具备：

```text
artifact_type
schema_version
contract_doc
validator
golden_sample
capabilities
dependencies
allowed_consumers
forbidden_consumers
production_allowed=false
owner_or_stage
```

PA1 至少需要新增一个实验 registry / policy artifact registry 条目，或在 manifest 中提供等价登记并由 validator 检查。否则 PA1 后续容易变成未登记实验产物绕过模块化合同。

#### M3. PA1 必须按主线完整执行，不能另行拆分或合并阶段

本审查只允许进入主线定义的 PA1：

```text
PA1: qlib-only supervised utility model
```

PA1 内部可以按工程依赖先落 validator / golden samples / dataset builder，再训练与评估；但对外阶段名称、审查输出和执行报告必须保持主线定义，不得新增子阶段，不得把 PA1 与 PA2 合并，也不得提前进入 contextual bandit / offline RL。

### Low

#### L1. PA1 输出路径可以保留主线命名并用子目录表达工程顺序

执行报告建议的 dataset 目录可接受：

```text
data_tw/experiments/policy_action_model_research/pa1_qlib_only_supervised_utility_dataset/
```

若 PA1 需要区分 validator、dataset、decision、evaluation，可在 PA1 目录内部使用子目录表达，不改变阶段名称。

## 5. 安全边界审查

未发现以下越界：

| 禁止项 | 审查结论 |
|---|---|
| 训练 policy/action model | PA0 未执行；PA1 才允许 supervised utility 训练 |
| 重训 qlib / LTR | 未执行 / PA1 不授权 |
| 修复 2023-2025 LTR artifact | 未执行 / PA1 不授权 |
| 读取 qlib/LTR 私有 CSV 作为 policy 输入 | 未授权 / 设计禁止 |
| 旧 `portfolio_decision_optimizer_v1` 动作作为标签 | 设计禁止 |
| future/replay/realized pnl 进入 inference feature | 设计禁止 |
| 直接 contextual bandit / offline RL | 未执行 / PA1 不授权 |
| 输出 target_position / target_weight / quantity / broker order | 设计禁止 |
| provider publish / refresh | 未执行 / PA1 不授权 |
| accepted latest switch | 未执行 / PA1 不授权 |
| monitor config / scan / alerts write | 未执行 / PA1 不授权 |
| broker / quick-trade / real order | 未执行 / PA1 不授权 |
| default strategy / frontend default switch | 未执行 / PA1 不授权 |
| OpenAI call / API key 读取 | 未执行 / PA1 不授权 |

关键词如 `order`、`broker`、`target_weight`、`accepted latest` 出现在禁止清单、安全声明和审查上下文中，不构成实际越界。

## 6. 审查判定

PA0 通过。

```text
review_decision = PASS_READY_FOR_PA1_SUPERVISED_UTILITY_DATASET
next_work = POLICY_PA1_QLIB_ONLY_SUPERVISED_UTILITY
```

后续必须按主线阶段推进，不得由审查者或执行者自行拆分、合并或改名阶段。

## 7. PA1 工作文档

### 7.1 目标

启动主线 PA1：qlib-only supervised utility model。

PA1 的目标按主线文档执行：

```text
1. 用 frozen_qlib_2018_2022 的 2023-2026H1 标准 signal 构造 policy dataset。
2. 训练简单 supervised utility model，优先 Logistic Regression / LightGBM / small MLP。
3. 预测每个候选动作的 utility 或 allow/block 概率。
4. 只在 validation 上选择阈值；strict_test 只做一次最终评估。
5. 输出 PolicyDecisionArtifact 与 readonly replay。
```

### 7.2 必须读取

执行者必须读取：

```text
docs/tw_portfolio_decision_model/PHASE_POLICY_ACTION_MODEL_RESEARCH_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PA0_CONTRACT_DATASET_EVAL_DESIGN_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_PA0_CONTRACT_DATASET_EVAL_DESIGN_REVIEW_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md
docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md
```

### 7.3 PA1 必须产出

PA1 至少产出：

```text
scripts/validate_tw_policy_action_model_artifacts.py
policy action model positive / negative golden samples
PolicyTrainingDatasetArtifact
PolicyDecisionArtifact
PolicyEvaluationArtifact
readonly replay artifacts, only through OrderIntentArtifact and ReplayResultArtifact
docs/tw_portfolio_decision_model/POLICY_PA1_QLIB_ONLY_SUPERVISED_UTILITY_EXECUTION_REPORT_CN.md
```

其中 artifact 路径按 PA0 设计和 PA1 主线要求落在：

```text
data_tw/experiments/policy_action_model_research/
```

### 7.4 PA1 必须满足的工程与审计要求

PA1 必须：

```text
1. source signal 固定为 frozen_qlib_2018_2022 标准 ModelSignalArtifact。
2. dataset builder 不读取模型私有 CSV。
3. 不把 portfolio_decision_optimizer_v1 动作当标签。
4. train / validation / strict_test 切分按 PA0 固定。
5. validator 与 positive/negative golden samples 落地。
6. label_utility_* 只在 dataset label namespace；不得进入 inference feature 或 PolicyDecisionArtifact。
7. threshold / reward / model selection 只能使用 validation。
8. strict_test 只做一次最终评估，不得倒调。
9. PolicyDecisionArtifact 为 readonly diagnostic，不接生产默认。
10. readonly replay 必须通过 StrategyRule adapter -> OrderIntentArtifact -> ReplayResultArtifact。
11. evaluation 必须包含 baseline comparison、R0/R1/R2、threshold_selection_audit、failure_mode_audit、forbidden_input_output_audit。
12. return-first metrics 必须放在报告前部。
```

validator 至少检查：

```text
FAIL_FORBIDDEN_FIELD_PRESENT
FAIL_SPLIT_BOUNDARY_VIOLATION
FAIL_LABEL_ENTERED_INFERENCE
FAIL_SOURCE_SIGNAL_NOT_FROZEN_QLIB
FAIL_POLICY_OUTPUT_CONTAINS_ORDER_OR_TARGET
FAIL_TEST_TUNING_EVIDENCE
FAIL_BASELINE_COMPARISON_MISSING
FAIL_FORBIDDEN_LABEL_SOURCE
```

### 7.5 PA1 评价门槛

PA1 通过必须 return-first：

```text
1. strict_test net_return_after_fee_tax 原则上应超过 baseline，至少不能显著低于 baseline。
2. validation 与 strict_test 的收益方向不能互相矛盾。
3. 若收益略低于 baseline，必须有统筹明确接受的回撤/成本 tradeoff。
4. 不能只凭 turnover、fee、drawdown 改善推进。
5. buy_count / sell_count / skip_count 不能复现旧 P 分支过度保守失败模式。
6. validator 和 modular regression 通过。
```

默认阻断：

```text
只降低 turnover / fee / drawdown，但 strict_test net_return_after_fee_tax 明显低于 baseline。
```

### 7.6 禁止事项

PA1 不授权：

```text
训练或重训 qlib / LTR
修复 2023-2025 LTR artifact
读取 qlib/LTR 私有 CSV 作为 policy 输入
把 portfolio_decision_optimizer_v1 动作当标签
用 replay return / realized pnl / future return 作为 inference feature
用 strict_test 选择 threshold / reward / model / feature / action space
进入 contextual bandit
进入 offline RL
Decision Transformer
输出 target_position / target_weight / quantity / cash allocation / broker order
provider publish / refresh
accepted latest switch
monitor write / scan / alerts
broker / quick-trade / real order
frontend default recommendation
Agent prompt/tool/action 扩权
OpenAI call
```

### 7.7 PA1 审查结论值

PA1 审查者可给：

```text
PASS_READY_FOR_PA2_CONTEXTUAL_BANDIT
FAIL_NEEDS_PA1_REPAIR
STOP_DO_NOT_CONTINUE
```

### 7.8 给 PA1 执行者的 Prompt

```text
你是执行者。请按主线文档启动 Policy / Action Model Research 的 PA1：qlib-only supervised utility model。

必须读取：
- docs/tw_portfolio_decision_model/PHASE_POLICY_ACTION_MODEL_RESEARCH_MAINLINE_CN.md
- docs/tw_portfolio_decision_model/POLICY_PA0_CONTRACT_DATASET_EVAL_DESIGN_EXECUTION_REPORT_CN.md
- docs/tw_portfolio_decision_model/POLICY_PA0_CONTRACT_DATASET_EVAL_DESIGN_REVIEW_CN.md
- docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
- docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
- docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
- docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
- docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
- docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
- docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
- docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md
- docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md

本轮是主线 PA1，不得拆分、合并或改名阶段。

目标：
1. 用 frozen_qlib_2018_2022 的 2023-2026H1 标准 signal 构造 policy dataset。
2. 落地 validator 与 positive/negative golden samples。
3. 训练简单 supervised utility model，优先 Logistic Regression / LightGBM / small MLP。
4. 做 R0/R1/R2 reward ablation。
5. 只在 validation 上选择模型、reward 和 threshold。
6. strict_test 只做一次最终评估。
7. 输出 PolicyDecisionArtifact 与 readonly replay。
8. 输出 PolicyEvaluationArtifact，包含 baseline comparison、threshold_selection_audit、reward_ablation_audit、failure_mode_audit、forbidden_input_output_audit。
9. 报告必须把 net_return_after_fee_tax 与 excess_net_return_vs_baseline 放在最前。

禁止：
不训练/重训 qlib/LTR；
不修 2023-2025 LTR artifact；
不读取模型私有 CSV；
不把 portfolio_decision_optimizer_v1 动作当标签；
不让 future/replay/realized pnl 进入 inference feature；
不使用 strict_test 调 threshold/reward/model/feature/action space；
不进入 contextual bandit/offline RL；
不输出 target_position/target_weight/quantity/order；
不 provider publish；
不 accepted latest switch；
不 monitor write；
不 broker/quick-trade/real order；
不 frontend default；
不 Agent 扩权；
不 OpenAI call。

输出：
docs/tw_portfolio_decision_model/POLICY_PA1_QLIB_ONLY_SUPERVISED_UTILITY_EXECUTION_REPORT_CN.md
```
