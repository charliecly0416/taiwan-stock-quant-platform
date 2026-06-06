# 台股产品适配 Phase 4 执行文档：浏览器安全验收与研究信号模拟草稿联动

日期：2026-06-05

## 1. Phase 3 审查结论

Phase 3 没有偏离主线，可以进入 Phase 4。

Phase 3 已完成前端模拟账户 MVP：`/tw-stock-sim-account` 页面可以创建/查看模拟账户、展示现金/持仓/权益、手动生成模拟买入/卖出草稿、确认或取消模拟成交，并防御式校验 `simulation_only=true`、`real_orders_enabled=false`、`connects_to_broker=false`。

抽查结果：新增页面只导入 `getTwStockSimAccounts`、`createTwStockSimAccount`、`getTwStockSimAccount`、`getTwStockSimPositions`、`getTwStockSimTrades`、`draftTwStockSimOrder`、`confirmTwStockSimOrder`、`cancelTwStockSimOrder`，没有导入 quick-trade、broker、Agent chat、monitor scan、alerts write 或 qlib ops。`frontend/src/api/tw-stock.js` 中虽然仍存在历史 monitor/Agent/ops helper，但 Phase 3 页面没有调用它们。

需要补强点：Phase 3 没有跑浏览器级 Playwright/network audit。Phase 4 必须先补这个验收，再做信号联动，避免前端功能扩大后才发现危险请求。

## 2. 本步目标

Phase 4 分成两个连续子任务，执行者必须按顺序完成：

1. 先补 `/tw-stock-sim-account` 浏览器级 Playwright smoke 和 network audit。
2. 再实现研究信号到“模拟交易草稿”的最小联动。

本阶段仍然只能生成模拟草稿，不能直接确认成交，不能自动交易，不能连接券商。

## 3. 子任务 A：补模拟账户浏览器安全验收

新增测试建议：

```text
frontend/tests/e2e/tw-stock-sim-account-smoke.mjs
```

如果项目现有 E2E 放在 `frontend/tests/unit`，也可沿用现有命名风格，但报告必须说明位置。

测试需要覆盖：

- 登录或写入测试 token 后打开 `/#/tw-stock-sim-account`。
- mock 或真实后端返回一个模拟账户。
- 页面展示固定边界提示。
- 生成模拟买入草稿。
- rejected 草稿不显示“确认模拟成交”。
- draft 草稿显示“确认模拟成交”和“取消草稿”。
- 点击确认后刷新账户、持仓、成交记录。
- 截图保存到 `/tmp/quantdinger_tw_sim_account_e2e` 或类似路径。

Network audit 必须统计并在测试输出中打印：

```text
sim_request_count
forbidden_request_count
quick_trade_request_count
broker_request_count
real_order_request_count
monitor_scan_post_count
monitor_alerts_write_count
qlib_ops_post_count
agent_chat_request_count
```

验收标准：

```text
forbidden_request_count=0
quick_trade_request_count=0
broker_request_count=0
real_order_request_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
qlib_ops_post_count=0
agent_chat_request_count=0
sim_request_count>0
```

## 4. 子任务 B：后端受控扩展 source_type

Phase 2 后端目前只允许 `source_type=manual`。Phase 4 如果要让研究信号生成草稿，必须先受控扩展白名单，但仍然只写模拟订单。

允许新增的 `source_type`：

```text
qlib_rank
cross_analysis
agent_research
```

不要使用：

```text
agent
paper_order
broker_order
strategy
live
```

后端草稿接口可以继续使用：

```text
POST /api/tw-stock/sim/orders/draft
```

但请求必须显式包含：

```json
{
  "source_type": "qlib_rank | cross_analysis | agent_research",
  "source_context": {
    "symbol": "2330",
    "asof": "YYYY-MM-DD",
    "run_id": "...",
    "qlib_rank": 1,
    "qlib_score": 0.1234,
    "trend_label": "uptrend",
    "cross_category": "focus_watch"
  }
}
```

后端需要持久化 source context。建议最小改动：

- 在 `qd_tw_sim_orders` 增加 `source_context_json TEXT DEFAULT ''`。
- 在 `qd_tw_sim_trades` 增加 `source_context_json TEXT DEFAULT ''`。
- payload 返回 `source_context`。

注意：如果当前 schema 迁移机制不完善，可以在 `ensure_schema()` 中用兼容性 `ALTER TABLE ADD COLUMN IF NOT EXISTS`，并补测试。

后端必须继续拒绝：

- 非白名单 source_type。
- 缺少 symbol/quantity/side 的草稿。
- 不符合 1000 股倍数的数量。
- 缺价格。
- 现金不足。
- 卖空。

## 5. 子任务 C：前端最小联动入口

允许新增两个入口，先不要做 Agent 联动：

