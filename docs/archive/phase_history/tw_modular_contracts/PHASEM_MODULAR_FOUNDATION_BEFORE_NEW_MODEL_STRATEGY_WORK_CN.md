# Phase M 主线工作文档：新模型/新策略开发前的模块化地基整理

生成日期：2026-06-17

## 1. 背景

D8 已经完成 readonly replay window 产品化收口。当前核心研究链路已经解耦：

```text
ModelSignalArtifact
  -> StrategyRule / StrategyDecisionEngine
  -> OrderIntentArtifact
  -> ReplayExecutionEngine
  -> ReplayResultArtifact
  -> ReplayWindowPolicy
  -> readonly API
  -> frontend readonly display
```

但在进入新模型、新策略开发前，仍需要补齐工程地基。目标不是继续跑收益，也不是新增模型或策略，而是让后续开发更简单、更规范、更不容易偏离主线。

本 M 主线只做：

```text
contracts
schemas
registry
validators
templates
golden samples
frontend display boundary
daily orchestration boundary
existing two-hour auto-update script boundary
frontend embedded agent readonly boundary placeholder
developer/reviewer workflow
```

本 M 主线不做：

```text
不训练新模型
不新增正式策略
不跑新收益结论
不切默认策略
不触发 provider publish / refresh
不切 accepted latest
不改 monitor / broker / quick-trade / order
不改前端嵌入 Agent 行为
不新增 Agent tool / action / prompt 能力
```

## 2. M 主线目标

M 主线要把后续新增数据、特征、模型、策略、回放、日更和前端展示都接入统一模块规范。

最终希望达到：

```text
新增数据 -> 按 DataSource/DataIngestion 合同落盘
新增特征 -> 按 FeatureArtifact 合同和 PIT validator 生成
新增模型 -> 只输出 raw score，再经 ModelAdapter 变成 ModelSignalArtifact
新增策略 -> 只新增 StrategyRule + dependency，不改 replay engine
新增回放 -> 只消费 OrderIntentArtifact，不读模型私有字段
新增展示 -> 只读 API/Frontend 只展示标准 artifact，不本地计算
新增日更 -> DailyOrchestrator 只串接标准模块，失败可回滚
既有两小时自动脚本 -> 保留调度职责，但不直接承载抓取/特征/模型/策略/展示业务逻辑
```

特别说明：项目里之前维护过“每隔两小时拉取新数据，拉到后更新数据、分析并展示到前端”的全自动链路。M 主线不是要废弃这个能力，而是要把它纳入 `DailyOrchestrator / RunRegistry` 合同。正确方向是：

```text
自动脚本保留
  -> 只负责调度、状态、重试、失败关闭、latest pointer policy
各业务步骤模块化
  -> DataIngestion / FeatureArtifact / ModelSignal / StrategyDecision / ReadonlySnapshot / ReplayWindow
```

自动脚本不得继续作为“什么都做的大脚本”扩张。后续新增数据、模型、策略时，必须先实现标准模块，再由自动脚本串联。

另外，项目里之前也做过前端嵌入小 Agent。该 Agent 在 M 主线中只做合同占位和边界冻结，不进入 M0-M6 的功能实现范围。M4 前端整理不得顺手修改 Agent 行为、prompt、tool 权限或动作入口。Agent 应在 M 主线收口后另开专项主线。

## 3. 总体分阶段

建议 M 主线分为 6 轮：

```text
M0 Contract Gap Closure
M1 Validator and Golden Sample Foundation
M2 Registry and Onboarding Templates
M3 Daily Orchestrator and Latest Pointer Boundary
M4 Frontend Readonly Display Refactor Contract
M5 New Model / New Strategy Dry-Run Harness
M6 Final Acceptance and Developer Guide
```

每轮都必须由执行者写执行报告，再由审查者审查。每轮审查通过后才能进入下一轮。

## 4. Phase M0：合同缺口冻结

