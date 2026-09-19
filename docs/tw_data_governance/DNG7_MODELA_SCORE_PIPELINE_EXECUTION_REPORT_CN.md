# DNG7 ModelA Score Pipeline 执行报告

生成时间：2026-09-18T10:39:08+00:00

## 1. 结论

- 执行状态：`SCORED_ASOF_TARGET`
- run_id：`dng9_daily_auto_model_signal_gate_20260918_20260918T103846Z`
- 目标 asof：`2026-09-18`
- 路径：`TRUE_LOCAL_INFERENCE`
- 是否生成 2026-09-18 qlib Model A score：`YES`

## 2. ModelInferenceInput

- validator：`PASS`
- rows：`150`
- path：`data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022/dng9_daily_auto_model_signal_gate_20260918_20260918T103846Z`

## 3. ScoreJob

- validator：`PASS`
- qlib source run：`option_c_daily_signal_20260918_20260918T103854Z`
- raw_scores rows：`150`
- path：`data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022/dng9_daily_auto_model_signal_gate_20260918_20260918T103846Z`

## 4. ModelSignalArtifact

- status：`READY`
- rows：`150`
- path：`data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng9_daily_auto_model_signal_gate_20260918_20260918T103846Z`

## 5. Forbidden Action Audit

- 未训练、未调参、未触发 LTR Model B。
- 未抓数、未 provider refresh/publish、未切 qlib accepted latest。
- 未 publish readonly/Agent latest。
- 未回放、未生成 ReplayResult/NAV、未 broker/order/quick-trade、未生成 target_position/target_weight。

## 6. DNG8 建议

ModelSignalArtifact validator 通过后，可进入 DNG8 的只读策略输入合同阶段；仍不得默认接入 readonly/Agent/latest 或 replay。
