---
created_at: 2026-06-22
status: coordinator_opinion_for_reviewer
scope: after_pal2_minimal_eiie_cnn_training_fail
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PAL_PAPER_ALIGNED_PORTFOLIO_ALLOCATION_RL_MAINLINE_CN.md
review_doc: docs/tw_portfolio_decision_model/POLICY_PAL2_MINIMAL_EIIE_CNN_TRAINING_REVIEW_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_PAL2_MINIMAL_EIIE_CNN_TRAINING_EXECUTION_REPORT_CN.md
recommended_next: PAL2_R_COST_AWARE_CONCENTRATION_CONSTRAINED_EIIE_REPAIR
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

# PAL2 统筹意见：不进 PAL3，转 PAL2-R 成本与集中度修复

## 1. 统筹结论

本轮 `PAL2 Minimal EIIE-CNN Training` 的执行和审查结论成立：

```text
FAIL_STOP_NO_STRICT_TEST_NO_PAL3
```

因此现在不得授权：

```text
PAL3 strict-test final replay
strict_test 读取或回放
qlib+LTR 适配
OrderIntent / target_weight / target_position / quantity
provider/latest/monitor/frontend/Agent/broker/production
```

但本轮也不应被解释为：

```text
EIIE / FinRL / PGPortfolio / allocation RL 论文路线整体失败。
```

当前证据只支持：

```text
在当前 qlib-only、top20、lookback20、8-channel、
32 episodes / 128 batches、CPU minimal EIIE-CNN with PVM 设置下，
validation=2025 after-fee-tax return 未超过 PAL1 baseline，
且 seed stability 与 concentration gate 未通过。
```

所以统筹建议：

```text
不进入 PAL3。
不关闭 PAL 主线。
授权审查者撰写一个受限的 PAL2-R repair 工作文档。
```

推荐下一步名称：

```text
POLICY_PAL2_R_COST_AWARE_CONCENTRATION_CONSTRAINED_EIIE_WORK_CN.md
```

## 2. 底层失败原因判断

### 2.1 不是完全没学到收益，而是收益被交易成本吃掉

本轮 selected seed 11：

```text
gross_return = 2.78097685
net_return_after_fee_tax = 0.66673752
baseline_after_fee_tax = 0.95376753
cost_drag = 2.11423933
```

这说明模型可能找到了一些 gross return 较高的价格路径，但没有学会：

```text
哪些调仓值得付成本
哪些小幅 allocation 变化应该不交易
如何在 after-fee-tax 目标下控制 turnover
```

因此后续修复重点不是简单加 episode，而是先把 reward、action smoothing、rebalance threshold 与 cost penalty 做成论文级适配。

### 2.2 allocation 过度集中，导致组合层风险过高

三个 seed 的 mean max asset allocation weight diagnostic 均失败：

```text
seed 11: 0.79758461
seed 23: 0.83111456
seed 37: 0.87665173
```

这说明 policy 倾向于把大部分诊断权重压到少数资产。即使短期 gross return 看起来高，也不适合作为可验证的 portfolio policy。

后续必须加入：

```text
单资产权重上限或 soft cap
entropy / diversification regularizer
HHI / effective number of holdings audit
max_weight audit
收益集中度 audit
```

### 2.3 seed stability 失败，不是单 seed 偶然

本轮：

```text
above_baseline_seed_count = 0 / 3
```

这说明当前配置没有形成稳定可复现的 validation edge。审查者不得允许执行者用单 seed、单 checkpoint 或单次局部收益解释为 PAL2 通过。

### 2.4 minimal training 不等于完整论文方法

本轮配置是 CPU minimal sanity：

```text
episode_count = 32
batch_count = 128
seed_count = 3
```

它不足以代表完整 EIIE / FinRL / PGPortfolio 论文方法最终失败。但当前失败模式已经暴露出结构性问题：

```text
after-cost objective 不够强
turnover/no-trade 机制不足
concentration 约束不足
```

如果在这些问题未修复前直接加长训练，风险是把高 gross、高换手、高集中度行为训练得更稳定，而不是更接近可用 policy。

## 3. 对“是否直接完整训练”的判断

不建议现在直接进入长训练或 GPU full training。

理由：

```text
1. 当前不是单纯 underfit，而是 reward/action/cost/concentration 结构未对齐 after-cost 目标。
2. gross 与 net 断裂已经足够明显。
3. concentration fail 是 portfolio allocation 结构性风险，不会靠训练更久自然消失。
4. seed stability 0/3 说明当前 objective 下没有稳定趋势。
```

因此后续顺序应为：

```text
PAL2-R: cost-aware + concentration-constrained repair
-> 若 validation after-fee-tax、seed stability、cost sensitivity、concentration 同时通过
-> 再考虑 PAL2-FULL / GPU / 更长训练
-> 再由统筹授权 PAL3 strict_test
```

## 4. PAL2-R 应采用的修复方向

审查者给执行者写下一步工作文档时，应把 PAL2-R 限定为结构性修复，而不是无界调参。

允许的修复方向：

