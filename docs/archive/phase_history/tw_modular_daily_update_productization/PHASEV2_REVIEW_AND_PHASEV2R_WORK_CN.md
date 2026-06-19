# Phase V2 审查与 Phase V2R 修复工作文档

生成日期：2026-06-17

## 1. 审查结论

Phase V2 暂不收尾，需要进入 Phase V2R 修复。

V2 后端 orchestrator、run registry、validator、受控 POST 路由和 API 静态安全检查已经成型，14 个 golden scenarios 复跑通过；但“真实 provider 数据就绪与全自动只读日更接入主线”还不能最终收口，原因是仍存在两个产品化阻断项：

1. 前端页面没有实际接入“只读策略结果更新”按钮和状态闭环。
2. 当前 provider staging 仍由 scenario 合同化生成器产出，不是真实 Yahoo / FinMind / orthogonal provider 拉取链路。

因此 V2 只能判定为后端骨架与 validator 条件通过，不能判定为 Phase V 最终收尾。

## 2. 复核范围

审查输入：

```text
docs/tw_modular_daily_update_productization/PHASEV2_AUTO_CHAIN_FRONTEND_ACCEPTANCE_EXECUTION_REPORT_CN.md
docs/tw_modular_daily_update_productization/PHASEV1_REVIEW_AND_PHASEV2_WORK_CN.md
scripts/run_tw_real_provider_daily_readonly_update.py
scripts/validate_tw_real_provider_daily_readonly_update.py
scripts/pull_tw_provider_staging_data.py
backend/app/services/readonly_daily_update_runs.py
backend/app/routes/readonly_daily_update_runs.py
frontend/src/api/tw-stock.js
frontend/src/views/tw-stock-monitor/index.vue
data_tw/artifacts/real_provider_daily_update_runs/phasev2_manual_trigger_success_codex_v1/run_registry.json
data_tw/artifacts/daily_readonly_latest/latest.json
```

复跑命令：

```text
python -m py_compile scripts/run_tw_real_provider_daily_readonly_update.py scripts/validate_tw_real_provider_daily_readonly_update.py scripts/build_tw_data_readiness_gate.py backend/app/services/readonly_daily_update_runs.py backend/app/routes/readonly_daily_update_runs.py
python scripts/validate_tw_real_provider_daily_readonly_update.py --run-golden --json
python scripts/validate_tw_real_provider_daily_readonly_update.py --static-api --json
python scripts/validate_tw_real_provider_daily_readonly_update.py --artifact-path data_tw/artifacts/real_provider_daily_update_runs/phasev2_manual_trigger_success_codex_v1/run_registry.json --json
```

复跑结果：

```text
py_compile: passed
run_golden: ok=true, status=passed, sample_count=14
static_api: ok=true, status=passed
single_run_registry: ok=true, status=passed
```

## 3. 已通过项

### 3.1 V1 latest 字段语义已修正

V2 报告说明 readiness manifest 已从 V1 的模糊字段：

```text
updates_readonly_latest=true
committed_readonly_latest=target_asof
```

修正为：

```text
gate_allows_downstream_readonly_latest_update=true/false
proposed_readiness_asof=target_asof when ready
actual_readonly_latest_updated=false
updates_readonly_latest=false
committed_readonly_latest=previous_readonly_latest
readonly_latest_preserved=true
```

该方向满足 V1 审查要求：DataReadinessGate 只表达放行资格，不表达实际 latest pointer 已提交。

### 3.2 V2 orchestrator 骨架满足 gate-first 规则

`scripts/run_tw_real_provider_daily_readonly_update.py` 的核心行为符合 V2 合同：

```text
pull provider staging
validate provider staging
build DataReadinessGate
validate DataReadinessGate
gate_status == all_required_ready 时才进入 U 链
U 链成功后才更新 readonly latest
非 ready / failed / no_new_data 保留 previous latest
```

示例 run registry 证明：

```text
status=success
gate_status=all_required_ready
u_chain_started=true
readonly_latest_updated=true
provider_accepted_latest_changed=false
qlib_accepted_latest_changed=false
monitor_broker_order_changed=false
agent_changed=false
production_trade_enabled=false
provider_refetch_on_model_strategy_switch=false
```

### 3.3 Golden scenarios 覆盖 V2 主要状态

复跑 `--run-golden` 通过 14 个场景：

```text
all_required_ready
already_latest
manual_trigger_success
manual_trigger_no_data
manual_trigger_running
manual_trigger_validator_failed
selected_model_strategy_ready
selected_model_strategy_unavailable
partial_data_pending
provider_failed
no_new_data
validator_failed
deadline_missed_keep_previous_latest
u_chain_validator_failed
```

