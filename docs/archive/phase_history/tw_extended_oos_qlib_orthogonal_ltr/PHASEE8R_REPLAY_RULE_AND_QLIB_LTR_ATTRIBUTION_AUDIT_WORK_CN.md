# Phase E8R 工作文档：Replay Rule 与 Qlib/LTR 归因审计

生成日期：2026-06-16

## 1. 本阶段目标

本阶段目标是正式审计以下异常发现：

```text
在 2026-01-01..2026-05-07 临时只读验证中，
fresh qlib adaptive 在 “跌出 qlib top50 才卖、每天最多买入 1 支” 规则下收益约 96.10%，
而 fresh qlib + 2025 orthogonal LTR 在同规则下约 48.83%。
```

本阶段必须回答：

1. `fresh qlib adaptive + top50-exit` 的高收益是否真实、合规、无未来函数、无实现偏差；
2. 为什么 LTR 在原 E6 规则下提升 qlib，但在 top50-exit 规则下反而削弱 qlib；
3. 前期“orthogonal LTR 对 qlib 有增益”的结论是否只适用于特定 replay rule；
4. 后续默认候选应该冻结哪一种 replay rule，而不是混用收益结论。

本阶段只做只读审计与正式对照回放，不训练 qlib，不训练 LTR，不改默认策略，不改前端/API。

## 2. 必须冻结的输入

执行者只能使用以下既有 artifact：

```text
fresh qlib control:
data_tw/experiments/fresh_top50_coverage_repair/phasec4_repaired_replay_ready_scores.csv

E6 Branch A fresh qlib + 2025 orthogonal LTR:
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_replay_ready_scores_2026.csv

E4 2018-2022 frozen qlib + 2023-2025 orthogonal LTR:
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_replay_ready_scores_2026.csv

price source:
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/

base replay engine reference:
scripts/evaluate_tw_ltr_s2d_full_daily_replay.py
```

不得读取或生成新的训练标签，不得重训模型，不得替换 score column。

## 3. 必须正式比较的策略

窗口统一为：

```text
2026-01-01..2026-05-07
```

初始资金、手续费、交易税、lot size、next-day execution 必须与 S2D/E4/E6 replay engine 保持一致。

### 3.1 原规则复现

先复现既有结果，作为 sanity check：

| strategy | expected net return |
| --- | ---: |
| fresh qlib adaptive 原规则 | `0.289419` |
| fresh qlib + 2025 LTR 原规则 | `0.464734` |
| E4 frozen qlib + 2023-2025 LTR 原规则 | `0.602499` |

原规则定义必须明确写出：

```text
candidate_k = 50
target_position_count = 10
sell: 当前持仓不在当日 score 排序 top10 target set 内则卖出，可一天卖多支
buy: 每个 signal day 最多买入 1 支 target set 内未持有股票
execution: next trading day
```

### 3.2 Top50-exit 规则

正式实现并回放：

```text
candidate_k = 50
target_position_count = 10
sell: 只有持仓跌出 qlib top50 / candidate set 才卖出；若多支同时跌出，则全卖出
buy: 每个 signal day 最多买入 1 支
buy ranking:
  - fresh qlib adaptive: 按 adaptive_score_baseline 在 qlib top50 内排序，买未持有最高名
  - fresh qlib + 2025 LTR: 按 phasee6_branch_a_fresh_ltr_score 在 qlib top50 内重排，买未持有最高名
  - E4: 按 phasee3_extended_oos_ltr_score 在 qlib top50 内重排，买未持有最高名
execution: next trading day
```

临时验证参考值如下，但执行者必须独立复现并审计：

| strategy | temporary net return |
| --- | ---: |
| fresh qlib adaptive top50-exit | `0.960964` |
| fresh qlib + 2025 LTR top50-exit | `0.488315` |
| E4 top50-exit | `0.630662` |

若正式结果与临时值不一致，必须停下来解释差异。

### 3.3 每日最多一卖一买规则

也必须正式回放：

```text
sell: 当前持仓不在当日 score 排序 top10 target set 内，最多卖出 1 支，优先卖出排名最差或已不在候选池的股票
buy: 每个 signal day 最多买入 1 支 score 排序最高且未持有股票
```

该规则用于判断 60.25% 是否依赖多卖机制，以及是否存在更合理的低换手生产规则。

## 4. Qlib 重点审计要求

本阶段必须把 qlib 审计放在第一优先级。原因是如果 `fresh qlib adaptive + top50-exit` 的 96% 是真实结果，那么默认策略讨论需要重新排序；如果它来自实现偏差，则不能让该结果污染 LTR 结论。

必须检查：

