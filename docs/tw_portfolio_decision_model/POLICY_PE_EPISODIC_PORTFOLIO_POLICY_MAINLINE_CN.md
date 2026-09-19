---
created_at: 2026-06-21
status: coordinator_mainline_policy_episode_portfolio_policy_v1
scope: policy_after_pa_pav_closure
previous_closure: docs/tw_portfolio_decision_model/POLICY_PAV2_ACTION_VALUE_RANKER_REPAIR_REVIEW_AND_ROUTE_CLOSURE_CN.md
base_signal_first: frozen_qlib_2018_2022
policy_train_valid_test_required: true
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
no_frontend_default_switch: true
---

# Policy Episode / Trajectory Portfolio Policy 主线

## 0. 统筹结论

PAV2 repair 已关闭：

```text
docs/tw_portfolio_decision_model/POLICY_PAV2_ACTION_VALUE_RANKER_REPAIR_REVIEW_AND_ROUTE_CLOSURE_CN.md
route_conclusion = CLOSE_COUNTERFACTUAL_ACTION_VALUE_ROUTE_AT_PAV2
```

关闭原因不是合同失败，而是研究假设失败：

```text
1. validation 和 strict_test 均低于 baseline。
2. 最终 policy 退化为 keep_baseline_action / no_action。
3. 没有任何 buy_one / sell_one / switch_pair non-baseline action 被最终采用。
4. 单日 action value label 没有稳定转化为滚动组合 replay return。
```

因此后续不能继续：

```text
PAV2 无界调参
PAV3 constrained slate policy
PAV4 offline RL
```

新的 policy 主线改为：

```text
直接优化 replay episode / trajectory 的组合收益，而不是先预测单动作 value。
```

本主线仍只做只读研究，不进入生产默认、不接 broker、不输出目标仓位、不输出真实订单。

## 1. 目标

本主线要回答的问题：

```text
在不增强 qlib/LTR 信号、不改变模型 ranking 的前提下，
能否通过 episode-level portfolio policy，
在 qlib-only strict_test 上获得接近或超过 baseline 的 after-fee-tax return？
```

第一阶段只使用 qlib-only：

```text
signal_artifact = data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json
base_model_train_window = 2018-2022
policy_train_window = 2023-2024
policy_validation_window = 2025
policy_strict_test_window = 2026-01-01..2026-05-07
```

只有 qlib-only 路线证明 policy 有增量价值后，才允许另开 qlib+orthogonal LTR adapter 阶段。

## 2. 非目标

本主线不是：

```text
1. qlib / LTR 信号增强。
2. 重新训练 qlib 或 LTR。
3. 继续 PAV2 action value ranker。
4. 直接上线 offline RL / PPO / CQL / IQL。
5. 通过降低参与度追求低回撤。
6. 输出 target_weight / target_position / quantity / broker order。
7. 切换 provider latest / accepted latest / frontend default。
8. 给出收益承诺。
```

本主线特别强调：

```text
return-first
```

收益率是第一目标。换手、回撤、费用、参与度是约束和诊断，不是主目标。

## 3. 当前 baseline 与失败事实

当前 qlib-only baseline 仍是第一对照：

```text
strategy baseline = top50_exit_one_worst_sell / equivalent readonly baseline replay
strict_test baseline net_return_after_fee_tax = 1.14173800
```

PAV2 repair 结果：

```text
validation baseline = 0.95376753
validation policy   = 0.84549802
validation excess   = -0.10826951

strict_test baseline = 1.14173800
strict_test policy   = 0.90317488
strict_test excess   = -0.23856312
```

最终动作分布：

```text
train:       no_action=4,   keep_baseline_action=477, buy/sell/switch=0
validation:  no_action=154, keep_baseline_action=88,  buy/sell/switch=0
strict_test: no_action=44,  keep_baseline_action=35,  buy/sell/switch=0
```

底层诊断：

```text
1. baseline 的收益来自持续参与和持续换仓。
2. PAV2 repair 的防守性 fallback 降低了参与度。
3. 单动作 value 没有解决组合路径依赖。
4. 单日动作可行，不等于整段 portfolio trajectory 更优。
5. 当前动作模型没有证明能稳定替换 baseline 的滚动决策。
```

因此新路线必须把优化单位从：

```text
single action row
```

改成：

```text
full replay episode / trajectory
```

## 4. 参考研究与本项目采用方式

