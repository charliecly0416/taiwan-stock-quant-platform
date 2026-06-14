# Phase B1B 默认基线决策修复执行报告

生成时间：2026-06-14

执行依据：`docs/tw_ltr_baseline_conservative_tuning/PHASEB1_REVIEW_AND_PHASEB1B_DEFAULT_DECISION_REPAIR_WORK_CN.md`

主线依据：`docs/TW_STOCK_LTR_BASELINE_AND_CONSERVATIVE_TUNING_MAINLINE_CN.md`

## 1. 本轮目标和边界

本轮只修复 Phase B1 默认基线决策逻辑，基于 B1 已有结果重新判断 `rank_rotate_top50_adaptive_score` 与 `phase1c_ltr_simple_daily` 谁更适合作为默认主策略。

本轮未跑新回放，未新增候选，未调参，未重训 LTR，未改 Phase1C frozen score，未改 replay 口径，未新增数据源，未联网，未改 provider / accepted latest，未写 monitor，未触碰 broker / quick-trade / orders / target position / target weight，未改前端/API。

## 2. 使用的既有输入

- `data_tw/experiments/ltr_baseline_conservative_tuning/phaseb1_conservative_replay/phaseb1_period_comparison.csv`
- `data_tw/experiments/ltr_baseline_conservative_tuning/phaseb1_conservative_replay/phaseb1_method_summary.csv`
- `data_tw/experiments/ltr_baseline_conservative_tuning/phaseb1_conservative_replay/phaseb1_conservative_candidate_delta.csv`
- `docs/tw_ltr_baseline_conservative_tuning/PHASEB1_CONSERVATIVE_REPLAY_AND_DEFAULT_COMPARISON_EXECUTION_REPORT_CN.md`

## 3. Top50 adaptive vs LTR simple 核心对比

| 指标 | rank_rotate_top50_adaptive_score | phase1c_ltr_simple_daily | 差异判断 |
| --- | ---: | ---: | --- |
| common full range 费用后收益 | 15.963677 | 40.018220 | LTR simple 高 24.054543 |
| common full range 最大回撤 | -0.402422 | -0.387816 | LTR simple 略好 0.014606 |
| common full range 动作数 | 1932 | 1978 | LTR simple 多 46 次 |
| common full range turnover proxy | 184.497379 | 199.489876 | LTR simple 高 14.992497 |
| method summary 平均收益 | 2.813583 | 6.360864 | LTR simple 高 3.547281 |
| method summary 最差收益 | -0.124560 | -0.001630 | LTR simple 更好 0.122930 |
| method summary 平均回撤 | -0.269099 | -0.259522 | LTR simple 略好 0.009577 |
| method summary 最差回撤 | -0.402422 | -0.387816 | LTR simple 略好 0.014606 |
| method summary 平均动作数 | 577.88 | 588.50 | LTR simple 多 10.62 次 |
| method summary 平均 turnover proxy | 55.314834 | 58.785876 | LTR simple 高 3.471042 |
| independent_test 收益 | 2.450848 | 3.550601 | LTR simple 高 1.099753 |
| independent_test 回撤 | -0.167457 | -0.160298 | LTR simple 略好 0.007159 |

结论：按 B1 已有回放指标，`phase1c_ltr_simple_daily` 是效果最好的默认主策略候选。它的收益、最差收益、平均回撤、最差回撤和 independent_test 表现均优于 `rank_rotate_top50_adaptive_score`；动作数和换手确实更高，但幅度不足以直接否决默认资格。

## 4. 逐项回答审查问题

### 4.1 如果默认基线只看 B1 回放指标，是否应承认 LTR simple 优于 Top50 adaptive

是。只看 B1 已有同口径回放指标，应承认 `phase1c_ltr_simple_daily` 优于 `rank_rotate_top50_adaptive_score`。

关键原因是：LTR simple 在 common full range、method summary 平均收益、最差收益、平均回撤、最差回撤、independent_test 收益和 independent_test 回撤上均占优。

### 4.2 Top50 adaptive 相比 LTR simple 的真实优势是什么

Top50 adaptive 的真实优势不是回放效果更好，而是：

- 规则更容易解释；
- 不是 LTR 模型输出，产品说明成本更低；
- common full range 动作数少 46 次；
- common full range turnover proxy 低 14.992497；
- method summary 平均动作数少 10.62 次；
- method summary 平均 turnover proxy 低 3.471042；
- 延续当前产品默认锚点。

这些是产品保守性和解释成本优势，不是量化效果优势。

### 4.3 这些优势是否可量化

可量化的部分是动作数和换手：

| 维度 | Top50 adaptive 优势 |
| --- | ---: |
| common full range 动作数 | 少 46 次 |
| common full range turnover proxy | 低 14.992497 |
| method summary 平均动作数 | 少 10.62 次 |
| method summary 平均 turnover proxy | 低 3.471042 |

不可完全量化但可审查的部分是：规则解释更简单、产品延续性更强、模型风险说明更少。

### 4.4 LTR simple 的动作数和 turnover proxy 高出多少，是否足以否决默认

LTR simple 在 common full range 多 46 次动作，turnover proxy 高 14.992497；在 method summary 平均多 10.62 次动作，平均 turnover proxy 高 3.471042。

该差距不足以否决默认。原因是 LTR simple 的收益优势明显更大，且回撤并未恶化，反而略好。对于小白用户第一性原则，用户最先关注的是“哪个历史回放效果更好”，换手和动作应作为风险/频率标签提示，而不是在没有明显回撤恶化的情况下直接压过收益证据。

