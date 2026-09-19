# POLICY_MTR2_QLIB_LTR_LINEAGE_REPAIR_AND_TRANSFER_REPLAY_EXECUTION_REPORT_CN

生成日期：2026-06-28

## 1. Verdict

```text
FAIL_NEEDS_REPAIR
```

本次先由短 ID 标准 artifact 同源派生产品长 ID qlib+LTR 标准 ModelSignalArtifact，再只使用长 ID 标准信号做 baseline parity 与 M2 transfer replay。未使用 LTR private artifacts、未把短 ID 作为策略输入、未收益后验扩展候选、未触碰 provider/latest、frontend/API/Agent/daily 或 broker/quick-trade。

## 2. Scope

- assigned phase: `POLICY_MTR2_QLIB_LTR_LINEAGE_REPAIR_AND_TRANSFER_REPLAY`
- goal: 修复产品长 ID qlib+LTR 标准 `ModelSignalArtifact`，然后在该长 ID 信号上跑 baseline parity 与 `M2_hold_rank_buffer_100` transfer replay。
- non-goals confirmed: 未训练、未调参、未扩候选、未改 production/default/frontend/API/Agent/daily/provider/latest、未触发 broker/order/quick-trade。

## 3. Documents / Contracts / Skills Read

```text
docs/tw_portfolio_decision_model/POLICY_MTR2_QLIB_LTR_LINEAGE_REPAIR_AND_TRANSFER_REPLAY_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_MTR_MECHANISM_TRANSFER_TO_BASELINE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_MTR0_CONTRACT_AND_BASELINE_PARITY_FEASIBILITY_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_MTR1_QLIB_ONLY_ORDER_INTENT_PARITY_AND_MECHANISM_REPLAY_REVIEW_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md
docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md
configs/strategy_dependencies/mechanism_transfer_top50_cost_aware_v1.yaml
```

## 4. 输入冻结

- signal manifest: `data_tw/artifacts/signals/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/r1_legacy_signal_adapter_20260616/manifest.json`
- source short-id manifest for lineage repair only: `data_tw/artifacts/signals/e4_frozen_qlib_2023_2025_ltr/r1_legacy_signal_adapter_20260616/manifest.json`
- strategy dependency: `configs/strategy_dependencies/mechanism_transfer_top50_cost_aware_v1.yaml`
- output_dir: `data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_qlib_ltr_lineage_repair_and_transfer_replay`
- candidates: `M0_baseline_parity`, `M2_hold_rank_buffer_75`, `M2_hold_rank_buffer_100`。

## 5. MTR2-A Lineage Repair

- status: `pass`
- long ID artifact 已生成：`data_tw/artifacts/signals/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/r1_legacy_signal_adapter_20260616/manifest.json`
- short/long equivalence: `pass`，row count `3950 -> 3950`，date/instrument key 一致，除 `model_name` 改为产品长 ID 外值一致。
- signal window: `2026-01-02..2026-05-07`
- daily row count min: `50`
- model family: `ltr`
- capabilities: `core_signal_v1`, `candidate_boundary=qlib_top50`, `buy_ordering=buy_score_desc`, `full_rank_exit=full_qlib_rank`, `supports_ltr_rerank=true`

## 6. 冻结阈值

- small_tolerance: `0.02`
- material_turnover_reduction: `0.2`
- material_cost_reduction: `0.2`
- max_drawdown_worse_tolerance: `0.05`
- cash_no_trade_degenerate_threshold: `0.1`

## 7. MTR2-B Baseline Parity

- OrderIntent parity: `pass`
- Replay metric parity: `pass`

## 8. MTR2-C Transfer Replay

| item | candidate | net | baseline_delta | turnover | fee_tax | max_drawdown | gate |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| baseline | baseline_top50_exit_one_worst_sell | 1.01456308 | 0.0 | 0.16451926 | 48978.65 | -0.12723523 | n/a |
| audit control | M2_hold_rank_buffer_75 | 1.01456308 | 0.0 | 0.16451926 | 48978.65 | -0.12723523 | False |
| main candidate | M2_hold_rank_buffer_100 | 1.01456308 | 0.0 | 0.16451926 | 48978.65 | -0.12723523 | False |

M2_75 与 M2_100 都与 baseline 完全等价，未降低 turnover / fee_tax，因此未通过 MTR2 gate。

