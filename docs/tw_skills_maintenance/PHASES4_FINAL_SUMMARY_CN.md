# Phase S4 最终总结：台股项目 Skills 维护路线

生成日期：2026-06-19

## 1. 最终结论

台股项目 skills 维护路线 S0-S3 已完成，S4 最终复核通过执行侧收尾。

当前项目级 `.agents/skills/` 下共有九个 `tw-stock-*` skills，覆盖安全边界审查、只读 E2E 验收、研究解释、数据 freshness 诊断、新模型接入、新策略接入、模块化集成回归、Agent DailyAgentPromptArtifact 维护、前端策略工作台 UX 审查。用户级 `/home/chuliyang/.agents/skills/tw-stock-*` active 路径为空，旧版本保留在 archive 目录，仅作为备份，不应作为 active skill 来源。

本阶段未修改业务代码、前端代码、模型策略代码或数据目录；未触发真实数据拉取、provider publish/refresh、accepted latest switch、monitor 写入、broker/order、OpenAI 调用或 key 读取。

## 2. 最终 skills 清单

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

辅助设计 skill：

```text
.agents/skills/frontend-design/SKILL.md
```

说明：`frontend-design` 不是台股业务 skill，但已被 `tw-stock-frontend-workbench-ux-review` 明确引用，用于前端工作台 UX 优化时保持产品化视觉与响应式质量。

## 3. 九个 skills 职责表

| Skill | 主要用途 | 触发场景 | 不应处理 | 关键禁止项 |
| --- | --- | --- | --- | --- |
| `tw-stock-safety-boundary-review` | 审查只读、安全、交易和 OpenAI 边界 | diff、Agent 回答、network/console audit、DailyAgentPromptArtifact、前端文本安全审查 | 新模型/新策略实现、UI 设计修复、freshness 诊断 | broker、quick-trade、order、target_position、target_weight、provider publish、accepted latest switch、frontend OpenAI/key |
| `tw-stock-readonly-e2e-acceptance` | 只读验收与 Playwright/审计证据汇总 | `/tw-stock-monitor` 验收、desktop/tablet/mobile 截图、network/console audit、simple-chat 验收 | 视觉设计重构、业务逻辑实现、真实数据刷新 | 真实数据拉取、monitor 写入、provider refresh/publish、accepted latest switch、OpenAI key、交易路径 |
| `tw-stock-research-context-analyst` | 研究解释与候选/策略语义说明 | 今日策略、2330 为什么在榜、TopN/Top30、readonly replay、paper portfolio 解释 | freshness stale 根因诊断、新模型/策略开发、安全审查 | 交易建议、仓位、target_weight、收益/胜率/上涨概率承诺、broker/order |
| `tw-stock-data-freshness-diagnosis` | 只读 freshness/latest/asof 诊断 | latest_asof、qlib accepted latest、provider raw latest、snapshot latest、prompt latest 差异 | prompt 构建修复、真实拉数、研究推荐解释 | 数据拉取、prompt build/publish、provider publish、accepted latest switch、POST/PUT/PATCH/DELETE |
| `tw-stock-new-model-onboarding` | 新台股模型接入合同与评估路径 | qlib/LTR/ensemble 模型、OOS、ModelSignalArtifact、registry、golden sample、validator | 策略规则实现、生产默认切换、前端默认切换 | default-switch、provider publish、accepted latest switch、broker/order、target_position/target_weight、收益承诺 |
| `tw-stock-new-strategy-onboarding` | 新策略规则与只读 replay 接入 | StrategyRule、dependency YAML、rebalance、candidate filter、OrderIntentArtifact、readonly replay | 新模型训练、真实订单执行、生产策略默认切换 | broker、quick-trade、submit/place order、target_position/target_weight、future-data leakage、provider publish |
| `tw-stock-modular-integration-regression` | 模块链路只读集成回归 | DataSourceSnapshot 到 DailyAgentPromptArtifact、Backend API、Frontend Workbench、Playwright evidence | 单模块开发替代、动态伪造 artifact、真实运维动作 | 真实数据拉取、provider publish、accepted latest switch、monitor 写入、OpenAI 调用、production default change |
| `tw-stock-agent-daily-prompt-maintenance` | Agent DailyAgentPromptArtifact 与 simple-chat 路线维护 | prompt builder/validator、simple-chat service、OpenAI adapter、citation、今日策略 Q&A | frontend UX 优化、freshness 根因诊断、复杂 tool Agent 重建 | frontend OpenAI、OpenAI key exposure、交易建议、monitor 写入、provider publish、accepted latest switch、orders |
| `tw-stock-frontend-workbench-ux-review` | `/tw-stock-monitor` 策略工作台 UX 与响应式审查 | Agent panel、候选名单、replay、paper portfolio、移动端重叠/空白、UI2 产品化验收 | 模型/策略算法、provider/accepted latest、实盘交易入口 | broker、quick-trade、real order、target position/weight、frontend OpenAI/key、monitor 写入、provider publish |

