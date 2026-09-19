---
created_at: 2026-06-20
status: proposed_mainline
scope: portfolio_decision_optimizer_v1
roadmap_phase: P0_to_P5
readonly_only: true
simulation_only: true
not_order: true
not_target_position: true
not_investment_advice: true
recommended_first_phase: P0_contract_freeze
---

# TW Portfolio Decision Optimizer v1 主线设计

## 1. 结论

路线 P 的正确定位是：

```text
Portfolio Decision Optimizer v1
= 排序模型之后的只读组合动作策略层
```

它不是新 Qlib，不是新 LTR，不是 Entry rerank v2，也不是实盘交易系统。

当前项目已经冻结的产品基线是：

```text
Base Qlib:
e4_frozen_qlib_2018_2022

Orthogonal LTR:
e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025

Default strategy:
top50_exit_one_worst_sell
```

因此路线 P 不应继续回答：

```text
哪只股票排名更高？
```

而应回答：

```text
已有 E4 Qlib + Orthogonal LTR 排名后，
在当前模拟持仓、成本、现金、持有天数、市场状态和执行价可得性约束下，
今天是否值得动作，以及为什么不动作。
```

第一版推荐：

```text
不训练机器学习策略模型。
先实现可解释、可回放、可审查的规则化组合决策优化器。
```

这样可以避开当前最核心的数据切分隐忧：

```text
Qlib 已用 2018-2022；
LTR 已用 2023-2025；
若再训练一个监督动作模型，严格 OOS 只剩 2026H1，样本过少。
```

所以路线 P 的短期方案不是“再训练一个动作模型”，而是：

```text
P0 合同冻结
P1 规则化组合优化器
P2 只读 replay 与压力测试
P3 解释 artifact
P4 风险过滤输入
P5 才考虑监督动作模型
```

## 2. 已读取规范与本主线边界

本设计遵守：

```text
docs/tw_new_model_strategy_pre_rnd/TW_CURRENT_STATE_FUTURE_RND_ROADMAP_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md
docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md
docs/tw_portfolio_decision_model/PORTFOLIO_DECISION_MODEL_FUTURE_MAINLINE_CN.md
docs/references/portfolio_decision_model_papers/README_CN.md
configs/tw_product_artifact_registry.yaml
.agents/skills/tw-stock-new-strategy-onboarding/SKILL.md
```

路线 P 只能消费标准上游产物：

```text
ModelSignalArtifact
PortfolioState / PaperPortfolioState
StrategyRuleConfig
StrategyDependency YAML
MarketRegime / risk context, if declared
PriceStore readiness / execution readiness, if declared
```

路线 P 输出：

```text
OrderIntentArtifact
Readonly ReplayResultArtifact
DecisionExplanationArtifact
```

路线 P 禁止：

```text
real order
broker / quick-trade
target_position / target_weight
provider publish / refresh
accepted latest switch
monitor config / scan / alerts write
default model switch
default strategy switch
frontend default switch
future return / label / realized pnl as strategy input
same-day unavailable execution price
```

## 3. 文献阅读后的采用判断

### 3.1 交易成本：采用成本、税费、换手作为一等约束

参考：

```text
1904.08925 The impact of proportional transaction costs on systematically generated portfolios
本地文件：docs/references/portfolio_decision_model_papers/1904.08925_transaction_costs_systematic_portfolios.pdf
arXiv: https://arxiv.org/abs/1904.08925
```

该论文关注在不同交易频率、成分股数量、renewing frequency 下，比例交易成本如何影响系统化组合，并提出平滑交易成本的思路。

对路线 P 的采用：

```text
1. replay 必须报告扣费税后的 net_return_after_fee_tax。
2. 动作层必须显式约束 action_count、turnover_proxy、fee_and_tax。
3. 不允许只看毛收益或排名改善。
4. 引入 no_trade_buffer、turnover_budget、partial_adjustment。
5. 所有候选通过与否必须看费用税费敏感性。
```

不采用：

