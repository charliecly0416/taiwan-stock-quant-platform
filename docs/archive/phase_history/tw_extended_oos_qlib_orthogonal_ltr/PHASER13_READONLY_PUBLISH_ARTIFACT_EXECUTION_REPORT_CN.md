# Phase R13 Readonly Publish Artifact 执行报告

生成日期：2026-06-16

## 1. 执行范围

本阶段根据：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER12R_REVIEW_AND_R13_WORK_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER12_R16_READONLY_PRODUCTIZATION_FULL_CHAIN_WORK_CN.md
```

执行 R13：

```text
Readonly Publish Artifact Contract / Writer / Validator
```

R13 只做 readonly publish artifact，不接入 API、前端或 daily orchestrator。

## 2. 修改文件

新增：

```text
docs/tw_modular_contracts/READONLY_STRATEGY_SNAPSHOT_CONTRACT_CN.md
scripts/publish_tw_modular_readonly_snapshot.py
scripts/validate_tw_modular_readonly_snapshot.py
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER13_READONLY_PUBLISH_ARTIFACT_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER13_READONLY_PUBLISH_ARTIFACT_REVIEW_HANDOFF_CN.md
```

新增 artifact：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-06-16/
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
```

未修改：

```text
frontend/
backend_api_python/
src/api/
scripts/run_daily_tw_stock_auto_update.py
scripts/run_extended_oos_formal_replay_matrix.py
```

## 3. Readonly Snapshot Contract

新增合约：

```text
docs/tw_modular_contracts/READONLY_STRATEGY_SNAPSHOT_CONTRACT_CN.md
```

合约明确：

- `readonly_strategy_snapshot` 是只读候选快照；
- `latest.json` 只属于 readonly snapshot 命名空间；
- 不得命名或实现为 provider accepted latest；
- 不得触发交易、目标仓位、broker、quick-trade、order、monitor；
- 不得接入 API / frontend / daily orchestrator。

## 4. Writer

新增 writer：

```text
scripts/publish_tw_modular_readonly_snapshot.py
```

输入：

```text
data_tw/artifacts/shadow_modular_daily/2026-06-16/manifest.json
data_tw/artifacts/signals/e4_frozen_qlib_2023_2025_ltr/r1_legacy_signal_adapter_20260616/manifest.json
data_tw/artifacts/full_rank/frozen_qlib_2018_2022_raw_oos/r9_full_rank_adapter_20260616/manifest.json
configs/strategy_dependencies/top50_exit_one_worst_sell.yaml
```

输出：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-06-16/manifest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-06-16/strategy_snapshot.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-06-16/validation_report.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-06-16/forbidden_scope_audit.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-06-16/checksum_manifest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
```

`latest.json` 内容仅指向：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-06-16/manifest.json
```

并包含：

```text
not_provider_accepted_latest: true
not_trade_target_latest: true
```

## 5. Snapshot 展示配置

R13 snapshot 使用产品化文档冻结的主展示组合：

```text
display_role: primary_readonly_candidate
model_id: e4_frozen_qlib_2023_2025_ltr
base_model_id: frozen_qlib_2018_2022
strategy_rule: top50_exit_one_worst_sell
candidate_boundary: qlib_top50
ranking_source: ltr_rerank_within_qlib_top50
is_production_trading_default: false
readonly_only: true
not_target_position: true
not_investment_advice: true
```

`strategy_snapshot.json` 包含：

- `top_candidates`；
- `exit_candidates`；
- `hold_candidates`；
- `comparison_group`；
- `hidden_diagnostic_rules`；
- readonly caveat。

这些字段均为只读候选解释，不是订单、目标仓位或投资建议。

## 6. Validator

新增 validator：

```text
scripts/validate_tw_modular_readonly_snapshot.py
```

检查项包括：

- artifact type / schema version；
- readonly flags；
- `production_trade_enabled == false`；
- `no_order_action == true`；
- `not_target_position == true`；
- `not_investment_advice == true`；
- `is_production_trading_default == false`；
- display role；
- source shadow manifest；
- qlib top50 boundary；
- LTR rerank source；
- forbidden scope audit；
- checksum；
- readonly latest pointer。

## 7. 执行命令与结果

### 7.1 编译检查

```bash
python -m py_compile scripts/publish_tw_modular_readonly_snapshot.py scripts/validate_tw_modular_readonly_snapshot.py
```

结果：

```text
pass
```

### 7.2 Publish Writer

```bash
python scripts/publish_tw_modular_readonly_snapshot.py --json
```

结果：

```json
{
  "ok": true,
  "asof": "2026-06-16",
  "out_dir": "data_tw/artifacts/publish/readonly_strategy_snapshot/2026-06-16",
  "manifest": "data_tw/artifacts/publish/readonly_strategy_snapshot/2026-06-16/manifest.json",
  "latest": "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json"
}
```

### 7.3 Validator

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

### 7.5 R12/R13 相关单元测试

```bash
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

结果：

```text
13 passed
```

说明：普通 sandbox 仍存在 `bwrap: loopback: Failed RTM_NEWADDR`，Python 命令使用升级权限执行。

## 8. R13 Gate

| Gate | 结果 |
| --- | --- |
| readonly_snapshot_validator_ok | pass |
| checksum_ok | pass |
| latest_pointer_points_to_readonly_snapshot_only | pass |
| forbidden_scope_audit.status | pass |

`manifest.json` gate：

```text
readonly_snapshot_validator_ok: true
checksum_ok: true
latest_pointer_points_to_readonly_snapshot_only: true
forbidden_scope_audit_status: pass
```

R13 gate 通过。

## 9. 禁止事项确认

R13 未执行：

- 训练；
- 调参；
- score recompute；
- replay recompute；
- 修改 R1/R9/R10/R12 canonical artifacts；
- 修改策略规则；
- 修改默认策略；
- 前端/API 接入；
- daily orchestrator 接入；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker / quick-trade / order；
- 读取真实券商持仓；
- 输出 target position / target weight。

R13 未修改：

```text
frontend/
backend_api_python/
src/api/
scripts/run_daily_tw_stock_auto_update.py
scripts/run_extended_oos_formal_replay_matrix.py
```

## 10. 结论

R13 已完成。

当前结论：

```text
readonly publish artifact generated
readonly snapshot validator pass
readonly latest pointer points only to readonly snapshot
provider accepted latest remains untouched
frontend/API/daily integration remains untouched
monitor/broker/order remains untouched
```

建议审查者审查通过后，才进入 R14 readonly API。
