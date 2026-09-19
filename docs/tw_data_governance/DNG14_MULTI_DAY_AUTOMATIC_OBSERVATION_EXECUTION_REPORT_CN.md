# DNG14 Multi-Day Automatic Observation 执行报告

生成日期：2026-06-29

## 1. Scope

- Assigned phase：`DNG14_MULTI_DAY_AUTOMATIC_OBSERVATION`
- Mainline document：`docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md`
- Work document：`docs/tw_data_governance/DNG14_MULTI_DAY_AUTOMATIC_OBSERVATION_WORK_CN.md`
- Non-goals confirmed：未触发真实 FinMind/Yahoo/TWSE 抓数、provider refresh/publish、formal qlib accepted latest switch、readonly latest publish、Agent prompt latest publish、broker/order/quick-trade、target position/target weight、模型训练或调参。

本轮目标是把 DNG13 job-local artifacts：

```text
daily_chain_status.json
skipped_asof_ledger.json
```

聚合成多日观察和 catalog overlay。

## 2. Documents / Contracts / Skills Read

- `docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md`
- `docs/tw_data_governance/DNG14_MULTI_DAY_AUTOMATIC_OBSERVATION_WORK_CN.md`
- `docs/tw_data_governance/DNG13_DAILY_AUTO_PRODUCTIONIZATION_CONTRACT_WORK_CN.md`
- `docs/tw_data_governance/DNG13_DAILY_AUTO_PRODUCTIONIZATION_CONTRACT_EXECUTION_REPORT_CN.md`
- `docs/tw_data_governance/DNG13_DAILY_AUTO_PRODUCTIONIZATION_CONTRACT_REVIEW_CN.md`
- `.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md`
- `data_tw/ops/daily_auto_update/**/daily_chain_status.json`
- `data_tw/ops/daily_auto_update/**/skipped_asof_ledger.json`

## 3. Changes Made

新增脚本：

```text
scripts/build_tw_dng14_multi_day_chain_observation.py
```

脚本职责：

1. 扫描 `data_tw/ops/daily_auto_update/*/daily_chain_status.json`。
2. 同一 `asof` 多个 job 时，按 DNG14 合同选择代表 job：
   - `required_fields_present=true`
   - `forbidden_actions.all_false=true`
   - `created_at` 最新
3. 保留同一 `asof` 的全部 candidates，并记录 `conflict_detected`。
4. 输出 asof-level 分类：
   - `READY_CHAIN`
   - `RAW_READY_BUT_QLIB_PROVIDER_STALE`
   - `DATA_WINDOW_WAIT`
   - `WEEKEND_OR_HOLIDAY_SKIPPED`
   - `MODEL_A_SCORE_MISSING`
   - `STRATEGY_OR_READONLY_CONTEXT_MISSING`
   - `PUBLISH_READY_BUT_NOT_PUBLISHED`
   - `BLOCKED_OTHER`
5. 写入 catalog overlay。

生成产物：

```text
data_tw/catalog/dng14_multi_day_chain_observation.json
data_tw/catalog/dng14_multi_day_chain_observation.csv
data_tw/catalog/dng14_latest_status_chain_overlay.json
```

## 4. Evidence Produced

### 4.1 安全 shadow/backfill 样本

现有 DNG13 artifacts 已包含：

```text
2026-06-25
2026-06-26
2026-06-29
```

为了满足 DNG14 至少 5 个交易日或等价 shadow/backfill 样本的要求，本轮用合同允许的安全命令补了：

```bash
python scripts/run_daily_tw_stock_auto_update.py --asof 2026-06-22 --force --skip-finmind --skip-qlib --today-earliest-time 00:00
python scripts/run_daily_tw_stock_auto_update.py --asof 2026-06-23 --force --skip-finmind --skip-qlib --today-earliest-time 00:00
python scripts/run_daily_tw_stock_auto_update.py --asof 2026-06-24 --force --skip-finmind --skip-qlib --today-earliest-time 00:00
python scripts/run_daily_tw_stock_auto_update.py --asof 2026-06-27 --force --skip-finmind --skip-qlib --today-earliest-time 00:00
python scripts/run_daily_tw_stock_auto_update.py --asof 2026-06-28 --force --skip-finmind --skip-qlib --today-earliest-time 00:00
```

