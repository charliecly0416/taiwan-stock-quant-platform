# Phase M5 审查与 Phase M6 工作文档

生成日期：2026-06-17

## 1. 审查结论

Phase M5 通过，允许进入 Phase M6。

M5 完成了新模型/新策略在真实开发前的 dry-run onboarding smoke：新增 dummy model signal、dummy strategy dependency、可选 order intent 兼容夹具、正负例 golden samples、registry smoke entry 和统一回归接入。审查未发现真实训练、调参、收益结论、默认策略切换、provider publish/refresh、accepted latest 切换、monitor 写入、broker/order 或 Agent prompt/tool/action 扩权。

本轮 smoke 产物只能作为 onboarding 合同兼容性证据，不能作为 alpha、return、default candidate、生产策略或交易证据。

## 2. 复核范围

审查输入：

```text
docs/tw_modular_contracts/PHASEM5_DRY_RUN_ONBOARDING_SMOKE_EXECUTION_REPORT_CN.md
scripts/validate_tw_modular_m5_smoke.py
scripts/run_tw_modular_contract_regression.py
configs/tw_modular_registry.yaml
configs/strategy_dependencies/dummy_new_strategy_dependency_smoke.yaml
data_tw/golden_samples/modular_contracts/m5/onboarding_smoke/pass_minimal
data_tw/golden_samples/modular_contracts/m5/onboarding_smoke/fail_missing_smoke_flags
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/m5_onboarding_smoke_validation.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/signal_artifact_validation.csv
```

审查重点：

```text
smoke 产物是否强制 smoke_only / not_valid_strategy_evidence / no_replay_return_conclusion / not_default_candidate
registry entry 是否 diagnostic_only 且 production_allowed=false
dummy strategy dependency 是否只绑定 dummy smoke artifact，不影响正式 signal/replay
validator 是否覆盖正例、负例、registry、ModelSignal、StrategyDependency、OrderIntent 兼容检查
统一回归是否纳入 M5 smoke gate
M3R daily gate 与 M4R frontend GET-only gate 是否仍通过
是否没有训练、调参、收益结论、默认切换、provider/latest、monitor/broker/order、Agent 扩权
```

## 3. 通过项

### 3.1 Smoke marker 已成为硬门

`scripts/validate_tw_modular_m5_smoke.py` 要求 M5 artifact 明确声明：

```text
smoke_only=true
not_valid_strategy_evidence=true
no_replay_return_conclusion=true
not_default_candidate=true
```

同时要求以下禁止动作标记为 true：

```text
no_training
no_tuning
no_default_switch
no_provider_publish
no_accepted_latest_switch
no_monitor_write
no_broker_order
agent_untouched
```

负例 `fail_missing_smoke_flags` 缺少 smoke markers，golden runner 返回预期错误：

```text
ok=false
error_codes=["smoke_marker_missing"]
```

这证明 smoke-only 语义不是执行报告中的描述性文字，而是 validator 可阻断的合同字段。

### 3.2 Registry smoke entry 不具备生产消费资格

`configs/tw_modular_registry.yaml` 中 M5 smoke registry entry 明确：

```text
production_allowed=false
diagnostic_only=true
forbidden_consumers:
  - default_candidate
  - broker
  - provider_publish
```

审查确认 dummy model signal 和 dummy strategy dependency 均位于 `m5_smoke_registry`，不是正式 default candidate，也没有 provider publish/latest 或 broker/order 消费入口。

### 3.3 Dummy strategy dependency 未污染正式 signal 验证

`configs/strategy_dependencies/dummy_new_strategy_dependency_smoke.yaml` 使用：

```text
applies_to_artifact_names:
  - dummy_new_model_signal_adapter_smoke
```

统一回归输出的 `signal_artifact_validation.csv` 显示，该 dummy dependency 对现有正式 signal manifests 均为 skipped。这一点很关键：M5 只验证“新增策略 dependency 能否按模板声明并被检查”，没有把 smoke 策略施加到正式信号或 replay 流程上。

