# 全场景 E2E 优化 Step 3 报告：控制台警告清理

生成时间：2026-06-04
对应文档：`docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP3_EXECUTION_CN.md`

## 1. 本步目标

清理 `/tw-stock-monitor` 及相关核心页面的可控 console warning/error，使台股核心页面更适合作为长期 Playwright 质量门禁。

本步没有改动数据链路、自动更新调度、watchlist 草稿回填或交易能力。

## 2. 新增/修改文件

修改：

- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/src/views/agent-tokens/index.vue`
- `frontend/src/views/profile/index.vue`

新增：

- `frontend/tests/unit/tw-stock-console-clean-check.mjs`
- `docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP3_REPORT_CN.md`

## 3. 修复明细

### DatePicker invalid moment value

修复前：

```js
qlibOpsForm: {
  asof: '2026-06-01'
}
```

该字符串会传给 Ant Design Vue `a-date-picker` 的 `v-model`，触发：

```text
Warning: [antdv: DatePicker] `value` provides invalidate moment time. If you want to set empty value, use `null` instead.
```

修复后：

```js
qlibOpsForm: {
  asof: moment('2026-06-01', 'YYYY-MM-DD')
}
```

空日期继续使用 `null`，已有 `backtestForm.startDate/endDate` 初始化逻辑保持不变。

### Vue prop casing warning

修复前：

```vue
<a-input :value="revealed.token" readOnly class="reveal-token-input" />
<a-input :value="referralLink" readonly size="small">
```

在 Vue 模板中，组件 prop 应使用 kebab-case；上述写法会触发：

```text
[Vue tip]: Prop "readonly" is passed to component <Anonymous>, but the declared prop name is "readOnly".
```

修复后：

```vue
<a-input :value="revealed.token" read-only class="reveal-token-input" />
<a-input :value="referralLink" read-only size="small">
```

原生 DOM 的 `setAttribute('readonly', '')` 未改动，因为它不是 Vue 组件 prop。

## 4. Allowlist

浏览器验证后仍保留 1 条第三方 notice：

```text
[antd-pro] NOTICE: Antd use lazy-load.
```

处理方式：精确 allowlist。

原因：

- 该 notice 来自项目当前 Ant Design Vue / antd-pro 懒加载初始化路径。
- 它不是页面运行错误，不影响业务请求、渲染或交互。
- 本步目标是清理可控 warning；不为该 notice 改造全局组件加载方式，避免引入更大范围风险。
- allowlist 仅匹配这一条完整字符串，不 blanket ignore warning/error。

## 5. 修复前后对比

修复前全场景记录：

- console issue count：8
- 包含 DatePicker invalid moment warning。
- 包含多条 Vue `readonly/readOnly` prop casing warning。

修复后 Playwright 验证：

```json
{
  "url": "http://127.0.0.1:8000/#/tw-stock-monitor",
  "console_issue_count": 1,
  "non_allowed_console_issue_count": 0,
  "page_error_count": 0,
  "failed_response_count": 0,
  "dangerous_request_count": 0
}
```

截图与结果：

```text
/tmp/quantdinger_tw_step3/tw-stock-console-clean.png
/tmp/quantdinger_tw_step3/console-clean-result.json
```

## 6. 测试命令与结果

静态检查：

```bash
cd frontend
node tests/unit/tw-stock-console-clean-check.mjs
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-daily-auto-update-panel-check.mjs
node tests/unit/tw-stock-agent-panel-check.mjs
node tests/unit/tw-stock-cross-analysis-check.mjs
node tests/unit/tw-stock-monitor-qlib-ops-check.mjs
```

结果：

```text
tw-stock console clean static checks passed
tw-stock-monitor static checks passed
tw-stock daily auto update panel checks passed
tw-stock agent panel checks passed
tw-stock cross-analysis checks passed
tw-stock-monitor qlib ops checks passed
```

前端构建：

```bash
corepack pnpm build
```

结果：

```text
✓ built
```

Playwright 浏览器验证：

```text
URL: http://127.0.0.1:8000/#/tw-stock-monitor
console issue count: 1
non-allowed console issue count: 0
page error count: 0
failed response count: 0
dangerous request count: 0
```

## 7. 是否触发写操作

本轮没有触发任何业务写操作。

未触发：

- 下单、quick-trade、broker 连接
- qlib publish / normal publish / EOD publish
- refresh provider
- FinMind/Yahoo 拉取
- watchlist 草稿回填修复
- monitor scan-all

Playwright 网络审计中危险写请求计数为 `0`。

## 8. 新风险评估

未发现新的 UI 或 E2E 风险。

本步只修改了：

- DatePicker 初始值类型。
- Ant Design Vue 输入组件 prop 写法。
- console clean 静态检查。

这些修改不改变 accepted latest、daily auto update、watchlist 草稿回填、Agent、cross-analysis 或 qlib ops 的业务逻辑。

## 9. 验收结论

Step 3 已完成。

- DatePicker invalid moment value 警告已修复。
- Vue prop casing warning 已修复。
- 没有通过全局禁用 console 掩盖问题。
- 台股核心前端静态检查通过。
- 前端 build 通过。
- Playwright 验证通过，非 allowlist console issue 为 0。
- 未新增危险网络请求。
