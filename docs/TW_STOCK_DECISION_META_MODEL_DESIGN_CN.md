# TW Stock 二阶段决策模型设计方案

## 1. 背景与问题

当前项目已经有一条相对成熟的 qlib baseline：Yahoo/Scrapling adjusted OHLCV -> qlib provider -> Alpha158 -> LightGBM -> qlib score/rank -> Top30/Top50/连续转弱复盘等策略。

这个 baseline 的优点是稳定、可复现、边界清晰；缺点是只靠价格和成交量类特征，无法直接表达法人、融资融券、营收、估值、技术状态冲突、追高风险、持仓状态等信息。

用户提出的新想法是：不要破坏 qlib baseline，不把补充信息硬塞进 qlib 特征；而是在 qlib 输出之后，用 qlib rank/score + FinMind 补充信息 + MA/RSI/MACD/Bollinger 等趋势技术信息，训练一个二阶段“决策模型”，用于判断是否观察、是否复盘、候选优先级。

结论：这个方向合理，且比直接训练“买卖模型”更适合当前项目。

## 2. 外部方案调研

### 2.1 Qlib 的启示

Qlib 的定位是 AI-oriented quant investment platform，强调从数据、模型、回测到投资组合分析的完整量化研究流程。Qlib 官方仓库也说明它支持 supervised learning、market dynamics modeling、RL 等多种建模范式。

参考：

- Qlib paper: https://arxiv.org/abs/2009.11189
- Qlib GitHub: https://github.com/microsoft/qlib

对本项目的启示：

- qlib baseline 适合作为第一阶段 alpha/ranking signal。
- 不应该轻易破坏已稳定的 provider、handler、模型和信号生产链路。
- 二阶段决策模型应作为 qlib 输出后的 overlay，而不是替换 qlib baseline。

### 2.2 Meta-labeling 的启示

Meta-labeling 的思想是：先有一个主模型或主策略生成方向/候选信号，再用第二个模型判断这个信号是否值得执行、是否应该过滤、是否调整仓位。它尤其适合“主信号已经存在，但误报较多”的场景。

参考：

- Meta-labeling overview: https://en.wikipedia.org/wiki/Meta-Labeling
- López de Prado, Advances in Financial Machine Learning, Wiley.

对本项目的启示：

- qlib baseline 负责给出候选和方向，不让二阶段模型从零开始预测全市场。
- 二阶段模型只判断“这个 qlib 候选是否值得进入观察/是否风险复盘”。
- 这样比直接训练买卖模型更低风险、更容易解释，也更符合用户第一性原则。

### 2.3 Learning-to-Rank 的启示

Learning-to-rank 用特征向量对候选集合排序，常见范式有 pointwise、pairwise、listwise。LightGBM 官方参数文档支持 `lambdarank` 和 `rank_xendcg` 等排序目标。

参考：

- Learning to Rank overview: https://en.wikipedia.org/wiki/Learning_to_rank
- LightGBM parameters: https://lightgbm.readthedocs.io/en/latest/Parameters.html

对本项目的启示：

- 我们的问题天然是“同一天 Top50 里谁更值得排前面”。
- 不需要把所有股票作为一个巨大输入向量。
- 每条样本是 `date-symbol`，以 `date` 作为 group/query，当天候选互相排序。
- 第一版可以用 LightGBM regression/binary 做 baseline，第二版再试 LambdaRank。

### 2.4 近期量化 AI 研究启示

近期 QuantBench、AI in Quant survey 等工作强调：量化模型要完整覆盖数据、模型、回测、组合、风控全流程，同时要特别注意分布漂移、过拟合、低信噪比和评估标准对齐。

参考：

- QuantBench: https://arxiv.org/abs/2504.18600
- AI in Quant survey: https://arxiv.org/abs/2503.21422
- LambdaRankIC: https://arxiv.org/abs/2605.00501

对本项目的启示：

- 不应只看单次收益率；必须看多年份、多行情、换手、回撤、费用后超额收益。
- 决策模型必须做 walk-forward，而不是随机切分。
- 如果模型目标是排序，Rank IC、NDCG@K、TopK forward return 比 MSE 更贴近任务。

