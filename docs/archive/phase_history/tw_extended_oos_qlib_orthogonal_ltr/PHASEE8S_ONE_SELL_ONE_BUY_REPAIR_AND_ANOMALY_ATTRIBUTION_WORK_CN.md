# Phase E8S 工作文档：One-Sell-One-Buy 修复与异常归因

生成日期：2026-06-16

## 1. 背景与目标

Phase E8R 报告发现：

```text
one_sell_one_buy 规则实现与工作文档不一致。
```

工作文档要求：

```text
当前持仓不在当日 score 排序 top10 target set 内，最多卖出 1 支，
优先卖出排名最差或已不在候选池的股票。
```

但 E8R 实现中：

```python
sell_candidates = sorted(
    sell_candidates,
    key=lambda x: (0 if x not in cand_set else 1, cand.index(x) if x in cand else 9999, x),
    reverse=False,
)
sells = sell_candidates[:1]
```

该逻辑会优先卖出：

1. 已不在 candidate top50 的股票；
2. 若仍在 candidate top50，则卖出 `cand.index` 更小、也就是排名更好的股票。

这与“卖出排名最差”相反。

异常现象是：错误规则下 E4 one_sell_one_buy 收益达到 `0.96184`，显著高于 E4 original `0.602499`，也高于 E4 top50-exit `0.630662`。本阶段必须同时完成：

1. 修复 one_sell_one_buy 规则并重跑；
2. 保留错误规则结果作为 anomaly case，解释为什么误打误撞表现很好；
3. 判断错误规则是否只是 bug 结果，还是揭示了某种可研究但未冻结的新策略假设。

本阶段只做只读审计与回放，不训练 qlib/LTR，不调参，不改默认策略，不改前端/API。

## 2. 输入冻结

只能使用 E8R 已使用的既有 artifact：

```text
fresh qlib control:
data_tw/experiments/fresh_top50_coverage_repair/phasec4_repaired_replay_ready_scores.csv

E6 Branch A fresh qlib + 2025 orthogonal LTR:
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_replay_ready_scores_2026.csv

E4 2018-2022 frozen qlib + 2023-2025 orthogonal LTR:
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_replay_ready_scores_2026.csv

price source:
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/
```

窗口固定：

```text
2026-01-01..2026-05-07
```

## 3. 必须实现的规则版本

本阶段必须明确区分三个规则，不得混名：

### 3.1 original

复用 S2D/E4 原始 replay：

```text
sell: 持仓不在当日 score top10 target set 内则卖出，可一天卖多支
buy: 每个 signal day 最多买入 1 支 top10 内未持有股票
```

### 3.2 one_sell_one_buy_correct

这是合同要求的正确版：

```text
candidate_k = 50
target_position_count = 10
sell_pool = 当前持仓中不在当日 score top10 target set 的股票
sell_priority:
  1. 已不在 candidate top50 的股票优先卖；
  2. 若仍在 candidate top50，卖出 score 排名最差者；
  3. 若并列，用 instrument 升序稳定排序。
sell_limit = 每个 signal day 最多 1 支
buy: 每个 signal day 最多买入 1 支 score 排序最高且未持有股票
execution: next trading day
```

注意正确排序应等价于：

```python
def sell_key(symbol):
    if symbol not in cand_set:
        return (0, 9999, symbol)
    return (1, -rank_in_candidate[symbol], symbol)
```

然后取 key 最小者；或者直接显式写成“not in top50 first, otherwise max rank number”。

不得再使用 E8R 错误逻辑。

### 3.3 one_sell_one_buy_buggy_e8r

保留 E8R 错误版作为 anomaly case：

```text
sell: 当前持仓不在 top10，最多卖 1 支；
buggy priority:
  1. 已不在 top50 的股票优先卖；
  2. 若仍在 top50，错误地卖出 score 排名较好的股票。
buy: 每个 signal day 最多买入 1 支 score 排序最高且未持有股票
```

该规则不得作为默认候选，只用于解释异常。

## 4. 必须重跑的对照

对以下三种策略分别跑 `original`、`one_sell_one_buy_correct`、`one_sell_one_buy_buggy_e8r`：

1. `fresh_qlib_adaptive`
2. `fresh_qlib_2025_ltr`
3. `e4_frozen_qlib_2023_2025_ltr`

同时保留 top50-exit 结果作为参考，但本阶段重点不是重审 top50-exit。

报告必须输出：

| rule | fresh | fresh+2025 LTR | E4 |
| --- | ---: | ---: | ---: |
| original | 复现 | 复现 | 复现 |
| top50_exit | 复现 | 复现 | 复现 |
| one_sell_one_buy_correct | 新结果 | 新结果 | 新结果 |
| one_sell_one_buy_buggy_e8r | 复现 E8R 错误结果 | 复现 E8R 错误结果 | 复现 E8R 错误结果 |

若 `one_sell_one_buy_buggy_e8r` 不能复现 E8R 的 `E4 = 0.96184`，必须停止解释。

## 5. 异常归因审计

