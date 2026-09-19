# Phase S1 工作文档：修改既有四个 tw-stock-* Skills

生成日期：2026-06-19

## 1. 工作结论

Phase S0 已审查通过，允许进入 Phase S1。

本阶段目标是更新四个既有台股 skills，使它们覆盖当前项目主线：

```text
模块化合同
只读研究边界
DailyAgentPromptArtifact
Agent simple-chat
前端策略工作台 UI2
readonly Playwright 验收
新模型/新策略扩展接入
```

本阶段只维护 skills，不修改台股业务代码、前端产品代码、模型策略默认行为或真实运维链路。

## 2. 本阶段范围

需要更新的四个既有 skills：

```text
tw-stock-safety-boundary-review
tw-stock-readonly-e2e-acceptance
tw-stock-research-context-analyst
tw-stock-data-freshness-diagnosis
```

本阶段落点采用 S0 审查结论：

```text
先在 repo 内 .agents/skills/tw-stock-* 建立版本化副本并修改。
不得直接覆盖用户级 /home/chuliyang/.agents/skills/tw-stock-*。
```

## 3. 必须先复制的源目录

执行者必须从用户级旧目录复制为 repo 内版本化副本：

```text
/home/chuliyang/.agents/skills/tw-stock-safety-boundary-review
-> .agents/skills/tw-stock-safety-boundary-review

/home/chuliyang/.agents/skills/tw-stock-readonly-e2e-acceptance
-> .agents/skills/tw-stock-readonly-e2e-acceptance

/home/chuliyang/.agents/skills/tw-stock-research-context-analyst
-> .agents/skills/tw-stock-research-context-analyst

/home/chuliyang/.agents/skills/tw-stock-data-freshness-diagnosis
-> .agents/skills/tw-stock-data-freshness-diagnosis
```

复制时必须保留已有：

```text
SKILL.md
references/
scripts/
```

如某目录不存在 `references/` 或 `scripts/`，按实际情况记录，不要伪造。

## 4. 严禁事项

不得执行：

```text
删除用户级 skills
覆盖用户级 skills
重命名用户级 skills
移动用户级 skills
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

本阶段只允许：

```text
复制旧 skills 到 repo 内
编辑 repo 内 .agents/skills/tw-stock-*/SKILL.md
必要时编辑 repo 内 references/
必要时补充 repo 内 scripts/ 的说明文档，但不要运行高风险脚本
写执行报告
```

## 5. 通用 Skill 编写要求

每个更新后的 `SKILL.md` 必须包含：

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

- 明确什么时候触发。
- 写清 skill 做什么。
- 包含关键触发词。
- 不泛化到所有台股问题。
- 不与其他台股 skill 大面积重叠。

每个 skill 必须保留：

- 旧 skill 的核心能力。
- 只读边界。
- 禁止真实交易和真实运维动作的边界。

长内容可以拆到 `references/`，但 `SKILL.md` 本体必须能独立说明：

```text
何时触发
先读什么
做什么
不能做什么
输出什么
何时停止
```

## 6. Skill 1：`tw-stock-safety-boundary-review`

### 6.1 必须补充的审查对象

加入：

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

### 6.2 必须补充的安全边界

明确：

```text
/api/tw-stock/agent/simple-chat 是允许的只读后端解释接口
前端不得出现 OpenAI API key
前端不得出现 OpenAI base URL
前端不得 browser-side OpenAI call
OpenAI key 只能在后端环境变量中读取
```

### 6.3 必须补充的英文危险语义

加入：

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

必须说明：这些词可出现在拒答、安全声明、只读 flags、历史模拟术语或测试 forbidden list 中；只有形成行动指令、真实入口、写接口或投资建议时才失败。

### 6.4 Agent answer 检查

必须加入：

- 不得伪造 citation。
- 不得把 qlib score 解释为收益率、胜率、上涨概率或买入概率。
- 不得输出买卖行动建议。
- 不得输出目标仓位/目标权重。
- 买卖问题必须转为研究解释或拒答。

### 6.5 UI 文案检查

允许：

```text
观察优先级
人工复盘
研究排序
候选调入
调出复核
历史模拟
模拟账户
策略解释助手
```

避免：

```text
该买
该卖
仓位建议
目标仓位
保证收益
上涨概率
自动下单
```

## 7. Skill 2：`tw-stock-readonly-e2e-acceptance`

### 7.1 必须扩展验收范围

加入：

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

### 7.2 必须扩展 Playwright 要求

加入：

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

### 7.3 必须扩展 network/console 指标

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
simple_chat_request_count 可为 0 或 1，取决于验收是否点击 Agent
frontend_openai_direct_request_count=0
broker_quick_trade_order_request_count=0
```

### 7.4 simple-chat 规则

明确：

```text
前端主路径只能调用 /api/tw-stock/agent/simple-chat
不能把旧 /agent/chat 作为主路径
不能暴露 OpenAI key
不能 browser-side 直连 OpenAI
simple-chat payload 不能包含 target_position / target_weight / order execution 字段
```

## 8. Skill 3：`tw-stock-research-context-analyst`

### 8.1 必须扩展允许证据

加入：

