# Phase5R LTR-only 回退执行报告

生成时间：2026-06-14

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

执行依据：`docs/tw_ltr_rerank_regime_turnover/PHASE5_REVIEW_AND_MANUAL_REVIEW_ROLLBACK_WORK_CN.md`

---

## 1. 本轮目标

只做一件事：回退误混入 Phase5 的 `manual review explanation`，只保留 `LTR readonly explanation` 最小只读接入。

本轮未新增模型、未新增数据源、未接入 provider / accepted latest / monitor 写入、未接入交易层或推荐层。

---

## 2. 实际回退文件清单

### 2.1 后端回退

- `backend/app/routes/tw_stock.py`
  - 删除 `TWManualReviewExplanationService` / `ManualReviewExplanationError` import；
  - 删除 `manual_review_explanation_service` 实例；
  - 删除 `_manual_review_*` query/context helper；
  - 删除 `GET /api/tw-stock/manual-review/explanation` route。

- 删除本轮误引入的 manual review explanation 文件：
  - `backend/app/services/tw_manual_review_explanation.py`
  - `backend/tests/test_tw_manual_review_explanation.py`
  - `backend/tests/test_tw_manual_review_explanation_api.py`

### 2.2 前端回退

- `frontend/src/api/tw-stock.js`
  - 删除 `getTwStockManualReviewExplanation()`。

- `frontend/src/views/tw-stock-monitor/index.vue`
  - 删除 `manualReviewReadonlyTestMode`；
  - 删除 `manual-review-readonly-test` 测试模式；
  - 删除 `manual-review-explanation-panel` 面板；
  - 删除 `manualReview*` explanation 相关状态、计算属性、方法和样式；
  - 删除 manual review explanation 在 mounted / loadQlibSignals 中的联动逻辑。

- 删除本轮误引入的 manual review explanation 前端测试：
  - `frontend/tests/e2e/tw-stock-manual-review-readonly.mjs`
  - `frontend/tests/unit/tw-stock-manual-review-explanation-check.mjs`

---

## 3. 保留的 LTR 主线文件清单

- `backend/app/services/tw_ltr_readonly_explanation.py`
- `backend/app/routes/tw_stock.py`
  - 仅保留新增 LTR route：`GET /api/tw-stock/ltr-readonly-explanation`
- `backend/tests/test_tw_ltr_readonly_explanation_api.py`
- `frontend/src/api/tw-stock.js`
  - 仅保留新增 LTR API：`getTwStockLTRReadonlyExplanation()`
- `frontend/src/views/tw-stock-monitor/index.vue`
  - 仅保留 LTR readonly explanation 最小只读面板
- `frontend/tests/unit/tw-stock-monitor-static-check.mjs`
- `frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs`

---

## 4. 代码搜索验证结果

执行搜索：

```text
rg -n "manual-review/explanation|TWManualReviewExplanationService|manualReviewReadonlyTestMode|manual-review-readonly-test|manual-review-explanation-panel|getTwStockManualReviewExplanation" backend/app frontend/src frontend/tests backend/tests
```

结果：无命中。

说明：`rg` 返回码为 1，表示没有找到指定残留。既有代码中仍可能存在 `manual_review` 业务枚举或“人工复核”文案，它们属于原有 rank-tech / portfolio replay 语义，不是本轮回退对象，也不属于 manual review explanation 模块。

---

## 5. 后端接口验证结果

执行：

```text
python -m py_compile backend/app/services/tw_ltr_readonly_explanation.py backend/app/routes/tw_stock.py backend/tests/test_tw_ltr_readonly_explanation_api.py
```

结果：通过。

执行：

```text
python -m pytest backend/tests/test_tw_ltr_readonly_explanation_api.py -q
```

结果：

```text
4 passed in 1.12s
```

覆盖点：

- `GET /api/tw-stock/ltr-readonly-explanation` 正常返回；
- POST / PUT / PATCH / DELETE 返回 405；
- 不暴露 `source_trace` / `summary_notes`；
- 不触发 monitor / provider / accepted latest 相关变更服务；
- 路由切片中未出现 manual review explanation 入口。

---

## 6. 前端静态检查结果

执行：

```text
node frontend/tests/unit/tw-stock-monitor-static-check.mjs
```

结果：

```text
tw-stock-monitor static checks passed
```

覆盖点：

- `getTwStockLTRReadonlyExplanation()` 仍存在；
- `/ltr-readonly-explanation` 路径仍存在；
- `data-testid="ltr-readonly-explanation-panel"` 仍存在；
- 首屏字段 `why_no_action` / `tradeoff_summary` / `research_role_label` / `readonly_disclaimer` 仍存在；
- 详情层字段仍存在；
- 不暴露 `source_trace` / `summary_notes`。

---

## 7. 只读 E2E 结果

构建：

```text
corepack pnpm build
```

结果：通过。

E2E 使用当前构建产物和临时静态服务验证：

```text
python scripts/serve_frontend_static_proxy.py --host 127.0.0.1 --port 8011 --dist frontend/dist --backend http://127.0.0.1:5000
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8011 node frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs
```

结果：

```text
tw-stock rank-tech portfolio replay readonly e2e passed
```

关键计数：

```json
{
  "ltr_readonly_explanation_request_count": 2,
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

临时 `127.0.0.1:8011` 静态服务已在验证后停止，最终端口检查未见 8011 监听。

---

## 8. 安全边界声明

本轮回退后，当前新增产品链路只剩 LTR readonly explanation。

未做事项：

- 没有保留 manual review explanation route / API / UI / 状态 / 方法 / 样式；
- 没有新增第二个 explanation 模块；
- 没有 provider refresh / publish；
- 没有 accepted latest switching；
- 没有 monitor config save / scan / alerts write；
- 没有 broker / quick-trade / order；
- 没有 target position / target weight；
- 没有收益承诺、胜率或上涨概率语义；
- 没有把 Phase3C explanation payload 抬升为推荐层。

---

## 9. 结论

Phase5R 回退完成。

当前版本已收窄为：

```text
LTR readonly explanation -> 固定 Phase3C payload -> 后端只读 GET -> 前端最小只读展示 -> 只读 E2E
```

manual review explanation 已从当前产品链路中移除，等待审查者复审。
