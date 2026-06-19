# Phase M2R Registry Validator 修复执行报告

生成日期：2026-06-17

## 1. 执行范围

本轮执行 Phase M2R：只修复 M2 review 指出的 registry 语义校验缺口和 Agent response semantics audit 未生效问题。

本轮未训练新模型、未新增正式策略、未运行新收益结论、未切默认策略、未触发 provider publish / refresh、未切 accepted latest、未改 monitor / broker / quick-trade / order、未修改前端 Agent 行为、prompt、tool 权限或 action 入口。

## 2. 修复项一：Registry artifact_type / golden contract 错配

修复前，以下 entry 使用了其他 artifact 类型的 pass sample：

```text
model_signal.m2_onboarding_template -> feature_artifact/pass_pit_safe
strategy_rule.m2_onboarding_template -> default_candidate_decision/pass_preserve_current_default
replay_window.m2_onboarding_template -> price_store/pass_minimal
```

修复后，新增同类 golden samples：

```text
data_tw/golden_samples/modular_contracts/m1/model_signal/pass_onboarding_template
data_tw/golden_samples/modular_contracts/m1/strategy_rule/pass_onboarding_template
data_tw/golden_samples/modular_contracts/m1/readonly_replay_window/pass_onboarding_template
```

`configs/tw_modular_registry.yaml` 已改为绑定同 contract sample：

```text
model_signal.m2_onboarding_template -> model_signal/pass_onboarding_template
strategy_rule.m2_onboarding_template -> strategy_rule/pass_onboarding_template
replay_window.m2_onboarding_template -> readonly_replay_window/pass_onboarding_template
```

未采用 alias；当前满足：

```text
entry.artifact_type == golden_sample.expected_result.contract
```

## 3. 修复项二：M2 Registry Validator 语义加强

已更新：

```text
scripts/validate_tw_modular_registry_m2.py
```

新增检查：

```text
读取 golden_sample/expected_result.json
检查 expected_result.contract 与 entry.artifact_type / validator_contract 匹配
检查 validator --list-contracts --json 支持该 contract
实际运行 validator --contract <contract> --artifact-path <golden_sample> --json
```

新增错误码：

```text
registry_contract_mismatch
registry_validator_contract_unsupported
registry_golden_validation_failed
```

## 4. 修复项三：response_semantics_audit 实际生效

已更新：

```text
scripts/validate_tw_modular_m_contracts.py
```

修复内容：

```text
validate_agent() 实际读取 response_semantics_audit
response_semantics_audit.forbidden_semantics_count > 0 返回 forbidden_semantics
response_semantics_audit 缺失仍由 required_audits 返回 audit_missing
```

新增独立失败样例：

```text
data_tw/golden_samples/modular_contracts/m1/agent_readonly_context/fail_response_semantics_audit_count
```

该样例的 `answer_samples` 不含危险文本，只依赖 `response_semantics_audit.forbidden_semantics_count=1` 触发失败。

## 5. 测试补强

已更新：

```text
tests/unit/test_tw_modular_m_contract_validators.py
tests/unit/test_tw_modular_m2_registry_validator.py
```

新增覆盖：

```text
registry artifact_type / golden contract mismatch 会失败
validator 不支持 entry contract 会失败
validator 实际校验 entry golden sample 失败会失败
response_semantics_audit.forbidden_semantics_count > 0 会失败
M1 golden validator 仍通过
M2 registry validator 仍通过
```

## 6. 验证命令与结果

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
M1 golden validator: ok=true, sample_count=33
M2 registry validator: ok=true, registry_count=4, entry_count=14, template_count=9
pytest: 8 passed
```

## 7. 安全边界确认

本轮只改 validator、registry、golden fixture、测试和文档。未触发：

```text
模型训练
新策略收益 replay
默认策略切换
provider publish / refresh
accepted latest switch
monitor / broker / quick-trade / order
前端 Agent 行为、prompt、tool 权限或 action 入口修改
```

## 8. 结论

M2R 已修复阻塞项。Registry validator 不再只做文件存在性检查；所有 registry entry 的 artifact_type / validator contract / golden sample contract 语义一致，且 validator 会实际校验 entry 绑定的 golden sample。Agent response semantics audit 的结构化计数检查已实际生效，并有独立失败样例和单元测试覆盖。
