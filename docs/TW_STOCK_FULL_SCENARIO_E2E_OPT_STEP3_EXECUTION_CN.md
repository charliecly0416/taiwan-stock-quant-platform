# 全场景 E2E 优化 Step 3 执行文档：控制台警告清理

## 1. 本步目标

清理全场景 E2E 中 `/tw-stock-monitor` 及相关核心页面出现的可控 console warning/error，让台股核心页面更适合作为长期 Playwright 质量门禁。

本步只处理控制台质量问题，不改变数据链路、不改变自动更新逻辑、不新增交易能力。

## 2. 背景问题

前置全场景 E2E 报告中记录到控制台存在 warning/error，主要包括：

- Ant Design lazy-load notice。
- DatePicker 收到 invalid moment value。
- Vue prop 使用 `readonly`，但组件声明为 `readOnly`，应改为 `read-only` 或正确 prop。

这些问题不阻断业务闭环，但会污染 E2E 质量门禁，也会降低长期可维护性。

## 3. 强制边界

本步不得引入：

- 下单、交易、broker 连接能力。
- qlib publish / normal publish / EOD publish。
- 自动 refresh provider。
- 自动触发 FinMind/Yahoo 拉取。
- watchlist 草稿回填修复。
- full scenario E2E 脚本纳入项目。

不得通过以下方式“掩盖”问题：

- 全局禁用 console。
- 在 Playwright 中忽略所有 warning/error。
- 删除 UI 组件但不修复根因。
- 把 warning 文案简单字符串替换隐藏。

允许对明确不可控的第三方 notice 做 allowlist，但必须在报告中说明原因。

## 4. 涉及文件建议

预计主要检查和修改：

```text
frontend/src/views/tw-stock-monitor/index.vue
frontend/src/views/**/*
frontend/src/components/**/*
frontend/tests/unit/*
```

如需要新增测试：

```text
frontend/tests/unit/tw-stock-console-clean-check.mjs
```

或扩展已有：

```text
frontend/tests/unit/tw-stock-monitor-static-check.mjs
```

完成后必须新增报告：

```text
docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP3_REPORT_CN.md
```

## 5. 具体任务

### 任务 1：定位 DatePicker invalid moment value

搜索 DatePicker / RangePicker / 日期输入相关代码：

```bash
rg -n "DatePicker|RangePicker|date-picker|range-picker|moment|readonly|readOnly" frontend/src
```

重点检查：

- 传给 DatePicker 的 `value` 是否可能是空字符串、非法字符串、普通 Date、非 moment 对象。
- 清空值时是否使用 `null` 而不是 `''`。
- 初始化值是否与组件期望类型一致。
- 表单 reset 是否把 date 字段设成非法值。

修复原则：

- 空日期用 `null`。
- 如果组件期望 moment，则保证传入 moment 或 null。
- 不要把 invalid date 字符串传入 DatePicker。

### 任务 2：修复 Vue prop casing warning

搜索：

```bash
rg -n "readonly|readOnly|read-only" frontend/src
```

处理原则：

- 在模板中对 Vue prop 使用 kebab-case：`read-only`。
- 如果是原生 HTML 属性，可保留 `readonly`。
- 如果是 Ant Design Vue 组件 prop，优先按组件文档/实际声明修正。

需要区分：

```vue
<!-- 组件 prop，推荐 -->
<a-input :read-only="true" />

<!-- 原生 input attribute，允许 -->
<input readonly />
```

实际应以当前组件和 warning 指向为准。

### 任务 3：处理 Ant Design lazy-load notice

判断 lazy-load notice 是否由项目代码触发。

如果是可控配置问题：

- 修复组件按需引入或使用方式。

如果是 Ant Design Vue 旧版本在 Vite/Vue2 下不可控 notice：

- 可以加入 E2E allowlist。
- 必须在报告中写明：
  - notice 原文
  - 为什么不可控
  - 为什么不影响业务
  - allowlist 范围必须精确，不允许 blanket ignore。

### 任务 4：建立 console clean 检查

建议新增脚本：

```text
frontend/tests/unit/tw-stock-console-clean-check.mjs
```

静态检查至少覆盖：

- 不再出现明显错误写法，如 `value: ''` 传给 DatePicker。
- 不再出现会触发 Vue prop casing warning 的组件写法。
- 如果存在 allowlist，allowlist 必须是精确字符串或精确正则。

如有 Playwright 条件，建议增加浏览器检查：

- 打开 `/tw-stock-monitor`
- 收集 console warning/error
- page error 必须为 0
- failed response 必须为 0
- console issue 必须为 0 或只包含明确 allowlist

## 6. 必跑命令

至少运行：

```bash
cd frontend
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-daily-auto-update-panel-check.mjs
node tests/unit/tw-stock-agent-panel-check.mjs
node tests/unit/tw-stock-cross-analysis-check.mjs
node tests/unit/tw-stock-monitor-qlib-ops-check.mjs
corepack pnpm build
```

如果新增 console clean 检查：

```bash
node tests/unit/tw-stock-console-clean-check.mjs
```

如果执行 Playwright 浏览器验证，报告中必须给出：

- 页面 URL
- console issue 数量
- page error 数量
- failed response 数量
- allowlist 明细

## 7. 验收标准

Step 3 完成必须满足：

1. DatePicker invalid moment value 警告被修复，或有明确不可控说明。
2. Vue prop casing warning 被修复。
3. 不通过全局禁用 console 掩盖问题。
4. 台股核心前端静态检查通过。
5. 前端 build 通过。
6. 不新增危险网络请求。
7. 不改变 accepted latest、daily auto update、watchlist 回填等业务逻辑。

## 8. 报告要求

完成后写：

```text
docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP3_REPORT_CN.md
```

报告必须包含：

- 新增/修改文件列表
- 修复的 console issue 明细
- 修复前后对比
- allowlist 明细及原因，如果存在
- 测试命令和结果
- 是否触发任何写操作
- 是否发现新的 UI 或 E2E 风险

## 9. 不要提前做的事

本步不要做：

- watchlist 草稿回填修复，这属于 Step 4。
- full scenario E2E 脚本纳入项目，这属于 Step 5。
- 自动更新状态面板功能扩展，除非是修复 console warning 必需。
- 后端 API 调整，除非 console warning 根因确实来自字段类型。

## 10. 下一报告断点

执行者完成后提交：

```text
docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP3_REPORT_CN.md
```

由审核者确认通过后，再进入 Step 4：watchlist 草稿回填复核与修正。
