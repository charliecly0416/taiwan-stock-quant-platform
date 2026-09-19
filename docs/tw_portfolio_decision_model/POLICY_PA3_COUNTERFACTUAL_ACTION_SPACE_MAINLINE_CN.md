---
created_at: 2026-06-21
status: coordinator_mainline_counterfactual_policy_action_space_v1
scope: policy_action_model_after_pa2_stop
previous_pa2_summary: docs/tw_portfolio_decision_model/POLICY_PA2_CONTEXTUAL_BANDIT_STAGE_SUMMARY_FOR_COORDINATOR_CN.md
base_signal_first: frozen_qlib_2018_2022
policy_train_valid_test_required: true
readonly_only: true
simulation_only: true
not_order: true
not_target_position: true
not_investment_advice: true
production_allowed: false
no_online_rl: true
no_target_weight: true
---

# Counterfactual Action Space Policy 主线：不再绑定 baseline 的动作价值学习

## 1. 统筹结论

PA2 qlib-only contextual bandit 已停止：

```text
summary = docs/tw_portfolio_decision_model/POLICY_PA2_CONTEXTUAL_BANDIT_STAGE_SUMMARY_FOR_COORDINATOR_CN.md
recommendation = STOP_DO_NOT_CONTINUE_PA3
```

PA2 的失败不是合同失败，也不是 qlib signal 失效，而是当前 policy 研究假设太窄：

```text
1. 初版 PA2 退化为 baseline copy，bandit_block_count=0。
2. repair 轮 validation 有 buy_replacement alpha，但 strict_test 低于 baseline。
3. guardrail 轮 accepted replacement=0，strict_test 仍低于 baseline。
4. behavior policy 是 deterministic baseline replay，不支持无偏 OPE，也不足以进入 offline RL。
```

因此后续仍然专注 policy，但必须换研究假设：

```text
从“修改 baseline 动作”转向“构造更丰富的 counterfactual action dataset，学习动作价值排序”。
```

本路线不回到 qlib / LTR 信号增强；第一阶段仍使用：

```text
signal_artifact = data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json
model_family = qlib
qlib_train_window = 2018-2022
policy_train/valid/test = 2023-2026H1 split
```

但 action space 不再被 baseline 绑死。

## 2. 为什么 PA2 不应继续调参

PA2 当前动作空间是：

```text
allow/block baseline buy/sell
buy_replacement within narrow qlib top50 constraints
sell_only diagnostic
```

这个空间的问题：

```text
1. baseline 已经吃到大部分 qlib ranking alpha。
2. policy 一旦 block 好动作，就形成 false_block_buy。
3. replacement 候选太少，guardrail 后 accepted replacement=0。
4. validation alpha 不迁移到 strict_test。
5. deterministic baseline replay 无法提供充分 behavior coverage。
```

所以继续做 PA2 修复，大概率只会在以下两种状态之间摆动：

```text
baseline copy: 安全但无增量。
nonzero action: validation 有收益但 strict_test false-block / false-replacement。
```

新路线必须扩大候选动作空间，让模型看到“同一状态下多个可能动作的反事实结果”，而不是只判断 baseline 做过的一个动作。

## 3. 参考研究与采用方式

本路线参考以下研究，但按本项目合同做取舍：

