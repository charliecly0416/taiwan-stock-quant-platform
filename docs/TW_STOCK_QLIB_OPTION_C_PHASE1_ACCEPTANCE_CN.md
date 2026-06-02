# qlib Option C 台股研究信号接入 Phase 1 验收与操作手册

## 1. 功能总览

Phase 1 已把 `/home/chuliyang/qlib` 产出的台股 Option C research-only daily signal artifact 只读接入 QuantDinger。

当前能力：

- 后端读取最新 accepted qlib artifact，并校验 recorder、run path、rank、asof、research-only flags。
- 后端 API 输出 top30/top50 qlib 研究排序。
- 可选 `enrichTrend=true`，把 QuantDinger 台股趋势解释并列补充到每条 qlib row。
- 前端台股监控页展示 qlib top30/top50、趋势解释、warnings。
- qlib row 可打开现有 TWStock 只读回测面板，由用户手动运行历史模拟。

Phase 1 不包含：自动交易、订单、仓位、broker 连接、qlib provider refresh、模型训练或调参。

## 2. 后端 API contract

Endpoint：

```text
GET /api/tw-stock/quant/signals/latest
```

Query：

```text
bucket=top30|top50|all
enrichTrend=true|false
trendLimit=20..500
```

说明：

- `bucket` 默认 `top30`。
- 前端只使用 `top30/top50`。
- `enrichTrend=false` 时只返回 qlib 排序。
- `enrichTrend=true` 时返回 qlib 排序并补充 `trend` 字段。
- `trendLimit` 会 clamp 到 `20..500`，非法值按默认 `120` 处理。

成功响应外层：

```json
{
  "code": 1,
  "msg": "success",
  "data": {
    "ok": true,
    "status": "accepted",
    "asof": "2026-06-01",
    "run_id": "option_c_daily_signal_20260601_20260601T121228Z",
    "recorder_id": "950741cfd5f14ee5a05464fec3e12e0a",
    "bucket": "top30",
    "signals": [],
    "trading": {
      "orders_enabled": false,
      "connects_to_broker": false,
      "paper_orders_enabled": false,
      "live_trading_enabled": false,
      "quick_trade_enabled": false,
      "writes_orders": false,
      "writes_positions": false,
      "research_signal_not_order": true
    }
  }
}
```

Enriched row 示例：

```json
{
  "rank": 1,
  "instrument": "TW3231",
  "symbol": "3231",
  "qlib_score": 0.133519245576231,
  "trend": {
    "ok": true,
    "trend_label": "uptrend",
    "trend_score": 92.78,
    "latest_close": 174.0,
    "latest_date": "2026-06-01",
    "quality_warnings": []
  }
}
```

## 3. qlib artifact 读取和校验规则

默认读取根目录：

```text
/home/chuliyang/qlib/data_tw/experiments/option_c_daily_signal
```

可用环境变量覆盖：

```text
QLIB_TW_OPTION_C_ROOT=/path/to/option_c_daily_signal
```

必须读取：

```text
latest_signal.json
<run_dir>/signal_summary.json
<run_dir>/run_metadata.json
<run_dir>/top30_signals.csv
<run_dir>/top50_signals.csv
```

关键校验：

- artifact path 必须留在 root 内部。
- `latest_signal.diagnostic_only == true`。
- `latest_signal.research_signal_not_order == true`。
- `signal_summary.status == accepted`。
- `prediction_rows == 150`、`top30_rows == 30`、`top50_rows == 50`。
- `finite_prediction_share == 1.0`。
- `run_metadata.frozen_recorder == 950741cfd5f14ee5a05464fec3e12e0a`。
- CSV 每行 `source_model_recorder` 必须等于固定 recorder。
- top30 rank 必须刚好是 `1..30`。
- top50 rank 必须刚好是 `1..50`。
- `asof` 必须在 latest、summary、metadata、CSV rows 之间一致。
- trading/training/provider fallback 相关 flags 必须保持 false。

当前真实 artifact 差异：

- `run_metadata.json` 缺少 `diagnostic_only` 和 `research_signal_not_order`。
- 代码要求 latest 和 summary 均校验为 true；metadata 缺字段时返回 warning：

```text
run_metadata_missing_research_only_flags_verified_by_latest_and_summary
```

## 4. 前端入口和用户操作流程

入口：

```text
QuantDinger-Vue -> 台股趋势监控页 -> qlib Option C 研究排序
```

页面能力：

- 切换 `Top 30` / `Top 50`。
- 查看 `asof/run_id/recorder_id`。
- 查看 `rank/symbol/instrument/qlib_score`。
- 查看 `trend_label/trend_score/latest_close/latest_date/quality_warnings`。
- 点击 qlib row 可联动现有 K 线/趋势查看。
- 点击 `回测验证` 可打开现有只读回测面板。

用户流程：

1. 打开台股趋势监控页。
2. 查看 qlib Option C 研究排序。
3. 切换 Top 30 或 Top 50。
4. 点击 symbol 或 row，查看现有 K 线/趋势上下文。
5. 点击 `回测验证`，打开只读回测面板。
6. 用户手动点击 `历史模拟` 运行只读回测。

