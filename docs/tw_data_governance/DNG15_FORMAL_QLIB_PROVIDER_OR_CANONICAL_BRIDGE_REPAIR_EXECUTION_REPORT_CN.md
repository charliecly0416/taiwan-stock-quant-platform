# DNG15 Formal Qlib Provider Or Canonical Bridge Repair 执行报告

生成时间：2026-06-29

## 1. Scope

- Assigned phase：`DNG15_FORMAL_QLIB_PROVIDER_OR_CANONICAL_BRIDGE_REPAIR`
- Mainline document：`docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md`
- Work document：`docs/tw_data_governance/DNG15_FORMAL_QLIB_PROVIDER_OR_CANONICAL_BRIDGE_REPAIR_WORK_CN.md`
- Target asof：`2026-06-26`
- Model：`e4_frozen_qlib_2018_2022`

非目标确认：

- 未触发真实网络抓数。
- 未触发 provider refresh / provider publish。
- 未切 formal qlib accepted latest。
- 未 publish readonly latest / Agent latest。
- 未触发模型训练、调参、LTR Model B、策略回放、broker/order、target_position 或 target_weight。
- 未用 `2026-06-25` score 冒充 `2026-06-26` score。

## 2. Documents / Contracts / Skills Read

- `docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md`
- `docs/tw_data_governance/DNG15_FORMAL_QLIB_PROVIDER_OR_CANONICAL_BRIDGE_REPAIR_WORK_CN.md`
- `docs/tw_data_governance/DNG14_MULTI_DAY_AUTOMATIC_OBSERVATION_EXECUTION_REPORT_CN.md`
- `docs/tw_data_governance/DNG14_MULTI_DAY_AUTOMATIC_OBSERVATION_REVIEW_CN.md`
- `data_tw/catalog/dng14_multi_day_chain_observation.json`
- `data_tw/catalog/dng14_latest_status_chain_overlay.json`
- `scripts/tw_modela_score_common.py`
- `scripts/build_tw_model_inference_input.py`
- `scripts/run_tw_model_score_job.py`
- `qlib_pipeline/examples/tw/run_option_c_daily_signal_option_c_provider.py`
- `.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md`

## 3. Route Decision

本轮选择先评估 `Route B: validated canonical bridge route`，但没有生成 bridge 或 score。

原因：

1. `Route A: formal qlib provider refresh route` 需要真实网络 provider refresh，且可能进入 formal provider write/publish flow。本阶段工作文档要求如果 Route A 需要真实网络或 provider refresh，必须停在 blocker。
2. `Route B` 只有在本地同口径 Option C normalized source 覆盖 `2026-06-26` 时才安全。实际检查发现 `option_c_150_normalized` 的 150 支标的全部只到 `2026-06-25`，`symbols_with_asof=0/150`。
3. daily auto 的 FinMind raw daily price 虽然覆盖 `2026-06-26`，但工作文档禁止“用 raw FinMind 直接冒充 qlib provider feature input”。把 FinMind raw 拼入 Yahoo/Scrapling Option C provider 会改变模型输入口径，不能在 DNG15 中静默执行。

因此本轮没有推进到 Model A score，而是把 blocker 从泛泛的 `provider stale` 具体化为：

```text
normalized_source_missing_asof_and_formal_refresh_requires_network
```

## 4. Changes Made

新增脚本：

```text
scripts/build_tw_dng15_provider_or_bridge_repair.py
```

脚本职责：

1. 检查 formal Option C provider calendar max。
2. 检查 formal Option C normalized 150 支标的是否覆盖目标 asof。
3. 检查 DNG13/DNG14 记录的 FinMind raw daily price evidence。
4. 检查 DNG15 指定的硬编码风险。
5. 生成机器可读 DNG15 decision / readiness artifact。

生成产物：

```text
data_tw/catalog/dng15_provider_or_bridge_repair_decision.json
data_tw/catalog/dng15_modela_20260626_readiness.json
```

额外 probe 产物：

```text
data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022/dng15_probe_modela_20260626/
```

该 probe 是用现有 `scripts/build_tw_model_inference_input.py --asof 2026-06-26` 生成的 blocked artifact，用于证明现有合同会拒绝 6/26 输入；不是 ready input。

## 5. Evidence Produced

### 5.1 DNG15 decision

`data_tw/catalog/dng15_provider_or_bridge_repair_decision.json`：

```text
decision=NO_SCORE_GENERATED_BLOCKER_CONCRETIZED
selected_route=B_VALIDATED_CANONICAL_BRIDGE
concrete_blocker=normalized_source_missing_asof_and_formal_refresh_requires_network
recommended_next_route=DNG15_REPAIR_SAME_LINEAGE_NORMALIZED_REFRESH_OR_EXPLICIT_MIXED_PROVIDER_BRIDGE_DECISION
production_go=false
publish_latest_authorized=false
```

