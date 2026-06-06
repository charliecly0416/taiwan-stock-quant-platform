# 台股 QuantDinger 15 分钟盘中观察 Step 1 执行文档：只读数据可行性探测

生成时间：2026-06-05

对应设计文档：`docs/TW_STOCK_INTRADAY_QUANTDINGER_DESIGN_CN.md`

## 1. 本步结论

设计方案总体合理，可以继续推进，但必须先做数据源可行性探测。

当前项目内台股主链路是日线研究链路：

- `backend/app/data_sources/tw_stock.py` 的 `TWStockDataSource.get_kline()` 只支持 `1D`、`1W`。
- `backend/app/services/tw_stock_trend.py` 固定通过 `KlineService:TWStock:1D` 做趋势分析。
- `backend/migrations/init.sql` 已有 `qd_tw_stock_daily_bars`，但没有 intraday bars 表。
- `frontend/src/api/tw-stock.js` 的 `getTwStockKline()` 默认请求 `timeframe: '1D'`。
- qlib Option C、cross-analysis、daily auto update、accepted latest 都是日线语义。

因此，15 分钟能力不能直接混入 qlib provider、accepted latest、Top30/Top50 排名或现有日线趋势服务。正确路线是先独立验证分钟级数据源，再独立实现 intraday adapter、表、只读 API 和前端盘中观察模块。

## 2. 本步目标

确认是否存在可用于台股 `15m/60m` 盘中观察的稳定数据来源，并形成可审查报告。

本步只回答这些问题：

- 能否取得台股分钟级、5 分钟、15 分钟或 tick 数据。
- 数据是否覆盖 Top30/Top50、持仓和自选标的。
- 数据延迟、交易时段、字段口径是否可接受。
- 是否需要 token、付费权限或代理。
- 是否有频率限制、节流、失败模式。
- 是否适合后续落入独立 `qd_tw_stock_intraday_bars` 链路。

本步不实现产品功能。

## 3. 明确禁止

本步不得执行：

- 不新增或修改数据库表。
- 不修改 `qd_tw_stock_daily_bars`。
- 不修改 qlib provider、Option C pipeline、accepted latest。
- 不运行 daily auto update、provider publish、accepted latest switching。
- 不新增前端入口。
- 不连接 broker、quick-trade、order、target position、target weight。
- 不把任何输出写成买入、卖出、立即交易、上涨概率或收益承诺。

允许写入的只有只读探测产物和报告，例如：

```text
data_tw/ops/intraday_probe/<run_id>/
docs/TW_STOCK_INTRADAY_QUANTDINGER_STEP1_REPORT_CN.md
```

## 4. 建议新增文件

建议新增一个只读探测脚本：

```text
scripts/probe_tw_stock_intraday_sources.py
```

脚本职责：

- 读取一组测试 symbol。
- 对候选数据源执行只读 HTTP/API 探测。
- 将原始响应摘要、覆盖率、bar 数、时间范围、错误信息写入 JSON。
- 不写业务数据库。
- 不调用现有 qlib、daily update 或 monitor scan 入口。

建议支持参数：

```text
--symbols 2330,2317,2454
--symbols-file <path>
--lookback-days 5
--timeframes 15m,60m
--output-dir data_tw/ops/intraday_probe/<run_id>
--max-symbols 10
--timeout 20
```

如果数据源需要 token，只读取环境变量，不把 token 写入报告：

```text
FINMIND_TOKEN
FINMIND_API_TOKEN
TW_INTRADAY_SOURCE_TOKEN
```

## 5. 探测 symbol 集合

第一轮使用 10 个标的，覆盖大型权值股、ETF、可能的上柜样本：

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

如果能从当前 qlib Top30 读取 latest signals，可额外记录 Top30 前 10，但读取失败不能阻塞本步。

## 6. 候选数据源探测顺序

### 6.1 现有本地能力

先检查当前项目是否已有可复用的本地 intraday 数据或 API：

- 搜索 `intraday`、`15m`、`60m`、`minute`、`tick`。
- 检查 `data_tw/` 是否有分钟级归档。
- 检查 `frontend` 是否已有周期切换遗留逻辑。

验收重点：如果本地没有分钟级数据，不要伪造 15m。

### 6.2 FinMind

只读探测 FinMind 是否提供可用分钟级或 tick 数据。

记录：

