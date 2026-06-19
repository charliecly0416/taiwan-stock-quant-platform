# Phase U3 审查与最终收口文档

生成日期：2026-06-17

## 1. 审查结论

Phase U3 通过。真实模块化日更只读产品化主线可以收口。

U3 已将 U1/U2 的 daily staging 链路串入只读日更 orchestrator，新增 GET-only 后端接口，前端读取 readonly daily latest 与 run registry，并通过 U3 validator 证明运行时只读边界成立。当前链路不训练模型、不调参、不替换冻结模型权重、不触发 provider refresh / publish、不切 provider accepted latest 或 qlib accepted latest、不写 monitor config / scan / alerts、不连接 broker / quick-trade / orders、不修改 Agent prompt / tool / action，也不让前端本地计算策略或 replay。

## 2. 复核范围

审查输入：

```text
docs/tw_modular_daily_update_productization/PHASEU3_AUTOMATION_FRONTEND_FINAL_ACCEPTANCE_EXECUTION_REPORT_CN.md
docs/tw_modular_daily_update_productization/PHASEU2_REVIEW_AND_PHASEU3_WORK_CN.md
docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_FINAL_ACCEPTANCE_CN.md
docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_RUNBOOK_CN.md
docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_REVIEWER_CHECKLIST_CN.md
scripts/run_tw_modular_daily_readonly_update.py
scripts/validate_tw_modular_daily_readonly_update.py
backend/app/services/readonly_daily_update.py
backend/app/routes/readonly_daily_update.py
frontend/src/api/tw-stock.js
frontend/src/views/tw-stock-monitor/index.vue
data_tw/experiments/modular_daily_update/u3_validation_summary.json
data_tw/artifacts/daily_readonly_latest/latest.json
```

审查重点：

```text
U1-U2 是否被串成 readonly daily orchestrator
success/no_new_data/validator_failed/module_failed 是否都有可追溯 registry
readonly latest pointer 是否仍不是 provider accepted latest / qlib accepted latest / trade target latest
后端新增路由是否 GET-only
前端新增 API 是否 GET-only
前端 readonly daily card 是否不调用 monitor/provider/broker/order/replay write path
network audit 是否 forbidden_request_count=0 且 ops_dry_run_post_count=0
Agent 是否未扩权
最终验收、runbook、reviewer checklist 是否存在
```

## 3. 通过项

### 3.1 Orchestrator 覆盖四类状态

`scripts/run_tw_modular_daily_readonly_update.py --scenario all --update-latest --json` 生成：

```text
data_tw/experiments/modular_daily_update/u3_validation_summary.json
```

覆盖状态：

```text
success
no_new_data
validator_failed
module_failed
```

summary 关键字段：

```text
ok=true
legacy_provider_publish_gate_default_disabled=true
readonly_latest_pointer=data_tw/artifacts/daily_readonly_latest/latest.json
readonly_latest_pointer_distinct_from_provider_accepted_latest=true
readonly_latest_pointer_distinct_from_qlib_accepted_latest=true
provider_accepted_latest_changed=false
qlib_accepted_latest_changed=false
monitor_broker_order_changed=false
```

每个场景的 RunRegistry 均通过 `validate_tw_daily_run_registry.py` 校验。

### 3.2 U3 validator 通过

复跑：

```bash
python -m py_compile scripts/validate_tw_modular_daily_readonly_update.py scripts/run_tw_modular_daily_readonly_update.py backend/app/services/readonly_daily_update.py backend/app/routes/readonly_daily_update.py
python scripts/validate_tw_modular_daily_readonly_update.py --json
```

结果：

```text
ok=true
status=passed
schema_version=u3.modular_daily_readonly_update_validator.v1
errors=[]
warnings=[]
```

### 3.3 后端 GET-only 接口成立

新增后端路由：

```text
GET /api/tw-stock/readonly-daily-latest
GET /api/tw-stock/readonly-daily-run-registry
```

U3 validator 结果：

```text
backend_get_only_audit.readonly_daily_latest=true
backend_get_only_audit.readonly_daily_run_registry=true
backend_get_only_audit.blueprint_registered=true
backend_get_only_audit.write_method_count=0
service_checks_provider_latest_flags=true
service_checks_trade_flags=true
```

`backend/app/services/readonly_daily_update.py` 会校验：