## 4. 委派关系与触发边界

- `safety-boundary-review` vs `readonly-e2e-acceptance`：安全审查关注危险动作、危险字段、OpenAI/key、交易语义；E2E acceptance 关注只读验收、截图、network/console 证据和最终 readiness。若验收中发现危险请求，可联用 safety。
- `readonly-e2e-acceptance` vs `frontend-workbench-ux-review`：验收/证据/Playwright run 触发 E2E；视觉层级、响应式布局、空白面板、文本重叠和产品化设计修复触发 UX review。
- `research-context-analyst` vs `data-freshness-diagnosis`：候选、排名、今日策略、个股解释触发 research；latest/asof/stale/retry/pending_asof 差异触发 freshness diagnosis。
- `agent-daily-prompt-maintenance` vs `safety-boundary-review`：prompt/service/adapter/validator 维护触发 Agent maintenance；审查回答是否越界、citation 是否伪造、payload 是否危险触发 safety。
- `new-model-onboarding` vs `new-strategy-onboarding`：模型、OOS、ModelSignalArtifact、registry、golden sample 触发 model；StrategyRule、rebalance、candidate filter、OrderIntentArtifact、readonly replay 触发 strategy。
- `modular-integration-regression` vs 单模块 onboarding/maintenance：跨 DataSourceSnapshot/FeatureArtifact/ModelSignalArtifact/StrategyRule/OrderIntentArtifact/ReplayResult/ReadonlyStrategySnapshot/DailyAgentPromptArtifact/API/frontend 的链路验收触发 integration；单点新增或修复委派给对应模块 skill。

## 5. 只读与安全边界

以下动作不属于当前九个台股 skills 的自动执行范围：

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

如用户请求包含上述动作，skill 应停止、拒绝、或改写为只读研究/审查任务；不得给出绕过边界的执行步骤。

## 6. S0-S3 阶段回顾

- S0 Inventory 与落点确认：确认台股 skills 应从用户级迁移到项目本地 `.agents/skills/`，并记录原有 skill 与项目需求差距。
- S1 既有四个 skills 更新：更新 safety、readonly E2E、research context、data freshness 四个既有 skills，引入 DailyAgentPromptArtifact、simple-chat、UI2、OpenAI 边界、latest 类型等新约束。
- S1R 项目本地迁移：将用户级旧 skills 迁移到项目级 `.agents/skills/`，并把用户级旧版本归档到 `_archived_tw_stock_skills_20260619/`。
- S2 新增五个 skills：新增 new-model、new-strategy、modular-integration、agent-daily-prompt、frontend-workbench-ux 五个项目级 skills。
- S3 触发、委派、越界停止静态验证：完成九个 skills 的结构检查、触发/委派矩阵、越界停止样例和红线扫描归因；统一四个旧 skill 的 `Allowed Actions / Evidence` 章节标题。

## 7. 静态检查结果

项目 skills 清单检查：

```bash
find .agents/skills/tw-stock-* -maxdepth 2 -name SKILL.md -print | sort
```

结果：恰好九个 `SKILL.md`，路径见第 2 节。

用户级 active 路径检查：

```bash
find /home/chuliyang/.agents/skills -maxdepth 1 -type d -name 'tw-stock-*' -print | sort
```

结果为空。

章节结构抽查：

```bash
rg -n "^(---|name:|description:|## Purpose|## Read First|## Allowed Actions / Evidence|## Forbidden Actions|## Workflow|## Output Format|## Trigger Examples|## Stop Conditions)" .agents/skills/tw-stock-*/SKILL.md
```

