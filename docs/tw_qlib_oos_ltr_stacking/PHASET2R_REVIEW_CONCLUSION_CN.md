# Phase T2R 审查结论

生成日期：2026-06-15

审查对象：

```text
docs/tw_qlib_oos_ltr_stacking/PHASET2R_FOLLOWUP_AUDIT_EXECUTION_REPORT_CN.md
data_tw/experiments/tw_qlib_oos_ltr_stacking/phase_t2r/
```

## 1. 审查结论

结论：

```text
T2R 补充审计通过；
T2R 没有推翻 T2 的负向结论；
不得进入 T3 默认候选；
不得切换默认策略；
建议停止本条作为默认候选推进，仅保留为研究支线。
```

推荐 gate：

```text
phase_t2r_review_passed_confirm_do_not_promote_default
```

## 2. 通过项

### 2.1 Full dynamic universe feature 已补齐

T2 的 overlap-feature universe 限制已被 T2R 修复：

```text
old_score_rows: 30475
full_feature_rows_before_fill: 30475
old_score_dates: 205
feature_dates: 205
missing_by_feature: {}
```

这说明 T2R 已补齐 `2025-07-01..2026-05-07` old/frozen final test 的 34-feature full old score coverage。

### 2.2 真实 PnL contribution 已补

T2R 已从 sell-notional proxy 升级为：

```text
realized_pnl
unrealized_pnl
fee_tax_allocated
net_pnl
share_of_total_net_pnl
```

第一贡献股票：

```text
TW2408 net_pnl: 185366.05
share_of_total_net_pnl: 0.167553
```

贡献归因质量满足 T2R 补充审计要求，同时也确认存在贡献集中风险。

### 2.3 Regime 反转解释已补

T2R 给出了 validation 与 final 的 regime 差异：

```text
validation risk_off share: 0.486858
validation normal share:   0.222118
final normal share:        0.754323
final risk_off share:      0.034290
```

这能解释 validation 全负、final 大正的一部分，但不能证明模型稳定泛化。

### 2.4 风险接受性审计明确

T2R 风险接受性结论为：

```text
old_frozen_t2r_ltr_simple:              reject_default
old_frozen_t2r_ltr_turnover_controlled: reject_default
```

关键对照：

```text
fresh_qlib_top50_adaptive common return:       0.663150
fresh_qlib_top50_adaptive common max_drawdown: -0.088516

old_frozen_t2r_ltr_simple return:              1.106315
old_frozen_t2r_ltr_simple max_drawdown:        -0.140099

old_frozen_t2r_ltr_turnover_controlled return:       0.633462
old_frozen_t2r_ltr_turnover_controlled max_drawdown: -0.147156
```

simple 版本收益更高但回撤显著更差；低换手版本收益更低且回撤更差。

## 3. 只读安全边界

未发现越界：

```text
provider_refresh_publish=false
accepted_latest_switching=false
monitor_or_trading_chain=false
frontend_api=false
broker_orders_quick_trade=false
```

安全关键词检索只命中否定性声明。动作产物中的：

```text
historical_add
historical_risk_reduce
```

属于历史回放 action 记录，不是实际交易、下单或仓位建议。

## 4. 仍阻止默认化的问题

### 4.1 回撤不可接受

old/frozen simple 的收益高，但最大回撤从 fresh baseline 的 `-0.088516` 恶化到 `-0.140099`。

这不满足主线“不能只看收益率”的要求。

### 4.2 低换手候选失败

old/frozen turnover-controlled：

```text
return:       0.633462 < 0.663150
max_drawdown: -0.147156 < -0.088516
```

低换手版本既没赢收益，也没赢回撤，不能作为实用默认候选。

### 4.3 Regime 依赖仍强

T2R 解释了 regime 反转，但解释不等于稳健。validation 中 risk_off 占比接近一半，而 final 中 normal 占比超过四分之三，说明收益很可能依赖 final test 的市场状态。

### 4.4 贡献集中风险仍在

第一贡献股票占总 net PnL 约 `16.8%`，top positive 日期也有阶段集中。该结果不适合包装成普通用户默认策略。

## 5. 最终建议

本支线应以如下结论收束：

```text
old/frozen qlib OOS score -> LTR stacking 在特定 final test normal regime 中有高收益信号；
但 validation 稳健性不足、回撤恶化、低换手候选失败、贡献集中风险仍在；
不应进入 T3 默认候选；
fresh qlib/top50 adaptive 继续保留为默认研究候选。
```

如后续继续研究，应作为新研究支线，目标应转向：

- 回撤约束；
- regime-aware gating；
- 低换手下的真实增益；
- 多个 OOS final window 验证；
- Q1/Q2 rolling qlib 窗口的完整 stacking 矩阵。

不得在当前证据下推进产品默认化。
