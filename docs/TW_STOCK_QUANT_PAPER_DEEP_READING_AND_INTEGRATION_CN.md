# 台股量化论文深读补强与项目整合分析

## 1. 目标与边界

本文档用于补强前一轮“论文方向判断”工作，目标不是做泛泛的论文摘抄，而是回答四个更严格的问题：

1. 这些论文到底在解决什么问题？
2. 它们的实验设定、输入特征、训练目标、组合构建方式是什么？
3. 哪些部分对当前台股项目可迁移，哪些部分不可迁移？
4. 结合当前项目数据面和用户第一性原则，下一条优化主线应该如何收敛？

本轮工作基于：

- 下载并本地抽取全文 PDF：
  - `tmp/papers/2012.07149.pdf`
  - `tmp/papers/2105.10019.pdf`
  - `tmp/papers/2302.10175.pdf`
  - `tmp/papers/2605.01176.pdf`
  - `tmp/papers/1904.08925.pdf`
  - `tmp/papers/1707.05552.pdf`
- 用 `pdftotext` 转成全文文本后做逐篇阅读。
- 再与项目现有数据审计文档、组合策略框架和产品边界进行对照。

因此，本文档比前一版更严格，但仍需明确：

- 这不是逐式复现实验；
- 不是证明论文结果必然在台股 150 股票 universe 上复现；
- 不是直接给出收益承诺；
- 而是给出“在当前项目里最值得实现、且证据最充分的优化路线”。

---

## 2. 当前项目的真实约束

在判断论文是否适合之前，必须先回到项目现实。

### 2.1 当前稳定可用数据

根据已有审计，当前项目稳定可用的研究特征包括：

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
- slippage / liquidity proxy
- TWII_ret20 / TWII_ret60 / drawdown / volatility
- market_breadth20

### 2.2 当前不适合进主线的数据

当前不具备 PIT 安全性的 FinMind 补充数据：

- institutional_net_buy
- margin / short balance
- monthly revenue
- valuation

问题不是这些数据没价值，而是：

- 当前归档 coverage 为 0；
- 缺 `available_at` / `announcement_date`；
- 强行使用会污染回测与训练。

### 2.3 当前项目最真实的问题

从前面多轮策略实现与回放里，已经暴露出几个核心问题：

1. `qlib score` 是横截面排序分数，不是收益率，也不是买入概率。
2. Top30 / Top50 的名单变动较快，简单追随排名会造成高换手。
3. 同一套规则在不同市场阶段表现不同，熊市/风险偏好下降阶段更容易失真。
4. 单纯用更复杂的模型不一定优于已有 baseline，之前的 Decision Model 路线已经证明过这一点。

所以，论文整合必须服务于这四个现实问题，而不是脱离项目场景空谈“更先进”。

---

## 3. 逐篇深读与项目适配分析

## 3.1 2012.07149：Learning to Rank for Cross-Sectional Strategies

论文：**Building Cross-Sectional Systematic Strategies By Learning to Rank**

### 论文真正解决的问题

这篇论文的关键不是“又发明了一个选股因子”，而是指出：

- 横截面策略的核心任务是**排序**；
- 但很多传统做法是先做点预测（回归/分类），再拿输出排序；
- 这在目标函数上和“最终要排好序”并不一致；
- 所以应该直接用 pairwise / listwise 的 LTR 方法来优化排序本身。

### 论文的重要实验设定

从正文可抽出的关键设定：

- 研究对象：US equities
- 重平衡频率：**月频**
- 组合构建：**long/short decile portfolios**
- 交易成本考虑：作者明确说明月频是为了避免日频带来的过高成本
- 代表模型：`LambdaMART`、`ListNet`、`ListMLE`
- 结论：LTR 模型，特别是 `LambdaMART`，在排序精度和策略表现上优于常规 pointwise 方法

### 对我们项目最重要的可迁移点

1. **你的问题本质上也是排序问题**
   - 当前项目主线就是：`qlib_score -> rank -> Top30/Top50 -> 组合规则`
   - 所以论文和你的问题结构高度一致。

2. **qlib 不该被推翻，而该被二阶段利用**
   - 论文不是在说“传统分数毫无价值”；
   - 它是在说：传统预测输出之后，应该再做更符合目标的排序层。
   - 对你项目来说，最自然的做法就是：
     - 第一阶段保留 qlib baseline
     - 第二阶段做 LTR rerank

3. **LTR 比起回归更符合你的产品语义**
   - 前端要展示的是“今天哪些更值得先看”；
   - 用户并不需要一个伪装成收益率的分数；
   - LTR 的输出天然更符合“研究排序”而不是“收益预测”。

