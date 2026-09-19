---
created_at: 2026-06-22
status: reviewer_next_work_document
phase: PAL2_R_COST_AWARE_CONCENTRATION_CONSTRAINED_EIIE
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PAL_PAPER_ALIGNED_PORTFOLIO_ALLOCATION_RL_MAINLINE_CN.md
coordinator_opinion: docs/tw_portfolio_decision_model/POLICY_PAL2_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
previous_review: docs/tw_portfolio_decision_model/POLICY_PAL2_MINIMAL_EIIE_CNN_TRAINING_REVIEW_CN.md
previous_execution_report: docs/tw_portfolio_decision_model/POLICY_PAL2_MINIMAL_EIIE_CNN_TRAINING_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/paper_aligned_portfolio_rl/pal2_r_cost_concentration_repair
strict_test_authorized: false
pal3_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_weight: true
not_target_position: true
not_quantity: true
---

# PAL2-R Cost-aware Concentration-constrained EIIE 工作文档

## 1. 本轮目标

你是执行者。请继续 PAL Paper-aligned Portfolio Allocation RL 主线的 PAL2。

本轮只执行统筹授权的：

```text
PAL2_R_COST_AWARE_CONCENTRATION_CONSTRAINED_EIIE
```

目标不是进入 PAL3，也不是换算法，而是在上一轮 `PAL2 minimal EIIE-CNN with PVM` 的失败基础上，做受限的结构性修复：

```text
1. 强化 after-fee-tax reward。
2. 显式惩罚 turnover / rebalance_delta_diagnostic。
3. 加入 no-trade / rebalance threshold。
4. 加入 allocation smoothing。
5. 加入 concentration control。
6. 完整审计 cost sensitivity、concentration、diversification、baseline clone。
```

本轮仍属于 PAL2，不是 PAL3。

## 2. 必须读取

执行前必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_PAL_PAPER_ALIGNED_PORTFOLIO_ALLOCATION_RL_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PAL2_MINIMAL_EIIE_CNN_TRAINING_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PAL2_MINIMAL_EIIE_CNN_TRAINING_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_PAL2_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
```

必须使用既有 PAL1/PAL2 产物作为输入和对照：

```text
data_tw/experiments/paper_aligned_portfolio_rl/pal1_allocation_env_tensor_memory_build/
data_tw/experiments/paper_aligned_portfolio_rl/pal2_minimal_eiie_cnn_training/
```

## 3. 授权范围

本轮只允许继续使用：

```text
algorithm = EIIE_CNN_with_PVM
topk = 20
lookback = 20
feature_channels = 8
train_window = 2023-01-01..2024-12-31
validation_window = 2025-01-01..2025-12-31
seeds = [11, 23, 37]
strict_test_used = false
```

允许的 repair config 仅限以下预声明配置：

```text
base_config:
  PAL2 minimal EIIE-CNN with PVM 原配置，用作复核对照。

repair_a:
  base + turnover penalty。

repair_b:
  base + turnover penalty + no-trade / rebalance threshold。

repair_c:
  base + turnover penalty + no-trade / rebalance threshold + concentration penalty/cap。
```

不得自由网格搜索，不得临时增加未预声明配置。

## 4. 允许的结构性修复

允许实现：

```text
1. transaction-cost-aware reward
   reward 必须以 after-fee-tax NAV change 为主目标。
   必须显式记录 fee、sell tax、turnover、cost_drag。

2. turnover penalty
   对 rebalance_delta_diagnostic 或其等价 readonly diagnostic delta 加惩罚。

3. no-trade / rebalance threshold
   小于预声明阈值的 allocation delta 不触发 simulated rebalance。
   threshold 必须写入 repair_config_manifest.json。

4. allocation smoothing
   约束 w_t 与 w_{t-1} 的变化，让 PVM 真实影响动作稳定性。

5. concentration control
   可使用单资产 soft cap、hard diagnostic cap、entropy regularizer、HHI penalty。
   所有输出字段仍必须使用 diagnostic 语义。

6. diversification audit
   必须输出 max_weight、HHI、effective_holding_count、top1/top3 weight share。

