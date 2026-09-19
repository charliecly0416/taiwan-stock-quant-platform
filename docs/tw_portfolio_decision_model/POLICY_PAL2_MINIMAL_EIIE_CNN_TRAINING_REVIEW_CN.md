---
created_at: 2026-06-22
status: review_fail_stop_no_strict_test
phase_reviewed: PAL2_MINIMAL_EIIE_CNN_TRAINING
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PAL_PAPER_ALIGNED_PORTFOLIO_ALLOCATION_RL_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_PAL2_MINIMAL_EIIE_CNN_TRAINING_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_PAL2_MINIMAL_EIIE_CNN_TRAINING_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/paper_aligned_portfolio_rl/pal2_minimal_eiie_cnn_training
verdict: FAIL_STOP_NO_STRICT_TEST_NO_PAL3
pal2_validation_passed: false
pal3_authorized: false
strict_test_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_position: true
not_target_weight: true
---

# PAL2 Minimal EIIE-CNN Training 审查报告

## 1. 审查结论

结论：

```text
FAIL_STOP_NO_STRICT_TEST_NO_PAL3
```

执行者完成了上一轮工作文档授权的 PAL2 minimal EIIE-CNN with PVM 训练，并且边界控制基本合规：

```text
strict_test_used = false
pal3_authorized = false
production_allowed = false
order_intent_output = false
target_weight_output = false
target_position_output = false
quantity_or_broker_output = false
```

但是 PAL2 最小训练没有通过主线 gate：

```text
validation return after fee/tax <= baseline
seed stability fail
concentration audit fail
pal2_minimal_validation_gate_pass = false
```

因此，本轮不得进入：

```text
PAL3 Strict-test Final Replay
```

也不得授权：

```text
strict_test
provider/latest/monitor/frontend/Agent/broker/production
OrderIntent / target_weight / target_position / quantity
```

## 2. 主线 Gate 对照

PAL 主线对 PAL2 的通过条件是：

```text
validation return > baseline
seed stability pass
turnover/cost audit pass
concentration audit pass
not baseline clone
strict_test_used=false
```

本轮结果：

```text
validation return > baseline: FAIL
seed stability pass: FAIL
turnover/cost audit pass: PASS as artifact audit, but cost drag materially damages return
concentration audit pass: FAIL
not baseline clone: PASS
strict_test_used=false: PASS
```

总体评价：

```text
FAIL
```

原因不是执行者越权，而是训练结果没有达到 PAL2 进入 PAL3 的必要条件。

## 3. 关键证据

### 3.1 Validation Return

PAL1 validation baseline after-fee-tax return：

```text
0.95376753
```

`validation_replay_metrics.csv` 显示 3 个 seed：

```text
seed 11: validation_net_return_after_fee_tax = 0.66673752, excess = -0.28703001
seed 23: validation_net_return_after_fee_tax = -0.14492043, excess = -1.09868796
seed 37: validation_net_return_after_fee_tax = 0.01554350, excess = -0.93822403
```

`validation_selection_audit.csv` 选择 seed 11，但仍低于 baseline：

```text
selected_seed = 11
selected_validation_net_return_after_fee_tax = 0.66673752
validation_baseline_net_return_after_fee_tax = 0.95376753
validation_pass = False
stop_reason = STOP_VALIDATION_NOT_ABOVE_BASELINE_NO_STRICT_TEST_REQUEST
```

评价：

```text
FAIL
```

### 3.2 Seed Stability

`seed_stability_audit.csv`：

```text
above_baseline_seed_count = 0 / 3
seed_stability_pass = False
same_config_used = True
```

评价：

```text
FAIL
```

这不是单 seed 波动问题，而是 3 个 seed 全部未超过 baseline。

### 3.3 Turnover / Cost

`turnover_cost_audit.csv` 显示 artifact audit 为 pass，但成本拖累很大：

```text
seed 11: gross_return = 2.78097685, net_return_after_fee_tax = 0.66673752, cost_drag = 2.11423933
seed 23: gross_return = 1.18540350, net_return_after_fee_tax = -0.14492043, cost_drag = 1.33032393
seed 37: gross_return = 1.67190598, net_return_after_fee_tax = 0.01554350, cost_drag = 1.65636248
```

`cost_sensitivity_audit.csv` 进一步显示 selected seed 11 在成本上升时转负：

```text
cost_multiplier 0.0: 2.78097685
cost_multiplier 0.5: 1.51167586
cost_multiplier 1.0: 0.66673752
cost_multiplier 2.0: -0.26836118
```

评价：

```text
PASS_AS_AUDIT_PRESENT
FAIL_AS_MODEL_QUALITY_SIGNAL
```

主线要求 return-first 且 after-cost，本轮模型的 after-cost 质量不足。

