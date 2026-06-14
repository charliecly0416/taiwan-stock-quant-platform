# Decision Meta Model Phase 1B 复审意见与 Phase 2 下一步工作文档

## 0. 审查入口与依据

审查入口：

- `docs/tw_decision_model/PHASE1_EXECUTION_REPORT_CN.md`

审查依据：

- `prompt_investigate.md`
- `docs/TW_STOCK_DECISION_META_MODEL_DESIGN_CN.md`
- `docs/tw_decision_model/PHASE1_REVIEW_AND_PHASE1B_WORK_CN.md`
- `scripts/build_tw_decision_phase1_samples.py`
- `data_tw/experiments/decision_model/phase1_schema.json`
- `data_tw/experiments/decision_model/phase1_leakage_audit_report.md`
- `data_tw/experiments/decision_model/phase1_label_quality_report.md`
- `data_tw/experiments/decision_model/phase1_date_coverage_report.csv`
- `data_tw/experiments/decision_model/phase1_exclusion_report.csv`

本次同时按台股 research-only 安全边界进行审查。

## 1. 本步审核结论

结论：通过，允许进入 Phase 2。

Phase 1B 已修复上次审查指出的 schema 问题：

- `market_regime` 已移出 `input_features`，进入 `grouping_columns`。
- `candidate_reason_flags` 已移出 `input_features`，进入 `audit_only_columns`。
- 新增日期覆盖报告，明确 2024 缺口。
- leakage audit 已补充 schema policy checks。

允许执行者进入 Phase 2，但 Phase 2 只能训练 Entry Model v1 研究模型。不得训练 Exit Risk Model，不得接组合回放，不得接前端，不得生成真实交易建议。

## 2. 主线一致性审查

### 2.1 修复项已完成

执行报告显示：

- 未训练模型，见 `PHASE1_EXECUTION_REPORT_CN.md:8`。
- 未触碰只读边界，见 `PHASE1_EXECUTION_REPORT_CN.md:9`。
- `market_regime` 移出 `input_features`，见 `PHASE1_EXECUTION_REPORT_CN.md:15`。
- `candidate_reason_flags` 移出 `input_features`，见 `PHASE1_EXECUTION_REPORT_CN.md:16`。
- 日期覆盖报告已生成，见 `PHASE1_EXECUTION_REPORT_CN.md:18`。
- leakage audit 已更新，见 `PHASE1_EXECUTION_REPORT_CN.md:19`。

### 2.2 Schema 复核通过

schema 复核结果：

- `input_features` 现在不包含 `market_regime`，见 `phase1_schema.json:4` 至 `phase1_schema.json:53`。
- `candidate_reason_flags` 位于 `audit_only_columns`，见 `phase1_schema.json:70` 至 `phase1_schema.json:84`。
- `market_regime` 位于 `grouping_columns`，见 `phase1_schema.json:85` 至 `phase1_schema.json:87`。
- `future_return_label_base` 仍在 `excluded_columns`，见 `phase1_schema.json:88` 至 `phase1_schema.json:90`。
- safety metadata 明确 research-only，见 `phase1_schema.json:126` 至 `phase1_schema.json:130`。

自动一致性检查结果：

```text
market_regime in input False
market_regime grouping True
candidate_reason in input False
candidate_reason audit True
future inputs []
label overlap []
audit overlap []
finmind deferred present in input []
```

### 2.3 Leakage audit 复核通过

`phase1_leakage_audit_report.md` 已补充：

- future-prefixed columns 不在输入特征，见 `phase1_leakage_audit_report.md:7`。
- `future_return_label_base` 不在输入特征，见 `phase1_leakage_audit_report.md:8`。
- TWII 缺口进入 exclusion report，见 `phase1_leakage_audit_report.md:9` 至 `phase1_leakage_audit_report.md:11`。
- FinMind 暂缓字段未进入样本，见 `phase1_leakage_audit_report.md:12`。
- `market_regime` 仅 grouping/audit，见 `phase1_leakage_audit_report.md:13`。
- schema policy checks 全部 pass，见 `phase1_leakage_audit_report.md:16` 至 `phase1_leakage_audit_report.md:24`。

### 2.4 日期覆盖复核通过

日期覆盖报告明确：

- 2022 sample rows：36231。
- 2023 sample rows：18426。
- 2024 sample rows：0。
- 2025 sample rows：36300。
- 2026 sample rows：13350。
- 2024 缺口说明为 `Phase2_must_not_assume_2024_available`，见 `phase1_date_coverage_report.csv:2` 至 `phase1_date_coverage_report.csv:6`。

这满足上次审查要求。Phase 2 必须基于实际可用年份定义训练/验证/测试，不得假设 2024 可用。

## 3. 发现的问题

本次没有阻塞 Phase 2 的问题。

仍需带入 Phase 2 的限制：

