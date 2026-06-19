# Phase V1 审查与 Phase V2 工作文档

生成日期：2026-06-17

## 1. 审查结论

Phase V1 条件通过，允许进入 Phase V2。

V1 已落地 provider staging-only runner、provider staging validator、DataReadinessGate builder、DataReadinessGate validator，并生成一次 staging run：

```text
data_tw/artifacts/provider_staging/phasev1_provider_staging_20260610_codex_v1/
```

审查复跑确认：V1 产物只写入 `data_tw/artifacts/provider_staging/<run_id>/`，没有修改 provider accepted latest、qlib accepted latest、readonly daily latest pointer、monitor、broker/order 或 Agent。11 个内置 golden scenarios 覆盖 ready、no_new_data、partial、provider_failed、validator_failed、deadline_missed、缺 orthogonal、缺 symbol mapping、provider publish、accepted latest 和 monitor/broker forbidden action。

条件项：V1 `data_readiness_manifest.json` 在 `all_required_ready` 时写入：

```text
updates_readonly_latest=true
committed_readonly_latest=2026-06-10
```

实际 `data_tw/artifacts/daily_readonly_latest/latest.json` 未被修改，因此这不是实际 latest 越界；但字段语义容易误导 V2。V2 必须把该语义明确修正为“gate allows downstream readonly latest update”，或在 V2 validator 中禁止把 V1 readiness manifest 直接视为已提交 latest。真正更新 readonly latest 只能发生在 V2 串接 U 链、全部 validator 通过之后。

## 2. 复核范围

审查输入：

```text
docs/tw_modular_daily_update_productization/PHASEV1_STAGING_PULL_AND_READINESS_GATE_EXECUTION_REPORT_CN.md
docs/tw_modular_daily_update_productization/PHASEV0_REVIEW_AND_PHASEV1_WORK_CN.md
scripts/pull_tw_provider_staging_data.py
scripts/validate_tw_provider_staging_data.py
scripts/build_tw_data_readiness_gate.py
scripts/validate_tw_data_readiness_gate.py
data_tw/artifacts/provider_staging/phasev1_provider_staging_20260610_codex_v1/
data_tw/artifacts/daily_readonly_latest/latest.json
```

辅助复跑：

```text
python -m py_compile scripts/pull_tw_provider_staging_data.py scripts/validate_tw_provider_staging_data.py scripts/build_tw_data_readiness_gate.py scripts/validate_tw_data_readiness_gate.py
python scripts/validate_tw_provider_staging_data.py --staging-dir data_tw/artifacts/provider_staging/phasev1_provider_staging_20260610_codex_v1 --json
python scripts/validate_tw_data_readiness_gate.py --staging-dir data_tw/artifacts/provider_staging/phasev1_provider_staging_20260610_codex_v1 --json
python scripts/validate_tw_data_readiness_gate.py --run-golden --json
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
python scripts/validate_tw_modular_daily_readonly_update.py --json
```

审查重点：

```text
是否只写 provider_staging
provider staging source contract 是否完整
DataReadinessGate 状态是否机器可读
partial/failed/no_new_data 是否阻断下游
model_strategy_availability_matrix 是否覆盖所有 selectable model/strategy
diagnostic/smoke strategy 是否不可 production selectable
forbidden_action_audit 是否能阻断 provider/latest/monitor/broker/order/Agent
是否实际修改 readonly latest pointer
是否仍保持 U3 GET-only 与 legacy provider gate 默认关闭
```

## 3. 通过项

### 3.1 Staging-only runner 未触发旧发布链路

`scripts/pull_tw_provider_staging_data.py` 的默认输出根目录为：

```text
data_tw/artifacts/provider_staging/
```

脚本只生成：

```text
provider_staging_pull_manifest.json
forbidden_action_audit.json
source_status.json
```

未调用：

```text
scripts/run_daily_tw_stock_auto_update.py
provider publish
accepted latest scheduler
monitor API
broker / quick-trade / orders
Agent prompt/tool/action
```

### 3.2 Provider staging validator 覆盖核心安全字段

`validate_tw_provider_staging_data.py` 校验：

```text
staging_only=true
required source 存在
source 必需字段完整
coverage_ratio >= 0.8
available_at <= decision_cutoff
pit_audit_passed
symbol_mapping_ready
forbidden_action_audit 中所有 action 必须 false
```

