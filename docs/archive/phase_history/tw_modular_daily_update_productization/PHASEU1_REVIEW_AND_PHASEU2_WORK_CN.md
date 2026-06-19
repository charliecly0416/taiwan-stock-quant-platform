# Phase U1 审查与 Phase U2 工作文档

生成日期：2026-06-17

## 1. 审查结论

Phase U1 通过，允许进入 Phase U2。

U1 已按 U0 审查要求新增每日 DataIngestionArtifact、FeatureArtifact、ModelSignalArtifact 的 staging builder / validator，并提供 `fresh_data_detected` 与 `no_new_data` 两类产物和 pass/fail golden samples。审查复跑显示 U1 没有训练新模型、没有调参、没有替换冻结模型权重、没有生成 OrderIntentArtifact、没有生成 ReadonlyStrategySnapshot、没有更新 readonly latest pointer、没有触发 provider refresh / publish、没有切 provider accepted latest 或 qlib accepted latest、没有写 monitor / broker / order、没有修改 Agent prompt / tool / action。

放行条件：U2 可以消费 U1 生成的 daily ModelSignalArtifact，但不得跳过 U2 自身 OrderIntent / ReadonlySnapshot / RunRegistry / latest pointer validator。U2 不得把 U1 staging output 当成可展示、可发布或可交易结果。

## 2. 复核范围

审查输入：

```text
docs/tw_modular_daily_update_productization/PHASEU1_DAILY_DATA_FEATURE_MODEL_SIGNAL_EXECUTION_REPORT_CN.md
docs/tw_modular_daily_update_productization/PHASEU0_REVIEW_AND_PHASEU1_WORK_CN.md
scripts/build_tw_daily_data_ingestion_artifact.py
scripts/validate_tw_daily_data_ingestion_artifact.py
scripts/build_tw_daily_feature_artifact.py
scripts/validate_tw_daily_feature_artifact.py
scripts/build_tw_daily_model_signal_artifact.py
scripts/validate_tw_daily_model_signal_artifact.py
data_tw/golden_samples/modular_daily_update/u1/
data_tw/artifacts/daily_data_ingestion/u1_fresh_data_detected_demo/
data_tw/artifacts/daily_data_ingestion/u1_no_new_data_noop_demo/
data_tw/artifacts/daily_features/u1_fresh_features_demo/
data_tw/artifacts/daily_features/u1_no_new_data_features_noop_demo/
data_tw/artifacts/daily_model_signals/e4_frozen_qlib_2023_2025_ltr/u1_fresh_model_signal_demo/
data_tw/artifacts/daily_model_signals/e4_frozen_qlib_2023_2025_ltr/u1_no_new_data_model_signal_noop_demo/
data_tw/experiments/modular_daily_update/u1_validation_summary.json
```

审查重点：

```text
U1 是否只生成 DataIngestion / Feature / ModelSignal artifact
fresh_data_detected 与 no_new_data 是否都有可验证样例
no_new_data 是否明确 updates_readonly_latest=false
ModelSignal 是否保持 U0 冻结候选 e4_frozen_qlib_2023_2025_ltr + top50_exit_one_worst_sell
validator 是否覆盖 PIT、future/action 字段、禁止动作标志、core fields 和 source artifacts
是否未触发 provider/latest、monitor/broker/order、Agent 扩权
M3 legacy gate 与 M4 frontend GET-only gate 是否仍通过
```

## 3. 通过项

### 3.1 U1 产物边界正确

U1 只新增三类 staging artifact：

```text
daily_data_ingestion
daily_feature_artifact
daily_model_signal
```

未生成：

```text
OrderIntentArtifact
ReadonlyStrategySnapshot
RunRegistry
readonly latest pointer update
provider accepted latest / qlib accepted latest
```

这符合 U1 范围。U2 才能进入 OrderIntent / Snapshot / RunRegistry / readonly latest pointer 行为验证。

### 3.2 Fresh 与 no_new_data 两类样例齐全

Fresh staging chain：

```text
data_tw/artifacts/daily_data_ingestion/u1_fresh_data_detected_demo/manifest.json
data_tw/artifacts/daily_features/u1_fresh_features_demo/manifest.json
data_tw/artifacts/daily_model_signals/e4_frozen_qlib_2023_2025_ltr/u1_fresh_model_signal_demo/manifest.json
```

No-new-data noop chain：

```text
data_tw/artifacts/daily_data_ingestion/u1_no_new_data_noop_demo/manifest.json
data_tw/artifacts/daily_features/u1_no_new_data_features_noop_demo/manifest.json
data_tw/artifacts/daily_model_signals/e4_frozen_qlib_2023_2025_ltr/u1_no_new_data_model_signal_noop_demo/manifest.json
```

no_new_data 产物均声明：

```text
freshness_status=no_new_data
row_count=0
updates_readonly_latest=false
```

审查复跑 no_new_data ModelSignalArtifact validator 通过，说明 noop 不会伪造成新信号或 latest 更新。

