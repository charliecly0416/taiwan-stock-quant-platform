# ReplayResultArtifact 合同

生成日期：2026-06-16

## 1. 目的

`ReplayResultArtifact` 是回放执行模块的标准输出。它只消费 `OrderIntentArtifact`、历史价格源、执行配置和初始组合状态，负责 next-day execution、费用、税费、现金、持仓、净值和审计。

回放模块不训练模型、不选择股票、不读取模型私有文件、不修改默认策略。

## 2. Artifact 结构

推荐目录：

```text
data_tw/artifacts/replays/{replay_name}/{run_id}/
```

必需文件：

```text
manifest.json
summary.csv
actions.csv
daily_nav.csv
position_snapshots.csv
coverage_audit.csv
position_integrity_audit.csv
forbidden_field_audit.csv
execution_audit.csv
forbidden_action_audit.json
```

可选文件：

```text
skipped_actions.csv
daily_cash_audit.csv
input_manifest_links.json
```

## 3. 输入

ReplayExecution 标准输入：

```text
OrderIntentArtifact
PriceStore
ExecutionConfig
InitialPortfolioState
```

不得直接读取 legacy 模型私有文件或训练产物。若回放需要模型相关字段，只能从 OrderIntent 的审计字段或其指向的标准 `ModelSignalArtifact` manifest 溯源。

## 4. Required Fields / Outputs

`summary.csv` 必需字段：

```text
window
model_name
model_family
strategy_rule
start_date
end_date
initial_cash
final_equity
total_return
max_drawdown
action_count
buy_count
sell_count
skipped_action_count
max_holding_count
duplicate_position_count
negative_cash_count
missing_price_count
diagnostic_only
```

`actions.csv` 必需字段：

```text
signal_date
execution_date
instrument
action
quantity
execution_price
commission
tax
cash_after
position_after
intent_reason
strategy_rule
model_name
order_intent_artifact
```

`daily_nav.csv` 必需字段：

```text
date
cash
market_value
equity
daily_return
holding_count
missing_price_count
```

`position_snapshots.csv` 必需字段：

```text
date
instrument
quantity
cost_basis
mark_price
market_value
unrealized_pnl
strategy_rule
model_name
```

`execution_audit.csv` 必需字段：

```text
audit_name
status
value
threshold
details
```

`coverage_audit.csv` 必需字段：

```text
audit_name
requested_start_date
requested_end_date
actual_start_date
actual_end_date
trading_day_count
signal_day_count
price_day_count
missing_signal_day_count
missing_price_day_count
status
details
```

`coverage_audit.csv` 最小检查项：

- `actual_start_date >= requested_start_date`；
- `actual_end_date <= requested_end_date`；
- 回放窗口不得越过请求窗口；
- 每个 replay day 的 signal / price 覆盖必须可追溯；
- 缺失 signal 或 price 必须有 skip/audit 说明。

`position_integrity_audit.csv` 必需字段：

```text
audit_name
date
instrument
status
value
threshold
details
```

`position_integrity_audit.csv` 最小检查项：

- active action quantity > 0；
- `execution_date > signal_date`；
- `max_holding_count <= target_holding_count`；
- duplicate position day/instrument 为 0；
- negative cash 为 0，除非 execution config 明确允许融资且审计标记；
- final holdings 完成 mark-to-market；
- skipped action reason 可追溯。

`forbidden_field_audit.csv` 必需字段：

```text
audit_name
artifact
field_name
field_category
present
used_for_ranking
status
details
```

`forbidden_field_audit.csv` 最小检查项：

- future label / future return 字段不存在；
- forbidden model/private 字段未被 ReplayExecution 读取；
- realized PnL、成交结果、持仓字段未参与策略 ranking；
- `one_sell_one_buy_buggy_e8r` 只能标记为 diagnostic result。

## 5. 执行语义

- `execution_date` 必须晚于 `signal_date`，通常为下一可交易日。
- 回放成交只能使用执行配置允许的价格字段，例如 next open 或 next close。
- 若缺失价格，必须记录 skip 或 audit，不得静默成交。
- 回放可计算收益、回撤、现金和持仓，但不得反向修改 OrderIntent。
- 回放不得根据收益自动选择最佳策略。

## 6. Forbidden Fields

Replay 输入侧不得读取：

```text
future_return_*
future_excess_return_*
forward_return_*
label_*
relevance_10d_top_heavy
ltr_relevance_label
phasee6_branch_a_fresh_ltr_score
phasee6_branch_b_frozen_ltr_score
phasee3_extended_oos_ltr_score
adaptive_score_baseline
qlib_score_raw
qlib_rank_raw
```

Replay 输出不得包含真实 broker/order 字段：

```text
broker_order_id
broker_account
quick_trade_status
real_order_status
provider_publish_status
accepted_latest_status
monitor_config_write_status
```

## 7. Forbidden Actions

生成 `ReplayResultArtifact` 时禁止：

- 训练模型；
- 调参；
- 重跑模型分数；
- 修改信号排序；
- 修改 OrderIntent；
- 根据收益自动改默认策略；
- 修改前端；
- 修改日更主链路；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker、quick-trade 或 order 行为。

## 8. buggy_e8r 边界

若输入规则为 `one_sell_one_buy_buggy_e8r`：

- `summary.csv.diagnostic_only` 必须为 true；
- manifest 必须声明 `not_valid_strategy_evidence: true`；
- 输出只能用于历史 bug 诊断和归因；
- 不得被纳入默认策略候选、收益筛选结论、产品展示或日更 publish。

## 9. 最小校验

Replay validator 至少检查：

- required output files 存在；
- `coverage_audit.csv`、`position_integrity_audit.csv`、`forbidden_field_audit.csv` 存在且 status 非 fail；
- `actual_start_date >= requested_start_date`；
- `actual_end_date <= requested_end_date`；
- `execution_date > signal_date`；
- active action quantity > 0；
- `max_holding_count <= target_holding_count`；
- duplicate position day/instrument 为 0；
- negative cash 为 0，除非 execution config 明确允许融资且审计标记；
- final holdings 完成 mark-to-market；
- missing price 有 skip/audit 记录；
- 不读取 forbidden model/private/future 字段；
- diagnostic rule 不作为有效策略收益证据。
