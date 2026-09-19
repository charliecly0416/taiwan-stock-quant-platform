# Phase S2 执行报告：新增五个项目级 tw-stock Skills

生成日期：2026-06-19

## 1. 本阶段目标

按 `docs/tw_skills_maintenance/PHASES2_NEW_SKILLS_WORK_CN.md` 在项目内新增五个台股项目级 skills：

```text
tw-stock-new-model-onboarding
tw-stock-new-strategy-onboarding
tw-stock-modular-integration-regression
tw-stock-agent-daily-prompt-maintenance
tw-stock-frontend-workbench-ux-review
```

目标是让后续新模型、新策略、模块集成、Agent prompt 维护和前端策略工作台 UX 审查都有明确触发边界与只读安全约束。

## 2. 新增文件

新增：

```text
.agents/skills/tw-stock-new-model-onboarding/SKILL.md
.agents/skills/tw-stock-new-strategy-onboarding/SKILL.md
.agents/skills/tw-stock-modular-integration-regression/SKILL.md
.agents/skills/tw-stock-agent-daily-prompt-maintenance/SKILL.md
.agents/skills/tw-stock-frontend-workbench-ux-review/SKILL.md
```

本阶段未新增 scripts，未新增 references。五个新增 skill 的要求均写入各自 `SKILL.md`。

## 3. 五个新 skills 的 name/description

### 3.1 `tw-stock-new-model-onboarding`

```text
Use this skill whenever the user asks to add, train, evaluate, review, or onboard a new Taiwan stock model, including new qlib/LTR/ensemble models, OOS evaluation, ModelSignalArtifact generation, model adapter work, registry entry creation, golden samples, validators, or a new model reviewer checklist. This skill keeps new models inside the modular contract path and must not default-switch production models, change frontend defaults, publish providers, switch accepted latest, trigger broker/order/quick-trade, or promise returns/win rates without validated OOS evidence.
```

### 3.2 `tw-stock-new-strategy-onboarding`

```text
Use this skill whenever the user asks to add, modify, review, or onboard a Taiwan stock strategy rule, strategy dependency YAML, rebalance rule, candidate filter, OrderIntentArtifact generation, readonly replay rule, replay evidence, or new strategy reviewer checklist. This skill keeps strategies contract-first and simulation/readonly-only; it must not produce real orders, broker/quick-trade actions, target_position/target_weight instructions, future-data leakage, provider publish, accepted latest switching, or default production strategy changes.
```

### 3.3 `tw-stock-modular-integration-regression`

```text
Use this skill whenever the user asks to run or review Taiwan stock module integration, end-to-end readonly regression, model-to-strategy-to-Agent linkage, artifact registry/validator consistency, release readiness, or pre-merge/onboarding integration across DataSourceSnapshot, FeatureArtifact, ModelSignalArtifact, StrategyRule, OrderIntentArtifact, ReplayResult, ReadonlyStrategySnapshot, DailyAgentPromptArtifact, Backend API, Frontend Strategy Workbench, and Playwright network/console/screenshots. This skill uses only validators, fixtures, dry-runs, read-only GETs, static checks, and readonly Playwright; it must stop at missing artifacts and must not use dynamic payloads to fake an artifact chain.
```

### 3.4 `tw-stock-agent-daily-prompt-maintenance`

```text
Use this skill whenever the user asks to modify, debug, review, or maintain the Taiwan stock Agent DailyAgentPromptArtifact route, prompt builder, prompt validator, simple-chat service, OpenAI adapter, Agent answer quality, citations, blocked buy/sell questions, today's strategy Q&A, or why the Agent is not answering accurately. This skill keeps the Agent on the DailyAgentPromptArtifact + backend /api/tw-stock/agent/simple-chat path and must not reintroduce complex tool Agents, frontend OpenAI calls, OpenAI key exposure, trading advice, monitor writes, provider publish, accepted latest switching, broker, quick-trade, orders, target positions, or target weights.
```

### 3.5 `tw-stock-frontend-workbench-ux-review`

```text
Use this skill whenever the user asks to optimize, design, review, or debug the Taiwan stock /tw-stock-monitor strategy workbench UI, frontend strategy workbench UX, Agent panel experience, responsive layout, text overlap, blank panels, Playwright screenshots, desktop/tablet/mobile visual evidence, network audit, console audit, or UI2 acceptance from a product/UX perspective. This skill must use .agents/skills/frontend-design/SKILL.md and keep the UI quiet, precise, research-workbench oriented, readonly, and free of broker, quick-trade, real order, target position, OpenAI key, browser-side OpenAI, monitor writes, provider publish, or accepted latest triggers.
```

