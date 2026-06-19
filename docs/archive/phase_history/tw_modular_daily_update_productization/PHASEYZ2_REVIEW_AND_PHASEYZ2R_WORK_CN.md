# Phase YZ2 审查与 Phase YZ2R Execution Price Readiness Repair 工作文档

生成日期：2026-06-18

## 1. YZ2 审查结论

YZ2 模型与正交特征部分通过，但 YZ2 整体不能直接进入完整 YZ3。

原因：

```text
strict E4 orthogonal package 已达到 50/50
Model B 已生成 50 行 LTR rerank artifact
但 execution price readiness 未通过
当前 next_open_available_count = 0
missing_next_open_count = 50
status = execution_price_unavailable
```

根据 YZ2 工作文档和统筹补充意见，YZ3 必须正式固化：

```text
default execution_price_mode = next_open
paper portfolio 模拟成交口径与 replay 默认口径一致
前端展示成交口径
不得在 next_open 缺失时 fallback 到 next_close
```

因此在进入 YZ3 前，必须先做一个小修复阶段：

```text
Phase YZ2R：Execution Price Readiness Repair
```

## 2. 已复核与复跑

审查对象：

```text
docs/tw_modular_daily_update_productization/PHASEYZ2_ORTHOGONAL_DATA_PACKAGE_EXECUTION_REPORT_CN.md
scripts/build_phase_yz2_orthogonal_package.py
scripts/validate_tw_daily_model_signal_artifact.py
backend/tests/test_phase_yz2_orthogonal_package.py
data_tw/artifacts/phase_yz/yz2_orthogonal_feature_package/2026-06-17/manifest.json
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_b_yz2/manifest.json
data_tw/artifacts/phase_yz/yz2_execution_price_readiness/2026-06-17/manifest.json
```

已复跑：

```text
python -m py_compile scripts/build_phase_yz2_orthogonal_package.py scripts/validate_tw_daily_model_signal_artifact.py backend/tests/test_phase_yz2_orthogonal_package.py
python -m pytest backend/tests/test_phase_yz0_clean_registry.py backend/tests/test_phase_yz1_strict_e4_model_adapters.py backend/tests/test_phase_yz2_orthogonal_package.py -q
python scripts/validate_tw_daily_model_signal_artifact.py --manifest data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_b_yz2/manifest.json --json
```

结果：

```text
13 passed
Model B validator passed, row_count=50
```

## 3. YZ2 通过项

### 3.1 Orthogonal readiness 已脱离 P3/fresh global readiness

YZ2 package 明确：

```text
p3_daily_ltr_rerank_latest_used_as_readiness = false
universe_source = YZ1 Model A manifest
scoped_model_id = e4_frozen_qlib_2018_2022
```

### 3.2 strict E4 top50 coverage 通过

YZ2 orthogonal package：

```text
artifact_type = YZ2StrictE4OrthogonalFeaturePackage
row_count = 50
covered_symbols = 50
missing_symbols = []
coverage_ratio = 1.0
feature_schema_column_count = 78
pit_violation_count = 0
no_fallback = true
```

### 3.3 Model B 生成通过

Model B：

```text
model_id = e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
row_count = 50
source_model_a_manifest = YZ1 Model A
source_model_artifact = E3 LTR model
source_feature_artifact = YZ2 orthogonal package
input_scope = YZ1 Model A qlib top50 only
fallback_to_p3_fresh_o4_bridge = false
```

Validator：

```text
ok = true
status = passed
row_count = 50
```

## 4. 阻塞项

Execution price readiness 未通过：

```text
artifact_type = YZ2ExecutionPriceReadiness
execution_price_mode_planned_for_yz3 = next_open
row_count = 50
next_trading_day = null
next_open_available_count = 0
next_close_available_count = 0
close_on_or_before_signal_asof_available_count = 50
missing_next_open_count = 50
missing_next_close_count = 50
status = execution_price_unavailable
no_fallback_to_next_close = true
```

这说明：

```text
YZ2 已正确识别缺失，没有 fallback
但 YZ3 不能在 next_open 缺失时接 replay/paper/frontend 默认执行口径
```

因此：

```text
不得直接进入完整 YZ3
必须先做 YZ2R 修复 next trading day OHLC / execution price readiness
```

## 5. YZ2R 目标

YZ2R 只做：

```text
补齐 signal_asof 后一交易日的本地价格可用性
重新生成 execution price readiness
确保 next_open 50/50 可用
确保 no fallback to next_close
不改模型、不改正交特征、不改前端、不接 replay 收益
```

YZ2R 不做：

```text
重训模型
调参
重新选择策略
replay 收益优劣判断
paper apply/reset 改造
frontend 改造
daily orchestrator 接入
provider publish
accepted latest switch
monitor / broker / order / quick-trade
```

## 6. YZ2R 输入

必须读取：

