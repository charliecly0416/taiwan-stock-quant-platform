# DNG4 Input Bundle Builder 执行报告

生成日期：2026-06-29T07:09:14+00:00

## 1. 输入来源

- signal：`data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_a`
- price：`data_tw/canonical/price_store/tw_equity_daily/dng2_r_price_market_calendar_20260625`
- market：`data_tw/canonical/market_feature_store/twii_daily/dng2_r_price_market_calendar_20260625`
- orthogonal：`data_tw/canonical/orthogonal_feature_store/daily_orthogonal/dng3_orthogonal_feature_store_20260625`

## 2. StrategyInputBundle 状态

- root：`data_tw/artifacts/strategy_input_bundles/top50_exit_one_worst_sell_dng4_contract/dng4_strategy_input_bundle_20260625`
- status：`PARTIAL_READY`
- ok：`True`
- partial reason：`missing_current_holdings_or_order_intents; model_signal_asof_lags_price_market_asof; can_continue_to_model_b_ltr=false`

## 3. ReplayInputBundle 状态

- root：`data_tw/artifacts/replay_input_bundles/top50_exit_one_worst_sell_dng4_replay_contract/dng4_replay_input_bundle_20260625`
- status：`PARTIAL_READY`
- ok：`True`
- partial reason：`empty_order_intents placeholder; no ReplayResult/NAV generated; next-day execution remains blocked for 2026-06-25`

## 4. Validator 输出