```text
1. transaction-cost-aware reward：
   reward 必须以 after-fee-tax NAV change 为主目标，
   并显式记录 fee、sell tax、turnover、cost drag。

2. turnover penalty：
   对 rebalance_delta_diagnostic 加惩罚，
   防止模型用高换手追逐 gross return。

3. no-trade / rebalance threshold：
   小于阈值的 allocation delta 不触发 simulated rebalance，
   对应交易成本文献中的 no-trade region 思路。

4. allocation smoothing：
   约束 w_t 与 w_{t-1} 的变化，
   让 PVM 不只是输入，而是实际影响动作稳定性。

5. concentration control：
   加单资产 soft cap / hard diagnostic cap / entropy regularizer / HHI penalty。

6. diversification audit：
   输出 max_weight、HHI、effective_holding_count、top1/top3 weight share。

7. cost sensitivity：
   至少继续做 cost_multiplier = 0.0 / 0.5 / 1.0 / 2.0。

8. baseline clone audit：
   继续证明不是简单复制 PAL1 baseline 或等权 top20。
```

不建议 PAL2-R 做：

```text
1. 直接换 PPO / DDPG / SAC。
2. 直接扩到 qlib+LTR。
3. 直接增加 universe 或 lookback 大范围搜索。
4. 直接加长训练并声称 full paper method。
5. 根据 validation 反复调参。
6. 读取 strict_test。
```

## 5. PAL2-R 建议实验设计

PAL2-R 应保持 train / validation / strict_test 隔离：

```text
train = 2023-01-01..2024-12-31
validation = 2025-01-01..2025-12-31
strict_test = declared only, not used
```

建议只允许少量预声明 config，不允许执行者自由网格搜索。可采用：

```text
base_config: PAL2 minimal EIIE-CNN with PVM 原配置
repair_a: base + turnover penalty
repair_b: base + turnover penalty + rebalance threshold
repair_c: base + turnover penalty + rebalance threshold + concentration penalty/cap
```

每个 config 必须同样运行：

```text
seeds = [11, 23, 37]
same train window
same validation window
same baseline
same artifact schema
strict_test_used = false
```

选择规则必须预先固定：

```text
primary metric = validation_net_return_after_fee_tax
hard gates = seed stability + concentration + cost sensitivity + contract audit
```

不能用以下指标作为通过条件：

```text
gross return
train return
单 seed 最好结果
零成本 cost_multiplier=0.0 结果
人工挑选 checkpoint 后的 validation peak
```

## 6. PAL2-R 通过条件建议

审查者可以把 PAL2-R 通过条件写成：

```text
1. selected validation net_return_after_fee_tax > PAL1 validation baseline。
2. seed stability pass，至少多数 seed 超 baseline，且不能只有单 seed 支撑。
3. cost sensitivity pass，1.0x 成本下必须超 baseline，2.0x 成本下不得崩溃到明显不可用。
4. concentration pass，max_weight / HHI / effective_holding_count 达到预设阈值。
5. turnover/cost drag 明显低于 PAL2 minimal，或至少不再吞噬大部分 gross return。
6. baseline clone audit pass。
7. strict_test_used=false。
8. forbidden consumer / OrderIntent / target_weight / target_position / quantity audit pass。
```

如果 PAL2-R 仍失败，则建议审查者回到统筹，不要自动进入：

```text
PAL3
PPO
DDPG/SAC
qlib+LTR
full GPU training
```

## 7. 给审查者的下一步指令

请审查者基于本意见文档撰写下一份工作文档：

```text
docs/tw_portfolio_decision_model/POLICY_PAL2_R_COST_AWARE_CONCENTRATION_CONSTRAINED_EIIE_WORK_CN.md
```

工作文档应要求执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_PAL_PAPER_ALIGNED_PORTFOLIO_ALLOCATION_RL_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PAL2_MINIMAL_EIIE_CNN_TRAINING_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PAL2_MINIMAL_EIIE_CNN_TRAINING_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_PAL2_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
```

PAL2-R 输出建议：

```text
data_tw/experiments/paper_aligned_portfolio_rl/pal2_r_cost_concentration_repair/
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

docs/tw_portfolio_decision_model/POLICY_PAL2_R_COST_AWARE_CONCENTRATION_CONSTRAINED_EIIE_EXECUTION_REPORT_CN.md
```

## 8. 禁止事项再次确认

PAL2-R 仍然禁止：

```text
strict_test
PAL3
qlib+LTR
OrderIntent
target_weight
target_position
quantity
broker / quick-trade / real order
provider publish / accepted latest switch
monitor write
frontend default
Agent recommendation
```

`allocation_weight_diagnostic` 仍只能作为：

```text
simulation-only
readonly research replay only
not production
not order
not advice
```

## 9. 统筹判断

本轮 PAL2 失败是有价值的，因为它把问题定位到了：

```text
不是 baseline 已经没有提升空间，
而是当前 allocation policy 没有把 after-cost、低无效换手、集中度控制做进学习目标和动作约束。
```

后续应继续死磕 policy，但要从论文机制出发，优先修正：

```text
reward/action/cost/concentration
```

而不是继续做：

```text
无界调参
直接加长训练
直接 strict_test
直接换新算法
```
