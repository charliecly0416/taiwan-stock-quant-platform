# Phase P0 执行报告：Orthogonal LTR Readonly Productization Design

生成时间：2026-06-15T12:24:00+00:00

## 1. Gate

P0 已完成只读产品化设计记录。

推荐 gate：

```text
phase_p0_readonly_productization_design_completed
```

本阶段只写设计文档，不修改前端代码、不修改 API、不修改 provider、不切换 accepted latest、不触发 monitor、不触发交易链路。

## 2. 产品路线冻结

产品路线固定为：

```text
default_strategy = fresh qlib / rank_rotate_top50_adaptive_score
ltr_research_candidate = O4 orthogonal LTR
legacy_simple_ltr = audit baseline
```

含义：

- 默认策略仍为 fresh qlib，不变。
- O4 orthogonal LTR 替代原 simple LTR 的“LTR 研究候选”展示位置。
- Phase1C simple LTR 不再作为优先研究候选，但必须保留为 audit baseline，用于解释 O4 treatment 的相对增益与风险。

禁止表达：

```text
orthogonal LTR 是默认策略；
orthogonal LTR 已可替代 fresh qlib；
orthogonal LTR 给出买入/卖出建议；
orthogonal LTR 保证未来收益、胜率或上涨概率。
```

## 3. 页面 / 模块入口建议

建议入口：

```text
TW Stock Monitor / Research / LTR Evidence
```

模块层级建议：

1. 默认策略状态条：显示当前默认仍为 fresh qlib。
2. LTR 研究候选卡：展示 O4 orthogonal LTR。
3. Audit baseline 卡：展示 Phase1C simple LTR。
4. 风险与限制卡：突出回撤更深、历史回放、非交易建议。
5. Common universe 审计卡：解释 O5R 闭环。
6. PIT / accounting 审计卡：解释数据可得性、样本对齐、next-day accounting。

入口必须使用只读语义，例如：

```text
Research evidence
Readonly replay audit
LTR candidate comparison
```

不得使用：

```text
Buy list
Trade signal
Recommended positions
Target weights
Auto strategy switch
```

## 4. 默认策略说明卡

卡片标题建议：

```text
Default Strategy Remains Fresh Qlib
```

必须展示：

```text
当前默认策略：fresh qlib / rank_rotate_top50_adaptive_score
O4 orthogonal LTR：仅作为 LTR 研究候选
Phase1C simple LTR：仅作为 audit baseline
```

说明文案建议：

```text
O4 orthogonal LTR 仅进入只读研究展示。当前默认策略仍保持 fresh qlib；本页面不触发 provider refresh、accepted latest 切换、monitor scan、交易或下单。
```

## 5. O4 Orthogonal LTR Evidence Card

卡片角色：

```text
LTR 研究候选
```

固定展示数值：

| item | value |
| --- | ---: |
| window | 2025-07-01..2026-05-07 |
| execution | next-day execution |
| fee_rate | 0.001425 |
| tax_rate | 0.003 |
| target_position_count | 10 |
| return | 0.800329 |
| max_drawdown | -0.074962 |
| action_count | 403 |
| turnover_proxy | 39.761877 |
| absolute improvement vs Phase1C | +0.078698 |
| top_symbol_abs_share_of_total_net_pnl | 0.102661 |
| top_day_abs_share_of_total_net_pnl | 0.069842 |
| max_abs_daily_nav_return | 0.038982 |
| rank_ic_10d | 0.068649444085 |
| ndcg_at_10 | 0.450302908476 |
| ndcg_at_30 | 0.590148409191 |
| ndcg_at_50 | 0.760603038855 |

Feature importance 摘要必须说明：

```text
O4 top30 feature importance 包含 margin_short 与 institutional_flow 正交特征：
margin_balance、short_balance、margin_balance_change_roll10、dealer_net_buy_roll10、
short_balance_change_roll10、institutional_total_net_buy_roll10、investment_trust_net_buy_roll10。
最高重要性仍来自 control_original 的 volatility20。
```

解释边界：

```text
这些数值来自冻结同窗口历史回放与只读审计，不代表未来收益、胜率、上涨概率或交易建议。
```

## 6. Phase1C Simple LTR Audit Baseline Card

卡片角色：

```text
Legacy simple LTR audit baseline
```

固定展示数值：

| item | value |
| --- | ---: |
| window | 2025-07-01..2026-05-07 |
| return | 0.721631 |
| max_drawdown | -0.050830 |
| action_count | 405 |
| turnover_proxy | 40.328422 |
| rank_ic_10d | 0.025736746681 |
| ndcg_at_10 | 0.441931104468 |
| ndcg_at_30 | 0.418683343053 |
| ndcg_at_50 | 0.465765871838 |

说明文案建议：

```text
Phase1C simple LTR 保留为 frozen audit baseline，用于解释 O4 orthogonal LTR 的增益、回撤变化和模型特征变化；不作为优先 LTR 研究候选。
```

## 7. 风险卡片

风险卡必须醒目展示：

```text
O4 orthogonal LTR 的 max_drawdown 更深：
O4 = -0.074962
Phase1C = -0.050830
drawdown change = -0.024132
```

