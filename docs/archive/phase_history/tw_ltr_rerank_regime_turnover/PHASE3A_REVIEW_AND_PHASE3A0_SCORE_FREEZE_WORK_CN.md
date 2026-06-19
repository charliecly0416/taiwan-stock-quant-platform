# Phase 3A Route B Turnover Replay 审查意见与 Phase3A0 输入冻结工作文档

生成时间：2026-06-13

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

Route B 依据：`docs/tw_ltr_rerank_regime_turnover/PHASE3A_ROUTE_B_TURNOVER_REPLAY_WORK_CN.md`

审查入口：`docs/tw_ltr_rerank_regime_turnover/PHASE3A_ROUTE_B_TURNOVER_REPLAY_EXECUTION_REPORT_CN.md`

---

## 1. 审查结论

Phase3A 执行者没有越界。

本轮执行者没有：

- 重新训练 LTR；
- 调整 Phase1C score；
- 重新打开 Phase2 regime gate 搜索；
- 把 regime gate 作为控制层；
- 新增数据源；
- 联网；
- provider refresh / publish；
- accepted latest switching；
- 改 frontend / API / monitor / database；
- 接 broker / quick-trade / orders；
- 输出 target position / target weight；
- 输出买入、卖出、持有、仓位建议；
- 输出收益承诺、胜率或上涨概率。

执行者没有伪造 replay 结果，这是正确的。

但本轮没有完成 Phase3A turnover replay，原因是固定输入缺失：

```text
score_head10_all_l31_alpha0.7_top50_only
```

当前没有行级 Phase1C score artifact，只有 Phase1C 汇总指标。

因此审查结论是：

```text
接受 Phase3A 的阻断诊断；
不接受把它解释成 turnover layer 本身不成立；
下一步应先做 Phase3A0：只读物化并冻结 Phase1C row-level score artifact。
```

---

## 2. 关键证据

执行报告指出：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_ltr_samples.csv
中不存在 score_head10_all_l31_alpha0.7_top50_only 行级分数列。
```

审查检索现有产物后确认：

- `phase1c_final_ltr_repair` 中有 validation / independent_test 汇总；
- 有 `phase1c_gate_summary.json`；
- 没有可直接 replay 的 row-level score CSV；
- 没有保存的 Phase1C 模型 artifact；
- Phase2B / Phase2C 曾在脚本中重建过 Phase1C score，但没有把它作为稳定输入物化。

这意味着当前不能合规执行：

```text
Phase1C qlib-preserving LTR rerank -> turnover replay
```

除非先冻结行级 score。

---

## 3. 对 gate 的修正理解

执行者给出：

```text
stop_phase3a_turnover_not_supported
```

审查认为这个 gate 名称不够准确。

当前不是证明了：

```text
turnover layer 不成立
```

而是证明了：

```text
Phase3A replay 输入未物化，无法执行。
```

因此本轮应理解为：

```text
phase3a_blocked_missing_frozen_phase1c_row_score
```

这不否定 Route B，也不否定 Phase1C 成果。

---

## 4. 验证结果

已执行：

```text
python -m py_compile scripts/evaluate_tw_ltr_phase3a_route_b_turnover_replay.py
```

结果：通过。

普通沙箱下执行：

```text
python scripts/evaluate_tw_ltr_phase3a_route_b_turnover_replay.py
```

遇到环境限制：

```text
bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
```

按环境规则提升权限复跑同一只读预检脚本，结果通过：

```text
ok = true
gate = stop_phase3a_turnover_not_supported
```

安全边界检索未发现 broker / orders / provider publish / accepted latest switching / frontend API 写入 / 交易语义。

---

## 5. Findings

### High：Phase3A 无法执行，因为固定行级输入缺失

Phase3A 的核心输入是固定 Phase1C row-level score。当前只有汇总指标，不能用于组合日级 replay。

### Medium：执行者停止是正确的，但 gate 命名容易误导

`stop_phase3a_turnover_not_supported` 容易被误读为 turnover 已经失败。

实际应是：

```text
blocked_missing_frozen_phase1c_row_score
```

### Low：Route B 边界遵守良好

报告明确写出：

```text
Regime-aware gating was not validated.
Regime is diagnostic-only in Phase3A.
```

没有把失败的 Stage3 包装成已通过前提。

---

## 6. 下一步给执行者：Phase3A0 输入冻结

本轮不允许直接重启 turnover replay。

下一轮只做一个前置任务：

```text
物化并冻结 Phase1C row-level score artifact。
```

该任务命名为：

```text
Phase3A0 Frozen Phase1C Row Score Materialization
```

---

## 7. Phase3A0 本轮目标

只回答：

```text
能否在不改变 Phase1C 语义、不调参、不进入 replay 的前提下，
生成可复用、可审计的 row-level Phase1C score artifact？
```

目标产物是一个稳定输入，不是新模型成果。

---

## 8. Phase3A0 允许范围

允许：

- 复用 Phase1C 既有脚本逻辑；
- 复用 Phase1 样本；
- 按 Phase1C 已确定配置重建 row-level score；
- 输出 date / instrument / split / qlib_score_raw / qlib_rank / Phase1C score / 必要标签与审计列；
- 校验重建后的汇总指标与 Phase1C 报告一致或在可解释数值容差内；
- 写入只读实验产物；
- 写执行报告。

允许新增脚本：

```text
scripts/materialize_tw_ltr_phase3a0_frozen_phase1c_scores.py
```

建议输出目录：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/
```

