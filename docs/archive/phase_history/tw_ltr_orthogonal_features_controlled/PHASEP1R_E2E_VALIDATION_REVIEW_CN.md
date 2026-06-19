# Phase P1R E2E/Readonly Validation 审查记录

生成日期：2026-06-15

审查对象：

```text
frontend/src/views/tw-stock-monitor/index.vue
docs/tw_ltr_orthogonal_features_controlled/PHASEP1R_IMPLEMENTATION_SCOPE_REPAIR_EXECUTION_REPORT_CN.md
```

## 1. 结论

P1R 范围修复方向正确，但真实只读验收未通过。

阻塞原因：

```text
frontend/tests/unit/tw-stock-monitor-static-check.mjs
失败：page contains forbidden text: target position
```

因此暂不进入后续 E2E / P2。

## 2. 已执行命令

在 `frontend/` 下执行：

```text
node tests/unit/tw-stock-monitor-static-check.mjs
```

结果：

```text
AssertionError [ERR_ASSERTION]: page contains forbidden text: target position
```

## 3. 失败来源

新增 P1R 面板中包含：

```text
不生成 target position/weight
```

既有静态安全检查禁止页面出现：

```text
target position
target weight
```

即使语义是否定句，也会被只读安全静态规则拦截。该规则是合理的：产品页面不应暴露交易/仓位术语，以免被用户理解成真实交易能力或仓位建议。

## 4. 审查判断

这不是模型、数据或主线偏离问题，而是前端只读安全文案问题。

需要最小修复：

```text
将新增 orthogonal LTR 面板中的 target position / target weight 英文文案替换为安全中文泛化表达；
不得引入“目标仓位 / 建议仓位 / 推荐买入 / 交易信号”等同类禁词；
修复后重跑静态检查和 build；
再继续浏览器 E2E。
```

## 5. Gate

当前 gate：

```text
stop_phase_p1r_blocked_by_readonly_static_check
```

下一步执行 Phase P1S 文案安全修复。