必须展示的风险说明：

- O4 orthogonal LTR 回撤更深，不能只展示收益提升。
- Common universe 是审计闭环，不是独立稳健性证明。
- 所有结果是历史只读回放，不是交易建议。
- 默认策略保持 fresh qlib。
- 本页面不输出买入、卖出、目标仓位、目标权重、收益承诺、胜率承诺或上涨概率。

## 8. O5R Common Universe 解释卡

卡片标题建议：

```text
Pairwise Common Universe Audit
```

必须展示：

```text
full_key_count = 30475
common_key_count = 10110
excluded_key_count = 20365
excluded_treatment_top50_preserve_masked = 20365
price/replay unavailable = 0
```

必须展示 O5R 结论：

```text
full/common action diff = 0
full/common NAV diff = 0
next-day accounting pass = yes
```

解释文案建议：

```text
Pairwise common universe 的收缩没有改变本轮实际买入、卖出、持仓路径或 NAV，因此 full/common 指标相同可复现。但 common universe 主要用于审计闭环，不应写成独立证明 O4 orthogonal LTR 稳健胜出。
```

## 9. PIT / Sample / Accounting 审计卡

必须展示：

```text
O2 gate: phase_o2_pit_safe_feature_builder_passed
O3: row-aligned treatment sample completed
O4 gate: phase_o4_controlled_treatment_ltr_trained
O5R gate: phase_o5r_common_universe_audit_repaired
```

Next-day accounting：

```text
execution_date_not_after_signal_violations = 0
missing_price_days = 0
skipped_trade_count = 0
last_day_new_trade_without_next_price_count = 0
```

说明文案建议：

```text
O4 orthogonal LTR 使用 PIT-safe delayed availability 特征、row-aligned treatment sample 与冻结同窗口 replay accounting。当前证据仅用于只读研究展示。
```

## 10. 低覆盖影响卡

必须展示低覆盖股票未形成主要收益来源：

```text
TW6683 share_of_total_net_pnl = 0.044069
TW6770 share_of_total_net_pnl = 0.028640
TW6919 share_of_total_net_pnl = 0.003025
TW6789 share_of_total_net_pnl = -0.009948
TW6446 share_of_total_net_pnl = -0.004001
```

说明文案建议：

```text
低覆盖股票有少量交易与 PnL 贡献，但不是 O4 orthogonal LTR 的主要收益来源。低覆盖与 delay/missing flags 仍需作为只读审计字段保留。
```

## 11. 禁止接入链路清单

P0 设计明确禁止接入：

```text
frontend default strategy switch
API write endpoint
provider refresh / publish
accepted latest switching
monitor scan / config / alerts
broker
orders
quick-trade
target position
target weight
```

P0 也禁止生成：

```text
buy/sell instruction
position recommendation
target weight
return promise
win-rate promise
upside probability claim
```

## 12. 后续 P1 工作文档要求

如需真实前端实现，必须另开 Phase P1 工作文档并等待审查确认。

P1 至少需要定义：

- 只读页面入口和组件树；
- 只读数据来源，只允许读取 frozen O4/O5/O5R evidence artifacts；
- 前端安全文案；
- 禁止 POST/PUT/PATCH/DELETE；
- 禁止 provider refresh / accepted latest / monitor / trading；
- E2E readonly safety audit；
- 不改变默认 fresh qlib 策略。

## 13. 必答问题

### 13.1 默认策略是否仍为 fresh qlib？

是。默认策略固定保持：

```text
fresh qlib / rank_rotate_top50_adaptive_score
```

### 13.2 O4 orthogonal LTR 在产品中扮演什么角色？

O4 orthogonal LTR 扮演：

```text
LTR research candidate
```

它替代原 simple LTR 的 LTR 研究候选位置，但不替代默认 fresh qlib。

### 13.3 原 simple LTR 如何保留为审计 baseline？

Phase1C simple LTR 保留为：

```text
legacy audit baseline
```

用于展示 O4 treatment 相对 simple LTR 的 return、drawdown、action_count、turnover、rank/NDCG 与 feature importance 差异。

### 13.4 哪些数值会展示？

展示：

```text
return
max_drawdown
action_count
turnover_proxy
PnL concentration
low coverage impact
rank_ic / NDCG
feature importance summary
window
fee/tax/execution assumptions
O5R common universe audit
PIT/sample/accounting gates
```

### 13.5 哪些风险必须展示？

必须展示：

```text
O4 回撤更深；
common universe 不是独立稳健性证明；
历史只读回放不是交易建议；
默认策略仍为 fresh qlib；
不承诺未来收益、胜率或上涨概率。
```

### 13.6 是否触碰任何前端/API/provider/monitor/trading 链路？

否。

P0 只写本文档，未修改前端、API、provider、accepted latest、monitor 或交易链路。

## 14. 本轮输出

本轮只写入：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEP0_READONLY_PRODUCTIZATION_DESIGN_EXECUTION_REPORT_CN.md
```

未执行：

```text
frontend code change
API change
provider change
accepted latest switch
monitor trigger
broker/orders/quick-trade
target position / target weight generation
model training
qlib rerun
replay rule change
filter/threshold/market gate change
default strategy change
```
