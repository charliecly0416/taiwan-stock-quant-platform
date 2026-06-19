# Phase 2 审查意见 + 用户决策请求

生成时间：2026-06-13

审查者角色：本轮严格以 `docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md` 为唯一主线依据。

审查入口：

- `docs/tw_ltr_rerank_regime_turnover/PHASE2_REGIME_GATING_EXECUTION_REPORT_CN.md`
- `scripts/evaluate_tw_ltr_phase2_regime_gating.py`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase2_regime_gating/`

---

## 1. 审查结论

Phase 2 执行者没有偏离主线，也没有新增分支。

本轮严格停留在 Stage 3：Regime-aware gating 的离线评估范围内；未进入 turnover layer、frontend/API、provider、monitor、database 或交易链路。

但是，本轮结果不能进入 Phase 3。

原因是 validation 选择出的最优 regime gate 为：

```text
regime_gate_c50_r50_p0.0
```

它等同于 Phase1C 原始 qlib-preserving LTR rerank，是 no-op gating。也就是说，本轮没有证明 normal / caution / risk_off 需要不同阈值或保守过滤。

执行者自己的 gate 与复现结果一致：

```text
stop_regime_gating_insufficient_evidence
```

因此必须停止推进，回到用户确认下一步。

---

## 2. 可复现核验

已复现执行：

```bash
python scripts/evaluate_tw_ltr_phase2_regime_gating.py
```

复现输出：

```text
recommended_gate = stop_regime_gating_insufficient_evidence
gate_reason = Regime gating did not provide incremental explanation or stability over Phase1C.
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

### 3.1 范围合规

本轮符合 Phase2 正式工作文档要求：

- 复用 Phase1 样本；
- 复现 Phase1C `qlib-preserving LTR rerank`；
- 仅使用 regime 白名单字段；
- 只做离线阈值 / 过滤 / 候选保守程度评估；
- 未生成真实动作指令；
- 未做组合换手层。

### 3.2 Regime 输入合规

Regime 输入为：

- `TWII_ret20`
- `TWII_ret60`
- `market_drawdown60`
- `market_volatility20`
- `market_breadth20`

符合主文档 Stage 3 白名单。

### 3.3 禁止事项合规

已确认：

- 未新增数据源；
- 未新增白名单外特征；
- 未引入 `trend_score`；
- 未引入 forbidden features；
- 未联网；
- 未 provider refresh / publish；
- 未 accepted latest switching；
- 未改 frontend / API / monitor / database；
- 未接 broker / quick-trade / orders / target position / target weight。

---

## 4. 关键结果审查

### 4.1 validation 选择结果

validation 阈值网格最高分为：

```text
regime_gate_c50_r50_p0.0
```

含义：

- caution scope = 50；
- risk_off scope = 50；
- risk penalty = 0；
- 与 Phase1C rerank 等价；
- 没有任何新增保守过滤。

### 4.2 independent_test 最终对照

| method | rank_ic_10d | ndcg@10 | ndcg@30 | ndcg@50 | top30_future_excess_rank_10d |
|---|---:|---:|---:|---:|---:|
| qlib top50 | 0.026642 | 0.543544 | 0.537373 | 0.565427 | 0.526614 |
| Phase1C rerank | 0.027360 | 0.559035 | 0.541729 | 0.567592 | 0.527890 |
| selected regime gate | 0.027360 | 0.559035 | 0.541729 | 0.567592 | 0.527890 |

审查判断：

- selected regime gate 不低于 Phase1C，是因为它就是 Phase1C；
- 没有新增 regime-aware 行为；
- 不能解释为 Phase2 证明了不同 regime 阈值有效。

### 4.3 分状态结果

独立测试集分布：

- normal：158 dates；
- caution：44 dates；
- risk_off：7 dates。

风险点：

- risk_off 样本只有 7 个交易日，不能作为强证据；
- no-op gate 在 caution / risk_off 下没有更保守的 top30 过滤；
- 报告中 `caution_or_risk_off_conservative_effect = False`。

---

## 5. Findings

### Finding 1：不能进入 Phase3 turnover layer

严重级别：High

证据：

- `phase2_gate_summary.json` 给出 `recommended_gate = stop_regime_gating_insufficient_evidence`；
- selected validation method 是 `regime_gate_c50_r50_p0.0`；
- `has_non_noop_gate = False`；
- `caution_or_risk_off_conservative_effect = False`。

结论：

Phase2 没有证明 regime gating 有增量价值，不能进入 Stage 4 turnover-controlled portfolio layer。

### Finding 2：非 no-op gate 的 independent_test 改善不能作为推进证据

严重级别：Medium

证据：

- 阈值选择要求基于 validation；
- validation 最优是 no-op；
- 个别非 no-op 配置在 independent_test 上看起来更好，但不能事后用 independent_test 反选参数。

结论：

不得越过 validation selection 规则推进。

### Finding 3：risk_off 样本不足，不能作为强 regime 证据

严重级别：Medium

证据：

- independent_test risk_off 仅 7 个日期；
- risk_off 结果容易受小样本影响。

结论：

不能基于 risk_off 局部结果扩写主线或进入组合层。

---

## 6. 本轮 Gate

审查 gate：

```text
phase2_stop_for_user_decision
```

原因：

```text
Phase2 范围合规，但 regime gating 未产生非 no-op 增量证据。是否停止本主线、回退为 Phase1C rerank-only、或允许重新定义 Phase2 gate，属于用户 tradeoff。
```

---

## 7. 需要用户确认的下一步

请用户在以下方向中选择一个。

### 选项 A：停止 regime gating，不进入 Phase3

含义：

- 接受 Phase2 结论：当前数据下 regime gating 没有增量；
- 保留 Phase1C `qlib-preserving LTR rerank` 作为本主线有效成果；
- 不进入 turnover layer；
- 本主线以 `stop_regime_gating_insufficient_evidence` 关闭。

### 选项 B：允许一次 Phase2B 修复，但不得进入 Phase3

含义：

- 仍停留在 Stage 3；
- 不新增数据源、不新增特征、不改前端/API、不做 turnover；
- 只允许重新检查 regime 定义和 validation selection 口径；
- 若 Phase2B 仍选出 no-op 或没有清晰保守效果，则必须停止本主线。

Phase2B 可允许范围：

- 固定 Phase1C rerank；
- 只调整 regime 规则阈值；
- 只在 validation 上选择；
- 明确要求 selected gate 必须是非 no-op，且不降低 Phase1C 核心 TopK；
- 独立测试只做最终检验。

### 选项 C：用户明确放宽 gate，允许进入 Phase3

含义：

- 用户明确接受 regime gating 没有增量证明；
- 仍允许进入 turnover layer；
- 审查者不建议该选项，因为它会削弱主文档 Stage 3 的证据要求。

---

## 8. 当前不给执行者的新工作指令

在用户确认前，不应给执行者继续执行文档。

原因：

- 进入 Phase3：证据不足；
- 继续 Phase2B：需要用户确认是否值得再投入一轮；
- 停止本主线：需要用户确认；
- 放宽 gate：必须由用户明确承担 tradeoff。

