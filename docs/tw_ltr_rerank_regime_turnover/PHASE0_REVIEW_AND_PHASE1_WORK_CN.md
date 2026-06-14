# Phase 0 口径冻结审查结论与 Phase 1 LTR Baseline 步骤文档

审查日期：2026-06-13

唯一主线依据：

- `docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

审查入口：

- `docs/tw_ltr_rerank_regime_turnover/PHASE0_EXECUTION_REPORT_CN.md`

审查产物：

- `scripts/audit_tw_ltr_phase0_contract.py`
- `docs/tw_ltr_rerank_regime_turnover/phase0_sample_feature_label_baseline_contract.md`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase0_feature_whitelist_inventory.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase0_forbidden_feature_audit.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase0_baseline_inventory.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase0_gate_summary.json`

## 1. 本轮审核结论

Phase 0 主线范围通过。

允许进入 Phase 1，但必须带约束进入：

- `trend_score` 在 Phase 0 中标记为 `defer_pending_existing_stable_definition`，Phase 1 默认不得纳入 input features。
- 只有执行者能证明仓库已有稳定、只读、PIT-safe 的 `trend_score` 口径，且不引入新数据源、不联网、不 provider、不 accepted latest switching，才允许把 `trend_score` 纳入 Phase 1 样本。
- 若无法证明，Phase 1 必须排除 `trend_score`。

Gate 结论：

- 接受 `recommended_gate=request_phase1_ltr_baseline_work`。
- 不允许跳过 Phase 1 样本构建与最小 LTR baseline，直接进入 regime gating、turnover layer、前端或 API。

## 2. 主线一致性审查

通过项：

- Phase 0 只做 proposal / inventory / audit。
- 未训练 LTR。
- 未训练任何模型。
- 未运行 replay。
- 未改前端。
- 未改 API。
- 未写数据库。
- 未联网。
- 未使用 token。
- 未新增数据源。
- 未 provider refresh/publish。
- 未 accepted latest switching。
- 未 monitor 写入或扫描。
- 未接 broker、quick-trade、orders。
- 未输出买卖、仓位、收益率、上涨概率或胜率语义。

未发现执行者偏离主线或新增分支。

## 3. 产物审查

### 3.1 白名单特征

`phase0_feature_whitelist_inventory.csv` 共 35 行，分组如下：

- qlib：12 个。
- technical：11 个。
- liquidity：5 个。
- market：7 个。

与主文档白名单一致。

审查复核：

- 非白名单字段：0。
- 缺失或不在白名单字段：0。
- 禁止字段进入 input：0。

注意项：

- `trend_score` 被标记为 `defer_pending_existing_stable_definition`，但 `phase1_status` 仍写成 `allowed_for_phase1_mapping`。这不是 Phase 0 阻塞项，因为合同正文已写明“若 Phase 1 找不到稳定定义，应继续排除”。但 Phase 1 必须严格执行这个条件，不得把它默认作为已可用特征。

### 3.2 禁止特征审计

`phase0_forbidden_feature_audit.csv` 覆盖主文档禁止特征：

- `institutional_net_buy`
- `margin_balance`
- `short_balance`
- `monthly_revenue_yoy_mom`
- `valuation_PER_PBR`
- `any_field_without_available_at_or_announcement_date`

审查判断：

- 禁止特征只作为禁止/审计文本出现。
- `found_in_phase0_input_features=false`。
- 不构成输入特征污染。

### 3.3 Baseline 对照

`phase0_baseline_inventory.csv` 覆盖主文档要求的 4 个 baseline：

- `rank_rotate_top30`
- `rank_rotate_top50`
- `rank_rotate_top50_adaptive_score`
- `confirmed_exit`

审查判断：

- Phase 0 只冻结对照名称与未来指标要求。
- 报告明确旧 replay 不能作为 LTR 主线收益证据。
- 符合主文档边界。

### 3.4 标签与切分

合同中的标签候选保持排序语义：

- `future_excess_return_rank_5d`
- `future_excess_return_rank_10d`
- `future_excess_return_rank_20d`
- `topk_forward_bucket`

审查判断：

- Phase 0 未训练，不构成点预测回归偏离。
- 已明确 input / label / audit / grouping 隔离。
- 已明确 train / validation / independent test / regime segment 原则。

Phase 1 必须将这些原则落到真实样本列级 schema，不能只延续文字说明。

## 4. 复现验证

复跑：

