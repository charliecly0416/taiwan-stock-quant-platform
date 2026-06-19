# 新策略接入工作模板

用于新增 StrategyRule 和 dependency；输出只能是 OrderIntentArtifact。

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

## 策略补充

```text
strategy_rule:
dependency_yaml:
required_core_fields:
required_extensions:
max_buy_count:
max_sell_count:
OrderIntentArtifact_output:
not_valid_strategy_evidence, if diagnostic_only:
```
