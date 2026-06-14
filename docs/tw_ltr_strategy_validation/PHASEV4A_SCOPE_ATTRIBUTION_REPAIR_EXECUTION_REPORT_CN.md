# Phase V4A 范围归因修复执行报告

生成时间：2026-06-14

执行依据：`docs/tw_ltr_strategy_validation/PHASEV4_REVIEW_AND_PHASEV4A_SCOPE_ATTRIBUTION_REPAIR_WORK_CN.md`

## 1. 本轮执行范围

本轮只做范围归因说明与证据整理。

未修改后端 route、service、前端页面、API、测试或数据产物；未新增功能；未重跑训练、回放、调参、联网或 provider / accepted latest / monitor / broker / orders 链路。

## 2. 结论

`ltr-readonly-explanation` 相关 route / API / panel / service / test 不是 Phase V4 optional sim 的新增分支；它属于此前 `tw_ltr_rerank_regime_turnover` 主线已经收口的 LTR-only readonly explanation 最小只读接入。

Phase V4 的真实新增范围是 optional sim：

```text
GET /api/tw-stock/ltr-optional-sim-strategies
getTwStockLTROptionalSimStrategies()
ltr-optional-sim-strategy-panel
TWLTROptionalSimStrategyService
```

当前 `git diff` 中同时出现 `ltr-readonly-explanation`，原因是工作树保留了此前主线的未提交改动，`git diff` 以当前仓库 HEAD 为基准展示，不能直接等同于 Phase V4 单轮新增范围。

## 3. `ltr-readonly-explanation` 归属说明

### 3.1 引入轮次

`ltr-readonly-explanation` 归属于此前 LTR rerank / regime / turnover 主线的 Phase5 系列。

本地文档证据：

- `docs/tw_ltr_rerank_regime_turnover/PHASE4B_REVIEW_AND_PHASE5_READONLY_INTEGRATION_IMPLEMENTATION_WORK_CN.md`
  - 授权 Phase5 真实只读接入；明确允许 `GET /api/tw-stock/ltr-readonly-explanation`。
- `docs/tw_ltr_rerank_regime_turnover/PHASE5_READONLY_INTEGRATION_IMPLEMENTATION_EXECUTION_REPORT_CN.md`
  - 记录 `GET /api/tw-stock/ltr-readonly-explanation`、`data-testid="ltr-readonly-explanation-panel"` 等接入内容。
- `docs/tw_ltr_rerank_regime_turnover/PHASE5_REVIEW_AND_MANUAL_REVIEW_ROLLBACK_WORK_CN.md`
  - 审查者要求回退 manual review explanation，只保留 `LTR readonly explanation`。
- `docs/tw_ltr_rerank_regime_turnover/PHASE5R_LTR_ONLY_ROLLBACK_EXECUTION_REPORT_CN.md`
  - 记录回退后仅保留 LTR readonly explanation 最小只读接入。
- `docs/tw_ltr_rerank_regime_turnover/PHASE5S_REVIEW_AND_LTR_MAINLINE_CLOSURE_CN.md`
  - Phase5S 通过，最终链路包含 `LTR readonly explanation service -> GET /api/tw-stock/ltr-readonly-explanation`。
- `docs/tw_ltr_rerank_regime_turnover/LTR_MAINLINE_FINAL_CLOSURE_ARCHIVE_CN.md`
  - 归档保留 `LTR readonly explanation` 最小只读接入。

### 3.2 是否属于此前已接受范围

是。

`ltr-readonly-explanation` 是此前 LTR-only readonly explanation 的最小接入，服务读取固定解释 payload，API 为 GET-only，前端展示“为什么现在不动”的只读解释，不提供交易、monitor、provider 或 accepted latest 写入。

### 3.3 是否在 Phase V4 被新增、修改或扩展

从 Phase V4 工作目标看，它不是 V4 optional sim 的必要新增项。

从当前工作树 diff 看，相关代码仍出现在 `git diff` 中，是因为此前 Phase5/Phase5R/Phase5S 主线改动未形成独立提交，导致多轮历史改动在同一个 dirty worktree 中同时显示。

本轮 Phase V4A 没有修改 `ltr-readonly-explanation` 相关代码，也没有扩展其 API 行为或展示逻辑。