- `python scripts/audit_tw_ltr_phase0_contract.py`

结果：

- 成功复现产物。
- 输出 `recommended_gate=request_phase1_ltr_baseline_work`。

结构化校验：

- 白名单行数：35。
- baseline：4 个。
- 禁止特征输入命中：0。
- `trend_score` deferred 但 phase1_status 为 allowed，已记录为 Phase 1 必须修正/处理的约束。

## 5. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：`trend_score` 状态表述需在 Phase 1 收紧，不影响 Phase 0 通过。

### Network Audit

未联网，未使用 token，未新增数据源。

### Console Audit

未发现 provider refresh/publish、accepted latest switching、monitor config save、monitor scan、alerts write、broker、quick-trade、orders、target position 或 target weight 证据。

### Text / Agent Semantics

买卖、仓位、收益率、上涨概率、胜率等词只出现在禁止事项或风险说明中，不是用户可执行建议。

### Verdict

只读研究边界通过。

## 6. 必须修复项

Phase 0 无必须修复项。

Phase 1 必须处理：

- `trend_score` 默认排除，除非证明稳定既有口径。
- 真正构建样本后，必须生成列级 schema，证明 input / label / audit / grouping 隔离。
- 真正构建样本后，必须复核 train / validation / independent test 覆盖是否成立。

## 7. 可暂缓项

继续暂缓：

- regime gating。
- turnover-controlled portfolio layer。
- 前端解释接入。
- API。
- 真实 replay。
- provider。
- accepted latest。
- monitor。
- 新数据源。
- 交易路径。

## 8. 是否需要用户确认

当前不需要用户确认。

理由：

- Phase 0 未触发主文档外 tradeoff。
- 未使用新数据源。
- 未联网或 token。
- 未训练模型。
- 未改前端/API。
- 未触发 provider / monitor / trading。
- `trend_score` 问题可通过 Phase 1 默认排除或证明稳定口径解决，不需要用户现在做 tradeoff。

如果 Phase 1 发现必须依赖 `trend_score`、新数据源、PIT 不确定字段，或样本覆盖不足以做 train/validation/test，则必须停止并回到用户确认。

## 9. 给执行者的下一轮步骤文档：Phase 1 最小 LTR Baseline

### 9.1 本轮目标

构建最小可用 LTR baseline：

1. 基于 Phase 0 合同构建真实样本。
2. 生成列级 schema，严格隔离 input / label / audit / grouping。
3. 使用 LambdaMART 或同等级树模型 LTR 做最小训练。
4. 报告 rank quality、TopK 指标、baseline vs rerank 对照、分年度 / 分阶段结果。

Phase 1 只允许做 LTR baseline 样本、训练、评估和报告。

### 9.2 允许改动范围

允许新增脚本：

- `scripts/build_tw_ltr_phase1_samples.py`
- `scripts/train_tw_ltr_phase1_lambdamart.py`

允许新增产物目录：

- `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/`

允许新增文档：

- `docs/tw_ltr_rerank_regime_turnover/PHASE1_LTR_BASELINE_EXECUTION_REPORT_CN.md`

允许产物示例：

- `phase1_sample_schema.json`
- `phase1_sample_coverage.json`
- `phase1_input_feature_list.json`
- `phase1_label_audit_summary.json`
- `phase1_split_summary.json`
- `phase1_ltr_metrics.csv`
- `phase1_topk_metrics.csv`
- `phase1_year_segment_metrics.csv`
- `phase1_baseline_comparison.csv`
- `phase1_gate_summary.json`

### 9.3 是否允许改接口 / 前端 / 训练口径

本轮允许：

- 构建样本。
- 训练最小 LTR baseline。
- 评估。
- 写报告。

本轮不允许：

- 改后端 API。
- 改前端。
- 接 provider。
- 接 accepted latest。
- 接 monitor。
- 做 turnover portfolio layer。
- 做 regime gating 动作实现。

训练口径限制：

- 第一版仅允许 LambdaMART 或同等级树模型 LTR。
- 不允许 Transformer reranker。
- 不允许复杂 end-to-end deep ranking。
- 不允许黑盒 decision-focused 主模型。
- 不允许将标签做成单纯未来收益点预测回归。

### 9.4 输入特征约束

Phase 1 input features 只能来自 Phase 0 白名单。

默认排除：

- `trend_score`

只有满足以下条件才可纳入：