## 3. 方案总览

推荐方案：保留 qlib baseline，新增 `Decision Model` 作为第二阶段，并把候选生成和候选重排序拆开。

```text
Yahoo/Scrapling OHLCV
  -> qlib baseline Alpha158 + LightGBM
  -> qlib score/rank/全市场候选信号

Candidate Generator
  -> qlib Top50
  -> qlib score 0.4-0.8 区间
  -> 排名明显改善
  -> 技术状态转强
  -> 流动性和数据完整性过滤

qlib output + 技术趋势 + FinMind 补充信息 + 大盘状态 + 持仓状态
  -> Decision Model
  -> entry_score / exit_risk_score / confidence

组合规则
  -> 每天最多买/卖一支
  -> 最多持有 N 支
  -> 手续费/交易税/回撤约束
  -> 生成只读建议与回放结果
```

模型不直接下单，不生成真实订单，不写 broker。它只输出研究信号。

这里的关键变化是：Decision Model 不应该只看 Top30/Top50。Top30/Top50 是当前稳定 baseline，但它可能漏掉熊市里更稳的中等 score 股票。因此更合理的方式是先扩大召回，再重排序，最后仍只把少量高价值结果展示给用户。

推荐的候选池规模：

- 第一版：从当前稳定股票池约 150 支中生成候选。
- 训练时：每个交易日尽量覆盖完整稳定股票池，至少覆盖 Top50 + score band + 技术转强股票。
- 前端展示时：只展示 3-5 支新增观察和 3-5 支风险复盘，不展示完整候选池。

## 4. 不建议的方案

### 4.1 不建议每只股票单独训练模型

原因：

- 单只股票样本太少，容易过拟合。
- 台股很多股票流动性和历史长度不均衡。
- 无法学习“同一天不同股票谁更好”的横截面关系。
- 维护成本高，不符合项目当前阶段。

### 4.2 不建议把全市场所有股票作为一个巨大输入

原因：

- 输入维度随股票池变化，不稳定。
- 缺失值和停牌处理复杂。
- 对普通 LightGBM/排序模型不友好。
- 难解释，难部署。

但这不等于不分析更多股票。正确做法是：每只股票仍然是一行 `date-symbol` 样本，扩大候选行数，而不是把 150 支股票拼成一个巨大向量。

```text
不推荐：
date -> [stock1_features, stock2_features, ..., stock150_features] -> model

推荐：
date-symbol -> features -> model
同一天的 symbol 作为 group 参与排序
```

### 4.3 不建议第一版直接做强化学习或端到端买卖模型

原因：

- 样本少、噪声大、容易过拟合。
- 很难解释为什么买卖。
- 对小白用户不友好。
- 当前项目核心目标是简单、准确、清晰、实用，不是追求复杂模型。

## 5. 推荐建模方式

### 5.1 样本粒度

每一行是一个 `date-symbol`。

例如：

```text
2026-06-04, 2357, qlib_rank=3, qlib_score=0.062, ma_state=strong, rsi=58, institution_5d_z=1.2, ...
```

每个交易日形成一个 group。第一版 group 不应只包含 Top50，而应包含稳定股票池或经 Candidate Generator 召回后的候选池。

推荐候选池：

- 稳定股票池约 150 支，要求有足够 OHLCV 历史、流动性、非长期停牌。
- qlib Top50 必须包含。
- qlib score 位于历史测试有效区间，例如 `0.4-0.8` 的股票必须纳入候选，但不能机械视为一定更好。
- 排名改善明显、技术状态转强、法人资金明显改善的股票可以补充纳入。

这样既避免只看 Top30/Top50 的选择偏差，也避免全市场过大导致噪声和产品复杂度上升。

### 5.2 输入特征

#### qlib baseline 特征

- qlib_rank
- qlib_score
- qlib_score_percentile_by_date
- qlib_score_zscore_by_date
- qlib_score_band，如 low/mid/high 或 0.4-0.8 flag
- rank_change_1d / 3d / 5d
- top10/top30/top50 flags
- top30_streak / top50_streak
- newly_entered_top30 / dropped_from_top30

