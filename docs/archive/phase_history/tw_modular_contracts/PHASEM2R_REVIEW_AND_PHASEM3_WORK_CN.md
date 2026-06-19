# Phase M2R Registry Validator 修复审查及 Phase M3 工作文档

生成日期：2026-06-17

## 1. 审查结论

Phase M2R 审查结论：通过，允许进入 Phase M3。

执行者提交的 `PHASEM2R_REGISTRY_VALIDATOR_REPAIR_EXECUTION_REPORT_CN.md` 已修复 M2 review 的两个阻塞项：

```text
registry artifact_type / golden sample contract 错配
response_semantics_audit.forbidden_semantics_count 检查未实际生效
```

本轮没有训练新模型、没有新增正式策略、没有运行新收益结论、没有切默认策略、没有触发 provider publish / refresh、没有切 accepted latest、没有改 monitor / broker / quick-trade / order，也没有修改前端 Agent 行为、prompt、tool 权限或 action 入口。

## 2. 审查依据

本次审查参考：

```text
docs/tw_modular_contracts/PHASEM2_REVIEW_AND_PHASEM2R_WORK_CN.md
docs/tw_modular_contracts/PHASEM2R_REGISTRY_VALIDATOR_REPAIR_EXECUTION_REPORT_CN.md
configs/tw_modular_registry.yaml
scripts/validate_tw_modular_m_contracts.py
scripts/validate_tw_modular_registry_m2.py
scripts/run_tw_modular_contract_regression.py
tests/unit/test_tw_modular_m_contract_validators.py
tests/unit/test_tw_modular_m2_registry_validator.py
data_tw/golden_samples/modular_contracts/m1/
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
M1 golden validator: ok=true, sample_count=33
M2 registry validator: ok=true, registry_count=4, entry_count=14, template_count=9
pytest: 8 passed
```

说明：两个单独 validator 命令在普通沙箱中被 bwrap 限制拦截，提升权限只读复跑通过。

## 4. 通过项

### 4.1 Registry 语义错配已修复

主 registry 中关键 entry 已改为同 contract golden sample：

```text
model_signal.m2_onboarding_template -> model_signal/pass_onboarding_template
strategy_rule.m2_onboarding_template -> strategy_rule/pass_onboarding_template
replay_window.m2_onboarding_template -> readonly_replay_window/pass_onboarding_template
```

审查解析结果：

```text
所有主 registry entry 均满足 artifact_type == golden_sample.expected_result.contract
```

### 4.2 M2 Registry Validator 已从存在性检查升级为语义检查

`scripts/validate_tw_modular_registry_m2.py` 已补充：

```text
读取 golden_sample/expected_result.json
检查 expected_result.contract 与 entry.artifact_type / validator_contract 匹配
检查 validator --list-contracts --json 是否支持对应 contract
实际运行 validator --contract <contract> --artifact-path <golden_sample> --json
```

新增错误码已进入测试覆盖：

```text
registry_contract_mismatch
registry_validator_contract_unsupported
registry_golden_validation_failed
```

### 4.3 Agent response semantics audit 已实际生效

`scripts/validate_tw_modular_m_contracts.py` 的 `validate_agent()` 已实际读取：

```text
agent_tool_audit
response_semantics_audit
panel_boundary_audit
```

新增独立失败样例：

```text
data_tw/golden_samples/modular_contracts/m1/agent_readonly_context/fail_response_semantics_audit_count
```

该样例不依赖 `answer_samples` 危险文本，只通过 `response_semantics_audit.forbidden_semantics_count=1` 触发 `forbidden_semantics`。

### 4.4 台股只读安全边界通过

安全边界审查结果：

```text
未发现真实 broker / quick-trade / order 写入口
未发现真实 target_position / target_weight 执行动作入口
未发现真实 provider publish / refresh 入口
未发现真实 accepted latest switch 入口
未发现 monitor config save / scan / alerts write 入口
危险词主要出现在 forbidden_consumers、禁止事项、validator 禁令、负例 fixture 或报告说明中
```

## 5. 残余风险

### Low. 新增 onboarding contract 目前主要补了 pass sample

M2R 为 `model_signal`、`strategy_rule`、`readonly_replay_window` 补了同类 pass sample，并解决了 registry 语义错配。由于本轮目标是修复 registry 映射，不要求为这三个新增 onboarding contract 建完整正负例矩阵，因此不阻塞 M3。