执行者不得 freestyle。PE0 必须逐项读取并在执行报告中写 `Research Adoption Audit`。

| id | 研究 | 链接 | 可借鉴点 | 本项目采用 | 本项目不采用 / 暂缓 |
|---|---|---|---|---|---|
| R1 | FinRL: A Deep Reinforcement Learning Library for Automated Stock Trading in Quantitative Finance | https://arxiv.org/abs/2011.09607 | environment / agent / backtest 分层；交易成本、流动性、风险约束纳入环境；可复现实验 | 采用 environment-policy-replay 分层；采用交易成本显式进入 reward/replay；采用 baseline 对照和可复现 artifact | 不接 live trading；不输出真实订单；不照搬 FinRL 在线训练流程 |
| R2 | A Deep Reinforcement Learning Framework for the Financial Portfolio Management Problem / EIIE | https://arxiv.org/abs/1706.10059 | 组合状态、Portfolio-Vector Memory、显式 reward、交易成本、episode 式组合管理 | 采用 portfolio state / previous holdings / cost-aware reward 的思想；用于解释为什么要 episode-level objective | 不采用连续 target_weight；不采用 OSBL 在线随机训练；不采用 crypto 高频假设 |
| R3 | Simple statistical gradient-following algorithms for connectionist reinforcement learning / REINFORCE | https://link.springer.com/article/10.1007/BF00992696 | 直接最大化 episode return，而不是单步分类 label；用 rollout trajectory 的 return 形成 policy 更新信号 | 采用“优化 policy 参数以最大化 trajectory return”的概念；PE1 先用黑盒/网格/交叉熵搜索近似 | PE1 不做高方差 policy gradient；不做在线随机探索 |
| R4 | Proximal Policy Optimization, PPO | https://arxiv.org/abs/1707.06347 | clipped policy update、trajectory rollout、advantage 估计 | 只作为 PE3+ 深度 policy 的参考；若进入神经 policy，必须限制 policy update 并做 validation-only selection | PE1/PE2 不做 PPO；不允许 online interaction；不允许 strict_test 调参 |
| R5 | A Tutorial on the Cross-Entropy Method | https://people.smp.uq.edu.au/DirkKroese/ps/aortut.pdf | 通过采样参数、评估 episode objective、保留 elite 更新搜索分布 | PE1 采用为主要方法之一：对离散/连续 policy 参数做 simulation-in-the-loop search | 不把随机搜索结果直接生产化；必须 train/validation/test 分离 |
| R6 | Conservative Q-Learning, CQL | https://arxiv.org/abs/2006.04779 | offline RL 中对 OOD action 价值保守，控制分布外高估 | PE3+ 若启动 offline RL，采用 OOD action audit / conservative value 思想 | PE0-PE2 不做 CQL；PAV2 未通过前置 evidence，不能直接升级 |
| R7 | Implicit Q-Learning, IQL | https://arxiv.org/abs/2110.06169 | 避免显式查询数据外 action，适合 offline coverage 不足 | PE3+ 候选，仅在已生成足够 behavior/trajectory coverage 后作为对照 | PE0-PE2 不做 IQL；不把 offline RL 当作当前主线第一步 |
| R8 | Decision Transformer | https://arxiv.org/abs/2106.01345 | 将 return-conditioned trajectory 作为序列建模 | 只作为长期 diagnostic；用于分析高收益 trajectory 的行为模式 | 暂不训练；returns-to-go 有泄漏风险，必须先有严格 audit |
| R9 | Portfolio Choice with Transaction Costs: a User's Guide | https://arxiv.org/abs/1207.7330 | 交易成本会让最优组合出现 no-trade region / rebalancing tradeoff，不能只看毛收益 | 采用成本敏感 replay、turnover/cost sensitivity audit；把费用税费纳入 objective | 不把降低交易成本当作主目标；本项目仍 return-first |

本项目真正采用的是：

```text
FinRL 的环境/agent/backtest 分层
EIIE 的 portfolio state、previous holding、cost-aware reward
policy search 的 trajectory objective
cross-entropy / black-box optimization 的 simulation-in-the-loop 参数搜索
offline RL 文献的 OOD/action coverage 风险意识
交易成本文献的 cost-aware replay 与成本敏感性审查
```

本项目当前不采用：

```text
连续仓位权重
在线探索
PPO/CQL/IQL/Decision Transformer 直接训练
实盘交易接口
```

## 5. 新研究假设

