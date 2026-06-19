# Phase V4 审查与 Phase V4R 修复工作文档

生成日期：2026-06-17

## 1. 审查结论

Phase V4 条件通过，但 V 路线暂不收尾，建议进入 Phase V4R。

V4 已完成外网 provider reader 的关键突破：FinMind 外网拉取成功，Yahoo 外网请求真实发生并被审计，provider network audit 记录了真实 host、HTTP status、重试和失败；系统在 Yahoo 403 导致 required price source 失败时正确停在 `provider_failed`，没有进入 U 链，没有更新 readonly latest，也没有触发 provider publish / accepted latest / monitor / broker / orders / Agent。

但 V4 当前真实运行结果仍是：

```text
status=provider_failed
gate_status=provider_failed
readonly_latest_updated=false
u_chain_started=false
```

这说明链路安全、可解释，但还不是“真实数据可用并成功更新只读策略结果”的最终收口状态。前端也能返回状态，但对普通用户仍不够准确：`provider_failed` 被统一映射成“更新失败”，主要展示内部 failure reason，不能清楚告诉用户“外部 Yahoo 数据源暂时拒绝访问，旧结果已保留，FinMind 数据已拉到”。

因此结论是：V4 外网接入方向通过，V 路线不能收尾。V4R 必须修复 Yahoo fallback / source policy 和前端用户解释。

## 2. 复核范围

审查输入：

```text
docs/tw_modular_daily_update_productization/PHASEV4_EXTERNAL_PROVIDER_READER_EXECUTION_REPORT_CN.md
docs/tw_modular_daily_update_productization/PHASEV3_REVIEW_AND_PHASEV4_WORK_CN.md
scripts/fetch_tw_provider_external_data.py
scripts/pull_tw_provider_staging_data.py
scripts/run_tw_real_provider_daily_readonly_update.py
scripts/validate_tw_real_provider_daily_readonly_update.py
backend/app/services/readonly_daily_update_runs.py
backend/app/routes/readonly_daily_update_runs.py
frontend/src/views/tw-stock-monitor/index.vue
frontend/tests/e2e/tw-stock-real-provider-daily-update-e2e.mjs
data_tw/artifacts/provider_staging/phasev4_external_provider_orchestrator_codex_v1_provider_staging/
data_tw/artifacts/real_provider_daily_update_runs/phasev4_external_provider_orchestrator_codex_v1/run_registry.json
```

复跑命令：

```text
python scripts/validate_tw_real_provider_daily_readonly_update.py --artifact-path data_tw/artifacts/real_provider_daily_update_runs/phasev4_external_provider_orchestrator_codex_v1/run_registry.json --json
python scripts/validate_tw_real_provider_daily_readonly_update.py --static-api --json
python scripts/validate_tw_real_provider_daily_readonly_update.py --run-golden --json
python -m py_compile scripts/fetch_tw_provider_external_data.py scripts/pull_tw_provider_staging_data.py scripts/run_tw_real_provider_daily_readonly_update.py scripts/validate_tw_real_provider_daily_readonly_update.py backend/app/services/readonly_daily_update_runs.py backend/app/routes/readonly_daily_update_runs.py
```

复跑结果：

```text
single_run_registry: ok=true, status=passed, run_status=provider_failed, gate_status=provider_failed
static_api: ok=true, status=passed
run_golden: ok=true, status=passed, sample_count=14
py_compile: passed
```

## 3. 已通过项

### 3.1 外网请求真实发生

V4 `provider_network_audit.json` 显示：

```text
request_count=25
actual_external_request_count=25
successful_request_count=15
failed_request_count=10
unauthorized_request_count=0
```

允许 host 仅为：

```text
api.finmindtrade.com
query1.finance.yahoo.com
```

这满足 V4 “必须证明外网请求真实发生且只访问允许 provider host” 的基础要求。

### 3.2 FinMind 三类数据已成功拉取

`data_readiness_manifest.json` 显示：

```text
finmind_daily_price: ready, actual_latest_asof=2026-06-17, coverage_ratio=1.0
finmind_institutional_flow: ready, actual_latest_asof=2026-06-17, coverage_ratio=1.0
finmind_margin_short: ready, actual_latest_asof=2026-06-17, coverage_ratio=1.0
```

这说明 FinMind 外网 reader 与 materialize 路径已基本成立。

