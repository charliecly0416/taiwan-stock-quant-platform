# 2018-2022 Frozen Qlib 五规则异常收益审计

生成日期：2026-06-16

## 1. 审计对象

本审计针对：

`data_tw/experiments/extended_oos_qlib_orthogonal_ltr/addon_frozen_qlib_2023_2026_five_replay_rule_check/`

重点检查新增规则 `top50_exit_one_worst_sell` 在 `2023-01-03..2026-05-07` 合并窗口出现 `11.919660` 净收益是否存在低级错误：

- qlib 训练窗是否混入 2023-2026；
- 回放是否跑在 qlib 训练集上；
- ranking / sell choice 是否使用未来收益或未来标签；
- 交易是否使用同日不可得价格参与决策；
- 是否存在重复持仓、卖出不存在持仓、负现金或超过 10 支持仓；
- 异常收益是否由回放实现错误产生。

## 2. 训练与 OOS 边界

依据：

- `phasee1_training_manifest.json`
- `phasee1_generated_qlib_config.yaml`
- `phasee1_raw_oos_score_rank_2023_2026.csv`
- `phasee1_leakage_audit.json`

审计结果：

| item | result |
| --- | --- |
| qlib train | `2018-01-01..2022-12-31` |
| qlib valid | `2022-07-01..2022-12-31`，在 train window 内 |
| handler fit | `2018-01-01..2022-12-31` |
| OOS score | `2023-01-01..2026-05-07` |
| raw score rows | `119862` |
| raw score segment | 全部为 `oos` |
| raw score min/max date | `2023-01-03..2026-05-07` |
| rows <= 2022-12-31 | `0` |
| duplicate date/instrument | `0` |

结论：未发现 2023-2026 分数来自 qlib 训练集。`2023-2025` 对 qlib 是 OOS，但对后续 LTR 分支曾作为训练区间；因此 `2023-2026` 合并回放只能作为 qlib replay rule 诊断，不能作为 LTR untouched 策略证据。

## 3. Replay-ready 覆盖

`top50` 输入覆盖完整：

| window | dates | rows | daily min/median/max | score_na | duplicate |
| --- | ---: | ---: | --- | ---: | ---: |
| 2023 | 239 | 11950 | 50/50/50 | 0 | 0 |
| 2024 | 242 | 12100 | 50/50/50 | 0 | 0 |
| 2025 | 242 | 12100 | 50/50/50 | 0 | 0 |
| 2026_ytd | 79 | 3950 | 50/50/50 | 0 | 0 |
| 2023_2026_ytd | 802 | 40100 | 50/50/50 | 0 | 0 |

结论：异常收益不是由 top50 覆盖缺口、缺 score 或重复 key 造成。

## 4. 新增规则语义复核

规则 `top50_exit_one_worst_sell` 的实际动作：

- 持仓仍在当日 qlib raw rank top50 内：不卖；
- 若有持仓跌出 top50：每个 signal day 最多卖 1 支；
- 多支持仓跌出 top50 时，卖 qlib raw rank 最差的一支；
- 每个 signal day 最多买 1 支；
- 买入对象为 top50 内当前 rank 最高且未持有的股票。

动作审计：

| audit | result |
| --- | --- |
| buy rank range | 1..7 |
| sell rank range | 51..150 |
| sells with rank <= 50 | 0 |
| buys with rank > 50 or missing | 0 |
| max buys per signal day | 1 |
| max sells per signal day | 1 |

结论：该规则没有偷偷变成“每天换成 top10”，也没有卖出仍在 top50 的股票；它确实是慢卖、长持 top50 内股票的规则。

## 5. 交易与账本一致性

对 `actions.csv` 独立重放动作生命周期，按同一执行日先卖后买检查：

| window | actions | reconstructed final positions | problems |
| --- | ---: | ---: | ---: |
| 2023 | 427 | 9 | 0 |
| 2024 | 435 | 9 | 0 |
| 2025 | 433 | 10 | 1 |
| 2026_ytd | 123 | 9 | 0 |
| 2023_2026_ytd | 1438 | 9 | 1 |

唯一问题：

- `TW6919` 在 `2025-07-21` 有一条 `quantity=0` 的 `historical_risk_reduce` 占位记录；
- `fee_and_tax=0`，`effective_nav_date` 为空；
- 不产生现金流，不解释高收益；
- 但说明该 add-on 脚本仍应正式化，避免跳过交易被写入 active action。

其他约束：

| audit | result |
| --- | --- |
| execution_date <= signal_date | 0 |
| same-day execution | 0 |
| max holding count | 10 |
| min cash | 9.62 |
| missing price days | 0 |
| negative fee/tax | 0 |
| duplicate same-day same-symbol action | 0 |

结论：未发现凭空卖出、重复买入、超过持仓上限、负现金或同日偷看执行。

## 6. 为什么收益会异常高

`top50_exit_one_worst_sell` 的高收益目前更像规则暴露出的强趋势/慢卖效应，而不是已发现的未来函数。

核心机制：

- `original` 规则用 top10 target set，持仓跌出 top10 就可能被卖，换手更快；
- `top50_exit_one_worst_sell` 只要股票仍在 top50 就继续持有，能保留中期强势股；
- 买入总是 rank 最高的未持有股票，卖出只清掉跌出 top50 且最差的一支；
- 多年合并窗口从 100 万连续复利到 2026，不是逐年重置，所以 `1191.97%` 是复利结果。

已实现 PnL 集中度粗查显示，收益不是单笔交易产生，但有明显强势股贡献：

| symbol | realized pnl | sell trades |
| --- | ---: | ---: |
| TW2408 | 1221782.38 | 8 |
| TW6515 | 829349.46 | 13 |
| TW3491 | 719400.68 | 4 |
| TW6187 | 661271.31 | 14 |
| TW3081 | 525836.97 | 13 |

最大单笔 realized sell return 约为 `101.17%`，来自 `TW2408`，不是单笔数倍异常。

## 7. 当前结论

截至本次审计，未发现以下低级问题：

- 未发现 qlib 训练使用 2023-2026；
- 未发现 2023-2026 raw score 落在 qlib train/fit/valid；
- 未发现 action ranking 使用未来 label / realized return 字段；
- 未发现买入 top50 外股票或卖出仍在 top50 股票；
- 未发现 same-day execution、负现金、超过 10 支持仓、卖不存在持仓等账本错误。

但不能直接收口为默认策略证据，原因：

- `2023-2026` 合并窗口对 LTR 不是 untouched test；
- 当前五规则 add-on 是临时脚本产物，不是主线 replay engine 的正式可复现阶段；
- 发现 `quantity=0` 占位 action，虽不影响收益，但需要修掉；
- 使用 next-day adjusted close 做执行价格是既有统一回放口径，但不是严格 pre-open 可成交价；
- 在看过多套 replay rule 后选择最佳规则，有数据挖掘风险，必须用固定规则做后续 OOS / walk-forward。

## 8. 建议

暂不把 `top50_exit_one_worst_sell` 的 `2023-2026` 合并结果作为策略优劣证据。

建议下一步只做一个收敛阶段：

1. 把五个 replay rule 固化为正式脚本和 manifest，不再用 ad-hoc add-on；
2. 修复 `quantity=0` action，不允许跳过交易进入 active actions；
3. 对 fresh qlib、2018-2022 frozen qlib、E4 LTR 等模型统一使用同一正式 replay engine；
4. 固定候选规则后，只在真正未参与规则选择的后续窗口或 walk-forward 上评估；
5. 若要用于日更候选，必须明确执行价口径：继续沿用 next-day close 回测，或改成 next-day open / VWAP 的可执行近似。