其中 `manual_trigger_no_data`、`manual_trigger_running`、`manual_trigger_validator_failed` 和 `u_chain_validator_failed` 均保持只读 latest 不被错误更新。

### 3.4 API 静态安全检查通过

后端新增：

```text
GET /api/tw-stock/provider-readiness/latest
GET /api/tw-stock/readonly-daily-update-runs
GET /api/tw-stock/readonly-daily-update-runs/<run_id>
POST /api/tw-stock/readonly-daily-update-runs
```

`POST /api/tw-stock/readonly-daily-update-runs` 当前是唯一允许的手动触发 POST，服务层返回：

```text
manual_trigger_post_allowlist=["/api/tw-stock/readonly-daily-update-runs"]
readonly_only=true
```

静态 validator 未发现 provider publish、accepted latest switch、monitor scan、broker/order 或 Agent action token。

## 4. 阻断项

### 4.1 Critical：前端页面未实际接入手动更新按钮

V2 工作文档要求前端必须提供“只读策略结果更新”按钮，并覆盖：

```text
already_latest -> 按钮置灰，提示已是最新
running -> 按钮置灰，展示正在更新 / run_id
triggerable -> 按钮可点，文案为更新只读策略结果
no_data_after_trigger -> 保留旧结果，提示最新数据暂不可用，等待自动重试
success_after_trigger -> 展示更新成功、latest_asof 和最新只读策略结果
failed_after_trigger -> 保留旧结果，展示可读 failure reason / retryable
```

实际抽查 `frontend/src/views/tw-stock-monitor/index.vue` 的只读日更卡片只包含：

```text
更新 latest
更新 registry
```

并且页面内未检索到：

```text
getTwStockProviderReadinessLatest
getTwStockReadonlyDailyUpdateRuns
getTwStockReadonlyDailyUpdateRun
triggerTwStockReadonlyDailyUpdateRun
只读策略结果更新
已是最新
正在更新
```

`frontend/src/api/tw-stock.js` 仅新增了 API wrapper，尚未被页面消费。因此 V2 报告中“前端/API 验收闭环”不成立；当前只能称为 API wrapper 已新增。

### 4.2 Critical：真实 provider 链路仍是 scenario 生成器

Phase V 主线目标是“真实 Yahoo / FinMind / orthogonal staging、DataReadinessGate、多模型策略矩阵和全自动只读日更接入”。但当前 `scripts/pull_tw_provider_staging_data.py` 仍是合同化 scenario 生成器：

```text
--scenario all_required_ready
--scenario no_new_data
--scenario partial_data_pending
--scenario provider_failed
--scenario validator_failed_future_available_at
```

它写入的是模拟 `source_status.json`，没有真实访问 Yahoo / FinMind，也没有读取真实 orthogonal 最新产物并做可得性判定。因此 V2 可以证明 gate/orchestrator 行为正确，但还不能证明“真实 provider 数据就绪与自动链路”已经产品化。

### 4.3 High：生产手动 POST 仍允许前端传入 scenario

`frontend/src/api/tw-stock.js` 的 `triggerTwStockReadonlyDailyUpdateRun(data)` 会把：

```text
scenario: data.scenario
```

传给后端；`backend/app/services/readonly_daily_update_runs.py` 默认也接受 payload 中的 `scenario` 并传给 orchestrator。

这适合测试，但不适合真实用户按钮。生产手动触发必须固定为 real provider mode，不允许用户或前端状态注入 `manual_trigger_success`、`validator_failed` 等测试 scenario。

### 4.4 High：V2 缺少前端运行时 network audit 证据

V2 报告提供了 API 静态安全验证，但没有提供前端运行时 E2E 证据来证明：

```text
manual_trigger_post_count <= 1 per user action
manual_trigger_post_path_allowlist only /api/tw-stock/readonly-daily-update-runs
forbidden_request_count=0
provider publish / refresh / accepted latest request count=0
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
broker_quick_trade_orders_request_count=0
ops_dry_run_post_count=0 for full readonly display E2E
```

在按钮未接入页面的前提下，静态 API 通过不足以支撑“前端验收完成”。

## 5. 台股只读安全边界审查

### Findings

Critical：未发现 V2 当前代码实际触发 broker / quick-trade / orders、target position、provider accepted latest 或 qlib accepted latest switch。

Critical：发现产品化收口阻断。前端按钮未落地，且 provider staging 仍为 scenario 合同化生成器；因此不能把 V2 判定为“真实 provider 自动链路与前端验收闭环已完成”。

High：生产手动 POST 仍接受 `scenario` 参数。V2R 必须把测试 scenario 与真实用户触发入口隔离。

High：缺少前端运行时 network audit 证据；尤其缺少手动按钮点击后的唯一 POST allowlist 和 forbidden request 计数。

