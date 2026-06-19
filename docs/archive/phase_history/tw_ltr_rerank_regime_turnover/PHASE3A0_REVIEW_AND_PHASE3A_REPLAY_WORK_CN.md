# Phase3A0 Frozen Phase1C Score 审查意见与 Phase3A Replay 工作文档

生成时间：2026-06-13

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

Route B 依据：`docs/tw_ltr_rerank_regime_turnover/PHASE3A_ROUTE_B_TURNOVER_REPLAY_WORK_CN.md`

审查入口：`docs/tw_ltr_rerank_regime_turnover/PHASE3A0_FROZEN_PHASE1C_SCORE_EXECUTION_REPORT_CN.md`

---

## 1. 审查结论

Phase3A0 通过审查。

执行者成功物化并冻结 Phase1C row-level score：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv
```

固定 score：

```text
score_head10_all_l31_alpha0.7_top50_only
```

审查接受 gate：

```text
request_phase3a_replay_with_frozen_scores
```

因此可以重启 Route B 的 Phase3A turnover / portfolio replay。

---

## 2. 通过依据

Phase1C 固定配置与要求一致：

```text
score_column = score_head10_all_l31_alpha0.7_top50_only
candidate_id = head10_all_l31_alpha0.7_top50_only
model_id = head10_all_l31
blend_alpha = 0.7
preserve_scope = top50_only
```

指标复现通过：

```text
max_metric_abs_diff = 4.440892098500626e-16
tolerance = 0.0007
metrics_reproduced_within_tolerance = true
```

row count / split 分布通过：

```text
sample_complete_rows = 152249
train = 90301
validation = 30877
independent_test = 31071
```

Top50 preserve 通过：

```text
outside_top50_preserve_ok = true
daily_outside_score_not_above_top50_ok = true
```

输入特征审查通过：

```text
forbidden_feature_hits = []
trend_score 未出现在复用 input_columns 中
```

---

## 3. 安全边界审查

本轮未发现：

- turnover replay；
- 组合净值 / 回撤 / 动作次数 / 换手 / 成本计算；
- 重新选择 candidate；
- validation reselection；
- independent_test 反选；
- 新增 LTR 特征；
- 新增数据源；
- provider refresh / publish；
- accepted latest switching；
- frontend / API / monitor / database 改动；
- broker / quick-trade / orders；
- target position / target weight；
- 买入、卖出、持有、仓位建议；
- 收益承诺、胜率、上涨概率语义。

注意：脚本为物化 Phase1C row-level score 重建了固定 LTR 分数。上一轮工作文档允许“按 Phase1C 已确定配置重建 row-level score”，且本轮未改配置、未重选 candidate、未做新实验主线，因此不视为越界。

---

## 4. 验证结果

已执行：

```text
python -m py_compile scripts/materialize_tw_ltr_phase3a0_frozen_phase1c_scores.py
```

结果：通过。

普通沙箱下执行：

```text
python scripts/materialize_tw_ltr_phase3a0_frozen_phase1c_scores.py
```

遇到环境限制：

```text
bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
```

按环境规则提升权限复跑同一只读脚本，结果通过：

```text
ok = true
gate = request_phase3a_replay_with_frozen_scores
```

---

## 5. Findings

### Low：Phase3A0 报告可接受

报告清楚说明未进入 replay，未计算组合指标，未打开 regime gate。

### Low：后续 replay 必须使用 frozen score artifact

后续 Phase3A 不得再次重建 Phase1C score，不得重新训练或调参。冻结产物已经足够作为输入。

---

## 6. 下一步给执行者：Phase3A Replay with Frozen Scores

下一轮允许重启 Phase3A turnover / portfolio replay，但必须使用 Phase3A0 冻结输入。

---

## 7. Phase3A 本轮目标

只回答：

```text
在固定 Phase1C row-level score 的前提下，
turnover control 是否能相对 baseline rule 改善成本后表现、动作次数、换手与回撤？
```

本轮不得再处理模型训练问题。

---

## 8. 固定输入

必须使用：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv
```

必须使用 score：

```text
score_head10_all_l31_alpha0.7_top50_only
```

不得重建、改写或替换该 score。

---

## 9. Regime 使用规则

Regime-aware gating 仍然未通过。

本轮 regime 只能作为：

- 分组统计字段；
- diagnostic-only 切片；
- 解释不同市场状态下 replay 表现的只读字段。

禁止：

- 用 regime 控制进出；
- 用 regime 调动作阈值；
- 使用 Phase2B selected gate；
- 声称 risk_off gate 成立；
- 把 regime 作为组合层正式过滤器。

报告中必须写明：

```text
Regime-aware gating was not validated.
Regime is diagnostic-only in Phase3A.
```

