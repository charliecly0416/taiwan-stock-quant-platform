# Phase U0 审查与 Phase U1 工作文档

生成日期：2026-06-17

## 1. 审查结论

Phase U0 通过，允许进入 Phase U1。

U0 按 `MODULAR_DAILY_UPDATE_PRODUCTIZATION_MAINLINE_CN.md` 完成了合同冻结与当前日更链路审计：列出了既有自动更新入口、前端/API readonly latest 读取入口、当前默认路径、legacy provider publish / accepted latest 路径、monitor/broker/order 边界，以及本主线冻结的默认 readonly candidate。

本轮没有发现生产代码修改、真实日更触发、provider refresh / publish、provider accepted latest 或 qlib accepted latest 切换、monitor config / scan / alerts 写入、broker / quick-trade / orders、训练、调参或重算模型分数。

## 2. 复核范围

审查输入：

```text
docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_PRODUCTIZATION_MAINLINE_CN.md
docs/tw_modular_daily_update_productization/PHASEU0_CONTRACT_AND_CURRENT_CHAIN_AUDIT_EXECUTION_REPORT_CN.md
scripts/run_daily_tw_stock_auto_update.py
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
backend/app/routes/readonly_strategy_snapshot.py
backend/app/services/readonly_strategy_snapshot.py
frontend/src/api/tw-stock.js
```

审查重点：

```text
U0 是否只做审计和冻结，不触发日更
既有两小时脚本默认路径是否仍不触发 provider publish / accepted latest
legacy provider path 是否被明确划为非默认路径
readonly latest pointer 是否区别于 provider accepted latest / qlib accepted latest
本主线默认 model / strategy / source artifacts 是否冻结
monitor / broker / order / Agent 是否未被纳入 U 主线默认链路
U1 工作范围是否能安全进入 dry-run / staging artifact builder
```

## 3. 通过项

### 3.1 U0 范围保持正确

执行报告明确 U0 只做：

```text
合同冻结
现状审计
候选范围冻结
legacy path 与 readonly path 划分
```

审查未发现 U0 修改生产代码、运行日更脚本、触发数据 provider、切换 accepted latest 或生成新的策略/收益结论。

### 3.2 自动更新入口审计充分

U0 已列出：

```text
scripts/run_daily_tw_stock_auto_update.py
docs/tw-daily-auto-update.cron.example
data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron
data_tw/ops/daily_auto_update/cron.log
backend/app/services/tw_stock_daily_auto_update_status.py
GET /api/tw-stock/quant/ops/daily-auto-update/status
```

其中仓库内 installed cron 标记和日志路径被标为现状审计对象，U0 没有修改或触发系统级 cron。

### 3.3 Legacy provider path 已与 U 主线默认路径分离

`scripts/run_daily_tw_stock_auto_update.py` 仍包含 legacy provider refresh / publish / accepted latest 能力，但当前默认 gate 关闭：

```text
--enable-legacy-provider-publish=false
TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH=false
```

复跑 M3 daily audit：

```text
ok=true
legacy_provider_gate_present=true
legacy_provider_gate_default_disabled=true
provider_refresh_guarded=true
provider_publish_guarded=true
accepted_latest_call_guarded=true
default_provider_refresh_reachable=false
default_provider_publish_reachable=false
default_accepted_latest_reachable=false
readonly_latest_pointer_distinct=true
```

保留 warning 是合理的：legacy 代码路径存在，但不属于 U 主线默认能力。后续 U1-U3 不得把该 warning 解释为允许接入 provider publish / accepted latest。

### 3.4 Readonly latest pointer 边界清楚

