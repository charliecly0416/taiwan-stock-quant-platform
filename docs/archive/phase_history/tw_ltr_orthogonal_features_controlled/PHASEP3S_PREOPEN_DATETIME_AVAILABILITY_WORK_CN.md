# Phase P3S 工作文档：Pre-open Datetime Availability 判定与可行修复

生成日期：2026-06-15

依据：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEP3RRR_ORTHOGONAL_SOURCE_FRESHNESS_REPAIR_EXECUTION_REPORT_CN.md
```

## 1. P3S 目标

P3S 只做一轮：

```text
判定 institutional / margin 正交数据是否能稳定在 T+1 开盘前取得；
若能证明，则把 P3 LTR 日更链路从日期级 available_at 升级为 datetime 级 available_at；
若不能证明，则停止，不做合同升级。
```

目标 gate 二选一：

```text
phase_p3s_preopen_datetime_availability_upgraded
phase_p3s_preopen_datetime_availability_not_proven_stop
```

## 2. 业务目标

目标生产口径：

```text
T 日收盘后
抓取 T 日完整 qlib / institutional / margin 数据
在 T+1 开盘前生成 T+1 readonly LTR 候选
```

这不是同日裸用数据。

允许使用的条件是：

```text
feature_trade_date = T
available_at_datetime <= strategy_generation_time
strategy_generation_time < T+1 market_open_datetime
target_execution_date = next_trading_day(T)
```

## 3. 一轮判定条件

必须同时满足以下条件，才允许修复：

```text
1. institutional 与 margin 均有可信 fetched_at / available_at_datetime；
2. 最近样本交易日中，T 日数据能在 T+1 开盘前稳定取得；
3. timestamp 不是执行后回填伪造，能追溯 raw response / raw archive；
4. P3 latest feature table 能记录 used_available_at_datetime；
5. P3 rerank summary 能记录 strategy_generation_time 与 target_execution_date；
6. PIT audit 能验证 used_available_at_datetime <= strategy_generation_time < target_open_datetime。
```

若任一条件不满足：

```text
不得升级合同；
继续保留现有日期级 current_or_pit_delayed；
提交 not_proven_stop gate。
```

## 4. 审计范围

执行者必须审计最近至少 5 个交易日，若本地 raw archive 不足 5 日，必须说明不足原因。

每个 family 必须报告：

```text
feature_family
trade_date
symbol_count
raw_row_count
fetched_at_min
fetched_at_max
available_at_datetime_min
available_at_datetime_max
next_trading_day
target_open_datetime
preopen_available_symbol_count
preopen_available_ratio
late_symbol_count
missing_timestamp_count
```

family 范围固定：

```text
TaiwanStockInstitutionalInvestorsBuySell
TaiwanStockMarginPurchaseShortSale
```

## 5. 可行则修复

只有判定通过时，才允许做以下最小修复：

```text
1. 在 P3RRR raw archive / latest feature table 中保留 available_at_datetime / fetched_at；
2. 在 P3 latest feature builder 中使用 datetime 级 as-of join；
3. 在 P3 rerank summary 中输出 strategy_generation_time、target_execution_date、target_open_datetime；
4. 在 PIT audit 中新增 datetime 违规检查；
5. 保持 qlib Top50 candidate universe 不变。
```

datetime 级规则：

```text
used_available_at_datetime <= strategy_generation_time
strategy_generation_time < target_open_datetime
feature_trade_date <= signal_asof
```

## 6. 禁止事项

禁止：

```text
重训 qlib；
重训 LTR；
调参；
改变 O4 model / feature whitelist；
扩大 qlib Top50；
改默认策略；
切换 accepted latest；
provider publish / refresh；
monitor scan/config/alerts；
broker/orders/quick-trade；
target position / target weight；
真实买卖建议；
收益、胜率或上涨概率承诺。
```

## 7. 执行报告

执行者必须写：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEP3S_PREOPEN_DATETIME_AVAILABILITY_EXECUTION_REPORT_CN.md
```

报告必须回答：

```text
1. 是否证明 T 日正交数据能稳定在 T+1 开盘前取得？
2. 使用了哪些 timestamp 字段，是否可追溯 raw archive？
3. 最近交易日 pre-open coverage 是多少？
4. 是否升级为 datetime available_at 合同？
5. 若未升级，阻塞原因是什么？
6. P3 rerank 是否仍只读、仍只用 qlib Top50、仍不改默认策略？
7. 是否触发 accepted latest/provider/monitor/trading 链路？
```

## 8. 给执行者的指令

请执行 Phase P3S：做一轮 pre-open datetime availability 判定。只有在 institutional / margin 的 T 日数据均能用可信 timestamp 证明稳定早于 T+1 开盘前取得时，才允许把 P3 LTR 日更链路升级为 datetime 级 available_at；否则必须停止并给 `phase_p3s_preopen_datetime_availability_not_proven_stop`，不得做合同升级。
