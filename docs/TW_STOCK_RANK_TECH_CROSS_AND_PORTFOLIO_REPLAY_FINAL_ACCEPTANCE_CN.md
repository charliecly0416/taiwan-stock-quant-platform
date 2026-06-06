# 台股排名技术交叉与组合回放最终验收报告

生成时间：2026-06-06

## 1. 总体结论

结论：通过。

本轮 Step1-Step6 功能线可以进入维护态。核心链路已经形成：`qlib 排名 + QuantDinger 趋势 + 技术指标状态 -> 当日交叉分类 -> 只读历史观察回放 -> 内存组合规则历史模拟 -> 前端只读展示`。

从用户第一性原则看，页面已经能优先回答三个问题：

- 今天先看什么：首屏“今日复盘与历史模拟”直接展示优先观察标的。
- 为什么看：同一区块展示 qlib 层级、QuantDinger 趋势、MA/RSI/MACD/Bollinger 技术状态与简短原因。
- 过去表现如何：同一区块展示 qlib-only、qlib + trend、qlib + trend + indicators 三种规则的历史模拟总收益、最大回撤、动作次数和费用税费估算。

安全边界通过：本功能线保持 research-only / simulation-only，不连接券商，不生成真实订单，不写入模拟账户，不触发 monitor 写入，不触发 qlib ops 发布或刷新。

## 2. Step1-Step5 功能链路摘要

Step1：建立 rank-tech cross 后端只读服务，把 qlib TopN 排名、QuantDinger 日线趋势与轻量技术状态合并为用户可读分类。

Step2：补充技术状态服务，支持 MA、RSI、MACD、Bollinger 等策略状态，并把复杂指标压缩成支持、中性、谨慎、数据不足等用户可理解结论。

Step3：实现 point-in-time observation replay，只做历史观察队列回放，不把历史动作解释成今日买卖指令。

Step4：实现 portfolio replay，只在内存中计算组合规则历史模拟，返回 `persist=false`、`writes_business_db=false`、`simulation_only=true` 等只读契约。

Step5：在台股研究页新增“今日复盘与历史模拟”区块，提供 Top30/Top50、近半年/近一年和规则组合切换，并新增只读 E2E 覆盖。

Step6：完成最终验收，修正既有 K 线模拟成交 marker 的自动 `/sim/` 读取，使本功能线 E2E 的 `/sim/` 自动请求计数收口为 0。

## 3. 用户第一性原则验收

通过。

页面表达保持简单、清晰、准确、实用：

- 简单：首屏不要求用户理解 run id、recorder、工程状态字段，先给“今天先看什么”。
- 清晰：每个标的旁边有中文名称、Top 层级、决策标签、技术状态和原因。
- 准确：历史表现明确标注为“只读历史模拟”，并显示数据提示，不承诺未来收益。
- 实用：用户能在同一块里比较 qlib-only、qlib + trend、qlib + trend + indicators，不需要跳到多个页面拼信息。

仍需注意：页面其它历史功能线仍有模拟账户和 K 线 marker 相关入口，但 Step6 已避免它们随本功能线首屏自动加载；这类功能应继续和“研究复盘”保持视觉与语义隔离。

## 4. 后端 API 验收

验收范围：

- `GET /api/tw-stock/rank-tech-cross/latest`
- `GET /api/tw-stock/rank-tech-cross/observation-replay`
- `POST /api/tw-stock/rank-tech-cross/portfolio-replay`

通过点：

- latest 接口只读返回 rank-tech 分类。
- observation replay 只做历史观察回放。
- portfolio replay 虽然使用 POST 提交复杂参数，但服务契约为只读历史模拟。
- portfolio replay 返回并保持 `persist=false`、`writes_business_db=false`、`simulation_only=true`、`orders_enabled=false`、`connects_to_broker=false`。

## 5. 前端展示验收

通过。

前端新增区块位于台股研究页，`data-testid="rank-tech-portfolio-replay-readonly"`。区块包含：

- 控制项：Top30 / Top50、近半年 / 近一年、全部规则 / 单规则。
- 安全提示：`只读历史模拟，不是投资建议，不连接券商，不生成订单。`
- 今日优先复盘：展示用户应该先看的标的和原因。
- 为什么：展示 qlib、QuantDinger、技术指标摘要。
- 过去表现：展示三类规则组合的历史模拟指标。

Step6 还把 K 线图的模拟成交 marker 改为显式按钮“加载模拟成交标记”，不再随 `refreshAll()` 自动读取 `/api/tw-stock/sim/**`。

## 6. 只读安全边界审查

审查结论：通过。

Findings：

- Critical：无。
- High：无。
- Medium：无。
- Low：无阻断项。

Network Audit：

