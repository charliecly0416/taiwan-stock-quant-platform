# Phase M2 Registry 与 Onboarding Template 审查及 Phase M2R 修复工作文档

生成日期：2026-06-17

## 1. 审查结论

Phase M2 审查结论：暂不通过，进入 Phase M2R 修复。

M2 的 registry、templates、validator、测试和 regression 接入已经具备基本形态，报告中的验证命令可以复跑通过。但审查发现 registry 语义校验仍有缺口：部分 registry entry 绑定的 validator / golden sample 与自身 `artifact_type` 不一致，M2 validator 只检查了“文件存在”和“validator 支持 `--json`”，没有证明该 entry 能被对应合同 validator 校验。

这会破坏 M2 的核心目标：后续新增模型、策略、replay window 时，registry 不能可靠地把 entry 追溯到正确的 contract、validator 和 golden sample。因此 M2 暂不能进入 M3。

## 2. 审查依据

本次审查参考：

```text
docs/tw_modular_contracts/PHASEM_MODULAR_FOUNDATION_BEFORE_NEW_MODEL_STRATEGY_WORK_CN.md
docs/tw_modular_contracts/PHASEM1_REVIEW_AND_PHASEM2_WORK_CN.md
docs/tw_modular_contracts/PHASEM2_REGISTRY_AND_ONBOARDING_TEMPLATE_EXECUTION_REPORT_CN.md
configs/tw_modular_registry.yaml
configs/data_source_registry.yaml
configs/feature_registry.yaml
configs/price_store_registry.yaml
docs/tw_modular_contracts/templates/
scripts/validate_tw_modular_registry_m2.py
scripts/validate_tw_modular_m_contracts.py
scripts/run_tw_modular_contract_regression.py
tests/unit/test_tw_modular_m2_registry_validator.py
```

## 3. 复跑结果

审查复跑：

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

说明：两个单独 validator 命令第一次在普通沙箱中被 bwrap 限制拦截，提升权限只读复跑通过。

## 4. Findings

### High. Registry entry 的 artifact_type 与 golden sample contract 不一致

证据：

```text
configs/tw_modular_registry.yaml:153-159
configs/tw_modular_registry.yaml:174-180
configs/tw_modular_registry.yaml:194-200
scripts/validate_tw_modular_registry_m2.py:120-132
```

当前主 registry 中至少三处 entry 存在错配：

```text
model_signal.m2_onboarding_template
  artifact_type=model_signal
  validator=scripts/validate_tw_modular_m_contracts.py
  golden_sample=data_tw/golden_samples/modular_contracts/m1/feature_artifact/pass_pit_safe
  golden_contract=feature_artifact

strategy_rule.m2_onboarding_template
  artifact_type=strategy_rule
  validator=scripts/validate_tw_modular_m_contracts.py
  golden_sample=data_tw/golden_samples/modular_contracts/m1/default_candidate_decision/pass_preserve_current_default
  golden_contract=default_candidate_decision

replay_window.m2_onboarding_template
  artifact_type=readonly_replay_window
  validator=scripts/validate_tw_modular_m_contracts.py
  golden_sample=data_tw/golden_samples/modular_contracts/m1/price_store/pass_minimal
  golden_contract=price_store
```

复现命令：

```bash
python scripts/validate_tw_modular_m_contracts.py --contract model_signal --artifact-path data_tw/golden_samples/modular_contracts/m1/feature_artifact/pass_pit_safe --json
```

复现结果：

```text
ok=false
status=unknown_contract
code=unknown_contract
```

问题原因是 M2 validator 目前只检查 `validator` 文件存在、能执行 `--list-contracts --json`，以及 `golden_sample/expected_result.json` 存在；没有检查：

```text
entry.artifact_type 是否被 validator 支持
golden_sample.expected_result.contract 是否与 entry.artifact_type 或明确 contract_alias 匹配
validator 是否能用 entry 对应 contract 实际校验该 golden sample
```

影响：

```text
M2 registry 不能可靠证明 model_signal / strategy_rule / readonly_replay_window 的 onboarding entry 可被对应合同校验。
后续 M3-M5 若依赖该 registry，会把错误 validator/golden sample 当成已覆盖。
```

修复要求：

```text
为 model_signal、strategy_rule、readonly_replay_window 绑定真实可用的 validator 和同类 golden sample；
或在 registry 中显式声明 contract_alias / validator_contract，并由 M2 validator 检查 alias 合理性；
禁止用 feature_artifact、price_store、default_candidate_decision 的 pass sample 代替不同 artifact_type 的验证证据。
```

### Medium. `response_semantics_audit` 补强声明没有实际生效

证据：

```text
docs/tw_modular_contracts/PHASEM2_REGISTRY_AND_ONBOARDING_TEMPLATE_EXECUTION_REPORT_CN.md:172-184
scripts/validate_tw_modular_m_contracts.py:212-220
```

执行报告声明 M2 已补强：

