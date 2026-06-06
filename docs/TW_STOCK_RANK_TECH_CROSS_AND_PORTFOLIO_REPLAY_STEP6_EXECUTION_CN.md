# 台股排名技术交叉与组合回放 Step 6 执行文档：最终验收与收口

生成时间：2026-06-06

前置报告：`docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_STEP5_REPORT_CN.md`

## 1. Step 5 审查结论

Step 5 主线基本正确：

- 已在现有台股研究页新增“今日复盘与历史模拟”只读区块。
- 已新增 `rank-tech-cross/latest`、`observation-replay`、`portfolio-replay` 的前端 API 封装。
- `runTwStockPortfolioReplay` 强制 `persist:false`。
- 新区块展示今日优先复盘、原因和三种规则的历史模拟指标。
- 新区块没有接入模拟账户写单、broker、quick-trade、monitor 写入或 qlib ops。
- 新增状态已放入 Vue 2 `data()`，避免响应式不刷新。

需要收口的点：

- Step 5 执行文档要求本步场景 `sim_request_count=0`，但 Step 5 报告中的全页 E2E 统计出现 `sim_request_count=1`。报告说明该请求来自既有 K 线图“模拟成交 marker”的只读 GET，不是 Step 5 新区块。
- 最终验收必须把这个口径说清楚，并优先将本功能线 E2E 的 `/api/tw-stock/sim/**` 计数降为 0；如果暂时不能降为 0，必须拆分统计为 `rank_tech_section_sim_request_count=0` 与 `page_existing_sim_read_request_count=1`，并确认没有 sim 写入。
- 页面仍存在其它历史功能线文案如“生成模拟草稿”“模拟买入/卖出 marker”。最终验收必须证明这些不在 Step 5 新区块中，不是本功能线新增交易建议。

## 2. 本步目标

完成最终验收与文档收口，判断这条功能线是否可以接受。

本步不新增功能，除非为了修复验收口径或安全边界问题做最小改动。

最终回答三个问题：

1. 用户第一屏是否能清楚回答“今天先看什么、为什么、过去模拟表现如何”。
2. 从 Step 1 到 Step 5 是否仍保持 research-only / simulation-only 边界。
3. 是否存在必须阻断上线或继续开发的偏离。

## 3. 明确禁止

本步不得执行：

- 不新增交易功能。
- 不新增模拟账户写入功能。
- 不新增 broker / quick-trade 入口。
- 不新增 monitor config save、monitor scan、alerts write。
- 不新增 qlib refresh、publish、provider mutation、accepted latest switching。
- 不新增 target position / target weight。
- 不把历史模拟指标写成未来收益、胜率、上涨概率或推荐承诺。
- 不把 `historical_add` / `historical_risk_reduce` 映射成真实买入/卖出/下单。

允许：

- 修正测试统计口径。
- 把 Step 5 场景中无关的既有 `/sim/` 只读 GET 延迟到用户显式打开图表或模拟标记时再加载。
- 增加只读安全静态测试和 E2E 断言。
- 更新最终验收报告。

## 4. 验收范围

必须覆盖以下文件和接口：

```text
backend/app/services/tw_stock_rank_tech_cross.py
backend/app/services/tw_stock_technical_status.py
backend/app/services/tw_stock_observation_replay.py
backend/app/services/tw_stock_portfolio_replay.py
backend/app/routes/tw_stock.py
frontend/src/api/tw-stock.js
frontend/src/views/tw-stock-monitor/index.vue
frontend/tests/unit/tw-stock-rank-tech-portfolio-replay-check.mjs
frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs
```

文档范围：

```text
docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_PLAN_CN.md
docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_STEP1_REPORT_CN.md
docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_STEP2_REPORT_CN.md
docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_STEP3_REPORT_CN.md
docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_STEP4_REPORT_CN.md
docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_STEP5_REPORT_CN.md
```

## 5. 必查项目

### 5.1 主线完整性

确认功能链路完整：

```text
latest ranking + trend + indicators
-> point-in-time observation replay
-> in-memory portfolio rule replay
-> readonly frontend display
```

确认用户第一屏包含：

- 今日优先复盘。
- 为什么进入该分类。
- 过去历史模拟表现。
- 只读 / 非投资建议 / 不连接券商 / 不生成订单说明。

### 5.2 安全边界

全链路检查不得出现：

```text
POST /api/tw-stock/monitor/config
POST /api/tw-stock/monitor/scan
POST /api/tw-stock/monitor/scan-all
POST /api/tw-stock/monitor/alerts
PUT/PATCH/DELETE /api/tw-stock/monitor/alerts/*
POST /api/tw-stock/quant/ops/**
POST /api/quick-trade/**
/api/broker/**
真实 order
target_position
target_weight
```

`portfolio-replay` 允许使用 POST，但必须满足：

```text
persist=false
writes_business_db=false
simulation_only=true
orders_enabled=false
connects_to_broker=false
writes_orders=false
writes_positions=false
```

