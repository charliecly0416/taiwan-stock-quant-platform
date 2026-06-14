# Phase B2A 审查意见与最终收口文档

生成时间：2026-06-14

主线依据：`docs/TW_STOCK_LTR_BASELINE_AND_CONSERVATIVE_TUNING_MAINLINE_CN.md`

审查入口：`docs/tw_ltr_baseline_conservative_tuning/PHASEB2A_SPLIT_PURITY_REPAIR_EXECUTION_REPORT_CN.md`

---

## 1. 审查结论

Phase B2A **通过**。

本主线可以收尾。

最终 gate：

```text
phaseb2a_split_purity_repaired_return_to_closure
```

---

## 2. Split Purity 是否修复

已修复。

执行者已经明确区分：

| period | split 归属 | 审查判断 |
| --- | --- | --- |
| `2022` | train | 只能历史复盘 |
| `2023` | train | 只能历史复盘 |
| `2024` | train / validation mixed | 不是纯 OOS |
| `2025` | validation / independent_test mixed | 不是纯 OOS |
| `2026_ytd` | independent_test / out-of-split mixed | 不等同冻结 independent_test |
| `common_full_range` | train / validation / independent_test mixed | 已降权为历史复盘 |
| `phase1c_validation_range` | validation | 只作辅助观察 |
| `phase1c_independent_test_range` | independent_test | 作为默认展示主要样本外支持 |

关键修复点：

- 首屏主指标已改为 `phase1c_independent_test_range`；
- `common full range` 已明确降权为混合历史复盘；
- API payload 增加 `primary_evidence_period`、`full_range_metrics`、`split_purity_note`；
- 前端增加“历史模拟，不代表未来收益；首屏主指标使用独立测试区间，明细包含样本内/验证/样本外混合结果。”提示；
- 文档明确 independent_test 已用于产品决策，不能再说成未触碰最终检验集或未来保证。

---

## 3. 默认展示结论是否仍成立

可以成立，但边界必须保持为：

```text
LTR simple 在固定候选的 independent_test 区间表现较强，
因此作为默认只读展示策略；
full range 只作为历史复盘明细，不作为样本外泛化证明。
```

不得表述为：

```text
LTR simple 未来收益最高
LTR simple 纯样本外保证更好
LTR simple 胜率更高
```

---

## 4. 安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：无实质问题。

### Static Safety Scan

产物：

```text
data_tw/experiments/ltr_baseline_conservative_tuning/phaseb2_product_closure/phaseb2a_static_safety_scan.json
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
data_tw/experiments/ltr_baseline_conservative_tuning/phaseb2_product_closure/phaseb2a_readonly_e2e_network_audit.json
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

---

## 5. 是否偏离主线

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
- 买卖、持有、仓位建议；
- 收益承诺、胜率或上涨概率；
- 把 train / validation / full range 包装成 OOS。

---

## 6. 最终接受范围

本次最终接受范围仅包括：

```text
LTR simple 默认只读展示，首屏主指标使用 independent_test；
Top50 adaptive 与两个保守 LTR 候选作为下拉参考；
full range 仅作为混合历史复盘明细。
```

具体包括：

- `GET /api/tw-stock/ltr-optional-sim-strategies` GET-only；
- `TWLTROptionalSimStrategyService` 只读读取 B1 artifact；
- 前端 `ltr-optional-sim-strategy-panel` 下拉式只读展示；
- split purity 提示；
- B2A 静态安全扫描；
- B2A 只读 E2E/network audit。

---

## 7. 主线最终状态

```text
Baseline and conservative tuning mainline closed after split-purity repair.
LTR simple is accepted as the default readonly display strategy only under split-aware wording.
Primary evidence shown on first screen is phase1c_independent_test_range.
Common full range is retained only as mixed historical replay detail.
No trading, no writes, no provider/accepted latest/monitor changes.
```

中文表述：

```text
台股默认基线选择与 LTR 保守版调优主线在 split purity 修复后关闭；
LTR simple 可作为默认只读展示策略，但必须使用 split-aware 文案；
首屏主证据使用 independent_test；
common full range 只保留为混合历史复盘明细；
不接交易、不写入、不碰 provider / accepted latest / monitor。
```

---

## 8. 后续限制

后续不得在本主线继续追加：

- 新策略；
- 新调参；
- 新回放；
- 新数据源；
- 默认策略再次切换；
- 前端交易化；
- API 写入；
- provider / accepted latest / monitor 操作；
- broker / quick-trade / orders；
- target position / target weight；
- 收益承诺、胜率或上涨概率。

如果后续要继续检验 LTR 是否稳健，必须开启新的严格 out-of-sample / walk-forward 验证主线，并预先冻结未来 holdout 区间和验收标准。

---

## 9. 给执行者的最终指令

本主线无需继续执行。

保持当前 split-aware、只读、非交易接受范围；不要再新增 Phase B3 或产品扩展。
