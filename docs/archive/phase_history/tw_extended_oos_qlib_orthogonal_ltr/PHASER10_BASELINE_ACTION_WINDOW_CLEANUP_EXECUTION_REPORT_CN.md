# Phase R10 Baseline Action Window Cleanup 执行报告

生成日期：2026-06-16

## 1. 执行范围

本阶段根据：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER9_REVIEW_AND_R10_WORK_CN.md
```

执行 R10：

```text
Baseline Action Window Cleanup
```

目标是消除 baseline actions 无 `window` 字段导致的 action parity 兼容口径。

## 2. 实现路径

采用推荐路径 B：

```text
新增 baseline normalized action artifact / adapter
```

理由：

- 不修改旧 baseline generator；
- 不改已归档 baseline formal replay matrix；
- 只在独立目录生成带 `window` 字段的 baseline actions；
- 可单独审查 window 字段赋值。

## 3. 新增/修改内容

新增 adapter：

```text
scripts/build_formal_replay_baseline_action_window_adapter.py
```

新增 windowed baseline artifact：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix_windowed/
```

输出：

```text
manifest.json
formal_replay_summary.csv
formal_replay_daily_nav.csv
formal_replay_actions.csv
action_window_assignment_audit.csv
```

更新：

```text
configs/tw_modular_replay_matrix.yaml
scripts/run_tw_modular_config_replay_matrix.py
```

## 4. Baseline Window Adapter

执行命令：

```bash
python scripts/build_formal_replay_baseline_action_window_adapter.py --json
```

结果：

```text
ok: true
windowed_action_rows: 23571
source_action_rows: 23571
```

赋值策略：

```text
summary_order_action_count_plus_skipped_count_to_window_field
```

说明：

- adapter 按 baseline summary 的原始写出顺序，为 baseline actions 补充 `window`；
- 同时保留 `source_action_row_index` 追溯原始行；
- 原始 baseline 目录不变；
- windowed baseline 只作为 normalized action artifact 参与 R10 parity。

## 5. Direct Window Parity

`scripts/run_tw_modular_config_replay_matrix.py` 的 action parity 已改为：

```text
baseline.window == 2026_ytd
modular.window == 2026_ytd
```

不再使用：

```text
baseline actions first N rows
```

R10 audit：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/r10_action_window_parity_audit.csv
```

结果：

```text
filter_policy: direct_window_filter_2026_ytd
baseline_total_rows: 23571
baseline_filtered_rows: 3651
baseline_window_field_present: True
modular_window_field_present: True
baseline_unique_action_keys: 3651
modular_action_rows: 3651
modular_unique_action_keys: 3651
baseline_not_modular_count: 0
modular_not_baseline_count: 0
duplicate_baseline_action_key_count: 0
duplicate_modular_action_key_count: 0
value_mismatch_count: 0
status: pass
```

## 6. Replay Parity

执行命令：

```bash
python scripts/run_tw_modular_config_replay_matrix.py --config configs/tw_modular_replay_matrix.yaml
```

结果：

```text
ok: true
parity_status: pass
```

Parity：

```text
summary: pass, 25 vs 25
daily_nav: pass, 1975 vs 1975
actions: pass, 3651 vs 3651
```

## 7. R9 非阻塞发现修复

R9 审查指出：

```text
formal_replay_coverage_audit.csv.full_rank_artifact
```

曾错误记录为 signal manifest 路径。

R10 已修复：

```text
formal_replay_coverage_audit.csv
```

现在同时记录：

```text
signal_artifact
full_rank_artifact
```

其中 `full_rank_artifact` 正确指向：

```text
data_tw/artifacts/full_rank/fresh_qlib_s2b_post_filter/r9_full_rank_adapter_20260616/manifest.json
data_tw/artifacts/full_rank/frozen_qlib_2018_2022_raw_oos/r9_full_rank_adapter_20260616/manifest.json
```

## 8. ReplayResult Validator / Regression

ReplayResult manifest：

```text
schema_version: replay_result_r10_action_window_cleanup
action_key_parity_audit: data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/r10_action_window_parity_audit.csv
```

Validator：

```bash
python scripts/validate_tw_modular_artifact_contract.py \
  --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json \
  --json
```

结果：

```text
ok: true
schema_version: replay_result_r10_action_window_cleanup
actions_window_field: pass
parity_audit_status: pass
action_key_parity_audit_status: pass
manifest_parity_status: pass
```

Regression：

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

## 9. Tests

执行命令：

```bash
python -m py_compile scripts/build_formal_replay_baseline_action_window_adapter.py scripts/run_tw_modular_config_replay_matrix.py scripts/validate_tw_modular_artifact_contract.py scripts/run_tw_modular_contract_regression.py
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

结果：

```text
py_compile: pass
pytest: 13 passed
```

## 10. 旧兼容口径清除检查

复核命令：

```bash
rg -n "baseline_actions_prefix|first N rows|head\\(expected_rows\\)|expected_rows|prefix count" \
  scripts/run_tw_modular_config_replay_matrix.py \
  data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/r10_action_window_parity_audit.csv \
  data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/r2_action_key_parity_audit.csv
```

结果：

```text
no matches
```

## 11. 边界确认

R10 未执行、未修改：

- 训练；
- 调参；
- score recompute；
- R1 canonical signals；
- 策略规则；
- 默认策略；
- 新策略收益结论；
- 前端；
- 日更脚本；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker / quick-trade / order。

R10 重跑 modular replay matrix，仅用于验证 direct window parity，不新增策略逻辑。

## 12. 结论

R10 已完成。

R10 后：

- baseline actions 已有 `window` 字段；
- modular actions 已有 `window` 字段；
- action parity 直接按 `window == 2026_ytd` 过滤；
- prefix compatibility 口径已消除；
- R9 coverage audit 路径记录问题已修复；
- ReplayResult validator、regression、tests 均通过。
