# Phase 2B 审查结论与 Phase 2C 收口工作文档

审查日期：2026-06-10

审查入口：

- `docs/tw_decision_model/PHASE2B_ENTRY_MODEL_DIAGNOSIS_REPORT_CN.md`
- `docs/tw_decision_model/PHASE2B_EXECUTION_REPORT_CN.md`

相关执行产物：

- `scripts/diagnose_tw_decision_entry_model_phase2b.py`
- `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2b_gate_deltas.csv`
- `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2b_ensemble_calibration_compare.csv`
- `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2b_feature_group_ablation.csv`
- `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2b_binary_diagnostics.csv`
- `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2b_regression_diagnostics.csv`

## 1. 审查结论

Phase 2B 执行范围通过，但 Phase 3 准入仍不通过。

本次执行者没有偏离主线，也没有新增需要叫停讨论的分支。Phase 2B 的实际工作仍限定在 Entry Model v1 的失败诊断、ensemble 评估口径修复、预定义 feature group ablation、binary/regression 失败定位，不包含 Exit Model、LambdaRank、组合回放、前端产品化、FinMind 新数据、2024 回填、provider refresh/publish、accepted latest switching 或任何交易动作。

但是，Phase 2B 没有证明 Entry Model v1 能稳定超越 qlib rank 基线。执行者报告中也明确给出“不建议进入 Phase 3”。审查者同意该判断：不得进入 Phase 3。

## 2. 主线一致性审查

通过项：

- 仍沿用 Phase 2 的 Entry Model v1 主线，没有训练 Exit Risk Model。
- 仍以 qlib rank 基线为准入比较对象，没有改成新的主指标。
- ensemble 修复从原先容易产生评估泄漏风险的 split-part minmax，改为 `train+validation fitted minmax` 与 `same-asof minmax` 两个诊断口径，且报告声明不使用 test/forward 全区间分布。
- feature group ablation 是诊断性工作，没有引入新数据源或重新定义任务目标。
- binary/regression 诊断聚焦失败原因，没有把失败解释包装成通过结论。

未发现的偏离：

- 未发现 Exit Model 分支。
- 未发现 LambdaRank 分支。
- 未发现组合回放或前端分支。
- 未发现 provider refresh/publish 或 accepted latest 切换。
- 未发现真实交易、券商、订单、quick-trade、target position 路径。

## 3. Gate 审查

Phase 2B 的 gate delta 表显示，没有任何一个模型口径在 `main test`、`main forward`、`sensitivity test`、`sensitivity forward` 四个区间上同时稳定通过。

关键判断：

- 原 `ensemble_original` 失败结论保留。
- `ensemble_fixed_trainval` 修复了评估口径，但没有修复收益排序稳定性；在 main test/main forward 仍有 top5/top10、NDCG 或 precision 劣化。
- `ensemble_fixed_same_asof` 也未稳定通过。
- `regression` 在 main test/main forward 接近或略优，但在 sensitivity test 的 top5/top10 delta 为负，不能作为 Phase 3 准入模型。
- `binary` 在 main test/main forward 明显弱于 qlib rank，不能继续作为主候选。

因此，Phase 3 gate 仍失败。当前不能做 Exit Model、组合回放或产品化验证。

## 4. 安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：仅出现安全说明类关键词，例如 broker/orders/provider/accepted latest/monitor config；语境为“未触碰”或边界声明，不构成危险行为。

### Network Audit

本次审查对象为本地脚本、报告与离线实验产物，未发现网络请求证据，也未发现需要网络执行的动作。

### Console Audit

未发现控制台证据表明触发 provider refresh/publish、accepted latest switching、monitor 写入、broker、quick-trade 或订单路径。

### Text / Agent Semantics

报告文本没有给出买入/卖出建议、目标仓位、收益承诺或上涨概率承诺。涉及交易相关词汇时均为安全边界说明。

### Verdict

只读研究边界通过。

## 5. 是否需要停下来讨论

本次未发现必须立即停下来向用户讨论的问题，因为执行者没有越过主线边界，也没有擅自进入 Phase 3。

但下一步必须防止无边界试错。Entry Model v1 已连续经历 Phase 2 与 Phase 2B 后仍未稳定过 gate，因此只允许做一次严格收口的 Phase 2C。Phase 2C 后若仍失败，应归档 Entry Model v1，不得继续追加 Phase 2D/Phase 2E 式搜索。

