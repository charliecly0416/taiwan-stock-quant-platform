# POLICY_MTRC2_U_SAME_SIGNAL_READONLY_REPLAY_BUILD_EXECUTION_REPORT_CN

生成时间：2026-06-28T16:46:56+00:00

## 1. Scope

本阶段生成 readonly、simulation-only、diagnostic-only 的 ReplayResultArtifact。未修改 OrderIntent 或 ModelSignal，未生成 ledger，未写正式 PriceStore、registry/config、provider/latest/default/frontend/API/Agent/daily/production，未执行 broker、quick-trade 或真实交易。

## 2. Inputs

- MTRC2_S OrderIntent manifest：`data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_s_same_signal_order_intent_build/manifest.json`
- MTRC2_S OrderIntent rows：`data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_s_same_signal_order_intent_build/order_intents.csv`
- MTRC2_T_R price bridge manifest：`data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_r_pricestore_bridge_or_readiness_repair/manifest.json`
- MTRC2_T_R prices：`data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_r_pricestore_bridge_or_readiness_repair/prices.csv`
- MTRC2_T_R join audit：`data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_r_pricestore_bridge_or_readiness_repair/order_intent_price_join_audit.csv`
- MTRC2_T gate rerun manifest：`data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_gate_rerun_with_repaired_price_bridge/manifest.json`
- MTRC2_T gate rerun validator：`data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_gate_rerun_with_repaired_price_bridge/validator_report.json`

## 3. Replay Results

```text
verdict = PASS_WITH_REPLAY_WARNINGS_NEEDS_REVIEW
final_equity = 2012130218.262249
total_return = 2011.1302182622
max_drawdown = -0.1990237415
action_count = 2332
buy_count = 1171
sell_count = 1161
skipped_action_count = 46
max_holding_count = 10
duplicate_position_count = 0
negative_cash_count = 0
missing_price_count = 10493
```

## 4. Validator

```text
blocking_reasons = []
execution_date_gt_signal_date = True
active_action_quantity_gt_0 = True
max_holding_count_lte_10 = True
negative_cash_count_equals_0 = True
duplicate_position_count_equals_0 = True
required_replay_files_present = True
```

## 5. Boundaries

Replay 输出中的 quantity、execution_price、cash、NAV、position、PnL 只存在于 MTRC2_U ReplayResult 产物内。它们未回写 OrderIntent 或 ModelSignal，未作为 ranking 输入，也不构成 target_weight/target_position 指令或生产 readiness。