说明：上述命令只生成 job-local audit artifacts，不是真实抓数、不代表 production readiness。

新增 job-local artifacts：

```text
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260622_20260629T123827Z/
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260623_20260629T123827Z/
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260624_20260629T123827Z/
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260627_20260629T123834Z/
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260628_20260629T123834Z/
```

### 4.2 asof-level 聚合表

| asof | classification | counts_as_trade_day | 解释 |
| --- | --- | --- | --- |
| 2026-06-22 | `MODEL_A_SCORE_MISSING` | true | formal provider 覆盖，但标准 Model A score/signal artifact 缺失 |
| 2026-06-23 | `MODEL_A_SCORE_MISSING` | true | formal provider 覆盖，但标准 Model A score/signal artifact 缺失 |
| 2026-06-24 | `MODEL_A_SCORE_MISSING` | true | formal provider 覆盖，但标准 Model A score/signal artifact 缺失 |
| 2026-06-25 | `READY_CHAIN` | true | Model A score/signal、StrategyInputBundle、readonly/Agent source context ready |
| 2026-06-26 | `RAW_READY_BUT_QLIB_PROVIDER_STALE` | true | raw/ops 有 6/26，但 formal qlib provider calendar 只到 6/25 |
| 2026-06-27 | `WEEKEND_OR_HOLIDAY_SKIPPED` | false | 周六，不计入交易日样本 |
| 2026-06-28 | `WEEKEND_OR_HOLIDAY_SKIPPED` | false | 周日，不计入交易日样本 |
| 2026-06-29 | `RAW_READY_BUT_QLIB_PROVIDER_STALE` | true | raw ready，但 formal qlib provider calendar 仍只到 6/25 |

分类计数：

```text
MODEL_A_SCORE_MISSING: 3
RAW_READY_BUT_QLIB_PROVIDER_STALE: 2
READY_CHAIN: 1
WEEKEND_OR_HOLIDAY_SKIPPED: 2
```

交易日样本数：

```text
observed_trade_day_count=6
required_additional_trade_days=0
```

### 4.3 6/25 ready 解释

`2026-06-25` 代表 job：

```text
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260625_20260629T122831Z/
```

关键状态：

```text
qlib_provider_view_status=READY
model_a_inference_input_status=READY
model_a_score_status=READY
model_a_signal_status=READY
strategy_input_bundle_status=READY
readonly_source_context_status=READY
agent_source_context_status=READY
classification=READY_CHAIN
```

### 4.4 6/26 provider stale 解释

`2026-06-26` 代表 job：

```text
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T122903Z/
```

关键状态：

```text
is_trading_day=true
raw_status=READY_FROM_PRIOR_JOB
qlib_provider_view_status=BLOCKED_PROVIDER_VIEW_STALE
model_a_score_status=BLOCKED_PROVIDER_VIEW_STALE
blocked_at=qlib_provider_view_or_formal_calendar
classification=RAW_READY_BUT_QLIB_PROVIDER_STALE
```

根因：

```text
FinMind raw / ops evidence covers 2026-06-26
formal qlib calendar max = 2026-06-25
Model A score cannot be generated without formal provider view or validated canonical bridge
```

### 4.5 周末处理

`2026-06-27`、`2026-06-28` 均分类为：

```text
WEEKEND_OR_HOLIDAY_SKIPPED
```

并且：

```text
counts_as_trade_day=false
blocked_at=market_calendar
```

## 5. Validation Commands

```bash
python -m py_compile scripts/run_daily_tw_stock_auto_update.py
```

结果：通过。

```bash
python -m py_compile scripts/build_tw_dng14_multi_day_chain_observation.py
```

结果：通过。

```bash
python scripts/build_tw_dng14_multi_day_chain_observation.py --json
```

结果：

