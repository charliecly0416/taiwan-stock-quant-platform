# DNG10 StrategyInputBundle / Readonly Source Context 执行报告

生成时间：2026-06-29T09:39:23+00:00

执行者：DNG10 Executor

## 1. 结论

本轮完成 DNG10 source context dry-run。

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
validator_status=PASS
```

本轮只读取本地既有 DNG7/DNG8/DNG2 artifact 并生成 source context，不执行 provider refresh/publish、accepted latest switch、readonly latest publish、Agent prompt latest publish、模型训练、调参、score 生成、策略收益回放、ReplayResult/NAV、broker/order/quick-trade、target_position 或 target_weight。

## 2. 使用输入

必读输入已覆盖：

- 主线：`docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md`
- 工作单：`docs/tw_data_governance/DNG10_STRATEGY_READONLY_CONTEXT_WORK_CN.md`
- DNG9 审查：`docs/tw_data_governance/DNG9_DAILY_AUTO_MODEL_SIGNAL_GATE_REVIEW_CN.md`
- Model A signal：`data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng7_modela_20260625/`
- PriceStore：`data_tw/canonical/price_store/tw_equity_daily/dng2_r_price_market_calendar_20260625/`
- TWII MarketFeatureStore：`data_tw/canonical/market_feature_store/twii_daily/dng2_r_price_market_calendar_20260625/`
- Model B ScoreJob blocker：`data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/dng8_modelb_ltr_20260625/`

关键输入状态：

- DNG7 Model A `manifest.json` 显示 `signal_asof=2026-06-25`、`status=READY`、`row_count=150`。
- DNG7 validator 显示 `ok=true`、`signal_rows=150`、`date_min=date_max=2026-06-25`。
- DNG8 Model B `manifest.json` 显示 `status=BLOCKED_INPUT_NOT_READY`、`model_b_ltr_ready=false`，blocking datasets 为 `corporate_actions`、`monthly_revenue`、`valuation`。
- DNG2 PriceStore/TWII 均覆盖 `2026-06-25`，但 next-day execution 对 replay/shadow 仍为 pending，不在 DNG10 生成 ReplayResult。

## 3. 生成产物

已生成：

```text
data_tw/artifacts/strategy_input_bundles/top50_exit_one_worst_sell_dng10_modela/dng10_strategy_input_bundle_20260625/
data_tw/artifacts/readonly_source_context/dng10_modela_20260625/manifest.json
data_tw/artifacts/readonly_source_context/dng10_modela_20260625/context.json
data_tw/artifacts/agent_daily_prompt_source_context/dng10_modela_20260625/manifest.json
data_tw/artifacts/agent_daily_prompt_source_context/dng10_modela_20260625/prompt_source_context.json
data_tw/catalog/dng10_strategy_readonly_context_validation.json
```

新增脚本：

```text
scripts/build_tw_readonly_source_context.py
scripts/validate_tw_readonly_source_context.py
```

StrategyInputBundle 行数：

```text
signals=150
price_context=150
market_context=1
calendar=2789
current_holdings=1 placeholder
```

`current_holdings.csv` 是 DNG10 source-context 占位审计行；本轮没有生成 OrderIntentArtifact。

## 4. Model B blocker 展示

Readonly source context 与 Agent source context 均显式展示：

```text
model_b_ltr_ready=false
model_b_status=BLOCKED_INPUT_NOT_READY
fallback_model=qlib_only_model_a
do_not_substitute_qlib_score_as_ltr_score=true
blocking_datasets=corporate_actions, monthly_revenue, valuation
```

因此 DNG10 没有把 qlib score 冒充为 LTR signal；前端/Agent 只能展示 qlib-only Model A fallback 状态。

## 5. Validator 输出

已运行：

```bash
python scripts/build_tw_readonly_source_context.py --json
python scripts/validate_tw_readonly_source_context.py --json
```

结果：

```text
ok=true
status=PASS
errors=[]
warnings=["current_holdings.csv is a DNG10 placeholder; no OrderIntentArtifact generated"]
signal_asof=2026-06-25
model_a_ready=true
model_b_ltr_ready=false
fallback_model=qlib_only_model_a
latest_pointer_updated=false
readonly_latest_updated=false
agent_prompt_latest_updated=false
```

Validation catalog：

```text
data_tw/catalog/dng10_strategy_readonly_context_validation.json
```

## 6. Forbidden Action Audit

本轮 validator 确认以下 flags 全部为 false：

```text
real_data_fetch_triggered=false
provider_refresh_triggered=false
provider_publish_triggered=false
qlib_accepted_latest_switched=false
readonly_latest_published=false
agent_prompt_published=false
model_training_triggered=false
model_tuning_triggered=false
model_inference_triggered=false
model_score_generated=false
ltr_score_generated=false
strategy_replay_triggered=false
replay_result_nav_generated=false
broker_order_quick_trade_triggered=false
target_position_or_weight_generated=false
```

额外文件检查未发现：

```text
latest.json
order_intents.csv
daily_nav.csv
summary.csv
actions.csv
target_positions.csv
target_weights.csv
```

## 7. DNG11 建议

建议进入 DNG11，但范围必须限定为多日 shadow/observation 与 readiness/dashboard 观察：

- 可观察 Model A signal、StrategyInputBundle、readonly source context、Agent source context 的多日稳定性。
- 不得把 DNG10 source context 通过视为 publish_latest_gate 通过。
- Model B 在 DNG3 external source repair 完成前继续保持 blocker / qlib-only fallback 展示。
- replay/shadow 收益、ReplayResult/NAV、OrderIntentArtifact、target position/weight、readonly latest publish、Agent prompt latest publish 仍需单独 gate 和审查授权。
