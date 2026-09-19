# Phase S1 工作文档 V2：更新项目内四个 tw-stock-* Skills

生成日期：2026-06-19

## 1. 工作结论

Phase S1R 已审查通过。四个旧 `tw-stock-*` skills 已迁入项目内 `.agents/skills/`，用户级旧版本已归档。

本阶段恢复 Phase S1 内容更新。执行者必须只编辑项目内版本：

```text
.agents/skills/tw-stock-safety-boundary-review
.agents/skills/tw-stock-readonly-e2e-acceptance
.agents/skills/tw-stock-research-context-analyst
.agents/skills/tw-stock-data-freshness-diagnosis
```

不得编辑：

```text
/home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/**
/home/chuliyang/.agents/skills/tw-stock-*
```

## 2. 本阶段目标

更新四个既有台股 skills，使它们覆盖当前项目主线：

```text
模块化合同
只读研究边界
DailyAgentPromptArtifact
Agent simple-chat
前端策略工作台 UI2
readonly Playwright 验收
新模型/新策略扩展接入
```

本阶段只维护 skills，不修改业务代码、前端产品代码、模型策略默认行为或真实运维链路。

## 3. 严禁事项

不得执行：

```text
修改 /home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619
恢复 /home/chuliyang/.agents/skills/tw-stock-* 原路径
修改台股业务代码
修改前端产品代码
修改模型/策略默认行为
触发真实数据拉取
provider refresh / publish
accepted latest switch
monitor config / scan / alerts 写入
broker / quick-trade / order
target position / target weight 写入
OpenAI 调用或 key 读取
```

本阶段允许：

```text
编辑 .agents/skills/tw-stock-*/SKILL.md
必要时编辑 .agents/skills/tw-stock-*/references/
必要时更新 .agents/skills/tw-stock-*/scripts/ 的只读说明或静态检查逻辑
写执行报告
```

不得新增五个新 skills；那属于 S2。

## 4. 通用 Skill 编写要求

每个 `SKILL.md` 必须包含：

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

每个 `description` 必须：

- 明确何时触发。
- 写清 skill 做什么。
- 包含关键触发词。
- 不泛化到所有台股问题。
- 不与其他台股 skill 大面积重叠。
- 对当前项目新路线足够敏感，避免 undertrigger。

每个 skill 必须保留：

- 旧 skill 的核心能力。
- 只读边界。
- 禁止真实交易和真实运维动作的边界。
- 原有 references/scripts 的有效入口。

## 5. `tw-stock-safety-boundary-review` 必修项

目标文件：

```text
.agents/skills/tw-stock-safety-boundary-review/SKILL.md
.agents/skills/tw-stock-safety-boundary-review/references/forbidden-actions.md
.agents/skills/tw-stock-safety-boundary-review/references/network-audit-rules.md
```

必须补充审查对象：

```text
DailyAgentPromptArtifact
prompt builder
prompt validator
POST /api/tw-stock/agent/simple-chat
Simple Chat OpenAI adapter
前端 Agent panel
策略工作台 UX
Playwright network/console artifacts
Playwright screenshots
```

必须补充安全边界：

```text
/api/tw-stock/agent/simple-chat 是允许的只读后端解释接口
前端不得出现 OpenAI API key
前端不得出现 OpenAI base URL
前端不得 browser-side OpenAI call
OpenAI key 只能在后端环境变量中读取
```

必须加入英文危险语义：

```text
order
place order
submit order
target_weight
target weight
target_position
target position
buy now
sell now
auto buy
auto sell
broker
quick-trade
```

必须区分：

- 拒答、安全声明、只读 flags、历史模拟术语、forbidden list 中的命中是允许语境。
- 行动指令、真实入口、写接口、投资建议是失败语境。

必须加入 Agent answer 检查：

- 不得伪造 citation。
- 不得把 qlib score 解释为收益率、胜率、上涨概率或买入概率。
- 不得输出买卖行动建议。
- 不得输出目标仓位/目标权重。
- 买卖问题必须转为研究解释或拒答。

## 6. `tw-stock-readonly-e2e-acceptance` 必修项

目标文件：

```text
.agents/skills/tw-stock-readonly-e2e-acceptance/SKILL.md
.agents/skills/tw-stock-readonly-e2e-acceptance/references/readonly-boundary.md
.agents/skills/tw-stock-readonly-e2e-acceptance/references/acceptance-report-template.md
```

必须扩展验收范围：

```text
/tw-stock-monitor 策略工作台 UX
今日策略总览
候选名单
readonly strategy snapshot
readonly replay window
模拟账户状态
Agent simple-chat panel
DailyAgentPromptArtifact dry-run/validator gate
```

必须扩展 Playwright 要求：

```text
desktop screenshot
tablet screenshot
mobile screenshot
overflowX=false
无明显文字重叠
按钮不溢出
主要面板不空白
技术详情默认折叠
```

通过标准至少包含：

```text
forbidden_request_count=0
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
ops_dry_run_post_count=0
failed_response_count=0
console_error_count=0
page_error_count=0
frontend_openai_direct_request_count=0
broker_quick_trade_order_request_count=0
```