Route A:

```text
status=BLOCKED_NOT_EXECUTED
blockers=needs_network_provider_refresh, requires_formal_provider_write_or_publish_flow
```

Route B:

```text
status=BLOCKED_NOT_SAFE_TO_BUILD
blockers=qlib_provider_calendar_stale, normalized_source_missing_asof
dump_tool_exists=true
dump_tool=qlib_pipeline/scripts/dump_bin.py
not_published_latest=true
production_allowed=false
```

### 5.2 6/26 readiness

`data_tw/catalog/dng15_modela_20260626_readiness.json`：

```text
status=BLOCKED_INPUT_NOT_READY
score_status=NOT_SCORED
blocked_at=normalized_source_missing_asof_and_formal_refresh_requires_network
```

Formal provider：

```text
provider_uri=qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin
calendar_max=2026-06-25
calendar_status=STALE
```

Formal Option C normalized：

```text
source_path=qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized
symbols_expected=150
symbols_found=150
symbols_with_asof=0
missing_asof_count=150
min_date_max=2026-06-25
max_date_max=2026-06-25
status=MISSING_TARGET_ASOF
```

FinMind raw evidence：

```text
status=READY_FROM_PRIOR_JOB
ready_candidate_count=6
latest_ready_evidence=data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260626T174322Z/daily_source_inventory.json
source_max_date=2026-06-26
row_count=25650
symbol_count=150
```

解释：raw 有，不等于可直接作为 frozen qlib Model A 的同口径 feature input。

### 5.3 Existing ModelInferenceInput builder probe

命令：

```bash
python scripts/build_tw_model_inference_input.py --asof 2026-06-26 --run-id dng15_probe_modela_20260626 --json
```

结果：

```text
status=BLOCKED_INPUT_NOT_READY
errors=price_market_readiness_asof_mismatch, qlib_provider_calendar_stale, normalized_source_missing_asof
```

该结果证明现有 builder 不会错误放行 6/26。

### 5.4 Fixed Option C provider dry-run

命令：

```bash
python qlib_pipeline/examples/tw/run_option_c_daily_signal_option_c_provider.py --asof 2026-06-26 --dry-run
```

结果：

```text
status=blocked_formal_validation_failed
errors=option_c_formal_source_missing_asof, option_c_provider_calendar_stale
run_dir=qlib_pipeline/data_tw/experiments/option_c_daily_signal_option_c_provider/option_c_provider_dry_run_20260626_20260629T125548Z
```

该 dry-run 没有写 latest，没 refresh，没 publish。

### 5.5 DNG14 overlay rerun

命令：

```bash
python scripts/build_tw_dng14_multi_day_chain_observation.py --json
```

结果：

```text
latest_ready_chain_asof=2026-06-25
latest_raw_ready_asof=2026-06-29
latest_provider_stale_asof=2026-06-29
observed_trade_day_count=6
recommended_next_route=formal_qlib_provider_refresh_route_or_validated_canonical_bridge_route
```

DNG15 未推进 6/26 ready chain；这是预期结果，因为 score 未生成。

## 6. Hardcoded Risk Check

DNG15 指定硬编码已检查并记录到 `dng15_modela_20260626_readiness.json`：

| 文件 | 发现 |
| --- | --- |
| `scripts/tw_modela_score_common.py` | 存在 `TARGET_ASOF = "2026-06-25"`、`readiness_matrix/2026-06-25`、`dng2_r_price_market_calendar_20260625`、固定 `option_c_150_qlib_bin` |
| `scripts/build_tw_model_inference_input.py` | 依赖 `PRICE_MARKET_READINESS`、`PRICE_STORE_DIR`、`QLIB_PROVIDER`、`TARGET_ASOF` |
| `scripts/run_tw_model_score_job.py` | 调用 fixed `run_option_c_daily_signal_option_c_provider.py --normal`，依赖 fixed provider |
| `qlib_pipeline/examples/tw/run_option_c_daily_signal_option_c_provider.py` | 固定 `OPTION_C_PROVIDER=option_c_150_qlib_bin`，不会写 `latest_signal.json` |

本轮没有修改这些生产合同。原因是当前 6/26 同口径 normalized 缺失，先参数化也不能产生合法 score；过早改 provider 参数反而可能让下游误用未验证 bridge。

## 7. Validation Commands

```bash
python -m py_compile scripts/tw_modela_score_common.py scripts/build_tw_model_inference_input.py scripts/run_tw_model_score_job.py scripts/run_daily_tw_stock_auto_update.py scripts/build_tw_dng15_provider_or_bridge_repair.py
```

结果：通过。

