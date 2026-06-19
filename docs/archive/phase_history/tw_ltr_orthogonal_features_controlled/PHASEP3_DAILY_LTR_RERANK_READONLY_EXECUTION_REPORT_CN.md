# Phase P3 执行报告：Daily LTR Rerank Readonly Candidate

生成时间：`2026-06-17T18:49:24+00:00`

## 1. 结论

- 默认策略仍为 `fresh qlib / rank_rotate_top50_adaptive_score`。
- 本轮只做 frozen O4 模型的 daily scoring / rerank，没有重训。
- LTR candidate 只使用 qlib Top50，未扩大候选池。
- 当前 asof：`2026-06-17`，top50 input/scored：`50/50`。
- PIT 结果：`True`。
- 当前状态：`ready`。

## 2. 输入

- `qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json`
- `qlib_pipeline/data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260617_20260617T103815Z/top50_signals.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_treatment_model.pkl`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_feature_whitelist.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/normalized_feature_daily.csv`

## 3. 输出

- `data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-17_top50.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-17_feature_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-17_pit_audit.json`
- `data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-17_summary.json`
- `data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_latest.json`

## 4. 安全与回归

- 未触发 broker / orders / quick-trade / positions。
- 未写 monitor config / scan / alerts。
- 未切 accepted latest，未触发 provider publish / refresh。
- 默认 fresh qlib 链路不受影响，仅写本地只读研究 artifact。

## 5. 风险

- O2 正交日表当前可用到 `2026-06-10` 的 trade_date / `2026-06-11` 的 available_at，P3 采用 as-of join，不补未来数据。
- 若后续要把这条候选接到展示层，仍应保持只读语义。

## 6. Gate

```text
phase_p3_daily_ltr_rerank_readonly_candidate_ready_for_review
```