### 5.3 `/sim/` 计数收口

推荐修正方向：

1. 优先改 E2E 场景或页面加载时机，让 Step 6 rank-tech readonly E2E 达到：

```text
sim_request_count=0
sim_write_request_count=0
```

2. 如果既有全页功能必须保留自动读取模拟成交 marker，则最终报告必须拆分：

```text
rank_tech_section_sim_request_count=0
page_existing_sim_read_request_count=1
sim_write_request_count=0
```

并提供证据：

- Step 5 新区块 DOM 子树不包含模拟账户按钮。
- Step 5 新区块方法不调用 `getTwStockSimAccounts` / `getTwStockSimTrades`。
- `/api/tw-stock/sim/**` 请求不是由 `rank-tech-replay-card` 控件触发。

若无法证明以上三点，最终验收不得通过。

### 5.4 文案安全

Step 5 新区块不得包含：

```text
立即买入
立即卖出
自动买入
自动卖出
下单
提交订单
目标仓位
目标权重
上涨概率
收益承诺
连接券商
```

允许：

```text
只读历史模拟
不是投资建议
不连接券商
不生成订单
新增观察
继续观察
风险复盘
人工复核
仅观察
数据不足
```

全页若存在其它功能线的“模拟买入/卖出”文案，最终报告必须标明其来源和所在模块，并确认不属于本功能线新增区块。

## 6. 测试要求

### 6.1 后端

```text
python -m py_compile backend/app/services/tw_stock_rank_tech_cross.py backend/app/services/tw_stock_technical_status.py backend/app/services/tw_stock_observation_replay.py backend/app/services/tw_stock_portfolio_replay.py backend/app/routes/tw_stock.py
python -m pytest backend/tests/test_tw_stock_rank_tech_cross.py backend/tests/test_tw_stock_rank_tech_cross_api.py backend/tests/test_tw_stock_technical_status.py backend/tests/test_tw_stock_observation_replay.py backend/tests/test_tw_stock_observation_replay_api.py backend/tests/test_tw_stock_portfolio_replay.py backend/tests/test_tw_stock_portfolio_replay_api.py -q
python backend/scripts/verify_tw_stock_research_stack.py
```

### 6.2 前端静态

```text
node frontend/tests/unit/tw-stock-rank-tech-portfolio-replay-check.mjs
node frontend/tests/unit/tw-stock-monitor-static-check.mjs
node frontend/tests/unit/tw-stock-cross-analysis-check.mjs
```

### 6.3 前端 E2E

```text
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:<port> node frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs
```

E2E 必须输出并归档以下统计：

```text
latest_request_count
observation_replay_request_count
portfolio_replay_request_count
portfolio_persist_false_count
sim_request_count
sim_write_request_count
quick_trade_request_count
broker_request_count
real_order_request_count
monitor_config_write_count
monitor_scan_post_count
monitor_alerts_write_count
qlib_ops_post_count
accepted_latest_switch_count
provider_publish_refresh_count
target_position_request_count
target_weight_request_count
forbidden_request_count
page_error_count
```

验收目标：

```text
forbidden_request_count=0
sim_write_request_count=0
quick_trade_request_count=0
broker_request_count=0
real_order_request_count=0
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
qlib_ops_post_count=0
accepted_latest_switch_count=0
provider_publish_refresh_count=0
target_position_request_count=0
target_weight_request_count=0
page_error_count=0
```

`sim_request_count` 推荐为 0；如不是 0，必须按 5.3 拆分说明。

### 6.4 Build

```text
corepack pnpm build
```

## 7. 最终报告要求

执行完成后新增：

```text
docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_FINAL_ACCEPTANCE_CN.md
```

报告必须包含：

1. 总体结论：通过 / 条件通过 / 不通过。
2. Step 1-5 功能链路摘要。
3. 用户第一性原则验收：今天看什么、为什么、过去表现。
4. 后端 API 验收。
5. 前端展示验收。
6. 只读安全边界审查。
7. `/sim/` 计数收口说明。
8. 测试命令与结果。
9. 未解决风险。
10. 是否建议进入维护态。

## 8. 通过标准

最终通过必须满足：

- 功能主线完整。
- Step 5 新区块只读且可用。
- 后端不落库组合回放契约成立。
- portfolio replay POST 全部 `persist=false`。
- 无 broker、quick-trade、真实 order、target position/weight。
- 无 monitor 写入、scan、alerts 写入。
- 无 qlib ops POST、accepted latest switching、provider publish/refresh。
- 无未来收益、胜率、上涨概率或收益承诺。
- 测试和 build 通过。
- `/sim/` 只读 GET 口径已收口，且不影响本功能线验收。

## 9. 审核断点

本步完成后停止，等待审查：

```text
docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_FINAL_ACCEPTANCE_CN.md
```

审查通过后，本功能线进入维护态，不再继续新增功能。
