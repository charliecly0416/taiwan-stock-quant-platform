# Phase S1B5R 执行报告：Baseline Readiness Repair

生成日期：2026-06-14T17:43:15+00:00

## 1. 本轮目标

按 `PHASES1B5_REVIEW_AND_PHASES1B5R_BASELINE_READINESS_REPAIR_WORK_CN.md` 要求，只修复 S1B6 完整日频回放所需的 baseline readiness 与 replay input contract。

## 2. 执行范围

- 读取 `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b4_ltr_training/phase_s1b4_ltr_scores.csv` 与 `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/phase_s1b2_ltr_samples.csv`。
- 按 `date/instrument/split/fold_id` 对齐字段。
- 生成 replay-ready score table。
- 重新冻结 6 个 mandatory baselines 的 readiness。
- 修复 gate 逻辑：任何 blocked baseline 必须阻断。

## 3. Replay-Ready Score Table

- 输出：`data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b5r_baseline_readiness_repair/phase_s1b5r_replay_ready_scores.csv`
- row_count：`298242`
- date_count：`2055`
- duplicate_key_count：`0`
- ltr_score_missing_count：`0`
- ltr_rank_missing_count：`0`
- adaptive_score_missing_count：`0`
- confirmed_exit_missing_count：`0`

Replay-ready strategy fields 包含：

```text
date
instrument
split
fold_id
qlib_score_raw
qlib_rank
ltr_score
ltr_rank
sample_complete
feature_complete
regime_segment
qlib_score_percentile_by_date
qlib_score_zscore_by_date
ret20
volatility20
TWII_ret20
TWII_ret60
market_volatility20
market_drawdown60
market_breadth20
adaptive_score_baseline
confirmed_exit_baseline
```

未来标签字段未进入策略决策字段；它们继续排除在 replay-ready table 之外。

## 4. Baseline Readiness

| baseline | status | note |
| --- | --- | --- |
| qlib_top50_adaptive_baseline | ready | existing local definition reused from scripts/train_tw_ltr_phase1_lambdamart.py and scripts/diagnose_tw_ltr_phase1c_final_repair.py |
| rank_rotate_top50 | ready | same-day qlib rank order, top 50 selection |
| rank_rotate_top30 | ready | same-day qlib rank order, top 30 selection |
| confirmed_exit | ready | existing local definition reused from scripts/train_tw_ltr_phase1_lambdamart.py and scripts/diagnose_tw_ltr_phase1c_final_repair.py |
| split_aligned_ltr_simple | ready | direct common LTR score usage candidate |
| split_aligned_ltr_turnover_controlled | ready | same common LTR score with frozen existing turnover usage-layer constraints |

## 5. Confirmed Exit 定义说明

本轮复用了仓内既有、且在多个历史 LTR 基线脚本中一致出现的 `confirmed_exit_baseline` 定义：

```text
qlib_score_zscore_by_date - 0.25 * 1[market_drawdown60 < -0.08] - 0.10 * volatility20
```

因此本轮没有出现 `confirmed_exit` authority gap，不需要阻断到该分支。

## 6. Gate 修复

本轮已修复 gate 逻辑：

```text
if any mandatory baseline status startswith('blocked'): gate = s1b5_blocked_by_missing_baseline_or_replay_policy
```

只有全部 mandatory baselines ready 时，才允许进入 S1B6。

## 7. 禁止事项执行结果

- 未训练 LTR / qlib。
- 未跑组合回放。
- 未比较策略收益、回撤、换手、动作次数。
- 未调参，未改 feature / label / split / universe。
- 未新增数据源，未联网。
- 未改前端/API，未触发 provider / accepted latest / monitor / trading chain。
- 未输出买卖、持有、仓位、收益承诺、胜率或上涨概率语义。

## 8. 结论

本轮完成 S1B5R baseline readiness repair。

推荐 gate：

```text
s1b5r_baseline_readiness_repair_pass_request_s1b6_full_daily_replay
```