### 4.5 LTR simple 是否存在某些年份、split 或市况明显失效

从 B1 已有结果看，没有发现 LTR simple 相对 Top50 adaptive 的明显失效切片。

逐期相对 Top50 adaptive：

| period | LTR simple 相对收益 | LTR simple 相对回撤 | LTR simple 相对动作 |
| --- | ---: | ---: | ---: |
| 2022 | 0.122930 | -0.015240 | 46 |
| 2023 | 0.593761 | -0.005705 | -8 |
| 2024 | 1.081363 | 0.047835 | -4 |
| 2025 | 1.186208 | 0.049846 | 4 |
| 2026_ytd | 0.077563 | -0.006640 | -2 |
| common_full_range_shared_by_all_compared_methods | 24.054543 | 0.014606 | 46 |
| phase1c_validation_range | 0.162125 | -0.015252 | 5 |
| phase1c_independent_test_range | 1.099753 | 0.007159 | -2 |

LTR simple 在全部 8 个 period 的相对收益均为正。回撤有 4 个 period 略好、4 个 period 略差，但差距整体不大，没有出现收益和回撤同时显著失效的切片。

### 4.6 如果没有明显失效，为什么不能把 LTR simple 作为默认主策略候选

没有充分理由阻止 LTR simple 成为默认主策略候选。

修复后的判断是：`phase1c_ltr_simple_daily` 应作为默认主策略进入 B2 产品化设计；`rank_rotate_top50_adaptive_score` 保留为规则型参考基线。如果后续产品验收认为 LTR 的动作频率、解释成本或用户理解成本不可接受，再把 Top50 adaptive 作为降级默认选项，但这个降级属于产品保守性选择，不应被表述为量化效果更优。

### 4.7 如果出于小白用户第一性继续选择 Top50 adaptive，是否需要用户确认

需要。

如果继续选择 Top50 adaptive，必须明确告知用户：这是为了规则简单、换手略低、解释更容易而做的产品保守性 tradeoff，不是 B1 回放指标最优结论。

但结合用户当前明确反馈“小白关注的还是收益率”，本轮不建议继续把 Top50 adaptive 作为默认主策略。

### 4.8 B2 应如何展示

B2 建议展示方式：

| 策略 | B2 定位 | 标签 | 一句话说明 |
| --- | --- | --- | --- |
| phase1c_ltr_simple_daily | 默认主策略 | 默认；历史回放收益最高；动作较多 | 历史回放收益表现最强，动作和换手略高，适合优先查看。 |
| rank_rotate_top50_adaptive_score | 规则型参考 | 规则简单；换手略低 | 规则更容易理解，历史收益低于默认 LTR，但动作和换手略低。 |
| phase1c_ltr_conservative_top30_2day_confirm_daily | 保守参考 | 保守；低动作；低换手 | 连续确认后才动作，收益低于默认 LTR，但动作明显更少。 |
| phase1c_ltr_conservative_top20_entry_2day_exit_daily | 保守参考 | 更严格入选；低动作 | 入选更严格，动作明显更少，作为低频参考。 |

B2 仍必须保持只读、非交易、非收益承诺。页面文案不得写成真实买卖建议、仓位建议、收益承诺、胜率承诺或上涨概率。

### 4.9 是否需要改默认基线建议

需要改为：

```text
default_ltr_simple_with_top50_adaptive_as_rule_based_reference
```

对应 gate：

```text
phaseb1b_repaired_request_phaseb2_ltr_simple_default_design
```

## 5. 修复后的默认建议

修复后的默认主策略建议：

```text
phase1c_ltr_simple_daily
```

理由：

- 在 B1 已有同口径回放中收益最高；
- common full range 费用后收益显著高于 Top50 adaptive；
- method summary 平均收益显著高于 Top50 adaptive；
- 最差收益优于 Top50 adaptive；
- 平均回撤和最差回撤均略优于 Top50 adaptive；
- independent_test 收益和回撤均优于 Top50 adaptive；
- 动作数和 turnover proxy 虽更高，但幅度不足以抵消收益和回撤证据。

降级参考：

```text
rank_rotate_top50_adaptive_score
```

降级理由只能是产品保守性 tradeoff：规则更简单、换手略低、解释更容易、延续当前默认锚点。不能再表述为 B1 回放效果更好。

## 6. 保守候选处理

B1 已通过的两个保守候选继续保留为 B2 下拉参考候选，不作为默认主策略：

- `phase1c_ltr_conservative_top30_2day_confirm_daily`
- `phase1c_ltr_conservative_top20_entry_2day_exit_daily`

它们的价值是低动作、低换手、解释相对清楚，不是收益最强。

## 7. B2 边界建议

B2 如进入产品化收口，应只做只读展示合同和最小实现：

- 默认选中 `phase1c_ltr_simple_daily`；
- 允许下拉切换 Top50 adaptive 和两个保守候选；
- 用标签提示“收益最高”“动作较多”“规则简单”“保守低频”；
- 不新增交易按钮；
- 不新增写请求；
- 不触发 provider / accepted latest / monitor；
- 不输出仓位、买卖、收益承诺、胜率或上涨概率语义；
- 不把历史回放结果写成未来保证。

## 8. Gate 建议

```text
phaseb1b_repaired_request_phaseb2_ltr_simple_default_design
```

