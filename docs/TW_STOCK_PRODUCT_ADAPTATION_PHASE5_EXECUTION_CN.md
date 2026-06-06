# 台股产品适配 Phase 5 执行文档：绩效复盘与全链路最终验收

日期：2026-06-05

## 1. Phase 4 审查结论

Phase 4 没有偏离主线，可以进入 Phase 5。

Phase 4 已按顺序完成：先补 `/tw-stock-sim-account` Playwright smoke/network audit，再受控扩展 `source_type/source_context`，最后实现研究页到模拟账户页的最小预填联动。审查确认：研究页按钮只写入 `tw-stock-sim-draft-context` 并跳转，不直接调用 `draftTwStockSimOrder` 或 `confirmTwStockSimOrder`；后端仍只写模拟订单和模拟成交，不接 broker、quick-trade、真实订单、monitor scan、alerts write、qlib ops、provider refresh/publish、accepted latest switch 或 Agent chat。

Phase 4 的主要补强点：已完成模拟账户页自身 smoke，但还缺一个从 `/tw-stock-monitor` 研究页入口开始的浏览器全链路测试。Phase 5 必须补齐这个验收，再判断是否可以收尾。

## 2. 本步目标

完成产品适配闭环的最后一层：

```text
研究信号 -> 模拟草稿预填 -> 用户生成模拟草稿 -> 用户确认模拟成交 -> 持仓计价 -> 绩效复盘 -> 全链路安全验收
```

Phase 5 的目标不是继续扩大功能，而是把已有功能做成可解释、可复盘、可验收的闭环。

## 3. 子任务 A：模拟账户绩效复盘 MVP

优先在已有模拟账户页完善绩效展示。可以通过新增后端 summary API，也可以前端基于现有 account/positions/trades 计算；选择改动最小、测试最清楚的方式。

必须展示：

- 初始资金。
- 现金。
- 持仓市值。
- 总权益。
- 累计收益金额。
- 累计收益率。
- 持仓浮动盈亏。
- 单笔成交现金影响、费用、交易税。
- 按来源统计的成交数量：`manual / qlib_rank / cross_analysis / agent_research`。

建议展示：

- 已实现盈亏 MVP：只需在卖出成交时基于持仓平均成本估算，不要求复杂 tax lot。
- 胜负笔数 MVP：基于已实现盈亏的正负统计。
- 净值点 MVP：可以先用当前总权益和成交后账户状态展示简化曲线，不强求历史每日 NAV。

可推迟：

- 最大回撤。
- 平均持有天数。
- 与加权指数或 0050 对比。
- 除权息现金流。
- 复杂归因。

## 4. 子任务 B：K 线模拟成交标记 MVP

在台股研究页或模拟账户页的现有 K 线图中，增加模拟成交标记。如果实现成本过高，可以放在模拟账户页用简化列表替代，但必须清楚说明。

建议规则：

- 读取当前账户成交记录。
- 对当前 symbol 的成交显示 marker。
- 买入 marker 文案：`模拟买入`。
- 卖出 marker 文案：`模拟卖出`。
- hover/详情展示：成交日期、模拟价格、数量、source_type。

禁止：

- 不显示真实订单 ID。
- 不显示券商账号。
- 不显示目标仓位/目标权重。
- 不把 qlib_score 解释成收益率、胜率、上涨概率或买入概率。

## 5. 子任务 C：研究页到模拟账户全链路 Playwright

新增或完善：

```text
frontend/tests/e2e/tw-stock-sim-account-full-flow.mjs
```

必须覆盖 Top30/Top50 链路：

1. 打开 `/#/tw-stock-monitor`。
2. mock latest qlib signals，确保至少一条 Top30 数据可见。
3. 点击 Top30 行的 `生成模拟草稿`。
4. 验证跳转到 `/#/tw-stock-sim-account`。
5. 验证 symbol、side、quantity、source_type=qlib_rank 已预填。
6. 验证此时还没有调用 `/sim/orders/draft`。
7. 用户点击 `生成模拟买入草稿` 后才调用 `/sim/orders/draft`。
8. 用户看到草稿详情后，点击 `确认模拟成交` 才调用 confirm。
9. 验证持仓、成交记录、绩效展示刷新。

