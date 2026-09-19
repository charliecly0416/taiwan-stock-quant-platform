---
created_at: 2026-06-20
status: coordinator_roadmap
scope: future_model_strategy_rnd_after_strict_e4_orthogonal_ltr
baseline: strict_e4_qlib_plus_orthogonal_ltr
recommended_next_mainline: portfolio_decision_optimizer_v1
roadmap_type: multi_mainline_handoff_for_new_coordinator
---

# 基于当前项目现况的新模型新策略后续研发路线

## 1. 结论

以前的论文方向文档提出过：

```text
qlib baseline
-> LTR reranker
-> regime gating
-> turnover-controlled portfolio layer
```

这条路线在当时是合理的。但按当前项目状态看，第一段已经不能再当作“下一步”：

```text
当前产品线已经是 E4 Qlib + Orthogonal LTR。
```

当前 registry 已冻结：

```text
Base Qlib:
e4_frozen_qlib_2018_2022

Orthogonal LTR:
e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025

Default strategy:
top50_exit_one_worst_sell
```

因此，后续不应再把“做一个 LTR reranker”作为主线。真正值得发展的方向应从：

```text
继续优化排序层
```

转向：

```text
用现有排序结果 + 当前模拟持仓 + 成本 + 市场状态，决定今天是否动作、动作多大、为什么不动作。
```

推荐下一条主线：

```text
TW Portfolio Decision Optimizer v1
```

第一阶段不是强化学习，也不是 Transformer，而是：

```text
可解释、可回放、可审查的规则化组合决策优化器
```

它解决的问题不是“哪只股票排名更高”，而是：

```text
在当前已经有 Qlib + Orthogonal LTR 排名的前提下，
今天是否值得为了新排名付出换仓成本、税费、风险和用户理解成本。
```

## 2. 当前真实项目状态

### 2.1 产品默认模型已经收敛

来自：

```text
configs/tw_product_artifact_registry.yaml
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_daily_update_productization/PHASEYZ_STRICT_E4_PRODUCTIZATION_FINAL_SUMMARY_CN.md
docs/tw_modular_daily_update_productization/PHASEYZ4_FINAL_CLOSURE_SUMMARY_FOR_COORDINATION_CN.md
```

当前只保留两个产品化模型：

```text
Model A:
e4_frozen_qlib_2018_2022

Model B:
e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
```

含义：

```text
Model A 使用 E1 frozen qlib，对当前 150 universe 打分。
Model B 使用 Model A 的 qlib top50，再用 E3 orthogonal LTR 对 top50 重排序。
```

当前产品化路径不得再默认使用：

```text
e4_frozen_qlib_2023_2025_ltr
fresh_qlib_adaptive
fresh_qlib_2025_ltr
P3 / O4 / bridge / frozen fresh 2025 LTR
```

这意味着：旧文档中“下一步做 LTR baseline / LambdaMART”的建议已经过时。

### 2.2 正交 LTR 不是空想，已经进入产品线

当前 LTR 语义已经被宪法固定：

```text
Qlib top50 定义候选与卖出边界。
LTR 只在 Qlib top50 内重排买入顺序。
LTR 不改变 Qlib top50 的退出边界。
```

这条边界非常重要。后续任何模型若想改变：

```text
universe
candidate boundary
sell boundary
multi-horizon risk
portfolio action
```

都不能伪装成“只是一个 LTR 字段”。必须新建合同、新建 artifact、新建审查 gate。

### 2.3 LTR 相关策略验证已经收口

来自：

```text
docs/tw_ltr_strategy_validation/PHASEV4_FINAL_REVIEW_AND_CLOSURE_CN.md
```

结论：

```text
LTR strategy validation closed.
Optional simulation strategy accepted as readonly, optional, non-default, non-trading product surface.
Top50 adaptive score remains the default baseline.
```

接受范围只包括：

```text
phase1c_ltr_simple_daily
phase1c_ltr_turnover_controlled_daily
```

作为：

```text
只读
可选
模拟
非默认
非交易
```

不得继续在该主线追加：

```text
策略调优
新模型
新数据源
默认化
前端推荐化
交易化
```

所以后续不能说“我们还没有做 LTR”。更准确的说法是：

```text
LTR 已经做过、验证过、产品化收口过；
下一步必须回答 LTR 排名之后的组合动作问题。
```

### 2.4 旧的 Entry Decision Model v1 已失败归档

来自：

```text
docs/tw_decision_model/PHASE2C_FINAL_REVIEW_CN.md
```

结论：

```text
Entry Model v1 不建议继续。
pass_phase3_gate=false。
archive_entry_model_v1_failed=true。
```

失败原因：

```text
没有稳定超过 qlib rank。
binary label 与排序目标不匹配。
ensemble 可能稀释 regression 的少量有效信号。
技术、流动性、大盘特征更像风险解释，而不是稳定重排信号。
```

这对后续路线有直接影响：

```text
不要再启动一个“Entry rerank 模型 v2”作为第一优先级。
```

更合理的迁移是：

```text
把技术、流动性、大盘、正交规则用于风险过滤、动作门槛和人工复盘解释。
```

### 2.5 正交规则探索也不能直接训练成模型

来自：

```text
docs/tw_decision_model_orthogonal/PHASE2D_ORTHOGONAL_RULE_CLOSURE_REPORT_CN.md
```

结论：

```text
orthogonal_rule_exploration_closed=true
manual_rule_cards_frozen=true
phase3_allowed=false
risk_filter_model_training_allowed=false
requires_user_decision_for_new_direction=true
```

