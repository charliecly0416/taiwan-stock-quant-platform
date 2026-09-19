---
created_at: 2026-06-22
status: coordinator_mainline_baseline_anchored_active_policy_v1
scope: after_pal2_r_eiie_free_allocation_failure
previous_pal_review: docs/tw_portfolio_decision_model/POLICY_PAL2_R_COST_AWARE_CONCENTRATION_CONSTRAINED_EIIE_REVIEW_CN.md
base_signal_first: frozen_qlib_2018_2022
policy_train_valid_test_required: true
readonly_only: true
simulation_only: true
not_order: true
not_investment_advice: true
production_allowed: false
strict_test_authorized_initially: false
provider_publish_authorized: false
accepted_latest_switch_authorized: false
monitor_write_authorized: false
broker_authorized: false
frontend_default_switch_authorized: false
order_intent_target_weight_allowed: false
---

# PBA Baseline-anchored Active Policy 主线

## 0. 统筹结论

PAL paper-aligned free allocation route 已给出足够清楚的阶段性负证据：

```text
PAL2 minimal EIIE-CNN:
  gross return 可高，但 after-fee-tax 被交易成本吞噬；
  allocation 高集中；
  seed stability fail。

PAL2-R cost/concentration repair:
  turnover / cost / concentration 指标形式改善；
  但策略退化为 cash / no-trade dominant；
  validation after-fee-tax 远低于 baseline；
  所有 config seed stability fail。
```

这说明当前失败不是：

```text
baseline 已经没有提升空间。
```

更可能是：

```text
free portfolio allocation action space 对本项目不适配。
```

本项目已经有强 ranking signal：

```text
frozen qlib 2018-2022
后续 qlib + orthogonal LTR
```

所以 policy 不应从零决定完整组合，而应学习：

```text
在强 baseline 组合上的主动增量决策。
```

本路线命名为：

```text
PBA = Baseline-anchored Active Policy
```

核心思想：

```text
baseline 负责主要选股 alpha；
policy 只负责 active overlay：
  是否参与；
  买哪些 baseline 候选；
  卖出是否延后；
  top-ranked 权重是否加减；
  score 阈值是否触发；
  市场状态下风险资产暴露是否收缩；
  是否减少无效换手。
```

## 1. 目标

本主线要回答：

```text
在 frozen qlib ranking / score、历史价格特征、当前持仓、交易成本和市场状态下，
能否学习一个 baseline-anchored active policy，
使 readonly replay 的 net_return_after_fee_tax 高于 baseline？
```

第一阶段只使用 qlib-only：

```text
input_signal_artifact =
data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json

base qlib train = 2018-2022
policy train = 2023-01-01..2024-12-31
policy validation = 2025-01-01..2025-12-31
policy strict_test = 2026-01-01..2026-05-07, declared only
```

初始阶段不使用 qlib+LTR。只有 qlib-only 在 validation 和 strict_test 均证明有效后，才允许另开 LTR adapter。

## 2. 非目标

本主线初始阶段不授权：

```text
1. strict_test。
2. qlib+orthogonal LTR。
3. provider publish / accepted latest switch。
4. monitor write / frontend default / Agent integration。
5. broker / quick-trade / real order。
6. 生产默认策略切换。
7. OrderIntent target_weight / target_position / quantity。
8. 从零自由 portfolio allocation。
9. 直接把论文结论当成本项目收益承诺。
```

本路线也不允许：

```text
用 cash-only / no-trade 作为成功。
用低换手、低成本、低回撤替代收益目标。
用 gross return 替代 after-fee-tax return。
用 validation 反复调参。
用 strict_test 选择模型。
```

## 3. 为什么从 PAL 转向 PBA

PAL 自由 allocation 的两类失败模式：

```text
1. 无强约束：
   policy 学到高换手、高集中、gross return 但 net return 不足。

2. 加强成本/集中约束：
   policy 学到 cash/no-trade，避免成本但错过 baseline alpha。
```

这说明：

```text
free allocation vector 给了模型过大的动作自由度，
但当前数据量、成本结构、强 baseline 和日频市场并不支持它稳定从零学组合。
```

PBA 的修正：

```text
不让 policy 从零做完整组合。
policy 以 baseline portfolio / baseline candidate actions 为锚点。
policy 只学习 active delta。
```

