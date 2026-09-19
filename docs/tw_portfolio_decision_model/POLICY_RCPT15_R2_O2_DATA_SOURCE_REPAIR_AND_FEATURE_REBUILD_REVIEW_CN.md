---
created_at: 2026-06-26
status: review
phase: RCPT15_R2_O2_DATA_SOURCE_REPAIR_AND_FEATURE_REBUILD
verdict: PASS_READY_FOR_RCPT15_R3_ISOLATED_RERANK
---

# RCPT15_R2 O2 Data Source Repair And Feature Rebuild 审查意见

## 1. 审查结论

结论：

```text
PASS_READY_FOR_RCPT15_R3_ISOLATED_RERANK
```

可以授权进入下一步 `RCPT15_R3_ISOLATED_RERANK`，但 R3 必须继续保持隔离输出，不得写 formal latest pointer、provider accepted latest、qlib accepted latest、production/default/latest/order/target/broker。

## 2. 本轮实际修复了什么数据

本轮补的是 O2 / orthogonal LTR rerank 所需的两类正交特征源，不是普通价格日线：

```text
institutional_flow = FinMind TaiwanStockInstitutionalInvestorsBuySell
margin_short = FinMind TaiwanStockMarginPurchaseShortSale
```

补源窗口：

```text
2026-06-11..2026-06-25
```

覆盖对象：

```text
R1 shadow top50 union symbols = 99
```

主要产物：

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r2_o2_data_source_repair_and_feature_rebuild/
data_tw/experiments/ltr_orthogonal_features_controlled/rcpt15_r2_o2_pit_safe_feature_builder/
```

## 3. 为什么原本没有这些数据

自动日更脚本确实在运行，但默认 M3 readonly path 只拉 FinMind 价格日线，并明确跳过：

```text
--no-institutional
--no-margin
```

而 O2 需要的正是 institutional/margin 数据。因此“每日自动脚本运行”并不等于“O2 source freshness / daily_ltr_rerank / 正交特征重建会自动推进”。

本轮 `daily_auto_update_gap_evidence.csv` 也显示：

```text
provider_publish_triggered = false
latest_signal_updated = false
qlib_legacy_provider_path_skipped = true
```

这是安全合同导致的下游研究数据未自动推进，不是 cron 未运行。

## 4. 关键证据

RCPT15_R2 专用候选 O2：

```text
gate = PASS_READY_FOR_RCPT15_R3_ISOLATED_RERANK
candidate_o2_trade_date_max = 2026-06-25
candidate_o2_available_at_max = 2026-06-26
source_pass = true
coverage_pass = true
forbidden_pass = true
available_at_le_trade_date_rows = 0
```

O2-builder 风格隔离产物：

```text
gate = phase_o2_pit_safe_feature_builder_passed
feature_daily_date_max = 2026-06-25
available_at_max = 2026-06-26
used_available_at_gt_sample_date_rows = 0
used_trade_date_gt_sample_date_rows = 0
missing_raw_snapshot_path_rows = 0
```

正式 latest pointer 未被切换：

```text
latest_orthogonal_features_latest.json asof = 2026-06-17
```

## 5. 6/19 特殊情况

2026-06-19 在 R1 `target_date_backfill_matrix.csv` 中被标为 trading day，但 staged qlib calendar 不包含该日，R1 产出的 shadow signal 是空输入：

```text
prediction_rows = 0
top50_rows = 0
```

因此 6/19 不是 O2 coverage 失败。本轮 R2 已将它分类为：

```text
no_signal_input_excluded_from_o2_gate
```

R3 应只对有 shadow top50 的日期做 rerank；6/19 应跳过或单独记录为 R1/calendar classification issue。

## 6. 边界审查

通过：

```text
provider_publish = PASS_NOT_PERFORMED
accepted_latest_switch = PASS_NOT_PERFORMED
latest_signal_json_write = PASS_NOT_PERFORMED
daily_ltr_rerank_latest_json_write = PASS_NOT_PERFORMED
latest_orthogonal_features_latest_json_write = PASS_NOT_PERFORMED
production/default/latest/provider/frontend/Agent/monitor/order mutation = PASS_NOT_PERFORMED
target/order/broker artifact = PASS_NOT_PRESENT
```

注意：执行 agent 同时改造了 archive/historical_research 脚本，使其支持 `--asof`、`--symbols-file`、`--no-write-latest-pointer`、`--rcpt15-r2-isolated` 等隔离参数。该改动方向合理，但后续若要纳入长期工具链，需要单独做一次历史脚本兼容性审查。

## 7. 下一步授权

授权：

```text
RCPT15_R3_ISOLATED_RERANK
```

R3 要求：

1. 使用 R1 shadow signal/top50 与 R2 O2 isolated artifacts；
2. 只写 RCPT15_R3 隔离目录；
3. 不写任何 formal latest pointer；
4. 跳过或单独标记 2026-06-19 no-signal input；
5. 输出 rerank score snapshot、coverage audit、PIT audit、forbidden scope audit、validator report；
6. R3 结束后再决定是否回到 RCPT14A/RCPT shadow accumulation rerun。
