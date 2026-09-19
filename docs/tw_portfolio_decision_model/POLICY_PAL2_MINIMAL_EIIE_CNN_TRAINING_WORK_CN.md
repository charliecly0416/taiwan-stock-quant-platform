---
created_at: 2026-06-22
status: reviewer_next_work_document
phase: PAL2_MINIMAL_EIIE_CNN_TRAINING_WORK
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PAL_PAPER_ALIGNED_PORTFOLIO_ALLOCATION_RL_MAINLINE_CN.md
previous_review: docs/tw_portfolio_decision_model/POLICY_PAL2_PAPER_ALIGNED_FULL_TRAINING_FEASIBILITY_REVIEW_CN.md
previous_execution_report: docs/tw_portfolio_decision_model/POLICY_PAL2_PAPER_ALIGNED_FULL_TRAINING_FEASIBILITY_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/paper_aligned_portfolio_rl/pal2_minimal_eiie_cnn_training
strict_test_authorized: false
pal3_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_position: true
not_target_weight: true
---

# PAL2 Minimal EIIE-CNN Training 工作文档

## 1. 本轮目标

你是执行者。请继续 PAL Paper-aligned Portfolio Allocation RL 主线的 PAL2。

本轮只执行：

```text
PAL2 minimal EIIE-CNN with PVM training
```

目标是在 PAL1 已冻结的 readonly allocation environment / price tensor / portfolio memory / reward accounting 上，运行一个最小但真实的 paper-aligned allocation training，并在 validation=2025 上做一次性选择审计。

本轮不是 PAL3，不允许 strict_test。

## 2. 必须读取

执行前必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_PAL_PAPER_ALIGNED_PORTFOLIO_ALLOCATION_RL_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PAL0_PAPER_CONTRACT_AUDIT_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PAL1_ALLOCATION_ENV_TENSOR_MEMORY_BUILD_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PAL2_PAPER_ALIGNED_FULL_TRAINING_FEASIBILITY_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PAL2_PAPER_ALIGNED_FULL_TRAINING_FEASIBILITY_EXECUTION_REPORT_CN.md
```

必须使用 PAL1 产物：

```text
data_tw/experiments/paper_aligned_portfolio_rl/pal1_allocation_env_tensor_memory_build/
```

必须参考 PAL2 feasibility 产物：

```text
data_tw/experiments/paper_aligned_portfolio_rl/pal2_full_training_feasibility/
```

## 3. 授权范围

本轮授权的唯一训练配置：

```text
config_id = PAL2_FEAS_EIIE_CNN_MIN_CPU
algorithm = EIIE_CNN_with_PVM
topk = 20
lookback = 20
feature_channels = 8
episode_count = 32
batch_count = 128
checkpoint_frequency = every_8_episodes
train_window = 2023-01-01..2024-12-31
validation_window = 2025-01-01..2025-12-31
strict_test_used = false
```

允许：

```text
1. 使用 PAL1 price tensor / portfolio memory / reward schema。
2. 输出 AllocationDiagnosticArtifact 风格的 allocation_weight_diagnostic / cash_weight_diagnostic。
3. 在 readonly research replay 内部做 simulated rebalance accounting。
4. 统计 after-fee-tax NAV、turnover、fee、sell tax、cost sensitivity、concentration。
5. 保存训练曲线、checkpoint manifest、validation selection audit。
```

不允许：

```text
1. 加入 EIIE-LSTM / PPO / DDPG / SAC。
2. 运行 strict_test 或读取 strict_test metrics。
3. 根据 validation 反复调参。
4. 输出 OrderIntent。
5. 输出 target_weight / target_position / quantity / broker_order。
6. provider publish / accepted latest switch。
7. monitor write / frontend default / Agent recommendation。
8. broker / quick-trade / real order。
9. 把 allocation_weight_diagnostic 改名、复制或映射为 target_weight。
10. 把本轮 lite/minimal training 声称为完整论文方法的最终成功或失败。
```

## 4. 必须实现或产出的内容

artifact root：

```text
data_tw/experiments/paper_aligned_portfolio_rl/pal2_minimal_eiie_cnn_training/
```

必须输出：

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

必须写执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_PAL2_MINIMAL_EIIE_CNN_TRAINING_EXECUTION_REPORT_CN.md
```

