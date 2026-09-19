# 台股项目 Skills 维护与新增分支工作文档

## 0. 分支目标

本分支只处理 Codex/Agent skills 的维护、迁移、新增、测试与审查，不修改台股业务代码、不改前端产品代码、不改模型策略默认行为。

目标是让后续开发、维护、调试、测试节点在进入台股项目时，能够通过专用 skills 自动遵守当前项目的核心路线：

```text
模块化合同与项目宪法
-> 只读研究边界
-> 新模型/新策略可扩展接入
-> DailyAgentPromptArtifact + simple-chat Agent
-> 前端策略工作台 UX
-> Playwright/readonly 集成验收
```

本分支的交付物不是“更多文档堆叠”，而是一组可被运行时触发、能约束后续节点行为的项目级 skills。

## 1. 必读上下文

执行者和审查者开工前必须阅读：

```text
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/TW_MODULAR_PIPELINE_FUTURE_DEVELOPMENT_GUIDE_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_OPENAI_REBUILD_DESIGN_CN.md
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md
docs/tw_agent_daily_prompt_rebuild/PHASE0_TO_PHASE6_FINAL_SUMMARY_CN.md
docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_OPTIMIZATION_PLAN_CN.md
```

执行者还必须阅读 skill 创建规范：

```text
/home/chuliyang/.agents/skills/skill-creator/SKILL.md
```

如路径在执行环境中不可读，必须停止并向统筹说明，不得凭记忆重写 skills。

## 2. 当前 Skills 状态判断

当前项目内 skill：

```text
.agents/skills/frontend-design/SKILL.md
```

当前用户级台股 skills：

```text
/home/chuliyang/.agents/skills/tw-stock-readonly-e2e-acceptance/SKILL.md
/home/chuliyang/.agents/skills/tw-stock-research-context-analyst/SKILL.md
/home/chuliyang/.agents/skills/tw-stock-data-freshness-diagnosis/SKILL.md
/home/chuliyang/.agents/skills/tw-stock-safety-boundary-review/SKILL.md
```

初步结论：

| Skill | 当前判断 | 处理方式 |
| --- | --- | --- |
| `tw-stock-safety-boundary-review` | 仍必要，但没有覆盖 Agent simple-chat、DailyAgentPromptArtifact、UI2、英文 `order/place order/target_weight` 风险 | 修改 |
| `tw-stock-readonly-e2e-acceptance` | 仍必要，但验收范围停留在旧 Step1-Step5，缺少 simple-chat network、策略工作台 UX、日更 Agent prompt gate | 修改 |
| `tw-stock-research-context-analyst` | 仍必要，但需要纳入 readonly strategy snapshot、DailyAgentPromptArtifact、当前 E4 Qlib + Orthogonal LTR 语义 | 修改 |
| `tw-stock-data-freshness-diagnosis` | 基本有效，但需要区分 provider/qlib accepted latest、readonly strategy snapshot latest、Agent prompt latest | 小改 |
| `frontend-design` | 已适合辅助前端优化，但不是台股业务 skill | 保留，不改；新前端 skill 应引用它 |

## 3. Skill 存放位置决策

执行者 Phase S0 必须先确认运行时加载优先级，再决定实际落点。

推荐策略：

1. 新增和修改后的台股项目 skills 优先放入 repo 内：

```text
.agents/skills/tw-stock-*/SKILL.md
```

2. 如果当前运行时只加载用户级 `/home/chuliyang/.agents/skills`，执行者不得直接双写两个位置。应在报告中说明验证结果，并请求统筹决定：

```text
方案 A：只在 repo 内创建，后续由统筹安装/同步到用户级 skills。
方案 B：先在 repo 内创建，再经明确批准同步到用户级 skills。
方案 C：继续只维护用户级 skills，但在 repo 文档中保留版本快照和变更说明。
```

3. 本分支默认不删除旧用户级 skills。迁移完成前，旧 skills 只能作为兼容保留。

## 4. 必须修改的既有 Skills

### 4.1 `tw-stock-safety-boundary-review`

必须补充：

- 审查对象加入：`DailyAgentPromptArtifact`、prompt builder、prompt validator、`POST /api/tw-stock/agent/simple-chat`、Simple Chat OpenAI adapter、前端 Agent panel、策略工作台 UX、Playwright network/console artifacts。
- 明确前端不得出现 OpenAI API key、OpenAI base URL、browser-side OpenAI call。
- 明确 `/api/tw-stock/agent/simple-chat` 是允许的只读后端解释接口。
- 加入英文危险语义：`order`、`place order`、`submit order`、`target_weight`、`target position`、`buy now`、`sell now`。必须区分拒答、disclaimer、只读回测术语和真实行动指令。
- 加入 Agent answer 检查：不得伪造 citation，不得把 qlib score 解释为收益率、胜率、上涨概率或买入概率。
- 加入 UI 文案检查：允许“观察优先级/人工复盘/研究排序”，避免“该买/该卖/仓位建议”。

