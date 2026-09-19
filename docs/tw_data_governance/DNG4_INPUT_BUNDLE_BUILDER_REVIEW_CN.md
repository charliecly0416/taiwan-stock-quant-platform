# DNG4 Input Bundle Builder 审查报告

生成日期：2026-06-29T07:09:14+00:00

## 1. 结论

```text
PASS_WITH_CONDITIONS_GO_DNG5
```

DNG4 已建立 StrategyInputBundle / ReplayInputBundle 的 builder、validator、manifest、dependency_readiness、lineage、validator_report 与 catalog 汇总证据。两个目标 bundle 的 validator 均通过，且 bundle 明确保持输入语义，没有生成订单、目标仓位、模型推理、策略回放或收益产物。

但本轮产物状态均为 `PARTIAL_READY`，不能进入 Model B LTR、OrderIntent、ReplayResult、shadow execution、publish 或 latest switch。DNG5 只允许继续做 RouteDataDependencyContract / gate 设计。

## 2. 审查范围

已按要求阅读：

```text
docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md
docs/tw_data_governance/DNG4_INPUT_BUNDLE_BUILDER_WORK_CN.md
docs/tw_data_governance/DNG4_INPUT_BUNDLE_BUILDER_REVIEW_WORK_CN.md
docs/tw_data_governance/DNG4_INPUT_BUNDLE_BUILDER_EXECUTION_REPORT_CN.md
scripts/build_tw_strategy_input_bundle.py
scripts/validate_tw_strategy_input_bundle.py
scripts/build_tw_replay_input_bundle.py
scripts/validate_tw_replay_input_bundle.py
data_tw/artifacts/strategy_input_bundles/top50_exit_one_worst_sell_dng4_contract/dng4_strategy_input_bundle_20260625/
data_tw/artifacts/replay_input_bundles/top50_exit_one_worst_sell_dng4_replay_contract/dng4_replay_input_bundle_20260625/
data_tw/catalog/dng4_input_bundle_validation.json
```

审查动作仅限本地文件读取、静态检查、py_compile 与 validator。未抓数、未训练、未推理、未 score、未回放、未 publish、未切 latest。

## 3. Validator 结果

已运行：

```text
python -m py_compile scripts/build_tw_strategy_input_bundle.py scripts/validate_tw_strategy_input_bundle.py scripts/build_tw_replay_input_bundle.py scripts/validate_tw_replay_input_bundle.py
python scripts/validate_tw_strategy_input_bundle.py --bundle-root data_tw/artifacts/strategy_input_bundles/top50_exit_one_worst_sell_dng4_contract/dng4_strategy_input_bundle_20260625 --json
python scripts/validate_tw_replay_input_bundle.py --bundle-root data_tw/artifacts/replay_input_bundles/top50_exit_one_worst_sell_dng4_replay_contract/dng4_replay_input_bundle_20260625 --json
```

结果：

| 检查项 | 结果 |
| --- | --- |
| py_compile | PASS |
| StrategyInputBundle validator | `ok=true`, `errors=[]`, `status=PARTIAL_READY` |
| ReplayInputBundle validator | `ok=true`, `errors=[]`, `status=PARTIAL_READY` |
| catalog validation | `ok=true`, `status=PARTIAL_READY` |

说明：validator 脚本会按现有实现刷新 `validator_report.json`、`data_tw/catalog/dng4_input_bundle_validation.json` 与执行报告的 `generated_at`。本审查没有修改 bundle 语义。

## 4. StrategyInputBundle 审查

路径：

```text
data_tw/artifacts/strategy_input_bundles/top50_exit_one_worst_sell_dng4_contract/dng4_strategy_input_bundle_20260625/
```

必需文件存在：

```text
manifest.json
signals.csv
current_holdings.csv
price_context.csv
market_context.csv
calendar.csv
dependency_readiness.json
lineage.json
validator_report.json
```

审查结论：

- `artifact_type=strategy_input_bundle`，语义是策略输入包，不是买卖建议。
- `readonly_only=true`、`no_order=true`、`no_target_position=true`、`no_target_weight=true`、`not_investment_advice=true`。
- `signals.csv` 表头未包含 `target_position`、`target_weight`、broker/order、NAV、收益、PnL、future label 等 forbidden 字段。
- `current_holdings.csv` 是 placeholder 语义，`partial_reason=missing_current_holdings_or_order_intents`。
- `model_b_ltr_ready=false`，`fallback_allowed=qlib_only_if_strategy_contract_allows`。
- `dependency_readiness.json` 明确阻断 `can_continue_to_replay=false`，并记录 `model_signal_asof_lags_price_market_asof`、`missing_current_holdings_or_order_intents`、`orthogonal_feature_store_partial_ready`、`can_continue_to_model_b_ltr_false`。