当前 pointer：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
```

关键字段：

```text
artifact_type=readonly_strategy_snapshot_latest_pointer
asof=2026-06-16
readonly_only=true
production_trade_enabled=false
not_provider_accepted_latest=true
not_trade_target_latest=true
snapshot_manifest=data_tw/artifacts/publish/readonly_strategy_snapshot/2026-06-16/manifest.json
```

后端 readonly snapshot route 仅暴露 GET：

```text
GET /api/tw-stock/readonly-strategy-snapshot
GET /api/tw-stock/readonly-strategy-snapshot/<asof>
```

loader 校验 `not_provider_accepted_latest`、`not_trade_target_latest`、`not_target_position`、`not_order` 等安全标志。该 pointer 可作为 U 主线后续 readonly latest 的现有基础，但不能等同于 provider accepted latest 或 qlib accepted latest。

### 3.5 候选模型与策略冻结完整

U0 冻结默认 readonly candidate：

```text
model_id=e4_frozen_qlib_2023_2025_ltr
model_family=ltr
strategy_rule=top50_exit_one_worst_sell
display_role=primary_readonly_candidate / readonly_candidate
is_production_trading_default=false
not_order=true
not_target_position=true
not_investment_advice=true
```

并列出当前 source artifacts：

```text
data_tw/artifacts/signals/e4_frozen_qlib_2023_2025_ltr/r1_legacy_signal_adapter_20260616/manifest.json
data_tw/artifacts/full_rank/frozen_qlib_2018_2022_raw_oos/r9_full_rank_adapter_20260616/manifest.json
configs/strategy_dependencies/top50_exit_one_worst_sell.yaml
data_tw/artifacts/shadow_modular_daily/2026-06-16/manifest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-06-16/manifest.json
```

审查认可该冻结范围。U 主线默认只接入已冻结、已审计 readonly candidate，不新增真实模型/策略，不切默认策略。

### 3.6 Frontend readonly gate 仍通过

复跑 M4 frontend readonly validator：

```text
ok=true
schema_version=m4.0.1
readonly_workflow_only_get=true
forbidden_request_count=0
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
ops_provider_publish_refresh_accepted_latest_request_count=0
replay_strategy_write_count=0
broker_quick_trade_orders_request_count=0
legacy_provider_gate_not_exposed=true
agent_implementation_untouched=true
agent_contract_placeholder_only=true
```

前端 API 文件中仍存在 monitor config、scan、alerts、sim order 等历史产品函数；它们不是 U 主线 readonly path。U1-U3 不得调用或暴露这些入口。

## 4. 台股只读安全边界审查

### Findings

Critical：未发现 U0 触发 provider refresh / publish、accepted latest switch、broker / quick-trade / orders、target position 或真实交易路径。

High：未发现 U0 写 monitor config / scan / alerts。历史 monitor 写入口存在于前端 API，但不属于 U 主线默认链路。

Medium：`scripts/run_daily_tw_stock_auto_update.py` 保留 legacy provider publish / accepted latest 代码路径。当前有显式非默认 gate，M3 audit 证明默认不可达；U1-U3 必须继续把它视为 legacy，不能为了“真实日更”绕过用户确认。

Low：U0 对训练窗口 `2023-2025` 的说明部分来自文件名和主线命名推断。U1 若生成真实 daily ModelSignalArtifact，应把 source model artifact、feature availability 和 PIT 策略写入 manifest，而不是沿用推断文字。

### Verdict

U0 通过。当前证据支持进入 U1，但 U1 只能做 daily data / feature / model signal artifact 的 dry-run 或 staging 接入，不能触发 provider publish / accepted latest，也不能更新 readonly latest pointer。

## 5. 残余风险

1. Legacy Option C accepted latest 当前 asof 为 `2026-06-17`，readonly snapshot latest 当前 asof 为 `2026-06-16`。U1 必须明确二者不是同一语义，不能用 legacy latest 新鲜度直接证明 U 主线 readonly latest 可发布。
2. 既有脚本具备真实 FinMind raw archive 写入能力，U1 如需要读取新数据，必须优先落到 staging `DataIngestionArtifact`，并说明是否触发外部请求或本地写入。
3. 前端/API 历史 monitor、sim order、ops 入口仍存在；U3 做前端/API 验收时必须用 network audit 证明 readonly workflow 未调用它们。
4. 当前 U0 未创建 U1 validator/golden sample，这符合 U0 范围，但 U1 必须补齐正例和负例，不得只输出 artifact。

## 6. Phase U1 工作范围

U1 目标：把每日数据状态安全转换成标准上游 artifact，并生成冻结模型可消费的每日 `ModelSignalArtifact`。

U1 可以新增或扩展：

```text
scripts/build_tw_daily_data_ingestion_artifact.py
scripts/validate_tw_daily_data_ingestion_artifact.py
scripts/build_tw_daily_feature_artifact.py
scripts/validate_tw_daily_feature_artifact.py
scripts/build_tw_daily_model_signal_artifact.py
scripts/validate_tw_daily_model_signal_artifact.py
```

建议输出目录：

```text
data_tw/artifacts/daily_data_ingestion/<run_id>/
data_tw/artifacts/daily_features/<run_id>/
data_tw/artifacts/daily_model_signals/e4_frozen_qlib_2023_2025_ltr/<run_id>/
```

U1 必须至少覆盖两类状态：

```text
fresh_data_detected
no_new_data
```

其中 `no_new_data` 只能生成可审计 noop artifact，不能更新 readonly latest pointer，不能伪造成新模型信号。

## 7. U1 必须实现的 artifact 字段

### 7.1 DataIngestionArtifact

至少包含：

```text
manifest.json
schema.json
coverage_audit.csv
symbol_mapping_audit.csv
forbidden_action_audit.json
freshness_audit.json
```

manifest 至少声明：

```text
run_id
asof_date
created_at
source_name
source_mode
raw_input_path
normalized_output_path, if produced
freshness_status
coverage_status
symbol_mapping_version
readonly_only=true
no_provider_publish=true
no_accepted_latest_switch=true
no_monitor_write=true
no_broker_order=true
```

### 7.2 FeatureArtifact

至少包含：

```text
manifest.json
features.csv or features.parquet
schema.json
coverage_audit.csv
pit_availability_audit.csv
forbidden_future_field_audit.json
```

必须证明：

```text
feature_asof
signal_asof
available_at
source_data_artifact
lookback_window
available_at <= signal_asof
无 future_return / forward_return / label / realized_pnl / execution / position / order 字段
```

### 7.3 ModelSignalArtifact

必须输出标准字段：

```text
date
instrument
model_name
model_family
candidate_rank
buy_score
raw_score
score_rank
full_qlib_rank
signal_asof
available_at
source_artifact
source_model_artifact
source_feature_artifact
```

必须声明：

```text
model_id=e4_frozen_qlib_2023_2025_ltr
strategy_compatibility=top50_exit_one_worst_sell
score_source
rank_source
candidate_k
no_training=true
no_tuning=true
no_score_recompute_outside_frozen_model=true
no_default_strategy_switch=true
no_provider_publish=true
no_accepted_latest_switch=true
```

## 8. U1 Validator / Golden Sample 要求

U1 必须提供 pass/fail golden samples。最低要求：

```text
pass_fresh_data_minimal
pass_no_new_data_noop
fail_missing_available_at
fail_future_field_present
fail_forbidden_action_marker_missing
fail_no_new_data_updates_latest
```

Validator 必须能阻断：

```text
available_at > signal_asof
缺 coverage audit
缺 symbol mapping audit
出现 future_return / forward_return / label / realized_pnl / execution / position / order 字段
缺 no_provider_publish / no_accepted_latest_switch / no_monitor_write / no_broker_order
no_new_data artifact 声称更新 readonly latest
model signal 缺 core fields
模型 signal 未声明 source_feature_artifact / source_model_artifact
```

建议统一输出：

```text
data_tw/golden_samples/modular_daily_update/u1/
data_tw/experiments/modular_daily_update/u1_validation_summary.json
```

## 9. U1 禁止事项

U1 不得做以下事项：

```text
不得训练新模型
不得调参或搜索模型
不得重算或替换冻结模型权重
不得新增正式策略收益结论
不得生成 OrderIntentArtifact
不得生成 ReadonlyStrategySnapshot
不得更新 readonly latest pointer
不得触发 provider refresh / publish
不得切 provider accepted latest 或 qlib accepted latest
不得写 monitor config / scan / alerts
不得连接 broker / quick-trade / orders
不得修改 Agent prompt / tool / action
不得让前端本地计算策略或 replay
```

如果执行者认为 U1 必须访问外部数据源或写入 raw archive，必须在执行前停下来说明：

```text
为什么不能从现有本地 artifact 构造 staging DataIngestionArtifact
会访问哪个 provider
会写入哪些路径
是否影响 accepted latest
失败如何回滚
是否可改为 dry-run/staging 输出
```

未经用户确认，不得把真实 provider refresh / accepted latest 纳入 U1。

## 10. U1 审查建议

U1 执行报告提交后，审查者应重点检查：

1. 是否只生成 daily data / feature / model signal artifact，没有进入 U2 的 order intent / snapshot / latest pointer。
2. `fresh_data_detected` 与 `no_new_data` 是否都有样例，且 noop 不更新 latest。
3. PIT 与 future field audit 是否可机读验证。
4. Validator 是否有正负例，并且负例确实失败。
5. 冻结模型/策略字段是否仍为 U0 冻结范围。
6. 是否没有 provider publish / accepted latest、monitor/broker/order、Agent 扩权。

U1 通过后，才允许进入 U2 的 OrderIntent / ReadonlySnapshot / RunRegistry / readonly latest pointer 行为验证。
