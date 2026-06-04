# 全场景 E2E 优化 Step 4 执行文档：watchlist 草稿回填复核与修正

## 1. 本步目标

复核并修正 `/tw-stock-monitor` 中 qlib TopN 研究排序的观察草稿链路：

```text
qlib Top30/Top50 行
-> 加入观察
-> 研究观察草稿
-> 填入监控配置
-> monitor config symbols textarea/input 包含目标股票
```

本步目标是确认该交互真实可用，并把测试选择器稳定化。

## 2. 背景问题

此前本地 smoke 脚本出现失败：

```text
draft symbols were not filled into monitor config form
```

可能原因有两类：

1. UI 真实缺陷：点击“填入监控配置”后，监控配置表单没有正确包含草稿股票。
2. 测试缺陷：页面现在有多个 textarea，旧测试读到了 Agent 输入框或其他 textarea，导致误判。

本步必须明确判断属于哪一种，并给出修复。

## 3. 强制边界

本步不得引入：

- 自动保存 monitor config。
- 自动触发 monitor scan。
- 自动触发 alerts 写操作。
- 下单、broker、quick-trade。
- qlib publish / refresh provider。
- Step 5 的 full scenario E2E 纳入项目。

观察草稿回填只能是“把候选股票填入配置表单”，不能自动执行扫描或交易。

## 4. 涉及文件建议

预计可能修改：

```text
frontend/src/views/tw-stock-monitor/index.vue
frontend/tests/unit/tw-stock-monitor-local-smoke.mjs
frontend/tests/unit/tw-stock-monitor-static-check.mjs
```

如新增专项测试：

```text
frontend/tests/unit/tw-stock-watchlist-draft-check.mjs
```

完成后必须新增报告：

```text
docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP4_REPORT_CN.md
```

## 5. 具体任务

### 任务 1：真实页面复核交互

用真实前后端或 mock Playwright 复现：

1. 打开 `/tw-stock-monitor`。
2. 确认 qlib Top30 表格可见。
3. 点击某行的“加入观察”。
4. 确认“研究观察草稿”出现目标股票。
5. 点击“填入监控配置”。
6. 确认监控配置表单打开。
7. 确认 symbols 输入区域包含目标股票。

必须记录：

- 目标股票代码。
- 点击前草稿状态。
- 点击后配置表单值。
- 是否触发任何写请求。

### 任务 2：判断根因

如果配置表单确实没有目标股票：

- 判定为 UI 缺陷。
- 修复回填逻辑。

如果配置表单已有目标股票，但测试读错输入框：

- 判定为测试缺陷。
- 修复测试选择器。

报告中必须明确写：

```text
判断结论：UI 缺陷 / 测试缺陷 / 两者都有
```

### 任务 3：增加稳定 data-testid

建议增加：

```text
data-testid="qlib-signal-table"
data-testid="qlib-watch-add"
data-testid="qlib-watch-draft"
data-testid="qlib-watch-fill-config"
data-testid="monitor-config-drawer"
data-testid="monitor-config-symbols"
```

要求：

- 测试优先用 `data-testid`。
- 不再依赖“第一个 textarea”这类不稳定选择器。
- 不因语言文案变化导致测试大面积失败。

### 任务 4：修复或更新测试

如果修改现有 smoke：

```text
frontend/tests/unit/tw-stock-monitor-local-smoke.mjs
```

必须保证：

- 回填后读取的是 monitor config symbols 输入框。
- 不读取 Agent textarea。
- 不读取 notes textarea。
- 不触发保存。
- 不触发 scan。

如新增专项静态/轻量测试：

```bash
node tests/unit/tw-stock-watchlist-draft-check.mjs
```

检查内容：

- `data-testid` 存在。
- 回填方法存在。
- 回填方法没有调用 save/scan/publish/order。

## 6. 网络请求审计

Playwright 复核时必须记录危险请求。

禁止出现：

```text
POST /api/tw-stock/monitor/config
POST /api/tw-stock/monitor/scan
POST /api/tw-stock/quant/ops/*
POST /api/quick-trade/*
POST /api/broker/*
POST /api/*order*
```

允许出现：

- 读取 qlib latest。
- 读取 monitor config。
- 读取 trend/alerts/history。
- 读取 Agent context。

## 7. 必跑命令

至少运行：

```bash
cd frontend
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-daily-auto-update-panel-check.mjs
node tests/unit/tw-stock-console-clean-check.mjs
node tests/unit/tw-stock-agent-panel-check.mjs
node tests/unit/tw-stock-cross-analysis-check.mjs
node tests/unit/tw-stock-monitor-qlib-ops-check.mjs
corepack pnpm build
```

如果新增专项测试：

```bash
node tests/unit/tw-stock-watchlist-draft-check.mjs
```

如果更新 local smoke，必须运行：

```bash
TW_STOCK_MONITOR_BASE_URL=<frontend_url> \
TW_STOCK_MONITOR_USERNAME=<username> \
TW_STOCK_MONITOR_PASSWORD=<password> \
node tests/unit/tw-stock-monitor-local-smoke.mjs
```

## 8. 验收标准

Step 4 完成必须满足：

1. qlib TopN 可以加入观察草稿。
2. 点击“填入监控配置”后，monitor config symbols 包含目标股票。
3. 回填动作不保存配置。
4. 回填动作不触发 scan。
5. 回填动作不触发 alerts 写操作。
6. 测试不再依赖不稳定 textarea 顺序。
7. 前端 build 通过。
8. 不改变 qlib accepted latest、daily auto update、Agent、cross-analysis 业务逻辑。

## 9. 报告要求

完成后写：

```text
docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP4_REPORT_CN.md
```

报告必须包含：

- 新增/修改文件列表
- 根因判断：UI 缺陷还是测试缺陷
- 修复说明
- 回填前后截图路径
- 配置表单 symbols 值摘要
- 网络请求审计
- 测试命令和结果
- 是否仍有未解决问题

## 10. 不要提前做的事

本步不要做：

- full scenario E2E 脚本纳入项目，这是 Step 5。
- 新增研究复盘日志、候选池标签等新功能。
- 改造自动更新 API 或面板。
- 改造 qlib 数据链路。

## 11. 下一报告断点

执行者完成后提交：

```text
docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP4_REPORT_CN.md
```

审核通过后再进入 Step 5：全场景只读 Playwright 脚本纳入项目。
