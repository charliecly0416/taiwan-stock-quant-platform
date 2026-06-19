# Phase V4 外网 Provider Reader 执行报告

生成时间：2026-06-17

对应工作文档：`docs/tw_modular_daily_update_productization/PHASEV3_REVIEW_AND_PHASEV4_WORK_CN.md`

## 0. 执行结论

Phase V4 已完成外网 provider reader 接入与审计闭环。

本轮实现了：

1. 外网 Yahoo / FinMind provider reader。
2. provider staging 仍只写入 `data_tw/artifacts/provider_staging/<run_id>/`。
3. provider network audit 真实记录了外网请求、主机和重试。
4. DataReadinessGate 可正确判定 `provider_failed`，并阻止 U 链。
5. 只读安全边界保持不变：未触发 provider publish、accepted latest 切换、monitor/broker/orders/Agent 改动。

## 1. 外网抓取

新增脚本：

- `scripts/fetch_tw_provider_external_data.py`

抓取范围：

- Yahoo `query1.finance.yahoo.com`
- FinMind `api.finmindtrade.com`

抓取模式：

- staging-only
- retry/backoff 有审计
- 不写 provider publish / accepted latest / qlib latest

## 2. Smoke 运行

命令：

```text
python scripts/pull_tw_provider_staging_data.py --run-id phasev4_external_provider_smoke_codex_v1 --mode external_provider_reader --target-asof 2026-06-17 --decision-for 2026-06-18 --decision-cutoff 2026-06-18T23:59:59+00:00 --external-start 2026-06-10 --external-end 2026-06-17 --symbol 2330 --symbol 2317 --symbol 2454 --max-symbols 3 --timeout 20 --retries 2 --retry-sleep-seconds 0.5 --json
```

结果摘要：

```text
mode=external_provider_reader
source_count=6
```

provider staging validator：

```text
ok=true
status=passed
```

DataReadinessGate：

```text
gate_status=provider_failed
```

## 3. 外网网络审计

Smoke 审计结果：

```text
request_count=15
actual_external_request_count=15
successful_request_count=9
failed_request_count=6
unauthorized_request_count=0
```

允许主机：

- `api.finmindtrade.com`
- `query1.finance.yahoo.com`

请求来源：

- `yahoo_daily_price`
- `finmind_daily_price`
- `finmind_institutional_flow`
- `finmind_margin_short`

## 4. 生产默认 orchestrator

命令：

```text
python scripts/run_tw_real_provider_daily_readonly_update.py --run-id phasev4_external_provider_orchestrator_codex_v1 --actor frontend_manual_trigger --idempotency-key phasev4_external_provider_orchestrator_codex_v1 --target-asof 2026-06-17 --decision-for 2026-06-18 --decision-cutoff 2026-06-18T23:59:59+00:00 --json
```

结果摘要：

```text
status=provider_failed
gate_status=provider_failed
mode=external_provider_reader
provider_reader_mode=external_provider_reader
readonly_latest_updated=false
u_chain_started=false
```

## 5. 只读边界

保持不变：

- `provider_publish_triggered=false`
- `provider_refresh_official_path_triggered=false`
- `accepted_latest_switched=false`
- `qlib_accepted_latest_switched=false`
- `monitor_config_written=false`
- `monitor_scan_triggered=false`
- `alerts_written=false`
- `broker_connected=false`
- `quick_trade_triggered=false`
- `orders_created_or_sent=false`
- `agent_prompt_or_tool_modified=false`

## 6. 产物路径

- `data_tw/artifacts/provider_staging/phasev4_external_provider_smoke_codex_v1/`
- `data_tw/artifacts/provider_staging/phasev4_external_provider_orchestrator_codex_v1_provider_staging/`
- `data_tw/artifacts/real_provider_daily_update_runs/phasev4_external_provider_orchestrator_codex_v1/run_registry.json`

## 7. 结论

V4 已把 provider reader 升级为真实外网拉取，并补齐 provider network audit。当前真实运行结果显示 Yahoo 路径失败、FinMind 路径成功，系统正确停留在 `provider_failed`，没有更新 readonly latest，也没有进入 U 链。
