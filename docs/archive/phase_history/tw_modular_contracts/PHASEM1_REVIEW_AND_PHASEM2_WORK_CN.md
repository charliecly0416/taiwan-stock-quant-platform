# Phase M1 Validator 与 Golden Sample 审查及 Phase M2 工作文档

生成日期：2026-06-17

## 1. 审查结论

Phase M1 审查结论：通过，允许进入 Phase M2。

执行者提交的 `PHASEM1_VALIDATOR_AND_GOLDEN_SAMPLE_EXECUTION_REPORT_CN.md` 与 M1 工作要求基本一致。M1 已把 M0 合同文本落成统一 validator、29 个 golden samples、预期错误码、单元测试和 contract regression 接入。

本轮没有训练新模型、没有新增正式策略、没有跑新收益结论、没有切默认策略、没有触发 provider publish / refresh、没有切 accepted latest、没有改 monitor / broker / quick-trade / order，也没有修改前端 Agent 行为、prompt、tool 权限或 action 入口。

## 2. 审查依据

本次审查参考：

```text
docs/tw_modular_contracts/PHASEM_MODULAR_FOUNDATION_BEFORE_NEW_MODEL_STRATEGY_WORK_CN.md
docs/tw_modular_contracts/PHASEM0_REVIEW_AND_PHASEM1_WORK_CN.md
docs/tw_modular_contracts/PHASEM1_VALIDATOR_AND_GOLDEN_SAMPLE_EXECUTION_REPORT_CN.md
scripts/validate_tw_modular_m_contracts.py
scripts/run_tw_modular_contract_regression.py
tests/unit/test_tw_modular_m_contract_validators.py
data_tw/golden_samples/modular_contracts/m1/
docs/tw_modular_contracts/TW_MODULAR_PIPELINE_FUTURE_DEVELOPMENT_GUIDE_CN.md
docs/README_CN.md
```

## 3. 验证结果

审查复跑：

```bash
python -m py_compile scripts/validate_tw_modular_m_contracts.py scripts/run_tw_modular_contract_regression.py tests/unit/test_tw_modular_m_contract_validators.py
python scripts/validate_tw_modular_m_contracts.py --run-golden --json
python -m pytest tests/unit/test_tw_modular_m_contract_validators.py -q
```

结果：

```text
py_compile: pass
golden validator: ok=true, sample_count=29, status=passed
pytest: 3 passed
```

说明：第一次在普通沙箱中运行 golden validator 被环境的 bwrap 限制拦截，提升权限后只读复跑通过。

## 4. 通过项

### 4.1 Validator 输出格式满足 M1 要求

`scripts/validate_tw_modular_m_contracts.py` 支持：

```text
--contract
--artifact-path
--run-golden
--list-contracts
--json
```

JSON 输出包含：

```text
ok
contract
status
errors
warnings
checked_files
schema_version
```

`errors` 中包含 `code`、`message`、`path` 和 `field`。M1 schema version 冻结为 `m1.0.0`。

### 4.2 Golden samples 覆盖 M0 合同

M1 golden samples 位于：

```text
data_tw/golden_samples/modular_contracts/m1/
```

共 29 个样例，覆盖 12 份 M0 合同。每个样例包含 `expected_result.json`，并校验 `expected_ok`、`schema_version` 和 `expected_error_codes`。

覆盖范围包括：

```text
required fields / required columns
forbidden fields
forbidden action audit missing
latest pointer noop / success / validator_failed / module_failed
auto-update no_new_data / fresh_data_success / validator_failed / forbidden accepted_latest / order
frontend GET-only / forbidden request / forbidden text
Agent readonly placeholder / forbidden tool / forbidden semantics / prompt-tool-action expansion
default candidate user confirmation
```

### 4.3 Validator 不是纯关键词扫描

实现会结构化读取：

```text
manifest.json
schema.json
CSV data columns
forbidden_action_audit.json
network_request_audit.json
agent_tool_audit.json
panel_boundary_audit.json
expected_result.json
latest pointer state transition fields
```

关键词和语义词表仅作为 forbidden text、forbidden semantics 和 forbidden field pattern 的辅助检查。

### 4.4 Contract regression 已接入

`scripts/run_tw_modular_contract_regression.py` 已接入 M1 golden validator，并输出：

```text
m1_contract_validation.json
m1_contract_sample_count
m1_contract_status
```

该接入满足 M1 “contract regression 纳入新增 validator”的通过标准。

### 4.5 台股只读安全边界通过

安全边界审查结果：

```text
未发现真实 broker / quick-trade / order 写入口
未发现真实 target position / target weight 动作入口
未发现真实 provider publish / refresh 入口
未发现真实 provider accepted latest / qlib accepted latest switch 入口
未发现 monitor config save / scan / alerts write 入口
危险语义只出现在负例 fixture、validator 禁令或报告说明中
```

前端和 Agent 的危险请求、危险文案、危险工具调用和 prompt/tool/action 扩权均有失败样例覆盖。

## 5. 残余风险

### Low. 部分 boundary audit 仍偏存在性检查

M1 已检查 `network_request_audit.json`、`agent_tool_audit.json` 和 `panel_boundary_audit.json` 的关键内容，但 `readonly_boundary_audit.json` 和 `response_semantics_audit.json` 当前更多承担 fixture 存在性角色。比如前端本地 replay / local ranking 这类边界，M1 样例已有字段，但 validator 主要依赖 manifest 文案和 network audit 判断。

