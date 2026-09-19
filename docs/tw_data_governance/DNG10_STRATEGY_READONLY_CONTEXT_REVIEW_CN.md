# DNG10 Strategy / Readonly Source Context 审查报告

生成时间：2026-06-29T09:42:54+00:00

审查者：DNG10 Reviewer

## 1. Verdict

```text
PASS_WITH_CONDITIONS_GO_DNG11
```

DNG10 执行结果通过 source context dry-run 审查，可以进入 DNG11 多日 shadow/observation，但条件是 DNG11 仍只能观察多日 source context / readiness / dashboard 稳定性，不得把本次通过解释为 publish latest、订单、目标仓位、ReplayResult、NAV 或策略绩效放行。

给出带条件通过的原因：DNG10 已把 DNG7 Model A `signal_asof=2026-06-25` 接到 StrategyInputBundle、readonly source context dry-run 和 Agent source context dry-run；validator 复跑通过；Model B blocker 明确保留为 `BLOCKED_INPUT_NOT_READY`，且 qlib-only fallback 未冒充 LTR signal。但本轮产物状态明确是 `READY_FOR_SOURCE_CONTEXT_DRY_RUN`，不是 readonly latest publish、Agent prompt latest publish、OrderIntentArtifact、ReplayResult 或 production readiness。

## 2. 已审查输入

已阅读：

```text
docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md
docs/tw_data_governance/DNG10_STRATEGY_READONLY_CONTEXT_WORK_CN.md
docs/tw_data_governance/DNG10_STRATEGY_READONLY_CONTEXT_REVIEW_WORK_CN.md
docs/tw_data_governance/DNG10_STRATEGY_READONLY_CONTEXT_EXECUTION_REPORT_CN.md
data_tw/artifacts/strategy_input_bundles/top50_exit_one_worst_sell_dng10_modela/dng10_strategy_input_bundle_20260625/
data_tw/artifacts/readonly_source_context/dng10_modela_20260625/
data_tw/artifacts/agent_daily_prompt_source_context/dng10_modela_20260625/
data_tw/catalog/dng10_strategy_readonly_context_validation.json
scripts/build_tw_readonly_source_context.py
scripts/validate_tw_readonly_source_context.py
```

本审查未修复 DNG10 产物，未触发抓数、训练、调参、provider publish、accepted latest switch、readonly latest publish、Agent prompt latest publish、回放或交易动作。按工作单要求复跑了 validator。

## 3. 必查项结论

| 检查项 | 结论 | 证据 |
| --- | --- | --- |
| `signal_asof=2026-06-25` | 通过 | StrategyInputBundle manifest、readonly manifest、Agent manifest、validation catalog 均为 `2026-06-25` |
| `model_a_ready=true` | 通过 | DNG7 Model A manifest 为 `status=READY`、`row_count=150`；DNG10 context 均标记 `model_a_ready=true` |
| `model_b_ltr_ready=false` 且 blocker 明确 | 通过 | Model B ScoreJob 为 `BLOCKED_INPUT_NOT_READY`，blocking datasets 为 `corporate_actions`、`monthly_revenue`、`valuation` |
| readonly / Agent source context dry-run | 通过 | artifact_type 分别为 `readonly_strategy_snapshot_source_context_dry_run` 和 `agent_daily_prompt_source_context_dry_run` |
| 没有 latest publish | 通过 | `latest_pointer_updated=false`、`readonly_latest_updated=false`、`agent_prompt_latest_updated=false`；产物目录未出现 `latest.json` |
| 没有 target position / target weight / order / broker | 通过 | manifest、lineage、validator flags 全部为 false；禁用文件扫描未发现订单或目标仓位文件 |
| 没有 ReplayResult / NAV / performance | 通过 | `not_replay_result=true`、`strategy_replay_triggered=false`、`replay_result_nav_generated=false`；未发现 NAV/performance 输出文件 |
| validator 通过 | 通过 | 复跑 `python scripts/validate_tw_readonly_source_context.py --json` 返回 `ok=true`、`status=PASS`、`errors=[]` |

## 4. Artifact 链路审查

StrategyInputBundle：

```text
path=data_tw/artifacts/strategy_input_bundles/top50_exit_one_worst_sell_dng10_modela/dng10_strategy_input_bundle_20260625/
status=READY_FOR_SOURCE_CONTEXT_DRY_RUN
signal_asof=2026-06-25
model_a_ready=true
model_b_ltr_ready=false
fallback_model=qlib_only_model_a
signals=150
price_context=150
market_context=1
calendar=2789
current_holdings=1 placeholder
```