```text
不照搬论文组合类型；
不假设美股或一般系统组合结论直接迁移到台股；
不把交易成本平滑写成真实成交机制。
```

### 3.2 Decision-focused / SPO：采用稳定机制，不采用第一版机器学习动作模型

参考：

```text
2605.01176 Decision-Induced Ranking Explains Prediction Inflation and Excessive Turnover
本地文件：docs/references/portfolio_decision_model_papers/2605.01176_decision_induced_ranking_turnover.pdf
arXiv: https://arxiv.org/abs/2605.01176
```

该论文从 KKT 角度解释 SPO / decision-focused portfolio optimization 可能形成风险和交易成本调整后的边际分数排序，并实证讨论 prediction inflation、excessive turnover，以及 clipping、min-max rescaling、partial portfolio adjustment 等稳定机制。

对路线 P 的采用：

```text
1. 不把 buy_score 的微小差异直接转成交易动作。
2. 引入 confidence_gap：新候选必须显著优于当前最弱持仓才允许替换。
3. 引入 no_trade_buffer：排名变化不足以覆盖成本时不动作。
4. 引入 score clipping / score bucket：把过细分数差异离散化，减少分数膨胀误读。
5. 引入 partial_adjustment：优先小额模拟买入或部分减仓，不默认整笔买卖。
6. 引入 turnover control：每周/月动作预算和换手预算。
```

不采用：

```text
P1 不训练 SPO / DFL 模型。
P1 不让优化器直接输出连续仓位。
P1 不输出 target_weight / target_position。
P1 不让收益驱动的分数重标定进入默认产品路径。
```

### 3.3 Spatio-temporal momentum：采用组合上下文，不采用深度联合模型

参考：

```text
2302.10175 Spatio-Temporal Momentum: Jointly Learning Time-Series and Cross-Sectional Strategies
本地文件：docs/references/portfolio_decision_model_papers/2302.10175_spatio_temporal_momentum.pdf
arXiv: https://arxiv.org/abs/2302.10175
```

该论文统一时间序列动量与横截面动量，并指出同时考虑资产自身时间特征、横截面关系和组合中其他资产状态的价值；其实证也强调 turnover regularization 与交易成本情境。

对路线 P 的采用：

```text
1. 动作决策不能只看单股 rank。
2. 必须看当前组合中是否已有同类或高相关暴露。
3. 必须看持仓自身趋势、持有天数、回撤和未实现盈亏状态。
4. 后续可以把行业集中度、主题集中度、相关性近似纳入组合风险审计。
5. replay 必须报告 symbol turnover concentration 和 PnL concentration。
```

不采用：

```text
P1 不实现神经网络 spatio-temporal model。
P1 不训练跨资产深度模型。
P1 不把复杂模型作为通过标准。
```

### 3.4 市场状态：采用分段审计和保守 gate，不声称 regime gate 已验证

参考：

```text
1707.05552 Wax and wane of the cross-sectional momentum and contrarian effects
本地文件：docs/references/portfolio_decision_model_papers/1707.05552_momentum_contrarian_market_conditions.pdf
arXiv: https://arxiv.org/abs/1707.05552
```

该论文说明横截面 momentum / contrarian 效应会随市场状态变化，且机会会 wax and wane。

对路线 P 的采用：

```text
1. replay 必须按 normal / caution / risk_off 分段。
2. risk_off 只能先作为保守动作门槛，不作为已验证 alpha gate。
3. risk_off 时提高新进门槛，减少替换数量，优先 no_action / manual_review_required。
4. 只在单一 normal regime 获胜，不得默认化。
```

不采用：

```text
不声称历史 Phase2B/Phase2C regime gate 已通过。
不把市场状态直接当买卖信号。
不把中国市场论文结果直接迁移成台股交易规则。
```

### 3.5 Context-aware LTR 与 FinRL：只作为后置研究，不进入 P1

参考：

```text
2105.10019 Enhancing Cross-Sectional Currency Strategies by Context-Aware Learning to Rank with Self-Attention
2011.09607 FinRL: A Deep Reinforcement Learning Library for Automated Stock Trading
```

