# StrategyRuleContract 合同

生成日期：2026-06-16

## 1. 目的

`StrategyRuleContract` 定义策略规则模块的输入、输出和安全边界。策略模块只消费标准 `ModelSignalArtifact`、当前 `PortfolioState` 和 `StrategyRuleConfig`，输出 `OrderIntentArtifact`。

策略模块不读取模型私有文件、不训练模型、不计算成交、不记账、不读取未来价格或未来收益。

## 2. 输入

策略模块标准输入：

```text
ModelSignalArtifact
PortfolioState
StrategyRuleConfig
```

`ModelSignalArtifact` 必需字段：

```text
date
instrument
model_name
model_family
candidate_rank
buy_score
raw_score
score_rank
full_qlib_rank
signal_asof
available_at
source_artifact
```

`PortfolioState` 必需字段：

```text
asof_date
instrument
quantity
cost_basis
current_holding_flag
```

`StrategyRuleConfig` 必需字段：

```text
strategy_rule
target_holding_count
candidate_k
max_buy_count
max_sell_count
sell_boundary
buy_order
tie_breaker
allow_diagnostic_rule
```

## 3. 输出

策略模块输出：

```text
OrderIntentArtifact
```

策略输出必须是意图，不得包含实际成交价、成交日期、手续费、税费、现金、净值或 broker 订单编号。

## 4. 当前规则冻结

| rule | status | 语义 |
| --- | --- | --- |
| original | valid | 以 top10/buy list 为主要持仓边界，买入顺序来自 top50 内 `buy_score`。 |
| top50_exit_all | valid | 卖出所有跌出 qlib top50 的持仓，并按 `buy_score` 补入。 |
| top50_exit_one_worst_sell | valid | 满仓后若有持仓跌出 qlib top50，只卖出 `full_qlib_rank` 最差的一支，再买入 top50 内 `buy_score` 最高且未持有标的。 |
| one_sell_one_buy_correct | valid | 每日最多一卖一买；top50 外持仓优先卖，若仍需调整则卖出买入排序最差的持仓。 |
| one_sell_one_buy_buggy_e8r | diagnostic only | 历史 bug 复现和异常归因专用，不得作为策略收益证据、默认策略或产品展示候选。 |

## 5. 排序字段语义

`candidate_rank`：

- 决定 qlib top50 universe / exit boundary。
- 策略只能用它判断是否在候选池内。

`buy_score`：

- 决定 top50 内买入顺序。
- 不能用于替代 `candidate_rank` 判断 top50 边界。

`full_qlib_rank`：

- 当持仓跌出 top50 或需要比较 qlib rank 最差持仓时使用。
- 不能由 LTR rank 替代。

## 6. qlib 与 LTR 规则一致性

策略规则必须对 qlib 与 LTR 使用同一套标准字段：

- 纯 qlib：`candidate_rank` 与 `buy_score` 均来自 qlib 体系；
- LTR：`candidate_rank` 仍来自底座 qlib，`buy_score` 来自 LTR rerank score；
- 策略不得根据 `model_family` 改变 sell boundary；
- LTR 不得通过策略规则静默改变 qlib top50 universe。

## 7. Forbidden Fields

策略模块不得读取或依赖以下字段：

```text
future_return_*
future_excess_return_*
forward_return_*
label_*
relevance_10d_top_heavy
ltr_relevance_label
realized_pnl
realized_return
execution_price
execution_date
next_open
next_close
broker_order_id
```

策略模块不得读取 legacy 私有模型列，例如：

```text
phasee6_branch_a_fresh_ltr_score
phasee6_branch_b_frozen_ltr_score
phasee3_extended_oos_ltr_score
adaptive_score_baseline
qlib_score_raw
qlib_rank_raw
```

这些字段必须先通过 `ModelSignalArtifact` adapter 映射成标准字段。

## 8. Forbidden Actions

策略模块禁止：

- 读取模型私有文件；
- 训练模型；
- 调参；
- 改 universe；
- 读 future return / label；
- 读未来价格；
- 负责成交记账；
- 产生 replay 收益结论；
- 修改默认策略；
- 修改前端；
- 修改日更主链路；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker、quick-trade 或 order 行为。

## 9. 最小校验

Strategy validator 至少检查：

- 只读取标准信号字段；
- 输出 action 数不超过 `max_buy_count` / `max_sell_count`；
- `one_sell_one_buy_buggy_e8r` 标记为 `diagnostic_only`；
- 输出不含成交价、现金、净值、手续费、税费；
- 不存在 future label / future return 字段；
- qlib 与 LTR 只通过标准字段分发，不读 legacy 私有列。
