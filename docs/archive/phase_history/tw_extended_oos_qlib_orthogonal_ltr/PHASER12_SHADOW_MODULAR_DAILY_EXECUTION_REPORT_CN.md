# Phase R12 Shadow Modular Daily Runner 执行报告

生成日期：2026-06-16

## 1. 执行范围

本阶段根据：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER12_R16_READONLY_PRODUCTIZATION_FULL_CHAIN_WORK_CN.md
```

仅执行 R12：

```text
Shadow Modular Daily Runner
```

R12 目标是新增独立 shadow runner，验证当前 modular artifact 链路可在“日更形态”下生成隔离只读产物。

R12 不做：

- readonly publish artifact writer；
- readonly latest pointer；
- API 接入；
- 前端接入；
- daily orchestrator 接入；
- provider publish；
- provider accepted latest 切换；
- monitor / broker / quick-trade / order；
- 训练、调参、score recompute。

## 2. 修改文件

新增：

```text
scripts/run_tw_modular_shadow_daily.py
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER12_SHADOW_MODULAR_DAILY_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER12_SHADOW_MODULAR_DAILY_REVIEW_HANDOFF_CN.md
```

未修改：

```text
frontend/
backend_api_python/
src/api/
scripts/run_daily_tw_stock_auto_update.py
scripts/run_extended_oos_formal_replay_matrix.py
data_tw/artifacts/publish/
```

## 3. Runner 输入

R12 runner 只读取：

```text
configs/tw_modular_registry.yaml
configs/tw_modular_replay_matrix.yaml
data_tw/artifacts/signals/*/manifest.json
data_tw/artifacts/full_rank/*/manifest.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
configs/strategy_dependencies/*.yaml
```

其中 signal/full-rank manifest 来自 R10 replay manifest 引用。

## 4. 新增 Shadow Artifact

生成目录：

```text
data_tw/artifacts/shadow_modular_daily/2026-06-16/
```

生成文件：

```text
manifest.json
model_signal_manifest.json
full_rank_manifest.json
strategy_dependency_snapshot.yaml
replay_result_manifest.json
validation_report.json
forbidden_scope_audit.json
checksum_manifest.json
shadow_summary.json
```

主 manifest：

```text
data_tw/artifacts/shadow_modular_daily/2026-06-16/manifest.json
```

## 5. Runner 行为

`scripts/run_tw_modular_shadow_daily.py` 执行以下只读 shadow 动作：

1. 读取 registry、replay config、R10 ReplayResult manifest；
2. 从 ReplayResult manifest 收集 5 个 ModelSignalArtifact manifest；
3. 从 ReplayResult manifest 收集 5 个 model 对应的 FullRankArtifact manifest；
4. 快照 strategy dependency 配置；
5. 运行 registry / model signal / full rank / replay result validator；
6. 生成 forbidden scope audit；
7. 生成 checksum manifest；
8. 写入隔离 shadow 目录。

runner 不读取真实券商持仓，不生成订单，不生成 target position，不修改 publish/latest/provider/daily/frontend/API。

## 6. 执行命令与结果

### 6.1 Python 编译检查

```bash
python -m py_compile scripts/run_tw_modular_shadow_daily.py
```

结果：

```text
pass
```

说明：普通 sandbox 多次出现 `bwrap: loopback: Failed RTM_NEWADDR`，因此 Python 验证命令使用升级权限执行。

### 6.2 R12 Shadow Runner

```bash
python scripts/run_tw_modular_shadow_daily.py --asof 2026-06-16 --json
```

结果：

```json
{
  "ok": true,
  "asof": "2026-06-16",
  "out_dir": "data_tw/artifacts/shadow_modular_daily/2026-06-16",
  "manifest": "data_tw/artifacts/shadow_modular_daily/2026-06-16/manifest.json",
  "gate": {
    "all_validators_pass": true,
    "forbidden_scope_audit_status": "pass",
    "artifact_output_under_shadow_dir_only": true,
    "no_frontend_change": true,
    "no_api_change": true,
    "no_daily_orchestrator_change": true,
    "no_provider_publish": true,
    "no_accepted_latest_switch": true,
    "no_broker_order": true
  }
}
```

### 6.3 Modular Contract Regression

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

### 6.4 R12 相关单元测试

命令：python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py

结果：13 passed

### 6.5 全量 pytest

命令：python -m pytest

结果：failed during collection

失败原因：ModuleNotFoundError: No module named ccxt

失败位置：

- backend/tests/test_crypto_live_kline_scope.py
- backend/tests/test_crypto_timeframe_resample.py

结论：全量 pytest 被当前环境缺失 ccxt 阻断，发生在 crypto backend 测试收集阶段；该失败与 R12 shadow runner 无关。R12 相关 modular contract 单测已单独通过。

## 7. Validator 结果

R12 `validation_report.json` 记录：

```text
registry_validation.ok: true
replay_result_validation.ok: true
model_signal_validation: pass / skipped only
full_rank_validation: pass
all_validators_pass: true
```

`sector_extension_analysis_smoke` dependency 仅适用于 R7 extension smoke artifact，因此对 R12 正式 replay 中的 5 个 signal artifact 记录为 `skipped`，与既有 modular contract regression 逻辑一致。

## 8. Forbidden Scope Audit

R12 `forbidden_scope_audit.json` 记录：

```text
status: pass
no_frontend_change: true
no_api_change: true
no_daily_orchestrator_change: true
no_provider_publish: true
no_accepted_latest_switch: true
no_broker_order: true
artifact_output_under_shadow_dir_only: true
```

审计路径：

```text
frontend
frontend/src/views/tw-stock-monitor/index.vue
backend_api_python
src/api
scripts/run_daily_tw_stock_auto_update.py
scripts/run_extended_oos_formal_replay_matrix.py
data_tw/artifacts/publish
```

均无 tracked diff。

补充说明：仓库中已有 unrelated tracked diff `README.md` 包含 `broker` 字样，R12 runner 将该关键词发现记录为 informational，不作为 R12 gate 失败依据；R12 gate 以禁止路径、shadow 输出隔离、provider/latest/交易标志为准。

## 9. R12 Gate

| Gate | 结果 |
| --- | --- |
| all_validators_pass | pass |
| forbidden_scope_audit.status == pass | pass |
| artifact_output_under_shadow_dir_only | pass |
| no_frontend_change | pass |
| no_api_change | pass |
| no_daily_orchestrator_change | pass |
| no_provider_publish | pass |
| no_accepted_latest_switch | pass |
| no_broker_order | pass |

R12 gate 通过。

## 10. 边界确认

R12 未执行：

- 训练；
- 调参；
- score recompute；
- replay recompute；
- publish artifact writer；
- readonly latest pointer；
- API wrapper；
- frontend change；
- daily orchestrator change；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker / quick-trade / order。

R12 未修改：

- R1 canonical signals；
- R9 FullRankArtifact；
- R10 windowed baseline artifact；
- R10 modular replay result；
- 前端；
- 后端 API；
- 日更脚本；
- 默认策略。

## 11. 结论

R12 已完成。

当前结论：

```text
shadow runner pass
shadow artifacts generated under isolated shadow directory
validators pass
forbidden scope audit pass
production/API/frontend/daily/provider/latest/trading integration remains untouched
```

建议审查者审查通过后，才进入 R13 readonly publish artifact contract / writer / validator。
