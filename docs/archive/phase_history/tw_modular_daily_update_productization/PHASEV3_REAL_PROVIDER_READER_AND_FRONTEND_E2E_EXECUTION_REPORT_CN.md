# Phase V3 Real Provider Reader 与 Frontend E2E 执行报告

生成时间：2026-06-17

对应工作文档：`docs/tw_modular_daily_update_productization/PHASEV2R_REVIEW_AND_PHASEV3_WORK_CN.md`

## 0. 执行结论

Phase V3 已完成静态修复与本地验证：

1. provider staging runner 默认改为 real_provider mode。
2. 生产默认 orchestrator 不再依赖测试 scenario 注入。
3. 真实本地产物读取会正确给出 `partial_data_pending` / `no_new_data`，并保留 previous readonly latest。
4. test-scenario 仅在显式 `--test-mode` 下生效，golden/validator 可复跑。
5. 前端只读日更按钮闭环仍可用，唯一受控 POST 保持不变。
6. 前端文案已收敛为“只读展示 / 受控更新 / 刷新页面数据 / 查看诊断记录 / 检查数据就绪”。

本轮仍未触发 provider publish、provider/qlib accepted latest、monitor、broker、quick-trade、orders 或 Agent 修改。

## 1. Real Provider Reader

`scripts/pull_tw_provider_staging_data.py` 现在默认以 `--mode real_provider` 读取本地真实产物并判定状态，读取来源包括：

```text
data_tw/self_contained_demo/normalized
data_tw/experiments/decision_orthogonal/phase0d_pit_clean
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/phaseo2_summary.json
data_tw/artifacts/signals/*/r1_legacy_signal_adapter_20260616/manifest.json
```

默认 real_provider 结果示例：

```text
yahoo_daily_price -> no_new_data (latest 2026-03-27 < target_asof 2026-06-10)
finmind_daily_price -> no_new_data
finmind_institutional_flow -> no_new_data (latest 2025-09-30 < target_asof 2026-06-10)
finmind_margin_short -> no_new_data
orthogonal_o2_features -> ready (latest 2026-06-10)
existing_signal_manifest -> ready
```

因此 V3 正确返回：

```text
partial_data_pending
```

并保留 previous readonly latest，不进入 U 链。

## 2. 生产 / 测试隔离

生产默认 orchestrator：

```text
python scripts/run_tw_real_provider_daily_readonly_update.py --run-id phasev3_real_provider_default_codex_v1 ...
```

结果：

```text
status=partial_data_pending
gate_status=partial_data_pending
readonly_latest_updated=false
u_chain_started=false
```

显式测试模式：

```text
python scripts/run_tw_real_provider_daily_readonly_update.py --test-mode --scenario manual_trigger_success ...
```

结果仍可通过，供 validator/golden 使用。

## 3. 前端闭环

V2R 已接入的前端主按钮与状态仍可用：

```text
更新 readiness
更新只读策略结果
已是最新 / 正在更新 / 可更新 / 最新数据暂不可用 / 更新成功 / 更新失败
```

前端 POST 只发送 `idempotency_key`，不再发送 `scenario`。

## 4. 验证结果

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
python scripts/validate_tw_real_provider_daily_readonly_update.py --artifact-path data_tw/artifacts/real_provider_daily_update_runs/phasev3_real_provider_default_codex_v1/run_registry.json --json
ok=true
status=passed
run_status=partial_data_pending
```

```text
python -m py_compile scripts/pull_tw_provider_staging_data.py scripts/run_tw_real_provider_daily_readonly_update.py scripts/validate_tw_real_provider_daily_readonly_update.py backend/app/services/readonly_daily_update_runs.py backend/app/routes/readonly_daily_update_runs.py
passed
```

## 5. 仍未完成项

V3 让真实本地产物读取和生产/test 隔离成立，但仍没有外网 Yahoo / FinMind 拉取，也没有前端运行时 network audit artifact。若要判断 Phase V 最终收尾，还需要补真实网络拉取与运行时 E2E 审计。


## 6. 运行时 E2E 审计

```text
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8011 TW_STOCK_API_BASE_URL=http://127.0.0.1:5000 node frontend/tests/e2e/tw-stock-real-provider-daily-update-e2e.mjs
ok=true
trigger_post_count=1
forbidden_request_count=0
console_error_count=0
page_error_count=0
```

审计结果表明：只产生 1 次允许的手动 POST，未见 provider publish / refresh / accepted latest、monitor config write、monitor scan、monitor alerts write、broker / quick-trade / orders 请求。
