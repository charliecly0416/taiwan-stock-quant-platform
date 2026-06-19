# Fresh Top50 覆盖修复总结

生成日期：2026-06-15

## 1. 原来是什么问题

Fresh qlib/top50 adaptive 在 `2025-07-01..2026-05-07` 同窗口回放里表现被低估。

表面现象：

```text
old Phase1C LTR daily rows:      147 / 149 / 150
fresh top50 adaptive daily rows:  88 / 109 / 150
```

也就是说，Phase1C 每天接近 150 支候选股票，而 fresh top50 adaptive 中位数只有 109 支。两边 full universe 对比并不公平。

根因不是缺 qlib score，也不是缺本地价格：

```text
fresh raw qlib score:      150 / 150 / 150
missing raw qlib score:    0
missing local price:       0
```

真正原因是 fresh retrain 链路中 S2B 引入了 post-score universe filter：

```text
raw fresh qlib score -> S2B post-filter -> S2D replay-ready
150 / 150 / 150       -> 88 / 109 / 150 -> 88 / 109 / 150
```

这层 filter 原本是为了规避 provider instrument 解析、股票别名、历史有效期、as-of active universe 等风险；设计动机合理，但实际过滤过窄，把一些本来有 score、有价格、可回放的股票排除掉了。

## 2. 怎么修复

修复方式是离线修复，不触发线上链路：

- 不重新训练 qlib；
- 不重新训练 LTR；
- 不改 Phase1C anchor；
- 不改前端/API；
- 不触发 provider refresh / publish；
- 不切换 accepted latest；
- 不触发 monitor / broker / orders / quick-trade。

具体做法：

```text
使用 phase_s2b_raw_score_rank.csv 的 raw fresh qlib score
+ 本地 normalized price
+ 原 fresh top50 adaptive 公式
=> 重建 repaired replay-ready scores
```

adaptive 公式保持：

```text
0.70 * qlib_score_zscore_by_date
+ 0.15 * ret20
- 0.10 * volatility20
+ 0.05 * TWII_ret20
```

修复后覆盖：

```text
repaired fresh top50 daily rows: 150 / 150 / 150
```

并通过了 next-day replay 审计：

```text
missing_price_days: 0
skipped_trade_count: 0
last_day_new_trade_without_next_price_count: 0
```

## 3. 效果如何

Full universe 下，修复后的 fresh top50 adaptive 明显改善：

| method | return | max_drawdown | action_count |
| --- | ---: | ---: | ---: |
| original fresh top50 adaptive | 0.662457 | -0.088396 | 410 |
| repaired fresh top50 adaptive | 0.801662 | -0.085205 | 410 |
| Phase1C anchor | 0.721631 | -0.050830 | 405 |
| original fresh LTR simple | 0.544381 | -0.132896 | 408 |

结论：

```text
full universe 下，repaired fresh top50 adaptive > Phase1C anchor > original fresh top50 > fresh LTR。
```

但 common universe 下，fresh top50 仍低于 Phase1C anchor：

| common universe | repaired fresh top50 | Phase1C anchor |
| --- | ---: | ---: |
| frozen S2F common | 0.625943 | 0.641235 |
| repaired pairwise common | 0.663150 | 0.697914 |

解释：

```text
fresh top50 的 full universe 提升主要来自覆盖修复后新增股票池的收益贡献；
在共同股票池内，Phase1C anchor 仍略强。
```

## 4. 现在能得出的结论

可以确定：

- 原 fresh top50 full universe 结果被 coverage 缺陷低估；
- S2B post-score filter 过滤过窄；
- 修复后 fresh top50 adaptive 在 full universe 下收益最好；
- fresh LTR 在这组同窗口结果中明显不如 repaired fresh top50；
- Phase1C anchor 仍是有效研究基准，但不能再说它在 full universe 下明显优于 fresh top50。

不能直接做的事：

- 不能直接改前端默认；
- 不能直接切换默认策略；
- 不能把 repaired fresh top50 包装成产品默认策略；
- 不能忽略 as-of universe / tradability 合同风险。

## 5. 剩余风险

本轮已确认这些股票有 score、有本地价格，并可完成 next-day replay。但还需要更严格确认：

1. `raw top150` 是否完全符合 as-of active universe；
2. 是否严格排除了未来上市/无效期股票；
3. 流动性 top150 口径是否与产品默认口径一致；
4. repaired fresh top50 是否能在更多 OOS 窗口保持优势；
5. 若进入前端，如何解释 full universe 强、common universe 仍弱于 Phase1C 的差异。

## 6. 后续应该做什么

建议下一步：

```text
1. 收尾 fresh top50 coverage repair 主线；
2. 保持当前前端默认和策略展示不变；
3. 把 repaired fresh top50 作为研究候选，不直接产品化；
4. 若要产品化，先做 tradability / as-of universe 合同审计；
5. 然后再进入正交数据主线。
```

如果后续要展示 repaired fresh top50，应另开前端只读展示合同，明确：

- 展示标签；
- full/common universe 差异解释；
- 是否默认展示；
- 不输出真实交易建议；
- 不触发 monitor / broker / orders / quick-trade。

一句话总结：

```text
这次不是模型训练问题，而是 fresh replay-ready 覆盖被 post-score filter 意外压低；离线修复后 fresh top50 full universe 表现超过 Phase1C，但 common universe 仍不占优，因此可以收尾研究主线，但不应直接改前端默认。
```
