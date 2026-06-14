# Phase B2 审查意见与基线保守调优主线收口文档

生成时间：2026-06-14

主线依据：`docs/TW_STOCK_LTR_BASELINE_AND_CONSERVATIVE_TUNING_MAINLINE_CN.md`

审查入口：`docs/tw_ltr_baseline_conservative_tuning/PHASEB2_USER_FIRST_PRODUCT_CLOSURE_EXECUTION_REPORT_CN.md`

---

## 1. 审查结论

Phase B2 **通过**。

本主线可以收口。

最终 gate：

```text
phaseb2_ltr_simple_default_readonly_product_closure_accepted
```

---

## 2. 是否符合用户第一性原则

符合。

B2 已按 B1B 修复后的结论，把 `phase1c_ltr_simple_daily` 作为默认展示策略；`rank_rotate_top50_adaptive_score` 与两个保守候选作为下拉参考策略。

实现方式满足：

- 简单：默认只突出一个主策略，不再平铺多张策略卡片；
- 准确：使用 B1 既有同口径 artifact，不跑新回放、不调参；
- 清晰：策略标签区分默认、规则型参考、保守低频参考；
- 实用：用户能直接看到默认主策略，也能切换低动作/规则型参考。

---

## 3. 产品合同核对

B2 接受的策略展示合同为：

| strategy_key | 产品定位 | 审查结论 |
| --- | --- | --- |
| `phase1c_ltr_simple_daily` | 默认主策略 | 通过 |
| `rank_rotate_top50_adaptive_score` | 规则型参考 | 通过 |
| `phase1c_ltr_conservative_top30_2day_confirm_daily` | 保守参考 | 通过 |
| `phase1c_ltr_conservative_top20_entry_2day_exit_daily` | 保守参考 | 通过 |

默认 key 已确认：

```text
phase1c_ltr_simple_daily
```

接口 schema 已确认：

```text
phaseb2_ltr_simple_default_readonly_product_view_v1
```

固定边界文案已保留：

```text
仅供只读历史模拟和研究复盘，不构成投资建议，不产生真实交易、委托或仓位。
```

---

## 4. 是否偏离主线

未发现偏离主线。

未发现：

- 新回放；
- 新调参；
- 新候选；
- 重训 LTR；
- 改 Phase1C score；
- 改 replay 口径；
- 新数据源；
- 联网；
- provider refresh / publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 真实买卖、持有、仓位建议；
- 收益承诺、胜率或上涨概率语义。

---

## 5. 安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：无实质问题。

### Static Safety Scan

产物：

```text
data_tw/experiments/ltr_baseline_conservative_tuning/phaseb2_product_closure/phaseb2_static_safety_scan.json
```

结果：

```text
ok = true
forbidden_request_count = 0
monitor_config_write_count = 0
monitor_scan_post_count = 0
monitor_alerts_write_count = 0
ops_dry_run_post_count = 0
broker_quick_trade_orders_count = 0
target_position_weight_count = 0
provider_refresh_publish_count = 0
accepted_latest_switch_count = 0
unsafe_buy_sell_hold_semantics_count = 0
endpoint_get_only = true
route_get_only = true
```

### E2E / Network Audit

产物：

```text
data_tw/experiments/ltr_baseline_conservative_tuning/phaseb2_product_closure/phaseb2_readonly_e2e_network_audit.json
```

结果：

```text
ok = true
forbidden_request_count = 0
sim_write_request_count = 0
quick_trade_request_count = 0
broker_request_count = 0
real_order_request_count = 0
monitor_config_write_count = 0
monitor_scan_post_count = 0
monitor_alerts_write_count = 0
qlib_ops_post_count = 0
accepted_latest_switch_count = 0
provider_publish_refresh_count = 0
target_position_request_count = 0
target_weight_request_count = 0
page_error_count = 0
```

### Text / Product Semantics

B2 页面文案使用：

- 独立测试较强；
- 动作较多；
- 换手略高；
- 规则型参考；
- 保守低频参考；
- 只读历史模拟。

这些属于历史模拟和风险标签语境；其中 full range 只作混合历史复盘，不构成真实交易建议、收益承诺或样本外泛化证明。

---


## 5A. B2A Split Purity 补充 caveat

B2A 修复后，本收口结论的解释边界补充如下：

- `phase1c_ltr_simple_daily` 默认只读展示不能解释为 full range 证明未来更好；
- common full range 包含 train / validation / independent_test，只能作为历史复盘明细；
- 默认展示的样本外支持主要来自 `phase1c_independent_test_range = 2025-06-25..2026-05-07`；
- independent_test 已参与产品默认决策，因此不能再作为未触碰的最终检验集或未来保证；
- 产品文案应使用“独立测试较强 / 历史回放表现较强 / 动作较多 / 换手略高”，并保留“历史模拟，不代表未来收益”的边界。

## 6. 最终接受范围

本次最终接受范围仅包括：

```text
LTR simple 默认只读展示 + Top50 adaptive / 两个保守候选下拉参考
```

具体包括：

- `TWLTROptionalSimStrategyService` 读取 B1 artifact 并输出 B2 payload；
- `GET /api/tw-stock/ltr-optional-sim-strategies` GET-only 只读接口；
- 前端 `ltr-optional-sim-strategy-panel` 下拉式只读展示；
- B2 静态安全扫描；
- B2 只读 E2E/network audit；
- 回退路径：可把默认 key 改回 `rank_rotate_top50_adaptive_score`，不影响只读边界。

不接受任何超出本范围的：

- 交易化；
- 自动执行；
- 写入；
- provider / accepted latest 操作；
- monitor 操作；
- 订单或仓位；
- 收益承诺；
- 继续调参。

---

## 7. 主线最终状态

本主线最终状态为：

```text
Baseline and conservative tuning mainline closed.
LTR simple is accepted as the default readonly product display strategy, with independent-test support and full-range results treated only as mixed historical review.
Top50 adaptive remains a rule-based reference.
Two conservative LTR variants remain low-action readonly references.
No trading, no writes, no provider/accepted latest/monitor changes.
```

中文表述：

```text
台股默认基线选择与 LTR 保守版调优主线关闭；
LTR simple 成为默认只读展示策略，样本外支持来自 independent_test，full range 仅作混合历史复盘；
Top50 adaptive 保留为规则型参考；
两个保守 LTR 变体保留为低动作只读参考；
不接交易、不写入、不碰 provider / accepted latest / monitor。
```

---

## 8. 后续限制

收口后不得在本主线继续追加：

- 新策略；
- 新调参；
- 新回放；
- 新数据源；
- 新 provider；
- accepted latest 操作；
- monitor 写入；
- 前端交易化；
- API 写入；
- broker / quick-trade / orders；
- target position / target weight；
- 收益承诺、胜率或上涨概率；
- 默认策略继续来回切换。

如果后续要继续优化 LTR simple 或保守候选，必须开启新主线，重新冻结目标、候选、口径、安全边界和审查 gate。

---

## 9. 给执行者的最终指令

本主线无需继续执行。

请保持当前接受范围，不再新增 Phase B3 或产品扩展；若需要后续优化，等待用户开启新主线。
