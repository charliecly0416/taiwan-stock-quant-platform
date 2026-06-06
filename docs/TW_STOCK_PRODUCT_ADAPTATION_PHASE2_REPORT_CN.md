# 台股产品适配 Phase 2 Report：模拟账户后端核心 MVP

日期：2026-06-05

## 1. 执行结论

已按 `docs/TW_STOCK_PRODUCT_ADAPTATION_PHASE2_EXECUTION_CN.md` 完成台股模拟账户后端 MVP。新增后端服务和 API，支持用户创建模拟账户、手动创建模拟买入/卖出草稿、确认模拟成交、取消草稿、查看账户、持仓和成交记录。

本阶段只实现后端核心，不做前端页面，不做 Top30 / Agent / cross-analysis 联动。所有模拟接口都固定返回 `simulation_only=true`、`real_orders_enabled=false`、`connects_to_broker=false`。

## 2. 新增/修改文件清单

- 新增：`backend/app/services/tw_stock_sim_account.py`
- 修改：`backend/app/routes/tw_stock.py`
- 新增：`backend/tests/test_tw_stock_sim_account.py`
- 新增：`docs/TW_STOCK_PRODUCT_ADAPTATION_PHASE2_REPORT_CN.md`

说明：当前工作区仍存在 Phase 2 之前已积累的台股 Agent、自动化脚本、前端 Phase 1 等未提交改动；本报告仅说明本阶段新增的模拟账户后端 MVP。

## 3. API 契约

只读 API：

```text
GET /api/tw-stock/sim/accounts
GET /api/tw-stock/sim/accounts/:account_uid
GET /api/tw-stock/sim/accounts/:account_uid/positions
GET /api/tw-stock/sim/accounts/:account_uid/trades
```

模拟写入 API：

```text
POST /api/tw-stock/sim/accounts
POST /api/tw-stock/sim/orders/draft
POST /api/tw-stock/sim/orders/:sim_order_uid/confirm
POST /api/tw-stock/sim/orders/:sim_order_uid/cancel
```

统一响应边界：

```json
{
  "simulation_only": true,
  "trading": {
    "real_orders_enabled": false,
    "connects_to_broker": false,
    "simulation_only": true
  }
}
```

草稿/成交状态：

```text
draft | filled | cancelled | rejected
```

本阶段只允许：

```text
source_type=manual
```

`agent`、`qlib_rank`、`cross-analysis` 等来源联动保留到 Phase 4。

## 4. 数据模型

服务会幂等创建 4 张表：

```text
qd_tw_sim_accounts
qd_tw_sim_orders
qd_tw_sim_trades
qd_tw_sim_positions
```

核心字段：

- `account_uid` / `sim_order_uid` / `sim_trade_uid`：模拟系统内部 ID。
- `user_id`：按登录用户隔离。
- `simulation_only`：固定为 true。
- `source_type`：Phase 2 实际只接受 manual。
- `created_at / updated_at / filled_at`：模拟记录时间。

没有使用或返回：

```text
exchange_order_id
broker_account
target_position
target_weight
live trading mode
paper trading mode
```

## 5. 成交价格与费用规则

成交参考价：

- 只查询本地 `qd_tw_stock_daily_bars` 最新可用 `close`。
- `price_source=latest_close`。
- 不调用 KlineService 外部数据源，不触发 Yahoo / FinMind / daily auto update 数据拉取。
- 如果找不到本地价格，草稿直接 `rejected`，不会伪造成交。
- 如果最新收盘价日期滞后超过默认 3 天，返回 `stale_latest_close` warning。

费用公式：

```text
buy_gross = quantity * latest_close
buy_fee = buy_gross * 0.001425
buy_cash_required = buy_gross + buy_fee

sell_gross = quantity * latest_close
sell_fee = sell_gross * 0.001425
sell_tax = sell_gross * 0.003
sell_cash_credit = sell_gross - sell_fee - sell_tax
```

金额按 TWD 分位四舍五入；参考价保留 4 位小数。

## 6. 业务规则覆盖

已实现：

- 默认初始资金 1,000,000 TWD，也允许请求传入。
- 默认 1000 股整张交易。
- 买入会检查现金，现金不足则 `rejected`。
- 卖出会检查持仓，不允许卖空，超量卖出则 `rejected`。
- 确认草稿后才写入模拟成交和更新现金/持仓。
- 取消只允许取消 `draft` 状态。
- 账户 NAV 返回 cash、market_value、total_equity、total_pnl、total_return。

暂未实现：

- 多账户复杂权限模型。
- 零股模式。
- 除权息现金流模拟。
- nav snapshot。
- 前端模拟账户页面。
- 研究信号到模拟草稿联动。

## 7. 安全边界证明

本阶段没有触发：

- broker / quick-trade / 真实 order API。
- monitor scan。
- alerts write。
- qlib ops dry-run。
- provider refresh / publish / accepted latest switch。
- OpenAI / Agent chat。
- 外部数据拉取。

新增服务 `backend/app/services/tw_stock_sim_account.py` 的静态测试确认不包含：

```text
quick_trade
quick-trade
app.services.broker
place_order(
submit_order(
target_position
target_weight
tw_stock_qlib_option_c_ops
refresh provider
accepted latest
openai
```

备注：`backend/app/routes/tw_stock.py` 里已有 qlib ops / accepted latest 运维路由属于历史功能，并非本次新增模拟账户路径；Phase 2 新增 `/sim/**` 路由没有调用这些路径。

## 8. 测试结果

已执行：

```bash
PYTHONPATH=backend python -m pytest backend/tests/test_tw_stock_sim_account.py -q
```

结果：

```text
8 passed
```

覆盖点：

- 创建账户。
- 买入成功。
- 现金不足买入被拒。
- 卖出成功。
- 卖空被拒。
- 所有响应包含 `simulation_only=true`。
- 默认只支持 `source_type=manual`。
- 响应包含 `real_orders_enabled=false` 和 `connects_to_broker=false`。
- 缺少价格时不会成交。
- 日期滞后时返回 warning。
- 服务源码不引用真实执行路径。
- API route 契约使用当前用户 id，并返回模拟安全 flags。

已执行：

```bash
PYTHONPATH=backend python -m pytest backend/tests/test_tw_stock_quant_signal_api.py -q
```

结果：

```text
18 passed
```

已执行：

```bash
python -m py_compile backend/app/services/tw_stock_sim_account.py backend/app/routes/tw_stock.py
```

结果：通过。

## 9. 是否建议进入 Phase 3

建议进入 Phase 3。

Phase 3 应实现前端“台股模拟账户”页面，但仍保持简单：账户概览、现金/权益、持仓、手动模拟交易表单、草稿确认/取消、成交记录。不要在 Phase 3 做 qlib / Agent 自动联动，也不要展示真实券商入口。
