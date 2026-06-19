# Phase R8 Final Release Bundle 审查交接

生成日期：2026-06-16

## 1. 本阶段目标

R8 根据 R7 审查意见执行：

```text
R0-R8 Modular Refactor Release Bundle / Final Boundary Audit
```

本阶段只新增最终报告和 release bundle 清单。

## 2. 审查对象

新增文档：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/R0_R8_MODULAR_REFACTOR_FINAL_STATE_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER8_FINAL_RELEASE_BUNDLE_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER8_FINAL_RELEASE_BUNDLE_REVIEW_HANDOFF_CN.md
```

## 3. Release Bundle 主清单

主清单在：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/R0_R8_MODULAR_REFACTOR_FINAL_STATE_CN.md
```

该文档明确：

- R0-R8 每阶段产物；
- canonical artifacts；
- smoke-only artifacts；
- release bundle manifest；
- 一键验证命令；
- parity 与 validator 证据；
- forbidden scope 证据；
- 残余风险；
- post-R8 allowed next steps；
- post-R8 forbidden actions。

## 4. Canonical / Smoke 分类

Canonical：

```text
五个 R1 signal artifacts
R2/R5 ReplayResult artifact
五个 canonical strategy dependencies
```

Smoke-only：

```text
configs/strategy_dependencies/sector_extension_analysis_smoke.yaml
data_tw/artifacts/signals_extension_smoke/sector_extension_smoke/
```

关键说明：

- `sector_extension_analysis_smoke` 不是 production strategy；
- `ext_sector_code` 不是生产级行业分类；
- skipped dependency 不代表失败，也不代表策略放行。

## 5. 已归档验证证据

Regression：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/regression_summary.json
ok: true
signal_manifest_count: 5
strategy_dependency_count: 6
signal_validation_rows: 35
```

Parity：

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

ReplayResult validator：

```text
ok: true
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

Extension smoke：

```text
ok: true
positive_validation_ok: true
negative_missing_extension_validation_ok: false
negative_expected_to_fail: true
```

Forbidden scope：

```text
frontend: pass
daily update: pass
old formal replay runner: pass
backend_api_python: pass
src/api: pass
```

## 6. 可复跑命令

```bash
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_artifact_contract.py \
  --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json \
  --json
python scripts/build_tw_modular_extension_smoke_artifact.py --json
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

审查注意：

- 上述命令是 audit/smoke 验证，不是生产接入；
- 复跑 regression / smoke 会更新各自审计输出目录；
- 不会修改 canonical R1/R2/R5 artifacts。

## 7. R8 边界

R8 未执行：

- 训练；
- 调参；
- score recompute；
- replay；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker / quick-trade / order。

R8 未修改：

- R1 canonical signals；
- R2/R5 replay summary；
- R2/R5 replay daily_nav；
- R2/R5 replay actions；
- 前端；
- 日更脚本；
- 旧 formal replay runner。

## 8. 残余风险

1. baseline actions 仍无 `window` 字段，当前 parity 依赖 R5/R6 已审查通过的兼容口径。
2. `ext_sector_code` 是 smoke-only，不是生产级 sector source。
3. R0-R8 bundle 是 research / audit artifact，不是 production integration package。
4. 当前仓库有历史 untracked 文件，正式发布应按 release bundle manifest 精确打包。

## 9. Post-R8 建议

若后续要进入生产/前端/日更接入，必须另开阶段单独审查，至少包含：

- production readiness checklist；
- artifact checksum / package manifest；
- frontend/API read-only contract；
- daily update failure / retry / rollback policy；
- provider publish 与 accepted latest governance；
- monitor 与交易链路隔离审计。

## 10. 建议结论

若审查者确认 R8 三份文档覆盖完整，建议本轮 R0-R8 modular refactor 归档通过。
