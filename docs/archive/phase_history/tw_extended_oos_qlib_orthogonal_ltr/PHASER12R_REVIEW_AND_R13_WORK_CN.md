# Phase R12R 审查与 R13 工作建议

生成日期：2026-06-16

## 1. 审查结论

R12R 审查通过，允许进入 R13。

R12R 已修复 R12 阻塞问题：

- `checksum_manifest.json` 不再包含自身；
- `checksum_manifest.json` 已包含 `manifest.json`；
- `checksum_manifest.json` 已包含 `shadow_summary.json`；
- checksum 清单 24 个文件均与当前文件 hash 一致；
- `checksum_manifest.validation.ok == true`；
- `manifest.gate.checksum_manifest_valid == true`；
- `shadow_summary.checksum_manifest_valid == true`；
- shadow 输出仍全部限制在 `data_tw/artifacts/shadow_modular_daily/2026-06-16/`；
- 未创建 publish artifact；
- 未创建 readonly latest pointer；
- 未修改前端、API、日更、provider/accepted latest、monitor 或交易链路。

## 2. 审查对象

R12R handoff：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER12R_SHADOW_CHECKSUM_REPAIR_REVIEW_HANDOFF_CN.md
```

R12R 执行报告：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER12R_SHADOW_CHECKSUM_REPAIR_EXECUTION_REPORT_CN.md
```

修改脚本：

```text
scripts/run_tw_modular_shadow_daily.py
```

更新 artifact：

```text
data_tw/artifacts/shadow_modular_daily/2026-06-16/
```

## 3. 复核结果

### 3.1 Detached checksum 设计正确

`checksum_manifest.json` 当前声明：

```text
algorithm: sha256
excluded_files: [checksum_manifest.json]
```

清单不包含：

```text
data_tw/artifacts/shadow_modular_daily/2026-06-16/checksum_manifest.json
```

这避免了 R12 的自引用 hash 失效问题。

### 3.2 关键 shadow 输出已纳入 checksum

清单已包含：

```text
data_tw/artifacts/shadow_modular_daily/2026-06-16/manifest.json
data_tw/artifacts/shadow_modular_daily/2026-06-16/model_signal_manifest.json
data_tw/artifacts/shadow_modular_daily/2026-06-16/full_rank_manifest.json
data_tw/artifacts/shadow_modular_daily/2026-06-16/strategy_dependency_snapshot.yaml
data_tw/artifacts/shadow_modular_daily/2026-06-16/replay_result_manifest.json
data_tw/artifacts/shadow_modular_daily/2026-06-16/validation_report.json
data_tw/artifacts/shadow_modular_daily/2026-06-16/forbidden_scope_audit.json
data_tw/artifacts/shadow_modular_daily/2026-06-16/shadow_summary.json
```

同时覆盖 source inputs：

```text
configs/tw_modular_registry.yaml
configs/tw_modular_replay_matrix.yaml
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
5 个 signal manifest
2 个 full-rank manifest
6 个 strategy dependency yaml
```

### 3.3 独立 checksum 校验通过

独立复核脚本重新计算了 `checksum_manifest.json` 中全部条目的 sha256。

结果：

```text
file_count: 24
validation.ok: true
validation.checked_file_count: 24
has_checksum_self: False
manifest.json included: True
shadow_summary.json included: True
bad_count: 0
```

说明 checksum manifest 可以稳定验证当前 shadow 输入和输出文件。

### 3.4 Gate 已补 checksum_manifest_valid

`manifest.json`：

```text
gate.checksum_manifest_valid: true
status: pass
```

`shadow_summary.json`：

```text
checksum_manifest_valid: true
```

`checksum_manifest.json`：

```text
validation.ok: true
validation.checked_file_count: 24
```

### 3.5 R12R runner 复跑通过

复核命令：

```bash
python scripts/run_tw_modular_shadow_daily.py --asof 2026-06-16 --json
```

结果：

