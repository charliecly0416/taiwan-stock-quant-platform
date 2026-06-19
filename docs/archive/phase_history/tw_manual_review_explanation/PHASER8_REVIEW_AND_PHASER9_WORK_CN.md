# Phase R8 审查结论与 Phase R9 工作文档

审查日期：2026-06-12

审查入口：

- `docs/tw_manual_review_explanation/PHASER8_EXECUTION_REPORT_CN.md`
- `docs/tw_manual_review_explanation/manual_review_context_mapping_contract.md`
- `docs/tw_manual_review_explanation/PHASER7_REVIEW_AND_PHASER8_WORK_CN.md`
- `docs/tw_manual_review_explanation/manual_review_explanation_contract.md`
- `backend/app/services/tw_manual_review_explanation.py`
- `backend/app/routes/tw_stock.py`
- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/src/api/tw-stock.js`
- 台股只读安全边界审查规则

## 1. 本步审核结论

Phase R8 通过。

接受 gate：

`request_phaser9_context_mapping_implementation`

执行者没有偏离主线，也没有新增分支：

- 本轮只新增字段映射合同与执行报告。
- 未修改前端代码。
- 未修改后端代码。
- 未修改测试代码。
- 未新增 API 或 route。
- 未新增数据源。
- 未联网、未使用 token、未拉取数据。
- 未训练模型。
- 未 provider refresh/publish。
- 未 accepted latest switching。
- 未 monitor config save、monitor scan、alerts write。
- 未接 broker、quick-trade、orders。
- 未输出买卖、仓位、收益、上涨概率或胜率语义。

R8 合同把字段分成主线索、详情、数据提示和暂缓，符合“简单、准确、清晰、实用”的用户第一性原则。

## 2. 主线一致性审查

R8 仍在人工复盘解释模块后续增强主线内。

通过项：

- 明确 `rank-tech-cross/latest` 是当前最完整的既有只读上下文来源。
- 明确当前 manual-review GET 已支持部分扁平 query 字段。
- 明确当前前端尚未传入 technical、positionRisk、data_quality_warnings。
- 明确 qlib rank change、cross category/alignment、冻结规则卡真实来源、decision/actionPlan raw code 暂缓。
- 明确不把 qlib score、trend score、技术指标解释为收益、胜率、上涨概率或买卖建议。

需要收紧项：

- R9 不得直接接入 `cross-analysis/latest` 或 `cross-analysis/symbol`，否则会把人工复盘解释扩展成第二套交叉分析解释主线。
- R9 不得直接展示或依赖 `decision.code` / `actionPlan.code`，这些字段名和语义容易被用户理解成行动建议。
- R9 不得为了 rank change、ret5/ret20/ret60 或冻结规则卡真实来源新增数据流。

## 3. 用户第一性原则审查

通过。

- 简单：合同要求默认最多 3 条主线索，详情最多 5 条。
- 准确：字段来源限定为已有只读 API/service/frontend context。
- 清晰：每个字段说明了来源、可见位置、文案限制、fallback 和 R9 建议。
- 实用：R9 可按白名单做最小实现，不需要重新判断字段边界。

R9 仍需防止“字段完整”压倒用户理解：技术指标和分数只应作为少量解释线索，不应变成指标堆叠。

## 4. 上下文字段映射审查

R8 字段分层总体合理。

允许 R9 首版接入：

- `qlib_rank.rank`
- `qlib_rank.rank_tier`
- `qlib_rank.score`，只进详情或内部解释，不进默认主线索。
- `trend.trend_label`
- `trend.trend_score`
- `trend.latest_date`
- `technical.status`
- `technical.summary`
- `technical.strategies` 中 MA/RSI/MACD/Bollinger 的 `state` / `reason` / 少量安全 metrics。
- `positionRisk.status`
- `positionRisk.label`
- `positionRisk.reason`
- `positionRisk.metrics` 中少量白名单字段：`price_percentile_120d`、`distance_ma20_pct`、`distance_ma60_pct`、`rsi14`、`bollinger_position`、`return_5d_pct`、`return_20d_pct`。
- `data_quality_warnings`。

R9 必须暂缓：

- qlib rank change。
- ret60。
- cross category / alignment。
- 冻结法人/融资融券规则卡真实来源。
- decision/actionPlan raw code。
- 任何 raw payload 整包透传。

## 5. 浏览器 / Network 审查

R8 为 doc-only，未执行浏览器或 network audit，原因合理。

R9 实现后必须复跑 R7 的 browser readonly smoke，并证明：

- `manual_review_get_count>=1`
- `forbidden_request_count=0`
- `portfolio_replay_post_count=0`
- `monitor_config_write_count=0`
- `monitor_scan_post_count=0`
- `monitor_alerts_write_count=0`
- `provider_or_accepted_latest_write_count=0`
- `broker_quick_trade_order_count=0`
- `unsafe_trading_semantics_count=0`

R9 不得新增任何业务写请求。

## 6. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：R8 文档中出现 provider、accepted latest、broker、orders、收益、上涨概率、胜率等词，仅用于禁止事项、字段限制和安全边界说明，不构成动作入口或交易建议。

### Network Audit

R8 未运行 network audit。doc-only 阶段可接受。

### Console Audit

R8 未运行 console audit。doc-only 阶段可接受。

### Text / Agent Semantics

通过。未发现 actionable 买卖/仓位/收益/概率语义。

### Verdict

只读研究安全边界通过。

## 7. 必须修复项

当前 R8 无必须修复项。

## 8. 可暂缓项

- R7 遗留：`frontend/tests/unit/tw-stock-monitor-static-check.mjs` 当前工作区有改动但 R7 报告未列入。R9 如继续修改或依赖该文件，必须在执行报告中说明归属。
- R8 合同提到 `cross-analysis` 只读来源，但 R9 首版不得接入。
- R8 合同提到 rank change 和 returns，但 R9 首版只允许接已有稳定字段，不能为了补齐字段新增数据链路。

## 9. 是否需要用户确认

不需要。

R8 已按授权完成设计。R9 是既定计划中的最小字段映射实现，但必须严格限制在已有只读上下文和白名单字段内。

## 10. 给执行者的下一步工作文档

### Phase R9：最小上下文字段映射实现

你是执行者。本轮只允许按 R8 合同实现 manual-review 的最小上下文字段增强。

#### 目标

把现有只读上下文字段以白名单方式传入 manual-review explanation，让复盘线索更贴近真实页面上下文，但仍保持简单、准确、清晰、实用。

R9 首版只做：

- 后端 service 白名单解析增强。
- 现有 GET route 的扁平 query 解析增强。
- 前端 `buildManualReviewParams()` 从页面已有只读上下文中补充白名单字段。
- 后端/前端静态检查和 R7 浏览器只读 smoke 复跑。

不得新增 API、不得新增 route、不得新增数据源。

#### 必读材料

必须阅读：

- `docs/tw_manual_review_explanation/PHASER8_REVIEW_AND_PHASER9_WORK_CN.md`
- `docs/tw_manual_review_explanation/manual_review_context_mapping_contract.md`
- `docs/tw_manual_review_explanation/manual_review_explanation_contract.md`
- `docs/tw_manual_review_explanation/PHASER7_REVIEW_AND_PHASER8_WORK_CN.md`
- `backend/app/services/tw_manual_review_explanation.py`
- `backend/app/routes/tw_stock.py`
- `backend/tests/test_tw_manual_review_explanation.py`
- `backend/tests/test_tw_manual_review_explanation_api.py`
- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/src/api/tw-stock.js`
- `frontend/tests/unit/tw-stock-manual-review-explanation-check.mjs`
- `frontend/tests/e2e/tw-stock-manual-review-readonly.mjs`

