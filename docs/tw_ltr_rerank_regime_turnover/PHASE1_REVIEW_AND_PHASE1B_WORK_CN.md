# Phase 1 审查意见 + Phase 1B 下一轮工作文档

生成时间：2026-06-13

审查者角色：本轮严格以 `docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md` 为唯一主线依据。

审查入口：

- `docs/tw_ltr_rerank_regime_turnover/PHASE1_LTR_BASELINE_EXECUTION_REPORT_CN.md`
- `scripts/build_tw_ltr_phase1_samples.py`
- `scripts/train_tw_ltr_phase1_lambdamart.py`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/`

---

## 1. 审查结论

本轮 Phase 1 可以确认为：执行者完成了主线允许范围内的最小 LTR baseline 工程闭环。

但本轮不能进入 Phase 2 regime-aware gating。

原因不是工程范围偏离，而是证据不满足推进条件：独立测试集上，LTR 只提升了 rank IC，但没有在主线要求关注的 TopK / NDCG 层面对 qlib baseline 形成有效改善；执行者产物自身 gate 也给出 `phase1_ltr_baseline_needs_repair`。

因此下一轮应进入 Phase 1B：LTR baseline 诊断与修复，而不是进入 regime、turnover、frontend 或 API。

---

## 2. 主线边界审查

### 2.1 未发现主线外扩

本轮仍处于 Stage 2：LTR reranker。

已核对：

- 未进入 Stage 3 regime-aware gating 的动作实现；
- 未进入 Stage 4 turnover-controlled portfolio layer；
- 未进入 frontend explanation；
- 未新增 provider / 联网 / token / accepted latest 切换；
- 未改前端、后端 API、monitor、broker、quick-trade、orders；
- 未输出买入、卖出、持有、仓位、收益承诺、上涨概率或胜率语义。

### 2.2 模型类型合规

本轮使用：

- `LightGBM LGBMRanker`
- `objective="lambdarank"`
- GBDT / LambdaMART 风格 LTR

符合主文档第一版仅允许 LambdaMART 或同等级树模型 LTR 的要求。

未发现 Transformer、deep reranker、end-to-end decision model 或黑盒 decision-focused 主模型。

### 2.3 输入特征边界合规

产物 `phase1_input_feature_list.json` 显示 input features 共 34 个，均在 Phase 0 白名单内。

已确认：

- `trend_score` 默认排除；
- 禁止特征命中为 `[]`；
- label / input overlap 为 `[]`；
- audit / input overlap 为 `[]`；
- grouping / input overlap 为 `[]`。

禁止特征包括：

- `institutional_net_buy`
- `margin_balance`
- `short_balance`
- `monthly_revenue_yoy_mom`
- `valuation_PER_PBR`

均未进入 input features。

---

## 3. 可复现核验

已复现执行：

```bash
python scripts/build_tw_ltr_phase1_samples.py
python scripts/train_tw_ltr_phase1_lambdamart.py
```

复现结果：

- 样本构建成功；
- 完整样本行数：152249；
- 完整样本日期数：1043；
- split counts：train 90301，validation 30877，independent_test 31071；
- LTR group size min / median / max：110 / 148.0 / 150；
- 训练脚本输出 gate：`phase1_ltr_baseline_needs_repair`。

安全边界关键词扫描只命中文档和脚本中的禁止声明、排序字段或内部变量，没有发现实际危险 API、provider publish/refresh、accepted latest switching、monitor 写入、broker、quick-trade、orders 或 target position 路径。

---

## 4. 关键结果审查

独立测试集核心对照：

| method | rank_ic_10d | ndcg@10 | ndcg@30 | ndcg@50 |
|---|---:|---:|---:|---:|
| ltr_lambdamart | 0.054690 | 0.514995 | 0.517182 | 0.560571 |
| rank_rotate_top50 / qlib | 0.026642 | 0.539438 | 0.532858 | 0.561234 |
| rank_rotate_top50_adaptive_score | 0.027657 | 0.541562 | 0.533366 | 0.561163 |
| confirmed_exit | 0.026509 | 0.539524 | 0.532913 | 0.561325 |

审查判断：

- LTR 的 rank IC 高于 qlib baseline，这是正向信号；
- 但 LTR 的 `ndcg@10`、`ndcg@30`、`ndcg@50` 均低于 qlib / adaptive / confirmed_exit 代理 baseline；
- independent_test TopK 指标中，LTR Top10 / Top30 的未来相对 rank 与未来超额收益也低于 qlib / adaptive baseline；
- 主文档明确要求不能只给单一整体收益率，且要同时看 rank quality、TopK、baseline 对照、年度 / 分段结果；
- 因此不能用 rank IC 单点改善来证明 LTR baseline 已成立。

---

## 5. 发现的问题

### Finding 1：不能进入 Phase 2

严重级别：High

证据：

- `phase1_gate_summary.json` 给出 `recommended_gate = phase1_ltr_baseline_needs_repair`；
- 独立测试集 LTR `ndcg@30 = 0.517182`，低于 qlib baseline `0.532858`；
- 独立测试集 LTR `ndcg@10 = 0.514995`，低于 qlib baseline `0.539438`；
- 独立测试集 LTR Top10 / Top30 的未来相对表现低于 qlib / adaptive baseline。

结论：

Phase1 工程合格，但研究证据不足。不得推进到 regime gating。

### Finding 2：当前 baseline 对照可用于 Phase1 rank/TopK 审查，但不能被解释为组合 replay 结论

严重级别：Medium

证据：

- 执行报告说明本轮只做 rank quality / TopK 层面对照；
- `rank_rotate_top50_adaptive_score` 与 `confirmed_exit_baseline` 是 Phase1 内部代理分数；
- 还没有真实组合净值、换手、动作次数、成本口径。

结论：

这不是阻塞 Phase1B 的问题，但执行者下一轮必须继续避免把这些代理 baseline 包装成组合收益、买卖建议或可执行仓位结论。

### Finding 3：LTR 在 validation 与 independent_test 的 TopK 表现方向不一致，需要诊断稳定性

严重级别：Medium

证据：

- validation 上 LTR 的 NDCG 优于 qlib；
- independent_test 上 LTR 的 NDCG 与 TopK 弱于 qlib；
- 年度 / regime segment 中部分细分样本日期数较少，例如 independent_test `risk_off` 只有 7 个日期，不能过度解释。

结论：

下一轮应优先诊断是否过拟合、标签定义不贴合 TopK、模型参数不稳、样本窗口或分段导致泛化下降。

---

## 6. Phase 1B 下一轮工作文档

### 6.1 下一轮目标

只做一件事：诊断并尝试修复 Phase1 LTR baseline 为什么 rank IC 改善但 TopK / NDCG 未打过 qlib baseline。

下一轮不得进入 Phase2 regime gating。

### 6.2 允许做的工作

执行者可以在 Stage 2 LTR reranker 范围内做以下工作：

- 读取并复用 Phase1 样本；
- 检查 label 定义是否与 TopK / NDCG 目标一致；
- 对 `ltr_relevance_label` 做小范围替代实验，例如 5d / 10d / 20d future excess rank label 对照；
- 做 feature group ablation：qlib-only、qlib+technical、qlib+liquidity、qlib+market、all whitelist；
- 做轻量参数搜索，但只能在 train / validation 上选择模型；
- 检查 LTR score 与 qlib score 的相关性、TopK 重叠率、替换名单稳定性；
- 检查 validation 到 independent_test 的退化来源；
- 产出清晰的诊断表、指标表和推荐 gate。

### 6.3 禁止事项

下一轮禁止：

- 新增白名单外特征；
- 引入 `trend_score`，除非先证明现有稳定定义与 PIT 安全，且单独列证据；
- 引入 forbidden features；
- 联网、拉 provider、publish / refresh provider、切换 accepted latest；
- 改 frontend、后端 API、monitor、数据库；
- 做 regime gating 动作实现；
- 做 turnover portfolio layer；
- 做 broker、quick-trade、orders、target position / target weight；
- 输出买入、卖出、持有、仓位、收益承诺、上涨概率、胜率语义；
- 为了通过 gate 直接在 independent_test 上调参。

### 6.4 必须输出的产物

建议新增目录：

`data_tw/experiments/ltr_rerank_regime_turnover/phase1b_ltr_repair/`

必须输出：

- `phase1b_diagnosis_summary.json`
- `phase1b_feature_ablation_metrics.csv`
- `phase1b_label_window_metrics.csv`
- `phase1b_validation_model_selection.csv`
- `phase1b_independent_test_comparison.csv`
- `phase1b_topk_overlap_and_stability.csv`
- `phase1b_gate_summary.json`
- `docs/tw_ltr_rerank_regime_turnover/PHASE1B_LTR_REPAIR_EXECUTION_REPORT_CN.md`

如新增脚本，建议命名：

- `scripts/diagnose_tw_ltr_phase1b_repair.py`

### 6.5 指标要求

必须同时报告：

- rank IC；
- NDCG@10 / @30 / @50；
- Top10 / Top30 / Top50 的 future excess rank；
- Top10 / Top30 / Top50 的 mean relevance label；
- baseline vs repaired LTR；
- validation 与 independent_test 分开报告；
- 分年度 / 分 regime segment 只作为诊断，不得作为单独推进依据。

### 6.6 Gate 规则

执行者必须在 `phase1b_gate_summary.json` 中给出以下三类之一：

1. `request_phase2_regime_gating_work`

   仅当 repaired LTR 在 independent_test 上同时满足：

   - rank IC 高于 qlib baseline；
   - NDCG@30 不低于 qlib baseline；
   - Top30 的 future excess rank 不低于 qlib baseline；
   - 结果不是只靠单一年份、单一 regime segment 或单一指标成立；
   - 没有越界特征、越权数据源或安全语义问题。

2. `phase1b_ltr_needs_repair`

   当诊断有明确修复方向，但证据仍不足以进入 Phase2。

3. `stop_ltr_mainline_insufficient_evidence`

   当多组合理修复仍无法打过 qlib baseline，或 LTR 只在 rank IC 上改善但 TopK 继续退化。

如出现是否放宽 gate、是否接受 rank IC 单点改善、是否换目标函数、是否新增白名单外数据等 tradeoff，必须停止并回到用户确认。

---

## 7. 给执行者的明确指令

请执行 Phase 1B，不要进入 Phase 2。

本轮要回答的问题是：

> 为什么 LambdaMART LTR 在 independent_test 上 rank IC 提升，但 TopK / NDCG 输给 qlib baseline？是否可以在不越界、不新增数据源、不碰 independent_test 调参的前提下修复？

完成后提交：

- `docs/tw_ltr_rerank_regime_turnover/PHASE1B_LTR_REPAIR_EXECUTION_REPORT_CN.md`
- 上述 Phase1B 诊断与 gate 产物