采用：

```text
Context-aware LTR 支持“同一排序在不同市场上下文中意义不同”。
FinRL 支持状态、动作、奖励、交易成本、流动性和风险厌恶的工程拆分。
```

不采用：

```text
P1 不做 Transformer reranker。
P1 不做 RL。
P1 不接 broker。
P1 不输出自动交易动作。
```

## 4. P 主线分阶段方案

### 4.1 Phase P0：合同冻结

目标：

```text
冻结 Portfolio Decision Optimizer v1 的输入、输出、动作集合、费用税费、执行价 gate、replay 指标和禁止事项。
```

不做：

```text
不写策略实现代码；
不训练模型；
不生成正式 artifact；
不跑收益筛选；
不改默认模型/策略/前端/latest。
```

P0 输出文档：

```text
docs/tw_portfolio_decision_model/PHASEP0_CONTRACT_FREEZE_WORK_REPORT_CN.md
```

P0 必须冻结：

```text
strategy_rule: portfolio_decision_optimizer_v1
dependency yaml draft
required core fields
required extensions
action enum
reason code enum
execution_price_mode = next_open
blocked_execution_price_unavailable
OrderIntentArtifact schema extension plan
ReplayResultArtifact metrics extension plan
DecisionExplanationArtifact draft
validator plan
golden sample plan
```

### 4.2 Phase P1：规则化组合优化器

目标：

```text
实现可解释、可回放、可审查的规则化动作决策。
```

P1 不得一次性做成“大保守策略”。P1A 先完成合同脚手架和 validator gate；P1B 开始实现时，必须以当前默认策略 `top50_exit_one_worst_sell` 为骨架，逐项加入规则并做 ablation。

原因：历史上简单降低换手或过度保守的策略容易牺牲收益。路线 P 的目标不是“少交易”，而是“只过滤低价值动作，不阻断默认策略的强信号”。

P1A：

```text
只做 StrategyDependency、多输入来源边界、validator、golden sample。
不实现完整策略。
不生成正式 OrderIntentArtifact / ReplayResultArtifact。
```

P1B 候选规则：

```text
no_trade_buffer
confidence_gap
score_bucket_or_clipping
min_holding_days
partial_adjustment
turnover_budget
risk_off_conservative_gate
position_risk_gate
execution_price_gate
```

推荐动作集合：

```text
no_action
add_observation_candidate
simulated_buy_small
simulated_reduce_partial
simulated_exit_full
keep_existing_position
manual_review_required
blocked_execution_price_unavailable
```

落到现有 `OrderIntentArtifact` 时的映射：

```text
simulated_buy_small -> intent_action=buy, intent_reason=simulated_buy_small
simulated_reduce_partial -> intent_action=sell, intent_reason=simulated_reduce_partial
simulated_exit_full -> intent_action=sell, intent_reason=simulated_exit_full
keep_existing_position -> intent_action=hold
no_action / add_observation_candidate / manual_review_required / blocked_* -> intent_action=skip
```

注意：

```text
OrderIntent 不得包含 execution_price、cash、NAV、fee、tax、PnL。
部分减仓的实际数量不得由策略层写入 OrderIntent；
若需要部分动作，必须先在 P0/P1 扩展合同，明确它仍是 simulation-only intent。
```

P1B 推荐 ablation 顺序：

```text
baseline:
  top50_exit_one_worst_sell

P1B-A:
  baseline + execution_price_gate
  只验证 next_open 缺失时 pending/block，不改变正常买卖逻辑。

P1B-B:
  baseline + tiny no_trade_buffer
  只阻止排名或分数差极小、费用税费后不值得的换仓。

P1B-C:
  baseline + confidence_gap
  新候选必须显著优于当前最弱持仓才允许替换。

P1B-D:
  baseline + min_holding_days with exception
  短持有原则上不卖，但跌出 top50 很深或风险明确时允许例外。

P1B-E:
  baseline + turnover_budget
  只在当周/当月动作过多时暂停低置信替换，不暂停强信号替换。

P1B-F:
  baseline + risk_off raised threshold
  risk_off 只提高弱信号门槛，不全面禁买。

P1B-G:
  baseline + partial_adjustment
  仅在 OrderIntent 合同支持 simulation-only partial intent 后启动。
```

