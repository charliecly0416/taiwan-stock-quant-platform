# Phase 2C 审查结论与探索停止建议

审查日期：2026-06-10

审查入口：

- `docs/tw_decision_model/PHASE2C_EXECUTION_REPORT_CN.md`

相关证据：

- `scripts/confirm_tw_decision_entry_model_phase2c.py`
- `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2c_gate_confirmation.csv`
- `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2c_candidate_comparison.csv`
- `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2c_failure_attribution.csv`

## 1. 审查结论

Phase 2C 执行范围通过，归档失败结论成立。本轮 Entry Model v1 探索应结束。

执行者遵守了 Phase 2C 的收口约束：只评估 `qlib + technical / ensemble_fixed_trainval` 与 `qlib + technical / regression` 两个预声明候选，以 `baseline_qlib_rank` 为唯一准入基线，没有新增 feature、数据源、模型分支、Exit Model、LambdaRank、组合回放、前端/API 或 provider 操作。

Phase 2C 的 gate confirmation 显示两个候选均未通过四个区间的逐项 gate。执行者给出：

- `pass_phase3_gate=false`
- `archive_entry_model_v1_failed=true`
- Phase 3 准入：否
- Phase 2D：不继续

审查者同意该结论。

## 2. 是否偏离主线或新增分支

未发现偏离主线。

通过项：

- Phase 2C 只做 closeout confirmation，没有继续搜索新模型。
- 候选模型集合与上一份审查文件一致。
- 通过标准使用逐区间、逐指标判断，没有用 overall 均值掩盖失败区间。
- 未使用容忍区间。
- 失败归因明确列出每个候选的失败指标。
- 报告标题和最终结论明确写出 Entry Model v1 归档失败。

未发现项：

- 未发现 Phase 2D 或额外实验分支。
- 未发现 Exit Model、LambdaRank、组合回放或前端/API 产品化。
- 未发现新增数据源、FinMind、2024 回填或数据补齐。
- 未发现 provider refresh/publish 或 accepted latest switching。

## 3. Gate 失败判断

Phase 2C 的失败不是单点噪声，而是准入条件下的系统性不通过。

`qlib + technical / ensemble_fixed_trainval`：

- `main/test` 通过。
- `main/forward` 失败，top5、RankIC、NDCG@10、precision@5 均为负 delta。
- `sensitivity/test` 失败，precision@5 为负 delta。
- `sensitivity/forward` 失败，top10、NDCG@10、precision@5 为负 delta。

`qlib + technical / regression`：

- `main/test` 失败，top5、top10、NDCG@10、precision@5 为负 delta。
- `main/forward` 失败，top5、top10、NDCG@10、precision@5 为负 delta。
- `sensitivity/test` 通过。
- `sensitivity/forward` 失败，top10、NDCG@10、precision@5 为负 delta。

因此，没有候选满足“同一个模型在四个区间 top5/top10 均非负，且 RankIC、NDCG@10、precision@5 不劣化”的 Phase 3 gate。不得进入 Phase 3。

## 4. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：仅出现安全声明类关键词，例如 provider、accepted latest、broker、orders、quick-trade、target position；语境均为“未触碰”或禁止范围说明。

### Network Audit

本次审查对象为本地离线报告、脚本与 CSV 产物。未发现网络请求证据。

### Console Audit

未发现触发 provider refresh/publish、accepted latest switching、monitor 写入、broker、quick-trade 或订单路径的证据。

### Text / Agent Semantics

报告没有给出买入/卖出建议、目标仓位、收益承诺或上涨概率承诺。所有交易相关词汇均处于边界声明或否定语境。

### Verdict

只读研究边界通过。

## 5. 是否结束探索

建议结束当前 Entry Model v1 探索。

理由：

- Phase 2 已发现原 Entry Model v1 未过 qlib rank gate。
- Phase 2B 修复 ensemble 评估口径并做失败诊断后，仍未稳定过 gate。
- Phase 2C 对最接近通过的预声明候选做最终复核，仍失败。
- 继续 Phase 2D 会从“收口复核”变成无边界模型搜索，偏离当前主线审查约束。
- 当前证据不支持进入 Exit Model、组合回放或产品化阶段。

结论：

- 停止 Entry Model v1 本轮探索。
- 冻结 Phase 0 到 Phase 2C 的证据链。
- 不再给执行者派发新的 Phase 2D 建模任务。
- 后续是否重启，需要用户先确认新的研究方案。

## 6. 停下来思考的方案

当前不要继续让执行者试模型。建议先在审查层面做一次方向选择。

### 方案 A：接受 qlib rank 作为当前主线基线

做法：

- 归档 Entry Model v1 失败。
- 将 `baseline_qlib_rank` 保留为当前研究排序基线。
- 只输出 Phase 0 到 Phase 2C 的审查闭环总结。
- 不进入 Phase 3。

优点：

- 最稳妥，避免继续过拟合。
- 与现有证据一致。
- 不新增安全边界风险。

缺点：

- 暂时没有 meta model 增益。
- 后续需要重新设计问题，而不是小修 Entry Model v1。

审查者建议：默认采用。

### 方案 B：重启问题定义，而不是继续 Phase 2D

只有用户明确要求重启时，才允许进入该方案。

可能方向：

- 重新定义 label，例如从单一短期 excess return 改成多周期稳健标签。
- 重新定义候选池，例如只在 qlib rank 已经较强的 TopN 内做 rerank，而不是全候选重排。
- 重新定义模型目标，例如从“直接超过 qlib rank”改为“给 qlib rank 增加不确定性/风险标注”。
- 重新做时间切分与市场状态覆盖，避免 sensitivity 失败被忽略。

限制：

- 必须从 Phase 0 级别重新写设计文档。
- 不能复用 Phase 2D 名义继续搜索。
- 不能直接进入 Exit Model、回放或前端。

### 方案 C：只做复盘报告，不做新实验

做法：

- 汇总 Phase 0、Phase 1、Phase 1B、Phase 2、Phase 2B、Phase 2C 的关键结论。
- 形成 Entry Model v1 失败复盘。
- 明确哪些假设失败、哪些边界有效、哪些产物可复用。

适用场景：

- 需要给后续研究者留下清晰上下文。
- 用户暂时不决定新方向。

## 7. 给执行者的当前指令

当前不给执行者新的建模或实验任务。

允许执行者做的只有文档性收尾：

- 不修改模型。
- 不新增脚本。
- 不新增数据。
- 不运行训练。
- 不进入 Phase 3。
- 不启动 Phase 2D。

如需执行者继续，只能在用户确认后执行以下二选一：

- 归档总结文档：整理 Phase 0 到 Phase 2C 的闭环证据。
- 新研究方向立项文档：从 Phase 0 重新定义目标、标签、候选池、gate 与安全边界。

## 8. 审查者最终裁决

- Phase 2C 执行范围：通过。
- Phase 2C 安全边界：通过。
- Phase 2C 是否偏离主线：否。
- Phase 2C 是否新增未授权分支：否。
- Phase 3 是否准入：否。
- Phase 2D 是否允许：否。
- Entry Model v1 本轮探索是否结束：是。
- 下一步：暂停实验，等待用户选择“归档闭环总结”或“从 Phase 0 重启新研究方向”。
