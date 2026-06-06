# 台股产品适配 Phase 4 Report：浏览器安全验收与研究信号模拟草稿联动

日期：2026-06-05

## 1. 执行结论

已按 `docs/TW_STOCK_PRODUCT_ADAPTATION_PHASE4_EXECUTION_CN.md` 完成 Phase 4。执行顺序符合文档要求：先补 `/tw-stock-sim-account` Playwright smoke/network audit，再扩展后端 `source_type/source_context`，最后实现研究页到模拟账户页的最小预填联动。

本阶段仍然只生成模拟草稿，不会在研究页直接创建草稿 API 请求，不会自动确认成交，不连接券商，不触发真实订单、monitor scan、alerts write、qlib ops、provider refresh/publish、accepted latest switch 或 Agent chat。

## 2. 新增/修改文件

新增：

- `frontend/tests/e2e/tw-stock-sim-account-smoke.mjs`
- `docs/TW_STOCK_PRODUCT_ADAPTATION_PHASE4_REPORT_CN.md`

修改：

- `backend/app/services/tw_stock_sim_account.py`
- `backend/app/routes/tw_stock.py`
- `backend/tests/test_tw_stock_sim_account.py`
- `frontend/src/api/tw-stock.js`
- `frontend/src/views/tw-stock-sim-account/index.vue`
- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/tests/unit/tw-stock-sim-account-check.mjs`
- `frontend/tests/unit/tw-stock-cross-analysis-check.mjs`

## 3. Phase 3 补测与 Network Audit

新增浏览器 smoke：`frontend/tests/e2e/tw-stock-sim-account-smoke.mjs`。

覆盖场景：

- 写入测试 token 后打开 `/#/tw-stock-sim-account`。
- mock 一个已有模拟账户。
- 页面展示固定边界提示。
- 生成 rejected 模拟买入草稿，确认按钮不显示。
- 生成 draft 模拟买入草稿，确认和取消按钮显示。
- 只有用户显式点击 `确认模拟成交` 后才调用 confirm endpoint。
- confirm 后刷新账户详情、持仓、成交记录接口。
- 截图保存到 `/tmp/quantdinger_tw_sim_account_e2e`。

Network audit 结果：

```json
{
  "sim_request_count": 10,
  "forbidden_request_count": 0,
  "quick_trade_request_count": 0,
  "broker_request_count": 0,
  "real_order_request_count": 0,
  "monitor_scan_post_count": 0,
  "monitor_alerts_write_count": 0,
  "qlib_ops_post_count": 0,
  "agent_chat_request_count": 0
}
```

截图产物在 `/tmp/quantdinger_tw_sim_account_e2e`，未写入仓库。

## 4. 后端 source_type / source_context 改动

`ALLOWED_SOURCE_TYPES` 从仅 `manual` 扩展为：

```text
manual
qlib_rank
cross_analysis
agent_research
```

仍然拒绝非白名单 source，例如 `agent`。

Schema 兼容扩展：

- `qd_tw_sim_orders.source_context_json TEXT DEFAULT ''`
- `qd_tw_sim_trades.source_context_json TEXT DEFAULT ''`

`ensure_schema()` 中加入兼容性 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`，旧库可补字段。

草稿接口继续使用：

```text
POST /api/tw-stock/sim/orders/draft
```

并新增透传：

```json
{
  "source_type": "qlib_rank | cross_analysis | agent_research",
  "source_context": {
    "symbol": "2330",
    "asof": "2026-06-04",
    "run_id": "run-1",
    "qlib_rank": 1,
    "qlib_score": 0.1234,
    "trend_label": "uptrend",
    "cross_category": "focus_watch",
    "cross_alignment": "aligned",
    "bucket": "top30",
    "source_label": "研究排名",
    "user_edited": false
  }
}
```

后端会规范化 `source_context` 字段，只保留允许字段，并强制 context 中的 `symbol` 与规范化后的请求 symbol 一致。

## 5. 新增研究页入口

`/tw-stock-monitor` 新增两个只预填入口：

- 今日研究排名 Top30/Top50 行：`生成模拟草稿`，写入 `source_type=qlib_rank`。
- 交叉分析行：`生成模拟草稿`，写入 `source_type=cross_analysis`。

交叉分析入口限制：

- `focus_watch` 可预填。
- `aligned` 可预填。
- `model_trend_divergence`、`data_review_required` 等不默认预填模拟买入，按钮禁用。

研究页按钮只写入 localStorage：

```text
tw-stock-sim-draft-context
```

然后跳转到：

```text
/tw-stock-sim-account
```

研究页不会调用 `draftTwStockSimOrder`，不会调用 `confirmTwStockSimOrder`。

## 6. 跳转/预填流程

流程如下：

1. 用户在台股研究页点击 `生成模拟草稿`。
2. 前端写入 `tw-stock-sim-draft-context`。
3. 页面跳转到 `/tw-stock-sim-account`。
4. 模拟账户页读取 context 后预填 symbol、side、quantity、source_type、source_context。
5. 页面显示“已从研究排名/交叉分析预填模拟草稿”的提示。
6. 用户仍需手动点击 `生成模拟买入草稿`。
7. 后端返回参考价、价格日期、费用、税费、warnings。
8. 用户看到草稿详情后，才会出现 `确认模拟成交`。
9. 只有用户显式点击 `确认模拟成交` 才调用 confirm。

如果用户修改 symbol 或 quantity，前端会在 `source_context.user_edited=true` 标记人工修改。

## 7. 安全边界审查

静态审查和 Playwright network audit 均通过。

新增模拟账户页仍只导入模拟账户 API helper。研究页新增入口只调用 localStorage 和 router，不直接调用模拟草稿 API，更不会 confirm。

风险词 grep 命中主要来自：

- 静态测试中的禁止清单。
- E2E network audit 的危险路径计数规则。
- `frontend/src/api/tw-stock.js` 中历史已有 monitor/Agent/ops helper。

新增模拟账户流程没有触发这些历史 helper。Playwright network audit 中危险请求计数为 0。

## 8. 测试命令与结果

后端：

```bash
PYTHONPATH=backend python -m pytest backend/tests/test_tw_stock_sim_account.py -q
# 8 passed

PYTHONPATH=backend python -m pytest backend/tests/test_tw_stock_quant_signal_api.py -q
# 18 passed

python -m py_compile backend/app/services/tw_stock_sim_account.py backend/app/routes/tw_stock.py
# passed
```

前端静态与构建：

```bash
cd frontend
node tests/unit/tw-stock-sim-account-check.mjs
# passed

node tests/unit/tw-stock-monitor-static-check.mjs
# passed

node tests/unit/tw-stock-cross-analysis-check.mjs
# passed

corepack pnpm build
# passed
```

浏览器 smoke：

```bash
cd frontend
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8000 node tests/e2e/tw-stock-sim-account-smoke.mjs
# passed
```

备注：命令环境仍会输出 `/bin/sh: 2: source: not found`，但上述通过项退出码均为 0，不影响测试结论。

## 9. 是否建议进入 Phase 5

建议进入 Phase 5。Phase 4 已把“研究信号 -> 模拟账户草稿”的链路控制在预填层，浏览器级 network audit 已证明没有危险请求。Phase 5 可以继续做 K 线模拟成交标记、模拟账户绩效复盘和更清晰的历史验证视图，但仍应保持“不自动确认、不连接券商、不承诺收益”的边界。