| 研究 | 链接 | 可借鉴点 | 本项目采用 | 本项目不采用 |
|---|---|---|---|---|
| FinRL | https://arxiv.org/abs/2011.09607 | 分层交易环境、agent、交易成本、回测分析 | 采用 environment / agent / backtest 分离；用于设计 counterfactual simulator 与 readonly replay 分层 | 不接 live trading，不输出 order/quantity |
| EIIE / Portfolio RL | https://arxiv.org/abs/1706.10059 | portfolio state、交易成本、显式 reward、组合上下文 | 采用 portfolio context 与 cost-aware return label；可作为未来 state extension | 不输出连续 target_weight，不采用 online stochastic update |
| LinUCB / contextual bandit | https://arxiv.org/abs/1003.0146 | context-action 价值估计，小动作空间 bandit | 采用“context + action features -> value”的监督/排序形式 | 不声称 deterministic replay 是无偏 bandit OPE |
| Doubly Robust OPE | https://arxiv.org/abs/1511.03722 | off-policy evaluation 需要处理 bias/variance；DR 可做安全 policy evaluation | 用于设计 OPE bias audit；只有 behavior propensity 可定义时才尝试 IPS/DR | 当前 deterministic baseline 不允许无偏 OPE claim |
| CQL | https://arxiv.org/abs/2006.04779 | offline RL 中保守估计 OOD action 价值 | 后续若进入 offline RL，用 conservative value / OOD action audit | 当前阶段不进 PA3 RL |
| IQL | https://arxiv.org/abs/2110.06169 | 尽量不显式查询数据外 action，适合 offline coverage 不足 | 作为后续 offline RL 候选，要求先有 action coverage | 当前不做 IQL |
| BCQ / behavior-constrained RL | https://arxiv.org/abs/1812.02900 | 约束 policy 接近 behavior distribution，降低 extrapolation error | 后续用于约束 action ranker 不选 coverage 过低动作 | 当前不做 batch RL |
| Slate / ranking RL 思路 | SlateQ / slate recommendation 相关研究 | 从单动作扩展到 slate/list 选择，关注组合动作集合价值 | 借鉴“动作集合/候选列表价值排序”，用于 topK action slate | 不做推荐系统式在线探索，不做无界 slate |

执行者必须在第一阶段报告中新增：

```text
Research Adoption Audit
```

逐项说明：

```text
adopted / rejected / deferred / risk / PA_mapping
```

## 4. 新路线核心：CounterfactualActionDataset

### 4.1 数据集目标

构造一个比 baseline replay 更丰富的数据集：

```text
one row = signal_date + portfolio_state + candidate_action
```

而不是：

```text
one row = baseline action only
```

每个交易日应生成多个可选动作：

```text
buy candidates from qlib topK
sell candidates from current holdings
hold candidates for current holdings
pair actions: sell_i + buy_j
no_action / keep_baseline
```

每个候选动作都计算可审查的反事实 label：

```text
future_after_fee_tax_return
relative_return_vs_baseline_action
relative_return_vs_no_action
action_cost
holding_period_return
missed_upside_if_not_selected
drawdown_or_volatility_proxy
```

注意：这些 label 只用于训练/评估，不得进入 inference feature。

### 4.2 推荐 action space v1

第一版仍保持离散动作，不输出目标仓位或数量：

```text
A0 = no_action / keep_current
A1 = buy_one(candidate_j)
A2 = sell_one(holding_i)
A3 = switch_pair(sell holding_i, buy candidate_j)
A4 = keep_baseline_action
```

推荐先聚焦：

```text
switch_pair(sell_i, buy_j)
```

原因：baseline 的收益来自持续参与；单纯 block buy 容易降低参与度。pair action 能在保持参与度的同时寻找更优替换。

候选边界：

```text
buy_j from qlib topK, K = 50 / 100 / 150 ablation
sell_i from current holdings, preferably worst rank / weak score / stale holding candidates
max candidate actions per day capped, e.g. 200 / 500 / 1000 for tractability
```

### 4.3 不允许的 action

第一版禁止：

```text
target_weight
target_position
shares
lots
execution_quantity
cash allocation
broker order
multi-day order schedule
online exploration action
```

即使动作是 `switch_pair`，输出也只能是 intent：

```text
sell intent + buy intent
```

实际数量、价格、现金和成交仍由 ReplayExecution 决定。

## 5. 训练目标：Action Value Ranking，而不是 baseline filtering

当前 PA1/PA2 的问题是 allow/block baseline。新路线改为：

```text
learn f(state, action) -> expected after-fee-tax action value
rank candidate actions per day
select top action or top small slate
```

