---
created_at: 2026-06-22
status: review_fail_stop_no_strict_test_no_pal3
phase_reviewed: PAL2_R_COST_AWARE_CONCENTRATION_CONSTRAINED_EIIE
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PAL_PAPER_ALIGNED_PORTFOLIO_ALLOCATION_RL_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_PAL2_R_COST_AWARE_CONCENTRATION_CONSTRAINED_EIIE_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_PAL2_R_COST_AWARE_CONCENTRATION_CONSTRAINED_EIIE_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/paper_aligned_portfolio_rl/pal2_r_cost_concentration_repair
verdict: FAIL_STOP_NO_STRICT_TEST_NO_PAL3
pal2_validation_passed: false
pal3_authorized: false
strict_test_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_weight: true
not_target_position: true
not_quantity: true
---

# PAL2-R Cost-aware Concentration-constrained EIIE 审查报告

## 1. 审查结论

结论：

```text
FAIL_STOP_NO_STRICT_TEST_NO_PAL3
```

执行者按工作文档完成了 PAL2-R 的受限结构性修复实验：

```text
base_config
repair_a: turnover penalty
repair_b: turnover penalty + no-trade threshold + smoothing
repair_c: turnover penalty + no-trade threshold + smoothing + concentration control
```

执行边界合规：

```text
strict_test_used = false
pal3_authorized = false
production_allowed = false
order_intent_output = false
target_weight_output = false
target_position_output = false
quantity_or_broker_output = false
```

但 PAL2-R 没有通过主线和统筹意见要求的 PAL2 validation gate：

```text
selected_mean_validation_net_return_after_fee_tax = 0.02833287
PAL1_validation_baseline_net_return_after_fee_tax = 0.95376753
excess_vs_PAL1_baseline_after_fee_tax = -0.92543466
above_baseline_seed_count = 0 / 3 for all configs
hard_gates_pass = false
```

因此不得进入：

```text
PAL3 Strict-test Final Replay
strict_test
qlib+LTR
PPO / DDPG / SAC
full GPU training
production / OrderIntent / Agent / frontend / broker / provider
```

## 2. 主线 Gate 对照

PAL2 / PAL2-R 要求：

```text
validation return > baseline
seed stability pass
turnover/cost audit pass
concentration audit pass
not baseline clone
strict_test_used=false
forbidden consumer / OrderIntent / target_weight / target_position / quantity audit pass
```

本轮结果：

```text
validation return > baseline: FAIL
seed stability pass: FAIL
turnover/cost audit: PASS_AS_AUDIT_PRESENT, FAIL_AS_POLICY_EDGE
concentration audit: MIXED, but repaired configs mostly become cash/no-trade dominant
not baseline clone: PASS
strict_test_used=false: PASS
contract / forbidden consumer audit: PASS
```

总体评价：

```text
FAIL
```

失败原因不是越权，而是 repair 后没有形成可用的 after-fee-tax validation edge。

## 3. 关键证据

### 3.1 Validation Selection

`validation_selection_audit.csv`：

```text
base_config:
  mean_validation_net_return_after_fee_tax = -0.09531552
  best_seed_validation_net_return_after_fee_tax = 0.01634666
  hard_gates_pass = False

repair_a:
  mean_validation_net_return_after_fee_tax = -0.00000018
  best_seed_validation_net_return_after_fee_tax = -0.00000002
  hard_gates_pass = False

repair_b:
  mean_validation_net_return_after_fee_tax = 0.02754071
  best_seed_validation_net_return_after_fee_tax = 0.08262213
  hard_gates_pass = False

repair_c:
  mean_validation_net_return_after_fee_tax = 0.02833287
  best_seed_validation_net_return_after_fee_tax = 0.08499861
  hard_gates_pass = False
```

PAL1 validation baseline：

```text
0.95376753
```

评价：

```text
FAIL
```

没有任何 config 的 mean 或 best seed 接近 baseline，更没有超过 baseline。

### 3.2 Seed Stability

`seed_stability_audit.csv`：

```text
base_config: above_baseline_seed_count = 0 / 3, seed_stability_pass = False
repair_a: above_baseline_seed_count = 0 / 3, seed_stability_pass = False
repair_b: above_baseline_seed_count = 0 / 3, seed_stability_pass = False
repair_c: above_baseline_seed_count = 0 / 3, seed_stability_pass = False
```

评价：

```text
FAIL
```

这比 PAL2 minimal 的失败更明确：repair 后没有一个 seed 超过 PAL1 baseline。

### 3.3 Turnover / Cost

`turnover_cost_audit.csv` 显示 repair 的确显著降低成本和换手：

```text
repair_b seed 23:
  turnover_proxy = 0.00087570
  cost_drag = 0.00027856
  net_return_after_fee_tax = 0.08262213

repair_c seed 23:
  turnover_proxy = 0.00089722
  cost_drag = 0.00028489
  net_return_after_fee_tax = 0.08499861
```

但这不是有效收益提升。它主要来自交易被压制，而非形成可验证的组合收益。

评价：

```text
PASS_AS_COST_REDUCTION_MECHANISM
FAIL_AS_RETURN_POLICY
```

### 3.4 Cost Sensitivity

`cost_sensitivity_audit.csv` 显示 repair_b / repair_c 对成本倍数不敏感：

```text
repair_c seed 23:
  cost_multiplier 0.0 = 0.08528350
  cost_multiplier 0.5 = 0.08514104
  cost_multiplier 1.0 = 0.08499861
  cost_multiplier 2.0 = 0.08471379
```

这不是强成本鲁棒收益，而是因为 turnover 已接近 0。

