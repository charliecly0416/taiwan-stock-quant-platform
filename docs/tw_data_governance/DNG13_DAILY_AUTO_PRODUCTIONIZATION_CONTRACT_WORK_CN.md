# DNG13 Daily Auto Productionization Contract 工作文档

生成日期：2026-06-29

## 1. 背景

DNG0-DNG12 已完成单日设计闭环，但还不是用户真正需要的“全自动”。

当前问题的代表案例是：

```text
2026-06-26 FinMind raw / ops job 已有
formal qlib calendar 仍只到 2026-06-25
qlib accepted latest 仍更旧
Model A score 只生成 2026-06-25
```

这说明每日脚本能抓到部分数据，但抓数后没有稳定推进到 canonical、qlib provider view、model score、strategy context、readonly/frontend source context 全链路。后续必须把 DNG 设计接入真实 daily auto，而不是继续靠人工发现缺哪层再 repair。

## 2. 目标

让每天盘后自动流程变成：

```text
抓 raw / normalized
-> 更新 catalog / latest_status
-> 构建 canonical PriceStore / MarketFeatureStore / OrthogonalFeatureStore
-> 构建 qlib provider view candidate
-> 构建 ModelInferenceInput
-> 生成 Model A score / ModelSignalArtifact
-> 在正交数据 ready 时生成 Model B LTR signal，否则写 blocker / fallback
-> 生成 StrategyInputBundle / ReplayInputBundle / readonly source context
-> 写 daily_chain_status / skipped_asof_ledger / readiness dashboard
-> 等待下一交易日或 pending retry
```

该阶段不是 production latest 发布阶段。它只负责每日自动生成和审计标准只读产物。

## 3. 非目标

本阶段不得做：

- broker/order/quick-trade；
- target position / target weight；
- production default model/strategy switch；
- formal qlib accepted latest 自动切换；
- readonly snapshot latest 自动发布；
- Agent prompt latest 自动发布；
- 模型训练或调参；
- 用旧 score 冒充新 asof score。

## 4. 必须保留的原链路兼容性

原本的：

```text
数据 -> 模型 -> 策略 -> 前端展示
```

必须继续可用，但要改成优先通过标准 artifact 串接：

```text
DataCatalog / latest_status
PriceStore / MarketFeatureStore
ModelInferenceInput
ScoreJob
ModelSignalArtifact
StrategyInputBundle
Readonly source context
Frontend readonly payload
```

旧 latest pointer 在未授权时不得改写。前端若要展示新 asof，只能消费通过 validator 的 readonly/source-context artifact，或由单独 publish gate 切换。

## 5. 必须新增或完善的产物

执行者必须新增或等价实现：

```text
data_tw/ops/daily_auto_update/{job_id}/daily_chain_status.json
data_tw/ops/daily_auto_update/{job_id}/skipped_asof_ledger.json
data_tw/catalog/daily_readiness_dashboard.json
data_tw/catalog/latest_status.json
```

`daily_chain_status.json` 必须逐层记录：

```text
asof
job_id
is_trading_day
data_window_status
raw_status
normalized_status
price_store_status
market_feature_status
orthogonal_feature_status
qlib_provider_view_status
model_a_inference_input_status
model_a_score_status
model_a_signal_status
model_b_ltr_status
strategy_input_bundle_status
replay_input_bundle_status
readonly_source_context_status
agent_source_context_status
frontend_payload_status
publish_latest_gate_status
pending_asof_status
next_retry_hint
blocked_at
blocker_reason
next_required_action
forbidden_actions
```

`skipped_asof_ledger.json` 必须逐日期记录：

```text
asof
candidate_reason
is_trading_day
skip_or_block_status
raw_status
formal_calendar_status
qlib_provider_view_status
score_status
strategy_context_status
skip_reason
retry_policy
next_required_action
evidence_paths
```

## 6. 2026-06-26 必须作为验收样例

执行者必须用只读证据解释 2026-06-26：

```text
6/26 是交易日，不是周末。
FinMind raw / ops job 已存在。
formal qlib provider calendar 未推进到 6/26。
option_c daily signal / Model A source run 没有 6/26。
DNG7 因此只能生成 6/25 Model A score。
```

验收要求不是强行生成 6/26 score，而是必须让 dashboard 和 ledger 能机器可读地说明：

