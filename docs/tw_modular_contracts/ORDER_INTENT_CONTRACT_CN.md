# OrderIntentArtifact 合同

生成日期：2026-06-16

## 1. 目的

`OrderIntentArtifact` 是策略规则输出给回放执行模块的标准意图产物。它表达“在某个 signal date，策略希望买入、卖出或跳过什么”，但不表达真实成交结果。

成交价格、成交日期、手续费、交易税、现金、持仓和净值只能由 ReplayExecution / ReplayResult 处理。

## 2. Artifact 结构

推荐目录：

```text
data_tw/artifacts/strategies/{strategy_rule}/{run_id}/
```

必需文件：

```text
manifest.json
order_intents.csv
schema.json
strategy_decision_audit.csv
forbidden_action_audit.json
```

## 3. Required Fields

`order_intents.csv` 必须包含：

| field | type | required | 语义 |
| --- | --- | --- | --- |
| signal_date | YYYY-MM-DD | yes | 策略读取信号并产生意图的日期。 |
| instrument | string | yes | 标准股票代码，使用 `TWxxxx` 格式。 |
| intent_action | enum | yes | `buy`、`sell`、`hold`、`skip`。 |
| intent_reason | string | yes | 规则原因，例如 `top50_exit_sell`、`buy_score_top_candidate`。 |
| strategy_rule | string | yes | 产生意图的规则名称。 |
| candidate_rank | numeric | yes | 产生意图时使用的 qlib candidate rank。 |
| buy_rank | numeric | yes | 产生意图时根据 `buy_score` 得到的买入排序。 |
| full_qlib_rank | numeric | yes | 产生意图时使用的完整 qlib rank。 |
| max_buy_count | int | yes | 当日规则允许最大买入意图数。 |
| max_sell_count | int | yes | 当日规则允许最大卖出意图数。 |
| model_name | string | yes | 信号来源模型名称。 |
| signal_artifact | string | yes | 输入 `ModelSignalArtifact` manifest 路径。 |

可选审计字段：

```text
portfolio_state_artifact
current_holding_flag
target_holding_count
candidate_k
tie_breaker
diagnostic_only
partial_intent_kind
partial_intent_policy
partial_intent_note
```

`partial_intent_*` 仅用于 simulation-only partial intent 的研究诊断，不得表达数量、仓位、权重、现金、成交或 broker/order 信息。

## 4. 行为语义

- `buy` 表示策略希望买入该标的，但是否成交由回放执行模块决定。
- `sell` 表示策略希望卖出该标的，但卖出数量、价格和成交日由回放执行模块决定。
- `hold` 表示规则明确保留持仓，通常用于审计，不要求执行模块产生交易。
- `skip` 表示规则明确跳过，必须提供 `intent_reason`。
- 若 `signal_date` 是窗口最后一天且无下一交易日价格，ReplayExecution 决定是否 skip，OrderIntent 不得提前伪造成交。

Simulation-only partial intent 只能通过意图原因表达，不得通过数量或目标仓位表达：

```text
intent_action=buy
intent_reason=simulated_buy_small
primary_reason_code=simulated_buy_small

intent_action=sell
intent_reason=simulated_reduce_partial
primary_reason_code=simulated_reduce_partial
```

上述 partial intent 仍然只是研究意图，必须同时满足 `readonly_only=true`、`simulation_only=true`、`not_order=true`、`not_target_position=true`、`not_investment_advice=true`。

## 5. Forbidden Fields

`order_intents.csv` 不得包含：

```text
execution_date
execution_price
execution_quantity
quantity_to_buy
quantity_to_sell
shares
lots
target_position
target_weight
allocation_weight
commission
fee
tax
cash
cash_after
nav
equity
daily_return
realized_pnl
unrealized_pnl
replay_return
execution_date
execution_price
broker
broker_order_id
order_id
quick_trade
provider_publish_status
accepted_latest_status
```

不得包含 future label 或 future return 字段：

```text
future_return_*
future_excess_return_*
forward_return_*
label_*
relevance_10d_top_heavy
ltr_relevance_label
```

## 6. Forbidden Actions

生成 `OrderIntentArtifact` 时禁止：

- 训练模型；
- 调参；
- 重跑收益筛选；
- 读取模型私有文件；
- 读取未来价格或未来收益；
- 写入成交账本；
- 修改默认策略；
- 修改前端；
- 修改日更主链路；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker、quick-trade 或 order 行为。

## 7. buggy_e8r 边界

当 `strategy_rule = one_sell_one_buy_buggy_e8r` 时：

- `diagnostic_only` 必须为 true；
- manifest 必须声明 `not_valid_strategy_evidence: true`；
- 该产物只能用于历史 bug 复现、差异归因和审计；
- 不得进入默认策略、收益筛选、产品展示或日更 publish。

## 8. 最小校验

OrderIntent validator 至少检查：

- required fields 全部存在；
- `intent_action` 值域合法；
- 每日 buy/sell 意图数不超过规则配置；
- 不含成交、现金、净值、PnL、broker 字段；
- 不含 future label / future return 字段；
- diagnostic 规则只能输出 diagnostic artifact。
