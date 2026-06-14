# 台股量化优化方向文档（基于论文核对与现有数据能力）

## 1. 结论先行

基于对下列论文原始来源（以 arXiv 摘要与任务设定为主）的逐篇核对：

1. Building Cross-Sectional Systematic Strategies By Learning to Rank
2. Spatio-Temporal Momentum: Jointly Learning Time-Series and Cross-Sectional Strategies
3. Enhancing Cross-Sectional Currency Strategies by Context-Aware Learning to Rank with Self-Attention
4. Decision-Induced Ranking Explains Prediction Inflation and Excessive Turnover in SPO-Based Portfolio Optimization
5. The impact of proportional transaction costs on systematically generated portfolios
6. Wax and wane of the cross-sectional momentum and contrarian effects

可以明确得出：

- 这些论文里，**真正适合当前项目主线**的，不是“直接上一个更大的黑盒模型”，而是：
  1. `qlib` 之上加一层 **Learning-to-Rank 横截面重排序**；
  2. 在组合层显式加入 **换手控制 / 交易成本约束**；
  3. 引入 **市场状态上下文** 做轻量自适应，而不是继续堆绝对 score 阈值；
  4. 保持 research-only，只做只读排序、回放和人工复盘辅助。
- **不适合当前项目立刻照搬**的，是需要更大样本、更高频、更完整 PIT 基本面/筹码数据，或者更复杂端到端优化的路线。

因此，推荐的新主线是：

```text
qlib baseline rank/score
-> LTR reranker（第二阶段横截面重排序）
-> context / regime gating（市场状态轻量自适应）
-> turnover-controlled portfolio layer（组合层换手与风险控制）
-> readonly replay / frontend explanation
```

---

## 2. 本文档的证据边界

本轮判断基于：

- 论文原始 arXiv 页面摘要与任务描述；
- 这些论文的方法是否与当前项目的数据条件、产品边界、已有 baseline 匹配；
- 项目已有文档中明确的数据可用性审计；
- 已经验证过的项目现状：Top30/Top50、adaptive score、confirmed_exit、portfolio replay、market regime、position risk。

需要明确：

- 本文档不是完整文献综述；
- 不是逐页复现实验；
- 不是证明这些论文方法在台股 150 股票 universe 上一定 outperform；
- 而是判断“哪些方向**值得进入你这个项目的下一阶段实现**”。

---

## 3. 逐篇判断

### 3.1 Learning to Rank for Cross-Sectional Strategies

论文：Building Cross-Sectional Systematic Strategies By Learning to Rank  
来源：arXiv:2012.07149

摘要核心：

- 横截面策略的关键在于 **先把资产排好序**；
- 用普通回归或分类的输出再排序并不理想；
- pairwise / listwise 的 Learning-to-Rank 能更直接优化“排序”本身；
- 文中在 momentum 案例上报告了明显优于传统方法的结果。

为什么适合当前项目：

- 你当前主线本来就是：`qlib_score -> rank -> Top30/Top50 -> 组合规则`；
- 也就是说，你的问题天然就是 **排序问题**，不是纯回归问题；
- 现有数据里：`qlib_score`、`qlib_rank`、技术特征、市场状态特征都已经具备；
- 所以最自然的升级不是推翻 qlib，而是把 qlib 当成第一阶段信号，再做第二阶段 rerank。

结论：

- **强适合**；
- 应作为下一阶段优化主线的核心方法；
- 第一版优先使用树模型 LTR（如 LambdaMART），而不是一开始就上深度排序网络。

---

### 3.2 Joint Time-Series + Cross-Sectional Momentum

论文：Spatio-Temporal Momentum: Jointly Learning Time-Series and Cross-Sectional Strategies  
来源：arXiv:2302.10175

摘要核心：

- 同时建模单资产时间趋势和跨资产横截面关系；
- 简单神经网络就能联合输出组合信号；
- 文中强调在交易成本存在时，`shrinkage + turnover regularization` 很重要。

为什么部分适合：