Medium：后端 `load_provider_readiness_latest()` 当前用 provider staging manifest 最新 mtime 推导 readiness 状态；V2R 若接入真实 provider，需要确保它与最新 V2 run registry、readonly latest pointer 的状态关系一致，避免页面显示 triggerable/already_latest 与实际 latest 不一致。

### Network Audit

本轮未提供前端 E2E network audit artifact。只能确认静态 API validator 通过，不能确认用户界面点击路径通过。

### Console Audit

本轮未提供前端 console audit artifact。

### Text / Agent Semantics

未发现 V2 新增 Agent prompt / tool / action。前端现有只读日更卡片仍展示 `action {{ intent_action }}`，该字段属于只读候选观察上下文；V2R 若新增按钮，文案必须使用“只读策略结果更新”，不得使用“刷新实盘策略”“买入/卖出”“调仓”“下单”等表达。

### Verdict

V2 安全骨架条件通过，但 Phase V 不可收尾。必须先完成 V2R。

## 6. Phase V2R 必须修复

### 6.1 前端按钮与状态闭环

在 `frontend/src/views/tw-stock-monitor/index.vue` 的只读日更卡片中接入：

```text
getTwStockProviderReadinessLatest
getTwStockReadonlyDailyUpdateRuns
getTwStockReadonlyDailyUpdateRun
triggerTwStockReadonlyDailyUpdateRun
```

按钮状态必须覆盖：

```text
already_latest -> disabled，提示已是最新
running -> disabled，展示 run_id / 正在更新
triggerable -> enabled，文案“更新只读策略结果”
no_data_after_trigger -> 保留旧结果，提示最新数据暂不可用，等待自动重试
success_after_trigger -> 展示更新成功、latest_asof 和最新只读策略结果
failed_after_trigger -> 保留旧结果，展示 failure reason / retryable
```

### 6.2 真实 provider mode 与 test scenario 隔离

生产手动触发 POST 不得接受前端传入的 scenario。建议：

```text
POST /api/tw-stock/readonly-daily-update-runs
```

只接受：

```text
idempotency_key
```

并在服务端固定进入真实 provider mode。

测试 scenario 只能通过 CLI 或测试专用环境变量启用，例如：

```text
python scripts/run_tw_real_provider_daily_readonly_update.py --scenario manual_trigger_success --test-mode
```

### 6.3 接入真实 provider staging

V2R 必须把 `pull_tw_provider_staging_data.py` 或新的 provider staging runner 从 scenario 生成器升级为真实读取：

```text
Yahoo daily price staging
FinMind daily price / institutional / margin short staging
orthogonal_o2_features local latest artifact
existing_signal_manifest local latest artifact
```

真实拉取仍必须写入：

```text
data_tw/artifacts/provider_staging/<run_id>/
```

并保持：

```text
staging_only=true
provider_publish_triggered=false
accepted_latest_switched=false
not_provider_accepted_latest=true
not_qlib_accepted_latest=true
```

如果外部 provider 当前拉不到收盘后数据，应返回 `no_new_data` / `partial_data_pending` / `provider_failed`，不得进入 U 链，不得更新 readonly latest。

### 6.4 前端 E2E / network audit

V2R 必须提供前端运行时证据：

```text
already_latest button disabled
running button disabled
triggerable click creates exactly one allowed POST
no data after trigger shows unavailable reason and preserves previous latest
success after trigger reloads latest readonly result
failed after trigger preserves previous latest and shows retryable/failure reason
```

网络审计必须证明：

```text
manual_trigger_post_count <= 1 per user action
manual_trigger_post_path_allowlist only /api/tw-stock/readonly-daily-update-runs
forbidden_request_count=0
provider publish / refresh / accepted latest request count=0
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
broker_quick_trade_orders_request_count=0
ops_dry_run_post_count=0 for full readonly display E2E
```

## 7. V2R 验收门槛

V2R 通过必须同时满足：

```text
真实 provider staging runner 不再依赖生产 POST 传入 scenario
真实 provider staging 拉不到数据时给出 no_new_data / partial_data_pending / provider_failed
all_required_ready 且 U-chain validators 通过后才更新 readonly latest
already_latest / running / no_data / failed 均保持 previous latest
前端按钮状态和文案完整
前端运行时 network audit 通过
provider accepted latest / qlib accepted latest 永远不变
monitor / broker / orders / Agent 均无写入或扩权
```

V2R 执行报告建议命名：

```text
docs/tw_modular_daily_update_productization/PHASEV2R_REAL_PROVIDER_FRONTEND_TRIGGER_REPAIR_EXECUTION_REPORT_CN.md
```

V2R 通过后，才可以再次判断 Phase V 是否收尾。
