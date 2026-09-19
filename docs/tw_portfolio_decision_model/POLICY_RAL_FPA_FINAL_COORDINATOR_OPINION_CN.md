---
created_at: 2026-06-23
status: coordinator_final_opinion
scope: after_ral_fpa_final_closure_review
closure_review: docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FINAL_CLOSURE_REVIEW_CN.md
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FULL_PATH_BASELINE_PLUS_ACTION_DIAGNOSTIC_MAINLINE_CN.md
fpa4_review: docs/tw_portfolio_decision_model/POLICY_RAL_FPA4_PREDECLARED_FULL_PATH_RULE_SANITY_REVIEW_CN.md
route_closed: true
recommended_next: no_rule_or_model_continuation_without_new_evidence
strict_test_authorized: false
model_training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
---

# RAL-FPA Final Closure 统筹意见：上界存在，但无法稳定转化为可接受规则

## 1. 统筹结论

`POLICY_RAL_FPA_FINAL_CLOSURE_REVIEW_CN.md` 的关闭结论成立：

```text
STOP_NO_PREDECLARED_RULE_SANITY_PASS
```

当前应该关闭 RAL-FPA 主线，不应继续 FPA4 repair、FPA5、strict_test、调阈值、扩候选、训练模型或生产化。

这条路线的完整结论是：

```text
FPA2: 证明 full-path oracle upper-bound 存在；
FPA3: 证明部分 upper-bound 可被低维可观测特征归因；
FPA4: 证明预声明出来的 5 个 full-path rule sanity candidate 全部不能通过完整 gate。
```

因此，失败不是因为没有任何事后空间，而是因为：

```text
事后 upper-bound 无法稳定转化为可交易、可预声明、跨窗口稳健的规则。
```

## 2. 为什么没有候选能够被接受

FPA4 不是执行失败，而是业务 gate 失败。

执行合同本身通过：

```text
candidate_count = 5
threshold_version_count = 7
validation_mining = false
strict_test = false
model_training = false
production = false
```

但所有候选都失败：

```text
candidate_pass_count = 0
```

底层原因分为四类。

## 3. 原因一：候选收益跨年份不稳

FPA4 中确实有候选在 2025 validation 为正，但 rolling OOS 不稳定。

例如 replacement buy 的 `FPA4_C01`：

```text
2023 excess = -0.26714501
2024 excess = 0.03890537
2025 excess = 0.25236201
rolling_oos_mean_excess = 0.00804079
rolling_oos_median_excess = 0.03890537
```

它在 2025 很强，但 2023 明显亏。若接受它，本质是在押注 2025 regime，而不是得到稳健规则。

FPA4 主线要求：

```text
validation 正收益；
rolling OOS mean / median 稳定；
不得单窗口通过。
```

所以 C01 不能通过。

## 4. 原因二：训练/历史强，2025 失效

多个 hold / sell timing 候选在 train 或 2023/2024 很强，但 2025 validation 转负。

例如：

```text
FPA4_C02 hold_continuation / unrealized_gain_large:
  train excess = 1.79417723
  2023 = 0.13600263
  2024 = 0.45457217
  2025 = -0.00244208

FPA4_C03 hold_continuation / unrealized_loss_large:
  train excess = 0.68452722
  2023 = 0.30680016
  2024 = 0.34383622
  2025 = -0.31069264

FPA4_C04 sell_timing / unrealized_gain_large:
  train excess = 0.9338598
  2023 = 0.09104063
  2024 = 0.27649591
  2025 = -0.0135812
```

这说明这些规则捕捉到的是过去窗口的条件结构，但无法在 2025 强 baseline regime 中稳定增益。

如果继续用这批特征调阈值，很容易变成 validation mining。

## 5. 原因三：部分候选只有微弱正收益，不足以抵抗 gate

例如：

```text
FPA4_C05 sell_timing / holding_days_020_059:
  2023 = -0.10797663
  2024 = 0.06805999
  2025 = 0.02334573
  rolling_oos_mean_excess = -0.00552364
  rolling_oos_median_excess = 0.02334573
```

2025 有小幅正收益，但 rolling mean 为负，说明收益边际太薄。

在 baseline 本身 2025 净收益约 `0.95376753` 的情况下，`+0.023` 这种级别如果没有稳定性、集中度和成本证据，不应被接受。

## 6. 原因四：缺少 trade-level / symbol-date PnL attribution，集中度 gate 无法通过

FPA4 的 `symbol_date_concentration_audit.csv` 显示：

```text
concentration_scope = rule_sanity_summary_no_symbol_date_pnl_attribution
symbol_date_concentration_status = not_computed_requires_trade_pnl_attribution
concentration_gate_status = review_required
```

执行脚本没有把该项误判为通过，因此所有 candidate 都不能通过完整 gate。

这不是唯一失败原因，因为多数组合本身收益稳定性也不够；但它说明：

```text
当前 replay summary 级产物不足以证明收益不是来自少数 symbol/date。
```

