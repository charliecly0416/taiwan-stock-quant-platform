# Phase A1 工作文档：Phase1C Anchor 精确复刻执行合同

生成日期：2026-06-15

依据文档：

```text
docs/tw_phase1c_anchor_reproduction/PHASE1C_ANCHOR_REPRODUCTION_MAINLINE_CN.md
```

前置 gate：

```text
phase_a1_anchor_reproduction_contract_frozen
```

## 1. A1 目标

Phase A1 只做一件事：

```text
精确复刻并审计原 Phase1C anchor。
```

A1 的目标不是改进策略，也不是重新训练模型，而是冻结一个不可混淆的历史 anchor，用于后续判断任何新 LTR / OOS stacking / fresh retrain 是否真的超过原 Phase1C。

A1 允许：

- 读取既有 Phase1C / Phase3A0 / S2F 产物；
- 复核 anchor identity；
- 复核 row-level score reproduction；
- 复核或复跑同窗口只读 replay；
- 输出 full universe 与 common universe 对照；
- 补真实 PnL contribution、异常日期/股票、费用税费、next-day accounting 审计。

A1 不允许：

- 训练 qlib；
- 训练 LTR；
- 新增 candidate；
- 改窗口；
- 改 feature；
- 改 label；
- 改 score column；
- 改 replay 费用、税费或 next-day execution 口径；
- 引入 Q0/Q1/Q2 或 L1/L2/L3/L4 补强主线实验。

## 2. Anchor Identity 冻结

Phase1C anchor 固定为：

```text
candidate_id: head10_all_l31_alpha0.7_top50_only
model_id: head10_all_l31
score_column: score_head10_all_l31_alpha0.7_top50_only
blend_alpha: 0.7
preserve_scope: top50_only
label_col: relevance_10d_top_heavy
model: LGBMRanker
objective: lambdarank
num_leaves: 31
learning_rate: 0.03
n_estimators: 120
random_state: 42
```

执行者必须逐项核对以上字段。任何字段不一致，都必须停止并报告，不得自行修正或替换。

## 3. 固定输入产物

A1 只能使用以下既有产物作为 anchor 证据来源。

文档来源：

```text
docs/tw_ltr_rerank_regime_turnover/PHASE1C_FINAL_LTR_REPAIR_EXECUTION_REPORT_CN.md
docs/tw_ltr_rerank_regime_turnover/PHASE3A0_FROZEN_PHASE1C_SCORE_EXECUTION_REPORT_CN.md
docs/tw_ltr_qlib_split_aligned_retrain/PHASES2F_OLD_VS_FRESH_SAME_WINDOW_RECHECK_REPORT_CN.md
```

