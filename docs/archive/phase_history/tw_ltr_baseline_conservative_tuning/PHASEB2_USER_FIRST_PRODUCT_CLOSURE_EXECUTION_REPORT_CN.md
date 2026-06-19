# Phase B2 用户第一性产品化收口执行报告

生成时间：2026-06-14

执行依据：`docs/tw_ltr_baseline_conservative_tuning/PHASEB1B_REVIEW_AND_PHASEB2_USER_FIRST_PRODUCT_CLOSURE_WORK_CN.md`

主线依据：`docs/TW_STOCK_LTR_BASELINE_AND_CONSERVATIVE_TUNING_MAINLINE_CN.md`

## 1. 本轮目标

本轮只做用户第一性产品化收口：默认展示 `phase1c_ltr_simple_daily`，`rank_rotate_top50_adaptive_score` 与两个保守候选作为下拉参考策略。

本轮未跑新回放，未重训 LTR，未调参，未新增数据源，未联网，未改 provider / accepted latest，未写 monitor，未触碰 broker / quick-trade / orders / target position / target weight。

## 2. 改动文件清单

| 文件 | 改动说明 |
| --- | --- |
| `backend/app/services/tw_ltr_optional_sim_strategy.py` | 将只读策略展示合同改为 Phase B2：读取 B1 产物，默认 `phase1c_ltr_simple_daily`，返回四策略清单、independent_test 首屏主指标、full range 混合复盘明细和 period 明细。 |
| `frontend/src/views/tw-stock-monitor/index.vue` | 将可选模拟策略面板改为下拉选择 + 单策略展示；默认选中 LTR simple；首屏展示 independent_test 样本范围、费用后历史模拟、最大回撤、动作数、换手 proxy、independent_test 标记；full range 仅在明细中作为混合历史复盘。 |
| `backend/tests/test_tw_ltr_readonly_explanation_api.py` | 更新 GET-only API 合同测试，断言 B2 schema、LTR simple 默认和四策略顺序。 |
| `frontend/tests/unit/tw-stock-monitor-static-check.mjs` | 更新前端静态检查，断言默认主策略、下拉显示、GET-only API 和只读边界文案。 |
| `frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs` | 更新 E2E mock payload 和 network audit，覆盖 B2 默认策略显示与 forbidden request 计数。 |
| `scripts/scan_tw_ltr_phasev4_optional_sim_static_safety.py` | 将扫描输出目录/schema 调整到 B2 产物；扫描范围仍限 optional sim endpoint/service/API/panel。 |

## 3. 默认策略确认

默认展示策略已改为：

```text
phase1c_ltr_simple_daily
```

修正后的默认展示理由分两层：样本外支持来自 `phase1c_independent_test_range = 2025-06-25..2026-05-07` 中 LTR simple 相对 Top50 adaptive 的同口径结果；产品决策来自用户收益优先偏好。common full range 包含 train / validation / independent_test，只能作为历史复盘明细，不作为样本外泛化证明。

后端 payload：`default_method_key=phase1c_ltr_simple_daily`。

前端初始选择：`ltrOptionalSimSelected: 'phase1c_ltr_simple_daily'`。

## 4. 下拉参考策略清单

B2 产品展示合同包含 4 个策略：

| strategy_key | 定位 |
| --- | --- |
| `phase1c_ltr_simple_daily` | 默认主策略，独立测试区间表现较强，动作较多 |
| `rank_rotate_top50_adaptive_score` | 规则型参考，规则简单，换手略低 |
| `phase1c_ltr_conservative_top30_2day_confirm_daily` | 保守参考，低动作，低换手 |
| `phase1c_ltr_conservative_top20_entry_2day_exit_daily` | 保守参考，更严格入选，低动作 |

前端不再平铺多张策略卡片，而是通过下拉选择当前策略，只展示一个策略详情。

## 5. 只读 / GET-only 状态

