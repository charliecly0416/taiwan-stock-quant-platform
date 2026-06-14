# Phase R2 只读 API 执行报告

- 生成时间：`2026-06-11T18:02:41+00:00`
- 当前阶段目标：为 R1 人工复盘解释服务增加只读 GET API 入口，返回符合 contract 的 explanation JSON。
- 执行范围：只新增 GET API route、query 参数到内存 context 的轻量适配、API 单元测试；未接前端，未新增数据源，未联网，未写数据库/provider。

## 1. 修改文件

- 修改 `backend/app/routes/tw_stock.py`
- 新增 `backend/tests/test_tw_manual_review_explanation_api.py`
- 新增 `docs/tw_manual_review_explanation/PHASER2_EXECUTION_REPORT_CN.md`

## 2. 新增 Route 列表

- `GET /api/tw-stock/manual-review/explanation`

未新增：

- POST
- PUT
- PATCH
- DELETE

## 3. API 输入输出摘要

输入来源：仅 query string，由 route 组装为内存 context 后调用 R1 `TWManualReviewExplanationService`。

支持的 query 参数包括：

- `symbol`
- `name`
- `asof` / `asOf`
- `rank`
- `rankTier` / `rank_tier`
- `trendLabel` / `trend_label`
- `trendScore` / `trend_score`
- `technicalStatus` / `technical_status`
- `positionStatus` / `position_status`
- `pricePercentile120d` / `price_percentile_120d`
- `rsi14`
- `return5dPct` / `return_5d_pct`
- `frozenRules` / `frozen_rules`

输出字段遵循 R0/R1 contract：

- `symbol`
- `name`
- `asof`
- `overall_status`
- `status_label`
- `confidence`
- `summary`
- `signals`
- `next_review_focus`
- `research_only=true`
- `not_trading_advice=true`
- `data_quality_notes`

数据不足时，API 不补拉数据，直接返回 `overall_status=data_insufficient` 或 contract violation 的只读错误结构。

## 4. 测试覆盖摘要

新增 API 测试覆盖：

1. GET 正常返回 explanation JSON，字段符合 contract。
2. GET 数据不足时返回安全解释，不触发数据补齐或 provider。
3. GET 输出通过禁止字段/禁止文案扫描。
4. POST/PUT/PATCH/DELETE 均不是该 route 的可用写入口。
5. API 测试确认不会调用 monitor、provider ops、normal publish、accepted latest scheduler 等路径。

## 5. 验证命令

- `python -m py_compile backend/app/routes/tw_stock.py backend/app/services/tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation_api.py`
- `python -m pytest backend/tests/test_tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation_api.py -q`

结果：11 个专项测试通过。

## 6. 安全边界检查

- 是否接前端：否。
- 是否联网/token：否。
- 是否新增数据源：否。
- 是否写数据库/provider：否。
- 是否 provider refresh/publish：否。
- 是否 accepted latest switching：否。
- 是否调用 monitor：否。
- 是否 broker / quick-trade / orders：否。
- 是否训练模型：否。
- 是否出现买卖/仓位/收益/概率语义：正常 API 输出无；相关词仅在禁止语义扫描器、测试负例和安全报告中出现。
- 是否读取或生成 fundamental 月营收输入：否。

## 7. 推荐 Gate

- recommended_gate：`request_phaser3_frontend_readonly_work`
- gate_reason：R2 只读 GET API 已接入并通过专项测试；无 POST/PUT/PATCH/DELETE 写入口，无联网/token/新数据源，无数据库/provider 写入，无 accepted latest switching，无 monitor/broker/orders，无交易/仓位/收益/概率语义。

## 8. 风险与待审查问题

- R3 若接前端，必须仅展示只读 explanation，不触发保存、扫描、告警、交易或 provider 操作。
- 当前 R2 只接受 query 参数或测试 fixture 形成内存 context；尚未接真实只读上下文字段映射。若后续接入真实上下文，需继续审查字段来源和禁止语义。
- 前端文案必须避免把 `multi_source_support` 写成推荐、确认或高概率。

完成后等待审查者审核，不自动进入 R3。