数据来源：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_ltr_samples.csv
data_tw/experiments/ltr_rerank_regime_turnover/phase1c_final_ltr_repair/phase1c_validation_selection.csv
data_tw/experiments/ltr_rerank_regime_turnover/phase1c_final_ltr_repair/phase1c_independent_test_comparison.csv
data_tw/experiments/ltr_rerank_regime_turnover/phase1c_final_ltr_repair/phase1c_gate_summary.json
data_tw/experiments/ltr_rerank_regime_turnover/phase1c_final_ltr_repair/phase1c_diagnosis_summary.json
data_tw/experiments/ltr_rerank_regime_turnover/phase1c_final_ltr_repair/phase1c_topk_preservation_diagnostics.csv
data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv
data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_score_reproduction_metrics.csv
```

若某个必需产物不存在，执行者必须报告缺失项。不得用 T2/T2R 新产物、Q0/L1-L4 新模型、fresh LTR 产物或临时重训结果代替。

## 4. Score Column 冻结

唯一允许作为 Phase1C anchor row score 的列：

```text
score_head10_all_l31_alpha0.7_top50_only
```

禁止使用或混用：

```text
ltr_score
score
score_head10_all_l31
Q0_L1_1y
Q0_L2_2y
Q0_L3_3y
Q0_L4_4y
old_frozen_t2_ltr_simple
old_frozen_t2r_ltr_simple
fresh_ltr_simple
fresh_ltr_turnover_controlled
```

若复刻脚本内部需要临时列名，最终审计必须证明该临时列完全来自：

```text
score_head10_all_l31_alpha0.7_top50_only
```

## 5. 固定回放窗口与口径

同窗口回放窗口固定为：

```text
2025-07-01..2026-05-07
```

回放口径固定：

```text
initial_cash_or_equity_assumption: 1000000.0
fee_rate: 0.001425
tax_rate: 0.003
position_count_target: 10
execution: next-day execution
price source: 与 S2F 同窗口复核一致
```

禁止：

- 改 final test 起止日期；
- 改 initial cash；
- 改 fee / tax；
- 改持仓数量；
- 改 next-day execution；
- 为了贴合结果替换价格源；
- 用 T2/T2R 的 replay 结果替代 Phase1C anchor replay。

## 6. Baseline 与对照冻结

A1 必须复核以下同窗口指标。

Full universe / 原 S2F 口径：

| method | fee_tax_adjusted_net_return | max_drawdown | action_count |
| --- | ---: | ---: | ---: |
| old_qlib_new_ltr_phase1c_simple | 0.721631 | -0.050830 | 405 |
| fresh_qlib_top50_adaptive_baseline | 0.662457 | -0.088396 | 410 |
| fresh_ltr_simple | 0.544381 | -0.132896 | 408 |
| fresh_ltr_turnover_controlled | 0.615059 | -0.111310 | 63 |

Common universe：

| method | fee_tax_adjusted_net_return | max_drawdown | action_count |
| --- | ---: | ---: | ---: |
| old_qlib_new_ltr_phase1c_simple | 0.641235 | -0.076739 | 405 |
| fresh_qlib_top50_adaptive_baseline | 0.625943 | -0.088431 | 410 |
| fresh_ltr_simple | 0.544381 | -0.132896 | 408 |
| fresh_ltr_turnover_controlled | 0.615059 | -0.111310 | 63 |

A1 可以复跑或读取既有 S2F 产物，但必须说明来源。若复跑结果与上表有差异，必须给出精确差异和原因，不得静默覆盖 anchor 指标。

## 7. Full / Common Universe 定义

Full universe：

```text
原 Phase1C / S2F 同窗口 replay 使用的可回放 universe。
```

Common universe：

```text
old_qlib_new_ltr_phase1c_simple
fresh_qlib_top50_adaptive_baseline
fresh_ltr_simple
fresh_ltr_turnover_controlled
在同窗口可共同比较的股票/日期集合。
```

A1 必须输出：

- full universe 指标；
- common universe 指标；
- common universe key 数量；
- 若 common universe 过滤影响指标，必须说明影响。

不得把 T2/T2R 的 overlap-feature universe 当作本支线 common universe。

## 8. 必做审计

A1 报告必须包含以下审计。

### 8.1 Anchor identity audit

| field | expected | actual | pass |
| --- | --- | --- | --- |
| candidate_id | head10_all_l31_alpha0.7_top50_only | 待填 | yes/no |
| model_id | head10_all_l31 | 待填 | yes/no |
| score_column | score_head10_all_l31_alpha0.7_top50_only | 待填 | yes/no |
| blend_alpha | 0.7 | 待填 | yes/no |
| preserve_scope | top50_only | 待填 | yes/no |
| label_col | relevance_10d_top_heavy | 待填 | yes/no |

### 8.2 Score reproduction audit

必须读取：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_score_reproduction_metrics.csv
```

并报告：

- row count；
- score column；
- max absolute difference；
- mean absolute difference；
- pass / fail；
- tolerance。

若 reproduction metrics 不通过，A1 必须停止，不得继续生成 anchor card 候选。

### 8.3 Replay metrics audit

必须输出：

```text
fee_tax_adjusted_net_return
gross_return
max_drawdown
action_count
buy_count
sell_count
fee_and_tax
turnover
daily_nav_available_count
missing_price_days
skipped_trade_count
last_day_new_trade_without_next_price_count
```

### 8.4 Next-day accounting audit

必须确认：

```text
execution_date > signal_date
missing_price_days = 0 或解释原因
skipped_trade_count = 0 或解释原因
last_day_new_trade_without_next_price_count = 0 或解释原因
```

### 8.5 Real PnL contribution

必须输出逐票与逐日真实 PnL contribution：