simple-chat 规则：

```text
前端主路径只能调用 /api/tw-stock/agent/simple-chat
不能把旧 /agent/chat 作为主路径
不能暴露 OpenAI key
不能 browser-side 直连 OpenAI
simple-chat payload 不能包含 target_position / target_weight / order execution 字段
```

## 7. `tw-stock-research-context-analyst` 必修项

目标文件：

```text
.agents/skills/tw-stock-research-context-analyst/SKILL.md
.agents/skills/tw-stock-research-context-analyst/references/qlib-cross-analysis-semantics.md
.agents/skills/tw-stock-research-context-analyst/references/research-report-template.md
```

必须扩展允许证据：

```text
current-strategy-context
readonly-strategy-snapshot
DailyAgentPromptArtifact 摘要
paper portfolio gate
readonly replay result summary
Agent context_digest
```

必须明确当前默认研究口径：

```text
E4 Qlib + Orthogonal LTR
LTR 在 qlib top50 内做重排
candidate_rank / score_rank / buy_score / full_qlib_rank 只能作为研究排序
这些分数不是收益率、胜率、上涨概率或买入概率
```

必须覆盖新工作台问题：

```text
今天策略是什么？
排名第一是谁？
为什么 2330 在榜？
今天有哪些候选调入？
今天有哪些调出复核？
为什么模拟账户不能应用？
数据新鲜度如何？
要不要买/卖某只股票？
```

买卖问题必须转换为：

```text
只读研究策略解释
候选观察
风险与数据口径
人工复盘说明
```

不得给交易动作。

回答必须优先引用：

```text
asof
run_id
artifact id
checksum
snapshot id
rank
score
strategy rule
candidate_rank
score_rank
full_qlib_rank
```

缺证据时必须说：

```text
当前证据不足
```

## 8. `tw-stock-data-freshness-diagnosis` 必修项

目标文件：

```text
.agents/skills/tw-stock-data-freshness-diagnosis/SKILL.md
.agents/skills/tw-stock-data-freshness-diagnosis/references/data-source-boundary.md
.agents/skills/tw-stock-data-freshness-diagnosis/references/freshness-status-fields.md
```

必须区分四类 latest：

```text
provider raw/latest
qlib accepted latest
readonly strategy snapshot latest
Agent DailyAgentPromptArtifact latest
```

必须明确：

```text
Agent prompt latest 落后不等于 provider/qlib 数据落后
它可能只是 prompt builder 未运行、validator 未通过、latest pointer 未更新或 artifact 未发布
```

允许只读检查：

```text
artifact manifest
latest pointer
DailyAgentPromptArtifact manifest/checksum
readonly strategy snapshot manifest/latest
```

不得触发构建、刷新、发布或切换。

输出中增加：

```text
下游影响
```

说明 stale prompt 或 stale snapshot 会影响：

```text
今日策略总览
候选名单
历史模拟
模拟账户 gate
Agent simple-chat 回答
```

## 9. Trigger prompts 与 near-miss prompts

每个 skill 至少准备：

```text
3 个 should_trigger prompts
2 个 should_not_trigger near-miss prompts
```

可写入执行报告，S3 再整理为 eval JSON。

## 10. 静态红线扫描

完成后运行：

```bash
rg -n "provider publish|accepted latest switch|quick-trade|broker|submit order|place order|target_position|target_weight|OpenAI API key|OPENAI_API_KEY" .agents/skills/tw-stock-*
```

命中必须逐条归因：

- 禁止动作列表、拒答规则、审查规则中的命中允许。
- 如果命中是在鼓励执行真实动作，必须修复。

还必须运行：

```bash
find .agents/skills/tw-stock-* -maxdepth 3 -type f | sort
find /home/chuliyang/.agents/skills -maxdepth 2 -name SKILL.md -print | sort
```

确认：

- 项目内四个 skills 仍完整。
- 用户级原路径没有同名 `tw-stock-*` skills。

## 11. 执行报告要求

完成后写：

```text
docs/tw_skills_maintenance/PHASES1_EXISTING_SKILLS_UPDATE_EXECUTION_REPORT_CN.md
```

报告必须包含：

```text
本阶段目标
已阅读文档
修改/新增文件
四个 skills 的 description 变化
四个 skills 的新增覆盖点
四个 skills 的保留旧能力说明
Trigger prompts 与 near-miss prompts
静态红线扫描结果与归因
确认只修改项目内 .agents/skills/tw-stock-*
确认未修改归档旧版本
确认用户级原路径无同名 tw-stock skills
确认未修改业务/前端/模型/策略代码
未解决问题
给审查者的重点
```

## 12. 停止条件

遇到以下任一情况必须停止：

- 需要修改归档目录才能继续。
- 需要恢复用户级原路径 `tw-stock-*` 才能继续。
- skill 内容需要真实数据拉取、provider publish、accepted latest switch、monitor write、broker/order/quick-trade 才能验证。
- 文档之间对 Agent 路线、DailyAgentPromptArtifact 或 simple-chat 边界存在矛盾。
- 修改过程中发现两个 skills 的触发边界严重冲突，无法用 description 区分。
