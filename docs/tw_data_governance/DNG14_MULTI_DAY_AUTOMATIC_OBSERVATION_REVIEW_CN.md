# DNG14 Multi-Day Automatic Observation 审查意见

生成日期：2026-06-29

## 1. Verdict

```text
PASS_WITH_CONDITIONS_GO_DNG15
```

DNG14 可以通过。条件是：DNG15 必须优先处理 formal qlib provider/calendar 或 validated canonical bridge repair，不得把 DNG14 解释为 production Go、latest publish 授权或交易授权。

## 2. Findings

### Critical

无。

### High

无。

### Medium

1. DNG14 通过的是多日观察和 catalog overlay，不是全自动 score 生产闭环。
   - 证据：`latest_raw_ready_asof=2026-06-29`，但 `latest_ready_chain_asof=2026-06-25`。
   - 影响：当前 daily auto 能解释 blocker，但 6/26 之后仍不能生成标准 Model A score。
   - 处理：DNG15 必须做 formal qlib provider refresh 或 validated canonical bridge。

2. `2026-06-22` 至 `2026-06-24` 是安全 shadow/backfill 样本。
   - 证据：这些样本通过 `--skip-finmind --skip-qlib` 生成，`raw_status=DISABLED_BY_SKIP_FINMIND`。
   - 影响：它们可用于观察 DNG13/DNG14 artifact 链路和分类，但不能当作真实抓数成功证明。
   - 处理：执行报告已明确说明，不阻断 DNG14。

### Low

1. `2026-06-26` 存在多个候选 job，DNG14 聚合正确保留了 candidates，且代表 job 选择最新 fully eligible job。
   - `conflict_detected=true` 是合理记录，不是失败。

## 3. Mainline Compliance

审查通过项：

- 已读取 DNG14 要求的主线、工作文档、DNG13 执行报告和审查意见。
- 已消费 `data_tw/ops/daily_auto_update/**/daily_chain_status.json`。
- 已消费 `data_tw/ops/daily_auto_update/**/skipped_asof_ledger.json`。
- 已生成：

```text
data_tw/catalog/dng14_multi_day_chain_observation.json
data_tw/catalog/dng14_multi_day_chain_observation.csv
data_tw/catalog/dng14_latest_status_chain_overlay.json
docs/tw_data_governance/DNG14_MULTI_DAY_AUTOMATIC_OBSERVATION_EXECUTION_REPORT_CN.md
```

- 新增聚合脚本：

```text
scripts/build_tw_dng14_multi_day_chain_observation.py
```

- 同一 asof 多 job 的选择规则符合合同：
  - `required_fields_present=true`
  - `forbidden_actions.all_false=true`
  - `created_at` 最新
  - candidates 保留

- 分类覆盖合同要求：
  - `2026-06-25`：`READY_CHAIN`
  - `2026-06-26`：`RAW_READY_BUT_QLIB_PROVIDER_STALE`
  - `2026-06-27`：`WEEKEND_OR_HOLIDAY_SKIPPED`
  - `2026-06-28`：`WEEKEND_OR_HOLIDAY_SKIPPED`

- 周末样本未计入交易日样本数。
- 未用旧 score 冒充新 asof score。

## 4. Evidence Checked

执行报告：

```text
docs/tw_data_governance/DNG14_MULTI_DAY_AUTOMATIC_OBSERVATION_EXECUTION_REPORT_CN.md
```

聚合产物：

```text
data_tw/catalog/dng14_multi_day_chain_observation.json
data_tw/catalog/dng14_multi_day_chain_observation.csv
data_tw/catalog/dng14_latest_status_chain_overlay.json
```

脚本：

```text
scripts/build_tw_dng14_multi_day_chain_observation.py
```

审查断言：

```bash
python -c "import json, pathlib; obs=json.load(open('data_tw/catalog/dng14_multi_day_chain_observation.json')); ov=json.load(open('data_tw/catalog/dng14_latest_status_chain_overlay.json')); rows={r['asof']: r for r in obs['asof_observations']}; assert rows['2026-06-25']['classification']=='READY_CHAIN'; assert rows['2026-06-26']['classification']=='RAW_READY_BUT_QLIB_PROVIDER_STALE'; assert rows['2026-06-27']['classification']=='WEEKEND_OR_HOLIDAY_SKIPPED'; assert rows['2026-06-28']['classification']=='WEEKEND_OR_HOLIDAY_SKIPPED'; assert rows['2026-06-27']['counts_as_trade_day'] is False; assert rows['2026-06-28']['counts_as_trade_day'] is False; assert obs['observed_trade_day_count'] >= 5; assert ov['forbidden_actions_all_false'] is True; print('DNG14 reviewer artifact assertions PASS')"
```

