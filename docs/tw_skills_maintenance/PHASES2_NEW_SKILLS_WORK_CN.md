# Phase S2 工作文档：新增五个项目级 tw-stock Skills

生成日期：2026-06-19

## 1. 工作结论

Phase S1 已审查通过，允许进入 Phase S2。

本阶段目标是在项目内新增五个台股项目级 skills，使后续新模型、新策略、模块集成、Agent prompt 维护和前端工作台 UX 审查都有明确触发边界与只读安全约束。

新增位置只能是：

```text
.agents/skills/
```

不得恢复或新增用户级：

```text
/home/chuliyang/.agents/skills/tw-stock-*
```

## 2. 本阶段新增 Skills

必须新增：

```text
.agents/skills/tw-stock-new-model-onboarding/SKILL.md
.agents/skills/tw-stock-new-strategy-onboarding/SKILL.md
.agents/skills/tw-stock-modular-integration-regression/SKILL.md
.agents/skills/tw-stock-agent-daily-prompt-maintenance/SKILL.md
.agents/skills/tw-stock-frontend-workbench-ux-review/SKILL.md
```

如需 references，可在各 skill 下新增：

```text
references/
```

本阶段不要求新增 scripts，除非是纯静态/只读辅助脚本，并且执行报告必须说明不用它触发真实写操作。

## 3. 严禁事项

不得修改：

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

不得执行或建议执行：

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
```

本阶段只允许新增 skill 文件和必要 references，并写执行报告。

## 4. 通用 Skill 结构要求

每个新增 `SKILL.md` 必须包含：

```text
YAML frontmatter:
  name
  description

Markdown sections:
  Purpose
  Read First
  Allowed Actions / Evidence
  Forbidden Actions
  Workflow
  Output Format
  Trigger Examples
  Stop Conditions