后续 M5 dry-run harness 或新模型/新策略接入前，应为这些 contract 补充更完整负例：

```text
model_signal missing adapter / forbidden field
strategy_rule missing dependency / broker consumer
readonly_replay_window non-GET API / accepted latest switch
```

## 6. Phase M3 目标

Phase M3 名称：Daily Orchestrator and Latest Pointer Boundary。

目标是冻结日更链路模块边界，把既有两小时自动更新脚本纳入可审计 orchestrator contract；只做 readonly shadow / dry-run 编排，不改变当前生产日更行为。

M3 必须证明：

```text
no_new_data 不更新 readonly latest pointer
fresh_data_success 只有在所有 validators 通过后才更新 readonly latest pointer
validator_failed / module_failed 保留 previous latest
readonly latest pointer != provider accepted latest
readonly latest pointer != qlib accepted latest
既有两小时脚本不触发 provider publish / refresh
既有两小时脚本不切 accepted latest
既有两小时脚本不写 monitor / broker / quick-trade / order
```

M3 不允许：

```text
训练新模型
新增正式策略
运行新收益结论
切默认策略
触发 provider publish / refresh
切 accepted latest
改 monitor / broker / quick-trade / order
修改前端 Agent 行为、prompt、tool 权限或 action 入口
用新大脚本替代旧大脚本
```

## 7. M3 必交付物

### 7.1 Orchestrator dry-run contract

新增或完善 dry-run orchestrator 产物，建议路径：

```text
data_tw/golden_samples/modular_contracts/m3/daily_orchestrator/
data_tw/golden_samples/modular_contracts/m3/run_registry/
data_tw/golden_samples/modular_contracts/m3/auto_update/
```

至少覆盖：

```text
no_new_data_noop_preserves_previous_latest
fresh_data_success_validators_passed_updates_readonly_latest
validator_failed_preserves_previous_latest
module_failed_preserves_previous_latest
forbidden_provider_publish_rejected
forbidden_accepted_latest_switch_rejected
forbidden_monitor_broker_order_rejected
```

### 7.2 既有两小时脚本审计

必须审计：

```text
scripts/run_daily_tw_stock_auto_update.py
```

审计内容：

```text
触发周期
no_new_data 行为
fresh_data_success 行为
validator_failed 行为
previous latest 是否保留
readonly latest pointer 更新条件
是否触发 provider publish / refresh
是否触发 provider accepted latest / qlib accepted latest
是否触发 monitor config save / scan / alerts write
是否触发 broker / quick-trade / order
```

### 7.3 M3 validator / regression

新增或扩展：

```text
scripts/validate_tw_daily_orchestrator_m3.py
scripts/run_tw_modular_contract_regression.py
tests/unit/test_tw_modular_m3_daily_orchestrator.py
```

validator 至少输出：

```text
ok
status
errors
warnings
checked_files
run_id
previous_latest
committed_latest
latest_pointer_policy
forbidden_action_audit
```

### 7.4 文档

新增：

```text
docs/tw_modular_contracts/PHASEM3_DAILY_ORCHESTRATOR_AND_LATEST_POINTER_EXECUTION_REPORT_CN.md
```

执行报告必须列出：

```text
validator 命令
dry-run 样例路径
既有两小时脚本审计结果
no_new_data / success / validator_failed / module_failed 结果
latest pointer previous/proposed/committed 对比
禁止事项确认
未覆盖项
```

## 8. M3 验收门槛

M3 审查通过必须同时满足：

```text
有 dry-run daily modular chain 样例
既有两小时自动更新脚本已被审计并映射到 orchestrator contract
no_new_data 不更新 latest
fresh_data_success 只有所有 validators 通过后才更新 readonly latest
validator_failed / module_failed 保留 previous latest
RunRegistry 记录 previous_latest / proposed_latest / committed_latest / run_id / checksum
失败样例证明 previous latest 保持不变
不会触发真实 provider refresh / publish
不会切 provider accepted latest 或 qlib accepted latest
不会写 monitor / broker / quick-trade / order
contract regression 纳入 M3 validator
测试可本地运行并通过
```

修复通过后方可进入 Phase M4。
