# DNG8 Model B LTR Score Pipeline 执行报告

生成时间：2026-08-26T10:39:34+00:00

## 1. 结论

- run_id：`dng9_daily_auto_model_signal_gate_20260826_20260826T103910Z`
- 目标 asof：`2026-08-26`
- score_status：`BLOCKED_INPUT_NOT_READY`
- LTR 是否 ready：`NO`
- 是否生成 Model B LTR signal：`NO`
- validator：`PASS`

DNG8 已建立 Model B LTR inference/ScoreJob gate，但未生成 LTR signal。原因是 DNG3 明确记录 `can_continue_to_model_b_ltr=false`，且必需正交数据未齐备。

## 2. Blocker 证据

- blocking_datasets：`corporate_actions, monthly_revenue, valuation`
- input blocker：`data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/dng9_daily_auto_model_signal_gate_20260826_20260826T103910Z/blocker_input_readiness.json`
- DNG3 readiness：`data_tw/catalog/readiness_matrix/2026-06-25/orthogonal_feature_store.json`
- input manifest：`data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/dng9_daily_auto_model_signal_gate_20260826_20260826T103910Z/manifest.json`
- score manifest：`data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/dng9_daily_auto_model_signal_gate_20260826_20260826T103910Z/manifest.json`

阻断语义：`corporate_actions`、`monthly_revenue`、`valuation` 仍未作为完整 PIT-safe canonical orthogonal feature family 放行；因此 LTR 特征 schema 与当前 DNG3 store 不能证明齐备。

## 3. Fallback 语义

- fallback_allowed：`qlib_only_if_strategy_contract_allows`
- fallback 只能引用：`data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng7_modela_20260625`
- fallback 不是 Model B LTR score；不得用 qlib score 冒充 LTR `buy_score/raw_score/score_rank`。
- 下游只有在 strategy dependency/contract 显式允许 qlib-only fallback 时，才能消费 DNG7 Model A。

## 4. LTR Top50 合同

- LTR 若未来放行，只能在 DNG7 Model A qlib top50 内 rerank。
- `candidate_rank` 与 `full_qlib_rank` 必须来自 DNG7 Model A。
- `buy_score` 与 `score_rank` 才能来自 LTR；本轮没有生成这些 LTR 字段。

## 5. Validator 输出

- status：`PASS`
- ok：`True`
- errors：`[]`
- catalog validation：`data_tw/catalog/dng8_modelb_ltr_score_pipeline_validation.json`

## 6. Forbidden Action Audit

- 未模型训练、未调参、未 LTR inference、未 LTR score 生成。
- 未真实抓数、未 provider refresh/publish、未 qlib accepted latest switch。
- 未 readonly/Agent publish。
- 未策略收益回放、未 ReplayResult/NAV。
- 未 broker/order/quick-trade，未生成 target_position/target_weight。

## 7. DNG9 建议

不建议进入会自动生成 Model B LTR signal 的 DNG9。可以进入 DNG9 daily auto model-signal gate integration 的前提是：只集成 gate/blocker 语义，并在 DNG3 仍为 blocked 时继续输出 `BLOCKED_INPUT_NOT_READY`；若要生成真实 LTR signal，必须先完成外部数据修复并重新通过 DNG3。
