# Phase O6 执行报告：Orthogonal LTR Decision

生成时间：2026-06-15T12:18:00+00:00

## 1. Final Decision

Decision：

```text
通过：允许进入只读产品化设计主线
```

Decision gate：

```text
phase_o6_orthogonal_ltr_decision_recorded
```

本结论只允许进入“只读产品化设计”阶段，用于设计后续只读展示、对照说明、审计卡片和研究解释。不得在 O6 直接改前端默认策略、切换 provider/accepted latest、触发 monitor、交易链路或任何 broker/orders/quick-trade/target position/target weight。

## 2. 决策依据摘要

O6 只使用 O0-O5R 冻结产物，没有重新训练、没有重新回放新规则、没有修改 Phase1C anchor 或 O4 treatment score。

主窗口固定为：

```text
2025-07-01..2026-05-07
```

回放口径固定为：

```text
next-day execution
fee_rate = 0.001425
tax_rate = 0.003
target_position_count = 10
preserve_scope = top50_only
```

Full universe：

| method | return | max_drawdown | action_count | turnover_proxy |
| --- | ---: | ---: | ---: | ---: |
| Phase1C control | 0.721631 | -0.050830 | 405 | 40.328422 |
| O4 orthogonal treatment | 0.800329 | -0.074962 | 403 | 39.761877 |

O4 treatment 相对 Phase1C：

```text
return +0.078698
max_drawdown -0.024132
action_count -2
turnover_proxy -0.566545
```

## 3. 必答问题

### 3.1 O4 treatment 是否在 full universe 收益不低于 Phase1C control？

是。

O4 treatment full universe `fee_tax_adjusted_net_return = 0.800329`，高于 Phase1C control 的 `0.721631`，差值 `+0.078698`。

### 3.2 Pairwise common universe 是否已审计闭环？

是。

O5R 已补齐 full/common action 与 NAV 独立产物，并确认：

```text
full_key_count = 30475
common_key_count = 10110
excluded_key_count = 20365
excluded_treatment_top50_preserve_masked = 20365
price/replay unavailable = 0
```

O5R action / NAV diff：

```text
action diff total = 0
historical_add diff = 0
historical_risk_reduce diff = 0
historical_skip diff = 0
daily_equity_max_abs_diff = 0
daily_cash_max_abs_diff = 0
daily_holding_count_max_abs_diff = 0
```

Phase1C 有 `84` 条 risk_reduce signal key 不在 common key 中，但 full/common actual action diff 为 `0`，NAV/cash/holding_count 也完全一致。因此 common 指标相同是可复现结果，不是审计遗漏。

### 3.3 O4 treatment 的 max drawdown 是否明显恶化？

有恶化，但不作为 O6 阻断项。

O4 treatment max drawdown 为 `-0.074962`，Phase1C 为 `-0.050830`，恶化 `-0.024132`。该风险必须在只读产品化设计中显式呈现，不能只展示收益提升。

判断：回撤恶化可接受但需风险标注；不允许据此直接产品化或默认替换。

### 3.4 Action count / turnover 是否明显恶化？

否。

O4 treatment action_count 为 `403`，Phase1C 为 `405`；O4 turnover proxy 为 `39.761877`，Phase1C 为 `40.328422`。动作数和 turnover proxy 均未恶化。

### 3.5 收益是否集中于单一月份、单一日期或单一股票？

未发现不可接受集中。

PnL concentration：

```text
O4 top_symbol_abs_share_of_total_net_pnl = 0.102661
O4 top_day_abs_share_of_total_net_pnl = 0.069842
O4 max_abs_daily_nav_return = 0.038982
```

月度表现并非单月贡献全部收益。O4 treatment 在 `2025-07`、`2025-08`、`2025-10`、`2025-12`、`2026-01`、`2026-02`、`2026-04` 均为正；`2026-03` 为负。

### 3.6 低覆盖股票是否贡献了不可接受的收益集中或风险？

否。

低覆盖股票中较大正贡献为：

```text
TW6683 share_of_total_net_pnl = 0.044069
TW6770 share_of_total_net_pnl = 0.028640
TW6919 share_of_total_net_pnl = 0.003025
```

较大负贡献为：

```text
TW6789 share_of_total_net_pnl = -0.009948
TW6446 share_of_total_net_pnl = -0.004001
```

低覆盖股票不是主要收益来源，也没有形成单一低覆盖股票主导的结果。

### 3.7 Rank/NDCG 改善是否与 replay PnL 方向一致？

基本一致。

Full universe ranking：

