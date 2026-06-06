# 台股产品适配 Phase 2 执行文档：模拟账户后端核心 MVP

日期：2026-06-05

## 1. 本步目标

实现台股模拟账户后端 MVP，让用户可以创建一个模拟账户、手动模拟买入/卖出、查看现金和持仓。

这是“模拟验证工具”，不是证券账户，不连接 broker，不调用 quick-trade，不生成真实订单。

Phase 1 已将台股主入口收敛为“台股研究”，并把运维信息折叠到高级区域。Phase 2 必须延续这个口径：模拟账户只用于研究信号验证，不得把页面或 API 重新带回真实交易、自动下单、策略运行语境。

## 2. MVP 范围

第一版只支持：

- 默认或单个模拟账户。
- 初始资金 TWD。
- 手动买入 / 手动卖出。
- 不允许卖空。
- 不允许现金为负。
- 默认 1000 股整张交易。
- 使用最新可用 K 线收盘价作为 MVP 成交参考价。
- 手续费与交易税使用后端默认配置。
- 返回账户现金、持仓、市值、基础收益。

暂不做：

- 多账户复杂权限。
- 自动交易。
- 真实 next open 强制成交。
- 除权息现金流模拟。
- 复杂绩效归因。
- Top30 / Agent / cross-analysis 到模拟草稿的联动。该联动放到 Phase 4。
- 前端模拟账户页面。前端放到 Phase 3。

## 3. 建议后端文件

```text
backend/app/services/tw_stock_sim_account.py
backend/tests/test_tw_stock_sim_account.py
```

路由可先放入现有：

```text
backend/app/routes/tw_stock.py
```

如路由过长，可拆：

```text
backend/app/routes/tw_stock_sim.py
```

## 4. 数据模型

MVP 建议保留 4 类数据：

```text
qd_tw_sim_accounts
qd_tw_sim_orders
qd_tw_sim_trades
qd_tw_sim_positions
```

`qd_tw_sim_nav_snapshots` 可在 Phase 5 再实现。

所有记录必须带：

- `simulation_only=true` 语义。
- `created_at / updated_at`。
- `source_type`：manual / qlib_rank / agent / backtest。

Phase 2 只允许实际使用 `source_type=manual`。其他来源字段可以作为枚举预留，但不得在本步自动生成 qlib_rank / agent 草稿。

命名注意：

- 后端服务、字段和测试应使用 `sim` / `simulation`。
- 不要复用 `quick_trade`、`paper_order`、`broker_order`、`target_position` 等容易混淆的语义。
- 如果已有历史 paper trading 代码，不要直接复用其交易执行路径。

## 5. API 范围

只读：

```text
GET /api/tw-stock/sim/accounts
GET /api/tw-stock/sim/accounts/:id
GET /api/tw-stock/sim/accounts/:id/positions
GET /api/tw-stock/sim/accounts/:id/trades
```

模拟写入：

```text
POST /api/tw-stock/sim/accounts
POST /api/tw-stock/sim/orders/draft
POST /api/tw-stock/sim/orders/:id/confirm
POST /api/tw-stock/sim/orders/:id/cancel
```

所有响应必须包含：

```json
{
  "trading": {
    "real_orders_enabled": false,
    "connects_to_broker": false,
    "simulation_only": true
  }
}
```

响应还必须包含清晰的状态字段：

```json
{
  "status": "draft | filled | cancelled | rejected",
  "simulation_only": true
}
```

禁止返回或使用：

```text
order_id from broker
exchange_order_id
broker_account
target_position
target_weight
live / paper trading mode
```

## 6. 业务规则

买入：

- 校验 symbol。
- 校验 quantity > 0。
- 默认必须为 1000 股倍数，除非明确启用零股模式。
- 现金不足则 rejected。
- 确认后扣现金，增加持仓。

卖出：

- 不允许卖空。
- 数量不能超过当前持仓。
- 确认后增加现金，减少持仓。

价格：

- MVP 使用最新可用收盘价。
- 如果无价格，草稿 rejected 或 pending，不能伪造成交。
- 价格来源必须写入响应，例如 `price_source=latest_close`。
- 如果日线数据日期落后，需要在响应 warnings 中说明，不要假装是实时价。

费用：

- 手续费、交易税可先用常量配置。
- 报告中必须说明公式。

账户：

- 若用户尚未创建账户，可由后端提供一个默认模拟账户创建流程。
- 初始资金默认值可用 1,000,000 TWD，但必须允许请求中传入。
- cash、market_value、total_equity 均使用 TWD。

## 7. 安全边界

服务代码不得导入或调用：

```text
quick_trade
broker
order
target_position
tw_stock_qlib_option_c_ops
publish
refresh provider
```

也不得调用或间接触发：

```text
monitor scan
alerts write
qlib ops dry-run
accepted latest switch
OpenAI / Agent chat
```

Phase 2 后端可以读取台股日线价格，但不得触发新的数据拉取或 daily auto update。

## 8. 必跑测试

```bash
PYTHONPATH=backend python -m pytest backend/tests/test_tw_stock_sim_account.py -q
PYTHONPATH=backend python -m pytest backend/tests/test_tw_stock_quant_signal_api.py -q
```

测试至少覆盖：

- 创建账户。
- 买入成功。
- 现金不足买入被拒。
- 卖出成功。
- 卖空被拒。
- 所有响应包含 `simulation_only=true`。
- 服务代码不引用 broker/quick-trade/order。
- 默认只支持 `source_type=manual`。
- 响应包含 `real_orders_enabled=false` 和 `connects_to_broker=false`。
- 缺少价格时不会成交。
- 日期滞后时返回 warning。

建议增加静态边界测试：

```text
backend/tests/test_tw_stock_sim_account_safety.py
```

检查服务源码中不包含：

```text
quick_trade
broker
place_order
target_position
target_weight
provider refresh
publish
accepted latest
```

## 9. 报告断点

完成后提交：

```text
docs/TW_STOCK_PRODUCT_ADAPTATION_PHASE2_REPORT_CN.md
```

报告必须包含：

- 新增/修改文件清单。
- API 契约。
- 成交价格和费用规则。
- 测试结果。
- 安全边界证明。
- 是否只使用 manual source。
- 是否没有触发数据拉取或 qlib ops。
- 是否建议进入 Phase 3。

