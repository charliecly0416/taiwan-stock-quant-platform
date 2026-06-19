# Phase V3 审查与 Phase V4 工作文档

生成日期：2026-06-17

## 1. 审查结论

Phase V3 通过，允许进入 Phase V4。

V3 已完成本地 real_provider reader、生产/test 隔离、前端只读按钮闭环和运行时 E2E 审计，且所有 validator / golden / static API 检查通过。V3 的结论也明确：当前 reader 读取的是本地真实产物，不是外网 Yahoo / FinMind 拉取。

因此 V4 的唯一正题是把 provider reader 从“本地真实产物读取”升级为“真实外网 provider 拉取”，并继续保持只读安全边界。

## 2. 复核范围

审查输入：

```text
docs/tw_modular_daily_update_productization/PHASEV2R_REVIEW_AND_PHASEV3_WORK_CN.md
docs/tw_modular_daily_update_productization/PHASEV3_REAL_PROVIDER_READER_AND_FRONTEND_E2E_EXECUTION_REPORT_CN.md
scripts/pull_tw_provider_staging_data.py
scripts/run_tw_real_provider_daily_readonly_update.py
scripts/validate_tw_real_provider_daily_readonly_update.py
backend/app/services/readonly_daily_update_runs.py
backend/app/routes/readonly_daily_update_runs.py
frontend/src/views/tw-stock-monitor/index.vue
frontend/src/api/tw-stock.js
data_tw/artifacts/real_provider_daily_update_runs/phasev3_real_provider_default_codex_v1/run_registry.json
```

复跑命令：

```text
python scripts/validate_tw_real_provider_daily_readonly_update.py --run-golden --json
python scripts/validate_tw_real_provider_daily_readonly_update.py --static-api --json
python scripts/validate_tw_real_provider_daily_readonly_update.py --artifact-path data_tw/artifacts/real_provider_daily_update_runs/phasev3_real_provider_default_codex_v1/run_registry.json --json
python -m py_compile scripts/pull_tw_provider_staging_data.py scripts/run_tw_real_provider_daily_readonly_update.py scripts/validate_tw_real_provider_daily_readonly_update.py backend/app/services/readonly_daily_update_runs.py backend/app/routes/readonly_daily_update_runs.py
```

复跑结果：

```text
run_golden: ok=true, status=passed, sample_count=14
static_api: ok=true, status=passed
single_run_registry: ok=true, status=passed
py_compile: passed
```

## 3. 已通过项

### 3.1 本地 real_provider reader 已成立

`scripts/pull_tw_provider_staging_data.py` 已能在 `--mode real_provider` 下读取本地真实产物，并正确判定：

```text
partial_data_pending
no_new_data
ready
```

它能稳定保留 `previous readonly latest`，并且不会越过 U 链或触发 provider publish / accepted latest。

### 3.2 生产/test 隔离已成立

生产默认 orchestrator 不再依赖测试 scenario 注入；测试态仅在显式 `--test-mode` 下可用。这一层隔离已通过 validator / golden / 单 run 校验。

### 3.3 前端只读闭环已成立

前端主按钮与状态已经满足最小可用产品形态：

```text
更新 readiness
更新只读策略结果
已是最新 / 正在更新 / 可更新 / 最新数据暂不可用 / 更新成功 / 更新失败
```

这部分已不再是 V4 的主要问题。

### 3.4 只读安全边界仍然成立

V3 run registry 与审计结果继续证明：

```text
provider_accepted_latest_changed=false
qlib_accepted_latest_changed=false
monitor_broker_order_changed=false
agent_changed=false
production_trade_enabled=false
manual_trigger_post_allowlist=["/api/tw-stock/readonly-daily-update-runs"]
forbidden_request_count=0
```

## 4. 阻断项

### 4.1 Critical：尚未接入外网 Yahoo / FinMind 真实网络拉取

V3 目前读取的是本地真实产物，来源包括：

```text
data_tw/self_contained_demo/normalized
data_tw/experiments/decision_orthogonal/phase0d_pit_clean
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/phaseo2_summary.json
data_tw/artifacts/signals/*/r1_legacy_signal_adapter_20260616/manifest.json
```

这意味着当前没有真正执行：

```text
Yahoo 外网 HTTP 拉取
FinMind 外网 HTTP 拉取
真实 provider 请求重试
真实 provider 限流 / 失败 / 部分成功判定
```

因此 Phase V 还不能在 V3 收尾；V4 必须把“本地真实产物读取”升级为“外网 provider reader”。

