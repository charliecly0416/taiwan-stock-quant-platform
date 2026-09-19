---
created_at: 2026-06-22
status: coordinator_opinion_for_reviewer
scope: after_pba3_supervised_bandit_active_policy_review
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
review_doc: docs/tw_portfolio_decision_model/POLICY_PBA3_SUPERVISED_BANDIT_ACTIVE_POLICY_REVIEW_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_PBA3_SUPERVISED_BANDIT_ACTIVE_POLICY_EXECUTION_REPORT_CN.md
recommended_next: PBA3_R_FOLD_STABILITY_CONSTRAINED_REPAIR
pba5_authorized: false
strict_test_authorized: false
pba4_offline_rl_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_weight: true
not_target_position: true
not_quantity: true
---

# PBA3 统筹意见：不进 PBA5，授权 PBA3-R 稳定性修复

## 1. 统筹结论

本轮 `PBA3 Supervised / Bandit Active Policy` 的审查结论成立：

```text
FAIL_STOP_NO_STRICT_TEST_NO_PBA5
```

不得授权：

```text
PBA5 strict-test final replay
strict_test
PBA4 offline RL
qlib+LTR adapter
OrderIntent / target_weight / target_position / quantity
provider/latest/monitor/frontend/Agent/broker/production
```

但本轮不应关闭 PBA 主线。相反，这是目前 policy 路线中第一次出现较强、且行为上不退化的 validation 收益信号：

```text
selected_model_id = shallow_mlp_active_policy_seed_23
validation_baseline_net_return_after_fee_tax = 0.95376753
PBA2_selected_validation_net_return_after_fee_tax = 0.97910586
selected_validation_net_return_after_fee_tax = 1.20247421
selected_excess_return_after_fee_tax = +0.24870668
```

并且 selected model 通过了关键行为与边界 gate：

```text
participation_rate = 0.98013245
risk_asset_exposure = 0.99173554
cash_dominance_rate = 0.00826446
OOD_action_rate = 0.0
seed_stability_pass = true
not_baseline_clone = true
strict_test_used = false
forbidden_consumer_audit = pass
```

所以统筹判断：

```text
不授权 PBA5。
不关闭 PBA。
授权审查者撰写 PBA3-R fold-stability constrained repair 工作文档。
```

推荐下一步文档：

```text
docs/tw_portfolio_decision_model/POLICY_PBA3_R_FOLD_STABILITY_CONSTRAINED_REPAIR_WORK_CN.md
```

## 2. 为什么不能直接授权 strict_test

PBA3 的硬失败点是：

```text
fold_stability_pass = False
```

selected model 的 train / validation 方向不一致：

```text
train_excess_return = -0.92621018
validation_excess_return = +0.24870668
```

PBA2 selected rule 也存在相同结构：

```text
train 显著输 baseline
validation 小幅赢 baseline
```

这说明当前 active policy 可能捕捉到了 2025 validation 的特定 regime，而不是稳定可迁移的 policy edge。若现在进入 strict_test，风险是：

```text
用 2025 validation 选出的窗口特化策略去赌 2026 strict_test。
```

因此即使 validation return 很强，也不能跳过 fold stability gate。

## 3. 底层原因判断

### 3.1 PBA 方向有效，但稳定性未证实

与 PAL free allocation 相比，PBA3 没有出现：

```text
高换手高集中
cash/no-trade 塌缩
OOD action
baseline clone
合同越界
```

这说明 baseline-anchored active policy 的 action space 比 free allocation 更适配本项目。

但 train/validation 方向反转说明：

```text
当前模型学到的 active overlay 可能依赖特定市场状态；
还不能证明它在多 regime 下稳定优于 baseline。
```

### 3.2 当前问题不是收益信号不足，而是跨窗口可信度不足

PBA3-R 的目标不应是继续追求更高 validation return，而应是验证并修复：

```text
fold / regime / time split stability
```

即：

```text
宁可 validation return 从 1.202 降到较低，
也要证明 train / subfold / validation 的方向不再明显反转。
```

### 3.3 不能用复杂模型或 offline RL 掩盖稳定性问题

PBA4 offline RL 现在不应启动。原因：

```text
PBA3 的小模型已经能在 validation 产生强收益；
当前瓶颈不是模型表达能力，而是稳定性和窗口依赖。
```

如果在 fold stability 失败时直接上 CQL/IQL/BCQ，可能只会增加解释难度和过拟合空间。

## 4. PBA3-R 授权范围

PBA3-R 只能做稳定性约束修复，不得无界调参。

允许：

```text
1. walk-forward / subfold stability audit。
2. train window 内部再切 rolling folds，例如 2023H1、2023H2、2024H1、2024H2。
3. 对 PBA3 已预声明模型做稳定性约束重训。
4. 降低模型复杂度，例如限制 MLP、优先 shallow / logistic / tree。
5. 加 regularization / early stopping，但必须只用 train folds。
6. 对 active decision change rate 设置下限和上限，避免 baseline clone 或过度动作。
7. 增加 regime stability audit：牛/熊/震荡、波动高低、score dispersion 高低。
8. 保留 participation / cash dominance / risk exposure / OOD / baseline clone / PnL concentration gates。
```

禁止：

