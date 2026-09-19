# DNG13 Daily Auto Productionization Contract 执行报告

生成日期：2026-06-29

## 1. 范围

- Assigned phase：`DNG13_DAILY_AUTO_PRODUCTIONIZATION_CONTRACT`
- Mainline document：`docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md`
- Work document：`docs/tw_data_governance/DNG13_DAILY_AUTO_PRODUCTIONIZATION_CONTRACT_WORK_CN.md`
- Non-goals confirmed：未触发 provider publish、accepted latest switch、readonly latest publish、Agent latest publish、broker/order、target position/target weight、模型训练或调参。

本轮目标是让 daily auto 每个 job 在 finalize 阶段生成可审计的链路状态：

```text
daily_chain_status.json
skipped_asof_ledger.json
job.json 引用上述两个产物
```

## 2. Documents / Contracts / Skills Read

- `docs/tw_data_governance/DNG13_DAILY_AUTO_PRODUCTIONIZATION_CONTRACT_WORK_CN.md`
- `docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md`
- `docs/tw_data_governance/DNG12_DATA_GOVERNANCE_DESIGN_ONLY_CLOSURE_CN.md`
- `.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md`
- `.agents/skills/tw-stock-data-freshness-diagnosis/SKILL.md`

## 3. Changes Made

修改文件：

- `scripts/run_daily_tw_stock_auto_update.py`

主要改动：

1. 新增 DNG13 schema：
   - `dng13.daily_chain_status.v1`
   - `dng13.skipped_asof_ledger.v1`
2. 在 `finalize_job()` 中统一写入：
   - `daily_chain_status.json`
   - `skipped_asof_ledger.json`
3. `job.json` 增加引用：
   - `job["daily_chain_status"]`
   - `job["skipped_asof_ledger"]`
4. 复用现有 `daily_source_inventory` / `daily_full_capture_accounting`，并补充只读 lineage 发现：
   - formal qlib calendar max
   - latest signal asof
   - Model A inference / score / signal artifact
   - StrategyInputBundle / readonly source context / Agent source context
   - 同一 asof 的历史 daily auto raw evidence
5. 对 `2026-06-26` 场景做机器可读分类：
   - `raw_status=READY_FROM_PRIOR_JOB`
   - `qlib_provider_view_status=BLOCKED_PROVIDER_VIEW_STALE`
   - `blocked_at=qlib_provider_view_or_formal_calendar`
   - `next_retry_hint=retry_after_provider_view_refresh_or_canonical_bridge`

## 4. Evidence Produced

### 4.1 2026-06-26 lineage gap 验收样例

安全 dry-run 命令：

```bash
python scripts/run_daily_tw_stock_auto_update.py --asof 2026-06-26 --force --skip-finmind --skip-qlib --today-earliest-time 00:00
```

产物：

```text
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T122903Z/daily_chain_status.json
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T122903Z/skipped_asof_ledger.json
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T122903Z/job.json
```

关键结果：

```text
is_trading_day=true
raw_status=READY_FROM_PRIOR_JOB
qlib_provider_view_status=BLOCKED_PROVIDER_VIEW_STALE
model_a_score_status=BLOCKED_PROVIDER_VIEW_STALE
blocked_at=qlib_provider_view_or_formal_calendar
lineage_gap_detected=true
publish_latest_gate_status=DISABLED_BY_DEFAULT
forbidden_actions.all_false=true
```

raw evidence 指向既有真实 6/26 job：

```text
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260626T174322Z/job.json
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260626T174322Z/daily_source_inventory.json
```

