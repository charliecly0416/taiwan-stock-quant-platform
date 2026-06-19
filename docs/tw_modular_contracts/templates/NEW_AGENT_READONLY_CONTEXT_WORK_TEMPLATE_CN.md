# 新 Agent Readonly Context 工作模板

M0-M6 只允许 placeholder，不允许功能扩权。

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

## Agent 边界

```text
readonly_artifact_only: true
not_in_m0_m6_implementation_scope: true
future_agent_phase_required: true
no_order_action: true
no_target_position: true
no_provider_publish: true
no_accepted_latest_switch: true
no_monitor_write: true
no_broker_or_order: true
forbidden_tool_calls:
forbidden_answer_semantics:
panel_boundary_audit.prompt_expanded: false
panel_boundary_audit.tool_permissions_expanded: false
panel_boundary_audit.action_entry_expanded: false
```
