# 台股 QuantDinger 15 分钟盘中观察 Step 1 Report：只读数据可行性探测

生成时间：2026-06-05

对应执行文档：`docs/TW_STOCK_INTRADAY_QUANTDINGER_STEP1_EXECUTION_CN.md`

## 1. 结论摘要

本步已完成只读数据可行性探测。结论：**暂不建议进入 Step 2 实现 intraday 表、API 或前端 15m UI**。

原因：当前可访问的数据源没有稳定返回台股分钟级或 tick 数据。

- 本地项目内没有可复用的台股 15m/60m/minute/tick 归档。
- FinMind token 已配置，但分钟级候选数据集当前权限不足或不可用。
- Yahoo/yfinance 本次探测被限流，未返回有效 15m/60m 台股数据。
- 覆盖率为 0%，不满足 Step 2 最低 80% 覆盖要求。

因此，不能继续做假 15 分钟页面或用日线插值成 15 分钟。下一步应先解决数据源权限或更换稳定分钟级数据源。

## 2. 修改文件清单

新增：

```text
scripts/probe_tw_stock_intraday_sources.py
docs/TW_STOCK_INTRADAY_QUANTDINGER_STEP1_REPORT_CN.md
```

生成探测产物：

```text
data_tw/ops/intraday_probe/intraday_probe_20260605T160728Z/summary.json
data_tw/ops/intraday_probe/intraday_probe_20260605T160728Z/sources.json
data_tw/ops/intraday_probe/intraday_probe_20260605T160728Z/symbols.json
```

说明：探测产物仅为 Step1 只读报告数据，不写业务数据库。

## 3. 探测 symbol 集合

本轮使用执行文档要求的 10 个标的：

```text
2330
2317
2454
2308
2412
2881
2882
0050
0056
6488
```

覆盖大型权值股、金融、ETF 和上柜样本。

## 4. 候选数据源逐项结果

### 4.1 本地能力

只读搜索范围：

```text
backend
frontend
scripts
data_tw
qlib_pipeline/data_tw
```

关键词：

```text
intraday, 15m, 60m, minute, tick, timeframe
```

结论：

- 未发现台股本地分钟级归档文件。
- 当前台股 `TWStockDataSource` 仍是日线/周线语义。
- 其它市场存在 15m/minute 相关能力，但不能直接复用于台股。

覆盖率：`0/10 = 0%`

### 4.2 FinMind

探测环境：

- 已读取本地 `FINMIND_TOKEN`。
- 报告未写入或打印 token。
- 只读调用 FinMind API，没有写业务库。

候选 dataset：

```text
TaiwanStockKBar
TaiwanStockPriceMinute
TaiwanStockPriceTick
```

结果：

| Dataset | HTTP/API 状态 | 结果 | 说明 |
|---|---:|---|---|
| `TaiwanStockKBar` | 400 | 不可用 | 返回 `Your level is register. Please update your user level.`，需要升级权限。 |
| `TaiwanStockPriceMinute` | 422 | 不可用 | 当前 API enum 不接受该 dataset 名称。 |
| `TaiwanStockPriceTick` | 400 | 不可用 | 返回 `Your level is register. Please update your user level.`，需要升级权限。 |

覆盖率：`0/10 = 0%`

字段可聚合性：

- 本轮没有拿到任何分钟级或 tick rows，因此无法确认 OHLCV 字段口径。
- `TaiwanStockKBar` 名称上最可能是后续可用的 K bar 数据源，但当前 token 权限不足。

### 4.3 Yahoo / Scrapling / yfinance

探测方式：

- 通过 `yfinance` 尝试台股 symbol 后缀：`.TW` 和 `.TWO`。
- 周期：`15m`、`60m`。
- lookback：5 天。

结果：

- 所有 10 个标的均未返回有效 15m/60m bar。
- 命令输出显示 Yahoo/yfinance 限流：`YFRateLimitError('Too Many Requests. Rate limited. Try after a while.')`。

覆盖率：`0/10 = 0%`

结论：

- 本次不可作为稳定 15m 来源。
- 即使后续短时恢复，也需要额外验证限流、延迟和覆盖率，不应直接进入 Step2。

## 5. 覆盖率、bar 数、最新时间、延迟

最终探测 run：