复跑结果：

```text
ok=true
status=passed
schema_version=v1.provider_staging_validator.v1
```

### 3.3 DataReadinessGate 状态与 golden 覆盖完整

Gate 只允许：

```text
all_required_ready
partial_data_pending
no_new_data
provider_failed
validator_failed
deadline_missed_keep_previous_latest
```

复跑 `--run-golden`：

```text
ok=true
status=passed
sample_count=11
```

覆盖：

```text
all_required_ready
no_new_data
partial_data_pending
provider_failed
validator_failed_future_available_at
deadline_missed_keep_previous_latest
missing_orthogonal_required_source
missing_symbol_mapping
provider_publish_triggered
accepted_latest_switched
monitor_or_broker_action
```

其中 forbidden action 三个负例均以：

```text
forbidden_action_triggered
```

被阻断。

### 3.4 Readiness manifest 覆盖核心 source

本次 run 覆盖：

```text
yahoo_daily_price
finmind_daily_price
finmind_institutional_flow
finmind_margin_short
orthogonal_o2_features
existing_signal_manifest
```

每个 source 均包含：

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
symbol_mapping_ready
pit_audit_passed
```

本次 run 的 `available_at` 均不晚于 `decision_cutoff`，coverage_ratio 为 1.0。

### 3.5 Availability matrix 已机器可读

`model_strategy_availability_matrix.json` 覆盖模型：

```text
e4_frozen_qlib_2023_2025_ltr
fresh_qlib_2025_ltr
fresh_qlib_adaptive
frozen_qlib_2018_2022
frozen_qlib_2025_ltr
```

覆盖策略：

```text
original
top50_exit_all
top50_exit_one_worst_sell
one_sell_one_buy_correct
one_sell_one_buy_buggy_e8r
sector_extension_analysis_smoke
dummy_new_strategy_dependency_smoke
```

诊断/smoke 策略均不是 production selectable：

```text
one_sell_one_buy_buggy_e8r.production_selectable=false
sector_extension_analysis_smoke.production_selectable=false
dummy_new_strategy_dependency_smoke.production_selectable=false
```

### 3.6 现有只读 gate 仍通过

复跑 M3：

```text
ok=true
default_provider_refresh_reachable=false
default_provider_publish_reachable=false
default_accepted_latest_reachable=false
readonly_latest_pointer_distinct=true
```

复跑 U3：

```text
ok=true
status=passed
readonly_workflow_only_get=true
forbidden_request_count=0
ops_provider_publish_refresh_accepted_latest_request_count=0
broker_quick_trade_orders_request_count=0
ops_dry_run_post_count=0
agent_implementation_untouched=true
```

## 4. 台股只读安全边界审查

### Findings

Critical：未发现 V1 实际触发 provider publish / refresh、provider accepted latest 或 qlib accepted latest switch、broker / quick-trade / orders、target position 或真实交易路径。

High：未发现 V1 写 monitor config / scan / alerts；未发现 Agent prompt / tool / action 修改；未发现真实 readonly latest pointer 文件被改写。

High：`all_required_ready` manifest 中 `updates_readonly_latest=true` 与 `committed_readonly_latest=target_asof` 存在语义风险。实际 pointer 未更新，所以不作为 V1 阻塞；但 V2 必须修正或重定义字段，避免 DataReadinessGate 被误当成发布动作。

Medium：V1 当前是合同化 staging 示例，报告也写明“可接入真实 provider 拉取实现”。这满足 V1 骨架要求；V2 若宣称真实自动链路，则必须说明真实外部请求、失败重试、幂等、日志和 provider 限流。

Low：`finmind_daily_price` 当前为 optional，而 Yahoo daily price required。若 V2 的前端可选模型或策略要求 FinMind price 作为强制交叉验证，V2 必须把它提升为 required 或给出 unavailable reason。

### Verdict

V1 条件通过。允许进入 V2，但 V2 必须关闭 readiness manifest 的 latest 语义歧义，并证明只有 U 链全部 validator 通过后才更新 readonly daily latest pointer。

## 5. 残余风险

1. `updates_readonly_latest=true` 是本轮最大语义风险。V2 不得直接消费该字段作为“已经更新”或“可无条件更新”的依据。
2. V1 没有真实调用 Yahoo / FinMind 网络 provider，只生成本地合同化 staging 示例。V2 如要真实自动触发，需要单独验证外部请求与 staging 写入。
3. Availability matrix 中 diagnostic/smoke strategy 的 `can_run_today=true` 但 `production_selectable=false`。V2 前端必须以 `production_selectable=false` 为准，不得把这些策略放入普通用户生产候选选择。
4. V1 不生成 RunRegistry；V2 非 ready 状态必须补齐 run registry / frontend reason / keep previous latest 证据。

## 6. Phase V2 工作范围

V2 目标：把 V1 DataReadinessGate 串到 U 链路前面，形成自动触发和前端/API 验收闭环。

V2 建议新增：

```text
scripts/run_tw_real_provider_daily_readonly_update.py
scripts/validate_tw_real_provider_daily_readonly_update.py
backend/app/routes/readonly_provider_readiness.py
backend/app/services/readonly_provider_readiness.py
backend/app/routes/readonly_daily_update_runs.py
backend/app/services/readonly_daily_update_runs.py
```

V2 可以纳入一个前端“只读策略结果更新”按钮，但它必须是受控手动作业触发入口，而不是 provider publish、accepted latest switch、交易、monitor scan 或 Agent action 入口。该按钮的产品语义应为“尝试拉取最新 provider staging 并运行只读日更链路”，不能写成“买入/卖出/调仓/下单/刷新实盘策略”。

V2 执行报告：

```text
docs/tw_modular_daily_update_productization/PHASEV2_AUTO_CHAIN_FRONTEND_ACCEPTANCE_EXECUTION_REPORT_CN.md
```

最终运维与审查文档：

```text
docs/tw_modular_daily_update_productization/REAL_PROVIDER_DAILY_UPDATE_RUNBOOK_CN.md
docs/tw_modular_daily_update_productization/REAL_PROVIDER_DAILY_UPDATE_REVIEWER_CHECKLIST_CN.md
```

## 7. V2 必须实现的链路规则

自动链路：

```text
create run_id
pull provider staging data
validate provider staging
build DataReadinessGate
if gate_status == all_required_ready:
    run U1-U3 readonly chain for default_model_id + default_strategy_rule_id
    validate all artifacts
    update readonly latest pointer