```text
YZ1 Model A:
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_a/manifest.json

YZ2 Model B:
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_b_yz2/manifest.json

YZ2 execution price readiness:
data_tw/artifacts/phase_yz/yz2_execution_price_readiness/2026-06-17/manifest.json

本地价格源:
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty
qlib calendar:
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt
```

目标 signal_asof：

```text
2026-06-17
```

目标 next trading day：

```text
2026-06-18
```

## 7. 价格数据修复要求

YZ2R 必须优先使用本地已存在、可审计的真实 provider/normalized 数据。

允许：

```text
读取本地 normalized OHLCV
读取本地 provider staging/raw archive
读取已有 qlib normalized dump
生成只读 price readiness artifact
```

如需要补齐 2026-06-18 OHLC，必须满足：

```text
来源可追踪
不是手写伪数据
不是用 close 填 open
不是用 signal_asof close 当 next_open
不是从未来 return / realized PnL 反推
```

如果本地没有 2026-06-18 provider 数据，执行者必须：

```text
保持 blocked
说明缺失数据源
不得进入 YZ3
```

除非用户/审查者明确授权真实外网 provider 拉取，否则 YZ2R 不得联网抓取。

## 8. Execution Price Readiness 合同

YZ2R 输出必须证明，对每个 strict E4 top50 instrument：

```text
signal_asof = 2026-06-17
next_trading_day = 2026-06-18
next_trading_day_open 可用
next_trading_day_close 可用
close_on_or_before_signal_asof 可用
fallback_to_next_close = false
```

通过标准：

```text
row_count = 50
next_open_available_count = 50
next_close_available_count = 50
close_on_or_before_signal_asof_available_count = 50
missing_next_open_count = 0
missing_next_close_count = 0
missing_signal_close_count = 0
status = pass
no_fallback_to_next_close = true
```

如果无法通过：

```text
status = execution_price_unavailable
missing_next_open_count > 0
no_fallback_to_next_close = true
recommended_gate = blocked_before_yz3
```

## 9. YZ2R 产物要求

执行者必须提交：

```text
docs/tw_modular_daily_update_productization/PHASEYZ2R_EXECUTION_PRICE_READINESS_REPAIR_EXECUTION_REPORT_CN.md
```

必须输出：

```text
data_tw/artifacts/phase_yz/yz2r_execution_price_readiness/2026-06-17/manifest.json
data_tw/artifacts/phase_yz/yz2r_execution_price_readiness/2026-06-17/price_availability_audit.csv
data_tw/artifacts/phase_yz/yz2r_execution_price_readiness/2026-06-17/source_trace.json
data_tw/artifacts/phase_yz/yz2r_execution_price_readiness/2026-06-17/forbidden_action_audit.json
```

报告必须包含：

```text
1. 是否找到 2026-06-18 next trading day
2. 2026-06-18 OHLC 数据来源
3. 50 个 strict E4 top50 instrument 的 open/close 可用性
4. 是否存在 open 缺失
5. 是否存在 close 缺失
6. 是否存在 fallback 到 next_close
7. 是否使用外网 provider
8. 是否触发 publish/accepted latest/monitor/broker/order
9. 是否建议进入 YZ3
```

## 10. YZ2R 测试要求

至少执行：

```text
python -m py_compile <新增/修改的 YZ2R scripts>
python -m pytest backend/tests/test_phase_yz0_clean_registry.py backend/tests/test_phase_yz1_strict_e4_model_adapters.py backend/tests/test_phase_yz2_orthogonal_package.py <新增 YZ2R tests> -q
```

新增测试必须覆盖：

```text
next_trading_day = 2026-06-18 或明确 blocked
next_open_available_count = 50 时才允许 pass
missing_next_open_count > 0 时 status 必须 execution_price_unavailable
fallback_to_next_close 全部 false
不得用 close 字段填 open 字段
不得修改 Model A / Model B manifest
不得触发 provider publish / accepted latest / monitor / broker / order / quick-trade
```

## 11. YZ3 放行条件

只有 YZ2R 达到以下条件，才允许进入完整 YZ3：

```text
execution_price_readiness.status = pass
next_open_available_count = 50
missing_next_open_count = 0
no_fallback_to_next_close = true
```

如果 YZ2R 仍 blocked：

```text
YZ3 不得接 replay/paper next_open 默认执行口径
YZ3 不得收口
只能继续停在数据 readiness 修复
```

## 12. 审查重点

审查 YZ2R 时必须确认：

```text
是否真实存在 2026-06-18 OHLC
open 是否是 open，不是 close 回填
next_close 是否仅用于 readiness，不作为 fallback
是否没有收益比较和策略优劣判断
是否没有 provider publish/accepted latest/monitor/broker/order/quick-trade
是否仍保持 YZ2 Model B artifact 不被重新污染
```

若任一不满足，停止，不允许进入 YZ3。
