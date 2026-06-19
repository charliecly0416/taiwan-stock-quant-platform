# Phase 1A POC 样本与单因子 Sanity Check 执行报告

## 1. 执行范围

- 执行日期：`2026-06-10T17:34:56+00:00`
- 阶段目标：构建受限 POC PIT 样本，并对法人筹码、融资融券做单因子 sanity check。
- 本阶段不是完整 Phase1，不允许放行 Phase2。
- 未联网、未重跑 FinMind、未新增数据源、未扩大时间范围或 symbol universe、未启用月营收。
- 未执行：Qlib bin/provider 写入、accepted latest switching、模型训练、规则 baseline、前端/API、broker/orders/quick-trade/target position/target weight。

## 2. 修改文件

- 新增 `scripts/build_tw_decision_orthogonal_phase1a_poc_samples.py`。
- 新增 `docs/tw_decision_model_orthogonal/PHASE1A_EXECUTION_REPORT_CN.md`。

## 3. 生成文件

- `data_tw/experiments/decision_orthogonal/phase1a_poc_samples.parquet`
- `data_tw/experiments/decision_orthogonal/phase1a_poc_samples_preview.csv`
- `data_tw/experiments/decision_orthogonal/phase1a_schema.json`
- `data_tw/experiments/decision_orthogonal/phase1a_factor_increment_report.md`
- `data_tw/experiments/decision_orthogonal/phase1a_leakage_audit_report.md`
- `data_tw/experiments/decision_orthogonal/phase1a_factor_metrics.csv`
- `docs/tw_decision_model_orthogonal/PHASE1A_EXECUTION_REPORT_CN.md`

## 4. 样本构建规则

- 样本粒度：`asof + symbol`。
- asof 来自本地既有 qlib prediction artifacts 的 `datetime`。
- symbol 限制为 Phase0D cleaned archive 中的 50 档 POC universe。
- qlib prediction rows：`3536`；sample rows：`3536`。
- qlib prediction path count in window：`104`。

## 5. PIT Join 规则

- 法人筹码与融资融券均使用 `available_at <= asof` 的最新可见记录。
- 不允许使用 `trade_date == asof` 且 `available_at > asof` 的记录。
- `available_at = next_trading_day(trade_date)` 是 conservative visibility proxy，不是官方发布时间声明。

## 6. Label 定义

- `fwd_5d_excess_return = symbol(asof 后第 5 个交易日 close / asof close - 1) - TWII 同 horizon return`。
- `fwd_10d_excess_return`、`fwd_20d_excess_return` 同理。
- label 从 asof 之后计算，不包含 asof 当日不可见信息。

## 7. 特征清单

- qlib：`qlib_score_raw`、`qlib_rank`、`qlib_score_percentile_by_date`、`qlib_score_zscore_by_date`。
- 法人筹码：外资/投信/自营商/合计净买卖超、5/10/20 日 rolling sum/mean、外资投信同步方向。
- 融资融券：融资余额变化、融券余额变化、5/10/20 日 rolling sum/mean。
- 禁止特征：月营收、无 `available_at` 字段、未来窗口特征、任何模型预测分数以外的新训练输出。

## 8. 覆盖率与缺失率

| month | sample_rows | symbols | asof_days | institutional_available_rate | margin_available_rate | label_5d_non_null_rate | label_10d_non_null_rate | label_20d_non_null_rate |
|---|---|---|---|---|---|---|---|---|
| 2025-05 | 646.000000 | 34.000000 | 19.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| 2025-06 | 714.000000 | 34.000000 | 21.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| 2025-07 | 782.000000 | 34.000000 | 23.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| 2025-08 | 680.000000 | 34.000000 | 20.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| 2025-09 | 714.000000 | 34.000000 | 21.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |

## 9. Leakage Audit 结论

- leakage audit status：`pass`。
| check | bad_rows | pass |
|---|---|---|
| institutional_available_at_lte_asof | 0.000000 | 1.000000 |
| margin_available_at_lte_asof | 0.000000 | 1.000000 |
| same_day_invisible_orthogonal_not_joined | 0.000000 | 1.000000 |
| qlib_predictions_present | 0.000000 | 1.000000 |
| fwd_5d_label_date_gt_asof | 0.000000 | 1.000000 |
| fwd_10d_label_date_gt_asof | 0.000000 | 1.000000 |
| fwd_20d_label_date_gt_asof | 0.000000 | 1.000000 |

## 10. 单因子/分组 Sanity Check