- 当前项目确实同时有：
  - 横截面：qlib rank / Top30 / Top50；
  - 时间序列：MA、RSI、MACD、ret20、volatility20；
- 所以“同时看时间趋势和横截面”的思想很适合你；
- 但论文是面向更完整的联合建模与深度结构，不是你项目最该先上的第一步。

为什么不建议直接照搬：

- 你当前样本规模偏有限；
- 用户第一原则要求前端简单清晰；
- 复杂神经网络的解释性和调参成本都更高；
- 当前项目最缺的也不是模型复杂度，而是“排序校准 + 换手约束 + regime 自适应”。

结论：

- **思想适合，直接实现不适合当前阶段**；
- 可作为二阶段或三阶段演化方向；
- 当前只吸收其中两点：
  1. 时间趋势 + 横截面同时进入 reranker；
  2. 换手正则必须进组合层。

---

### 3.3 Context-Aware Re-Ranking

论文：Enhancing Cross-Sectional Currency Strategies by Context-Aware Learning to Rank with Self-Attention  
来源：arXiv:2105.10019

摘要核心：

- 全局 ranker 虽然平均有效，但会忽略每次调仓时的局部上下文差异；
- 在 risk-off 等关键阶段，错误排序尤其致命；
- 论文通过 context-aware reranking 改善重要阶段表现。

为什么适合当前项目：

- 你前面遇到的核心问题之一就是：
  - 牛市时可行的规则，熊市会失效；
  - 同样的 score，在不同市场状态下意义不同；
- 当前项目已有可用的上下文数据：
  - `TWII_ret20`
  - `TWII_ret60`
  - `market_drawdown60`
  - `market_volatility20`
  - `market_breadth20`
- 这些数据正好足够做“上下文自适应”。

为什么不直接做 self-attention：

- 论文的实现比你当前项目需要的更重；
- 当前最合理的做法是先把论文的思想落成轻量版本：
  - 正常 / 谨慎 / risk-off 三态；
  - 对 rerank 分数或补仓阈值做轻量 gating；
  - 而不是直接引入复杂 Transformer reranker。

结论：

- **强适合其思想，不适合直接照搬其复杂结构**；
- 应进入当前项目主线，但实现上采用轻量 regime gating / context rerank。

---

### 3.4 Decision-Focused + Excessive Turnover

论文：Decision-Induced Ranking Explains Prediction Inflation and Excessive Turnover in SPO-Based Portfolio Optimization  
来源：arXiv:2605.01176

摘要核心：

- 端到端 decision-focused learning 容易产生预测膨胀与过度换手；
- clipping、rescaling、partial adjustment、turnover control 是实用稳定手段。

为什么对当前项目很重要：

- 你项目已经在真实讨论里反复碰到：
  - 推荐买入会不会追高；
  - 推荐卖出会不会低卖；
  - 每天 top30/50 变化大，频繁交易会不会把 alpha 吃掉；
- 这篇论文没有直接给你一个“更强 alpha 模型”，但它非常准确地点中了你当前产品最现实的痛点：
  **模型分数和组合动作之间必须加稳定层**。

结论：

- **非常适合当前项目的组合层设计**；
- 应直接转化为工程约束：
  - no-trade buffer
  - confidence gap
  - partial rebalance
  - max daily actions
  - score clipping / calibration

---

### 3.5 Transaction Costs on Systematic Portfolios

论文：The impact of proportional transaction costs on systematically generated portfolios  
来源：arXiv:1904.08925

摘要核心：

- 交易频率、成分数、更新频率都会显著影响净表现；
- 论文还讨论了 transaction cost smoothing。

为什么适合当前项目：

- 你当前项目已经在做只读组合回放；
- 但如果没有把 turnover / fee / tax 放到策略主体里，前端展示出来的“高收益”可能不真实；
- 你用户场景又很强调“不要频繁交易”。

结论：

- **强适合**；
- 不是拿来做 alpha，而是拿来定义回放和组合规则的现实约束；
- 是 `LTR + portfolio layer` 必须吸收的论文。

---

### 3.6 Market-Condition Dependence of Cross-Sectional Effects