这些规则卡可以进入：

```text
人工复盘解释
风险提示
动作约束的候选依据
```

但不能自动进入：

```text
新模型训练
前端/API 默认展示
provider/latest
交易链路
```

### 2.6 fresh / orthogonal fresh 研究给出的教训

来自：

```text
docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ4_ORTHOGONAL_FRESH_QLIB_DECISION_REVIEW_CN.md
docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC4_DECISION_REVIEW_CN.md
docs/tw_qlib_oos_ltr_stacking/PHASET2R_REVIEW_CONCLUSION_CN.md
```

关键结论：

```text
Orthogonal Fresh Qlib 不优于 fresh qlib baseline。
Frozen Fresh Qlib + Orthogonal LTR clean stacking 不优于 frozen fresh qlib baseline。
OOS LTR stacking 在特定 final normal regime 中有高收益信号，但 validation 稳健性不足、回撤恶化、低换手候选失败、贡献集中风险仍在。
```

这说明：

```text
继续在排序层堆新 qlib / 新 LTR / 新 stacking，边际收益不确定，且容易被单一市场阶段误导。
```

后续排序层研究仍可做，但不应成为第一主线。

## 3. 后续研发的核心判断

当前最有价值的问题不是：

```text
能不能再训练一个更强的排序模型？
```

而是：

```text
已有 Qlib + Orthogonal LTR 排名之后，今天是否应该动作？
如果动作，是买、卖、减仓、保留，还是不动作？
动作幅度是否值得覆盖手续费、交易税、滑点和回撤风险？
为什么这次排名变化不足以换仓？
```

排序层回答：

```text
哪只股票在今天的候选池里更有吸引力。
```

组合决策层回答：

```text
在我现在持有什么、成本多少、现金多少、风险多少的情况下，今天要不要动。
```

这两个问题不同。当前项目已经有排序层，因此下一步应补组合决策层。

## 4. 推荐主线：TW Portfolio Decision Optimizer v1

### 4.1 主线目标

新增一个只读组合决策优化器，消费现有标准产物：

```text
ModelSignalArtifact
ReadonlyStrategySnapshot
PaperPortfolioState / simulated portfolio state
PriceStore / execution readiness
MarketRegime features
fee / tax config
```

输出：

```text
OrderIntentArtifact
Readonly ReplayResultArtifact
DecisionExplanationArtifact
```

第一版只允许：

```text
只读历史模拟
模拟账户候选动作解释
不接真实 broker
不输出目标仓位
不切默认策略
不改前端默认
```

### 4.2 第一版不要做什么

第一版不要做：

```text
强化学习
Transformer
端到端 portfolio optimization
新 qlib 重训
新 LTR 重训
默认模型替换
默认策略替换
真实交易
目标仓位建议
```

原因：

```text
当前最缺的是动作层约束，不是更复杂的预测器。
规则化优化器更容易审查、解释、回放和失败归因。
```

### 4.3 第一版输入

模型/排序输入：

```text
candidate_rank
buy_score
raw_score
score_rank
full_qlib_rank
signal_asof
available_at
source_model_artifact
```

模拟组合状态：

```text
current_holdings
cash
cost_basis
holding_days
unrealized_return
max_drawdown_since_entry
current_weight_simulated
```

市场与风险状态：

```text
market_regime: normal / caution / risk_off
TWII_ret20
TWII_ret60
market_drawdown60
market_volatility20
market_breadth20
position_risk_status
liquidity_proxy
```

费用与执行约束：

```text
execution_price_mode = next_open
fee_rate
tax_rate
min_lot_policy
max_daily_buy_count
max_daily_sell_count
max_single_name_weight
min_holding_days
turnover_budget
```

### 4.4 第一版动作集合

第一版动作集合建议保持简单：

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

注意：

```text
这些是模拟/只读 intent，不是真实订单，不是目标仓位。
```

如果字段名容易被误读为交易指令，必须在合同里明确：

```text
not_order=true
not_target_position=true
simulation_only=true
readonly_only=true
```

### 4.5 第一版规则机制

建议先实现可解释规则，而不是学习模型：

```text
no_trade_buffer:
  新候选没有显著优于当前最弱持仓时，不动作。

confidence_gap:
  新候选 buy_score / rank 改善必须超过阈值才允许替换。

min_holding_days:
  未达到最短持有天数，除非风险信号明确，否则不退出。

partial_adjustment:
  优先部分减仓或小额模拟买入，不默认整笔买卖。

turnover_budget:
  每周/月最大模拟换手预算。

risk_off_gate:
  risk_off 时提高新进门槛，减少替换数量。

position_risk_gate:
  价格位置过热、流动性不足或数据质量差时，降级为人工复盘。

execution_price_gate:
  next_open 不可用时，禁止生成可应用模拟动作，只输出 pending/block。
```

### 4.6 第一版验收指标

不能只看收益率。必须同时报告：

```text
net_return_after_fee_tax
max_drawdown
action_count
turnover_proxy
fee_and_tax
average_holding_days
no_action_days
blocked_days
regime_segment_metrics
yearly_metrics
rolling_6m_metrics
PnL concentration
symbol turnover concentration
```

通过标准建议：

```text
不要求每个窗口都赢默认策略。
但必须证明动作次数、换手、回撤或用户可解释性至少有一项稳定改善。
收益若提高但回撤/换手显著恶化，不得通过。
只在单一 normal regime 获胜，不得默认化。
```

