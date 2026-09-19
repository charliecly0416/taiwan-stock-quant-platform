# Phase S1 审查意见：项目内四个 tw-stock-* Skills 更新

生成日期：2026-06-19

## 1. 结论

审查结论：通过，允许进入 Phase S2。

执行者已按 `PHASES1_EXISTING_SKILLS_UPDATE_WORK_V2_CN.md` 更新项目内四个既有台股 skills：

```text
.agents/skills/tw-stock-safety-boundary-review
.agents/skills/tw-stock-readonly-e2e-acceptance
.agents/skills/tw-stock-research-context-analyst
.agents/skills/tw-stock-data-freshness-diagnosis
```

本次更新覆盖了当前项目主线要求：DailyAgentPromptArtifact、Agent simple-chat、前端策略工作台 UI2、readonly Playwright 验收、四类 freshness、英文危险语义与只读安全边界。

允许进入：

```text
Phase S2：新增五个项目 skills
```

## 2. 对照本主文档的符合性

S1 V2 要求：

- 只编辑项目内 `.agents/skills/tw-stock-*`。
- 不编辑归档旧版本。
- 不恢复用户级原路径 `tw-stock-*`。
- 四个 skill 都保留旧能力并补齐新路线。
- description 更准确触发但不过度泛化。
- 准备 trigger / near-miss prompts。
- 运行静态红线扫描并归因。

审查结果：

```text
符合。
```

独立复核显示用户级原路径下不再有同名 `tw-stock-*` skills，只有：

```text
latex-paper-en
pptx
skill-creator
_archived_tw_stock_skills_20260619
```

归档旧版本仍保留在：

```text
/home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/
```

## 3. Findings

### Critical

无。

### High

无。

### Medium

无。

### Low

1. 当前阶段只在执行报告中列出 trigger / near-miss prompts，尚未形成 eval JSON。
   这符合 S1 V2 约定；S3 必须系统化落地到 `docs/tw_skills_maintenance/evals/`。

2. 当前会话的 available skills 元数据可能仍是会话启动时旧状态。
   文件层面项目内版本已是权威版本。后续新会话应加载项目内版本；当前会话审查以文件路径为准。

## 4. Skill 触发与误触发风险

### 4.1 `tw-stock-safety-boundary-review`

审查结论：通过。

已覆盖：

- Agent simple-chat answers。
- DailyAgentPromptArtifact。
- prompt builder / validator。
- Simple Chat OpenAI adapter。
- frontend Agent/workbench text。
- Playwright screenshots、network audit、console audit。
- OpenAI key/base URL/browser-side call 禁止项。
- 英文危险语义：`order`、`place order`、`submit order`、`target_weight`、`target position`、`buy now`、`sell now`、`auto buy`、`auto sell`。
- forged citation 与 qlib score 误解释检查。

触发边界清楚：这是审查 skill，不是研究解释 skill；near-miss 已把“解释 2330 为什么在候选名单里”和“检查 freshness”排除出去。

### 4.2 `tw-stock-readonly-e2e-acceptance`

审查结论：通过。

已覆盖：

- `/tw-stock-monitor` 策略工作台 UI2。
- 今日策略总览、候选名单、历史模拟、模拟账户状态、Agent simple-chat panel。
- readonly strategy snapshot / readonly replay window。
- DailyAgentPromptArtifact dry-run/validator gate。
- desktop/tablet/mobile screenshots。
- network/console/page audit。
- simple-chat 只读主路径 `/api/tw-stock/agent/simple-chat`。
- frontend OpenAI direct request 检查。

触发边界清楚：它负责验收与证据审查，不负责研究解释、模型新增或安全语义单点审查。

### 4.3 `tw-stock-research-context-analyst`

审查结论：通过。

已覆盖：

- current-strategy-context。
- readonly strategy snapshot。
- DailyAgentPromptArtifact summaries。
- paper portfolio gate。
- readonly replay summaries。
- Agent context_digest。
- E4 Qlib + Orthogonal LTR 默认研究口径。
- `candidate_rank`、`score_rank`、`buy_score`、`full_qlib_rank` 的研究排序语义。
- 缺证据时必须说“当前证据不足”。
- 买卖问题转为研究解释，不给交易动作。

触发边界清楚：它解释策略/候选/排名/个股在榜原因，不做 diff 安全审查或 Playwright 验收。

### 4.4 `tw-stock-data-freshness-diagnosis`

审查结论：通过。

已覆盖四类 latest：

```text
provider raw/latest
qlib accepted latest
readonly strategy snapshot latest
Agent DailyAgentPromptArtifact latest
```

已说明：

- Agent prompt latest 落后不等于 provider/qlib 数据落后。
- prompt lag 可能来自 builder 未运行、validator 未通过、latest pointer 未更新、artifact 未发布或 source mismatch。
- stale snapshot/prompt 对今日策略总览、候选名单、历史模拟、模拟账户 gate、Agent simple-chat 的下游影响。

触发边界清楚：它只做 freshness 诊断，不做策略新增、安全审查或 Playwright 验收。

## 5. 只读/安全边界审查

S1 只修改项目内 skills 文本与 references。

未修改：

```text
backend/
frontend/
scripts/
configs/
examples/
qlib/
data_tw/
/home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/**
```

未触发：

```text
真实数据拉取
provider refresh / publish
accepted latest switch
monitor config / scan / alerts 写入
broker / quick-trade / order
target position / target weight 写入
OpenAI 调用或 key 读取
skill eval
```

静态红线扫描命中均属于：

- Forbidden Actions。
- deny-list。
- pass/fail criteria。
- Stop Conditions。
- safety review rules。
- simple-chat payload 禁止字段说明。

未发现鼓励执行真实动作、真实下单、provider publish、accepted latest switch、broker/quick-trade/order、target_position/target_weight 或 OpenAI key 暴露的语境。

## 6. 文档与测试充分性

执行报告包含：

- 四个 descriptions 的变化。
- 新增覆盖点。
- 保留旧能力说明。
- trigger / near-miss prompts。
- 静态红线扫描与归因。
- 用户级原路径无同名 `tw-stock-*` skills 确认。

充分满足 S1。

S3 仍需将 prompts 正式整理为 eval JSON，并检查 skill 间职责重叠。

## 7. 必修项

进入 S2 时必须遵守：

1. 只在项目内新增五个 skills：

```text
.agents/skills/tw-stock-new-model-onboarding
.agents/skills/tw-stock-new-strategy-onboarding
.agents/skills/tw-stock-modular-integration-regression
.agents/skills/tw-stock-agent-daily-prompt-maintenance
.agents/skills/tw-stock-frontend-workbench-ux-review
```

2. 不恢复用户级 `/home/chuliyang/.agents/skills/tw-stock-*` 原路径。

3. 不编辑归档旧版本。

4. 不修改业务、前端、模型、策略代码。

5. 每个新增 skill 必须包含：

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

6. 新增 skill 的 description 必须与 S1 四个旧 skill 边界清晰，避免触发混乱。

## 8. 下一阶段工作文档

下一阶段工作文档：

```text
docs/tw_skills_maintenance/PHASES2_NEW_SKILLS_WORK_CN.md
```
