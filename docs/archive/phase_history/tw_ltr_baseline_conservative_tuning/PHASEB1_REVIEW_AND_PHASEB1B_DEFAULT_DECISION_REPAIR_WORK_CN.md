# Phase B1 审查意见与 Phase B1B 默认基线决策修复工作文档

生成时间：2026-06-14

主线依据：`docs/TW_STOCK_LTR_BASELINE_AND_CONSERVATIVE_TUNING_MAINLINE_CN.md`

审查入口：`docs/tw_ltr_baseline_conservative_tuning/PHASEB1_CONSERVATIVE_REPLAY_AND_DEFAULT_COMPARISON_EXECUTION_REPORT_CN.md`

---

## 1. 审查结论

Phase B1 **暂不放行进入 B2**。

不是因为 B1 回放失败，也不是因为发现交易或写入越界，而是因为默认基线结论与数值证据之间存在解释缺口。

当前 gate：

```text
request_phaseb1b_default_baseline_decision_repair
```

---

## 2. 先回答用户问题：为什么执行者还选择 Top50 adaptive，LTR 不是更好吗？

按 B1 当前结果，`phase1c_ltr_simple_daily` 的确在多数核心回放指标上更好。

关键证据：

| 指标 | `rank_rotate_top50_adaptive_score` | `phase1c_ltr_simple_daily` | 判断 |
| --- | ---: | ---: | --- |
| common full range 费用后收益 | `15.963677` | `40.018220` | LTR simple 明显更高 |
| common full range 最大回撤 | `-0.402422` | `-0.387816` | LTR simple 略好 |
| common full range 动作数 | `1932` | `1978` | LTR simple 略高，差距约 `46` 次 |
| common full range turnover proxy | `184.497379` | `199.489876` | LTR simple 略高 |
| method summary 平均收益 | `2.813583` | `6.360864` | LTR simple 更高 |
| method summary 最差收益 | `-0.124560` | `-0.001630` | LTR simple 更好 |
| method summary 平均回撤 | `-0.269099` | `-0.259522` | LTR simple 略好 |
| method summary 最差回撤 | `-0.402422` | `-0.387816` | LTR simple 略好 |
| method summary 平均动作数 | `577.88` | `588.50` | LTR simple 略高 |
| independent_test 收益 | `2.450848` | `3.550601` | LTR simple 更高 |
| independent_test 回撤 | `-0.167457` | `-0.160298` | LTR simple 略好 |

因此，单看 B1 回放指标，不能简单说 Top50 adaptive 更优。

执行者选择 Top50 adaptive 的理由是：

```text
当前默认锚点 + 用户可理解性 + 产品延续性 + LTR 模型解释复杂度
```

这个理由可以作为产品 tradeoff，但它不是一个充分的量化结论。尤其 B1 数据显示 LTR simple 的动作数和换手只比 Top50 adaptive 略高，回撤还略好，因此“高动作/高换手/解释复杂”不足以自动否决 LTR simple 默认候选。

审查结论：

```text
B1 的保守候选验证可以接受；
B1 的“默认仍选 Top50 adaptive”结论证据不足，需要修复。
```

---

## 3. 已通过的部分

B1 已完成以下工作：

- 使用 B0 冻结的两个新增保守候选；
- 未追加候选，未做无边界网格搜索；
- 未重训 LTR；
- 未改 Phase1C frozen score；
- 未改回放口径；
- 输出了年度、full range、validation、independent_test 切片；
- 输出了收益、回撤、动作、费用、换手和相对 Top50 adaptive 指标；
- 明确 `phase1c_independent_test_range` 和 `2026_ytd` 没有用于反向改参数；
- 两个新增保守候选相对原保守版有一定改善，可进入 B2 参考列表候选。

---

## 4. 阻塞问题

### Finding 1：默认基线结论与指标证据不匹配

严重级别：Medium

B1 建议：

```text
默认基线仍保持 rank_rotate_top50_adaptive_score
```

但当前量化证据显示：