```json
{
  "asof_count": 8,
  "csv_path": "data_tw/catalog/dng14_multi_day_chain_observation.csv",
  "latest_provider_stale_asof": "2026-06-29",
  "latest_ready_chain_asof": "2026-06-25",
  "observation_path": "data_tw/catalog/dng14_multi_day_chain_observation.json",
  "observed_trade_day_count": 6,
  "overlay_path": "data_tw/catalog/dng14_latest_status_chain_overlay.json",
  "recommended_next_route": "formal_qlib_provider_refresh_route_or_validated_canonical_bridge_route",
  "required_additional_trade_days": 0
}
```

## 6. Catalog Overlay 结论

`data_tw/catalog/dng14_latest_status_chain_overlay.json`：

```text
latest_ready_chain_asof=2026-06-25
latest_raw_ready_asof=2026-06-29
latest_provider_stale_asof=2026-06-29
latest_model_a_ready_asof=2026-06-25
latest_strategy_context_ready_asof=2026-06-25
latest_readonly_context_ready_asof=2026-06-25
current_blocker=formal qlib provider/calendar has not advanced to latest raw-ready asof
recommended_next_route=formal_qlib_provider_refresh_route_or_validated_canonical_bridge_route
production_go=false
publish_latest_authorized=false
```

## 7. Compliance With Mainline

通过项：

- 已消费 DNG13 job-local `daily_chain_status.json` 与 `skipped_asof_ledger.json`。
- 已生成 DNG14 要求的 JSON / CSV / overlay。
- 同一 asof 多 job 已保留 candidates，并记录 selection reason / conflict。
- 已包含 `2026-06-25` ready 样例。
- 已包含 `2026-06-26` provider stale 样例。
- 周末样本未计入交易日样本数。
- 未用旧 score 冒充新 asof score。
- 未授权或触发 latest publish / accepted latest switch / trading。

## 8. Forbidden Actions Audit

本轮新增聚合脚本只读 job-local artifacts 并写 catalog overlay。

所有代表 job：

```text
forbidden_actions_all_false=true
```

overlay：

```text
forbidden_actions_all_false=true
forbidden_action_violations=[]
production_go=false
publish_latest_authorized=false
```

## 9. Issues / Blockers / Deviations

1. `2026-06-22` 至 `2026-06-24` 是安全 shadow/backfill 样本，`raw_status=DISABLED_BY_SKIP_FINMIND`。它们可用于 DNG14 观察 formal provider 覆盖但 Model A score 缺失，不代表当日真实抓数完成。
2. `2026-06-26` 与 `2026-06-29` 的共同 blocker 是 formal qlib provider/calendar 没有推进到 raw-ready asof。
3. DNG14 完成的是多日观察和 catalog overlay，不是 production Go。

## 10. Files Changed

```text
scripts/build_tw_dng14_multi_day_chain_observation.py
data_tw/catalog/dng14_multi_day_chain_observation.json
data_tw/catalog/dng14_multi_day_chain_observation.csv
data_tw/catalog/dng14_latest_status_chain_overlay.json
docs/tw_data_governance/DNG14_MULTI_DAY_AUTOMATIC_OBSERVATION_EXECUTION_REPORT_CN.md
```

安全 backfill/shadow 生成：

```text
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260622_20260629T123827Z/
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260623_20260629T123827Z/
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260624_20260629T123827Z/
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260627_20260629T123834Z/
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260628_20260629T123834Z/
```

## 11. Recommendation For Reviewer

建议 verdict：

```text
PASS_WITH_CONDITIONS_GO_DNG15
```

条件：DNG15 不应直接进入 production Go，而应先做：

```text
formal_qlib_provider_refresh_route
or
validated_canonical_bridge_route
```

理由：DNG14 已证明每日 artifacts 可以被聚合和解释，但最新 raw-ready asof 已到 `2026-06-29`，正式可打分链路仍停在 `2026-06-25`。下一步必须修 formal qlib provider/calendar 或建立 validated canonical bridge，然后再让 Model A score / StrategyInputBundle / readonly context 每日自动推进。