评价：

```text
PASS_AS_SENSITIVITY_STABLE
FAIL_AS_BASELINE_OUTPERFORMANCE
```

PAL2-R 通过条件要求 1.0x 成本下超过 baseline；本轮远未达到。

### 3.5 Concentration / Cash Dominance

`concentration_audit.csv`：

```text
repair_a cash_weight_mean ~= 0.999999
repair_b seed 11 / 37 cash_weight_mean = 1.0
repair_c seed 11 / 37 cash_weight_mean = 1.0
repair_c seed 23 cash_weight_mean = 0.94446041
```

repair 的方向从 PAL2 minimal 的单资产过度集中，变成了明显的现金/不交易占优。

评价：

```text
FAIL_AS_PORTFOLIO_POLICY
```

即使个别 concentration row 标记为 pass，组合行为也没有形成有效风险资产配置。`effective_holding_count` 在现金占优场景下还出现 `0.0` 或超大值，这说明仅靠该字段不能证明组合可用。

### 3.6 Baseline Clone

`baseline_clone_audit.csv`：

```text
status = pass for base_config / repair_a / repair_b / repair_c
```

评价：

```text
PASS
```

本轮失败不是 baseline clone，而是收益、seed stability 和有效参与失败。

## 4. 合同与安全边界

`validator_report.json` 通过：

```text
same_train_window = true
same_validation_window = true
same_seed_set = true
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
repair_configs_predeclared = true
no_unbounded_grid_search = true
validation_primary_metric_after_fee_tax = true
```

`golden_samples_report.json` 覆盖并通过：

```text
target_weight field must fail
target_position field must fail
quantity / broker_order must fail
OrderIntentArtifact consumer must fail
strict_test metrics access must fail
validation pass claim based on gross return must fail
validation pass claim based on single seed must fail
unpredeclared config must fail
PAL3 request without PAL2-R gates must fail
```

评价：

```text
PASS
```

执行者没有触碰 forbidden consumer，也没有在失败后请求 strict_test。这一点符合主线。

## 5. Findings

### High: PAL2-R validation gate 未通过

selected config `repair_c` 的 mean validation after-fee-tax return 为 `0.02833287`，远低于 PAL1 baseline `0.95376753`。

影响：

```text
不得进入 PAL3。
不得运行 strict_test。
不得声称 PAL2 validation pass。
```

### High: 所有 config 的 seed stability 均失败

`above_baseline_seed_count = 0 / 3` 对所有 config 成立。

影响：

```text
没有稳定可复现的 validation edge。
```

### High: Repair 退化为现金/不交易占优

repair_a / repair_b / repair_c 大量 seed 的现金权重接近或等于 1.0，executed rebalance 很少甚至为 0。

影响：

```text
成本和集中度指标改善不能视为策略成功；
它主要是停止交易，而不是学到 after-cost portfolio allocation。
```

### Medium: Audit 指标存在“形式 pass、经济失败”的解释风险

部分 cost sensitivity 和 concentration 字段显示 pass，但原因是近乎不交易或持有现金。

影响：

```text
后续如继续该路线，必须把 minimum market participation / minimum risk-asset exposure 纳入 gate，
否则 repair 会继续朝 cash-only / no-trade 解退化。
```

## 6. 对执行者工作的评价

执行质量：

```text
PASS_FOR_SCOPE_BOUNDARY_AND_EVIDENCE_COMPLETENESS
```

模型结果：

```text
FAIL_FOR_PAL2_R_VALIDATION_GATE
```

执行者正确执行了统筹授权的受限 repair，没有换算法、没有无界搜索、没有读取 strict_test、没有请求 PAL3。

## 7. 下一步控制

本审查不写 PAL3 工作文档。

本审查也不直接写下一轮 executor 工作文档。原因：

```text
1. PAL2-R 已按统筹意见执行，但 validation 仍显著低于 baseline。
2. 主线规定 validation 不过不得 strict_test。
3. 统筹意见规定 PAL2-R 失败后不得自动进入 PAL3 / PPO / DDPG/SAC / qlib+LTR / full GPU training。
4. 后续是否继续 PAL 内修复、切换 PAL 候选实现、关闭 PAL 主线，必须由统筹决定。
```

在统筹给出新意见前，执行者不得继续：

```text
运行 strict_test
进入 PAL3
继续同线调参
自动切 PPO / DDPG / SAC
扩到 qlib+LTR
full GPU training
接入 production / OrderIntent / Agent / frontend / broker / provider
```

## 8. 给统筹的建议

建议统筹把本轮记录为：

```text
PAL2-R cost-aware concentration-constrained EIIE: executed, boundary compliant, validation failed, STOP before strict_test.
```

当前证据支持：

```text
1. 成本/集中度 repair 可以降低 turnover 和单资产集中度。
2. 但 repair 主要退化为 cash/no-trade dominant behavior。
3. 没有任何 config / seed 超过 PAL1 validation baseline。
4. 当前 EIIE-CNN with PVM qlib-only PAL2 路径尚未形成可用 after-fee-tax validation edge。
```

当前证据不支持：

```text
1. 进入 PAL3。
2. 使用 strict_test。
3. 声称 paper-aligned allocation RL 整体失败。
4. 声称 repair_c 已经成功。
```

若统筹决定继续 PAL，建议下一份主控意见先回答：

```text
是否允许新增 minimum market participation / risk-asset exposure gate；
是否继续 EIIE-CNN 修复，还是按主线候选顺序转 EIIE-LSTM/RNN 或 PPO；
是否关闭 qlib-only PAL2 的 EIIE-CNN 子线。
```