- 找到仓库已有稳定定义。
- 定义只使用当前日及历史 OHLCV。
- 不使用未来数据。
- 不使用新数据源。
- 不联网。
- 不 provider refresh/publish。
- 不 accepted latest switching。
- 在执行报告中列出证明路径与函数/文件位置。

禁止输入：

- `institutional_net_buy`
- `margin_balance`
- `short_balance`
- `monthly_revenue_yoy_mom`
- `valuation_PER_PBR`
- 任意没有 `available_at` / `announcement_date` 的 PIT 不安全字段。
- `future_return_*`
- `future_excess_return_*`
- `label_*`
- `topk_forward_bucket`
- `audit_*`
- 成本、净值、动作次数、回撤等审计列。
- `date`、`instrument`、`year`、`regime_segment` 作为普通模型输入。

### 9.5 样本构建要求

必须：

- 同一天横截面作为 LTR group。
- 用 qlib prediction / top30 / top50、OHLCV、TWII 现有本地只读数据派生。
- 对每个 input feature 写明 derivation rule。
- 对每个 label 写明 future window。
- 对每个 row 标记是否 label complete。
- 对缺失 feature 做清晰处理，不得静默填入未来信息。

如果实际覆盖不足以形成 train / validation / independent test，必须停止并报告。

### 9.6 数据切分要求

必须至少包含：

- train。
- validation。
- independent test。
- regime segment / 差市况与非差市况分段审计。

切分必须时间有序，不得随机打散同一天横截面。

### 9.7 评估要求

至少报告：

- rank quality 指标。
- TopK 表现指标。
- baseline vs rerank 对照。
- 分年度 / 分阶段结果。

不得只报告单一整体收益率。

不得宣称收益承诺、胜率承诺、上涨概率或买卖建议。

### 9.8 Baseline 对照要求

至少对照：

- `rank_rotate_top30`
- `rank_rotate_top50`
- `rank_rotate_top50_adaptive_score`
- `confirmed_exit`

Phase 1 可做 rank quality / TopK 层面对照。若需要真实组合回放才能比较某些指标，应明确标记为 Phase 3/4 后续，不得伪造。

### 9.9 必做验证

必须执行并报告：

- input feature 白名单校验。
- forbidden feature 校验。
- label / input / audit / grouping 隔离校验。
- future leakage 检查。
- split 覆盖检查。
- LTR group 完整性检查。
- baseline 对照完整性检查。
- 模型类型检查，确认不是 Transformer / deep reranker / decision-focused 主模型。

### 9.10 必交付报告

执行报告必须固定包含：

1. 本轮目标。
2. 实际完成内容。
3. 改动文件清单。
4. 新增产物清单。
5. 样本覆盖与切分。
6. input / label / audit / grouping schema。
7. 模型类型与训练口径。
8. 评估指标与结果。
9. baseline 对照。
10. 是否达到本轮门槛。
11. 风险 / 异常 / 未解决问题。
12. 需要审查者重点检查的点。

### 9.11 验收门槛

允许进入 Phase 2 regime gating 的最低条件：

- 样本构建成功。
- input features 全部来自白名单。
- `trend_score` 已排除或稳定口径证据充分。
- 禁止特征命中为 0。
- label / input / audit / grouping 隔离通过。
- train / validation / independent test 成立。
- LTR 训练成功，模型类型符合主文档。
- 至少报告 rank quality、TopK、baseline 对照、年度/分段结果。
- 不能只靠单一整体收益率。
- 无前端/API/provider/monitor/trading 越权。

### 9.12 若失败如何收尾

若 Phase 1 发现：

- 样本覆盖不足。
- 标签泄漏风险无法排除。
- 白名单字段无法构建。
- 必须依赖 `trend_score` 但无稳定口径。
- LTR 结果不优于 qlib baseline 或只在单一偶然窗口改善。
- 需要新数据源、联网、provider、accepted latest 或 PIT 不确定字段。

必须停止并报告：

- `phase1_needs_repair`
- 或 `phase1_needs_user_decision`
- 或 `stop_ltr_mainline_insufficient_evidence`

不得强行进入 regime / turnover / frontend。

### 9.13 Phase 1 Gate

Phase 1 完成后推荐 gate 只能是：

- `request_phase2_regime_gating_work`
- `phase1_ltr_baseline_needs_repair`
- `phase1_needs_user_decision`
- `stop_ltr_mainline_insufficient_evidence`
- `stop_ltr_mainline_scope_invalid`

完成后等待审查者审核，不得自动进入 Phase 2。
