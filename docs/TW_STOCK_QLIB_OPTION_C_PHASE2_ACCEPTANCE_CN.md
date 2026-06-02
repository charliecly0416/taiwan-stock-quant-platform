# qlib Option C 台股研究信号接入 Phase 2 最终验收文档

## 1. Phase 2 功能总览

Phase 2 在 Phase 1 latest research signal 只读接入的基础上，补齐了面向用户复盘和维护者验收的只读能力：

- 历史 qlib signal run 只读浏览。
- latest 与历史 run 的 Top 30 / Top 50 研究排序查看。
- accepted / blocked / wait-state run 状态区分。
- 浏览器 E2E smoke，覆盖 qlib latest、历史 run、只读回测入口、观察草稿和数据状态。
- 前端本地“研究观察草稿”，只存在于浏览器 localStorage，供人工复盘。
- qlib Option C artifact freshness 和数据可用性状态展示。

Phase 2 仍然保持：`research-only`、`read-only`、`not order`、`manual review`、`no broker`、`no quick-trade`、`no auto trading`。

## 2. API contract 索引

### latest research signal

```text
GET /api/tw-stock/quant/signals/latest?bucket=top30|top50|all&enrichTrend=true|false&trendLimit=20..500
```

用途：读取最新 accepted qlib Option C artifact。accepted 时返回 selected bucket 的研究排序；blocked/missing/error 时返回空 signals 和状态说明。

### historical run list

```text
GET /api/tw-stock/quant/signals/runs?limit=1..100&status=all|accepted|blocked|wait_state
```

用途：列出本地 artifact root 下已存在的历史 run 元数据。该接口不返回 full signals，不读取 CSV 明细。

### historical run detail

```text
GET /api/tw-stock/quant/signals/runs/<run_id>?bucket=top30|top50|all&enrichTrend=true|false&trendLimit=20..500
```

用途：读取单个历史 run。只有 accepted 且校验通过时返回研究排序；wait-state/blocked run 只返回 metadata、summary、warnings 和空 signals。

### artifact health

```text
GET /api/tw-stock/quant/signals/health
```

用途：展示 latest artifact 是否存在、是否 accepted/validated、freshness、最近 run 状态分布、wait-state 提示、趋势/回测数据依赖。该接口只读取 JSON 元数据和 run 列表，不读取 full signals。

## 3. 前端入口和用户流程

入口：

```text
QuantDinger-Vue -> 台股趋势监控 -> qlib Option C 研究排序
```

用户流程：

1. 打开台股趋势监控页。
2. 查看 `qlib Option C 数据状态`，确认 latest artifact、freshness 和 wait-state warning。
3. 查看 `qlib Option C 研究排序` 的 Top 30 / Top 50。
4. 查看 `qlib Option C 历史研究 run`，必要时点击 accepted 历史 run 做人工对照。
5. 点击 row 或 symbol 联动趋势/K 线信息。
6. 点击 `加入观察` 放入本地研究观察草稿。
7. 点击 `填入监控配置` 只把草稿 symbol 填入配置抽屉，保存仍由用户手动点击。
8. 点击 `回测验证` 只打开只读回测面板，历史模拟仍由用户手动点击。

## 4. 历史 run 浏览说明

历史 run 浏览只读取本地已有 artifact 目录：

```text
/home/chuliyang/qlib/data_tw/experiments/option_c_daily_signal
```

列表字段包括：

- `run_id`
- `asof`
- `status`
- `created_at`
- `prediction_rows/top30_rows/top50_rows`
- `accepted_validated`
- `warnings`

状态处理：

- `accepted + accepted_validated=true`：允许查看研究排序。
- `wait_state_*`：只展示 wait-state 状态、summary/metadata 和 warning，不展示可用 signals。
- `blocked_*`：只展示 blocked 状态和 warning。
- missing/invalid run：只展示错误状态，不触发修复。

## 5. 研究观察草稿说明

研究观察草稿是前端本地辅助区块：

- 存储位置：浏览器 localStorage。
- 存储 key：`tw-stock-monitor-qlib-watch-draft`。
- 展示字段：`symbol/run_id/rank/qlib_score/trend_label/trend_score`。
- 操作：加入、移除、清空、填入监控配置抽屉。

安全边界：

- 不调用 `saveConfig`。
- 不调用 `saveTwStockMonitorConfig`。
- 不调用 `runScan` 或 `scanTwStockMonitor`。
- 不自动建立提醒。
- 不自动运行回测。
- 不生成订单或仓位。

## 6. freshness/data availability 说明

`qlib Option C 数据状态` 使用 health API 展示：

- latest artifact 是否存在。
- latest `status/asof/run_id/created_at`。
- latest 是否 accepted/validated。
- asof age 和 created age。
- 最近 runs 的 accepted/wait-state/blocked/other 分布。
- metadata/freshness/data availability warnings。
- 趋势解释依赖：`TWStock local daily bars`。
- 回测依赖：`qd_tw_stock_daily_bars`。