formal qlib calendar evidence：

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt
formal_calendar_max=2026-06-25
```

### 4.2 2026-06-25 ready 链路样例

安全 dry-run 命令：

```bash
python scripts/run_daily_tw_stock_auto_update.py --asof 2026-06-25 --force --skip-finmind --skip-qlib --today-earliest-time 00:00
```

产物：

```text
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260625_20260629T122831Z/daily_chain_status.json
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260625_20260629T122831Z/skipped_asof_ledger.json
```

关键结果：

```text
is_trading_day=true
qlib_provider_view_status=READY
model_a_inference_input_status=READY
model_a_score_status=READY
model_a_signal_status=READY
strategy_input_bundle_status=READY
readonly_source_context_status=READY
agent_source_context_status=READY
blocked_at=
blocker_reason=none
forbidden_actions.all_false=true
```

说明：该 dry-run 使用 `--skip-finmind`，因此 `raw_status=DISABLED_BY_SKIP_FINMIND` 只表示本次验证没有重新抓 raw；不会覆盖既有 Model A / Strategy / readonly source context ready 事实。

## 5. Validation Commands

```bash
python -m py_compile scripts/run_daily_tw_stock_auto_update.py
```

结果：通过，无输出。

```bash
python scripts/run_daily_tw_stock_auto_update.py --asof 2026-06-26 --force --skip-finmind --skip-qlib --today-earliest-time 00:00
```

结果：通过，生成 DNG13 两个产物，未触发 FinMind / qlib / publish / latest / trading。

```bash
python scripts/run_daily_tw_stock_auto_update.py --asof 2026-06-25 --force --skip-finmind --skip-qlib --today-earliest-time 00:00
```

结果：通过，识别 6/25 Model A / Strategy / readonly source context ready。

## 6. 2026-06-26 解释

`2026-06-26` 不是周末，也不是 raw 无数据。

本轮机器可读解释为：

```text
FinMind raw / ops: 已有 2026-06-26
formal qlib provider calendar: 只到 2026-06-25
option_c daily signal / standard Model A score artifact: 没有 2026-06-26
因此 blocked_at=qlib_provider_view_or_formal_calendar
```

这解决了原先“raw 有但 score 没有却解释不清”的问题。

## 7. Forbidden Actions Audit

本轮验证命令均使用：

```text
--skip-finmind
--skip-qlib
publish/latest gate 默认关闭
```

产物中的 forbidden actions：

```text
provider_refresh_triggered=false
provider_publish_triggered=false
accepted_latest_switch_triggered=false
qlib_accepted_latest_switched=false
readonly_latest_published=false
agent_prompt_published=false
production_default_model_or_strategy_switched=false
broker_order_quick_trade_triggered=false
target_position_or_weight_generated=false
all_false=true
```

## 8. Issues / Blockers / Deviations

1. 本轮只完成 daily chain audit productionization，不负责真正把 formal qlib provider 推进到 2026-06-26。
2. `daily_chain_status.json` 当前是 job-local artifact；`data_tw/catalog/latest_status.json` 与 `daily_readiness_dashboard.json` 未在本轮强制写入 DNG13 聚合结果。
3. 真实自动运行时若打开 `enable_data_catalog_dashboard`，仍会沿用既有 DNG6 dashboard builder；DNG13 的 job-local status 已可作为 DNG14 观察输入。

## 9. Files Changed

```text
scripts/run_daily_tw_stock_auto_update.py
docs/tw_data_governance/DNG13_DAILY_AUTO_PRODUCTIONIZATION_CONTRACT_EXECUTION_REPORT_CN.md
```

验证生成的新 job artifacts：

```text
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260625_20260629T122831Z/
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T122903Z/
```

## 10. Recommendation For Reviewer

建议 verdict：

```text
PASS_WITH_CONDITIONS_GO_DNG14
```

条件：

1. 审查者确认 6/26 被正确分类为 lineage gap。
2. DNG14 多日观察应消费 `daily_chain_status.json` / `skipped_asof_ledger.json`，累计至少 5 个交易日或等价 shadow/backfill 样本。
3. 后续如要真正推进 6/26 score，应开单独 formal qlib provider refresh / validated canonical bridge route，不应在 DNG13 中混入 publish/latest switch。