#### 技术趋势特征

- trend_label
- trend_score
- MA5/10/20/60 方向
- distance_to_ma20_pct
- RSI14
- MACD state
- Bollinger position
- 20d return
- 20d volatility
- volume_ratio_20d
- position_risk_status: reasonable/elevated/overheated/pullback

#### 大盘环境特征

- TWII market_regime: bull/normal/caution/bear
- TWII ret20 / ret60
- TWII close vs MA60/MA120
- market_volatility_20d
- market_breadth_20d，如上涨家数比例、站上 MA20 股票比例
- top50_avg_score / top50_avg_trend_score
- market_drawdown_from_60d_high

大盘信息是 Decision Model 的必选输入，不是可选增强。否则模型无法学习同一个 qlib score 在牛市、震荡市、熊市里的不同含义。

建议显式构造交互特征：

- qlib_score_percentile_by_date × market_regime
- qlib_score_band × market_regime
- trend_score × market_regime
- position_risk_status × market_regime

这些交互特征用于解决一个核心问题：高 qlib score 在牛市可能代表趋势延续，在熊市可能代表短期拥挤或追高风险。

#### FinMind 补充特征

第一版只接入已归档、可 point-in-time 的字段，不强行扩太多：

- institutional_net_buy_1d/5d/20d
- institutional_net_buy_z20
- margin_balance_change_5d
- short_balance_change_5d
- monthly_revenue_yoy / mom
- valuation_percentile，如 PER/PBR 分位

所有 FinMind 特征必须按实际可用时间做 T+1 或更保守滞后，禁止偷看未来。

#### 持仓状态特征

仅在模拟账户/组合回放中使用：

- currently_holding
- holding_days
- unrealized_return
- max_drawdown_since_entry
- entry_rank
- entry_score

### 5.3 标签设计

第一版不要直接训练三分类“买/卖/持有”。建议拆成两个模型。

#### Entry Model

目标：判断一个候选股票是否值得新进观察。候选不局限于 qlib Top50，而是来自 Candidate Generator。

候选标签：

```text
entry_label = 1 if future_20d_excess_return_after_fee > threshold and future_20d_max_drawdown > -risk_limit else 0
```

可选阈值：

- future_20d_excess_return_after_fee > 2%
- future_20d_max_drawdown > -8%

输出：

- entry_score: 0-1
- confidence

#### Exit Risk Model

目标：判断已持有股票是否应该风险复盘。

候选标签：

```text
exit_label = 1 if future_10d_excess_return_after_fee < -threshold or future_10d_drawdown < -risk_limit else 0
```

输出：

- exit_risk_score: 0-1
- reason features

### 5.4 模型选择

第一阶段：LightGBM binary/regression。

理由：

- 与当前 qlib baseline 技术栈一致。
- 对 tabular 特征友好。
- 可解释性较好，能做 feature importance。
- 训练和回测速度可控。

第二阶段：LightGBM LambdaRank / rank_xendcg。

理由：

- 更贴近“每天候选池内重排”的任务。
- 以 `date` 为 group，优化排序质量。
- 可用 NDCG@10、TopK forward return、Rank IC 评估。

第三阶段才考虑更复杂模型，例如 TabNet、Transformer、图模型或 RL。

## 6. 决策输出与产品呈现

用户不应该看到复杂模型细节。前端只展示简单、可解释的结果。

### 6.1 今日操作建议

每个策略下展示：

- 建议新增观察：最多 3-5 支
- 建议风险复盘：最多 3-5 支
- 建议继续持有/继续观察
- 模型置信度：低/中/高
- 主要原因：最多 3 条

不要展示过多原始指标。

示例：

```text
Top50 决策模型：今日偏谨慎

新增观察候选：
1. 2357 华硕：qlib Top10，趋势支持，法人 5 日净流入，位置未过热
2. 2303 联电：qlib 排名改善，MA 状态转强，估值分位不高

风险复盘候选：
1. 2409 友达：跌出 Top50，MACD 转弱，融资上升但价格未跟随
```