### 4.7 前端与 Agent 表达

前端不应展示复杂优化公式，只展示：

```text
今日模拟动作状态：不动作 / 小幅调整 / 风险复盘 / pending
为什么：排名差距、持仓天数、换手成本、市场状态、价格位置
影响：模拟现金变化、模拟持仓变化、预计手续费税费
边界：只读模拟，不构成交易建议
```

Agent 回答应围绕：

```text
为什么今天不动作？
为什么某只虽然排名高但暂缓？
为什么某只需要风险复盘？
当前 pending 是因为 next_open 不可用还是数据不齐？
```

不得回答：

```text
应该买多少仓位
目标仓位是多少
能赚多少
上涨概率多少
是否现在下单
```

## 5. 后续新模型 / 新策略研发大方向总览

下面不是只给“下一步”，而是给后续几个可连续推进的大方向。排序依据是：

```text
1. 是否补当前产品最短板；
2. 是否复用已经通过的 E4 Qlib + Orthogonal LTR 排序层；
3. 是否符合小白用户的今日策略 / 明日候选 / 模拟动作需求；
4. 是否容易审查、回放、解释；
5. 是否避免重复过去失败或已收口的 LTR / Entry rerank 路线。
```

推荐顺序：

```text
主线 1：Portfolio Decision Optimizer v1
主线 2：Risk Filter / Holding Risk Model
主线 3：PIT Data Foundation for FinMind / Fundamentals / Flow
主线 4：Fresh Qlib Base Model Window Sensitivity
主线 5：Supervised Portfolio Action Model
主线 6：Context-Aware Transformer / Graph Model Research
主线 7：Offline RL Portfolio Research
```

其中：

```text
主线 1-3 是最实用、最值得近期做的。
主线 4 是模型基座研究，可并行但不应抢主线。
主线 5 必须建立在主线 1 的规则化动作数据之上。
主线 6-7 是后置研究，不建议近期进入产品化。
```

## 6. 主线 1：Portfolio Decision Optimizer v1

### 6.1 定位

这是最优先主线。

它不是新排序模型，而是新策略 / 组合动作层：

```text
E4 Qlib + Orthogonal LTR 给出“哪些股票更值得排前面”。
Portfolio Decision Optimizer 回答“在当前模拟持仓和成本约束下，今天是否值得动作”。
```

### 6.2 要解决的问题

当前系统已经能给出候选和排名，但用户更关心：

```text
今天为什么不动作？
排名第一但是否值得换？
当前持仓是否要风险复盘？
如果换仓，手续费税费是否值得？
risk_off 时是否应该降低动作频率？
next_open 不可用时为什么不能应用模拟账户？
```

### 6.3 第一阶段做什么

第一阶段做规则化优化器，不训练模型，但不能一次性做成“大保守策略”。

执行顺序应拆开：

```text
P1A:
  先做 StrategyDependency、多输入边界、validator、golden sample。
  不实现完整策略，不生成正式 artifact。

P1B/P2:
  在 top50_exit_one_worst_sell 骨架上做增量 ablation。
  每次只增加一个规则机制，单独回放和审查。
```

候选机制包括：

```text
no_trade_buffer
confidence_gap
partial_adjustment
min_holding_days
turnover_budget
risk_off_gate
position_risk_gate
execution_price_gate
```

推荐 ablation 顺序：

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
```

输出标准产物：

```text
StrategyDependency
OrderIntentArtifact
Readonly ReplayResultArtifact
DecisionExplanationArtifact
```

### 6.4 参考论文

优先参考：

```text
1904.08925 The impact of proportional transaction costs on systematically generated portfolios
2605.01176 Decision-Induced Ranking Explains Prediction Inflation and Excessive Turnover
2302.10175 Spatio-Temporal Momentum
1707.05552 Wax and wane of cross-sectional momentum and contrarian effects
```

使用方式：

```text
1904.08925：证明交易成本和换手会改变净表现，支持 fee/tax/turnover 纳入策略目标。
2605.01176：证明分数直接驱动组合优化容易导致过度换手，支持 clipping / partial adjustment / no-trade buffer。
2302.10175：支持时间序列趋势、横截面排名和其他资产状态共同影响动作。
1707.05552：支持 market regime 影响动量/反转效果，不同市况不能机械执行同一动作。
```

### 6.5 不做什么

```text
不训练新 Qlib。
不训练新 LTR。
不做 RL。
不切默认模型。
不切默认策略。
不输出 target_position / target_weight。
不接 broker/order/quick-trade。
```

### 6.6 验收重点

```text
动作次数是否下降；
换手是否下降；
费用税费是否更可控；
回撤是否不恶化；
不动作解释是否清楚；
pending/block 是否正确；
是否仍完整保留 research-only / simulation-only 语义。
```

必须额外遵守：

```text
不能只因为“更保守、换手更低”就通过。
如果收益率下降，必须证明回撤、费用税费、动作质量或解释性有明确补偿。
如果收益下降且回撤/费用/解释性没有足够补偿，该规则不得进入下一阶段。
每个 gate 必须有单独 ablation 结果，不能一次性叠加后只报告总结果。
保守规则不得阻断明显有效的默认策略强信号：
  - 明显跌出 top50 的弱持仓退出；
  - 新候选优势显著且成本可覆盖的替换；
  - next_open 可用且合同允许的模拟动作。
