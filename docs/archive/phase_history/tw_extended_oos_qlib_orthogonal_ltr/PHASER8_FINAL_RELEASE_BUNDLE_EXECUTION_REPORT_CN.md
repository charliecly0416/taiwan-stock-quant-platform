# Phase R8 Final Release Bundle 执行报告

生成日期：2026-06-16

## 1. 执行范围

本阶段根据：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER7_REVIEW_AND_R8_WORK_CN.md
```

执行 R8：

```text
R0-R8 Modular Refactor Release Bundle / Final Boundary Audit
```

R8 只新增最终报告和 release bundle 清单，不新增机制，不运行训练，不运行新 replay，不修改 canonical artifacts。

## 2. 新增文档

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/R0_R8_MODULAR_REFACTOR_FINAL_STATE_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER8_FINAL_RELEASE_BUNDLE_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER8_FINAL_RELEASE_BUNDLE_REVIEW_HANDOFF_CN.md
```

## 3. Release Bundle 覆盖

本次 release bundle 已在最终状态文档中明确：

- R0-R8 每阶段产物；
- contract docs；
- configs；
- scripts；
- canonical signal artifacts；
- canonical ReplayResult artifact；
- R6 regression audit bundle；
- R7 smoke-only artifact；
- review reports；
- validation commands；
- parity evidence；
- forbidden scope evidence；
- residual risks；
- post-R8 allowed next steps；
- post-R8 forbidden actions。

主清单：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/R0_R8_MODULAR_REFACTOR_FINAL_STATE_CN.md
```

## 4. Canonical Artifacts

Canonical signal artifacts：

```text
data_tw/artifacts/signals/fresh_qlib_adaptive/r1_legacy_signal_adapter_20260616/manifest.json
data_tw/artifacts/signals/fresh_qlib_2025_ltr/r1_legacy_signal_adapter_20260616/manifest.json
data_tw/artifacts/signals/frozen_qlib_2025_ltr/r1_legacy_signal_adapter_20260616/manifest.json
data_tw/artifacts/signals/e4_frozen_qlib_2023_2025_ltr/r1_legacy_signal_adapter_20260616/manifest.json
data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json
```

Canonical ReplayResult：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
```

Canonical strategy dependencies：

```text
configs/strategy_dependencies/original.yaml
configs/strategy_dependencies/top50_exit_all.yaml
configs/strategy_dependencies/top50_exit_one_worst_sell.yaml
configs/strategy_dependencies/one_sell_one_buy_correct.yaml
configs/strategy_dependencies/one_sell_one_buy_buggy_e8r.yaml
```

说明：

- `one_sell_one_buy_buggy_e8r` 为 diagnostic-only historical bug evidence；
- 它不是 valid production strategy evidence。

## 5. Smoke-Only Artifacts

Smoke-only dependency：

```text
configs/strategy_dependencies/sector_extension_analysis_smoke.yaml
```

Smoke-only artifact：

```text
data_tw/artifacts/signals_extension_smoke/sector_extension_smoke/
```

说明：

- `ext_sector_code` 是 smoke-only 静态派生字段；
- 不代表真实行业分类；
- 不参与 ranking；
- 不参与 replay；
- 不产生策略收益结论；
- registry 中的 `applies_to_artifact_names` 限定它只适用于 smoke artifact。

## 6. 验证证据

R8 未重新运行会写输出的命令；以下为 R6/R7 已归档验证证据。

### 6.1 Regression Summary

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/regression_summary.json
ok: true
signal_manifest_count: 5
strategy_dependency_count: 6
signal_validation_rows: 35
```

### 6.2 Parity Evidence

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/parity_summary.csv
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

### 6.3 ReplayResult Validator Evidence

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/replay_result_validation.json
ok: true
```

关键 pass：

```text
actions_window_field
execution_date_after_signal_date
active_quantity_positive
position_integrity
coverage_audit_status
forbidden_field_audit_status
parity_audit_status
action_key_parity_audit_status
manifest_parity_status
```

### 6.4 Extension Smoke Evidence

```text
data_tw/artifacts/signals_extension_smoke/sector_extension_smoke/smoke_summary.json
ok: true
positive_validation_ok: true
negative_missing_extension_validation_ok: false
negative_expected_to_fail: true
```

### 6.5 Forbidden Scope Evidence

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/forbidden_scope_audit.csv
```

已归档状态：

```text
frontend/src/views/tw-stock-monitor/index.vue: pass
scripts/run_daily_tw_stock_auto_update.py: pass
scripts/run_extended_oos_formal_replay_matrix.py: pass
backend_api_python: pass
src/api: pass
```

## 7. 固化验证命令

后续审查者可复跑：

```bash
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_artifact_contract.py \
  --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json \
  --json
python scripts/build_tw_modular_extension_smoke_artifact.py --json
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

注意：

- 前两条不训练、不调参、不重算模型分数；
- `run_tw_modular_contract_regression.py` 会更新 R6 regression audit 输出目录；
- `build_tw_modular_extension_smoke_artifact.py` 会更新 R7 smoke 输出目录；
- 不应在 R8 阶段将这些命令解释为生产接入。

## 8. 边界确认

R8 未执行、未修改：

- 新训练；
- 调参；
- score recompute；
- R1 canonical signals；
- R2/R5 replay results；
- 新 replay 策略结果；
- 默认策略；
- 前端；
- 日更脚本；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker / quick-trade / order。

## 9. 残余风险

1. baseline actions 仍无 `window` 字段，action parity 继续沿用 R5/R6 已通过的 prefix compatibility 口径。
2. full rank fallback rows 是 R1 legacy compatibility 的一部分，不应被解释为新模型改动。
3. `ext_sector_code` 仅为 smoke-only，不可作为真实 sector source。
4. R0-R8 release bundle 是审计归档，不是 production integration package。
5. 后续如需前端、日更、provider publish、accepted latest 或交易链路接入，必须另开阶段单独审查。

## 10. 结论

R8 已完成。

本轮 R0-R8 modular refactor 已形成可审查 release bundle，并明确当前仍停留在 research / audit artifact 边界内。