- `forbidden_request_count=0`
- `sim_write_request_count=0`
- `quick_trade_request_count=0`
- `broker_request_count=0`
- `real_order_request_count=0`
- `monitor_config_write_count=0`
- `monitor_scan_post_count=0`
- `monitor_alerts_write_count=0`
- `qlib_ops_post_count=0`
- `accepted_latest_switch_count=0`
- `provider_publish_refresh_count=0`
- `target_position_request_count=0`
- `target_weight_request_count=0`

Text / Agent Semantics：

- 新区块没有出现立即买入、立即卖出、自动买入、自动卖出、下单、提交订单、目标仓位、目标权重、上涨概率、收益承诺等危险语义。
- “历史模拟”“回测”“过去表现”均作为只读历史分析呈现，不作为未来收益或买卖承诺。

Verdict：满足 `tw-stock-safety-boundary-review` 的通过条件。

## 7. `/sim/` 计数收口说明

Step5 E2E 曾出现 `sim_request_count=1`，来源是既有 K 线图模拟成交 marker 的只读 GET，不是 rank-tech 新区块。

Step6 已做最小修正：

- 从 `refreshAll()` 自动加载流程移除 `loadSimTradeMarkers()`。
- 在 K 线脚注增加显式按钮“加载模拟成交标记”。
- 保留 marker 功能，但只有用户主动点击时才读取模拟成交数据。

Step6 E2E 最新结果：

- `sim_request_count=0`
- `sim_write_request_count=0`

因此本功能线 readonly E2E 的 `/sim/` 计数已完全收口。

## 8. 测试命令与结果

后端语法检查：通过。

```bash
python -m py_compile backend/app/services/tw_stock_rank_tech_cross.py backend/app/services/tw_stock_technical_status.py backend/app/services/tw_stock_observation_replay.py backend/app/services/tw_stock_portfolio_replay.py backend/app/routes/tw_stock.py
```

后端单元与 API 测试：通过，`27 passed in 2.58s`。

```bash
python -m pytest backend/tests/test_tw_stock_rank_tech_cross.py backend/tests/test_tw_stock_rank_tech_cross_api.py backend/tests/test_tw_stock_technical_status.py backend/tests/test_tw_stock_observation_replay.py backend/tests/test_tw_stock_observation_replay_api.py backend/tests/test_tw_stock_portfolio_replay.py backend/tests/test_tw_stock_portfolio_replay_api.py -q
```

研究栈安全验证：通过，脚本输出 `ok:true`，内部 pytest `86 passed in 1.88s`。

```bash
python backend/scripts/verify_tw_stock_research_stack.py
```

前端静态检查：全部通过。

```bash
node frontend/tests/unit/tw-stock-rank-tech-portfolio-replay-check.mjs
node frontend/tests/unit/tw-stock-monitor-static-check.mjs
node frontend/tests/unit/tw-stock-cross-analysis-check.mjs
```

前端 Playwright 只读 E2E：通过。

```bash
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8010 node frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs
```

E2E 关键统计：

```json
{
  "latest_request_count": 3,
  "observation_replay_request_count": 0,
  "portfolio_replay_request_count": 5,
  "portfolio_persist_false_count": 5,
  "sim_request_count": 0,
  "sim_write_request_count": 0,
  "quick_trade_request_count": 0,
  "broker_request_count": 0,
  "real_order_request_count": 0,
  "monitor_config_write_count": 0,
  "monitor_scan_post_count": 0,
  "monitor_alerts_write_count": 0,
  "qlib_ops_post_count": 0,
  "accepted_latest_switch_count": 0,
  "provider_publish_refresh_count": 0,
  "target_position_request_count": 0,
  "target_weight_request_count": 0,
  "forbidden_request_count": 0,
  "page_error_count": 0
}
```

前端生产构建：通过。注意该命令需要在 `frontend/` 目录执行；如果在仓库根目录执行，pnpm 会误处理 `/home/chuliyang/node_modules` 并可能因权限问题失败。

```bash
cd frontend
corepack pnpm build
```

说明：本次 E2E 使用临时 Vite 服务 `http://127.0.0.1:8010/` 跑当前源码；验收后该临时服务已关闭。现有 `8000` 和 `5000` 服务未被修改。

## 9. 未解决风险

- 历史模拟依赖 qlib、Yahoo/FinMind、QuantDinger 日线数据质量。前端已展示数据提示，但用户仍可能把历史模拟误读为预测，需要后续继续保持免责声明和命名克制。
- observation replay 已有 API，但当前首屏主要展示 portfolio replay 指标；如果未来展开逐日观察明细，应继续默认折叠，避免页面变复杂。
- 其它产品线仍存在模拟账户、K 线 marker、只读回测等功能，后续维护时要避免把它们和“今日复盘”混在一起，保持信息层级清楚。

## 10. 是否建议进入维护态

建议进入维护态。

进入维护态后的优先级建议：

- 只做数据质量、文案清晰度和性能的小步优化。
- 不急于增加更多策略组合，避免页面再次复杂化。
- 若继续扩展，应优先补“为什么这个历史模拟可靠或不可靠”的解释，而不是增加更多按钮。
