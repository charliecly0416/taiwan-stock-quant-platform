# Phase V1B 审查意见与 Phase V2 综合稳定性验证工作文档

生成时间：2026-06-14

主线依据：`docs/tw_ltr_strategy_validation/LTR_STRATEGY_VALIDATION_MAINLINE_CN.md`

审查入口：`docs/tw_ltr_strategy_validation/PHASEV1B_SPLIT_AWARE_REPAIR_EXECUTION_REPORT_CN.md`

---

## 1. 审查结论

Phase V1B **通过**，允许进入 Phase V2 综合稳定性验证。

本轮修复已补齐 Phase V1 缺失的 split-aware / lookahead 审查维度：

- 已明确 split 定义：
  - `train`: 2022-01-10 至 2024-08-09
  - `validation`: 2024-08-12 至 2025-06-24
  - `independent_test`: 2025-06-25 至 2026-05-07
- 已补充年度 split 覆盖字段；
- 已补充样本状态；
- 已补充样本外解释限制；
- 已明确 2022/2023 不能作为样本外证据；
- 已明确 2024 是 train/validation mixed；
- 已明确 2025 是 validation/independent_test mixed；
- 已明确 2026 YTD 含 out-of-split 日期，不得整体解释为 independent_test；
- 已明确后续产品化前必须依赖 independent_test、walk-forward、label-shuffle 与 leakage scan。

---

## 2. 产物核对

已核对以下产物存在并包含必要字段：

```text
data_tw/experiments/ltr_strategy_validation/phasev1_yearly_replay/phasev1b_yearly_split_coverage.csv
data_tw/experiments/ltr_strategy_validation/phasev1_yearly_replay/phasev1b_yearly_split_method_comparison.csv
data_tw/experiments/ltr_strategy_validation/phasev1_yearly_replay/phasev1b_split_gate_summary.json
```

关键字段已存在：

- `split_coverage`
- `train_days`
- `validation_days`
- `independent_test_days`
- `out_of_split_days`
- `sample_status`
- `oos_interpretation_allowed`
- `oos_interpretation_note`

`phasev1b_split_gate_summary.json` 已包含：

```text
split_aware_audit_passed = true
oos_interpretation_guardrail_passed = true
ready_for_phase_v2_comprehensive_stability_validation = true
```

---

## 3. 重要解释约束

Phase V2 以及后续产品化判断必须继续遵守：

1. 2022 / 2023 是 `train_only`，只能作为样本内复盘；
2. 2024 是 `train_validation_mixed`，不能作为独立样本外证据；
3. 2025 是 `validation_independent_test_mixed`，年度聚合值不能直接当作独立样本外效果；
4. 2026 YTD 是 `independent_test_out_of_split_mixed`，不能整体当作 independent_test；
5. 任何进入产品化设计的判断，必须以 independent_test 和 walk-forward out-of-sample 审查为核心；
6. 不得用 train / validation 年度收益为产品化背书。

---

## 4. 安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：无实质问题。

### 判断

本轮未发现：

- rolling 已执行；
- 市况分段已执行；
- walk-forward 已执行；
- label-shuffle 已执行；
- feature leakage scan 已执行；
- 产品化设计已启动；
- 前端/API 修改；
- 重训 LTR；
- 调参；
- 改候选策略；
- 改 Phase1C score；
- 改 replay 口径；
- 新增数据源或联网；
- provider refresh/publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 买卖、仓位、收益承诺、胜率或上涨概率语义。

只读研究边界通过。

---

## 5. Phase V2 本轮唯一目标

只做一件事：

```text
在 Phase V1/V1B 年度与 split-aware 审计基础上，
完成 LTR 候选策略的综合稳定性验证。
```

Phase V2 必须同时覆盖：

1. rolling 6M / 12M 稳定性验证；
2. 市况分段验证；
3. walk-forward out-of-sample validation；
4. label-shuffle sanity check；
5. feature leakage scan。

本轮仍然不是产品化，不允许前端/API 或策略入口实现。

---

## 6. Phase V2 允许改动范围

允许：

- 新增只读验证脚本，例如：
  - `scripts/validate_tw_ltr_strategy_phasev2_comprehensive_stability.py`
- 读取 Phase V1 / V1B 产物；
- 读取 Phase3A2C 冻结产物；
- 读取本地既有信号、价格、冻结分数；
- 使用冻结候选策略和冻结 replay 口径做只读验证；
- 输出只读验证产物到：
  - `data_tw/experiments/ltr_strategy_validation/phasev2_comprehensive_stability/`
- 提交执行报告：
  - `docs/tw_ltr_strategy_validation/PHASEV2_COMPREHENSIVE_STABILITY_EXECUTION_REPORT_CN.md`

---

## 7. Phase V2 禁止事项

禁止：

- 重训 LTR；
- 调参；
- 改候选策略；
- 改 Phase1C score；
- 改 replay 口径；
- 新增数据源；
- 联网；
- provider refresh/publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 前端/API 改动；
- 产品化设计或实现；
- 把结果写成买卖、仓位、收益承诺、胜率或上涨概率语义；
- 用 train / validation 结果冒充样本外效果。

---

## 8. Phase V2 必做验证 A：Rolling 6M / 12M

必须输出 rolling 6M 和 rolling 12M。

每个窗口必须包含：