这与本项目现实更一致：

```text
alpha 主要来自 qlib/LTR ranking；
policy 的价值是把 ranking alpha 更好地转成组合收益。
```

## 4. 参考研究与采用方式

执行者在 PBA0 必须逐项审计下列研究/方案，不能只列论文名。

| id | 研究 / 方案 | 链接 | 关键机制 | 本项目采用 | 本项目不采用 |
|---|---|---|---|---|---|
| R1 | Active Portfolio Management / active return 框架 | Grinold & Kahn, Active Portfolio Management | 组合以 benchmark 为锚点，管理 active weights / tracking risk / active return | 采用“baseline portfolio + active overlay”的思想；policy 学 active delta 而非完整组合 | 不采用生产级风险模型或 tracking error 作为主目标；本项目仍 return-first |
| R2 | Residual Policy Learning | https://arxiv.org/abs/1812.03201 | 学习对已有 controller 的 residual action，而不是从零控制 | 采用 residual/overlay 思想：baseline action + policy delta | 不照搬机器人控制环境；只做 readonly finance replay |
| R3 | FinRL | https://arxiv.org/abs/2011.09607 | market env / agent / backtest 分层，交易成本、风险控制、baseline 对照 | 采用 env-agent-replay 分层、成本和 baseline 对照、artifact 化证据 | 不接 live trading；不输出真实订单 |
| R4 | EIIE / PGPortfolio | https://arxiv.org/abs/1706.10059 | portfolio vector memory、交易成本 reward、组合状态进入模型 | 只保留 portfolio memory / cost-aware reward / trajectory replay 思想 | 不再采用 free allocation vector 作为第一优先路线 |
| R5 | Transaction cost / no-trade region literature | https://arxiv.org/abs/1207.7330 | 交易成本下存在 no-trade region，调仓需权衡成本和收益 | 采用 no-trade / minimum edge / rebalance threshold，但必须防 cash-only 退化 | 不把少交易作为成功目标 |
| R6 | Contextual bandit / LinUCB | https://arxiv.org/abs/1003.0146 | 给定 context 选择 action，适合小动作空间 | 用于 threshold/participation/active overlay 的小动作决策 baseline | 不做真实在线探索，不把非随机 replay 当无偏日志 |
| R7 | Offline RL: CQL / IQL / BCQ | https://arxiv.org/abs/2006.04779 / https://arxiv.org/abs/2110.06169 / https://arxiv.org/abs/1812.02900 | 控制 offline RL 的 OOD action 过估计 | 后续 PBA3 若做 offline RL，必须采用 behavior-anchored / conservative 约束 | PBA0-PBA2 不直接启动复杂 offline RL |
| R8 | Alpha / signal combination 与 meta-labeling 思路 | López de Prado, Advances in Financial Machine Learning | 在已有信号上学习是否执行、过滤、加权 | 采用“meta-policy over existing signal”的思想 | 不把 meta-label 当 future leakage 标签；必须 PIT-safe |

PBA0 的 `Research Adoption Audit` 必须逐项输出：

```text
paper_or_method
original_problem_setting
baseline_or_benchmark
state_definition
action_definition
reward_or_label
cost_model
why_it_may_work_here
why_it_may_fail_here
adopted_component
rejected_component
required_contract_or_artifact_change
PBA_phase_mapping
```

## 5. 核心设计：Baseline-anchored Active Overlay

PBA 不直接输出完整目标权重，也不输出生产订单。

PBA 的研究对象是：

```text
baseline portfolio / baseline action
+
active policy decision
= simulated policy portfolio / simulated policy action
```

### 5.1 Baseline 锚点

baseline 可以是 PAL1/PAL2 使用的 qlib-only baseline，必须合同化：

```text
date
baseline_candidate_universe
baseline_rank
baseline_score
baseline_buy_candidates
baseline_sell_candidates
baseline_holdings_before
baseline_holdings_after
baseline_cash_after
baseline_net_return_after_fee_tax
baseline_turnover
baseline_cost
```

执行者不得自行换 baseline。

### 5.2 PBA 允许的 active decisions

第一阶段只允许 simulation-only diagnostic decision，不进入 OrderIntent。