## 4. 五个新 skills 的边界与触发场景

### 4.1 新模型接入

触发：新增/训练/评估/接入 qlib、LTR、ensemble、新模型 registry、ModelSignalArtifact、OOS、validator、golden sample。

边界：必须进入 `ModelSignalArtifact` 或 extension schema；不得默认切生产模型、不得改前端默认策略、不得 provider publish、不得切 accepted latest、不得 broker/order、不得收益/胜率承诺。

### 4.2 新策略接入

触发：新增策略、改策略规则、组合策略、rebalance、OrderIntent、readonly replay、新策略 checklist。

边界：先 dependency YAML/rule registry，再实现；策略输出只能是 `OrderIntentArtifact` 或 readonly replay artifact；禁止未来数据、真实订单、target position/weight、默认生产策略切换。

### 4.3 模块化集成回归

触发：模块联调、全链路 readonly regression、模型到策略到 Agent 链路、registry/validator 一致性、上线前集成验收。

边界：只允许 validators、fixtures、dry-run、read-only GET、静态检查、readonly Playwright；缺 artifact 必须停在缺口报告，不得用动态 payload 伪造链路。

### 4.4 Agent Daily Prompt 维护

触发：修改 Agent prompt、simple-chat、DailyAgentPromptArtifact validator、OpenAI adapter、Agent 回答质量、citation、blocked intent、今天策略问答。

边界：Agent 固定走 `DailyAgentPromptArtifact -> backend simple-chat`；OpenAI 只能后端消费 artifact 和用户问题；不得前端 OpenAI、不得 key 泄露、不得复杂工具 Agent、不得交易建议。

### 4.5 前端工作台 UX 审查

触发：优化/审查 `/tw-stock-monitor`、策略工作台 UX、Agent panel、响应式、重叠/空白、Playwright 截图、network/console audit。

边界：必须读取 `.agents/skills/frontend-design/SKILL.md`；设计方向是安静、精确、研究工作台；不得营销页、大 hero、装饰背景、交易入口、OpenAI 前端直连或真实仓位建议。

## 5. 与 S1 四个既有 skills 的分工

- `tw-stock-safety-boundary-review`：审查安全边界与危险语义；S2 的 Agent/前端/集成 skills 遇到安全审查时应配合它，但不替代它。
- `tw-stock-readonly-e2e-acceptance`：运行或审查只读 E2E/Playwright 验收；`tw-stock-frontend-workbench-ux-review` 聚焦 UX 设计与页面体验，验收证据可交给 E2E skill。
- `tw-stock-research-context-analyst`：解释今日策略、候选、排名和个股研究上下文；新模型/新策略 skill 不负责回答“能不能买”。
- `tw-stock-data-freshness-diagnosis`：诊断四类 latest 和 stale 原因；Agent maintenance 和 frontend UX skill 只引用其结论，不触发数据刷新。
- `tw-stock-new-model-onboarding`：只管模型合同、PIT、OOS、ModelSignalArtifact、registry、validator。
- `tw-stock-new-strategy-onboarding`：只管策略 dependency、OrderIntent、readonly replay、validator。
- `tw-stock-modular-integration-regression`：跨模块只读联调，遇到单模块新模型/新策略应交给对应 onboarding skill。
- `tw-stock-agent-daily-prompt-maintenance`：维护 Agent prompt/simple-chat/OpenAI adapter 路线，不做 general safety review 或 freshness diagnosis。
- `tw-stock-frontend-workbench-ux-review`：维护策略工作台 UX，必须结合 frontend-design，但不做业务模型/策略实现。

## 6. Read First 覆盖情况

- 新模型 skill 要求读取：项目宪法、新模型与新策略手册、ModelSignal 合同、Extension schema、NEW_MODEL_REVIEWER_CHECKLIST。
- 新策略 skill 要求读取：StrategyRule、OrderIntent、ReplayResult、TW_NEW_STRATEGY_ONBOARDING_TEMPLATE、NEW_STRATEGY_REVIEWER_CHECKLIST。
- 集成回归 skill 要求读取：项目宪法、未来开发规范、ModelSignal、StrategyRule、OrderIntent、ReplayResult、DailyAgentPromptArtifact 合同，并按需读取 S1 skills。
- Agent maintenance skill 要求读取：Agent OpenAI 重构设计、DailyAgentPromptArtifact 合同、Phase0-6 总结。
- 前端 UX skill 要求读取：`.agents/skills/frontend-design/SKILL.md` 和相关 UI 文档。

