# 台股 QuantDinger 15 分钟盘中观察 Step 1B 执行文档：数据源权限复核与二次只读探测

生成时间：2026-06-05

前置报告：`docs/TW_STOCK_INTRADAY_QUANTDINGER_STEP1_REPORT_CN.md`

## 1. 审查结论

Step 1 Report 的主结论成立：当前不能进入 Step 2 的 intraday 表、API 或前端 15m UI 实现。

证据：

- `data_tw/ops/intraday_probe/intraday_probe_20260605T160728Z/summary.json` 显示 `can_continue_to_step2=false`。
- `local`、`finmind`、`yahoo_scrapling` 覆盖率均为 `0.0%`。
- FinMind `TaiwanStockKBar`、`TaiwanStockPriceTick` 返回权限不足。
- 当前没有任何 source 返回有效 intraday rows。
- 安全边界字段保持：`orders_enabled=false`、`connects_to_broker=false`、`writes_business_db=false`。

因此后续工作不是 Step 2 实现，而是 Step 1B：补强数据源验证，解决权限或替换稳定来源，再重跑只读探测。

## 2. 本步目标

本步目标是把“没有可用数据源”的阻塞变成可审查的明确结论：

1. 确认 FinMind 权限升级或新 token 是否可访问分钟级/ tick 数据。
2. 补强 Yahoo/yfinance 探测诊断，把限流、空数据、异常写入 JSON。
3. 允许新增一个外部候选数据源 adapter 的只读探测分支，但不接业务链路。
4. 产出 Step 1B report，明确是否可以进入真正的 Step 2。

## 3. 明确禁止

本步仍然禁止：

- 不新增 `qd_tw_stock_intraday_bars`。
- 不修改 `qd_tw_stock_daily_bars`。
- 不修改 qlib provider、Option C pipeline、accepted latest。
- 不运行 daily auto update、provider publish、accepted latest switching。
- 不新增后端 intraday route。
- 不新增前端 15m UI。
- 不触发 monitor scan、alerts 写入、monitor config 保存。
- 不连接 broker、quick-trade、order、target position、target weight。
- 不把任何输出写成买入、卖出、立即交易、上涨概率或收益承诺。

允许写入：

```text
data_tw/ops/intraday_probe/<run_id>/
docs/TW_STOCK_INTRADAY_QUANTDINGER_STEP1B_REPORT_CN.md
```

## 4. 必做修正

### 4.1 结构化 Yahoo/yfinance 诊断

修改 `scripts/probe_tw_stock_intraday_sources.py`，让 Yahoo/yfinance 探测把以下信息写入 `sources.json` 和 `symbols.json`：

- provider symbol 候选列表，例如 `2330.TW`、`2330.TWO`。
- 每个候选 symbol 的最终状态：`ok`、`empty`、`rate_limited`、`http_error`、`exception`。
- yfinance exception 类型和 message。
- 如果 yfinance 只打印错误但未抛异常，记录 `empty_after_provider_warning`。
- 每个 symbol/timeframe 的 attempts 数量。

建议字段：

```json
{
  "provider_attempts": [
    {
      "provider_symbol": "2330.TW",
      "status": "rate_limited",
      "row_count": 0,
      "error": "YFRateLimitError: Too Many Requests"
    }
  ],
  "provider_status": "rate_limited"
}
```

### 4.2 FinMind 权限复核

如果已经取得升级后的 token 或替代 token，重跑 FinMind 探测。

需要记录：

- token 是否存在，但不得输出 token 值。
- `TaiwanStockKBar` 是否可访问。
- `TaiwanStockPriceTick` 是否可访问。
- 返回字段样本。
- 是否可聚合为 `15m` 和 `60m`。
- 最近 3 个交易日 bar 覆盖。

如果没有升级 token，本步仍可执行，但报告必须明确写为：

```text
FinMind intraday permission not available; Step 2 remains blocked.
```

### 4.3 可选新增外部来源只读探测

如需要评估非 FinMind/Yahoo 来源，只能新增“探测分支”，不能接业务服务。

命名建议：