```text
daily_readonly_latest_pointer
updated_only_after_all_validators_passed=true
not_provider_accepted_latest=true
not_qlib_accepted_latest=true
not_trade_target_latest=true
readonly_only=true
production_trade_enabled=false
snapshot 位于 data_tw/artifacts/daily_readonly_snapshots/
snapshot readonly_only / not_order / not_target_position / not_investment_advice
```

### 3.4 前端 GET-only 与文案边界成立

新增前端 API：

```text
getTwStockReadonlyDailyLatest -> GET /readonly-daily-latest
getTwStockReadonlyDailyRunRegistry -> GET /readonly-daily-run-registry
```

U3 validator 结果：

```text
method_get=true
write_method_count=0
forbidden text hits 全部 0
```

前端新增 readonly daily card 使用：

```text
candidate observations
readonly_only
not_order
not_investment_advice
```

未把 `intent_action=buy` 展示成“下单”“买入指令”“目标仓位”或自动交易语义。

### 3.5 Network audit 通过

U3 validator 输出：

```text
readonly_workflow_only_get=true
forbidden_request_count=0
forbidden_requests=[]
suspicious_requests=[]
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
ops_provider_publish_refresh_accepted_latest_request_count=0
broker_quick_trade_orders_request_count=0
replay_strategy_write_count=0
ops_dry_run_post_count=0
failed_response_count=0
```

这满足 full readonly E2E 的关键要求：前端完整只读 workflow 不通过 POST 触发 ops dry-run，也不触发 provider/latest、monitor、broker/order 或 replay write。

### 3.6 最终交付文档存在

U3 已输出：

```text
docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_FINAL_ACCEPTANCE_CN.md
docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_RUNBOOK_CN.md
docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_REVIEWER_CHECKLIST_CN.md
```

这些文档内容偏简洁，但覆盖了最终读取点、日常执行命令、验证命令、GET API、运行约束和审查清单。当前不阻塞收口；后续正式运维前可继续加厚故障排查细节和部署细节。

## 4. 台股只读安全边界审查

### Findings

Critical：未发现 U3 触发 provider refresh / publish、provider accepted latest 或 qlib accepted latest switch、broker / quick-trade / orders、target position 或真实交易路径。

High：未发现 U3 写 monitor config / scan / alerts；前端 readonly daily workflow 的 forbidden request counters 全为 0，`ops_dry_run_post_count=0`。

Medium：当前 orchestrator 仍使用本地 staging/demo artifact 构建链路。它已经满足“模块化只读日更产品化”的 dry-run/shadow-run 收口，但后续若接真实 provider 拉取或 raw archive 写入，必须另开数据源接入/生产运行专项，并重新审查 provider、accepted latest、失败回滚和外部请求边界。

Low：最终 runbook/checklist 较简洁。建议后续运维强化：定时任务配置、日志位置、常见失败码、手动回滚 readonly latest pointer 的流程，以及前端 E2E 复跑说明。

### Verdict

U3 通过。真实模块化日更只读产品化主线可以收口。

## 5. 残余风险

1. 当前 `data_tw/artifacts/daily_readonly_latest/latest.json` 是 readonly daily latest pointer，不是 qlib/provider accepted latest，也不是交易 latest。后续任何迁移到其他 latest 路径都必须重新审查。
2. 当前自动链路默认使用本地 staging artifact；真实外部数据刷新不在本次收口范围内。
3. 前端页面仍有历史 monitor、sim order、ops 区块，但 U3 readonly daily card 和 API audit 已证明新增 workflow 不调用这些入口。后续改动仍需复跑 U3 validator。
4. Agent 未扩权。若要让 Agent 解释 readonly daily result，必须另开 Agent readonly context 专项，不能直接复用本次主线作为 Agent tool/action 授权。

## 6. 最终收口判定

本主线从 U0 到 U3 的目标已经达成：

```text
U0: 合同冻结与当前链路审计
U1: daily DataIngestion / Feature / ModelSignal staging artifact
U2: daily OrderIntent / ReadonlySnapshot / RunRegistry / readonly latest pointer
U3: readonly orchestrator + GET-only API + frontend display + final runbook/checklist
```

可以收尾。

后续如继续推进，建议不要在本主线内追加范围，而是另开以下专项：

```text
真实 provider 数据源接入与 raw archive 写入专项
生产调度 / cron / systemd 部署专项
readonly daily frontend E2E 自动化专项
Agent readonly daily context 专项
```

这些专项仍必须继承本次边界：

```text
no provider publish / accepted latest without explicit approval
no monitor write
no broker / quick-trade / orders
no Agent prompt/tool/action expansion by default
frontend readonly workflow GET-only
```
