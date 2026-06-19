# Phase R6 Full Registry Regression 审查交接

生成日期：2026-06-16

## 1. 本阶段目标

R6 根据 R5 审查意见执行：

```text
Full Registry Regression / Artifact Audit / Release Bundle
```

本阶段只新增只读 regression runner 和审计产物，不改变 R1 signals，不改变 R2/R5 replay 结果，不接入前端、日更或生产链路。

## 2. 审查对象

新增 runner：

```text
scripts/run_tw_modular_contract_regression.py
```

R6 输出目录：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/
```

R6 执行报告：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER6_FULL_REGISTRY_REGRESSION_EXECUTION_REPORT_CN.md
```

## 3. 一键复核命令

```bash
python scripts/run_tw_modular_contract_regression.py --json
```

预期：

```text
ok: true
signal_manifest_count: 5
strategy_dependency_count: 5
signal_validation_rows: 30
```

## 4. 测试命令

```bash
python -m py_compile scripts/run_tw_modular_contract_regression.py
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

当前结果：

```text
py_compile: pass
pytest: 12 passed
```

## 5. R6 输出清单

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/registry_validation.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/signal_artifact_validation.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/replay_result_validation.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/parity_summary.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/forbidden_scope_audit.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/manifest_coverage_audit.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/regression_summary.json
```

## 6. 当前审计结论

### 6.1 Registry

```text
registry_version: pass
registry_dependency_paths: pass
registry_contract_docs: pass
```

### 6.2 Signal artifacts

```text
signal_manifest_count: 5
strategy_dependency_count: 5
signal_validation_rows: 30
failed_checks: none
```

覆盖五个 R1 signal artifacts：

- `fresh_qlib_adaptive`
- `fresh_qlib_2025_ltr`
- `frozen_qlib_2025_ltr`
- `e4_frozen_qlib_2023_2025_ltr`
- `frozen_qlib_2018_2022`

### 6.3 ReplayResult

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

### 6.4 Parity

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

### 6.5 Forbidden scope

```text
frontend/src/views/tw-stock-monitor/index.vue: pass
scripts/run_daily_tw_stock_auto_update.py: pass
scripts/run_extended_oos_formal_replay_matrix.py: pass
backend_api_python: pass
src/api: pass
```

审计口径为：

```text
git diff --name-only HEAD -- tracked files
```

## 7. 边界说明

R6 未执行：

- 训练；
- 调参；
- score recompute；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker / quick-trade / order。

R6 未修改：

- R1 `signals.csv`；
- R2/R5 `formal_replay_summary.csv`；
- R2/R5 `formal_replay_daily_nav.csv`；
- R2/R5 `formal_replay_actions.csv`；
- 前端；
- 日更脚本；
- 旧 formal replay runner。

## 8. 建议审查重点

建议审查者重点看：

1. R6 runner 是否只读；
2. registry dependency paths 是否覆盖五个策略；
3. signal artifact validation 是否覆盖五个模型与五个 dependency；
4. replay result validation 是否复用 R5 validator；
5. parity summary 是否仍为 pass；
6. forbidden scope audit 的 tracked diff 口径是否可接受；
7. manifest coverage 是否覆盖 R0-R5 必需合同与产物。

## 9. 建议结论

若审查者确认以上输出可复核，建议 R6 通过。