1. 2024 完全缺失，训练切分必须显式避开。
2. 2023 覆盖 symbol 数少于 2022/2025/2026，Phase 2 必须报告年度 coverage 差异对指标的影响。
3. `market_regime` 只能用于分组评估和解释，不得作为模型输入。
4. `candidate_reason_flags` 只能用于报告解释，不得作为模型输入。
5. FinMind 暂缓字段不得进入模型。

## 4. 台股只读安全边界审查

### Findings

Critical：无。

High：无。

Medium：无。

Low：关键词扫描命中 `broker`、`orders`、`quick-trade`、`target position`、`provider refresh`、`accepted latest` 等词，但上下文均为禁止事项、安全声明或执行报告说明，不是真实动作入口。

### Network Audit

未提供 network audit。审查范围是本地样本构建和 schema 修复，未发现网络请求、provider publish/refresh 或 accepted latest switching。

### Console Audit

未提供 console audit。审查过程中本地只读检查遇到沙箱 `bwrap: loopback: Failed RTM_NEWADDR`，已按权限流程重跑只读命令。该问题不影响复审结论。

### Text / Agent Semantics

未发现真实交易建议、下单、目标仓位、自动买卖、连接券商、收益承诺或上涨概率承诺语义。

### Verdict

通过。

## 5. 是否需要用户确认的问题

当前没有需要停下来让用户确认的问题。

如果执行者在 Phase 2 想改变以下任一口径，必须停止并提交用户确认：

- 把 `market_regime` 放回模型输入。
- 启用 FinMind 暂缓字段。
- 回填或刷新 qlib/provider 数据。
- 为了补 2024 数据触发 provider refresh/publish。
- 将 Entry Model 输出接入组合回放或前端。
- 生成真实交易建议。

## 6. 下一步工作文档：Phase 2 Entry Model v1 训练

### 6.1 目标

训练 Entry Model v1，用于研究性地重排候选池，输出 `entry_score`、模型评估、特征重要性、分组表现和错误分析。

Phase 2 只训练 Entry Model，不训练 Exit Risk Model，不做组合回放，不接前端。

### 6.2 范围

允许：

- 读取 Phase 1B 产物。
- 训练 LightGBM binary baseline。
- 训练 LightGBM regression baseline。
- 对比 qlib score/rank baseline。
- 输出 validation/test/forward 评估。
- 输出 feature importance、prediction artifacts、calibration、分组评估。

禁止：

- 不训练 Exit Risk Model。
- 不做 LambdaRank，除非先作为单独 Phase 2B 申请。
- 不做组合回放或策略回测集成。
- 不接前端。
- 不生成真实交易建议。
- 不写 broker / orders / quick-trade / target position。
- 不触发 provider refresh / publish / accepted latest switching。
- 不修改 monitor config / alerts / 模拟账户。
- 不启用 FinMind 暂缓字段。
- 不把 `market_regime` 或 `candidate_reason_flags` 作为输入特征。
- 不在 test/forward 上调参。
- 不使用固定 qlib score 绝对区间作为准入规则。

### 6.3 输入

必须使用：

- `data_tw/experiments/decision_model/phase1_samples.parquet`
- `data_tw/experiments/decision_model/phase1_schema.json`
- `data_tw/experiments/decision_model/phase1_label_quality_report.md`
- `data_tw/experiments/decision_model/phase1_date_coverage_report.csv`

训练输入只能来自 `phase1_schema.json` 的 `input_features`。

训练标签：

- binary：`entry_label_dynamic`
- regression：`entry_target_regression`
- ranking/evaluation target：`entry_rank_target`

训练行过滤：

- `is_labeled == true`
- `candidate_in_expanded_pool == true`
- `passes_liquidity_filter == true`

如果执行者认为需要训练全稳定股票池版本，也只能作为对照输出，不能替代 expanded candidate pool 主线。

### 6.4 时间切分

由于 2024 缺失，Phase 2 必须使用预声明切分，不能随机切分。

主切分：

- train：2022
- validation：2023
- test：2025
- forward：2026 labeled rows

敏感性切分：

- train：2022 + 2023
- validation：2025 上半年
- test：2025 下半年
- forward：2026 labeled rows

要求：

- 两套切分都必须输出。
- 不能在 test 或 forward 上调参。
- 2024 必须明确为 unavailable，不得插值、回填或静默跳过。
- 若某个 split 的 candidate rows 过少，必须报告并停止进入 Phase 3，不得强行宣称通过。

### 6.5 模型要求

必须训练两个 baseline：

1. Binary Entry Model：
   - objective：binary
   - target：`entry_label_dynamic`
   - output：`entry_score_binary`

2. Regression Entry Model：
   - objective：regression
   - target：`entry_target_regression`
   - output：`entry_score_regression`

允许训练一个简单 ensemble score：

- `entry_score_v1 = normalized(entry_score_binary) * 0.5 + normalized(entry_score_regression) * 0.5`

但必须同时报告 binary、regression、ensemble 三者表现，不能只报最好的一组。

### 6.6 Baseline 对照

必须对比：

