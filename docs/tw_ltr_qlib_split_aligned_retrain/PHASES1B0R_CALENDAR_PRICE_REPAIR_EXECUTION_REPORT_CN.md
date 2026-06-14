# Phase S1B0R Calendar/Price Trading-Day 修复诊断执行报告

生成日期：2026-06-14

## 1. 执行范围

本轮按 `docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B0_REVIEW_AND_USER_DECISION_CN.md` 路线 A 执行，只做 calendar / price trading-day 修复诊断与 dynamic universe feasibility 重算。

已执行：

- 逐日核查 S1B0 中 `selected count < 50` 的 63 个低覆盖日期；
- 对比 qlib `day.txt` calendar；
- 对比 `TWII.csv` normalized price calendar；
- 对比低覆盖日期的 normalized stock price breadth；
- 用修复交易日历重新计算 dynamic universe feasibility。

未执行：

- 未训练 qlib；
- 未训练 LTR；
- 未生成 qlib score/rank；
- 未构建 LTR 样本；
- 未跑回放；
- 未调参；
- 未改前端/API；
- 未联网；
- 未触发 provider refresh/publish；
- 未切换 accepted latest；
- 未触发 monitor、broker、orders、quick-trade 或任何交易链路。

## 2. 产物

| 产物 | 路径 |
| --- | --- |
| 低覆盖日期逐日诊断 | `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b0r_calendar_price_repair/phase_s1b0r_low_coverage_date_diagnosis.csv` |
| 修复后 dynamic universe feasibility | `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b0r_calendar_price_repair/phase_s1b0r_dynamic_universe_feasibility_repaired.csv` |
| 修复后 daily 明细 | `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b0r_calendar_price_repair/phase_s1b0r_dynamic_universe_feasibility_repaired_daily.csv` |
| 修复前后对比 | `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b0r_calendar_price_repair/phase_s1b0r_before_after_feasibility_comparison.csv` |
| gate summary | `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b0r_calendar_price_repair/phase_s1b0r_gate_summary.json` |

## 3. 修复口径

本轮不联网、不引入外部交易日数据，使用本地可审查口径：

```text
repaired_scoring_calendar = qlib day.txt ∩ TWII normalized price calendar
```

输入：

- qlib calendar：`qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt`
- price calendar：`qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TWII.csv`
- 原始 daily feasibility：`phase_s1b0_dynamic_universe_feasibility_daily.csv`

解释：

- qlib `day.txt` 代表 qlib provider 可用日历；
- `TWII.csv` 有价格的日期代表本地台湾市场价格日历；
- 不在 qlib `day.txt` 的日期不应进入 S1 scoring calendar；
- 不在 `TWII.csv` 的日期不应作为台湾市场价格可用交易日。

## 4. 低覆盖日期逐日结论

S1B0 中共有 `63` 个 `selected count < 50` 日期。

逐日诊断结果：

| 项目 | 数量 |
| --- | ---: |
| low coverage dates checked | `63` |
| not in qlib calendar | `63` |
| not in TWII price calendar | `53` |
| in both qlib and TWII but stock breadth < 50 | `0` |

结论：

```text
原 63 个 selected count < 50 低覆盖日期全部不是 qlib day.txt 中的有效 qlib scoring calendar 日期。
```

其中多数也不在 TWII 价格日历，符合春节、节假日、补班日或价格不可用日造成的 calendar/price mismatch 特征。

## 5. 修复后 Feasibility

修复后按 `qlib day.txt ∩ TWII price calendar` 重算：

| split | year | dates | selected min | selected median | selected max | dates selected < 50 | dates selected < 150 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 2015 | 169 | 145 | 149 | 150 | 0 | 92 |
| train | 2016 | 241 | 146 | 150 | 150 | 0 | 70 |
| train | 2017 | 243 | 147 | 150 | 150 | 0 | 43 |
| train | 2018 | 245 | 149 | 150 | 150 | 0 | 86 |
| train | 2019 | 241 | 149 | 150 | 150 | 0 | 22 |
| train | 2020 | 245 | 150 | 150 | 150 | 0 | 0 |
| validation | 2021 | 243 | 148 | 150 | 150 | 0 | 115 |
| validation | 2022 | 246 | 148 | 150 | 150 | 0 | 50 |
| test | 2023 | 239 | 148 | 150 | 150 | 0 | 56 |
| test | 2024 | 242 | 148 | 150 | 150 | 0 | 80 |
| test | 2025 | 116 | 149 | 150 | 150 | 0 | 5 |

修复后汇总：

| 指标 | 值 |
| --- | ---: |
| selected count < 50 | `0` |
| selected count < 150 | `619` |
| min selected count | `145` |
| repaired calendar dates in prior daily range | `2470` |

## 6. 判断

### 6.1 已修复的问题

S1B0 阻断中的核心疑点成立：`selected count < 50` 主要来自 calendar/price trading-day 口径错配。

修复后：

```text
selected count < 50 = 0
```

因此不能再把原 63 个低覆盖日作为 dynamic universe 不可行的证据。

### 6.2 仍需审查的问题

修复后仍有 `619` 个交易日 `selected count < 150`，但最低为 `145`，中位数为 `150`。

这不是 calendar/price trading-day 失败，而是严格 Top150 满额规则下的轻微短缺。下一步需要审查者决定：

1. 是否允许 dynamic universe 使用 `up to 150`，并要求最低 selected count >= 145；
2. 是否要求对 `<150` 日期继续做 symbol-level 缺口归因；
3. 是否仍坚持每天必须满 150，只要不满即阻断。

执行者本轮不做该决策。

## 7. 越权检查

本轮未发现越权：

- `no_qlib_training = true`
- `no_ltr_training = true`
- `no_score_generation = true`
- `no_ltr_sample_build = true`
- `no_replay = true`
- `no_parameter_tuning = true`
- `no_frontend_api = true`
- `no_provider_refresh_publish = true`
- `no_accepted_latest_switching = true`
- `no_monitor_or_trading_chain = true`

## 8. Gate 建议

建议 gate：

```text
s1b0r_calendar_price_repair_pass_request_s1b1_policy_review
```

理由：calendar/price 修复后，原 `selected count < 50` 低覆盖阻断已消除；剩余为 Top150 精确满额容忍度问题，应由审查者在下一步 S1B1 前冻结。