### 不可直接照搬的部分

- 论文使用的是 US equities 和它自己的 momentum 输入；
- 你当前不是要重建论文里的整套特征工程，而是把其“目标函数和问题形式”迁移到台股项目；
- 论文是月频 decile long/short，你项目当前以日频研究、长仓视角和只读回放为主，不能简单照抄组合构建。

### 结论

- **强适合当前项目**；
- 是最值得进入实现主线的论文；
- 第一版应采用 `LambdaMART` 这类解释性强、样本效率较高的方法，而不是一开始上深度排序网络。

---

## 3.2 2105.10019：Context-Aware Re-Ranking

论文：**Enhancing Cross-Sectional Currency Strategies by Context-Aware Learning to Rank with Self-Attention**

### 论文真正解决的问题

这篇论文不是在否定 LTR，而是在指出：

- 全局训练出的 ranker 虽然平均有效；
- 但它忽略了**每次调仓时局部上下文的差异**；
- 这会导致在某些特殊环境下，尤其 risk-off 时刻，排序失真；
- 结果不是平均表现差，而是容易在关键阶段遭遇不必要的大回撤。

### 论文的重要实验设定

正文中的关键点：

- 研究对象：**31 currencies**
- 重平衡频率：**日频**
- 先有一个 baseline ranker（如 `ListNet`、`LambdaMART`）
- 再把 top / bottom 已排序资产子集送入 **Transformer-based context-aware reranker**
- 文中直接写明：
  - `re-rank the top 10` and pick `top 3`
  - `re-rank the bottom 10` and pick `bottom 3`
- risk-off 定义使用 **VIX 相对其滚动均值的抬升**
- 报告结果：Sharpe 提升约 30%，且在 normal 与 risk-off 条件下都改善，risk-off 改善更明显

### 对我们项目最重要的可迁移点

1. **全局排序器在特殊市场环境下会失真**
   - 这和你项目之前的实际问题高度一致：
     - 牛市表现较好的规则，在熊市会变差；
     - 同样的 score，在不同市场状态下含义不同。

2. **context-aware rerank 很适合做在 qlib/LTR 之后**
   - 论文结构是：先初排，再局部 rerank；
   - 你项目最适合的对应结构也是：
     - qlib baseline
     - LTR second-stage
     - context/regime-aware rerank 或 gating

3. **risk-off 强化是重点，不是平均 everywhere 优化**
   - 论文强调的是关键阶段的排序质量；
   - 这很适合你当前目标：
     - 正常市况不破坏已有有效策略；
     - 差市况尽量别被大盘拖下水。

### 不应直接照搬的部分

- 不建议当前项目直接上 Transformer reranker：
  - 样本规模有限；
  - 解释成本高；
  - 工程复杂度高；
  - 对当前用户价值不一定大于轻量版本。

### 应如何迁移

论文的**思想应保留，结构应简化**：

- 不做复杂 self-attention reranker 作为第一步；
- 先做 **three-state regime gating**：
  - `normal`
  - `caution`
  - `risk_off`
- 在 `caution/risk_off` 环境下：
  - 提高新补仓阈值；
  - 降低允许替换数量；
  - 增强对价格位置风险与流动性约束的权重。

### 结论

- **强适合其核心思想**；
- **不适合当前阶段直接照搬其 Transformer 架构**；
- 适合转化为轻量的 `context-aware rerank / regime gating`。

---

## 3.3 2302.10175：Spatio-Temporal Momentum

论文：**Spatio-Temporal Momentum: Jointly Learning Time-Series and Cross-Sectional Strategies**

### 论文真正解决的问题

这篇论文在批判两个经典范式：

- time-series momentum 只看单资产自己的时间趋势；
- cross-sectional momentum 虽然比较了资产相对位置，但在构建分数时仍然主要依赖各资产自身历史；
- 两者都没有充分利用“其他资产也携带当前市场状态信息”这一点。

作者的核心想法是：

- 直接联合建模多资产随时间变化的 momentum 特征；
- 一次性输出整个资产池的 trading signals；
- 不再依赖传统 decile rank 决策；
- 用 Sharpe ratio 直接做优化目标；
- 再通过 `L1 shrinkage + turnover regularization` 控制可执行性。

### 论文的重要实验设定

正文中的关键点：

- 研究对象：
  - 46 actively-traded US equities
  - 12 equity index futures
- 频率：**日频**
- 回测区间：
  - equities 1990–2022
  - futures 2003–2020