### 3.3 Golden samples 覆盖正负例

复跑 U1 golden validator：

```text
DataIngestion golden: ok=true, sample_count=4
Feature golden: ok=true, sample_count=4
ModelSignal golden: ok=true, sample_count=5
```

负例覆盖：

```text
fail_forbidden_action_marker_missing
fail_no_new_data_updates_latest
fail_missing_available_at
fail_future_field_present
```

具体阻断结果包括：

```text
no_new_data_updates_latest
readonly_latest_update_forbidden
available_at_after_signal_asof
future_field_present
model_signal_core_field_missing
forbidden_action_marker_missing
```

### 3.4 Direct artifact validation 通过

已复跑：

```bash
python scripts/validate_tw_daily_data_ingestion_artifact.py --artifact-path data_tw/artifacts/daily_data_ingestion/u1_fresh_data_detected_demo --json
python scripts/validate_tw_daily_feature_artifact.py --artifact-path data_tw/artifacts/daily_features/u1_fresh_features_demo --json
python scripts/validate_tw_daily_model_signal_artifact.py --artifact-path data_tw/artifacts/daily_model_signals/e4_frozen_qlib_2023_2025_ltr/u1_fresh_model_signal_demo --json
python scripts/validate_tw_daily_model_signal_artifact.py --artifact-path data_tw/artifacts/daily_model_signals/e4_frozen_qlib_2023_2025_ltr/u1_no_new_data_model_signal_noop_demo --json
```

结果均为：

```text
ok=true
status=passed
```

### 3.5 冻结候选保持一致

U1 ModelSignalArtifact 保持 U0 冻结范围：

```text
model_id=e4_frozen_qlib_2023_2025_ltr
model_family=ltr
strategy_compatibility=top50_exit_one_worst_sell
candidate_k=50
readonly_only=true
updates_readonly_latest=false
no_training=true
no_tuning=true
no_score_recompute_outside_frozen_model=true
no_default_strategy_switch=true
no_provider_publish=true
no_accepted_latest_switch=true
```

U1 builder 从冻结既有 ModelSignalArtifact 按 asof 截取，不训练、不调参、不替换模型权重。

### 3.6 安全 gate 仍通过

复跑 M3 daily audit：

```text
ok=true
default_provider_refresh_reachable=false
default_provider_publish_reachable=false
default_accepted_latest_reachable=false
readonly_latest_pointer_distinct=true
```

复跑 M4 frontend readonly validator：

```text
ok=true
readonly_workflow_only_get=true
forbidden_request_count=0
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
ops_provider_publish_refresh_accepted_latest_request_count=0
replay_strategy_write_count=0
broker_quick_trade_orders_request_count=0
agent_implementation_untouched=true
```

## 4. 台股只读安全边界审查

### Findings

Critical：未发现 U1 触发 provider refresh / publish、accepted latest switch、broker / quick-trade / orders、target position 或真实交易路径。

High：未发现 U1 写 monitor config / scan / alerts，未发现 readonly latest pointer 更新，未发现 OrderIntent / Snapshot 生成。

Medium：Feature validator 当前检查 manifest 禁止标志、`updates_readonly_latest=false`、PIT 与 future fields，但未像 DataIngestion / ModelSignal validator 那样读取 `forbidden_action_audit.json` 中每个 action value 并阻断 `true`。当前不阻塞 U2，因为 Feature manifest 标志、ModelSignal validator 和 U2 自身 validator 仍是硬门；但 U2 不得把 Feature forbidden_action_audit 当成已完整校验的安全证据。若后续文档继续声称 Feature validator 覆盖 action audit values，应补强 validator 或修正文档表述。

Low：U1 fresh staging 使用本地 demo normalized 数据，适合 U1 dry-run/staging；后续接真实日更数据时，仍需在 U2/U3 前明确 provider 访问、raw archive 写入和失败回滚策略。

### Verdict

U1 通过。Daily data / feature / model signal staging 链路已具备进入 U2 的基础，但 U2 必须重新验证 OrderIntent、ReadonlySnapshot、RunRegistry 和 readonly latest pointer 行为，不能沿用 U1 结果作为发布证据。

## 5. 残余风险

1. Feature validator 对 `forbidden_action_audit.json` action values 的检查弱于 DataIngestion / ModelSignal validator。U2 如消费 FeatureArtifact，应优先依赖已通过的 ModelSignalArtifact，并在 U2 validator 中重新检查 forbidden action。
2. U1 产物是 staging/demo 链路，不能被前端展示为正式 daily result。
3. U1 没有实现真实 provider 拉取或 raw archive 写入，这符合范围；U3 接入自动化前必须重新审查真实数据来源。
4. U1 没有更新 readonly latest pointer，这符合范围；U2 才允许在 validator-gated 条件下测试 latest pointer 行为。

## 6. Phase U2 工作范围

