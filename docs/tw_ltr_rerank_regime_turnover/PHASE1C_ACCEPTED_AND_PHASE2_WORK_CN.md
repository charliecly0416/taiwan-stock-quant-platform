# Phase 1C 接受确认 + Phase 2 正式工作文档

生成时间：2026-06-13

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

用户确认：用户已说明 Phase1C 是与执行者直接确认后运行，因此上一轮“流程授权证据不足”的阻塞解除。

---

## 1. 放行结论

Phase1C 正式接受。

允许执行者进入：

```text
Phase 2: Regime-aware gating
```

冻结的 Stage 2 rerank 结果为：

```text
qlib-preserving LTR rerank
best_candidate = head10_all_l31_alpha0.7_top50_only
score_column = score_head10_all_l31_alpha0.7_top50_only
```

注意：该 rerank 是 qlib Top50 内保守重排序，不是替代 qlib 的独立全市场模型。后续文档和报告必须使用“qlib-preserving LTR rerank”语义。

---

## 2. Phase2 目标

只做 Stage 3：Regime-aware gating 的最小离线实现与评估。

目标是验证：

```text
qlib baseline + qlib-preserving LTR rerank
在 normal / caution / risk_off 下是否需要不同动作阈值或保守过滤
```

本轮不得进入 Stage 4 turnover-controlled portfolio layer。

---

## 3. 允许输入

Regime 输入只允许使用主文档白名单：

- `TWII_ret20`
- `TWII_ret60`
- `market_drawdown60`
- `market_volatility20`
- `market_breadth20`

LTR rerank 输入只允许使用 Phase1C 已冻结结果：

- `score_head10_all_l31_alpha0.7_top50_only`
- 或其可复现生成逻辑

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
- 把 regime 解释成买卖信号、收益预测或概率预测。

---

## 5. Phase2 最小实现要求

建议新增只读离线脚本：

```text
scripts/evaluate_tw_ltr_phase2_regime_gating.py
```

实现内容：

- 复用 Phase1 样本与 Phase1C rerank score；
- 按主文档 regime 白名单生成 3 态：`normal` / `caution` / `risk_off`；
- 只做离线阈值 / 过滤 / 候选保守程度评估；
- 不生成真实动作指令；
- 不做组合换手层；
- 不接前端或 API。

---

## 6. 必须输出产物

建议目录：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase2_regime_gating/
```

必须输出：

- `phase2_regime_definition.json`
- `phase2_regime_distribution.csv`
- `phase2_regime_metric_by_state.csv`
- `phase2_gating_threshold_grid.csv`
- `phase2_baseline_vs_regime_gated_comparison.csv`
- `phase2_gate_summary.json`
- `docs/tw_ltr_rerank_regime_turnover/PHASE2_REGIME_GATING_EXECUTION_REPORT_CN.md`

---

## 7. 指标要求

必须至少报告：

- 每个 regime 的 date_count / row_count；
- qlib baseline vs Phase1C rerank vs regime-gated rerank；
- NDCG@10 / @30 / @50；
- Top10 / Top30 / Top50 future excess rank；
- 分年度结果；
- 是否有单一 regime 或单一年份支撑的问题。

不得只报告整体收益率或单一 aggregate。

---

## 8. Phase2 Gate

执行者必须在 `phase2_gate_summary.json` 给出以下之一：

1. `request_phase3_turnover_layer_work`

   仅当：

   - regime-gated rerank 不低于 Phase1C rerank 的核心 TopK 质量；
   - 在 caution / risk_off 下能展示合理的保守过滤效果；
   - 结果不是只靠单一年份或单一 regime 成立；
   - 无越界数据、越权动作或交易语义。

2. `phase2_regime_gating_needs_repair`

   当 regime 定义或阈值有修复方向，但证据不足。

3. `stop_regime_gating_insufficient_evidence`

   当 regime gating 不能提供增量解释或稳定性。

如执行者发现需要改变 Phase2 目标、放宽 gate、进入 turnover、引入新数据源或改变用户语义，必须停止并回到用户确认。