PAV2 的假设是：

```text
learn f(state, action) -> action value
rank daily candidate actions
adapter converts selected action to rolling portfolio replay
```

这个假设已失败。

PE 主线的新假设是：

```text
Define a parameterized portfolio policy pi_theta.
Run pi_theta through the readonly replay engine over a full train/validation episode.
Select theta by validation net_return_after_fee_tax.
Evaluate once on strict_test.
```

核心变化：

```text
优化目标 = 整段组合 replay return
选择单位 = policy parameter set / episode behavior
审查单位 = train/validation/strict_test replay artifact
```

而不是：

```text
优化目标 = 单动作 label
选择单位 = 单日 top action
审查单位 = action value prediction metric
```

## 6. Policy Space v1

PE1 第一版必须采用可解释、参数化、离散 intent policy。不得直接上深度网络。

### 6.1 每日状态

允许的 state：

```text
date
current holdings from PortfolioState
candidate_rank
buy_score
raw_score
score_rank
full_qlib_rank
rank_delta / score_delta based only on past available signal
holding_age
holding_rank_now
holding_score_now
cash/full-slot status as replay state
recent market regime features if PIT-safe and declared
```

禁止的 state：

```text
future_return
forward_return
label
realized_pnl
future price
same-day unavailable data
replay outcome from current/future date
strict_test selection metric
```

### 6.2 每日动作

PE1 允许输出 intent-level action slate：

```text
no_action
keep_baseline_action
sell_k_weak_holdings
buy_k_top_candidates
switch_pairs: sell_i weak holding + buy_j strong candidate
```

第一版建议动作上限：

```text
max_sell_count in {1, 2, 3}
max_buy_count in {1, 2, 3}
max_switch_pair_count in {1, 2, 3}
candidate_k in {30, 50, 100, 150}
target_holding_count = follow current baseline or declared fixed value
```

输出仍必须是 `OrderIntentArtifact` intent：

```text
side = buy/sell/skip
instrument
reason_code
source_policy
```

不得包含：

```text
quantity
target_position
target_weight
execution_price
execution_date
broker_order_id
cash amount
```

### 6.3 参数化策略族

PE1 至少实现以下策略族，作为 trajectory policy search 的候选。

#### Family A: aggressive rank-capture policy

目标：提高参与度，避免 PA/PAV 旧线的过度 skip。

参数：

```text
candidate_k
sell_boundary_rank
buy_min_rank
max_sell_count
max_buy_count
min_holding_days
rank_improvement_threshold
score_improvement_threshold
```

行为：

```text
1. 持仓跌出 sell_boundary_rank，优先卖出。
2. 若有更强候选满足 rank/score improvement，允许 switch。
3. 每日最多多笔，但受 max_buy/sell 限制。
4. 优先保持满仓或接近 baseline 参与度。
```

#### Family B: switch-pair return capture policy

目标：不再只 block baseline，而是在满仓状态下主动做替换。

参数：

```text
weak_holding_rank_quantile
weak_holding_score_quantile
buy_candidate_rank_cutoff
pair_rank_gap_threshold
pair_score_gap_threshold
max_switch_pair_count
min_holding_days
```

行为：

```text
1. 从当前持仓中找弱持仓。
2. 从 qlib topK 中找强候选。
3. 满足 pair gap 时输出 sell+buy intent。
4. 以组合 replay return 选择参数，而不是单动作 label。
```

#### Family C: baseline-plus offensive override

目标：保留 baseline 持续参与能力，但允许更激进的额外替换。

参数：

```text
baseline_action_weight
override_rank_gap
override_score_gap
override_max_count
fallback_to_baseline
```

行为：

```text
1. baseline action 是默认可执行骨架。
2. 当 policy 判断存在明显更强替换时覆盖 baseline 的买入或卖出选择。
3. 不允许因为不确定而大规模 no_action。
```

#### Family D: regime-conditioned offensive policy

目标：只在 PIT-safe 市场状态下调整参与强度。

参数：

```text
regime_feature_set
risk_on_max_switch
risk_off_max_switch
risk_on_candidate_k
risk_off_candidate_k
```

行为：

```text
1. 使用仅由过去可得价格/市场宽度/波动构成的 regime feature。
2. risk-on 时提高 candidate_k 和 switch_count。
3. risk-off 时不默认退出市场，只降低过度换手。
```

Family D 只有在 PE0 证明 regime feature PIT-safe 后才能执行。

