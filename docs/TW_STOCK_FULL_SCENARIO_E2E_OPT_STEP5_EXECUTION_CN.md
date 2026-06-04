# 台股全场景 E2E 优化 Step 5 执行文档：全场景只读 Playwright 仿真测试入库

生成时间：2026-06-04

## 1. 本步目标

将此前临时执行的全场景浏览器仿真测试整理为项目内可重复运行的只读 Playwright 脚本，验证独立项目已经保留并串联以下闭环能力：

- Scrapling/Yahoo qlib accepted latest 展示。
- FinMind raw 与每日自动更新状态展示。
- qlib TopN 研究信号、趋势图、历史 accepted run、只读回测入口。
- QuantDinger 数据分析与 cross-analysis 展示。
- Agent 上下文与常见问题只读查询入口。
- watchlist 草稿回填到监控配置表单，但不保存、不扫描、不下单。
- 前端关键画布、表格、面板在真实浏览器中可见且非空。

本步仍然是只读验证，不允许触发数据拉取、provider publish、accepted latest 切换、broker/order/quick-trade 写操作。

## 2. 前置修正要求

Step 4 的 watchlist 修复方向正确，但 `frontend/tests/unit/tw-stock-monitor-local-smoke.mjs` 中有两处覆盖被放宽，执行 Step 5 前必须修正：

1. 恢复中文危险交易文案检查，至少包含：
   - `下單`
   - `买入`
   - `買入`
   - `卖出`
   - `賣出`
   - `提交订单`
   - `提交訂單`

2. 不要用固定 `waitForTimeout(500)` 替代关键 UI 断言。若 `30/120 bars` 文案已因产品调整不稳定，应改成更稳定的真实断言，例如：
   - 选择 `30D` 后 active range button 为 `30D`。
   - 图表 canvas 仍非空。
   - bars/data status 仍可见。
   - range/window 状态能证明 30D 切换生效。

修正后保留 Step 4 的稳定 `data-testid` 方案。

## 3. 建议新增文件

建议新增：

```text
frontend/tests/e2e/tw-stock-full-scenario-readonly.mjs
```

如项目当前没有 `frontend/tests/e2e/` 目录，可以新建。脚本应支持以下环境变量：

```text
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8000
TW_STOCK_MONITOR_USERNAME=quantdinger
TW_STOCK_MONITOR_PASSWORD=123456
TW_STOCK_FULL_E2E_ARTIFACT_DIR=data_tw/ops/e2e_full_scenario/<timestamp>
```

产物目录应写入 `.gitignore` 覆盖范围，不提交截图、trace、临时 JSON。

## 4. 必测场景

### 4.1 登录与首页路由

- 使用 Playwright 登录前端。
- 进入 `/tw-stock-monitor`。
- 验证页面无致命 console error。
- 允许已知 Ant Design lazy-load notice，但其他 warning/error 要记录。

### 4.2 qlib accepted latest 与 TopN

- 验证 latest accepted 区块可见。
- 验证 accepted asof、run_id、status 可见。
- 验证 TopN 表格可见，至少存在一行股票。
- 点击 TopN 第一行，确认趋势图选中 symbol 发生变化。
- 验证价格 canvas 和至少一个量化图表 canvas 有尺寸且非空。

### 4.3 历史 accepted run 与只读回测

- 打开历史 accepted run 区块。
- 验证历史列表或空状态可解释。
- 点击某个 qlib row 的只读回测入口。
- 验证只读回测面板可见。
- 禁止触发任何交易、下单、broker、target position、quick-trade 写请求。

### 4.4 每日自动更新状态

- 验证每日自动更新状态面板可见。
- 验证 FinMind raw、Yahoo/Scrapling qlib、pending asof、latest accepted asof 等字段可见。
- 验证面板只读取状态 API，不触发 daily auto update runner、refresh provider、publish、accepted latest 切换。

