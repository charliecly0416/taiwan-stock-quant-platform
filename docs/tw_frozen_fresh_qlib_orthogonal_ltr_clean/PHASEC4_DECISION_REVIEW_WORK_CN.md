# Phase C4 工作文档：Clean Stacking 决策审查

生成日期：2026-06-15

## 1. 本阶段目标

本阶段只做一件事：

```text
基于 C0-C3 的冻结合同、样本、训练和 2026 untouched replay 结果，
判断 frozen fresh qlib + orthogonal LTR clean stacking
是否值得进入只读研究候选，或应收尾为不支持。
```

本阶段不训练、不调参、不回放、不改默认策略。

## 2. 上游 Gate

必须满足：

```text
phase_c0_clean_stacking_contract_feasible
phase_c1_clean_stacking_sample_passed
phase_c2_clean_stacking_ltr_trained
phase_c3_clean_stacking_2026_replay_completed
```

必须引用：

- `docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC0_CONTRACT_AND_FEASIBILITY_EXECUTION_REPORT_CN.md`
- `docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC1_ROW_ALIGNED_SAMPLE_EXECUTION_REPORT_CN.md`
- `docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC2_ORTHOGONAL_LTR_TRAINING_EXECUTION_REPORT_CN.md`
- `docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC3_2026_REPLAY_EXECUTION_REPORT_CN.md`

## 3. 必须使用的 C3 事实

C4 必须明确列出：

```text
2026 untouched test:
control net return:   0.217260
treatment net return: 0.212462
relative return:     -0.004798

control max drawdown:   -0.056116
treatment max drawdown: -0.066907
relative drawdown:      -0.010791

control action_count:   153
treatment action_count: 154

control turnover_proxy:   15.092610
treatment turnover_proxy: 15.296526

control fee_and_tax:   48854.89
treatment fee_and_tax: 51149.91
```

同时说明：

- treatment 仅在 qlib top50 内 rerank；
- coverage 公平，每日 50 rows；
- baseline 2026 可复现；
- next-day accounting 无违规；
- 未使用 2026 label / future return 做回放决策；
- 正交特征有 feature importance，但没有转化为 2026 回放优势。

## 4. 决策标准

支持进入只读研究候选至少应满足：

- 2026 net return 高于 fresh qlib，或收益基本持平但回撤、动作、换手明显改善；
- 最大回撤不明显恶化；
- action_count / turnover 不明显恶化；
- PnL 不集中在单一股票或日期；
- 正交特征有可解释贡献；
- 没有 PIT / score provenance / accounting 问题。

若 treatment 收益略低，同时回撤、动作、换手和费用也略差，不得包装为优于 baseline。

## 5. C4 执行范围

执行者应完成：

1. 汇总 C0-C3 gate。
2. 汇总合同合规性。
3. 汇总 2026 untouched replay 指标。
4. 判断收益、回撤、动作、换手、费用的取舍。
5. 判断 PnL concentration 是否有单点主导。
6. 判断 feature importance 是否有解释价值。
7. 判断是否满足只读候选标准。
8. 给出最终 gate：
   - `clean_stacking_supported_for_readonly_candidate`
   - `clean_stacking_not_supported_vs_fresh_qlib`
   - `clean_stacking_blocked_by_sample_or_contract`
9. 给出后续建议。

## 6. 建议判定

基于 C3 当前结果，除非执行者发现 C3 计算错误，否则推荐最终 gate：

```text
clean_stacking_not_supported_vs_fresh_qlib
```

建议结论：

```text
Clean stacking 合同、样本、训练和回放均合规，
但 2026 untouched test 中 treatment 未跑赢 frozen fresh qlib baseline。
收益略低，最大回撤略差，action_count、turnover_proxy 和 fee/tax 也略高。
因此不建议进入只读研究候选，不切换默认策略。
```

## 7. 禁止事项

C4 禁止：

- 新训练；
- 新调参；
- 新回放；
- 改 split / label / model；
- 改 replay 规则；
- 新增 filter / market gate / turnover rule；
- 用 2026 label / future return 做选择；
- 改默认前端策略；
- 接 provider refresh / publish / accepted latest；
- 接 monitor / broker / orders / quick-trade；
- 把略差结果包装成优于 baseline；
- 输出真实买卖建议、目标仓位、目标权重、收益承诺、胜率或上涨概率。

## 8. 输出报告

必须输出：

```text
docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC4_DECISION_REVIEW_CN.md
```

报告必须包含：

- C0-C3 gate 汇总；
- 2025 train / 2026 test 合同是否保持；
- qlib score provenance 是否安全；
- C2 是否只训练一个 treatment；
- C3 replay 口径是否一致；
- 2026 return / drawdown / action / turnover / fee tax 对比；
- coverage / next-day accounting / PnL concentration；
- feature importance 解释；
- 是否满足只读候选标准；
- 最终 gate；
- 是否保持 fresh qlib 为默认研究基线；
- 后续建议。

## 9. 给执行者的一句话

```text
请按 docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC4_DECISION_REVIEW_WORK_CN.md 执行 Phase C4：只基于 C0-C3 既有产物做决策审查，不训练、不调参、不回放、不改默认策略；重点判断 2026 untouched test 中 frozen_fresh_qlib_orthogonal_ltr 是否相对 fresh_qlib_top50_adaptive_baseline 形成真实增益。若无 C3 计算错误，按当前结果应判为 clean_stacking_not_supported_vs_fresh_qlib。
```

## 10. 给审查者的一句话

```text
请按 docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC4_DECISION_REVIEW_WORK_CN.md 审查 C4 决策报告，重点确认没有新增训练/回放/调参/规则，是否正确使用 C3 结果，是否没有把未跑赢 baseline 的 treatment 包装成只读候选，并确认最终 gate 是否合理。
```