每个 ablation 必须单独输出 replay 与审查结论；不得一次性叠加所有 gate 后只报告一个总结果。

### 4.3 Phase P2：只读 replay 与压力测试

目标：

```text
用同口径 replay 验证动作质量、成本、换手、回撤和解释性。
```

对照组：

```text
default: top50_exit_one_worst_sell
candidate: portfolio_decision_optimizer_v1
optional diagnostic: phase1c_ltr_turnover_controlled_daily, if already readonly artifact exists
```

必须报告：

```text
net_return_after_fee_tax
gross_return
max_drawdown
action_count
buy_count
sell_count
skip_count
no_action_days
blocked_days
turnover_proxy
fee_and_tax
average_holding_days
median_holding_days
regime_segment_metrics
yearly_metrics
rolling_3m_metrics
rolling_6m_metrics
PnL concentration
symbol turnover concentration
missing_next_open_count
execution_block_count
```

通过标准：

```text
不要求每个窗口都赢默认策略。
收益提高但换手、费用或回撤显著恶化，不通过。
只在单一 normal regime 获胜，不得默认化。
必须证明动作次数、换手、回撤或用户解释性至少一项稳定改善。
必须保持 readonly / simulation-only。
```

### 4.4 Phase P3：DecisionExplanationArtifact

目标：

```text
把动作原因变成可展示、可审查的解释 artifact。
```

解释字段：

```text
decision_date
portfolio_state_asof
instrument
decision_status
primary_reason_code
secondary_reason_codes
candidate_rank
buy_score_bucket
current_holding_flag
holding_days
rank_gap_vs_weakest_holding
cost_gate_status
turnover_budget_status
regime_status
execution_price_status
readonly_disclaimer
not_investment_advice
```

前端/Agent 可回答：

```text
为什么今天不动作？
为什么排名高但暂缓？
为什么进入人工复盘？
为什么 pending/block？
```

不得回答：

```text
应该买多少仓位；
目标仓位是多少；
现在是否下单；
能赚多少；
上涨概率是多少。
```

### 4.5 Phase P4：Risk Filter 接入

目标：

```text
把风险标签作为动作约束或解释输入，而不是新排序模型。
```

允许：

```text
risk tag -> manual_review_required
risk tag -> raise confidence_gap
risk tag -> block simulated_buy_small
risk tag -> keep but review
```

禁止：

```text
risk tag 直接变成卖出建议；
risk tag 直接改变 qlib top50 boundary；
risk tag 直接训练新模型；
risk tag 直接默认前端推荐。
```

### 4.6 Phase P5：监督动作模型，后置且必须重新审查

P5 才考虑：

```text
Supervised Portfolio Action Model
```

它不是近期任务。启动前必须满足：

```text
P1 规则化动作层稳定；
P2 replay 多窗口证据充分；
P3 解释 artifact 稳定；
P4 风险标签 PIT-safe；
有严格 nested OOS 数据切分方案。
```

## 5. 数据切分与“训练窗口交叉”问题

### 5.1 核心问题

当前产品模型训练历史为：

```text
Qlib: 2018-2022
Orthogonal LTR: 2023-2025
```

如果再训练监督动作模型，直觉上可用严格 OOS 只有：

```text
2026H1
```

这确实太少，不足以训练可靠机器学习动作模型。

### 5.2 哪些交叉是允许的

允许：

```text
1. 用 2023-2025 的已产出 ModelSignalArtifact 做规则化策略 replay。
2. 用 2023-2025 做实现诊断、字段覆盖、费用税费压力测试。
3. 用 2023-2025 做非收益调参的工程校准，例如 max action count、缺失价 block 行为。
4. 用 2026H1 做严格 forward readonly acceptance。
```

