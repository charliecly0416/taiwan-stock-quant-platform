# Phase R3 审查报告：Artifact 链路入口确认

生成日期：2026-06-20

## 1. 审查结论

结论：通过，允许进入 Phase R4。

通过性质：`PASS`。

Phase R3 执行报告正确完成了 artifact 链路入口确认：

```text
正确读取并解释 configs/tw_product_artifact_registry.yaml 当前产品路径入口。
确认新模型必须通过 ModelSignalArtifact 接入。
确认新策略必须通过 StrategyRule / StrategyDependency 接入。
确认策略输出只能是 OrderIntentArtifact，Replay 必须是 readonly ReplayResultArtifact。
正确区分 Agent prompt latest、readonly strategy latest、provider/qlib accepted latest 和 frontend defaults。
列出了非阻塞稳定化点，未把缺口伪装为已完成。
未触发真实数据、provider publish、accepted latest、monitor、broker/order、OpenAI、模型训练或策略实现。
```

R3 不需要 repair。

## 2. 审查依据

审查对象：

```text
docs/tw_new_model_strategy_pre_rnd/PHASER3_ARTIFACT_CHAIN_ENTRY_EXECUTION_REPORT_CN.md
docs/tw_new_model_strategy_pre_rnd/PHASER3_ARTIFACT_CHAIN_ENTRY_WORK_CN.md
docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_EXECUTION_AND_REVIEW_PLAN_CN.md
configs/tw_product_artifact_registry.yaml
```

复核的关键合同：

```text
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/TW_MODULAR_PIPELINE_FUTURE_DEVELOPMENT_GUIDE_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md
docs/tw_new_model_strategy_pre_rnd/TW_DAILY_UPDATE_DATA_FLOW_EXPLAINED_FOR_BEGINNERS_CN.md
```

## 3. Findings

### Critical

无。

### High

无。

### Medium

无阻塞项。

R3 明确声明其只确认入口与职责，不验证每个生产 source artifact 的现时存在性，也不生成 artifact。这个边界是正确的；后续真实研发使用具体 artifact 时，仍必须读取 manifest/latest pointer 并运行对应 validator，缺失时停在缺口报告。

### Low

仍需在最终 R4 readiness 中继续保留两类非阻塞提醒：

```text
project-local skills 仍需纳入版本冻结提交范围。
当前运行时可能仍显示 archive 旧 skill metadata，后续执行节点必须显式以 project-local skills 为准。
```

## 4. Registry 入口复核

本地读取 `configs/tw_product_artifact_registry.yaml`，与执行报告一致：

```text
schema_version = tw_product_artifact_registry_v1
profile = strict_e4_yz_product
readonly_only = true
base_model_id = e4_frozen_qlib_2018_2022
treatment_model_id = e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
treatment_display_model_id = e4_frozen_qlib_2023_2025_ltr
default_strategy_rule = top50_exit_one_worst_sell
signal_root = data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals
readonly_strategy_latest = data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
```

安全 flags 存在：

```text
no_training_in_product_context = true
no_provider_publish = true
no_accepted_latest_switch = true
no_monitor_write = true
no_broker_order = true
```

`git diff -- configs/tw_product_artifact_registry.yaml` 为空，未发现 R3 修改 registry。

判定：通过。

## 5. 新模型入口复核

执行报告对新模型入口的判断符合合同：

```text
新模型先产生 raw output。
ModelAdapter 负责映射为 ModelSignalArtifact。
策略、Replay、Frontend、Agent 不得直接读取模型私有产物。
candidate_rank / buy_score / raw_score / score_rank / full_qlib_rank / signal_asof / available_at 等 core fields 语义不得被扩展字段改写。
```

执行报告也正确禁止：

```text
直接改策略
直接改前端默认
直接改 DailyAgentPromptArtifact 默认来源
直接切 provider / qlib accepted latest
直接写 readonly_strategy_latest
default-switch production model
承诺收益、胜率或上涨概率
```

判定：通过。

## 6. 新策略入口复核

执行报告对新策略入口的判断符合合同：

```text
新策略必须先声明 StrategyRule / StrategyDependency。
策略模块只消费 ModelSignalArtifact、PortfolioState、StrategyRuleConfig。
策略输出只能是 OrderIntentArtifact。
ReplayResultArtifact 只能消费 OrderIntentArtifact、PriceStore、ExecutionConfig、InitialPortfolioState。
ReadonlyStrategySnapshot 是前端/API 只读展示入口。
```

执行报告也正确禁止：

```text
真实订单
broker / quick-trade
target_position / target_weight
未来价格、future return、future label、realized pnl
模型私有字段
默认策略切换
provider publish / accepted latest switch
monitor config / scan / alerts write
```

判定：通过。

## 7. Latest / Default 区分复核

R3 正确区分：

```text
frontend display defaults：来自 configs/tw_product_artifact_registry.yaml。
readonly strategy latest：data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json。
Agent prompt latest：data_tw/artifacts/agent_daily_prompt/latest.json。
provider / qlib accepted latest：数据/qlib provider 层高风险入口。
PaperPortfolio state：simulation-only，不代表真实 broker 或目标仓位。
```

关键判断正确：`Agent prompt latest` 和 `readonly strategy latest` 都不是 provider/qlib `accepted latest`，不得混用。

判定：通过。

## 8. 只读安全边界

本轮审查未发现 R3 执行报告包含实际触发以下动作的证据：

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
artifact/latest pointer 生成或发布
```

报告中的 forbidden words 均位于禁止项、边界声明或风险说明语境中。

## 9. R4 准入要求

允许进入 Phase R4：研发入场建议与最终 readiness 总结。

R4 必须输出：

```text
docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_FINAL_SUMMARY_CN.md
```

R4 不得进入新模型/新策略研发；只能基于 R0-R3 审查结果给出是否允许开研发节点、建议先开模型还是策略、第一轮研发边界和执行者第一条命令。
