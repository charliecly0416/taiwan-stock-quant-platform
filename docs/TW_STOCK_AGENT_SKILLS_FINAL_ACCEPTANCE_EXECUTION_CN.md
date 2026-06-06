# 台股 Agent Skills 最终验收执行文档

生成时间：2026-06-04

## 1. 本阶段目标

对三个阶段实现的 4 个台股 Agent skills 做最终验收，判断是否可以收尾。

验收对象：

```text
tw-stock-readonly-e2e-acceptance
tw-stock-safety-boundary-review
tw-stock-data-freshness-diagnosis
tw-stock-research-context-analyst
```

## 2. 必查项目

- 4 个 `SKILL.md` 是否存在。
- 每个 skill 是否有清晰 description，能被正确触发。
- 每个 skill 是否遵守只读边界。
- 每个 skill 是否有至少 3 个 eval prompt 的执行结果。
- research skill 是否拒绝买卖建议、仓位、收益承诺。
- freshness skill 是否只做 GET/文件读取，不触发更新。
- e2e skill 是否只运行 readonly E2E 和测试，不触发真实数据更新。
- safety skill 是否能区分危险行动指令与允许的拒绝/免责声明上下文。

## 3. 建议验收组合

执行以下组合测试：

```text
准备提交 / 发版 / 验收
-> tw-stock-readonly-e2e-acceptance
-> tw-stock-safety-boundary-review
```

```text
latest 没更新 / 数据不一致
-> tw-stock-data-freshness-diagnosis
-> tw-stock-safety-boundary-review
```

```text
研究解释 / 观察名单
-> tw-stock-research-context-analyst
-> tw-stock-safety-boundary-review
```

## 4. 收尾标准

满足以下条件即可收尾：

- 4 个 skills 均能被触发。
- 4 个 skills 的 eval 均通过。
- 没有默认流程触发 POST/PUT/PATCH/DELETE 或真实更新任务。
- 没有 broker/quick-trade/order/target position 能力泄漏。
- research 输出始终是人工研究复盘，不构成交易建议。
- 文档说明了 skills 位于用户级目录还是项目目录。

## 5. 最终报告

执行者完成后提交：

```text
docs/TW_STOCK_AGENT_SKILLS_FINAL_ACCEPTANCE_CN.md
```

报告必须包含：

- 4 个 skills 的目录位置。
- 每个 skill 的 description。
- 每个 skill 的 eval 结果摘要。
- 安全边界审查结果。
- 是否有误触发、漏触发或越界输出。
- 是否建议收尾。

