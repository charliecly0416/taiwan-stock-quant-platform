# Decision Meta Model Phase 2 审核意见与 Phase 2B 下一步工作文档

## 0. 审查入口与依据

审查入口：

- `docs/tw_decision_model/PHASE2_EXECUTION_REPORT_CN.md`
- `docs/tw_decision_model/PHASE2_ENTRY_MODEL_REPORT_CN.md`

审查依据：

- `prompt_investigate.md`
- `docs/TW_STOCK_DECISION_META_MODEL_DESIGN_CN.md`
- `docs/tw_decision_model/PHASE1B_REVIEW_AND_PHASE2_WORK_CN.md`
- `scripts/train_tw_decision_entry_model_v1.py`
- `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2_metrics.csv`
- `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2_split_summary.csv`
- `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2_feature_importance.csv`
- `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2_group_metrics.csv`

本次同时按台股 research-only 安全边界进行审查。

## 1. 本步审核结论

结论：Phase 2 执行范围通过，但 Phase 3 准入不通过。

执行者没有偏离主线，没有新增无关分支，也没有越过 research-only 边界。Phase 2 确实只训练了 Entry Model v1，没有训练 Exit Risk Model、没有组合回放、没有前端集成、没有真实交易动作。

但当前模型表现不满足进入 Phase 3 的稳健性要求。下一步不得进入 Exit Risk Model。应先执行 Phase 2B：Entry Model v1 失败分析、校准修复与有限重跑。

## 2. 主线一致性审查

### 2.1 未发现越阶段实现

执行报告显示：

- 新增脚本为 `scripts/train_tw_decision_entry_model_v1.py`，见 `PHASE2_EXECUTION_REPORT_CN.md:5` 至 `PHASE2_EXECUTION_REPORT_CN.md:7`。
- 只训练 Entry Model，见 `PHASE2_EXECUTION_REPORT_CN.md:8`。
- 未触碰 broker/orders/quick-trade/provider/accepted latest/monitor，见 `PHASE2_EXECUTION_REPORT_CN.md:9`。
- 未使用 `market_regime`、`candidate_reason_flags`、FinMind 暂缓字段作为输入，见 `PHASE2_EXECUTION_REPORT_CN.md:11` 至 `PHASE2_EXECUTION_REPORT_CN.md:19`。
- 时间切分按 Phase 2 文档执行，且明确 2024 unavailable，见 `PHASE2_EXECUTION_REPORT_CN.md:21` 至 `PHASE2_EXECUTION_REPORT_CN.md:27`。

### 2.2 Schema 与 forbidden feature 审查通过

自动复核：

```text
feature_count 48
forbidden_features []
importance_forbidden []
```

脚本也显式拦截 `market_regime`、`candidate_reason_flags` 和 future fields，见 `train_tw_decision_entry_model_v1.py:76` 至 `train_tw_decision_entry_model_v1.py:81`。

模型报告中的 forbidden check 为空，见 `PHASE2_ENTRY_MODEL_REPORT_CN.md:40` 至 `PHASE2_ENTRY_MODEL_REPORT_CN.md:42`。

## 3. 发现的问题

### 3.1 High：不满足 Phase 3 准入

Phase 2 文档要求模型至少在独立 test/forward 区间相对 qlib baseline 有稳健改善，且另一区间不能明显劣化。当前结果不满足。

执行者报告也给出相同判断，见 `PHASE2_EXECUTION_REPORT_CN.md:169` 至 `PHASE2_EXECUTION_REPORT_CN.md:172`，以及 `PHASE2_ENTRY_MODEL_REPORT_CN.md:44` 至 `PHASE2_ENTRY_MODEL_REPORT_CN.md:46`。

关键对比：

```text
main test: ensemble top5 delta vs qlib_rank = -0.029209, top10 delta = -0.026805
main forward: ensemble top5 delta vs qlib_rank = -0.037481, top10 delta = -0.031008
sensitivity test: ensemble top5 delta = -0.017021, top10 delta = -0.015915
sensitivity forward: ensemble top5 delta = +0.043737, top10 delta = +0.013443
```

因此不能进入 Phase 3。

### 3.2 Medium：Phase 3 gate 分析过度聚焦 ensemble，遗漏 regression-only 的有用信号