```json
{
  "forbidden_action_flags": {
    "agent_prompt_published": false,
    "broker_order_quick_trade_triggered": false,
    "model_inference_triggered": false,
    "model_training_triggered": false,
    "provider_publish_triggered": false,
    "provider_refresh_triggered": false,
    "qlib_accepted_latest_switched": false,
    "readonly_latest_published": false,
    "real_data_fetch_triggered": false,
    "strategy_replay_triggered": false,
    "target_position_or_weight_generated": false
  },
  "generated_at": "2026-06-29T07:09:14+00:00",
  "ok": true,
  "replay_input_bundle": {
    "asof": "2026-06-25",
    "bundle_id": "top50_exit_one_worst_sell_dng4_replay_contract",
    "bundle_root": "data_tw/artifacts/replay_input_bundles/top50_exit_one_worst_sell_dng4_replay_contract/dng4_replay_input_bundle_20260625",
    "errors": [],
    "forbidden_action_flags": {
      "agent_prompt_published": false,
      "broker_order_quick_trade_triggered": false,
      "model_inference_triggered": false,
      "model_training_triggered": false,
      "provider_publish_triggered": false,
      "provider_refresh_triggered": false,
      "qlib_accepted_latest_switched": false,
      "readonly_latest_published": false,
      "real_data_fetch_triggered": false,
      "strategy_replay_triggered": false,
      "target_position_or_weight_generated": false
    },
    "generated_at": "2026-06-29T07:09:14+00:00",
    "not_replay_result": true,
    "ok": true,
    "partial_reason": "missing_current_holdings_or_order_intents",
    "required_paths": {
      "cost_config.json": "data_tw/artifacts/replay_input_bundles/top50_exit_one_worst_sell_dng4_replay_contract/dng4_replay_input_bundle_20260625/cost_config.json",
      "dependency_readiness.json": "data_tw/artifacts/replay_input_bundles/top50_exit_one_worst_sell_dng4_replay_contract/dng4_replay_input_bundle_20260625/dependency_readiness.json",
      "empty_order_intents.csv": "data_tw/artifacts/replay_input_bundles/top50_exit_one_worst_sell_dng4_replay_contract/dng4_replay_input_bundle_20260625/empty_order_intents.csv",
      "execution_availability_audit.csv": "data_tw/artifacts/replay_input_bundles/top50_exit_one_worst_sell_dng4_replay_contract/dng4_replay_input_bundle_20260625/execution_availability_audit.csv",
      "initial_portfolio_state.json": "data_tw/artifacts/replay_input_bundles/top50_exit_one_worst_sell_dng4_replay_contract/dng4_replay_input_bundle_20260625/initial_portfolio_state.json",
      "lineage.json": "data_tw/artifacts/replay_input_bundles/top50_exit_one_worst_sell_dng4_replay_contract/dng4_replay_input_bundle_20260625/lineage.json",
      "manifest.json": "data_tw/artifacts/replay_input_bundles/top50_exit_one_worst_sell_dng4_replay_contract/dng4_replay_input_bundle_20260625/manifest.json",
      "market_calendar.csv": "data_tw/artifacts/replay_input_bundles/top50_exit_one_worst_sell_dng4_replay_contract/dng4_replay_input_bundle_20260625/market_calendar.csv",
      "price_store_ref.json": "data_tw/artifacts/replay_input_bundles/top50_exit_one_worst_sell_dng4_replay_contract/dng4_replay_input_bundle_20260625/price_store_ref.json",
      "validator_report.json": "data_tw/artifacts/replay_input_bundles/top50_exit_one_worst_sell_dng4_replay_contract/dng4_replay_input_bundle_20260625/validator_report.json"
    },
    "row_counts": {
      "empty_order_intents.csv": 0,
      "execution_availability_audit": 150,
      "market_calendar": 2789
    },
    "run_id": "dng4_replay_input_bundle_20260625",
    "schema_version": "v1.dng4.replay_input_bundle.validation",
    "selected_order_intents": "data_tw/artifacts/replay_input_bundles/top50_exit_one_worst_sell_dng4_replay_contract/dng4_replay_input_bundle_20260625/empty_order_intents.csv",
    "status": "PARTIAL_READY",
    "warnings": [
      "empty_order_intents.csv placeholder is present; replay execution remains blocked"
    ]
  },
  "schema_version": "v1.dng4.input_bundle.validation_catalog",
  "status": "PARTIAL_READY",
  "strategy_input_bundle": {
    "asof": "2026-06-25",
    "bundle_id": "top50_exit_one_worst_sell_dng4_contract",
    "bundle_root": "data_tw/artifacts/strategy_input_bundles/top50_exit_one_worst_sell_dng4_contract/dng4_strategy_input_bundle_20260625",
    "errors": [],
    "fallback_allowed": "qlib_only_if_strategy_contract_allows",
    "forbidden_action_flags": {
      "agent_prompt_published": false,
      "broker_order_quick_trade_triggered": false,
      "model_inference_triggered": false,
      "model_training_triggered": false,
      "provider_publish_triggered": false,
      "provider_refresh_triggered": false,
      "qlib_accepted_latest_switched": false,
      "readonly_latest_published": false,
      "real_data_fetch_triggered": false,
      "strategy_replay_triggered": false,
      "target_position_or_weight_generated": false
    },
    "generated_at": "2026-06-29T07:09:14+00:00",
    "model_b_ltr_ready": false,
    "ok": true,
    "partial_reason": "missing_current_holdings_or_order_intents",
    "required_paths": {
      "calendar.csv": "data_tw/artifacts/strategy_input_bundles/top50_exit_one_worst_sell_dng4_contract/dng4_strategy_input_bundle_20260625/calendar.csv",
      "current_holdings.csv": "data_tw/artifacts/strategy_input_bundles/top50_exit_one_worst_sell_dng4_contract/dng4_strategy_input_bundle_20260625/current_holdings.csv",
      "dependency_readiness.json": "data_tw/artifacts/strategy_input_bundles/top50_exit_one_worst_sell_dng4_contract/dng4_strategy_input_bundle_20260625/dependency_readiness.json",
      "lineage.json": "data_tw/artifacts/strategy_input_bundles/top50_exit_one_worst_sell_dng4_contract/dng4_strategy_input_bundle_20260625/lineage.json",
      "manifest.json": "data_tw/artifacts/strategy_input_bundles/top50_exit_one_worst_sell_dng4_contract/dng4_strategy_input_bundle_20260625/manifest.json",
      "market_context.csv": "data_tw/artifacts/strategy_input_bundles/top50_exit_one_worst_sell_dng4_contract/dng4_strategy_input_bundle_20260625/market_context.csv",
      "price_context.csv": "data_tw/artifacts/strategy_input_bundles/top50_exit_one_worst_sell_dng4_contract/dng4_strategy_input_bundle_20260625/price_context.csv",
      "signals.csv": "data_tw/artifacts/strategy_input_bundles/top50_exit_one_worst_sell_dng4_contract/dng4_strategy_input_bundle_20260625/signals.csv",
      "validator_report.json": "data_tw/artifacts/strategy_input_bundles/top50_exit_one_worst_sell_dng4_contract/dng4_strategy_input_bundle_20260625/validator_report.json"
    },
    "row_counts": {
      "calendar": 2789,
      "current_holdings": 1,
      "market_context": 1,
      "price_context": 150,
      "signals": 150
    },
    "run_id": "dng4_strategy_input_bundle_20260625",
    "schema_version": "v1.dng4.strategy_input_bundle.validation",
    "status": "PARTIAL_READY",
    "warnings": []
  }
}
```

## 5. Forbidden Action Audit

本轮只读取本地既有 artifact 并生成 bundle/validator/report。未执行真实抓数、provider refresh/publish、accepted latest switch、readonly/Agent publish、模型训练、模型推理、模型 score 生成、策略收益回放、ReplayResult/NAV、broker/order/quick-trade、target_position 或 target_weight。

## 6. DNG5 建议

建议进入 DNG5 route dependency contract，但仅限 contract/gate 设计。不得进入 Model B LTR、order intent 生成、replay execution、shadow execution 或 publish，直到 current holdings/order intents、2026-06-25 ModelSignalArtifact、DNG3 blockers 与 next-day execution availability 被修复并重新验证。