保留条件：

- 当前 signal 来源为 `2026-06-17` Model A artifact，而 bundle asof 为 `2026-06-25`；该差异已被标记为 blocker，不能解释成 2026-06-25 ModelSignalArtifact ready。
- 当前 holdings 不是真实标准 PortfolioState artifact；不得据此生成 OrderIntent 或策略执行结果。

## 5. ReplayInputBundle 审查

路径：

```text
data_tw/artifacts/replay_input_bundles/top50_exit_one_worst_sell_dng4_replay_contract/dng4_replay_input_bundle_20260625/
```

必需文件存在：

```text
manifest.json
empty_order_intents.csv
price_store_ref.json
cost_config.json
initial_portfolio_state.json
market_calendar.csv
execution_availability_audit.csv
dependency_readiness.json
lineage.json
validator_report.json
```

审查结论：

- `artifact_type=replay_input_bundle`，且 `not_replay_result=true`。
- `empty_order_intents.csv` 只有 schema header，row count 为 0；未生成实际 order intents。
- manifest 明确 `no_nav=true`、`no_performance_metrics=true`、`no_order=true`、`no_target_position=true`、`no_target_weight=true`。
- 目录中未发现 `daily_nav.csv`、`summary.csv`、`position_snapshots.csv`、`daily_return`、`realized_pnl`、`total_return`、`max_drawdown` 等 ReplayResult / performance 产物。
- `cost_config.json` 仅是 contract placeholder，写明未执行 DNG4 回放、未计算 fee/tax、未 mark-to-market。
- `dependency_readiness.json` 明确 `can_continue_to_replay_execution=false`，阻断原因为 `missing_current_holdings_or_order_intents`、`latest_next_day_execution_pending`、`orthogonal_feature_store_partial_ready`。

保留条件：

- ReplayInputBundle 只能证明回放输入合同已物化，不能证明 replay 可执行，更不能证明策略收益、NAV 或 performance。
- 2026-06-25 的 next-day execution availability 仍是 blocker，进入任何 replay execution 前必须重新验证。

## 6. Partial / Fallback / LTR 状态

Partial 与 fallback 标记是清楚的：

- StrategyInputBundle：`status=PARTIAL_READY`，`partial_reason=missing_current_holdings_or_order_intents`。
- ReplayInputBundle：`status=PARTIAL_READY`，`partial_reason=missing_current_holdings_or_order_intents`。
- LTR：`model_b_ltr_ready=false`。
- fallback：`fallback_allowed=qlib_only_if_strategy_contract_allows`，没有静默把 qlib-only 冒充为 qlib+LTR ready。
- 主要 blocker：2026-06-25 ModelSignalArtifact 缺失、current holdings/order intents 缺失、DNG3 正交数据 blocker、next-day execution pending。

## 7. Forbidden Action Audit

审查未发现 forbidden action 被触发。manifest、lineage、dependency_readiness、validator_report 与 catalog 中以下 flag 均为 false：

```text
real_data_fetch_triggered
provider_refresh_triggered
provider_publish_triggered
qlib_accepted_latest_switched
readonly_latest_published
agent_prompt_published
model_training_triggered
model_inference_triggered
strategy_replay_triggered
broker_order_quick_trade_triggered
target_position_or_weight_generated
```

脚本静态审查也未发现 builder 调用 provider refresh/publish、训练、推理、score、回放或 latest switch。builder 只复制/过滤本地既有 artifact，写入 placeholder、manifest、lineage 与 readiness。

## 8. DNG5 进入条件

允许进入 DNG5，但范围限定为：

```text
RouteDataDependencyContract
dependency gate schema
allowed fallback / blocker 表达
validator / static gate 设计
```

不得进入：

```text
Model B LTR
OrderIntentArtifact 生成
Replay execution
ReplayResult / NAV / performance
shadow execution
readonly latest publish
Agent prompt latest publish
formal qlib accepted latest switch
production/default model or strategy switch
broker/order/quick-trade
```

后续若要解除条件，至少需要重新提供并验证：

```text
2026-06-25 标准 ModelSignalArtifact
标准 PortfolioState / current holdings artifact
标准 OrderIntentArtifact
DNG3 正交数据 blocker 修复证据
next-day execution availability ready 证据
对应 validator_report 与 lineage
```