论文：Wax and wane of the cross-sectional momentum and contrarian effects  
来源：arXiv:1707.05552

摘要核心：

- 横截面动量/反转效应会随市场状态、波动、流动性、宏观不确定性而变化；
- 不是一种在所有阶段都同样有效的静态规律。

为什么适合当前项目：

- 这篇论文从更传统的经验金融角度支持了你已经观察到的现象：
  - 不同市场阶段，Top30/Top50 策略表现会不一样；
  - 熊市里要避免简单照抄牛市规则。

为什么只能吸收一部分：

- 论文是中国市场，不是台股；
- 涉及的一些宏观/流动性背景变量，你当前项目没有完整归档；
- 但“策略必须有 market-condition awareness”这个结论依然成立。

结论：

- **适合做思想支撑，不适合直接当成实现模板**；
- 可支撑 regime-aware 设计，但不是单独可落地方案。

---

## 4. 和当前项目数据面的匹配

根据现有项目数据审计，当前稳定可用的主数据是：

- `qlib_score`
- `qlib_rank`
- `qlib_score_percentile_by_date`
- `qlib_score_zscore_by_date`
- Yahoo/Scrapling adjusted OHLCV
- MA5/10/20/60
- RSI14
- MACD
- Bollinger_position
- ret20
- volatility20
- volume_ratio20
- avg_trading_value_20d
- volume_stability20
- missing_rate20
- suspension/liquidity proxy
- TWII_ret20 / ret60 / drawdown / volatility
- market_breadth20

当前**不适合进主线**的数据：

- FinMind institutional_net_buy
- margin / short balance
- monthly revenue YoY/MoM
- valuation PER/PBR

原因不是“这些数据没价值”，而是：

- 目前归档 coverage 为 0；
- 缺 `available_at` / `announcement_date`；
- 不能安全做 PIT join；
- 强行使用会破坏回测可信度。

因此，本轮论文路线必须建立在：

- `qlib + OHLCV 技术特征 + 市场状态特征 + 流动性 proxy`

而不是建立在“等以后补齐 FinMind 筹码和基本面再说”。

---

## 5. 适合当前项目的优化主线

### 5.1 主线一：LTR 横截面重排序

目标：

- 不替换 qlib baseline；
- 把 qlib 作为第一阶段；
- 再用第二阶段 LTR 重新排序候选股票。

建议输入特征：

- qlib 层：
  - `qlib_score_raw`
  - `qlib_rank`
  - `qlib_score_percentile_by_date`
  - `qlib_score_zscore_by_date`
- 技术趋势层：
  - MA 偏离
  - RSI14
  - MACD
  - Bollinger_position
  - ret20
  - volatility20
- 流动性层：
  - avg_trading_value_20d
  - volume_stability20
  - missing_rate20
  - slippage/liquidity proxy
- 市场状态层：
  - TWII_ret20
  - TWII_ret60
  - market_drawdown60
  - market_volatility20
  - market_breadth20

建议模型：

- 第一版：`LambdaMART`
- 不建议第一版直接上 Transformer / deep LTR

原因：

- 更贴合当前样本规模；
- 可解释；
- 易做 feature importance；
- 更方便和当前前端的“为什么值得看”结合。

---

### 5.2 主线二：Regime-aware 轻量上下文自适应

目标：

- 正常市况下不破坏现有有效策略；
- 差市况下降低错误补仓和追高风险。

建议做法：

- 先定义三态：
  - `normal`
  - `caution`
  - `risk_off`
- 不用上帝视角，而是只用当下可观测数据判断：
  - `TWII_ret20`
  - `TWII_ret60`
  - `drawdown60`
  - `volatility20`
  - `breadth20`
- 在 `caution/risk_off` 下：
  - 提高新入选阈值；
  - 降低每日允许替换数量；
  - 更强调价格位置风险与流动性约束。

这条是对论文 2105.10019 与 1707.05552 的轻量工程化吸收。

---

### 5.3 主线三：组合层换手控制

目标：