模型选择顺序：

```text
PAV1: supervised action value regression / ranking
PAV2: listwise/pairwise action ranker
PAV3: constrained slate policy
PAV4: offline RL only after coverage evidence
```

第一版不做 RL，而做监督学习：

```text
regression: predict future_after_fee_tax_return or relative_return_vs_baseline
classification: action_value > baseline_action_value
ranking: pairwise rank candidate actions within same day
```

推荐模型：

```text
LightGBM / sklearn HistGradientBoosting / RandomForest
Logistic Regression / Ridge as baseline
small MLP diagnostic only
```

## 6. 切分与 OOS

必须沿用 policy 自身切分：

```text
train = 2023-01-03 到 2024-12-31
validation = 2025-01-01 到 2025-12-31
strict_test = 2026-01-01 到 2026-05-07
```

只允许 validation 选择：

```text
K topK universe
candidate action cap
model family
label horizon
threshold / topN action count
risk/cost penalty
slate size
```

strict_test 只能最终评估一次。

## 7. Artifact 设计

### 7.1 CounterfactualActionDatasetArtifact

推荐路径：

```text
data_tw/experiments/policy_action_model_research/pav1_counterfactual_action_dataset/
```

必需文件：

```text
manifest.json
actions.csv
schema.json
action_generation_audit.csv
label_audit.csv
split_audit.csv
coverage_audit.csv
forbidden_field_audit.csv
counterfactual_price_audit.csv
```

`actions.csv` 字段建议：

```text
action_id
signal_date
instrument_buy
instrument_sell
action_type
split
source_signal_artifact
state_feature_*
action_feature_*
label_future_after_fee_tax_return
label_relative_return_vs_baseline
label_relative_return_vs_no_action
label_horizon
available_at
```

禁止字段作为 inference feature：

```text
label_*
future_*
realized_pnl
replay_return
execution_price
cash_after
nav_after
```

### 7.2 ActionValueModelArtifact

必需文件：

```text
manifest.json
model_config.json
feature_schema.json
training_metrics.csv
validation_selection_audit.csv
feature_importance.csv, if available
forbidden_feature_audit.csv
```

### 7.3 ActionSlateDecisionArtifact

policy 输出不是订单，而是动作选择诊断：

```text
manifest.json
action_slate_decisions.csv
schema.json
policy_input_audit.csv
forbidden_output_audit.csv
```

字段建议：

```text
signal_date
selected_action_id
action_type
instrument_buy
instrument_sell
policy_score
policy_rank
policy_reason_code
source_counterfactual_dataset
readonly_only
simulation_only
not_order
not_target_position
```

禁止输出：

```text
quantity
shares
lots
target_weight
target_position
cash_allocation
broker_order_id
quick_trade
```

### 7.4 Strategy adapter

标准链路：

```text
ModelSignalArtifact
  -> CounterfactualActionDatasetArtifact
  -> ActionValueModelArtifact
  -> ActionSlateDecisionArtifact
  -> StrategyRule adapter
  -> OrderIntentArtifact
  -> ReplayResultArtifact
```

adapter 只把选中的离散动作转成 buy/sell/hold/skip intent，不计算仓位、数量、价格或现金。

## 8. 阶段计划

## PAV0：合同与 counterfactual dataset 设计

目标：

```text
1. 定义 CounterfactualActionDatasetArtifact / ActionValueModelArtifact / ActionSlateDecisionArtifact。
2. 定义 action space v1：no_action / buy_one / sell_one / switch_pair / keep_baseline。
3. 定义 topK 候选、action cap、pair generation rule。
4. 定义 label 计算方式和 leakage audit。
5. 不训练、不 replay。
```

执行者输出：

```text
docs/tw_portfolio_decision_model/POLICY_PAV0_COUNTERFACTUAL_ACTION_DATASET_DESIGN_EXECUTION_REPORT_CN.md
```

审查者输出：

