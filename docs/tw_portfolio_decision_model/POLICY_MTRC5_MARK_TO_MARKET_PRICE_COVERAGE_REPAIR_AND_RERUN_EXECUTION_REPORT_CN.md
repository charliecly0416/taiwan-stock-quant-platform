# POLICY_MTRC5_MARK_TO_MARKET_PRICE_COVERAGE_REPAIR_AND_RERUN_EXECUTION_REPORT_CN

生成时间：2026-06-28T17:43:45+00:00

## 1. Scope

本阶段只修复 mark-to-market close coverage，并在固定 MTRC2_S OrderIntent 与 MTRC2_T_R execution join / next_open 的前提下重跑 readonly ReplayResultArtifact 和 diagnostic。未修改 OrderIntent 或 ModelSignal，未生成 ledger，未写正式 PriceStore、registry/config、provider/latest/default/frontend/API/Agent/daily/production，未执行 broker、quick-trade 或真实交易。

## 2. Inputs

- MTRC2_S OrderIntent manifest：`data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_s_same_signal_order_intent_build/manifest.json`
- MTRC2_S OrderIntent rows：`data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_s_same_signal_order_intent_build/order_intents.csv`
- MTRC2_T_R execution join audit：`data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_r_pricestore_bridge_or_readiness_repair/order_intent_price_join_audit.csv`
- MTRC2_U replay baseline for required mark universe：`data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_u_same_signal_readonly_replay_build/manifest.json`
- MTRC3 diagnostic baseline for comparison：`data_tw/experiments/policy_mtr_research_only_continuation/mtrc3_extended_concentration_window_diagnostic/manifest.json`
- MTRC5 repaired mark bridge：`data_tw/experiments/policy_mtr_research_only_continuation/mtrc5_mark_to_market_price_coverage_repair_and_rerun/mark_price_bridge.csv`

## 3. Replay Results

```text
verdict = PASS_MARK_QUALITY_REPAIRED_READY_FOR_REVIEW
final_equity = 2765375861.077763
total_return = 2764.3758610778
max_drawdown = -0.3928470036
action_count = 2129
buy_count = 1069
sell_count = 1060
skipped_action_count = 249
max_holding_count = 10
duplicate_position_count = 0
negative_cash_count = 0
missing_price_count = 0
```

## 4. Mark Coverage

```text
same_day_mark_coverage_ratio = 1.0
same_day_mark_coverage_gate = pass
final_date_same_day_mark_coverage_ratio = 1.0
final_date_same_day_mark_coverage_gate = pass
max_mark_lag_days = 0
max_mark_lag_days_gate = pass
```

## 5. Validator

```text
blocking_reasons = []
execution_date_gt_signal_date = True
active_action_quantity_gt_0 = True
max_holding_count_lte_10 = True
negative_cash_count_equals_0 = True
duplicate_position_count_equals_0 = True
required_replay_files_present = True
```

## 6. Boundaries

Replay 输出中的 quantity、execution_price、cash、NAV、position、PnL 只存在于 MTRC5 ReplayResult 产物内。它们未回写 OrderIntent 或 ModelSignal，未作为 ranking 输入，也不构成 target_weight/target_position 指令或生产 readiness。