- `phase1c_ltr_simple_daily` 收益显著更高；
- common full range 最大回撤略好；
- method summary 平均和最差回撤略好；
- independent_test 收益和回撤也更好；
- 动作数和 turnover proxy 虽更高，但幅度并非压倒性；
- B1 未给出可量化阈值说明为什么这些额外动作/换手足以否决 LTR simple。

因此，B1 不能直接进入 B2 产品化收口。

---

## 5. 安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：默认基线决策证据不足，需要修复。
- Low：无实质问题。

### Verdict

未发现：

- 重训 LTR；
- 改 Phase1C score；
- 新数据源；
- 联网；
- provider refresh / publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 前端/API 改动；
- 买卖、持有、仓位、收益承诺、胜率或上涨概率语义。

只读研究边界通过。

---

## 6. Phase B1B 唯一目标

只做一件事：

```text
修复默认基线决策逻辑，明确 Top50 adaptive 与 LTR simple 谁更适合作为默认主策略。
```

Phase B1B 不跑新调参，不新增候选，不改代码，不改前端/API。

---

## 7. Phase B1B 允许事项

允许执行者新增一个窄报告：

```text
docs/tw_ltr_baseline_conservative_tuning/PHASEB1B_DEFAULT_BASELINE_DECISION_REPAIR_EXECUTION_REPORT_CN.md
```

允许内容：

- 基于 B1 已有结果重新分析默认基线；
- 计算或整理 Top50 adaptive vs LTR simple 的差异；
- 明确产品 tradeoff；
- 给出修复后的默认建议；
- 如果仍建议 Top50 adaptive，必须给出可量化或可审查的理由；
- 如果改建议为 LTR simple，必须说明 B2 如何保持只读、可选、非交易、安全边界。

---

## 8. Phase B1B 必须回答的问题

执行者必须逐项回答：

1. 如果默认基线只看 B1 回放指标，是否应承认 `phase1c_ltr_simple_daily` 优于 `rank_rotate_top50_adaptive_score`；
2. Top50 adaptive 相比 LTR simple 的真实优势到底是什么；
3. 这个优势是否可量化，例如更低 turnover、更少动作、更简单解释、更少模型风险；
4. LTR simple 的动作数和 turnover proxy 高出多少，这个差距是否足以否决默认；
5. LTR simple 是否存在某些年份、split 或市况明显失效；
6. 如果没有明显失效，为什么不能把 LTR simple 作为默认主策略候选；
7. 如果出于“小白用户第一性”继续选择 Top50 adaptive，是否需要用户确认这是产品保守性 tradeoff，而不是量化最优结论；
8. B2 应如何展示：
   - 默认主策略；
   - LTR simple；
   - 两个保守候选；
   - 风险/动作/换手标签；
9. 是否需要把默认基线建议改为以下之一：
   - `default_top50_adaptive_for_product_simplicity_ltr_simple_best_replay_candidate`
   - `default_ltr_simple_with_top50_adaptive_as_rule_based_reference`
   - `requires_user_tradeoff_confirmation_before_b2`

---

## 9. Phase B1B 禁止事项

本轮禁止：

- 新回放；
- 新候选；
- 新调参；
- 重训 LTR；
- 改 Phase1C score；
- 改 replay 口径；
- 新数据源；
- 联网；
- provider refresh / publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 前端/API 改动；
- 输出买卖、持有、仓位建议；
- 输出收益承诺、胜率或上涨概率；
- 用“解释复杂”一句话直接盖过量化证据。

---

## 10. Phase B1B Gate

如果执行者承认 LTR simple 是回放最强，但建议 Top50 adaptive 作为产品默认，并明确这是产品保守性 tradeoff：

```text
requires_user_tradeoff_confirmation_before_b2
```

如果执行者修正默认建议为 LTR simple，并给出只读、非交易、非收益承诺的 B2 展示边界：

```text
phaseb1b_repaired_request_phaseb2_ltr_simple_default_design
```

如果执行者仍坚持 Top50 adaptive 量化更优但没有证据：

```text
stop_and_discuss_with_user
```
