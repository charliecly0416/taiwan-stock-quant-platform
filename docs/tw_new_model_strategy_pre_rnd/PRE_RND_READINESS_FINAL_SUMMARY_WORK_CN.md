# Phase R4 工作文档：Pre-RND Readiness 最终总结与研发入场建议

生成日期：2026-06-20

## 1. 工作结论

Phase R3 已审查通过，允许进入 Phase R4。

R4 的目标是输出新模型/新策略研发前最终 readiness 总结，明确是否允许进入研发、允许进入哪类研发、第一轮研发应如何收窄边界。

本阶段仍不是新模型或新策略研发。

## 2. 严禁事项

不得执行或触发：

```text
训练新模型
新增策略规则
修改默认模型或默认策略
修改前端默认展示
真实数据拉取
provider refresh / publish
accepted latest switch
monitor config / scan / alerts 写入
broker / quick-trade / order
target_position / target_weight 写入
OpenAI key 读取
真实 OpenAI smoke
生成或发布 artifact/latest pointer
```

不得用 R4 总结替代后续新模型或新策略的合同、validator、golden sample、OOS/replay evidence。

## 3. 运行时 skill 约束

R4 必须继续声明：

```text
后续执行节点以 project-local .agents/skills/tw-stock-* 为准。
不得把 /home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/ 下的旧 skills 当作 active 来源。
如运行时自动触发到 archive 旧 skill 描述，必须停止并报告。
```

## 4. 执行报告输出

执行者必须输出：

```text
docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_FINAL_SUMMARY_CN.md
```

## 5. 必读输入

执行者必须只读汇总：

```text
docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_EXECUTION_AND_REVIEW_PLAN_CN.md
docs/tw_new_model_strategy_pre_rnd/PHASER0_VERSION_FREEZE_INVENTORY_EXECUTION_REPORT_CN.md
docs/tw_new_model_strategy_pre_rnd/PHASER0_VERSION_FREEZE_INVENTORY_REVIEW_CN.md
docs/tw_new_model_strategy_pre_rnd/PHASER1_READONLY_INTEGRATION_REGRESSION_EXECUTION_REPORT_CN.md
docs/tw_new_model_strategy_pre_rnd/PHASER1_READONLY_INTEGRATION_REGRESSION_REVIEW_CN.md
docs/tw_new_model_strategy_pre_rnd/PHASER1_REPAIR_REVIEW_CN.md
docs/tw_new_model_strategy_pre_rnd/PHASER1R2_REMAINING_REGRESSION_REPAIR_REVIEW_CN.md
docs/tw_new_model_strategy_pre_rnd/PHASER2_SKILL_RUNTIME_ENTRY_EXECUTION_REPORT_CN.md
docs/tw_new_model_strategy_pre_rnd/PHASER2_SKILL_RUNTIME_ENTRY_REVIEW_CN.md
docs/tw_new_model_strategy_pre_rnd/PHASER3_ARTIFACT_CHAIN_ENTRY_EXECUTION_REPORT_CN.md
docs/tw_new_model_strategy_pre_rnd/PHASER3_ARTIFACT_CHAIN_ENTRY_REVIEW_CN.md
configs/tw_product_artifact_registry.yaml
docs/tw_new_model_strategy_pre_rnd/TW_DAILY_UPDATE_DATA_FLOW_EXPLAINED_FOR_BEGINNERS_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md
docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md
```

如某个 review/report 文件缺失，必须列为输入缺口，不得假设通过。

## 6. 必须汇总的阶段结论

R4 必须按阶段汇总：

```text
R0：版本冻结与范围盘点结论、仍需纳入冻结的文件范围。
R1：只读集成回归初始失败项、repair 后通过状态。
R2：project-local skills 与运行时入口状态、archive metadata 残余风险。
R3：artifact 链路入口、registry/default/latest 职责区分。
```

必须明确 R1 最终状态是：

```text
PASS_AFTER_REPAIR
```

不得只写“R1 通过”而遗漏曾经的失败项和 repair 证据。

## 7. 最终结论格式

R4 必须给出以下三类之一：

```text
通过，可以进入新模型/新策略研发。
有条件通过，只允许进入列明的窄范围研发。
不通过，必须先修复列明阻塞项。
```

建议执行者优先判断是否应给出：

```text
有条件通过，只允许进入列明的窄范围研发。
```

原因：R0-R3 地基已通过，但 project-local skills 和文档/合同仍处于待冻结状态，且第一轮研发不建议同时改新模型和新策略。

## 8. 必须回答的问题

R4 必须逐项回答：

```text
是否允许开新模型节点？
是否允许开新策略节点？
是否允许同时开模型和策略节点？
第一轮研发是否必须限制为单模型或单策略？
建议第一轮优先路线是新模型还是新策略？
执行者第一条命令是什么？
```

建议默认判断：

```text
允许开新模型节点：可以，但必须只走 ModelSignalArtifact，不切默认。
允许开新策略节点：可以，但必须只走 StrategyDependency / StrategyRule / OrderIntentArtifact / readonly ReplayResultArtifact，不切默认。
不建议同时开模型和策略节点。
第一轮必须限制为单变量：单模型或单策略。
```

## 9. 第一轮研发边界建议

R4 必须给出两条候选路线，并推荐其中一条。

### 路线 A：新模型研发

范围：

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

不得：

```text
改策略
改前端默认
改 DailyAgentPromptArtifact 默认来源
切 provider / qlib accepted latest
切 readonly_strategy_latest
default-switch production model
```

### 路线 B：新策略研发

范围：

```text
StrategyDependency
StrategyRule
OrderIntentArtifact
readonly ReplayResultArtifact
validator
golden sample
review report
```

不得：

```text
改模型
读取模型私有字段
改前端默认
输出 target_position / target_weight
连接 broker / quick-trade / order
切默认策略
```

## 10. 必须保留的非阻塞风险

R4 必须保留：

```text
project-local skills 仍需纳入最终版本冻结提交范围。
当前运行时可能仍显示 archive 旧 skill metadata；后续节点必须显式以 project-local skills 为准。
生产 source artifacts 物化链路仍需后续明确和稳定化。
Agent prompt latest publish 默认关闭/dry-run，未来 release 需单独验收。
legacy provider publish / accepted latest 代码仍存在，但当前默认路径不可达。
新模型/新策略不得直接切当前产品默认路径。
```

## 11. 报告格式

请输出：

```markdown
# Pre-RND Readiness 最终总结

## 1. 最终结论
## 2. R0-R3 阶段汇总
## 3. 当前已通过的地基能力
## 4. 仍需保留的非阻塞风险
## 5. 是否允许开新模型节点
## 6. 是否允许开新策略节点
## 7. 是否允许同时开模型和策略节点
## 8. 第一轮研发建议路线
## 9. 第一轮执行者命令
## 10. 严禁事项
## 11. 需要审查者最终验收的问题
```

## 12. 审查入口

执行者完成后，审查者应审查：

```text
docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_FINAL_SUMMARY_CN.md
```

审查者最终验收输出：

```text
docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_FINAL_ACCEPTANCE_REVIEW_CN.md
```