7. cost sensitivity
   必须覆盖 cost_multiplier = 0.0 / 0.5 / 1.0 / 2.0。

8. baseline clone audit
   必须继续证明不是简单复制 PAL1 baseline 或等权 top20。
```

## 5. 禁止事项

本轮禁止：

```text
1. 运行 strict_test 或读取 strict_test metrics。
2. 进入 PAL3。
3. qlib+LTR 适配。
4. 换 PPO / DDPG / SAC。
5. 扩大 universe、lookback 或 feature_channels 做无界搜索。
6. 直接加长训练并声称 full paper method。
7. 根据 validation 反复调参。
8. 使用 gross return、train return、单 seed 最好结果、零成本结果作为通过条件。
9. 人工挑选 validation peak checkpoint。
10. 输出 OrderIntent。
11. 输出 target_weight / target_position / quantity / broker_order。
12. broker / quick-trade / real order。
13. provider publish / accepted latest switch。
14. monitor write / frontend default / Agent recommendation。
15. 将 allocation_weight_diagnostic 改名、复制或映射为 target_weight。
```

`allocation_weight_diagnostic` 仍只能作为：

```text
simulation-only
readonly research replay only
not production
not order
not advice
```

## 6. 输出产物

artifact root：

```text
data_tw/experiments/paper_aligned_portfolio_rl/pal2_r_cost_concentration_repair/
```

必须输出：

```text
manifest.json
repair_config_manifest.json
reward_design_audit.md
train_curve_by_config_seed.csv
validation_replay_metrics_by_config_seed.csv
validation_selection_audit.csv
turnover_cost_audit.csv
cost_sensitivity_audit.csv
concentration_audit.csv
allocation_smoothing_audit.csv
no_trade_threshold_audit.csv
baseline_clone_audit.csv
forbidden_feature_and_consumer_audit.csv
validator_report.json
golden_samples_report.json
```

必须写执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_PAL2_R_COST_AWARE_CONCENTRATION_CONSTRAINED_EIIE_EXECUTION_REPORT_CN.md
```

## 7. 训练与选择规则

训练规则：

```text
1. 每个 config 使用同一 train window：2023-01-01..2024-12-31。
2. 每个 config 使用同一 seeds：[11, 23, 37]。
3. 不得读取 validation return 作为训练反馈。
4. 不得读取 strict_test。
5. train curve 必须按 config_id + seed 输出。
6. 所有 reward/cost/concentration 参数必须在 repair_config_manifest.json 中预声明。
```

Validation 规则：

```text
1. 只在 2025-01-01..2025-12-31 做 validation replay。
2. primary metric = validation_net_return_after_fee_tax。
3. 必须与 PAL1 validation baseline 对照。
4. 必须与 PAL2 minimal EIIE-CNN 结果对照。
5. 通过条件只能基于 after-fee-tax，不得基于 gross return。
6. 如果 validation 不超过 baseline，必须 STOP，不得请求 strict_test。
```

选择规则：

```text
1. 先按 hard gates 过滤：contract、seed stability、concentration、cost sensitivity、baseline clone。
2. 只在 hard gates 全部通过的 config 中，按 validation_net_return_after_fee_tax 选择。
3. 若无 config 全部通过，必须写 STOP，不得挑选单项最好结果冒充通过。
4. 不得根据 strict_test 做任何选择。
```

## 8. PAL2-R 通过条件

PAL2-R 只有在以下全部满足时，才可建议审查者考虑 PAL2 validation pass：

```text
1. selected validation net_return_after_fee_tax > PAL1 validation baseline。
2. seed stability pass，至少多数 seed 超 baseline，且不能只有单 seed 支撑。
3. cost sensitivity pass，1.0x 成本下必须超 baseline，2.0x 成本下不得崩溃到明显不可用。
4. concentration pass，max_weight / HHI / effective_holding_count 达到预设阈值。
5. turnover/cost drag 明显低于 PAL2 minimal，或至少不再吞噬大部分 gross return。
6. baseline clone audit pass。
7. strict_test_used = false。
8. forbidden consumer / OrderIntent / target_weight / target_position / quantity audit pass。
```