### 4.1 目标

补齐当前还没有正式合同的模块。

M0 只写文档和 schema 设计，不写生产代码，不跑新模型，不跑 replay。

### 4.2 必须新增或完善的合同

新增：

```text
docs/tw_modular_contracts/DATA_SOURCE_CONTRACT_CN.md
docs/tw_modular_contracts/DATA_INGESTION_ARTIFACT_CONTRACT_CN.md
docs/tw_modular_contracts/FEATURE_ARTIFACT_CONTRACT_CN.md
docs/tw_modular_contracts/PRICE_STORE_CONTRACT_CN.md
docs/tw_modular_contracts/DAILY_ORCHESTRATOR_CONTRACT_CN.md
docs/tw_modular_contracts/RUN_REGISTRY_CONTRACT_CN.md
docs/tw_modular_contracts/AUTO_UPDATE_ORCHESTRATOR_CONTRACT_CN.md
docs/tw_modular_contracts/ANALYSIS_ARTIFACT_CONTRACT_CN.md
docs/tw_modular_contracts/FRONTEND_READONLY_DISPLAY_CONTRACT_CN.md
docs/tw_modular_contracts/AGENT_READONLY_CONTEXT_CONTRACT_CN.md
docs/tw_modular_contracts/FRONTEND_AGENT_PANEL_CONTRACT_CN.md
docs/tw_modular_contracts/DEFAULT_CANDIDATE_DECISION_CONTRACT_CN.md
```

更新：

```text
docs/tw_modular_contracts/TW_MODULAR_PIPELINE_FUTURE_DEVELOPMENT_GUIDE_CN.md
docs/tw_modular_contracts/READONLY_REPLAY_WINDOW_PRODUCTIZATION_GUIDE_CN.md
docs/README_CN.md
```

### 4.3 合同必须覆盖的关键字段

DataSource / DataIngestion：

```text
source_name
provider
raw_path
normalized_path
symbol_mapping_version
asof_date
available_at
coverage_audit
schema_audit
no_provider_publish
no_accepted_latest_switch
```

FeatureArtifact：

```text
feature_date
instrument
feature_name
feature_value
source_data_artifact
lookback_window
signal_asof
available_at
pit_policy
forbidden_future_field_audit
```

PriceStore：

```text
price_date
instrument
open
close
adj_factor
tradable_flag
halt_flag
next_day_execution_availability
price_source
adjustment_policy
coverage_audit
```

DailyOrchestrator / RunRegistry：

```text
run_id
run_asof
schedule_interval
trigger_reason
data_freshness_check_result
input_artifacts
output_artifacts
validation_results
latest_pointer_policy
failure_mode
rollback_policy
keep_previous_latest_on_failure
```

AutoUpdateOrchestrator：

```text
poll_interval_hours
fresh_data_detected
no_new_data_noop
module_call_sequence
module_result_status
retry_policy
failure_closes_without_publish
previous_latest_preserved
readonly_latest_update_only_after_all_validators_pass
does_not_switch_provider_accepted_latest
does_not_place_orders
```

FrontendReadonlyDisplay：

```text
allowed_primary_fields
allowed_audit_fields
hidden_audit_fields
forbidden_text
forbidden_requests
component_boundary
GET-only API dependency
```

AgentReadonlyContext / FrontendAgentPanel：

```text
allowed_context_sources
readonly_artifact_only
allowed_question_types
forbidden_answer_semantics
forbidden_tool_calls
no_order_action
no_target_position
no_provider_publish
no_accepted_latest_switch
no_monitor_write
no_broker_or_order
not_in_m0_m6_implementation_scope
future_agent_phase_required
```

DefaultCandidateDecision：

```text
候选模型/策略如何比较
必须使用哪些 OOS 证据
必须展示哪些风险指标
如何标记 diagnostic-only
如何保留旧默认
如何回滚
默认策略切换必须用户确认
```