```text
response_semantics_audit.forbidden_semantics_count must be 0
```

但实现中 `validate_agent()` 只遍历：

```python
for key in ["agent_tool_audit", "panel_boundary_audit"]:
```

后续分支却判断：

```python
if key == "response_semantics_audit" ...
```

该分支永远不会触发。因此如果某个样例只在 `response_semantics_audit.json` 中声明 `forbidden_semantics_count > 0`，但 `manifest.answer_samples` 没有危险文本，validator 会漏报。

修复要求：

```text
把 response_semantics_audit 纳入 validate_agent() 的实际读取列表；
新增 fail sample，专门验证 forbidden_semantics_count > 0 会失败；
更新 expected_result.json，确保失败码为 forbidden_semantics；
补单元测试防止该分支再次失效。
```

### Low. M2 validator 对 template 仍以 marker 存在为主

证据：

```text
scripts/validate_tw_modular_registry_m2.py:146-164
```

当前模板校验主要检查必填 marker 是否出现，尚未解析模板结构，也未确认每个模板的禁止事项和默认值是否在固定字段块内。这不阻塞 M2R 的主修复，但建议后续继续加强。

## 5. 台股只读安全边界审查

安全边界结论：未发现真实危险动作入口。

```text
未发现真实 broker / quick-trade / order 写入口
未发现真实 target_position / target_weight 执行动作入口
未发现真实 provider publish / refresh 入口
未发现真实 accepted latest switch 入口
未发现 monitor config save / scan / alerts write 入口
危险词主要出现在 forbidden_consumers、禁止事项、validator 禁令、负例 fixture 或报告说明中
```

安全边界不阻塞；阻塞项是 registry contract/golden sample 语义错配和 `response_semantics_audit` 补强未生效。

## 6. Phase M2R 修复目标

M2R 只修复 M2 registry / validator / sample / test 缺口，不进入 M3，不审计真实两小时自动脚本，不改真实日更行为，不改前端 Agent 行为。

M2R 禁止：

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

## 7. M2R 必交付物

### 7.1 Registry 语义修复

修复 `configs/tw_modular_registry.yaml` 中错配 entry：

```text
model_signal.m2_onboarding_template
strategy_rule.m2_onboarding_template
replay_window.m2_onboarding_template
```

每个 entry 必须满足以下之一：

```text
artifact_type == golden_sample.expected_result.contract
```

或显式声明并校验：

```text
validator_contract
contract_alias_reason
```

如果采用 alias，M2R 报告必须说明为什么该 alias 合法，且不得用无关 artifact 的 pass sample 充当覆盖。

### 7.2 M2 Validator 加强

更新 `scripts/validate_tw_modular_registry_m2.py`：

```text
读取 golden_sample/expected_result.json
检查 expected_result.contract 与 entry.artifact_type 或 validator_contract 匹配
检查 validator --list-contracts --json 返回支持该 contract
实际运行 validator --contract <contract> --artifact-path <golden_sample> --json
把失败写入明确 error code，例如 registry_contract_mismatch / registry_validator_contract_unsupported / registry_golden_validation_failed
```

### 7.3 Agent response semantics 修复

更新 `scripts/validate_tw_modular_m_contracts.py`：

```text
validate_agent() 必须实际读取 response_semantics_audit
forbidden_semantics_count > 0 必须失败
缺失 response_semantics_audit 时仍按 required_audits 返回 audit_missing
```

新增或调整 golden sample：

```text
agent_readonly_context/fail_response_semantics_audit_count/
```

该样例应只依赖 `response_semantics_audit.forbidden_semantics_count > 0` 触发失败，避免被 `answer_samples` 文本扫描掩盖。

### 7.4 测试与报告

更新：

```text
tests/unit/test_tw_modular_m2_registry_validator.py
tests/unit/test_tw_modular_m_contract_validators.py
docs/tw_modular_contracts/PHASEM2R_REGISTRY_VALIDATOR_REPAIR_EXECUTION_REPORT_CN.md
```

测试必须覆盖：

```text
registry artifact_type / golden contract mismatch 会失败
validator 不支持 entry contract 会失败
validator 能实际校验 entry golden sample
response_semantics_audit.forbidden_semantics_count > 0 会失败
M1 golden validator 仍通过
M2 registry validator 通过
```

## 8. M2R 验收门槛

M2R 通过必须同时满足：

```text
M2 registry validator 不再只做存在性检查
所有 registry entry 的 artifact_type / validator_contract / golden sample contract 语义一致
model_signal、strategy_rule、readonly_replay_window entry 不再指向无关 artifact 的 pass sample
response_semantics_audit.forbidden_semantics_count > 0 有独立失败样例
py_compile 通过
M1 golden validator 通过
M2 registry validator 通过
pytest 覆盖 M1/M2R 并通过
没有训练、replay、默认策略切换、provider publish、accepted latest、monitor/broker/order 或 Agent 扩权
```

修复通过审查后，才允许进入 Phase M3。
