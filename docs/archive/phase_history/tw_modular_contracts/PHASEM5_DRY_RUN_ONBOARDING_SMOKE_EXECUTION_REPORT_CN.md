# Phase M5 Dry-run Onboarding Smoke 执行报告

生成日期：2026-06-17

## 1. 执行结论

Phase M5 已完成 smoke-only / dry-run onboarding 验证。新增 dummy model signal adapter smoke 和 dummy strategy dependency smoke，用于证明新模型/新策略接入流程可通过 registry、合同引用、validator、ModelSignalArtifact 兼容、StrategyDependency 检查和可选 OrderIntentArtifact 兼容检查。

本阶段未训练真实新模型，未新增正式策略收益结论，未运行可被解释为 alpha / return evidence 的 replay，未切默认策略或 default candidate，未触发 provider refresh / publish，未切 accepted latest，未写 monitor config / scan / alerts，未连接 broker / quick-trade / orders，未修改 Agent prompt/tool/action，未修改 `scripts/run_daily_tw_stock_auto_update.py`。

## 2. 交付物

新增 M5 validator：

```text
scripts/validate_tw_modular_m5_smoke.py
```

新增 smoke-only strategy dependency：

```text
configs/strategy_dependencies/dummy_new_strategy_dependency_smoke.yaml
```

新增 M5 golden samples：

```text
data_tw/golden_samples/modular_contracts/m5/onboarding_smoke/pass_minimal
data_tw/golden_samples/modular_contracts/m5/onboarding_smoke/fail_missing_smoke_flags
```

统一回归输出：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/m5_onboarding_smoke_validation.json
```

Registry 新增 M5 smoke registry：

```text
configs/tw_modular_registry.yaml::m5_smoke_registry.entries.model_signal.dummy_new_model_signal_adapter_smoke
configs/tw_modular_registry.yaml::m5_smoke_registry.entries.strategy_rule.dummy_new_strategy_dependency_smoke
```

`strategies.dummy_new_strategy_dependency_smoke` 也已登记 dependency path，但带 `applies_to_artifact_names: [dummy_new_model_signal_adapter_smoke]`，因此对现有正式信号 artifact 全部跳过，不参与正式 replay 或收益结论。

## 3. Smoke 标记

M5 所有 smoke 产物和 registry entry 均要求：

```text
smoke_only=true
not_valid_strategy_evidence=true
no_replay_return_conclusion=true
not_default_candidate=true
```

同时要求以下安全边界为 true 或计数为 0：

```text
no_training=true
no_tuning=true
no_default_switch=true
no_provider_publish=true
no_accepted_latest_switch=true
no_monitor_write=true
no_broker_order=true
agent_untouched=true
```

负例 `fail_missing_smoke_flags` 删除 smoke 标记，validator 返回 `smoke_marker_missing`，证明缺失标记会被拒绝。

## 4. Validator 覆盖

`validate_tw_modular_m5_smoke.py` 覆盖：

```text
registry entry exists
registry production_allowed=false
registry diagnostic_only=true
registry forbidden_consumers 包含 default_candidate / broker / provider_publish
smoke marker enforcement
ModelSignalArtifact compatibility check
StrategyDependency check
OrderIntentArtifact compatibility check
forbidden surface audit
positive / negative golden expectation check
```

正例结果：

```text
ok=true
schema_version=m5.0.0
registry_entries: pass
model_signal_compatibility.ok=true
strategy_dependency_check.ok=true
order_intent_compatibility.status=pass
```

负例结果：

```text
ok=false
actual_error_codes=[smoke_marker_missing]
```

## 5. 回归结果

已复跑：

```bash
python -m py_compile scripts/validate_tw_modular_m5_smoke.py scripts/run_tw_modular_contract_regression.py
python scripts/validate_tw_modular_m5_smoke.py --artifact-path data_tw/golden_samples/modular_contracts/m5/onboarding_smoke/pass_minimal --json
python scripts/validate_tw_modular_m5_smoke.py --run-golden --json
python scripts/validate_tw_frontend_readonly_m4.py --json
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
python scripts/run_tw_modular_contract_regression.py --json
```

结果：

```text
py_compile: pass
M5 pass sample: ok=true
M5 golden: ok=true, sample_count=2
M4R frontend readonly validator: ok=true
M3R daily script audit: ok=true
contract regression: ok=true
m5_onboarding_smoke_status=passed
m5_onboarding_smoke_sample_count=2
```

统一回归中新增 strategy dependency 对 5 个现有正式 signal manifest 均为 skipped：

```text
strategy_dependency=dummy_new_strategy_dependency_smoke
failed_checks=applies_to_artifact_names=['dummy_new_model_signal_adapter_smoke']
```

这证明 M5 smoke dependency 不影响正式模型、策略或 replay pipeline。

## 6. 安全边界

M5 forbidden surface audit：

```text
training_count=0
replay_return_conclusion_count=0
default_switch_count=0
provider_publish_refresh_accepted_latest_count=0
monitor_write_count=0
broker_order_count=0
agent_expansion_count=0
```

M3R script audit 仍通过：

```text
default_provider_refresh_reachable=false
default_provider_publish_reachable=false
default_accepted_latest_reachable=false
```

M4R frontend readonly validator 仍通过：

```text
readonly_workflow_only_get=true
forbidden_request_count=0
replay_strategy_write_count=0
legacy_provider_gate_not_exposed=true
```

## 7. 残余风险

1. M5 只验证 onboarding 流程，不证明任何真实模型、真实策略或收益表现。
2. dummy order intent 仅用于兼容性检查，不是订单、目标仓位或 replay 输入。
3. 未来真实模型/策略仍必须另开阶段，重新完成数据、特征、训练、PIT、回放和前端/Agent 安全审查。

## 8. 结论

Phase M5 完成。Smoke-only onboarding 流程可跑通，validator 能拒绝缺少关键 smoke 标记的样例，统一回归已接入 M5，且未引入训练、收益结论、默认切换、provider/latest、monitor、broker/order 或 Agent 扩权。