### 4.5 cross-analysis

- 验证 cross-analysis 摘要区块可见。
- 验证至少能看到 bucket/top30/overlap/consensus 等交叉分析字段之一。
- 若点击 symbol detail，只允许 GET/只读请求。

### 4.6 Agent 上下文

- 验证 Agent 面板或 Agent 上下文入口可见。
- 验证常见问题所需上下文字段存在，例如 Top30、买入/卖出建议、指标值、accepted latest。
- 本步不要求真实调用 OpenAI API，除非已有 mock 或本地测试 key；默认只验证前端上下文和只读接口。

### 4.7 watchlist 草稿回填

- 点击 qlib TopN 行的 `加入观察`。
- 验证研究观察草稿出现目标 symbol。
- 点击 `填入監控配置`。
- 验证监控配置 drawer 打开，symbols textarea 包含目标 symbol。
- 验证没有保存 monitor config，没有触发 monitor scan，没有新增 alerts 写操作。

## 5. 网络请求审计边界

脚本必须记录所有请求，并在结束时输出审计 JSON。

允许：

- `GET /api/tw-stock/**`
- `GET /api/quick-trade/**` 的历史或只读查询，如果页面天然会加载。
- 静态资源请求。

禁止：

- `POST /api/tw-stock/monitor/config`
- `POST /api/tw-stock/monitor/scan`
- `POST /api/tw-stock/quant/ops/**` 中的 refresh、publish、accepted latest 切换、非 dry-run 操作。
- `POST /api/quick-trade/**`
- `/api/broker/**`
- URL 或 body 含 `order`、`target-position`、`target_weight` 的写请求。
- 任何真实下单、真实券商连接、真实持仓调整。

如果出现禁止请求，测试必须失败。

## 6. 输出产物

每次运行至少输出：

```text
data_tw/ops/e2e_full_scenario/<timestamp>/summary.json
data_tw/ops/e2e_full_scenario/<timestamp>/network_audit.json
data_tw/ops/e2e_full_scenario/<timestamp>/console_audit.json
data_tw/ops/e2e_full_scenario/<timestamp>/*.png
```

`summary.json` 至少包含：

- base_url
- latest_asof
- selected_symbol
- topn_visible
- daily_auto_update_visible
- cross_analysis_visible
- agent_context_visible
- watchlist_refill_ok
- chart_nonblank_ok
- forbidden_request_count
- console_error_count
- overall_passed

## 7. 必跑命令

在执行者环境中完成以下验证：

```bash
cd frontend
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-daily-auto-update-panel-check.mjs
node tests/unit/tw-stock-console-clean-check.mjs
node tests/unit/tw-stock-watchlist-draft-check.mjs
node tests/e2e/tw-stock-full-scenario-readonly.mjs
corepack pnpm build
```

如 E2E 需要前后端服务，执行者应在报告中写明启动命令、端口、配置文件、测试账号、是否使用 mock。

## 8. 验收标准

- 全场景 Playwright 脚本已入库，可重复运行。
- Step 4 被放宽的安全文案检查和 range/window 断言已恢复或替换为等价稳定断言。
- E2E 覆盖 qlib、QuantDinger 分析、cross-analysis、daily auto update、Agent 上下文、watchlist 回填。
- E2E 全程只读，没有触发保存、扫描、发布、刷新 provider、切换 accepted latest、下单或券商写操作。
- 失败时能从 summary/network/console/screenshot 快速定位原因。
- 前端构建通过。

## 9. 报告要求

执行完成后提交：

```text
docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP5_REPORT_CN.md
```

报告必须包含：

- 修改文件清单。
- Step 4 两处测试弱化点的修正说明。
- E2E 覆盖场景清单。
- 网络请求审计结果。
- console 审计结果。
- 截图和 JSON 产物路径。
- 所有测试命令与结果。
- 是否仍有未覆盖或需要人工确认的场景。