`current_holdings.csv` 是 source context 占位审计行，内容标记为 `SOURCE_CONTEXT_PLACEHOLDER`，原因是 `no_current_holdings_or_order_intents_generated_in_dng10`。这不是真实持仓，也不是 OrderIntentArtifact。

Readonly source context：

```text
path=data_tw/artifacts/readonly_source_context/dng10_modela_20260625/
artifact_type=readonly_strategy_snapshot_source_context_dry_run
signal_asof=2026-06-25
readonly_only=true
production_allowed=false
latest_pointer_updated=false
readonly_latest_updated=false
```

Agent source context：

```text
path=data_tw/artifacts/agent_daily_prompt_source_context/dng10_modela_20260625/
artifact_type=agent_daily_prompt_source_context_dry_run
signal_asof=2026-06-25
readonly_only=true
production_allowed=false
latest_pointer_updated=false
agent_prompt_latest_updated=false
```

Agent `answer_policy` 已把 `place_order`、`auto_trade`、`target_position_request`、`portfolio_weight`、`broker_operation`、`monitor_write` 等问题类型列为 blocked，并要求说明 qlib score 不是收益率、胜率、涨幅或买入概率。

## 5. Model B Blocker 审查

结论：通过。

Model B ScoreJob manifest 显示：

```text
status=BLOCKED_INPUT_NOT_READY
score_status=BLOCKED_INPUT_NOT_READY
model_b_ltr_ready=false
row_count=0
signal_artifact=null
ltr_signal_generated=false
qlib_score_used_as_ltr_score=false
do_not_substitute_qlib_score_as_ltr_score=true
blocking_datasets=corporate_actions, monthly_revenue, valuation
```

DNG10 readonly context 与 Agent context 均显式展示 `model_b_ltr_ready=false`、`model_b_status=BLOCKED_INPUT_NOT_READY`、`fallback_model=qlib_only_model_a`，且 `ltr_top10=[]`。未发现把 qlib score 冒充为 LTR score 的证据。

## 6. Validator / Static Checks

已运行：

```bash
python scripts/validate_tw_readonly_source_context.py --json
```

结果摘要：

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
not_order=true
not_target_position=true
not_target_weight=true
not_replay_result=true
```

脚本审查结论：

- `scripts/build_tw_readonly_source_context.py` 只从本地 DNG7/DNG8/DNG2 artifact 复制、过滤和打包 source context。
- `scripts/validate_tw_readonly_source_context.py` 检查 schema、forbidden flags、禁用字段、禁用文件和 dry-run 状态。
- 未发现脚本触发 provider refresh/publish、模型训练/调参/推理补分、回放、broker/order 或 latest pointer 写入。

## 7. 禁止动作审计

validation catalog 与各 manifest/lineage/context 的 forbidden flags 均为 false：

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

文件清单审查未发现：

```text
latest.json
order_intents.csv
target_positions.csv
target_weights.csv
daily_nav.csv
summary.csv
actions.csv
position_snapshots.csv
```

关键词扫描命中的 `target_position`、`target_weight`、`ReplayResult`、`NAV`、`broker_order`、`quick_trade` 均位于安全标志、blocked policy 或“未生成”说明中，不是实际交易、仓位、NAV 或绩效产物。

## 8. DNG11 放行条件

DNG11 可以继续：

- 多日 shadow/observation 的 source context 稳定性观察。
- 多日 readiness/dashboard 观察。
- 保留 Model A qlib-only fallback 展示。
- 保留 Model B blocker 展示，并明确 blocker 来自 DNG3 正交数据缺口。

DNG11 不得默认执行：

- provider refresh / publish。
- qlib accepted latest switch。
- readonly latest publish。
- Agent prompt latest publish。
- 模型训练、调参或补 score。
- OrderIntentArtifact、target_position、target_weight。
- ReplayResult、NAV、performance 结论。
- broker/order/quick-trade。

如 DNG11 需要推进 publish latest、OrderIntentArtifact、ReplayResult/NAV 或生产默认展示，必须另开 gate、validator 和审查授权。

最终结论：

```text
PASS_WITH_CONDITIONS_GO_DNG11
```
