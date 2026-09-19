# DNG14 Multi-Day Automatic Observation 工作文档

生成日期：2026-06-29

## 1. 背景

DNG13 已通过审查：

```text
PASS_WITH_CONDITIONS_GO_DNG14
```

DNG13 解决的是 job-local 可审计性：每个 daily auto job 可以生成 `daily_chain_status.json` 和 `skipped_asof_ledger.json`。但 DNG13 还没有把这些 job-local 结果聚合到全局 catalog/dashboard，也没有证明多日观察稳定。

DNG14 要补上这个缺口。

## 2. 目标

基于已有 daily auto job artifacts 和必要的安全 backfill/shadow 样本，形成多日观察：

```text
daily_chain_status.json
skipped_asof_ledger.json
-> asof-level aggregation
-> category classification
-> catalog overlay
-> next route decision
```

## 3. 非目标

DNG14 不得执行：

- 真实 FinMind/Yahoo/TWSE 抓数；
- provider refresh / publish；
- formal qlib accepted latest switch；
- readonly latest publish；
- Agent prompt latest publish；
- broker/order/quick-trade；
- target position / target weight；
- 模型训练或调参；
- 用旧 score 冒充新 asof score。

若需要补样本，只能用安全方式触发 daily auto：

```bash
python scripts/run_daily_tw_stock_auto_update.py --asof <YYYY-MM-DD> --force --skip-finmind --skip-qlib --today-earliest-time 00:00
```

该方式只生成 job-local audit artifacts，不代表真实抓数或 production readiness。

## 4. 输入

必须读取：

```text
docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md
docs/tw_data_governance/DNG13_DAILY_AUTO_PRODUCTIONIZATION_CONTRACT_WORK_CN.md
docs/tw_data_governance/DNG13_DAILY_AUTO_PRODUCTIONIZATION_CONTRACT_EXECUTION_REPORT_CN.md
docs/tw_data_governance/DNG13_DAILY_AUTO_PRODUCTIONIZATION_CONTRACT_REVIEW_CN.md
data_tw/ops/daily_auto_update/**/daily_chain_status.json
data_tw/ops/daily_auto_update/**/skipped_asof_ledger.json
```

## 5. 输出

执行者必须生成：

```text
data_tw/catalog/dng14_multi_day_chain_observation.json
data_tw/catalog/dng14_multi_day_chain_observation.csv
data_tw/catalog/dng14_latest_status_chain_overlay.json
docs/tw_data_governance/DNG14_MULTI_DAY_AUTOMATIC_OBSERVATION_EXECUTION_REPORT_CN.md
```

审查者必须生成：

```text
docs/tw_data_governance/DNG14_MULTI_DAY_AUTOMATIC_OBSERVATION_REVIEW_CN.md
```

## 6. 聚合规则

### 6.1 asof 选择

同一 asof 可能有多个 job。执行者必须按以下优先级选择代表 job：

1. 有 `daily_chain_status.json` 且 `required_fields_present=true`。
2. forbidden actions `all_false=true`。
3. created_at 最新。
4. 如果多个 job 状态冲突，保留全部 candidates，并在代表 job 里写 `selection_reason`。

### 6.2 分类枚举

每个 asof 必须分类为以下之一：

```text
READY_CHAIN
RAW_READY_BUT_QLIB_PROVIDER_STALE
DATA_WINDOW_WAIT
WEEKEND_OR_HOLIDAY_SKIPPED
MODEL_A_SCORE_MISSING
STRATEGY_OR_READONLY_CONTEXT_MISSING
PUBLISH_READY_BUT_NOT_PUBLISHED
BLOCKED_OTHER
```

最低要求：

- `2026-06-25` 应分类为 `READY_CHAIN` 或等价 ready。
- `2026-06-26` 应分类为 `RAW_READY_BUT_QLIB_PROVIDER_STALE`。
- `2026-06-27`、`2026-06-28` 如纳入样本，应分类为 weekend/holiday，不得和 provider stale 混淆。

### 6.3 观察样本数

目标是至少 5 个交易日或等价 shadow/backfill 样本。

如果当前只能覆盖不足 5 个交易日，执行者必须：

1. 明确写 `observed_trade_day_count`。
2. 明确写 `required_additional_trade_days`。
3. 若使用等价 backfill/shadow，说明每个样本是否真实交易日、是否只是只读 artifact backfill。
4. 不得把周末样本计入 trade-day count。

## 7. catalog overlay 要求

`dng14_latest_status_chain_overlay.json` 必须说明：

```text
latest_ready_chain_asof
latest_raw_ready_asof
latest_provider_stale_asof
latest_model_a_ready_asof
latest_strategy_context_ready_asof
latest_readonly_context_ready_asof
current_blocker
recommended_next_route
```

如果当前最大 blocker 是 6/26 之后 formal qlib provider/calendar 没推进，应建议：

```text
formal_qlib_provider_refresh_route
or
validated_canonical_bridge_route
```

不得建议绕过 provider view 直接用 raw FinMind 打 Model A score。

## 8. 验证要求

至少运行：

```bash
python -m py_compile scripts/run_daily_tw_stock_auto_update.py
```

如果新增聚合脚本，也必须运行：

```bash
python -m py_compile <new_script>
python <new_script> --json
```

若没有新增脚本、只做文档/人工聚合，必须在执行报告说明原因，并提供机器可读 JSON/CSV 产物。

## 9. 执行报告要求

执行报告必须包含：

1. 样本来源列表。
2. asof-level 聚合表。
3. 交易日样本数与不足项。
4. 6/25 ready 解释。
5. 6/26 provider stale 解释。
6. 周末/假日处理。
7. catalog overlay 结论。
8. forbidden actions audit。
9. 是否建议进入 DNG15，还是先做 provider/bridge repair。

## 10. 审查 verdict

审查者只能给：

```text
PASS_GO_DNG15
PASS_WITH_CONDITIONS_GO_DNG15
FAIL_NEEDS_DNG14_REPAIR
STOP_NEEDS_COORDINATOR_DECISION
```

DNG14 通过不等于 production Go。它只表示多日观察/聚合可用。
