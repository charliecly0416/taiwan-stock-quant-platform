# Phase1C Anchor 精确复刻审计主线文档

生成日期：2026-06-15

## 1. 背景

近期 `docs/tw_qlib_oos_ltr_stacking/` 补强主线证明：新构建的 OOS stacking LTR 在 final test 有高收益信号，但 validation 稳健性不足、回撤恶化、低换手版本失败，因此不能默认化。

同时，本轮审查发现一个关键问题：补强主线已经从“复核原先效果较好的 old qlib + new LTR Phase1C”扩展成了“重新训练新的 OOS stacking LTR”。这两个对象不同，不能混为一谈。

因此，本支线只做一件事：

```text
回到原先 Phase1C 版本，做一次精确复刻审计，冻结它作为 anchor。
```

该 anchor 后续用于回答：

```text
任何新 LTR / OOS stacking / fresh retrain 是否真的超过原 Phase1C anchor？
```

而不是继续把 Phase1C 直接产品默认化。

---

## 2. 原先 Phase1C Anchor 是什么

根据既有产物，Phase1C anchor 固定为：

```text
candidate_id: head10_all_l31_alpha0.7_top50_only
model_id: head10_all_l31
score_column: score_head10_all_l31_alpha0.7_top50_only
blend_alpha: 0.7
preserve_scope: top50_only
label_col: relevance_10d_top_heavy
model: LGBMRanker objective=lambdarank, num_leaves=31, learning_rate=0.03, n_estimators=120, random_state=42
```

核心来源：

```text
docs/tw_ltr_rerank_regime_turnover/PHASE1C_FINAL_LTR_REPAIR_EXECUTION_REPORT_CN.md
docs/tw_ltr_rerank_regime_turnover/PHASE3A0_FROZEN_PHASE1C_SCORE_EXECUTION_REPORT_CN.md
docs/tw_ltr_qlib_split_aligned_retrain/PHASES2F_OLD_VS_FRESH_SAME_WINDOW_RECHECK_REPORT_CN.md
```

