# Phase M2 Registry 与 Onboarding Template 执行报告

生成日期：2026-06-17

## 1. 执行范围

本轮执行 Phase M2：新增/完善 registry、onboarding templates、M2 registry validator、单元测试和 contract regression 接入。

本轮未训练新模型、未新增正式策略、未运行新收益结论、未切默认策略、未触发 provider publish / refresh、未切 accepted latest、未改 monitor / broker / quick-trade / order、未修改前端 Agent 行为、prompt、tool 权限或 action 入口。

## 2. Registry 交付

新增或完善：

```text
configs/tw_modular_registry.yaml
configs/data_source_registry.yaml
configs/feature_registry.yaml
configs/price_store_registry.yaml
configs/model_onboarding_templates/model_signal_m2_template.yaml
configs/strategy_dependencies/m2_strategy_dependency_template.yaml
```

M2 registry entry 统一字段：

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
diagnostic_only
owner_or_stage
```

`schema_version` 继续绑定 M1 validator 版本：

```text
m1.0.0
```

## 3. Registry Entry 覆盖

M2 validator 检查到 registry entry 总数：14。

覆盖模块：

```text
data_source
data_ingestion
feature_artifact
price_store
model_signal
strategy_rule
readonly_replay_window
frontend_readonly_display
agent_readonly_context
analysis_artifact
default_candidate_decision
```

独立 registry：

```text
data_source_registry: 1 entry
feature_registry: 1 entry
price_store_registry: 1 entry
```

所有 entry 均声明 contract_doc、validator、golden_sample、capabilities、dependencies、allowed_consumers、forbidden_consumers、production_allowed=false、diagnostic_only 和 owner_or_stage。

## 4. Onboarding Templates

新增模板目录：

```text
docs/tw_modular_contracts/templates/
```

模板清单：

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

每份模板均要求填写：

```text
contract_doc
schema_version
input_artifacts
output_artifacts
validator_command
golden_sample_path
allowed_consumers
forbidden_consumers
readonly_boundary
forbidden_actions_audit
rollback_or_failure_policy
diagnostic_only
production_allowed=false
```

Agent readonly context 模板额外冻结：

```text
readonly_artifact_only=true
not_in_m0_m6_implementation_scope=true
future_agent_phase_required=true
no_order_action=true
no_target_position=true
no_provider_publish=true
no_accepted_latest_switch=true
no_monitor_write=true
no_broker_or_order=true
```

## 5. 新增 Validator

新增：

```bash
python scripts/validate_tw_modular_registry_m2.py --json
```

检查内容：

```text
registry 文件存在
每个 entry 的 contract_doc 存在
每个 entry 的 validator 存在且支持 --json
每个 entry 的 golden_sample 存在
schema_version 与 m1.0.0 兼容
allowed_consumers / forbidden_consumers 非空
production_allowed=false
diagnostic_only 不进入默认策略消费者
Agent entry 保持 placeholder 并禁止 tool/action/prompt 扩权
9 份模板存在并包含 required markers
```

## 6. Regression 接入

已更新：

```text
scripts/run_tw_modular_contract_regression.py
```

新增输出：

```text
m2_registry_validation.json
m2_template_coverage.json
m2_registry_status
m2_registry_entry_count
m2_template_count
```

## 7. Boundary Audit 补强

根据 M1 review 残余风险，本轮同步补强了 `scripts/validate_tw_modular_m_contracts.py`：

```text
readonly_boundary_audit.local_replay must be false
readonly_boundary_audit.local_ranking must be false
readonly_boundary_audit.local_signal_compute must be false
response_semantics_audit.forbidden_semantics_count must be 0
panel_boundary_audit prompt/tool/action expansion remains false
```

对应 M1 frontend / Agent golden fixtures 已同步补字段，M1 golden validator 仍通过。

## 8. 验证命令与结果

已运行：

```bash
python -m py_compile scripts/validate_tw_modular_m_contracts.py scripts/validate_tw_modular_registry_m2.py scripts/run_tw_modular_contract_regression.py tests/unit/test_tw_modular_m_contract_validators.py tests/unit/test_tw_modular_m2_registry_validator.py
python scripts/validate_tw_modular_m_contracts.py --run-golden --json
python scripts/validate_tw_modular_registry_m2.py --json
python -m pytest tests/unit/test_tw_modular_m_contract_validators.py tests/unit/test_tw_modular_m2_registry_validator.py -q
```

结果：

```text
py_compile: pass
M1 golden validator: ok=true, sample_count=29
M2 registry validator: ok=true, registry_count=4, entry_count=14, template_count=9
pytest: 4 passed
```

## 9. 未覆盖项 / 后续必查

M2 未运行真实两小时自动更新脚本，未修改真实日更行为，也未接入真实前端 Agent 行为。M3 必须审计：

```text
scripts/run_daily_tw_stock_auto_update.py
no_new_data 行为
fresh_data_success 行为
validator_failed 行为
previous latest 是否保留
是否触发 provider accepted latest
是否触发 monitor / broker / order
```

M4 必须在真实前端组件层继续验证 GET-only、无本地 replay、无 forbidden text/request，以及 Agent panel 无 prompt/tool/action 扩权。

## 10. 结论

Phase M2 已建立 registry 与 onboarding template 地基。后续新增数据、特征、模型、策略、replay window、前端 readonly display 或 Agent readonly context 时，必须先登记 registry、填写模板、绑定 contract_doc、validator 和 golden sample，并保持 `production_allowed=false` 直到后续审查明确放行。