### 4.2 `tw-stock-readonly-e2e-acceptance`

必须补充：

- 验收范围加入 `/tw-stock-monitor` 策略工作台 UX、Agent simple-chat panel、readonly strategy snapshot、readonly replay window。
- 增加 simple-chat 静态/网络检查：前端主路径只能调用 `/api/tw-stock/agent/simple-chat`，不能调用旧 `/agent/chat` 作为主路径，不能暴露 OpenAI key。
- 增加 Playwright 截图要求：desktop/tablet/mobile 至少各一张；检查文字不重叠、主要面板不空白、图表/表格可读。
- 增加 DailyAgentPromptArtifact 构建 gate：只允许 dry-run/read-only 构建和 validator；不得触发 provider publish、accepted latest switch 或真实数据拉取。
- 更新通过标准，把 `forbidden_request_count=0` 扩展到 Agent simple-chat、monitor write、provider/accepted latest、broker/order/quick-trade。

### 4.3 `tw-stock-research-context-analyst`

必须补充：

- 允许证据加入只读策略上下文：`current-strategy-context`、`readonly-strategy-snapshot`、DailyAgentPromptArtifact 摘要、paper portfolio gate、replay result summary。
- 明确当前默认研究口径：E4 Qlib + Orthogonal LTR 排序语义；`candidate_rank/buy_score/full_qlib_rank` 只能作为研究排序，不是收益/概率。
- 用户问“今天策略是什么、排名第一是谁、为什么在榜、要不要买卖”时，统一转换为：今日只读研究策略、候选观察、风险与数据口径，不给交易动作。
- 回答必须引用可追溯字段：asof、run_id、artifact id/checksum、rank、score、strategy rule、snapshot id。
- 缺证据时必须说“当前证据不足”，不得臆造今日结论。

### 4.4 `tw-stock-data-freshness-diagnosis`

必须补充：

- 区分四类 latest：provider raw/latest、qlib accepted latest、readonly strategy snapshot latest、Agent DailyAgentPromptArtifact latest。
- 明确 Agent prompt latest 落后不等于 provider/qlib 数据落后；它可能只是 prompt 构建未运行或 validator 未通过。
- 增加只读检查 artifact manifest/latest pointer 的建议，但不得触发构建、刷新、发布或切换。
- 输出中增加“下游影响”：哪些页面/Agent 回答会受 stale prompt 或 stale snapshot 影响。

## 5. 必须新增的 Skills

### 5.1 `tw-stock-new-model-onboarding`

用途：后续新增、训练、评估、接入台股新模型时触发。

触发场景：

```text
新增模型
训练一个新模型
接入新的 qlib/ltr/ensemble 模型
生成 ModelSignalArtifact
评估模型 OOS
把新模型加入 registry
```

必须约束：

- 先读项目宪法、新模型指南、`MODEL_SIGNAL_CONTRACT_CN.md`、`MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md`、`NEW_MODEL_REVIEWER_CHECKLIST_CN.md`。
- 新模型输出必须进入 `ModelSignalArtifact` 或兼容 extension schema。
- 必须有 point-in-time、`available_at`、OOS 区间、数据泄漏检查、registry entry、validator、golden sample。
- 不得默认切换生产模型，不得改前端默认策略，不得发布 provider，不得切 accepted latest，不得触发 broker/order。
- 任何“收益更高”“胜率更高”必须绑定已验证 OOS 报告，不得作为承诺。

建议输出格式：

```markdown
# 新模型接入工作报告
## 1. 范围
## 2. 合同与 registry
## 3. 数据与 PIT
## 4. 训练/评估
## 5. ModelSignalArtifact
## 6. Validator 与测试
## 7. 未接入生产声明
## 8. 风险与下一步
```

### 5.2 `tw-stock-new-strategy-onboarding`

用途：后续新增策略规则、组合策略、候选筛选、再平衡规则、replay 规则时触发。

触发场景：

```text
新增策略
改策略规则
做一个组合策略
接入新的 rebalance 规则
生成 OrderIntent
做 readonly replay
```

必须约束：

