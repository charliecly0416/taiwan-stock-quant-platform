# LTR 重排序 + Regime + Turnover 主线审查意见与 Phase 0 步骤文档

审查日期：2026-06-13

唯一主线依据：

- `docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

本轮审查对象：

- 当前工作区代码、文档、脚本与产物。
- 本轮未发现独立的 LTR 主线执行报告。

## 1. 审查结论

当前不能放行任何 LTR / regime / turnover 实现结果。

原因：

- 未发现执行者针对本主线提交的执行报告。
- 未发现命名明确的 LTR 主线产物目录或阶段报告。
- 当前工作区存在大量旧主线、人工复盘模块、正交规则、decision model 和历史 replay 产物，不能自动视为本主线证据。
- 主文档要求执行者每轮必须提交固定格式执行报告；当前证据不满足审查入口要求。

因此本轮判断为：

- `current_round_review_passed=false`
- `evidence_sufficient=false`
- `implementation_accepted=false`
- `must_not_advance_to_training=true`
- `must_not_advance_to_frontend=true`

## 2. 是否偏离主线或新增分支

由于缺少本主线执行报告，不能判断执行者本轮是否完成了指定目标。

但从现有工作区观察：

- 没有可确认的本主线 Phase 0 执行报告。
- 没有可确认的 LTR 样本/特征/标签/baseline 口径冻结产物。
- 旧 `decision_model`、`orthogonal`、`manual_review_explanation`、`rank-tech-cross` 等产物不能并入本主线。

审查判断：

- 不能把旧产物自动迁移为本主线结论。
- 不能从旧 Entry Model 或旧 orthogonal 规则继续推进。
- 不能跳过样本、特征、标签、baseline 对照冻结，直接进入 LTR 训练、regime gating、turnover layer 或前端包装。

## 3. 主线边界复核

本主线唯一允许的最终方向是：

```text
qlib baseline
-> LTR reranker
-> regime-aware gating
-> turnover-controlled portfolio layer
-> readonly replay + frontend explanation
```

但推荐推进顺序必须先从：

```text
冻结样本 / 特征 / 标签 / baseline 对照口径
```

开始。

当前不得直接做：

- LambdaMART 训练。
- 复杂深度 reranker。
- regime action gate。
- turnover portfolio layer。
- 前端解释接入。
- API 接入。
- provider refresh/publish。
- accepted latest switching。
- monitor 写入或扫描。
- 真实交易或订单路径。

## 4. 安全边界审查

本轮没有发现新的 LTR 主线执行代码可供安全审查。

但下一轮必须继续保持：

- readonly / research-only。
- 不接 broker。
- 不接 quick-trade。
- 不写 orders。
- 不输出 target position / target weight。
- 不输出 expected return / upside probability / win rate。
- 不触发 provider refresh/publish。
- 不切换 accepted latest。
- 不触发 monitor config save / monitor scan / alerts write。

允许的语义仅限：

- 研究排序。
- 只读回放。
- 历史模拟。
- baseline 对照。
- 口径冻结。

## 5. 必须停止推进的原因

按主文档要求，若出现证据不足必须停止推进并回到用户确认。

当前停止点：

- 缺少执行报告。
- 缺少本主线阶段产物。
- 缺少本轮目标与验收门槛。

因此本文件只允许给出下一轮 Phase 0 步骤文档；不能审查通过任何实现结果。

## 6. 给执行者的下一轮步骤文档：Phase 0 口径冻结

### 6.1 本轮目标

冻结 LTR 主线第一轮基础口径：

1. 样本范围。
2. 特征白名单映射。
3. 禁止特征扫描。
4. 标签定义候选。
5. baseline 对照口径。
6. 数据切分口径。
7. 后续 LTR 训练前必须满足的验收门槛。

Phase 0 只做 proposal / inventory / audit，不训练模型、不做回放、不改前端、不改 API。

### 6.2 允许改动范围

允许新增：

- `docs/tw_ltr_rerank_regime_turnover/PHASE0_EXECUTION_REPORT_CN.md`
- `docs/tw_ltr_rerank_regime_turnover/phase0_sample_feature_label_baseline_contract.md`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase0_feature_whitelist_inventory.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase0_forbidden_feature_audit.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase0_baseline_inventory.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase0_gate_summary.json`

允许新增只读审计脚本：

- `scripts/audit_tw_ltr_phase0_contract.py`

脚本只能读取现有本地文件并生成上述 Phase 0 产物。

### 6.3 本轮禁止事项

禁止：

- 训练 LTR。
- 训练任何模型。
- 新增 Transformer / deep reranker。
- 新增 end-to-end decision model。
- 做 regime gating 实现。
- 做 turnover portfolio layer 实现。
- 做前端。
- 做 API。
- 写数据库。
- 联网。
- 使用 token。
- 新增数据源。
- provider refresh/publish。
- accepted latest switching。
- monitor config save。
- monitor scan。
- alerts write。
- broker、quick-trade、orders。
- target position / target weight。
- expected return / upside probability / win rate。
- 输出买入/卖出/持有建议。