## 9. Failure Analysis / Repair Need

失败原因不是 baseline parity 或 replay validator 失败，而是当前长 ID 标准信号是由短 ID artifact 严格等价派生；短 ID artifact 每日只有 qlib top50 的 50 行。`M2_hold_rank_buffer_75/100` 需要看到持仓跌出 top50 后是否仍处于 `full_qlib_rank <= 75/100`，但标准信号缺少 51-100 乃至 broad universe 行，因此跌出 top50 的持仓在策略日状态中没有可见 full-rank，hold buffer 条件无法触发，机制退化为 baseline。

上游 `phasee1_raw_oos_score_rank_2023_2026.csv` / E3 lineage 存在 broad qlib rank 证据，但 MTR2 工作文档本轮要求若由短 ID 派生则必须保持 row count/key/value 与短 ID 可审计一致。因此本执行者没有擅自把长 ID signals 扩到 150 行继续 replay。下一步应开 MTR2 repair：冻结并生成 `qlib broad full-rank + top50 LTR buy_score` 的标准 ModelSignalArtifact 合同版本，或者新增可被策略合法消费的 `ext_full_rank_broad`/holding-rank lookup 合同，再重跑 M2 transfer。

## 10. 输出清单

```text
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_qlib_ltr_lineage_repair_and_transfer_replay/manifest.json
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_qlib_ltr_lineage_repair_and_transfer_replay/lineage_repair_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_qlib_ltr_lineage_repair_and_transfer_replay/long_id_short_id_equivalence_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_qlib_ltr_lineage_repair_and_transfer_replay/input_signal_lineage_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_qlib_ltr_lineage_repair_and_transfer_replay/model_signal_validator_report.json
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_qlib_ltr_lineage_repair_and_transfer_replay/dependency_validation_report.json
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_qlib_ltr_lineage_repair_and_transfer_replay/order_intent_artifact_index.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_qlib_ltr_lineage_repair_and_transfer_replay/order_intent_validator_report.json
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_qlib_ltr_lineage_repair_and_transfer_replay/baseline_order_intent_parity_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_qlib_ltr_lineage_repair_and_transfer_replay/replay_artifact_index.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_qlib_ltr_lineage_repair_and_transfer_replay/replay_validator_report.json
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_qlib_ltr_lineage_repair_and_transfer_replay/baseline_replay_parity_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_qlib_ltr_lineage_repair_and_transfer_replay/mechanism_candidate_contract.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_qlib_ltr_lineage_repair_and_transfer_replay/mechanism_replay_comparison.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_qlib_ltr_lineage_repair_and_transfer_replay/turnover_cost_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_qlib_ltr_lineage_repair_and_transfer_replay/holding_overlap_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_qlib_ltr_lineage_repair_and_transfer_replay/rank_overlap_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_qlib_ltr_lineage_repair_and_transfer_replay/cash_no_trade_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_qlib_ltr_lineage_repair_and_transfer_replay/forbidden_field_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_qlib_ltr_lineage_repair_and_transfer_replay/forbidden_action_audit.csv
```

## 11. Forbidden Actions Audit

```text
no_training
no_tuning
no_posthoc_candidate_expansion
no_private_ltr_strategy_input
no_short_id_strategy_input_bypass
no_provider_publish
no_accepted_latest_switch
no_production_default_switch
no_frontend_api_agent_daily_change
no_broker_order_quick_trade
no_target_weight_position_quantity_instruction
```

## 12. Files Changed

```text
scripts/run_tw_policy_mtr2_qlib_ltr_lineage_repair_and_transfer_replay.py
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/r1_legacy_signal_adapter_20260616/
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_qlib_ltr_lineage_repair_and_transfer_replay/
docs/tw_portfolio_decision_model/POLICY_MTR2_QLIB_LTR_LINEAGE_REPAIR_AND_TRANSFER_REPLAY_EXECUTION_REPORT_CN.md
```

## 13. Recommendation

```text
FAIL_NEEDS_REPAIR。不要进入 MTR3。建议审查者授权 MTR2_R：修复 qlib+LTR 标准信号的 broad full-rank 可见性，使 hold buffer 75/100 机制可表达后再重跑 baseline parity 与 M2 transfer replay。
```