```text
blocked_at=qlib_provider_view_or_formal_calendar
score_status=BLOCKED_PROVIDER_VIEW_STALE
retry_policy=retry_after_provider_view_refresh_or_canonical_bridge
```

如果执行者选择 repair 并生成 6/26 score，必须先通过 qlib provider view / canonical input validator，不得直接用 FinMind raw 冒充 qlib feature input。

## 7. pending_asof 语义扩展

`pending_asof` 不能只表示 raw 抓数失败。它应支持：

```text
fresh_data_wait
raw_provider_failed
normalized_build_failed
canonical_price_failed
market_feature_failed
qlib_provider_view_stale
model_a_score_failed
model_b_ltr_blocked
strategy_bundle_failed
readonly_context_failed
publish_gate_waiting_review
```

下一次 daily auto 必须先处理 pending asof，再处理新的 Taipei today。若 pending asof 是周末/假日，必须写 holiday evidence 后跳过。

## 8. daily auto gate 要求

执行者必须保持 gate 分层：

| Gate | 默认 | 允许动作 |
| --- | --- | --- |
| `raw_normalized_gate` | 开 | 抓 raw、建 normalized、写 raw accounting |
| `canonical_feature_gate` | 可开 | 建 PriceStore、TWII、正交 feature、qlib provider view candidate |
| `model_signal_gate` | 可开 | 只读推理、ScoreJob、ModelSignalArtifact |
| `strategy_context_gate` | 可开 | StrategyInputBundle、readonly/Agent source context dry-run |
| `publish_latest_gate` | 关 | readonly latest、Agent latest、formal accepted latest |

审查者必须拒绝任何把 `model_signal_gate` 通过解释成 `publish_latest_gate` 通过的报告。

## 9. 执行者任务

1. 阅读主线文档和 DNG12 closure。
2. 检查 `scripts/run_daily_tw_stock_auto_update.py` 当前 gate 和 finalize_job 行为。
3. 设计并实现 `daily_chain_status.json` 与 `skipped_asof_ledger.json`。
4. 将 daily auto 在抓数后串到 DNG canonical / score / strategy source context 阶段，至少在 gate 关闭时也要输出 skipped/disabled reason。
5. 用 2026-06-25 ready 与 2026-06-26 lineage gap 做验收样例。
6. 保持 forbidden actions 全 false。
7. 写执行报告：

```text
docs/tw_data_governance/DNG13_DAILY_AUTO_PRODUCTIONIZATION_CONTRACT_EXECUTION_REPORT_CN.md
```

## 10. 审查者任务

审查者必须检查：

1. 是否真的解决“raw 有但 score 没有却解释不清”的问题。
2. 6/26 是否被正确分类为 qlib provider view / formal calendar lineage gap。
3. daily auto 是否保留原本数据-模型-策略-前端展示链路。
4. latest / publish / production / trading gate 是否仍默认关闭。
5. `pending_asof` 是否能表达非 raw 层 blocker。
6. 是否有旧 signal 冒充新 asof。

审查输出：

```text
docs/tw_data_governance/DNG13_DAILY_AUTO_PRODUCTIONIZATION_CONTRACT_REVIEW_CN.md
```

Verdict 只能是：

```text
PASS_GO_DNG14_MULTI_DAY_AUTOMATIC_OBSERVATION
PASS_WITH_CONDITIONS_GO_DNG14
FAIL_NEEDS_DNG13_REPAIR
STOP_NEEDS_COORDINATOR_DECISION
```

## 11. 通过条件

DNG13 通过的最低条件：

- 每个 daily auto job 都有 `daily_chain_status.json`。
- 每个未生成 score 的候选 asof 都进入 `skipped_asof_ledger.json`。
- 6/26 lineage gap 可被机器可读解释。
- 6/25 Model A ready 链路仍可被识别。
- 原有 readonly/frontend 链路未被破坏。
- forbidden actions 全 false。

## 12. 后续 DNG14

若 DNG13 通过，进入 DNG14：

```text
DNG14_MULTI_DAY_AUTOMATIC_OBSERVATION
```

DNG14 目标是观察至少 5 个交易日或等价 backfill/shadow 样本，确认每天抓数后能自动进入 DNG 链路，并且失败都能被 ledger/dashboard 解释和重试。