### 3.4 ModelSignal / StrategyDependency / OrderIntent 兼容检查可跑通

正例 `pass_minimal` 覆盖：

```text
manifest.json
model_signal_manifest.json
order_intent_manifest.json
order_intents.csv
```

其中 order intent 夹具带有：

```text
readonly_only=true
not_order=true
not_target_position=true
not_investment_advice=true
```

审查结论：该 order intent 是 smoke 兼容夹具，不是订单、目标仓位、投资建议或 replay 收益证据。

### 3.5 复跑验证

已复跑：

```bash
python -m py_compile scripts/validate_tw_modular_m5_smoke.py scripts/run_tw_modular_contract_regression.py
python scripts/validate_tw_modular_m5_smoke.py --artifact-path data_tw/golden_samples/modular_contracts/m5/onboarding_smoke/pass_minimal --json
python scripts/validate_tw_modular_m5_smoke.py --run-golden --json
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_frontend_readonly_m4.py --json
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
```

结果：

```text
py_compile: pass
M5 pass_minimal validator: ok=true, schema_version=m5.0.0
M5 golden runner: ok=true, sample_count=2
contract regression: ok=true, m5_onboarding_smoke_status=passed, m5_onboarding_smoke_sample_count=2
M4R frontend readonly validator: ok=true, schema_version=m4.0.1, GET-only forbidden counters=0
M3R daily orchestrator audit: ok=true, default reachable provider/latest gates=false
```

M3R audit 仍报告 legacy provider publish/latest path present warning，但默认可达字段为 false，符合 M3R 已接受的治理状态。

## 4. 台股只读安全边界审查

### Findings

Critical：未发现 M5 引入 broker/order/quick-trade/target-position、provider publish/refresh、accepted latest、monitor config/scan/alerts 写入、真实训练、真实调参、正式收益结论或默认策略切换。

High：未发现 Agent prompt/tool/action 扩权。M5 报告和 validator 均要求 `agent_untouched=true`。

Medium：`dummy_new_strategy_dependency_smoke` 出现在顶层 `strategies` registry section 中，但通过 `applies_to_artifact_names=[dummy_new_model_signal_adapter_smoke]` 限定为 dummy smoke artifact，统一回归也证明它对正式 signals 为 skipped。M6 手册必须把“smoke entry 不得进入正式 replay/default/product path”写成明确规则。

Low：M5 validator 中 `forbidden_surface_audit` 是面向本 smoke fixture 的汇总结果，不是全仓运行时扫描。当前可接受，因为 registry、strategy dependency、manifest 和 order intent 字段已有具体硬门；M6 最终验收文档应说明该 validator 的审计边界，避免后续误读为全系统安全扫描。

### Verdict

M5 通过。Dry-run onboarding smoke 已证明新增模型/策略接入模板、registry 声明、validator 正负例和统一回归路径可用，且没有越过只读研究边界。

## 5. 残余风险

1. Smoke strategy dependency 虽被 dummy artifact 限定，但 M6 必须在开发手册中规定 smoke/diagnostic entry 不得作为 formal replay、default candidate、frontend product display 或 production consumer 输入。
2. Optional order intent 夹具只用于 compatibility smoke；后续真实策略开发必须重新走 OrderIntent 合同、动作限制、readonly replay 和审查，不得复用 M5 smoke 作为策略有效性证据。
3. M3R legacy provider publish/latest 代码路径仍存在但默认不可达；M6 最终验收应沿用 M3R 的 gate 结论，不应把 warning 当成已删除。
4. M4R frontend GET-only 结论仍依赖 validator/E2E audit 规则；M6 最终验收应把 GET-only network audit 列为后续前端变更的必跑项。

## 6. Phase M6 工作范围

M6 目标：把 M0-M5 的模块化地基收口为最终验收和后续开发/审查手册。

M6 必须输出：

```text
docs/tw_modular_contracts/MODULAR_FOUNDATION_FINAL_ACCEPTANCE_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md
docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md
```

M6 不应再新增业务能力。它应该汇总并固化：

