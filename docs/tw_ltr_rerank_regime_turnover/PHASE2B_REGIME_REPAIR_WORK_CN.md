# Phase 2B Regime Gating 修复工作文档

生成时间：2026-06-13

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

用户确认：允许尝试使用合理方法修复 Phase2 regime gating，但不得直接进入 Phase3。

---

## 1. 本轮目标

只做 Stage 3：Regime-aware gating 的一次修复。

要回答的问题是：

```text
在固定 Phase1C qlib-preserving LTR rerank 的前提下，
是否能用更合理的 regime 定义或 validation 选择口径，
得到一个非 no-op、可解释、且不降低核心 TopK 质量的 regime gating？
```

本轮不得进入 Stage 4 turnover-controlled portfolio layer。

---

## 2. 固定输入

必须固定使用 Phase1C 结果：

```text
score_head10_all_l31_alpha0.7_top50_only
```

该分数语义必须保持为：

```text
qlib-preserving LTR rerank
```

不得把它描述成替代 qlib 的全市场独立模型。

---

## 3. 允许修复范围

只允许在以下范围内修复：

- 重新检查 `normal / caution / risk_off` 规则阈值；
- 只使用主文档 regime 白名单字段：
  - `TWII_ret20`
  - `TWII_ret60`
  - `market_drawdown60`
  - `market_volatility20`
  - `market_breadth20`
- 改进 validation selection score，使其显式奖励非 no-op 保守效果；
- 增加对 caution / risk_off 下 TopK 过滤强度的诊断；
- 对 `risk_off` 小样本问题做稳健性说明；
- 保持 independent_test 只用于最终检验，不得用来反选参数。

---

## 4. 禁止事项

执行者不得：

- 新增数据源；
- 新增白名单外特征；
- 引入 `trend_score`；
- 引入 forbidden features；
- 联网、provider refresh / publish、accepted latest switching；
- 改 frontend / API / monitor / database；
- 做 turnover portfolio layer；
- 做真实交易、broker、quick-trade、orders、target position / target weight；
- 输出买入、卖出、持有、仓位、收益承诺、上涨概率、胜率语义；
- 把 regime 解释成买卖信号、收益预测或概率预测；
- 用 independent_test 选择阈值或反向调参。

---

## 5. 建议实现

建议新增脚本：

```text
scripts/repair_tw_ltr_phase2b_regime_gating.py
```

建议输出目录：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase2b_regime_repair/
```

实现要点：

- 复用 Phase1 样本；
- 复现 Phase1C score；
- 生成多个候选 regime definition；
- 生成多个非 no-op gating rule；
- validation 上选择候选；
- independent_test 上只做最终对照；
- 明确比较：
  - qlib baseline；
  - Phase1C rerank；
  - Phase2 no-op gate；
  - Phase2B repaired regime gate。

---

## 6. 必须输出产物

必须输出：

- `phase2b_regime_definition_candidates.json`
- `phase2b_regime_distribution.csv`
- `phase2b_validation_selection.csv`
- `phase2b_regime_metric_by_state.csv`
- `phase2b_independent_test_comparison.csv`
- `phase2b_gate_summary.json`
- `docs/tw_ltr_rerank_regime_turnover/PHASE2B_REGIME_REPAIR_EXECUTION_REPORT_CN.md`

---

## 7. 指标要求

必须报告：

- 每个 regime 的 date_count / row_count；
- NDCG@10 / @30 / @50；
- Top10 / Top30 / Top50 future excess rank；
- TopK median qlib rank；
- qlib baseline vs Phase1C vs Phase2B；
- 分年度结果；
- caution / risk_off 下是否产生非 no-op 保守过滤；
- 是否存在单一年份或单一 regime 支撑。

---

## 8. Phase2B Gate

执行者必须在 `phase2b_gate_summary.json` 给出以下之一：

1. `request_phase3_turnover_layer_work`

   仅当同时满足：

   - selected gate 是非 no-op；
   - validation 选择流程没有使用 independent_test；
   - independent_test 上 Phase2B 不低于 Phase1C 的核心 TopK 质量；
   - caution / risk_off 至少一个状态展示清晰保守过滤效果；
   - 结果不是只靠单一年份或单一 regime 成立；
   - 无越界数据、越权动作或交易语义。

2. `stop_regime_gating_insufficient_evidence`

   当 Phase2B 仍选出 no-op，或非 no-op gate 无法稳定保留 Phase1C 核心 TopK 质量。

3. `phase2b_needs_user_decision`

   仅当出现必须由用户决定的 tradeoff，例如：

   - 是否接受轻微 TopK 下降来换取更保守过滤；
   - 是否放宽 regime gate；
   - 是否绕过 regime 直接进入 turnover。

如出现第 3 类情况，必须停止并回到用户确认。

