# Phase R10 Baseline Action Window Cleanup 审查交接

生成日期：2026-06-16

## 1. 本阶段目标

R10 根据 R9 审查意见执行：

```text
Baseline Action Window Cleanup
```

目标是消除 baseline actions 无 `window` 字段导致的 action parity prefix compatibility。

## 2. 审查对象

新增：

```text
scripts/build_formal_replay_baseline_action_window_adapter.py
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix_windowed/
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER10_BASELINE_ACTION_WINDOW_CLEANUP_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER10_BASELINE_ACTION_WINDOW_CLEANUP_REVIEW_HANDOFF_CN.md
```

更新：

```text
configs/tw_modular_replay_matrix.yaml
scripts/run_tw_modular_config_replay_matrix.py
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/
```

## 3. 一键复核命令

```bash
python scripts/build_formal_replay_baseline_action_window_adapter.py --json
python scripts/run_tw_modular_config_replay_matrix.py --config configs/tw_modular_replay_matrix.yaml
python scripts/validate_tw_modular_artifact_contract.py \
  --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json \
  --json
python scripts/run_tw_modular_contract_regression.py --json
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

## 4. 当前复核结果

Baseline window adapter：

```text
ok: true
windowed_action_rows: 23571
source_action_rows: 23571
```

Replay parity：

```text
ok: true
parity_status: pass
summary: pass, 25 vs 25
daily_nav: pass, 1975 vs 1975
actions: pass, 3651 vs 3651
```

R10 action window parity：

```text
filter_policy: direct_window_filter_2026_ytd
baseline_window_field_present: True
modular_window_field_present: True
baseline_filtered_rows: 3651
modular_action_rows: 3651
baseline_not_modular_count: 0
modular_not_baseline_count: 0
duplicate_baseline_action_key_count: 0
duplicate_modular_action_key_count: 0
value_mismatch_count: 0
status: pass
```

ReplayResult validator：

```text
ok: true
schema_version: replay_result_r10_action_window_cleanup
action_key_parity_audit_status: pass
manifest_parity_status: pass
```

Regression：

```text
ok: true
signal_manifest_count: 5
strategy_dependency_count: 6
full_rank_artifact_count: 2
signal_validation_rows: 35
full_rank_validation_rows: 5
```

Tests：

```text
pytest: 13 passed
```

## 5. Prefix Compatibility 清除检查

复核命令：

```bash
rg -n "baseline_actions_prefix|first N rows|head\\(expected_rows\\)|expected_rows|prefix count" \
  scripts/run_tw_modular_config_replay_matrix.py \
  data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/r10_action_window_parity_audit.csv \
  data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/r2_action_key_parity_audit.csv
```

当前结果：

```text
no matches
```

## 6. R9 Coverage Audit 修复

`formal_replay_coverage_audit.csv` 已修复：

```text
signal_artifact: R1 signal manifest
full_rank_artifact: R9 FullRankArtifact manifest
```

不再把 `full_rank_artifact` 误写为 signal manifest 路径。

## 7. 边界说明

R10 未执行：

- 训练；
- 调参；
- score recompute；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker / quick-trade / order。

R10 未修改：

- R1 canonical signals；
- 策略规则；
- 默认策略；
- 前端；
- 日更脚本；
- 旧 baseline formal replay generator。

R10 采用路径 B，原始 baseline formal replay matrix 保持不变。

## 8. 建议审查重点

建议审查者重点看：

1. `formal_replay_matrix_windowed/formal_replay_actions.csv` 是否有 `window`；
2. `action_window_assignment_audit.csv` 是否全部 pass；
3. `r10_action_window_parity_audit.csv` 是否直接按 window 过滤；
4. 是否不再使用 prefix compatibility；
5. summary / daily_nav / action key parity 是否保持 pass；
6. ReplayResult validator 和 regression 是否通过；
7. 是否没有越界执行 R11。

## 9. 建议结论

若审查者确认以上输出可复核，建议 R10 通过，并允许进入 R11。