```text
M0 contracts 完整性
M1 validator / golden samples / error codes
M2/M2R registry 与 onboarding template 语义 gate
M3/M3R daily orchestrator / latest pointer default-unreachable legacy gate
M4/M4R frontend readonly GET-only boundary
M5 smoke onboarding dry-run gate
Agent placeholder / readonly context freeze
```

## 7. M6 必须验收的硬门

M6 最终验收至少要给出以下命令或等价证据：

```bash
python -m py_compile scripts/validate_tw_modular_contracts.py scripts/validate_tw_modular_registry.py scripts/validate_tw_daily_orchestrator_m3.py scripts/validate_tw_frontend_readonly_m4.py scripts/validate_tw_modular_m5_smoke.py scripts/run_tw_modular_contract_regression.py
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
python scripts/validate_tw_frontend_readonly_m4.py --json
python scripts/validate_tw_modular_m5_smoke.py --run-golden --json
```

通过标准：

```text
合同齐全
validator 齐全
golden samples 齐全
registry regression 通过
daily dry-run / latest pointer gate 通过
frontend readonly GET-only gate 通过
M5 smoke onboarding 通过
Agent 未扩权，或仅保留只读合同占位
无真实训练
无正式策略收益结论
无 default candidate / default strategy switch
无 provider publish / refresh
无 accepted latest switch
无 monitor 写入
无 broker / quick-trade / order
```

## 8. M6 开发手册必须写清的规则

### 8.1 新模型开发规则

手册必须要求新模型先输出 raw score，再经 adapter 变成标准 `ModelSignalArtifact`。不得让策略、replay、frontend 或 Agent 直接读取模型私有字段。

新模型进入任何正式候选前，至少必须声明：

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

### 8.2 新策略开发规则

手册必须要求新策略只新增 `StrategyRule / StrategyDependency`，不得修改 replay engine 来适配私有模型字段。

新策略至少必须声明：

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

### 8.3 Smoke / diagnostic 规则

M6 必须把以下规则写为硬约束：

```text
smoke_only=true 的产物不能作为有效策略证据
not_valid_strategy_evidence=true 的产物不能进入 default candidate
no_replay_return_conclusion=true 的产物不能被写成收益结论
not_default_candidate=true 的产物不能切默认策略
diagnostic_only=true 且 production_allowed=false 的 registry entry 不能被生产 consumer 消费
order intent smoke 夹具不是订单、目标仓位或投资建议
```

### 8.4 Agent 规则

M6 不进入 Agent 功能开发。最终文档只允许确认：

```text
Agent prompt/tool/action 未扩权
Agent 只读 context placeholder 保持冻结
后续 Agent 整理另开专项
Agent 不建议买卖
Agent 不输出目标仓位
Agent 不调用 provider/latest/monitor/broker/order
```

## 9. M6 禁止事项

M6 不得做以下事项：

```text
不得训练真实新模型
不得调参或搜索真实模型
不得新增正式策略收益结论
不得运行会被解释为 alpha / return evidence 的 replay
不得切默认策略或 default candidate
不得触发 provider publish / refresh
不得切 accepted latest
不得写 monitor config / scan / alerts
不得触发 broker / quick-trade / orders
不得修改 Agent prompt / tool / action / 行为
不得把 M5 smoke 产物写入正式产品展示或生产消费路径
```

## 10. M6 审查建议

M6 执行报告提交后，审查者应按以下顺序复核：

1. 最终验收文档是否逐项覆盖 M0-M5 的通过证据和残余风险。
2. 开发手册是否能指导一个新模型/新策略从 registry、manifest、validator、golden sample 到 readonly display 的完整接入。
3. 两份 reviewer checklist 是否可直接用于阻断真实训练、收益结论、default switch、provider/latest、monitor/broker/order 和 Agent 扩权。
4. 所有 validator 命令是否复跑通过。
5. smoke/diagnostic 与正式 production/default/replay/display 路径的隔离规则是否足够明确。

M6 通过后，才建议把“真实新模型/新策略开发”作为新的项目主线开启。
