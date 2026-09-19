---
created_at: 2026-06-22T12:09:10+00:00
status: executed_pal2_minimal_eiie_cnn_training
phase: PAL2_MINIMAL_EIIE_CNN_TRAINING
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PAL_PAPER_ALIGNED_PORTFOLIO_ALLOCATION_RL_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_PAL2_MINIMAL_EIIE_CNN_TRAINING_WORK_CN.md
artifact_root: data_tw/experiments/paper_aligned_portfolio_rl/pal2_minimal_eiie_cnn_training
strict_test_used: false
production_allowed: false
readonly_only: true
simulation_only: true
recommendation: STOP_NO_STRICT_TEST_REQUEST
---

# PAL2 Minimal EIIE-CNN Training 执行报告

## 1. Scope

本轮只执行 work doc 授权的 `PAL2_FEAS_EIIE_CNN_MIN_CPU`：

```text
algorithm = EIIE_CNN_with_PVM
topk = 20
lookback = 20
feature_channels = 8
episode_count = 32
batch_count = 128
seeds = [11, 23, 37]
train = 2023-01-01..2024-12-31
validation = 2025-01-01..2025-12-31
strict_test_used = false
```

未执行 strict_test，未进入 PAL3，未输出 OrderIntent / target_weight / target_position / quantity / broker order，未接入 provider/latest/monitor/frontend/Agent/broker/production。

## 2. Training

训练使用 PAL1 冻结的 top20/lookback20/8-channel allocation environment 口径，从 frozen qlib signal 与价格库重建 price tensor，并在 PyTorch 中训练最小 EIIE-CNN with previous portfolio memory input。

```text
train_state_count = 401
validation_state_count = 198
checkpoint_count = 12
train_curve_rows = 12288
```

## 3. Validation Selection

PAL1 validation baseline after-fee-tax return：

```text
0.95376753
```

本轮只做一次 final validation replay / selection audit。selected seed：

```text
seed = 11
validation_net_return_after_fee_tax = 0.66673752
excess_return_after_fee_tax = -0.28703001
```

seed stability：

```text
above_baseline_seed_count = 0 / 3
seed_stability_pass = False
```

## 4. Gate

```text
validation_after_fee_tax_above_baseline = False
turnover_cost_concentration_clone_audit_pass = False
strict_test_used = false
pal2_minimal_validation_gate_pass = False
recommendation = STOP_NO_STRICT_TEST_REQUEST
```

若 validation 未超过 baseline，本报告按 work doc STOP，不请求 strict_test。

## 5. Artifacts

主要产物：

```text
manifest.json
training_config.json
model_checkpoint_manifest.json
train_curve.csv
allocation_diagnostic_action_sample.csv
allocation_replay_ledger_train.csv
allocation_replay_ledger_validation.csv
validation_replay_metrics.csv
validation_selection_audit.csv
seed_stability_audit.csv
turnover_cost_audit.csv
cost_sensitivity_audit.csv
concentration_audit.csv
baseline_clone_audit.csv
forbidden_feature_and_consumer_audit.csv
validator_report.json
golden_samples_report.json
```

## 6. Boundary

本轮是 minimal/lite training evidence，不是完整论文方法最终成功或失败结论。allocation vector 仅作为 `AllocationDiagnosticArtifact` 风格诊断输出，用于 readonly research replay。