### 4.2 High：外网 provider reader 目前没有独立的网络审计闭环

V3 已有前端 E2E 审计，但那只是 UI 到后端的只读路径审计。V4 引入外网后，必须新增 provider 网络审计，证明：

```text
actual external requests were sent only to allowed Yahoo / FinMind endpoints
no provider publish / refresh / accepted latest
no monitor / broker / orders / Agent write path
no unauthorized domains
retry / timeout / backoff behavior is recorded
```

### 4.3 Medium：V3 的 real_provider 名称仍偏本地语义

`real_provider` 这个名称在 V3 语境里仍对应“本地真实产物读取”。V4 接入外网后，必须在文档和代码中区分：

```text
local_real_provider_reader
external_provider_reader
test_scenario
```

避免后续执行者把“real_provider”误解成“已经联网拉取”。

## 5. 台股只读安全边界审查

### Findings

Critical：未发现 V3 触发 broker / quick-trade / orders、target position、provider accepted latest 或 qlib accepted latest switch。

Critical：V3 仍未接入外网 Yahoo / FinMind，因此允许进入 V4，但不允许把 V3 视为最终收尾。

High：V4 接入外网时必须补 provider 网络审计，不可只靠本地 validator。

Medium：当前前端已经足够实用，但如果 V4 引入更细粒度 provider 状态，UI 需要继续保持简单、准确、清晰，不能把网络错误、provider 错误和业务不可用混成一类。

### Network Audit

V3 有运行时 E2E 审计，但那是针对只读前端路径。V4 需要新增 provider 网络审计，不得只保留前端 E2E 审计。

### Console Audit

V3 未提供外网 provider 的 console audit；V4 需要补齐。

### Text / Agent Semantics

未发现 Agent 扩权。V4 期间仍不得出现“自动买入/自动卖出/目标仓位/下单/连接券商/刷新 provider/切换 accepted latest”等语义。

### Verdict

V3 可以进入 V4，但 V4 是新的外网 provider 接入阶段，不是收尾阶段。

## 6. Phase V4 工作范围

V4 目标：把 provider reader 从本地真实产物读取，升级为真实外网 Yahoo / FinMind 拉取。

V4 必做：

```text
1. 接入 Yahoo 真实网络抓取
2. 接入 FinMind 真实网络抓取
3. 统一 provider retry / timeout / backoff / rate-limit 策略
4. 将真实 provider 结果写入 provider_staging/<run_id>/
5. 保留 data_readiness_manifest / model_strategy_availability_matrix / forbidden_action_audit
6. 对 partial / no_new_data / failed / ready 进行真实判定
7. 保持 non-ready 不进入 U 链，U-chain failed 不更新 readonly latest
8. 新增 provider 网络审计与运行时证据
```

V4 建议新增：

```text
scripts/fetch_tw_provider_external_data.py
scripts/pull_tw_provider_staging_data.py  # 升级为外网 provider reader 主入口
scripts/validate_tw_provider_external_data.py
scripts/validate_tw_provider_staging_data.py  # 扩展网络/来源审计
scripts/validate_tw_real_provider_daily_readonly_update.py  # 扩展 provider network audit 断言
docs/tw_modular_daily_update_productization/PHASEV4_EXTERNAL_PROVIDER_READER_EXECUTION_REPORT_CN.md
```

## 7. Phase V4 必须实现的链路规则

外网 provider reader：

```text
create run_id
fetch Yahoo external data
fetch FinMind external data
validate provider payloads
materialize staging artifacts
build DataReadinessGate
if gate_status == all_required_ready:
    run U1-U3 readonly chain
    update readonly latest pointer
else:
    write RunRegistry / readiness status
    keep previous readonly latest
```

V4 外网拉取不得做：

```text
provider publish
provider refresh official path
provider accepted latest switch
qlib accepted latest switch
monitor config / scan / alerts
broker / quick-trade / orders
Agent prompt / tool / action 修改
```

## 8. Phase V4 验收门槛

V4 通过必须同时满足：

```text
Yahoo 外网请求真实发生且有审计
FinMind 外网请求真实发生且有审计
partial / no_new_data / failed / ready 状态真实可判定
provider network audit 通过
前端只读闭环继续通过
all_required_ready 且 U-chain validators 全通过后才更新 readonly latest
provider accepted latest / qlib accepted latest 永远不变
monitor / broker / orders / Agent 均无写入或扩权
```

V4 通过后，Phase V 才能继续向“真实 provider 数据就绪”最终收口推进。