- `window_type`
- `window_start`
- `window_end`
- `split_coverage`
- `sample_status`
- `method`
- `fee_tax_adjusted_net_return`
- `final_equity`
- `max_drawdown`
- `action_count`
- `buy_count`
- `sell_count`
- `fee_and_tax`
- `turnover_proxy_by_notional_over_avg_equity`
- `missing_price_count`
- `trading_days_used`
- `relative_return_vs_top50_adaptive`
- `relative_drawdown_vs_top50_adaptive`
- `relative_actions_vs_top50_adaptive`
- `oos_interpretation_allowed`

必须回答：

- LTR simple 是否只靠少数强势窗口；
- turnover-controlled LTR 是否稳定降低回撤和动作；
- Top50 自适应是否在多数 rolling 窗口更稳；
- independent_test 覆盖窗口中的表现是否支持继续产品化设计。

---

## 9. Phase V2 必做验证 B：市况分段

必须输出 bull / normal / bear，或 normal / caution / risk_off。

如果使用 normal / caution / risk_off，必须给出映射关系。

每个市况分段必须包含：

- `regime`
- `regime_definition`
- `split_coverage`
- `sample_status`
- `trading_days_used`
- `method`
- `fee_tax_adjusted_net_return`
- `final_equity`
- `max_drawdown`
- `action_count`
- `turnover_proxy_by_notional_over_avg_equity`
- `relative_return_vs_top50_adaptive`
- `relative_drawdown_vs_top50_adaptive`
- `relative_actions_vs_top50_adaptive`
- `oos_interpretation_allowed`

必须回答：

- LTR simple 是否只在 bull/normal 强；
- turnover-controlled LTR 是否在 bear/risk_off 更抗跌；
- Top50 自适应是否仍是更稳定主基线；
- confirmed_exit 是否只是低动作低收益参考。

---

## 10. Phase V2 必做验证 C：Walk-forward Out-of-sample

必须新增 walk-forward out-of-sample validation。

要求：

- 不重训当前 LTR；
- 不调参；
- 不更改 Phase1C frozen score；
- 使用固定候选策略和固定 replay 口径；
- 只验证不同时间切片下的样本外稳定性；
- 每个 walk-forward fold 必须明确：
  - `fold_id`
  - `train_like_period`
  - `validation_like_period`
  - `test_period`
  - `method`
  - 核心指标
  - 相对 Top50 自适应差值
  - 是否允许样本外解释

如果现有冻结 score 不支持真正重新训练式 walk-forward，必须明确写：

```text
walk_forward_mode = frozen_score_oos_replay_only
```

不得伪装成重新训练后的 walk-forward。

---

## 11. Phase V2 必做验证 D：Label-shuffle Sanity Check

必须新增 label-shuffle sanity check。

目标：

```text
确认 LTR 候选表现不是标签/排序流程偶然泄漏或日期对齐错误导致。
```

要求：

- 不训练新正式模型；
- 可做只读 sanity 诊断；
- 必须说明 shuffle 对象、shuffle 粒度和日期约束；
- 必须输出 sanity 结论：
  - `pass`
  - `warning`
  - `fail`

如果当前冻结产物无法支持 label-shuffle，必须标记：

```text
label_shuffle_status = blocked_by_missing_artifact
```

并说明缺失项，不得跳过不报。

---

## 12. Phase V2 必做验证 E：Feature Leakage Scan

必须新增 feature leakage scan。

至少扫描：

- Phase1C score 输入字段；
- label / future return 字段；
- date / asof / execution date 对齐；
- available-at 风险；
- 是否使用 future_return、future_rank、未来收益标签作为输入；
- 是否把测试期结果用于调参；
- 是否有 train/validation/independent_test 混用导致解释越界。

输出必须包含：

- `leakage_scan_status`
- `checked_fields`
- `suspicious_fields`
- `blocked_fields`
- `date_alignment_status`
- `available_at_status`
- `conclusion`

---

## 13. Phase V2 必交付产物

建议至少输出：

```text
data_tw/experiments/ltr_strategy_validation/phasev2_comprehensive_stability/phasev2_rolling_6m_12m.csv
data_tw/experiments/ltr_strategy_validation/phasev2_comprehensive_stability/phasev2_regime_segments.csv
data_tw/experiments/ltr_strategy_validation/phasev2_comprehensive_stability/phasev2_walk_forward_oos.csv
data_tw/experiments/ltr_strategy_validation/phasev2_comprehensive_stability/phasev2_label_shuffle_sanity.csv
data_tw/experiments/ltr_strategy_validation/phasev2_comprehensive_stability/phasev2_feature_leakage_scan.csv
data_tw/experiments/ltr_strategy_validation/phasev2_comprehensive_stability/phasev2_gate_summary.json
```

执行报告：

```text
docs/tw_ltr_strategy_validation/PHASEV2_COMPREHENSIVE_STABILITY_EXECUTION_REPORT_CN.md
```

---

## 14. Phase V2 验收门槛

Phase V2 通过最低门槛：

- rolling 6M / 12M 完成；
- 市况分段完成；
- walk-forward out-of-sample 完成或明确受阻；
- label-shuffle sanity check 完成或明确受阻；
- feature leakage scan 完成；
- independent_test 与 OOS 解释边界清楚；
- 未把 train/validation 结果当作产品化证据；
- 没有重训、调参、前端/API、联网、新数据、provider、accepted latest、monitor、交易链路越权；
- 能支持审查者判断是否进入 Phase V3 用户第一性产品化设计。

---

## 15. Gate

如果 V2 综合稳定性通过：

```text
request_phase_v3_user_first_product_design
```

如果 V2 显示 LTR 只在样本内/少数窗口强、OOS 不稳定、shuffle/leakage 失败或证据不足：

```text
archive_ltr_candidate_as_research_only
```

不得直接进入前端/API 实现或产品化。
