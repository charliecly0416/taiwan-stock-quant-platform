# Phase R16 审查与只读产品化链路验收

生成日期：2026-06-16

## 1. 审查结论

R16 审查通过。

R16 已将 readonly strategy snapshot publish 接入 daily orchestrator 末端，并满足只读产品化边界：

- `ENABLE_TW_READONLY_STRATEGY_SNAPSHOT_PUBLISH` 默认关闭；
- `TW_READONLY_STRATEGY_SNAPSHOT_DRY_RUN` 默认开启；
- 开关关闭时不调用 writer；
- writer 始终以 `--no-latest` 调用；
- manifest validator 通过后才允许写 readonly latest pointer；
- dry-run 模式不写 latest pointer；
- readonly snapshot 失败被隔离为 warning/audit，不改变 daily 主流程成功状态；
- 只允许更新 `data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json`；
- 未新增 provider accepted latest switch、broker、quick-trade、order、monitor 写入、target position、target weight；
- 总合同回归恢复并保持 `ok=true`。

## 2. 审查对象

R16 handoff：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER16_DAILY_READONLY_INTEGRATION_REVIEW_HANDOFF_CN.md
```

R16 执行报告：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER16_DAILY_READONLY_INTEGRATION_EXECUTION_REPORT_CN.md
```

修改文件：

```text
scripts/run_daily_tw_stock_auto_update.py
scripts/run_tw_modular_contract_regression.py
tests/unit/test_tw_daily_readonly_snapshot_integration.py
tests/unit/test_validate_tw_modular_artifact_contract.py
```

## 3. 复核结果

### 3.1 开关默认安全

`run_readonly_strategy_snapshot_publish()` 中：

```text
ENABLE_TW_READONLY_STRATEGY_SNAPSHOT_PUBLISH default=false
TW_READONLY_STRATEGY_SNAPSHOT_DRY_RUN default=true
```

默认结果：

```text
enabled=false
attempted=false
ok=true
dry_run=true
latest_updated=false
```

开关关闭时不会调用 writer。

### 3.2 调用顺序正确

R16 调用顺序：

```text
publish --no-latest --json
validate --manifest <manifest> --json
if not dry_run:
  write readonly latest pointer
  validate --latest --json
```

关键点：

- writer 不直接更新 latest；
- manifest validator 失败时不会写 latest；
- dry-run 默认不写 latest；
- latest pointer 只写 readonly snapshot namespace。

### 3.3 Daily 主流程失败隔离

接入点在 daily update 成功后：

```text
clear_pending_asof(asof)
readonly_snapshot = run_readonly_strategy_snapshot_publish(...)
job["readonly_snapshot"] = readonly_snapshot
job status remains daily_auto_update_passed
```

失败时：

```text
job["readonly_snapshot_warning"] = ...
```

判断：readonly snapshot publish/validate 失败不会导致 data update 主流程失败。

### 3.4 Forbidden-scope audit 通过

`forbidden_scope_audit.csv` 当前关键行：

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

判断：R16 对 daily 脚本是内容级放行，不是无条件路径白名单。其它禁区仍保持 hard fail。

### 3.5 只读 latest pointer 边界正确

R16 只允许写：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
```

latest pointer 写入内容包含：

```text
readonly_only=true
production_trade_enabled=false
not_provider_accepted_latest=true
not_trade_target_latest=true
```

未发现 provider accepted latest、qlib accepted latest 或 trade target latest 写入。

### 3.6 安全关键词复核

新增 R16 daily block 未发现：

```text
quick-trade
broker API
order_action
target_position
target_weight
monitor scan/config/alerts write helper
provider_publish
accepted_latest_switch
training / score recompute / replay recompute
```

`run_daily_tw_stock_auto_update.py` 既有 provider publish / accepted latest 逻辑仍存在，但不是 R16 新增逻辑；R16 readonly snapshot 调用在既有主流程成功后执行，并不改变 provider accepted latest 行为。

## 4. 验证命令

### 4.1 Python 编译

复核命令：

```bash
python -m py_compile scripts/run_daily_tw_stock_auto_update.py scripts/publish_tw_modular_readonly_snapshot.py scripts/validate_tw_modular_readonly_snapshot.py scripts/run_tw_modular_contract_regression.py
```

结果：

```text
pass
```

### 4.2 R16 单元测试

复核命令：

```bash
python -m pytest tests/unit/test_tw_daily_readonly_snapshot_integration.py
```

结果：

```text
6 passed
```

覆盖：

- 开关关闭不调用 writer；
- dry-run 成功不写 latest；
- 非 dry-run 在 manifest validator 通过后写 latest；
- writer 失败隔离；
- manifest validator 失败不写 latest；
- daily integration block 静态 forbidden scan。

### 4.3 总合同回归

复核命令：

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

### 4.4 Readonly snapshot validator

复核命令：

```bash
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

结果：

```text
ok=true
checksum_ok=pass
latest_pointer_points_to_readonly_snapshot_only=pass
no_unsafe_field_names=pass
```

### 4.5 其它回归

复核命令：

```bash
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
PYTHONPATH=backend python -m pytest backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py
cd frontend && node tests/unit/tw-stock-readonly-strategy-snapshot-check.mjs
```

结果：

```text
15 passed
4 passed
[readonly-strategy-snapshot-check] ok
```

说明：前端静态检查输出中仍有 `/bin/sh: 2: source: not found` 的 shell 环境提示，但命令退出码为 0，不影响判断。

## 5. 非阻塞建议

### P2：latest pointer 写入后校验失败时应支持原子写或回滚

当前实现流程是：

```text
write latest pointer
validate --latest
```

若 latest validator 失败，R16 会记录 `ok=false` 和错误，但不会自动回滚已经写入的 latest pointer。

当前不阻塞通过，原因：

- writer 始终 `--no-latest`；
- 写 latest 前已经通过 manifest validator；
- latest pointer 内容固定、只读、非 provider accepted latest；
- R16 默认 dry-run，不写 latest。

后续生产强化建议：

```text
写 latest.tmp
validate latest.tmp or validate by explicit path
atomic replace latest.json
失败则保留旧 latest.json
```

或在写前保存旧 latest，`--latest` 失败时回滚。

### P2：latest validator 应同时检查 returncode 与 JSON ok

当前 manifest validator 检查了：

```text
validate_result.ok && validate_payload.ok
```

latest validator 分支主要检查：

```text
latest_validate_result.ok
```

建议后续补强为：

```text
latest_validate_result.ok && latest_validator_payload.ok
```

并增加单测覆盖“进程退出 0 但 JSON ok=false”的异常情况。

## 6. 最终验收状态

R12-R16 readonly productization chain 当前闭环：

```text
R12/R12R shadow modular daily artifact
  -> R13 readonly publish snapshot
  -> R14 readonly API
  -> R15 frontend readonly display
  -> R15R total regression scope repair
  -> R16 daily readonly snapshot integration
```

当前最终 gate：

```text
readonly snapshot validator: ok=true
contract regression: ok=true
R16 unit tests: pass
backend readonly API tests: pass
frontend readonly static check: pass
no provider accepted latest change from R16
no broker / quick-trade / order
no monitor write
no target position / target weight
```

## 7. 最终结论

R16 通过。

Readonly productization 全链路可以视为本轮阶段性验收通过。后续若进入真实生产运行强化，建议先处理 latest pointer 原子写/回滚、latest validator JSON ok 检查、以及真实 daily dry-run/非 dry-run smoke。