### 3.3 Yahoo 失败被正确审计和阻断

Yahoo 请求真实发生，但全部返回 403：

```text
source_id=yahoo_daily_price
http_status=403
symbols_success=0
symbols_failed=5
status=failed
failure_reason=external provider failed symbols: 5
```

由于 `yahoo_daily_price` 是 required source，DataReadinessGate 正确判定：

```text
gate_status=provider_failed
gate_allows_downstream_readonly_latest_update=false
```

### 3.4 只读安全边界继续成立

V4 run registry 证明：

```text
provider_accepted_latest_changed=false
qlib_accepted_latest_changed=false
monitor_broker_order_changed=false
agent_changed=false
production_trade_enabled=false
readonly_latest_updated=false
u_chain_started=false
```

未发现 broker / quick-trade / orders、target position、provider accepted latest、qlib accepted latest、monitor scan / alerts 或 Agent action 扩权。

## 4. 阻断项

### 4.1 Critical：真实默认链路仍停在 provider_failed，V 路线不能收尾

V4 的默认 orchestrator 真实结果为：

```text
status=provider_failed
gate_status=provider_failed
readonly_latest_updated=false
u_chain_started=false
```

这对安全是正确的，但不满足最终收尾所需的“外网数据可用、all_required_ready、U 链通过、readonly latest 更新、前端展示最新只读策略结果”。

### 4.2 High：Yahoo required source 无 fallback 策略

当前 Yahoo chart API 返回 403，导致整个 required price source 失败。系统没有明确支持：

```text
Yahoo 403 时使用 FinMind daily price 作为 required price fallback
或把 required price provider 从 Yahoo-only 改为 price_source_any_of=[Yahoo, FinMind]
或实现 Yahoo crumb/cookie/alternate endpoint
```

在 FinMind daily price 已 ready 的情况下，V4 仍因 Yahoo required 失败而阻断。这可能是正确保守策略，但需要 V4R 明确产品策略，否则外网自动链路会长期停在 provider_failed。

### 4.3 High：前端运行时 E2E 是 mock 后端，不证明真实后端返回及时

`frontend/tests/e2e/tw-stock-real-provider-daily-update-e2e.mjs` 使用 Playwright route mock 了：

```text
provider-readiness/latest
readonly-daily-update-runs
readonly-daily-latest
readonly-daily-run-registry
```

该测试证明了前端按钮能发出 1 次允许 POST，且无 forbidden request；但不能证明真实后端外网 provider run 在用户点击后能及时返回，也不能证明真实 `provider_failed` response 在 UI 上准确展示。

V4 报告中“前端可运行且返回及时、准确结果”的证据不足。

### 4.4 Medium：前端不完全符合用户第一性原则

用户第一性原则要求：简单、准确、实用、清晰。

当前前端：

```text
简单：主按钮“更新只读策略结果”清楚，但旁边仍有“刷新页面数据 / 查看诊断记录 / 检查数据就绪”，普通用户路径还略复杂。
准确：provider_failed 被统一映射为“更新失败”，但真实原因是 Yahoo 外部数据源 403、FinMind 已成功、旧结果已保留。用户无法一眼理解是数据源问题，不是策略系统故障。
实用：失败时保留旧结果，并显示 failure reason，具备基础实用性。
清晰：状态文案仍偏工程化，例如 `yahoo_daily_price: external provider failed symbols: 5`，不够用户化。
```

V4R 必须把 provider_failed 文案收敛成用户能理解的一句话，同时把详细 provider 审计放入诊断折叠区。

### 4.5 Medium：provider network audit 尚未形成前端可读摘要

后端已经记录 provider network audit，但 API / 前端没有把关键摘要转成用户级解释：

```text
Yahoo 暂时不可用
FinMind 数据已更新到 2026-06-17
旧策略结果已保留
系统会等待下一轮自动重试
```

这影响“及时、准确”的前端验收。

## 5. 台股只读安全边界审查

### Findings

Critical：未发现 V4 触发 broker / quick-trade / orders、target position、provider accepted latest 或 qlib accepted latest switch。

Critical：真实默认链路仍为 `provider_failed`，不能作为 V 路线最终收尾。

High：Yahoo required source 403 缺少 fallback / any-of source policy，导致 FinMind ready 也无法进入 ready gate。

High：前端 E2E 使用 mock 后端，不能证明真实外网 provider run 的及时返回和真实失败文案准确性。

