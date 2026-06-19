# Phase R4 Validator / Registry 审查说明

生成日期：2026-06-16

## 1. 审查范围

本 handoff 供审查者复核 R4。R4 只实现 validator / registry / capability metadata backfill，不改变 R1 signal 值，不改变 R2 replay 结果。

## 2. 新增 / 修改文件

```text
configs/tw_modular_registry.yaml
configs/strategy_dependencies/original.yaml
configs/strategy_dependencies/top50_exit_all.yaml
configs/strategy_dependencies/top50_exit_one_worst_sell.yaml
configs/strategy_dependencies/one_sell_one_buy_correct.yaml
configs/strategy_dependencies/one_sell_one_buy_buggy_e8r.yaml
scripts/validate_tw_modular_artifact_contract.py
tests/unit/test_validate_tw_modular_artifact_contract.py
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER4_VALIDATOR_REGISTRY_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER4_VALIDATOR_REGISTRY_REVIEW_HANDOFF_CN.md
```

Metadata-only backfill：

```text
data_tw/artifacts/signals/*/r1_legacy_signal_adapter_20260616/manifest.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
```

## 3. 必查点

请审查：

- validator 是否仍为只读；
- registry dependency paths 是否存在；
- 五个 strategy dependency 是否符合 R0-R3 边界；
- `one_sell_one_buy_buggy_e8r` 是否仍为 diagnostic only；
- capabilities backfill 是否只改 manifest metadata；
- R1 `signals.csv` 是否未改；
- R2 `formal_replay_summary.csv`、`formal_replay_actions.csv`、`formal_replay_daily_nav.csv` 是否未改；
- 前端、日更、旧 formal replay matrix 是否无 diff。

## 4. 建议复核命令

```bash
python -m py_compile scripts/validate_tw_modular_artifact_contract.py
python scripts/validate_tw_modular_artifact_contract.py \
  --artifact data_tw/artifacts/signals/fresh_qlib_adaptive/r1_legacy_signal_adapter_20260616/manifest.json \
  --strategy-dependency configs/strategy_dependencies/top50_exit_one_worst_sell.yaml \
  --json
python scripts/validate_tw_modular_artifact_contract.py \
  --artifact data_tw/artifacts/signals/fresh_qlib_adaptive/r1_legacy_signal_adapter_20260616/manifest.json \
  --registry configs/tw_modular_registry.yaml \
  --json
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
git diff -- data_tw/artifacts/signals/*/r1_legacy_signal_adapter_20260616/signals.csv \
  data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_summary.csv \
  data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_actions.csv \
  data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_daily_nav.csv \
  frontend/src/views/tw-stock-monitor/index.vue \
  scripts/run_daily_tw_stock_auto_update.py \
  scripts/run_extended_oos_formal_replay_matrix.py
```

预期：

- validator 编译通过；
- strategy dependency validation `ok=true`；
- registry validation `ok=true`；
- pytest `4 passed`；
- signals / replay result / frontend / daily / old formal replay 无 diff。

## 5. 不应放行的情况

如发现以下任一情况，不应放行 R4：

- validator 会写 artifact 或触发 replay；
- capabilities backfill 改变 signals 或 replay CSV；
- strategy dependency 允许 legacy 私有列；
- buggy_e8r 可作为 valid strategy evidence；
- 前端、日更或 provider/accepted latest/monitor/broker/order 有变更。
