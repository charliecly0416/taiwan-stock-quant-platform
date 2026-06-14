# Phase 1C 审查意见 + 条件式 Phase 2 工作文档

生成时间：2026-06-13

审查者角色：本轮严格以 `docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md` 为唯一主线依据。

审查入口：

- `docs/tw_ltr_rerank_regime_turnover/PHASE1C_FINAL_LTR_REPAIR_EXECUTION_REPORT_CN.md`
- `scripts/diagnose_tw_ltr_phase1c_final_repair.py`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1c_final_ltr_repair/`

---

## 1. 审查结论

本轮 Phase 1C 的技术结果可以复现，且从指标上满足进入 Phase 2 的最低证据门槛。

但存在一个流程问题：上一轮审查文件要求先由用户在 A/B/C 中确认方向，才能执行最后一轮 Phase1C。当前对话中未见用户明确选择 A，但执行者报告写成“根据用户选择的最后一轮 Phase1C”。这属于流程证据不足，不是模型代码越界。

因此本轮审查结论为：

```text
technical_gate = request_phase2_regime_gating_work
process_gate = needs_user_acceptance_of_phase1c_result
```

在用户确认接受 Phase1C 结果前，不应让执行者直接开始 Phase2。

---

## 2. 可复现核验

已复现执行：

```bash
python scripts/diagnose_tw_ltr_phase1c_final_repair.py
```

复现输出：

```text
recommended_gate = request_phase2_regime_gating_work
gate_reason = Phase1C conservative rerank cleared all user-approved final gate conditions.
```

安全边界扫描结果：

- 只命中文档和脚本中的禁止声明、排序字段或内部变量；
- 未发现实际危险 API；
- 未发现 provider publish / refresh；
- 未发现 accepted latest switching；
- 未发现 monitor 写入或扫描；
- 未发现 broker / quick-trade / orders / target position / target weight；
- 未发现买入、卖出、仓位、收益承诺、上涨概率或胜率语义。

---

## 3. 主线边界审查

### 3.1 范围

Phase1C 仍处于 Stage 2：LTR reranker。

已确认：

- 未进入 regime-aware gating 动作实现；
- 未进入 turnover-controlled portfolio layer；
- 未进入 frontend explanation；
- 未改 frontend / API / monitor / database；
- 未新增 provider / token / network；
- 未做真实 replay、净值、成本、换手或动作次数结论。

### 3.2 特征与数据源

已确认：

- 复用 Phase1 样本；
- 不新增数据源；
- `trend_score` 仍排除；
- forbidden feature hits 为 `[]`；
- 未加入 institutional / margin / short / revenue / valuation 等禁止特征。

### 3.3 模型与 rerank 方式

本轮使用：

- LightGBM `LGBMRanker(objective="lambdarank")`；
- top-heavy label；
- qlib-preserving rerank；
- best candidate：`head10_all_l31_alpha0.7_top50_only`。

该方案不是纯粹替换 qlib，而是在 qlib Top50 内做保守重排序。它符合主文档“不推翻 qlib、在 qlib baseline 之上做第二阶段研究重排序”的方向。

但后续前端或报告必须把它描述为：

```text
qlib-preserving LTR rerank
```

不得描述成独立取代 qlib 的全市场新模型。

---

## 4. 关键结果审查

independent_test 对照：

| method | rank_ic_10d | ndcg@10 | ndcg@30 | ndcg@50 | top30_future_excess_rank_10d |
|---|---:|---:|---:|---:|---:|
| phase1c conservative rerank | 0.027360 | 0.559268 | 0.541698 | 0.567569 | 0.527896 |
| qlib top50 | 0.026642 | 0.543544 | 0.537373 | 0.565427 | 0.526614 |
| adaptive score | 0.027657 | 0.545739 | 0.537928 | 0.565340 | 0.527020 |
| confirmed_exit | 0.026509 | 0.543636 | 0.537459 | 0.565503 | 0.526716 |

审查判断：

- 相对 qlib top50：rank IC、NDCG@30、Top30 future excess rank 均通过；
- 相对 adaptive score：NDCG@30、Top30 future excess rank 通过，rank IC 略低；
- Top50 Jaccard = 1.0，说明该方案严格保留 qlib Top50 候选集合，只在内部重排；
- Top10 Jaccard = 0.503351，Top30 Jaccard = 0.691217，说明头部有实质重排；
- 因为 Stage 2 关注 TopK / rank quality，不是组合 replay，本轮结果足以作为进入 Phase2 的技术前置证据。

---

## 5. Findings

### Finding 1：流程授权证据不足

严重级别：High

上一轮审查要求用户确认后才能进入 Phase1C。当前未见用户明确选择“继续 Phase1C”，但执行者报告写成“根据用户选择”。这不影响代码产物本身复现，但影响流程合规。

处理：

必须由用户确认是否接受本轮 Phase1C 结果。确认后才可进入 Phase2。

### Finding 2：Phase1C 技术 gate 通过，但必须保守解释

严重级别：Medium

Phase1C 的胜出方案是 qlib-preserving top50-only rerank，不是全市场自由重排模型。

处理：

后续所有文档、脚本、前端解释必须称为“qlib-preserving LTR rerank”，不得把它包装成完全独立的新排序信号。

### Finding 3：本轮仍不是组合层结论

严重级别：Medium

本轮没有真实组合 replay，也没有净值、换手、成本、动作次数。

处理：

不得把 Phase1C 的 rank / NDCG / TopK 结果解释成组合收益、买卖动作、仓位、胜率或上涨概率。

---

## 6. 本轮 Gate

审查 gate：

```text
phase1c_technical_pass_but_wait_user_acceptance
```

只有用户确认接受 Phase1C 结果后，才允许执行者进入 Phase2。

---

## 7. 条件式 Phase 2 下一轮工作文档

以下文档仅在用户明确确认“接受 Phase1C，允许进入 Phase2”后生效。

### 7.1 Phase2 目标

只做 Stage 3：Regime-aware gating 的最小实现与离线评估。

目标是验证：

```text
qlib baseline + qlib-preserving LTR rerank
在 normal / caution / risk_off 下是否需要不同动作阈值
```

不得进入 turnover-controlled portfolio layer。

### 7.2 允许输入

Regime 输入只允许使用主文档白名单：

- `TWII_ret20`
- `TWII_ret60`
- `market_drawdown60`
- `market_volatility20`
- `market_breadth20`

LTR score 输入只允许使用 Phase1C 已冻结的：

- `score_head10_all_l31_alpha0.7_top50_only`
- 或其可复现生成逻辑

### 7.3 禁止事项

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
- 把 regime 解释成买卖信号或预测概率。

### 7.4 Phase2 最小实现要求

执行者应新增一个只读离线脚本，例如：

```text
scripts/evaluate_tw_ltr_phase2_regime_gating.py
```

实现内容：

- 复用 Phase1 样本与 Phase1C rerank score；
- 按主文档 regime 白名单生成 3 态：`normal` / `caution` / `risk_off`；
- 只做离线阈值 / 过滤 / 候选保守程度评估；
- 不生成真实动作指令；
- 不做组合换手层。

### 7.5 必须输出产物

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

### 7.6 指标要求

必须至少报告：

- 每个 regime 的 date_count / row_count；
- qlib baseline vs Phase1C rerank vs regime-gated rerank；
- NDCG@10 / @30 / @50；
- Top10 / Top30 / Top50 future excess rank；
- 分年度结果；
- 是否有单一 regime 或单一年份支撑的问题。

不得只报告整体收益率或单一 aggregate。

### 7.7 Phase2 Gate

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

