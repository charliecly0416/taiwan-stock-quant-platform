# Phase V2R 审查与 Phase V3 工作文档

生成日期：2026-06-17

## 1. 审查结论

Phase V2R 不可收尾，建议进入 Phase V3。

V2R 已修复 V2 的一部分阻断项：前端页面实际接入“只读策略结果更新”按钮，生产前端 POST 不再传入 `scenario`，V2 orchestrator / validator / static API safety / golden scenarios 复跑通过。

但 Phase V 主线目标是“真实 provider 数据就绪与全自动只读日更接入”。V2R 执行报告也明确写明：

```text
本轮仍未接入真实 Yahoo / FinMind / orthogonal 网络拉取；provider staging 仍保留合同化生成器形态
```

因此 V2R 只能判定为“前端触发闭环与生产/test 隔离修复通过”，不能判定为真实 provider 自动链路产品化收尾。

## 2. 复核范围

审查输入：

```text
docs/tw_modular_daily_update_productization/PHASEV2R_REAL_PROVIDER_FRONTEND_TRIGGER_REPAIR_EXECUTION_REPORT_CN.md
docs/tw_modular_daily_update_productization/PHASEV2_REVIEW_AND_PHASEV2R_WORK_CN.md
frontend/src/views/tw-stock-monitor/index.vue
frontend/src/api/tw-stock.js
backend/app/routes/readonly_daily_update_runs.py
backend/app/services/readonly_daily_update_runs.py
scripts/run_tw_real_provider_daily_readonly_update.py
scripts/validate_tw_real_provider_daily_readonly_update.py
scripts/pull_tw_provider_staging_data.py
data_tw/artifacts/real_provider_daily_update_runs/phasev2r_manual_trigger_success_codex_v1/run_registry.json
```

复跑命令：

```text
python scripts/validate_tw_real_provider_daily_readonly_update.py --run-golden --json
python scripts/validate_tw_real_provider_daily_readonly_update.py --static-api --json
python scripts/validate_tw_real_provider_daily_readonly_update.py --artifact-path data_tw/artifacts/real_provider_daily_update_runs/phasev2r_manual_trigger_success_codex_v1/run_registry.json --json
python -m py_compile backend/app/services/readonly_daily_update_runs.py backend/app/routes/readonly_daily_update_runs.py scripts/run_tw_real_provider_daily_readonly_update.py scripts/validate_tw_real_provider_daily_readonly_update.py
```

复跑结果：

```text
run_golden: ok=true, status=passed, sample_count=14
static_api: ok=true, status=passed
single_run_registry: ok=true, status=passed
py_compile: passed
```

## 3. 已通过项

### 3.1 前端按钮已实际接入页面

`frontend/src/views/tw-stock-monitor/index.vue` 的只读日更卡片已包含：

```text
更新 readiness
更新只读策略结果
```

并实际调用：

```text
getTwStockProviderReadinessLatest
getTwStockReadonlyDailyUpdateRuns
getTwStockReadonlyDailyUpdateRun
triggerTwStockReadonlyDailyUpdateRun
```

这修复了 V2 “只有 API wrapper、页面未消费”的阻断项。

### 3.2 前端 POST 不再传入 scenario

`frontend/src/api/tw-stock.js` 的手动触发只发送：

```text
idempotency_key
```

不再发送：

```text
scenario
```

这修复了 V2 的前端测试态注入风险。

### 3.3 状态闭环覆盖核心场景

前端状态已覆盖：

```text
already_latest -> 已是最新
running -> 正在更新
triggerable -> 可更新
no_data_after_trigger -> 最新数据暂不可用
success_after_trigger -> 更新成功
failed_after_trigger -> 更新失败
```

失败、未拉到数据、运行中、已最新都会保留旧结果语义，没有把用户引导到交易、下单或 target position。

### 3.4 只读安全边界继续通过

V2R 示例 run registry 和 validator 仍证明：

```text
provider_accepted_latest_changed=false
qlib_accepted_latest_changed=false
monitor_broker_order_changed=false
agent_changed=false
production_trade_enabled=false
manual_trigger_post_allowlist=["/api/tw-stock/readonly-daily-update-runs"]
```

未发现 broker / quick-trade / orders、target position、provider accepted latest、qlib accepted latest、monitor scan / alerts 或 Agent action 扩权。

## 4. 阻断项

### 4.1 Critical：真实 provider staging 仍未产品化

`scripts/pull_tw_provider_staging_data.py` 仍是合同化 scenario 生成器，核心逻辑仍围绕：

```text
--scenario all_required_ready
--scenario no_new_data
--scenario partial_data_pending
--scenario provider_failed
--scenario validator_failed_future_available_at
```

它生成 source_status，而不是实际拉取或读取：

```text
Yahoo daily price
FinMind daily price
FinMind institutional flow
FinMind margin short
orthogonal_o2_features latest local artifact
existing_signal_manifest latest local artifact
```

因此当前无法证明真实收盘后数据拉不到、拉到、partial、provider failed、orthogonal stale 等真实状态能被正确判定。

### 4.2 High：服务端默认仍是测试 scenario

`backend/app/services/readonly_daily_update_runs.py` 中：

```text
scenario = os.environ.get("TW_REAL_PROVIDER_DAILY_UPDATE_TEST_SCENARIO", "manual_trigger_success")
```