#### 允许修改

允许修改：

- `backend/app/services/tw_manual_review_explanation.py`
- `backend/app/routes/tw_stock.py`
- `backend/tests/test_tw_manual_review_explanation.py`
- `backend/tests/test_tw_manual_review_explanation_api.py`
- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/tests/unit/tw-stock-manual-review-explanation-check.mjs`
- `frontend/tests/unit/tw-stock-monitor-static-check.mjs`，仅当本轮改动导致静态检查必须同步时；若修改，报告必须说明原因和归属。
- `frontend/tests/e2e/tw-stock-manual-review-readonly.mjs`，仅为更新 fixture 或断言。

必须新增：

- `docs/tw_manual_review_explanation/PHASER9_EXECUTION_REPORT_CN.md`

#### 后端实现要求

后端只允许做白名单解析，不得整包透传。

允许新增或扩展的 context 字段：

- `qlib_rank.score`
- `trend.latest_date`
- `technical_status.summary`
- `technical_status.strategies`
- `position_risk.label`
- `position_risk.reason`
- `position_risk.metrics`
- `data_quality_warnings`

route 仍必须是：

- `GET /api/tw-stock/manual-review/explanation`

不得新增 POST 或新 route。

如果 query 参数需要扁平化，建议使用明确字段名，例如：

- `qlibScore`
- `trendLatestDate`
- `technicalStatus`
- `technicalSummary`
- `technicalStrategies`
- `positionLabel`
- `positionReason`
- `pricePercentile120d`
- `distanceMa20Pct`
- `distanceMa60Pct`
- `bollingerPosition`
- `return20dPct`
- `dataQualityWarnings`

如传递数组或对象，必须只接受 JSON 字符串中的白名单字段，并在 service 内再次过滤。解析失败时应降级为数据提示，不应报 500。

#### 前端实现要求

前端只能从已加载的只读上下文取字段：

- 当前 qlib row。
- 当前 symbol 对应的 `rankTechItems` / `rank-tech-cross/latest` item。
- 当前已有 trend / technical / positionRisk / warnings 字段。

前端不得：

- 新增 API 请求来补字段。
- 调用 `cross-analysis` 作为 R9 首版字段来源。
- 调用 rank changes 作为 R9 首版字段来源。
- 调用任何 provider/monitor/ops/refresh/scan/alerts/broker/order 路径。

如果某字段当前页面没有加载到，就不要强行补；让后端 fallback 到数据提示。

#### 输出限制

R9 后用户可见输出必须继续满足：

- 默认 `signals` 最多 3 条。
- 详情/复盘重点最多 5 条。
- 不展示 raw rule id。
- 不展示 provider、gate、run id、IC、RankIC、训练指标。
- 不展示 decision/actionPlan raw code。
- 不展示 target horizon、target position、target weight。
- 不输出买入、卖出、持有建议。
- 不输出仓位建议、收益承诺、上涨概率或胜率承诺。

分数与指标文案必须保持解释性：

- qlib score 只能称为“研究排序分数”。
- trend score 只能称为“趋势强弱分”。
- RSI、Bollinger、均线距离只能称为“复盘线索”或“位置风险线索”。
- return_5d / return_20d 只能表示已发生涨跌背景，不得写成未来收益。

#### 必须暂缓

R9 不得实现：

- qlib rank change。
- ret60。
- cross category / alignment。
- 冻结法人/融资融券规则卡真实来源接入。
- decision/actionPlan raw code 映射。
- 新详情页或新产品入口。
- 新数据源或新 API。

#### 必跑验证

至少执行：

- `python -m py_compile backend/app/routes/tw_stock.py backend/app/services/tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation_api.py`
- `python -m pytest backend/tests/test_tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation_api.py -q`
- `node frontend/tests/unit/tw-stock-manual-review-explanation-check.mjs`
- `node frontend/tests/unit/tw-stock-monitor-static-check.mjs`
- `node --check frontend/tests/e2e/tw-stock-manual-review-readonly.mjs`
- R7 Playwright readonly smoke
- 如前端改动影响 build，执行 `corepack pnpm build`，工作目录 `frontend`

R7 Playwright readonly smoke 必须继续输出并满足：

- `forbidden_request_count=0`
- `manual_review_get_count>=1`
- `portfolio_replay_post_count=0`
- `monitor_config_write_count=0`
- `monitor_scan_post_count=0`
- `monitor_alerts_write_count=0`
- `provider_or_accepted_latest_write_count=0`
- `broker_quick_trade_order_count=0`
- `unsafe_trading_semantics_count=0`

#### R9 执行报告要求

新增：

- `docs/tw_manual_review_explanation/PHASER9_EXECUTION_REPORT_CN.md`

报告必须包含：

- 当前阶段目标。
- 修改文件清单。
- 字段实现清单。
- 暂缓字段清单。
- 是否新增 API/route。
- 是否新增数据源。
- 是否修改默认页面行为。
- 是否修改 R7 query flag/test-only mode。
- 验证命令与结果。
- Playwright network/console artifact 路径。
- 页面文本摘要。
- 用户第一性原则自查。
- 安全边界自查。
- 是否偏离主线。
- 是否新增分支。
- 推荐 gate。

#### R9 Gate

R9 通过时建议 gate：

`manual_review_context_mapping_implementation_passed`

R9 需要修复时：

`phaser9_context_mapping_implementation_needs_repair`

如发现范围越权：

`stop_manual_review_next_round_scope_invalid`

#### 必须停下来讨论的情况

出现以下任一情况，立即停止：

- 需要新增 API 或 route。
- 需要新增数据源、联网、token、拉取数据或补数据。
- 需要训练模型。
- 需要 provider refresh/publish 或 accepted latest switching。
- 需要 monitor 写入、扫描或 alerts。
- 需要 broker、quick-trade、orders。
- 需要 target position 或 target weight。
- 需要买入、卖出、持有、仓位、收益、上涨概率或胜率语义。
- 需要接入 cross-analysis、rank change、冻结规则卡真实来源或 decision/actionPlan raw code。
- 页面输出开始变成字段堆叠，破坏简单、准确、清晰、实用。
