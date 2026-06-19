# Phase E7 工作文档：默认候选决策收口

生成日期：2026-06-16

## 1. 本阶段目标

本阶段只做决策审查，不训练、不回放、不改默认策略：

```text
综合 E4、E5B、E6 证据，
判断 frozen qlib + orthogonal LTR 是否可以进入新的默认候选讨论，
以及是否需要继续验证或产品化支线。
```

本阶段不得直接切换默认策略，不得触发前端/API/provider/accepted latest/monitor/交易链路。

## 2. 必须引用的证据

必须引用：

- `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE4_2026_REPLAY_EXECUTION_REPORT_CN.md`
- `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE5_E4_FAIRNESS_AUDIT_EXECUTION_REPORT_CN.md`
- `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE5B_E4_VS_FRESH_EXACT_2026_BRIDGE_REPORT_CN.md`
- `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE6_BRIDGE_LTR_2025_TWO_QLIB_BASES_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_bridge_manifest.json`

## 3. 必须回答的问题

E7 必须回答：

1. E4 是否合规且公平；
2. E4 是否在 2026 exact bridge 中高于 repaired fresh qlib；
3. E6 是否证明 2025-only orthogonal LTR 在 fresh qlib 和 frozen qlib 两个底座上都有增益；
4. E6 是否支持更长 LTR 训练窗口带来额外提升；
5. E4 的高收益是否仍有未解释风险；
6. 回撤、换手、费用、PnL 集中是否可接受；
7. 是否建议把 E4 作为默认候选，而不是直接默认；
8. 是否需要开启日更/产品化支线；
9. 是否需要更长 OOS 或 rolling robustness 进一步验证。

## 4. 决策边界

允许的结论：

```text
recommend_default_candidate_discussion
recommend_readonly_productization_design
recommend_daily_readonly_candidate_refresh
recommend_additional_robustness_validation
```

禁止的结论：

```text
直接切换默认策略
直接替换前端展示
直接触发 provider / accepted latest
直接触发 monitor / broker / orders
承诺未来收益、胜率或上涨概率
```

## 5. 输出报告

必须输出：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE7_DEFAULT_CANDIDATE_DECISION_CN.md
```

报告必须包含：

- E4/E5B/E6 核心指标表；
- 正交 LTR 增益判断；
- 训练长度影响判断；
- 与 fresh qlib 的公平比较结论；
- 风险与 caveat；
- 是否建议进入默认候选讨论；
- 下一步工作建议。

## 6. Gate

若完成且未触发禁止事项，gate 为：

```text
phase_e7_default_candidate_decision_recorded
```