```bash
python scripts/build_tw_dng15_provider_or_bridge_repair.py --json
```

结果：

```text
decision=NO_SCORE_GENERATED_BLOCKER_CONCRETIZED
readiness_status=BLOCKED_INPUT_NOT_READY
```

```bash
python scripts/build_tw_model_inference_input.py --asof 2026-06-26 --run-id dng15_probe_modela_20260626 --json
```

结果：按预期返回 code 2，并生成 blocked artifact。

```bash
python qlib_pipeline/examples/tw/run_option_c_daily_signal_option_c_provider.py --asof 2026-06-26 --dry-run
```

结果：按预期返回 code 1，`blocked_formal_validation_failed`。

```bash
python scripts/build_tw_dng14_multi_day_chain_observation.py --json
```

结果：通过，且 `latest_ready_chain_asof` 仍为 `2026-06-25`。

## 8. Forbidden Actions Audit

通过。

`data_tw/catalog/dng15_provider_or_bridge_repair_decision.json` 与 `data_tw/catalog/dng15_modela_20260626_readiness.json` 中所有 forbidden actions 均为 false：

```text
real_data_fetch_triggered=false
provider_refresh_triggered=false
provider_publish_triggered=false
qlib_accepted_latest_switched=false
readonly_latest_published=false
agent_prompt_published=false
production_default_model_or_strategy_switched=false
model_training_triggered=false
model_tuning_triggered=false
strategy_replay_triggered=false
broker_order_quick_trade_triggered=false
target_position_or_weight_generated=false
```

## 9. Issues / Blockers / Deviations

### 9.1 Main blocker

```text
normalized_source_missing_asof_and_formal_refresh_requires_network
```

解释：

- FinMind raw daily price 已覆盖 `2026-06-26`。
- 但 frozen qlib Model A 的输入口径是 Option C Yahoo/Scrapling adjusted normalized -> qlib bin provider。
- 当前 `option_c_150_normalized` 没有任何标的覆盖 `2026-06-26`。
- 当前 formal qlib provider calendar 也只到 `2026-06-25`。
- 因此不能构造合法 `2026-06-26` ModelInferenceInput，更不能生成 ScoreJob / ModelSignalArtifact。

### 9.2 为什么没有直接用 FinMind raw 生成 bridge

这会把模型输入从 Yahoo/Scrapling adjusted price 口径切成 FinMind raw/adjusted-like 口径。即使可以技术上 dump 成 qlib bin，也不是同一个 feature distribution，违反 DNG15 禁止事项：

```text
不得用 raw FinMind 直接冒充 qlib provider feature input
```

若后续要走 mixed-provider bridge，必须由统筹明确授权，并新增 validator 比较：

```text
Yahoo/Scrapling vs FinMind OHLCV/factor/vwap 口径差异
Alpha158 feature drift
score rank stability
top-k overlap
no latest publish / no production gate
```

## 10. Files Changed

新增：

```text
scripts/build_tw_dng15_provider_or_bridge_repair.py
docs/tw_data_governance/DNG15_FORMAL_QLIB_PROVIDER_OR_CANONICAL_BRIDGE_REPAIR_EXECUTION_REPORT_CN.md
data_tw/catalog/dng15_provider_or_bridge_repair_decision.json
data_tw/catalog/dng15_modela_20260626_readiness.json
data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022/dng15_probe_modela_20260626/
qlib_pipeline/data_tw/experiments/option_c_daily_signal_option_c_provider/option_c_provider_dry_run_20260626_20260629T125548Z/
```

更新：

```text
data_tw/catalog/dng14_multi_day_chain_observation.json
data_tw/catalog/dng14_multi_day_chain_observation.csv
data_tw/catalog/dng14_latest_status_chain_overlay.json
```

## 11. Recommendation For Reviewer

建议 verdict：

```text
STOP_NEEDS_COORDINATOR_DECISION
```

理由：

- DNG15 已满足“把不能推进的 blocker 具体化”的最低要求。
- 但没有推进 `latest_ready_chain_asof >= 2026-06-26`，因此不能进入 `DNG16_DAILY_AUTO_MODEL_SCORE_INTEGRATION`。
- 下一步需要统筹选择：
  1. 授权同口径 Yahoo/Scrapling Option C normalized refresh / isolated staged provider build；
  2. 或明确授权 mixed-provider FinMind bridge research-only，并增加 drift validator；
  3. 或等待正式日更链路补出同口径 normalized 后再重跑 DNG15。

如果审查者认为无需用户决策、可直接继续 repair，则建议 repair 名称：

```text
DNG15_R_SAME_LINEAGE_OPTION_C_NORMALIZED_REFRESH_OR_ISOLATED_PROVIDER_VIEW_BUILD
```