已确认这些必读合同/checklist 文件存在。

## 7. Allowed / Forbidden Actions 覆盖情况

五个新增 skills 均包含 `Allowed Actions / Evidence` 与 `Forbidden Actions`。

共同禁止：

```text
真实数据拉取
provider refresh / publish
accepted latest switch
monitor config / scan / alerts 写入
broker / quick-trade / order
target position / target weight 写入
OpenAI key 泄露或前端 OpenAI 调用
默认切换生产模型/策略
```

各自允许范围限定为合同读取、artifact/manifest 检查、validator、fixtures、dry-run、readonly GET、静态检查、readonly Playwright 或项目内 skill 文档工作。

## 8. 输出格式覆盖情况

五个新增 skills 均包含 `Output Format`：

- 新模型：`# 新模型接入工作报告`
- 新策略：`# 新策略接入工作报告`
- 集成回归：`# 台股模块化只读集成回归报告`
- Agent maintenance：`# 台股 Agent Daily Prompt 维护报告`
- 前端 UX：`# 台股策略工作台 UX 审查 / 执行报告`

## 9. Trigger Examples 与 Stop Conditions

五个新增 skills 均包含：

```text
Trigger Examples
Stop Conditions
```

Trigger examples 均包含 should_trigger 与 should_not_trigger，Stop Conditions 均覆盖真实数据、provider/accepted latest、monitor 写入、broker/order/quick-trade、target position/weight、OpenAI key/调用、生产默认切换等停止条件。

## 10. 静态红线扫描结果与归因

执行：

```bash
rg -n "provider publish|accepted latest switch|quick-trade|broker|submit order|place order|target_position|target_weight|OpenAI API key|OPENAI_API_KEY|browser-side OpenAI" .agents/skills/tw-stock-*
```

结果：有命中，均为允许语境。

归因：

- S1 旧 skills 的命中位于 Forbidden Actions、Stop Conditions、deny-list、readonly boundary、network audit rules、安全报告模板或既有静态脚本中。
- `tw-stock-new-model-onboarding` 命中位于 description、Forbidden Actions、Stop Conditions，用于禁止默认切生产模型、provider publish、accepted latest switch、broker/order/quick-trade、target_position/target_weight。
- `tw-stock-new-strategy-onboarding` 命中位于 description、Forbidden Actions、Workflow、Stop Conditions，用于禁止真实订单、target_position/target_weight、provider publish、accepted latest switch。
- `tw-stock-modular-integration-regression` 命中位于 Forbidden Actions、Stop Conditions，用于只读集成回归边界。
- `tw-stock-agent-daily-prompt-maintenance` 命中位于 description、Forbidden Actions、Trigger Examples、Stop Conditions，用于保持 backend simple-chat 与禁用前端 OpenAI/交易动作。
- `tw-stock-frontend-workbench-ux-review` 命中位于 description、Forbidden Actions、Workflow、Stop Conditions，用于禁止交易入口、OpenAI key、browser-side OpenAI、provider/accepted latest/monitor 写入。

未发现任何鼓励执行真实动作的命中。

## 11. 九个 tw-stock-* skills 清单

执行：

```bash
find .agents/skills/tw-stock-* -maxdepth 2 -name SKILL.md -print | sort
```

结果共九个：

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

用户级原路径检查：

```bash
find /home/chuliyang/.agents/skills -maxdepth 1 -type d -name 'tw-stock-*' -print | sort
```

结果为空，确认用户级原路径没有同名 `tw-stock-*` skills。

## 12. 未修改范围确认

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
/home/chuliyang/.agents/skills/tw-stock-* 原路径
```

未执行或触发：

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
skill eval
```

## 13. 未解决问题

无阻塞问题。

说明：本阶段未创建 eval JSON，S3 将为九个台股 skills 建立测试集和触发边界验证。

## 14. 是否建议进入 S3

建议进入 S3。

理由：五个新增 skills 已按 S2 文档落在 `.agents/skills/`，结构完整，触发边界与 S1 四个既有 skills 可区分，静态红线扫描命中均为禁止/边界语境，用户级原路径无同名冲突。
