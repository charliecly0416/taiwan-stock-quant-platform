# Phase T2 审查结论与后续工作文档

生成日期：2026-06-15

审查对象：

```text
docs/tw_qlib_oos_ltr_stacking/PHASET2_EXECUTION_REPORT_CN.md
docs/tw_qlib_oos_ltr_stacking/PHASET2_WORKDOC_CN.md
data_tw/experiments/tw_qlib_oos_ltr_stacking/phase_t2/
```

## 1. 审查结论

结论：

```text
T2 报告作为只读研究执行结果可以接受；
不得进入 T3 默认候选；
不得切换默认策略；
若继续推进，必须先做 T2R 补充审计。
```

推荐 gate：

```text
phase_t2_review_passed_negative_result_do_not_promote_default
```

原因：

- T2 遵守了只读边界，未发现 provider refresh / publish、accepted latest switching、monitor write/scan、broker、orders、quick-trade、target position / target weight 等越界；
- final test 未用于窗口选择，`phase_t2_overfit_audit.csv` 显示 `final_test_used_for_selection=False`；
- 但 validation 中 Q0/L1-L4 全部为负收益，最终 Q0/L4 只是亏损最小；
- final test 中 old/frozen simple 大幅正收益，但 validation 到 final test 方向反转，稳定性不足；
- old/frozen simple 回撤显著恶化；
- old/frozen turnover-controlled 没有超过 fresh qlib/top50 adaptive；
- old/frozen final test 特征只覆盖 overlap-feature universe，不是完整 dynamic universe；
- 贡献审计仍是 sell-notional proxy，不是逐票真实 PnL attribution。

因此，本轮不能支持默认化，只能支持“继续做严格补充审计或停止默认候选推进”。

## 2. 通过项

以下内容审查通过：

### 2.1 只读安全边界

报告和产物未显示真实交易或写链路触发：

```text
provider_refresh_publish=false
accepted_latest_switching=false
monitor_or_trading_chain=false
frontend_api=false
broker_orders_quick_trade=false
```

安全关键词检索只命中否定性声明、历史回放字段或贡献 proxy 说明，未发现行动建议。

### 2.2 Final test provenance

T2 输出了 final test score provenance：

```text
score window: 2025-07-01..2026-05-07
qlib train end: 2020-12-31
usage: inference_only
OOS_pass: True
```

但该 provenance 也暴露覆盖限制：

```text
old_score_rows: 30475
feature_overlap_rows: 22523
dates: 205
```

这意味着 old/frozen T2 LTR 结果不能宣称为完整 old dynamic universe。

### 2.3 窗口选择未使用 final test

`phase_t2_overfit_audit.csv`：

```text
selected_window_id: Q0_L4_4y
selection_basis: validation_fee_tax_adjusted_net_return_then_drawdown
validation_return: -0.130647
final_return: 1.221918
final_test_used_for_selection: False
```

没有发现 final test 事后挑窗口的证据。

### 2.4 Common universe 对照已输出

common universe 下：

```text
fresh_qlib_top50_adaptive:       0.663150, max_drawdown -0.088516
old_frozen_t2_ltr_simple:        1.221918, max_drawdown -0.148581
old_frozen_t2_ltr_turnover_ctl:  0.579378, max_drawdown -0.083835
```

结果支持“simple 收益高但回撤显著更差；低换手版本不如 fresh baseline”的报告判断。

## 3. 阻止进入 T3 的问题

### 3.1 Validation 全负，final test 大正

Q0/L1-L4 validation 结果：

```text
Q0_L4_4y: -0.130647
Q0_L1_1y: -0.170079
Q0_L2_2y: -0.233877
Q0_L3_3y: -0.299983
```

这说明 LTR stacking 在 validation 上没有形成稳定正收益。final test 的 `1.221918` 不能直接解释为稳定泛化。

### 3.2 回撤恶化明显

common universe：

```text
fresh baseline max_drawdown:       -0.088516
old_frozen_t2_ltr_simple drawdown: -0.148581
```

收益提升伴随更差回撤，不满足“不能只看收益率”的主线要求。

### 3.3 Overlap-feature universe 限制

old/frozen final test 使用：

```text
phase3a0 old qlib score/rank + S2C same-date historical features
```

最终 feature overlap 行数仅 `22523 / 30475`。这可能引入覆盖偏差，不能把结果包装成完整 old/frozen dynamic universe 结论。

### 3.4 贡献审计仍不够

当前 contribution audit 是：

```text
historical sell notional proxy
```

它不是逐 lot / 逐票真实 PnL attribution。若要讨论产品化或默认候选，必须补真实贡献归因。

### 3.5 Q1/Q2 没有完整展开

本轮实际训练的是：

```text
Q0 + L1/L2/L3/L4
```

Q1/Q2 只通过既有 fresh 结果作为对照纳入，没有形成完整 rolling OOS qlib score -> LTR stacking 窗口矩阵。报告已说明未追加窗口，因此不构成事后调参问题，但也不能声称已完成完整 qlib 窗口敏感性验证。

## 4. 后续 T2R 工作

若用户决定继续研究，而不是停止该默认候选推进，建议新增 T2R，不进入 T3。

T2R 目标：

```text
补齐 old/frozen final test full dynamic universe feature；
补真实 PnL contribution；
解释 validation 全负与 final 大正的 regime 反转；
复核 simple 高收益是否由覆盖、单票、单日或异常价格主导；
明确是否仍值得进入下一轮研究，而不是默认候选。
```

T2R 不得：

- 改前端/API；
- 切换默认策略；
- provider refresh / publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / orders / quick-trade；
- 输出真实买卖、持有、仓位、target position、target weight、收益承诺、胜率或上涨概率语义。

## 5. T2R 必做项

### 5.1 Full dynamic universe feature 补齐

必须明确 old/frozen final test 是否能补齐：

```text
2025-07-01..2026-05-07
34 input features
dynamic universe selected_count >= 145
```

若不能补齐，必须将结论限定为：

```text
old/frozen overlap-feature universe research result
```

不得用于默认候选。

### 5.2 真实 PnL contribution

必须输出逐票真实 PnL contribution，而不是 sell-notional proxy：

```text
realized_pnl
unrealized_pnl
fee_tax_allocated
net_pnl
share_of_total_net_pnl
top contribution symbols
worst contribution symbols
single_day contribution
```

### 5.3 Regime 反转解释

必须解释：

```text
validation return = -0.130647
final return = 1.221918
gap = 1.352565
```

至少检查：

- validation / final 的市场状态分布；
- factor exposure 是否改变；
- qlib score/rank 的相关性是否改变；
- LTR 特征重要性是否在 final test 异常偏向某些技术/流动性特征；
- high-return 日期是否集中。

### 5.4 风险接受性

必须单独回答：

```text
收益提升是否足以补偿 max_drawdown 从 -0.088516 恶化到 -0.148581？
若不能，则不得推荐为默认候选。
```

### 5.5 低换手候选

若用户目标偏向实用默认候选，必须重点看低换手结果：

```text
old_frozen_t2_ltr_turnover_controlled: 0.579378
fresh_qlib_top50_adaptive:             0.663150
```

当前低换手 old/frozen LTR 没有超过 fresh baseline，因此不能作为低动作默认候选。

## 6. 给执行者的一句话

T2 报告作为负向研究结论可接受，但不得进入 T3 默认候选；如继续推进，请执行 T2R：补齐 old/frozen final test full dynamic universe feature、逐票真实 PnL contribution、regime 反转解释和回撤接受性审计，全程保持只读，不得触发 provider/accepted latest/monitor/交易链路，也不得输出任何真实交易建议。
