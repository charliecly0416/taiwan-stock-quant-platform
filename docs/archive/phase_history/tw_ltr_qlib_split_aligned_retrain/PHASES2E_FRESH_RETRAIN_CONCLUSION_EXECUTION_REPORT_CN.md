# Phase S2E 执行报告：Fresh Retrain Conclusion

生成日期：2026-06-14T19:37:28+00:00

## 1. 本轮目标

只基于 S1 与 S2D 既有证据，给出 fresh retrain 研究结论 gate，并明确 LTR 与 qlib/top50 家族的当前定位。

## 2. S1 与 S2 的关系

- S1 的作用：验证旧窗口下 LTR 方法是否值得继续进入 fresh retrain。
- S2 的作用：验证当前 fresh retrain 场景下谁更适合作为默认研究候选。
- 结论边界：不能把 S1 的方法有效性包装成 S2 的 fresh 默认资格。

## 3. Full Validation / Full Test 结论

- fresh top50 adaptive validation net_return: `0.038270`
- fresh LTR simple validation relative_return_vs_top50: `-0.095723`
- fresh LTR turnover-controlled validation relative_return_vs_top50: `-0.061636`
- fresh top50 adaptive test net_return: `0.662457`
- fresh confirmed_exit test relative_return_vs_top50: `0.006066`
- fresh LTR simple test relative_return_vs_top50: `-0.118076`
- fresh LTR turnover-controlled test relative_return_vs_top50: `-0.047398`

解释：validation 与 full test 都不支持把 LTR 设为 fresh 默认；`fresh_confirmed_exit` 在 full test 略高于 top50 adaptive，但仍属于 qlib/top50 同家族证据，不构成 LTR default 支持。

## 4. LTR 定位

- `fresh_ltr_simple`：不支持默认。
- `fresh_ltr_turnover_controlled`：可保留为低动作研究候选，但不能自动当作默认；它是收益/回撤换低动作的 tradeoff，不应由执行者自动替用户选择。

## 5. Rolling / Regime Caveat

- rolling 6m window count: `4`
- regime `sample_too_small` rows: `10`
- 部分 rolling/regime 窗口可为 LTR turnover-controlled 提供局部正信号，但不能覆盖 full validation/full test 的默认候选结论。

## 6. 研究结论

当前主线研究结论应为：

```text
fresh_retrain_qlib_or_top50_default_supported
```

这表示：当前更合理的 fresh 默认研究方向仍是 qlib/top50 家族；LTR 保留为研究候选，而不是默认候选。

## 7. 主要产物

- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2e_fresh_retrain_conclusion/phase_s2e_s1_s2_evidence_summary.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2e_fresh_retrain_conclusion/phase_s2e_default_candidate_decision_matrix.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2e_fresh_retrain_conclusion/phase_s2e_ltr_positioning_note.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2e_fresh_retrain_conclusion/phase_s2e_forbidden_action_audit.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2e_fresh_retrain_conclusion/phase_s2e_gate_summary.json`
