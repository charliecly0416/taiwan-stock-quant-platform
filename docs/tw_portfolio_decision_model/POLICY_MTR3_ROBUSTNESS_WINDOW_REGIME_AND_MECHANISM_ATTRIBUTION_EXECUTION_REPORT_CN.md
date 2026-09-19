# POLICY_MTR3_ROBUSTNESS_WINDOW_REGIME_AND_MECHANISM_ATTRIBUTION_EXECUTION_REPORT_CN

生成日期：2026-06-28

## 1. Verdict

```text
PASS_MTR3_WITH_CONCENTRATION_OR_WINDOW_RISK
```

MTR3 只消费 MTR2_R 已落地 artifacts 做 robustness / window / regime / action-level attribution。未改策略、未调参、未新增候选、未重写 MTR2_R replay 结果，未修改 production/default/frontend/API/Agent/daily/provider/latest。

## 2. Scope

- input_dir: `data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair`
- broad_signal_manifest: `data_tw/artifacts/signals/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025_broad_full_rank_mtr2_r/r1_broad_full_rank_visibility_repair_20260628/manifest.json`
- fixed_candidate: `M2_hold_rank_buffer_100`
- baseline: `baseline_top50_exit_one_worst_sell`
- output_dir: `data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution`

## 3. Documents / Contracts Read

- `docs/tw_portfolio_decision_model/POLICY_MTR3_ROBUSTNESS_WINDOW_REGIME_AND_MECHANISM_ATTRIBUTION_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTR_MECHANISM_TRANSFER_TO_BASELINE_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTR2_R_BROAD_FULL_RANK_VISIBILITY_REPAIR_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTR2_R_BROAD_FULL_RANK_VISIBILITY_REPAIR_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTR2_R_BROAD_FULL_RANK_VISIBILITY_REPAIR_REVIEW_CN.md`
- `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`
- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`

## 4. Input Artifact Lineage

MTR2_R manifest、broad signal manifest、baseline parity、top50 LTR equivalence、non-top50 buy forbidden audit、OrderIntent validator 和 Replay validator 均作为 MTR3 输入 lineage 检查对象。详见 `input_artifact_lineage_audit.csv` 与 `coverage_and_validator_audit.csv`。

## 5. Window Robustness

Full-window 结果：

| metric | baseline | M2_100 | delta |
| --- | ---: | ---: | ---: |
| net_total_return_after_fee_tax | 0.87459073 | 1.32852091 | 0.45393018 |
| average_turnover | 0.17040339 | 0.07651037 | -0.09389302 |
| total_fee_plus_tax | 48476.04 | 23979.01 | -24497.03 |
| max_drawdown | -0.13675456 | -0.10619259 | 0.03056197 |
| hold_buffer_trigger_count | 0 | 61 | 61 |
| non_top50_buy_intent_count | 0 | 0 | 0 |

Monthly positive delta: `3/5`。

## 6. Regime Attribution

Regime 使用 baseline daily_return 做 diagnostic 切片，明确不是策略输入：

- `risk_on`: day_count=45, delta=0.6564897, hold_triggers=38, fee_tax_delta=-15140.25
- `neutral`: day_count=12, delta=0.0431491, hold_triggers=6, fee_tax_delta=-2786.34
- `risk_off`: day_count=22, delta=0.01063245, hold_triggers=17, fee_tax_delta=-6570.45

## 7. Action-level PnL Attribution

`action_level_pnl_attribution.csv` 与 `hold_buffer_trigger_pnl_attribution.csv` 使用 replay 输出侧 actions / daily_nav / position_snapshots 做后验归因，解释 skipped baseline sell、延后换仓、费用节省和持仓保留贡献。该归因没有反馈给策略决策。

## 8. Concentration Audit

- top1_symbol_share: `0.631760`
- top3_symbol_share: `0.972756`
- top1_event_share: `0.300709`

Risks:

- `negative_month_delta_count=2`
- `symbol_concentration_top1=0.632_top3=0.973`
- `event_concentration_top1=0.301`

## 9. Turnover / Fee / Tax Decomposition

详见 `turnover_fee_tax_decomposition.csv`。M2_100 的 turnover 与 fee/tax 下降来自实际 action count、buy/sell notional 与 tax/commission 同步下降，不是报告层重算。

## 10. Forbidden Actions Audit

`forbidden_field_audit.csv` 与 `forbidden_action_audit.csv` 显示：没有训练、调参、后验扩候选、非 top50 买入、production/default/frontend/API/Agent/daily/provider/latest 改动、provider publish、accepted latest switch、monitor、broker/quick-trade、target_weight/target_position，也没有把 replay return 反馈给策略。

## 11. Files Changed

- 新增脚本：`scripts/run_tw_policy_mtr3_robustness_window_regime_and_mechanism_attribution.py`
- 新增执行报告：`docs/tw_portfolio_decision_model/POLICY_MTR3_ROBUSTNESS_WINDOW_REGIME_AND_MECHANISM_ATTRIBUTION_EXECUTION_REPORT_CN.md`
- 新增 MTR3 artifacts:

- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution/manifest.json`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution/input_artifact_lineage_audit.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution/window_robustness_summary.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution/monthly_return_comparison.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution/regime_attribution_summary.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution/drawdown_segment_attribution.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution/action_level_pnl_attribution.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution/hold_buffer_trigger_pnl_attribution.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution/missed_replacement_opportunity_audit.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution/symbol_concentration_audit.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution/event_concentration_audit.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution/turnover_fee_tax_decomposition.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution/position_overlap_timeseries.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution/coverage_and_validator_audit.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution/forbidden_field_audit.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution/forbidden_action_audit.csv`

## 12. Recommendation

建议先让审查者重点审查窗口/集中度风险；若风险可接受，再进入 MTR4 readiness design，仍不得直接切生产。