```

## 7. 主线 2：Risk Filter / Holding Risk Model

### 7.1 定位

这是第二优先级主线。

它不是 Entry rerank v2。旧 Entry Model v1 已经失败归档，因此不能继续做“再重排一遍候选”的模型。

它应该改成：

```text
对高排名候选和当前持仓做风险标注 / 风险复盘优先级判断。
```

### 7.2 要解决的问题

```text
某股票虽然 qlib/LTR 排名高，但是否过热？
某股票是否有融资拥挤 / 法人流向冲突 / 技术转弱？
持仓股是否应该进入风险复盘？
是否应该降低新进观察优先级？
```

### 7.3 第一阶段做什么

先做规则 / 模型前审计，不直接训练：

```text
复用 Phase2C / Phase2D 冻结规则卡。
把技术、流动性、大盘、正交规则变成 risk tags。
输出 RiskTagArtifact 或 DecisionExplanationArtifact extension。
只做人工复盘解释和组合优化器输入，不直接改变排序。
```

可选标签：

```text
normal_observation
caution_observation
manual_review_required
exit_risk_review
data_quality_blocked
overheated_but_ranked_high
weakening_holding_review
```

### 7.4 参考论文

优先参考：

```text
2105.10019 Context-Aware Learning to Rank with Self-Attention
1707.05552 Wax and wane of cross-sectional momentum and contrarian effects
2302.10175 Spatio-Temporal Momentum
```

使用方式：

```text
2105.10019：吸收 context-aware / risk-off 下排序失真的思想，但不直接上 Transformer。
1707.05552：支持横截面效应受市场状态影响。
2302.10175：支持单股趋势要结合市场与其他资产状态解释。
```

### 7.5 不做什么

```text
不重启 Entry Model v1。
不把规则卡直接当训练标签。
不把 caution tag 当卖出建议。
不接前端默认推荐。
不改 OrderIntent，除非主线 1 已定义好消费方式。
```

### 7.6 验收重点

```text
风险标签是否 PIT-safe；
是否能解释已发生的风险复盘样例；
是否减少“高排名但明显过热/转弱”的误读；
是否只作为解释/过滤输入，不直接变成交易动作。
```

## 8. 主线 3：PIT Data Foundation for FinMind / Fundamentals / Flow

### 8.1 定位

这是数据地基主线，不是立即训练模型。

之前很多模型方向受限于：

```text
FinMind institutional / margin / revenue / valuation 的 PIT coverage 不足；
available_at / announcement_date 不可靠；
不能安全 join 到日频训练样本。
```

所以如果要追求真正的信息增量，必须先补数据合同。

### 8.2 要解决的问题

```text
法人买卖超什么时候可见？
融资融券数据什么时候可见？
月营收公告日是什么？
估值数据用哪个 available_at？
哪些字段 coverage 足够？
哪些字段只能解释，不能训练？
```

### 8.3 第一阶段做什么

```text
DataSource contract
PIT archive
available_at policy
coverage report
feature dictionary
leakage negative samples
golden samples
validator
小白数据说明
```

### 8.4 参考论文 / 文献

优先参考：

```text
Qlib: An AI-oriented Quantitative Investment Platform
QuantBench
AI in Quant survey
Meta-labeling / Advances in Financial Machine Learning
```

使用方式：

```text
Qlib：参考数据、模型、回测、组合的研究平台化流程。
QuantBench / AI in Quant survey：参考低信噪比、分布漂移、评估标准对齐和 benchmark 设计。
Meta-labeling：参考二阶段过滤/确认思想，但必须先有 PIT-safe 特征。
```

### 8.5 不做什么

```text
不一边补数据一边训练模型。
不使用 period date 代替 announcement_date。
不把 coverage=0 或 available_at 不明的字段放入训练。
不触发 provider publish / accepted latest switch。
```

### 8.6 验收重点

```text
字段 coverage 是否足够；
available_at 是否可审计；
PIT join 是否有负例验证；
是否能给出 2330 这类真实样例的数据时间线；
是否能被后续 Risk Filter / Portfolio Optimizer 安全消费。
```

## 9. 主线 4：Fresh Qlib Base Model Window Sensitivity

### 9.1 定位

这是模型基座研究主线。

它不替代当前 strict E4 产品线，也不和组合优化器混在一起。

它回答：

```text
fresh qlib 使用更短训练窗口是否更适合近期台股？
```

### 9.2 要解决的问题

```text
2017-2024 长窗口是否引入过旧市场结构？
2020-2024 / 2021-2024 / 2022-2024 是否更适合 2025-2026？
较短窗口是否牺牲稳定性？
```

### 9.3 第一阶段做什么

参考既有文档：

```text
docs/tw_fresh_qlib_training_window_sensitivity/FRESH_QLIB_TRAINING_WINDOW_SENSITIVITY_FUTURE_MAINLINE_CN.md
```

只允许改变：

```text
train_start
```

不允许改变：

```text
qlib params
universe
provider
label
validation/test
strategy rule
fee/tax
execution
```

### 9.4 参考论文

优先参考：

```text
Qlib paper
AI in Quant survey
QuantBench
Wax and wane of cross-sectional momentum and contrarian effects
```

使用方式：

```text
Qlib：基座模型训练与研究流程。
AI in Quant / QuantBench：分布漂移、时间切分、benchmark。
1707.05552：市场结构变化会影响横截面效应。
```

### 9.5 不做什么

```text
不加入正交数据。
不训练 LTR。
不调参。
不改默认模型。
不改前端/API。
不根据 test 最优直接默认化。
```

### 9.6 验收重点

```text
validation 与 untouched test 是否都支持；
是否分 2025H2 / 2026YTD / rolling 6m / regime；
收益提升是否伴随回撤/换手恶化；
是否有贡献集中；
是否只作为候选研究，不自动切换默认。
```

## 10. 主线 5：Supervised Portfolio Action Model

### 10.1 定位

这是主线 1 之后的监督学习动作模型。

它不能先于规则化组合优化器启动，因为它需要规则化优化器产生稳定的动作空间、状态空间和回放标签。

### 10.2 要解决的问题

```text
在某一天、某个组合状态下，哪些动作比不动作更好？
是小幅买入、部分减仓、清仓、保留，还是风险复盘？
```

### 10.3 第一阶段做什么

基于主线 1 的回放结果构造样本：

```text
state: 当前组合 + 候选排名 + 市场状态 + 费用约束
action: no_action / buy_small / reduce_partial / exit_full / keep / review
label: 未来 5/10/20 日净收益、回撤、是否优于不动作
```

第一版可以先做：

```text
LightGBM regression / binary
action value ranking
pairwise action comparison
```

### 10.4 参考论文

优先参考：

```text
2605.01176 Decision-Induced Ranking Explains Prediction Inflation and Excessive Turnover
1904.08925 Transaction costs on systematic portfolios
Meta-labeling / Advances in Financial Machine Learning
QuantBench
```

使用方式：

```text
2605.01176：避免动作模型过度换手和分数膨胀。
1904.08925：标签必须扣费用税费。
Meta-labeling：动作模型更像确认/过滤/调整层，不是从零选股。
QuantBench：必须严格 OOS、walk-forward、指标对齐。
```

### 10.5 不做什么

```text
不直接输出目标仓位。
不直接替代规则化优化器。
不把历史最优动作当无噪声标签。
不进入默认产品路径。
```

### 10.6 验收重点

```text
动作模型是否稳定优于规则化优化器；
是否降低换手或回撤；
是否不过度学习少数行情；
是否能解释“为什么优于不动作”；
是否没有未来函数和 replay leakage。
```

## 11. 主线 6：Context-Aware Transformer / Graph Model Research

### 11.1 定位

这是后置研究，不是近期产品主线。

它可以研究，但必须在：

```text
主线 1 的组合动作层稳定；
主线 3 的 PIT 数据地基更完整；
已有足够 rolling windows / regime 证据；
```

之后再考虑。

### 11.2 可研究问题

```text
不同股票之间的关系是否能帮助解释排名和动作？
行业/供应链/相关性/市场状态是否能改善风险过滤？
context-aware reranking 是否只在 risk-off 有价值？
```

### 11.3 参考论文

优先参考：

```text
2105.10019 Context-Aware Re-Ranking with Self-Attention
2302.10175 Spatio-Temporal Momentum
2012.07149 Learning to Rank for Cross-Sectional Strategies
```

使用方式：

```text
2105.10019：作为 context-aware / self-attention rerank 思想参考。
2302.10175：作为时间序列 + 横截面联合建模参考。
2012.07149：仍作为排序任务目标函数参考。
```

### 11.4 不做什么

```text
不直接替换当前 E4 Qlib + Orthogonal LTR。
不在样本不足时做深度黑盒。
不以模型复杂度作为成功标准。
不进入默认策略。
```

### 11.5 验收重点

```text
是否只作为 diagnostic / research artifact；
是否在多个 regime 和 rolling windows 有稳定增益；
是否提供解释或至少可审查归因；
是否没有牺牲用户第一性原则。
```

## 12. 主线 7：Offline RL Portfolio Research

### 12.1 定位

这是最后优先级研究主线。

强化学习可以研究，但不能作为当前阶段主线，更不能接真实交易。

### 12.2 启动前置条件

必须先具备：

```text
标准化 portfolio state
标准化 action space
标准化 fee/tax/slippage
规则化优化器 baseline
监督动作模型 baseline
多窗口 OOS / rolling / regime benchmark
严格 offline-only 环境
```

### 12.3 参考论文

优先参考：

```text
2011.09607 FinRL: A Deep Reinforcement Learning Library for Automated Stock Trading
2012.13773 Deep Reinforcement Learning for Portfolio Management
2112.04755 Deep Reinforcement Learning for High Dimensional Stock Portfolio Management
2603.29086 RL under Transaction Cost / Market Impact
```

使用方式：

```text
FinRL：参考数据层、环境层、Agent 层拆分，不照搬自动交易。
2012.13773：参考组合权重调整的状态/动作/奖励设计。
2112.04755：参考高维股票池动作空间风险。
2603.29086：参考交易成本和市场冲击下 RL 的风险。
```

### 12.4 不做什么

```text
不接 broker。
不做 live trading。
不输出目标仓位给用户执行。
不把 RL 回测收益包装成产品能力。
不在无真实成本/滑点/成交约束时做产品化。
```

### 12.5 验收重点

```text
是否稳定超过规则化优化器和监督动作模型；
是否对交易成本敏感性稳健；
是否避免过拟合单一市场阶段；
是否可解释或至少可审查；
是否完整隔离为 offline research。
```

## 13. 推荐总体推进节奏

建议新统筹按这个节奏推进：

```text
第一轮：主线 1 P0-P2
第二轮：主线 1 P3 + 主线 2 R0
第三轮：主线 3 D0-D1 或主线 4 W0-W2
第四轮：根据主线 1/2/3 的证据，决定是否进入主线 5
第五轮：只有在足够证据后，才允许主线 6/7 研究
```

更具体地：

```text
先做 Portfolio Decision Optimizer v1，因为它直接服务用户今天是否动作。
再做 Risk Filter，因为它能增强动作解释和风险复盘。
再补 PIT 数据，因为它决定未来模型有没有真实信息增量。
Fresh Qlib 窗口敏感性可以并行研究，但不得抢默认产品主线。
监督动作模型必须等规则化动作层稳定。
Transformer / RL 只能作为后置研究。
```

## 14. 新统筹接手后的第一阶段任务

新统筹不要立即让执行者写代码。第一阶段应做：

```text
1. 阅读本文档和关键收口文档。
2. 确认当前 baseline 已是 E4 Qlib + Orthogonal LTR。
3. 确认旧 Entry Decision Model / 正交规则 / clean stacking 的失败和限制。
4. 接受“多主线排序”，但第一轮只启动主线 1。
5. 给执行者下达 Portfolio Decision Optimizer v1 P0 合同冻结任务。
6. 给审查者要求：必须检查是否重复做 LTR、是否误入目标仓位/真实交易、是否改默认路径。
```

## 15. 给执行者的第一条建议命令

如果统筹批准进入下一主线，建议先给执行者：

```text
你是执行者。请准备 TW Portfolio Decision Optimizer v1 的 P0 合同冻结工作文档，只做计划和边界确认，不实现代码、不训练模型、不生成新 artifact、不修改默认模型/默认策略/前端默认/latest 路径。