- dataset 名称。
- 是否需要 token。
- 返回字段。
- 单标的最近 3 个交易日是否足够聚合成 15m。
- 是否有延迟或频率限制。
- HTTP status、错误信息、空数据原因。

### 6.3 Yahoo/Scrapling

只读探测是否能稳定取得台股 intraday 数据。

如果只能稳定取得日线，则结论应写为“不作为 15m 来源”，不能用日线插值成分钟线。

## 7. 输出 JSON 要求

每次运行至少输出：

```text
data_tw/ops/intraday_probe/<run_id>/summary.json
data_tw/ops/intraday_probe/<run_id>/sources.json
data_tw/ops/intraday_probe/<run_id>/symbols.json
```

`summary.json` 至少包含：

```json
{
  "run_id": "intraday_probe_20260605T000000Z",
  "started_at": "2026-06-05T00:00:00Z",
  "finished_at": "2026-06-05T00:01:00Z",
  "symbols_requested": 10,
  "sources_checked": ["local", "finmind", "yahoo_scrapling"],
  "usable_source_count": 0,
  "recommended_source": null,
  "can_continue_to_step2": false,
  "orders_enabled": false,
  "connects_to_broker": false,
  "writes_business_db": false
}
```

`symbols.json` 中每个 symbol 至少包含：

```json
{
  "symbol": "2330",
  "source": "finmind",
  "timeframe": "15m",
  "ok": false,
  "bar_count": 0,
  "first_bar_time": null,
  "latest_bar_time": null,
  "latency_minutes": null,
  "warnings": ["no_intraday_dataset_confirmed"],
  "error": null
}
```

## 8. 可行性判定标准

建议把结论分成三档。

### 8.1 可以进入 Step 2

满足：

- 至少一个来源可稳定返回分钟级或更细粒度数据。
- 10 个测试标的覆盖率不低于 80%。
- 最近 3 个交易日至少能聚合出有效 15m bar。
- 字段足够构造 OHLCV。
- 频率限制可通过批量节流处理。
- 无需修改 qlib 日线链路。

### 8.2 可以继续，但 Step 2 需降级

满足部分条件，但存在限制：

- 需要 token 或付费权限。
- 覆盖率低于 80% 但高于 50%。
- 数据延迟较大，只适合“延迟盘中观察”。
- 只能取得 5m/1m，需要本地聚合为 15m。

此时 Step 2 应设计为 provider 可插拔，并在前端明确展示数据延迟和覆盖不足。

### 8.3 暂停实现

出现任一情况：

- 没有稳定分钟级或 tick 来源。
- 只能拿到日线。
- 数据源条款或权限不允许使用。
- 覆盖率过低，无法支撑 Top30/持仓观察。

此时不能继续做假 15m UI，应回到数据源选型。

## 9. 必跑检查

本步完成后至少运行：

```text
python -m py_compile scripts/probe_tw_stock_intraday_sources.py
python scripts/probe_tw_stock_intraday_sources.py --symbols 2330,2317,2454,2308,2412,2881,2882,0050,0056,6488 --lookback-days 5 --timeframes 15m,60m
python backend/scripts/verify_tw_stock_research_stack.py
```

如果因为网络、token 或环境限制无法完成真实探测，报告必须明确写明：

- 哪个数据源无法访问。
- HTTP status 或异常摘要。
- 是否需要 token。
- 是否需要用户授权联网。
- 本步是否因此阻塞 Step 2。

## 10. 报告要求

执行完成后新增：

```text
docs/TW_STOCK_INTRADAY_QUANTDINGER_STEP1_REPORT_CN.md
```

报告必须包含：

1. 结论摘要：是否建议进入 Step 2。
2. 修改文件清单。
3. 探测 symbol 集合。
4. 候选数据源逐项结果。
5. 覆盖率、bar 数、最新 bar 时间、延迟。
6. 数据字段口径和可聚合性。
7. token、频率限制、网络限制。
8. 只读安全边界检查。
9. 命令执行结果。
10. 产物路径。
11. Step 2 设计约束建议。

## 11. 审核断点

本步完成后停止，等待审查：

```text
docs/TW_STOCK_INTRADAY_QUANTDINGER_STEP1_REPORT_CN.md
```

审查通过后，再编写 Step 2 执行文档。Step 2 才允许设计 intraday 表、adapter、导入脚本和只读 API。
