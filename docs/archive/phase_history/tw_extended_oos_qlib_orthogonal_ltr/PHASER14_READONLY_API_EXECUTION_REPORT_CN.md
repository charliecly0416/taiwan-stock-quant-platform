# Phase R14 Readonly API 执行报告

生成日期：2026-06-16

## 1. 执行范围

本阶段根据：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER13_REVIEW_AND_R14_WORK_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER12_R16_READONLY_PRODUCTIZATION_FULL_CHAIN_WORK_CN.md
```

执行 R14：

```text
Readonly API 接入
```

R14 只新增后端只读 API，用于读取 R13 readonly snapshot artifact。

R14 不做：

- 前端接入；
- daily orchestrator 接入；
- provider publish；
- provider accepted latest 切换；
- monitor scan / config save / alerts write；
- broker / quick-trade / order；
- 训练、调参、score recompute、replay recompute。

## 2. 修改文件

新增：

```text
backend/app/services/readonly_strategy_snapshot.py
backend/app/routes/readonly_strategy_snapshot.py
backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER14_READONLY_API_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER14_READONLY_API_REVIEW_HANDOFF_CN.md
```

修改：

```text
backend/app/routes/__init__.py
scripts/validate_tw_modular_readonly_snapshot.py
```

`scripts/validate_tw_modular_readonly_snapshot.py` 的修改是按 R13 审查建议补强 forbidden unsafe keys，新增：

```text
target_position
target-position
targetposition
```

未修改：

```text
frontend/
scripts/run_daily_tw_stock_auto_update.py
scripts/run_extended_oos_formal_replay_matrix.py
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
```

## 3. API Endpoint

新增 GET-only endpoint：

```text
GET /api/tw-stock/readonly-strategy-snapshot
GET /api/tw-stock/readonly-strategy-snapshot/<asof>
```

实现位置：

```text
backend/app/routes/readonly_strategy_snapshot.py
```

注册位置：

```text
backend/app/routes/__init__.py
```

## 4. API 数据来源

API 只读取静态 readonly artifact：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-06-16/manifest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-06-16/strategy_snapshot.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-06-16/validation_report.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-06-16/forbidden_scope_audit.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-06-16/checksum_manifest.json
```

服务实现：

```text
backend/app/services/readonly_strategy_snapshot.py
```

服务会校验：

- latest pointer 是 `readonly_strategy_snapshot_latest_pointer`；
- latest pointer 不在 readonly root 之外；
- `not_provider_accepted_latest == true`；
- `not_trade_target_latest == true`；
- manifest / snapshot 的 readonly flags；
- checksum 可复算；
- `production_trade_enabled == false`；
- `not_target_position == true`。

## 5. Response Schema

API 返回：

```text
code: 1
msg: success
data.schema_version: readonly_strategy_snapshot_api_r14_v1
data.readonly_only: true
data.not_order: true
data.no_order_action: true
data.not_target_position: true
data.not_investment_advice: true
data.production_trade_enabled: false
data.manifest
data.snapshot
data.validation
data.checksum
data.forbidden_scope_audit
data.latest_pointer
data.sources
data.no_write_guarantees
```

`no_write_guarantees` 包含：

```text
read_only_http_method: true
reads_static_readonly_snapshot_only: true
does_not_touch_provider_accepted_latest: true
does_not_touch_monitor_or_alerts: true
does_not_touch_broker_or_orders: true
```

## 6. Route Method Audit

源码中只注册：

```text
@readonly_strategy_snapshot_bp.route("/readonly-strategy-snapshot", methods=["GET"])
@readonly_strategy_snapshot_bp.route("/readonly-strategy-snapshot/<asof>", methods=["GET"])
```

测试覆盖：

```text
POST /api/tw-stock/readonly-strategy-snapshot -> 405
PUT /api/tw-stock/readonly-strategy-snapshot -> 405
PATCH /api/tw-stock/readonly-strategy-snapshot -> 405
DELETE /api/tw-stock/readonly-strategy-snapshot -> 405
POST /api/tw-stock/readonly-strategy-snapshot/2026-06-16 -> 405
PUT /api/tw-stock/readonly-strategy-snapshot/2026-06-16 -> 405
PATCH /api/tw-stock/readonly-strategy-snapshot/2026-06-16 -> 405
DELETE /api/tw-stock/readonly-strategy-snapshot/2026-06-16 -> 405
```

## 7. 执行命令与结果

### 7.1 编译检查

```bash
python -m py_compile backend/app/services/readonly_strategy_snapshot.py backend/app/routes/readonly_strategy_snapshot.py scripts/validate_tw_modular_readonly_snapshot.py
```

结果：

```text
pass
```

### 7.2 R14 API Tests

```bash
PYTHONPATH=backend python -m pytest backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py
```

结果：

```text
4 passed
```

### 7.3 R13 Snapshot Validator

```bash
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

结果：

```text
ok: true
checksum_ok: pass
latest_pointer_points_to_readonly_snapshot_only: pass
```

### 7.4 Modular Contract Regression

```bash
python scripts/run_tw_modular_contract_regression.py --json
```

结果：

```json
{
  "ok": true,
  "signal_manifest_count": 5,
  "strategy_dependency_count": 6,
  "full_rank_artifact_count": 2,
  "signal_validation_rows": 35,
  "full_rank_validation_rows": 5
}
```

### 7.5 Modular Contract Unit Tests

```bash
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

结果：

```text
13 passed
```

说明：普通 sandbox 仍存在 `bwrap: loopback: Failed RTM_NEWADDR`，Python 命令使用升级权限执行。

## 8. R14 Gate

| Gate | 结果 |
| --- | --- |
| API GET latest endpoint | pass |
| API GET asof endpoint | pass |
| POST/PUT/PATCH/DELETE blocked | pass |
| readonly response schema | pass |
| checksum status returned | pass |
| validation status returned | pass |
| provider accepted latest untouched | pass |
| monitor/broker/order untouched | pass |
| target position / target weight not output | pass |

R14 gate 通过。

## 9. 禁止事项确认

R14 未执行：

- 训练；
- 调参；
- score recompute；
- replay recompute；
- 修改 R1/R9/R10/R12/R13 artifact；
- 修改默认模型或策略；
- 前端接入；
- daily orchestrator 接入；
- provider publish；
- accepted latest 切换；
- monitor scan / config save / alerts write；
- broker / quick-trade / order。

R14 未修改：

```text
frontend/
scripts/run_daily_tw_stock_auto_update.py
scripts/run_extended_oos_formal_replay_matrix.py
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
```

## 10. 结论

R14 已完成。

当前结论：

```text
readonly API endpoint added
GET-only route tests pass
readonly response schema tests pass
readonly snapshot validator remains pass
provider accepted latest remains untouched
frontend/daily integration remains untouched
monitor/broker/order remains untouched
```

建议审查者审查通过后，才进入 R15 frontend readonly display。
