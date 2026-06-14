# LTR Rerank + Regime + Turnover 主线最终归档

生成时间：2026-06-14

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

收口依据：`docs/tw_ltr_rerank_regime_turnover/PHASE5S_REVIEW_AND_LTR_MAINLINE_CLOSURE_CN.md`

---

## 1. 最终结论

LTR rerank + regime + turnover 主线已完成只读产品收口。

最终保留链路为：

```text
Phase3C fixed payload
-> LTR readonly explanation service
-> GET /api/tw-stock/ltr-readonly-explanation
-> 前端最小只读展示
-> static check / readonly E2E
```

当前状态可以归档为：

```text
保留 LTR readonly explanation 最小只读接入；
不恢复 manual review explanation；
不继续扩展推荐/交易/写入链路；
不再围绕本主线新增功能分支。
```

---

## 2. 最终保留文件

### 2.1 后端

- `backend/app/services/tw_ltr_readonly_explanation.py`
  - 只读取固定 Phase3C payload artifact；
  - 输出 Phase4B/Phase5 白名单产品视图；
  - 不触发数据刷新、provider、accepted latest、monitor 或交易链路。

- `backend/app/routes/tw_stock.py`
  - 保留只读接口：

```text
GET /api/tw-stock/ltr-readonly-explanation
```

- `backend/tests/test_tw_ltr_readonly_explanation_api.py`
  - 覆盖 GET 返回、405 写方法拒绝、字段过滤和不触发变更服务。

### 2.2 前端

- `frontend/src/api/tw-stock.js`
  - 保留：`getTwStockLTRReadonlyExplanation()`。

- `frontend/src/views/tw-stock-monitor/index.vue`
  - 保留 LTR readonly explanation 最小面板；
  - 面板位于“今日复盘与历史模拟”卡片内；
  - 不替代“今天先看什么”主流程；
  - 首屏只展示原因、取舍、角色标签、只读边界；
  - 详情层才展示历史回放指标。

### 2.3 测试

- `frontend/tests/unit/tw-stock-monitor-static-check.mjs`
  - 覆盖 LTR API、面板、字段、详情字段、manual review explanation 残留禁用检查。

- `frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs`
  - 覆盖只读请求计数、LTR 面板渲染、主流程顺序、首屏禁止高风险数值、禁止写请求/交易/provider/accepted/monitor 路径。

---

## 3. 最终展示契约

### 3.1 首屏固定信息

LTR 面板首屏只保留 4 个信息单元：

1. `今天不动作的主要原因：{原因短语}。`
2. `历史回放取舍：{动作频率}，{换手压力}，{回撤水平}。`
3. `{用户短标签}`，例如 `少动作观察`
4. `仅供只读研究复盘，不构成操作建议，不会产生任何真实执行动作。`

### 3.2 首屏禁止内容

LTR 首屏不展示：

- 费用后净值变化；
- 大百分比收益；
- 最大回撤详情；
- notional turnover proxy；
- 胜率；
- 上涨概率；
- 仓位或目标仓位。

### 3.3 详情层规则

详情层通过折叠面板 `查看历史回放明细` 展示，且必须把以下历史回放指标同屏展示：

- `net_return_summary`
- `drawdown_summary`
- `action_count_summary`
- `turnover_summary`
- `relative_to_top50_adaptive`
- `detail_disclaimer`

详情层指标只用于历史复盘，不作为推荐 CTA、主排序依据或未来表现承诺。

---

## 4. Manual Review Explanation 回退状态

manual review explanation 已从当前产品链路中回退。

最终不保留：

- `GET /api/tw-stock/manual-review/explanation`
- `TWManualReviewExplanationService`
- `ManualReviewExplanationError`
- `getTwStockManualReviewExplanation()`
- `manualReviewReadonlyTestMode`
- `manual-review-readonly-test`
- `manual-review-explanation-panel`
- `tw_manual_review_explanation` 服务与测试文件

最终搜索口径：

```text
rg -n "manual-review/explanation|TWManualReviewExplanationService|ManualReviewExplanationError|manualReviewReadonlyTestMode|manual-review-readonly-test|manual-review-explanation-panel|getTwStockManualReviewExplanation|tw_manual_review_explanation" backend/app frontend/src frontend/tests backend/tests docs/tw_ltr_rerank_regime_turnover
```

结论：

- 产品代码与测试中无 manual review explanation 产品链路残留；
- `docs/tw_ltr_rerank_regime_turnover` 中的命中仅为历史审查/执行说明。

未来若要恢复 manual review explanation，必须作为新主线重新由用户确认，不得并入本 LTR 主线。

---

## 5. 最终验证命令

本主线最终验收使用以下命令：

```text
python -m pytest backend/tests/test_tw_ltr_readonly_explanation_api.py -q
```

结果：`4 passed`。

```text
python -m py_compile backend/app/services/tw_ltr_readonly_explanation.py backend/app/routes/tw_stock.py backend/tests/test_tw_ltr_readonly_explanation_api.py
```

结果：通过。

```text
node frontend/tests/unit/tw-stock-monitor-static-check.mjs
```

结果：`tw-stock-monitor static checks passed`。

```text
corepack pnpm build
```

结果：`vite build` 通过。

```text
python scripts/serve_frontend_static_proxy.py --host 127.0.0.1 --port 8011 --dist frontend/dist --backend http://127.0.0.1:5000
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8011 node frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs
```

结果：`tw-stock rank-tech portfolio replay readonly e2e passed`。

E2E 关键计数：

```json
{
  "ltr_readonly_explanation_request_count": 2,
  "forbidden_request_count": 0,
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
  "page_error_count": 0
}
```

临时 `127.0.0.1:8011` 静态服务已在验收后停止。

---

## 6. 安全边界归档

当前 LTR 主线保持只读研究复盘边界：

- 不新增模型训练；
- 不新增数据源；
- 不联网抓取；
- 不 provider refresh/publish；
- 不 accepted latest switching；
- 不 monitor config save / scan / alerts write；
- 不 broker / quick-trade / order；
- 不 target position / target weight；
- 不提供收益承诺、胜率承诺或上涨概率；
- 不把 LTR explanation payload 抬升为推荐层或交易层。

只读边界文案固定为：

```text
仅供只读研究复盘，不构成操作建议，不会产生任何真实执行动作。
```

---

## 7. 用户第一性原则归档

### 简单

LTR 面板只回答“为什么现在不动”，不扩展为复杂研究工作台。

### 准确

首屏不展示收益、胜率、上涨概率或仓位；历史指标保留在详情层，并明确是历史回放复盘。

### 清晰

页面仍先展示“今日复盘与历史模拟”和“今天先看什么”，LTR explanation 是辅助解释。

### 实用

用户可以快速看到不动作原因、历史取舍和只读边界；需要深入复盘时再展开详情层。

---

## 8. 归档结论

本主线最终归档完成。

后续维护规则：

1. 保持当前 LTR-only 只读接入；
2. 不围绕本主线新增功能分支；
3. 不恢复 manual review explanation；
4. 不扩展推荐、交易或写入链路；
5. 若未来需要新的 explanation 模块，必须作为新主线重新立项并由用户确认。