核心数据产物：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_ltr_samples.csv
data_tw/experiments/ltr_rerank_regime_turnover/phase1c_final_ltr_repair/phase1c_validation_selection.csv
data_tw/experiments/ltr_rerank_regime_turnover/phase1c_final_ltr_repair/phase1c_independent_test_comparison.csv
data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv
data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_score_reproduction_metrics.csv
```

已知同窗口复核结果：

| method | fee_tax_adjusted_net_return | max_drawdown | action_count |
| --- | ---: | ---: | ---: |
| old_qlib_new_ltr_phase1c_simple | 0.721631 | -0.050830 | 405 |
| fresh_qlib_top50_adaptive_baseline | 0.662457 | -0.088396 | 410 |
| fresh_ltr_simple | 0.544381 | -0.132896 | 408 |
| fresh_ltr_turnover_controlled | 0.615059 | -0.111310 | 63 |

共同股票池复核：

| method | fee_tax_adjusted_net_return | max_drawdown | action_count |
| --- | ---: | ---: | ---: |
| old_qlib_new_ltr_phase1c_simple | 0.641235 | -0.076739 | 405 |
| fresh_qlib_top50_adaptive_baseline | 0.625943 | -0.088431 | 410 |
| fresh_ltr_simple | 0.544381 | -0.132896 | 408 |
| fresh_ltr_turnover_controlled | 0.615059 | -0.111310 | 63 |

解释：Phase1C anchor 有小幅优势，但共同股票池下优势约 `+1.53` 个百分点，不足以直接切默认。

---

## 3. 本支线目标

本支线目标是建立一个不可混淆的 anchor contract：

1. 精确复刻 Phase1C 固定配置；
2. 复核 row-level score 与原 Phase3A0 一致；
3. 复核同窗口 full / common universe 回放指标；
4. 补齐只读审计：score provenance、feature schema、universe coverage、next-day accounting、费用税费、真实 PnL contribution、异常价格/日期；
5. 输出最终 anchor card，供后续所有新策略对照。

本支线不是：

- 重新训练新的 LTR；
- 重新选择 LTR 窗口；
- 引入 Q0/Q1/Q2、L1/L2/L3/L4；
- 改 label、feature、universe、策略规则；
- 做 regime gating、turnover-controlled 新变体；
- 改前端/API；
- 推动默认策略切换。

---

## 4. 用户第一性原则

本支线最终只输出普通用户能理解的结论：

```text
Phase1C anchor 是否真实可复现？
相对当前默认 fresh qlib/top50 adaptive 是否仍有稳定优势？
如果有，优势多大、风险是什么？
它只能作为研究候选，还是可以进入下一步默认候选讨论？
```

普通用户不需要看到所有研究表格。研究表格只作为审计证据。

---

## 5. Phase 设计

### Phase A0：审查者冻结工作文档

目标：由审查者先写 Phase A1 工作文档，冻结执行者可做事项。

必须冻结：

- anchor identity；
- 固定输入产物；
- 固定 score column；
- 固定回放窗口 `2025-07-01..2026-05-07`；
- 固定 baseline 对照；
- full universe 与 common universe 定义；
- 只读安全边界；
- 禁止重新训练、调参、换窗口、换特征。

### Phase A1：Anchor 精确复刻执行

执行者只能做只读复刻：

1. 读取 Phase1C / Phase3A0 / S2F 既有产物；
2. 复核 Phase1C 配置是否一致；
3. 复核 row-level score reproduction metrics 是否完全一致或在既定容差内；
4. 复跑或复核同窗口 replay，不得改引擎、费用、执行口径；
5. 输出 full universe 与 common universe 指标；
6. 输出真实 PnL contribution 与异常日期/股票审计；
7. 输出 anchor reproduction report。

建议输出：

```text
docs/tw_phase1c_anchor_reproduction/PHASEA1_ANCHOR_REPRODUCTION_EXECUTION_REPORT_CN.md
data_tw/experiments/phase1c_anchor_reproduction/phasea1_anchor_metrics.csv
data_tw/experiments/phase1c_anchor_reproduction/phasea1_common_universe_metrics.csv
data_tw/experiments/phase1c_anchor_reproduction/phasea1_score_reproduction_audit.csv
data_tw/experiments/phase1c_anchor_reproduction/phasea1_real_pnl_contribution_by_symbol.csv
data_tw/experiments/phase1c_anchor_reproduction/phasea1_real_pnl_contribution_by_day.csv
data_tw/experiments/phase1c_anchor_reproduction/phasea1_anchor_summary.json
```

### Phase A2：审查与 Anchor Card

审查者必须判断：

- 是否确实复刻原 Phase1C，而不是新训练；
- 是否存在任何窗口、特征、label、universe、回放口径漂移；
- 同窗口指标是否与 S2F 一致；
- common universe 优势是否仍存在；
- 回撤和贡献集中是否可接受；
- 结论是否只写成研究候选，不擅自默认化。

若通过，审查者输出：

```text
docs/tw_phase1c_anchor_reproduction/PHASEA2_REVIEW_AND_ANCHOR_CARD_CN.md
```

Anchor card 应包含：

```text
策略名称：Phase1C qlib-preserving LTR rerank anchor
定位：研究候选 / anchor benchmark
回放窗口：2025-07-01..2026-05-07
full universe return / drawdown / actions
common universe return / drawdown / actions
相对 fresh qlib/top50 adaptive 的差值
主要风险：优势小、universe 敏感、贡献集中、仍需多窗口验证
后续用途：作为所有新 LTR / OOS stacking 的最低比较锚点
```

---

## 6. 禁止事项

全支线禁止：

- 重新训练 qlib；
- 重新训练 LTR；
- 新增 LTR candidate；
- 新增 Q0/Q1/Q2 或 L1/L2/L3/L4 窗口矩阵；
- 改 label、feature、score column、blend alpha、preserve scope；
- 改 replay 费用、税费、next-day execution 口径；
- 改前端/API；
- provider refresh / publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / orders / quick-trade；
- target position / target weight；
- 输出真实买卖、持有、仓位、收益承诺、胜率或上涨概率。

若执行者发现必须训练或改口径才能复刻，必须停止并报告，不得自行扩展。

---

## 7. 通过标准

Phase A1/A2 通过标准：

1. anchor identity 与 Phase1C / Phase3A0 完全一致；
2. row-level score reproduction metrics 通过；
3. S2F 同窗口指标可复现或差异有明确解释；
4. common universe 结果单独列出；
5. 真实 PnL contribution 和异常日审计完成；
6. 未引入新训练、新窗口、新特征、新数据源；
7. 结论不默认化，只冻结 anchor。

失败条件：

- 找不到原 Phase1C 必要产物；
- row-level score 不能复现；
- replay 指标与 S2F 差异大且无法解释；
- 发现任何静默改口径；
- 执行者新增了主线未授权内容。

---

## 8. 给审查者的一句话

请按 `docs/tw_phase1c_anchor_reproduction/PHASE1C_ANCHOR_REPRODUCTION_MAINLINE_CN.md` 先撰写 Phase A1 工作文档，冻结原 Phase1C anchor 的身份、输入产物、score column、同窗口回放口径、full/common universe 对照和只读禁止事项；重点防止执行者重新训练、改窗口、换特征或把补强主线的 Q0/L1-L4 新实验混入本支线。

## 9. 给执行者的一句话

请等待审查者的 Phase A1 工作文档后再执行；执行时只能精确复刻原 Phase1C anchor，复核 Phase1C/Phase3A0/S2F 既有产物和同窗口 full/common universe 回放指标，并补齐只读审计报告，不得重新训练 qlib/LTR、不得改窗口/特征/label/score column/回放口径、不得改前端/API 或触发 provider/accepted latest/monitor/交易链路。
