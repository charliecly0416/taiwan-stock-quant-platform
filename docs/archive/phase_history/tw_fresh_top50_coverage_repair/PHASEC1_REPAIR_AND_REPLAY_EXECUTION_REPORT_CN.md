# Phase C1 离线覆盖修复与只读 Replay 执行报告

生成时间：2026-06-15T07:34:01+00:00

## 结论

repaired fresh top50 覆盖为 `150/150.0/150`，达到目标。full universe 下 repaired fresh top50 return `0.801662`，Phase1C anchor `0.721631`，差值 `0.080031`。

根据审计意见，本修订版同时输出两套 common universe：`frozen_s2f_common_universe` 与 `repaired_pairwise_common_universe`。C2 如需回答与 Phase A2/S2F 冻结 anchor 的 common 对照，应优先使用 frozen S2F common 口径；pairwise common 仅用于解释 repaired 覆盖过滤影响。

不得据此修改前端或切换默认策略，C2 前端影响判断仍需单独审查。

## Source Provenance

- repaired source：`data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_raw_score_rank.csv` + 本地 normalized price + `scripts/build_tw_ltr_s2c_fresh_samples.py` 的历史特征构建逻辑。
- replay engine：`scripts/evaluate_tw_ltr_s2d_full_daily_replay.py`，费用、税费、持仓数、next-day execution 与 S2F/Phase1C anchor 一致。
- repaired artifact schema：`data_tw/experiments/fresh_top50_coverage_repair/phasec1_repaired_artifact_schema.json`。

## Coverage

- original fresh top50 daily rows：`88 / 109.0 / 150`。
- repaired fresh top50 daily rows：`150 / 150.0 / 150`。

## Full Universe Metrics

| method | fee_tax_adjusted_net_return | max_drawdown | action_count | fee_and_tax | missing_price_days | skipped_trade_count | relative_return_vs_phase1c_anchor |
| --- | --- | --- | --- | --- | --- | --- | --- |
| phase1c_anchor_simple | 0.721631 | -0.05083 | 405 | 157661.34 | 0 | 0 | 0.0 |
| original_fresh_top50_adaptive | 0.662457 | -0.088396 | 410 | 155259.42 | 0 | 0 | -0.059174 |
| repaired_fresh_top50_adaptive | 0.801662 | -0.085205 | 410 | 161853.68 | 0 | 0 | 0.080031 |
| original_fresh_ltr | 0.544381 | -0.132896 | 408 | 145915.05 | 0 | 0 | -0.17725 |

## Frozen S2F Common Universe

- definition：Phase1C anchor ∩ original fresh top50 ∩ original fresh LTR。
- key count：`22474`。
- Phase1C common return / max DD：`0.641235 / -0.076739`。

| method | fee_tax_adjusted_net_return | max_drawdown | action_count | fee_and_tax | missing_price_days | skipped_trade_count | relative_return_vs_phase1c_anchor |
| --- | --- | --- | --- | --- | --- | --- | --- |
| phase1c_anchor_simple | 0.641235 | -0.076739 | 405 | 149876.44 | 0 | 0 | 0.0 |
| original_fresh_top50_adaptive | 0.625943 | -0.088431 | 410 | 153601.13 | 0 | 0 | -0.015292 |
| repaired_fresh_top50_adaptive | 0.625943 | -0.088431 | 410 | 153601.13 | 0 | 0 | -0.015292 |

## Repaired Pairwise Common Universe

- definition：Phase1C anchor ∩ original fresh top50 ∩ repaired fresh top50。
- key count：`22523`。
- 该口径下 Phase1C common return 从 frozen S2F 的 `0.641235` 变为 `0.697914`，原因是该 key set 不要求 original fresh LTR score，且包含不同的 date/instrument 交集；它不是 Phase A2/S2F 冻结 common。

| method | fee_tax_adjusted_net_return | max_drawdown | action_count | fee_and_tax | missing_price_days | skipped_trade_count | relative_return_vs_phase1c_anchor |
| --- | --- | --- | --- | --- | --- | --- | --- |
| phase1c_anchor_simple | 0.697914 | -0.076583 | 405 | 154568.25 | 0 | 0 | 0.0 |
| original_fresh_top50_adaptive | 0.66315 | -0.088516 | 410 | 155311.67 | 0 | 0 | -0.034764 |
| repaired_fresh_top50_adaptive | 0.66315 | -0.088516 | 410 | 155311.67 | 0 | 0 | -0.034764 |

## Feature Complete Definition Audit

`feature_complete` 表示 LTR 全特征合同完整，不等同于 fresh top50 adaptive 必需字段完整。repaired top50 replay 只依赖 `adaptive_score_baseline`、本地价格和 next-day execution；score 缺失行会被 replay ranking 的 `dropna(score_col)` 排除。早期 `feature_complete=0` 不阻断 replay，因为 adaptive 必需字段仍大多可用。

| field | used_by_repaired_top50_replay | impact |
| --- | --- | --- |
| feature_complete | False | Rows can have feature_complete=false while adaptive_score_baseline is available. |
| adaptive_required_fields | True | Rows with adaptive_score_baseline null are excluded from candidate ranking by replay dropna on score column. |
| price | True | Missing execution/mark-to-market prices would appear in missing/skipped/last-day audits. |
| adaptive_nonnull | True | Daily candidate ranking uses these non-null rows; early days still have at least 148-149 non-null rows, above top10 holding needs. |

## Next-day / Fee / Action Audit

