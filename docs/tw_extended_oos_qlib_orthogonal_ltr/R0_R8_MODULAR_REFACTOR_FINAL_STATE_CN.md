# R0-R8 Modular Refactor Final State

生成日期：2026-06-16

## 1. 总体状态

本轮 R0-R8 modular decoupled refactor 已完成。

最终状态：

```text
status: archived_for_review
canonical_signal_artifacts: 5
canonical_strategy_dependencies: 5
smoke_only_dependencies: 1
replay_result_artifact: 1
extension_smoke_artifact: 1
latest_regression_status: ok=true
```

本轮没有将 modular artifacts 接入前端、日更、provider publish、accepted latest、monitor 或交易链路。

## 2. 阶段产物

| phase | 主题 | 主要产物 |
|---|---|---|
| R0 | Minimal contracts | `docs/tw_modular_contracts/*.md` |
| R1 | Legacy signal adapter | `scripts/build_tw_modular_legacy_signal_adapter.py`，五个 R1 signal artifacts |
| R2 | Config-driven replay matrix | `configs/tw_modular_replay_matrix.yaml`，`scripts/run_tw_modular_config_replay_matrix.py`，modular replay matrix |
| R3 | Extensible contract design | extension/capability/dependency 设计文档，validator skeleton |
| R4 | Validator + registry | `configs/tw_modular_registry.yaml`，五个 strategy dependency yaml，validator tests |
| R5 | ReplayResult validator + action window | ReplayResult validator，actions `window` 字段，R2 parity 保持 pass |
| R6 | Full registry regression | `scripts/run_tw_modular_contract_regression.py`，regression audit outputs |
| R7 | Extension smoke | `scripts/build_tw_modular_extension_smoke_artifact.py`，`ext_sector_code` smoke artifact |
| R8 | Final release bundle | 本文档、R8 执行报告、R8 handoff |

## 3. Release Bundle Manifest

### 3.1 Contract Docs

```text
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/EXTENSIBLE_CONTRACT_CAPABILITY_DESIGN_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
docs/tw_modular_contracts/STRATEGY_DEPENDENCY_CONTRACT_CN.md
```

### 3.2 Configs

```text
configs/tw_modular_replay_matrix.yaml
configs/tw_modular_registry.yaml
configs/strategy_dependencies/original.yaml
configs/strategy_dependencies/top50_exit_all.yaml
configs/strategy_dependencies/top50_exit_one_worst_sell.yaml
configs/strategy_dependencies/one_sell_one_buy_correct.yaml
configs/strategy_dependencies/one_sell_one_buy_buggy_e8r.yaml
configs/strategy_dependencies/sector_extension_analysis_smoke.yaml
```

### 3.3 Scripts

```text
scripts/build_tw_modular_legacy_signal_adapter.py
scripts/run_tw_modular_config_replay_matrix.py
scripts/validate_tw_modular_artifact_contract.py
scripts/run_tw_modular_contract_regression.py
scripts/build_tw_modular_extension_smoke_artifact.py
```

### 3.4 Canonical Signal Artifacts

```text
data_tw/artifacts/signals/fresh_qlib_adaptive/r1_legacy_signal_adapter_20260616/manifest.json
data_tw/artifacts/signals/fresh_qlib_2025_ltr/r1_legacy_signal_adapter_20260616/manifest.json
data_tw/artifacts/signals/frozen_qlib_2025_ltr/r1_legacy_signal_adapter_20260616/manifest.json
data_tw/artifacts/signals/e4_frozen_qlib_2023_2025_ltr/r1_legacy_signal_adapter_20260616/manifest.json
data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json
```

每个 canonical signal artifact 包含：

```text
manifest.json
signals.csv
schema.json
coverage_audit.csv
forbidden_field_audit.csv
legacy_mapping_audit.csv
```

### 3.5 Canonical ReplayResult Artifact

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_summary.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_daily_nav.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_actions.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_position_snapshots.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_coverage_audit.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_position_integrity_audit.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_forbidden_field_audit.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/r2_parity_audit.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/r2_action_key_parity_audit.csv
```

### 3.6 Regression Audit Bundle

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/registry_validation.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/signal_artifact_validation.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/replay_result_validation.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/parity_summary.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/forbidden_scope_audit.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/manifest_coverage_audit.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/regression_summary.json
```

### 3.7 Smoke-Only Artifact

```text
data_tw/artifacts/signals_extension_smoke/sector_extension_smoke/manifest.json
data_tw/artifacts/signals_extension_smoke/sector_extension_smoke/signals.csv
data_tw/artifacts/signals_extension_smoke/sector_extension_smoke/schema.json
data_tw/artifacts/signals_extension_smoke/sector_extension_smoke/positive_validation.json
data_tw/artifacts/signals_extension_smoke/sector_extension_smoke/negative_missing_extension_validation.json
data_tw/artifacts/signals_extension_smoke/sector_extension_smoke/smoke_summary.json
```

`sector_extension_smoke` 是 smoke-only，不是 canonical strategy evidence。

