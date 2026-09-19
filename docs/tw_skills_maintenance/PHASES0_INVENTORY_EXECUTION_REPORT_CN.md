# Phase S0 执行报告

生成日期：2026-06-19

## 1. 本阶段目标

按 `docs/tw_skills_maintenance/TW_SKILLS_MAINTENANCE_BRANCH_WORK_CN.md` 执行 Phase S0：Inventory 与落点确认。

本阶段只做：

- 清点 repo 内 `.agents/skills` 与用户级 `/home/chuliyang/.agents/skills` 的 skill。
- 判断当前运行时加载来源。
- 读取四个既有 `tw-stock-*` skills、`frontend-design`、`skill-creator` 与主线必读上下文。
- 识别四个旧台股 skills 的过期点。
- 给出后续新增/修改 skills 的落点建议。

本阶段未修改任何既有 skill，未新增 skill 目录，未删除或移动旧 skill。

## 2. 已阅读文档

### 2.1 Skill 维护主文档

- `docs/tw_skills_maintenance/TW_SKILLS_MAINTENANCE_BRANCH_WORK_CN.md`

### 2.2 Skill 创建规范

- `/home/chuliyang/.agents/skills/skill-creator/SKILL.md`

### 2.3 已有 skills

- `.agents/skills/frontend-design/SKILL.md`
- `/home/chuliyang/.agents/skills/tw-stock-readonly-e2e-acceptance/SKILL.md`
- `/home/chuliyang/.agents/skills/tw-stock-readonly-e2e-acceptance/references/readonly-boundary.md`
- `/home/chuliyang/.agents/skills/tw-stock-readonly-e2e-acceptance/references/acceptance-report-template.md`
- `/home/chuliyang/.agents/skills/tw-stock-research-context-analyst/SKILL.md`
- `/home/chuliyang/.agents/skills/tw-stock-research-context-analyst/references/qlib-cross-analysis-semantics.md`
- `/home/chuliyang/.agents/skills/tw-stock-research-context-analyst/references/research-report-template.md`
- `/home/chuliyang/.agents/skills/tw-stock-data-freshness-diagnosis/SKILL.md`
- `/home/chuliyang/.agents/skills/tw-stock-data-freshness-diagnosis/references/data-source-boundary.md`
- `/home/chuliyang/.agents/skills/tw-stock-data-freshness-diagnosis/references/freshness-status-fields.md`
- `/home/chuliyang/.agents/skills/tw-stock-safety-boundary-review/SKILL.md`
- `/home/chuliyang/.agents/skills/tw-stock-safety-boundary-review/references/forbidden-actions.md`
- `/home/chuliyang/.agents/skills/tw-stock-safety-boundary-review/references/network-audit-rules.md`

### 2.4 项目必读上下文