```text
ok: true
gate.all_validators_pass: true
gate.forbidden_scope_audit_status: pass
gate.artifact_output_under_shadow_dir_only: true
gate.no_frontend_change: true
gate.no_api_change: true
gate.no_daily_orchestrator_change: true
gate.no_provider_publish: true
gate.no_accepted_latest_switch: true
gate.no_broker_order: true
gate.checksum_manifest_valid: true
```

### 3.6 Regression / tests 通过

复核命令：

```bash
python scripts/run_tw_modular_contract_regression.py --json
```

结果：

```text
ok: true
signal_manifest_count: 5
strategy_dependency_count: 6
full_rank_artifact_count: 2
signal_validation_rows: 35
full_rank_validation_rows: 5
```

复核命令：

```bash
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

结果：

```text
13 passed
```

### 3.7 Forbidden scope 通过

`forbidden_scope_audit.json`：

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

Targeted diff：

```text
frontend
src
backend
backend_api_python
scripts/run_daily_tw_stock_auto_update.py
scripts/run_extended_oos_formal_replay_matrix.py
data_tw/artifacts/publish
```

结果：无 tracked diff。

未发现：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/
readonly latest pointer
provider accepted latest change
frontend/API 接入
daily orchestrator 接入
monitor / broker / quick-trade / order
```

## 4. 非阻塞建议

### P3：R13 应新增 readonly snapshot validator，而不是复用 shadow validator

R12R 修复的是 shadow artifact 的 checksum 完整性。R13 将进入 readonly publish artifact contract / writer / validator，必须新增针对 `readonly_strategy_snapshot` 的 validator。

该 validator 至少检查：

- `readonly_only == true`；
- `production_trade_enabled == false`；
- `no_order_action == true`；
- `not_target_position == true`；
- `not_investment_advice == true`；
- `is_production_trading_default == false`；
- `display_role` 合法；
- `source_shadow_manifest` 指向 R12/R12R shadow 目录；
- `checksum_manifest` 存在且可验证；
- 不含 broker / quick-trade / order / target_position / target_weight 字段；
- 不创建或修改 provider accepted latest。

## 5. R13 工作建议

允许执行 R13：Readonly Publish Artifact Contract / Writer / Validator。

R13 目标：

- 新增 readonly publish artifact contract；
- 新增 writer；
- 新增 validator；
- 从 R12R shadow artifact 生成 readonly strategy snapshot；
- 可创建 readonly snapshot 自己的 latest pointer；
- 不得接前端/API；
- 不得接 daily orchestrator；
- 不得 provider publish；
- 不得 accepted latest；
- 不得 monitor / broker / order。

R13 建议新增：

```text
docs/tw_modular_contracts/READONLY_STRATEGY_SNAPSHOT_CONTRACT_CN.md
scripts/publish_tw_modular_readonly_snapshot.py
scripts/validate_tw_modular_readonly_snapshot.py
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-06-16/
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER13_READONLY_PUBLISH_ARTIFACT_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER13_READONLY_PUBLISH_ARTIFACT_REVIEW_HANDOFF_CN.md
```

R13 snapshot 必须体现产品化工作文档冻结的展示选择：

```text
display_role: primary_readonly_candidate
model_id: e4_frozen_qlib_2023_2025_ltr
strategy_rule: top50_exit_one_worst_sell
is_production_trading_default: false
readonly_only: true
not_target_position: true
not_investment_advice: true
```

R13 可生成 readonly latest pointer，但必须满足：

```text
路径仅限 data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
不得命名为 accepted latest
不得修改 qlib/provider accepted latest
不得被前端/API读取，直到 R14/R15 单独审查
```

## 6. R13 禁止事项

R13 禁止：

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
- broker、quick-trade 或 order；
- 输出 target position / target weight；
- 将 readonly snapshot 表述为交易建议。

## 7. 最终结论

R12R 通过。

R12 shadow artifact 的 checksum 完整性问题已修复，shadow runner gate 已补 `checksum_manifest_valid` 并通过。允许进入 R13，但 R13 仍仅限 readonly publish artifact contract / writer / validator，不得接入前端、API、daily orchestrator、provider accepted latest 或交易链路。
