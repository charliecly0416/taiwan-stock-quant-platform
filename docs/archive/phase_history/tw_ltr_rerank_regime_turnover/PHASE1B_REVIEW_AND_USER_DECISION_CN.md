# Phase 1B 审查意见 + 用户决策请求

生成时间：2026-06-13

审查者角色：本轮严格以 `docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md` 为唯一主线依据。

审查入口：

- `docs/tw_ltr_rerank_regime_turnover/PHASE1B_LTR_REPAIR_EXECUTION_REPORT_CN.md`
- `scripts/diagnose_tw_ltr_phase1b_repair.py`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1b_ltr_repair/`

---

## 1. 审查结论

Phase 1B 执行者没有偏离主线，也没有新增分支。

本轮仍然停留在 Stage 2：LTR reranker 的诊断与修复范围内。执行者没有进入 Phase 2 regime-aware gating，没有进入 turnover layer，没有改 frontend / API / provider / monitor / broker / quick-trade / orders。

但是，本轮结果仍然不能进入 Phase 2。

原因是 repaired LTR 仍未满足进入 Phase 2 的证据门槛：虽然 rank IC 继续高于 qlib baseline，但 independent_test 上 `NDCG@30` 和 `Top30 future excess rank` 仍低于 qlib baseline。执行者自己的 gate 与复现结果一致，均为 `phase1b_ltr_needs_repair`。

因此本轮必须暂停推进，回到用户确认下一步 tradeoff。

---

## 2. 可复现核验

已复现执行：

```bash
python scripts/diagnose_tw_ltr_phase1b_repair.py
```

复现输出：

```text
recommended_gate = phase1b_ltr_needs_repair
gate_reason = some repaired LTR signals improved, but Phase1B gate was not fully cleared
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

本轮执行内容符合上一轮 Phase 1B 工作文档：

- 复用 Phase1 样本；
- 做 5d / 10d / 20d label window 对照；
- 做 qlib-only、qlib+technical、qlib+liquidity、qlib+market、all whitelist feature ablation；
- 使用 train / validation 做模型选择；
- independent_test 只用于最终检验；
- 输出 diagnosis、ablation、label window、model selection、test comparison、TopK overlap / stability、gate summary。

### 3.2 特征边界合规

已确认：

- input feature count：34；
- `trend_score` 仍排除；
- forbidden feature hits：`[]`；
- 未新增数据源；
- 未引入 institutional / margin / short / revenue / valuation 等主文档禁止特征。

### 3.3 模型边界合规

仍使用 LightGBM / LambdaMART 风格 LTR。

未发现：

- Transformer reranker；
- deep ranking；
- end-to-end decision model；
- decision-focused 主模型。

---

## 4. 关键结果审查

best candidate：

```text
candidate_30_20d_all_whitelist_without_trend_score
label_window = 20d
feature_group = all_whitelist_without_trend_score
num_leaves = 31
learning_rate = 0.03
n_estimators = 120
```

independent_test 核心对照：

| method | rank_ic_10d | ndcg@10 | ndcg@30 | ndcg@50 | top30_future_excess_rank_10d |
|---|---:|---:|---:|---:|---:|
| repaired_ltr | 0.059551 | 0.520816 | 0.525077 | 0.566626 | 0.523047 |
| qlib top50 | 0.026642 | 0.543544 | 0.537373 | 0.565427 | 0.526614 |
| adaptive score | 0.027657 | 0.545739 | 0.537928 | 0.565340 | 0.527020 |
| confirmed_exit | 0.026509 | 0.543636 | 0.537459 | 0.565503 | 0.526716 |

审查判断：

- rank IC 条件：通过；
- NDCG@30 条件：不通过；
- Top30 future excess rank 条件：不通过；
- 非单一 segment 条件：执行者标记为通过，但由于核心 TopK 条件未通过，不足以支持进入 Phase2。

---

## 5. 发现的问题

### Finding 1：Phase 2 前置证据仍不足

严重级别：High

证据：

- repaired LTR `ndcg@30 = 0.525077`；
- qlib top50 `ndcg@30 = 0.537373`；
- repaired LTR `top30_future_excess_rank_10d = 0.523047`；
- qlib top50 `top30_future_excess_rank_10d = 0.526614`；
- `phase1b_gate_summary.json` 给出 `recommended_gate = phase1b_ltr_needs_repair`。

结论：

不能进入 Phase 2 regime-aware gating。

### Finding 2：继续修 LTR 已经成为用户 tradeoff，不应由执行者或审查者自动决定

严重级别：High

证据：

- Phase1 最小 LTR 未过 gate；
- Phase1B 多组 label window、feature ablation、轻量参数选择后仍未过 gate；
- 部分指标改善存在，但核心 TopK / NDCG 仍不成立；
- 主文档要求遇到证据不足或需要 tradeoff 判断必须停下回到用户确认。

结论：

下一步不能自动给执行者继续扩大搜索、放宽 gate、进入 regime、或停止整条主线。必须由用户确认方向。

### Finding 3：LTR 稳定性改善不能替代 TopK 质量改善

严重级别：Medium

证据：

- repaired LTR 的 day-to-day Jaccard stability 高于 qlib；
- 但 repaired LTR 与 qlib 的 TopK overlap 很低，且没有带来更好的 independent_test TopK 质量；
- 主文档当前 Stage 2 要解决的是 rerank 是否更合理，不是单独追求名单稳定。

结论：

不能把稳定性改善解释为 LTR 已经成立。稳定性可以作为后续 turnover layer 的参考，但不能作为进入 Phase2 的替代证据。

---

## 6. 本轮 Gate

审查 gate：

```text
phase1b_pause_for_user_decision
```

原因：

```text
Phase1B 未偏离主线，但 repaired LTR 未满足进入 Phase2 的 TopK / NDCG 证据门槛；继续修复、停止 LTR 主线或放宽 gate 都属于用户 tradeoff。
```

---

## 7. 需要用户确认的下一步

请用户在以下方向中选择一个，再给执行者下一轮工作文档。

### 选项 A：继续 Phase1C，但严格限制为最后一轮 LTR 修复

含义：

- 不进入 Phase2；
- 不新增数据源；
- 不新增白名单外特征；
- 不引入 `trend_score`；
- 不做 frontend / API / provider / monitor / trading；
- 只允许在 Stage 2 内做最后一轮更保守的 LTR 修复。

可允许的最后修复范围：

- 只使用 validation 选择；
- 尝试更贴近头部排序的 label / objective / group weighting；
- 尝试 qlib-preserving rerank，例如只在 qlib Top50 内重排，避免大幅替换头部名单；
- 明确设置若 Phase1C 仍不过 gate，则停止 LTR 主线，不再继续修。

### 选项 B：停止 LTR reranker 主线

含义：

- 接受当前证据：qlib baseline 在 TopK 头部质量上仍更稳；
- 不再继续 LTR 修复；
- 不进入 regime / turnover；
- 本主线以 `stop_ltr_mainline_insufficient_evidence` 关闭。

### 选项 C：用户明确放宽 gate

含义：

- 用户明确接受 rank IC 改善但 TopK / NDCG 不改善的风险；
- 允许进入 Phase2 regime-aware gating；
- 审查者不建议该选项，因为它会弱化主文档“TopK + baseline 对照”的证据要求。

---

## 8. 当前不给执行者的新工作指令

在用户确认前，不应给执行者继续执行文档。

原因：

- 进入 Phase2：证据不足；
- 继续 Phase1C：需要确认是否值得再投入一轮；
- 停止主线：需要用户确认；
- 放宽 gate：必须由用户明确承担 tradeoff。