## 6. 给执行者的 Phase 2C 工作文档

### 6.1 目标

Phase 2C 不是新模型开发阶段，而是 Entry Model v1 的最后一次 gate confirmation / closeout。

目标只有两个：

1. 对 Phase 2B 中最接近通过的候选进行固定口径复核。
2. 给出二选一结论：`pass_phase3_gate=true` 或 `archive_entry_model_v1_failed=true`。

### 6.2 允许范围

只允许评估以下预声明候选：

- `qlib + technical / ensemble_fixed_trainval`
- `qlib + technical / regression`
- 原 `baseline_qlib_rank` 作为唯一准入基线

允许输出：

- Phase 2C gate confirmation CSV
- Phase 2C candidate comparison CSV
- Phase 2C failure attribution CSV，如果仍失败
- Phase 2C 中文执行报告

允许复核的指标：

- top5 excess return delta vs qlib rank
- top10 excess return delta vs qlib rank
- RankIC delta vs qlib rank
- NDCG@10 delta vs qlib rank
- precision@5 delta vs qlib rank

必须覆盖的区间：

- `main / test`
- `main / forward`
- `sensitivity / test`
- `sensitivity / forward`

### 6.3 禁止范围

Phase 2C 禁止做以下事项：

- 禁止新增 feature。
- 禁止新增数据源。
- 禁止 FinMind 接入、2024 回填或任何数据补齐。
- 禁止 provider refresh/publish。
- 禁止 accepted latest switching。
- 禁止训练 Exit Model。
- 禁止 LambdaRank 或其他新排序模型。
- 禁止组合回放。
- 禁止前端、API 或产品化改动。
- 禁止根据 test/forward 表现反向调参。
- 禁止把单一区间改善解释为 Phase 3 通过。
- 禁止新增 Phase 2C 范围外候选模型。

### 6.4 Phase 2C 通过标准

Phase 2C 只有在同一个候选模型同时满足以下条件时，才允许建议进入 Phase 3：

- 四个区间的 top5 delta vs qlib rank 均为非负。
- 四个区间的 top10 delta vs qlib rank 均为非负。
- RankIC、NDCG@10、precision@5 不得出现材料性劣化。
- 不能依赖 `all input features` 的偶然 sensitivity 改善来覆盖 main 失败。
- 报告必须明确列出每个区间的 pass/fail，不得只给 overall 均值。

如果执行者认为需要使用容忍区间，必须在执行前写入固定阈值，并且该阈值只能用于判断统计噪声，不能掩盖稳定负 delta。默认审查口径是不使用容忍区间。

### 6.5 Phase 2C 失败标准

满足任一条件即判定失败：

- 任一候选在四个区间中存在 top5 或 top10 明确负 delta。
- 任一候选以牺牲 RankIC、NDCG@10 或 precision@5 的稳定性换取单个收益指标改善。
- 需要引入新 feature、新数据、新模型或新分支才能解释通过。
- 只在 forward 或 sensitivity forward 改善，但 main test 或 sensitivity test 不通过。

失败后必须输出：

- `archive_entry_model_v1_failed=true`
- 不进入 Phase 3
- 不再继续 Phase 2D
- 后续若要重启，只能由用户另行确认新研究方向

### 6.6 建议输出文件

执行者下一步建议新增：

- `scripts/confirm_tw_decision_entry_model_phase2c.py`
- `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2c_gate_confirmation.csv`
- `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2c_candidate_comparison.csv`
- `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2c_failure_attribution.csv`
- `docs/tw_decision_model/PHASE2C_EXECUTION_REPORT_CN.md`

如果 Phase 2C 失败，报告标题和摘要必须明确写出 Entry Model v1 归档失败，不得用“接近通过”“可进入下一阶段观察”等措辞替代 gate 结论。

## 7. 审查者最终裁决

- Phase 2B 执行范围：通过。
- Phase 2B 安全边界：通过。
- Phase 2B 是否偏离主线：否。
- Phase 2B 是否新增未授权分支：否。
- Phase 3 是否准入：否。
- 下一步：只允许执行 Phase 2C 收口复核；若 Phase 2C 仍失败，归档 Entry Model v1 并停止该主线。
