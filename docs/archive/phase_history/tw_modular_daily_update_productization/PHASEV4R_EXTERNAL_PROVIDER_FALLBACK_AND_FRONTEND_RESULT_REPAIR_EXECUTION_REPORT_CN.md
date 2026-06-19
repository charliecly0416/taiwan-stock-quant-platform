# Phase V4R 外部价格源 fallback 与前端结果修复执行报告

生成日期：2026-06-17

## 1. 目标

修复 V4 中 Yahoo 403 导致的价格源阻断，补齐真实外网 provider 可解释性，并提供真实后端前端 E2E 证据。

## 2. 方案

采用 `preferred_yahoo_fallback_finmind`：
- Yahoo 作为首选价格源。
- Yahoo 失败时，若 FinMind daily price ready 且覆盖率满足阈值，则将价格层标记为 ready。
- 仅记录价格源 fallback，不触发 provider publish、accepted latest、monitor、broker、orders 或 Agent。

## 3. 代码修复

- `scripts/pull_tw_provider_staging_data.py`
  - 为 `yahoo_daily_price` 增加 fallback 元数据：`price_source_policy`、`fallback_used`、`fallback_source_id`、`fallback_reason`。
  - Yahoo 403 但 FinMind ready 时，将价格层标记为 ready。
- `scripts/build_tw_data_readiness_gate.py`
  - 透传 `price_source_policy` 与 `price_fallback_used`。
  - 保持非 ready 场景不误更新 readonly latest。
- `scripts/validate_tw_provider_staging_data.py`
  - 校验 fallback policy、fallback source、FinMind ready、provider network audit。
- `scripts/validate_tw_real_provider_daily_readonly_update.py`
  - 校验 real-provider run registry 能证明外网 fallback 是只读、可机读的。
- `backend/app/services/readonly_daily_update_runs.py`
  - 增加用户可读状态摘要 `user_status` / `user_message` / `provider_user_status`。
- `frontend/src/views/tw-stock-monitor/index.vue`
  - 将 `provider_failed` 收敛为用户可读状态文案。
  - 主文案优先显示后端返回的用户消息。
- `frontend/tests/e2e/tw-stock-real-provider-daily-update-real-backend-e2e.mjs`
  - 新增真实后端 E2E，按钮路径使用真实 POST。

## 4. 真实运行结果

### 4.1 real-provider orchestrator

Run ID:
- `phasev4r_external_provider_orchestrator_codex_v1`

结果：
- `status=no_new_data`
- `gate_status=no_new_data`
- `readonly_latest_updated=false`
- `u_chain_started=false`

### 4.2 provider staging 关键证据

`data_readiness_manifest.json`：
- `price_source_policy.policy=preferred_yahoo_fallback_finmind`
- `price_source_policy.fallback_used=true`
- `price_source_policy.ready_source_id=finmind_daily_price`
- `yahoo_daily_price.status=ready`
- `yahoo_daily_price.fallback_used=true`
- `yahoo_daily_price.fallback_source_id=finmind_daily_price`
- `finmind_daily_price.status=ready`
- `orthogonal_o2_features.status=no_new_data`

`provider_network_audit.json`：
- `request_count=25`
- `actual_external_request_count=25`
- `successful_request_count=15`
- `failed_request_count=10`
- `unauthorized_request_count=0`
- allowed hosts only:
  - `api.finmindtrade.com`
  - `query1.finance.yahoo.com`

### 4.3 validator

- provider staging validator: passed
- data readiness gate validator: passed
- real-provider run validator: passed
- golden 回归：passed

## 5. 前端真实后端 E2E

脚本：
- `frontend/tests/e2e/tw-stock-real-provider-daily-update-real-backend-e2e.mjs`

结果：
- `trigger_post_count=1`
- `forbidden_request_count=0`
- `console_error_count=0`
- `page_error_count=0`
- 真实后端 daily update 路径已命中

## 6. 安全边界

未发现以下越界行为：
- provider publish
- accepted latest switch
- monitor config/scan/alerts 写入
- broker / quick-trade / orders
- Agent prompt / tool / action 修改

## 7. 结论

V4R 已修复价格源 fallback 与前端用户解释，并补齐真实后端前端 E2E 证据。当前真实链路在外部价格源可用性方面已从 `provider_failed` 收敛为可解释的 `no_new_data`，且仍保持 readonly 安全边界。