```text
docs/tw_portfolio_decision_model/POLICY_PAV0_COUNTERFACTUAL_ACTION_DATASET_DESIGN_REVIEW_CN.md
```

通过条件：

```text
PASS_READY_FOR_PAV1_DATASET_BUILD
```

## PAV1：构建 counterfactual action dataset

目标：

```text
1. 用 frozen_qlib_2018_2022 标准 signal 构造 train/validation/strict_test counterfactual actions。
2. 覆盖 buy_one / sell_one / switch_pair / no_action / keep_baseline。
3. 输出 label、coverage、forbidden audit。
4. 不训练模型。
```

执行者输出：

```text
docs/tw_portfolio_decision_model/POLICY_PAV1_COUNTERFACTUAL_ACTION_DATASET_BUILD_EXECUTION_REPORT_CN.md
```

审查者输出：

```text
docs/tw_portfolio_decision_model/POLICY_PAV1_COUNTERFACTUAL_ACTION_DATASET_BUILD_REVIEW_CN.md
```

通过条件：

```text
PASS_READY_FOR_PAV2_ACTION_VALUE_RANKER
```

## PAV2：Action value ranker

目标：

```text
1. 训练 action value regression / classification / pairwise ranker。
2. 只用 validation 选择模型、topK、slate size、penalty。
3. strict_test final-only。
4. 输出 ActionSlateDecisionArtifact、OrderIntentArtifact、ReplayResultArtifact。
```

执行者输出：

```text
docs/tw_portfolio_decision_model/POLICY_PAV2_ACTION_VALUE_RANKER_EXECUTION_REPORT_CN.md
```

审查者输出：

```text
docs/tw_portfolio_decision_model/POLICY_PAV2_ACTION_VALUE_RANKER_REVIEW_CN.md
```

通过条件：

```text
PASS_READY_FOR_PAV3_CONSTRAINED_SLATE_POLICY
```

PAV2 必须超过或接近 baseline：

```text
strict_test net_return_after_fee_tax >= baseline, preferred
or strict_test not materially below baseline with clear coordinator-approved tradeoff
```

## PAV3：Constrained slate policy

只有 PAV2 有稳定 strict_test nonzero positive evidence 后才允许。

目标：

```text
1. 每日选择 top small slate 的 action，而不是单一 action。
2. 加入 action diversity、turnover cap、position integrity constraints。
3. 仍然只输出 OrderIntent，不输出 target weight / quantity。
```

## PAV4：Offline RL deferred

只有在 PAV1/PAV2/PAV3 证明 action coverage 足够、behavior/action support 可审查后，才允许重新讨论 CQL/IQL/BCQ。

当前不授权 PAV4。

## 9. 评估指标

收益指标置于最前：

```text
net_return_after_fee_tax
excess_net_return_vs_baseline
gross_return
max_drawdown
action_count
buy_count
sell_count
switch_pair_count
no_action_count
turnover_proxy
fee_and_tax
average_holding_days
median_holding_days
yearly_metrics
rolling_3m_metrics
rolling_6m_metrics
regime_segment_metrics
PnL concentration
symbol turnover concentration
action_coverage_by_day
action_coverage_by_type
selected_action_value_distribution
false_positive_action_count
missed_best_action_count
baseline_action_rank_distribution
replacement_success_rate
forbidden_input_output_audit
```

必须报告：

```text
baseline action 在候选动作集合中的 rank 分布
policy 选择动作相对 baseline 动作的 label advantage
strict_test selected nonzero actions 的逐笔解释
```

## 10. 停止条件

任一情况应停止当前路线或回到统筹：

```text
1. counterfactual labels 存在 leakage，无法修复。
2. strict_test 仍无法超过或接近 baseline。
3. 选中动作主要来自低覆盖 / OOD action。
4. validation alpha 连续不迁移 strict_test。
5. policy 退化为 baseline copy，没有 nonzero action evidence。
6. policy 输出 target_weight / quantity / order 等越界字段。
```

