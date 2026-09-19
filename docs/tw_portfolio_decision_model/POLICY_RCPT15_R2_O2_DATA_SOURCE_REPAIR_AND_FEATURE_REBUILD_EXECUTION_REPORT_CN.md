# RCPT15_R2 O2 Data Source Repair And Feature Rebuild 执行报告

生成时间：`2026-06-26T03:48:04+00:00`

## 1. 结论

- gate: `PASS_READY_FOR_RCPT15_R3_ISOLATED_RERANK`
- shadow symbol union count: `99`
- candidate O2 rows: `207050`
- candidate O2 max trade date: `2026-06-25`
- candidate O2 max available_at: `2026-06-26`
- no signal input dates excluded from O2 gate: `2026-06-19`

## 2. 为什么自动日更没有这些数据

日更脚本有运行，但默认 M3 readonly path 只更新价格日线；job argv 中有 `--no-institutional` 与 `--no-margin`，所以不会补 O2 所需的法人/融资融券源。
同时 `provider_publish_triggered=false`、`latest_signal_updated=false`、`qlib_legacy_provider_path_skipped=true`，因此不会自动推进正式 qlib/LTR/O2 下游。

## 3. 输出

- `data_tw/experiments/risk_control_policy_2022/rcpt15_r2_o2_data_source_repair_and_feature_rebuild/source_repair_attempts.csv`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r2_o2_data_source_repair_and_feature_rebuild/source_repair_summary.csv`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r2_o2_data_source_repair_and_feature_rebuild/candidate_o2_normalized_feature_daily.csv`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r2_o2_data_source_repair_and_feature_rebuild/shadow_target_o2_coverage.csv`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r2_o2_data_source_repair_and_feature_rebuild/daily_auto_update_gap_evidence.csv`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r2_o2_data_source_repair_and_feature_rebuild/forbidden_scope_audit.csv`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r2_o2_data_source_repair_and_feature_rebuild/validator_report.json`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r2_o2_data_source_repair_and_feature_rebuild/manifest.json`

## 4. 禁止动作

- 未 provider publish。
- 未 accepted latest switch。
- 未写 latest_signal / daily_ltr_rerank_latest / latest_orthogonal_features_latest。
- 未输出 OrderIntent / target / broker artifact。