允许动作从小到大分三层：

```text
Layer A: participation / gating
  allow_baseline_buy
  block_baseline_buy
  allow_baseline_sell
  delay_baseline_sell
  no_extra_action

Layer B: threshold / breadth
  require_score_gap
  require_score_zscore
  dynamic_topk_expand_or_shrink_diagnostic
  market_risk_reduce_participation_diagnostic

Layer C: active tilt, diagnostic only
  overweight_top_ranked_diagnostic
  underweight_low_edge_candidate_diagnostic
  cap_low_score_holding_diagnostic
```

Layer C 只能作为 simulation-only diagnostic，不得进入 OrderIntent target_weight。

### 5.3 禁止动作

禁止：

```text
free allocation vector
all-cash policy without explicit risk-off justification
short selling
leverage
target_weight
target_position
quantity
broker order
production default switch
```

## 6. 数据与窗口

第一轮 qlib-only：

```text
train = 2023-01-01..2024-12-31
validation = 2025-01-01..2025-12-31
strict_test = 2026-01-01..2026-05-07, declared only
```

允许 state：

```text
1. qlib rank / score / raw_score / score_rank / score gap / score zscore。
2. baseline candidate action context。
3. current holdings / holding age / unrealized return, past-only。
4. historical price features: MA、volatility、momentum、volume, past-only。
5. transaction cost estimate, past-only。
6. market regime features, PIT-safe。
7. previous policy diagnostic decisions, train replay only。
```

禁止 state：

```text
future_return
label
future price
same-day unavailable data
realized_pnl as feature
oracle action
strict_test metric
validation metric used inside training loop
```

## 7. Artifact 合同

PBA 必须新增或冻结 research-only artifacts。

### 7.1 BaselineActionSnapshotArtifact

用途：

```text
记录 baseline 在每个 rebalance date 的候选动作和组合状态。
```

必需字段：

```text
date
instrument
baseline_rank
baseline_score
baseline_action_type
baseline_position_before_diagnostic
baseline_position_after_diagnostic
baseline_holding_age
baseline_candidate_reason
source_signal_artifact
simulation_only = true
readonly_research_only = true
production_allowed = false
```

字段使用 `_diagnostic` 后缀时，不得映射为 OrderIntent。

### 7.2 ActivePolicyDecisionArtifact

用途：

```text
记录 policy 对 baseline action 的 active overlay 决策。
```

允许字段：

```text
date
instrument
baseline_action_type
active_decision_type
active_decision_score
active_decision_reason_code
active_overlay_delta_diagnostic
participation_flag_diagnostic
risk_asset_exposure_flag_diagnostic
source_policy_id
source_baseline_snapshot_artifact
simulation_only = true
readonly_research_only = true
production_allowed = false
forbidden_consumers
```

禁止字段：

```text
target_weight
target_position
quantity
order_size
broker_order
```

### 7.3 PBAReplayResultArtifact

用途：

```text
只在 readonly research replay 内部评估 active overlay 后的模拟组合。
```

必须包含：

```text
net_return_after_fee_tax
gross_return
turnover
fee
sell_tax
cost_drag
drawdown
participation_rate
risk_asset_exposure
cash_dominance_rate
baseline_excess_return_after_fee_tax
action_concentration
pnl_concentration
seed_stability
strict_test_used
```

## 8. 新增 Gate：防止 cash/no-trade 退化

PBA 必须从 PAL2-R 的失败中吸取教训，新增 hard gates：

```text
minimum_participation_rate
minimum_risk_asset_exposure
maximum_cash_dominance_rate
minimum_baseline_action_coverage
minimum_buy_candidate_coverage
minimum_sell_review_coverage
```

通过条件不能只看：

```text
cost 低
turnover 低
drawdown 低
concentration pass
```

如果策略通过这些指标的方式是：

```text
长期现金
长期不交易
长期 block baseline buy
只交易极少日期
```

则必须失败。

## 9. 阶段计划

## PBA0: Contract / Baseline Snapshot / Research Audit

目标：

```text
冻结 baseline-anchored active policy 的合同、baseline snapshot、动作空间、gate 和研究采用矩阵。
```

执行者必须：

