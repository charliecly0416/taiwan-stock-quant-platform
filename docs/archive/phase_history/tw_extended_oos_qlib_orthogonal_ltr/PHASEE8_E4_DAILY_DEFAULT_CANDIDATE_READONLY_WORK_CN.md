# Phase E8 工作文档：E4 默认候选只读日更链路

生成日期：2026-06-16

## 1. 本阶段目标

本阶段目标：

```text
把 E4 策略定义为新的默认候选策略，
并接入每日数据更新后的只读候选分数 / top50 rerank / 策略结论生成链路。
```

本阶段只做只读产物与展示准备，不触发真实交易。

## 2. 策略身份

默认候选策略身份冻结为：

```text
strategy_id: e4_frozen_qlib_orthogonal_ltr_2023_2025
qlib_base: 2018-2022 frozen qlib
ltr_model: orthogonal LTR trained on 2023-2025
replay_boundary: qlib top50 rerank only
target_position_count: 10
candidate_k: 50
execution_assumption: next-day execution
```

不得混入：

- E6 2025-only LTR；
- fresh qlib + 2025 LTR；
- O4 old qlib LTR；
- Orthogonal Fresh Qlib；
- 任何新 filter、market gate、turnover rule。

## 3. 每日日更合同

每日数据更新完成后，执行者应只读生成：

1. 最新 signal_asof 的 2018-2022 frozen qlib score/rank；
2. O4/O2 正交特征的 PIT-safe as-of 特征；
3. E4 LTR score；
4. 仅在 qlib top50 内重排后的 top50；
5. 目标 top10 候选；
6. 与上一期候选/持仓模拟结果的 diff；
7. coverage、available_at、next-day replay-ready 审计；
8. 禁止动作审计。

## 4. 数据可用性规则

必须保持：

```text
feature_available_at <= signal_asof
price/tradability available for signal_asof
next execution price only used for backtest/accounting audit, not for ranking
```

不得使用：

- signal_asof 之后的正交数据；
- signal_asof 之后的价格；
- future return；
- future label；
- realized PnL；
- 当日之后才知道的 instrument 状态。

## 5. 输出 Artifact

建议输出目录：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/daily_e4_default_candidate/
```

每个 signal_asof 至少输出：

```text
e4_daily_candidate_manifest_{asof}.json
e4_daily_qlib_top150_scores_{asof}.csv
e4_daily_ltr_top50_rerank_{asof}.csv
e4_daily_target_top10_{asof}.csv
e4_daily_diff_vs_previous_{asof}.csv
e4_daily_coverage_audit_{asof}.csv
e4_daily_pit_available_at_audit_{asof}.csv
e4_daily_forbidden_action_audit_{asof}.json
```

## 6. 默认展示边界

若用户确认进入默认展示，前端/API 只能展示：

- 策略名称；
- signal_asof；
- top50 rerank；
- top10 候选；
- 相对上一期变化；
- coverage / PIT / replay-ready 审计状态；
- 风险提示。

不得展示为：

- 自动买卖指令；
- 目标仓位；
- target weight；
- broker order；
- quick-trade；
- 收益承诺；
- 胜率或上涨概率承诺。

## 7. 停止条件

遇到以下任一情况必须停止：

- qlib top50 不完整且无法解释；
- 正交特征 available_at 违规；
- replay-ready coverage 异常；
- 使用 future label / future return / realized PnL；
- 需要重训 qlib 或 LTR；
- 需要改特征、改 label、改参数；
- 需要触发 provider publish / accepted latest switch；
- 需要触发 monitor scan / broker / orders / quick-trade。

## 8. 执行报告

必须输出：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE8_E4_DAILY_DEFAULT_CANDIDATE_READONLY_EXECUTION_REPORT_CN.md
```

报告必须说明：

- 是否成功生成最新 signal_asof 候选；
- 是否严格使用 E4 frozen qlib + E4 LTR；
- 是否 top50 rerank only；
- coverage 与 available_at 是否通过；
- 是否触发任何禁止链路；
- 是否允许进入默认展示切换讨论。

## 9. Gate

若完成且未触发停止条件，gate 为：

```text
phase_e8_e4_daily_default_candidate_readonly_completed
```

