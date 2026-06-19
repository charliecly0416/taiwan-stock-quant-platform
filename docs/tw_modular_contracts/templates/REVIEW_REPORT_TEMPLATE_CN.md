# 审查报告模板


## 必填项

```text
contract_doc:
schema_version: m1.0.0
input_artifacts:
output_artifacts:
validator_command:
golden_sample_path:
allowed_consumers:
forbidden_consumers:
readonly_boundary:
forbidden_actions_audit:
rollback_or_failure_policy:
diagnostic_only:
production_allowed: false
```

## 禁止事项

```text
不训练新模型，除非另开模型训练阶段
不运行新收益结论
不切默认策略
不触发 provider publish / refresh
不切 accepted latest
不写 monitor / broker / quick-trade / order
不修改前端 Agent 行为、prompt、tool 权限或 action 入口
```

## 审查结论

```text
conclusion: pass / conditional_pass / reject
reviewed_files:
validator_commands_replayed:
findings_by_severity:
residual_risks:
next_phase_allowed:
```
