# Phase3A2 Full Daily Replay 执行报告

生成时间：2026-06-13T19:12:46+00:00

## 1. 本轮目标

按 Phase3A2 文档，先确认 Top50 adaptive 权威完整日频回放口径，并检查是否能把全部 required methods 放入同一口径。Phase3B 暂停。

## 2. 权威 Top50 Adaptive 日频回放口径来源

- 权威候选脚本：`scripts/run_tw_rank_rotation_stress_replay.py`
- `close_after(asof)` / local Yahoo-adjusted price / initial cash / lot size / fee rate / sell tax / equity curve / max drawdown / adaptive_score 检查：`True`
- 结论：该脚本是当前可定位的 Top50 adaptive 完整日频组合回放口径。

## 3. 是否复用权威脚本

本轮只复用其作为权威口径来源进行可执行性诊断；没有改动 `scripts/run_tw_rank_rotation_stress_replay.py`，也没有运行局部替代回放。

## 4. 停止原因

`confirmed_exit` 的完整日频 replay 口径未能在权威脚本中定位。Phase1 中的 `confirmed_exit_baseline` 是 rank / TopK 层面的代理分数，不是带现金、价格、费用、税费、动作和权益曲线的日频组合回放。

因此，按 Phase3A2 文档“如果 `confirmed_exit` 权威口径无法在同一引擎中定位，必须停下说明原因；不得继续以 blocked 带过”，本轮停止，不构造不完整对照。

## 5. 输入路径与覆盖诊断

- Historical signal root：`qlib_pipeline/data_tw/experiments/option_c_historical_signal_backfill`
- accepted signal runs：`1360`，范围 `2022-01-03` 到 `2026-05-29`
- Price root：`qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized`
- Price files：`150`，范围 `2015-01-05` 到 `2026-06-12`
- Frozen Phase1C score：`data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv`，rows `152249`，score col present `True`

## 6. 方法对照总表

| method | comparison_status | reason |
| --- | --- | --- |
| rank_rotate_top30 | authority_available_not_run | Authoritative daily replay engine located, but Phase3A2 stops before partial replay because confirmed_exit cannot be completed in the same engine. |
| rank_rotate_top50 | authority_available_not_run | Authoritative daily replay engine located, but Phase3A2 stops before partial replay because confirmed_exit cannot be completed in the same engine. |
| rank_rotate_top50_adaptive_score | authority_available_not_run | Authoritative daily replay engine located, but Phase3A2 stops before partial replay because confirmed_exit cannot be completed in the same engine. |
| confirmed_exit | missing_authoritative_daily_replay | No confirmed_exit method/function was found in scripts/run_tw_rank_rotation_stress_replay.py; Phase1 confirmed_exit_baseline is rank-quality proxy, not full daily replay. |
| phase1c_ltr_simple_daily | blocked_by_incomplete_required_baseline | LTR daily replay must share the same complete baseline set; stopped before constructing partial comparison. |
| phase1c_ltr_turnover_controlled_daily | blocked_by_incomplete_required_baseline | LTR daily replay must share the same complete baseline set; stopped before constructing partial comparison. |

## 7. 区间覆盖表

| period | start_date | end_date | accepted_signal_days | comparison_status |
| --- | --- | --- | --- | --- |
| 2022_full_available_replay_range | 2022-01-01 | 2022-12-31 | 297 | blocked_incomplete_confirmed_exit_daily_replay |
| 2025_full_available_replay_range | 2025-01-01 | 2025-12-31 | 242 | blocked_incomplete_confirmed_exit_daily_replay |
| 2026_ytd_available_replay_range | 2026-01-01 | 2026-06-13 | 97 | blocked_incomplete_confirmed_exit_daily_replay |
| phase1c_validation_range | 2024-08-12 | 2025-06-24 | 210 | blocked_incomplete_confirmed_exit_daily_replay |
| phase1c_independent_test_range | 2025-06-25 | 2026-05-07 | 211 | blocked_incomplete_confirmed_exit_daily_replay |
| common_full_range_shared_by_all_compared_methods | 2022-01-01 | 2026-05-07 | 1344 | blocked_incomplete_confirmed_exit_daily_replay |

## 8. 产物路径

- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_method_comparison.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_period_comparison.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_equity_curves.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_actions_summary.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_data_quality.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_gate_summary.json`

## 9. Gate 结论

`stop_phase3a2_incomplete_baseline_or_data`

原因：confirmed_exit authoritative full daily replay could not be located in the Top50 adaptive daily replay engine; Phase3A2 cannot proceed with incomplete baseline comparison.

## 10. 是否建议恢复 Phase3B

不建议。本轮未完成 Top50 adaptive / confirmed_exit / LTR simple / LTR turnover-controlled 的同口径日频回放，不能进入只读解释层。

## 11. 验证命令与结果

- `python -m py_compile scripts/evaluate_tw_ltr_phase3a2_full_daily_replay.py`：通过。
- `python scripts/evaluate_tw_ltr_phase3a2_full_daily_replay.py`：通过；普通沙箱若触发 `bwrap` 环境限制，则同一只读/写本轮产物命令经授权在沙箱外复跑。
- 文本与安全边界扫描：仅允许命中出现在安全说明或禁止事项中。

## 12. Safety Boundary

本轮未执行 Phase3B，未改 frontend / API / monitor / database，未新增数据源，未联网，未 provider refresh / publish，未 accepted latest switching，未重新训练 LTR，未重建 Phase1C score，未重新打开 regime gate，未接 broker / quick-trade / orders / target position / target weight，未输出真实买入、卖出、持有、仓位建议、收益更优、胜率或上涨概率语义。
