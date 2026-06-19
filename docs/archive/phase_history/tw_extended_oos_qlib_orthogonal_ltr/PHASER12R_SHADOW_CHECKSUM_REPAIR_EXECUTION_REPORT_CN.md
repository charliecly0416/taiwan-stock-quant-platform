# Phase R12R Shadow Checksum Repair 执行报告

生成日期：2026-06-16

## 1. 执行范围

本阶段根据：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER12_REVIEW_AND_R12R_REPAIR_WORK_CN.md
```

执行 R12R：

```text
Shadow checksum manifest repair
```

R12R 只修复 R12 shadow artifact 的 checksum manifest 完整性问题。

## 2. 修改文件

修改：

```text
scripts/run_tw_modular_shadow_daily.py
data_tw/artifacts/shadow_modular_daily/2026-06-16/
```

新增：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER12R_SHADOW_CHECKSUM_REPAIR_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER12R_SHADOW_CHECKSUM_REPAIR_REVIEW_HANDOFF_CN.md
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

## 3. 修复内容

R12R 修复了两个问题：

1. `checksum_manifest.json` 不再包含自身 hash；
2. `checksum_manifest.json` 补齐关键 shadow 输出：
   - `manifest.json`
   - `shadow_summary.json`

同时新增：

```text
manifest.gate.checksum_manifest_valid: true
shadow_summary.checksum_manifest_valid: true
checksum_manifest.validation.ok: true
```

## 4. Checksum 设计

当前 checksum manifest 明确采用 detached 方案：

```text
checksum_manifest.json 不校验自身
checksum_manifest.json 校验 source inputs + non-checksum shadow outputs
```

`checksum_manifest.json` 包含：

- registry；
- replay config；
- replay manifest；
- signal manifests；
- full-rank manifests；
- strategy dependency yaml；
- `model_signal_manifest.json`；
- `full_rank_manifest.json`；
- `strategy_dependency_snapshot.yaml`；
- `replay_result_manifest.json`；
- `validation_report.json`；
- `forbidden_scope_audit.json`；
- `shadow_summary.json`；
- `manifest.json`。

`checksum_manifest.json` 不包含：

```text
data_tw/artifacts/shadow_modular_daily/2026-06-16/checksum_manifest.json
```

## 5. 执行命令与结果

### 5.1 Python 编译检查

```bash
python -m py_compile scripts/run_tw_modular_shadow_daily.py
```

结果：

```text
pass
```

### 5.2 重新生成 R12 Shadow Artifact

```bash
python scripts/run_tw_modular_shadow_daily.py --asof 2026-06-16 --json
```

结果：

```json
{
  "ok": true,
  "gate": {
    "all_validators_pass": true,
    "forbidden_scope_audit_status": "pass",
    "artifact_output_under_shadow_dir_only": true,
    "no_frontend_change": true,
    "no_api_change": true,
    "no_daily_orchestrator_change": true,
    "no_provider_publish": true,
    "no_accepted_latest_switch": true,
    "no_broker_order": true,
    "checksum_manifest_valid": true
  }
}
```

### 5.3 Checksum 自校验

重算 `checksum_manifest.json` 中所有文件的 sha256：

```json
{
  "checksum_manifest_included": false,
  "manifest_included": true,
  "shadow_summary_included": true,
  "file_count": 24,
  "all_hashes_match": true,
  "validation": {
    "ok": true,
    "checked_file_count": 24
  },
  "missing_or_mismatch": []
}
```

### 5.4 Modular Contract Regression

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

### 5.5 R12 相关单元测试

```bash
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

结果：

```text
13 passed
```

说明：普通 sandbox 仍存在 `bwrap: loopback: Failed RTM_NEWADDR`，Python 命令使用升级权限执行。

## 6. R12R Gate

| Gate | 结果 |
| --- | --- |
| checksum_manifest excludes itself | pass |
| checksum_manifest includes manifest.json | pass |
| checksum_manifest includes shadow_summary.json | pass |
| all checksum hashes match current files | pass |
| manifest.gate.checksum_manifest_valid | pass |
| shadow_summary.checksum_manifest_valid | pass |
| R12 shadow runner ok | pass |
| modular contract regression | pass |
| R12 related unit tests | pass |

R12R gate 通过。

## 7. 禁止事项确认

R12R 未执行：

- 训练；
- 调参；
- score recompute；
- replay recompute；
- readonly publish writer；
- readonly latest pointer；
- API wrapper；
- frontend change；
- daily orchestrator change；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker / quick-trade / order。

R12R 未修改：

- R1 canonical signals；
- R9 FullRankArtifact；
- R10 ReplayResultArtifact；
- 默认策略；
- 前端；
- 后端 API；
- 日更脚本；
- publish artifact。

## 8. 结论

R12R 已完成。

当前结论：

```text
checksum manifest self-reference removed
manifest.json and shadow_summary.json are included
all checksum entries validate against current files
checksum_manifest_valid gate is present and true
R12 shadow remains isolated and readonly
```

建议审查者审查通过后，才进入 R13 readonly publish artifact contract / writer / validator。