虽然前端不能注入 scenario，但生产服务端默认仍落到 `manual_trigger_success`。这对测试方便，但对真实产品化不准确。Phase V3 必须把默认模式改成 real provider mode；测试 scenario 只能在显式 test mode 中启用。

### 4.3 High：缺少前端运行时 network audit

V2R 仍未提供针对按钮点击路径的运行时 network audit。当前只有 static API validator 通过，不能证明：

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

### 4.4 Medium：前端不够符合用户第一性原则

用户第一性原则要求：简单、准确、实用、清晰。

当前 V2R 前端方向可接受，但还不够好：

```text
简单：按钮区同时有“更新 latest / 更新 registry / 更新 readiness / 更新只读策略结果”，普通用户不容易判断该点哪个。
准确：卡片标题区仍显示 GET only，但同一张卡片里存在受控 POST 手动触发按钮，语义不够准确。
实用：状态文案能告诉用户“成功 / 不可用 / 失败 / 已最新”，这是实用的。
清晰：主按钮“更新只读策略结果”是清晰的，但辅助按钮和字段名 data_asof/run_asof/provider readiness/latest run 偏工程化。
```

Phase V3 应把普通用户主路径收敛成一个主按钮和一个状态解释，工程诊断内容折叠到“查看诊断 / registry”中。

## 5. 台股只读安全边界审查

### Findings

Critical：未发现 V2R 触发 broker / quick-trade / orders、target position、provider accepted latest 或 qlib accepted latest switch。

Critical：真实 provider 数据链路未产品化，因此 Phase V 不能收尾。

High：服务端生产默认仍是测试 scenario `manual_trigger_success`，必须在 Phase V3 修正为真实 provider mode。

High：缺少前端按钮点击路径的运行时 network audit。

Medium：前端按钮接入后功能可用，但 UI 对普通用户仍偏工程化，不完全符合“简单、准确、实用、清晰”。

### Network Audit

V2R 未提供新的前端运行时 network audit artifact。静态 API 安全验证通过，但不足以替代按钮点击 E2E。

### Console Audit

V2R 未提供新的 console audit artifact。

### Text / Agent Semantics

未发现 Agent prompt / tool / action 修改。前端主按钮文案“更新只读策略结果”安全且准确；但 “GET only” 标签与同卡片受控 POST 并存，会给用户造成误解。

### Verdict

V2R 修复部分通过，但 Phase V 不可收尾。必须进入 Phase V3，完成真实 provider reader、生产默认 real mode、前端运行时 audit 和 UI 收敛。

## 6. Phase V3 必须完成

### 6.1 真实 provider reader

生产入口必须默认运行真实 provider mode：

```text
Yahoo daily price staging
FinMind daily price staging
FinMind institutional flow staging
FinMind margin short staging
orthogonal_o2_features local latest check
existing_signal_manifest local latest check
```

所有产物仍只能写入：

```text
data_tw/artifacts/provider_staging/<run_id>/
```

禁止：

```text
provider publish
provider refresh official publish path
provider accepted latest switch
qlib accepted latest switch
monitor / broker / orders / Agent
```

### 6.2 生产 / 测试模式硬隔离

Phase V3 必须满足：

```text
POST /api/tw-stock/readonly-daily-update-runs -> real provider mode only
TW_REAL_PROVIDER_DAILY_UPDATE_TEST_SCENARIO 不得在 production config 默认启用
CLI golden scenario 仅用于 validator / test
服务端返回 must include mode=real_provider 或 mode=test_scenario
validator 必须阻断 production POST 使用 test_scenario mode
```

### 6.3 前端第一性原则优化

普通用户视图建议收敛为：

```text
主按钮：更新只读策略结果
主状态：已是最新 / 正在更新 / 数据暂不可用 / 更新成功 / 更新失败
一句解释：成功后展示最新只读策略；失败或没数据时保留旧结果
```

工程诊断折叠展示：

```text
provider readiness
run registry
latest pointer
model_strategy_availability_matrix
failure_reasons
```

文案修正：

```text
GET only -> 只读展示 / 受控更新
更新 latest -> 刷新页面数据
更新 registry -> 查看诊断记录
更新 readiness -> 检查数据就绪
```

### 6.4 前端运行时验收

Phase V3 必须提供 Playwright 或等价 E2E artifact，覆盖：

```text
already_latest：按钮置灰，提示已是最新
running：按钮置灰，显示 run_id
triggerable：点击只产生一个允许 POST
no_data：提示数据暂不可用，旧结果保留
success：提示成功并刷新 latest readonly result
failed：提示失败原因，旧结果保留
```

network audit 必须证明：

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

## 7. Phase V3 验收门槛

Phase V3 通过后，才可以再次判断 Phase V 是否收尾。最低门槛：

```text
真实 provider reader 已接入生产 POST 默认路径
test scenario 与 production real mode 硬隔离
真实 no_new_data / partial / provider_failed / all_ready 样本至少各一例
all_ready 且 U-chain validators 全通过才更新 readonly latest
非 ready / failed / no_data / U-chain failed 保留 previous latest
前端主路径简单、准确、实用、清晰
前端运行时 network audit 通过
无 provider accepted latest / qlib accepted latest / monitor / broker / orders / Agent 越界
```

建议下一份执行报告命名：

```text
docs/tw_modular_daily_update_productization/PHASEV3_REAL_PROVIDER_READER_AND_FRONTEND_E2E_EXECUTION_REPORT_CN.md
```
