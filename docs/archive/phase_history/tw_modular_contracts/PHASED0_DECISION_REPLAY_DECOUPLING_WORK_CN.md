# Phase D0 决策与回放解耦合同冻结工作文档

生成日期：2026-06-17

## 1. D0 范围

D0 只做合同冻结与可行性审计，不抽代码、不生成正式 `OrderIntentArtifact`、不改回放行为、不接前端/API。

D0 的目标是回答四个问题：

1. 现有五种冻结规则是否都能被 `OrderIntentArtifact` 表达；
2. 当前 `ModelSignalArtifact` 是否足够作为 `StrategyDecisionEngine` 输入；
3. 当前 replay 是否可以改造成只消费 order intent 的 `ReplayExecutionEngine`；
4. readonly snapshot 是否只保留展示职责，而不是 canonical 决策输入。

## 2. 冻结链路

后续主线冻结为：

```text
ModelSignalArtifact
  -> StrategyDecisionEngine
  -> OrderIntentArtifact
  -> ReplayExecutionEngine
  -> ReplayResultArtifact
  -> Readonly API / Frontend Display
```

D1 之前不得把前端/API 接入新链路；D3 parity 通过前，不得将新 replay 结果作为展示或产品化依据。

## 3. 决策输入冻结

`StrategyDecisionEngine` 后续只允许读取：

```text
ModelSignalArtifact
PortfolioState
StrategyRuleConfig
```

`ModelSignalArtifact` 最低字段：

```text
date
instrument
candidate_rank
buy_score
score_rank
full_qlib_rank
signal_asof
available_at
```

不得读取：

```text
future_return_*
future_excess_return_*
forward_return_*
label_*
relevance_10d_top_heavy
ltr_relevance_label
realized_pnl
execution_price
execution_date
equity
cash
drawdown
broker_order_id
```

## 4. OrderIntentArtifact 冻结字段

D1 生成的 `order_intents.csv` 至少包含：

```text
signal_date
instrument
intent_action
intent_reason
strategy_rule
candidate_rank
buy_rank
full_qlib_rank
max_buy_count
max_sell_count
model_name
signal_artifact
```

只允许表达策略意图：

```text
buy
sell
hold
skip
```

不得包含成交价、成交日期、成交数量、手续费、税费、现金、净值、PnL、broker/order id。

## 5. 五规则表达冻结

五种规则均可表达为 OrderIntent：

| rule | sell intent | buy intent | D0 status |
| --- | --- | --- | --- |
| original | 卖出不在 buy top10 的持仓 | qlib top50 内按 buy_score 选择候选 | pass |
| top50_exit_all | 卖出所有跌出 qlib top50 的持仓 | qlib top50 内按 buy_score 选择候选 | pass |
| top50_exit_one_worst_sell | 最多卖出一支 top50 外且 full_qlib_rank 最差持仓 | qlib top50 内按 buy_score 选择候选 | pass |
| one_sell_one_buy_correct | 每日最多一卖；top50 外优先，否则卖买入排序最差持仓 | 每日最多一买 | pass |
| one_sell_one_buy_buggy_e8r | 仅 diagnostic 的历史 bug 卖出复现 | 仅 diagnostic 的买入复现 | pass |

`one_sell_one_buy_buggy_e8r` 必须保持：

```text
diagnostic_only=true
not_valid_strategy_evidence=true
```

## 6. ReplayExecutionEngine 冻结边界

D2 后 replay 只允许消费：

```text
OrderIntentArtifact
PriceStore
ExecutionConfig
InitialPortfolioState
```

ReplayExecutionEngine 负责：

- next-day execution；
- quantity sizing；
- execution price；
- commission / tax；
- cash / holdings；
- daily nav / return / drawdown / turnover；
- coverage / integrity / forbidden field audit。

ReplayExecutionEngine 不得：

- 调用 `choose_sells()`；
- 根据 `strategy_rule` 内联决定卖什么；
- 读取模型私有字段；
- 读取 future return / label；
- 反向修改 OrderIntent；
- 根据收益自动选择默认策略。

## 7. D0 审计产物

D0 审计脚本：

```text
scripts/audit_tw_modular_decision_replay_d0.py
```

审计输出目录：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/decision_replay_decoupling_d0/
```

关键产物：

```text
d0_summary.json
signal_input_audit.csv
rule_expressibility_audit.csv
replay_decoupling_feasibility_audit.csv
readonly_snapshot_boundary_audit.csv
d1_d5_acceptance_checklist.csv
```

## 8. D0 结论

D0 审计结论：

```text
ok=true
d0_conclusion=feasible_to_enter_d1
```

允许进入 D1，但 D1 只能抽出 `StrategyDecisionEngine` 与 `OrderIntentArtifact` builder/validator，不得改前端/API/日更/默认策略，不得训练、调参、重算分数或重跑收益筛选。