### 6.2 回放页面

新增策略卡：

- Top50 原始轮动
- Top50 自适应 score
- Top50 决策模型 v1
- 连续转弱复盘
- 决策模型 + 连续转弱复盘

卡片只显示：

- 收益率
- 最大回撤
- 操作次数
- 手续费税费
- 相对大盘
- 相对 Top50 baseline

## 7. 回测与验收标准

### 7.1 数据切分

不能随机切分。必须时间切分。

建议：

- train: 2018-2021
- validation: 2022
- test: 2023
- forward test: 2025-2026

如果早期数据不足，则先从已有 2022/2023/2026 历史回放开始，后续逐步补齐。

### 7.2 指标

模型层：

- Rank IC
- NDCG@10
- precision@5
- TopK future excess return
- calibration curve

策略层：

- total return after fee/tax
- max drawdown
- turnover
- action count
- win/loss distribution
- benchmark excess return
- bull/flat/bear regime breakdown

### 7.3 通过标准

第一版不要求每年都正收益，但必须满足：

- 相比 Top50 自适应 score，至少一个独立测试区间收益更好，且另一个区间不显著变差。
- 最大回撤不能明显恶化。
- 操作次数不能明显高于 baseline。
- 2022 熊市不能比 Top50 自适应 score 明显更差。
- 所有特征必须有 point-in-time 证明。

## 8. 风险与防护

### 8.1 最大风险：数据泄漏

FinMind 的月营收、法人、融资融券不是都能在交易日盘中可用。必须记录每个特征的 `available_at`，训练和回放只能使用当时已经可见的数据。

### 8.2 第二风险：过拟合

防护：

- 固定训练/验证/测试区间。
- 不在测试集上调阈值。
- 限制特征数量，先做 20-40 个强解释特征。
- 用 walk-forward 验证。
- 保留 baseline 对照。

### 8.3 第三风险：产品复杂化

防护：

- 前端只展示结论和少量原因。
- 模型细节放在“展开查看”。
- 默认策略不超过 3 个。
- 所有建议保持 research-only，不出现“立即买入/卖出”。

### 8.4 第四风险：候选池选择偏差

如果只训练和评估 Top30/Top50，模型会天然继承 qlib baseline 的选择偏差，可能永远看不到熊市里更稳的中等 score 股票。

防护：

- 训练样本覆盖稳定股票池或至少覆盖 Top50 + score band + 技术转强股票。
- 回测同时报告 Top30/Top50 限制版和扩大候选池版。
- 单独评估熊市、震荡市、牛市下各 score band 的收益、回撤和换手。

### 8.5 第五风险：qlib score 绝对值不可比

`qlib score` 不一定等于预期收益率，也不保证不同日期、不同训练版本之间绝对值完全可比。历史上观察到 `0.4-0.8` 在熊市更稳，不代表这个区间永远有效。

防护：

- 同时使用 raw score、date percentile、date z-score、自身历史分位。
- score band 只作为特征，不作为硬买卖规则。
- 每次模型版本变化后重新校准 score band 表现。

### 8.6 第六风险：只优化收益，忽略换手和回撤

如果模型只追求短期 forward return，可能选出高波动、高换手股票，费用后收益反而更差。

防护：

- 标签中加入费用后超额收益和最大回撤条件。
- 验收必须看 after-fee return、max drawdown、turnover、action count。
- 候选排序中保留 position_risk_status 和 liquidity filter。

### 8.7 第七风险：大盘状态定义本身不稳定

如果 market_regime 规则过度拟合 2022，可能在未来误判。

防护：

- market_regime 使用简单、透明、可复现的规则，例如 TWII ret60、MA120、回撤、波动率。
- 规则只负责提供状态特征，不直接决定买卖。
- walk-forward 中单独报告不同 market_regime 的表现。

## 9. 分阶段实施计划

### Phase 0：数据审计与特征可用性确认

目标：确认哪些补充特征已经可用，哪些只是脚本存在但未进入稳定归档。

