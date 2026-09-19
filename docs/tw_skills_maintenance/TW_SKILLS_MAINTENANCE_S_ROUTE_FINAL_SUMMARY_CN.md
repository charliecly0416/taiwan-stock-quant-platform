# 台股项目 Skills 维护 S 路线最终总结

生成日期：2026-06-19

## 1. 收尾结论

台股项目 skills 维护 S 路线已完成，可以收尾。

本路线完成了项目级 skills 的盘点、迁移、更新、新增、触发边界验证和最终验收总结。当前项目本地 `.agents/skills/` 下共有九个 `tw-stock-*` skills，用户级 `/home/chuliyang/.agents/skills/tw-stock-*` active 路径为空。

最终验收结论见：

```text
docs/tw_skills_maintenance/PHASES4_FINAL_ACCEPTANCE_REVIEW_CN.md
```

## 2. 最终交付物

项目级台股 skills：

```text
.agents/skills/tw-stock-agent-daily-prompt-maintenance/SKILL.md
.agents/skills/tw-stock-data-freshness-diagnosis/SKILL.md
.agents/skills/tw-stock-frontend-workbench-ux-review/SKILL.md
.agents/skills/tw-stock-modular-integration-regression/SKILL.md
.agents/skills/tw-stock-new-model-onboarding/SKILL.md
.agents/skills/tw-stock-new-strategy-onboarding/SKILL.md
.agents/skills/tw-stock-readonly-e2e-acceptance/SKILL.md
.agents/skills/tw-stock-research-context-analyst/SKILL.md
.agents/skills/tw-stock-safety-boundary-review/SKILL.md
```

辅助 skill：

```text
.agents/skills/frontend-design/SKILL.md
```

路线文档与报告：

```text
docs/tw_skills_maintenance/PHASES0_INVENTORY_EXECUTION_REPORT_CN.md
docs/tw_skills_maintenance/PHASES0_INVENTORY_REVIEW_CN.md
docs/tw_skills_maintenance/PHASES1_EXISTING_SKILLS_UPDATE_EXECUTION_REPORT_CN.md
docs/tw_skills_maintenance/PHASES1_EXISTING_SKILLS_UPDATE_REVIEW_CN.md
docs/tw_skills_maintenance/PHASES1R_PROJECT_SKILLS_MIGRATION_EXECUTION_REPORT_CN.md
docs/tw_skills_maintenance/PHASES1R_PROJECT_SKILLS_MIGRATION_REVIEW_CN.md
docs/tw_skills_maintenance/PHASES2_NEW_SKILLS_EXECUTION_REPORT_CN.md
docs/tw_skills_maintenance/PHASES2_NEW_SKILLS_REVIEW_CN.md
docs/tw_skills_maintenance/PHASES3_SKILLS_TRIGGER_AND_BOUNDARY_VALIDATION_EXECUTION_REPORT_CN.md
docs/tw_skills_maintenance/PHASES3_SKILLS_TRIGGER_AND_BOUNDARY_VALIDATION_REVIEW_CN.md
docs/tw_skills_maintenance/PHASES4_FINAL_SUMMARY_CN.md
docs/tw_skills_maintenance/PHASES4_FINAL_ACCEPTANCE_REVIEW_CN.md
```

## 3. 阶段回顾

S0 Inventory：确认项目原本缺少台股专用 project-local skills，识别用户级旧 skills 与当前项目路线的差距。

S1 Existing Skills Update：更新四个既有 skills，使其覆盖 DailyAgentPromptArtifact、backend `/api/tw-stock/agent/simple-chat`、UI2、OpenAI key/前端调用边界、latest/asof 语义和只读验收要求。

S1R Project Skills Migration：将用户级旧 `tw-stock-*` skills 迁移到项目本地 `.agents/skills/`，并将旧用户级版本归档到 `_archived_tw_stock_skills_20260619/`。

S2 New Skills：新增五个项目级 skills，覆盖新模型接入、新策略接入、模块化集成回归、Agent Daily Prompt 维护和前端策略工作台 UX 审查。

S3 Trigger and Boundary Validation：完成九个 skills 的静态结构检查、触发/委派矩阵、越界停止样例和红线扫描归因，并统一章节标题。

S4 Final Summary and Acceptance：完成最终清单、职责边界、版本化状态、用户级同步建议、archive 风险和未覆盖范围说明；审查判定通过。

## 4. 当前权威来源

当前权威来源为项目本地：

```text
.agents/skills/tw-stock-*
```

不应恢复或维护用户级 active 路径：

```text
/home/chuliyang/.agents/skills/tw-stock-*
```

archive 目录仅作备份：

```text
/home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/
```

如果运行时仍加载 archive 元数据，应在后续单独处理 skill 搜索路径、archive 命名或加载排除策略。

## 5. 不可越过的边界

九个台股 skills 均必须保持只读、研究、审查、合同优先边界。不得自动执行：

```text
真实数据拉取
provider refresh / publish
accepted latest switch
monitor config / scan / alerts 写入
broker / quick-trade / order
target_position / target_weight
前端 OpenAI 调用
OpenAI key 暴露
默认生产模型/策略切换
默认前端策略切换
收益、胜率、上涨概率承诺
```

## 6. 版本管理要求

当前复核状态显示：

```text
?? .agents/skills/
?? docs/tw_skills_maintenance/
```

收尾后的合并前要求：

```text
.agents/skills/
docs/tw_skills_maintenance/
```

必须纳入版本管理，否则后续 agent 运行无法稳定复用这些项目级 skills 和维护报告。

## 7. 未覆盖范围

本路线完成的是静态触发矩阵 + 人工边界验证。

未覆盖：

```text
完整 skill-creator 子会话 eval
with-skill / baseline 对比
eval viewer
真实运行时自动触发命中率
跨会话加载缓存刷新验证
archive 目录是否被运行时扫描的配置级验证
```

这些不是当前 S 路线阻塞项，但应作为后续运行时质量改进方向。

## 8. 后续维护触发条件

以下情况发生时，应更新对应 skills 与维护文档：

```text
新增模型合同或 registry 规则
新增策略合同或 readonly replay 规则
DailyAgentPromptArtifact 或 simple-chat 合同变化
/tw-stock-monitor 前端工作台主线变化
readonly E2E 验收证据格式变化
freshness/latest/asof 字段变化
新增 forbidden endpoints 或 forbidden fields
OpenAI/key、broker/order、monitor 写入边界变化
```

维护顺序：先更新项目级 `.agents/skills/tw-stock-*`，再更新对应验证报告；不得在用户级 active skills 中创建平行版本。