必须读取并遵守：
- docs/tw_new_model_strategy_pre_rnd/TW_CURRENT_STATE_FUTURE_RND_ROADMAP_CN.md
- docs/tw_portfolio_decision_model/PORTFOLIO_DECISION_MODEL_FUTURE_MAINLINE_CN.md
- docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
- docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
- docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
- docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
- docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md

P0 文档必须冻结：输入数据、组合状态、动作集合、费用税费、next_open execution price gate、OrderIntentArtifact 输出、ReplayResultArtifact 指标、前端/Agent 只读表达、validator/golden sample 计划和禁止事项。

不得触发真实数据拉取、provider publish、accepted latest switch、monitor config/scan/alerts 写入、broker/order/quick-trade、target_position/target_weight、OpenAI key 读取、真实 OpenAI smoke、默认模型/默认策略/前端默认切换。

完成后提交 docs/tw_portfolio_decision_model/PHASEP0_CONTRACT_FREEZE_WORK_REPORT_CN.md，等待审查者审查。
```

## 16. 给审查者的第一条建议命令

```text
你是审查者。请在执行者提交 docs/tw_portfolio_decision_model/PHASEP0_CONTRACT_FREEZE_WORK_REPORT_CN.md 后，依据 docs/tw_new_model_strategy_pre_rnd/TW_CURRENT_STATE_FUTURE_RND_ROADMAP_CN.md 和项目宪法审查 P0 是否只冻结合同、未实现代码、未训练模型、未生成 artifact、未修改默认路径。