### 3.4 为什么 V4 报告没有列入该归属

Phase V4 执行报告只列了 optional sim 主线视角的改动，没有解释当前 dirty worktree 中保留的历史 `ltr-readonly-explanation` diff，因此造成审查者无法从报告直接区分“本轮新增”和“此前已接受但未提交”的代码。

这是报告范围归因遗漏，不是 optional sim 功能越界证据。

## 4. 文件级归因

### 4.1 此前 LTR readonly explanation 归属文件

这些文件或文件片段归属于此前 Phase5/Phase5R/Phase5S LTR-only readonly explanation 主线：

- `backend/app/services/tw_ltr_readonly_explanation.py`
  - 归属：此前 LTR-only readonly explanation service。
- `backend/app/routes/tw_stock.py`
  - 归属片段：`TWLTRReadonlyExplanationService` import、`ltr_readonly_explanation_service` 实例、`GET /ltr-readonly-explanation` route。
- `frontend/src/api/tw-stock.js`
  - 归属片段：`getTwStockLTRReadonlyExplanation()`。
- `frontend/src/views/tw-stock-monitor/index.vue`
  - 归属片段：`data-testid="ltr-readonly-explanation-panel"`、`loadLtrReadonlyExplanation()`、`ltrReadonlyExplanationMethods`、`.ltr-readonly-explanation` 样式。
- `backend/tests/test_tw_ltr_readonly_explanation_api.py`
  - 归属片段：文件头部 Phase5 LTR readonly explanation API tests 及 `/ltr-readonly-explanation` 测试。
- `frontend/tests/unit/tw-stock-monitor-static-check.mjs`
  - 归属片段：`ltr-readonly-explanation` 静态断言。
- `frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs`
  - 归属片段：`ltrReadonlyExplanationPayload()`、`/ltr-readonly-explanation` mock、`ltr-readonly-explanation-panel` E2E 断言。

### 4.2 Phase V4 optional sim 真实最小改动清单

这些文件或文件片段归属于 Phase V4 optional sim：

- `backend/app/services/tw_ltr_optional_sim_strategy.py`
  - 新增 optional sim 只读服务，只读 Phase V2 既有 artifact。
- `backend/app/routes/tw_stock.py`
  - 归属片段：`TWLTROptionalSimStrategyService` import、`ltr_optional_sim_strategy_service` 实例、`GET /ltr-optional-sim-strategies` route。
- `frontend/src/api/tw-stock.js`
  - 归属片段：`getTwStockLTROptionalSimStrategies()`。
- `frontend/src/views/tw-stock-monitor/index.vue`
  - 归属片段：`data-testid="ltr-optional-sim-strategy-panel"`、`loadLtrOptionalSimStrategies()`、`ltrOptionalSimStrategies`、`ltrOptionalSimMetricText()`、`.ltr-optional-*` 样式。
- `backend/tests/test_tw_ltr_readonly_explanation_api.py`
  - 归属片段：`/ltr-optional-sim-strategies` 的 GET payload、405、mutating service 防调用、route slice 检查。
- `frontend/tests/unit/tw-stock-monitor-static-check.mjs`
  - 归属片段：`getTwStockLTROptionalSimStrategies`、`/ltr-optional-sim-strategies`、`ltr-optional-sim-strategy-panel` 静态断言。
- `frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs`
  - 归属片段：`ltrOptionalSimPayload()`、`/ltr-optional-sim-strategies` mock、optional sim 面板文本与 network audit 计数。
- `scripts/scan_tw_ltr_phasev4_optional_sim_static_safety.py`
  - Phase V4 scoped 静态安全扫描脚本。
- `data_tw/experiments/ltr_strategy_validation/phasev4_min_optional_sim/phasev4_static_safety_scan.json`
  - Phase V4 静态扫描产物。
- `data_tw/experiments/ltr_strategy_validation/phasev4_min_optional_sim/phasev4_e2e_network_audit.json`
  - Phase V4 E2E/network audit 产物。

## 5. `git diff --name-only` 说明

当前 `git diff --name-only` 输出中，与 V4 optional sim 相关的已跟踪文件为：