| feature | label | n | valid_periods | value |
|---|---|---|---|---|
| margin_balance_change_20d_sum | fwd_20d_excess_return | 3536.000000 | 104.000000 | 0.153156 |
| margin_balance_change_10d_sum | fwd_20d_excess_return | 3536.000000 | 104.000000 | 0.116380 |
| margin_balance_change_20d_sum | fwd_10d_excess_return | 3536.000000 | 104.000000 | 0.087914 |
| qlib_rank | fwd_10d_excess_return | 3536.000000 | 104.000000 | -0.087333 |
| qlib_score_raw | fwd_10d_excess_return | 3536.000000 | 104.000000 | 0.087301 |
| qlib_score_zscore_by_date | fwd_10d_excess_return | 3536.000000 | 104.000000 | 0.087301 |
| qlib_score_percentile_by_date | fwd_10d_excess_return | 3536.000000 | 104.000000 | 0.087301 |
| qlib_rank | fwd_5d_excess_return | 3536.000000 | 104.000000 | -0.082979 |
| qlib_score_zscore_by_date | fwd_5d_excess_return | 3536.000000 | 104.000000 | 0.082953 |
| qlib_score_percentile_by_date | fwd_5d_excess_return | 3536.000000 | 104.000000 | 0.082953 |
| qlib_score_raw | fwd_5d_excess_return | 3536.000000 | 104.000000 | 0.082953 |
| margin_balance_change_5d_sum | fwd_20d_excess_return | 3536.000000 | 104.000000 | 0.079385 |
| qlib_rank | fwd_20d_excess_return | 3536.000000 | 104.000000 | -0.067617 |
| qlib_score_raw | fwd_20d_excess_return | 3536.000000 | 104.000000 | 0.067610 |
| qlib_score_zscore_by_date | fwd_20d_excess_return | 3536.000000 | 104.000000 | 0.067610 |

## 11. 与 qlib rank 的相关性

| feature | label | n | valid_periods | value |
|---|---|---|---|---|
| institutional_total_net_buy_10d_sum | qlib_score_raw | 3536.000000 | 104.000000 | 0.230094 |
| institutional_total_net_buy_20d_sum | qlib_score_raw | 3536.000000 | 104.000000 | 0.221197 |
| institutional_total_net_buy_10d_sum | qlib_rank | 3536.000000 | 104.000000 | -0.212480 |
| institutional_total_net_buy_5d_sum | qlib_score_raw | 3536.000000 | 104.000000 | 0.205447 |
| institutional_total_net_buy_20d_sum | qlib_rank | 3536.000000 | 104.000000 | -0.203113 |
| institutional_total_net_buy_5d_sum | qlib_rank | 3536.000000 | 104.000000 | -0.188268 |
| foreign_trust_sync_direction | qlib_score_raw | 3536.000000 | 104.000000 | 0.156092 |
| foreign_trust_sync_direction | qlib_rank | 3536.000000 | 104.000000 | -0.148934 |
| institutional_total_net_buy | qlib_score_raw | 3536.000000 | 104.000000 | 0.144904 |
| institutional_total_net_buy | qlib_rank | 3536.000000 | 104.000000 | -0.137271 |
| short_balance_change_20d_sum | qlib_score_raw | 3536.000000 | 104.000000 | 0.123615 |
| investment_trust_net_buy | qlib_score_raw | 3536.000000 | 104.000000 | 0.122821 |
| short_balance_change_20d_sum | qlib_rank | 3536.000000 | 104.000000 | -0.122327 |
| short_balance_change_10d_sum | qlib_score_raw | 3536.000000 | 104.000000 | 0.121935 |
| short_balance_change_10d_sum | qlib_rank | 3536.000000 | 104.000000 | -0.121556 |

## 12. 按月份稳定性

- 详见 `phase1a_factor_metrics.csv` 中 `month != all` 的 RankIC rows。
- 当前仅 2025-05 到 2025-09 的 POC，不足以证明跨年度稳定性。

## 13. Phase 1A Gate 结论

- `request_larger_backfill=true`
- `stop_orthogonal_poc=false`
- `phase1a_incomplete=false`
- `enter_phase2=false`
- `train_model=false`
- `phase1_gate_pass=false`
- reason：POC 有非零 RankIC 或分组差异迹象，但仅覆盖 5 个月/50 档，需要更大范围验证。

## 14. 安全边界

- 禁止联网：未触碰。
- provider refresh/publish：未触碰。
- accepted latest switching：未触碰。
- Qlib bin/provider 写入：未触碰。
- 模型训练：未执行。
- Phase2 规则 baseline：未执行。
- 前端/API：未触碰。
- broker/orders/quick-trade/target position/target weight：未触碰。
- 真实交易建议语义：未生成。

## 15. 需要审查者或用户确认的问题

- 若审查者接受 POC 迹象，下一步只能请求用户授权更长历史/更多 symbols backfill；不能直接进入 Phase2。
- 月营收继续 deferred，除非用户另行授权具备发布时间的数据源。
- T+1 conservative visibility proxy 是否可继续用于更大样本，仍需审查者确认。
