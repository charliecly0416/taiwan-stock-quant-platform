# Phase S0 审查意见：Inventory 与落点确认

生成日期：2026-06-19

## 1. 结论

审查结论：通过，允许进入 Phase S1。

允许进入的下一阶段仅限：

```text
Phase S1：修改既有四个 tw-stock-* skills
```

但有一个明确限制：S1 不得直接覆盖或删除用户级 `/home/chuliyang/.agents/skills/tw-stock-*`。S1 应先在 repo 内 `.agents/skills/tw-stock-*` 建立版本化副本并修改，完成审查后再由统筹决定是否同步到用户级运行时目录。

## 2. 对照主文档的符合性

S0 主文档要求执行者：

1. 列出 repo 内 `.agents/skills` 和用户级 `/home/chuliyang/.agents/skills` 的 skill 清单。
2. 判断当前运行时加载来源。
3. 读取四个既有 `tw-stock-*` skills 和 `frontend-design`。
4. 读取本工作文档和必读上下文。
5. 给出落点建议。
6. 不修改 skill，不新增 skill 目录，不删除或移动旧 skill。

执行报告基本满足上述要求。

我独立复核到：

repo 内当前只有：

```text
.agents/skills/frontend-design/SKILL.md
```

用户级当前有：

```text
/home/chuliyang/.agents/skills/pptx/SKILL.md
/home/chuliyang/.agents/skills/tw-stock-readonly-e2e-acceptance/SKILL.md
/home/chuliyang/.agents/skills/tw-stock-research-context-analyst/SKILL.md
/home/chuliyang/.agents/skills/tw-stock-data-freshness-diagnosis/SKILL.md
/home/chuliyang/.agents/skills/skill-creator/SKILL.md
/home/chuliyang/.agents/skills/latex-paper-en/SKILL.md
/home/chuliyang/.agents/skills/tw-stock-safety-boundary-review/SKILL.md
```

四个既有台股 skills 只在用户级目录中存在，repo 内暂无对应版本化副本。

## 3. Findings

### Critical

无。

### High

无。

### Medium

无。

### Low

1. 同名 skill 优先级仍未被严格证明。
   当前会话显示 repo 内 `.agents/skills/frontend-design` 与用户级 `tw-stock-*` 都能暴露给运行时，但无法证明如果 repo 内和用户级出现同名 `tw-stock-*`，运行时会选择哪个版本。执行报告已如实记录该不确定性。

2. 用户级旧 skills 仍是当前运行时已暴露版本。
   在 repo 内建立同名新版后，可能存在触发版本歧义。因此 S1 必须在执行报告中显式说明“repo 内版本化副本”与“用户级运行时旧版本”的关系。

## 4. Skill 触发与误触发风险

执行报告对四个旧 skills 的过期点判断成立。

### `tw-stock-safety-boundary-review`

当前仍能覆盖基础只读安全审查，但缺少：

- `DailyAgentPromptArtifact`。
- prompt builder / validator。
- OpenAI adapter。
- `/api/tw-stock/agent/simple-chat` 允许语境。
- 前端 OpenAI key/base URL/browser-side OpenAI call 禁止项。
- 英文危险语义，如 `place order`、`submit order`、`target_weight`、`target position`、`buy now`、`sell now`。
- Agent citation/qlib score 误解释检查。
- UI2 策略工作台与 Playwright artifacts 审查。

### `tw-stock-readonly-e2e-acceptance`

当前仍偏旧 full-scenario E2E，缺少：

- UI2 工作台 UX 验收。
- Agent simple-chat panel 验收。
- readonly strategy snapshot / readonly replay window。
- desktop/tablet/mobile 截图检查。
- `/agent/simple-chat` 与旧 `/agent/chat` 的主路径区分。
- 前端 OpenAI key/base URL/browser-side call 检查。
- DailyAgentPromptArtifact dry-run/validator gate。

### `tw-stock-research-context-analyst`

当前仍偏 qlib accepted latest / cross-analysis，缺少：

- `current-strategy-context`。
- `readonly-strategy-snapshot`。
- DailyAgentPromptArtifact 摘要。
- paper portfolio gate。
- replay result summary。
- 当前 E4 Qlib + Orthogonal LTR 默认研究口径。
- artifact id/checksum/snapshot id 等可追溯字段要求。

### `tw-stock-data-freshness-diagnosis`

当前仍偏 provider/qlib freshness，缺少四类 latest 区分：

```text
provider raw/latest
qlib accepted latest
readonly strategy snapshot latest
Agent DailyAgentPromptArtifact latest
```

也缺少 stale prompt / stale snapshot 对 UI2 工作台和 simple-chat 的下游影响说明。

## 5. 只读/安全边界审查

S0 只做读取、清单和报告写入。

我复核未发现 S0 修改：

```text
.agents/skills/tw-stock-*
/home/chuliyang/.agents/skills/tw-stock-*
台股业务代码
前端产品代码
模型/策略代码
测试代码
```

未触发：

```text
真实数据拉取
provider refresh / publish
accepted latest switch
monitor config / scan / alerts 写入
broker / quick-trade / order
target position / target weight
OpenAI 调用或 key 读取
```

S0 安全边界通过。

## 6. 文档与测试充分性

S0 执行报告充分说明了：

- repo 内与用户级 skills 差异。
- 当前四个旧台股 skills 的过期点。
- 当前运行时至少同时暴露 repo 内和用户级 skills。
- 同名优先级未知。
- 推荐 repo 内为准、审查后再同步用户级。

本阶段不要求 eval，也不要求修改 skills；因此未运行 skill eval 不构成问题。

## 7. 必修项

Phase S1 必须遵守以下约束：

1. 先在 repo 内创建四个既有台股 skills 的版本化副本：

```text
.agents/skills/tw-stock-safety-boundary-review/
.agents/skills/tw-stock-readonly-e2e-acceptance/
.agents/skills/tw-stock-research-context-analyst/
.agents/skills/tw-stock-data-freshness-diagnosis/
```

2. 从用户级旧目录复制 `SKILL.md`、`references/`、`scripts/` 等已有资源作为起点，再做修改。

3. 不得直接覆盖、删除、重命名或移动用户级 `/home/chuliyang/.agents/skills/tw-stock-*`。

4. 每个更新后的 `SKILL.md` 必须包含：

```text
name
description
Purpose
Read First
Allowed Evidence / Allowed Actions
Forbidden Actions
Workflow
Output Format
Trigger Examples
Stop Conditions
```

5. 每个 description 必须更准确触发，但不得泛化到所有台股任务。

6. 每个 skill 必须保留旧能力，同时补齐 simple-chat、DailyAgentPromptArtifact、UI2、modular contracts 和英文危险语义。

7. 每个 skill 至少准备：

```text
3 个 should_trigger prompts
2 个 should_not_trigger near-miss prompts
```

可以先写在 S1 执行报告中，S3 再整理为 eval JSON。

## 8. 下一阶段工作文档

下一阶段工作文档已另行给出：

```text
docs/tw_skills_maintenance/PHASES1_EXISTING_SKILLS_UPDATE_WORK_CN.md
```
