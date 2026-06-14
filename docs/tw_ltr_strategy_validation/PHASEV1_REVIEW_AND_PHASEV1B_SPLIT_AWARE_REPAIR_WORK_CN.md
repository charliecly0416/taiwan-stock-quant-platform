# Phase V1 审查意见与 Phase V1B Split-aware / Lookahead 修复工作文档

生成时间：2026-06-14

主线依据：`docs/tw_ltr_strategy_validation/LTR_STRATEGY_VALIDATION_MAINLINE_CN.md`

审查入口：`docs/tw_ltr_strategy_validation/PHASEV1_YEARLY_REPLAY_EXECUTION_REPORT_CN.md`

---

## 1. 审查结论

Phase V1 **暂不通过**，不得进入 Phase V2。

执行者完成了 2022 / 2023 / 2024 / 2025 / 2026 YTD 的年度完整日频回放，且表面上满足年度、方法、指标、只读边界要求；但本轮缺少关键的 **split-aware / lookahead 审查维度**：

```text
年度回放没有标注 train / validation / independent_test 覆盖区间；
报告没有区分样本内、验证期、独立测试期；
不能防止把 train/validation 年度收益解释为样本外效果。
```

因此必须先做 Phase V1B 修复，再重新审查。

---

## 2. 新增强制 split 定义

后续所有年度、rolling、市况和产品化判断必须使用以下 split 定义：

| split | 起始日期 | 结束日期 | 语义 |
| --- | --- | --- | --- |
| `train` | 2022-01-10 | 2024-08-09 | 样本内训练覆盖区间，不得解释为样本外效果 |
| `validation` | 2024-08-12 | 2025-06-24 | 验证期，不得解释为独立样本外效果 |
| `independent_test` | 2025-06-25 | 2026-05-07 | 独立测试期，可作为样本外审查核心 |

注意：

- 2022、2023 完全属于 train；
- 2024 同时覆盖 train 与 validation；
- 2025 同时覆盖 validation 与 independent_test；
- 2026 YTD 中 2026-01-01 至 2026-05-07 属于 independent_test，2026-05-08 之后不在上述 split 内，必须标注为 `post_independent_test_or_out_of_split`，不得混入 independent_test 结论。

---

## 3. 主要问题

### P1：年度表缺少 split 覆盖字段

当前产物：

```text
data_tw/experiments/ltr_strategy_validation/phasev1_yearly_replay/phasev1_yearly_comparison.csv
data_tw/experiments/ltr_strategy_validation/phasev1_yearly_replay/phasev1_yearly_data_quality.csv
data_tw/experiments/ltr_strategy_validation/phasev1_yearly_replay/phasev1_gate_summary.json
```

均没有以下字段：

- `split_coverage`
- `train_days`
- `validation_days`
- `independent_test_days`
- `out_of_split_days`
- `sample_status`
- `oos_interpretation_allowed`

这会让 2022/2023/2024 的结果被误读为“策略样本外表现”。

### P1：报告没有拆分年度内混合 split

2024 和 2025 是混合年度：

- 2024 = train + validation
- 2025 = validation + independent_test

当前报告只按自然年度汇总，无法判断：

- 2024 的优势来自 train 还是 validation；
- 2025 的优势来自 validation 还是 independent_test；
- independent_test 是否真的支持 LTR 后续稳定性验证。

### P1：缺少样本外解释限制

当前报告展示了较强年度收益，但没有显式声明：

- train 区间结果只能作为样本内复盘；
- validation 区间结果只能作为模型选择/验证参考；
- independent_test 才能作为后续产品化前的核心样本外证据；
- train/validation 年度收益不得用于产品化背书。

---

## 4. 安全边界审查

只读安全边界本身通过。

未发现：

- rolling 或市况分段已执行；
- 调参；
- 重训 LTR；
- 前端/API 修改；
- 联网或新增数据源；
- provider refresh/publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 买卖、仓位、收益承诺、胜率或上涨概率语义。

本轮不通过的原因不是交易安全越界，而是 split-aware / lookahead 审计不足。

---

## 5. Phase V1B 本轮唯一目标

只做一件事：

```text
在不改变 Phase V1 回放口径、不重跑调参、不改变策略的前提下，
补齐年度结果的 split-aware / lookahead 审计，
并重新提交修复报告。
```

本轮不是 Phase V2，不允许 rolling、市况分段或产品化设计。

---

## 6. Phase V1B 允许改动范围

允许：

