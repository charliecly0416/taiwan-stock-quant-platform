# Phase V0 审查与 Phase V1 工作文档

生成日期：2026-06-17

## 1. 审查结论

Phase V0 通过，允许进入 Phase V1。

V0 已完成真实 provider 数据就绪主线的第一轮合同冻结与现状审计：识别了历史两小时自动脚本的 provider publish / accepted latest 风险，明确 Phase V 不能复用旧发布入口作为默认 staging 链路；列出 Yahoo、FinMind、orthogonal、existing signal manifest 等数据源合同；冻结 staging-only 输出路径；列出 selectable model 与 strategy 矩阵；定义 DataReadinessGate 状态和 forbidden action audit 字段。

本轮未修改生产链路，未触发真实 provider 抓取，未 provider publish，未切 provider accepted latest 或 qlib accepted latest，未写 monitor，未触发 broker / quick-trade / orders，未修改 Agent prompt / tool / action。

## 2. 复核范围

审查输入：

```text
docs/tw_modular_daily_update_productization/PHASEV_REAL_PROVIDER_DATA_READINESS_AND_AUTO_CHAIN_WORK_CN.md
docs/tw_modular_daily_update_productization/PHASEV0_PROVIDER_DATA_CONTRACT_AUDIT_EXECUTION_REPORT_CN.md
scripts/run_daily_tw_stock_auto_update.py
scripts/run_tw_modular_daily_readonly_update.py
backend/scripts/update_tw_stock_daily.py
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260617_20260617T103001Z/job.json
```

辅助复跑：

```text
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
python scripts/validate_tw_modular_daily_readonly_update.py --json
python scripts/validate_tw_frontend_readonly_m4.py --json
```

审查重点：

```text
V0 是否只做审计与合同冻结
是否列全 Yahoo / FinMind / orthogonal / local signal 的 required data
是否覆盖所有前端可选模型，而不是只服务默认模型
是否冻结 model_strategy_availability_matrix 口径
是否明确 partial data 不能进入模型/策略链路
是否定义 target_asof / decision_for / decision_cutoff / available_at
是否明确 staging path 与 provider/qlib accepted latest 解耦
是否没有 provider publish / accepted latest / monitor / broker/order / Agent 越界
```

## 3. 通过项

### 3.1 历史入口风险识别正确

V0 报告指出 `scripts/run_daily_tw_stock_auto_update.py` 不能直接作为 Phase V 默认 staging 链路。该判断成立。

审查抽查历史 job：

```text
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260617_20260617T103001Z/job.json
```

可见：

```text
finmind_update_triggered=true
yahoo_refresh_triggered=true
provider_publish_triggered=true
latest_signal_updated=true
```

这证明旧入口曾承担真实更新、provider publish 和 latest_signal 更新职责。Phase V 必须新建 staging-only 链路或显式隔离旧入口，不能把旧入口默认接入 V1。

### 3.2 当前默认 gate 仍安全

复跑 M3 daily audit：

```text
ok=true
legacy_provider_gate_default_disabled=true
provider_refresh_guarded=true
provider_publish_guarded=true
accepted_latest_call_guarded=true
default_provider_refresh_reachable=false
default_provider_publish_reachable=false
default_accepted_latest_reachable=false
readonly_latest_pointer_distinct=true
```

保留 warning：

```text
legacy_provider_publish_path_present
legacy_accepted_latest_path_present
```

该 warning 不阻塞 V0，但要求 V1/V2 继续把 legacy provider path 视为非默认路径。

### 3.3 数据合同覆盖了核心 provider 与正交依赖

V0 报告列出最小数据源矩阵：

```text
yahoo_daily_price
finmind_daily_price
finmind_institutional_flow
finmind_margin_short
orthogonal_o2_features
existing_signal_manifest
```

对每个 source 定义了：

```text
source_id
provider
required
required_fields
expected_asof
actual_latest_asof
available_at
coverage_count / coverage_ratio
write_path
failure_reason
retryable
```

其中 FinMind institutional flow、margin/short 和 orthogonal O2 features 被列为 LTR orthogonal 必需项，这符合主线“不能只服务默认模型”和“正交数据默认强制”的要求。

### 3.4 日期与 PIT 合同明确

V0 定义：

```text
target_asof
decision_for
decision_cutoff
available_at
source_trade_date
accepted_latest_before
accepted_latest_after
```

并写明：

```text
required input is usable only if available_at <= decision_cutoff
partial provider data must stay in provider_staging and must not enter U-chain accepted artifacts
```

该口径满足 Phase V 对真实数据可得性和 PIT 安全的最低要求。

### 3.5 Staging-only 输出路径明确

