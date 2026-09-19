# Phase R2 工作文档：Skills 与运行时入口确认

生成日期：2026-06-20

## 1. 工作结论

Phase R1 已在 R1R2 repair 后审查通过，允许进入 Phase R2。

R2 的目标是确认新模型/新策略研发前，台股 project-local skills 与运行时入口没有冲突、没有全局旧版本抢占、archive 旧版本不会误作为 active skill 使用。

本阶段不是新模型或新策略研发。

## 2. 严禁事项

不得执行或触发：

```text
训练新模型
新增策略规则
修改默认模型或默认策略
修改前端默认展示
真实数据拉取
provider refresh / publish
accepted latest switch
monitor config / scan / alerts 写入
broker / quick-trade / order
target_position / target_weight 写入
OpenAI key 读取
真实 OpenAI smoke
```

不得删除、移动或覆盖 archive 旧 skills，除非统筹另行明确授权。

## 3. 执行报告输出

执行者必须输出：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER2_SKILL_RUNTIME_ENTRY_EXECUTION_REPORT_CN.md
```

## 4. 必须检查项

### 4.1 Project-local skills 清单

执行：

```bash
find .agents/skills/tw-stock-* -maxdepth 2 -name SKILL.md -print | sort
```

预期恰好九个：

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

### 4.2 用户级 active 路径检查

执行：

```bash
find /home/chuliyang/.agents/skills -maxdepth 1 -type d -name 'tw-stock-*' -print | sort
```

预期：为空。

如果不为空，必须列出路径并判定为阻塞，不得继续。

### 4.3 Archive 目录检查

检查：

```text
/home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/
```

要求：

- 只读检查是否存在。
- 不删除、不移动、不覆盖。
- 说明 archive 只是旧版本备份，不应作为 active skill 来源。
- 如果当前运行时仍显示 archive skills 元数据，必须列为运行时加载残余风险。

### 4.4 Project-local skill frontmatter 抽查

对九个 `SKILL.md` 抽查：

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

不要求重写 skills；只确认当前文件仍完整。

### 4.5 关键 skills 触发边界确认

必须在报告中说明以下 skill 的研发前用途：

```text
tw-stock-new-model-onboarding：新模型研发入口，但不能默认切生产模型。
tw-stock-new-strategy-onboarding：新策略研发入口，但只能走 StrategyRule / OrderIntent / readonly replay。
tw-stock-modular-integration-regression：后续模型/策略接入后的只读集成回归。
tw-stock-safety-boundary-review：审查 forbidden actions。
tw-stock-readonly-e2e-acceptance：只读 UI/Agent/E2E 验收。
```

### 4.6 Runtime entry 风险说明

执行报告必须明确：

```text
当前执行节点是否能看到 project-local .agents/skills；
是否仍可能看到 archive 旧 skills；
后续新模型/新策略执行者启动前是否必须提醒“以 project-local skills 为准”；
是否需要统筹提供额外运行时配置来排除 archive。
```

## 5. 建议静态检查

执行：

```bash
rg -n "provider publish|accepted latest switch|quick-trade|broker|submit order|place order|target_position|target_weight|OpenAI API key|OPENAI_API_KEY|browser-side OpenAI|frontend OpenAI|default-switch|production default" .agents/skills/tw-stock-*
```

预期：

```text
命中只能出现在 Forbidden Actions、Stop Conditions、deny-list、readonly boundary 或审查规则语境。
```

## 6. 报告格式

请输出：

```markdown
# Phase R2 执行报告：Skills 与运行时入口确认

## 1. 结论
## 2. Project-local skills 清单
## 3. 用户级 active 路径检查
## 4. Archive 目录与运行时风险
## 5. Skill frontmatter / 章节抽查
## 6. 关键 skills 触发边界
## 7. 红线扫描与归因
## 8. 是否建议进入 R3
```

## 7. R2 通过标准

R2 可通过必须满足：

```text
project-local 九个 tw-stock skills 完整
用户级 active tw-stock-* 路径为空
archive 没有被误判为 active 来源
关键 skills 职责边界清楚
红线扫描无执行性危险文本
明确后续执行者必须以 project-local skills 为准
未触发真实数据、provider publish、accepted latest、monitor、broker/order、OpenAI key
```