但必须标注：

```text
2023-2025 replay 对 Orthogonal LTR 不是严格模型 OOS；
它可以作为策略工程诊断和 replay 稳定性证据，
不能单独作为“机器学习动作模型有效”的 OOS 收益证据。
```

### 5.3 哪些交叉不允许

不允许：

```text
1. 用 2023-2025 replay 收益训练动作模型，再用同一窗口宣称策略 OOS。
2. 用 2018-2022 的 qlib in-sample 信号训练动作模型，再宣称对当前产品严格有效。
3. 用 LTR 训练期内的收益标签调动作模型阈值，再把 2023-2025 当 validation。
4. 用 replay realized pnl、future return、future label 作为策略当日输入。
```

### 5.4 推荐方案 A：近期采用，无需重训模型

推荐近期采用：

```text
规则化 Portfolio Decision Optimizer v1
```

原因：

```text
1. 不训练动作模型，所以不存在消耗 2026H1 训练样本的问题。
2. 规则参数先来自合同、费用税费、动作上限和文献启发，而非收益拟合。
3. 2023-2025 可用于 replay 压力测试和行为审计。
4. 2026H1 可作为严格 forward acceptance。
5. 通过标准不只看收益，重点看换手、费用、回撤、解释性和 block 行为。
```

该方案不需要重训 Qlib 或 LTR。

### 5.5 方案 B：若未来要监督动作模型，做 nested OOS 研究

如果 P5 必须训练动作模型，应使用 nested OOS，不得直接拿产品模型的 in-sample 信号训练。

示例设计：

```text
Fold 1:
  qlib_train: 2018-2020
  ltr_train: 2021
  action_train: 2022
  action_valid: 2023
  final_test: 2024

Fold 2:
  qlib_train: 2018-2021
  ltr_train: 2022
  action_train: 2023
  action_valid: 2024
  final_test: 2025

Fold 3:
  qlib_train: 2018-2022
  ltr_train: 2023
  action_train: 2024
  action_valid: 2025
  final_test: 2026H1
```

缺点：

```text
每个 fold 的 LTR 训练期较短；
需要重新生成一套研究用 qlib/LTR OOS signals；
不能直接等同当前 strict E4 产品线；
工程成本高。
```

优点：

```text
能产生更多严格外推动作样本；
可审查每个层级的训练/验证/测试边界；
适合 P5 监督动作模型研究。
```

### 5.6 方案 C：重切产品训练窗口，仅作为中期研究，不建议近期做

如果未来坚持“监督动作模型必须进入主线”，可以重切：

```text
Qlib train: 2018-2021
LTR train: 2022-2023
Action train/calibration: 2024
Validation: 2025
Final forward: 2026
```

但这会改变当前产品基线，必须单独开新模型/新策略联合主线，重新审查：

```text
Qlib 性能是否下降；
LTR 是否仍有增量；
Action model 是否真的弥补排序层损失；
默认模型/策略是否需要切换；
是否值得牺牲当前 strict E4 baseline。
```

近期不建议这样做。

### 5.7 2018 年前数据是否可用

可以研究，但不能直接假设可用。

使用 2018 年前数据需要先确认：

```text
1. 当前 150 universe 在 2018 年前的覆盖；
2. 价格、复权、停牌、下市和流动性质量；
3. 特征 available_at 和 PIT 合同；
4. 是否与当前 Yahoo / FinMind / qlib provider 口径一致；
5. 是否足够代表 2023-2026 台股结构。
```

如果这些条件不满足，2018 年前数据只能用于：

```text
鲁棒性压力测试；
历史情境分析；
规则参数敏感性检查；
```

不能直接作为当前产品动作模型训练证据。

## 6. P1 规则设计草案

### 6.1 输入

ModelSignalArtifact core fields：

```text
date
instrument
candidate_rank
buy_score
raw_score
score_rank
full_qlib_rank
signal_asof
available_at
source_artifact
source_model_artifact
```