```text
1. 运行或读取 strict_test。
2. 进入 PBA5。
3. 启动 PBA4 offline RL。
4. 扩展到 qlib+LTR。
5. 新增 free allocation vector。
6. 新增 target_weight / target_position / quantity。
7. provider/latest/monitor/frontend/Agent/broker/production 扩权。
8. 根据 validation 反复调参。
9. 只为了保留 2025 validation 最优结果而放宽 stability gate。
```

## 5. PBA3-R 建议实验设计

PBA3-R 应保持窗口隔离：

```text
outer_train = 2023-01-01..2024-12-31
outer_validation = 2025-01-01..2025-12-31
strict_test = 2026-01-01..2026-05-07, declared only, not used
```

在 `outer_train` 内部做 stability folds：

```text
fold_1 = 2023H1
fold_2 = 2023H2
fold_3 = 2024H1
fold_4 = 2024H2
或按现有交易日做 rolling / expanding split
```

候选不得无界扩展，建议只保留：

```text
1. supervised_utility_logistic_or_tree_stability_constrained
2. contextual_bandit_conservative_stability_constrained
3. shallow_mlp_active_policy_stability_constrained
```

每个候选必须输出：

```text
train_fold_metrics
fold_excess_return_distribution
fold_direction_stability
validation_replay_metrics
selected_model_audit
```

选择规则必须预先固定：

```text
1. 先过 hard gates。
2. 再看 fold stability。
3. 再看 validation net_return_after_fee_tax。
```

不能用以下方式选择：

```text
单一 2025 validation 最好结果
单 seed 最好结果
gross return
train return
strict_test
人工挑选 checkpoint
```

## 6. PBA3-R 通过条件建议

PBA3-R 只有在以下全部满足时，才可建议统筹考虑 PBA5：

```text
1. validation net_return_after_fee_tax > PBA1 baseline。
2. validation net_return_after_fee_tax >= PBA2 selected rule，或略低但有清楚稳定性收益。
3. fold stability pass：
   - train folds 中多数 fold excess_return >= 0；
   - 不得再出现整体 train 大幅输 baseline、validation 大幅赢 baseline 的方向反转。
4. seed stability pass。
5. participation gates pass。
6. cash dominance gates pass。
7. risk asset exposure gates pass。
8. cost / turnover not pathological。
9. not baseline clone。
10. OOD action audit pass。
11. pnl concentration audit pass。
12. strict_test_used = false。
13. forbidden consumer / OrderIntent / target_weight / target_position / quantity audit pass。
```

如果 PBA3-R 仍然出现：

```text
train/fold 方向显著为负，
但 validation 显著为正，
```

则不得进入 PBA5，应回到统筹判断是否：

```text
1. 关闭 PBA3 模型子线；
2. 退回 PBA2 rule-based active overlay；
3. 改做更明确的 regime-conditioned policy；
4. 重新规划 policy train/validation 切分。
```

## 7. 建议产物

审查者撰写 PBA3-R 工作文档时，建议要求执行者输出：

```text
data_tw/experiments/baseline_anchored_active_policy/pba3_r_fold_stability_repair/
  manifest.json
  model_candidate_manifest.json
  train_fold_split_manifest.json
  stability_constraint_design.md
  train_fold_replay_metrics_by_model.csv
  fold_stability_audit.csv
  regime_stability_audit.csv
  validation_replay_metrics_by_model.csv
  validation_selection_audit.csv
  seed_stability_audit.csv
  participation_gate_audit.csv
  cash_dominance_gate_audit.csv
  risk_asset_exposure_audit.csv
  cost_turnover_audit.csv
  baseline_clone_audit.csv
  active_decision_change_rate_audit.csv
  ood_action_audit.csv
  behavior_policy_coverage_audit.csv
  pnl_concentration_audit.csv
  feature_available_at_audit.csv
  forbidden_feature_and_consumer_audit.csv
  validator_report.json
  golden_samples_report.json

docs/tw_portfolio_decision_model/POLICY_PBA3_R_FOLD_STABILITY_CONSTRAINED_REPAIR_EXECUTION_REPORT_CN.md
```

## 8. 给审查者的下一步指令

请审查者基于本意见文档撰写：

```text
docs/tw_portfolio_decision_model/POLICY_PBA3_R_FOLD_STABILITY_CONSTRAINED_REPAIR_WORK_CN.md
```

工作文档应要求执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA3_SUPERVISED_BANDIT_ACTIVE_POLICY_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA3_SUPERVISED_BANDIT_ACTIVE_POLICY_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA3_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
```

不得写：

```text
PBA5 strict-test 工作文档
PBA4 offline RL 工作文档
qlib+LTR adapter 工作文档
production integration 工作文档
```

## 9. 统筹判断

PBA3 是目前最值得继续的 policy 路线，因为它第一次同时满足：

```text
明显 validation excess return
高参与度
高风险资产暴露
低现金塌缩
无 OOD action
非 baseline clone
合同边界合规
```

但 fold stability 失败是硬门槛，不能用强 validation 收益绕过。

因此最终控制是：

```text
PBA3-R stability repair: authorized
PBA5 strict_test: not authorized
PBA4 offline RL: not authorized
production/default/order: not authorized
```
