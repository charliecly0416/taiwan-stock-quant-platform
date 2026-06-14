# Phase V4 最小可选模拟策略实现执行报告

生成时间：2026-06-14

主线依据：`docs/tw_ltr_strategy_validation/PHASEV3_REVIEW_AND_PHASEV4_MIN_OPTIONAL_SIM_IMPLEMENTATION_WORK_CN.md`

## 1. 本轮目标

仅把 V3 冻结的两条同等级 LTR 可选模拟策略接入为只读历史模拟展示，并完成只读验收。

本轮未做默认策略切换、策略优化、调参、重训、新数据源、联网、provider / accepted latest 写入、monitor 写入、broker / quick-trade / orders / target position / target weight。

## 2. 改动文件清单

- `backend/app/services/tw_ltr_optional_sim_strategy.py`
  - 新增只读服务，从既有 Phase V2 artifact 读取 `phasev2_walk_forward_oos.csv`、`phasev2_rolling_6m_12m.csv`、`phasev2_gate_summary.json`。
  - 输出 `phasev4_optional_sim_strategy_readonly_v1` payload。
- `backend/app/routes/tw_stock.py`
  - 新增 `GET /api/tw-stock/ltr-optional-sim-strategies`。
  - 只返回静态 artifact 派生 payload，不写业务状态。
- `frontend/src/api/tw-stock.js`
  - 新增 `getTwStockLTROptionalSimStrategies()`，method 固定为 `get`。
- `frontend/src/views/tw-stock-monitor/index.vue`
  - 新增 `data-testid="ltr-optional-sim-strategy-panel"` 只读展示区。
  - 首屏展示：默认主基线、LTR 模拟策略 A、LTR 模拟策略 B、样本范围、费用后历史模拟、最大回撤、动作数、independent_test 切片、固定边界文案。
- `backend/tests/test_tw_ltr_readonly_explanation_api.py`
  - 新增 Phase V4 GET-only、405、mutating service 防调用、route slice 静态检查。
- `frontend/tests/unit/tw-stock-monitor-static-check.mjs`
  - 新增 Phase V4 API / 页面静态检查。
- `frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs`
  - 新增 Phase V4 mock payload、面板断言、GET-only network audit 计数。
- `scripts/scan_tw_ltr_phasev4_optional_sim_static_safety.py`
  - 新增 Phase V4 scoped 静态安全扫描脚本。

## 3. 只读与 GET-only 确认

- 新增 API：`GET /api/tw-stock/ltr-optional-sim-strategies`。
- POST / PUT / PATCH / DELETE 对该 endpoint 均返回 405。
- 服务只读本地既有 Phase V2 artifact。
- 前端只调用 GET，不保存用户选择，不写 monitor config，不触发 scan / alerts。

## 4. 策略关系确认

- `rank_rotate_top50_adaptive_score` 保持默认主基线。
- `phase1c_ltr_simple_daily` 展示为 `LTR 模拟策略 A`。
- `phase1c_ltr_turnover_controlled_daily` 展示为 `LTR 模拟策略 B`。
- 两条 LTR 均为同等级可选模拟策略，不排序、不标优劣、不替代默认主基线。

固定首屏边界文案：

```text
仅供只读历史模拟和研究复盘，不构成投资建议，不产生真实交易、委托或仓位。
```

## 5. 禁止事项确认

本轮未新增或触发：

- POST / PUT / PATCH / DELETE 新写请求；
- provider refresh / publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 新数据源、联网、重训、调参；
- 默认启用 LTR 或替换 Top50 自适应；
- 推荐策略、更优策略、最佳策略、买入/卖出/持有建议、预计收益、胜率、上涨概率等产品语义。

## 6. 验证结果

### 6.1 编译检查

```text
python -m py_compile backend/app/services/tw_ltr_optional_sim_strategy.py scripts/scan_tw_ltr_phasev4_optional_sim_static_safety.py
结果：通过
```

### 6.2 后端 API / 服务测试

```text
python -m pytest backend/tests/test_tw_ltr_readonly_explanation_api.py -q
结果：8 passed in 1.17s
```

覆盖：GET payload、POST/PUT/PATCH/DELETE=405、mutating service monkeypatch 防调用、route slice GET-only。

### 6.3 前端静态检查

```text
node frontend/tests/unit/tw-stock-monitor-static-check.mjs
结果：tw-stock-monitor static checks passed
```

### 6.4 静态禁止文案 / 写链路扫描

```text
python scripts/scan_tw_ltr_phasev4_optional_sim_static_safety.py
结果：ok=true, forbidden_request_count=0
```

产物：`data_tw/experiments/ltr_strategy_validation/phasev4_min_optional_sim/phasev4_static_safety_scan.json`

关键计数：

```json
{
  "monitor_config_write_count": 0,
  "monitor_scan_post_count": 0,
  "monitor_alerts_write_count": 0,
  "ops_dry_run_post_count": 0,
  "broker_quick_trade_orders_count": 0,
  "target_position_weight_count": 0,
  "provider_refresh_publish_count": 0,
  "accepted_latest_switch_count": 0,
  "unsafe_buy_sell_hold_semantics_count": 0,
  "forbidden_request_count": 0
}
```

### 6.5 构建与只读 E2E / network audit

```text
corepack pnpm build
结果：通过
```

Vite dev / preview 在当前机器因系统 watcher 上限 `ENOSPC` 退出；为避免新增系统配置变更，本轮使用已构建 `frontend/dist` + `python -m http.server` 作为静态服务运行 E2E。

```text
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:5177 node frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs
结果：通过
```

产物：`data_tw/experiments/ltr_strategy_validation/phasev4_min_optional_sim/phasev4_e2e_network_audit.json`

关键 E2E/network audit 结果：

```json
{
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

## 7. 回退方式

如审查者要求回退 V4，可移除以下最小接入点：

1. 删除 `backend/app/services/tw_ltr_optional_sim_strategy.py`。
2. 从 `backend/app/routes/tw_stock.py` 移除 `TWLTROptionalSimStrategyService` import、实例和 `/ltr-optional-sim-strategies` route。
3. 从 `frontend/src/api/tw-stock.js` 移除 `getTwStockLTROptionalSimStrategies()`。
4. 从 `frontend/src/views/tw-stock-monitor/index.vue` 移除 `ltr-optional-sim-strategy-panel`、相关 data/computed/method/CSS 和 load 调用。
5. 移除 V4 相关测试断言与 `scripts/scan_tw_ltr_phasev4_optional_sim_static_safety.py`。
6. 删除 `data_tw/experiments/ltr_strategy_validation/phasev4_min_optional_sim/` 下本轮 artifact。

## 8. Gate 建议

建议 gate：

```text
optional_sim_strategy_accepted_readonly_non_default
```

理由：实现保持最小、只读、可选、模拟、非默认；静态扫描、API 测试、前端静态检查、构建和只读 E2E/network audit 均通过。