PortfolioState：

```text
asof_date
instrument
quantity
cost_basis
current_holding_flag
holding_days
unrealized_return
max_drawdown_since_entry
current_weight_simulated
```

Strategy config：

```text
target_holding_count
candidate_k
max_daily_buy_count
max_daily_sell_count
min_holding_days
confidence_gap
no_trade_buffer
turnover_budget_daily
turnover_budget_weekly
max_single_name_weight
execution_price_mode
```

Market/risk context：

```text
market_regime
TWII_ret20
TWII_ret60
market_drawdown60
market_volatility20
market_breadth20
position_risk_status
liquidity_proxy
```

### 6.2 决策顺序

推荐顺序：

```text
1. Validate signal_asof / available_at。
2. Validate portfolio_state.asof_date <= signal_date。
3. Validate next_open readiness；不可用则 blocked_execution_price_unavailable。
4. 标记当前持仓是否跌出 qlib top50。
5. 找出可替换最弱持仓：full_qlib_rank 最差或 risk tag 最差。
6. 找出候选新进标的：top50 内未持有，buy_score 排名前列。
7. 应用 min_holding_days。
8. 应用 confidence_gap / no_trade_buffer。
9. 应用 turnover_budget。
10. 应用 risk_off_conservative_gate。
11. 应用 position_risk_gate。
12. 输出 buy/sell/hold/skip intent 和 reason code。
13. 输出 strategy_decision_audit。
```

### 6.3 简化伪代码

```text
if next_open_not_ready:
    skip all executable actions with reason blocked_execution_price_unavailable

if market_regime == risk_off:
    confidence_gap = confidence_gap * risk_off_multiplier
    max_daily_buy_count = min(max_daily_buy_count, risk_off_buy_cap)

weakest_holding = select_worst_holding_by_full_qlib_rank_or_risk()
best_candidate = select_best_unheld_candidate_by_buy_score()

if no weakest_holding and portfolio_is_full:
    no_action

if weakest_holding.holding_days < min_holding_days and not severe_risk:
    keep_existing_position

score_gap = bucket(best_candidate.buy_score) - bucket(weakest_holding.buy_score)

if score_gap < confidence_gap:
    no_action with reason insufficient_score_gap

if estimated_turnover_after_action > turnover_budget:
    no_action with reason turnover_budget_exceeded

if candidate_has_position_risk:
    add_observation_candidate or manual_review_required

else:
    simulated_exit_full or simulated_reduce_partial for weakest_holding
    simulated_buy_small for best_candidate
```

## 7. 实验设计

### 7.1 实验组

实验组必须以默认策略为共同骨架：

```text
E0: default top50_exit_one_worst_sell
E1: E0 + execution_price_gate
E2: E1 + tiny no_trade_buffer
E3: E2 + confidence_gap
E4: E3 + min_holding_days with exception
E5: E4 + turnover_budget
E6: E5 + risk_off_conservative_gate
E7: E6 + partial_adjustment, if contract supports partial intent
```

每一步只能增加一个机制，避免混合后无法归因。若 E2-E7 任一规则导致收益下降，必须证明回撤、费用税费、动作质量或解释性有明确补偿；否则该规则不得进入下一阶段。

### 7.2 时间窗口

用途区分：

```text
2023-2025:
  行为 replay、压力测试、字段覆盖、费用税费敏感性。
  不能作为 LTR 严格 OOS 收益证明。

2026H1:
  strict forward acceptance。
  样本少，所以不用于训练，只用于只读验收。
```

若需要更强证据：

```text
另开 nested OOS 研究，重新生成研究用 qlib/LTR signals。
```

### 7.3 指标

收益类：

```text
gross_return
net_return_after_fee_tax
max_drawdown
daily_return_volatility
```

动作类：

```text
action_count
buy_count
sell_count
skip_count
no_action_days
blocked_days
average_holding_days
median_holding_days
turnover_proxy
fee_and_tax
```