## 11. 禁止事项

本路线不授权：

```text
重训 qlib / LTR
修 2023-2025 LTR artifact
读取 qlib/LTR 私有 CSV 作为策略输入
把 portfolio_decision_optimizer_v1 动作当标签
用 future/replay/realized pnl 作为 inference feature
用 strict_test 做模型/阈值/topK/slate 选择
输出 target_position / target_weight / quantity / cash allocation / broker order
provider publish / accepted latest switch
monitor write / scan / alerts
broker / quick-trade / real order
frontend default recommendation
Agent / OpenAI 调用
online RL
offline RL, until PAV4 separately authorized
```

## 12. 给 PAV0 执行者的 Prompt

```text
你是执行者。请启动 Counterfactual Action Space Policy 主线 PAV0：合同与 counterfactual dataset 设计。

必须读取：
- docs/tw_portfolio_decision_model/POLICY_PA2_CONTEXTUAL_BANDIT_STAGE_SUMMARY_FOR_COORDINATOR_CN.md
- docs/tw_portfolio_decision_model/POLICY_PA2_QLIB_ONLY_CONTEXTUAL_BANDIT_REPAIR_GUARDRAIL_REVIEW_CN.md
- docs/tw_portfolio_decision_model/PHASE_POLICY_ACTION_MODEL_RESEARCH_MAINLINE_CN.md
- docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
- docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
- docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
- docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
- docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
- .agents/skills/tw-stock-new-model-onboarding/SKILL.md
- .agents/skills/tw-stock-new-strategy-onboarding/SKILL.md

本轮只做 PAV0 设计，不训练、不 replay、不进入 RL。

目标：
1. 明确 PA2 停止原因：baseline-bound small action space 不足。
2. 设计 CounterfactualActionDatasetArtifact。
3. 设计 action space v1：no_action / buy_one / sell_one / switch_pair / keep_baseline。
4. 设计 topK、action cap、pair generation、label horizon、cost-aware label。
5. 设计 ActionValueModelArtifact 与 ActionSlateDecisionArtifact。
6. 设计 leakage audit、coverage audit、forbidden output audit、strict_test final-only audit。
7. 完成 Research Adoption Audit，说明 FinRL / EIIE / LinUCB / DR-OPE / CQL / IQL / BCQ / Slate-ranking 思路 adopted/rejected/deferred。

禁止：
不训练模型；不 replay；不进入 PA3/offline RL；不重训 qlib/LTR；不修 LTR artifact；不读取私有 CSV；不用旧 P 动作当标签；不输出 target_position/target_weight/quantity/order；不 provider/latest/monitor/broker/OpenAI。

输出：
docs/tw_portfolio_decision_model/POLICY_PAV0_COUNTERFACTUAL_ACTION_DATASET_DESIGN_EXECUTION_REPORT_CN.md
```

## 13. 给 PAV0 审查者的 Prompt

```text
你是审查者。请审查 PAV0 执行报告：

- 是否正确理解 PA2 停止原因；
- 是否没有回到信号/排序增强，而是专注 policy action space；
- 是否设计 counterfactual action dataset，而不是 baseline-only action log；
- action space 是否离散、可审查，且不输出 target weight / quantity / order；
- label 是否只用于训练/评估，不进入 inference feature；
- 是否有 train/validation/strict_test split；
- 是否有 leakage / coverage / OOD / forbidden audit；
- 是否严格禁止 strict_test selection；
- 是否没有进入 offline RL；
- 是否完成研究采用矩阵，而不是只列论文名。

审查结论值：
PASS_READY_FOR_PAV1_DATASET_BUILD
FAIL_NEEDS_PAV0_REPAIR
STOP_DO_NOT_CONTINUE

输出：
docs/tw_portfolio_decision_model/POLICY_PAV0_COUNTERFACTUAL_ACTION_DATASET_DESIGN_REVIEW_CN.md
```
