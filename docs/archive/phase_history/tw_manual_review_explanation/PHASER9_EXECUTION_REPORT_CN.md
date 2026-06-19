# Phase R9 执行报告：最小上下文字段映射实现

执行日期：2026-06-12

## 1. 本轮目标

根据 `PHASER8_REVIEW_AND_PHASER9_WORK_CN.md`，本轮只做 manual-review explanation 的最小上下文字段增强：

- 后端 service 白名单解析增强。
- 现有 GET route 的扁平 query 解析增强。
- 前端 `buildManualReviewParams()` 从页面已有只读上下文补充白名单字段。
- 复跑后端测试、前端静态检查、前端 build 与 R7 只读 browser smoke。

本轮未扩展到新数据源、模型训练、provider/accepted latest、monitor 写入、交易路径或买卖/仓位/收益/概率语义。

## 2. 修改文件

本轮主线相关文件：

- `backend/app/services/tw_manual_review_explanation.py`
- `backend/app/routes/tw_stock.py`
- `backend/tests/test_tw_manual_review_explanation.py`
- `backend/tests/test_tw_manual_review_explanation_api.py`
- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/tests/e2e/tw-stock-manual-review-readonly.mjs`

沿用/验证文件：

- `frontend/src/api/tw-stock.js`：沿用既有 `getTwStockManualReviewExplanation` GET client。
- `frontend/tests/unit/tw-stock-manual-review-explanation-check.mjs`：复跑通过。
- `frontend/tests/unit/tw-stock-monitor-static-check.mjs`：复跑通过；该文件已有只读历史模拟文本白名单检查改动，R9 未继续扩展其业务范围。

新增报告：

- `docs/tw_manual_review_explanation/PHASER9_EXECUTION_REPORT_CN.md`

说明：当前工作区存在前序阶段未提交/未跟踪文件，本报告只覆盖 R9 主线相关改动。

## 3. 后端实现

### 3.1 Service 白名单增强

`TWManualReviewExplanationService` 增强内容：

- 支持读取 `qlib_rank.score`，仅进入 details，不进入默认主线索。
- 支持读取 `trend.latest_date` 与 `trend_score`，用于趋势 details。
- 支持读取 `technical_status.summary` 与 `technical_status.strategies`。
- 技术策略只输出最多 2 条 details，总 details 最多 5 条。
- 支持读取 `position_risk.metrics` 下的白名单字段：
  - `price_percentile_120d`
  - `distance_ma20_pct`
  - `distance_ma60_pct`
  - `rsi14`
  - `bollinger_position`
  - `return_5d_pct`
  - `return_20d_pct`
- 支持 `data_quality_warnings` 映射为用户可读的数据提示。

安全处理：

- 保持 forbidden semantics 检查。
- 保持 `signals` 最多 5 条。
- 新增 `details` 不输出 raw payload，不输出整包字段。

### 3.2 Route 扁平 query 解析增强

`GET /api/tw-stock/manual-review/explanation` 继续使用既有 route，仅扩展 query 白名单解析：

- `qlibScore`
- `trendLatestDate`
- `technicalSummary`
- `technicalStrategiesDetail`
- `positionLabel`
- `positionReason`
- `distanceMa20Pct`
- `distanceMa60Pct`
- `bollingerPosition`
- `return20dPct`
- `dataQualityWarnings`

解析限制：

- `technicalStrategiesDetail` 只接受 `ma`、`rsi`、`macd`、`bollinger`。
- 技术 metrics 只保留白名单字段。
- warnings 最多保留 6 条，每条截断长度。
- 不接收 cross-analysis、rank change、frozen-rule 真实来源、decision/actionPlan raw code。

## 4. 前端实现

`frontend/src/views/tw-stock-monitor/index.vue` 增强内容：

- 新增 `manualReviewRankTechRow`，从当前页面已加载的 `rankTechItems` 匹配当前 manual-review symbol。
- `buildManualReviewParams()` 从页面已有只读上下文组装白名单字段：
  - qlib rank/score/asof
  - trend label/score/latest date
  - technical status/summary/strategies
  - position status/label/reason/metrics
  - data quality warnings
- 未新增默认页面 API 请求；仅使用页面已有上下文。
- 未新增写请求。

R7/R9 browser smoke 使用的 `manual_review_readonly=1` 是测试专用分支。R9 为该分支补了 `seedManualReviewReadonlyContext()`：

- 只在 `manualReviewReadonlyTestMode` 为 true 时执行。
- 只写入组件内存态 `qlibPayload` 与 `rankTechLatestPayload`。
- 不触发 rank-tech、cross-analysis、monitor、provider 或交易相关请求。
- 目的仅是让 browser smoke 能验证 R9 新字段确实进入 manual-review GET query。

默认 `/tw-stock-monitor` 行为没有改为 fixture，也没有新增数据来源。

## 5. 暂缓字段

按 R8/R9 工作文档暂缓：

- qlib rank change。
- ret60。
- cross category / alignment。
- 冻结法人/融资融券规则卡真实来源。
- decision/actionPlan raw code。
- raw payload 整包透传。

## 6. 验证结果

### 6.1 后端

命令：

```bash
python -m py_compile backend/app/routes/tw_stock.py backend/app/services/tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation_api.py
```

结果：通过。

命令：

```bash
python -m pytest backend/tests/test_tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation_api.py -q
```

结果：`13 passed in 1.14s`。

### 6.2 前端静态检查

命令：

```bash
node --check frontend/tests/e2e/tw-stock-manual-review-readonly.mjs
node frontend/tests/unit/tw-stock-manual-review-explanation-check.mjs
node frontend/tests/unit/tw-stock-monitor-static-check.mjs
```

结果：全部通过。

备注：普通沙箱运行 Node 检查时遇到 `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`，随后按权限规则提升执行本地检查；不涉及联网、拉数或业务写入。

### 6.3 前端 build

命令：

```bash
cd frontend && corepack pnpm build
```

结果：通过。

备注：输出中有 `/bin/sh: 2: source: not found`，但 build 退出码为 0，Vite 构建完成。

### 6.4 R7 browser readonly smoke 复跑

命令：

```bash
cd frontend/dist && python -m http.server 5178 --bind 127.0.0.1
cd frontend && TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:5178 TW_STOCK_MANUAL_REVIEW_E2E_ARTIFACT_DIR=../data_tw/ops/manual_review_readonly_e2e/phase_r9 node tests/e2e/tw-stock-manual-review-readonly.mjs
```

结果：通过。

关键摘要：

- `manual_review_get_count=1`
- `forbidden_request_count=0`
- `portfolio_replay_post_count=0`
- `monitor_config_write_count=0`
- `monitor_scan_post_count=0`
- `monitor_alerts_write_count=0`
- `provider_or_accepted_latest_write_count=0`
- `broker_quick_trade_order_count=0`
- `unsafe_trading_semantics_count=0`
- `disallowed_api_request_count=0`
- `console_issue_count=0`
- `page_error_count=0`
- `failed_response_count=0`

R9 browser smoke 的 manual-review GET query 已包含：

- `qlibScore=0.318765`
- `trendLatestDate=2026-06-04`
- `technicalStatus=technical_strong`
- `technicalSummary=...`
- `technicalStrategiesDetail=...`
- `positionStatus=elevated`
- `positionLabel=强势但偏高`
- `distanceMa20Pct=8.4`
- `distanceMa60Pct=13.1`
- `bollingerPosition=0.91`
- `return20dPct=12.3`
- `dataQualityWarnings=["short_history_below_60_bars"]`

## 7. Browser 产物

产物目录：

- `data_tw/ops/manual_review_readonly_e2e/phase_r9/summary.json`
- `data_tw/ops/manual_review_readonly_e2e/phase_r9/network_audit.json`
- `data_tw/ops/manual_review_readonly_e2e/phase_r9/console_audit.json`
- `data_tw/ops/manual_review_readonly_e2e/phase_r9/manual_review_readonly.png`

页面文本摘要：

```text
复盘线索
只读解释当前标的的研究线索。
2330
查看线索
需要人工复盘
2330 台积电
模型排名靠前，但仍需要人工确认趋势、位置与资料完整性。
模型排名靠前
位于 Top30，属于主要研究池。
资料待补
部分上下文字段尚未完整映射，需人工补看。
查看复盘重点
```

## 8. 安全边界自查

本轮确认：

- 未新增新数据源。
- 未联网拉取真实资料。
- 未使用 token。
- 未训练模型。
- 未 provider refresh/publish。
- 未 accepted latest switching。
- 未 monitor config save。
- 未 monitor scan。
- 未 alerts write。
- 未接 broker、quick-trade、orders。
- 未新增 portfolio replay POST。
- 未接 cross-analysis 或 rank-change 新数据流。
- 未使用 decision/actionPlan raw code。
- 未输出买卖、目标仓位、目标权重、收益承诺、上涨概率或胜率语义。

## 9. 用户第一性原则自查

- 简单：默认主线索仍最多 3 条，details 最多 5 条。
- 准确：仅使用页面已有只读上下文与后端白名单字段。
- 清晰：qlib score 明确为横截面研究排序分数；技术和位置指标只作为复盘线索。
- 实用：新增字段能帮助人工复盘看到趋势、技术、位置和资料提示，但不变成指标堆叠。

## 10. 结论

Phase R9 已完成最小上下文字段映射实现，并通过后端测试、前端静态检查、前端 build 与 browser readonly smoke。

建议审查 gate：

`manual_review_context_mapping_implementation_passed`