若未来还要做任何 full-path rule sanity，都必须先补：

```text
trade-level realized/unrealized PnL attribution；
symbol-date contribution audit；
candidate-level concentration gate。
```

否则就算有 validation 正收益，也不能严格通过。

## 7. 更底层的解释

FPA2 上界很高，但 FPA4 规则失败，说明问题不在“动作空间完全没有收益”，而在：

```text
oracle 知道哪些具体动作事后会赢；
低维规则只能用 action 前可观测特征粗略近似；
这种近似在不同年份/regime 中方向不稳。
```

换句话说，真实可利用 edge 很可能是：

```text
高阶、条件化、依赖具体股票和市场路径；
不是单一 rank / holding_days / unrealized bucket 能稳定表达。
```

这也解释了为什么此前 ML/RL、bandit、规则探索都难以超过 baseline：

```text
baseline 已经吃掉主要 qlib ranking alpha；
policy 层剩下的是弱二阶 edge；
弱二阶 edge 在样本少、regime 变化强、交易成本存在时很难稳定提取；
强行加稳定性 gate 后，候选会退化为 baseline clone 或失败。
```

## 8. 后续该怎么做

当前不建议继续同一方向的规则或模型搜索。

不建议：

```text
1. FPA4 repair by adding candidates。
2. FPA4 threshold tuning。
3. FPA5 / strict_test。
4. 训练模型拟合 FPA3/FPA4 这批弱特征。
5. 用 validation 继续找特征组合。
```

原因：

```text
这会把已经失败的规则 sanity 变成反复挖 validation；
即使找到正收益，也缺乏可信 OOS。
```

合理后续只有两个方向。

## 9. 方向 A：收尾并暂停 policy 层收益增强

这是当前最稳妥的选择。

执行：

```text
整理 RAL / ED / FPA 全路线 closure；
明确 policy 层未找到稳定可接受收益；
保留 baseline 作为当前最佳策略；
后续研发资源回到 signal/model/data 或组合风险诊断。
```

这不是承认 baseline 完美，而是承认：

```text
在当前样本、当前输入、当前可审计规则/模型路线下，
policy 层没有稳定可交付的增量收益。
```

## 10. 方向 B：只补基础账本，不做新策略

如果仍希望未来继续 policy，需要先补基础数据，而不是继续写规则。

可新开一个低优先级基础设施支线：

```text
Action / Trade PnL Attribution Ledger
```

目标不是找策略，而是补齐：

```text
1. trade-level realized PnL；
2. open-position unrealized contribution；
3. symbol-date contribution；
4. candidate-level concentration；
5. replacement / sell / hold action 的局部与全路径贡献分解。
```

有了这些之后，未来才有资格回答：

```text
某个规则的收益是否来自少数股票？
某个动作空间的收益是否真实可重复？
某个年份的正收益是否只是集中事件？
```

但这个方向不应承诺短期超过 baseline。

## 11. 到底还有没有方法超过 baseline

结论：

```text
理论上有；
当前证据下没有已证明可走通的方法。
```

更具体地说：

```text
1. block-buy-only 已失败。
2. full-path low-dimensional rules 已失败。
3. ML/RL/bandit 之前也未稳定超过 baseline。
4. baseline/replay 已被审计可信。
```

因此，若问“马上继续找一个规则超过 baseline”，答案应是：

```text
不建议。
```

若问“长期是否还有机会”，可能的突破口不是当前规则层，而是：

```text
1. 更强信号或模型 alpha；
2. 更细粒度 trade-level ledger 后重新做归因；
3. 更长样本或更多市场 regime；
4. portfolio risk / drawdown 约束下的收益风险优化；
5. 接受收益不一定超过 baseline，但改善回撤、波动或收益风险比。
```

但如果唯一目标仍是：

```text
net_return_after_fee_tax > current baseline
```

那当前 policy/rule 主线应暂停。

## 12. 给审查者和执行者的建议

当前不应给执行者新的策略开发任务。

可以给的下一步只有：

```text
1. RAL / ED / FPA 全路线 closure report；
2. 或 Action / Trade PnL Attribution Ledger 基础设施工作文档。
```

建议优先写：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_FPA_POLICY_RESEARCH_CLOSURE_AND_LEDGER_NEXT_OPINION_CN.md
```

该文档应面向外部读者总结：

```text
项目背景；
baseline 口径；
尝试路线；
为什么没有候选通过；
为什么不是 baseline bug；
后续若继续需要先补哪些基础账本。
```

仍然禁止：

```text
strict_test；
模型训练；
新增规则候选；
阈值搜索；
生产/default/order/provider/frontend/Agent 集成。
```

## 13. 一句话

```text
FPA 证明了“事后动作空间有上界”，但也证明了“当前低维可观测规则无法稳定提取这个上界”。

所以当前没有可接受候选；
后续不应继续调规则，而应收尾，或只补 trade-level PnL / concentration ledger 这类基础账本。
```