- 防止“高点买入、低点卖出、手续费吃掉优势”；
- 把策略从“研究排序”变成“可执行的低频组合规则”。

建议机制：

1. `no_trade_buffer`
   - 新候选没有显著优于当前最差持仓时，不换。
2. `confidence_gap`
   - 只有当新旧候选差距超过阈值才换。
3. `partial_adjustment`
   - 每天最多 1 卖 1 买，或最多替换 10%-20% 仓位。
4. `min_holding_days`
   - 新买入至少持有 N 天，除非强风险信号。
5. `turnover_budget`
   - 周 / 月最大换手预算。
6. `score_clipping_or_rescaling`
   - 避免模型输出膨胀直接驱动过度动作。

这条是对论文 2605.01176 与 1904.08925 的直接工程吸收。

---

### 5.4 主线四：前端解释层升级

当前前端已经收敛到：

- 哪些股票值得先看；
- 为什么；
- 历史回放如何。

下一步不应把前端做得更复杂，而应让输出更明确：

- `基础排名高`：来自 qlib baseline
- `重排序上调 / 下调`：来自 LTR reranker
- `市场环境`：normal / caution / risk_off
- `动作约束`：因为换手预算、风险或价格位置原因，本日不建议替换

这样用户看到的是：

- 这支不是简单“分数高就买”；
- 而是“模型看好，但当前环境/价格位置/换手预算下是否值得动作”。

这才符合用户第一性原则。

---

## 6. 当前不建议做的方向

### 6.1 直接上大黑盒 Decision Model v2

原因：

- 前一条主线已经验证过：复杂模型不自动等于更好；
- 当前项目最缺的不是复杂度，而是约束和排序校准。

### 6.2 依赖 FinMind 财务/筹码因子做主线升级

原因：

- 当前 PIT 归档不完整；
- 贸然加入会让结果不可信。

### 6.3 直接做 self-attention / Transformer reranker

原因：

- 可解释性和调参成本高；
- 对当前项目样本规模与产品阶段都不划算。

---

## 7. 推荐的后续执行顺序

### Phase A：LTR baseline

- 目标：建立 `qlib -> LTR rerank` 基线；
- 输出：新的排序结果、Top30/Top50 变化、对 baseline 的回放对比。

### Phase B：regime gating

- 目标：在不破坏正常市况表现的前提下，提高差市况稳健性；
- 输出：normal/caution/risk_off 三态下的差异指标。

### Phase C：turnover-controlled portfolio layer

- 目标：把净收益、手续费后收益、动作次数、回撤一起纳入验收；
- 输出：真实可执行的组合策略规则。

### Phase D：frontend explanation

- 目标：把 rerank、环境、换手约束解释清楚；
- 输出：用户看得懂、不会误解成自动交易建议的研究界面。

---

## 8. 最终建议

如果只保留一句话：

**当前项目最值得做的，不是更复杂的预测模型，而是“LTR 重排序 + 市场状态轻量自适应 + 组合层换手控制”。**

这是目前最符合：

- 项目现有数据条件；
- 你前面几轮实战里暴露出来的问题；
- 用户第一性原则；
- 以及这些论文真正可迁移部分的路线。

---

## 9. 参考来源

- Building Cross-Sectional Systematic Strategies By Learning to Rank  
  https://arxiv.org/abs/2012.07149
- Spatio-Temporal Momentum: Jointly Learning Time-Series and Cross-Sectional Strategies  
  https://arxiv.org/abs/2302.10175
- Enhancing Cross-Sectional Currency Strategies by Context-Aware Learning to Rank with Self-Attention  
  https://arxiv.org/abs/2105.10019
- Decision-Induced Ranking Explains Prediction Inflation and Excessive Turnover in SPO-Based Portfolio Optimization  
  https://arxiv.org/abs/2605.01176
- The impact of proportional transaction costs on systematically generated portfolios  
  https://arxiv.org/abs/1904.08925
- Wax and wane of the cross-sectional momentum and contrarian effects: Evidence from the Chinese stock markets  
  https://arxiv.org/abs/1707.05552
