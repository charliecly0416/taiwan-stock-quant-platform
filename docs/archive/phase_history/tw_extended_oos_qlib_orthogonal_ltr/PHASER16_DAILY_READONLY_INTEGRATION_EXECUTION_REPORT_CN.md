# Phase R16 日更只读策略快照集成执行报告

生成日期：2026-06-16

## 1. 执行范围

本轮按照 `PHASER15R_REVIEW_AND_R16_WORK_CN.md` 执行 R16：将 readonly strategy snapshot publish 接入 daily orchestrator 末端。

R16 实际修改/新增文件：

```text
scripts/run_daily_tw_stock_auto_update.py
tests/unit/test_tw_daily_readonly_snapshot_integration.py
scripts/run_tw_modular_contract_regression.py
tests/unit/test_validate_tw_modular_artifact_contract.py
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER16_DAILY_READONLY_INTEGRATION_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER16_DAILY_READONLY_INTEGRATION_REVIEW_HANDOFF_CN.md
```

说明：R16 工作文档允许修改 daily orchestrator，但 R15R 的总合同回归仍把 `scripts/run_daily_tw_stock_auto_update.py` 作为路径级 forbidden hard fail。为了满足 R16 要求的“总合同回归 ok=true”，本轮同步把 contract regression 中该路径改为 R16 内容级审计，只放行当前 readonly snapshot daily integration diff，并保留 forbidden pattern 检查。

## 2. 开关与默认值

新增开关：

```text
ENABLE_TW_READONLY_STRATEGY_SNAPSHOT_PUBLISH
```

默认值：`false`。

新增 dry-run 开关：

```text
TW_READONLY_STRATEGY_SNAPSHOT_DRY_RUN
```

默认值：`true`。

默认行为：不开启 writer；即使开启 publish 开关，默认 dry-run 下也不会写 `data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json`。

## 3. Daily 调用点

调用点位于 `scripts/run_daily_tw_stock_auto_update.py` 主流程末端：

```text
clear_pending_asof(asof)
run_readonly_strategy_snapshot_publish(asof=asof, job_dir=job_dir)
job status = daily_auto_update_passed
```

因此 R16 readonly snapshot 只在 daily 数据更新主流程已经完成之后执行。主流程中 FinMind、Yahoo/Scrapling、provider publish、accepted latest 既有逻辑未改动。

## 4. Readonly Publish 调用命令

R16 只调用以下两个脚本：

```text
scripts/publish_tw_modular_readonly_snapshot.py
scripts/validate_tw_modular_readonly_snapshot.py
```

writer 调用参数：

```text
python scripts/publish_tw_modular_readonly_snapshot.py --out-root data_tw/artifacts/publish/readonly_strategy_snapshot --no-latest --json
```

关键点：writer 始终带 `--no-latest`，避免 writer 直接更新 latest pointer。R16 在 writer 成功且 manifest validator 成功后，才由 daily orchestrator 写 readonly latest pointer。

validator 调用：

```text
python scripts/validate_tw_modular_readonly_snapshot.py --manifest <manifest> --json
```

非 dry-run 且 manifest validator 通过后，才写：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
```

写入后再执行：

```text
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

## 5. 失败隔离

`run_readonly_strategy_snapshot_publish()` 返回结构包含：

```text
enabled
attempted
ok
dry_run
manifest
latest_updated
validator_ok
error
```

失败隔离规则：

- publish 开关关闭：`attempted=false`，不调用 writer；
- writer 失败：`ok=false`，不调用 validator，不写 latest；
- manifest validator 失败：`ok=false`，不写 latest；
- latest validator 失败：记录 `ok=false` 与错误，但 daily 主流程仍返回 `daily_auto_update_passed`；
- daily job 中记录 `readonly_snapshot`，失败时额外记录 `readonly_snapshot_warning`；
- 若实际 attempted，则写只读集成审计：`data_tw/artifacts/publish/readonly_strategy_snapshot/daily_integration_audit.json`。

R16 readonly snapshot 失败不会导致 daily data update 主流程失败。

## 6. Latest Pointer 更新条件

R16 只允许更新 readonly snapshot latest pointer：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
```

更新条件：

1. `ENABLE_TW_READONLY_STRATEGY_SNAPSHOT_PUBLISH=true`；
2. `TW_READONLY_STRATEGY_SNAPSHOT_DRY_RUN=false`；
3. writer 命令 returncode ok；
4. writer JSON 输出 `ok=true` 且包含 manifest；
5. `validate_tw_modular_readonly_snapshot.py --manifest <manifest> --json` 返回 ok；
6. latest pointer 写入后再由 `--latest --json` 校验。

latest pointer 内容明确标注：

```text
readonly_only=true
production_trade_enabled=false
not_provider_accepted_latest=true
not_trade_target_latest=true
```

## 7. Forbidden Scope Audit

总合同回归输出：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/forbidden_scope_audit.csv
```

关键结果：

```text
frontend/src/views/tw-stock-monitor/index.vue:
  audit_mode=r15_readonly_frontend_content_audit
  status=pass

scripts/run_daily_tw_stock_auto_update.py:
  audit_mode=r16_daily_readonly_content_audit
  status=pass
  unit_test_exists=True

scripts/run_extended_oos_formal_replay_matrix.py: pass
backend_api_python: pass
src/api: pass
```

R16 daily 内容级审计要求 readonly markers 存在，并扫描 added lines 中的 broker、quick-trade、order、target position/weight、monitor write、training、score/replay recompute、accepted latest switch 等 forbidden pattern。

## 8. 验证结果

已执行验证：

```bash
python -m py_compile scripts/run_daily_tw_stock_auto_update.py scripts/publish_tw_modular_readonly_snapshot.py scripts/validate_tw_modular_readonly_snapshot.py scripts/run_tw_modular_contract_regression.py
```

结果：pass。

```bash
python -m pytest tests/unit/test_tw_daily_readonly_snapshot_integration.py
```

结果：`6 passed`。

```bash
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

结果：`15 passed`。

```bash
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

结果：`ok=true`，21 项 checks 全部 pass。

```bash
python scripts/run_tw_modular_contract_regression.py --json
```

结果：

```text
ok=true
signal_manifest_count=5
strategy_dependency_count=6
full_rank_artifact_count=2
signal_validation_rows=35
full_rank_validation_rows=5
```

```bash
python -m pytest backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py
```

结果：`4 passed`。

```bash
cd frontend && node tests/unit/tw-stock-readonly-strategy-snapshot-check.mjs
```

结果：退出码 0，输出 `[readonly-strategy-snapshot-check] ok`。命令同时出现 `/bin/sh: 2: source: not found` 的 shell 环境提示，但不影响该静态检查通过。

## 9. 安全边界确认

R16 本轮未执行训练、调参、score recompute、replay recompute。

R16 本轮未修改默认模型、默认策略、R13 snapshot schema、R14 API contract、R15 frontend display。

R16 新增逻辑未新增 broker、quick-trade、order、monitor scan/config/alerts write、target position、target weight。

R16 新增 readonly latest pointer 明确不是 provider accepted latest，不是 trade target latest。

R16 未改变既有 provider accepted latest 主流程；readonly snapshot 调用发生在主流程成功之后，且失败仅记录 warning/audit。