else:
    write RunRegistry / readiness status
    keep previous readonly latest
```

前端手动触发链路必须复用同一条 orchestrator，不得实现第二条捷径：

```text
GET readiness/latest -> 判断当前是否 already_latest / running / triggerable
POST readonly_daily_update_runs -> 创建一次受控 run_id，幂等触发同一条 V2 orchestrator
GET readonly_daily_update_runs/<run_id> -> 轮询状态、reason、latest_asof、previous_latest_asof
GET latest readonly result -> 成功后展示最新只读策略结果
```

手动触发入口必须具备：

```text
idempotency_key
rate_limit / cooldown
single_flight_lock，已有 run 运行中时返回 running
明确 actor=frontend_manual_trigger
完整 RunRegistry 记录
失败保留 previous latest
非 all_required_ready 不进入 U 链
U-chain validator 失败不更新 readonly latest
```

按需模型/策略切换：

```text
given target_asof + model_id + strategy_rule_id
load existing ready provider staging / feature artifacts
build or load selected ModelSignalArtifact
build selected OrderIntentArtifact
return readonly decision response
```

按需入口不得重新抓 Yahoo / FinMind / orthogonal 外部数据。如果所选模型/策略不可运行，只能返回 unavailable reason。

## 8. V2 必须修正或澄清的 V1 字段语义

V2 必须满足以下任一方式：

1. 将 V1 readiness manifest 中的：

```text
updates_readonly_latest=true
committed_readonly_latest=target_asof
```

改为更明确的非发布语义，例如：

```text
gate_allows_downstream_readonly_latest_update=true
proposed_readiness_asof=target_asof
actual_readonly_latest_updated=false
```

2. 或在 V2 validator 中明确规定：

```text
V1 readiness manifest 的 updates_readonly_latest 不是实际 pointer update
实际 readonly latest 只能以 data_tw/artifacts/daily_readonly_latest/latest.json 的变更和 U/V2 RunRegistry 为准
```

无论采用哪种方式，V2 必须证明：

```text
gate_status != all_required_ready 时 latest 不变
all_required_ready 但 U-chain validator 失败时 latest 不变
all_required_ready 且 U-chain 全部通过后才更新 readonly latest pointer
provider accepted latest / qlib accepted latest 永远不变
```

## 9. V2 Validator / Acceptance 要求

V2 至少覆盖：

```text
all_required_ready -> 生成新 readonly latest
already_latest -> 不创建重复更新或返回 noop，前端按钮置灰并提示已是最新
manual_trigger_success -> 拉到新数据且 U-chain 全部通过，更新 readonly latest 并展示最新只读策略结果
manual_trigger_no_data -> 未拉到可用新数据，保留 previous latest，提示数据暂不可用/等待下一轮
manual_trigger_running -> 已有更新 run 运行中，按钮置灰并展示运行中状态
manual_trigger_validator_failed -> 保留 previous latest，展示 validator failure reason
selected_model_strategy_ready -> 按需只读决策可返回
selected_model_strategy_unavailable -> 返回 unavailable reason，不重抓数据
partial_data_pending -> 不生成策略，保留 previous latest
provider_failed -> 不生成策略，保留 previous latest
no_new_data -> 不生成策略或 noop，保留 previous latest
validator_failed -> 不生成策略，保留 previous latest
deadline_missed_keep_previous_latest -> 不生成策略，保留 previous latest
```

V2 validator 必须阻断：

```text
非 all_required_ready 进入 U 链路
partial data 生成策略结果
前端切换模型/策略触发 provider refetch
前端按钮绕过 V2 orchestrator 直接调用 provider pull / publish / latest switch
重复点击创建并发更新 run
diagnostic/smoke strategy 被 production selectable
U-chain validator failed 仍更新 readonly latest
provider accepted latest / qlib accepted latest switch
monitor config / scan / alerts write
broker / quick-trade / orders
Agent prompt/tool/action expansion
```

## 10. V2 Frontend / API 硬门

展示类 API 仍必须保持 GET-only：

```text
provider readiness
latest readonly result
model_strategy_availability_matrix
selected model/strategy readonly decision response
readonly daily update run status
```

若 V2 接纳前端“只读策略结果更新”按钮，只允许新增一个受控触发 endpoint：

```text
POST /api/tw-stock/readonly-daily-update-runs
```

该 POST 只能创建/复用 V2 orchestrator run，不能直接调用 provider publish / refresh、accepted latest switch、monitor scan、broker、orders 或 Agent action。网络审计必须把它作为唯一允许的 manual trigger POST 单独计数，其余展示流程仍按 GET-only 验收。

前端按钮状态必须覆盖：

```text
already_latest -> 按钮置灰，提示已是最新
running -> 按钮置灰，展示正在更新 / run_id
triggerable -> 按钮可点，文案为更新只读策略结果
no_data_after_trigger -> 保留旧结果，提示最新数据暂不可用，等待自动重试
success_after_trigger -> 展示更新成功、latest_asof 和最新只读策略结果
failed_after_trigger -> 保留旧结果，展示可读 failure reason / retryable
```

前端必须证明：

```text
forbidden_request_count=0
provider publish / refresh / accepted latest request count=0
manual_trigger_post_count <= 1 per user action
manual_trigger_post_path_allowlist only /api/tw-stock/readonly-daily-update-runs
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
broker_quick_trade_orders_request_count=0
ops_dry_run_post_count=0 for full readonly display E2E
```

前端文案必须保持：

```text
readonly
只读策略结果更新
candidate / observation
not order
not target position
not investment advice
```

不得把 `intent_action=buy` 或模型/策略选择展示成买入指令、下单、目标仓位或收益承诺。

## 11. V2 禁止事项

V2 不得做：

```text
训练、重训或替换模型权重
切 default strategy / default candidate
provider publish / refresh 正式发布路径
切 provider accepted latest 或 qlib accepted latest
写 monitor config / scan / alerts
连接 broker / quick-trade / orders
修改 Agent prompt / tool / action
用 partial data 生成策略
只为默认模型拉取窄口径数据
前端切换模型/策略时重新触发外部数据抓取
手动按钮绕过 DataReadinessGate 或 U-chain validator
手动按钮在 already_latest / running 时重复创建 run
gate 未 all_required_ready 时更新 readonly latest
```

V2 通过后，Phase V 才能判定为真实 provider 数据就绪与全自动只读日更接入主线收口。