```text
1. 阅读本主线和 PAL2-R review。
2. 审计 R1-R8 研究/方案，并输出 Research Adoption Audit。
3. 定义 BaselineActionSnapshotArtifact。
4. 定义 ActivePolicyDecisionArtifact。
5. 定义 PBAReplayResultArtifact。
6. 定义 action space：Layer A/B/C。
7. 定义 cash/no-trade 退化 gates。
8. 设计 validator / golden samples。
9. 不训练、不 replay 收益、不 strict_test。
```

PBA0 输出：

```text
data_tw/experiments/baseline_anchored_active_policy/pba0_contract_baseline_audit/
  manifest.json
  research_adoption_audit.csv
  baseline_action_snapshot_schema.json
  active_policy_decision_schema.json
  pba_replay_result_schema.json
  action_space_design.md
  cash_no_trade_degeneracy_gate_design.md
  forbidden_consumer_audit.csv
  validator_design.md
  golden_sample_design.md

docs/tw_portfolio_decision_model/POLICY_PBA0_CONTRACT_BASELINE_AUDIT_EXECUTION_REPORT_CN.md
```

PBA0 通过条件：

```text
1. 研究采用矩阵完整。
2. baseline snapshot 可复现 baseline 动作。
3. ActivePolicyDecisionArtifact 不含 target_weight / target_position / quantity。
4. cash/no-trade 防退化 gate 清晰。
5. forbidden consumers 完整。
6. reviewer 能据此写 PBA1 工作文档。
```

## PBA1: Baseline Snapshot Build And Parity Replay

只有 PBA0 通过后允许。

目标：

```text
构建 baseline action snapshot，并证明 replay parity。
```

必须输出：

```text
baseline_action_snapshot_artifact
baseline_parity_replay_ledger
baseline_parity_metrics
feature_available_at_audit
cash/no-trade gate dry-run audit
```

PBA1 不允许训练，不允许 strict_test。

PBA1 通过条件：

```text
baseline parity pass
feature PIT / available_at pass
baseline action coverage pass
validator/golden samples pass
```

## PBA2: Rule-calibrated Active Overlay Sanity

只有 PBA1 通过后允许。

目标：

```text
先用少量可解释、预声明的 active overlay rule 验证 action space 是否有提升空间。
```

允许规则示例：

```text
score_gap_buy_filter
score_zscore_buy_filter
holding_age_sell_delay
trend_confirmed_hold
market_risk_exposure_reduce
top_rank_active_tilt_diagnostic
```

要求：

```text
1. 规则必须预声明。
2. validation 只能一次选择。
3. 必须与 baseline 比较 after-fee-tax。
4. 必须检查 participation / risk exposure / cash dominance。
5. 失败不能直接进入复杂模型。
```

PBA2 通过条件：

```text
validation net_return_after_fee_tax > baseline
participation gates pass
cash dominance gates pass
cost/turnover not pathological
not baseline clone
strict_test_used=false
```

## PBA3: Supervised / Bandit Active Policy

只有 PBA2 证明 action space 有可用提升空间后允许。

目标：

```text
训练一个小模型学习 baseline active overlay，而不是完整组合。
```

候选：

```text
1. supervised utility model
2. contextual bandit with conservative offline evaluation
3. shallow MLP / LightGBM active policy
```

训练标签或 reward 不得使用 future feature，但可以在训练窗口内用 replay 构造 action utility，必须严格防 leakage。

PBA3 通过条件：

```text
validation return > baseline
seed stability / fold stability pass
participation gates pass
cash dominance gates pass
OOD action audit pass
strict_test_used=false
```

## PBA4: Optional Conservative Offline RL

只有 PBA3 通过后才允许另开。

目标：

```text
在 baseline-anchored 小动作空间中试 CQL / IQL / BCQ，而不是 free allocation RL。
```

要求：

```text
behavior policy coverage audit
OOD action penalty
conservative value audit
no online exploration
no strict_test tuning
```

## PBA5: Strict-test Final Replay

只有 PBA2/PBA3/PBA4 的 validation 通过后，由统筹单独授权。

规则：

```text
1. strict_test final-only。
2. 不得根据 strict_test 改参数。
3. strict_test return > baseline 才可写阶段通过。
4. 失败则 closure，不得同线反复试。
```