1. `fresh qlib adaptive` 的 score column 是否只来自 repaired fresh qlib artifact；
2. 是否错误使用了 future return、future label、realized PnL 或 2026 之后数据；
3. qlib top50 membership 是否按每个 signal_asof 当日 score/rank 得到，而不是从未来日期倒灌；
4. 持仓“是否跌出 top50”的判断是否使用当日 qlib top50 candidate set；
5. 买入排序是否只使用当日可见 score；
6. next-day execution price 是否只用于成交和记账，不参与 ranking；
7. pending order 是否导致同一股票重复买入、重复卖出、卖空、现金穿透或持仓数量异常；
8. final NAV 是否包含仍持仓股票的 mark-to-market，而不是只看已实现收益；
9. 价格文件是否存在复权、停牌、缺价、异常跳价导致的收益集中；
10. 收益是否由少数 1-3 支股票贡献超过 50%，若是必须列出并人工解释。

必须输出 qlib 专项审计表：

```text
phasee8r_qlib_top50_exit_audit.csv
phasee8r_qlib_position_lifecycle.csv
phasee8r_qlib_pnl_concentration.csv
phasee8r_qlib_forbidden_field_audit.json
```

## 5. LTR 归因审计要求

执行者不能简单说“LTR 无效”。必须解释 LTR 在不同 replay rule 下的作用边界：

1. 原规则下 LTR 是否通过更快 top10 轮动带来收益；
2. top50-exit 规则下，LTR 是否因为改变买入优先级而错过 fresh qlib 的长期强势股；
3. 对 fresh qlib + 2025 LTR，列出 top50-exit 下相对 pure fresh qlib 的：
   - 买入差异；
   - 持仓差异；
   - 卖出差异；
   - 单票 PnL 差异；
   - 前 20 个导致收益差的交易事件。
4. 检查 LTR score 是否只在 qlib top50 内重排，没有引入 top50 外股票。
5. 检查 LTR 输入特征 available_at 是否 PIT-safe。

必须输出：

```text
phasee8r_ltr_vs_qlib_trade_diff.csv
phasee8r_ltr_vs_qlib_position_diff_by_day.csv
phasee8r_ltr_vs_qlib_pnl_diff_by_symbol.csv
phasee8r_ltr_attribution_summary.csv
```

## 6. 公平性与控制变量

所有对照必须保持：

- 同窗口；
- 同初始资金；
- 同 fee/tax/lot size；
- 同 next-day execution；
- 同 price source；
- 同 qlib top50 coverage；
- 同 candidate_k；
- 同 target_position_count；
- 不重训；
- 不调参；
- 不新增 filter、market gate、turnover rule。

除 replay rule 与 score column 外，不得改变其他变量。

## 7. 停止条件

遇到以下任一情况必须停止并报告：

- fresh qlib top50-exit 96% 无法复现；
- qlib top50 membership 存在未来倒灌；
- score column 与合同不一致；
- replay 中使用了 future label / future return / realized PnL；
- next-day execution 不完整或使用同日/未来不可得价格；
- pending order 导致持仓重复、卖空、现金异常或超过目标持仓且无法解释；
- LTR 分数覆盖不是每天 50/50/50；
- 任何模型被重新训练；
- 任何 provider / accepted latest / monitor / frontend / API / broker / quick-trade / order 链路被触发。

## 8. 输出 Artifact

建议输出目录：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e8r_replay_rule_and_qlib_ltr_attribution_audit/
```

至少输出：

```text
phasee8r_manifest.json
phasee8r_replay_rule_summary.csv
phasee8r_daily_nav.csv
phasee8r_actions.csv
phasee8r_coverage_audit.csv
phasee8r_next_day_accounting_audit.csv
phasee8r_position_integrity_audit.csv
phasee8r_qlib_top50_exit_audit.csv
phasee8r_qlib_position_lifecycle.csv
phasee8r_qlib_pnl_concentration.csv
phasee8r_ltr_vs_qlib_trade_diff.csv
phasee8r_ltr_vs_qlib_position_diff_by_day.csv
phasee8r_ltr_vs_qlib_pnl_diff_by_symbol.csv
phasee8r_ltr_attribution_summary.csv
phasee8r_forbidden_action_audit.json
```

## 9. 执行报告

必须输出：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE8R_REPLAY_RULE_AND_QLIB_LTR_ATTRIBUTION_AUDIT_EXECUTION_REPORT_CN.md
```

报告必须包含：

1. 原规则复现是否通过；
2. top50-exit 规则正式结果；
3. 每日最多一卖一买规则正式结果；
4. fresh qlib 96% 是否公平、合理、无未来函数；
5. LTR 在 top50-exit 下为什么弱于 pure qlib；
6. 前期“LTR 有增益”结论是否仍成立，以及成立边界是什么；
7. 是否建议进入默认策略决策；
8. 若建议进入，候选默认策略到底是：
   - fresh qlib adaptive top50-exit；
   - E4 original；
   - E4 top50-exit；
   - fresh qlib + LTR；
   - 或继续保持现默认。

## 10. Gate

若全部审计完成且无停止条件，gate 为：

```text
phase_e8r_replay_rule_and_qlib_ltr_attribution_audit_completed
```