- `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`
- `docs/tw_modular_contracts/TW_MODULAR_PIPELINE_FUTURE_DEVELOPMENT_GUIDE_CN.md`
- `docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md`
- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_OPENAI_REBUILD_DESIGN_CN.md`
- `docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md`
- `docs/tw_agent_daily_prompt_rebuild/PHASE0_TO_PHASE6_FINAL_SUMMARY_CN.md`
- `docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_OPTIMIZATION_PLAN_CN.md`

## 3. 修改/新增文件

新增本执行报告：

- `docs/tw_skills_maintenance/PHASES0_INVENTORY_EXECUTION_REPORT_CN.md`

未修改：

- `.agents/skills/**`
- `/home/chuliyang/.agents/skills/**`
- 任何台股业务代码、前端代码、模型/策略代码或测试代码

## 4. Skill 清单

### 4.1 Repo 内 `.agents/skills`

当前仓库内只有一个 skill：

```text
.agents/skills/frontend-design/SKILL.md
```

判断：

- repo 内暂无 `tw-stock-*` 项目 skills。
- `frontend-design` 已作为项目内 skill 暴露给当前运行时。
- 该 skill 是前端视觉/UX 方法，不是台股业务安全或 artifact 合同 skill。

### 4.2 用户级 `/home/chuliyang/.agents/skills`

当前用户级 skills：

```text
/home/chuliyang/.agents/skills/pptx/SKILL.md
/home/chuliyang/.agents/skills/tw-stock-readonly-e2e-acceptance/SKILL.md
/home/chuliyang/.agents/skills/tw-stock-research-context-analyst/SKILL.md
/home/chuliyang/.agents/skills/tw-stock-data-freshness-diagnosis/SKILL.md
/home/chuliyang/.agents/skills/skill-creator/SKILL.md
/home/chuliyang/.agents/skills/latex-paper-en/SKILL.md
/home/chuliyang/.agents/skills/tw-stock-safety-boundary-review/SKILL.md
```

其中台股相关既有 skills：

```text
tw-stock-readonly-e2e-acceptance
tw-stock-research-context-analyst
tw-stock-data-freshness-diagnosis
tw-stock-safety-boundary-review
```

判断：

- 四个既有台股 skills 目前只存在于用户级目录。
- repo 内没有这些 skills 的版本化副本。
- 本阶段未发现 repo 内与用户级同名 `tw-stock-*` skill 冲突。

### 4.3 系统级 `/home/chuliyang/.codex/skills`

读取清单时还观察到系统级/其他用户 skills，例如：

```text
/home/chuliyang/.codex/skills/.system/imagegen/SKILL.md
/home/chuliyang/.codex/skills/.system/skill-creator/SKILL.md
/home/chuliyang/.codex/skills/.system/openai-docs/SKILL.md
/home/chuliyang/.codex/skills/academic-paper-reviewer/SKILL.md
...
```

这些不是本分支台股 skills 维护目标，仅记录为运行时背景。

## 5. 运行时加载位置判断

根据本会话启动时的 available skills 列表，当前运行时至少加载了：

- repo 内 skill：`frontend-design`，路径为 `.agents/skills/frontend-design/SKILL.md`。
- 用户级 skills：四个 `tw-stock-*` skills，路径为 `/home/chuliyang/.agents/skills/...`。
- 用户级 `skill-creator` 与其他非台股 skills。
- 系统级 `.codex/skills/.system/*`。

可信判断：

```text
当前运行时会同时暴露 repo 内 .agents/skills 与用户级 /home/chuliyang/.agents/skills。
```

不能严格确认的点：

```text
如果未来 repo 内和用户级出现同名 skill，当前证据不能证明二者的优先级、覆盖顺序或冲突处理规则。
```

因此，S0 不建议直接双写或覆盖用户级 skills。后续如果要从 repo 内同步到用户级，应由统筹明确同步策略，或先通过审查确认同名优先级。

## 6. 关键设计决定

### 6.1 推荐落点方案

推荐方案：

```text
方案 A：以 repo 内 .agents/skills/tw-stock-* 作为后续新增和修改的主落点，完成审查后再由统筹决定是否同步到用户级 /home/chuliyang/.agents/skills。
```

理由：

- repo 内 skills 可版本化、可 review、可和项目合同/报告一起提交。
- 当前用户级四个 `tw-stock-*` skills 已过期，但仍是运行时当前可触发版本；直接覆盖会影响后续节点行为，风险较高。
- 当前运行时已经能加载 repo 内 `.agents/skills/frontend-design`，说明 repo 内 skill 具备被暴露的基础。
- 同名优先级未知，先在 repo 内落地再审查，可避免未经确认覆盖用户级生产使用版本。

不推荐在 S1/S2 默认直接执行：

```text
repo 内和用户级双写
直接覆盖 /home/chuliyang/.agents/skills/tw-stock-*
删除或移动旧用户级 skills
```

### 6.2 是否需要统筹确认

需要统筹确认两点：

1. 后续是否接受“repo 内为准，用户级后续同步”的策略。
2. 如果 repo 内与用户级出现同名 `tw-stock-*` skills，运行时触发应以哪个版本为准，以及是否允许审查通过后同步覆盖用户级版本。

在未确认前，建议 Phase S1 的修改目标限定为 repo 内版本化副本，或由审查者在 S0 Review 中明确允许的落点。

## 7. 当前四个 `tw-stock-*` skills 的过期点

### 7.1 `tw-stock-safety-boundary-review`

当前能力：

- 能审查 diff、network audit、console audit、Agent 文本、前端文本、后端片段。
- 能识别 broker、quick-trade、orders、target positions、monitor 写入、provider publish/refresh、accepted latest、危险买卖语义。

过期点：

- 未覆盖 `DailyAgentPromptArtifact`、prompt builder、prompt validator、OpenAI adapter、simple-chat 后端服务。
- 未明确 `POST /api/tw-stock/agent/simple-chat` 是允许的只读解释接口。
- 未覆盖前端禁止 OpenAI key、OpenAI base URL、browser-side OpenAI call。
- 英文危险语义不完整；工作文档要求补 `order`、`place order`、`submit order`、`target_weight`、`target position`、`buy now`、`sell now`。
- 未加入 Agent answer 的 forged citation 检查。
- 未明确 qlib score 不能解释为收益率、胜率、上涨概率或买入概率。
- 未纳入 UI2 策略工作台 UX、Playwright 截图/network/console artifacts 的审查项。

### 7.2 `tw-stock-readonly-e2e-acceptance`

当前能力：

- 覆盖旧 full-scenario readonly E2E。
- 检查 summary/network/console artifact、watchlist refill、chart nonblank、frontend build。
- 保留只读边界，禁止真实数据刷新、provider publish、accepted latest switch、monitor 写入、broker/order。

过期点：

- 验收范围仍偏旧 Step1-Step5，不覆盖 UI2 后的 `/tw-stock-monitor` 策略工作台 UX。
- 未纳入 `readonly strategy snapshot`、`readonly replay window`、`paper portfolio`、Agent `simple-chat` panel 的工作台级验收。
- 未要求 desktop/tablet/mobile 三视口截图与文字重叠/主要面板非空/表格可读检查。
- 未检查前端主路径只能调用 `/api/tw-stock/agent/simple-chat`，不能回退旧 `/agent/chat`。
- 未覆盖前端 OpenAI key/base URL/browser-side OpenAI 请求检查。
- 未纳入 `DailyAgentPromptArtifact` dry-run/validator gate。
- 通过标准未包含 `simple_chat_request_count`、`frontend_openai_direct_request_count`、`broker_quick_trade_order_request_count` 等新审计指标。

### 7.3 `tw-stock-research-context-analyst`

当前能力：

- 解释 qlib accepted latest、TopN/Top30、trend、cross-analysis、monitor history、kline 与 Agent context。
- 将买卖问题转为研究上下文。
- 强调 qlib_score 只是横截面研究排序分数。

过期点：

- 证据源仍以 qlib accepted latest/cross-analysis/旧 Agent context 为主，未纳入 `current-strategy-context`、`readonly-strategy-snapshot`、DailyAgentPromptArtifact 摘要、paper portfolio gate、replay result summary。
- 未明确当前默认研究口径：`E4 Qlib + Orthogonal LTR`，且 LTR 只在 qlib top50 内重排买入顺序。
- 未要求回答引用 artifact id/checksum、snapshot id、strategy rule、candidate_rank、buy_score、full_qlib_rank 等可追溯字段。
- 对“今天策略是什么、排名第一是谁、为什么在榜、要不要买卖”的新工作台问法覆盖不足。
- 缺证据时“不臆造今日结论”的要求需要加强。

### 7.4 `tw-stock-data-freshness-diagnosis`

当前能力：

- 诊断 daily auto-update status、FinMind/raw、Yahoo/Scrapling qlib、accepted latest、pending_asof、fresh_data_wait 与 retry。
- 严格只读，不触发真实拉数、provider publish、accepted latest switch、POST/PUT/PATCH/DELETE。

过期点：

- 只区分 daily status/latest signals/FinMind/raw/qlib，不区分四类 latest：
  - provider raw/latest
  - qlib accepted latest
  - readonly strategy snapshot latest
  - Agent DailyAgentPromptArtifact latest
- 未说明 Agent prompt latest 落后不等于 provider/qlib 落后，可能只是 prompt builder 未运行或 validator 未通过。
- 未纳入只读检查 artifact manifest/latest pointer 的建议。
- 输出缺少“下游影响”：stale prompt 或 stale snapshot 会影响哪些页面/Agent 回答。
- 未覆盖 UI2 工作台和 simple-chat 对 snapshot/prompt freshness 的依赖关系。

## 8. Skill 触发边界

S0 暂未修改 descriptions，只记录后续边界建议：

- `tw-stock-safety-boundary-review`：应触发于代码 diff、Agent 回答、DailyAgentPromptArtifact、simple-chat、前端文本、Playwright network/console/screenshot 只读安全审查；不应触发为一般研究解读。
- `tw-stock-readonly-e2e-acceptance`：应触发于 `/tw-stock-monitor` 只读验收、Playwright UX/network/console artifact 验收、最终接受判断；不应触发真实数据刷新或运维执行。
- `tw-stock-research-context-analyst`：应触发于 qlib/LTR/候选/排名/个股为什么在榜/今日策略是什么等研究解释；不应触发为交易建议、目标仓位或实盘操作。
- `tw-stock-data-freshness-diagnosis`：应触发于 latest/asof/pending/retry/stale/prompt latest/snapshot latest 诊断；不应触发真实拉数、publish 或 accepted latest 切换。

## 9. 只读/安全边界确认

本阶段只执行读取、清单和报告写入。

未触发：

- 真实 Yahoo/FinMind 数据拉取。
- qlib provider refresh / publish。
- provider accepted latest 或 qlib accepted latest 切换。
- monitor config / scan / alerts 写入。
- broker / quick-trade / order。
- target position / target weight。
- OpenAI 调用或 key 读取。
- 前端构建、Playwright、后端服务启动或业务测试。

## 10. 测试或静态检查

本阶段执行的命令类型：

- `find .agents/skills -maxdepth 2 -name SKILL.md -print`
- `find /home/chuliyang/.agents/skills -maxdepth 2 -name SKILL.md -print`
- `find /home/chuliyang/.codex/skills -maxdepth 3 -name SKILL.md -print`
- `sed -n ...` 读取主文档、合同文档、skill 文件和 references。
- `rg -n ...` 检索 DailyAgentPromptArtifact、simple-chat、OpenAI、readonly、ModelSignalArtifact、StrategyRule、OrderIntent、ReplayResult、UI2、provider/accepted latest、broker/quick-trade 等关键语义。
- `wc -l ...` 统计必读文档规模。

注意：

- 曾尝试对 repo 内与用户级路径同时执行 `git status --short docs/tw_skills_maintenance .agents/skills /home/chuliyang/.agents/skills`，Git 返回用户级目录在仓库外，无法一起检查。这不影响 S0 清单判断；用户级目录仅作为读取对象。

## 11. 未解决问题

1. 同名 skill 的运行时优先级未被严格证明。当前只能确认 repo 内和用户级 skills 都会暴露，不能确认同名冲突时的选择规则。
2. 后续是否把修改后的台股 skills 同步到 `/home/chuliyang/.agents/skills` 需要统筹确认。
3. 当前四个用户级 `tw-stock-*` skills 仍是运行时已暴露版本；在 repo 内新增同名版本前，应确认是否会产生误触发或版本歧义。

## 12. 给审查者的重点

请重点审查：

- 本报告的 repo 内与用户级 skill 清单是否完整。
- “当前运行时同时加载 repo 内和用户级 skills，但同名优先级未知”的判断是否成立。
- 推荐“repo 内为准，审查后再同步用户级”的方案是否符合可版本化、可触发、可维护原则。
- 四个旧 `tw-stock-*` skills 的过期点是否覆盖 Agent simple-chat、DailyAgentPromptArtifact、UI2、modular contracts、只读边界和英文 dangerous terms。
- S0 是否遵守“只做清单/读取/落点建议，不修改 skill、不新增 skill 目录、不删除或移动旧 skill”的限制。