---

## 9. Phase3A0 禁止事项

执行者不得：

- 做 turnover replay；
- 做组合净值、回撤、动作次数、换手、成本计算；
- 改 Phase1C 模型配置；
- 重新选择 candidate；
- 重新做 validation selection；
- 用 independent_test 反选；
- 新增 LTR 特征；
- 新增数据源；
- 联网；
- provider refresh / publish；
- accepted latest switching；
- 改 frontend / API / monitor / database；
- 重新打开 regime gate；
- 使用 regime 控制任何输出；
- 接 broker / quick-trade / orders；
- 输出 target position / target weight；
- 输出买入、卖出、持有、仓位建议；
- 输出收益承诺、胜率、上涨概率。

---

## 10. Phase3A0 必须固定的 Phase1C 配置

必须固定：

```text
score_column = score_head10_all_l31_alpha0.7_top50_only
candidate_id = head10_all_l31_alpha0.7_top50_only
model_id = head10_all_l31
blend_alpha = 0.7
preserve_scope = top50_only
```

不得改名，不得改参数。

---

## 11. Phase3A0 必须输出产物

必须输出：

- `phase3a0_frozen_phase1c_row_scores.csv`
- `phase3a0_score_reproduction_metrics.csv`
- `phase3a0_score_schema.json`
- `phase3a0_gate_summary.json`
- `docs/tw_ltr_rerank_regime_turnover/PHASE3A0_FROZEN_PHASE1C_SCORE_EXECUTION_REPORT_CN.md`

---

## 12. Phase3A0 必须验证

必须验证：

1. row count 与 Phase1 sample complete rows 一致；
2. split 分布一致；
3. 必须包含 `score_head10_all_l31_alpha0.7_top50_only`；
4. 该 score 只在 qlib Top50 内产生有效重排；
5. qlib Top50 外仍保持 preserve 逻辑；
6. validation / independent_test 的 rank_ic、NDCG@10/@30/@50、Top10/Top30/Top50 future excess rank 与 Phase1C 报告一致或给出可解释容差；
7. 没有新增白名单外特征；
8. 没有使用 regime gate；
9. 没有 safety 边界问题。

建议验证命令：

```text
python -m py_compile scripts/materialize_tw_ltr_phase3a0_frozen_phase1c_scores.py
python scripts/materialize_tw_ltr_phase3a0_frozen_phase1c_scores.py
```

---

## 13. Phase3A0 Gate

`phase3a0_gate_summary.json` 必须给出以下之一：

### 13.1 `request_phase3a_replay_with_frozen_scores`

仅当：

- row-level score 成功物化；
- Phase1C 指标可复现；
- schema 清晰；
- 没有改模型配置；
- 没有 safety / scope 问题。

### 13.2 `stop_phase3a_route_b_missing_replay_input`

当：

- 无法在不重训 / 不改配置的前提下复现 Phase1C score；
- 或复现指标与 Phase1C 报告不一致且无法解释；
- 或发现 Phase1C 产物本身不足以审计。

### 13.3 `phase3a0_needs_user_decision`

仅当必须由用户决定是否允许重新训练或重新物化 Phase1C。

---

## 14. Phase3A0 执行报告必须包含

1. 本轮目标；
2. 固定 Phase1C 配置；
3. 实际完成内容；
4. 改动文件清单；
5. 新增产物清单；
6. row-level score schema；
7. Phase1C 指标复现对照；
8. 与原 Phase1C 报告的差异说明；
9. 验证命令与结果；
10. gate 结论；
11. 禁止事项遵守情况；
12. 需要审查者重点检查的点。

---

## 15. 后续规则

只有 Phase3A0 通过后，才能重启 Phase3A turnover replay。

重启后的 Phase3A 必须继续遵守 Route B：

```text
Phase1C 是固定排序输入；
regime 只做 diagnostic-only；
turnover replay 只做只读历史回放；
不得进入前端/API/交易系统。
```

