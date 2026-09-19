# Phase R2 执行报告：Skills 与运行时入口确认

生成日期：2026-06-20

## 1. 结论

Phase R2 已完成只读检查。结论：有条件通过，建议进入审查。

通过项：

```text
project-local 九个 tw-stock skills 完整
用户级 active /home/chuliyang/.agents/skills/tw-stock-* 路径为空
archive 目录存在且本次未删除、未移动、未覆盖
九个 project-local SKILL.md 均具备 frontmatter 与核心章节
关键 skills 研发前职责边界清楚
红线扫描命中均处于 Forbidden Actions / Stop Conditions / deny-list / readonly boundary / 审查规则语境
```

需要审查者关注的运行时风险：

```text
当前会话可见 project-local .agents/skills。
但当前运行时 skill 元数据列表仍可见 archive 旧 skills 条目。
文件系统 active 路径为空不等于运行时一定不会残留已加载 archive metadata。
后续新模型/新策略执行节点启动前，必须明确提示“以 project-local .agents/skills 为准”。
建议统筹确认是否需要额外运行时配置或启动约束，排除 /home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/。
```

本阶段未触发真实数据、provider publish、accepted latest、monitor 写入、broker/order 或 OpenAI。

## 2. Project-local skills 清单

执行命令：

```bash
find .agents/skills/tw-stock-* -maxdepth 2 -name SKILL.md -print | sort
```

结果恰好九个：

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

判定：通过。

## 3. 用户级 active 路径检查

执行命令：

```bash
find /home/chuliyang/.agents/skills -maxdepth 1 -type d -name 'tw-stock-*' -print | sort
```

结果：

```text
空输出
```

判定：通过。用户级 active skill 根目录没有平行 `tw-stock-*` 版本抢占 project-local skills。

## 4. Archive 目录与运行时风险

检查目录：

```text
/home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/
```

只读检查结果：目录存在，包含四个旧 skill 备份：

```text
tw-stock-data-freshness-diagnosis
tw-stock-readonly-e2e-acceptance
tw-stock-research-context-analyst
tw-stock-safety-boundary-review
```

对应 SKILL.md：

```text
/home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/tw-stock-data-freshness-diagnosis/SKILL.md
/home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/tw-stock-readonly-e2e-acceptance/SKILL.md
/home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/tw-stock-research-context-analyst/SKILL.md
/home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/tw-stock-safety-boundary-review/SKILL.md
```

本次未删除、未移动、未覆盖 archive。

运行时风险说明：当前会话的可用 skills 元数据中仍显示这些 archive 旧 skill 条目，说明运行时可能已加载历史 metadata。虽然 `/home/chuliyang/.agents/skills` maxdepth 1 active 路径为空，但后续执行者仍必须显式优先使用 project-local `.agents/skills/tw-stock-*`。建议统筹确认启动配置是否能排除 archive 子目录，避免新节点误触发旧版本描述。

判定：文件系统 active 检查通过；运行时 archive metadata 残余风险需审查确认。

## 5. Skill frontmatter / 章节抽查

抽查命令：

```bash
rg -n "^(---|name:|description:|# |## Purpose|## Read First|## Allowed Actions / Evidence|## Forbidden Actions|## Workflow|## Output Format|## Trigger Examples|## Stop Conditions)" .agents/skills/tw-stock-*/SKILL.md
```

九个 project-local skills 均包含：

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

抽查结论：通过。

## 6. 关键 skills 触发边界

研发前关键入口说明：

```text
tw-stock-new-model-onboarding
```

用途：新模型研发/接入入口，包括 ModelSignalArtifact、adapter、registry、golden samples、validator、OOS 证据。边界：不能 default-switch production model，不能改前端默认，不能 provider publish / accepted latest switch，不能 broker/order/quick-trade，不能承诺收益或胜率。

```text
tw-stock-new-strategy-onboarding
```

用途：新策略规则、dependency YAML、OrderIntentArtifact、readonly replay、review checklist。边界：只能走 StrategyRule / OrderIntent / readonly ReplayResult，不产生真实订单，不连接 broker，不输出 target_position / target_weight，不改默认策略。

