# 新前端只读展示工作模板

用于新增 readonly display 组件或字段。

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

## 前端补充

```text
GET_only_API_dependency:
allowed_primary_fields:
allowed_audit_fields:
forbidden_text:
forbidden_requests:
readonly_boundary_audit.local_replay: false
readonly_boundary_audit.local_ranking: false
readonly_boundary_audit.local_signal_compute: false
```
