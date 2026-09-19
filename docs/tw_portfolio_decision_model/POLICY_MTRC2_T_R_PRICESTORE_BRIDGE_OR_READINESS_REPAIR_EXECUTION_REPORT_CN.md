# POLICY_MTRC2_T_R_PRICESTORE_BRIDGE_OR_READINESS_REPAIR_EXECUTION_REPORT_CN

生成时间：2026-06-28T16:26:38+00:00

## 1. Scope

本阶段执行 `MTRC2_T_R_PRICESTORE_BRIDGE_OR_READINESS_REPAIR`，只生成隔离的 research-only price bridge/readiness 产物，为 MTRC2_S `order_intents.csv` 每条 intent 审计 `signal_date` 之后下一可交易日 `next_open`。

未生成 ReplayResult、ledger、summary/actions/daily_nav/position snapshots；未运行收益 replay；未计算收益、回撤、集中度、rolling window 或 risk-off；未写正式 PriceStore、registry/config、provider/latest/default/frontend/API/Agent/daily/production；未 broker/order、target_weight、target_position 或 quantity instruction。

## 2. 变更

- 新增 builder：`scripts/build_tw_policy_mtrc2_t_r_pricestore_bridge_or_readiness_repair.py`
- 生成 MTRC2_T_R 授权目录下 price bridge/readiness/audit/validator 产物。
- 写入本执行报告。

## 3. 价格覆盖结果

```text
required_order_intent_count = 2378
available_next_open_count = 2378
order_intent_next_open_coverage = 2378/2378
missing_price_file_count = 0
missing_next_open_count = 0
price_row_count = 2378
price_date_range = 2017-01-11..2026-05-08
selected_source_counts = {"staged_candidate_normalized": 763, "stock_price_bridge": 1615}
```

来源选择：优先使用已有 `stock_price_bridge`；其缺口由已存在 staged local `candidate_normalized` OHLC source 补齐。`data_tw/self_contained_demo/normalized` 已审计为 invalid，未用于 `prices.csv`。

## 4. 产物路径

- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_r_pricestore_bridge_or_readiness_repair/manifest.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_r_pricestore_bridge_or_readiness_repair/prices.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_r_pricestore_bridge_or_readiness_repair/schema.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_r_pricestore_bridge_or_readiness_repair/source_inventory.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_r_pricestore_bridge_or_readiness_repair/source_selection_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_r_pricestore_bridge_or_readiness_repair/coverage_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_r_pricestore_bridge_or_readiness_repair/execution_availability_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_r_pricestore_bridge_or_readiness_repair/adjustment_audit.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_r_pricestore_bridge_or_readiness_repair/order_intent_price_join_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_r_pricestore_bridge_or_readiness_repair/missing_price_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_r_pricestore_bridge_or_readiness_repair/missing_next_open_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_r_pricestore_bridge_or_readiness_repair/invalid_source_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_r_pricestore_bridge_or_readiness_repair/forbidden_field_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_r_pricestore_bridge_or_readiness_repair/forbidden_action_audit.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_r_pricestore_bridge_or_readiness_repair/validator_report.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_r_pricestore_bridge_or_readiness_repair/diagnostic_findings.md`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_t_r_pricestore_bridge_or_readiness_repair/mtrc2_t_rerun_gate_recommendation.md`

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC2_T_R_PRICESTORE_BRIDGE_OR_READINESS_REPAIR_EXECUTION_REPORT_CN.md
```

## 5. Validator 结果

```text
PASS_READY_FOR_MTRC2_T_GATE_RERUN
```

blocking_reasons：`[]`

price_store_ready：`True`

research_only_price_bridge_ready：`True`

## 6. Forbidden Actions Audit

`forbidden_action_audit.json` status：`pass`。所有禁止动作均 `performed=false`，覆盖网络/provider refresh/publish、accepted latest switch、正式 PriceStore/registry/config 写入、ReplayResult/ledger/replay/收益诊断、frontend/API/Agent/daily/production、broker/order/target/quantity，以及 close/same-day open fallback。

## 7. Verdict

```text
PASS_READY_FOR_MTRC2_T_GATE_RERUN
```
