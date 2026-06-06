# 台股 QuantDinger 15 分钟盘中观察 Step 1B Report：数据源权限复核与收尾结论

生成时间：2026-06-05

对应执行文档：`docs/TW_STOCK_INTRADAY_QUANTDINGER_STEP1B_EXECUTION_CN.md`

## 1. 是否建议进入 Step 2

不建议进入 Step 2。

本轮 Step 1B 已完成二次只读探测，结论仍然是：**当前没有稳定可用的台股 15m/60m 数据源**。

按照用户指示：“如果数据都拉不到的话就直接收尾，不做15分钟间隔的实现了。”本轮到此收尾：

- 不新增 intraday 表。
- 不新增 intraday API。
- 不新增前端 15m 周期切换。
- 不改 qlib、accepted latest、daily auto update。
- 不做任何伪 15m UI 或日线插值分钟线。

## 2. Step 1 报告审查结论与遗留问题

Step 1 报告结论成立：

- `local` 覆盖率 `0%`。
- `finmind` 覆盖率 `0%`。
- `yahoo_scrapling` 覆盖率 `0%`。
- `can_continue_to_step2=false`。
- 安全边界字段均为 false：`orders_enabled=false`、`connects_to_broker=false`、`writes_business_db=false`。

Step 1B 对遗留问题做了补强：

- 增加 Yahoo/yfinance 结构化诊断。
- 增加 `provider_diagnostics.json`。
- 保留 FinMind `TaiwanStockKBar`、`TaiwanStockPriceTick` 权限复核结果。

## 3. 修改文件清单

修改：

```text
scripts/probe_tw_stock_intraday_sources.py
```

新增：

```text
docs/TW_STOCK_INTRADAY_QUANTDINGER_STEP1B_REPORT_CN.md
```

生成探测产物：

```text
data_tw/ops/intraday_probe/intraday_probe_20260605T161628Z/summary.json
data_tw/ops/intraday_probe/intraday_probe_20260605T161628Z/sources.json
data_tw/ops/intraday_probe/intraday_probe_20260605T161628Z/symbols.json
data_tw/ops/intraday_probe/intraday_probe_20260605T161628Z/provider_diagnostics.json
```

## 4. FinMind 权限复核结果

环境：

- 本地 `FINMIND_TOKEN` 存在。
- 报告未输出 token 值。
- 只读 HTTP 探测，不写业务库。

候选 dataset：

```text
TaiwanStockKBar
TaiwanStockPriceMinute
TaiwanStockPriceTick
```

结果：

| Dataset | 结果 | 说明 |
|---|---|---|
| `TaiwanStockKBar` | 不可用 | HTTP/API 400，返回 `Your level is register. Please update your user level.` |
| `TaiwanStockPriceMinute` | 不可用 | HTTP 422，当前 FinMind enum 不接受该 dataset 名称。 |
| `TaiwanStockPriceTick` | 不可用 | HTTP/API 400，返回 `Your level is register. Please update your user level.` |

覆盖率：

```text
0 / 10 = 0%
```

结论：

- 当前 token 可用于此前日线数据，但不能访问分钟级 KBar/Tick。
- 如果未来要重启 15m 项目，最直接解除阻塞方式是提供能访问 `TaiwanStockKBar` 或 `TaiwanStockPriceTick` 的 FinMind 权限。

## 5. Yahoo / yfinance 结构化诊断结果

Step 1B 已将 yfinance 探测写入结构化字段：

```json
{
  "provider_symbol_candidates": ["2330.TW", "2330.TWO"],
  "provider_attempts": [
    {
      "provider_symbol": "2330.TW",
      "status": "rate_limited",
      "row_count": 0,
      "error": null,
      "stderr_tail": "YFRateLimitError('Too Many Requests. Rate limited. Try after a while.')"
    }
  ],
  "provider_status": "rate_limited",
  "attempts_count": 2
}
```

本轮结果：

- `.TW`、`.TWO` 候选都被尝试。
- `15m`、`60m` 都未返回有效 rows。
- yfinance stderr 被捕获并写入 `provider_diagnostics.json`。
- 状态为 `rate_limited`。

覆盖率：

```text
0 / 10 = 0%
```

