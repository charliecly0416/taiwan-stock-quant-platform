# Phase S1 执行报告：更新项目内四个 tw-stock-* Skills

生成日期：2026-06-19

## 1. 本阶段目标

按 `docs/tw_skills_maintenance/PHASES1_EXISTING_SKILLS_UPDATE_WORK_V2_CN.md` 更新项目内四个既有台股 skills：

```text
.agents/skills/tw-stock-safety-boundary-review
.agents/skills/tw-stock-readonly-e2e-acceptance
.agents/skills/tw-stock-research-context-analyst
.agents/skills/tw-stock-data-freshness-diagnosis
```

目标是让四个 skills 覆盖当前主线：模块化合同、只读研究边界、DailyAgentPromptArtifact、Agent simple-chat、前端策略工作台 UI2、readonly Playwright 验收，以及后续新模型/新策略扩展接入的边界。

## 2. 已阅读文档

- `/home/chuliyang/.agents/skills/skill-creator/SKILL.md`
- `docs/tw_skills_maintenance/PHASES1_EXISTING_SKILLS_UPDATE_WORK_V2_CN.md`
- `docs/tw_skills_maintenance/PHASES1R_PROJECT_SKILLS_MIGRATION_EXECUTION_REPORT_CN.md`

并读取/复核了项目内四个旧 skill 及其 references/scripts 文件清单。

## 3. 修改/新增文件

修改项目内 skills：

```text
.agents/skills/tw-stock-safety-boundary-review/SKILL.md
.agents/skills/tw-stock-safety-boundary-review/references/forbidden-actions.md
.agents/skills/tw-stock-safety-boundary-review/references/network-audit-rules.md

.agents/skills/tw-stock-readonly-e2e-acceptance/SKILL.md
.agents/skills/tw-stock-readonly-e2e-acceptance/references/readonly-boundary.md
.agents/skills/tw-stock-readonly-e2e-acceptance/references/acceptance-report-template.md

.agents/skills/tw-stock-research-context-analyst/SKILL.md
.agents/skills/tw-stock-research-context-analyst/references/qlib-cross-analysis-semantics.md
.agents/skills/tw-stock-research-context-analyst/references/research-report-template.md

.agents/skills/tw-stock-data-freshness-diagnosis/SKILL.md
.agents/skills/tw-stock-data-freshness-diagnosis/references/data-source-boundary.md
.agents/skills/tw-stock-data-freshness-diagnosis/references/freshness-status-fields.md
```

保留未改脚本：

```text
.agents/skills/tw-stock-safety-boundary-review/scripts/audit_tw_stock_diff.mjs
.agents/skills/tw-stock-readonly-e2e-acceptance/scripts/summarize_e2e_artifacts.mjs
.agents/skills/tw-stock-research-context-analyst/scripts/summarize_research_context.mjs
.agents/skills/tw-stock-data-freshness-diagnosis/scripts/fetch_tw_stock_readonly_status.mjs
```

新增/更新本报告：

```text
docs/tw_skills_maintenance/PHASES1_EXISTING_SKILLS_UPDATE_EXECUTION_REPORT_CN.md
```

## 4. 四个 skills 的 description 变化

### 4.1 `tw-stock-safety-boundary-review`

从旧的通用只读边界审查，扩展为会在以下场景触发：

```text
Agent simple-chat answers
DailyAgentPromptArtifact files
prompt builders/validators
OpenAI adapter code
frontend Agent/workbench text
Playwright screenshots
network_audit.json / console_audit.json
```

description 明确检查：`order/place order/submit order`、`target_position/target_weight`、monitor writes、provider publish/refresh、accepted latest switching、frontend OpenAI key/base URL/browser-side calls、forged citations、qlib score 误解释。

### 4.2 `tw-stock-readonly-e2e-acceptance`

从旧 full-scenario readonly E2E，扩展为 `/tw-stock-monitor` 策略工作台 UI2 验收 skill。

新增触发场景：

```text
strategy workbench UI2
Agent simple-chat panel
DailyAgentPromptArtifact dry-run/validator gate
Playwright desktop/tablet/mobile screenshots
network/console artifacts
```

### 4.3 `tw-stock-research-context-analyst`

从 qlib accepted latest / TopN / cross-analysis 解读，扩展为策略工作台研究上下文解释。

新增触发场景：

```text
今天策略是什么
为什么某标的在候选名单
current-strategy-context
readonly strategy snapshot
DailyAgentPromptArtifact summaries
paper portfolio gate
readonly replay summaries
Agent context_digest
```