```text
current-strategy-context
readonly-strategy-snapshot
DailyAgentPromptArtifact 摘要
paper portfolio gate
readonly replay result summary
Agent context_digest
```

### 8.2 当前默认研究口径

必须明确：

```text
当前默认研究口径为 E4 Qlib + Orthogonal LTR
LTR 是在 qlib top50 内做重排
candidate_rank / buy_score / full_qlib_rank 只能作为研究排序
这些分数不是收益率、胜率、上涨概率或买入概率
```

如果代码/数据字段实际使用 `score_rank`、`candidate_rank`、`full_qlib_rank`，也要兼容说明，不强造不存在字段。

### 8.3 新工作台问题处理

以下问题必须触发或适用：

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
人工复盘建议
```

不得给交易动作。

### 8.4 可追溯字段

回答必须优先引用可追溯字段：

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

不得臆造今日结论。

## 9. Skill 4：`tw-stock-data-freshness-diagnosis`

### 9.1 必须区分四类 latest

加入：

```text
provider raw/latest
qlib accepted latest
readonly strategy snapshot latest
Agent DailyAgentPromptArtifact latest
```

### 9.2 Agent prompt latest 解释

必须明确：

```text
Agent prompt latest 落后不等于 provider/qlib 数据落后
它可能只是 prompt builder 未运行、validator 未通过、latest pointer 未更新或 artifact 未发布
```

### 9.3 允许证据

加入只读检查建议：

```text
artifact manifest
latest pointer
DailyAgentPromptArtifact manifest/checksum
readonly strategy snapshot manifest/latest
```

只允许读取，不允许触发构建、刷新、发布或切换。

### 9.4 输出下游影响

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

## 10. Trigger prompts 与 near-miss prompts

每个 skill 至少准备：

```text
3 个 should_trigger prompts
2 个 should_not_trigger near-miss prompts
```

S1 可先写入执行报告；S3 再整理为 eval JSON。

### 10.1 `tw-stock-safety-boundary-review` 示例

should_trigger：

```text
审查这个 Agent 回答有没有越过只读边界
检查 network_audit.json 里有没有 forbidden request
审查 /tw-stock-monitor 文案是否把 Agent 做成交易助手
```

should_not_trigger：

```text
解释 2330 为什么在候选名单里
检查 latest_asof 为什么没更新
```

### 10.2 `tw-stock-readonly-e2e-acceptance` 示例

should_trigger：

```text
跑一次 /tw-stock-monitor 只读验收
审查 Playwright network/console/screenshot 产物能不能接受
确认策略工作台 UI2 是否最终通过
```

should_not_trigger：

```text
帮我新增一个模型
解释 qlib score 是什么意思
```

### 10.3 `tw-stock-research-context-analyst` 示例

should_trigger：

```text
今天策略是什么？
2330 为什么排名第一？
今天有哪些候选调入，能不能买？
```

should_not_trigger：

```text
审查这个 diff 是否有 order submit 风险
跑 Playwright 验收截图
```

### 10.4 `tw-stock-data-freshness-diagnosis` 示例

should_trigger：

```text
为什么 Agent prompt latest 还是昨天？
qlib accepted latest 和 readonly snapshot latest 不一致怎么办？
检查 latest_asof 为什么没更新
```

should_not_trigger：

```text
新增一个策略规则
审查 Agent 回答有没有目标仓位建议
```

## 11. 静态红线扫描

完成后必须运行：

```bash
rg -n "provider publish|accepted latest switch|quick-trade|broker|submit order|place order|target_position|target_weight|OpenAI API key|OPENAI_API_KEY" .agents/skills/tw-stock-*
```

命中必须逐条归因：

- 禁止动作列表、拒答规则、审查规则中的命中允许。
- 如果命中是在鼓励执行真实动作，必须修复。

还必须运行：

```bash
find .agents/skills/tw-stock-* -maxdepth 2 -type f | sort
```

确认四个 repo 内 skill 目录与资源完整。

## 12. 执行报告要求

完成后写：

```text
docs/tw_skills_maintenance/PHASES1_EXISTING_SKILLS_UPDATE_EXECUTION_REPORT_CN.md
```

报告必须包含：

```text
本阶段目标
已阅读文档
复制来源与 repo 内落点
修改/新增文件
四个 skills 的 description 变化
四个 skills 的新增覆盖点
四个 skills 的保留旧能力说明
Trigger prompts 与 near-miss prompts
静态红线扫描结果与归因
确认未修改用户级 skills
确认未修改业务/前端/模型/策略代码
未解决问题
给审查者的重点
```

## 13. 停止条件

遇到以下任一情况必须停止并报告：

- 无法读取用户级旧 skill 源目录。
- 复制到 repo 内时发现同名 repo 目录已有内容且无法判断是否用户修改。
- 需要覆盖用户级 skills 才能继续。
- skill 内容需要真实数据拉取、provider publish、accepted latest switch、monitor write、broker/order/quick-trade 才能验证。
- 文档之间对 Agent 路线、DailyAgentPromptArtifact 或 simple-chat 边界存在矛盾。
- 修改过程中发现两个 skills 的触发边界严重冲突，无法用 description 区分。