`/api/tw-stock/ltr-optional-sim-strategies` 仍为 GET-only。后端服务只读取本地 B1 artifact：

- `phaseb1_period_comparison.csv`
- `phaseb1_method_summary.csv`
- `phaseb1_gate_summary.json`

无 POST / PUT / PATCH / DELETE 写入。

## 6. 禁止链路确认

本轮未触发或新增：

- provider refresh / publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 新数据源；
- 重训 / 调参 / 新回放。

## 7. 文案安全确认

前端固定显示边界文案：

```text
仅供只读历史模拟和研究复盘，不构成投资建议，不产生真实交易、委托或仓位。
```

产品文案使用“独立测试较强、动作较多、换手略高、规则型参考、保守低频参考”等历史模拟标签，并明确 full range 含样本内/验证/样本外混合结果；未输出买卖、持有、仓位、收益承诺、胜率或上涨概率语义。

## 8. E2E / Network Audit Artifact

E2E/network audit artifact：

```text
data_tw/experiments/ltr_baseline_conservative_tuning/phaseb2_product_closure/phaseb2_readonly_e2e_network_audit.json
```

关键结果：

| 指标 | 结果 |
| --- | ---: |
| forbidden_request_count | 0 |
| monitor_config_write_count | 0 |
| monitor_scan_post_count | 0 |
| monitor_alerts_write_count | 0 |
| qlib_ops_post_count | 0 |
| broker / quick-trade / orders | 0 |
| accepted latest switching | 0 |
| provider publish / refresh | 0 |
| target position / target weight | 0 |
| page_error_count | 0 |

说明：Vite dev / preview 因系统 watcher 限制 `ENOSPC` 无法常驻；已改用项目既有无 watcher 静态服务 `scripts/serve_frontend_static_proxy.py` 服务 `frontend/dist` 后执行 Playwright E2E。该服务已在测试后关闭。

## 9. Static Safety Scan Artifact

static safety scan artifact：

```text
data_tw/experiments/ltr_baseline_conservative_tuning/phaseb2_product_closure/phaseb2_static_safety_scan.json
```

结果：

| 检查项 | 结果 |
| --- | ---: |
| forbidden_request_count | 0 |
| monitor_config_write_count | 0 |
| monitor_scan_post_count | 0 |
| monitor_alerts_write_count | 0 |
| ops_dry_run_post_count | 0 |
| broker_quick_trade_orders_count | 0 |
| target_position_weight_count | 0 |
| provider_refresh_publish_count | 0 |
| accepted_latest_switch_count | 0 |
| unsafe_buy_sell_hold_semantics_count | 0 |
| endpoint_get_only | true |
| route_get_only | true |

## 10. 验证命令

已通过：

```text
python -m py_compile backend/app/services/tw_ltr_optional_sim_strategy.py
python -m pytest backend/tests/test_tw_ltr_readonly_explanation_api.py
node frontend/tests/unit/tw-stock-monitor-static-check.mjs
python scripts/scan_tw_ltr_phasev4_optional_sim_static_safety.py
corepack pnpm build
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8011 node frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs
```

其中 `node` 静态检查和安全扫描曾因 sandbox loopback 限制重跑为提升权限；Vite dev / preview 曾因系统 watcher `ENOSPC` 失败，最终使用无 watcher 静态服务完成 E2E。

## 11. 回退路径

如审查认为 LTR simple 默认展示仍不适合产品，可回退为：

```text
rollback_to_top50_adaptive_default_with_ltr_reference_only
```

回退方式：

- 后端 `default_method_key` 改回 `rank_rotate_top50_adaptive_score`；
- 前端 `ltrOptionalSimSelected` 改回 `rank_rotate_top50_adaptive_score`；
- 保留四策略下拉和只读边界不变；
- 不改回放、不重训、不触发写链路。

## 12. Gate 建议

```text
phaseb2_ltr_simple_default_readonly_product_closure_accepted
```