V0 冻结 staging-only 路径：

```text
data_tw/artifacts/provider_staging/<run_id>/yahoo/
data_tw/artifacts/provider_staging/<run_id>/finmind/
data_tw/artifacts/provider_staging/<run_id>/orthogonal/
data_tw/artifacts/provider_staging/<run_id>/model_signals/
data_tw/artifacts/provider_staging/<run_id>/data_readiness_manifest.json
data_tw/artifacts/provider_staging/<run_id>/model_strategy_availability_matrix.json
data_tw/artifacts/provider_staging/<run_id>/forbidden_action_audit.json
```

并禁止在未通过 readiness gate 前写入：

```text
data_tw/ops/daily_auto_update/<accepted-or-production-run>/
data_tw/artifacts/signals/<model_id>/<production-adapter-or-latest>/
data_tw/accepted_latest*
monitor write paths
broker / quick-trade / orders paths
```

### 3.6 Model / Strategy 矩阵覆盖面可接受

V0 model matrix 覆盖：

```text
e4_frozen_qlib_2023_2025_ltr
fresh_qlib_2025_ltr
fresh_qlib_adaptive
frozen_qlib_2018_2022
frozen_qlib_2025_ltr
```

strategy matrix 覆盖：

```text
original
top50_exit_all
top50_exit_one_worst_sell
one_sell_one_buy_correct
one_sell_one_buy_buggy_e8r
sector_extension_analysis_smoke
dummy_new_strategy_dependency_smoke
```

报告也区分了诊断/smoke 策略不得作为 V2 默认或生产展示默认。这为 V1 的机器可读 availability matrix 提供了足够起点。

## 4. 台股只读安全边界审查

### Findings

Critical：未发现 V0 触发 provider publish / refresh、accepted latest switch、broker / quick-trade / orders、target position 或真实交易路径。

High：未发现 V0 写 monitor config / scan / alerts；未发现 Agent prompt / tool / action 修改。

Medium：V0 报告第 0 节写到“V1/V2/V3”，但主线实际只有 V0/V1/V2。该编号不影响 V0 审查结论，但 V1/V2 文档必须统一为三阶段口径，避免执行者误开不存在的 V3。

Medium：策略矩阵列出诊断/smoke 策略，但尚未形成机器可读 `model_strategy_availability_matrix.json`。V1 必须把生产可选、诊断-only、smoke-only、不可选原因写成机器可读字段，不能只靠文档表格。

Low：FinMind 月营收、估值被列为后续扩展特征而非 V1 最小必需。当前可接受；若前端后续允许选择依赖这些字段的模型，V1 readiness gate 必须自动变为 required 或给出 unavailable reason。

### Verdict

V0 通过。允许进入 V1，但 V1 必须把 V0 的文档合同落成可机读 staging artifact、readiness manifest、availability matrix 和 forbidden action audit。

## 5. 残余风险

1. 历史自动脚本仍包含 provider publish / accepted latest 能力，虽然默认 gate 关闭。V1 不得复用它作为默认 provider staging runner。
2. 旧 job 证明 provider publish / latest_signal update 曾真实发生；V1 必须通过 `forbidden_action_audit.json` 证明 staging runner 未触发这些动作。
3. V0 对 O2 orthogonal lineage 使用现有观测值作为审计依据；V1 必须按本次 run 重新计算 `actual_latest_asof`、`available_at`、coverage 和 failure reason。
4. V0 是文档冻结，不含 validator/golden sample。V1 必须补齐 validator 和正负例，否则不能放行到 V2。

## 6. Phase V1 工作范围

V1 目标：实现真实数据源 staging 拉取和统一 DataReadinessGate。系统可以记录“能拉到什么”，但在 `all_required_ready` 之前不得进入模型/策略链路。

V1 可以新增或改造：

```text
scripts/pull_tw_provider_staging_data.py
scripts/validate_tw_provider_staging_data.py
scripts/build_tw_data_readiness_gate.py
scripts/validate_tw_data_readiness_gate.py
```

V1 输出目录：

```text
data_tw/artifacts/provider_staging/<run_id>/yahoo/
data_tw/artifacts/provider_staging/<run_id>/finmind/
data_tw/artifacts/provider_staging/<run_id>/orthogonal/
data_tw/artifacts/provider_staging/<run_id>/model_signals/
data_tw/artifacts/provider_staging/<run_id>/data_readiness_manifest.json
data_tw/artifacts/provider_staging/<run_id>/model_strategy_availability_matrix.json
data_tw/artifacts/provider_staging/<run_id>/forbidden_action_audit.json
```

V1 执行报告：