执行者的结论主要按 ensemble 判断失败。这个结论对“不进入 Phase 3”是正确的，但分析不完整。

从 `PHASE2_EXECUTION_REPORT_CN.md:59` 至 `PHASE2_EXECUTION_REPORT_CN.md:64` 及 baseline 行 `PHASE2_EXECUTION_REPORT_CN.md:92` 至 `PHASE2_EXECUTION_REPORT_CN.md:99` 可见：

- main test 中 regression 的 top5/top10 excess return 分别为 `0.046758` / `0.047104`，高于 qlib rank 的 `0.044263` / `0.041242`。
- main forward 中 regression 的 top5/top10 excess return 分别为 `0.081534` / `0.102625`，高于 qlib rank 的 `0.078387` / `0.086197`。
- 但 sensitivity test 中 regression top5/top10 为 `0.056850` / `0.052195`，低于 qlib rank 的 `0.076455` / `0.070832`，见 `PHASE2_EXECUTION_REPORT_CN.md:72` 和 `PHASE2_EXECUTION_REPORT_CN.md:112` 至 `PHASE2_EXECUTION_REPORT_CN.md:114`。

结论：

- regression-only 不是完全无效。
- 当前问题更像是稳健性不足和 ensemble 构造失败，而不是 Entry Model 方向整体失败。
- Phase 2B 应优先诊断 regression 信号为何 main split 有效、sensitivity test 失效。

### 3.3 Medium：ensemble min-max 归一化使用 split part 自身分布，评估口径不够上线一致

脚本中：

- `minmax_by_split()` 使用当前传入 series 的 min/max，见 `train_tw_decision_entry_model_v1.py:158` 至 `train_tw_decision_entry_model_v1.py:163`。
- `entry_score_v1` 在每个 split part 内分别计算，见 `train_tw_decision_entry_model_v1.py:166` 至 `train_tw_decision_entry_model_v1.py:171`。
- 执行报告也写明 ensemble rule 是 `within split part`，见 `PHASE2_EXECUTION_REPORT_CN.md:41` 至 `PHASE2_EXECUTION_REPORT_CN.md:47`。

这没有使用标签，不是严重未来函数；但它使用 test/forward 整段 score 分布做校准，不符合上线时固定校准或逐日候选重排的口径。Phase 2B 必须改为：

- 用 train/validation 拟合 score scaler，再应用到 test/forward；或
- 只做 same-asof per-date normalization，且报告该选择。

不得继续使用 test/forward 全区间 min/max 作为 ensemble calibration。

### 3.4 Medium：binary 模型在 validation/forward 表现偏弱，需要单独诊断

main validation binary AUC 为 `0.468941`，RankIC 为 `-0.055211`，见 `PHASE2_EXECUTION_REPORT_CN.md:56`。main forward binary RankIC 为 `-0.085280`，见 `PHASE2_EXECUTION_REPORT_CN.md:62`。

这说明 binary label 或 binary objective 可能与排序任务不匹配。Phase 2B 不应继续把 binary 和 regression 等权 ensemble 作为默认主方案。

### 3.5 Low：特征重要性存在集中于波动/趋势/市场变量的风险

Top importance 主要集中在 `ma60_slope`、`volatility20`、`twii_close_vs_ma120`、`market_volatility20`、`liquidity_percentile_by_date` 等，见 `PHASE2_EXECUTION_REPORT_CN.md:127` 至 `PHASE2_EXECUTION_REPORT_CN.md:147`。

这些不是 forbidden features，但 Phase 2B 需要检查是否在特定年份或 market regime 上过拟合。

## 4. 已通过项

1. Phase 2 只训练 Entry Model。
2. 未训练 Exit Risk Model。
3. 未做组合回放。
4. 未接前端。
5. 未生成真实交易建议。
6. 未触碰 broker/orders/quick-trade/provider/accepted latest/monitor。
7. 未使用 FinMind 暂缓字段。
8. 未使用 `market_regime` 作为输入。
9. 未使用 `candidate_reason_flags` 作为输入。
10. 同时报告 binary、regression、ensemble。
11. 同时报告 qlib baseline、candidate baseline、random baseline。
12. 明确 2024 不可用。

## 5. 必须修复项

进入任何后续模型阶段前必须完成：