- 特征：
  - 多时间尺度波动归一化收益：1 / 20 / 63 / 126 / 252 天
  - MACD 不同尺度组合
- 输出：对所有资产直接生成信号
- 优化：直接优化 **Sharpe ratio**
- 交易成本测试：**5–10 bps**
- 结论：在高交易成本下，`least absolute shrinkage + turnover regularization` 的版本最稳

### 对我们项目最重要的可迁移点

1. **时间序列特征和横截面信息应该一起进入模型**
   - 这和你当前数据条件是吻合的：
     - 时间序列层：MA / RSI / MACD / ret20 / vol20
     - 横截面层：qlib rank / percentile / zscore
     - 市场层：TWII / breadth / drawdown

2. **“其他股票的特征也能帮助判断这支股票”这一点是重要启发**
   - 论文在 SHAP 分析里还发现，某股票的预测，重要特征并不全来自它自己，还来自别的资产；
   - 这支持你后续做 cross-asset / market-context feature aggregation。

3. **turnover regularization 是实用而不是装饰**
   - 论文明确指出，在成本场景下，turnover regularization 带来稳定改进；
   - 这和你项目当前痛点完全一致。

### 为什么不适合作为当前第一步直接实现

- 它是 joint-signal 神经网络；
- 需要更复杂的数据组织、训练和解释；
- 你的项目当前已经明确不想走“更黑的模型优先”这条路；
- 对用户来说，直接抛弃 rank-based 结构也会破坏现有产品心智。

### 应如何迁移

这篇论文不适合作为当前第一优先级模型，但非常适合提供两条原则：

1. **LTR reranker 的输入要同时包含时间趋势和横截面特征**；
2. **组合层必须显式做 turnover regularization / turnover budget**。

### 结论

- **思想适合，直接照搬不适合**；
- 当前阶段只吸收：
  - multi-asset context input
  - transaction-cost-aware turnover control

---

## 3.4 2605.01176：Decision-Focused Learning 的信号膨胀与过度换手

论文：**Decision-Induced Ranking Explains Prediction Inflation and Excessive Turnover in SPO-Based Portfolio Optimization**

### 论文真正解决的问题

这篇论文非常关键，因为它不是在吹“端到端更强”，而是在解释：

- decision-focused learning 虽然看起来目标更对；
- 但一旦输出直接喂给下游优化器；
- 很容易出现 **prediction inflation** 和 **excessive turnover**；
- 结果是组合动作不稳定，不可实现。

### 论文的重要机制结论

正文给出的核心解释是：

- 下游优化器真正使用的，不是裸预测收益；
- 而是**风险和交易成本调整后的 marginal score**；
- 所以模型学到的其实更像“排序驱动的决策信号”；
- 如果没有约束，这个信号很容易被放大，导致频繁剧烈调仓。

### 论文的重要工程建议

作者实际测试了三类稳定机制：

1. **prediction clipping**
   - 限制预测值范围，抑制极端输出
2. **min-max rescaling**
   - 对整体预测向量缩放
3. **partial portfolio adjustment**
   - 不一次性完全换仓，而是部分调整

论文结论很明确：

- 单纯调大 risk aversion **不能有效解决换手问题**；
- clipping 有帮助，但本身不是最强；
- **partial adjustment** 才是降低 turnover 的主机制；
- `Clip + Adj` 最稳健。

### 为什么这篇对你项目极其重要

因为它几乎正面回答了你一直问的问题：

- 为什么会高点买、低点卖？
- 为什么只看排名变化容易出问题？
- 为什么模型再复杂，最终动作还是可能很差？

答案不是“模型必须更强”，而是：

- **排序信号和组合动作之间，必须加稳定层**。

### 对当前项目的直接迁移

这篇论文几乎可以直接转化为工程约束：

1. `score clipping / confidence clipping`
2. `no_trade_buffer`
3. `confidence_gap`
4. `partial rebalance`
5. `max actions per day`
6. `turnover budget`

### 结论

- **极强适配**；
- 不是拿来做 alpha 模型，而是拿来设计组合层；
- 对当前项目的价值，甚至高于再找一个更复杂的预测模型。

---

## 3.5 1904.08925：交易成本如何系统性吃掉组合收益

论文：**The impact of proportional transaction costs on systematically generated portfolios**

### 论文真正解决的问题

这篇论文不是 alpha 论文，而是可执行性论文。它回答的是：

