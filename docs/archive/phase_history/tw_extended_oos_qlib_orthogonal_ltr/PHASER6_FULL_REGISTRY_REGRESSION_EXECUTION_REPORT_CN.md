# Phase R6 Full Registry Regression 执行报告

生成日期：2026-06-16

## 1. 执行范围

本阶段根据：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER5_REVIEW_AND_R6_WORK_CN.md
```

执行 R6：

```text
Full Registry Regression / Artifact Audit / Release Bundle
```

目标是新增只读一键回归入口，验证 R0-R5 modular artifact 是否仍满足 registry、contract、signal artifact、ReplayResult 和 parity 要求。

## 2. 新增内容

新增 runner：

```text
scripts/run_tw_modular_contract_regression.py
```

新增审计输出目录：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/
```

输出文件：

```text
registry_validation.json
signal_artifact_validation.csv
replay_result_validation.json
parity_summary.csv
forbidden_scope_audit.csv
manifest_coverage_audit.csv
regression_summary.json
```

## 3. Runner 行为

`scripts/run_tw_modular_contract_regression.py` 为只读审计入口：

- 读取 `configs/tw_modular_registry.yaml`；
- 验证 registry dependency paths 与 contract docs；
- 从 R2/R5 replay manifest 自动读取五个 R1 signal manifest；
- 对每个 signal artifact 执行 core contract validator；
- 对每个 signal artifact 交叉执行五个 strategy dependency validator；
- 验证 R2/R5 ReplayResult manifest；
- 汇总 summary / daily_nav / actions parity；
- 审计禁止范围 tracked diff；
- 审计 R0-R5 manifest / output artifact 覆盖。

## 4. 回归结果

执行命令：

```bash
python scripts/run_tw_modular_contract_regression.py --json
```

结果：

```text
ok: true
signal_manifest_count: 5
strategy_dependency_count: 5
signal_validation_rows: 30
```

说明：

- 5 个 R1 signal artifact 均通过；
- 5 个 strategy dependency path 均存在；
- 5 个 signal artifact x 5 个 strategy dependency 均通过；
- ReplayResult validator 通过；
- R2/R5 parity summary 全部 pass；
- forbidden scope audit 全部 pass；
- manifest coverage audit 全部 pass。

## 5. 关键输出复核

### 5.1 registry validation

```text
registry_version: pass
registry_dependency_paths: pass
registry_contract_docs: pass
```

### 5.2 signal artifact validation

输出：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/signal_artifact_validation.csv
```

统计：

```text
rows: 30
failed_checks: none
```

覆盖：

- `fresh_qlib_adaptive`
- `fresh_qlib_2025_ltr`
- `frozen_qlib_2025_ltr`
- `e4_frozen_qlib_2023_2025_ltr`
- `frozen_qlib_2018_2022`

每个 artifact 均执行：

- core ModelSignalArtifact validation；
- `original` dependency validation；
- `top50_exit_all` dependency validation；
- `top50_exit_one_worst_sell` dependency validation；
- `one_sell_one_buy_correct` dependency validation；
- `one_sell_one_buy_buggy_e8r` diagnostic dependency validation。

### 5.3 replay result validation

输出：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/replay_result_validation.json
```

结果：

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

### 5.4 parity summary

输出：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/parity_summary.csv
```

结果：

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

### 5.5 forbidden scope audit

输出：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/forbidden_scope_audit.csv
```

审计口径：

```text
git diff --name-only HEAD -- tracked files
```

结果：

```text
frontend/src/views/tw-stock-monitor/index.vue: pass
scripts/run_daily_tw_stock_auto_update.py: pass
scripts/run_extended_oos_formal_replay_matrix.py: pass
backend_api_python: pass
src/api: pass
```

## 6. 测试

执行命令：

```bash
python -m py_compile scripts/run_tw_modular_contract_regression.py
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

结果：

```text
py_compile: pass
pytest: 12 passed
```

## 7. 边界确认

本阶段未执行、未修改：

- qlib / LTR 训练；
- 调参；
- score recompute；
- R1 `signals.csv`；
- R2/R5 replay summary / daily_nav / actions 结果；
- 根据收益筛选模型；
- 默认策略；
- 前端；
- 日更脚本；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker / quick-trade / order。

## 8. 残余风险

1. `forbidden_scope_audit.csv` 使用 tracked diff 口径，目的是避免当前仓库已有大量历史 untracked 产物造成误报。该口径适合审查本阶段是否改动禁止范围 tracked 文件。
2. baseline actions 仍无 `window` 字段，R6 继续复用 R5 已审查通过的 action parity 兼容口径。
3. R6 不重新生成 R1/R2/R5 artifact，只验证现有产物。

## 9. 结论

R6 已完成。

建议审查者重点复核：

- `scripts/run_tw_modular_contract_regression.py`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/regression_summary.json`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/signal_artifact_validation.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/replay_result_validation.json`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/parity_summary.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/forbidden_scope_audit.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/manifest_coverage_audit.csv`
