# 台股产品适配 Phase 5 Report：绩效复盘与全链路最终验收

日期：2026-06-05

## 1. 执行结论

已按 `docs/TW_STOCK_PRODUCT_ADAPTATION_PHASE5_EXECUTION_CN.md` 完成 Phase 5。当前闭环为：

```text
研究信号 -> 模拟草稿预填 -> 用户生成模拟草稿 -> 用户确认模拟成交 -> 持仓计价 -> 绩效复盘 -> 全链路安全验收
```

本阶段没有扩大到 Agent 联动、自动交易、真实券商连接、目标仓位/目标权重、provider refresh/publish、accepted latest switch 或数据拉取改动。

## 2. 新增/修改文件

新增：

- `frontend/tests/e2e/tw-stock-sim-account-full-flow.mjs`
- `docs/TW_STOCK_PRODUCT_ADAPTATION_PHASE5_REPORT_CN.md`
- `docs/TW_STOCK_PRODUCT_ADAPTATION_FINAL_ACCEPTANCE_CN.md`

修改：

- `frontend/src/views/tw-stock-sim-account/index.vue`
- `frontend/tests/unit/tw-stock-sim-account-check.mjs`

## 3. 绩效复盘指标

模拟账户页新增 `绩效复盘` 区块，基于已有 account/positions/trades 前端计算，不新增后端 API。

展示指标：

- 初始资金。
- 现金。
- 持仓市值。
- 总权益。
- 累计收益金额。
- 累计收益率。
- 持仓浮动盈亏。
- 已实现盈亏 MVP：卖出成交按移动平均成本估算。
- 胜负笔数 MVP：基于已实现盈亏正负统计。
- 累计手续费。
- 累计交易税。
- 按来源统计成交数量：`manual / qlib_rank / cross_analysis / agent_research`。

页面明确显示：

```text
历史/模拟结果，不代表未来收益。价格按最新可用收盘价估算；价格缺失或日期滞后时请先复核数据。
```

## 4. K 线模拟成交标记

后续补充已在台股研究页现有 canvas K 线图上叠加 `模拟买入` / `模拟卖出` marker，并保留模拟账户页的 `模拟成交标记` 简化列表。

原因：当前核心风险仍是研究信号与模拟成交链路的安全边界；先用清晰列表验证成交标记的业务含义，后续如要叠加到 K 线图，可以在不改变交易链路的前提下做 UI 增强。

当前 marker/list 支持：

- 按 symbol 过滤。
- 展示 `模拟买入` / `模拟卖出`。
- 展示成交日期、模拟价格、数量、source_type。
- 不展示真实订单 ID。
- 不展示券商账号。
- 不展示目标仓位或目标权重。

## 5. Top30 / Cross 全链路流程

新增浏览器测试：

```text
frontend/tests/e2e/tw-stock-sim-account-full-flow.mjs
```

覆盖 Top30/Top50 链路：

1. 打开 `/#/tw-stock-monitor`。
2. mock latest qlib signals，展示 Top30 数据。
3. 点击 Top30 行 `生成模拟草稿`。
4. 跳转到 `/#/tw-stock-sim-account`。
5. 验证 symbol=2330、source_type=qlib_rank 已预填。
6. 验证跳转后还没有调用 `/sim/orders/draft`。
7. 用户点击 `生成模拟买入草稿` 后才调用 draft。
8. 用户点击 `确认模拟成交` 后才调用 confirm。
9. 验证 `绩效复盘` 和 `模拟成交标记` 出现在模拟账户页。

覆盖 cross-analysis 链路：

1. mock `focus_watch/aligned` 项。
2. 点击 `生成模拟草稿`。
3. 验证 source_type=`cross_analysis`。
4. 验证 `model_trend_divergence` 行按钮禁用，不默认生成模拟买入草稿。
5. 验证跳转后仍需用户手动点击 `生成模拟买入草稿` 才调用 draft。

## 6. Playwright / Network Audit

模拟账户 smoke：

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

全链路 full-flow：

```json
{
  "sim_request_count": 18,
  "forbidden_request_count": 0,
  "quick_trade_request_count": 0,
  "broker_request_count": 0,
  "real_order_request_count": 0,
  "monitor_scan_post_count": 0,
  "monitor_alerts_write_count": 0,
  "qlib_ops_post_count": 0,
  "agent_chat_request_count": 0,
  "accepted_latest_switch_count": 0,
  "provider_publish_refresh_count": 0
}
```

截图产物：

- `/tmp/quantdinger_tw_sim_account_e2e/01_loaded.png`
- `/tmp/quantdinger_tw_sim_account_e2e/02_rejected.png`
- `/tmp/quantdinger_tw_sim_account_e2e/03_draft.png`
- `/tmp/quantdinger_tw_sim_account_e2e/04_confirmed.png`
- `/tmp/quantdinger_tw_sim_full_flow_e2e/01_qlib_full_flow.png`
- `/tmp/quantdinger_tw_sim_full_flow_e2e/02_cross_prefill.png`

截图保存在 `/tmp`，未纳入仓库。

## 7. 测试命令与结果

后端：

```bash
PYTHONPATH=backend python -m pytest backend/tests/test_tw_stock_sim_account.py -q
# 8 passed

PYTHONPATH=backend python -m pytest backend/tests/test_tw_stock_quant_signal_api.py -q
# 18 passed

python -m py_compile backend/app/services/tw_stock_sim_account.py backend/app/routes/tw_stock.py
# passed
```

前端静态：

```bash
cd frontend
node tests/unit/tw-stock-sim-account-check.mjs
# passed

node tests/unit/tw-stock-monitor-static-check.mjs
# passed

node tests/unit/tw-stock-cross-analysis-check.mjs
# passed

node tests/unit/tw-stock-agent-panel-check.mjs
# passed

corepack pnpm build
# passed
```

浏览器：

```bash
cd frontend
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8000 node tests/e2e/tw-stock-sim-account-smoke.mjs
# passed

TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8000 node tests/e2e/tw-stock-sim-account-full-flow.mjs
# passed
```

备注：命令环境仍会输出 `/bin/sh: 2: source: not found`，但上述通过项退出码均为 0，不影响结论。

## 8. 安全边界

未出现真实交易能力泄漏。新增页面和测试保持以下边界：

- 不连接券商。
- 不提交真实订单。
- 不自动确认模拟成交。
- 不从研究页直接调用 draft/confirm。
- 不使用目标仓位/目标权重。
- 不把 qlib_score 解释为收益率、胜率、上涨概率或买入概率。
- 不触发 monitor scan、alerts write、qlib ops POST、Agent chat、provider publish/refresh 或 accepted latest switch。

风险词 grep 命中来自：边界提示、测试禁止清单、E2E network audit 计数规则，均不是可执行真实交易入口。

## 9. 是否建议最终收尾

建议最终收尾。Phase 1-5 已经把台股产品主线从“功能很多但不清晰”收敛到“研究、模拟、复盘”的可验收闭环，并且浏览器级全链路 network audit 通过。