U2 目标：从 U1 `ModelSignalArtifact` 生成每日只读 `OrderIntentArtifact`，再生成 `ReadonlyStrategySnapshot`、写入 `RunRegistry`，并在全部 validator 通过后验证 readonly latest pointer 行为。

U2 可以新增或扩展：

```text
scripts/build_tw_daily_order_intent_artifact.py
scripts/validate_tw_daily_order_intent_artifact.py
scripts/publish_tw_daily_readonly_snapshot.py
scripts/validate_tw_daily_readonly_snapshot.py
scripts/validate_tw_daily_run_registry.py
```

建议输出目录：

```text
data_tw/artifacts/daily_order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/<run_id>/
data_tw/artifacts/daily_readonly_snapshots/<run_id>/
data_tw/artifacts/daily_run_registry/<run_id>/
data_tw/artifacts/daily_readonly_latest/latest.json
```

## 7. U2 必须实现的合同行为

### 7.1 OrderIntentArtifact

必须声明：

```text
readonly_only=true
not_order=true
not_target_position=true
not_investment_advice=true
no_broker_order=true
strategy_rule=top50_exit_one_worst_sell
model_id=e4_frozen_qlib_2023_2025_ltr
source_signal_artifact
portfolio_state_source
max_buy_count=1
max_sell_count=1
```

必须禁止：

```text
execution_price
cash
equity
broker_order_id
target_position
target_weight
order_qty
order_id
quick_trade
```

### 7.2 ReadonlySnapshot

必须从 OrderIntentArtifact 生成，只用于研究展示：

```text
readonly_only=true
not_order=true
not_target_position=true
not_investment_advice=true
production_trade_enabled=false
source_order_intent_artifact
source_model_signal_artifact
source_strategy_rule
audit_status
checksum
```

不得把 snapshot 写成交易建议、目标仓位、自动买卖或收益承诺。

### 7.3 RunRegistry 与 latest pointer

RunRegistry 必须覆盖四类状态：

```text
success_validators_passed_updates_readonly_latest
no_new_data_noop_preserves_previous_latest
validator_failed_preserves_previous_latest
module_failed_preserves_previous_latest
```

readonly latest pointer 必须记录：

```text
previous_latest
proposed_latest
committed_latest
checksum
run_id
status
updated_only_after_all_validators_passed=true
not_provider_accepted_latest=true
not_qlib_accepted_latest=true
not_trade_target_latest=true
```

## 8. U2 Validator / Golden Sample 要求

U2 必须提供 pass/fail golden samples。最低要求：

```text
pass_success_updates_readonly_latest
pass_no_new_data_preserves_previous_latest
pass_validator_failed_preserves_previous_latest
pass_module_failed_preserves_previous_latest
fail_order_intent_contains_broker_order
fail_order_intent_contains_target_position
fail_snapshot_missing_readonly_flags
fail_latest_pointer_updates_before_validators_pass
fail_latest_pointer_is_provider_accepted_latest
```

Validator 必须能阻断：

```text
OrderIntent 缺 readonly_only / not_order / not_target_position / not_investment_advice
OrderIntent 出现 execution / broker / order / target_position / target_weight / cash / equity 字段
策略读取 replay result 或模型私有字段
Snapshot 缺 source_order_intent_artifact / checksum / readonly flags
validator_failed 或 module_failed 更新 latest
no_new_data 更新 latest
latest pointer 指向 provider accepted latest 或 qlib accepted latest
latest pointer 缺 previous/proposed/committed/checksum/run_id
```

## 9. U2 禁止事项

U2 不得做以下事项：

```text
不得训练新模型
不得调参或替换冻结模型权重
不得触发 provider refresh / publish
不得切 provider accepted latest 或 qlib accepted latest
不得写 monitor config / scan / alerts
不得连接 broker / quick-trade / orders
不得修改 Agent prompt / tool / action
不得让前端本地计算策略或 replay
不得把 U1/U2 staging 产物接入前端默认展示
不得运行正式收益结论 replay
```

U2 可以验证 readonly latest pointer 的 staging 行为，但只能在全部 U2 validator 通过后更新 U2 专用 readonly latest pointer 路径；不得修改 provider accepted latest、qlib accepted latest 或既有生产交易状态。

## 10. U2 审查建议

U2 执行报告提交后，审查者应重点检查：

1. OrderIntent 是否仍是 observation / intent 语义，不是订单或目标仓位。
2. Snapshot 是否只读展示，不含交易建议、自动买卖或收益承诺。
3. RunRegistry 是否覆盖 success/no_new_data/validator_failed/module_failed 四类状态。
4. latest pointer 是否只在全部 validator 通过后更新，失败和 noop 是否保留 previous latest。
5. U2 是否没有触发 provider/latest、monitor/broker/order、Agent 扩权。
6. U2 是否没有把 staging 产物接入前端默认展示；前端/API 接入留到 U3。

U2 通过后，才允许进入 U3 的自动脚本接入、前端/API 验收和最终 runbook。
