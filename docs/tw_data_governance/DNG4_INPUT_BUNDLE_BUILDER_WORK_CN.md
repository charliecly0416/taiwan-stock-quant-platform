# DNG4 StrategyInputBundle / ReplayInputBundle Builder 工作文档

生成日期：2026-06-29

## 1. 背景

DNG3 审查结论：

```text
PASS_WITH_CONDITIONS_GO_DNG4
```

条件：

- `can_continue_to_model_b_ltr=false`，不得宣称 LTR Model B ready；
- DNG4 可以做 bundle contract / builder；
- 不得做模型 score、策略收益回放、shadow execution、publish 或 latest switch。

## 2. 目标

建立标准 StrategyInputBundle 和 ReplayInputBundle builder / validator，让后续策略、回放、shadow 不再直接读取散落路径。

## 3. 必须生成

脚本：

```text
scripts/build_tw_strategy_input_bundle.py
scripts/validate_tw_strategy_input_bundle.py
scripts/build_tw_replay_input_bundle.py
scripts/validate_tw_replay_input_bundle.py
```

产物：

```text
data_tw/artifacts/strategy_input_bundles/{bundle_id}/{run_id}/manifest.json
data_tw/artifacts/strategy_input_bundles/{bundle_id}/{run_id}/signals.csv
data_tw/artifacts/strategy_input_bundles/{bundle_id}/{run_id}/current_holdings.csv
data_tw/artifacts/strategy_input_bundles/{bundle_id}/{run_id}/price_context.csv
data_tw/artifacts/strategy_input_bundles/{bundle_id}/{run_id}/market_context.csv
data_tw/artifacts/strategy_input_bundles/{bundle_id}/{run_id}/calendar.csv
data_tw/artifacts/strategy_input_bundles/{bundle_id}/{run_id}/dependency_readiness.json
data_tw/artifacts/strategy_input_bundles/{bundle_id}/{run_id}/lineage.json
data_tw/artifacts/strategy_input_bundles/{bundle_id}/{run_id}/validator_report.json
data_tw/artifacts/replay_input_bundles/{bundle_id}/{run_id}/manifest.json
data_tw/artifacts/replay_input_bundles/{bundle_id}/{run_id}/order_intents.csv 或 empty_order_intents.csv
data_tw/artifacts/replay_input_bundles/{bundle_id}/{run_id}/price_store_ref.json
data_tw/artifacts/replay_input_bundles/{bundle_id}/{run_id}/cost_config.json
data_tw/artifacts/replay_input_bundles/{bundle_id}/{run_id}/initial_portfolio_state.json
data_tw/artifacts/replay_input_bundles/{bundle_id}/{run_id}/market_calendar.csv
data_tw/artifacts/replay_input_bundles/{bundle_id}/{run_id}/execution_availability_audit.csv
data_tw/artifacts/replay_input_bundles/{bundle_id}/{run_id}/dependency_readiness.json
data_tw/artifacts/replay_input_bundles/{bundle_id}/{run_id}/lineage.json
data_tw/artifacts/replay_input_bundles/{bundle_id}/{run_id}/validator_report.json
data_tw/catalog/dng4_input_bundle_validation.json
docs/tw_data_governance/DNG4_INPUT_BUNDLE_BUILDER_EXECUTION_REPORT_CN.md
```

## 4. 输入来源

优先使用当前已规范化或 catalog 中记录的本地产物：

```text
data_tw/catalog/data_catalog.json
data_tw/catalog/latest_status.json
data_tw/catalog/readiness_matrix/2026-06-25/price_market_calendar.json
data_tw/catalog/readiness_matrix/2026-06-25/orthogonal_feature_store.json
data_tw/canonical/price_store/tw_equity_daily/dng2_r_price_market_calendar_20260625/
data_tw/canonical/market_feature_store/twii_daily/dng2_r_price_market_calendar_20260625/
data_tw/canonical/orthogonal_feature_store/daily_orthogonal/dng3_orthogonal_feature_store_20260625/
data_tw/artifacts/signals/**
data_tw/artifacts/order_intents/**
data_tw/artifacts/paper_portfolio/**
```

如果 current holdings 或 order intents 无可用标准源，允许生成 empty/placeholder artifact，但必须标记：

```text
status=PARTIAL_READY
reason=missing_current_holdings_or_order_intents
not_replay_result=true
```

## 5. Bundle 语义

StrategyInputBundle 只表示策略可消费输入，不是买卖建议。

ReplayInputBundle 只表示回放输入准备，不得生成 NAV、收益、turnover 或 performance 结论。

如果 LTR Model B 不 ready，bundle 必须标明：

```text
model_b_ltr_ready=false
fallback_allowed=qlib_only_if_strategy_contract_allows
```

## 6. Validator 要求

Validator 必须检查：

- required files；
- required fields；
- forbidden fields；
- dependency_readiness 存在；
- lineage 存在；
- no order / no broker / no target_position / no target_weight；
- replay bundle 不包含 NAV、daily_return、realized_pnl、performance metrics；
- 如果 partial，必须有 reason。

建议命令：

```text
python scripts/validate_tw_strategy_input_bundle.py --bundle-root <path> --json
python scripts/validate_tw_replay_input_bundle.py --bundle-root <path> --json
```

## 7. 禁止动作

不得执行：

```text
真实抓数
provider refresh / publish
qlib accepted latest switch
readonly latest publish
Agent prompt latest publish
模型训练
模型推理
模型 score 生成
策略收益回放
ReplayResult/NAV 生成
broker/order/quick-trade
target_position / target_weight
```

## 8. 执行报告

报告必须说明：

1. 使用的 signal、price、market、orthogonal 来源。
2. StrategyInputBundle 状态。
3. ReplayInputBundle 状态。
4. partial/missing/fallback 原因。
5. validator 输出。
6. forbidden action audit。
7. 是否建议进入 DNG5 route dependency contract。