结果：

```text
DNG14 reviewer artifact assertions PASS
```

验证命令：

```bash
python -m py_compile scripts/run_daily_tw_stock_auto_update.py
python -m py_compile scripts/build_tw_dng14_multi_day_chain_observation.py
python scripts/build_tw_dng14_multi_day_chain_observation.py --json
```

结果均通过。

## 5. Missing Evidence Or Open Questions

1. DNG14 尚未证明 6/26、6/29 可以自动进入 formal qlib provider / Model A score / StrategyInputBundle / readonly context。
2. 真实 daily auto cron 的连续多日观察仍需要后续继续积累；但 DNG14 的多日 artifact aggregation 已可用。
3. 现有最大 blocker 已从“看不清数据缺口”收敛为明确的 provider/calendar 或 canonical bridge 缺口。

## 6. Forbidden Actions Audit

通过。

overlay 显示：

```text
forbidden_actions_all_false=true
forbidden_action_violations=[]
production_go=false
publish_latest_authorized=false
```

未发现：

```text
provider_refresh_triggered=true
provider_publish_triggered=true
accepted_latest_switch_triggered=true
qlib_accepted_latest_switched=true
readonly_latest_published=true
agent_prompt_published=true
production_default_model_or_strategy_switched=true
broker_order_quick_trade_triggered=true
target_position_or_weight_generated=true
```

## 7. Next Work Document

下一阶段建议命名：

```text
DNG15_FORMAL_QLIB_PROVIDER_OR_CANONICAL_BRIDGE_REPAIR
```

### 7.1 背景

DNG14 已证明：

```text
latest_raw_ready_asof=2026-06-29
latest_ready_chain_asof=2026-06-25
latest_provider_stale_asof=2026-06-29
```

这说明 daily auto raw/ops 层可以前进，但 Model A score 所需的 formal qlib provider/calendar 或等价 validated canonical bridge 没有跟上。

### 7.2 目标

DNG15 必须在不发布 latest、不交易的前提下，选择并实现一种安全路线：

```text
Route A: formal qlib provider refresh route
Route B: validated canonical bridge route
```

最低验收目标：

1. 让 `2026-06-26` 从 `RAW_READY_BUT_QLIB_PROVIDER_STALE` 推进到可生成标准 Model A score 的状态。
2. 生成新的 Model A score / ModelSignalArtifact 时，必须使用 formal provider view 或通过 validator 的 canonical ModelInferenceInput。
3. 生成对应 StrategyInputBundle 与 readonly/Agent source context dry-run。
4. 重新运行 DNG14 聚合，证明 `latest_ready_chain_asof` 至少推进到 `2026-06-26`。
5. 保持 publish/latest/trading gate 全关闭。

### 7.3 非目标

DNG15 不得做：

```text
formal accepted latest switch
readonly latest publish
Agent latest publish
production default model/strategy switch
broker/order/quick-trade
target position / target weight
模型训练或调参
用 raw FinMind 直接冒充 qlib feature input
```

### 7.4 执行者必须读取

```text
docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md
docs/tw_data_governance/DNG14_MULTI_DAY_AUTOMATIC_OBSERVATION_EXECUTION_REPORT_CN.md
docs/tw_data_governance/DNG14_MULTI_DAY_AUTOMATIC_OBSERVATION_REVIEW_CN.md
data_tw/catalog/dng14_multi_day_chain_observation.json
data_tw/catalog/dng14_latest_status_chain_overlay.json
scripts/run_daily_tw_stock_auto_update.py
scripts/build_tw_dng14_multi_day_chain_observation.py
```

### 7.5 审查者重点

审查者必须确认：

1. DNG15 没有绕过 provider/canonical validator。
2. 6/26 的 ready 推进不是旧 score 冒充。
3. publish/latest/trading gate 仍关闭。
4. DNG14 overlay 在修复后能机器可读地显示 blocker 减少。

### 7.6 建议 verdict 集合

```text
PASS_GO_DNG16_DAILY_AUTO_MODEL_SCORE_INTEGRATION
PASS_WITH_CONDITIONS_GO_DNG16
FAIL_NEEDS_DNG15_REPAIR
STOP_NEEDS_COORDINATOR_DECISION
```