- 先读 `STRATEGY_RULE_CONTRACT_CN.md`、`ORDER_INTENT_CONTRACT_CN.md`、`REPLAY_RESULT_CONTRACT_CN.md`、`TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md`、`NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`。
- 策略输出只能是只读 `OrderIntentArtifact` 或 replay artifact，不得产生真实订单。
- 先写 dependency YAML / rule registry，再写实现。
- 禁止使用未来收益、未来价格、未来标签、同日不可得字段。
- 禁止真实 `target_position`、真实 `target_weight`、broker、quick-trade、order submit。
- replay 必须显式标注模拟、历史、只读。

建议输出格式：

```markdown
# 新策略接入工作报告
## 1. 策略目标与非目标
## 2. 依赖与可得性
## 3. StrategyRule
## 4. OrderIntent 只读输出
## 5. Replay 结果
## 6. Validator 与测试
## 7. 未实盘声明
## 8. 风险与下一步
```

### 5.3 `tw-stock-modular-integration-regression`

用途：把各模块串起来做只读集成回归，避免模型、策略、Agent、前端各自通过但链路断裂。

触发场景：

```text
做一次模块联调
验证模型到策略再到 Agent 是否打通
跑全链路 readonly regression
检查 artifact registry 和 validators
上线前集成验收
```

覆盖链路：

```text
DataSourceSnapshot
-> FeatureArtifact
-> ModelSignalArtifact
-> StrategyRule
-> OrderIntentArtifact
-> ReplayResult
-> ReadonlyStrategySnapshot
-> DailyAgentPromptArtifact
-> Backend API
-> Frontend Strategy Workbench
-> Playwright network/console/screenshots
```

必须约束：

- 默认只运行 validators、fixtures、dry-run、read-only GET、静态检查、Playwright 只读访问。
- 不触发真实数据拉取、provider publish、accepted latest switch、monitor config save、monitor scan、alerts write、broker/order。
- 报告必须列出每个 artifact 的 asof、run_id、checksum/latest pointer、validator 结果。
- 如果某一环缺 artifact，必须停止在缺口报告，不得用动态服务 payload 假装通过。

### 5.4 `tw-stock-agent-daily-prompt-maintenance`

用途：维护新 Agent 路线，避免后续节点重新走复杂工具 Agent 或绕过 DailyAgentPromptArtifact。

触发场景：

```text
修改 Agent prompt
修改 simple-chat
检查 Agent 回答
DailyAgentPromptArtifact validator
OpenAI adapter
今天的策略问答
Agent 不回答/回答不准
```

必须约束：

- OpenAI 只能消费 `DailyAgentPromptArtifact` 和用户问题。
- 前端只能调用后端 `/api/tw-stock/agent/simple-chat`。
- OpenAI key 只能在后端环境变量，不得进入前端 bundle、测试截图或日志。
- prompt builder/validator 必须保留 forbidden terms、citation、asof/run_id/checksum 校验。
- 用户的买卖问题必须转为研究解释，不给行动建议。
- 修改 Agent 后至少运行 simple-chat unit/static checks 和 safety-boundary review。

### 5.5 `tw-stock-frontend-workbench-ux-review`

用途：维护 `/tw-stock-monitor` 策略工作台 UX，并把 `frontend-design` 的视觉方法和台股只读边界结合起来。

触发场景：

```text
优化前端
审查策略工作台 UI
跑 Playwright 看页面
检查 Agent 面板体验
修 /tw-stock-monitor 重叠/空白/不好用
```

必须约束：

- 使用 `.agents/skills/frontend-design/SKILL.md`，但设计方向必须是安静、精确、研究工作台，不做营销页、大 hero、装饰性背景。
- 必须用 Playwright 证据：desktop/tablet/mobile 截图、network audit、console audit。
- 必须检查：首屏信息层级、今日策略摘要、候选池、replay、Agent simple-chat、数据状态、风险提示。
- 前端不得出现实盘交易入口、broker、quick-trade、真实 order、target position 设置。
- 允许“填入问题并调用 simple-chat”的快捷问题按钮，但按钮不得触发交易或 monitor 写入。

## 6. 不建议新增的 Skills

本分支不新增以下 skills，除非统筹后续明确改主线：

| 不新增项 | 原因 |
| --- | --- |
| `tw-stock-daily-auto-update-operator` | 容易把只读诊断升级成真实拉数、publish、accepted latest 切换；应保留在显式人工授权流程中 |
| `tw-stock-broker-trading-operator` | 当前项目主线是研究与只读策略工作台，不是实盘执行 |
| `tw-stock-provider-publish-runner` | provider publish 和 accepted latest switch 是高风险运维动作，不应由 skill 自动触发 |
| 过细的单模块 debug skills | 会造成触发混乱；模型、策略、Agent、前端、集成五类已经足够覆盖主要开发面 |