- 修改或新增只读审计脚本，例如：
  - `scripts/repair_tw_ltr_strategy_phasev1_split_aware_audit.py`
- 读取既有 Phase V1 产物；
- 必要时按同一冻结口径重算年度结果，但不得改策略、参数或 replay 逻辑；
- 输出 split-aware 修复产物到：
  - `data_tw/experiments/ltr_strategy_validation/phasev1_yearly_replay/`
- 提交修复报告：
  - `docs/tw_ltr_strategy_validation/PHASEV1B_SPLIT_AWARE_REPAIR_EXECUTION_REPORT_CN.md`

允许新增产物建议：

```text
phasev1b_yearly_split_coverage.csv
phasev1b_yearly_split_method_comparison.csv
phasev1b_split_gate_summary.json
```

---

## 7. Phase V1B 禁止事项

禁止：

- rolling 6M / 12M；
- 市况分段；
- walk-forward out-of-sample validation；
- label-shuffle sanity check；
- feature leakage scan；
- 产品化设计；
- 前端/API；
- 重训 LTR；
- 调参；
- 改候选策略；
- 改 Phase1C score；
- 改 replay 口径；
- 新增数据源或联网；
- provider / accepted latest / monitor / trading；
- 把 train / validation 结果解释为样本外效果。

说明：walk-forward、label-shuffle、feature leakage scan 是后续 Phase V2 必须加入的内容，不属于 V1B 修复范围。

---

## 8. Phase V1B 必须输出字段

年度数据质量表必须补充：

- `split_coverage`
- `train_days`
- `validation_days`
- `independent_test_days`
- `out_of_split_days`
- `sample_status`
- `oos_interpretation_allowed`
- `oos_interpretation_note`

年度方法结果表必须补充：

- `split_coverage`
- `sample_status`
- `oos_interpretation_allowed`
- `oos_interpretation_note`

建议 `sample_status` 取值：

- `train_only`
- `train_validation_mixed`
- `validation_independent_test_mixed`
- `independent_test_only`
- `independent_test_out_of_split_mixed`
- `out_of_split_only`

---

## 9. Phase V1B 必须修正的解释

执行报告必须明确：

1. 2022 和 2023 是 train-only，不能作为样本外证据；
2. 2024 是 train/validation mixed，不能作为独立样本外证据；
3. 2025 是 validation/independent_test mixed，必须拆出或至少标注混合属性；
4. 2026 YTD 只有 2026-01-01 至 2026-05-07 属于 independent_test，2026-05-08 之后必须标注为 out-of-split；
5. 任何进入 V2 或产品化设计的判断，必须以 independent_test 与后续 walk-forward 审查为核心，不能只看 train/validation 年度收益；
6. 不得用 2022/2023/2024 的强收益为产品化背书。

---

## 10. Phase V2 路线新增要求

Phase V2 综合稳定性验证在原有 rolling + 市况分段基础上，必须新增：

```text
walk-forward out-of-sample validation
label-shuffle sanity check
feature leakage scan
```

但这些只在 Phase V1B 修复通过后才能执行。

Phase V2 后续工作文档必须把三项纳入必做项：

- walk-forward：验证不同训练/验证/测试滚动切片下的样本外表现；
- label-shuffle：确认 LTR 候选表现不是标签或排序流程偶然泄漏造成；
- feature leakage scan：扫描输入特征、score、label、日期对齐和 available-at 风险。

---

## 11. Phase V1B 验收门槛

Phase V1B 通过最低门槛：

- 年度表和数据质量表都包含 split-aware 字段；
- 2022 / 2023 / 2024 / 2025 / 2026 YTD 均有 split 覆盖说明；
- 报告明确 train / validation / independent_test / out-of-split 语义；
- 报告不把 train/validation 结果解释成样本外；
- gate summary 明确：

```text
split_aware_audit_passed = true
oos_interpretation_guardrail_passed = true
ready_for_phase_v2_comprehensive_stability_validation = true/false
```

- 无重训、调参、前端/API、联网、新数据、provider、accepted latest、monitor、交易链路越权。

---

## 12. Gate

当前 gate：

```text
stop_phasev1_until_split_aware_repair
```

修复完成后，执行者提交：

```text
docs/tw_ltr_strategy_validation/PHASEV1B_SPLIT_AWARE_REPAIR_EXECUTION_REPORT_CN.md
```

审查通过后，才允许进入：

```text
request_phase_v2_comprehensive_stability_validation
```