### 4.4 M0 禁止事项

```text
不新增模型训练
不新增策略收益回放
不接 API/前端
不修改前端 Agent panel、prompt、tool 权限或 action 入口
不修改日更脚本行为
不重写或替换既有两小时自动脚本
不切 latest pointer
不切默认策略
不触发 provider / accepted latest / monitor / broker / order
```

### 4.5 M0 通过标准

```text
所有新增合同存在
每个合同定义输入、输出、manifest、forbidden fields、forbidden actions
每个合同列出最小 validator 要求
未来开发总规范已链接这些合同
没有生产代码或收益产物变更
```

## 5. Phase M1：Validator 与 Golden Sample 地基

### 5.1 目标

为 M0 合同建立最小 validator 和 golden sample。后续新增模型/策略前，必须能用这些 validator 证明产物合规。

### 5.2 必须新增 validator

建议新增：

```text
scripts/validate_tw_data_ingestion_artifact.py
scripts/validate_tw_feature_artifact.py
scripts/validate_tw_price_store.py
scripts/validate_tw_daily_orchestrator_run.py
scripts/validate_tw_run_registry.py
scripts/validate_tw_auto_update_orchestrator_contract.py
scripts/validate_tw_analysis_artifact.py
scripts/validate_tw_frontend_readonly_display_contract.py
scripts/validate_tw_agent_readonly_context_contract.py
```

更新：

```text
scripts/run_tw_modular_contract_regression.py
```

### 5.3 必须新增 golden samples

建议放在：

```text
data_tw/artifacts/modular_contract_golden_samples/
```

至少包含：

```text
valid_data_ingestion_artifact
invalid_data_ingestion_missing_available_at
valid_feature_artifact
invalid_feature_future_label
valid_price_store
invalid_price_store_missing_next_day_execution
valid_daily_run_registry
invalid_daily_run_switches_accepted_latest
valid_auto_update_no_new_data_noop
valid_auto_update_fresh_data_all_validators_publish_readonly_latest
invalid_auto_update_validator_failed_but_latest_changed
invalid_auto_update_switches_provider_accepted_latest
valid_analysis_artifact
invalid_analysis_uses_diagnostic_as_strategy_evidence
valid_agent_readonly_context_placeholder
invalid_agent_context_contains_order_tool
invalid_agent_response_target_position_semantics
```

### 5.4 M1 通过标准

```text
每个 validator 至少有一个正例和一个负例
contract regression 纳入新增 validator
所有 validator 支持 --json
失败时返回明确 status
自动更新 validator 覆盖 no_new_data、fresh_data_success、validator_failed 三类状态
不跑新模型、不跑新 replay、不改默认策略
```

## 6. Phase M2：Registry 与 Onboarding 模板

### 6.1 目标

让后续新增数据、特征、模型、策略时不再临时写文档，而是按模板接入。

### 6.2 必须新增或完善

新增或完善：

```text
configs/tw_modular_registry.yaml
configs/model_onboarding_templates/
configs/strategy_dependencies/
configs/data_source_registry.yaml
configs/feature_registry.yaml
configs/price_store_registry.yaml
docs/tw_modular_contracts/templates/
```

模板至少包括：

```text
NEW_DATA_SOURCE_WORK_TEMPLATE_CN.md
NEW_FEATURE_WORK_TEMPLATE_CN.md
NEW_MODEL_WORK_TEMPLATE_CN.md
NEW_STRATEGY_WORK_TEMPLATE_CN.md
NEW_REPLAY_WINDOW_WORK_TEMPLATE_CN.md
NEW_FRONTEND_READONLY_DISPLAY_WORK_TEMPLATE_CN.md
NEW_AGENT_READONLY_CONTEXT_WORK_TEMPLATE_CN.md
EXECUTION_REPORT_TEMPLATE_CN.md
REVIEW_REPORT_TEMPLATE_CN.md
```

