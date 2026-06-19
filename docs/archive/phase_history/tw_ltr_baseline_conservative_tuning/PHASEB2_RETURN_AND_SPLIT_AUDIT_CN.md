# Phase B2 策略收益与 Split 使用审查说明

生成时间：2026-06-14

数据来源：`data_tw/experiments/ltr_baseline_conservative_tuning/phaseb1_conservative_replay/phaseb1_period_comparison.csv`

字段说明：以下“收益”均为 `fee_tax_adjusted_net_return`，是费用税费后历史回放净收益字段，不是年化收益，也不是未来收益承诺。若按百分比表达，可乘以 100%。

---

## 1. B2 当前展示的四个策略

| 策略 | 定位 |
| --- | --- |
| `phase1c_ltr_simple_daily` | 默认主策略 |
| `rank_rotate_top50_adaptive_score` | 规则型参考 |
| `phase1c_ltr_conservative_top30_2day_confirm_daily` | 保守参考 |
| `phase1c_ltr_conservative_top20_entry_2day_exit_daily` | 保守参考 |

---

## 2. Common Full Range 收益

区间：`2022-01-01` 至 `2026-05-07`

| 策略 | fee_tax_adjusted_net_return | 约等于百分比 | max_drawdown | action_count |
| --- | ---: | ---: | ---: | ---: |
| `phase1c_ltr_simple_daily` | `40.018220` | `4001.822%` | `-0.387816` | `1978` |
| `rank_rotate_top50_adaptive_score` | `15.963677` | `1596.368%` | `-0.402422` | `1932` |
| `phase1c_ltr_conservative_top30_2day_confirm_daily` | `7.420780` | `742.078%` | `-0.225025` | `312` |
| `phase1c_ltr_conservative_top20_entry_2day_exit_daily` | `8.060574` | `806.057%` | `-0.207133` | `314` |

注意：common full range 不能解释为纯样本外，因为它包含 train、validation 和 independent_test。

---

## 3. Validation Range 收益

区间：`2024-08-12` 至 `2025-06-24`

| 策略 | fee_tax_adjusted_net_return | 约等于百分比 | max_drawdown | action_count |
| --- | ---: | ---: | ---: | ---: |
| `phase1c_ltr_simple_daily` | `0.485349` | `48.535%` | `-0.385550` | `404` |
| `rank_rotate_top50_adaptive_score` | `0.323224` | `32.322%` | `-0.370298` | `399` |
| `phase1c_ltr_conservative_top30_2day_confirm_daily` | `0.176050` | `17.605%` | `-0.128686` | `63` |
| `phase1c_ltr_conservative_top20_entry_2day_exit_daily` | `0.028840` | `2.884%` | `-0.206277` | `63` |

Validation 结果可用于诊断，但不能当作独立样本外效果。

---

## 4. Independent Test Range 收益

区间：`2025-06-25` 至 `2026-05-07`

| 策略 | fee_tax_adjusted_net_return | 约等于百分比 | max_drawdown | action_count |
| --- | ---: | ---: | ---: | ---: |
| `phase1c_ltr_simple_daily` | `3.550601` | `355.060%` | `-0.160298` | `384` |
| `rank_rotate_top50_adaptive_score` | `2.450848` | `245.085%` | `-0.167457` | `386` |
| `phase1c_ltr_conservative_top30_2day_confirm_daily` | `1.257516` | `125.752%` | `-0.098271` | `63` |
| `phase1c_ltr_conservative_top20_entry_2day_exit_daily` | `0.650070` | `65.007%` | `-0.143129` | `63` |

Independent test 单独看，`phase1c_ltr_simple_daily` 在四个固定候选中费用后历史模拟收益字段最高，且最大回撤略好于 Top50 adaptive；这只说明该独立测试切片支持默认展示，不代表未来收益。

---

## 5. 年度收益摘要

| period | LTR simple | Top50 adaptive | LTR Top30 连续确认 | LTR Top20 严格入选 |
| --- | ---: | ---: | ---: | ---: |
| `2022` | `-0.001630` | `-0.124560` | `0.033920` | `0.021816` |
| `2023` | `1.965554` | `1.371793` | `0.931025` | `0.998570` |
| `2024` | `1.875720` | `0.794357` | `0.702011` | `0.976266` |
| `2025` | `2.019370` | `0.833162` | `0.626518` | `0.513323` |
| `2026_ytd` | `0.973726` | `0.896163` | `0.683008` | `0.221910` |

解释：

- `2022`、`2023` 属于 train 复盘，不可解释为样本外。
- `2024` 混有 train / validation。
- `2025` 混有 validation / independent_test。
- `2026_ytd` 当前产物区间为 `2026-01-01` 至 `2026-06-13`，不等同于此前冻结的 independent_test range，因为 independent_test 截止到 `2026-05-07`。

---

## 6. 是否用到了训练集或验证集

结论：有，但用途必须区分。

### 6.1 用到了哪些非独立测试区间

- common full range 包含 train、validation、independent_test；
- 年度 `2022`、`2023` 是 train；
- 年度 `2024` 是 train / validation mixed；
- 年度 `2025` 是 validation / independent_test mixed；
- `phase1c_validation_range` 是 validation。

### 6.2 是否用于调参

从 B0/B1/B1B/B2 文档看，两个保守候选在 B0 已冻结，B1 只跑一次固定候选回放，B1B/B2 没有新增候选、没有改阈值、没有重训。因此当前证据没有显示使用 validation 或 independent_test 反向调参。

### 6.3 是否用于默认选择与产品展示

是。B1/B1B/B2 的默认选择参考了 full range、年度、validation、independent_test 等整体结果。因此不能把最终默认结论表述为“纯样本外最优”。

更准确的表述应为：

```text
在 B1 固定候选、同口径历史回放中，LTR simple 的默认展示主要由 independent_test 切片支持；full range 只能作为包含 train / validation / independent_test 的混合历史复盘明细。
```

不得写成：

```text
LTR simple 未来收益最高
LTR simple 样本外必然更好
LTR simple 胜率更高
```

---

## 7. 审查结论

- 如果看 common full range：LTR simple 的费用后历史模拟收益字段最高，但该区间是混合历史复盘，不作为样本外证据。
- 如果只看 independent_test：LTR simple 的费用后历史模拟收益字段在固定候选中较强，且回撤略好于 Top50 adaptive。
- 当前确实使用了 train / validation 作为历史复盘和综合展示的一部分。
- 当前没有证据显示用 validation 或 independent_test 做了反向调参。
- 后续文案必须明确“历史回放 / 固定候选 / 非未来承诺”，不能把 common full range 说成纯样本外效果。
