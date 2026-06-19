# 新模型与新策略开发手册

生成日期：2026-06-17

## 1. 总原则

新模型、新策略必须先进入模块化合同体系，再进入任何 replay、前端、日更、Agent 或生产讨论。不得通过临时脚本、私有字段、前端直读、Agent prompt 或日更脚本绕过合同。

标准链路：

```text
DataSource / PriceStore / FeatureArtifact
  -> Model / ModelAdapter
  -> ModelSignalArtifact
  -> StrategyRule / StrategyDependency
  -> OrderIntentArtifact
  -> ReplayExecution
  -> ReplayResultArtifact
  -> Analysis / Review
```

## 2. 新模型开发规则

新模型必须先输出 raw score，再经 adapter 生成标准 `ModelSignalArtifact`。策略、replay、frontend、Agent 不得直接读取模型私有字段或训练输出。

新模型进入正式候选前至少声明：

```text
artifact_type
schema_version
artifact_name
model_name
asof_date
input_artifacts
feature_dependencies
score_field
capabilities
forbidden_fields audit
no_default_switch
no_provider_publish
no_accepted_latest_switch
diagnostic_only policy, if applicable
```

`ModelSignalArtifact` 必须包含 core fields：

```text
date
instrument
model_name
model_family
candidate_rank
buy_score
raw_score
score_rank
full_qlib_rank
signal_asof
available_at
source_artifact
source_model_artifact
source_feature_artifact
```

新增字段必须走 `ext_*` extension schema，不能复用 core field 改语义。

## 3. 新策略开发规则

新策略只新增 `StrategyRule / StrategyDependency`，不得修改 replay engine 来适配私有模型字段。

新策略至少声明：

```text
required_signal_fields
required_capabilities
required_extensions
forbidden_signal_fields
forbidden_actions
diagnostic_only
applies_to_artifact_names, if limited
OrderIntent output contract
ReplayExecutionEngine remains strategy-agnostic
```

策略输出必须先生成 `OrderIntentArtifact`，不得直接写 replay result、target position、broker order 或 frontend action。

## 4. Replay 与收益结论规则

正式 replay 必须消费 `OrderIntentArtifact` 和 `PriceStore`，不得反向修改模型信号或策略意图。

禁止：

```text
用 smoke artifact 写收益结论
用 diagnostic rule 作为有效策略证据
从 replay result 反推或重写 strategy intent
把 replay result 直接切 default candidate
把 replay result 直接接 broker/order/quick-trade
```

## 5. Smoke / Diagnostic 规则

Smoke 仅用于流程验证，必须声明：

```text
smoke_only=true
not_valid_strategy_evidence=true
no_replay_return_conclusion=true
not_default_candidate=true
production_allowed=false
diagnostic_only=true
```

Smoke strategy dependency 必须使用 `applies_to_artifact_names` 绑定 dummy artifact，避免污染正式 signal validation。

Diagnostic artifact 可以用于审查、排错和 parity 解释，但不能作为 default candidate、正式策略收益证据、前端默认产品展示或生产 consumer 输入。

## 6. Registry 与 Golden Sample

新增能力必须登记 registry，并具备：

```text
artifact_type
schema_version
contract_doc
validator
golden_sample
capabilities
dependencies
allowed_consumers
forbidden_consumers
production_allowed=false
owner_or_stage
```

新增 validator 必须提供 pass/fail golden samples。负例必须验证关键安全字段缺失会失败。

## 7. Frontend / Daily / Agent 边界

前端 readonly display 必须 GET-only，并复跑：

```bash
python scripts/validate_tw_frontend_readonly_m4.py --json
```

日更脚本默认路径不得 provider refresh / publish / accepted latest，并复跑：

```bash
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
```

M0-M6 Agent 仍保持 placeholder / readonly context：

```text
不得改 prompt/tool/action
不得建议买卖
不得输出目标仓位
不得调用 provider/latest/monitor/broker/order
```

## 8. 新开发最小提交流程

1. 写清楚目标属于数据、特征、模型、策略、replay、analysis、frontend readonly 还是 Agent。
2. 补 registry entry 和 contract reference。
3. 产出 manifest / schema / validator。
4. 加 positive / negative golden sample。
5. 若是模型，生成标准 `ModelSignalArtifact`。
6. 若是策略，生成 `StrategyDependency` 和 `OrderIntentArtifact`。
7. 只在 review 通过后进入 replay 或产品展示讨论。
8. 复跑统一回归：

```bash
python scripts/run_tw_modular_contract_regression.py --json
```

## 9. 绝对禁止

```text
真实训练与合同补丁混在一个阶段
未经过 adapter 让策略读取模型私有字段
未经过 OrderIntent 让 replay 读取策略私有状态
把 smoke/diagnostic 当收益证据
自动切 default candidate / default strategy
provider refresh / publish / accepted latest 默认可达
monitor 写入、broker、quick-trade、orders 混入研究阶段
Agent 扩权混入模型/策略开发阶段
```