### 3.8 Review Reports

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER0_MINIMAL_CONTRACT_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER0_REPAIR_REVIEW_HANDOFF_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER1_LEGACY_SIGNAL_ADAPTER_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER1_LEGACY_SIGNAL_ADAPTER_REVIEW_HANDOFF_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_REVIEW_HANDOFF_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER3_EXTENSIBLE_CONTRACT_DESIGN_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER3_EXTENSIBLE_CONTRACT_DESIGN_REVIEW_HANDOFF_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER4_VALIDATOR_REGISTRY_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER4_VALIDATOR_REGISTRY_REVIEW_HANDOFF_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER5_REPLAY_RESULT_VALIDATOR_ACTION_WINDOW_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER5_REPLAY_RESULT_VALIDATOR_ACTION_WINDOW_REVIEW_HANDOFF_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER6_FULL_REGISTRY_REGRESSION_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER6_FULL_REGISTRY_REGRESSION_REVIEW_HANDOFF_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER7_EXTENSION_SMOKE_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER7_EXTENSION_SMOKE_REVIEW_HANDOFF_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER8_FINAL_RELEASE_BUNDLE_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER8_FINAL_RELEASE_BUNDLE_REVIEW_HANDOFF_CN.md
```

## 4. Canonical vs Smoke

### 4.1 Canonical

Canonical artifacts:

- 五个 R1 signal artifacts；
- R2/R5 modular replay matrix ReplayResult artifact；
- 五个 canonical strategy dependencies：
  - `original`
  - `top50_exit_all`
  - `top50_exit_one_worst_sell`
  - `one_sell_one_buy_correct`
  - `one_sell_one_buy_buggy_e8r`

说明：

- `one_sell_one_buy_buggy_e8r` 是 diagnostic-only historical bug evidence，不应作为 valid production strategy evidence。

### 4.2 Smoke-Only

Smoke-only artifacts:

- `sector_extension_analysis_smoke`
- `data_tw/artifacts/signals_extension_smoke/sector_extension_smoke/`

说明：

- `ext_sector_code` 是由 instrument 静态派生的 smoke 字段；
- 不代表真实行业分类；
- 不参与 ranking；
- 不参与 replay；
- 不产生策略收益结论；
- registry regression 中对 canonical R1 artifacts 显示为 `skipped` 是预期行为。

## 5. 一键验证命令

只读/审计类命令：

```bash
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_artifact_contract.py \
  --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json \
  --json
python scripts/build_tw_modular_extension_smoke_artifact.py --json
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

注意：

- `run_tw_modular_contract_regression.py` 会写入 R6 regression audit output directory；
- `build_tw_modular_extension_smoke_artifact.py` 会重建 R7 smoke output directory；
- 两者不修改 canonical R1/R2/R5 artifacts。

## 6. 已归档证据

### 6.1 Regression

最新已归档结果：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/regression_summary.json
ok: true
signal_manifest_count: 5
strategy_dependency_count: 6
signal_validation_rows: 35
```

### 6.2 Parity

```text
summary: pass, 25 vs 25
daily_nav: pass, 1975 vs 1975
actions: pass, 3651 vs 3651
action_key_parity: pass
baseline_not_modular_count: 0
modular_not_baseline_count: 0
duplicate_baseline_action_key_count: 0
duplicate_modular_action_key_count: 0
value_mismatch_count: 0
```

### 6.3 ReplayResult Validator

```text
ReplayResultArtifact: ok=true
actions_window_field: pass
execution_date_after_signal_date: pass
active_quantity_positive: pass
position_integrity: pass
coverage_audit_status: pass
forbidden_field_audit_status: pass
parity_audit_status: pass
action_key_parity_audit_status: pass
manifest_parity_status: pass
```

### 6.4 Extension Smoke

```text
smoke_summary.ok: true
positive_validation_ok: true
negative_missing_extension_validation_ok: false
negative_expected_to_fail: true
```

### 6.5 Forbidden Scope

Forbidden scope tracked diff audit:

```text
frontend/src/views/tw-stock-monitor/index.vue: pass
scripts/run_daily_tw_stock_auto_update.py: pass
scripts/run_extended_oos_formal_replay_matrix.py: pass
backend_api_python: pass
src/api: pass
```

## 7. Residual Risks

1. Baseline actions 仍无 `window` 字段；modular actions 已补 `window`，但 baseline parity 继续使用 R5/R6 已审查通过的 prefix compatibility 口径。
2. R1 legacy signal adapter 为兼容旧 replay 结果，`fresh_qlib_adaptive` 和 `fresh_qlib_2025_ltr` 存在 full rank fallback rows；R2/R5 parity 已证明未改变旧结果。
3. `ext_sector_code` 是 smoke-only，不代表真实行业分类。
4. 当前 release bundle 是研究/审计归档，不是生产接入包。
5. 当前仓库有大量历史 untracked 文件；R6/R8 forbidden scope 证据采用 tracked diff 口径，正式发布时应按本 release bundle manifest 精确打包。

## 8. Post-R8 Allowed Next Steps

允许后续另开阶段审查的方向：

- production integration readiness review；
- frontend/API 只读展示接入设计；
- daily update 接入设计；
- provider/accepted latest 发布流程设计；
- sector-aware real dependency 设计；
- replay baseline action `window` 字段彻底消除兼容口径；
- release artifact packaging / checksum manifest。

以上都必须另开阶段并重新定义边界。

## 9. Post-R8 Forbidden Actions

未经新阶段审查，仍禁止：

- 新训练；
- 调参；
- 重算模型分数；
- 修改 R1 canonical signals；
- 修改 R2/R5 replay results；
- 新增 replay 策略结果；
- 根据收益筛选模型；
- 修改默认策略；
- 前端接入；
- 日更接入；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker、quick-trade 或 order。

## 10. Final Conclusion

R0-R8 本轮 modular refactor 已达到归档状态。

本状态只证明：

- contract / registry / validator / replay result / extension smoke 机制可复核；
- canonical replay parity 已保持；
- 当前 artifacts 未接入生产链路。

本状态不证明：

- 任一策略应进入生产；
- smoke sector 字段可用于真实投资判断；
- 可以自动接入前端、日更、provider publish、accepted latest 或交易链路。