### 6.3 Registry 必须声明

```text
artifact_type
schema_version
contract_doc
validator
capabilities
dependencies
allowed_consumers
forbidden_consumers
production_allowed=false by default
diagnostic_only flag, if applicable
```

### 6.4 M2 通过标准

```text
新增模型/策略/数据都有模板入口
registry regression 能检查合同、validator、dependency 是否存在
registry 不触发训练、replay、latest switch 或默认策略切换
```

## 7. Phase M3：日更编排与 latest pointer 边界

### 7.1 目标

冻结日更链路的模块边界，防止后续新增模型或数据时把抓取、训练、推理、策略、snapshot、replay 混在一起。

M3 必须把既有“两小时自动更新脚本”纳入设计范围，但只做 readonly shadow / dry-run 编排，不改变当前生产日更行为。

原则：

```text
保留全自动能力
拆掉业务耦合
自动脚本只做 orchestrator
业务模块各自生成标准 artifact
所有 validator 通过后才更新 readonly latest pointer
失败时保留上一版 latest
```

M3 不允许用一个新大脚本替代旧大脚本。目标是把旧自动链路改造成可审计的 orchestrator contract，而不是制造另一个耦合入口。

### 7.2 必须定义的链路

```text
Two-hour scheduler / manual dry-run trigger
  -> FreshnessCheck
  -> if no_new_data: record noop and keep previous latest
  -> if fresh_data_detected:
DataIngestion
  -> FeatureArtifact build
  -> ModelSignalArtifact build
  -> StrategyDecisionArtifact build
  -> ReadonlySnapshot build
  -> optional ReplayWindowArtifact registration
  -> RunRegistry record
  -> latest pointer update, only after all validators pass
```

### 7.3 latest pointer 政策

必须明确：

```text
readonly latest pointer != provider accepted latest
readonly latest pointer != qlib accepted latest
auto-update readonly latest pointer != provider accepted latest
失败时保留 previous latest
不得在 validator 失败时发布半成品
每次 latest 更新必须记录 previous/latest/run_id/checksum
no_new_data 时不得刷新 latest pointer 伪造成新结果
```

### 7.4 自动脚本职责边界

自动脚本可以做：

```text
定时触发
检查是否有新数据
调用模块
收集 validator 状态
写 RunRegistry
在全部通过后更新 readonly latest pointer
失败时记录错误并保留 previous latest
```

自动脚本不得做：

```text
直接拼特征
直接读模型私有字段
直接决定策略买卖
直接执行 replay 记账
绕过 validator 更新 latest
切 provider / accepted latest
触发 monitor / broker / order
```

### 7.5 M3 通过标准

```text
有 dry-run daily modular chain
既有两小时自动更新脚本已被审计并映射到 orchestrator contract
no_new_data 场景不会更新 latest
fresh_data_success 场景只有在所有 validators 通过后才更新 readonly latest
validator_failed 场景保留 previous latest
不会触发真实 provider refresh / publish
不会切 accepted latest
不会写 monitor / broker / order
RunRegistry 能记录成功和失败样例
失败样例证明 previous latest 保持不变
```

## 8. Phase M4：前端只读展示边界整理

### 8.1 目标

前端需要符合用户第一性原则：简单、准确、清晰、实用。当前 D8 前端安全，但工程字段偏多，应整理为组件化只读展示。

### 8.2 建议组件拆分

```text
ReadonlyStrategySnapshotPanel.vue
ReadonlyReplayWindowPanel.vue
ReplayMetricSummary.vue
ReplayActionsTable.vue
ReplayAuditDetail.vue
ReadonlyModelStrategySelector.vue
```

### 8.3 展示层级

主视图优先展示：

```text
模型
策略
合法窗口
净收益
最大回撤
交易次数
手续费/税费
覆盖状态
审计状态
```

折叠审计详情展示：

