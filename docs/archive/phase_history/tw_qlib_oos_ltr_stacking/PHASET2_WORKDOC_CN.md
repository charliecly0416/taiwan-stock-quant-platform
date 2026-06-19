# Phase T2 工作文档：LTR Stacking 训练与同窗口只读回放

生成日期：2026-06-15

前置 gate：

```text
phase_t1_oos_sample_audit_review_passed_proceed_to_t2
```

依据文档：

```text
docs/TW_STOCK_QLIB_OOS_LTR_STACKING_MAINLINE_CN.md
docs/tw_qlib_oos_ltr_stacking/PHASET0_EXECUTION_REPORT_CN.md
docs/tw_qlib_oos_ltr_stacking/PHASET1_WORKDOC_CN.md
docs/tw_qlib_oos_ltr_stacking/PHASET1_EXECUTION_REPORT_CN.md
```

## 1. T2 目标

Phase T2 目标是验证：

```text
时序错开的 qlib OOS score -> LTR meta-reranker
在同一 final test 上是否比 fresh qlib/top50 adaptive 更稳定、更有研究增益。
```

T2 允许：

- 训练 LTR stacking 模型；
- 在冻结 final test 上做只读历史回放；
- 做有限窗口敏感性验证；
- 输出 train / validation / final test、年度 / regime、common universe、费用税费、换手、回撤、单票贡献等审计。

T2 不允许：

- 改前端/API；
- 切换默认策略；
- 输出真实交易指令；
- provider refresh / publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / orders / quick-trade。

默认策略与产品只读展示合同留到 T3。

## 2. 固定输入

T2 必须以 T1 产物作为训练/验证输入：

```text
data_tw/experiments/tw_qlib_oos_ltr_stacking/phase_t1/phase_t1_ltr_samples.csv
data_tw/experiments/tw_qlib_oos_ltr_stacking/phase_t1/phase_t1_qlib_oos_scores.csv
data_tw/experiments/tw_qlib_oos_ltr_stacking/phase_t1/phase_t1_score_provenance.csv
data_tw/experiments/tw_qlib_oos_ltr_stacking/phase_t1/phase_t1_leakage_audit.json
data_tw/experiments/tw_qlib_oos_ltr_stacking/phase_t1/phase_t1_horizon_guard_audit.csv
```

训练/验证 split：

```text
LTR train:       2020-01-02..2024-06-14
LTR validation:  2024-07-01..2025-06-16
final test:      2025-07-01..2026-05-07
```

guard 区间继续禁止进入训练、validation、模型选择或窗口选择：

```text
2024-06-17..2024-06-28
2025-06-17..2025-06-30
```

## 3. Final Test 推理期输入合同

T2 必须先冻结并审计 `2025-07-01..2026-05-07` 的推理期 score / feature 生成合同。

要求：

- final test qlib score 只用于推理和历史回放；
- final test label / return / replay result 不得用于训练、validation、模型选择或窗口选择；
- 若需要生成 final test qlib score，必须满足 `qlib train end < score start`；
- 不得触发 provider refresh / publish / accepted latest switching；
- 不得使用 final test 结果反向决定 qlib score window 或 LTR window；
- final test features 必须只使用 sample date 当日及过去数据。

T2 报告必须输出 final test provenance 表：

| score window | qlib train start | qlib train end | score source | usage | OOS pass |
| --- | --- | --- | --- | --- | --- |
| 2025-07-01..2026-05-07 | 待填 | 待填 | 待填 | inference_only | yes/no |

若无法合规生成 final test score / feature，T2 必须停止，不得用替代口径静默回放。

## 4. 有限窗口矩阵

T2 只能在 T0 冻结的有限矩阵内执行。

qlib train window candidates：

| id | score policy | 目的 |
| --- | --- | --- |
| Q0 | expanding frozen/WF，score window 前一年底截止 | 长历史基线 |
| Q1 | recent 5y rolling OOS | 较近期窗口 |
| Q2 | recent 7-8y / expanding long OOS | 较长窗口对照 |

LTR train window candidates：

| id | train sample length | 目的 |
| --- | --- | --- |
| L1 | 1y OOS score sample | 太短纠错窗口 |
| L2 | 2y OOS score sample | 推荐最小稳健候选 |
| L3 | 3y OOS score sample | 与旧 Phase1C 经验接近 |
| L4 | 4y OOS score sample | 较长样本候选 |

算力或数据不足时，优先保留：

```text
qlib: Q0 vs Q1
LTR:  L2 vs L3
```

