# Phase C3 执行报告：Repaired Fresh Top50 Asof-Aware 与 Replay-Ready 合同审计

生成时间：2026-06-15T08:20:07+00:00

## 1. 执行范围

- 审计窗口：`2025-07-01..2026-05-07`。
- 输入 repaired artifact：`data_tw/experiments/fresh_top50_coverage_repair/phasec1_repaired_replay_ready_scores.csv`。
- instrument range：`qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt`。
- dynamic universe 辅助审计：`qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/universe/tw_liquid_dyn.txt`。
- accepted prediction universe：`qlib_pipeline/data_tw/experiments/option_c_forward_validation/timed_data_availability_retry_20260601T101323Z/symbols_accepted_prediction_universe.txt`。
- 本阶段只做 coverage / asof / replay-ready 合同审计，不使用收益率证明策略优劣。

## 2. 总体结论

- repaired rows：`150 / 150.0 / 150`。
- eligible rows：`30750` / `30750`，daily min `150`。
- replay-ready rows：`30630` / `30750`，daily min `148`。
- instrument 有效期违规 / 未来倒灌 rows：`0`。
- missing next-day execution price rows：`100`。
- recommended gate：`phase_c3_blocked_requires_universe_contract_repair`。

## 3. Asof-Aware Eligibility

option_c `all.txt` 的 start/end 区间作为硬 eligibility 门槛；accepted prediction universe 作为静态 150 合同核对。目标窗口内未发现 instrument 起始日前进入或结束日后继续进入的记录。

`tw_liquid_dyn` 本轮只作为辅助动态流动性覆盖审计，不作为硬门槛；若将其作为硬门槛，会重新制造 C1 已修复的 S2B post-filter 覆盖收缩。

## 4. Replay-Ready Audit

| reason | row_count |
| --- | --- |
| outside_option_c_instrument_range | 0 |
| not_in_accepted_prediction_universe | 0 |
| missing_current_price | 100 |
| missing_next_execution_price | 100 |
| missing_adaptive_score | 120 |
| missing_ret20 | 120 |
| missing_volatility20 | 120 |
| missing_twii_ret20 | 0 |
| feature_complete_false_ltr_full_feature_aux | 1020 |
| outside_tw_liquid_dyn_range_aux_only | 8082 |

说明：`feature_complete=false` 是 LTR 全特征合同不完整，不等于 fresh top50 adaptive 不可 replay。C3 replay-ready 硬条件是 qlib score、current price、next execution price、adaptive score、ret20、volatility20、TWII_ret20 与 asof eligibility。

## 5. 是否存在阻断项

- 未来上市 / 无效期股票倒灌：`0`。
- 有 score 但缺 next-day execution price：`100`。
- 有 repaired row 但缺 adaptive score：`120`。
- 有 repaired row 但缺 current price：`100`。

## 6. 后续建议

C3 合同审计通过时，可以准备前端只读展示合同，把 repaired fresh top50 作为研究候选展示；仍不直接切默认策略。严格策略收益比较必须另开 OOS / walk-forward 主线。

## 7. 安全边界

- 未训练 qlib/LTR。
- 未使用收益率证明策略优劣。
- 未修改前端/API。
- 未修改 accepted latest。
- 未触发 provider refresh / publish、monitor、broker、orders、quick-trade。
- 未输出真实买卖、仓位、收益承诺、胜率或上涨概率语义。

## 8. 输出产物

- `data_tw/experiments/fresh_top50_coverage_repair/phasec3_asof_eligibility_audit.csv`
- `data_tw/experiments/fresh_top50_coverage_repair/phasec3_replay_ready_audit.csv`
- `data_tw/experiments/fresh_top50_coverage_repair/phasec3_daily_coverage_summary.csv`
- `data_tw/experiments/fresh_top50_coverage_repair/phasec3_replay_ready_reason_summary.csv`
- `data_tw/experiments/fresh_top50_coverage_repair/phasec3_summary.json`
