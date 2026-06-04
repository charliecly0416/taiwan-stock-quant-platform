# 台股独立项目全场景 E2E 优化工作文档

## 1. 背景

根据 `docs/TW_STOCK_FULL_SCENARIO_E2E_ANALYSIS_CN.md` 的全场景 Playwright 分析，独立项目主闭环已经成立：

```text
FinMind raw 补数
Yahoo/Scrapling qlib 补数
-> qlib provider
-> accepted latest
-> backend API
-> frontend 展示
-> Agent / cross-analysis / human review
```

但仍有几类用户体验和工程质量问题需要补齐：

- 自动更新状态只存在于文件和日志中，前端不可见。
- `fresh_data_wait`、pending asof、Yahoo/FinMind 新鲜度差异没有用户级解释。
- 控制台存在可修复警告。
- watchlist 草稿回填可能存在测试老化或真实 UI 缺陷。
- full scenario E2E 尚未纳入项目级只读验收脚本。

本阶段目标不是扩大交易能力，也不是接入实盘。所有工作必须保持研究只读边界。

## 2. 总目标

完成“全场景 E2E 优化”：

1. 前端能一眼看到每日自动更新状态。
2. 用户能理解 FinMind raw 已更新但 Yahoo qlib 尚未更新时的等待状态。
3. 核心页面控制台警告清理到可作为 E2E 门禁。
4. watchlist 草稿回填交互被复核并修正。
5. 全场景 Playwright 只读脚本纳入项目，作为后续回归测试。

## 3. 强制边界

执行者不得引入以下行为：

- 不允许自动下单。
- 不允许连接 broker。
- 不允许生成 paper/live order。
- 不允许绕过 accepted latest 发布门禁。
- 不允许把 FinMind raw 价格混入 qlib Yahoo/Scrapling provider。
- 不允许让前端普通页面触发正式 qlib publish、normal publish 或 EOD publish。
- 不允许把 generated data、模型、大型报告提交到 Git。

所有新增 API 和 UI 必须继续返回或展示研究边界：

```text
orders_enabled=false
connects_to_broker=false
research_signal_not_order=true
```

## 4. 工作拆分

建议拆成 5 步执行。每一步完成后必须写 report 文档，等待审核后再进入下一步。

---

## Step 1：自动更新状态后端 API

### 目标

新增只读 API，把当前每日自动更新状态从文件系统和日志中结构化暴露给前端。

### 工作内容

1. 新增或扩展 backend service，用于读取：
   - `qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json`
   - `data_tw/ops/daily_auto_update/pending_asof.json`
   - `data_tw/ops/daily_auto_update/*/job.json` 中最新 job
   - `data_tw/ops/daily_auto_update/cron.log` 最近若干行，如果存在
2. 解析并返回：
   - `latest_asof`
   - `latest_status`
   - `latest_run_id`
   - `pending_asof`
   - `pending_reason`
   - `last_job_id`
   - `last_job_status`
   - `last_job_started_at`
   - `last_job_finished_at`
   - `finmind_update_status`
   - `finmind_archived_count`
   - `yahoo_target_asof`
   - `yahoo_date_max`
   - `yahoo_missing_asof_count`
   - `fresh_data_wait`
   - `next_retry_hint`
   - `cron_installed_hint`
3. 新增只读 API，例如：

```text
GET /api/tw-stock/quant/ops/daily-auto-update/status
```

4. API 不需要登录也可读，或复用现有登录策略均可；但不能触发任何写操作。
5. 增加 backend 单元测试，覆盖：
   - 无 job
   - latest 已成功
   - pending asof 存在
   - fresh_data_wait
   - job.json 损坏或缺字段时降级返回 warning

### 验收标准

- API 返回 HTTP 200。
- 不创建、不修改、不删除任何数据文件。
- pending asof 存在时能正确显示。
- latest 已更新时能显示 latest asof/run_id。
- 返回研究安全 flags。
- backend 测试通过。

### 报告断点

完成后写：

```text
docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP1_REPORT_CN.md
```

报告必须包含：

- 新增/修改文件列表
- API 示例响应
- 测试命令与结果
- 是否触发任何写操作
- 是否发现数据状态异常

---

## Step 2：前端自动更新状态面板

### 目标

在 `/tw-stock-monitor` 页面增加“每日自动更新状态”只读面板，让用户不用看命令行也能理解当前数据状态。

### 工作内容

1. 新增 frontend API helper 调用 Step 1 API。
2. 在台股监控页面增加状态面板，建议放在 qlib 数据状态附近。
3. 面板展示：
   - latest accepted asof
   - pending asof
   - last job status
   - FinMind raw 是否成功
   - FinMind archived count
   - Yahoo/Scrapling 当前最大日期
   - 目标 asof 是否缺失
   - 下次重试提示
4. 对 `fresh_data_wait` 给出明确用户文案：

```text
FinMind raw 数据已更新，但 Yahoo/Scrapling qlib 复权数据尚未到目标日期。系统会继续按定时任务重试 pending asof。
```

5. 面板必须是只读展示，不提供普通用户触发 publish/refresh 的按钮。
6. 增加前端静态检查或 E2E 检查：
   - 面板存在
   - fresh_data_wait 文案存在
   - pending asof 可见
   - 页面没有新增危险请求

### 验收标准

- 页面可见自动更新状态。
- fresh_data_wait 时用户能理解“不是失败，是等待 Yahoo 数据”。
- 不出现下单、broker、publish 按钮。
- 前端 build 通过。
- 相关测试通过。

