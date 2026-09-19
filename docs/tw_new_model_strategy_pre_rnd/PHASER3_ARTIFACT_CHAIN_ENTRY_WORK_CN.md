# Phase R3 工作文档：Artifact 链路入口确认

生成日期：2026-06-20

## 1. 工作结论

Phase R2 已审查通过，允许进入 Phase R3。

R3 的目标是确认新模型/新策略研发前的 artifact 链路入口是否清晰、是否仍遵守当前产品默认路径、是否明确后续研发只能通过合同产物接入。

本阶段不是新模型或新策略研发，不允许训练模型、实现策略、切默认路径或触发真实生产链路。

## 2. 运行时 skill 约束

执行者启动前必须明确：

```text
以 project-local .agents/skills/tw-stock-* 为准。
不得把 /home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/ 下的旧 skills 当作 active 来源。
如当前运行时自动触发到 archive 旧 skill 描述，必须停止并在报告中说明，不得继续执行。
```

本阶段主要参考：

```text
.agents/skills/tw-stock-new-model-onboarding/SKILL.md
.agents/skills/tw-stock-new-strategy-onboarding/SKILL.md
.agents/skills/tw-stock-modular-integration-regression/SKILL.md
.agents/skills/tw-stock-safety-boundary-review/SKILL.md
```

## 3. 严禁事项

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
```

不得用动态服务 payload 假装 artifact 链路已经存在；如 artifact、manifest、latest pointer 或 source link 缺失，必须列为缺口。

## 4. 执行报告输出

执行者必须输出：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER3_ARTIFACT_CHAIN_ENTRY_EXECUTION_REPORT_CN.md
```

## 5. 必读文件

执行者必须只读检查：

```text
configs/tw_product_artifact_registry.yaml
docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_EXECUTION_AND_REVIEW_PLAN_CN.md
docs/tw_new_model_strategy_pre_rnd/TW_DAILY_UPDATE_DATA_FLOW_EXPLAINED_FOR_BEGINNERS_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/TW_MODULAR_PIPELINE_FUTURE_DEVELOPMENT_GUIDE_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md
```

如任一必读文件缺失，停止并报告，不得自行发明合同要求。

## 6. 必须确认项

### 6.1 当前产品 registry 入口

对照 `configs/tw_product_artifact_registry.yaml`，列出并解释当前产品路径入口：

```text
base_model_id
treatment_model_id
default_strategy_rule
signal_root
readonly_strategy_latest
price sources
safety flags / readonly flags
```

要求：

```text
不得修改 registry。
不得把未来新模型或新策略写入默认路径。
不得把缺失项解释为已经接入。
```

### 6.2 新模型入口

必须确认：

```text
新模型只能通过 ModelSignalArtifact 接入。
新模型输出必须经过 adapter 映射到合同字段或声明的 ext_* 字段。
新模型不得直接改策略、前端默认、DailyAgentPromptArtifact 默认来源或生产 latest。
```

至少说明以下字段/语义：

```text
candidate_rank
buy_score
raw_score
score_rank
full_qlib_rank
signal_asof
available_at
source artifact links
manifest / checksum / validator
```

### 6.3 新策略入口

必须确认：

```text
新策略只能通过 StrategyRule / StrategyDependency 接入。
新策略输出只能是 OrderIntentArtifact。
Replay 必须是历史模拟、readonly 的 ReplayResultArtifact。
新策略不得产生真实订单、broker 指令、target_position、target_weight 或默认策略切换。
```

至少说明以下链路：

```text
StrategyRule / StrategyDependency
-> OrderIntentArtifact
-> ReplayResultArtifact
-> ReadonlyStrategySnapshot
```

### 6.4 全链路入口图

报告中必须明确后续新模型/新策略标准链路：

```text
DataSource / PriceStore / FeatureArtifact
-> ModelSignalArtifact
-> StrategyRule / StrategyDependency
-> OrderIntentArtifact
-> ReplayResultArtifact
-> ReadonlyStrategySnapshot
-> DailyAgentPromptArtifact
-> API / Frontend
```

要求区分：

```text
Agent prompt latest
provider / qlib accepted latest
readonly strategy latest
frontend display defaults
```

不得混淆这些 latest/default 的职责。

### 6.5 非阻塞稳定化点

必须列出当前仍需未来稳定化、但不阻塞 R3 入口确认的事项，例如：

```text
生产 source artifacts 物化链路仍需后续明确。
Agent prompt latest publish 默认关闭，需要在未来 release 节点单独验收。
legacy provider publish / accepted latest 代码仍存在，但当前默认路径不可达。
新模型/新策略不得直接切当前产品默认路径。
project-local skills 仍需纳入最终版本冻结提交范围。
```

如执行者发现新增稳定化点，应列入报告，不得隐去。

## 7. 建议只读检查命令

可执行：

```bash
sed -n '1,260p' configs/tw_product_artifact_registry.yaml
rg -n "base_model_id|treatment_model_id|default_strategy_rule|signal_root|readonly_strategy_latest|price|readonly|production|accepted|latest" configs/tw_product_artifact_registry.yaml docs/tw_modular_contracts docs/tw_new_model_strategy_pre_rnd/TW_DAILY_UPDATE_DATA_FLOW_EXPLAINED_FOR_BEGINNERS_CN.md
rg -n "ModelSignalArtifact|StrategyRule|StrategyDependency|OrderIntentArtifact|ReplayResult|ReadonlyStrategySnapshot|DailyAgentPromptArtifact" docs/tw_modular_contracts docs/tw_new_model_strategy_pre_rnd/TW_DAILY_UPDATE_DATA_FLOW_EXPLAINED_FOR_BEGINNERS_CN.md
```

这些命令只允许读取文件。不得运行会生成、发布、切换或写入 artifact/latest 的命令。

## 8. 报告格式

请输出：

```markdown
# Phase R3 执行报告：Artifact 链路入口确认

## 1. 结论
## 2. Registry 当前产品入口
## 3. 新模型入口：ModelSignalArtifact
## 4. 新策略入口：StrategyRule / OrderIntent / Replay
## 5. 标准 artifact 链路图
## 6. Latest / Default 职责区分
## 7. 非阻塞稳定化点
## 8. 只读安全边界
## 9. 是否建议进入 R4
```

## 9. R3 通过标准

R3 可通过必须满足：

```text
正确解释 configs/tw_product_artifact_registry.yaml 的当前产品路径入口。
确认新模型必须从 ModelSignalArtifact 接入。
确认新策略必须从 StrategyRule / StrategyDependency 进入，并输出 OrderIntentArtifact 与 readonly ReplayResultArtifact。
正确区分 Agent prompt latest、provider/qlib accepted latest、readonly strategy latest 和 frontend defaults。
列出非阻塞稳定化点，不把它们伪装成已完成。
未触发真实数据、provider publish、accepted latest、monitor、broker/order、OpenAI key、模型训练或策略实现。
```
