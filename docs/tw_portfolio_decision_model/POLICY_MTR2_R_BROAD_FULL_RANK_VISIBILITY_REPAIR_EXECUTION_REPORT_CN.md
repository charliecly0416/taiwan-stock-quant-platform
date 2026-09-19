# POLICY_MTR2_R_BROAD_FULL_RANK_VISIBILITY_REPAIR_EXECUTION_REPORT_CN

生成日期：2026-06-28

## 1. Verdict

```text
PASS_MTR2_R_WITH_BROAD_FULL_RANK_TRANSFER_CANDIDATE
```

MTR2_R 已生成 research-only broad full-rank qlib+LTR signal artifact，并只用它做 baseline parity 与预声明 M2 transfer replay。未替换产品默认长 ID，未修改 production/default/frontend/API/Agent/daily/provider/latest。

## 2. Scope

- broad artifact: `data_tw/artifacts/signals/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025_broad_full_rank_mtr2_r/r1_broad_full_rank_visibility_repair_20260628/manifest.json`
- output_dir: `data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair`
- candidates: `M0_baseline_parity`, `M2_hold_rank_buffer_75`, `M2_hold_rank_buffer_100`
- non-goals confirmed: no training, no tuning, no posthoc expansion, no provider/latest/default switch, no broker/order/quick-trade, no target_weight/target_position.

## 3. Broad Signal

- row_count: `11837`
- window: `2026-01-02..2026-05-07`
- daily row count min: `149`，通过工作文档 `>=100` gate。
- top50 rows keep MTR2 top50-only LTR values equivalent.
- non-top50 rows are visibility-only and forbidden as buy candidates.

## 4. Candidate Metrics

| candidate | net | turnover | fee+tax | max_drawdown | hold_buffer_trigger_count | non_top50_buy_intent_count | gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| baseline_top50_exit_one_worst_sell | 0.87459073 | 0.17040339 | 48476.04 | -0.13675456 | 0 | 0 | False |
| M0_baseline_parity | 0.87459073 | 0.17040339 | 48476.04 | -0.13675456 | 0 | 0 | False |
| M2_hold_rank_buffer_75 | 1.096829 | 0.10496683 | 32769.85 | -0.14269324 | 30 | 0 | False |
| M2_hold_rank_buffer_100 | 1.32852091 | 0.07651037 | 23979.01 | -0.10619259 | 61 | 0 | True |

## 5. Gate Summary

- baseline net: `0.87459073`
- M2_hold_rank_buffer_100 net: `1.32852091`
- M2 turnover reduction: `0.55100441`
- M2 fee/tax reduction: `0.50534305`
- M2 hold buffer trigger count: `61`
- M2 non-top50 buy intent count: `0`

## 6. Output Files

```text
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/manifest.json
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/broad_signal_lineage_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/top50_ltr_equivalence_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/non_top50_buy_forbidden_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/baseline_order_intent_parity_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/baseline_replay_parity_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/mechanism_replay_comparison.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/hold_buffer_trigger_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/non_top50_buy_attempt_audit.csv
```

## 7. Recommendation

`PASS` 候选只能作为 readonly research candidate；是否进入 robustness / production readiness 必须另开阶段。