### 4.4 `tw-stock-data-freshness-diagnosis`

从 daily/qlib freshness 诊断，扩展为四类 latest 诊断：

```text
provider raw/latest
qlib accepted latest
readonly strategy snapshot latest
Agent DailyAgentPromptArtifact latest
```

description 明确 Agent prompt latest 落后不等于 provider/qlib 数据落后，并要求解释 UI/Agent 下游影响。

## 5. 四个 skills 的新增覆盖点

### 5.1 Safety Boundary

新增覆盖：

- DailyAgentPromptArtifact / prompt builder / prompt validator。
- `POST /api/tw-stock/agent/simple-chat` 允许只读语境。
- Simple Chat OpenAI adapter 后端边界。
- 前端 Agent panel 与策略工作台 UX。
- Playwright network/console/screenshots。
- OpenAI key/base URL/browser-side call 禁止项。
- 英文危险语义：`order`、`place order`、`submit order`、`target_weight`、`target position`、`buy now`、`sell now`、`auto buy`、`auto sell`。
- Agent citation、unsafe answer 和 qlib score 误解释检查。

### 5.2 Readonly E2E Acceptance

新增覆盖：

- 今日策略总览、候选名单、历史模拟、模拟账户状态、Agent simple-chat panel。
- readonly strategy snapshot / readonly replay window。
- DailyAgentPromptArtifact dry-run/validator gate。
- desktop/tablet/mobile screenshots。
- `overflowX=false`、无明显文字重叠、按钮不溢出、主要面板不空白、技术详情默认折叠。
- `frontend_openai_direct_request_count=0`、`broker_quick_trade_order_request_count=0`。
- 前端主路径必须是 `/api/tw-stock/agent/simple-chat`，不能回退旧 `/agent/chat`。

### 5.3 Research Context Analyst

新增覆盖：

- `current-strategy-context`、`readonly-strategy-snapshot`。
- DailyAgentPromptArtifact 摘要。
- paper portfolio gate、readonly replay result summary。
- Agent `context_digest`。
- 当前默认研究口径：E4 Qlib + Orthogonal LTR。
- `candidate_rank / score_rank / buy_score / full_qlib_rank` 只能作为研究排序。
- “当前证据不足”规则，防止臆造今日结论。

### 5.4 Data Freshness Diagnosis

新增覆盖：

- 四类 latest 区分。
- Agent prompt latest 落后原因：builder 未运行、validator 未通过、latest pointer 未更新、artifact 未发布、source mismatch。
- 只读检查 artifact manifest/latest pointer。
- 下游影响：今日策略总览、候选名单、历史模拟、模拟账户 gate、Agent simple-chat 回答。

## 6. 四个 skills 的保留旧能力说明

保留旧能力：

- Safety skill 仍审查 diff、Agent 文本、frontend text、network/console audit，并按 severity 输出。
- E2E skill 仍可运行/审查旧 full-scenario readonly E2E、summary/network/console artifacts 和 frontend build。
- Research skill 仍解释 qlib accepted latest、TopN/Top30、trend、cross-analysis、monitor history、kline、Agent context。
- Freshness skill 仍诊断 daily auto-update status、FinMind raw、Yahoo/Scrapling qlib、pending_asof、fresh_data_wait、retry。

## 7. Trigger prompts 与 near-miss prompts

### 7.1 `tw-stock-safety-boundary-review`

should_trigger:

```text
审查这个 Agent simple-chat 回答有没有越过只读边界。
检查 Playwright network_audit.json 里有没有 forbidden request。
审查 /tw-stock-monitor 文案是否把策略解释助手做成交易助手。
审查 DailyAgentPromptArtifact 里有没有 order 或 target_weight 风险。
检查前端有没有暴露 OpenAI API key 或 browser-side OpenAI call。
```

should_not_trigger:

```text
解释 2330 为什么在候选名单里。
检查 Agent prompt latest 为什么没更新。
跑一次 /tw-stock-monitor Playwright 验收。
```

### 7.2 `tw-stock-readonly-e2e-acceptance`

should_trigger:

```text
跑一次 /tw-stock-monitor 策略工作台只读验收。
审查 Playwright desktop/tablet/mobile 截图和 network/console 产物能不能接受。
确认 UI2 策略工作台和 Agent simple-chat 是否最终通过验收。
检查 DailyAgentPromptArtifact dry-run gate 和 simple-chat network audit 是否安全。
```

should_not_trigger:

```text
帮我新增一个模型并接入 registry。
解释 qlib score 是什么意思。
审查这个 Agent 回答有没有目标仓位风险。
```

