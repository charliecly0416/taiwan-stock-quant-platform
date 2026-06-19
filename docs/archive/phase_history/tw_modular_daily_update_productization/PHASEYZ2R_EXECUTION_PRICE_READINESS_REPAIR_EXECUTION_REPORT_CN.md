# PHASE YZ2R Execution Price Readiness Repair 执行报告

执行日期：2026-06-18

## 1. 执行范围

本次执行 `PHASEYZ2_REVIEW_AND_PHASEYZ2R_WORK_CN.md` 中的 YZ2R：Execution Price Readiness Repair。

本阶段只做：

- 只读检查 `2026-06-17` strict E4 top50 的 `2026-06-18` next_open / next_close 可用性
- 读取本地 qlib calendar 与本地 normalized OHLCV
- 生成 YZ2R execution price readiness artifact
- 明确 blocked 状态与不能进入完整 YZ3 的 gate

本阶段未做：联网抓取、provider refresh/publish、accepted latest switch、训练、调参、策略重选、replay 收益比较、paper apply/reset、frontend、daily orchestrator、monitor、broker、order、quick-trade。

## 2. 修改文件

- `scripts/build_phase_yz2r_execution_price_readiness.py`
- `backend/tests/test_phase_yz2r_execution_price_readiness.py`

## 3. 输入

读取：

```text
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_a/manifest.json
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_b_yz2/manifest.json
data_tw/artifacts/phase_yz/yz2_execution_price_readiness/2026-06-17/manifest.json
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt
```

目标：

```text
signal_asof = 2026-06-17
target_next_trading_day = 2026-06-18
execution_price_mode_planned_for_yz3 = next_open
```

## 4. 是否找到 2026-06-18 next trading day

未找到。

当前 qlib calendar 最后一日为：

```text
2026-06-17
```

YZ2R manifest 中：

```text
calendar_next_trading_day = null
calendar_contains_target_next_day = false
```

## 5. 2026-06-18 OHLC 数据来源

未找到可用的本地 2026-06-18 OHLC。

已检查本地价格源：

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty
```

并额外做了本地 CSV 只读扫描，未发现任何 `2026-06-18` 价格行。

因此未补写 calendar，未补写 normalized price，未构造任何 OHLC。

## 6. YZ2R 产物

manifest：

```text
data_tw/artifacts/phase_yz/yz2r_execution_price_readiness/2026-06-17/manifest.json
```

price audit：

```text
data_tw/artifacts/phase_yz/yz2r_execution_price_readiness/2026-06-17/price_availability_audit.csv
```

source trace：

```text
data_tw/artifacts/phase_yz/yz2r_execution_price_readiness/2026-06-17/source_trace.json
```

forbidden action audit：

```text
data_tw/artifacts/phase_yz/yz2r_execution_price_readiness/2026-06-17/forbidden_action_audit.json
```

## 7. 可用性结果

YZ2R manifest 结果：

```text
row_count = 50
next_open_available_count = 0
next_close_available_count = 0
close_on_or_before_signal_asof_available_count = 50
missing_next_open_count = 50
missing_next_close_count = 50
missing_signal_close_count = 0
open_equals_signal_close_count = 0
status = execution_price_unavailable
recommended_gate = blocked_before_yz3
no_fallback_to_next_close = true
no_fallback_to_signal_close = true
```

说明：50 个 strict E4 top50 instrument 均有 `close_on_or_before_signal_asof`，但本地数据没有 `2026-06-18` next_open / next_close。

## 8. Fallback 与伪数据检查

YZ2R 未做 fallback：

```text
fallback_to_next_close = false
fallback_to_signal_close = false
```

YZ2R 未用 close 填 open：

```text
open_equals_signal_close_count = 0
manual_or_synthetic_ohlc = false
```

YZ2R 未从 future return / realized PnL 反推价格。

## 9. 外网与生产写路径

YZ2R 未使用外网 provider：

```text
external_network_used = false
```

未触发：

```text
provider_refresh = false
provider_publish = false
accepted_latest_switch = false
monitor_write = false
monitor_scan = false
broker_order = false
quick_trade = false
paper_apply_reset_write = false
frontend_change = false
```

## 10. 验证命令与结果

已执行：

```bash
python -m py_compile scripts/build_phase_yz2r_execution_price_readiness.py backend/tests/test_phase_yz2r_execution_price_readiness.py
```

结果：通过。

已执行：

```bash
python scripts/build_phase_yz2r_execution_price_readiness.py --signal-asof 2026-06-17 --json
```

结果：

```text
status = execution_price_unavailable
next_open_available_count = 0
missing_next_open_count = 50
recommended_gate = blocked_before_yz3
```

已执行：

```bash
python -m pytest backend/tests/test_phase_yz0_clean_registry.py backend/tests/test_phase_yz1_strict_e4_model_adapters.py backend/tests/test_phase_yz2_orthogonal_package.py backend/tests/test_phase_yz2r_execution_price_readiness.py -q
```

结果：`17 passed in 1.16s`

## 11. 结论

YZ2R 已按要求完成修复检查，但本地没有 `2026-06-18` OHLC 数据，因此 execution price readiness 仍为 blocked。

不建议进入完整 YZ3。只有满足以下条件后才允许进入完整 YZ3：

```text
execution_price_readiness.status = pass
next_open_available_count = 50
missing_next_open_count = 0
no_fallback_to_next_close = true
```

当前 gate：

```text
recommended_gate = blocked_before_yz3
```