```text
backend/app/routes/tw_stock.py
frontend/src/api/tw-stock.js
frontend/src/views/tw-stock-monitor/index.vue
frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs
frontend/tests/unit/tw-stock-monitor-static-check.mjs
```

其中存在两类归因：

- `ltr-readonly-explanation` 片段：此前 LTR-only readonly explanation 主线遗留在 dirty worktree 中；
- `ltr-optional-sim-strategies` / `ltr-optional-sim-strategy-panel` 片段：Phase V4 optional sim 本轮真实新增范围。

当前 `git diff --name-only` 不显示未跟踪文件。与 Phase V4 optional sim 相关的未跟踪文件包括：

```text
backend/app/services/tw_ltr_optional_sim_strategy.py
scripts/scan_tw_ltr_phasev4_optional_sim_static_safety.py
docs/tw_ltr_strategy_validation/PHASEV4_MIN_OPTIONAL_SIM_IMPLEMENTATION_EXECUTION_REPORT_CN.md
docs/tw_ltr_strategy_validation/PHASEV4A_SCOPE_ATTRIBUTION_REPAIR_EXECUTION_REPORT_CN.md
```

与此前 LTR readonly explanation 相关的未跟踪文件包括：

```text
backend/app/services/tw_ltr_readonly_explanation.py
backend/tests/test_tw_ltr_readonly_explanation_api.py
```

## 6. Optional Sim Scoped Diff 说明

Optional sim endpoint scoped diff：

```text
backend/app/routes/tw_stock.py
- 新增 GET /ltr-optional-sim-strategies
- 调用 ltr_optional_sim_strategy_service.product_view()
- 错误时只返回 read_error payload，不写状态
```

Optional sim frontend scoped diff：

```text
frontend/src/api/tw-stock.js
- 新增 getTwStockLTROptionalSimStrategies()
- method 固定为 get

frontend/src/views/tw-stock-monitor/index.vue
- 新增 ltr-optional-sim-strategy-panel
- 展示默认主基线、LTR 模拟策略 A、LTR 模拟策略 B
- 默认 selected key 仍为 rank_rotate_top50_adaptive_score
- 用户选择只影响本地展示 active 状态，不保存、不发写请求
```

Optional sim validation scoped diff：

```text
backend/tests/test_tw_ltr_readonly_explanation_api.py
- 新增 /ltr-optional-sim-strategies GET-only 与 readonly 检查

frontend/tests/unit/tw-stock-monitor-static-check.mjs
- 新增 optional sim GET API 与 panel 静态检查

frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs
- 新增 optional sim fixture、GET mock、panel 文本断言、network audit 计数
```

## 7. 安全边界复核

沿用 Phase V4 已生成产物即可，因为 Phase V4A 未修改代码或行为。

### 7.1 Static Safety Scan

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
  "unsafe_buy_sell_hold_semantics_count": 0
}
```

### 7.2 E2E / Network Audit

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

## 8. Manual Review 回流检查

未发现 Phase V4 optional sim 路径引入 manual review explanation。

V4 静态检查中仍保持以下断言：

```text
manual-review/explanation 不存在
getTwStockManualReviewExplanation 不存在
manualReviewReadonlyTestMode 不存在
manual-review-readonly-test 不存在
manual-review-explanation-panel 不存在
```

结论：没有 manual review explanation 回流。

## 9. 是否需要修改 V4 执行报告

本轮未修改 `docs/tw_ltr_strategy_validation/PHASEV4_MIN_OPTIONAL_SIM_IMPLEMENTATION_EXECUTION_REPORT_CN.md`。

原因：Phase V4A 文档只授权提交窄报告，不授权改代码或扩展实现；本报告作为 V4 报告的范围归因补充材料即可解决审查阻塞。

如果审查者要求把归因说明合并进 V4 报告，可在下一轮按审查意见补充 V4 报告文本，不需要改功能代码。

## 10. Gate 建议

建议 gate：

```text
return_to_phasev4_final_acceptance_review
```

理由：`ltr-readonly-explanation` 已证明属于此前已接受的 LTR-only readonly explanation 主线；Phase V4 optional sim 的真实最小范围独立、清楚，未夹带 manual review、交易、monitor/provider 写入、accepted latest、broker、orders、target position / target weight 或默认策略切换。
