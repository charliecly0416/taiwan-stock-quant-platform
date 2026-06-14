# Phase B2A Split Purity 修复执行报告

生成时间：2026-06-14

## 1. 执行范围

本轮只执行 `PHASEB2A_SPLIT_PURITY_REPAIR_WORK_CN.md` 要求的 split purity 修复：

- 修正 B2 默认策略说明中的 train / validation / independent_test 边界；
- 修正 API payload 与前端展示文案，首屏主指标改为独立测试区间；
- 保留 full range 作为历史复盘明细，不作为 OOS 或未来泛化证明；
- 重新执行静态安全扫描与只读 E2E/network audit。

未执行：新回放、调参、重训、新候选、新数据源、联网、provider refresh/publish、accepted latest switching、monitor 写入/扫描、交易链路、前端/API 范围外改造。

## 2. Split 定义

本轮采用审查文档冻结的口径：

| period | split 归属 | 说明 |
| --- | --- | --- |
| `2022` | train | 训练期历史结果，只能用于历史复盘 |
| `2023` | train | 训练期历史结果，只能用于历史复盘 |
| `2024` | train / validation mixed | 混合区间，不是纯 OOS |
| `2025` | validation / independent_test mixed | 混合区间，不是纯 OOS |
| `2026_ytd` | independent_test / out-of-split mixed | 当前产物到 `2026-06-13`，不等同于冻结 independent_test 截止 `2026-05-07` |
| `common_full_range` | train / validation / independent_test mixed | 只能作为完整历史复盘，不作为样本外泛化证据 |
| `phase1c_validation_range` | validation | 可辅助观察候选行为，不作为最终证明 |
| `phase1c_independent_test_range` | independent_test | `2025-06-25..2026-05-07`，作为默认展示的主要样本外支持 |

补充边界：由于本轮把 `phase1c_independent_test_range` 用于产品默认决策，它不再是完全未触碰的最终检验集，只能表述为“已用于产品决策的独立测试结果”，不能表述为未来收益保证。

## 3. Independent Test 单独比较

| 策略 | independent_test return | max_drawdown | action_count |
| --- | ---: | ---: | ---: |
| `phase1c_ltr_simple_daily` | `3.550601` | `-0.160298` | `384` |
| `rank_rotate_top50_adaptive_score` | `2.450848` | `-0.167457` | `386` |
| `phase1c_ltr_conservative_top30_2day_confirm_daily` | `1.257516` | `-0.098271` | `63` |
| `phase1c_ltr_conservative_top20_entry_2day_exit_daily` | `0.650070` | `-0.143129` | `63` |

结论边界：`phase1c_ltr_simple_daily` 在该独立测试区间相对 Top50 adaptive 更强，同时动作较多；这只能支持当前固定候选下的产品默认展示选择，不能扩展为未来表现承诺。

## 4. Common Full Range 降权说明

`common_full_range` 包含 train、validation、independent_test，已降权为“历史回放复盘 / 混合区间明细”。它仍可在详情中展示，用于帮助用户理解完整历史表现和波动，但不得作为默认策略优于其他策略的唯一理由，也不得写成 OOS、泛化证明或未来收益证明。

## 5. 修正后的默认展示理由

默认展示 `phase1c_ltr_simple_daily` 的理由已拆成两层：

1. 样本外支持：在 `phase1c_independent_test_range` 中，LTR simple 的 return 高于 Top50 adaptive；
2. 产品决策：用户明确偏好收益优先，因此默认展示 LTR simple，同时标注“动作较多”，并保留 Top50 adaptive 作为规则型参考。

边界文案已补充：历史模拟不代表未来收益；首屏主指标使用独立测试区间，明细包含样本内/验证/样本外混合结果。

## 6. 修改文件

代码与测试：

- `backend/app/services/tw_ltr_optional_sim_strategy.py`
  - 默认策略状态改为“默认 / 独立测试较强 / 动作较多”；
  - 首屏 `metrics` 改为 `phase1c_independent_test_range`；
  - 新增 `primary_evidence_period`、`full_range_metrics`、`split_purity_note`；
  - caveat 明确 full range 是混合历史复盘，不是 OOS。
- `frontend/src/views/tw-stock-monitor/index.vue`
  - 只读模拟面板增加 split purity 提示。
- `backend/tests/test_tw_ltr_readonly_explanation_api.py`
  - 更新 API payload 断言，覆盖 independent_test 主指标与 full range 明细。
- `frontend/tests/unit/tw-stock-monitor-static-check.mjs`
  - 增加 split purity 文案静态断言。
- `frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs`
  - 更新只读 E2E mock payload 与 caveat 断言。

文档：

- `docs/tw_ltr_baseline_conservative_tuning/PHASEB2_USER_FIRST_PRODUCT_CLOSURE_EXECUTION_REPORT_CN.md`
- `docs/tw_ltr_baseline_conservative_tuning/PHASEB2_REVIEW_AND_CLOSURE_CN.md`
- `docs/tw_ltr_baseline_conservative_tuning/PHASEB2_RETURN_AND_SPLIT_AUDIT_CN.md`
- `docs/tw_ltr_baseline_conservative_tuning/PHASEB2A_SPLIT_PURITY_REPAIR_EXECUTION_REPORT_CN.md`

## 7. 验证结果

已执行并通过：

```text
python -m py_compile backend/app/services/tw_ltr_optional_sim_strategy.py
python -m pytest backend/tests/test_tw_ltr_readonly_explanation_api.py
node frontend/tests/unit/tw-stock-monitor-static-check.mjs
python scripts/scan_tw_ltr_phasev4_optional_sim_static_safety.py
corepack pnpm build
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8011 node frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs
```

只读 E2E/network audit 关键结果：

| 项目 | 结果 |
| --- | ---: |
| `ltr_optional_sim_strategies_request_count` | `2` |
| `portfolio_persist_false_count` | `5` |
| `sim_write_request_count` | `0` |
| `quick_trade_request_count` | `0` |
| `broker_request_count` | `0` |
| `real_order_request_count` | `0` |
| `monitor_config_write_count` | `0` |
| `monitor_scan_post_count` | `0` |
| `monitor_alerts_write_count` | `0` |
| `accepted_latest_switch_count` | `0` |
| `provider_publish_refresh_count` | `0` |
| `target_position_request_count` | `0` |
| `target_weight_request_count` | `0` |
| `forbidden_request_count` | `0` |
| `page_error_count` | `0` |

产物：

- `data_tw/experiments/ltr_baseline_conservative_tuning/phaseb2_product_closure/phaseb2a_static_safety_scan.json`
- `data_tw/experiments/ltr_baseline_conservative_tuning/phaseb2_product_closure/phaseb2a_readonly_e2e_network_audit.json`

备注：本环境中部分命令在默认沙箱下出现 `bwrap: loopback: Failed RTM_NEWADDR` 或 Vite watcher `ENOSPC`，已按权限规则使用提升权限重跑必要只读检查，并使用 `frontend/dist` 静态代理完成 E2E；未改变验证范围。

## 8. Gate 建议

建议进入：

```text
phaseb2a_split_purity_repaired_return_to_closure
```

理由：本轮已清楚区分 train / validation / independent_test / mixed，默认展示主证据改为 independent_test，full range 已降权为混合历史复盘，未把 train / validation / full range 包装成 OOS 或未来泛化证据。