## 7. 执行阶段

### Phase S0：Inventory 与落点确认

执行者要做：

1. 列出 repo 内 `.agents/skills` 和用户级 `/home/chuliyang/.agents/skills` 的 skill 清单。
2. 确认运行时是否加载 repo 内 skills、用户级 skills、或两者。
3. 读取四个既有 `tw-stock-*` skills 和 `frontend-design`。
4. 读取本工作文档和必读上下文。
5. 给出落点建议：repo 内、用户级、或 repo 内为准并后续同步。

审查者要审查：

- 清单是否完整。
- 是否误删、移动或修改了 skill。
- 落点建议是否符合可版本化、可触发、可维护原则。
- 是否发现同名 skill 冲突。

执行者报告：

```text
docs/tw_skills_maintenance/PHASES0_INVENTORY_EXECUTION_REPORT_CN.md
```

审查者报告：

```text
docs/tw_skills_maintenance/PHASES0_INVENTORY_REVIEW_CN.md
```

### Phase S1：修改既有四个 `tw-stock-*` Skills

执行者要做：

1. 按第 4 节更新四个既有 skills。
2. 每个 `SKILL.md` frontmatter description 必须更准确触发，但不得泛化到所有台股任务。
3. 每个 skill 都必须保留只读/禁止动作边界。
4. 长内容可拆到 `references/`，但 `SKILL.md` 必须能独立说明何时触发、读什么、做什么、不能做什么。
5. 准备每个 skill 至少 3 个 trigger test prompts 和 2 个 near-miss negative prompts。

审查者要审查：

- 是否覆盖 Agent simple-chat、DailyAgentPromptArtifact、UI2 和新 modular contracts。
- 是否出现真实写操作、真实下单、真实 provider 运维暗示。
- description 是否既能触发又不会误触发。
- 是否保留旧 skill 的核心能力。

执行者报告：

```text
docs/tw_skills_maintenance/PHASES1_EXISTING_SKILLS_UPDATE_EXECUTION_REPORT_CN.md
```

审查者报告：

```text
docs/tw_skills_maintenance/PHASES1_EXISTING_SKILLS_UPDATE_REVIEW_CN.md
```

### Phase S2：新增五个项目 Skills

执行者要做：

1. 新增第 5 节列出的五个 skills。
2. 每个 skill 建立目录：

```text
.agents/skills/<skill-name>/SKILL.md
```

如果 S0 决定使用用户级位置，则按 S0 审查结论执行。

3. 每个 skill 必须包含：

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

4. 对 `tw-stock-frontend-workbench-ux-review`，必须明确读取并使用 `.agents/skills/frontend-design/SKILL.md`。
5. 对 `tw-stock-new-model-onboarding` 和 `tw-stock-new-strategy-onboarding`，必须强调不会默认进入生产，不会改默认策略。

审查者要审查：

- 五个 skills 是否确有必要，是否与既有四个 skill 边界清晰。
- 新模型和新策略 skill 是否真正落到 contracts/registry/validator/golden sample，而不是泛泛建议。
- 集成回归 skill 是否覆盖 artifact 链，不以动态 payload 替代 artifact。
- Agent skill 是否锁定 DailyAgentPromptArtifact + backend-only OpenAI。
- 前端 UX skill 是否结合 `frontend-design`，但不变成营销设计。

执行者报告：

```text
docs/tw_skills_maintenance/PHASES2_NEW_SKILLS_EXECUTION_REPORT_CN.md
```

审查者报告：

```text
docs/tw_skills_maintenance/PHASES2_NEW_SKILLS_REVIEW_CN.md
```

### Phase S3：Skill 测试集与触发边界验证

执行者要做：

1. 为九个台股 skills 建立轻量 eval/test prompts。推荐路径：

```text
docs/tw_skills_maintenance/evals/<skill-name>-evals.json
```

2. 每个 eval 至少包含：

```text
3 个 should_trigger prompts
2 个 should_not_trigger near-miss prompts
2 条必须满足的输出约束
```

3. 如果环境支持 skill-creator 的 eval viewer，可按 skill-creator 流程生成静态 review HTML。若当前环境不适合运行完整 eval，则至少交付人工可审的 eval JSON 和触发理由。
4. 做一次静态红线扫描，确认 skill 文本没有鼓励执行 forbidden actions。

审查者要审查：