### 7.3 `tw-stock-research-context-analyst`

should_trigger:

```text
今天策略是什么？
2330 为什么排名第一？
今天有哪些候选调入，能不能买？
为什么模拟账户不能应用？
数据新鲜度如何影响今天策略解释？
```

should_not_trigger:

```text
审查这个 diff 是否有 order submit 风险。
跑 Playwright 验收截图。
为什么 Agent prompt latest 还是昨天？
```

### 7.4 `tw-stock-data-freshness-diagnosis`

should_trigger:

```text
为什么 Agent prompt latest 还是昨天？
qlib accepted latest 和 readonly snapshot latest 不一致怎么办？
检查 latest_asof 为什么没更新。
FinMind raw 更新了但 qlib accepted latest 没动，后面会自动重试吗？
readonly strategy snapshot latest 落后会影响哪些页面？
```

should_not_trigger:

```text
新增一个策略规则。
审查 Agent 回答有没有目标仓位建议。
跑 Playwright 验收截图。
```

## 8. 静态红线扫描结果与归因

执行：

```bash
rg -n "provider publish|accepted latest switch|quick-trade|broker|submit order|place order|target_position|target_weight|OpenAI API key|OPENAI_API_KEY" .agents/skills/tw-stock-*
```

结果：有命中，均为允许语境。

归因：

- `tw-stock-safety-boundary-review/SKILL.md` 与 references：命中出现在 description、Forbidden Actions、Workflow、Trigger Examples、Verdict Rules、危险 API/语义 deny-list、允许/禁止语境说明中，用于审查和阻断。
- `tw-stock-safety-boundary-review/scripts/audit_tw_stock_diff.mjs`：命中为既有静态审查脚本的危险路径正则。
- `tw-stock-readonly-e2e-acceptance/SKILL.md` 与 references：命中出现在 Forbidden Actions、Pass Criteria、simple-chat payload 检查、报告模板和只读边界说明中。
- `tw-stock-research-context-analyst/SKILL.md` 与 references：命中出现在 Forbidden Actions、Stop Conditions 和安全语言说明中。
- `tw-stock-data-freshness-diagnosis/SKILL.md` 与 references：命中出现在 Forbidden Actions、Stop Conditions、四类 latest 诊断边界和禁止调用列表中。

未发现鼓励执行真实动作、真实下单、provider publish、accepted latest switch、broker/quick-trade/order、target_position/target_weight 或 OpenAI key 暴露的语境。

## 9. 文件完整性检查

执行：

```bash
find .agents/skills/tw-stock-* -maxdepth 3 -type f | sort
```

结果确认四个项目内 skills 仍完整，包含 `SKILL.md`、`references/` 和既有 `scripts/`。

执行：

```bash
find /home/chuliyang/.agents/skills -maxdepth 2 -name SKILL.md -print | sort
```

结果：

```text
/home/chuliyang/.agents/skills/latex-paper-en/SKILL.md
/home/chuliyang/.agents/skills/pptx/SKILL.md
/home/chuliyang/.agents/skills/skill-creator/SKILL.md
```

确认用户级原路径没有同名 `tw-stock-*` skills。

## 10. 范围确认

只修改项目内：

```text
.agents/skills/tw-stock-*
docs/tw_skills_maintenance/PHASES1_EXISTING_SKILLS_UPDATE_EXECUTION_REPORT_CN.md
```

未修改：

```text
/home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/**
/home/chuliyang/.agents/skills/tw-stock-* 原路径
backend/
frontend/
scripts/
configs/
examples/
qlib/
data_tw/
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

## 11. 未解决问题

无阻塞问题。

说明：S3 会把本阶段 prompts 整理成 eval JSON；本阶段按 V2 要求只在报告中列出 trigger / near-miss prompts。

## 12. 给审查者的重点

请重点审查：

- 四个 `description` 是否足够触发新路线，但没有泛化到所有台股任务。
- Safety skill 是否覆盖 simple-chat、DailyAgentPromptArtifact、OpenAI adapter、UI2、英文危险语义和 citation/score 误解释。
- E2E skill 是否覆盖 UI2 工作台、三视口截图、network/console 指标和 frontend OpenAI 直连检查。
- Research skill 是否正确把买卖问题转成只读研究解释，并引用可追溯字段。
- Freshness skill 是否正确区分四类 latest，并说明 stale prompt/snapshot 的下游影响。
- 静态红线扫描命中是否都属于禁止/审查/拒答语境。
- 是否确认未修改归档旧版本、用户级原路径和业务/前端/模型/策略代码。
