# Phase R2 Config-driven Replay Matrix 审查说明

生成日期：2026-06-16

## 1. 审查范围

本 handoff 供审查者复核 R2。R2 只新增 config-driven replay matrix，不接入前端、日更或生产链路。

## 2. 新增/修改文件

```text
configs/tw_modular_replay_matrix.yaml
scripts/run_tw_modular_config_replay_matrix.py
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_REVIEW_HANDOFF_CN.md
```

## 3. 建议复核命令

```bash
python scripts/run_tw_modular_config_replay_matrix.py --config configs/tw_modular_replay_matrix.yaml
cat data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/r2_parity_audit.csv
cat data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/r2_action_key_parity_audit.csv
rg -n "fail" data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/r2_parity_audit.csv data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/r2_action_key_parity_audit.csv
git diff -- frontend/src/views/tw-stock-monitor/index.vue scripts/run_daily_tw_stock_auto_update.py scripts/run_extended_oos_formal_replay_matrix.py
```

预期：

- parity audit 无 `fail`；
- summary / daily_nav 与 baseline `2026_ytd` 关键结果完全一致；
- `r2_action_key_parity_audit.csv` 中 `baseline_not_modular_count=0`、`modular_not_baseline_count=0`、重复 key 为 0、value mismatch 为 0；
- 前端、日更脚本、旧 formal replay matrix 的 `git diff` 为空；
- 输出 manifest 的 `parity_status` 为 `pass`。