本轮若仍失败，不得自动进入：

```text
PAL3
PPO
DDPG/SAC
qlib+LTR
full GPU training
```

必须回到统筹。

## 9. Audit 要求

### 9.1 Reward Design Audit

`reward_design_audit.md` 必须说明：

```text
1. reward 如何以 after-fee-tax NAV change 为主目标。
2. fee / sell tax / turnover / cost_drag 如何进入训练和 replay。
3. turnover penalty 的定义、符号和量纲。
4. no-trade threshold 如何影响 simulated rebalance。
5. concentration penalty/cap 如何影响 allocation_weight_diagnostic。
6. 为什么这些改动不是根据 validation 反复调参。
```

### 9.2 Cost / Turnover Audit

`turnover_cost_audit.csv` 必须至少包含：

```text
config_id
seed
gross_return
net_return_after_fee_tax
turnover_proxy
fee_and_tax
cost_drag
cost_drag_vs_pal2_minimal
status
```

### 9.3 Concentration / Diversification Audit

`concentration_audit.csv` 必须至少包含：

```text
config_id
seed
max_weight_diagnostic
mean_max_asset_allocation_weight_diagnostic
HHI
effective_holding_count
top1_weight_share
top3_weight_share
cash_weight_mean
status
```

### 9.4 Smoothing / No-trade Audit

`allocation_smoothing_audit.csv` 必须说明：

```text
config_id
seed
mean_abs_rebalance_delta_before_smoothing
mean_abs_rebalance_delta_after_smoothing
turnover_reduction_vs_base
status
```

`no_trade_threshold_audit.csv` 必须说明：

```text
config_id
threshold
skipped_rebalance_count
executed_rebalance_count
estimated_cost_saved
net_return_impact
status
```

## 10. Validator / Golden Samples

`validator_report.json` 必须检查：

```text
pal1_artifact_loaded
pal2_minimal_artifact_loaded
same_train_window
same_validation_window
same_seed_set
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
repair_configs_predeclared
no_unbounded_grid_search
validation_primary_metric_after_fee_tax
cost_sensitivity_exists
concentration_audit_exists
allocation_smoothing_audit_exists
no_trade_threshold_audit_exists
baseline_clone_audit_exists
seed_stability_exists
```

`golden_samples_report.json` 必须包含：

```text
positive: PAL readonly research replay can consume AllocationDiagnosticArtifact.
positive: repair config can reduce diagnostic turnover without touching OrderIntent.
positive: concentration cap/penalty can be audited only through diagnostic fields.
negative: target_weight field must fail.
negative: target_position field must fail.
negative: quantity / broker_order must fail.
negative: OrderIntentArtifact consumer must fail.
negative: strict_test metrics access must fail.
negative: validation pass claim based on gross return must fail.
negative: validation pass claim based on single seed must fail.
negative: unpredeclared config must fail.
negative: PAL3 request without PAL2-R gates must fail.
```

## 11. 执行报告要求

执行报告必须包括：

```text
1. Scope：说明只做 PAL2-R EIIE repair。
2. Documents read：列出本工作文档要求读取的文件。
3. Repair implementation：说明 reward、turnover penalty、threshold、smoothing、concentration control。
4. Configs run：列出 base_config / repair_a / repair_b / repair_c，若有任何未执行必须说明原因。
5. Evidence produced：列出 artifact root 下全部产物。
6. Validation result：按 config + seed 报告 after-fee-tax return、excess return、seed stability。
7. Cost/concentration result：报告 cost drag、turnover、HHI、effective holdings、max weight。
8. Forbidden actions audit：明确 strict_test=false，未输出 OrderIntent/target_weight/target_position/quantity/broker。
9. Recommendation：只能是 PASS_READY_FOR_REVIEWER_TO_CONSIDER_PAL2_VALIDATION_PASS 或 STOP_NO_STRICT_TEST_REQUEST。
```

如果 PAL2-R 未通过，推荐语必须是：

```text
STOP_NO_STRICT_TEST_REQUEST
```

不得请求 PAL3。