### 3.4 Concentration

`concentration_audit.csv`：

```text
seed 11: mean_max_asset_allocation_weight_diagnostic = 0.79758461, status = fail
seed 23: mean_max_asset_allocation_weight_diagnostic = 0.83111456, status = fail
seed 37: mean_max_asset_allocation_weight_diagnostic = 0.87665173, status = fail
```

评价：

```text
FAIL
```

该结果符合主线中对 concentration 的审查重点，不能被收益或 gross return 掩盖。

### 3.5 Baseline Clone

`baseline_clone_audit.csv`：

```text
mean_corr_to_baseline_top10_reference = 0.27920618
mean_corr_to_equal_top20_reference = 0.0
single_symbol_or_day_dominates = False
status = pass
```

评价：

```text
PASS
```

本轮失败不是 baseline clone 问题，而是 validation after-cost return、seed stability 和 concentration 未通过。

## 4. 合同与安全边界审查

`validator_report.json` 通过以下关键检查：

```text
pal1_artifact_loaded = true
train_window_only_for_training = true
validation_window_only_for_selection = true
strict_test_not_used = true
no_future_return_or_label_feature = true
no_realized_pnl_feature = true
allocation_diagnostic_suffix_only = true
no_target_weight = true
no_target_position = true
no_quantity = true
no_broker_order = true
no_order_intent_output = true
no_provider_publish = true
no_monitor_frontend_agent_broker_consumer = true
```

`forbidden_feature_and_consumer_audit.csv` 也显示 forbidden fields / forbidden consumers 未触发。

评价：

```text
PASS
```

执行者在失败情况下正确 STOP，没有请求 strict_test。这一点符合 PAL 主线：

```text
若 validation 不过，不得 strict_test。
```

## 5. Findings

### High: PAL2 validation gate 未通过

selected seed 的 after-fee-tax return 为 `0.66673752`，低于 baseline `0.95376753`。

影响：

```text
不得进入 PAL3。
不得运行 strict_test。
不得声称 PAL2 通过。
```

### High: Seed stability 未通过

3 个 seed 中 `0 / 3` 超过 baseline。

影响：

```text
即使 selected seed 接近 baseline，也不能作为稳定 policy。
```

### High: Concentration audit 未通过

mean max asset allocation weight diagnostic 达到 `0.7976..0.8767`，三个 seed 均 fail。

影响：

```text
策略存在明显集中度风险，不符合 PAL2 通过条件。
```

### Medium: 成本敏感性显示 gross return 与 net return 断裂

selected seed gross return 为 `2.78097685`，但 after-fee-tax return 仅 `0.66673752`。

影响：

```text
模型可能学到了高换手/高成本路径，不能用 gross return 解释为有效。
```

## 6. 对执行者工作的评价

执行质量层面：

```text
PASS_FOR_BOUNDARY_AND_EVIDENCE_COMPLETENESS
```

模型结果层面：

```text
FAIL_FOR_PAL2_VALIDATION_GATE
```

执行者没有越权推进，也没有用 lite/minimal training 声称完整论文方法成功或失败。报告中明确写出：

```text
STOP_NO_STRICT_TEST_REQUEST
```

这是正确的停止行为。

## 7. 下一步控制

本审查不写 PAL3 工作文档。

本审查也不直接写新的 executor repair 文档，因为 PAL 主线已明确：

```text
若 validation 不过，不得 strict_test。
PAL3 只有 PAL2 validation 通过后才允许。
训练只是 lite sanity，却声称完整论文方法失败或成功，是停止条件。
```

因此下一步必须回到统筹，由统筹决定：

```text
1. 是否关闭 qlib-only PAL minimal EIIE-CNN 路线；
2. 是否在 PAL2 内另行授权一个严格受限的非调参性质诊断步骤；
3. 是否按主线候选顺序考虑 EIIE-LSTM/RNN 或 PPO allocation policy；
4. 是否终止 PAL 主线并另开新路线。
```

在统筹给出新意见前，执行者不得继续：

```text
同线反复调参
运行 strict_test
进入 PAL3
扩展到 DDPG/SAC
接入任何 production / OrderIntent / Agent / frontend / broker / provider
```

## 8. 给统筹的建议

建议统筹把本轮记录为：

```text
PAL2 minimal EIIE-CNN with PVM: executed, boundary compliant, validation failed, STOP before strict_test.
```

如果继续 PAL 主线，建议只在 PAL2 内做清晰授权，不要把本轮失败解释为整条 paper-aligned allocation RL 方法失败。当前证据只支持：

```text
minimal EIIE-CNN with PVM under current qlib-only top20/lookback20/8-channel setting did not beat validation baseline after costs.
```

不支持：

```text
所有 PAL allocation RL 候选均失败。
```
