# Phase C2 审查报告：Fresh Top50 覆盖修复后的前端影响判断

生成时间：2026-06-15T07:38:41+00:00

## 1. 审查输入

- C1 修订版 gate：`phase_c1_repair_and_common_revision_review_passed_proceed_to_c2`。
- 使用 `phasec1_full_universe_metrics.csv`、`phasec1_frozen_s2f_common_universe_metrics.csv`、`phasec1_repaired_pairwise_common_universe_metrics.csv`。
- 本轮只做审查判断，不改前端/API，不切换默认策略。

## 2. 必答问题

### 2.1 fresh top50 原 full universe 对比是否被 coverage 缺陷低估

是。original fresh top50 replay-ready 覆盖只有 `88 / 109.0 / 150`；repaired 后为 `150 / 150.0 / 150`。full universe return 从 original fresh top50 的 `0.662457` 提升到 repaired fresh top50 的 `0.801662`，说明原 full universe 对比显著受 coverage 缺陷低估。

### 2.2 full/common 分歧如何解释

full universe 下 repaired fresh top50 利用了新增覆盖后的 method-specific 可交易集合，return `0.801662` 高于 Phase1C anchor `0.721631`，但 max drawdown `-0.085205` 差于 Phase1C 的 `-0.050830`。

frozen S2F common universe 下 key count 为 `22474`，repaired fresh top50 return `0.625943`，低于 Phase1C common `0.641235`。pairwise common 下 key count 为 `22523`，repaired fresh top50 return `0.663150`，也低于 Phase1C `0.697914`。

解释：full universe 改善主要来自 coverage 扩展后的可用股票池收益贡献；在共同 key 集合内，fresh top50 的排序/回放结果仍未超过 Phase1C anchor。

### 2.3 前端默认展示是否应调整

本阶段不调整。理由是 full universe 结果支持 repaired fresh top50 有明显改善，但两套 common universe 仍低于 Phase1C，且 repaired fresh top50 不是当前前端已冻结展示合同的一部分。默认策略和前端展示应继续冻结，避免把研究修复结果直接推成产品默认。

### 2.4 若要改前端，是否需要另开合同

需要。若后续要展示 repaired fresh top50，应另开前端只读展示合同，明确展示口径、标签、风险解释、默认策略是否变更、以及不得触发 monitor / broker / orders / quick-trade。C2 不执行任何前端变更。

### 2.5 是否可以进入正交数据主线

可以进入审查或准备阶段。前提是继续保持研究只读边界，不把 repaired fresh top50 直接写入默认策略，不改 accepted latest/provider/monitor/交易链路。

## 3. C2 判定

| item | decision | reason |
| --- | --- | --- |
| full universe 结论 | repaired fresh top50 超过 Phase1C | return `0.801662` vs `0.721631` |
| frozen S2F common 结论 | repaired fresh top50 未超过 Phase1C | return `0.625943` vs `0.641235` |
| pairwise common 结论 | repaired fresh top50 未超过 Phase1C | return `0.663150` vs `0.697914` |
| 前端默认策略 | 不切换 | common 仍未超过，且需单独前端合同 |
| 正交数据主线 | 可进入后续审查 | coverage repair 证据已闭环 |

## 4. 推荐 Gate

```text
phase_c2_review_completed_frontend_default_frozen_allow_orthogonal_data_review
```

## 5. 安全边界

- 未训练 qlib/LTR。
- 未改 Phase1C anchor。
- 未改前端/API。
- 未触发 provider / accepted latest / monitor / broker / orders / quick-trade。
- 未输出真实买卖、持有、仓位、收益承诺、胜率或上涨概率语义。

## 6. 输出产物

- `docs/tw_fresh_top50_coverage_repair/PHASEC2_FRONTEND_IMPACT_REVIEW_CN.md`
- `data_tw/experiments/fresh_top50_coverage_repair/phasec2_frontend_impact_summary.json`
