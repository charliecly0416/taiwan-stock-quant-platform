# POLICY_MTR1_QLIB_ONLY_ORDER_INTENT_PARITY_AND_MECHANISM_REPLAY_EXECUTION_REPORT_CN

生成日期：2026-06-28

## 1. Verdict

```text
PASS_MTR1_QLIB_ONLY_WITH_MECHANISM_CANDIDATE
```

本次只使用 qlib-only 标准 ModelSignalArtifact，未使用 qlib+LTR、LTR private artifacts、收益后验扩展候选、provider/latest、frontend/API/Agent/daily 或 broker/quick-trade。

## 2. 输入冻结

- signal manifest: `data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json`
- strategy dependency: `configs/strategy_dependencies/mechanism_transfer_top50_cost_aware_v1.yaml`
- output_dir: `data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay`
- M5/C4: deferred，未运行。

## 3. 冻结阈值

- small_tolerance: `0.02`
- material_turnover_reduction: `0.2`
- material_cost_reduction: `0.2`
- max_drawdown_worse_tolerance: `0.05`
- cash_no_trade_degenerate_threshold: `0.1`

## 4. M0 Parity

- OrderIntent parity: `pass`
- Replay metric parity: `pass`

## 5. Baseline 与 Best Mechanism

| item | candidate | net | turnover | fee_tax | max_drawdown | gate |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| baseline | baseline_top50_exit_one_worst_sell | 11.82112201 | 0.17115347 | 1244140.76 | -0.32496728 | n/a |
| best | M2_hold_rank_buffer_100 | 13.71864776 | 0.1024199 | 784348.68 | -0.35223608 | True |

## 6. 输出清单

```text
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/manifest.json
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/input_signal_lineage_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/dependency_validation_report.json
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/order_intent_artifact_index.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/order_intent_validator_report.json
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/baseline_order_intent_parity_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/replay_artifact_index.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/replay_validator_report.json
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/baseline_replay_parity_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/mechanism_candidate_contract.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/mechanism_replay_comparison.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/turnover_cost_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/holding_overlap_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/rank_overlap_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/cash_no_trade_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/forbidden_field_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/forbidden_action_audit.csv
```

## 7. Recommendation

```text
MTR1 qlib-only 可作为 readonly research candidate 继续审查；MTR2 仍必须等待 qlib+LTR 标准 ModelSignalArtifact lineage repair。不得切 production/default/frontend/API/Agent/daily/provider/latest。
```
