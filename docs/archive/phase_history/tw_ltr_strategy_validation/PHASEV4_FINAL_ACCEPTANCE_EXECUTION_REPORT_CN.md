# Phase V4 最终验收执行报告

生成时间：2026-06-14

执行依据：`docs/tw_ltr_strategy_validation/PHASEV4A_REVIEW_AND_PHASEV4_FINAL_ACCEPTANCE_WORK_CN.md`

## 1. 本轮执行范围

本轮只做 Phase V4 optional sim 最终验收确认。

未改前端、API、service、replay 口径、模型、数据源或任何交易 / monitor / provider / accepted latest 链路。

## 2. 最终文件清单

### 2.1 Phase V4 Optional Sim 本轮新增归因

- `backend/app/services/tw_ltr_optional_sim_strategy.py`
  - `TWLTROptionalSimStrategyService`，只读 Phase V2 既有 artifact。
- `backend/app/routes/tw_stock.py`
  - `GET /api/tw-stock/ltr-optional-sim-strategies`。
- `frontend/src/api/tw-stock.js`
  - `getTwStockLTROptionalSimStrategies()`，method 固定为 `get`。
- `frontend/src/views/tw-stock-monitor/index.vue`
  - `data-testid="ltr-optional-sim-strategy-panel"` 只读展示。
- `backend/tests/test_tw_ltr_readonly_explanation_api.py`
  - optional sim GET-only、405、readonly 防调用测试。
- `frontend/tests/unit/tw-stock-monitor-static-check.mjs`
  - optional sim API / panel 静态检查。
- `frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs`
  - optional sim E2E / network audit 断言。
- `scripts/scan_tw_ltr_phasev4_optional_sim_static_safety.py`
  - Phase V4 scoped static safety scan。
- `data_tw/experiments/ltr_strategy_validation/phasev4_min_optional_sim/phasev4_static_safety_scan.json`
- `data_tw/experiments/ltr_strategy_validation/phasev4_min_optional_sim/phasev4_e2e_network_audit.json`
- `docs/tw_ltr_strategy_validation/PHASEV4_MIN_OPTIONAL_SIM_IMPLEMENTATION_EXECUTION_REPORT_CN.md`
- `docs/tw_ltr_strategy_validation/PHASEV4A_SCOPE_ATTRIBUTION_REPAIR_EXECUTION_REPORT_CN.md`

### 2.2 `ltr-readonly-explanation` 既有归因

`ltr-readonly-explanation` 属于此前 `tw_ltr_rerank_regime_turnover` 主线已接受的 LTR-only readonly explanation 最小接入，不是 Phase V4 optional sim 的新增分支。

归因证据见：

```text
docs/tw_ltr_strategy_validation/PHASEV4A_SCOPE_ATTRIBUTION_REPAIR_EXECUTION_REPORT_CN.md
```

该报告已说明：

- `GET /api/tw-stock/ltr-readonly-explanation` 来自此前 Phase5 系列；
- manual review explanation 已在此前 Phase5R 回退；
- Phase5S 已收口 LTR-only readonly explanation；
- 当前 dirty worktree 的 diff 混合显示不等同于 Phase V4 单轮新增范围。

## 3. 策略关系最终确认

- 默认主基线仍为：`rank_rotate_top50_adaptive_score`。
- LTR 可选模拟策略 A：`phase1c_ltr_simple_daily`。
- LTR 可选模拟策略 B：`phase1c_ltr_turnover_controlled_daily`。
- A / B 同等级展示，不排序、不标优劣、不替代默认主基线。
- 用户选择只影响本地展示 active 状态，不保存、不触发写请求。

固定边界文案保留：

```text
仅供只读历史模拟和研究复盘，不构成投资建议，不产生真实交易、委托或仓位。
```

## 4. 只读 / GET-only / Non-default / Non-trading 结论

最终结论：通过。

确认项：

- 只读：服务只读 Phase V2 既有 artifact，不写业务状态；
- GET-only：新增 endpoint 仅为 `GET /api/tw-stock/ltr-optional-sim-strategies`；
- 可选：不自动启用 LTR；
- 模拟：只用于历史模拟和研究复盘语境；
- 非默认：不替换 `rank_rotate_top50_adaptive_score`；
- 非交易：不连接 broker，不提交 orders，不产生 target position / target weight；
- 不触发 provider refresh / publish；
- 不触发 accepted latest switching；
- 不触发 monitor config save / scan / alerts write；
- 不输出买卖、持有、仓位、收益承诺、胜率或上涨概率语义。

## 5. Static Safety Scan 结果

产物：

```text
data_tw/experiments/ltr_strategy_validation/phasev4_min_optional_sim/phasev4_static_safety_scan.json
```

结果：

```json
{
  "ok": true,
  "forbidden_request_count": 0,
  "monitor_config_write_count": 0,
  "monitor_scan_post_count": 0,
  "monitor_alerts_write_count": 0,
  "ops_dry_run_post_count": 0,
  "broker_quick_trade_orders_count": 0,
  "target_position_weight_count": 0,
  "provider_refresh_publish_count": 0,
  "accepted_latest_switch_count": 0,
  "unsafe_buy_sell_hold_semantics_count": 0,
  "endpoint_get_only": true,
  "route_get_only": true
}
```

## 6. E2E / Network Audit 结果

产物：

```text
data_tw/experiments/ltr_strategy_validation/phasev4_min_optional_sim/phasev4_e2e_network_audit.json
```

结果：

```json
{
  "ok": true,
  "ltr_optional_sim_strategies_request_count": 2,
  "sim_write_request_count": 0,
  "quick_trade_request_count": 0,
  "broker_request_count": 0,
  "real_order_request_count": 0,
  "monitor_config_write_count": 0,
  "monitor_scan_post_count": 0,
  "monitor_alerts_write_count": 0,
  "qlib_ops_post_count": 0,
  "accepted_latest_switch_count": 0,
  "provider_publish_refresh_count": 0,
  "target_position_request_count": 0,
  "target_weight_request_count": 0,
  "forbidden_request_count": 0,
  "page_error_count": 0
}
```

## 7. 回退路径

如需回退 Phase V4 optional sim，仅移除 optional sim 接入，不影响此前已接受的 `ltr-readonly-explanation`：

1. 删除 `backend/app/services/tw_ltr_optional_sim_strategy.py`。
2. 从 `backend/app/routes/tw_stock.py` 移除 `TWLTROptionalSimStrategyService`、`ltr_optional_sim_strategy_service` 和 `/ltr-optional-sim-strategies` route。
3. 从 `frontend/src/api/tw-stock.js` 移除 `getTwStockLTROptionalSimStrategies()`。
4. 从 `frontend/src/views/tw-stock-monitor/index.vue` 移除 `ltr-optional-sim-strategy-panel`、`ltrOptionalSim*` data/computed/method/CSS 和加载调用。
5. 移除 optional sim 相关测试断言和 `scripts/scan_tw_ltr_phasev4_optional_sim_static_safety.py`。
6. 删除 `data_tw/experiments/ltr_strategy_validation/phasev4_min_optional_sim/` 下 V4 optional sim artifact。

## 8. 最终 Gate 建议

建议最终 gate：

```text
optional_sim_strategy_accepted_readonly_non_default
```

理由：Phase V4 optional sim 已完成最小只读接入，范围归因已由 Phase V4A 澄清，static safety scan 与 E2E/network audit 均通过，且未改变默认主基线、未新增交易或写入链路。