## PBA6: Optional qlib+orthogonal LTR Adapter

只有 qlib-only strict_test 通过后才允许。

注意：

```text
LTR 2023-2025 是训练窗口，不能把 2023-2025 LTR replay 当严格 OOS 策略证明。
```

## 10. 审查重点

审查者每轮必须检查：

```text
1. 是否以 baseline 为锚点，而不是重新做 free allocation。
2. 是否没有 target_weight / target_position / quantity。
3. 是否没有 OrderIntent / provider / frontend / Agent / broker / production。
4. 是否 train / validation / strict_test 分离。
5. 是否没有 future feature / oracle action / realized pnl feature leakage。
6. 是否 return-first，primary metric 是 net_return_after_fee_tax。
7. 是否新增并执行 participation / risk exposure / cash dominance gates。
8. 是否没有通过 cash-only / no-trade 获得形式 pass。
9. 是否不是 baseline clone。
10. 是否没有用 validation 或 strict_test 反复调参。
```

## 11. 停止条件

必须停止并回到统筹：

```text
1. PBA0 无法给出安全合同。
2. baseline parity 失败。
3. ActivePolicyDecisionArtifact 被误接入 OrderIntent / Agent / frontend / broker。
4. 出现 target_weight / target_position / quantity。
5. feature available_at 或 PIT audit 失败。
6. validation 不过却要求 strict_test。
7. strict_test 被用于调参。
8. 策略通过 cash/no-trade 形式通过 gate。
9. action space 与 baseline 锚点脱离，退回 free allocation。
```

## 12. PBA0 执行者命令

```text
你是执行者。请启动 PBA Baseline-anchored Active Policy 主线 PBA0。

必须读取：
1. docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
2. docs/tw_portfolio_decision_model/POLICY_PAL2_R_COST_AWARE_CONCENTRATION_CONSTRAINED_EIIE_REVIEW_CN.md
3. docs/tw_portfolio_decision_model/POLICY_PAL2_R_COST_AWARE_CONCENTRATION_CONSTRAINED_EIIE_EXECUTION_REPORT_CN.md
4. docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
5. docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
6. docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
7. docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
8. docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
9. docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md

本轮只做 PBA0：
- 审计 R1-R8 研究/方案，并输出 Research Adoption Audit；
- 定义 BaselineActionSnapshotArtifact；
- 定义 ActivePolicyDecisionArtifact；
- 定义 PBAReplayResultArtifact；
- 定义 Layer A/B/C active action space；
- 定义 participation / risk exposure / cash dominance 防退化 gates；
- 设计 forbidden consumer audit、validator、golden samples；
- 写 PBA0 execution report。

本轮禁止：
- 训练模型；
- 运行收益 replay；
- 运行 strict_test；
- 输出 OrderIntent；
- 输出 target_weight / target_position / quantity / broker order；
- provider/latest/monitor/frontend/Agent/broker 扩权。

artifact root:
data_tw/experiments/baseline_anchored_active_policy/pba0_contract_baseline_audit/

执行报告：
docs/tw_portfolio_decision_model/POLICY_PBA0_CONTRACT_BASELINE_AUDIT_EXECUTION_REPORT_CN.md
```

## 13. PBA0 审查者命令

```text
你是审查者。请审查 PBA0 执行报告是否符合 PBA 主线。

必须检查：
1. R1-R8 是否逐项审计；
2. 是否真正分析 baseline-anchored / residual / active overlay 机制；
3. 是否明确 PBA 与 PAL free allocation 的差异；
4. BaselineActionSnapshotArtifact 是否能支持 baseline parity；
5. ActivePolicyDecisionArtifact 是否不含 target_weight / target_position / quantity；
6. cash/no-trade 防退化 gate 是否完整；
7. forbidden consumers 与 negative golden samples 是否完整；
8. 是否未训练、未 replay 收益、未 strict_test；
9. 是否能据此写 PBA1 baseline snapshot build 工作文档。

审查输出：
docs/tw_portfolio_decision_model/POLICY_PBA0_CONTRACT_BASELINE_AUDIT_REVIEW_CN.md

如果 PBA0 通过，请写 PBA1 工作文档。
如果合同冲突无法安全解决，请 STOP 回到统筹。
```