## 5. 训练与验证规则

训练规则：

```text
1. 只在 2023-01-01..2024-12-31 训练。
2. 不得读取 validation return 作为训练反馈。
3. 不得读取 strict_test。
4. checkpoint 每 8 episodes 输出一次 manifest 记录。
5. train curve 必须至少包含 episode、batch、train_reward_after_fee_tax、train_turnover、train_cost。
```

Validation 规则：

```text
1. 只在 2025-01-01..2025-12-31 做一次 final validation replay / selection audit。
2. selection metric 必须是 validation net_return_after_fee_tax。
3. 必须与 PAL1 baseline 对照。
4. 必须报告 gross 与 after-fee-tax，但通过条件只能使用 after-fee-tax。
5. 如果 validation 不超过 baseline，必须 STOP，不得请求 strict_test。
```

Seed stability 规则：

```text
1. 至少运行 3 个 seed。
2. 每个 seed 使用同一配置，不得为 seed 单独调参。
3. 报告每个 seed 的 validation after-fee-tax return、excess return、turnover、concentration。
4. 若只有单 seed 能超过 baseline，不得写 PAL2 通过。
```

## 6. 必须通过的 PAL2 Gate

PAL2 最小训练只有在以下全部满足时，才可建议审查者考虑 PAL2 validation pass：

```text
validation return after fee/tax > validation baseline
seed stability pass
turnover/cost audit pass
cost sensitivity audit pass
concentration audit pass
baseline_clone_audit pass
strict_test_used = false
contract audit pass
```

其中：

```text
baseline_clone_audit
```

必须证明策略不是简单复制 PAL1 baseline 排名或等权持仓，包括至少检查：

```text
allocation 与 baseline 权重/排名的相关性
现金权重是否长期异常固定
单一 symbol / 单日 / 单动作是否主导收益
```

## 7. Validator / Golden Samples 要求

`validator_report.json` 必须检查：

```text
pal1_artifact_loaded
train_window_only_for_training
validation_window_only_for_selection
strict_test_not_used
no_future_return_or_label_feature
no_realized_pnl_feature
allocation_diagnostic_suffix_only
no_target_weight
no_target_position
no_quantity
no_broker_order
no_order_intent_output
no_provider_publish
no_monitor_frontend_agent_broker_consumer
validation_metrics_exist
turnover_cost_audit_exist
cost_sensitivity_audit_exist
concentration_audit_exist
baseline_clone_audit_exist
seed_stability_audit_exist
```

`golden_samples_report.json` 必须包含正负样本：

```text
positive: AllocationDiagnosticArtifact can be consumed by PAL readonly research replay.
positive: validation replay can consume diagnostic allocation and produce after-fee-tax metrics.
negative: target_weight field must fail.
negative: OrderIntentArtifact consumer must fail.
negative: broker / quick-trade consumer must fail.
negative: strict_test metrics access must fail.
negative: validation success claim without training metrics must fail.
negative: PAL3 request without PAL2 validation gates must fail.
```

## 8. Blocker 处理

如果训练无法在当前 CPU 环境完成，执行者必须输出 blocker / feasibility update，而不是声称论文方法失败：

```text
runtime_blocker_report.md
partial_train_curve.csv, if available
checkpoint_manifest.json, if available
updated_estimated_runtime
minimum_next_viable_setting
whether_gpu_required
```

如果发现 PAL1 tensor / memory / reward accounting 有 PIT、成本、baseline parity 或合同问题，必须 STOP 并报告，不得继续训练。

## 9. 审查者下一轮重点

下一轮审查者将检查：

```text
1. 是否严格只做 PAL2 minimal EIIE-CNN。
2. 是否真实训练，而不是只输出 feasibility。
3. 是否 train / validation / strict_test 分离。
4. 是否 validation after-fee-tax return 超过 baseline。
5. seed stability 是否通过。
6. turnover/cost/cost sensitivity 是否通过。
7. concentration 是否通过。
8. baseline clone audit 是否通过。
9. 是否没有 target_weight / target_position / quantity / broker / OrderIntent。
10. 是否没有 provider/latest/monitor/frontend/Agent/production 扩权。
```

只有本轮全部通过，审查者才可建议统筹考虑是否进入 PAL3。执行者不得自行进入 PAL3。
