# Phase C4 决策审查：Clean Stacking

生成时间：`2026-06-15T17:54:41+00:00`

## 1. 结论

- 最终 gate：`clean_stacking_not_supported_vs_fresh_qlib`
- 结论：frozen fresh qlib + orthogonal LTR clean stacking 不优于 frozen fresh qlib baseline，暂不进入只读研究候选。
- frozen fresh qlib 继续作为默认研究基线。

## 2. C0-C3 Gate 汇总

- C0：`phase_c0_clean_stacking_contract_feasible`
- C1：`phase_c1_clean_stacking_sample_passed`
- C2：`phase_c2_clean_stacking_ltr_trained`
- C3：`phase_c3_clean_stacking_2026_replay_completed`

## 3. 合同合规性

- 2025 train / 2026 test 合同保持不变。
- qlib score provenance 安全，2025/2026 都来自同一个 frozen fresh qlib OOS artifact。
- C2 只训练了一个 treatment。
- C3 replay 口径一致，next-day accounting 无违规。

## 4. C3 关键事实

2026 untouched test:

- control net return: `0.217260`
- treatment net return: `0.212462`
- relative return: `-0.004798`

- control max drawdown: `-0.056116`
- treatment max drawdown: `-0.066907`
- relative drawdown: `-0.010791`

- control action_count: `153`
- treatment action_count: `154`

- control turnover_proxy: `15.092610`
- treatment turnover_proxy: `15.296526`

- control fee_and_tax: `48854.89`
- treatment fee_and_tax: `51149.91`

## 5. 取舍判断

- treatment 仅在 qlib top50 内 rerank。
- coverage 公平，每日 50 rows。
- baseline 2026 可复现。
- 未使用 2026 label / future return 做回放决策。
- 正交特征有 feature importance，但没有转化为 2026 回放优势。
- treatment 在收益、回撤、动作数、换手和费用上都没有形成优势。

## 6. Coverage / Accounting / Concentration

- coverage 公平，control/treatment 每日均为 50 行。
- next-day accounting 无违规。
- PnL concentration 未见单一股票主导。
- 最大 symbol turnover share 约 `0.105618`，不构成单点异常，但也不能解释为收益优势来源。

## 7. Feature Importance 解释

- C2 / C3 里正交特征确实被模型使用，`short_balance`、`margin_balance`、`dealer_net_buy_roll10` 等均有可见重要性。
- 但这种使用痕迹没有转化为 2026 untouched test 的净收益提升。

## 8. 是否满足只读候选标准

- 2026 net return 未高于 baseline。
- 最大回撤更差。
- action_count / turnover / fee 也更差。
- 无 PIT / score provenance / accounting 问题。

结论：不满足只读研究候选标准。

## 9. 后续建议

- 保持 frozen fresh qlib 为默认研究基线。
- Clean stacking 结论收口，不继续在当前合同下做补丁式优化。
- 若后续继续探索，需重新定义新合同，而不是在当前结果上包装为候选。

## 10. 参考产物

- [C0 执行报告](PHASEC0_CONTRACT_AND_FEASIBILITY_EXECUTION_REPORT_CN.md)
- [C1 执行报告](PHASEC1_ROW_ALIGNED_SAMPLE_EXECUTION_REPORT_CN.md)
- [C2 执行报告](PHASEC2_ORTHOGONAL_LTR_TRAINING_EXECUTION_REPORT_CN.md)
- [C3 执行报告](PHASEC3_2026_REPLAY_EXECUTION_REPORT_CN.md)