禁止把以下特征纳入输入：

- `institutional_net_buy`
- `margin_balance`
- `short_balance`
- `monthly_revenue_yoy_mom`
- `valuation_PER_PBR`
- 任意没有 `available_at` / `announcement_date` 的 PIT 不安全字段。

### 6.4 Phase 0 必须盘点的白名单

必须按主文档白名单逐项盘点可用性。

qlib 层：

- `qlib_score_raw`
- `qlib_rank`
- `qlib_score_percentile_by_date`
- `qlib_score_zscore_by_date`
- `rank_change_1d`
- `rank_change_3d`
- `rank_change_5d`
- `top10_flag`
- `top30_flag`
- `top50_flag`
- `top30_streak`
- `top50_streak`

技术趋势层：

- `MA5`
- `MA10`
- `MA20`
- `MA60`
- `RSI14`
- `MACD`
- `Bollinger_position`
- `ret20`
- `volatility20`
- `volume_ratio20`
- `trend_score`

流动性层：

- `avg_trading_value_20d`
- `volume_stability20`
- `missing_rate20`
- `suspension_proxy`
- `slippage_proxy`

市场状态层：

- `TWII_ret20`
- `TWII_ret60`
- `TWII_close_vs_MA60`
- `TWII_close_vs_MA120`
- `market_volatility20`
- `market_drawdown60`
- `market_breadth20`

### 6.5 标签与切分要求

Phase 0 只能提出标签候选与审计口径，不得训练。

必须说明：

- 标签如何服务横截面排序，而不是点预测回归。
- 标签和 TopK / rank quality / replay 之间的关系。
- 如何避免 future leakage。
- 哪些列是 label / audit / grouping，哪些才是 input feature。

切分至少要规划：

- 训练期。
- 验证期。
- 独立测试期。
- 差市况 / 非差市况分段。

### 6.6 Baseline 对照要求

必须盘点并冻结至少以下 baseline：

- `rank_rotate_top30`
- `rank_rotate_top50`
- `rank_rotate_top50_adaptive_score`
- `confirmed_exit`

Phase 0 只冻结口径，不重新解释旧结果为本主线增益。

### 6.7 必做验证

执行者必须运行或产出：

- 白名单覆盖率检查。
- 禁止特征扫描。
- label / input / audit / grouping 字段隔离检查。
- baseline 对照清单检查。
- PIT 安全说明。

如果任何关键输入不可用，必须明确：

- 缺失字段。
- 缺失原因。
- 是否可由现有只读本地数据派生。
- 是否需要用户 tradeoff。

若需要新数据源、联网、token、provider、accepted latest 或 PIT 不确定字段，必须停止并回报。

### 6.8 必交付产物

必须交付：

- `docs/tw_ltr_rerank_regime_turnover/PHASE0_EXECUTION_REPORT_CN.md`
- `docs/tw_ltr_rerank_regime_turnover/phase0_sample_feature_label_baseline_contract.md`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase0_feature_whitelist_inventory.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase0_forbidden_feature_audit.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase0_baseline_inventory.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase0_gate_summary.json`

执行报告必须包含：

1. 本轮目标。
2. 实际完成内容。
3. 改动文件清单。
4. 新增产物清单。
5. 验证内容与结果。
6. 是否达到本轮门槛。
7. 风险 / 异常 / 未解决问题。
8. 需要审查者重点检查的点。

### 6.9 验收门槛

允许进入 Phase 1 LTR baseline 的最低条件：

- 样本范围清楚。
- input features 只来自主文档白名单。
- 禁止特征扫描为 0。
- 标签列、未来收益列、audit/grouping 列没有进入 input features。
- baseline 对照口径完整覆盖四个指定 baseline。
- 数据切分口径包含 train / validation / independent test / regime segment。
- 没有新数据源、联网、provider、accepted latest、monitor、交易路径。

### 6.10 若失败如何收尾

若 Phase 0 发现：

- 关键字段不可用。
- 禁止字段混入。
- baseline 对照不可复现。
- 标签口径无法避免泄漏。
- 需要用户在样本范围、标签周期、数据源或 baseline 对照上做 tradeoff。

执行者必须停止，报告 `phase0_needs_user_decision=true`，不得进入训练。

### 6.11 Phase 0 Gate

Phase 0 完成后推荐 gate 只能是：

- `request_phase1_ltr_baseline_work`
- `phase0_contract_needs_repair`
- `phase0_needs_user_decision`
- `stop_ltr_mainline_scope_invalid`

完成后等待审查者审核，不得自动进入 Phase 1。