稳定性：

```text
yearly_metrics
rolling_3m_metrics
rolling_6m_metrics
regime_segment_metrics
PnL concentration
symbol turnover concentration
single_day_PnL_concentration
```

安全：

```text
missing_next_open_count
execution_block_count
forbidden_field_audit
forbidden_action_audit
readonly_only
not_order
not_target_position
not_investment_advice
```

### 7.4 参数选择原则

允许：

```text
用文献和业务约束给出少量固定参数；
做 sensitivity grid；
报告所有网格结果；
不按收益挑唯一最优参数进入默认。
```

禁止：

```text
在 2023-2025 上按收益调参后，把同窗口当验证；
只展示最优网格；
忽略换手、费用、回撤；
把 2026H1 小样本胜出包装成稳定 alpha；
把“更保守、换手更低”本身当作通过理由；
用保守 gate 阻断明显跌出 top50 的弱持仓退出或优势显著的新候选替换。
```

## 8. 推荐 P0 执行者任务

```text
你是执行者。请准备 TW Portfolio Decision Optimizer v1 的 P0 合同冻结工作文档，只做计划和边界确认，不实现代码、不训练模型、不生成正式 artifact、不修改默认模型/默认策略/前端默认/latest 路径。

必须读取并遵守：
- docs/tw_portfolio_decision_model/PHASEP_PORTFOLIO_DECISION_OPTIMIZER_MAINLINE_CN.md
- docs/tw_new_model_strategy_pre_rnd/TW_CURRENT_STATE_FUTURE_RND_ROADMAP_CN.md
- docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
- docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
- docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
- docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
- docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md
- docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md
- docs/references/portfolio_decision_model_papers/README_CN.md
- .agents/skills/tw-stock-new-strategy-onboarding/SKILL.md

P0 文档必须冻结：
- strategy_rule 与 dependency yaml draft；
- 输入字段；
- PortfolioState 字段；
- 动作集合与 OrderIntent 映射；
- reason code；
- fee/tax/replay 指标；
- next_open execution price gate；
- validator/golden sample；
- 禁止事项；
- 数据切分与不可作为 OOS 证据的窗口说明。

完成后提交：
docs/tw_portfolio_decision_model/PHASEP0_CONTRACT_FREEZE_WORK_REPORT_CN.md
```

## 9. 推荐审查者任务

```text
你是审查者。请审查 P0 是否只冻结合同，未实现代码、未训练模型、未生成正式 artifact、未修改默认路径。

重点审查：
1. 是否承认当前 baseline 是 E4 Qlib + Orthogonal LTR；
2. 是否把路线 P 定位为组合动作层，不是排序层；
3. 是否没有重启 Entry rerank v2；
4. 是否禁止 target_position / target_weight；
5. 是否禁止 broker / order / quick-trade；
6. 是否保留 next_open missing => pending/block；
7. 是否没有把 2023-2025 LTR 训练期 replay 当严格 OOS；
8. 是否没有训练监督动作模型；
9. 是否给出 validator/golden sample 计划；
10. 是否使用 project-local tw-stock-new-strategy-onboarding skill。
```

## 10. 最终建议

路线 P 应先做：

```text
规则化 Portfolio Decision Optimizer v1
```

不应先做：

```text
监督动作模型
SPO / DFL 动作模型
Transformer / Graph model
Offline RL
重训 Qlib / LTR 以挤出动作模型训练集
```

训练窗口问题的合理处理是：

```text
近期不训练动作模型，因此不需要牺牲当前 E4 Qlib + Orthogonal LTR。
用 2023-2025 做行为压力测试，用 2026H1 做严格 forward readonly acceptance。
如果未来必须训练动作模型，再开 P5 nested OOS 或重切模型窗口研究。
```

一句话：

```text
路线 P 的第一性目标不是多训练一个模型，
而是让已有排序结果在模拟持仓、成本、换手、风险和执行价约束下，
形成可解释、可回放、低误读风险的今日动作决策。
```