必须覆盖 cross-analysis 链路：

1. mock `focus_watch` 或 `aligned` 项。
2. 点击 `生成模拟草稿`。
3. 验证 source_type= `cross_analysis`。
4. 验证 `model_trend_divergence` / `data_review_required` 不默认生成模拟买入草稿，按钮禁用或提示人工复核。

Network audit 必须统计：

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
accepted_latest_switch_count
provider_publish_refresh_count
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
accepted_latest_switch_count=0
provider_publish_refresh_count=0
sim_request_count>0
```

## 6. 子任务 D：最终验收文档

完成后新增最终验收：

```text
docs/TW_STOCK_PRODUCT_ADAPTATION_FINAL_ACCEPTANCE_CN.md
```

最终验收必须回答：

- Phase 1-5 是否全部完成。
- 当前台股产品主线是否清楚：研究、模拟、复盘，而不是实盘交易。
- 页面清单：台股研究、台股模拟账户、相关 Agent/交叉分析展示。
- API 清单：只读研究 API、模拟账户 API、禁止触发的 API。
- 模拟账户闭环是否成立。
- 全链路 Playwright/network audit 是否通过。
- 是否有真实交易能力泄漏。
- 是否可以收尾。

## 7. 数据准确性与文案要求

所有收益统计必须标注：

```text
历史/模拟结果，不代表未来收益。
```

所有价格字段必须注明来源：

```text
最新可用收盘价
```

如果价格缺失或日期滞后：

- 显示缺失/滞后 warning。
- 不伪造价格。
- 不显示为实时价。

禁止文案：

```text
建议买入
建议卖出
目标仓位
目标权重
上涨概率
胜率保证
收益承诺
自动下单
一键买入
真实交易
连接券商
```

允许文案：

```text
生成模拟草稿
确认模拟成交
历史/模拟验证
人工复盘
研究信号，不是交易指令
```

## 8. 必跑测试

后端：

```bash
PYTHONPATH=backend python -m pytest backend/tests/test_tw_stock_sim_account.py -q
PYTHONPATH=backend python -m pytest backend/tests/test_tw_stock_quant_signal_api.py -q
python -m py_compile backend/app/services/tw_stock_sim_account.py backend/app/routes/tw_stock.py
```

前端静态：

```bash
cd frontend
node tests/unit/tw-stock-sim-account-check.mjs
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-cross-analysis-check.mjs
node tests/unit/tw-stock-agent-panel-check.mjs
corepack pnpm build
```

浏览器：

```bash
cd frontend
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8000 node tests/e2e/tw-stock-sim-account-smoke.mjs
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8000 node tests/e2e/tw-stock-sim-account-full-flow.mjs
```

如果本地服务不可用，不能直接收尾。报告需要说明服务不可用原因，并至少给出静态测试与后端测试结果；全链路最终验收应等待浏览器测试补齐。

## 9. 明确不做

Phase 5 不做：

- Agent 回答到模拟草稿联动。
- 自动交易。
- 真实券商连接。
- 目标仓位/目标权重。
- 根据 qlib_score 自动决定数量或仓位。
- provider refresh/publish、accepted latest switch。
- daily auto update 或数据拉取改动。

Agent 联动如果之后要做，必须单独开 Phase 6，并重新审查语义边界。

## 10. 报告断点

完成后提交：

```text
docs/TW_STOCK_PRODUCT_ADAPTATION_PHASE5_REPORT_CN.md
docs/TW_STOCK_PRODUCT_ADAPTATION_FINAL_ACCEPTANCE_CN.md
```

Phase 5 report 必须包含：

- 新增/修改文件清单。
- 绩效复盘指标说明。
- K 线标记或替代方案说明。
- Top30/cross-analysis 全链路流程说明。
- Playwright/network audit 计数。
- 所有测试命令和结果。
- 是否出现真实交易文案或危险 API。
- 是否建议最终收尾。