结论：

- Yahoo/yfinance 当前不能作为稳定 intraday 来源。
- 即使后续暂时恢复，也需要单独做更长时间稳定性验证，不能直接进入 Step2。

## 6. 可选外部来源探测结果

本轮没有配置新的外部来源。

原因：当前没有提供新的稳定 intraday provider、base URL 或 `TW_INTRADAY_SOURCE_TOKEN`。按执行文档要求，未提供参数时不访问额外来源。

## 7. 覆盖率、bar 数、最新 bar 时间、延迟

最终 Step 1B run：

```text
run_id: intraday_probe_20260605T161628Z
started_at: 2026-06-05T16:16:28Z
finished_at: 2026-06-05T16:17:42Z
```

汇总：

| Source | ok_symbol_count | Coverage | recommended_source |
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

因为没有任何有效 intraday rows：

- `bar_count = 0`
- `first_bar_time = null`
- `latest_bar_time = null`
- `latency_minutes = null`

## 8. 字段口径与 15m/60m 可聚合性

当前无法确认字段口径，因为没有任何来源返回有效 rows。

因此无法验证：

- OHLCV 字段。
- tick 聚合为 15m 的可行性。
- 交易时段切分。
- 最近 3 个交易日覆盖。
- 最新 bar 延迟。

## 9. Token、权限、频率限制、成本与条款风险

### FinMind

- token 已配置，但当前权限等级不足以访问 intraday KBar/Tick。
- 成本风险：需要升级 FinMind 权限，具体费用和调用限制需由账户侧确认。
- 条款风险：后续使用前需要确认分钟级数据是否允许缓存、展示和派生指标。

### Yahoo / yfinance

- 当前出现 rate limit。
- 稳定性不足，不适合作为自动化 15m 数据来源。
- 即使可用，也需要节流、缓存、重试和代理策略。

## 10. 只读安全边界检查

本轮没有执行：

- 数据库建表。
- 写入 `qd_tw_stock_daily_bars`。
- 写入任何 intraday business table。
- qlib provider refresh/publish。
- accepted latest switching。
- daily auto update。
- monitor scan、alerts 写入、monitor config 保存。
- broker、quick-trade、orders、target position、target weight。

`summary.json` 和 `provider_diagnostics.json` 均保留：

```json
{
  "orders_enabled": false,
  "connects_to_broker": false,
  "writes_business_db": false
}
```

## 11. 命令执行结果

### 语法检查

```text
python -m py_compile scripts/probe_tw_stock_intraday_sources.py
```

结果：通过。

### Step 1B 基础重跑

```text
python scripts/probe_tw_stock_intraday_sources.py   --symbols 2330,2317,2454,2308,2412,2881,2882,0050,0056,6488   --lookback-days 5   --timeframes 15m,60m   --max-symbols 10   --timeout 20
```

结果：exit code `2`。

解释：这不是脚本运行失败，而是探测完成后 `can_continue_to_step2=false`，表示数据源仍不满足进入 Step2。

### 研究栈安全验证

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

## 12. 产物路径

```text
data_tw/ops/intraday_probe/intraday_probe_20260605T161628Z/
```

文件：

```text
summary.json
sources.json
symbols.json
provider_diagnostics.json
```

## 13. 收尾结论与解除阻塞条件

按当前结果，15 分钟间隔能力本轮收尾，不继续实现。

解除阻塞需要满足至少一个条件：

1. 提供可访问 FinMind `TaiwanStockKBar` 或 `TaiwanStockPriceTick` 的升级权限/token。
2. 提供另一个稳定台股 intraday provider，覆盖 10 个基础标的中至少 8 个。
3. provider 返回最近 3 个交易日有效 intraday rows。
4. 字段可构造 OHLCV，tick 数据可本地聚合为 15m/60m。
5. 权限、频率限制、缓存/展示条款明确。

在这些条件满足前，不做：

- 15m 表。
- 15m API。
- 15m 前端切换。
- 15m 模拟账户执行观察。

当前项目应继续保持：

```text
qlib / cross-analysis / 模拟账户核心候选 = 日线研究链路
QuantDinger 15m = 暂停，等待稳定数据源
```