必须解释为什么 buggy rule 会出现高收益，尤其是 E4 的 `0.96184`。

执行者必须输出以下归因：

### 5.1 逐日卖出选择差异

比较 correct vs buggy：

```text
signal_date
holdings_before_signal
candidate_rank_by_symbol
target_top10
correct_sell_symbol
correct_sell_rank
buggy_sell_symbol
buggy_sell_rank
same_sell
next_execution_date
correct_sell_forward_return_to_end
buggy_sell_forward_return_to_end
```

目的：判断 buggy 是否因为“卖掉排名较好者”反而避开了后续下跌。

### 5.2 被错误保留股票贡献

列出 buggy 相对 correct 多保留的股票：

```text
symbol
first_divergence_date
days_extra_held_by_buggy
pnl_extra_vs_correct
max_drawdown_during_extra_hold
whether_rank_worse_at_divergence
```

目的：判断 96.18% 是否来自少数被错误保留的长持强势股。

### 5.3 被错误卖出股票贡献

列出 buggy 相对 correct 提前卖出的股票：

```text
symbol
first_divergence_date
days_less_held_by_buggy
pnl_avoided_or_missed
forward_return_after_buggy_sell
```

目的：判断 buggy 是否偶然避开了高排名但后续下跌的股票。

### 5.4 收益集中度

对 buggy E4 的 96.18% 必须输出：

```text
top1 positive pnl share
top3 positive pnl share
top5 positive pnl share
top10 positive pnl share
largest single divergence contribution
```

若 top3 或某个 divergence 贡献过大，不能作为稳健策略，只能作为异常现象。

### 5.5 排名信号反转检查

必须检查在 E4 score 中，`rank 11..50` 被错误保留的股票是否在后续收益上系统性强于 `rank 1..10`：

```text
daily mean forward return by rank bucket:
  rank 1-10
  rank 11-20
  rank 21-30
  rank 31-50
```

这一步只用于诊断，不得把 future return 引入策略。

如果 rank 11-50 在该窗口明显更强，说明 E4 LTR top10 在 2026 可能存在过度追高或排序反转风险。

## 6. Qlib/LTR 结论保护

本阶段不得用 buggy rule 推翻或支持“LTR 有增益”的主结论。

必须把结论分成三类：

1. `valid_controlled_result`：合同正确、可进入策略讨论；
2. `bug_anomaly_result`：实现错误导致，只能用于诊断；
3. `hypothesis_for_future_work`：如果 buggy 暗示“保留中位排名股票”有效，只能另开新支线验证，不能混入当前默认策略。

特别要求：

- 若 correct one_sell_one_buy 下 LTR 仍提升 qlib，说明 LTR 结论在低换手正确规则下仍有支持。
- 若 correct one_sell_one_buy 下 LTR 不提升 qlib，必须说明该结论只限于该 replay rule，不得外推到 original 或其他规则。
- buggy E4 96.18% 不能作为默认策略收益证据。

## 7. 停止条件

遇到以下情况必须停止：

- 无法复现 E8R buggy one_sell_one_buy 结果；
- correct rule 与工作文档仍不一致；
- 使用 future return/label/realized PnL 参与 replay decision；
- next-day execution 被破坏；
- 持仓重复、卖空、现金穿透、超过目标持仓且无法解释；
- 任何重训、调参、换 score column；
- 任何 provider / accepted latest / frontend / API / monitor / broker / order 链路被触发。

## 8. 输出 Artifact

建议输出目录：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8s_one_sell_one_buy_repair_and_anomaly_attribution/
```

至少输出：

```text
phasee8s_manifest.json
phasee8s_replay_rule_summary.csv
phasee8s_daily_nav.csv
phasee8s_actions.csv
phasee8s_rule_implementation_audit.csv
phasee8s_next_day_accounting_audit.csv
phasee8s_position_integrity_audit.csv
phasee8s_correct_vs_buggy_sell_decision_diff.csv
phasee8s_buggy_extra_held_pnl.csv
phasee8s_buggy_early_sold_pnl.csv
phasee8s_buggy_e4_pnl_concentration.csv
phasee8s_rank_bucket_forward_return_diagnostic.csv
phasee8s_forbidden_action_audit.json
```

## 9. 执行报告

必须输出：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE8S_ONE_SELL_ONE_BUY_REPAIR_AND_ANOMALY_ATTRIBUTION_EXECUTION_REPORT_CN.md
```

报告必须回答：

1. correct one_sell_one_buy 的真实收益是多少；
2. E8R buggy one_sell_one_buy 是否复现；
3. buggy E4 为什么能到约 96.18%；
4. 该异常是否由少数股票或少数日期贡献；
5. 是否存在 E4 score 在 2026 rank bucket 上的排序反转；
6. 哪些结果可参考，哪些必须作废；
7. 是否允许回到默认策略讨论。

## 10. Gate

若完成且无停止条件，gate 为：

```text
phase_e8s_one_sell_one_buy_repair_and_anomaly_attribution_completed
```