## 7. Objective 与约束

主目标：

```text
maximize validation net_return_after_fee_tax
```

严格对照：

```text
policy_validation_return >= baseline_validation_return
policy_strict_test_return >= baseline_strict_test_return
```

优先级：

```text
1. net_return_after_fee_tax
2. excess return vs baseline
3. participation ratio
4. action_count / fill_count
5. max_drawdown
6. turnover / fee / tax
```

约束：

```text
participation_ratio >= 0.85 of baseline on validation
action_count_ratio >= 0.80 of baseline on validation
no_action_ratio must not be the source of return improvement
turnover_ratio <= 2.00 of baseline unless validation excess return is clearly positive
max_drawdown must not be catastrophically worse than baseline
```

审查者必须注意：

```text
低换手、低费用、低回撤不能替代收益通过。
```

## 8. 数据切分与防泄漏

第一阶段固定：

```text
train = 2023-01-01..2024-12-31
validation = 2025-01-01..2025-12-31
strict_test = 2026-01-01..2026-05-07
```

使用原则：

```text
1. train 可用于搜索参数分布、生成候选 theta、做初筛。
2. validation 只能用于最终 policy/config 选择。
3. strict_test 只能最终评估一次，不得参与任何选择。
4. 不得用 strict_test 结果反向修参数。
5. 若 strict_test 失败，必须写 review/closure 或另开新 coordinator 文档，不能在同一路线继续试。
```

如果执行者需要多轮 PE1 search：

```text
只能在 train 内做 internal resampling / walk-forward。
validation 只能作为外层 selection。
strict_test 只 final-only。
```

## 9. Artifact 与合同

PE 主线必须复用模块化链路：

```text
ModelSignalArtifact
  -> EpisodicPolicyConfigArtifact
  -> PolicyTrajectoryDecisionArtifact
  -> OrderIntentArtifact
  -> ReplayResultArtifact
  -> PolicyEpisodeEvaluationArtifact
```

### 9.1 EpisodicPolicyConfigArtifact

至少包含：

```text
artifact_type = EpisodicPolicyConfigArtifact
schema_version
policy_family
policy_parameters
search_method
train_window
validation_window
strict_test_window
input_signal_artifact
forbidden_fields_audit
strict_test_used_for_selection=false
readonly_only=true
production_allowed=false
```

### 9.2 PolicyTrajectoryDecisionArtifact

至少包含：

```text
date
policy_family
policy_config_id
portfolio_state_hash
selected_action_slate
reason_code
candidate_count
selected_sell_count
selected_buy_count
selected_switch_count
baseline_action_reference_id, optional
fallback_reason, optional
```

不得包含：

```text
quantity
target_weight
target_position
execution_price
execution_date
broker_order_id
realized_pnl
future_return
```

### 9.3 PolicyEpisodeEvaluationArtifact

至少包含：

```text
split
policy_return
baseline_return
excess_return
action_count
baseline_action_count
participation_ratio
turnover
fee_tax
max_drawdown
selection_source
strict_test_used_for_selection
```

## 10. 阶段计划

## PE0: Episode Policy Contract And Research Design Freeze

目标：

```text
冻结 PE artifact schema、policy family、objective、search/evaluation protocol。
```

执行者必须：

```text
1. 读取本主线、PAV2 closure、项目宪法、ModelSignal/StrategyRule/OrderIntent/ReplayResult 合同。
2. 逐项读取 R1-R9 研究。
3. 写 Research Adoption Audit。
4. 设计 EpisodicPolicyConfigArtifact / PolicyTrajectoryDecisionArtifact / PolicyEpisodeEvaluationArtifact schema。
5. 设计 validator / golden sample 正负例。
6. 写 PE0 execution report。
```

PE0 不允许：

```text
训练模型
搜索参数
生成收益结论
跑 strict_test
接 frontend / Agent / provider / broker
```

PE0 通过条件：

```text
1. schema 完整。
2. forbidden field / forbidden action 定义完整。
3. research adoption audit 完整。
4. evaluator protocol 明确 train/validation/strict_test。
5. reviewer 能据此写 PE1 work doc。
```

## PE1: Qlib-only Simulation-in-the-loop Policy Search

目标：

```text
用 qlib-only signal，在 train/validation 上搜索参数化 episode policy。
```

推荐搜索方法：

```text
1. deterministic grid for small policy families
2. random search for wide parameter space
3. cross-entropy method for promising parameter ranges
```