```text
realized_pnl
unrealized_pnl
fee_tax_allocated
net_pnl
share_of_total_net_pnl
top contribution symbols
worst contribution symbols
top contribution days
```

禁止只用 sell-notional proxy 冒充真实 PnL。

### 8.6 异常审计

必须检查：

- 单票贡献集中；
- 单日贡献集中；
- 异常价格；
- 异常日收益；
- 是否存在一两只股票或几天主导结论。

## 9. 输出产物

执行者应提交：

```text
docs/tw_phase1c_anchor_reproduction/PHASEA1_ANCHOR_REPRODUCTION_EXECUTION_REPORT_CN.md
```

建议输出目录：

```text
data_tw/experiments/phase1c_anchor_reproduction/
```

建议产物：

```text
phasea1_anchor_identity_audit.csv
phasea1_score_reproduction_audit.csv
phasea1_anchor_metrics.csv
phasea1_common_universe_metrics.csv
phasea1_next_day_accounting_audit.csv
phasea1_real_pnl_contribution_by_symbol.csv
phasea1_real_pnl_contribution_by_day.csv
phasea1_outlier_audit.csv
phasea1_anchor_summary.json
```

## 10. 只读安全边界

A1 全程只读研究，不得触发任何真实链路。

禁止：

```text
provider refresh / publish
accepted latest switching
monitor config save / scan / alerts write
broker
orders
quick-trade
target position
target weight
frontend/API 改动
```

禁止输出：

```text
真实买入/卖出指令
持有建议
仓位建议
收益承诺
胜率
上涨概率
```

允许出现：

```text
历史回放
只读复刻
研究候选
anchor benchmark
历史 action_count / buy_count / sell_count
```

其中 `buy_count` / `sell_count` 只能作为历史回放统计，不得写成行动建议。

## 11. 禁止混入补强主线

A1 特别禁止混入以下内容：

```text
docs/tw_qlib_oos_ltr_stacking/
data_tw/experiments/tw_qlib_oos_ltr_stacking/phase_t1
data_tw/experiments/tw_qlib_oos_ltr_stacking/phase_t2
data_tw/experiments/tw_qlib_oos_ltr_stacking/phase_t2r
Q0_L1_1y
Q0_L2_2y
Q0_L3_3y
Q0_L4_4y
old_frozen_t2_ltr_simple
old_frozen_t2r_ltr_simple
```

这些产物只能作为“不得混入”的审查参照，不能作为 A1 anchor 输入。

## 12. A1 通过标准

A1 可提交审查的最低标准：

- anchor identity 完全一致；
- score column 完全一致；
- row-level score reproduction 通过；
- 同窗口 full universe 指标复现或差异可解释；
- common universe 指标复现或差异可解释；
- next-day accounting 通过；
- 费用税费口径与 S2F 一致；
- 真实 PnL contribution 完成；
- 异常价格 / 单票 / 单日贡献审计完成；
- 未训练、未调参、未换窗口、未换特征；
- 未混入 Q0/L1-L4 或 T2/T2R 产物；
- 未触发任何 provider / accepted latest / monitor / broker / order / quick-trade / frontend API 链路；
- 结论只冻结 anchor，不推动默认化。

## 13. 失败处理

若出现以下任一情况，执行者必须停止并报告：

- 找不到必需 Phase1C / Phase3A0 / S2F 产物；
- anchor identity 字段不一致；
- score reproduction 不通过；
- 同窗口 replay 指标与 S2F 差异大且无法解释；
- 必须训练或改口径才能继续；
- 发现历史产物本身存在无法解释的数据污染。

不得用新训练、新窗口、新特征或补强主线产物绕过失败。

## 14. 给执行者的一句话

请按本文执行 Phase A1：只读复刻原 Phase1C anchor，固定使用 `head10_all_l31_alpha0.7_top50_only` 与 `score_head10_all_l31_alpha0.7_top50_only`，复核 Phase1C/Phase3A0/S2F 既有产物和 `2025-07-01..2026-05-07` 同窗口 full/common universe 指标，并补齐 score reproduction、next-day accounting、费用税费、真实 PnL contribution 与异常审计；不得重新训练、改窗口、换特征、换 score column、混入 Q0/L1-L4 或触发任何真实交易/monitor/provider/accepted latest/前端 API 链路。
