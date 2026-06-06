# 台股产品适配最终验收

日期：2026-06-05

## 1. Phase 1-5 完成状态

Phase 1-5 已全部完成。

- Phase 1：台股研究页信息结构收敛，弱化冗余运维信息，明确研究边界。
- Phase 2：后端模拟账户 API 建立，支持模拟账户、模拟草稿、确认模拟成交、取消草稿、持仓和成交记录。
- Phase 3：模拟账户前端 MVP 建立，用户可创建账户、生成草稿、确认/取消模拟成交。
- Phase 4：补浏览器 smoke/network audit，扩展 `source_type/source_context`，研究页到模拟账户页实现只预填联动。
- Phase 5：补绩效复盘、模拟成交标记、研究页到模拟账户全链路 Playwright/network audit。

## 2. 当前产品主线

当前台股产品主线清楚：

```text
研究 -> 模拟 -> 复盘
```

它不是实盘交易终端，不连接券商，不提交真实订单，不提供自动交易或目标仓位。

## 3. 页面清单

核心页面：

- `/tw-stock-monitor`：台股研究页，展示 Top30/Top50、排名变化、交叉分析、Agent 研究上下文、K 线与只读历史验证。
- `/tw-stock-sim-account`：台股模拟账户页，展示账户、持仓、成交、模拟草稿、确认/取消、绩效复盘、模拟成交标记列表。

相关展示：

- 交叉分析：只读研究解释和人工复盘，不触发交易。
- Agent 区域：研究上下文问答，不做模拟草稿联动；如需联动应另开 Phase 6 审查。

## 4. API 清单

只读研究 API：

- `/api/tw-stock/quant/signals/latest`
- `/api/tw-stock/quant/signals/rank-changes`
- `/api/tw-stock/cross-analysis/latest`
- `/api/tw-stock/cross-analysis/symbol/**`
- `/api/tw-stock/agent/context`
- `/api/tw-stock/trends`
- `/api/indicator/kline`

模拟账户 API：

- `GET /api/tw-stock/sim/accounts`
- `POST /api/tw-stock/sim/accounts`
- `GET /api/tw-stock/sim/accounts/:account_uid`
- `GET /api/tw-stock/sim/accounts/:account_uid/positions`
- `GET /api/tw-stock/sim/accounts/:account_uid/trades`
- `POST /api/tw-stock/sim/orders/draft`
- `POST /api/tw-stock/sim/orders/:sim_order_uid/confirm`
- `POST /api/tw-stock/sim/orders/:sim_order_uid/cancel`

禁止触发的 API：

- quick-trade。
- broker。
- 真实 order/orders。
- monitor scan POST。
- alerts POST/PUT/PATCH/DELETE。
- qlib ops POST。
- provider refresh/publish。
- accepted latest switch。
- Agent chat 联动模拟草稿。

## 5. 模拟账户闭环

闭环成立：

1. 研究页 Top30/Top50 或 cross-analysis 只写入 localStorage 预填上下文。
2. 页面跳转到模拟账户页。
3. 模拟账户页预填 symbol、side、quantity、source_type、source_context。
4. 用户手动生成模拟草稿。
5. 用户查看参考价、价格日期、费用、交易税、warning。
6. 用户手动确认模拟成交。
7. 页面刷新持仓、成交记录、绩效复盘和模拟成交标记。

## 6. 全链路验收

已通过浏览器全链路 Playwright/network audit：

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

## 7. 真实交易能力泄漏

未发现真实交易能力泄漏。

所有新增流程均保持：

- `simulation_only=true`。
- `real_orders_enabled=false`。
- `connects_to_broker=false`。
- 用户显式确认才会写入模拟成交。
- 研究页不直接调用 draft/confirm。

## 8. 最终结论

可以收尾。

当前版本已经形成清晰、简单、准确的台股研究与模拟验证产品线。后续新增功能应继续围绕复盘质量提升，例如更丰富的 marker hover 详情、绩效曲线、持仓周期分析和指数对比；任何 Agent 到模拟草稿联动都应另开阶段并重新审查语义边界。