---

## 10. 允许实现范围

允许新增或修改 Phase3A replay 脚本：

```text
scripts/evaluate_tw_ltr_phase3a_route_b_turnover_replay.py
```

允许输出目录：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase3a_route_b_turnover_replay/
```

允许机制仅限主文档 Stage 4 第一版：

- `no_trade_buffer`
- `confidence_gap`
- `partial_rebalance`
- `max_actions_per_day`
- `min_holding_days`
- `score_or_confidence_clipping`
- `turnover_budget`

可以做小规模 validation 参数网格，但必须：

- validation-only 选择；
- independent_test 只做最终检验；
- 不用 independent_test 反选；
- 不扩展成复杂优化器；
- 不做真实交易系统。

---

## 11. 必须对照 baseline

至少对照：

- `rank_rotate_top30`
- `rank_rotate_top50`
- `rank_rotate_top50_adaptive_score`
- `confirmed_exit`
- `phase1c_simple_topk_no_turnover`
- `phase1c_turnover_controlled`

若某个 baseline 无法复现，必须说明原因，并保留 blocked 行。

---

## 12. 必须报告指标

必须报告：

- gross return；
- fee/tax-adjusted net return；
- final equity；
- max drawdown；
- action count；
- turnover proxy；
- average holding days；
- cost drag；
- yearly result；
- validation / independent_test 分开结果；
- regime diagnostic-only 分组结果；
- 与 baseline 的差异。

不得只报告毛收益。

不得使用：

- 收益承诺；
- 胜率承诺；
- 上涨概率；
- 买入概率；
- 仓位建议。

---

## 13. 禁止事项

执行者不得：

- 重新训练 LTR；
- 重建 Phase1C score；
- 调整 Phase1C score；
- 重新选择 candidate；
- 重新打开 Phase2 regime gate 搜索；
- 使用 regime gate 控制组合；
- 新增数据源；
- 联网；
- provider refresh / publish；
- accepted latest switching；
- 改 frontend；
- 改 API；
- 改 monitor；
- 改 database；
- 接 broker；
- quick-trade；
- orders；
- target position；
- target weight；
- 输出买入、卖出、持有、仓位建议；
- 输出收益承诺、胜率、上涨概率；
- 做真实交易动作。

---

## 14. 必须输出产物

必须输出：

- `phase3a_validation_selection.csv`
- `phase3a_independent_test_comparison.csv`
- `phase3a_yearly_metrics.csv`
- `phase3a_regime_diagnostic_metrics.csv`
- `phase3a_turnover_action_summary.csv`
- `phase3a_gate_summary.json`
- `docs/tw_ltr_rerank_regime_turnover/PHASE3A_ROUTE_B_TURNOVER_REPLAY_EXECUTION_REPORT_CN.md`

---

## 15. Phase3A Gate

`phase3a_gate_summary.json` 必须给出以下之一：

### 15.1 `request_phase3b_replay_repair`

仅当：

- validation 上 Phase1C + turnover 相对 baseline 有明确净收益 / 回撤 / 换手 / 成本改善方向；
- independent_test 没有明显反转；
- action count 和 turnover proxy 有实质改善；
- 没有牺牲过大 final equity 或 max drawdown；
- 没有 safety / scope 问题。

### 15.2 `request_user_decision_route_b_tradeoff`

当出现用户必须判断的 tradeoff，例如：

- 净收益改善但回撤变差；
- 换手下降但 final equity 明显下降；
- validation 与 independent_test 方向冲突；
- 成本假设对结论高度敏感。

### 15.3 `stop_phase3a_turnover_not_supported`

当：

- Phase1C + turnover 无法优于 baseline；
- 改善只在单一窗口；
- 成本后优势消失；
- 动作减少但组合表现显著恶化；
- 或发现越界。

---

## 16. 验证要求

必须运行：

```text
python -m py_compile scripts/evaluate_tw_ltr_phase3a_route_b_turnover_replay.py
python scripts/evaluate_tw_ltr_phase3a_route_b_turnover_replay.py
```

如普通沙箱因 `bwrap` 环境限制失败，按既有方式复跑并在报告中说明。

---

## 17. 执行报告必须包含

1. 本轮目标；
2. 使用 frozen score artifact 的说明；
3. Route B tradeoff 与 regime diagnostic-only 说明；
4. 实际完成内容；
5. 改动文件清单；
6. 新增产物清单；
7. validation 参数选择；
8. independent_test 最终结果；
9. baseline 对照；
10. 年度结果；
11. turnover / action / cost 结果；
12. regime diagnostic-only 分组结果；
13. 验证命令与结果；
14. gate 结论；
15. 禁止事项遵守情况；
16. 需要审查者重点检查的点。

