# Phase S4 工作文档：Skills 最终总结、版本化验收与同步建议

生成日期：2026-06-19

## 1. 工作结论

Phase S3 已审查通过，允许进入 Phase S4。

本阶段目标是收尾台股项目 skills 维护路线，给出可长期维护的最终清单、职责边界、触发关系、版本化状态和用户级同步建议。

本阶段不是新增 skill 阶段，也不是业务开发阶段。

## 2. 本阶段输出

执行者必须输出：

```text
docs/tw_skills_maintenance/PHASES4_FINAL_SUMMARY_CN.md
```

审查者后续将输出：

```text
docs/tw_skills_maintenance/PHASES4_FINAL_ACCEPTANCE_REVIEW_CN.md
```

## 3. 必须复核的最终对象

九个项目级台股 skills：

```text
.agents/skills/tw-stock-safety-boundary-review/SKILL.md
.agents/skills/tw-stock-readonly-e2e-acceptance/SKILL.md
.agents/skills/tw-stock-research-context-analyst/SKILL.md
.agents/skills/tw-stock-data-freshness-diagnosis/SKILL.md
.agents/skills/tw-stock-new-model-onboarding/SKILL.md
.agents/skills/tw-stock-new-strategy-onboarding/SKILL.md
.agents/skills/tw-stock-modular-integration-regression/SKILL.md
.agents/skills/tw-stock-agent-daily-prompt-maintenance/SKILL.md
.agents/skills/tw-stock-frontend-workbench-ux-review/SKILL.md
```

辅助 skill：

```text
.agents/skills/frontend-design/SKILL.md
```

其中 `frontend-design` 不是台股业务 skill，但必须被 `tw-stock-frontend-workbench-ux-review` 引用。

## 4. 严禁事项

不得修改：

```text
backend/
frontend/
scripts/
configs/
examples/
qlib/
data_tw/
```

不得新增或恢复：

```text
/home/chuliyang/.agents/skills/tw-stock-*
```

不得触发：

```text
真实数据拉取
provider refresh / publish
accepted latest switch
monitor config / scan / alerts 写入
broker / quick-trade / order
target position / target weight 写入
OpenAI 调用或 key 读取
默认切换生产模型
默认切换前端策略
```

本阶段只允许读取文件、做静态检查、写最终总结文档。如发现 skill 文本仍有明确错误，必须先在报告中列为待修，不要自行扩大修改范围。

## 5. 必须执行的最终检查

### 5.1 项目 skills 清单

执行并记录：

```bash
find .agents/skills/tw-stock-* -maxdepth 2 -name SKILL.md -print | sort
```

预期：恰好九个。

### 5.2 用户级 active 路径检查

执行并记录：

```bash
find /home/chuliyang/.agents/skills -maxdepth 1 -type d -name 'tw-stock-*' -print | sort
```

预期：为空。

### 5.3 Archive 残余风险说明

检查并说明：

```text
/home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/
```

要求：

- 不修改 archive。
- 说明 archive 只是旧版本备份，不应作为 active skill 来源。
- 如果当前运行时仍可能加载 archive 中的旧 skills，列为后续运行时配置风险，不在 S4 内擅自删除。

### 5.4 章节结构抽查

确认九个 `SKILL.md` 均包含：

```text
name
description
Purpose
Read First
Allowed Actions / Evidence
Forbidden Actions
Workflow
Output Format
Trigger Examples
Stop Conditions
```

### 5.5 红线扫描

执行并归因：

```bash
rg -n "provider publish|accepted latest switch|quick-trade|broker|submit order|place order|target_position|target_weight|OpenAI API key|OPENAI_API_KEY|browser-side OpenAI|frontend OpenAI|default-switch|production default" .agents/skills/tw-stock-*
```

预期：命中只能出现在禁止项、停止条件、审查规则、deny-list、readonly boundary 或安全脚本中。

### 5.6 版本化状态

执行并记录：

```bash
git status --short .agents/skills docs/tw_skills_maintenance
```

要求：

- 明确 `.agents/skills/` 是否仍为 untracked。
- 明确 `docs/tw_skills_maintenance/` 是否仍为 untracked。
- 如仍未跟踪，给出建议：最终合并前必须纳入版本管理。

## 6. 最终总结必须包含的内容

### 6.1 九个 skills 的职责表

至少包含：

| Skill | 主要用途 | 触发场景 | 不应处理 | 关键禁止项 |
| --- | --- | --- | --- | --- |

九个 skills 都要覆盖。

### 6.2 Skill 之间的委派关系

必须说明：

```text
safety-boundary-review vs readonly-e2e-acceptance
readonly-e2e-acceptance vs frontend-workbench-ux-review
research-context-analyst vs data-freshness-diagnosis
agent-daily-prompt-maintenance vs safety-boundary-review
new-model-onboarding vs new-strategy-onboarding
modular-integration-regression vs 单模块 onboarding/maintenance
```

### 6.3 只读与安全边界总表

必须明确这些动作不属于当前 skills 自动执行范围：

```text
真实数据拉取
provider refresh / publish
accepted latest switch
monitor 写入
broker / quick-trade / order
target_position / target_weight
前端 OpenAI 调用
OpenAI key 暴露
默认生产模型/策略切换
```

### 6.4 已完成阶段回顾

按 S0-S3 总结：

```text
S0 Inventory 与落点确认
S1 既有四个 skills 更新
S1R 项目本地迁移
S2 新增五个 skills
S3 触发、委派、越界停止静态验证
```

### 6.5 未覆盖范围与残余风险

至少说明：

```text
未运行完整 skill-creator 子会话 eval
未生成 eval viewer
未验证真实运行时自动触发命中率
archive 旧 skills 仍存在于归档目录
.agents/skills 若未纳入版本管理会影响后续复用
```

这些是残余风险，不必在 S4 内修复，除非统筹另行授权。

### 6.6 后续维护建议

必须说明什么时候需要更新 skills：

```text
新增模型合同或 registry 规则
新增策略合同或 replay 规则
Agent route 或 DailyAgentPromptArtifact 合同变化
/tw-stock-monitor 前端工作台主线变化
readonly E2E 验收证据格式变化
数据 freshness 字段或 latest pointer 变化
安全边界新增 forbidden endpoints/fields
```

## 7. 执行报告格式

请输出：

```text
docs/tw_skills_maintenance/PHASES4_FINAL_SUMMARY_CN.md
```

报告结构：

```markdown
# Phase S4 最终总结：台股项目 Skills 维护路线

## 1. 最终结论
## 2. 最终 skills 清单
## 3. 九个 skills 职责表
## 4. 委派关系与触发边界
## 5. 只读与安全边界
## 6. S0-S3 阶段回顾
## 7. 静态检查结果
## 8. 版本化状态
## 9. 用户级同步建议
## 10. Archive 残余风险
## 11. 未覆盖范围
## 12. 后续维护建议
```

## 8. 通过标准

Phase S4 通过必须满足：

```text
九个项目级 tw-stock skills 清单完整
用户级 active tw-stock-* 路径为空
职责表和委派关系清楚
只读/安全边界无放松
红线扫描无执行性危险文本
明确版本化状态和纳入版本管理建议
明确 archive 旧 skills 的残余风险
明确未运行完整 eval 的覆盖边界
未修改业务代码、前端代码、模型策略代码或数据目录
```