Medium：前端对普通用户仍偏工程化，`provider_failed` 的解释不够简单、准确、清晰。

### Network Audit

Provider network audit 通过基础安全检查：

```text
actual_external_request_count=25
unauthorized_request_count=0
allowed_hosts=[api.finmindtrade.com, query1.finance.yahoo.com]
```

但 Yahoo 10 次请求均失败，HTTP 403；FinMind 15 次请求成功。

前端运行时 E2E 只证明允许 POST 与无 forbidden request，不证明真实 provider run 时延和真实结果文案。

### Console Audit

V4 报告给出的 E2E 摘要为：

```text
console_error_count=0
page_error_count=0
```

但未输出独立可审计的 frontend network_audit artifact；报告仅有摘要。

### Text / Agent Semantics

未发现 Agent prompt / tool / action 修改。前端文案保持“只读展示 / 受控更新 / 更新只读策略结果”，没有交易、下单、目标仓位或收益承诺语义。

### Verdict

V4 条件通过，V 路线不可收尾。必须进入 V4R。

## 6. Phase V4R 必须修复

### 6.1 价格源 fallback / any-of policy

V4R 必须明确并实现以下任一策略：

```text
方案 A：修复 Yahoo 外网 reader，使 Yahoo daily price 可稳定返回 ready
方案 B：引入 price_source_any_of=[Yahoo, FinMind]，Yahoo 403 但 FinMind price ready 时允许 price layer ready
方案 C：将 Yahoo 作为 preferred source、FinMind daily price 作为 required fallback，并在 manifest 中记录 fallback_used=true
```

无论采用哪种方案，都必须证明：

```text
价格源 ready 的判断可机读
fallback 不触发 provider publish / accepted latest
fallback 有 provider_network_audit
fallback 后仍通过 schema / PIT / coverage / symbol mapping
```

### 6.2 真实后端前端 E2E

V4R 必须提供非 mock 的前端按钮路径验收，至少覆盖：

```text
用户点击更新只读策略结果
真实后端触发 external_provider_reader
前端在合理时间内返回状态
返回 provider_failed / no_new_data / all_ready 中的真实状态
只产生 1 次允许 POST
无 provider publish / accepted latest / monitor / broker / orders / Agent 请求
```

如果外网 provider 运行超过前端可接受时间，后端应立即返回 `running` + `run_id`，前端轮询 run detail，而不是让用户长时间等待同步 POST。

### 6.3 前端用户第一性原则修复

V4R 前端必须将 provider 状态解释成用户级文案：

```text
provider_failed + Yahoo 403 -> 外部行情源暂时不可用，旧策略结果已保留，系统会等待下一轮重试。
FinMind ready + Yahoo failed -> 部分数据已更新，但行情价格源未通过，暂不生成新策略。
all_required_ready -> 数据已更新，正在展示最新只读策略结果。
no_new_data -> 数据源还没有新收盘数据，旧结果继续有效。
```

诊断细节可以折叠展示：

```text
provider_network_audit
failed symbols
HTTP status
retry count
source-level readiness
```

主界面只保留一条主状态、一条主解释和一个主按钮。

### 6.4 V4R validator / report 必须新增

V4R 执行报告必须提供：

```text
price fallback / Yahoo repair 设计说明
真实外网 provider run registry
provider network audit artifact
data_readiness_manifest
frontend real-backend E2E artifact
frontend network audit artifact
console audit artifact
是否更新 readonly latest 的证据
```

建议执行报告命名：

```text
docs/tw_modular_daily_update_productization/PHASEV4R_EXTERNAL_PROVIDER_FALLBACK_AND_FRONTEND_RESULT_REPAIR_EXECUTION_REPORT_CN.md
```

## 7. V 路线最终收尾门槛

V 路线最终收尾至少需要：

```text
外网 price source ready，或明确 any-of fallback ready
FinMind price / institutional / margin-short ready
orthogonal / existing signal ready
gate_status=all_required_ready 的真实外网样本
U-chain validators 全部通过
readonly latest 只在全部通过后更新
前端真实后端 E2E 返回及时、准确、用户可理解
provider network audit + frontend network audit 均通过
无 provider accepted latest / qlib accepted latest / monitor / broker / orders / Agent 越界
```

达到以上门槛后，才能再次判断 Phase V 是否可以最终收尾。