```text
docs/tw_modular_daily_update_productization/PHASEV1_STAGING_PULL_AND_READINESS_GATE_EXECUTION_REPORT_CN.md
```

## 7. V1 必须实现的 DataReadinessGate

Gate 只能输出以下状态：

```text
all_required_ready
partial_data_pending
no_new_data
provider_failed
validator_failed
deadline_missed_keep_previous_latest
```

只有：

```text
all_required_ready
```

可以进入后续 U1-U3 readonly chain。其他状态必须：

```text
写 provider_staging manifest
写 failure / pending reason
写 run registry 或 V1 gate report
保留 previous readonly latest
不得生成新的策略结果
不得更新 readonly latest pointer
不得调用 provider accepted latest / qlib accepted latest
```

## 8. V1 Validator / Golden Sample 要求

V1 必须提供正负例。最低要求：

```text
pass_all_required_ready
pass_no_new_data_keep_previous_latest
fail_partial_data_pending
fail_provider_failed
fail_validator_failed_future_available_at
fail_deadline_missed_keep_previous_latest
fail_missing_orthogonal_required_source
fail_missing_symbol_mapping
fail_provider_publish_triggered
fail_accepted_latest_switched
fail_monitor_or_broker_action
```

Validator 必须能阻断：

```text
required source 缺失
required_fields 缺失
coverage_ratio 低于合同门槛
actual_latest_asof 未达到 expected_asof 且未给出允许的 no_new_data/pending 状态
available_at > decision_cutoff
orthogonal PIT 审计失败
symbol mapping / universe / trading calendar 缺失
model_strategy_availability_matrix 缺 model 或 strategy
diagnostic/smoke strategy 被标为 default/selectable production
partial_data_pending / provider_failed / validator_failed 更新 readonly latest
provider_publish_triggered=true
accepted_latest_switched=true
monitor/broker/order/Agent action 任一 true
```

## 9. V1 机器可读 Manifest 要求

`data_readiness_manifest.json` 至少包含：

```text
run_id
target_asof
decision_for
decision_cutoff
gate_status
previous_readonly_latest
committed_readonly_latest
sources[]
forbidden_action_audit
failure_reasons[]
retryable_sources[]
created_at
```

每个 `sources[]` 至少包含：

```text
source_id
provider
required
required_fields
expected_asof
actual_latest_asof
available_at
coverage_count
coverage_ratio
write_path
failure_reason
retryable
```

`model_strategy_availability_matrix.json` 至少包含：

```text
models[]
strategies[]
default_model_id
default_strategy_rule_id
target_asof
decision_for
```

每个 model：

```text
model_id
model_type
required_data_sources
required_feature_artifacts
required_signal_artifacts
train_window
allowed_signal_window
can_run_today
unavailable_reason
```

每个 strategy：

```text
strategy_rule_id
strategy_role
required_inputs
compatible_model_types
decision_output_schema
can_run_today
unavailable_reason
production_selectable
diagnostic_only
smoke_only
```

## 10. V1 禁止事项

V1 不得做以下事项：

```text
不得训练、重训或替换模型权重
不得切 default strategy / default candidate
不得 provider publish / refresh 正式发布路径
不得切 provider accepted latest 或 qlib accepted latest
不得写 monitor config / scan / alerts
不得连接 broker / quick-trade / orders
不得修改 Agent prompt / tool / action
不得用 partial data 生成策略
不得只为默认模型拉取窄口径数据
不得在前端模型/策略切换时重新触发外部数据抓取
不得在 gate 未 all_required_ready 时更新 readonly latest
```

说明：V1 可以访问真实外部数据源并写 staging/raw artifact，但必须写入 V0 冻结的 staging-only 路径，并记录 forbidden action audit。若执行者认为必须调用旧 provider publish / accepted latest 路径，必须停止并请求用户确认，不能自行纳入 V1。

## 11. V1 审查建议

V1 执行报告提交后，审查者应重点检查：

1. 是否真的写入 `data_tw/artifacts/provider_staging/<run_id>/`，而不是 accepted/latest/生产路径。
2. `data_readiness_manifest.json` 是否可机读，且 status 不用自然语言散落判断。
3. 是否覆盖所有 selectable model 和 strategy，而不是只覆盖默认组合。
4. orthogonal required source 缺失是否会失败关闭。
5. partial/pending/failed/deadline_missed 是否保留 previous readonly latest。
6. forbidden action audit 是否证明未 publish、未 accepted latest、未 monitor/broker/order、未 Agent 扩权。
7. 若有真实外部请求，是否记录 provider、actual_latest_asof、available_at、coverage、failure reason 和 retryable。

V1 通过后，才允许进入 V2 自动触发、U 链路串接和前端/API 验收。