搜索流程：

```text
1. 在 train replay 上评估候选 policy configs。
2. 过滤明显低参与、不可执行、越界配置。
3. 将候选 configs 在 validation replay 上评估。
4. 只用 validation net_return_after_fee_tax 选择最终 config。
5. strict_test 不运行或只在 reviewer 授权的 PE2 执行。
```

PE1 输出：

```text
data_tw/experiments/policy_episode_research/pe1_qlib_only_policy_search/
  manifest.json
  policy_config_candidates.csv
  train_replay_metrics.csv
  validation_replay_metrics.csv
  validation_selection_audit.csv
  participation_audit.csv
  forbidden_feature_audit.csv
  validator_report.json
  golden_samples_report.json
docs/tw_portfolio_decision_model/POLICY_PE1_QLIB_ONLY_POLICY_SEARCH_EXECUTION_REPORT_CN.md
```

PE1 通过条件：

```text
validation policy net_return_after_fee_tax >= validation baseline
participation_ratio >= 0.85
action_count_ratio >= 0.80
policy 不得靠 no_action/低参与获得表面收益
validator/golden samples pass
```

PE1 若 validation 失败：

```text
STOP_OR_REPAIR_WITH_COORDINATOR_DECISION
```

不得自动进入 PE2。

## PE2: Strict-test Final Replay

目标：

```text
对 PE1 validation 选出的唯一 final policy config，做 strict_test final-only replay。
```

PE2 执行者必须：

```text
1. 读取 PE1 review 的 final selected config。
2. 确认 strict_test_used_for_selection=false。
3. 对 baseline 和 policy 跑 strict_test readonly replay。
4. 输出 PolicyEpisodeEvaluationArtifact。
5. 写 PE2 execution report。
```

PE2 不允许：

```text
新增参数搜索
改 policy family
看 strict_test 后改阈值
合并多个 config ensemble
进入 deep RL
```

PE2 通过条件：

```text
strict_test policy net_return_after_fee_tax >= strict_test baseline
strict_test excess_return > 0
参与度不显著低于 baseline
收益不是由异常单日/单股集中贡献造成
```

如果 strict_test 低于 baseline：

```text
关闭 PE1/PE2 当前 policy family，写 closure review。
```

## PE3: Walk-forward Robustness And Concentration Audit

只有 PE2 通过后才允许进入。

目标：

```text
验证 PE2 不是偶然样本胜利。
```

必须做：

```text
1. rolling sub-window replay
2. monthly/quarterly excess return decomposition
3. symbol concentration audit
4. trade contribution audit
5. cost sensitivity audit
6. missing price / pending execution audit
```

PE3 通过条件：

```text
大多数子窗口不显著崩坏
收益不完全来自极少数交易或单一股票
费用/税费敏感性下仍接近或超过 baseline
```

PE3 不通过：

```text
不得进入 LTR adapter 或 deep RL。
```

## PE4: Optional Deep / RL Policy Research

只有 PE2 和 PE3 均通过后才允许讨论。

可选方向：

```text
1. behavior-constrained offline RL
2. CQL / IQL 对照
3. PPO-like policy gradient only in offline simulation sandbox
4. Decision Transformer diagnostic only
```

PE4 前置门槛：

```text
1. PE1/PE2 已证明 trajectory policy search 有正收益。
2. 有足够 action/trajectory coverage。
3. 已有 OOD action audit。
4. reviewer 明确批准进入 PE4。
```

PE4 仍然禁止：

```text
online RL with real market interaction
target_weight / target_position output
broker / quick-trade
production default switch
```

## PE5: Optional Qlib + Orthogonal LTR Adapter

只有 qlib-only PE2/PE3 通过后才允许。

目标：

```text
把同一 episode policy 框架适配到 qlib+orthogonal LTR ModelSignalArtifact。
```

注意：

```text
1. LTR 2023-2025 是训练窗口，不能把 2023-2025 LTR replay 当严格 OOS 策略证明。
2. 若要评估 qlib+LTR policy，需要另行定义无泄漏窗口或承认只是 strategy behavior diagnostic。
3. 不得把 qlib-only 通过结论直接迁移为 LTR 通过结论。
```

## 11. Reviewer 审查重点

审查者每轮必须检查：