```text
tw-stock-modular-integration-regression
```

用途：新模型/新策略接入后的只读集成回归，确认 DataSourceSnapshot / FeatureArtifact / ModelSignalArtifact / StrategyRule / OrderIntentArtifact / ReplayResult / ReadonlyStrategySnapshot / DailyAgentPromptArtifact / Backend / Frontend 链路。边界：只用 validators、fixtures、dry-run、GET、静态检查、readonly Playwright。

```text
tw-stock-safety-boundary-review
```

用途：审查 diffs、Agent 回答、frontend/network/console evidence 是否违反 forbidden actions。边界：只审查，不触发 provider/latest/monitor/broker/order/OpenAI。

```text
tw-stock-readonly-e2e-acceptance
```

用途：只读 UI/Agent/E2E 验收，包括 screenshots、network_audit、console_audit、DailyAgentPromptArtifact validator gate。边界：不得触发真实数据 refresh、provider publish、accepted latest、monitor writes、broker/order、frontend OpenAI。

## 7. 红线扫描与归因

执行命令：

```bash
rg -n "provider publish|accepted latest switch|quick-trade|broker|submit order|place order|target_position|target_weight|OpenAI API key|OPENAI_API_KEY|browser-side OpenAI|frontend OpenAI|default-switch|production default" .agents/skills/tw-stock-*
```

命中归因：

- `tw-stock-agent-daily-prompt-maintenance`：命中在 description、Forbidden Actions、Stop Conditions、validator 审查示例中，语义为禁止 frontend OpenAI、OpenAI key、provider publish、accepted latest、broker、quick-trade、target_position/target_weight。
- `tw-stock-new-model-onboarding`：命中在 description、Forbidden Actions、Stop Conditions 中，语义为禁止 default-switch production model、frontend defaults、provider publish、accepted latest、broker/order/quick-trade、target_position/target_weight。
- `tw-stock-new-strategy-onboarding`：命中在 description、Forbidden Actions、Workflow、Stop Conditions 中，语义为禁止真实订单、broker、quick-trade、submit/place order、target_position/target_weight、provider publish、accepted latest。
- `tw-stock-modular-integration-regression`：命中在 Forbidden Actions、Stop Conditions 中，语义为禁止 provider publish/refresh、accepted latest switch、broker/quick-trade/order、target_position/target_weight、production default switch。
- `tw-stock-safety-boundary-review`：命中在审查对象、Forbidden Actions、Workflow、Stop Conditions、references deny-list 和 audit script 中，语义为检测/禁止危险路径，不是授权执行。
- `tw-stock-readonly-e2e-acceptance`：命中在 readonly boundary、Forbidden Actions、Workflow、Stop Conditions、report template 中，语义为验收中确认 forbidden counts 为 0。
- `tw-stock-data-freshness-diagnosis`：命中在 description、Forbidden Actions、Stop Conditions、references 中，语义为只读诊断不得触发 publish/latest/broker/order。
- `tw-stock-frontend-workbench-ux-review`：命中在 description、Forbidden Actions、Workflow、Stop Conditions 中，语义为 UX 工作不得暴露 broker/order/frontend OpenAI/provider/latest 等入口。
- `tw-stock-research-context-analyst`：命中在 description、Forbidden Actions、Stop Conditions、references 中，语义为研究解释不得变成交易指令或目标仓位。

判定：红线扫描无执行性危险文本。命中均为 forbidden list、readonly boundary、Stop Conditions、审查规则或拒绝语境。

## 8. 是否建议进入 R3

执行侧建议：可以提交 R2 审查，并在审查通过后进入 R3。

进入 R3 前建议保留两条约束：

```text
1. 后续新模型/新策略执行者启动前必须提醒：以 project-local .agents/skills/tw-stock-* 为准。
2. 因当前运行时仍可见 archive 旧 skill 元数据，建议统筹确认是否需要额外运行时配置排除 /home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/。
```

本次 R2 未触发：

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
