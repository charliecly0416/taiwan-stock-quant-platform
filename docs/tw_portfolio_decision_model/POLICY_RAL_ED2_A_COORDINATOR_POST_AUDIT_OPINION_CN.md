---
created_at: 2026-06-23
status: coordinator_post_audit_opinion
scope: after_ral_ed2_a_baseline_replay_accounting_audit_review
review_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ED2_A_BASELINE_REPLAY_ACCOUNTING_AUDIT_REVIEW_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_RAL_ED2_A_BASELINE_REPLAY_ACCOUNTING_AUDIT_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/explicit_rule_discovery/ral_ed2_a_baseline_replay_accounting_audit
recommended_control: close_block_buy_only_route_as_negative_evidence
recommended_next_if_continue: full_path_baseline_plus_action_space_diagnostic
ral_ed3_authorized: false
strict_test_authorized: false
threshold_tuning_authorized: false
rule_grid_authorized: false
model_training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
---

# RAL-ED2-A 后统筹意见：Baseline 可信，Block-buy-only 失败，应关闭该支线并更换动作空间

## 1. 统筹结论

`POLICY_RAL_ED2_A_BASELINE_REPLAY_ACCOUNTING_AUDIT_REVIEW_CN.md` 的审查结论成立：

```text
PASS_WITH_MINOR_CONDITION_CLOSE_BLOCK_BUY_ROUTE_AS_NEGATIVE_EVIDENCE
```

本轮最关键的事实是：

```text
ED2 reported baseline net_return_after_fee_tax = 0.95376753
ED2-A recomputed baseline net_return_after_fee_tax = 0.95376753
absolute_diff = 0
validator_ok = true
failed_count = 0
```

同时：

```text
baseline final_equity = 1953767.53
baseline gross_return = 1.09998226
baseline max_drawdown = -0.34681374
baseline action_count = 436
baseline buy_count = 223
baseline sell_count = 213
baseline turnover_proxy = 42.18778217
baseline fee_and_tax = 146214.73
negative_cash_count = 0
missing_price_count = 0
```

期末清算敏感性也不改变结论：

```text
baseline_net_return_nav = 0.95376753
baseline_net_return_if_liquidated_at_period_end = 0.94512277
liquidation_fee_tax_drag = 8644.76
```

市场对比显示：

```text
TWII_2025_return = 0.26854957
baseline_2025_return = 0.95376753
baseline_excess_vs_TWII = 0.68521796
baseline_average_cash_rate = 0.12981877
baseline_max_holding_count = 10
```

因此，当前不能再把 ED2 失败主要归因于 baseline 计算错误。更合理的判断是：

```text
2025 baseline 确实非常强；
ED2 block-buy-only 动作空间太窄；
当前预声明 block-buy 规则没有稳定超过 baseline；
该支线应关闭为 negative evidence。
```

## 2. 这次问题出在哪里

这次问题不在 accounting，不在费用税，不在窗口错位，也不在明显未来数据。

问题主要在策略动作空间：

```text
ED2 只允许 block baseline buy；
不允许替换买入；
不改变卖出时点；
不保留或释放持仓节奏；
不做现金再部署；
不处理组合路径反馈。
```

这种动作空间只有一种可能赢：

```text
baseline 原本买入中存在大量明显负贡献交易，
而规则能稳定识别并挡掉这些交易。
```

但 2025 的事实更像是：

```text
baseline 买入整体很强；
qlib ranking alpha 在 2025 validation 被充分兑现；
挡掉买入会丢失上涨暴露；
只挡不补会把策略推向现金化或 baseline clone。
```

现有 ED2 结果正好符合这个机制：

```text
1. 高阈值 zscore 规则几乎不交易，变成 cash-only，收益为 0。
2. 宽松 zscore / rank_delta 规则几乎不改动作，变成 baseline clone，收益等于 baseline。
3. score_gap_high / cost_edge_high 挡掉大量 baseline 买入，参与率太低，错过收益。
4. score_gap_mid_high 参与率接近 baseline，但仍低于 baseline，说明被挡掉的买入整体不是稳定负贡献。
```

所以这次失败的底层原因是：

```text
block-buy-only 是删除动作，不是优化动作；
在强 ranking alpha 窗口，删除买入通常会降低收益；
除非规则能极精准地只删除坏买入，否则很难超过 baseline。
```

## 3. Baseline 有没有问题

基于 ED2-A，baseline 目前应视为可信。

可信的理由：

```text
1. ED2 reported baseline 被独立重算完全复现。
2. NAV accounting 通过。
3. fee/tax/turnover 通过。
4. pending order window 通过。
5. price/signal alignment 通过。
6. 期末清算后结论不变。
7. rule replay fairness audit 显示 baseline 与 rule 使用同一初始资金、窗口、价格源、费用口径和执行策略。
8. baseline clone 规则能复现 baseline。
```

保留的轻微条件是：

```text
baseline_concentration_summary 未做完整单股/单日集中度归因；
baseline_clone_consistency_audit 可补充 fee/tax 与 turnover 相等列。
```

这些缺口不影响当前主结论，但若后续要形成长期 closure bundle，可以要求执行者补充说明。

## 4. 到底还有没有方法超过 baseline

结论要分层：

```text
当前 block-buy-only 支线：基本没有继续价值。
整个 policy / 显式规则方向：不能判死刑。
```

原因是 baseline 虽强，但并非没有缺点：

```text
max_drawdown = -0.34681374
turnover_proxy = 42.18778217
fee_and_tax = 146214.73
action_count = 436
average_cash_rate = 0.12981877
```

