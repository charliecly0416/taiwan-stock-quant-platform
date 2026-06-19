# Phase M1 Validator 与 Golden Sample 地基执行报告

生成日期：2026-06-17

## 1. 执行范围

本轮执行 Phase M1：新增统一 validator、M1 golden samples、单元测试和 contract regression 接入。

本轮未训练新模型、未新增正式策略、未跑新收益结论、未切默认策略、未触发 provider publish / refresh、未切 accepted latest、未改 monitor / broker / quick-trade / order、未改前端 Agent 行为、未新增 Agent tool / action / prompt 能力。

## 2. 新增 Validator

统一入口：

```bash
python scripts/validate_tw_modular_m_contracts.py --contract <contract> --artifact-path <sample_dir> --json
python scripts/validate_tw_modular_m_contracts.py --run-golden --json
python scripts/validate_tw_modular_m_contracts.py --list-contracts --json
```

JSON 输出字段：

```text
ok
contract
status
errors
warnings
checked_files
schema_version
```

`errors` 每项包含：

```text
code
message
path
field
```

初始 `schema_version` 冻结为：

```text
m1.0.0
```

## 3. Validator 检查口径

M1 validator 结构化读取：

```text
manifest.json
schema.json
CSV data columns
forbidden_action_audit.json
network_request_audit.json
readonly_boundary_audit.json
agent_tool_audit.json
panel_boundary_audit.json
expected_result.json
latest pointer state transition fields
```

不是只做关键词扫描。关键词/语义词表只用于辅助检查 forbidden text、Agent forbidden semantics 和 forbidden field pattern。

统一错误码包括：

```text
required_field_missing
required_column_missing
forbidden_field
forbidden_action
audit_missing
forbidden_request
forbidden_text
forbidden_semantics
forbidden_tool_call
agent_boundary_expanded
latest_pointer_changed_on_noop
latest_pointer_changed_on_failure
validators_not_passed
user_confirmation_missing
schema_version_mismatch
```

## 4. Golden Samples

目录：

```text
data_tw/golden_samples/modular_contracts/m1/
```

样例总数：29。每个 sample 均包含 `expected_result.json`，声明 contract、schema_version、expected_ok、expected_status 和 expected_error_codes。

覆盖清单：

```text
data_source/pass_minimal
data_source/fail_forbidden_field
data_ingestion/pass_minimal
data_ingestion/fail_missing_audit
feature_artifact/pass_pit_safe
feature_artifact/fail_future_field
price_store/pass_minimal
price_store/fail_missing_next_day_execution
daily_orchestrator/pass_success
daily_orchestrator/pass_module_failed_preserve_previous_latest
daily_orchestrator/fail_validator_failed_latest_switched
run_registry/pass_noop_preserve_previous_latest
run_registry/pass_success_update
run_registry/fail_provider_accepted_latest_switch
auto_update/pass_no_new_data_noop
auto_update/pass_fresh_data_success
auto_update/pass_validator_failed_preserve_previous_latest
auto_update/fail_order_action
auto_update/fail_accepted_latest_switch
analysis_artifact/pass_diagnostic_only
analysis_artifact/fail_default_strategy_selected
frontend_readonly_display/pass_get_only
frontend_readonly_display/fail_forbidden_request
agent_readonly_context/pass_placeholder
agent_readonly_context/fail_forbidden_tool_call
frontend_agent_panel/pass_placeholder
frontend_agent_panel/fail_prompt_or_tool_expansion
default_candidate_decision/pass_preserve_current_default
default_candidate_decision/fail_user_confirmation_missing
```

## 5. RunRegistry / Latest Pointer 状态机覆盖

已覆盖：

```text
success_validators_passed_updates_readonly_latest
no_new_data_noop_preserves_previous_latest
validator_failed_preserves_previous_latest
module_failed_preserves_previous_latest
attempted_provider_accepted_latest_switch_rejected
attempted_order_or_monitor_write_rejected
```

## 6. Frontend / Agent 边界覆盖

已覆盖：

```text
GET-only readonly API pass
POST /orders forbidden request fail
买入建议 forbidden text fail
readonly replay action table allowed
Agent readonly placeholder pass
Agent order tool fail
Agent 应该买入 forbidden semantics fail
Frontend Agent prompt/tool expansion fail
```

M1 未修改前端 Agent panel、prompt、tool 权限或 action 入口。

## 7. Contract Regression 接入

已更新：

```text
scripts/run_tw_modular_contract_regression.py
```

新增输出：

```text
m1_contract_validation.json
m1_contract_sample_count
m1_contract_status
```

该 regression 现在会调用：

```bash
python scripts/validate_tw_modular_m_contracts.py --run-golden --golden-root data_tw/golden_samples/modular_contracts/m1 --json
```

## 8. 验证结果

已运行：

```bash
python -m py_compile scripts/validate_tw_modular_m_contracts.py scripts/run_tw_modular_contract_regression.py tests/unit/test_tw_modular_m_contract_validators.py
python scripts/validate_tw_modular_m_contracts.py --run-golden --json
python -m pytest tests/unit/test_tw_modular_m_contract_validators.py -q
```

结果：

```text
py_compile: pass
golden validator: ok=true, sample_count=29, errors=[]
pytest: 3 passed
```

## 9. 检查文件数量

本轮 golden validator 批量检查 29 个 sample 目录。每个目录至少检查 `manifest.json` 和 `expected_result.json`；数据类样例额外检查 `schema.json`、CSV 数据列和 audit 文件；前端/Agent 样例额外检查 network/tool/panel boundary audit。

## 10. 未覆盖项 / 后续必查

M1 暂未运行真实两小时自动更新脚本，也未审计真实线上网络请求。原因：M1 只要求 validator、schema fixture、golden samples 和离线边界检查，不允许修改生产链路行为。

M3 必须审计真实脚本：

```text
scripts/run_daily_tw_stock_auto_update.py
触发周期
no_new_data 行为
fresh_data_success 行为
validator_failed 行为
previous latest 是否保留
是否触发 provider accepted latest
是否触发 monitor / broker / order
```

## 11. 结论

Phase M1 已把 M0 的合同文本落成可执行 validator 与 golden samples。正确样例可通过，缺 required fields/audit、含 forbidden fields、越权 action audit、latest pointer 状态机违规、前端 forbidden request/text、Agent forbidden tool/semantics 和默认候选缺用户确认均会失败，并且失败码与 `expected_result.json` 精确匹配。
