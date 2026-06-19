# Phase O1R 审查结论：覆盖与 available_at 合同修复

生成日期：2026-06-15

审查对象：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEO1R_COVERAGE_AVAILABLE_AT_REPAIR_WORK_CN.md
docs/tw_ltr_orthogonal_features_controlled/PHASEO1R_COVERAGE_AVAILABLE_AT_REPAIR_EXECUTION_REPORT_CN.md
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o1r_coverage_available_at_repair/
```

## 1. 审查结论

结论：

```text
需要用户确认
```

执行者本轮没有发现控制变量越界。O1R 只处理覆盖补齐与 available_at 合同审计，没有训练 qlib/LTR，没有回放收益率，没有构建 treatment sample，没有修改 Phase1C control，也没有触发 frontend/API/provider/accepted latest/monitor/交易链路。

但 O1R 推荐把主线原始合同：

```text
available_at = next_trading_day(trade_date)
```

调整为：

```text
available_at >= next_trading_day(trade_date)
PIT-safe delayed availability
```

这是主线数据合同变更，必须由用户确认。审查者不能静默放行。

## 2. 覆盖补齐审查

O1R 覆盖补齐通过。

覆盖前后：

| category | before symbols with rows | after symbols with rows | absent before | absent after |
| --- | ---: | ---: | ---: | ---: |
| institutional_flow | 103 | 150 | 47 | 0 |
| margin_short | 103 | 150 | 47 | 0 |

47 个 absent control symbols 在两个数据族中均显示 fetch success。未发现因为补覆盖而引入月营收或其他数据源。

需要保留的覆盖风险：

```text
institutional_flow low coverage < 0.95: 4 symbols
margin_short low coverage < 0.95: 9 symbols
```

尤其融资融券仍有极低覆盖：

```text
TW7769: 0.017949
TW6919: 0.038415
TW3131: 0.110801
TW6683: 0.118250
TW4749: 0.194471
```

这些低覆盖不阻止进入 O2，但 O2/O3 必须显式 missing flag + neutral fill，不能删行，O5/O6 必须报告这些股票/日期对结果解释的影响。

## 3. available_at 与 PIT 安全审查

禁止性提前可见未发现：

```text
available_at <= trade_date rows: 0
prohibited_early_visible_rows: 0
```

这意味着当前没有发现同日可见或未来函数倒灌。

但 exact T+1 未通过：

| category | rows | exact_t1_rows | delayed_rows | missing_calendar_rows | pit_safe_delayed_pass |
| --- | ---: | ---: | ---: | ---: | --- |
| institutional_flow | 208059 | 207464 | 396 | 197 | yes |
| margin_short | 203123 | 202925 | 3 | 193 | yes |

另有少量 `available_at < next_trading_day`：

```text
institutional_flow: 2
margin_short: 2
```

这些行没有触发 `available_at <= trade_date`，报告分类为 `calendar_gap`，更像交易日历期望值错配，不是同日提前可见。但 O2 必须继续保留该审计列，不能把这些行无条件当作 exact T+1。

## 4. 合同判断

不建议继续坚持 strict exact T+1。

原因：

```text
combined archive 中存在 delayed availability / listing_status_gap / calendar_gap；
强行 exact T+1 会要求人工提前 available_at 或剔除大量合法延迟可见记录；
人工提前 available_at 会破坏 PIT 安全。
```

可以接受的合同是：

```text
PIT-safe delayed availability
available_at >= next_trading_day(trade_date)
```

但必须附带硬约束：

```text
O2/O3 按真实 available_at 做 as-of join；
不得把 delayed rows 静默当作 exact T+1；
不得人工提前 available_at；
不得用未来数据补历史特征；
每行保留 delay_days / delay_reason / available_at_contract；
低覆盖处 neutral fill + missing flag，不删 control rows。
```

## 5. 控制变量边界

未发现 O1R 偏离主线：

```text
未训练 qlib/LTR
未构建 treatment sample
未做收益率回放
未改 Phase1C control
未改 LTR 样本、标签、训练窗口、模型参数
未新增月营收 YoY
未新增其他数据源
未新增 filter / market gate / turnover rule
未写 provider / accepted latest
未改 frontend/API/monitor/交易链路
```

联网拉取发生过，但属于 O1R 工作文档允许范围，且只写入本地主线实验目录。

## 6. 是否允许进入 O2

当前不应直接进入 O2。

必须先由用户确认是否接受以下合同变更：

```text
从 exact T+1
改为 PIT-safe delayed availability
```

如果用户确认接受，则审查者建议允许进入 O2，gate 可记录为：

```text
phase_o1r_passed_after_user_confirmation_for_pit_safe_delayed_availability
```

进入 O2 后只允许做：

```text
raw archive / normalized daily table / feature builder；
PIT-safe as-of join 设计；
feature dictionary；
missing report；
PIT leakage audit。
```

仍禁止：

```text
训练 qlib/LTR；
构建最终 treatment LTR sample 并训练；
做收益率回放；
改变 control rows / label / original features；
新增过滤器、阈值、market gate、turnover rule；
改 frontend/API/provider/accepted latest/monitor/交易链路。
```

## 7. 最终判断

```text
覆盖补齐：通过
PIT 禁止性提前可见：未发现
exact T+1 合同：不通过
PIT-safe delayed availability：可接受，但必须用户确认
控制变量边界：通过
是否允许进入 O2：用户确认 delayed availability 后才允许
```