工作：

- 审计 qd_tw_stock_daily_bars 覆盖率。
- 审计 FinMind institutional/margin/monthly revenue/valuation 数据覆盖率。
- 为每类数据定义 available_at / lag 规则。
- 生成 feature availability report。

验收：

- 输出每类特征的覆盖率、缺失率、最早/最新日期。
- 明确哪些特征能进 v1，哪些暂缓。

### Phase 1：构建 point-in-time 训练样本

目标：生成 `date-symbol` 面板数据。

工作：

- 从 qlib historical signal 读取 rank/score，并覆盖稳定股票池而不只 Top50。
- 建立 Candidate Generator：Top50、score band、排名改善、技术转强、流动性过滤。
- 从 KlineService/本地归档读取技术趋势。
- 从 FinMind 归档读取补充特征。
- 生成 future return / drawdown 标签。
- 输出 parquet/csv 样本和 schema。

验收：

- 任意样本都能追溯来源。
- 没有未来日期字段。
- 有单测验证 T+1 lag。

### Phase 2：训练 Entry Model v1

目标：先做“是否值得新增观察”的二分类/回归模型。

工作：

- LightGBM binary/regression baseline。
- 输出 entry_score。
- 做 feature importance。
- 做 validation/test 评估。

验收：

- 生成模型文件、训练报告、特征重要性。
- 和 qlib score 单独排序、Top50 原始轮动、Top50 自适应 score 做对比。
- 单独报告 Top50 限制版和扩大候选池版。
- 至少在一个独立区间提升 TopK forward return，且熊市区间不能明显劣化。

### Phase 3：训练 Exit Risk Model v1

目标：判断已持有股票是否需要风险复盘。

工作：

- 构建 holding-aware 样本。
- 训练 exit_risk_score。
- 与“跌出 Top50”和“连续转弱”规则对比。

验收：

- 能解释哪些股票被判为高风险。
- 不显著增加换手。
- 对最大回撤有改善或至少不恶化。

### Phase 4：组合回放集成

目标：把模型输出接入只读组合回放。

工作：

- 新增策略：`expanded_pool_decision_model_v1`，并保留 `top50_decision_model_v1` 作为对照。
- 买入候选：Candidate Generator 召回后的候选池按 entry_score 排序。
- 卖出候选：持仓按 exit_risk_score + rank deterioration + 技术转弱排序。
- 仍保留每天最多买/卖一支、最多持有 N 支。

验收：

- 只读回放，不写模拟账户。
- 输出收益、回撤、操作次数、费用。
- 与 Top50、Top50 自适应 score、连续转弱复盘、扩大候选池规则版对比。

### Phase 5：前端产品化

目标：简单、清晰、实用地展示。

工作：

- 今日建议增加“决策模型”下拉选项。
- 展示新增观察、风险复盘、继续观察。
- 每个建议最多 3 个原因。
- 增加“数据不足/模型不可用”友好提示。

验收：

- 用户不需要理解模型细节也能看懂。
- 不出现真实下单文案。
- Playwright 只读 E2E 覆盖。

### Phase 6：长期验证与上线门槛

目标：避免模型过拟合后误导用户。

工作：

- 每周/每日自动生成模型表现报告。
- 监控模型建议与实际后验收益。
- 如果连续低于 baseline，自动降级为 baseline 展示。

验收：

- 有 drift warning。
- 有 baseline fallback。
- 有模型版本、训练数据、特征 schema 记录。

## 10. 最终建议

建议实施，但不要一步到位做“自动买卖模型”。

最合理路径是：

1. 保留 qlib baseline。
2. 先做 Candidate Generator，扩大候选池，避免只看 Top30/Top50。
3. 做 Entry Model，用大盘状态、score band、技术趋势和补充信息重排候选。
4. 再做 Exit Risk Model，辅助连续转弱复盘。
5. 组合规则仍负责交易频率和仓位。
6. 前端只展示“候选优先级 + 风险复盘 + 简短原因”。

这条路径既符合现有项目结构，也符合用户第一性原则：简单、准确、清晰、实用。