```text
1. 是否仍在本阶段范围内。
2. 是否严格 train/validation/strict_test 分离。
3. strict_test 是否只 final-only。
4. 是否没有读取 forbidden future fields。
5. 是否没有输出 target_weight / target_position / quantity / broker order。
6. 是否没有 provider/latest/monitor/frontend default/Agent 扩权。
7. 是否 return-first，而不是用低换手/低回撤替代收益。
8. 是否 action participation 足够。
9. 是否 policy 真正产生 buy/sell/switch slate，而不是退化 no_action。
10. 是否引用并正确采用/拒绝相关研究。
```

## 12. 停止条件

任一情况出现，必须停止并回到 coordinator：

```text
1. validation 低于 baseline，执行者仍要求进 strict_test。
2. strict_test 被用于选择参数。
3. policy 收益来自大规模 no_action 或参与度塌缩。
4. 输出 target_position / target_weight / quantity / broker order。
5. 读取 future return / label / realized pnl 作为 feature。
6. 试图接 provider latest / monitor / frontend default / Agent / broker。
7. 未通过 validator/golden samples。
8. 未写 Research Adoption Audit。
9. 执行者自行把 PE1 改成 PPO/CQL/IQL/Decision Transformer。
```

## 13. Closure Criteria

本主线可以被判定成功的最低标准：

```text
1. qlib-only PE2 strict_test net_return_after_fee_tax > baseline。
2. PE3 robustness 不显示极端集中或单窗口偶然性。
3. 所有 artifact validator/golden samples pass。
4. 全程 readonly/simulation-only。
5. reviewer 明确 PASS_READY_FOR_NEXT_ROUTE。
```

本主线应被关闭的标准：

```text
1. PE1 validation 无法超过 baseline。
2. PE2 strict_test 无法超过 baseline。
3. policy 再次退化为低参与/no_action。
4. 多个 policy family 均显示组合轨迹优化无法打败 baseline。
```

## 14. PE0 执行者命令

```text
你是执行者。请启动 Policy Episode / Trajectory Portfolio Policy 主线 PE0。

必须读取：
1. docs/tw_portfolio_decision_model/POLICY_PE_EPISODIC_PORTFOLIO_POLICY_MAINLINE_CN.md
2. docs/tw_portfolio_decision_model/POLICY_PAV2_ACTION_VALUE_RANKER_REPAIR_REVIEW_AND_ROUTE_CLOSURE_CN.md
3. docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
4. docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
5. docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
6. docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
7. docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
8. docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md

本轮只做 PE0 contract/research/design freeze：
- 读取并总结 R1-R9 研究采用方式；
- 设计 EpisodicPolicyConfigArtifact、PolicyTrajectoryDecisionArtifact、PolicyEpisodeEvaluationArtifact schema；
- 设计 validator 和 golden samples；
- 设计 PE1 simulation-in-the-loop policy search protocol；
- 写 PE0 execution report。

本轮禁止：
- 训练模型；
- 搜索 policy 参数；
- 运行收益 replay 结论；
- 运行 strict_test；
- 进入 PPO/CQL/IQL/Decision Transformer；
- 输出 target_position/target_weight/quantity/order；
- 修改 provider/latest/monitor/frontend default/Agent/broker。

执行报告路径：
docs/tw_portfolio_decision_model/POLICY_PE0_EPISODIC_POLICY_CONTRACT_DESIGN_EXECUTION_REPORT_CN.md
```

## 15. PE0 审查者命令

```text
你是审查者。请审查 PE0 执行报告是否符合 Policy Episode / Trajectory Portfolio Policy 主线。

必须检查：
1. 是否完整读取主线、PAV2 closure、项目合同和 R1-R9 研究；
2. Research Adoption Audit 是否逐项说明 adopted/rejected/deferred/risk/PE_mapping；
3. 三类 artifact schema 是否完整且不含 forbidden fields；
4. validator/golden sample 设计是否覆盖正负例；
5. PE1 search protocol 是否严格 train/validation/strict_test 分离；
6. 是否没有训练、没有 replay 收益结论、没有 strict_test、没有 production/default 扩权；
7. 是否明确 return-first，且参与度 guardrail 防止旧路线低参与失败复现。

审查输出：
docs/tw_portfolio_decision_model/POLICY_PE0_EPISODIC_POLICY_CONTRACT_DESIGN_REVIEW_CN.md

如果通过，请在 review 文档中写 PE1 work document。
如果不通过，请写 PE0 repair work document。
不得自行授权 PE2/PE3/PE4。
```