```text
--extra-source <name>
--extra-source-base-url <url>
--extra-source-token-env TW_INTRADAY_SOURCE_TOKEN
```

要求：

- token 只从环境变量读取。
- 原始响应只保存字段摘要和前 1 条样本，避免写入过大文件。
- 明确 provider 条款、延迟、频率限制。
- 默认关闭，未提供参数时不访问。

## 5. 二次探测 symbol 集合

继续使用 Step 1 的 10 个基础标的：

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

如果 qlib latest 可读，额外加入 Top30 前 10；如果读取失败，不阻塞本步。

最终最多探测 20 个 symbol，避免对 provider 造成压力。

## 6. 输出产物要求

每次运行至少输出：

```text
data_tw/ops/intraday_probe/<run_id>/summary.json
data_tw/ops/intraday_probe/<run_id>/sources.json
data_tw/ops/intraday_probe/<run_id>/symbols.json
data_tw/ops/intraday_probe/<run_id>/provider_diagnostics.json
```

`summary.json` 需保留：

```json
{
  "can_continue_to_step2": false,
  "recommended_source": null,
  "orders_enabled": false,
  "connects_to_broker": false,
  "writes_business_db": false
}
```

如果任一来源达到进入 Step 2 条件，`recommended_source` 才能非空。

## 7. 进入 Step 2 的硬门槛

只有满足以下条件，Step 1B report 才能建议进入 Step 2：

- 至少一个来源覆盖基础 10 个 symbol 中 8 个以上。
- 每个 ok symbol 最近 3 个交易日至少有可用 intraday rows。
- 能明确构造 OHLCV；tick 来源必须能聚合。
- `15m` 与 `60m` 的 bar 时间按台北交易时段可解释。
- 最新 bar 延迟、频率限制、权限成本已写清楚。
- 二次探测仍不写业务数据库，不触发 qlib，不触发交易链路。

未满足时，继续阻塞 Step 2。

## 8. 必跑命令

先做语法检查：

```text
python -m py_compile scripts/probe_tw_stock_intraday_sources.py
```

基础重跑：

```text
python scripts/probe_tw_stock_intraday_sources.py --symbols 2330,2317,2454,2308,2412,2881,2882,0050,0056,6488 --lookback-days 5 --timeframes 15m,60m --max-symbols 10 --timeout 20
```

如果有新 token 或升级权限：

```text
FINMIND_TOKEN=<configured_in_env> python scripts/probe_tw_stock_intraday_sources.py --symbols 2330,2317,2454,2308,2412,2881,2882,0050,0056,6488 --lookback-days 5 --timeframes 15m,60m --max-symbols 10 --timeout 20 --skip-yahoo
```

安全边界验证：

```text
python backend/scripts/verify_tw_stock_research_stack.py
```

如果探测脚本返回 exit code `2`，但 report 显示 `can_continue_to_step2=false`，这不是执行失败；它表示探测完成但数据源仍不满足进入 Step 2。

## 9. 报告要求

执行完成后新增：

```text
docs/TW_STOCK_INTRADAY_QUANTDINGER_STEP1B_REPORT_CN.md
```

报告必须包含：

1. 是否建议进入 Step 2。
2. Step 1 报告审查结论和遗留问题。
3. 修改文件清单。
4. FinMind 权限复核结果。
5. Yahoo/yfinance 结构化诊断结果。
6. 可选外部来源探测结果。
7. 覆盖率、bar 数、最新 bar 时间、延迟。
8. 字段口径和 15m/60m 可聚合性。
9. token、权限、频率限制、成本和条款风险。
10. 只读安全边界检查。
11. 命令执行结果和 exit code 解释。
12. 产物路径。
13. 如果仍阻塞，列出解除阻塞所需的具体外部条件。

## 10. 审核断点

本步完成后停止，等待审查：

```text
docs/TW_STOCK_INTRADAY_QUANTDINGER_STEP1B_REPORT_CN.md
```

只有 Step 1B report 明确 `can_continue_to_step2=true` 且审查通过后，下一份文档才进入 intraday 表、adapter、只读 API 的 Step 2。