- 交易成本到底会怎样系统性改变组合表现；
- 交易频率、换仓频率、成分更新频率、成分数这些配置如何影响净结果；
- 是否可以通过 smoothing transaction costs 的方式改善表现。

### 论文的重要经验结论

全文反复强调的结论包括：

- 即使很小的比例交易成本，也会显著影响最终表现；
- 在有成本时，高频调仓可能明显伤害组合；
- 同样成本率下，**更低的更新频率 / renewing frequency** 往往更优；
- 交易成本不是只体现在扣掉几笔手续费，它还会扭曲财富路径；
- 可以通过 smoothing / dynamic adjustment 让组合更平滑。

### 对当前项目的意义

这篇论文从另一个角度支持了你项目当前很需要的一点：

- 即便排序是对的，**换仓节奏**仍然可能决定策略是否可用；
- 所以前端展示“动作次数”“手续费后收益”“最大回撤”必须和总收益一起出现；
- 你的模拟账户和策略回放不能只展示毛收益率。

### 对当前项目的直接迁移

1. 组合回放验收指标必须包含：
   - gross return
   - fee/tax-adjusted net return
   - turnover / action count
   - max drawdown
2. 规则层要支持：
   - 低频再平衡
   - 成分更新节奏控制
   - 换仓平滑
3. 前端要明确告诉用户：
   - “高收益但高换手”不一定真优于“中等收益但低换手”。

### 结论

- **强适合**；
- 是组合层和评估层必须吸收的论文；
- 不直接提供新 alpha，但直接提升策略可信度与产品质量。

---

## 3.6 1707.05552：市场状态依赖性

论文：**Wax and wane of the cross-sectional momentum and contrarian effects**

### 论文真正解决的问题

这篇论文关注的是：

- 横截面动量 / 反转效应并不是恒定有效；
- 它们会随着市场状态、波动、流动性、不确定性变化而变化；
- 这符合 Adaptive Markets Hypothesis 的框架。

### 论文的重要经验结论

从正文提炼出的关键点：

- 套利机会和风险溢价关系是 **time-varying** 的；
- 策略表现具有明显 **context dependence**；
- 在其样本中：
  - upward trend market state
  - higher market volatility
  - higher market liquidity
  - lower macro uncertainty
  往往对应更高的 contrarian profitability。

### 对当前项目的意义

虽然论文研究的是中国市场中的 contrarian/CSMOM 效应，但它支持了一条非常重要的产品认知：

- 同一套排序或轮动规则，不该假设它在所有市场状态都同样有效；
- 这也是你之前 repeatedly 遇到的问题：
  - 2022 和 2025 的有效策略不一样；
  - 熊市/差市况不应该机械照搬牛市规则。

### 不应直接照搬的部分

- 这篇论文不是台股专门研究；
- 它的一些宏观和流动性刻画方式，不一定能直接映射到你当前项目；
- 它支持的是“需要 regime awareness”，而不是给你一个现成模型。

### 结论

- **适合做理论支撑**；
- 不适合作为直接实现模板；
- 但足以支撑你把 `market state / volatility / liquidity / uncertainty proxy` 放进 regime-aware 模块。

---

## 4. 跨论文综合：哪些共识最重要

把这几篇论文放在一起，不难发现有三个稳定共识。

### 共识一：横截面策略的核心是排序，不是点预测

- 2012.07149 直接支持这一点；
- 2605.01176 也从 decision perspective 说明下游真正关心的是排序驱动的 marginal signal；
- 对你项目来说，这意味着：
  - 不要把 `qlib_score` 继续解释成收益率；
  - 也不应把下一阶段设计成“回归未来收益率”的普通模型；
  - 应该直接做 **排序层优化**。

### 共识二：平均有效不够，关键阶段更重要

- 2105.10019 强调 risk-off 排序失真；
- 1707.05552 强调 market-condition dependence；
- 对你项目来说，这意味着：
  - 下一阶段不能只看 overall Sharpe；
  - 要分 normal / caution / risk_off 看表现。

### 共识三：换手控制不是附属功能，而是主策略的一部分

- 2302.10175 强调 turnover regularization；
- 2605.01176 强调 partial adjustment 是稳定主机制；
- 1904.08925 从经验上说明交易成本会系统性改变结果；
- 对你项目来说，这意味着：
  - 组合层要成为主线，而不是事后修补。

---

## 5. 对当前项目最合理的整合方案

基于全文深读后的结论，当前项目最合理的新主线应收敛为：

```text
Stage 1: qlib baseline score/rank
Stage 2: LTR reranker
Stage 3: regime-aware gating / context rerank
Stage 4: turnover-controlled portfolio layer
Stage 5: readonly replay + frontend explanation
```

