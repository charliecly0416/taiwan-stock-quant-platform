# 组合决策模型参考论文索引

生成日期：2026-06-15

本文献目录用于后续“组合决策模型 / 策略模型”主线参考。

使用原则：

```text
论文只提供方法参考；
不得把论文结论直接当成台股策略收益承诺；
不得跳过本项目自己的 PIT、费用税费、next-day execution 和用户第一性原则审查。
```

## 1. LTR 与横截面排序

### 1.1 Building Cross-Sectional Systematic Strategies By Learning to Rank

本地文件：

```text
docs/references/portfolio_decision_model_papers/2012.07149_learning_to_rank_cross_sectional_strategies.pdf
```

后续参考方式：

- 参考“投资组合选股本质上是排序问题”的建模视角；
- 参考 pairwise/listwise ranking 对横截面选股的意义；
- 用于理解 qlib -> LTR rerank 为什么是合理路线。

不应照搬：

- 不应假设论文结果能直接迁移到台股 150 股票池；
- 不应在没有正交特征的情况下继续无限调 LTR。

### 1.2 Context-Aware Re-Ranking with Self-Attention

本地文件：

```text
docs/references/portfolio_decision_model_papers/2105.10019_context_aware_ltr_self_attention.pdf
```

后续参考方式：

- 参考“同一个排序模型在不同市场上下文中表现不同”的思想；
- 参考 context-aware reranking 对 risk-off 阶段的意义；
- 可支持后续 market regime / risk context 特征进入策略模型。

不应照搬：

- 不建议当前阶段直接实现 self-attention reranker；
- 不应让复杂模型牺牲可解释性。

## 2. 时间序列 + 横截面联合建模

### 2.1 Spatio-Temporal Momentum

本地文件：

```text
docs/references/portfolio_decision_model_papers/2302.10175_spatio_temporal_momentum.pdf
```

后续参考方式：

- 参考“股票自身时间趋势 + 横截面相对排名”同时建模；
- 支持把 MA/RSI/MACD/ret/volatility 与 qlib/LTR ranking 一起作为策略模型输入；
- 支持后续把 market regime 纳入决策。

不应照搬：

- 不建议第一版直接上深度联合模型；
- 当前更适合先用可解释规则化优化器。

## 3. 交易成本、换手与组合层

### 3.1 The impact of proportional transaction costs on systematically generated portfolios

本地文件：

```text
docs/references/portfolio_decision_model_papers/1904.08925_transaction_costs_systematic_portfolios.pdf
```

后续参考方式：

- 参考交易成本如何改变系统化组合的净收益；
- 支持把手续费、交易税、换手率纳入策略目标函数；
- 支持 no-trade buffer、turnover penalty、partial rebalance。

不应照搬：

- 不应只报告毛收益；
- 不应忽略台股交易税和项目已有费用口径。

### 3.2 Decision-Induced Ranking Explains Prediction Inflation and Excessive Turnover

本地文件：

```text
docs/references/portfolio_decision_model_papers/2605.01176_decision_induced_ranking_turnover.pdf
```

后续参考方式：

- 参考 decision-focused / SPO 类方法可能导致过度换手的问题；
- 支持在策略模型中加入 clipping、rescaling、partial adjustment、turnover control；
- 支持“模型分数不能直接等于交易动作”的产品原则。

不应照搬：

- 不应为了提高回测收益放任高换手；
- 不应把分数膨胀当成真实收益能力。

## 4. 市场状态与动量/反转条件

### 4.1 Wax and wane of the cross-sectional momentum and contrarian effects

本地文件：

```text
docs/references/portfolio_decision_model_papers/1707.05552_momentum_contrarian_market_conditions.pdf
```

后续参考方式：

- 参考横截面动量/反转效应会随市场环境变化；
- 支持 normal / caution / risk-off 的市场状态设计；
- 支持在熊市、震荡市中避免机械追随排名。

不应照搬：

- 论文市场不是台股；
- 只能作为 regime-aware 思想支撑，不能直接变成台股规则。

## 5. 强化学习与组合管理

### 5.1 FinRL: A Deep Reinforcement Learning Library for Automated Stock Trading

本地文件：

```text
docs/references/portfolio_decision_model_papers/2011.09607_finrl_deep_reinforcement_learning_framework.pdf
```

后续参考方式：

- 参考 RL 交易系统的三层 pipeline；
- 参考交易环境、状态、动作、奖励、交易成本的组织方式；
- 若后续做离线 RL，可作为工程框架参考。

不应照搬：

- 不应直接接券商或自动交易；
- 不应跳过规则化优化器直接上 RL；
- 不应把 RL 回测当成实盘能力。

### 5.2 Deep Reinforcement Learning for Portfolio Management

本地文件：

```text
docs/references/portfolio_decision_model_papers/2012.13773_deep_rl_portfolio_management.pdf
```

后续参考方式：

- 参考 RL 如何学习组合权重调整；
- 参考状态/动作/奖励设计；
- 支持后续“动作不是买卖一支，而是调整权重”的建模方向。

不应照搬：

- 当前台股样本规模可能不足以支撑复杂 RL；
- 不应忽略过拟合和回测外失效风险。

### 5.3 Deep Reinforcement Learning for High Dimensional Stock Portfolio Management

本地文件：

```text
docs/references/portfolio_decision_model_papers/2112.04755_high_dimensional_stock_portfolio_rl.pdf
```

后续参考方式：

- 参考高维股票池下的 portfolio RL 设计；
- 对台股 150 股票池的动作空间设计有参考意义；
- 可用于评估是否需要先缩小候选池再做策略模型。

不应照搬：

- 不应直接把 150 支股票全部做连续动作空间；
- 需要先有候选池和动作约束。

### 5.4 RL under Transaction Cost / Market Impact

本地文件：

```text
docs/references/portfolio_decision_model_papers/2603.29086_rl_transaction_cost_market_impact.pdf
```

后续参考方式：

- 参考 RL 在交易成本、市场冲击下的风险；
- 支持把成本、滑点、换手、可成交性作为硬约束；
- 用于审查 RL 是否只是回测过拟合。

不应照搬：

- 若无法真实建模成本和成交约束，不应把 RL 策略产品化。

## 6. 后续最建议的使用顺序

建议后续主线按以下顺序引用：

1. 规则化组合优化器：
   - `1904.08925`
   - `2605.01176`
   - `1707.05552`
2. 策略模型监督学习：
   - `2012.07149`
   - `2302.10175`
   - `2105.10019`
3. 离线强化学习探索：
   - `2011.09607`
   - `2012.13773`
   - `2112.04755`
   - `2603.29086`

一句话：

```text
先用交易成本和换手论文约束策略动作，再用排序和上下文论文提升评分，最后才把 RL 当研究支线。
```