这些说明 baseline 不是完美策略，只是 2025 收益很强。理论上仍可能有改进空间，但改进不应再来自“只挡买入”，而应来自完整组合路径上的 baseline-plus 动作：

```text
1. 替换买入：挡掉低质量 baseline buy 后，买入下一候选，而不是持现金。
2. 卖出时点：baseline 只卖离开 top50 中最差的一只，可能存在提前卖、延后卖、保留强持仓的空间。
3. 持仓延续：当持仓仍强但排名短期波动时，不必机械替换。
4. 市场状态参与：不是简单风险关闭，而是在 risk_off / rebound / trend 强弱中调整参与节奏。
5. 交易成本边际：只有当替换后的 score/expected edge 足够覆盖成本时才动作。
6. 多候选选择：同一天不必只考虑最高分，也不应只用单个阈值删动作。
```

但是必须强调：

```text
是否能超过 baseline 不能靠直觉保证；
必须先做可验证的 upper-bound / attribution diagnostic。
```

如果连 oracle-style diagnostic 都显示改动空间很小，就不应继续投入规则或模型训练。

## 5. 后续不应该做什么

当前不应继续：

```text
1. 调 block-buy 阈值。
2. 扩展 block-buy grid。
3. 在同一 ED2 结果上进入 ED3 strict_test。
4. 用 strict_test 找规则。
5. 训练模型去拟合同一组弱动作。
6. 只追求低换手、低成本、低回撤而不超过 baseline 净收益。
```

原因：

```text
block-buy-only 的失败已经被 baseline audit 确认；
继续调参大概率只是 validation mining；
即使找到局部正收益，也很可能不稳。
```

## 6. 建议下一步

建议分两步走。

### Step 1：关闭当前 block-buy-only route

授权审查者或执行者整理 closure：

```text
RAL-ED2 block-buy-only route closure
```

closure 应包含：

```text
1. ED2 规则结果；
2. ED2-A baseline accounting audit；
3. 为什么不是 baseline bug；
4. 为什么 block-buy-only 动作空间失败；
5. 后续只允许另开新动作空间，不允许继续调 block-buy。
```

### Step 2：若继续 policy/rule，另开 full-path baseline-plus action diagnostic

新方向不应直接做规则回测，而应先做诊断：

```text
full_path_baseline_plus_action_space_diagnostic
```

核心目标：

```text
在完整 readonly portfolio path replay 下，
评估替换买入、卖出时点、持仓延续、市场状态参与是否存在可超过 baseline 的上界空间。
```

先做上界，不先写规则：

```text
1. replacement-buy oracle diagnostic：
   当 baseline buy 被挡掉时，允许从同日后续候选中替换，评估是否存在可实现正上界。

2. sell-timing oracle diagnostic：
   对 baseline sell 做提前/延后/保留的只读路径对比，评估卖出时点是否有可观 edge。

3. hold-continuation diagnostic：
   对被卖出的持仓，评估继续持有若干窗口是否改善净收益。

4. regime-participation diagnostic：
   按市场趋势、波动、回撤、score dispersion 分桶，看 baseline 超额主要来自哪些 regime，规则是否只应在少数 regime 调整。

5. transaction-cost marginal diagnostic：
   对每个替换或卖出动作计算成本覆盖情况，确认收益不是被费用吃掉。
```

只有当这些诊断显示：

```text
存在稳定、非单日/单股集中、扣费税后仍超过 baseline 的上界空间
```

才值得进入下一阶段预声明规则。

## 7. 是否有现实机会超过 baseline

现实判断：

```text
有机会，但难度高，且机会不在 block-buy-only。
```

更具体地说：

```text
1. 只减少买入参与，很难超过 +95.38% 的 2025 baseline。
2. 只降低费用，也很难弥补丢失的上涨收益。
3. 可能有机会的是：在不显著降低有效市场暴露的前提下，减少错误替换、改善卖出时点、用更好的候选替换弱买入。
4. 如果 full-path 上界诊断也没有正空间，则应承认当前 qlib baseline policy 已经很难在 policy 层提升，后续应回到信号/模型或数据层。
```

所以后续判断标准应是：

```text
先证明动作空间有 upper-bound；
再写预声明规则；
再 rolling OOS；
最后才考虑 strict_test。
```

不能再反过来先写规则、再用 validation 找阈值。

## 8. 给审查者和执行者的控制建议

当前授权：

```text
1. 关闭 RAL-ED2 block-buy-only route；
2. 如用户继续推进，另写 full-path baseline-plus action diagnostic 主线或工作文档。
```

当前不授权：

```text
RAL-ED3
strict_test
继续调 block-buy 阈值
扩展 block-buy grid
模型训练
生产/default/order/provider/frontend/Agent 集成
```

如果写下一份工作文档，建议命名为：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FULL_PATH_BASELINE_PLUS_ACTION_DIAGNOSTIC_MAINLINE_CN.md
```

或先写较窄的：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ED2_BLOCK_BUY_ROUTE_CLOSURE_AND_NEXT_ACTION_SPACE_OPINION_CN.md
```

## 9. 一句话结论

```text
这次不是 baseline 算错；
是 block-buy-only 动作空间太弱，无法超过一个经审计可信、且 2025 非常强的 qlib baseline。

后续若还要超过 baseline，不能继续删买入，
必须转向完整组合路径下的替换买入、卖出时点、持仓延续和 regime participation，
并先做 upper-bound / attribution diagnostic 证明那里确实有收益空间。
```