1. `tw-stock-monitor` 的 Top30/Top50 行按钮：`生成模拟草稿`。
2. cross-analysis 的 `focus_watch` 或 `aligned` 项按钮：`生成模拟草稿`。

Agent 回答区域联动暂缓到下一阶段。原因：Agent 语义更容易被用户理解为“AI 建议买入”，需要单独审查文案和拒答边界。

入口行为：

- 点击后不直接调用 confirm。
- 只生成草稿数据并跳转或打开 `/tw-stock-sim-account`。
- 在模拟账户页让用户选择账户、确认 symbol、side、quantity。
- 用户点击“生成模拟买入草稿”后才调用 `/sim/orders/draft`。
- 用户看到价格/费用/warnings 后，才允许点击“确认模拟成交”。

推荐实现方式：

- 从研究页写入 localStorage 草稿上下文，例如 `tw-stock-sim-draft-context`。
- 模拟账户页读取后填充 symbol、side、quantity、source_type、source_context。
- 读取后不要自动提交；只作为表单预填。
- 用户改动 symbol/quantity 后，source_context 仍保留但需要标记 `user_edited=true` 或清晰显示“已人工修改”。

## 6. 保守业务规则

默认 side 规则：

- `focus_watch` / `aligned`：可预填 `模拟买入`，但文案必须是“生成模拟买入草稿”，不是“建议买入”。
- `model_trend_divergence` / `data_review_required`：不预填买入；只允许生成观察草稿或提示“该项需人工复核，不生成默认模拟买入草稿”。
- Top30/Top50：可预填 `模拟买入`，但必须显示“仅用于历史与模拟验证”。

数量规则：

- 默认 1000 股。
- 不根据 qlib_score 自动计算仓位。
- 不出现目标仓位、目标权重、推荐仓位。

## 7. 禁止事项

Phase 4 禁止：

- 真实买入/真实卖出。
- 一键买入/一键卖出。
- 自动下单。
- 跟随 AI 买入。
- 目标仓位/目标权重。
- 从 Agent 回答直接生成草稿。
- 点击研究页按钮后自动调用 confirm。
- 点击研究页按钮后直接写入 filled trade。
- 触发 broker、quick-trade、真实 order API。
- 触发 monitor scan、alerts write、qlib ops dry-run、provider refresh/publish、accepted latest switch。
- 触发 OpenAI/Agent chat。

## 8. K 线标记

K 线买卖点标记本阶段暂不做，推迟到 Phase 5。

原因：Phase 4 的核心风险是“研究信号到模拟草稿”容易越界，先把草稿链路和 network audit 做稳更重要。

## 9. 必跑测试

后端：

```bash
PYTHONPATH=backend python -m pytest backend/tests/test_tw_stock_sim_account.py -q
PYTHONPATH=backend python -m pytest backend/tests/test_tw_stock_quant_signal_api.py -q
```

前端静态：

```bash
cd frontend
node tests/unit/tw-stock-sim-account-check.mjs
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-cross-analysis-check.mjs
corepack pnpm build
```

浏览器 smoke：

```bash
cd frontend
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8000 node tests/e2e/tw-stock-sim-account-smoke.mjs
```

如果新增了 signal draft smoke，则执行：

```bash
cd frontend
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8000 node tests/e2e/tw-stock-sim-signal-draft-smoke.mjs
```

如果本地服务无法启动，报告必须说明原因，并至少提供静态检查结果；但 Phase 4 不建议在完全没有 Playwright/network audit 的情况下收尾。

## 10. 验收标准

必须同时满足：

- `/tw-stock-sim-account` Playwright/network audit 通过。
- Top30/Top50 只能预填模拟草稿，不能直接成交。
- cross-analysis 只能对 `focus_watch/aligned` 预填模拟买入草稿。
- divergence/data_review 不默认买入。
- 后端接受 `qlib_rank/cross_analysis/agent_research` 白名单，但本阶段前端只实际使用 `qlib_rank/cross_analysis`。
- 所有模拟订单仍返回 `simulation_only=true`。
- network audit 中危险请求计数全部为 0。
- 页面文案没有真实交易、自动交易、目标仓位、收益承诺。

## 11. 报告断点

完成后提交：

```text
docs/TW_STOCK_PRODUCT_ADAPTATION_PHASE4_REPORT_CN.md
```

报告必须包含：

- Phase 3 补测结果和 network audit 计数。
- 后端 `source_type` 和 `source_context` 改动说明。
- 新增研究页入口清单。
- 草稿字段示例。
- 研究页到模拟账户页的跳转/预填流程。
- 确认流程说明，证明不会自动 confirm。
- 所有测试命令和结果。
- 是否出现真实交易文案或危险 API。
- 是否建议进入 Phase 5。