```text
source manifest
checksum
window index
schema version
validator result
run_id
```

### 8.4 Agent 边界

M4 可以整理普通 readonly 展示组件，但不得修改前端嵌入 Agent 的行为。Agent 在 M 主线中只允许做合同占位和安全扫描，不允许进入实现。

禁止：

```text
修改 Agent prompt
新增 Agent tool
新增 Agent action button
让 Agent 调用 provider / accepted latest / monitor / broker / order
让 Agent 生成买卖指令、目标仓位、收益承诺或上涨概率
让 Agent 本地计算策略或 replay
```

允许：

```text
记录 Agent 未来合同缺口
定义 Agent 只读上下文来源
定义 Agent 后续专项主线入口
检查 M4 前端改动没有误碰 Agent 区域
```

### 8.5 禁止事项

```text
前端不得本地 replay
前端不得本地生成策略意图
前端不得绕过后端窗口校验
前端不得显示目标仓位、下单、一键交易、自动交易、保证收益、胜率承诺
前端不得调用 POST/PUT/PATCH/DELETE 的 replay/strategy 路由
```

### 8.6 M4 通过标准

```text
readonly 展示组件从大页面拆出或至少形成明确组件边界
E2E 证明 replay/strategy readonly workflow 只有 GET
页面主视图不被工程审计字段主导
审计字段可追溯但默认不压过用户指标
frontend build 通过
```

## 9. Phase M5：新模型/新策略 Dry-Run Harness

### 9.1 目标

在真正开发新模型、新策略前，用 smoke/dry-run 验证 onboarding 流程是否顺。

M5 仍不训练真实新模型，不产出策略收益结论。

### 9.2 Dry-run 对象

建议做两个 smoke：

```text
dummy_new_model_signal_adapter_smoke
dummy_new_strategy_dependency_smoke
```

它们必须标记：

```text
smoke_only=true
not_valid_strategy_evidence=true
no_replay_return_conclusion=true
not_default_candidate=true
```

### 9.3 验证目标

证明以下流程可跑通：

```text
registry entry
contract reference
validator pass/fail
strategy dependency check
ModelSignalArtifact compatibility check
OrderIntentArtifact compatibility check, if applicable
no replay return conclusion
no default switch
```

### 9.4 M5 通过标准

```text
新增模型 smoke 不需要改策略或回放引擎
新增策略 smoke 不需要改 replay execution 主体
registry regression 能识别 smoke-only
审查报告明确 smoke 不代表 alpha、不代表策略收益、不代表可上线
```

## 10. Phase M6：最终验收与开发手册

### 10.1 目标

把 M0-M5 收口成后续开发手册，让执行者以后按模板做新模型、新策略。

### 10.2 必须输出

```text
docs/tw_modular_contracts/MODULAR_FOUNDATION_FINAL_ACCEPTANCE_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md
docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md
```

### 10.3 M6 通过标准

```text
合同齐全
validator 齐全
golden samples 齐全
registry regression 通过
前端只读边界通过
前端嵌入 Agent 未被误改，或仅完成合同占位
日更 dry-run 边界通过
新增模型/策略 smoke onboarding 通过
没有真实训练、收益结论、默认策略切换或生产写入口
```

## 11. 执行者通用 Prompt

```text
你是执行者。请按 docs/tw_modular_contracts/PHASEM_MODULAR_FOUNDATION_BEFORE_NEW_MODEL_STRATEGY_WORK_CN.md 执行当前 Phase M 子阶段。

本阶段目标是为后续新增模型、新策略建立模块化地基。你必须严格保持只读和研究边界：
- 不训练新模型；
- 不新增正式策略收益结论；
- 不切默认策略；
- 不触发 provider publish / refresh；
- 不切 accepted latest；
- 不写 monitor config / scan / alerts；
- 不触发 broker / quick-trade / orders；
- 不把 diagnostic/smoke 产物作为有效策略证据；
- 不修改前端嵌入 Agent 的 prompt、tool、action 或行为。

请输出执行报告，至少包含：
1. 本阶段目标；
2. 修改/新增文件；
3. 合同或 schema 变化；
4. validator / golden sample / registry 变化；
5. 正例和负例验证结果；
6. 只读安全边界；
7. 明确没有做的事项；
8. 残余风险；
9. 下一阶段建议。
```

