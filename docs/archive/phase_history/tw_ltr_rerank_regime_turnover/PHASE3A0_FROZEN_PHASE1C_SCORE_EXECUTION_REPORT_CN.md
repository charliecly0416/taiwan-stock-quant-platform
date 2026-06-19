# Phase3A0 执行报告：冻结 Phase1C Row-level Score

生成时间：2026-06-13T18:20:17+00:00

## 1. 本轮目标

只读物化并冻结 Phase1C row-level score artifact，为后续 Route B replay 提供稳定输入。本轮不做 turnover replay。

## 2. 固定 Phase1C 配置

- score_column：`score_head10_all_l31_alpha0.7_top50_only`
- candidate_id：`head10_all_l31_alpha0.7_top50_only`
- model_id：`head10_all_l31`
- blend_alpha：`0.7`
- preserve_scope：`top50_only`
- label_col：`relevance_10d_top_heavy`
- model：`LGBMRanker objective=lambdarank, num_leaves=31, learning_rate=0.03, n_estimators=120, random_state=42`

## 3. 实际完成内容

- 复用 Phase1 样本和 Phase1C 已确定配置重建 row-level score。
- 输出可复用 row-level score CSV、schema、指标复现对照和 gate summary。
- 校验 row count、split 分布、Top50 preserve 逻辑、Phase1C 汇总指标复现。
- 未进入 replay，未做组合净值、回撤、动作次数、换手或成本计算。

## 4. 改动文件清单

- `scripts/materialize_tw_ltr_phase3a0_frozen_phase1c_scores.py`
- `docs/tw_ltr_rerank_regime_turnover/PHASE3A0_FROZEN_PHASE1C_SCORE_EXECUTION_REPORT_CN.md`

## 5. 新增产物清单

- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_score_reproduction_metrics.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_score_schema.json`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_gate_summary.json`

## 6. row-level score schema

详见 `data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_score_schema.json`。核心列包含 `date`、`instrument`、`split`、`qlib_score_raw`、`qlib_rank`、`score_head10_all_l31_alpha0.7_top50_only`、必要标签与审计列。

## 7. Phase1C 指标复现对照

```text
           split                       metric     produced    reference     abs_diff  tolerance  within_tolerance
      validation                   date_count   209.000000   209.000000 0.000000e+00     0.0000              True
      validation                    row_count 30877.000000 30877.000000 0.000000e+00     0.0000              True
      validation                  rank_ic_10d     0.057973     0.057973 4.857226e-17     0.0007              True
      validation                   ndcg_at_10     0.552003     0.552003 0.000000e+00     0.0007              True
      validation                   ndcg_at_30     0.541477     0.541477 0.000000e+00     0.0007              True
      validation                   ndcg_at_50     0.574794     0.574794 0.000000e+00     0.0007              True
      validation top10_future_excess_rank_10d     0.533149     0.533149 0.000000e+00     0.0007              True
      validation     top10_mean_relevance_10d     2.157416     2.157416 4.440892e-16     0.0007              True
      validation top30_future_excess_rank_10d     0.528095     0.528095 0.000000e+00     0.0007              True
      validation     top30_mean_relevance_10d     2.133014     2.133014 0.000000e+00     0.0007              True
      validation top50_future_excess_rank_10d     0.520453     0.520453 0.000000e+00     0.0007              True
      validation     top50_mean_relevance_10d     2.098756     2.098756 0.000000e+00     0.0007              True
independent_test                   date_count   209.000000   209.000000 0.000000e+00     0.0000              True
independent_test                    row_count 31071.000000 31071.000000 0.000000e+00     0.0000              True
independent_test                  rank_ic_10d     0.027360     0.027360 6.938894e-17     0.0007              True
independent_test                   ndcg_at_10     0.559268     0.559268 0.000000e+00     0.0007              True
independent_test                   ndcg_at_30     0.541698     0.541698 0.000000e+00     0.0007              True
independent_test                   ndcg_at_50     0.567569     0.567569 0.000000e+00     0.0007              True
independent_test top10_future_excess_rank_10d     0.550175     0.550175 0.000000e+00     0.0007              True
independent_test     top10_mean_relevance_10d     2.258852     2.258852 0.000000e+00     0.0007              True
independent_test top30_future_excess_rank_10d     0.527896     0.527896 0.000000e+00     0.0007              True
independent_test     top30_mean_relevance_10d     2.149761     2.149761 4.440892e-16     0.0007              True
independent_test top50_future_excess_rank_10d     0.513406     0.513406 0.000000e+00     0.0007              True
independent_test     top50_mean_relevance_10d     2.077512     2.077512 0.000000e+00     0.0007              True
```

## 8. 与原 Phase1C 报告的差异说明

- 最大绝对差异：`4.440892098500626e-16`。
- 容差：`0.0007`，row_count/date_count 要求完全一致。
- 指标复现通过：`True`。

## 9. Top50 preserve 校验

```json
{
  "outside_top50_rows": 101304,
  "outside_top50_preserve_max_abs_diff": 0.0,
  "outside_top50_preserve_ok": true,
  "inside_top50_rows": 50945,
  "inside_top50_score_not_constant": true,
  "inside_top50_changed_share_proxy": 1.0,
  "daily_outside_score_not_above_top50_count": 0,
  "daily_outside_score_not_above_top50_ok": true
}
```

## 10. 验证命令与结果

- `python -m py_compile scripts/materialize_tw_ltr_phase3a0_frozen_phase1c_scores.py`：通过。
- `python scripts/materialize_tw_ltr_phase3a0_frozen_phase1c_scores.py`：普通沙箱若触发 `bwrap` 环境限制，则同一只读命令经授权在沙箱外复跑；本次最终通过。

## 11. Gate 结论

`request_phase3a_replay_with_frozen_scores`

原因：Frozen Phase1C row-level score was materialized and reproduced Phase1C metrics within tolerance.

## 12. 禁止事项遵守情况

本轮未做 turnover replay，未做组合净值、回撤、动作次数、换手、成本计算，未改 Phase1C 模型配置，未重新选择 candidate，未重新做 validation selection，未用 independent_test 反选，未新增 LTR 特征，未新增数据源，未联网，未 provider refresh / publish，未 accepted latest switching，未改 frontend / API / monitor / database，未重新打开 regime gate，未使用 regime 控制任何输出，未接 broker / quick-trade / orders / target position / target weight，未输出买入、卖出、持有、仓位建议、收益承诺、胜率或上涨概率语义。

## 13. 需要审查者重点检查的点

- Phase1C 固定配置是否完全一致。
- row-level score schema 是否足够支持后续 Phase3A replay。
- 指标复现容差是否可接受。
- 是否可以按 gate 重启 Phase3A replay。