```

`description` 必须：

- 明确何时触发。
- 说明 skill 做什么。
- 包含真实用户可能说出的触发词。
- 不泛化到所有台股任务。
- 与 S1 四个既有 skills 分工清楚。

## 5. Skill 1：`tw-stock-new-model-onboarding`

### 5.1 用途

用于后续新增、训练、评估、接入台股新模型。

### 5.2 触发场景

应触发于：

```text
新增模型
训练一个新模型
接入新的 qlib/ltr/ensemble 模型
生成 ModelSignalArtifact
评估模型 OOS
把新模型加入 registry
新模型 reviewer checklist
```

不应触发于：

```text
解释 2330 为什么在榜
审查 Agent 回答是否越界
跑 /tw-stock-monitor Playwright 验收
检查 latest_asof 为什么没更新
```

### 5.3 必读文档

必须要求先读：

```text
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
```

如存在 checklist，也应要求读取：

```text
NEW_MODEL_REVIEWER_CHECKLIST_CN.md
```

如果文件不存在，要求报告缺失，不得编造。

### 5.4 必须约束

必须写清：

- 新模型输出必须进入 `ModelSignalArtifact` 或兼容 extension schema。
- 必须有 point-in-time、`available_at`、OOS 区间、数据泄漏检查。
- 必须有 registry entry、validator、golden sample。
- 不得默认切换生产模型。
- 不得改前端默认策略。
- 不得发布 provider。
- 不得切 accepted latest。
- 不得触发 broker/order。
- “收益更高”“胜率更高”必须绑定已验证 OOS 报告，不得作为承诺。

### 5.5 输出格式

必须包含：

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

## 6. Skill 2：`tw-stock-new-strategy-onboarding`

### 6.1 用途

用于新增策略规则、组合策略、候选筛选、再平衡规则、readonly replay 规则。

### 6.2 触发场景

应触发于：

```text
新增策略
改策略规则
做一个组合策略
接入新的 rebalance 规则
生成 OrderIntent
做 readonly replay
新增 replay 规则
```

不应触发于：

```text
新增模型
解释 qlib score
审查 network_audit
检查 Agent prompt latest
```

### 6.3 必读文档

必须要求先读：

```text
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
```

如存在模板/checklist，也应要求读取：

```text
TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md
NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md
```

如果文件不存在，要求报告缺失，不得编造。

### 6.4 必须约束

必须写清：

- 策略输出只能是只读 `OrderIntentArtifact` 或 replay artifact。
- 不得产生真实订单。
- 先写 dependency YAML / rule registry，再写实现。
- 禁止使用未来收益、未来价格、未来标签、同日不可得字段。
- 禁止真实 `target_position`、真实 `target_weight`、broker、quick-trade、order submit。
- replay 必须显式标注模拟、历史、只读。
- 不得默认改当前生产策略或前端默认策略。

### 6.5 输出格式

必须包含：

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

## 7. Skill 3：`tw-stock-modular-integration-regression`

### 7.1 用途

用于只读模块联调与全链路 regression，避免模型、策略、Agent、前端分别通过但链路断裂。

### 7.2 触发场景

应触发于：

```text
做一次模块联调
验证模型到策略再到 Agent 是否打通
跑全链路 readonly regression
检查 artifact registry 和 validators
上线前集成验收
```

不应触发于：

```text
只解释个股为什么在榜
只审查 Agent 回答安全边界
只做 freshness 诊断
只新增模型或策略的单模块接入
```

### 7.3 覆盖链路

必须覆盖：

```text
DataSourceSnapshot
FeatureArtifact
ModelSignalArtifact
StrategyRule
OrderIntentArtifact
ReplayResult
ReadonlyStrategySnapshot
DailyAgentPromptArtifact
Backend API
Frontend Strategy Workbench
Playwright network/console/screenshots
```

### 7.4 必须约束

默认只允许：

```text
validators
fixtures
dry-run
read-only GET
静态检查
Playwright 只读访问
```

不得触发：

```text
真实数据拉取
provider publish
accepted latest switch
monitor config save
monitor scan
alerts write
broker/order
```

报告必须列出每个 artifact 的：

```text
asof
run_id
checksum/latest pointer
validator 结果
```

如果某一环缺 artifact，必须停止在缺口报告，不得用动态服务 payload 假装通过。

## 8. Skill 4：`tw-stock-agent-daily-prompt-maintenance`

### 8.1 用途

用于维护新 Agent 路线，避免后续节点重新走复杂工具 Agent 或绕过 DailyAgentPromptArtifact。

### 8.2 触发场景

应触发于：

```text
修改 Agent prompt
修改 simple-chat
检查 Agent 回答
DailyAgentPromptArtifact validator
OpenAI adapter
今天的策略问答
Agent 不回答
Agent 回答不准
```

不应触发于：

```text
解释 qlib accepted latest 为什么 stale
跑 Playwright UI 验收
新增模型
新增策略
只审查安全边界
```

### 8.3 必读文档

必须要求先读：

```text
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_OPENAI_REBUILD_DESIGN_CN.md
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md
docs/tw_agent_daily_prompt_rebuild/PHASE0_TO_PHASE6_FINAL_SUMMARY_CN.md
```

### 8.4 必须约束

必须写清：

- OpenAI 只能消费 `DailyAgentPromptArtifact` 和用户问题。
- 前端只能调用后端 `/api/tw-stock/agent/simple-chat`。
- OpenAI key 只能在后端环境变量，不得进入前端 bundle、测试截图或日志。
- prompt builder/validator 必须保留 forbidden terms、citation、asof/run_id/checksum 校验。
- 用户的买卖问题必须转为研究解释，不给行动建议。
- 修改 Agent 后至少运行 simple-chat unit/static checks 和 safety-boundary review。

## 9. Skill 5：`tw-stock-frontend-workbench-ux-review`

### 9.1 用途

用于维护 `/tw-stock-monitor` 策略工作台 UX，并把 `frontend-design` 的视觉方法和台股只读边界结合起来。

### 9.2 触发场景

应触发于：

```text
优化前端
审查策略工作台 UI
跑 Playwright 看页面
检查 Agent 面板体验
修 /tw-stock-monitor 重叠/空白/不好用
策略工作台 UX
```

不应触发于：

```text
新增模型
新增策略
解释某个股票为什么在候选名单
检查 Agent prompt latest 为什么没更新
```

### 9.3 必须读取 frontend-design

必须明确要求读取：

```text
.agents/skills/frontend-design/SKILL.md
```

设计方向必须是：

```text
安静、精确、研究工作台
```

不得做：

```text
营销页
大 hero
装饰性背景
渐变光斑
深色霓虹终端风
卡片套卡片
```

### 9.4 必须约束

必须要求 Playwright 证据：

```text
desktop/tablet/mobile screenshots
network audit
console audit
overflowX=false
无明显文字重叠
主要面板不空白
```

必须检查：

```text
首屏信息层级
今日策略摘要
候选池
readonly replay / 历史模拟
模拟账户状态
Agent simple-chat
数据状态
风险提示
技术详情默认折叠
```

前端不得出现：

```text
实盘交易入口
broker
quick-trade
真实 order
target position 设置
OpenAI key
browser-side OpenAI call
```

允许：

```text
填入问题并调用 simple-chat 的快捷问题按钮
```

但按钮不得触发交易、monitor 写入、provider、accepted latest 或日更。

## 10. S2 静态检查

完成后必须运行：

```bash
find .agents/skills/tw-stock-* -maxdepth 2 -name SKILL.md -print | sort
```

必须包含 S1 四个旧 skills + S2 五个新 skills，共九个 `tw-stock-*` SKILL.md。

必须运行红线扫描：

```bash
rg -n "provider publish|accepted latest switch|quick-trade|broker|submit order|place order|target_position|target_weight|OpenAI API key|OPENAI_API_KEY|browser-side OpenAI" .agents/skills/tw-stock-*
```

命中必须逐条归因：

- 禁止动作、Stop Conditions、safety review、deny-list 中的命中允许。
- 鼓励执行真实动作的命中必须修复。

必须运行 description 清单：

```bash
for f in .agents/skills/tw-stock-*/SKILL.md; do head -20 "$f"; done
```

执行报告中必须摘录每个新增 skill 的 name/description。

## 11. 执行报告要求

完成后写：

```text
docs/tw_skills_maintenance/PHASES2_NEW_SKILLS_EXECUTION_REPORT_CN.md
```

报告必须包含：

```text
本阶段目标
新增文件
五个新 skills 的 name/description
五个新 skills 的边界与触发场景
与 S1 四个既有 skills 的分工
Read First 覆盖情况
Allowed / Forbidden Actions 覆盖情况
输出格式覆盖情况
Trigger Examples 与 Stop Conditions
静态红线扫描结果与归因
确认共九个 tw-stock-* skills 位于 .agents/skills
确认用户级原路径没有 tw-stock-* skills
确认未修改业务/前端/模型/策略代码
未解决问题
是否建议进入 S3
```

## 12. 停止条件

遇到以下任一情况必须停止：

- 需要恢复用户级 `/home/chuliyang/.agents/skills/tw-stock-*` 才能继续。
- 新增 skill 与 S1 既有 skill 触发边界严重重叠，无法区分。
- 某 skill 需要真实数据拉取、provider publish、accepted latest switch、monitor write、broker/order/quick-trade 才能验证。
- 新模型/新策略 skill 被要求直接切成默认生产策略。
- 前端 UX skill 被要求加入交易执行入口或真实仓位建议。
- 找不到必读合同文档，且 skill 需要引用其具体要求。