结论：九个 `SKILL.md` 均包含 frontmatter `name`、`description`，并包含 `Purpose`、`Read First`、`Allowed Actions / Evidence`、`Forbidden Actions`、`Workflow`、`Output Format`、`Trigger Examples`、`Stop Conditions`。

红线扫描：

```bash
rg -n "provider publish|accepted latest switch|quick-trade|broker|submit order|place order|target_position|target_weight|OpenAI API key|OPENAI_API_KEY|browser-side OpenAI|frontend OpenAI|default-switch|production default" .agents/skills/tw-stock-*
```

结论：有命中，均位于 description 中的禁止边界、Forbidden Actions、Workflow 检查点、Stop Conditions、reference deny-list、readonly boundary、network audit rules 或安全脚本中。未发现鼓励真实执行交易、provider publish、accepted latest switch、monitor 写入、OpenAI key 暴露或前端 OpenAI 调用的文本。

## 8. 版本化状态

执行：

```bash
git status --short .agents/skills docs/tw_skills_maintenance
```

结果：

```text
?? .agents/skills/
?? docs/tw_skills_maintenance/
```

结论：当前 `.agents/skills/` 与 `docs/tw_skills_maintenance/` 仍为未跟踪内容。最终合并前必须纳入版本管理，否则后续节点无法稳定复用这些项目级 skills 和维护报告。

## 9. 用户级同步建议

项目本地 `.agents/skills/tw-stock-*` 应作为当前台股项目唯一权威来源。

建议：

- 不恢复 `/home/chuliyang/.agents/skills/tw-stock-*` active 路径。
- 不在用户级 active skills 中维护另一套台股 skills，避免项目版本和用户版本漂移。
- 后续如需跨仓库复用，应通过明确的复制、插件化或版本化同步流程进行，而不是让 archive 目录参与运行时加载。
- 若运行时技能列表仍显示 archive 中旧 skills 的元数据，应单独评估 Codex/agent 的 skill 搜索路径、archive 命名或加载排除策略。

## 10. Archive 残余风险

归档目录存在：

```text
/home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/
```

当前包含旧版：

```text
tw-stock-data-freshness-diagnosis
tw-stock-readonly-e2e-acceptance
tw-stock-research-context-analyst
tw-stock-safety-boundary-review
```

该目录只是旧版本备份，不应作为 active skill 来源。本阶段不修改 archive，也不删除 archive。

残余风险：当前运行时若仍扫描 archive 子目录，可能暴露旧 skills 元数据，造成触发歧义。该风险不代表用户级 active 路径已恢复，但需要后续在运行时配置或 archive 管理策略中单独处理。

## 11. 未覆盖范围

本次验收级别是静态触发矩阵 + 人工边界验证。

未覆盖：

```text
完整 skill-creator 子会话 eval
with-skill / baseline 对比
evals/*.json 与 eval viewer
真实运行时自动触发命中率
跨会话 skill 加载缓存刷新验证
archive 目录是否被运行时扫描的配置级验证
```

这些是残余风险，不在 S4 内修复，除非统筹另行授权。

## 12. 后续维护建议

以下变化发生时，应同步更新相关 skills：

- 新增模型合同、model registry 规则、ModelSignalArtifact 字段、OOS 评估口径或 golden sample 要求。
- 新增策略合同、StrategyRule、OrderIntentArtifact、candidate filter、readonly replay 规则或 replay evidence 格式。
- Agent route、DailyAgentPromptArtifact、prompt builder、prompt validator、simple-chat service、OpenAI adapter 或 citation 合同变化。
- `/tw-stock-monitor` 前端工作台主线、Agent panel、候选名单、paper portfolio、readonly replay 或响应式布局发生结构变化。
- readonly E2E 验收证据、Playwright screenshot、network_audit.json、console_audit.json 或 summary 格式变化。
- 数据 freshness 字段、latest pointer、pending_asof、fresh_data_wait、run_id 或 provider/qlib/snapshot/prompt latest 语义变化。
- 安全边界新增 forbidden endpoints、forbidden fields、OpenAI/key 暴露路径、broker/order/quick-trade 路径或 monitor 写入路径。

维护原则：先更新项目级 `.agents/skills/tw-stock-*`，再更新对应文档和验收报告；不得在用户级 active skills 中创建平行版本。