freshness 保守规则：

- `asof_age_days > 3` 标记 stale。
- latest 非 accepted 标记 stale/blocked。
- latest 未通过 JSON 元数据一致性校验标记 stale。
- 如果存在更新 asof 的 wait-state run，展示 `fresh_data_wait_state_present`。

health 只报告状态，不刷新 provider、不生成 qlib 信号、不自动补数据。

## 7. 浏览器 E2E 截图说明

浏览器 smoke 截图目录：

```text
/tmp/quantdinger_tw_qlib_e2e
```

截图清单：

- `latest.png`：latest qlib 研究排序。
- `historical-accepted.png`：accepted 历史 run 明细。
- `historical-blocked-or-wait-state.png`：blocked/wait-state 历史 run 不展示可用 signals。
- `readonly-backtest-linkage.png`：qlib row 只打开只读回测面板，不自动运行回测。
- `watchlist-draft.png`：研究观察草稿和手动填入配置抽屉。
- `qlib-health.png`：artifact freshness/data availability 状态。

## 8. 安全边界和禁止事项

Phase 2 全链路禁止：

- 调用 qlib daily signal script。
- 刷新 qlib provider。
- 训练或调参模型。
- 自动补数据。
- 写 DB。
- 自动保存监控配置。
- 自动扫描。
- 自动创建提醒。
- 自动运行回测。
- 写订单、仓位、pending order、交易计划。
- 连接 broker。
- 调用 quick-trade。
- 生成 target position / target weight。
- 把 qlib score、trend score、回测结果合成为买入分。
- 把 qlib score 表述为收益率、胜率、涨幅、买入概率或仓位。

## 9. 本地验证命令

后端：

```bash
cd /path/to/taiwan-stock-quant-platform
python -m py_compile backend/app/services/tw_stock_qlib_option_c.py backend/app/routes/tw_stock.py
python -m pytest backend/tests/test_tw_stock_qlib_option_c_signals.py backend/tests/test_tw_stock_quant_signal_api.py -q
python -m pytest backend/tests/test_tw_stock_backtest.py backend/tests/test_verify_tw_stock_research_stack.py -q
```

前端：

```bash
cd /path/to/taiwan-stock-quant-platform-Vue
node --check tests/unit/tw-stock-monitor-local-smoke.mjs
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-monitor-workflow-check.mjs
corepack pnpm build
```

浏览器 smoke：

```bash
TW_STOCK_MONITOR_USERNAME=quantdinger TW_STOCK_MONITOR_PASSWORD=change-me TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8000 TW_STOCK_MONITOR_SCREENSHOT_DIR=/tmp/quantdinger_tw_qlib_e2e node tests/unit/tw-stock-monitor-local-smoke.mjs
```

## 10. 真实 artifact smoke 方法

真实 artifact smoke 只读运行：

```bash
cd /path/to/taiwan-stock-quant-platform
PYTHONPATH=/path/to/taiwan-stock-quant-platform/backend python - <<'PY'
from app.services.tw_stock_qlib_option_c import QlibOptionCSignalReader
r = QlibOptionCSignalReader()
latest = r.latest(bucket='top30', enrich_trend=True, trend_limit=120)
print('latest', latest['status'], latest['asof'], latest['run_id'], len(latest.get('signals') or []))
runs = r.list_runs(limit=5, status='all')
print('runs', [(i.get('run_id'), i.get('status'), i.get('accepted_validated')) for i in runs.get('items', [])])
health = r.health()
print('health', health['status'], health['latest'], health['freshness'], health['runs'])
PY
```

该 smoke 只读取本地 artifact，不生成、刷新或写入任何内容。

## 11. 残余风险

- 真实 artifact freshness 取决于 qlib 侧人工生成节奏；QuantDinger 只显示状态，不自动修复。
- health 的 `accepted_validated` 是 JSON 元数据级校验；CSV 明细完整校验仍由 latest/run detail 路径负责。
- 前端研究观察草稿是 localStorage，本机浏览器级持久化，不是团队共享配置。
- 浏览器 smoke 使用 mock qlib API 响应覆盖 UI 工作流；真实 artifact smoke 覆盖后端真实读取。
- 前端 build 仍有既有 `/deep/` CSS warning 和大 chunk warning。

## 12. 后续候选方向

Phase 3 如启动，建议仍保持只读边界：

- 编写运维手册：如何人工生成 qlib artifact、如何查看 freshness、如何处理 wait-state。
- 增加只读告警：仅提示 artifact stale，不自动补数据。
- 增加更多真实 artifact 离线报告：覆盖 run 分布、asof 连续性、趋势数据覆盖率。
- 优化前端 build warning 和 chunk 拆分。
- 增加只读导出功能，仅导出研究报告，不导出交易计划或目标仓位。