该问题不阻塞 M2，因为 M1 的验收重点是合同 validator 和 golden sample 地基；但后续 M2/M4 应把 boundary audit 内容转成更严格的结构化字段检查。

M2/M4 建议补强：

```text
readonly_boundary_audit.local_replay must be false
readonly_boundary_audit.local_ranking must be false
readonly_boundary_audit.local_signal_compute must be false
response_semantics_audit.forbidden_semantics_count must be 0
panel_boundary_audit prompt/tool/action expansion must remain false
```

### Low. M1 未审计真实两小时自动脚本

执行报告已明确 M1 未运行真实两小时自动更新脚本，也未审计真实线上网络请求，并把 `scripts/run_daily_tw_stock_auto_update.py` 列为 M3 必查项。该处理符合 M1 范围，但 M3 不得跳过。

## 6. Phase M2 目标

Phase M2 名称：Registry and Onboarding Templates。

目标是让后续新增数据、特征、模型、策略、回放、前端展示或 Agent readonly context 时，不再临时写散文档，而是通过 registry 和模板接入。

M2 仍然不得：

```text
训练新模型
新增正式策略
运行新收益结论
切默认策略
触发 provider publish / refresh
切 accepted latest
改 monitor / broker / quick-trade / order
修改前端 Agent 行为、prompt、tool 权限或 action 入口
```

## 7. M2 必交付物

### 7.1 Registry

新增或完善：

```text
configs/tw_modular_registry.yaml
configs/data_source_registry.yaml
configs/feature_registry.yaml
configs/price_store_registry.yaml
configs/model_onboarding_templates/
configs/strategy_dependencies/
```

每个 registry entry 至少声明：

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

### 7.2 Onboarding Templates

新增：

```text
docs/tw_modular_contracts/templates/NEW_DATA_SOURCE_WORK_TEMPLATE_CN.md
docs/tw_modular_contracts/templates/NEW_FEATURE_WORK_TEMPLATE_CN.md
docs/tw_modular_contracts/templates/NEW_MODEL_WORK_TEMPLATE_CN.md
docs/tw_modular_contracts/templates/NEW_STRATEGY_WORK_TEMPLATE_CN.md
docs/tw_modular_contracts/templates/NEW_REPLAY_WINDOW_WORK_TEMPLATE_CN.md
docs/tw_modular_contracts/templates/NEW_FRONTEND_READONLY_DISPLAY_WORK_TEMPLATE_CN.md
docs/tw_modular_contracts/templates/NEW_AGENT_READONLY_CONTEXT_WORK_TEMPLATE_CN.md
docs/tw_modular_contracts/templates/EXECUTION_REPORT_TEMPLATE_CN.md
docs/tw_modular_contracts/templates/REVIEW_REPORT_TEMPLATE_CN.md
```

模板必须要求填写：

```text
遵守的 contract_doc
schema_version
输入 artifact
输出 artifact
validator 命令
golden sample 路径
allowed_consumers / forbidden_consumers
readonly boundary
forbidden actions audit
rollback / failure policy
是否 diagnostic_only
是否 production_allowed=false
```

### 7.3 Registry Validator

新增或扩展 registry validator，建议：

```text
scripts/validate_tw_modular_registry_m2.py
```

至少检查：

```text
registry 文件存在
每个 entry 的 contract_doc 存在
每个 entry 的 validator 存在且支持 --json
每个 entry 的 golden_sample 存在
每个 entry 的 schema_version 与 M1 validator 兼容
allowed_consumers / forbidden_consumers 非空
production_allowed 默认为 false
diagnostic_only 项不得作为默认策略证据
Agent template 只允许 placeholder，不允许 tool/action/prompt 扩权
```

### 7.4 Regression 接入

更新：

```text
scripts/run_tw_modular_contract_regression.py
```

新增输出建议：

```text
m2_registry_validation.json
m2_template_coverage.json
m2_registry_status
```

## 8. M2 验收门槛

M2 审查通过必须同时满足：

```text
新增或完善的 registry 文件存在
所有 registry entry 指向的 contract_doc / validator / golden_sample 存在
所有 validator 可用 --json 运行
registry regression 能检查合同、validator、dependency 和 template coverage
新增数据、特征、模型、策略、replay window、frontend readonly display、Agent readonly context 都有模板入口
所有模板默认 production_allowed=false
所有模板保留 forbidden actions audit 和 readonly boundary
Agent 模板明确 not_in_m0_m6_implementation_scope=true
没有训练模型、运行新 replay、切默认策略、publish provider、切 accepted latest、monitor/broker/order 或 Agent 扩权
执行报告列出 validator 命令、registry entry 数、template 清单、测试结果、未覆盖项
```

## 9. 下一步给执行者的工作指令

执行者进入 Phase M2。请优先完成：

1. 先定义 registry entry 的最小字段和 schema version 规则。
2. 再补齐 data source、feature、price store、model、strategy、replay、frontend readonly、Agent readonly 的模板入口。
3. 实现 M2 registry validator，确保每个 entry 都能追到 contract、validator 和 golden sample。
4. 接入 contract regression。
5. 写 `PHASEM2_REGISTRY_AND_ONBOARDING_TEMPLATE_EXECUTION_REPORT_CN.md`，列出命令、结果、未覆盖项和禁止事项确认。

M2 不得顺手开发新模型、新策略或改真实日更/前端 Agent 行为。