禁止新增窗口、扩大搜索或根据 final test 表现事后补跑窗口。

## 5. 待比较策略

T2 至少比较：

```text
fresh qlib/top50 adaptive
old/frozen qlib + stacked LTR simple
old/frozen qlib + stacked LTR turnover-controlled
fresh qlib + fresh LTR simple
fresh qlib + fresh LTR turnover-controlled
```

若某策略无法在冻结合同下合规生成，必须报告原因并标记为不可比，不得用近似替代。

## 6. 模型选择规则

T2 必须先基于 train / validation 做模型与窗口选择，再进入 final test 评估。

选择原则：

- 不得只选 final test 收益最高的窗口；
- 不得用 final test 回放表现调参；
- 若 train 显著优于 validation / final test，标记过拟合风险；
- 若 validation 与 final test 方向相反，标记稳定性不足；
- 若 stacked LTR 在 common universe 下优势小于 2-3 个百分点，不建议切默认；
- 若收益来自少数日期或少数股票，标记贡献集中风险；
- 若回撤或换手显著恶化，不得只按收益率推荐。

## 7. 必做审计

T2 报告必须包含：

1. score provenance / OOS 审计；
2. train / validation / final test 表现；
3. 年度分段表现；
4. regime 分段表现；
5. full dynamic universe 结果；
6. common universe 对照；
7. 持仓贡献审计；
8. 单票贡献集中度；
9. 异常价格 / 单票异常收益审计；
10. next-day accounting audit；
11. 费用税费审计；
12. 换手率、action_count、最大回撤；
13. LTR feature importance / qlib score 依赖度；
14. train vs validation vs final test 过拟合审计。

## 8. 输出指标

核心指标至少包括：

```text
fee_tax_adjusted_net_return
gross_return
max_drawdown
turnover
action_count
annualized_return
volatility
sharpe_like_metric
win_days / loss_days
largest_single_stock_contribution
largest_single_day_contribution
```

注意：`win_days` 只允许作为历史回放统计，不得写成未来胜率或上涨概率。

## 9. 交付物

执行者应提交：

```text
docs/tw_qlib_oos_ltr_stacking/PHASET2_EXECUTION_REPORT_CN.md
```

建议数据产物目录：

```text
data_tw/experiments/tw_qlib_oos_ltr_stacking/phase_t2/
```

建议产物：

```text
phase_t2_final_test_score_provenance.csv
phase_t2_ltr_model_registry.csv
phase_t2_window_matrix_results.csv
phase_t2_strategy_comparison_full_universe.csv
phase_t2_strategy_comparison_common_universe.csv
phase_t2_yearly_results.csv
phase_t2_regime_results.csv
phase_t2_turnover_fee_audit.csv
phase_t2_next_day_accounting_audit.csv
phase_t2_contribution_audit.csv
phase_t2_single_stock_outlier_audit.csv
phase_t2_overfit_audit.csv
phase_t2_summary.json
```

## 10. T2 通过标准

T2 可提交审查的最低标准：

- final test score / feature 生成合同合规；
- 所有 LTR train / validation score 保持 OOS 语义；
- final test 未参与训练、validation、模型选择或窗口选择；
- stacked LTR 的增益在 common universe 下仍存在；
- 增益不是由单票、单日、异常价格或 universe 差异主导；
- 回撤、费用税费后收益、换手和 action_count 同时可接受；
- 窗口结论不是事后挑最高收益；
- 未触发任何真实交易、monitor、provider、accepted latest 或前端/API 改动。

若优势不足、稳定性不足或风险审计不过，T2 应给出“不建议进入 T3 默认候选”的结论。

## 11. 安全边界

T2 报告和产物中允许使用以下语义：

```text
只读回放
历史模拟
研究候选
策略比较
费用税费后收益
最大回撤
换手率
```

禁止输出：

```text
买入/卖出指令
持有建议
目标仓位
target position
target weight
下单
连接券商
收益承诺
胜率承诺
上涨概率承诺
```

若报告中出现买入/卖出等词，只能出现在“禁止事项、拒绝语义、历史回放术语解释”中，不能作为行动建议。

## 12. 给执行者的一句话

请按本工作文档执行 Phase T2：先冻结 final test 推理期 score/feature 合同，再在 T0/T1 冻结矩阵内训练 LTR stacking 并做同窗口只读历史回放；必须同时输出 full universe 与 common universe、年度/regime、费用税费、换手、回撤、贡献集中和过拟合审计，不得事后扩展窗口或触发任何真实交易/monitor/provider/accepted latest/前端 API 链路。
