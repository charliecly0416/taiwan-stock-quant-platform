# Phase O2 审查结论：PIT-safe Feature Builder

生成日期：2026-06-15

审查对象：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEO2_PIT_SAFE_FEATURE_BUILDER_WORK_CN.md
docs/tw_ltr_orthogonal_features_controlled/PHASEO2_PIT_SAFE_FEATURE_BUILDER_EXECUTION_REPORT_CN.md
scripts/build_orthogonal_ltr_phase_o2_pit_safe_features.py
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/
```

## 1. 审查结论

结论：

```text
通过
```

推荐 gate：

```text
phase_o2_pit_safe_feature_builder_passed
```

本轮没有发现需要停下来阻塞沟通的问题。执行者没有训练 qlib/LTR，没有做收益率回放，没有构建最终 treatment LTR sample，没有修改 Phase1C control，也没有触发 frontend/API/provider/accepted latest/monitor/交易链路。

允许进入 Phase O3，但 O3 必须继续受控，只能做 treatment sample row-aligned 拼接，不能训练。

## 2. 合同边界审查

O2 正确继承了用户已确认的合同：

```text
available_at >= next_trading_day(trade_date)
PIT-safe delayed availability
as-of join uses available_at <= sample_date
```

输出中保留了：

```text
trade_date
available_at
next_trading_day
delay_days
delay_reason
available_at_contract
raw_snapshot_id
fetched_at
raw_snapshot_path
raw_checksum_or_size
lineage_source
```

未发现把 delayed rows 静默当作 exact T+1。

## 3. 产物完整性

O2 输出产物齐全：

```text
feature_dictionary.csv
normalized_feature_daily.csv
pit_normalized_daily_with_lineage.csv
feature_builder_manifest.json
pit_lineage_audit.csv
pit_leakage_audit.csv
missing_by_feature_family.csv
missing_by_symbol.csv
missing_by_date.csv
delay_distribution.csv
phaseo2_summary.json
```

Feature family 范围符合主线，只包含：

```text
institutional_flow
margin_short
```

未纳入月营收 YoY，也未引入 O1R 未审查的新数据源。`buy_sell_over_volume_ratio` 因 volume 不在 O1R 审查字段内被延后，这是正确处理。

## 4. Row / Symbol / Lineage

O2 feature daily artifact：

```text
feature_daily_rows: 312022
feature_daily_symbol_count: 150
feature_daily_date_min: 2022-01-03
feature_daily_date_max: 2026-06-10
```

分族 lineage：

| family | rows | symbols | lineage sources | missing raw path |
| --- | ---: | ---: | --- | ---: |
| institutional_flow | 158317 | 150 | phase0e / phaseo1r | 0 |
| margin_short | 153705 | 150 | phase0e / phaseo1r | 0 |

使用 Phase0E manifest 做既有 103 支股票 lineage 映射是合理的；O1R 补齐的是缺失 47 支，O2 需要合并 Phase0E 与 PhaseO1R 两类 archive 才能覆盖完整 150 支 control symbols。

## 5. PIT Leakage 审查

执行报告中的 as-of audit：

| family | control rows checked | missing rows | missing ratio | available_at > sample_date | trade_date > sample_date |
| --- | ---: | ---: | ---: | ---: | ---: |
| institutional_flow | 159993 | 595 | 0.003719 | 0 | 0 |
| margin_short | 159993 | 5417 | 0.033858 | 0 | 0 |

禁止性提前可见：

```text
available_at <= trade_date rows: 0
```

这满足 O2 PIT-safe as-of join 要求。

## 6. Rolling 特征附加审查

脚本中 rolling 特征按 `trade_date` 在 symbol 内滚动构造。该实现的潜在风险是：如果 `available_at` 随 `trade_date` 非单调，rolling window 可能包含当时尚未可见的历史行。

审查者追加只读检查：

```text
按 feature_family + symbol + trade_date 排序，
检查 available_at 是否单调不降。
```

结果：

```text
nonmonotonic_groups: 0
```

因此当前 O2 artifact 未发现 rolling 特征可见性倒退问题。

但 O3 必须把这一点作为正式审计项保留：

```text
rolling_window_available_at_monotonic_groups == 0
```

如 O3 重新生成或改写 feature builder，必须重新审计。

## 7. 缺失与低覆盖风险

整体 missing ratio：

```text
institutional_flow: 0.3719%
margin_short: 3.3858%
```

低覆盖风险仍集中在融资融券个别股票：

```text
TW7769
TW6919
TW3131
TW6683
TW4749
TW6805
TW6446
TW6789
TW6770
```

这不阻止进入 O3，但 O3/O5/O6 必须保留：

```text
neutral fill
missing flag
missing ratio by symbol/date/family
增益是否集中来自高覆盖股票的审计
```

不得因为缺失删除 control rows。

## 8. 是否允许进入 O3

允许进入 O3。

O3 只允许做：

```text
读取 Phase1C control LTR sample；
按 symbol + sample_date 做 PIT-safe as-of join；
生成 treatment candidate sample；
输出 row-level 对齐报告；
输出 label hash / original feature hash /新增 feature schema diff；
输出 missing flag / delay flag / PIT leakage audit。
```

O3 硬门槛：

```text
control_rows == treatment_rows
control_label_hash == treatment_label_hash
control_original_feature_hash == treatment_original_feature_hash
新增列只来自 O2 feature dictionary
used_available_at_gt_sample_date_rows == 0
used_trade_date_gt_sample_date_rows == 0
rolling_window_available_at_monotonic_groups == 0
不得因缺失删除样本
```

O3 仍禁止：

```text
训练 qlib/LTR
做收益率回放
改变 Phase1C control
改变 label / 原始特征 / 训练窗口 / 回放窗口
新增过滤器、阈值、market gate、turnover rule
改 frontend/API/provider/accepted latest/monitor/交易链路
```

## 9. 最终判断

```text
O2 执行合规；
PIT as-of 审计通过；
raw lineage 完整；
feature dictionary 范围合规；
缺失风险已显式化；
允许进入 O3。
```