| metric | Phase1C | O4 treatment |
| --- | ---: | ---: |
| rank_ic_10d | 0.025736746681 | 0.068649444085 |
| ndcg_at_10 | 0.441931104468 | 0.450302908476 |
| ndcg_at_30 | 0.418683343053 | 0.590148409191 |
| ndcg_at_50 | 0.465765871838 | 0.760603038855 |

Ranking metric 只能作为辅助证据；O6 主证据仍是同窗口 replay、accounting、PnL concentration 与 common audit。

### 3.8 O4 feature importance 是否显示正交特征确实被模型使用？

是。

O4 feature importance top30 中包含多个正交特征：

```text
margin_balance
short_balance
margin_balance_change_roll10
dealer_net_buy_roll10
short_balance_change_roll10
institutional_total_net_buy_roll10
investment_trust_net_buy_roll10
```

同时，最高重要性仍来自原始 control feature `volatility20`，说明 treatment 不是完全由正交特征单独驱动，而是在原 Phase1C simple LTR 基础上吸收了 margin_short / institutional_flow 信息。

### 3.9 是否存在 PIT / sample alignment / universe / next-day accounting 合同问题？

未发现阻断问题。

既有 gate：

```text
O2: phase_o2_pit_safe_feature_builder_passed
O3: row-aligned treatment sample completed
O4: phase_o4_controlled_treatment_ltr_trained
O5R: phase_o5r_common_universe_audit_repaired
```

O5R next-day accounting full/common 全部通过：

```text
execution_date_not_after_signal_violations = 0
missing_price_days = 0
skipped_trade_count = 0
last_day_new_trade_without_next_price_count = 0
```

### 3.10 是否足以进入只读产品化设计主线？

是，但仅限只读产品化设计。

允许进入的范围：

```text
只读展示设计
只读审计卡片
研究解释文案
O4 treatment vs Phase1C control 的 frozen evidence summary
风险提示与不可默认化边界设计
```

禁止：

```text
直接替换默认策略
改前端默认信号来源
改 API/provider/accepted latest/monitor
触发交易链路
触发 broker/orders/quick-trade/target position/target weight
```

## 4. 支持证据

支持进入只读产品化设计的证据：

- Full universe return 明确高于 Phase1C：`+0.078698`。
- Pairwise common universe 已由 O5R 补齐 action/nav diff，审计闭环。
- Action count 与 turnover proxy 未恶化。
- PnL 未集中于单一股票或单一日期。
- 低覆盖股票不是主要收益来源。
- Rank IC 与 NDCG 改善方向与 replay PnL 方向一致。
- O4 feature importance 显示正交特征被实际使用。
- PIT / sample alignment / universe / next-day accounting 未发现阻断问题。

## 5. 反证与风险

必须保留的风险：

- O4 treatment max drawdown 更深：`-0.074962` vs Phase1C `-0.050830`。
- O5/O5R 的 pairwise common universe 对 O4 treatment 天然非约束，因为 common 定义直接使用 treatment top50-preserve score 非空。
- Common universe 不能作为独立稳健胜出证据，只能说明 common 收缩没有改变本轮实际 replay 路径。
- 当前证据仍是离线历史回放与只读审计，不是产品默认策略授权。
- O6 没有证明未来收益、胜率或任何实时交易优势。

## 6. Decision

综合判断：

```text
O4 orthogonal treatment 给 Phase1C simple LTR 带来了可用增益。
```

但该增益伴随更深回撤，且 common universe 主要是审计闭环而非独立稳健性证明。因此 O6 决策为：

```text
通过进入只读产品化设计主线；
不得直接产品化；
不得改默认；
不得触发任何真实交易或 monitor/provider/accepted latest 链路。
```

## 7. 下一步建议

下一步仅建议启动只读产品化设计工作文档，内容应包括：

- 冻结 evidence card：Phase1C vs O4 treatment。
- 明确展示 return、max drawdown、action_count、turnover proxy、PnL concentration。
- 明确展示 O5R common universe 审计解释。
- 前端/API 只读设计必须默认关闭，不接 provider refresh / accepted latest / monitor / trading。
- 所有文案使用“研究/回放/只读审计”语义，不使用买卖建议、目标仓位、收益承诺或默认替换措辞。

## 8. 输出与边界

本轮只写入：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEO6_ORTHOGONAL_LTR_DECISION_EXECUTION_REPORT_CN.md
```

未执行：

```text
qlib/LTR training
score regeneration
replay rule change
feature/window/label/hyperparameter change
frontend/API/provider/accepted latest/monitor change
broker/orders/quick-trade/target position/target weight
```
