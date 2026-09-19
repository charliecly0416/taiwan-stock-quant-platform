# DNG10 StrategyInputBundle / Readonly Source Context 衔接工作文档

生成日期：2026-06-29

## 1. 背景

DNG9 审查结论：

```text
PASS_WITH_CONDITIONS_GO_DNG10
```

条件：

- 不得放宽 legacy provider/latest；
- 不得发布 readonly latest；
- 不得发布 Agent prompt latest；
- 不得生成订单、target position/weight、replay NAV。

## 2. 目标

用 DNG7 生成的 2026-06-25 Model A signal，重建只读下游输入与 source context：

```text
StrategyInputBundle refresh
ReadonlyStrategySnapshot source context dry-run
Agent DailyPrompt source context dry-run
```

只做 source context / dry-run，不更新任何 latest pointer。

## 3. 必须生成/更新

```text
data_tw/artifacts/strategy_input_bundles/top50_exit_one_worst_sell_dng10_modela/dng10_strategy_input_bundle_20260625/
data_tw/artifacts/readonly_source_context/dng10_modela_20260625/manifest.json
data_tw/artifacts/readonly_source_context/dng10_modela_20260625/context.json
data_tw/artifacts/agent_daily_prompt_source_context/dng10_modela_20260625/manifest.json
data_tw/artifacts/agent_daily_prompt_source_context/dng10_modela_20260625/prompt_source_context.json
data_tw/catalog/dng10_strategy_readonly_context_validation.json
docs/tw_data_governance/DNG10_STRATEGY_READONLY_CONTEXT_EXECUTION_REPORT_CN.md
```

可复用 DNG4 bundle builder/validator。如果需要新增轻量 source context builder/validator，允许新增：

```text
scripts/build_tw_readonly_source_context.py
scripts/validate_tw_readonly_source_context.py
```

## 4. 输入来源

必须使用：

```text
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng7_modela_20260625/
data_tw/canonical/price_store/tw_equity_daily/dng2_r_price_market_calendar_20260625/
data_tw/canonical/market_feature_store/twii_daily/dng2_r_price_market_calendar_20260625/
data_tw/catalog/readiness_matrix/2026-06-25/price_market_calendar.json
data_tw/catalog/readiness_matrix/2026-06-25/orthogonal_feature_store.json
data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/dng8_modelb_ltr_20260625/
```

## 5. 必须标明的状态

```text
signal_asof=2026-06-25
model_a_ready=true
model_b_ltr_ready=false
fallback_model=qlib_only_model_a
readonly_only=true
not_order=true
not_target_position=true
not_target_weight=true
not_replay_result=true
latest_pointer_updated=false
agent_prompt_latest_updated=false
```

## 6. 禁止动作

不得执行：

```text
provider refresh / publish
qlib accepted latest switch
readonly latest publish
Agent prompt latest publish
模型训练
模型调参
模型 score 生成
策略收益回放
ReplayResult/NAV 生成
broker/order/quick-trade
target_position / target_weight
```

## 7. 执行报告

报告必须说明：

1. DNG10 使用的 signal/price/market/source context。
2. StrategyInputBundle 是否从 DNG7 signal 更新到 2026-06-25。
3. readonly source context 与 Agent source context 状态。
4. latest pointer 是否未更新。
5. validator 输出。
6. forbidden action audit。
7. 是否建议进入 DNG11 多日 shadow/observation。
