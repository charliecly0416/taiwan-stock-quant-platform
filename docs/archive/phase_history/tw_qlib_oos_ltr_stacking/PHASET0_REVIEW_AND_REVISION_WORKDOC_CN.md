# Phase T0 审查结论与修订工作文档

生成日期：2026-06-15

审查对象：

```text
docs/TW_STOCK_QLIB_OOS_LTR_STACKING_MAINLINE_CN.md
docs/tw_qlib_oos_ltr_stacking/PHASET0_EXECUTION_REPORT_CN.md
```

## 1. 审查结论

结论：`T0 暂不通过；不得进入 T1；需先修订 split / label horizon 合同后重新提交审查`。

T0 报告整体没有偏离主线方向：

- 保持了 OOS stacking 主线，没有把旧高收益直接默认化；
- 认可 `2020` 只有在使用 `WF-2020` 这类独立 walk-forward score 时才能进入 LTR train；
- 保持 dynamic universe 主口径，并要求 T2 做 common universe 对照；
- 冻结了 Q0/Q1/Q2 与 L1/L2/L3/L4 的有限窗口矩阵，没有扩展成无边界调参；
- 本轮未训练、未调参、未回放、未改前端/API、未触发 provider/accepted latest/monitor/交易链路。

但 T0 报告存在一个必须先修复的边界问题：

```text
validation end = 2025-06-24
final test start = 2025-07-01
primary label horizon = 10 trading days
```

按本地 qlib calendar：

```text
2025-06-24 line 2546
2025-07-01 line 2551
2025-07-08 line 2556
```

如果 `2025-06-24` 的 validation 样本使用 10 个交易日 label，其 label 终点会落到 `2025-07-08`，已经进入 `2025-07-01..2026-05-07` final test。T0 报告将 `2025-06-25..2025-06-30` 作为 buffer，但这不足以满足 10 trading days primary label horizon guard。

这违反主线对 split 边界污染的审查要求：

```text
是否存在 label horizon 导致 split 边界污染
validation 只能用于选择，不得反复看 final test
final test 不得参与 feature scaling、label bucket fitting、模型选择或窗口选择
```

因此，当前 T0 合同不能作为 T1 输入。

## 2. 必须修订项

执行者需要修订 `PHASET0_EXECUTION_REPORT_CN.md`，至少完成以下事项。

### 2.1 重新冻结 validation / final test 边界

必须选择一种明确口径，不能保留当前含混 buffer。

推荐修订口径 A：

```text
final test:                  2025-07-01..2026-05-07
primary label horizon:       10 trading days
validation label end <=      2025-06-30
validation sample end <=     final_test_start 前第 10 个可交易日
```

执行者需用 qlib day calendar 计算精确的 `validation sample end`，并在报告中写明：

```text
last validation sample date
its 10d label end date
final test start date
```

推荐修订口径 B：

```text
validation:                  2024-07-01..2025-06-24
final test accounting start:  validation 最后一日 10d label 结束之后的下一交易日
```

采用 B 时，必须解释为什么放弃 `2025-07-01..2026-05-07` 同窗口复核口径；若 T2 仍需与 S2F 同窗口比较，则不建议采用 B。

审查偏好：优先采用口径 A，保持 final test 为 `2025-07-01..2026-05-07`。

### 2.2 同步修订所有 split 派生字段

修订后必须同步更新：

- 主 split；
- 备选保守 split；
- `2025-06-25..2025-06-30` buffer 说明；
- T1 降级语义；
- 5d / 10d / 20d horizon guard 规则；
- T1/T2 输入输出合同。

若 20d 只作为 secondary audit horizon，则需要明确：

```text
20d audit 是否参与模型选择；
若参与，必须使用 20 trading days guard；
若不参与，只能作为训练/验证外的事后审计指标，不得用于选择窗口或模型。
```

### 2.3 补一张 split guard 审计表

修订版 T0 报告必须新增表格：

| boundary | sample end | horizon | label end | next split start | pass |
| --- | --- | ---: | --- | --- | --- |
| train -> validation | 待填 | 10d | 待填 | 待填 | yes/no |
| validation -> final test | 待填 | 10d | 待填 | 2025-07-01 | yes/no |
| validation -> final test audit | 待填 | 20d | 待填 | 2025-07-01 | yes/no / not used for selection |

其中 `pass` 不能靠文字判断，必须由 qlib calendar 推导。

## 3. 可保留项

以下内容审查通过，修订时不需要推翻：

- `2020-2021` normalized price / TWII 覆盖判断；
- `2020` 只能使用 `WF-2020` 或等价 OOS fold 的判断；
- `2021` 在 qlib base train 截止 `2020-12-31` 后作为 OOS score 候选区间的判断；
- `trend_score` 排除 input features；
- fixed percentile label bucket policy，不在 validation/test 上 fit bucket；
- dynamic universe 主口径 + T2 common universe 对照；
- Q0/Q1/Q2 和 L1/L2/L3/L4 有限窗口矩阵；
- 禁止训练、调参、回放、前端/API、provider/accepted latest/monitor/交易链路。

## 4. 修订后重新提交条件

执行者重新提交 T0 时，必须给出：

1. 修订后的完整 split 合同；
2. qlib calendar 推导出的 horizon guard 审计表；
3. 说明 final test 是否仍为 `2025-07-01..2026-05-07`；
4. 说明 validation 末端被截掉的样本是否进入任何训练、模型选择或窗口选择；
5. 若保留 2020 进入 LTR train，继续强制使用 `WF-2020` OOS score；
6. 明确 T1 只能做 score/sample/leakage audit，不得训练 LTR 或回放。

重新提交前，不得启动 Phase T1。

## 5. 给执行者的一句话

请先修订 Phase T0：保留当前 OOS score、数据覆盖、dynamic universe、窗口矩阵等已通过内容，但必须用 qlib calendar 重新冻结 validation/final test 的 label horizon guard，确保 validation 的 10d primary label 不跨入 `2025-07-01..2026-05-07` final test；修订完成后重新提交 T0 审查，不得进入 T1。