```text
run_id: intraday_probe_20260605T160728Z
started_at: 2026-06-05T16:07:28Z
finished_at: 2026-06-05T16:08:49Z
```

汇总：

| Source | ok_symbol_count | Coverage | recommended |
|---|---:|---:|---|
| local | 0 | 0.0% | no |
| finmind | 0 | 0.0% | no |
| yahoo_scrapling | 0 | 0.0% | no |

整体：

```json
{
  "usable_source_count": 0,
  "recommended_source": null,
  "can_continue_to_step2": false,
  "orders_enabled": false,
  "connects_to_broker": false,
  "writes_business_db": false
}
```

由于没有任何 source 返回有效 rows：

- `bar_count = 0`
- `first_bar_time = null`
- `latest_bar_time = null`
- `latency_minutes = null`

## 6. 数据字段口径和可聚合性

当前无法确认字段口径，因为没有拿到有效 intraday rows。

下一次可行探测中需要确认：

- 是否有 `open/high/low/close/volume`。
- 如果是 tick 数据，是否至少有 `time/price/volume` 可以聚合为 15m。
- 是否能按台北交易时段正确切分。
- 是否能覆盖最近 3 个交易日。

## 7. Token、权限、频率限制、网络限制

### FinMind

- token 已配置。
- 日线权限此前可用，但分钟级权限不足。
- `TaiwanStockKBar` 和 `TaiwanStockPriceTick` 都返回 register 等级不足。
- 若要继续 Step2，需要升级 FinMind 权限或提供可访问 KBar/Tick 的 token。

### Yahoo / yfinance

- 本次遭遇 `YFRateLimitError`。
- 不能作为当前稳定 intraday 来源。
- 如果后续继续考虑 Yahoo，需要加入代理、节流、缓存和更长时间稳定性验证。

## 8. 只读安全边界检查

本步没有执行：

- 数据库建表或迁移。
- 写入 `qd_tw_stock_daily_bars`。
- 写入 intraday business table。
- qlib provider refresh/publish。
- accepted latest switching。
- daily auto update。
- monitor scan。
- broker / quick-trade / orders / target position / target weight。

探测脚本输出 summary 明确：

```json
{
  "orders_enabled": false,
  "connects_to_broker": false,
  "writes_business_db": false
}
```

## 9. 命令执行结果

### 编译检查

```text
python -m py_compile scripts/probe_tw_stock_intraday_sources.py
```

结果：通过。

### 完整探测

```text
python scripts/probe_tw_stock_intraday_sources.py   --symbols 2330,2317,2454,2308,2412,2881,2882,0050,0056,6488   --lookback-days 5   --timeframes 15m,60m   --max-symbols 10   --timeout 20
```

结果：exit code `2`。

解释：脚本按设计在 `can_continue_to_step2=false` 时返回 2，表示探测完成但当前数据源不满足进入 Step2 条件。

### 研究栈验证

```text
python backend/scripts/verify_tw_stock_research_stack.py
```

结果：通过。

摘要：

```text
ok=true
orders_enabled=false
connects_to_broker=false
writes_production_data=false
86 passed
```

## 10. 产物路径

最终采用 run：

```text
data_tw/ops/intraday_probe/intraday_probe_20260605T160728Z/
```

文件：

```text
summary.json
sources.json
symbols.json
```

文件大小：

- `summary.json`：约 720 bytes。
- `sources.json`：包含 local / finmind / yahoo_scrapling 详细结果。
- `symbols.json`：包含每个 symbol/source/timeframe 的探测结果。

## 11. 是否建议进入 Step2

不建议直接进入 Step2。

推荐阻塞条件：

1. 至少取得一个稳定 intraday 来源。
2. 10 个测试标的覆盖率达到 80% 以上。
3. 最近 3 个交易日至少能聚合有效 15m bars。
4. 明确字段口径和延迟。
5. 明确频率限制和权限成本。

当前最佳下一步：

- 优先确认 FinMind `TaiwanStockKBar` 是否可通过升级权限访问。
- 如果升级后可用，再重跑 Step1。
- 如果 FinMind 不适合，再选另一个稳定分钟级数据源。
- 在数据源确认前，不新增 15m 前端 UI，不新增 intraday 表和 API。