重点审查：
1. 是否承认当前 baseline 已是 E4 Qlib + Orthogonal LTR，而不是重复规划 LTR baseline；
2. 是否把新主线定位为组合动作层，不是排序层；
3. 是否先定义 StrategyDependency / OrderIntent / ReplayResult 合同；
4. 是否禁止 target_position / target_weight / broker / order / quick-trade；
5. 是否保留 next_open execution price pending/block 规则；
6. 是否不改默认模型、默认策略、前端默认、latest/default pointer；
7. 是否给出 validator/golden sample 计划；
8. 是否遇到无法确认的问题时停止并报告统筹。

若通过，请撰写 Phase P1 规则化组合优化器工作文档；若不通过，请列出必须修复项并停止。
```

## 17. 新统筹必须继承的开发规范、模块合同与 Skills

新统筹不能只看研发方向。后续所有新模型、新策略、新数据、新前端或 Agent 接入，都必须先遵守项目的最高层宪法、模块合同和 project-local skills。

### 17.1 最高层规则

必须优先读取并遵守：

```text
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/TW_CURRENT_PROJECT_DOC_ENTRY_AND_ARCHIVE_POLICY_CN.md
docs/tw_modular_contracts/TW_PROJECT_MODULE_MAP_AND_FLOW_CN.md
docs/tw_modular_contracts/TW_MODULAR_PIPELINE_FUTURE_DEVELOPMENT_GUIDE_CN.md
docs/tw_modular_contracts/TW_DEVELOPER_TEST_AND_EXPERIMENT_PLAYBOOK_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
```

这些文档的关系：

```text
TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md 是最高规则。
TW_CURRENT_PROJECT_DOC_ENTRY_AND_ARCHIVE_POLICY_CN.md 告诉新节点先读哪些当前文档、哪些历史文档只用于追溯。
TW_PROJECT_MODULE_MAP_AND_FLOW_CN.md 说明数据、模型、策略、回放、API、前端、日更和模拟账户如何串联。
TW_MODULAR_PIPELINE_FUTURE_DEVELOPMENT_GUIDE_CN.md 是新增数据/特征/模型/策略/回放/分析/前端/Agent 的总开发规范。
TW_DEVELOPER_TEST_AND_EXPERIMENT_PLAYBOOK_CN.md 是开发、测试、实验的执行手册。
NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md 是新模型/新策略的最小提交流程。
```

如果路线文档、执行者报告、审查者意见和以上规范冲突，以宪法和模块合同为准。若冲突影响默认模型、默认策略、安全边界或 latest/default 路径，必须停止并找用户/统筹确认。

### 17.2 模块合同入口

按任务类型读取对应合同，不得凭经验开发。

新数据 / 特征：

```text
docs/tw_modular_contracts/DATA_SOURCE_CONTRACT_CN.md
docs/tw_modular_contracts/DATA_INGESTION_ARTIFACT_CONTRACT_CN.md
docs/tw_modular_contracts/FEATURE_ARTIFACT_CONTRACT_CN.md
docs/tw_modular_contracts/PRICE_STORE_CONTRACT_CN.md
```

新模型：

```text
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md
```

新策略 / 组合动作层：

```text
docs/tw_modular_contracts/STRATEGY_DEPENDENCY_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md
docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md
```

日更 / API / 前端 / Agent：

```text
docs/tw_modular_contracts/DAILY_ORCHESTRATOR_CONTRACT_CN.md
docs/tw_modular_contracts/RUN_REGISTRY_CONTRACT_CN.md
docs/tw_modular_contracts/AUTO_UPDATE_ORCHESTRATOR_CONTRACT_CN.md
docs/tw_modular_contracts/FRONTEND_READONLY_DISPLAY_CONTRACT_CN.md
docs/tw_modular_contracts/FRONTEND_AGENT_PANEL_CONTRACT_CN.md
docs/tw_modular_contracts/AGENT_READONLY_CONTEXT_CONTRACT_CN.md
```

### 17.3 Registry 与默认路径规范

新统筹必须要求执行者从 registry 读默认口径：

```text
configs/tw_product_artifact_registry.yaml
configs/tw_modular_registry.yaml
configs/tw_replay_window_policy.yaml
configs/strategy_dependencies/*.yaml
```

不得在前端、API、脚本、测试中重新硬编码默认模型、默认策略或核心 artifact 路径。

若确实要改变默认口径，必须单独开默认切换审查主线，至少补齐：

```text
registry change
validator
golden sample
readonly E2E
safety audit
review report
explicit user approval
```

### 17.4 可用 project-local skills

新统筹必须优先使用项目本地 skills，而不是历史 archive skill。当前 project-local skills 位于：

```text
.agents/skills/
```

可用入口：

```text
.agents/skills/tw-stock-new-model-onboarding/SKILL.md
.agents/skills/tw-stock-new-strategy-onboarding/SKILL.md
.agents/skills/tw-stock-modular-integration-regression/SKILL.md
.agents/skills/tw-stock-readonly-e2e-acceptance/SKILL.md
.agents/skills/tw-stock-safety-boundary-review/SKILL.md
.agents/skills/tw-stock-research-context-analyst/SKILL.md
.agents/skills/tw-stock-data-freshness-diagnosis/SKILL.md
.agents/skills/tw-stock-frontend-workbench-ux-review/SKILL.md
.agents/skills/tw-stock-agent-daily-prompt-maintenance/SKILL.md
.agents/skills/frontend-design/SKILL.md
.agents/skills/llm-wiki/SKILL.md
```

使用建议：

```text
新模型：tw-stock-new-model-onboarding
新策略 / 组合动作层：tw-stock-new-strategy-onboarding
模块化总回归：tw-stock-modular-integration-regression
只读 E2E / 前端验收：tw-stock-readonly-e2e-acceptance
安全红线审查：tw-stock-safety-boundary-review
研究上下文解释：tw-stock-research-context-analyst
数据新鲜度问题：tw-stock-data-freshness-diagnosis
前端工作台优化：tw-stock-frontend-workbench-ux-review + frontend-design
Agent 日更 prompt / simple-chat：tw-stock-agent-daily-prompt-maintenance
项目 wiki 更新：llm-wiki / wiki-* skills
```

必须注意：

```text
不要使用 /home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/ 作为 active skill 来源。
如果运行时 metadata 自动露出 archive 旧 skill，必须显式声明以 project-local .agents/skills/tw-stock-* 为准。
```

### 17.5 每个阶段的最低输出格式

执行者每一步必须输出工作报告，至少包含：

```text
目标与非目标
读取的规范 / 合同 / skills
修改或生成的文件
输入 artifact / 输出 artifact
validator / golden sample / 测试结果
未触发的禁止事项
风险与阻塞项
下一步建议
```

审查者每一步必须输出审查意见和下一步工作文档，至少包含：

```text
结论：PASS / PASS_WITH_CONDITIONS / FAIL_NEEDS_REPAIR / STOP
Findings：Critical / High / Medium / Low
是否符合本 roadmap
是否符合宪法和模块合同
是否使用正确 project-local skills
是否触发禁止事项
必须修复项
下一阶段执行文档或停止原因
```

## 18. 给新统筹窗口的完整交接 Prompt

```text
你是新的统筹节点，负责接手台股量化平台后续新模型 / 新策略研发路线。请先不要让执行者直接写代码或训练模型。你的第一任务是阅读并理解当前项目真实状态，然后按多主线研发路线推进。

必须先读取：
- docs/tw_new_model_strategy_pre_rnd/TW_CURRENT_STATE_FUTURE_RND_ROADMAP_CN.md
- docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
- docs/tw_modular_contracts/TW_CURRENT_PROJECT_DOC_ENTRY_AND_ARCHIVE_POLICY_CN.md
- docs/tw_modular_contracts/TW_PROJECT_MODULE_MAP_AND_FLOW_CN.md
- docs/tw_modular_contracts/TW_MODULAR_PIPELINE_FUTURE_DEVELOPMENT_GUIDE_CN.md
- docs/tw_modular_contracts/TW_DEVELOPER_TEST_AND_EXPERIMENT_PLAYBOOK_CN.md
- docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
- configs/tw_product_artifact_registry.yaml
- configs/tw_modular_registry.yaml
- docs/tw_modular_daily_update_productization/PHASEYZ_STRICT_E4_PRODUCTIZATION_FINAL_SUMMARY_CN.md
- docs/tw_modular_daily_update_productization/PHASEYZ4_FINAL_CLOSURE_SUMMARY_FOR_COORDINATION_CN.md
- docs/tw_ltr_strategy_validation/PHASEV4_FINAL_REVIEW_AND_CLOSURE_CN.md
- docs/tw_decision_model/PHASE2C_FINAL_REVIEW_CN.md
- docs/tw_decision_model_orthogonal/PHASE2D_ORTHOGONAL_RULE_CLOSURE_REPORT_CN.md
- docs/tw_portfolio_decision_model/PORTFOLIO_DECISION_MODEL_FUTURE_MAINLINE_CN.md
- docs/references/portfolio_decision_model_papers/README_CN.md

你必须继承以下事实：
1. 当前产品 baseline 已经是 E4 Qlib + Orthogonal LTR，不是普通 qlib，也不是尚未做 LTR。
2. 当前产品模型只保留 e4_frozen_qlib_2018_2022 与 e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025。
3. 当前默认策略是 top50_exit_one_worst_sell。
4. LTR optional sim 策略已经只读、可选、非默认收口；不得继续在旧 LTR 主线追加调优。
5. Entry Decision Model v1 已失败归档，不应重启为 Entry rerank v2。
6. 正交规则卡只能作为人工解释或风险输入，不能直接当训练证据。
7. Orthogonal Fresh Qlib、Clean Stacking、OOS LTR stacking 的结论都不支持直接默认化。
8. 项目身份仍是只读研究 + 产品化候选展示 + 模拟账户，不是实盘交易系统。

后续多主线排序为：
1. Portfolio Decision Optimizer v1：组合动作层，最高优先级。
2. Risk Filter / Holding Risk Model：风险标注与持仓复盘。
3. PIT Data Foundation：FinMind / fundamentals / flow 的 PIT 数据地基。
4. Fresh Qlib Base Model Window Sensitivity：模型基座训练窗口研究。
5. Supervised Portfolio Action Model：在规则化动作层稳定后做监督动作模型。
6. Context-Aware Transformer / Graph Research：后置研究。
7. Offline RL Portfolio Research：最后优先级，只能 offline research。

你的近期执行策略：
- 第一轮只启动主线 1 的 P0-P2。
- P0 只做合同冻结，不写代码、不训练模型、不生成 artifact、不改默认路径。
- P1 才允许实现规则化组合优化器。
- P2 才允许同口径只读 replay 验证。
- P3 前不得做前端/Agent 产品接入。
- 主线 2/3 可在主线 1 P0/P1 稳定后规划，但不得抢主线。
- 主线 6/7 不得近期启动为产品主线。

你必须持续约束执行者和审查者：
- 每个任务必须先声明读取了哪些宪法、合同、开发规范和 project-local skills。
- 新模型任务使用 .agents/skills/tw-stock-new-model-onboarding/SKILL.md。
- 新策略 / 组合动作任务使用 .agents/skills/tw-stock-new-strategy-onboarding/SKILL.md。
- 集成回归使用 .agents/skills/tw-stock-modular-integration-regression/SKILL.md。
- 只读 E2E 使用 .agents/skills/tw-stock-readonly-e2e-acceptance/SKILL.md。
- 安全红线审查使用 .agents/skills/tw-stock-safety-boundary-review/SKILL.md。
- 不得使用 archived tw-stock skills 作为 active skill 来源。
- 不得真实数据拉取，除非用户单独明确批准。
- 不得 provider refresh / publish。
- 不得 accepted latest switch。
- 不得 monitor config / scan / alerts 写入。
- 不得 broker / order / quick-trade。
- 不得 target_position / target_weight。
- 不得读取 OpenAI key 或做真实 OpenAI smoke。
- 不得修改默认模型、默认策略、前端默认或 latest/default pointer。
- 不得把论文结果包装成台股收益承诺。
- 不得把模拟动作写成真实交易建议。

你给执行者的第一条命令应是：准备 TW Portfolio Decision Optimizer v1 的 P0 合同冻结工作文档。执行者必须输出工作报告，报告中必须列明读取的规范、合同和 skills；审查者必须输出审查意见和下一步工作文档，审查意见中必须检查是否遵守宪法、模块合同、开发规范和 project-local skills。所有工作都必须紧贴 TW_CURRENT_STATE_FUTURE_RND_ROADMAP_CN.md，遇到无法确认的问题必须停止并向用户和统筹沟通。
```

## 19. 最终建议

当前项目已经适合进入新模型 / 新策略研发，但研发方向必须更新为多主线体系：

```text
近期主线：组合动作层 + 风险过滤 + PIT 数据地基。
中期主线：fresh qlib 窗口敏感性 + 监督动作模型。
远期研究：Transformer / Graph / Offline RL。
```

一句话：

```text
项目已经完成“排序层”的主要地基，下一阶段应把重点从“选哪只更好”升级为“已有排序、模拟持仓和成本约束下，今天是否值得动作，以及为什么”。
```
