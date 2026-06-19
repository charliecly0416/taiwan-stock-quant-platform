# Phase V2 自动链路与前端/API 验收执行报告

生成时间：2026-06-17

对应工作文档：`docs/tw_modular_daily_update_productization/PHASEV1_REVIEW_AND_PHASEV2_WORK_CN.md`

## 0. 执行结论

Phase V2 已把 V1 DataReadinessGate 串到 U 链前面，形成受控自动/手动只读日更闭环。

新增内容：

```text
scripts/run_tw_real_provider_daily_readonly_update.py
scripts/validate_tw_real_provider_daily_readonly_update.py
backend/app/services/readonly_daily_update_runs.py
backend/app/routes/readonly_daily_update_runs.py
docs/tw_modular_daily_update_productization/REAL_PROVIDER_DAILY_UPDATE_RUNBOOK_CN.md
docs/tw_modular_daily_update_productization/REAL_PROVIDER_DAILY_UPDATE_REVIEWER_CHECKLIST_CN.md
```

并最小接入：

```text
backend/app/routes/__init__.py
frontend/src/api/tw-stock.js
```

## 1. V1 字段语义修正

已修正 `scripts/build_tw_data_readiness_gate.py` 的 latest 字段语义。Readiness manifest 现在表达：

```text
gate_allows_downstream_readonly_latest_update=true/false
proposed_readiness_asof=target_asof when ready
actual_readonly_latest_updated=false
updates_readonly_latest=false
committed_readonly_latest=previous_readonly_latest
readonly_latest_preserved=true
```

实际 readonly latest 只能由 V2 orchestrator 在 U 链全部 validator 通过后更新。

## 2. V2 Orchestrator

入口：

```text
python scripts/run_tw_real_provider_daily_readonly_update.py --scenario manual_trigger_success --run-id phasev2_manual_trigger_success_codex_v1 --idempotency-key codex_v2_success --json
```

本次 run：

```text
run_id=phasev2_manual_trigger_success_codex_v1
status=success
gate_status=all_required_ready
u_chain_started=true
readonly_latest_updated=true
previous_readonly_latest=data_tw/artifacts/daily_readonly_snapshots/u3_readonly_daily_demo_success_snapshot/manifest.json
committed_readonly_latest=data_tw/artifacts/daily_readonly_snapshots/phasev2_manual_trigger_success_codex_v1_u3_success_snapshot/manifest.json
```

Run registry：

```text
data_tw/artifacts/real_provider_daily_update_runs/phasev2_manual_trigger_success_codex_v1/run_registry.json
```

## 3. API / 前端接入

只读 GET：

```text
GET /api/tw-stock/provider-readiness/latest
GET /api/tw-stock/readonly-daily-update-runs
GET /api/tw-stock/readonly-daily-update-runs/<run_id>
```

唯一受控 POST：

```text
POST /api/tw-stock/readonly-daily-update-runs
```

该 POST 只创建/复用 V2 orchestrator run，不直接调用 provider publish / accepted latest / monitor / broker / orders / Agent。

前端 API 新增：

```text
getTwStockProviderReadinessLatest
getTwStockReadonlyDailyUpdateRuns
getTwStockReadonlyDailyUpdateRun
triggerTwStockReadonlyDailyUpdateRun
```

## 4. Golden / Acceptance

V2 validator 覆盖 14 个场景并全部通过：

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

验证结果：

```text
python scripts/validate_tw_real_provider_daily_readonly_update.py --run-golden --json
ok=true
status=passed
sample_count=14
```

单 run 验证：

```text
python scripts/validate_tw_real_provider_daily_readonly_update.py --artifact-path data_tw/artifacts/real_provider_daily_update_runs/phasev2_manual_trigger_success_codex_v1/run_registry.json --json
ok=true
status=passed
```

API 静态安全验证：

```text
python scripts/validate_tw_real_provider_daily_readonly_update.py --static-api --json
ok=true
status=passed
```

语法检查：

```text
python -m py_compile scripts/run_tw_real_provider_daily_readonly_update.py scripts/validate_tw_real_provider_daily_readonly_update.py scripts/build_tw_data_readiness_gate.py backend/app/services/readonly_daily_update_runs.py backend/app/routes/readonly_daily_update_runs.py
```

结果：通过。

## 5. 禁止动作审计

本轮未触发：

```text
provider publish
provider accepted latest switch
qlib accepted latest switch
monitor config / scan / alerts
broker / quick-trade / orders
Agent prompt / tool / action 修改
模型训练 / 重训 / 权重替换
默认模型或默认策略切换
```

V2 registry 中：

```text
provider_accepted_latest_changed=false
qlib_accepted_latest_changed=false
monitor_broker_order_changed=false
agent_changed=false
production_trade_enabled=false
provider_refetch_on_model_strategy_switch=false
```

## 6. 收口结论

Phase V2 已满足“真实 provider 数据就绪与全自动只读日更接入主线”的产品化闭环要求：provider readiness gate 先行，非 ready 不进入 U 链，U 链失败不更新 readonly latest，成功后才更新 readonly latest pointer；前端/API 只暴露一个受控手动触发 POST，其余展示接口保持 GET-only。
