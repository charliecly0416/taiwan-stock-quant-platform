# 执行报告模板

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

## 执行范围

```text
objective:
module_owner:
artifact_type:
run_id:
asof:
source_artifacts:
created_artifacts:
```

## Validator 与 Golden Sample

```text
validator_command:
validator_result:
golden_sample_path:
negative_sample_path:
```

## Consumer 边界

```text
allowed_consumers:
forbidden_consumers:
readonly_boundary:
diagnostic_only:
production_allowed: false
```

## Forbidden Actions Audit

```text
forbidden_actions_audit:
no_provider_publish:
no_accepted_latest_switch:
no_monitor_write:
no_broker_or_order:
not_default_model_or_strategy:
```

## 失败与回滚

```text
rollback_or_failure_policy:
known_gaps:
blocking_issues:
next_review_required:
```
