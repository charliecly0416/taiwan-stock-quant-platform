# Pre-RND Readiness 最终验收审查

生成日期：2026-06-20

## 1. 最终验收结论

结论：通过，可以收尾。

验收性质：`ACCEPTED_WITH_CONDITIONS`。

接受执行者最终总结中的主结论：

```text
有条件通过，只允许进入列明的窄范围新模型/新策略研发。
```

本支线的目标是新模型/新策略研发前 readiness freeze，不是实际研发。R0-R4 已完成版本范围盘点、只读集成回归、skills/runtime 入口确认、artifact 链路入口确认和最终入场建议。当前证据足以关闭 pre-RND readiness 支线，并提交统筹审核。

## 2. 是否完善可收尾

判定：完善，可收尾。

理由：

```text
R0-R3 阶段结论完整汇总。
R1 初始失败和两轮 repair 没有被抹掉，最终状态明确为 PASS_AFTER_REPAIR。
R2 archive metadata 残余风险被保留，不被误判为已彻底消失。
R3 registry/default/latest/artifact 链路入口清楚。
R4 明确回答是否允许开新模型节点、是否允许开新策略节点、是否允许同时开、第一轮建议路线和执行者第一条命令。
严禁事项覆盖真实数据、provider publish、accepted latest、monitor、broker/order、OpenAI、默认路径切换和动态 payload 伪造。
```

不需要执行者 repair。

## 3. Findings

### Critical

无。

### High

无。

### Medium

无阻塞项。

R4 的“有条件通过”判断是正确的：地基回归和入口确认已通过，但项目仍有待冻结文件、archive metadata 残余、生产 source artifacts 物化链路和 Agent prompt latest publish 等非阻塞风险。因此不能给出无条件通过，也不应直接允许大范围研发。

### Low

以下事项必须留给统筹决策，不影响本支线收尾：

```text
是否在正式研发节点前做版本冻结提交或 baseline tag。
是否配置运行时排除 /home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/。
是否要求第一轮新模型节点先提交独立 work doc 后再允许训练或 artifact 生成。
是否要求第一轮研发先复跑 R1R2 full modular regression 作为基线。
```

## 4. 对执行者最终总结的审查

审查对象：

```text
docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_FINAL_SUMMARY_CN.md
```

该总结满足 R4 工作文档要求：

```text
给出三类结论之一：有条件通过。
汇总 R0-R3 阶段结论。
明确 R1 = PASS_AFTER_REPAIR。
保留 R2 runtime archive metadata 风险。
明确当前已通过的地基能力。
保留非阻塞风险。
回答是否允许开新模型节点。
回答是否允许开新策略节点。
回答是否允许同时开模型和策略节点。
推荐第一轮研发路线。
给出第一轮执行者命令。
列出严禁事项。
列出需要审查者最终验收的问题。
```

判定：通过。

## 5. 最终允许范围

允许开新模型节点：允许，但仅限窄范围。

允许内容：

```text
raw score
ModelAdapter
ModelSignalArtifact
registry entry
golden sample
OOS evidence
validator
review report
```

条件：

```text
production_allowed=false。
不改当前默认模型。
不改前端默认。
不改 DailyAgentPromptArtifact 默认来源。
不切 provider / qlib accepted latest。
不切 readonly_strategy_latest。
不承诺收益、胜率或上涨概率。
```

允许开新策略节点：允许，但仅限窄范围。

允许内容：

```text
StrategyDependency
StrategyRule
OrderIntentArtifact
readonly ReplayResultArtifact
validator
golden sample
review report
```

条件：

```text
不改模型。
不读取模型私有字段。
不改前端默认。
不输出 target_position / target_weight。
不连接 broker / quick-trade / order。
不切默认策略。
```

是否允许同时开模型和策略节点：不建议，不应作为第一轮研发方式。

第一轮研发限制：必须限制为单变量，单模型或单策略。

第一轮推荐：路线 A，单新模型节点。

## 6. 必须保留的启动约束

后续任何研发节点必须继承：

```text
以 project-local .agents/skills/tw-stock-* 为准。
不得把 /home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/ 当作 active skill 来源。
如运行时自动触发 archive 旧 skill 描述，必须停止并报告。
不得切当前产品默认模型、默认策略、前端默认展示或 latest/default 路径。
不得用动态服务 payload 假装 artifact 链路已经存在。
任一 artifact、manifest、latest pointer、source link 或 validator 缺失时，停在缺口报告。
```

## 7. 严禁事项

正式进入第一轮研发后仍严禁：

```text
真实数据拉取
provider refresh / publish
accepted latest switch
monitor config / scan / alerts 写入
broker / quick-trade / order
target_position / target_weight 写入
OpenAI key 读取
真实 OpenAI smoke
生成或发布 production artifact/latest pointer
让 Agent 扩权或绕过 DailyAgentPromptArtifact
把 smoke/diagnostic 当收益证据
```

## 8. 统筹需决策事项

建议统筹审核时确认：

```text
1. 是否接受本支线以 ACCEPTED_WITH_CONDITIONS 收尾。
2. 是否在正式研发节点前做版本冻结提交或 baseline tag。
3. 是否批准第一轮研发走单新模型节点。
4. 是否要求第一轮新模型节点先提交 work doc，再允许训练或 artifact 生成。
5. 是否要求第一轮研发启动前复跑 full modular regression 作为基线。
6. 是否需要运行时配置排除 archive skill 目录。
```

## 9. 本支线收尾结论

本支线可以关闭。

后续建议进入：

```text
第一轮窄范围新模型研发准备节点
```

但该节点必须先写独立工作文档，并以 `tw-stock-new-model-onboarding` project-local skill 与新模型合同/checklist 为准。