### 报告断点

完成后写：

```text
docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP2_REPORT_CN.md
```

报告必须包含：

- 截图路径
- API 响应摘要
- 前端测试命令和结果
- 是否发现 UI 溢出或移动端问题

---

## Step 3：控制台警告清理

### 目标

清理本次 E2E 发现的控制台警告，让台股核心页面更适合作为长期质量门禁。

### 工作内容

1. 修复 DatePicker invalid moment value。
2. 修复 Vue prop casing：
   - `readonly` 改为组件声明兼容的 `read-only` 或 `readOnly`。
3. 复查是否还有 Ant Design/Vue 可控 warning。
4. 对不可控第三方 notice，测试中可降级为 allowlist，但必须写明原因。
5. 增加 console clean 检查：
   - page error 必须为 0。
   - failed response 必须为 0。
   - warning/error 只允许明确 allowlist。

### 验收标准

- `/tw-stock-monitor` 无 DatePicker invalid value。
- 无 Vue prop casing warning。
- Playwright console issue 数量显著下降。
- 不通过隐藏 console 或禁用日志来“修复”问题。

### 报告断点

完成后写：

```text
docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP3_REPORT_CN.md
```

报告必须包含：

- 修复前后 console issue 对比
- allowlist 项及原因
- Playwright 结果摘要

---

## Step 4：watchlist 草稿回填复核与修正

### 目标

确认 qlib TopN “加入观察草稿 -> 填入监控配置”的链路是真实可用，还是旧测试选择器失效。

### 工作内容

1. 用真实页面复现：
   - 打开 `/tw-stock-monitor`
   - 从 qlib Top30 选择一只股票
   - 点击加入观察
   - 点击填入监控配置
   - 检查 monitor config symbols 是否包含该股票
2. 如果是 UI 缺陷：
   - 修复回填逻辑
   - 保证不自动保存
   - 保证不触发 monitor scan
   - 保证不触发 alerts 写操作
3. 如果是测试缺陷：
   - 更新测试选择器
   - 增加稳定 `data-testid`
4. 建议新增 `data-testid`：
   - `qlib-signal-table`
   - `qlib-watch-add`
   - `qlib-watch-fill-config`
   - `monitor-config-symbols`
   - `monitor-config-drawer`

### 验收标准

- 回填后配置表单确实包含目标股票。
- 回填动作不保存配置。
- 回填动作不触发 scan。
- E2E 脚本稳定通过。

### 报告断点

完成后写：

```text
docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP4_REPORT_CN.md
```

报告必须包含：

- 判断结论：UI 缺陷还是测试缺陷
- 修复说明
- E2E 截图
- 网络请求审计

---

## Step 5：全场景只读 Playwright 脚本纳入项目

### 目标

把本次 `full_scenario_check.mjs` 类型的全场景测试纳入项目，用于后续回归。

### 工作内容

1. 将脚本整理到项目目录，例如：

```text
frontend/tests/e2e/tw-stock-full-scenario-readonly.mjs
```

2. 测试保持只读：
   - 允许 GET health/latest/context/history/templates。
   - 禁止 POST order/publish/broker/refresh。
   - 对 quick-trade GET history 明确标记为只读。
3. 覆盖：
   - 主要前端路由可达
   - 台股监控页加载
   - qlib latest
   - Top30/Top50
   - cross-analysis
   - Agent context
   - 自动更新状态面板
   - 图表 canvas 非空
   - dangerous request count 为 0，或只读 allowlist 明确
4. 输出结构化报告到 ignored 目录：

```text
data_tw/ops/e2e_full_scenario/<timestamp>/
```

5. README 或使用文档补充运行方式。

### 验收标准

- 脚本可在真实本地前后端上运行。
- 失败时有截图和 JSON 报告。
- 不触发写操作。
- dangerous action 拦截有效。
- 可作为 CI/local smoke 的候选脚本。

### 报告断点

完成后写：

```text
docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP5_REPORT_CN.md
```

报告必须包含：

- 路由覆盖数量
- API 覆盖数量
- console issue 数量
- dangerous request 明细
- screenshot/report 路径

---

## 5. 最终验收

五步完成后，执行者需要写总验收报告：

```text
docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_ACCEPTANCE_CN.md
```

总验收必须回答：

1. 自动更新状态是否已在前端可见？
2. fresh_data_wait 是否能被普通用户理解？
3. pending asof 是否能跨午夜继续重试？
4. qlib accepted latest 是否仍只通过门禁更新？
5. FinMind raw 与 Yahoo qlib 口径是否仍然隔离？
6. watchlist 草稿回填是否稳定？
7. console clean 是否达到门禁要求？
8. full scenario E2E 是否可重复运行？
9. 是否出现任何交易、下单、broker、副作用写操作？

## 6. 推荐执行顺序

严格按以下顺序执行：

```text
Step 1 后端自动更新状态 API
-> Step 2 前端自动更新状态面板
-> Step 3 控制台警告清理
-> Step 4 watchlist 草稿回填复核
-> Step 5 全场景只读 E2E 脚本纳入项目
-> Acceptance 总验收
```

不要把 Step 5 提前到 Step 1/2 之前，否则 E2E 脚本会缺少自动更新状态面板覆盖点。

## 7. 当前建议

优先让执行者从 Step 1 开始。Step 1 是后续 UI 和 E2E 的基础，断点适中，风险低，且不会改变 qlib 数据或前端行为。
