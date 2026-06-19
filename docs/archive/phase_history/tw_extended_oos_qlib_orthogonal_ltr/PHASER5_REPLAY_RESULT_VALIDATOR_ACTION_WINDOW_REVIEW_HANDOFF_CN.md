# Phase R5 ReplayResult Validator + Action Window 审查说明

生成日期：2026-06-16

## 1. 审查范围

本 handoff 供审查者复核 R5。本阶段只做 ReplayResult validator 和 modular actions `window` 字段兼容改造，不改策略语义、不接生产链路。

## 2. 修改文件

```text
scripts/run_tw_modular_config_replay_matrix.py
scripts/validate_tw_modular_artifact_contract.py
tests/unit/test_validate_tw_modular_artifact_contract.py
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_actions.csv
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER5_REPLAY_RESULT_VALIDATOR_ACTION_WINDOW_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER5_REPLAY_RESULT_VALIDATOR_ACTION_WINDOW_REVIEW_HANDOFF_CN.md
```

## 3. 必查点

请审查：

- `formal_replay_actions.csv` 是否新增 `window` 字段；
- `r2_action_key_parity_audit.csv` 是否仍为 pass；
- `baseline_not_modular_count` 是否为 0；
- `modular_not_baseline_count` 是否为 0；
- `value_mismatch_count` 是否为 0；
- ReplayResult validator 是否 `ok=true`；
- pytest 是否 `12 passed`；
- 前端、日更、旧 formal replay matrix 是否无 diff。

## 4. 建议复核命令

```bash
head -1 data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_actions.csv
cat data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/r2_action_key_parity_audit.csv
python scripts/validate_tw_modular_artifact_contract.py \
  --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json \
  --json
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
git diff -- frontend/src/views/tw-stock-monitor/index.vue \
  scripts/run_daily_tw_stock_auto_update.py \
  scripts/run_extended_oos_formal_replay_matrix.py
```

预期：

- actions header 包含 `window`；
- action key parity audit 为 pass；
- ReplayResult validator `ok=true`；
- pytest `12 passed`；
- 前端、日更、旧 formal replay matrix 无 diff。

## 5. 不应放行的情况

如发现以下任一情况，不应放行：

- action key parity 不为 pass；
- 新增 `window` 后 summary/daily_nav/actions parity 失效；
- validator 触发 replay 或写 artifact；
- 前端、日更、provider、accepted latest、monitor、broker/order 有变更。