| method | active_action_count | execution_date_after_signal_date | missing_price_days | skipped_trade_count | last_day_new_trade_without_next_price_count | pass |
| --- | --- | --- | --- | --- | --- | --- |
| repaired_fresh_top50_adaptive | 410 | True | 0 | 0 | 0 | yes |

- repaired action_count：`410`，buy_count：`204`，sell_count：`206`。这些均为历史回放统计。
- fee_rate：`0.001425`，tax_rate：`0.003`，fee_and_tax：`161853.68`。

## Real PnL Contribution

Top symbols：

| symbol | realized_pnl | unrealized_pnl | fee_tax_allocated | net_pnl | share_of_total_net_pnl |
| --- | --- | --- | --- | --- | --- |
| TW8358 | 94875.0 | 0.0 | 4402.09 | 90472.91 | 0.112857 |
| TW2337 | 60562.0 | 0.0 | 2866.23 | 57695.77 | 0.07197 |
| TW6683 | 58260.0 | 0.0 | 2963.95 | 55296.05 | 0.068977 |
| TW8110 | 58568.5 | 0.0 | 6621.35 | 51947.15 | 0.064799 |
| TW4989 | 54039.5 | 0.0 | 3172.28 | 50867.22 | 0.063452 |

Worst symbols：

| symbol | realized_pnl | unrealized_pnl | fee_tax_allocated | net_pnl | share_of_total_net_pnl |
| --- | --- | --- | --- | --- | --- |
| TW6285 | -23930.0 | 0.0 | 1853.1 | -25783.1 | -0.032162 |
| TW3189 | -22030.0 | 0.0 | 2322.03 | -24352.03 | -0.030377 |
| TW6919 | -15537.0 | 0.0 | 5108.16 | -20645.16 | -0.025753 |
| TW6510 | -17700.0 | 0.0 | 2675.28 | -20375.28 | -0.025416 |
| TW3260 | -16272.14 | 0.0 | 3204.14 | -19476.28 | -0.024295 |

Top days：

| date | realized_pnl | unrealized_pnl | fee_tax_allocated | net_pnl | share_of_total_net_pnl |
| --- | --- | --- | --- | --- | --- |
| 2026-04-20 | 99390.0 | 53080.0 | 2852.8 | 149617.2 | 0.186634 |
| 2026-01-19 | 47532.07 | 38203.6 | 1652.34 | 84083.33 | 0.104886 |
| 2026-01-20 | 44050.0 | 37264.02 | 1630.23 | 79683.79 | 0.099398 |
| 2025-10-07 | 35698.95 | 43404.82 | 1446.44 | 77657.33 | 0.09687 |
| 2025-08-11 | 27983.5 | 44543.0 | 1162.98 | 71363.52 | 0.089019 |

## Outlier Audit

| audit_item | value | status | note |
| --- | --- | --- | --- |
| repaired_coverage_min_median_max | 150/150.0/150 | ok | coverage target min>=145 median>=149 max<=150 |
| real_pnl_total_vs_nav_gain | 0.33 | ok | symbol-level net PnL sum minus repaired final equity gain |
| top_symbol_abs_share_of_total_net_pnl | 0.112857 | ok | single-symbol contribution concentration threshold 0.35 |
| top_day_abs_share_of_total_net_pnl | 0.186634 | ok | single-day contribution concentration threshold 0.35 |
| max_abs_daily_nav_return | 0.041689 | ok | abnormal daily return threshold 0.12 |
| max_action_price | 7100.0 | info | historical replay action price sanity sample maximum |
| repaired_vs_phase1c_full_return_diff | 0.080031 | info | positive means repaired fresh top50 above Phase1C anchor |

## Fresh LTR 说明

repaired fresh LTR 未生成：现有冻结 LTR score 只覆盖原 post-filter 行，扩展到 repaired 新增行需要新的 LTR score 生产；本轮目标是 fresh top50 adaptive 覆盖修复，避免混入 LTR score 变更。

## 产物

- `data_tw/experiments/fresh_top50_coverage_repair/phasec1_repaired_replay_ready_scores.csv`
- `data_tw/experiments/fresh_top50_coverage_repair/phasec1_coverage_by_day.csv`
- `data_tw/experiments/fresh_top50_coverage_repair/phasec1_full_universe_metrics.csv`
- `data_tw/experiments/fresh_top50_coverage_repair/phasec1_frozen_s2f_common_universe_metrics.csv`
- `data_tw/experiments/fresh_top50_coverage_repair/phasec1_repaired_pairwise_common_universe_metrics.csv`
- `data_tw/experiments/fresh_top50_coverage_repair/phasec1_common_universe_key_audit.csv`
- `data_tw/experiments/fresh_top50_coverage_repair/phasec1_feature_complete_definition_audit.csv`
- `data_tw/experiments/fresh_top50_coverage_repair/phasec1_daily_nav.csv`
- `data_tw/experiments/fresh_top50_coverage_repair/phasec1_action_audit.csv`
- `data_tw/experiments/fresh_top50_coverage_repair/phasec1_next_day_accounting_audit.csv`
- `data_tw/experiments/fresh_top50_coverage_repair/phasec1_real_pnl_contribution_by_symbol.csv`
- `data_tw/experiments/fresh_top50_coverage_repair/phasec1_real_pnl_contribution_by_day.csv`
- `data_tw/experiments/fresh_top50_coverage_repair/phasec1_outlier_audit.csv`
- `data_tw/experiments/fresh_top50_coverage_repair/phasec1_summary.json`

## 边界

未训练 qlib/LTR，未改 Phase1C anchor，未改费用税费/next-day execution/持仓数量/窗口，未改前端/API，未触发 provider/accepted latest/monitor/交易链路。
