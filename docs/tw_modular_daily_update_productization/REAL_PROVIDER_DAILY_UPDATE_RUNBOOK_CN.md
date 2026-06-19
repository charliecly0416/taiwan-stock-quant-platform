# Real Provider Daily Update Runbook

生成时间：2026-06-17

## 运行入口

受控手动/自动入口：

```text
python scripts/run_tw_real_provider_daily_readonly_update.py --scenario manual_trigger_success --json
```

前端唯一允许的手动触发 POST：

```text
POST /api/tw-stock/readonly-daily-update-runs
```

只读展示接口：

```text
GET /api/tw-stock/provider-readiness/latest
GET /api/tw-stock/readonly-daily-update-runs
GET /api/tw-stock/readonly-daily-update-runs/<run_id>
GET /api/tw-stock/readonly-daily-latest
```

## 状态处理

```text
all_required_ready -> 运行 U 链，通过后更新 readonly latest
already_latest -> noop，保留 latest
running -> 返回已有 run，禁止并发
no_new_data / partial_data_pending / provider_failed / validator_failed / deadline_missed_keep_previous_latest -> 不进入 U 链，保留 previous latest
u_chain_validator_failed -> gate ready 但 U 链失败，保留 previous latest
```

## 安全边界

本链路不得触发：provider publish、provider accepted latest、qlib accepted latest、monitor config/scan/alerts、broker、quick-trade、orders、Agent prompt/tool/action。

模型/策略切换只读取已有 `model_strategy_availability_matrix.json` 和 readiness artifact，不重新抓 Yahoo / FinMind / orthogonal。

## 验证命令

```text
python scripts/validate_tw_real_provider_daily_readonly_update.py --run-golden --json
python scripts/validate_tw_real_provider_daily_readonly_update.py --static-api --json
python scripts/validate_tw_real_provider_daily_readonly_update.py --artifact-path data_tw/artifacts/real_provider_daily_update_runs/<run_id>/run_registry.json --json
```