1. 不允许进入 Phase 3。
2. 不允许训练 Exit Risk Model。
3. 归档当前 Phase 2 为 insufficient / failed-gate experiment。
4. 修复 ensemble calibration，不得使用 test/forward 全区间 min/max。
5. 补充 regression-only gate 分析。
6. 补充 binary label/objective 失效分析。
7. 补充 feature group ablation，判断是 qlib、技术、流动性、大盘哪类特征导致不稳。
8. 补充 by-year / by-market-regime / by-rank-bucket 的失败原因摘要。

## 6. 可暂缓项

以下内容继续暂缓：

1. Exit Risk Model。
2. LambdaRank。
3. 组合回放。
4. 前端产品化。
5. FinMind institutional / margin / monthly revenue / valuation。
6. provider refresh / data backfill。

## 7. 是否需要用户确认的问题

当前没有必须停下来让用户确认的问题。

若执行者想做以下任何事情，必须先提交用户确认：

- 进入 Phase 3。
- 启用 Exit Risk Model。
- 做组合回放。
- 接前端。
- 为补 2024 触发数据刷新、回填、provider publish 或 accepted latest switching。
- 改变 Phase 1B schema，引入 FinMind 暂缓字段。

## 8. 台股只读安全边界审查

### Findings

Critical：无。

High：无。

Medium：无。

Low：关键词扫描命中 broker/orders/quick-trade/provider refresh/publish/accepted latest 等词，但上下文均为禁止事项、安全声明或执行报告说明，不是真实动作入口。

### Network Audit

未提供 network audit。审查范围为本地模型训练与报告生成，未发现网络请求、provider publish/refresh 或 accepted latest switching。

### Console Audit

未提供 console audit。审查过程中本地只读检查遇到沙箱 `bwrap: loopback: Failed RTM_NEWADDR`，已按权限流程重跑只读命令。该问题不影响审查结论。

### Text / Agent Semantics

未发现真实交易建议、下单、目标仓位、自动买卖、连接券商、收益承诺或上涨概率承诺语义。

### Verdict

通过。

## 9. 下一步工作文档：Phase 2B Entry Model 失败分析与有限修复

### 9.1 目标

解释 Phase 2 Entry Model v1 未通过 Phase 3 gate 的原因，并在不扩大阶段范围的前提下，做有限、预声明的修复实验。

Phase 2B 不是 Phase 3，不训练 Exit Risk Model，不做组合回放。

### 9.2 范围

允许：

- 读取 Phase 1B 样本与 Phase 2 预测/指标。
- 修复 ensemble calibration。
- 做预声明 feature group ablation。
- 做 regression-only、binary-only、ensemble 的 gate 分析。
- 做失败分组诊断。
- 生成 Phase 2B 报告。

禁止：

- 不训练 Exit Risk Model。
- 不做 LambdaRank。
- 不做组合回放。
- 不接前端。
- 不生成真实交易建议。
- 不写 broker / orders / quick-trade / target position。
- 不触发 provider refresh / publish / accepted latest switching。
- 不修改 monitor config / alerts / 模拟账户。
- 不启用 FinMind 暂缓字段。
- 不新增数据刷新或 2024 回填。
- 不在 test/forward 上调参。
- 不提交只报最好实验的选择性结果。

### 9.3 必须完成的诊断

#### 9.3.1 Gate 分析重算

必须对以下模型分别输出 gate table：

- binary
- regression
- ensemble 原始版
- ensemble 修复版

每个模型必须比较：

- qlib raw
- qlib percentile
- qlib rank
- candidate sort

必须输出 test 和 forward 的：

- RankIC delta
- NDCG@10 delta
- precision@5 delta
- top5 excess return delta
- top10 excess return delta

#### 9.3.2 Ensemble calibration 修复

不得使用 test/forward 全区间 min/max。

必须至少实现一种：

- train/validation fitted scaler：只用 train 或 train+validation 的 score min/max 或分位数，应用到 test/forward。
- same-asof normalization：每天候选池内独立归一化，只用当日候选 score。

若两种都实现，必须同时报告，不能只保留较好结果。

#### 9.3.3 Feature group ablation

预声明 feature groups：

- qlib only
- qlib + technical
- qlib + liquidity
- qlib + market continuous
- qlib + technical + liquidity
- all input features

要求：