### 5.1 Stage 1 保留 qlib baseline

理由：

- qlib baseline 已经稳定；
- 也已被前面多轮工作验证为当前产品主心骨；
- 论文没有任何一篇要求你推翻 baseline。

### 5.2 Stage 2 引入 LTR reranker

建议：

- 第一版用 `LambdaMART`
- 输入特征：
  - qlib score / rank / percentile / zscore
  - MA / RSI / MACD / Bollinger / ret20 / vol20
  - liquidity proxies
  - TWII / breadth / drawdown / volatility

目标：

- 不是预测收益率；
- 而是在每日横截面上更好地排序候选股票。

### 5.3 Stage 3 引入 regime-aware 轻量自适应

建议：

- 用当前已有特征定义三态：
  - `normal`
  - `caution`
  - `risk_off`
- 只做轻量 gating：
  - 新入选阈值
  - 允许替换数量
  - 风险/流动性约束强度

不建议：

- 第一版直接做 Transformer context reranker

### 5.4 Stage 4 加入 turnover-controlled portfolio layer

建议：

- `no_trade_buffer`
- `confidence_gap`
- `partial_rebalance`
- `min_holding_days`
- `turnover_budget`
- `score clipping`

理由：

- 这是最直接对应论文 2605.01176 和 1904.08925 的工程实现；
- 也是最能避免“高点买入、低点卖出”的部分。

### 5.5 Stage 5 只读回放与前端解释

前端应解释的是：

- baseline 高不高
- reranker 上调还是下调
- 当前市场状态是什么
- 为什么今天不建议替换（即使 baseline 高）
- 是被换手预算、价格位置风险还是流动性约束挡住

这比继续堆更多“神秘分数”更符合用户第一性原则。

---

## 6. 当前不应进入主线的方向

### 6.1 直接做 end-to-end decision model v2

原因：

- 2605.01176 明确提示这类方法容易带来 prediction inflation 与 turnover；
- 你项目前一轮主线已经证明复杂模型未必优于 baseline；
- 当前最缺的是稳定层，不是更大的端到端模型。

### 6.2 直接做 Transformer / self-attention reranker

原因：

- 2105.10019 的思想对，但架构太重；
- 当前项目的第一步应先拿到轻量、清晰、可解释的改进。

### 6.3 把还没 PIT 安全的 FinMind 特征强行纳入主线

原因：

- 会破坏研究可信度；
- 与“严谨分析如何结合进我们的项目”的要求相冲突。

---

## 7. 最终收敛结论

如果把这轮论文深读压缩成一句话：

**当前项目最该做的，不是继续追求更复杂预测模型，而是把“排序、市场状态、换手控制”这三层真正做完整。**

更具体地说：

1. 用 `qlib` 做 baseline
2. 用 `LTR` 做第二阶段横截面重排序
3. 用 `regime-aware gating` 处理不同市场状态
4. 用 `turnover-controlled portfolio layer` 把动作变得可执行
5. 用前端解释层把这些原因讲清楚

这是目前：

- 证据最充分；
- 最符合现有数据条件；
- 最符合用户第一性原则；
- 也最可能在项目里真正落地的一条路线。

---

## 8. 下一步建议

推荐下一步直接进入新的实现方案文档，主题应收敛为：

**`TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`**

文档中应至少包含：

1. 数据与标签设计
2. LTR baseline 训练方案
3. Regime 定义与 gating 规则
4. Portfolio layer 约束与回放口径
5. 前端解释字段与展示方式
6. 分 phase 执行与审查合同

---

## 9. 参考论文

- Building Cross-Sectional Systematic Strategies By Learning to Rank  
  https://arxiv.org/abs/2012.07149
- Enhancing Cross-Sectional Currency Strategies by Context-Aware Learning to Rank with Self-Attention  
  https://arxiv.org/abs/2105.10019
- Spatio-Temporal Momentum: Jointly Learning Time-Series and Cross-Sectional Strategies  
  https://arxiv.org/abs/2302.10175
- Decision-Induced Ranking Explains Prediction Inflation and Excessive Turnover in SPO-Based Portfolio Optimization  
  https://arxiv.org/abs/2605.01176
- The impact of proportional transaction costs on systematically generated portfolios  
  https://arxiv.org/abs/1904.08925
- Wax and wane of the cross-sectional momentum and contrarian effects: Evidence from the Chinese stock markets  
  https://arxiv.org/abs/1707.05552