- should_trigger 是否真实覆盖未来常见开发/维护请求。
- should_not_trigger 是否包含危险近邻，例如真实下单、真实拉数、发布 provider。
- 输出约束是否能检查“只读、安全、合同优先、证据优先”。
- 是否存在 skill 之间职责重叠导致触发混乱。

执行者报告：

```text
docs/tw_skills_maintenance/PHASES3_SKILL_EVALS_EXECUTION_REPORT_CN.md
```

审查者报告：

```text
docs/tw_skills_maintenance/PHASES3_SKILL_EVALS_REVIEW_CN.md
```

### Phase S4：最终验收与同步建议

执行者要做：

1. 汇总九个台股 skills 的最终清单、路径、用途、触发场景。
2. 明确 repo 内和用户级 skills 是否一致。
3. 给出后续维护建议：什么时候更新 skill、谁负责更新、如何避免过期。
4. 输出最终总结。

审查者要审查：

- 是否可以作为后续新节点默认工作基础。
- 是否需要同步到用户级 `.agents/skills`。
- 是否还存在过时 skill 或冲突 skill。
- 是否可以收尾。

执行者报告：

```text
docs/tw_skills_maintenance/PHASES4_FINAL_SUMMARY_CN.md
```

审查者报告：

```text
docs/tw_skills_maintenance/PHASES4_FINAL_ACCEPTANCE_REVIEW_CN.md
```

## 8. 统一停工条件

执行者或审查者遇到以下情况必须停下来找用户和统筹确认：

- 不确定 skills 应写入 repo 内还是用户级目录，且会影响运行时触发。
- 需要删除、重命名、覆盖旧用户级 skills。
- 某 skill 需要真实数据拉取、provider publish、accepted latest switch、monitor write、broker/order/quick-trade 才能验证。
- 发现现有文档互相矛盾，例如 Agent 路线绕过 DailyAgentPromptArtifact。
- 新模型/新策略 skill 被要求直接切成默认生产策略。
- 前端 skill 被要求加入交易执行入口或真实仓位建议。
- eval 结果显示两个 skills 的触发边界严重冲突。

## 9. 执行者每阶段报告模板

```markdown
# Phase Sx 执行报告

## 1. 本阶段目标
## 2. 已阅读文档
## 3. 修改/新增文件
## 4. 关键设计决定
## 5. Skill 触发边界
## 6. 只读/安全边界确认
## 7. 测试或静态检查
## 8. 未解决问题
## 9. 给审查者的重点
```

## 10. 审查者每阶段报告模板

```markdown
# Phase Sx 审查意见

## 1. 结论
## 2. 对照本主文档的符合性
## 3. Findings
## 4. Skill 触发与误触发风险
## 5. 只读/安全边界审查
## 6. 文档与测试充分性
## 7. 必修项
## 8. 下一阶段工作文档
```

审查结论只能使用：

```text
通过，允许进入下一阶段
不通过，需修复后复审
有条件通过，仅允许执行列明的修复项
```

## 11. 给执行者的第一条命令

```text
你是执行者。请按 docs/tw_skills_maintenance/TW_SKILLS_MAINTENANCE_BRANCH_WORK_CN.md 执行 Phase S0：Inventory 与落点确认。只做清单、读取、运行时加载位置判断和落点建议，不修改任何 skill、不新增文件到 skills 目录、不删除或移动旧 skill。完成后写执行报告 docs/tw_skills_maintenance/PHASES0_INVENTORY_EXECUTION_REPORT_CN.md。必须说明 repo 内 .agents/skills 与 /home/chuliyang/.agents/skills 的差异、当前四个 tw-stock skills 的过期点、推荐落点方案、以及是否需要统筹确认。遇到不确定运行时加载优先级或权限问题，立即停下来报告。
```

## 12. 给审查者的第一条命令

```text
你是审查者。请等待执行者给出 docs/tw_skills_maintenance/PHASES0_INVENTORY_EXECUTION_REPORT_CN.md 后，按 docs/tw_skills_maintenance/TW_SKILLS_MAINTENANCE_BRANCH_WORK_CN.md 审查 Phase S0。重点审查：skill 清单是否完整、repo 内与用户级 skill 落点判断是否可信、是否误修改了 skill、是否识别四个旧 tw-stock skills 的过期点、推荐落点是否有利于版本化和运行时触发。审查后写 docs/tw_skills_maintenance/PHASES0_INVENTORY_REVIEW_CN.md，并给出 Phase S1 的下一步工作文档。不得越过本主文档扩展到业务代码开发。
```