- 使用同样 split。
- 不调参。
- 不引入新特征。
- 不使用 `market_regime`。
- 不使用 `candidate_reason_flags`。
- 不使用 FinMind 暂缓字段。

#### 9.3.4 Binary failure diagnosis

必须报告：

- binary best_iteration。
- train/validation/test/forward score distribution。
- calibration by split。
- label positive rate by split。
- binary 是否系统性低估/高估。
- binary 排序指标是否与 AUC 背离。

#### 9.3.5 Regression robustness diagnosis

必须报告：

- regression 在 main test/forward 为什么优于 qlib。
- regression 在 sensitivity test 为什么劣化。
- 劣化是否集中于特定 year/month、market_regime、rank bucket、liquidity bucket、position_risk_status。
- top feature 在 main 与 sensitivity 是否一致。

### 9.4 输出

必须生成：

1. `scripts/diagnose_tw_decision_entry_model_phase2b.py`
2. `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2b_gate_deltas.csv`
3. `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2b_ensemble_calibration_compare.csv`
4. `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2b_feature_group_ablation.csv`
5. `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2b_binary_diagnostics.csv`
6. `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2b_regression_diagnostics.csv`
7. `docs/tw_decision_model/PHASE2B_ENTRY_MODEL_DIAGNOSIS_REPORT_CN.md`
8. `docs/tw_decision_model/PHASE2B_EXECUTION_REPORT_CN.md`

### 9.5 验收标准

Phase 2B 只有满足以下条件才可重新申请 Phase 3 gate：

1. 原 Phase 2 失败结论被完整保留，不得覆盖。
2. ensemble calibration 不使用 test/forward 全区间分布。
3. regression-only、binary-only、ensemble 都有 gate delta。
4. feature group ablation 完整输出。
5. binary failure diagnosis 完整输出。
6. regression robustness diagnosis 完整输出。
7. 若仍无法稳健超过 qlib baseline，必须明确建议停止 Entry Model v1，不得进入 Phase 3。
8. 若某个修复版声称通过，必须同时满足 main 与 sensitivity 的 test/forward 稳健性要求，不能只挑 forward 或单一切分。
9. research-only 安全边界通过。

### 9.6 执行报告模板

执行者完成后提交：

```markdown
# Phase 2B Entry Model 失败分析与有限修复执行报告

## 1. 执行摘要

- 执行日期：
- 修改文件：
- 生成文件：
- 是否训练 Exit Model：
- 是否做组合回放：
- 是否触碰只读边界：

## 2. 原 Phase 2 Gate 复述

- main test 结论：
- main forward 结论：
- sensitivity test 结论：
- sensitivity forward 结论：
- 是否允许进入 Phase 3：

## 3. Gate Delta 表

| split | part | model | baseline | rankic_delta | ndcg10_delta | precision5_delta | top5_delta | top10_delta |
|---|---|---|---|---:|---:|---:|---:|---:|

## 4. Ensemble Calibration 修复

- 原始 within split part minmax：
- train/validation fitted scaler：
- same-asof normalization：
- 是否使用 test/forward 分布：

## 5. Feature Group Ablation

| feature_group | split | part | model | RankIC | NDCG@10 | precision@5 | top5_excess_return | top10_excess_return |
|---|---|---|---|---:|---:|---:|---:|---:|

## 6. Binary Failure Diagnosis

- best_iteration：
- score distribution：
- calibration：
- label balance：
- failure summary：

## 7. Regression Robustness Diagnosis

- main 改善来源：
- sensitivity test 劣化来源：
- 分组失败点：
- feature importance 稳定性：

## 8. 安全边界

- broker/orders/quick-trade：
- provider publish/refresh：
- accepted latest switching：
- monitor config/alerts：
- 真实交易建议语义：

## 9. 风险与待审查问题

- 必须修复：
- 需要用户确认：
- 可暂缓：

## 10. Phase 3 准入建议

- 是否建议进入 Phase 3：
- 证据：
- 若不建议，归档结论：
```

## 10. 审查者最终意见

Phase 2 作为执行工作没有越界，但模型效果未达标。

不得进入 Phase 3。执行者下一步应完成 Phase 2B 失败分析与有限修复，重点解释 regression 信号不稳、binary 失效和 ensemble calibration 问题。
