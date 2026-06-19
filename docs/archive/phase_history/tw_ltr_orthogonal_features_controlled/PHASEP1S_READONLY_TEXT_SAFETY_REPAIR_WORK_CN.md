# Phase P1S 工作文档：Readonly Text Safety Repair

生成日期：2026-06-15

依据：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEP1R_E2E_VALIDATION_REVIEW_CN.md
frontend/tests/unit/tw-stock-monitor-static-check.mjs
```

## 1. P1S 目标

P1S 只做一件事：

```text
修复 P1R 新增 orthogonal LTR 只读面板中的只读安全禁词问题。
```

目标 gate：

```text
phase_p1s_readonly_text_safety_repaired
```

## 2. 必须修复的问题

当前静态检查失败：

```text
page contains forbidden text: target position
```

新增面板中的以下文案必须修改：

```text
不生成 target position/weight
```

禁止改成：

```text
目标仓位
建议仓位
target weight
target position
推荐买入
交易信号
买入概率
预测收益
预期涨幅
```

建议改成安全表达，例如：

```text
不生成操作指令
不输出交易执行信息
不产生实盘动作
```

## 3. 允许范围

P1S 只允许修改：

```text
frontend/src/views/tw-stock-monitor/index.vue
docs/tw_ltr_orthogonal_features_controlled/PHASEP1S_READONLY_TEXT_SAFETY_REPAIR_EXECUTION_REPORT_CN.md
```

只允许修改新增 orthogonal LTR 面板相关只读安全文案。

## 4. 禁止事项

P1S 禁止：

```text
改默认策略；
改 backend；
新增 API；
新增 POST/PUT/PATCH/DELETE；
触发 provider refresh / publish；
切换 accepted latest；
触发 monitor scan/config/alerts；
触发 broker/orders/quick-trade；
重训模型；
重跑 qlib；
新增 replay rule / filter / threshold / market gate；
扩大 P1R 面板功能范围。
```

## 5. 验证要求

执行者必须至少运行：

```text
cd frontend
node tests/unit/tw-stock-monitor-static-check.mjs
corepack pnpm build
```

若可行，继续运行：

```text
node tests/unit/tw-stock-daily-auto-update-panel-check.mjs
node tests/unit/tw-stock-console-clean-check.mjs
node tests/unit/tw-stock-watchlist-draft-check.mjs
```

修复报告必须贴出命令结果。

## 6. 输出要求

执行者必须写：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEP1S_READONLY_TEXT_SAFETY_REPAIR_EXECUTION_REPORT_CN.md
```

报告必须说明：

```text
修改了哪一句文案；
是否只改 frontend；
是否保留默认 fresh qlib；
是否仍只读；
静态检查是否通过；
build 是否通过；
是否仍有未完成浏览器 E2E。
```

P1S 通过后，再继续真实浏览器 E2E。