## 12. 审查者通用 Prompt

```text
你是审查者。请按 docs/tw_modular_contracts/PHASEM_MODULAR_FOUNDATION_BEFORE_NEW_MODEL_STRATEGY_WORK_CN.md 审查执行者的 Phase M 子阶段报告。

重点确认：
1. 是否严格保持本阶段范围；
2. 是否没有训练新模型、跑新收益结论、切默认策略；
3. 是否没有 provider / accepted latest / monitor / broker / order 越界；
4. 合同是否定义输入、输出、manifest、forbidden fields、forbidden actions；
5. validator 是否有正例和负例；
6. registry 是否只做声明，不触发执行；
7. daily/latest pointer 是否失败关闭；
8. 既有两小时自动更新脚本是否只承担 orchestrator 职责；
9. no_new_data / fresh_data_success / validator_failed 三类状态是否有证据；
10. validator 失败时 readonly latest pointer 是否保持不变；
11. frontend 是否只读、GET-only、不本地计算、不出现危险交易语义；
12. 前端嵌入 Agent 是否未被误改，或仅做只读合同占位；
13. Agent 是否没有新增 tool/action/prompt 能力；
14. smoke/diagnostic 是否没有被当成有效策略证据；
15. 是否允许进入下一阶段。

如果发现偏离主线，必须停下来要求修复，不得放行。

审查输出必须包含：
- Findings，按 Critical / High / Medium / Low；
- 是否阻塞；
- 通过项；
- 必须修复项；
- 是否允许进入下一阶段；
- 下一阶段工作文档或补充建议。
```

## 13. 新模型开发前硬门

M 主线未完成前，不建议进入真实新模型开发。

真实新模型必须等待以下条件满足：

```text
FeatureArtifact contract exists
PriceStore contract exists, if replay will be used
DataIngestion contract exists, if using new data
AutoUpdateOrchestrator contract exists, if model will join daily updates
ModelSignalArtifact adapter template exists
registry entry template exists
signal validator and registry regression pass
OOS/train window policy declared
no default strategy switch without user confirmation
```

## 14. 新策略开发前硬门

真实新策略必须等待以下条件满足：

```text
Strategy dependency template exists
required fields/capabilities/extensions declared
OrderIntent validator covers action limits
ReplayExecutionEngine remains strategy-agnostic
strategy does not read model private fields
strategy does not read future labels/prices/replay returns
diagnostic_only policy exists
frontend display policy exists, if shown
daily orchestrator policy exists, if strategy will join automatic readonly updates
```

## 15. M6 后续 Agent 专项建议

M 主线收口后，如果要继续整理前端嵌入 Agent，建议另开专项主线：

```text
Phase A0 Agent Readonly Contract and Safety Boundary
Phase A1 Agent Context Builder for Modular Artifacts
Phase A2 Agent Frontend Panel Readonly Refactor
Phase A3 Agent Response Safety Validator and E2E Audit
```

Agent 专项主线的默认边界：

```text
只读解释 artifact / replay / window / audit
不建议买卖
不输出目标仓位
不调用 provider / accepted latest / monitor / broker / order
不本地计算策略或 replay
不把训练窗口收益当成策略优劣证据
```

## 16. 推荐先做顺序

建议立即开始：

```text
Phase M0 Contract Gap Closure
```

M0 只做文档和合同，不需要执行复杂代码，因此风险低、收益高。M0 审查通过后，再进入 M1 validator / golden sample。