## 5. blocked/missing/error 状态说明

后端 blocked/missing/error 时：

- API 返回 `code=0`。
- `signals/top30/top50` 返回空数组。
- 保留 research-only `trading` flags。
- 返回 `status/message/warnings` 供前端展示。

前端处理：

- 请求开始会清空旧 `qlibPayload`，避免旧表格冒充当前信号。
- accepted 才展示 qlib 表格。
- blocked/missing/error 只展示状态信息和空状态文案。
- 不显示“推荐”“交易信号”等暗示。

## 6. 只读回测联动说明

qlib row 的 `回测验证` 只做：

- 设置当前 symbol。
- 打开已有 `台股只读回测验证` 面板。
- 滚动定位到回测面板。

不会自动运行回测。

用户手动运行回测时，现有 API client 固定：

```text
POST /api/indicator/backtest
market=TWStock
timeframe=1D
persist=false
enableMtf=false
```

回测文案明确：

```text
历史模拟，仅供人工复盘；不连接 broker，不建立委托，不写入持仓。
回测结果不是 qlib score 的验证结论，也不是未来收益承诺。
```

## 7. 安全边界和禁止事项

Phase 1 全链路禁止：

- 自动交易。
- broker 连接。
- paper/live order。
- quick-trade。
- target position / target weight。
- pending order。
- 写订单、仓位、交易计划。
- 自动把 qlib top30/top50 写入监控并启用提醒。
- 自动生成 qlib 信号。
- 刷新 qlib provider。
- 训练或调参模型。
- 把 qlib score、trend score、回测结果合成为买入分。
- 把 qlib score 解释为收益率、胜率、涨幅、买入概率或仓位。

## 8. 本地验证命令

后端：

```bash
cd /path/to/taiwan-stock-quant-platform
python -m pytest backend/tests/test_tw_stock_qlib_option_c_signals.py backend/tests/test_tw_stock_quant_signal_api.py -q
python -m pytest backend/tests/test_tw_stock_backtest.py backend/tests/test_verify_tw_stock_research_stack.py -q
```

前端：

```bash
cd /path/to/taiwan-stock-quant-platform-Vue
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-monitor-workflow-check.mjs
corepack pnpm build
```

真实 artifact smoke：

```bash
cd /path/to/taiwan-stock-quant-platform
PYTHONPATH=/path/to/taiwan-stock-quant-platform/backend python - <<'PY'
from app.services.tw_stock_qlib_option_c import QlibOptionCSignalReader
p = QlibOptionCSignalReader().latest(bucket='top30', enrich_trend=False)
print(p['status'], p['asof'], p['run_id'], p['recorder_id'], len(p['signals']))
print(p['signals'][0])
print(p['trading'])
print(p.get('warnings', []))
PY
```

Enrich smoke：

```bash
PYTHONPATH=/path/to/taiwan-stock-quant-platform/backend python - <<'PY'
from app.services.tw_stock_qlib_option_c import QlibOptionCSignalReader
p = QlibOptionCSignalReader().latest(bucket='top30', enrich_trend=True, trend_limit=120)
print(p['status'], p['enrichTrend'], len(p['signals']))
print(p['signals'][0].get('trend'))
PY
```

## 9. 常见问题和排查

### latest_signal.json missing

检查 qlib artifact 是否已生成：

```text
/home/chuliyang/qlib/data_tw/experiments/option_c_daily_signal/latest_signal.json
```

如使用测试目录，确认 `QLIB_TW_OPTION_C_ROOT` 指向正确 root。

### blocked_validation_failed

优先检查：

- recorder 是否为固定 id。
- run_dir 是否与 run_metadata.run_id 一致。
- top30/top50 path 是否在 run_dir 下。
- rank 是否重复、缺失或越界。
- asof 是否一致。
- safety flags 是否被误设为 true。

### trend unavailable

表示 qlib 排序可用，但 QuantDinger 趋势解释不可用。常见原因：

- 本地日线数据不足。
- KlineService 无法返回该 symbol 的 TWStock 1D 数据。
- 数据日期过旧或质量 warning。

### 回测无法运行

检查：

- 本地 `qd_tw_stock_daily_bars` 是否有该 symbol 日线数据。
- 只读回测 API 是否可用。
- 请求是否保持 `persist=false`。

## 10. 残余风险与后续 Phase 2 候选项

残余风险：

- 当前 API 只读取 qlib latest artifact，不生成或刷新 artifact。
- 当前真实 metadata 缺少两个 research-only 字段，仍依赖 latest/summary 校验和 warning 暴露。
- 趋势解释和回测可用性依赖本地台股日线数据质量。
- 前端验证以静态和构建为主，未形成浏览器截图级 E2E。

Phase 2 候选项：

- 历史 qlib signal run 只读归档。
- 人工观察名单，但必须由用户手动保存且不自动启用交易或扫描。
- 前端 E2E smoke 截图。
- 数据可用性仪表盘。
- qlib artifact freshness 监控。

Phase 2 仍不应进入自动交易或订单能力。
