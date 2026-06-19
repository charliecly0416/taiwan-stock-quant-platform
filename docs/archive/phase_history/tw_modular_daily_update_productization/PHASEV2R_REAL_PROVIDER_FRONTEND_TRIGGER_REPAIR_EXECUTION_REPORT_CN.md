# Phase V2R Real Provider Frontend Trigger Repair 执行报告

生成时间：2026-06-17

对应工作文档：`docs/tw_modular_daily_update_productization/PHASEV2_REVIEW_AND_PHASEV2R_WORK_CN.md`

## 0. 执行结论

Phase V2R 已完成 V2 的产品化修复：

1. 前端“只读策略结果更新”按钮已接入只读日更卡片。
2. 前端状态闭环已补齐 provider readiness、run list、run detail、triggerable / running / already_latest / success / failed / no_data 文案。
3. 生产手动 POST 不再接受前端注入的 `scenario`，测试 scenario 仅保留在服务端环境变量或 CLI 路径。
4. V2 orchestrator、validator、static API safety、golden scenarios 仍通过。

本轮仍未接入真实 Yahoo / FinMind / orthogonal 网络拉取；provider staging 仍保留合同化生成器形态，因此 V2R 只修复了前端触发闭环和生产/test 隔离，不宣称真实 provider 拉取已产品化。

## 1. 本轮修改

### 1.1 前端

`frontend/src/views/tw-stock-monitor/index.vue` 的只读日更卡片新增：

```text
更新 readiness
更新只读策略结果
```

并补齐状态展示：

```text
already_latest -> 已是最新
running -> 正在更新
triggerable -> 可更新
no_data_after_trigger -> 最新数据暂不可用
success_after_trigger -> 更新成功
failed_after_trigger -> 更新失败
```

同时接入：

```text
getTwStockProviderReadinessLatest
getTwStockReadonlyDailyUpdateRuns
getTwStockReadonlyDailyUpdateRun
triggerTwStockReadonlyDailyUpdateRun
```

### 1.2 前端 API

`frontend/src/api/tw-stock.js` 新增只读 update 相关 API wrapper，手动触发 POST 仅发送 `idempotency_key`。

### 1.3 后端

`backend/app/routes/readonly_daily_update_runs.py` 与 `backend/app/services/readonly_daily_update_runs.py` 提供：

```text
GET /api/tw-stock/provider-readiness/latest
GET /api/tw-stock/readonly-daily-update-runs
GET /api/tw-stock/readonly-daily-update-runs/<run_id>
POST /api/tw-stock/readonly-daily-update-runs
```

其中 POST 只接收 `idempotency_key`，测试 scenario 转移到服务端环境变量 `TW_REAL_PROVIDER_DAILY_UPDATE_TEST_SCENARIO`，避免前端注入测试态。

## 2. V2R 修复结果

### 2.1 前端闭环

页面已实际接入手动更新按钮和状态闭环，不再只停留在 API wrapper。

### 2.2 生产 / 测试隔离

生产 POST 不再接受 `scenario` 参数。

### 2.3 只读安全边界

本轮仍保持：

```text
provider accepted latest unchanged
qlib accepted latest unchanged
monitor / broker / orders / Agent unchanged
readonly_only=true
```

## 3. 验证结果

```text
python scripts/run_tw_real_provider_daily_readonly_update.py --scenario manual_trigger_success --run-id phasev2r_manual_trigger_success_codex_v1 --json
ok=true
status=success
gate_status=all_required_ready
```

```text
python scripts/validate_tw_real_provider_daily_readonly_update.py --run-golden --json
ok=true
status=passed
sample_count=14
```

```text
python scripts/validate_tw_real_provider_daily_readonly_update.py --static-api --json
ok=true
status=passed
```

```text
python -m py_compile backend/app/services/readonly_daily_update_runs.py backend/app/routes/readonly_daily_update_runs.py scripts/run_tw_real_provider_daily_readonly_update.py scripts/validate_tw_real_provider_daily_readonly_update.py
passed
```

## 4. 仍未完成项

V2R 未把 provider staging 升级为真实 Yahoo / FinMind / orthogonal 网络拉取链路，因此 Phase V 仍不能宣称真实 provider 自动链路已完全产品化。后续若要真正收尾，还需要单独把 staging runner 从合同生成器升级为真实 provider reader，并补充前端运行时 network audit 证据。