- qlib raw score 排序。
- qlib date percentile 排序。
- qlib rank 排序。
- Candidate Generator 原始排序。
- random within candidate pool，固定 seed，仅作为 sanity check。

不得只和较弱 baseline 对比。

### 6.7 评估指标

模型层：

- AUC，binary validation/test/forward。
- logloss 或 Brier score。
- regression IC。
- Rank IC。
- NDCG@5 / NDCG@10。
- precision@5。
- Top5 / Top10 future excess return。
- calibration curve。
- feature importance。

分组评估：

- by year。
- by `market_regime`，仅分组，不作为输入。
- by qlib rank bucket。
- by liquidity percentile bucket。
- by position_risk_status。

标签质量：

- 每个 split 的正负样本比例。
- 每个 split 的 target mean/std。
- 每个 split 的 candidate rows。

### 6.8 输出

必须生成：

1. `scripts/train_tw_decision_entry_model_v1.py`
2. `data_tw/experiments/decision_model/phase2_entry_model_v1/entry_model_binary.txt`
3. `data_tw/experiments/decision_model/phase2_entry_model_v1/entry_model_regression.txt`
4. `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2_predictions.parquet`
5. `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2_metrics.csv`
6. `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2_split_summary.csv`
7. `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2_feature_importance.csv`
8. `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2_calibration.csv`
9. `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2_group_metrics.csv`
10. `docs/tw_decision_model/PHASE2_ENTRY_MODEL_REPORT_CN.md`
11. `docs/tw_decision_model/PHASE2_EXECUTION_REPORT_CN.md`

如果 LightGBM 不可用，执行者必须停止并报告，不得擅自切换模型技术路线。

### 6.9 验收标准

Phase 2 只有满足以下条件才可进入 Phase 3：

1. 只训练 Entry Model。
2. 使用 Phase 1B schema 的 `input_features`。
3. `market_regime` 不作为输入特征。
4. `candidate_reason_flags` 不作为输入特征。
5. FinMind 暂缓字段不进入模型。
6. 无随机切分。
7. 无 test/forward 调参。
8. 同时报告 binary、regression、ensemble。
9. 同时报告 qlib baseline 与 candidate baseline。
10. 报告 2024 缺口和 split coverage。
11. 报告 label imbalance。
12. 至少一个独立 test/forward 区间的 TopK forward excess return 优于 qlib rank 或 qlib percentile baseline，且另一区间不能明显劣化。
13. 最大候选拥挤、低流动性、position risk 分组不能出现明显不可解释恶化。
14. 输出 feature importance，且没有明显未来字段或 forbidden 字段。
15. research-only 安全边界通过。

若未达到第 12 条，Phase 2 可以作为失败实验归档，但不得进入 Phase 3。

### 6.10 执行报告模板

执行者完成后提交：

```markdown
# Phase 2 Entry Model v1 执行报告

## 1. 执行摘要

- 执行日期：
- 修改文件：
- 生成文件：
- 是否只训练 Entry Model：
- 是否触碰只读边界：

## 2. 输入与 Schema

- samples path：
- schema path：
- input_features count：
- label target：
- market_regime 是否输入：
- candidate_reason_flags 是否输入：
- FinMind 暂缓字段是否输入：

## 3. 时间切分

| split_name | train | validation | test | forward | notes |
|---|---|---|---|---|---|

## 4. Split Coverage

| split | rows | candidate_rows | positive_rate | target_mean | target_std | unique_dates | unique_symbols |
|---|---:|---:|---:|---:|---:|---:|---:|

## 5. 模型与参数

- binary model：
- regression model：
- ensemble rule：
- fixed random seed：
- 是否在 test/forward 调参：

## 6. Metrics

| split | model | AUC | Brier/logloss | RankIC | NDCG@5 | NDCG@10 | precision@5 | top5_excess_return | top10_excess_return |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|

## 7. Baseline 对比

| split | baseline | RankIC | NDCG@10 | precision@5 | top5_excess_return | top10_excess_return |
|---|---|---:|---:|---:|---:|---:|

## 8. 分组评估

- by year：
- by market_regime：
- by qlib rank bucket：
- by liquidity bucket：
- by position_risk_status：

## 9. Feature Importance

- top positive/important features：
- 是否有 forbidden/future/deferred 字段：
- 是否过度依赖单一特征：

## 10. Calibration

- binary calibration：
- regression score distribution：
- score drift by split：

## 11. 安全边界

- broker/orders/quick-trade：
- provider publish/refresh：
- accepted latest switching：
- monitor config/alerts：
- 真实交易建议语义：

## 12. 风险与待审查问题

- 必须修复：
- 需要用户确认：
- 可暂缓：

## 13. Phase 3 准入建议

- 是否建议进入 Phase 3：
- 若建议，限制条件：
```

## 7. 审查者最终意见

Phase 1B 通过。执行者可以进入 Phase 2 Entry Model v1 训练。

Phase 2 仍是 research-only 模型实验阶段。任何 Exit Risk Model、组合回放、前端展示或真实交易语义都必须等后续阶段审查通过后再做。
