# Phase5S LTR-only 最终验收执行报告

生成时间：2026-06-14

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

执行依据：`docs/tw_ltr_rerank_regime_turnover/PHASE5R_REVIEW_AND_PHASE5S_LTR_ONLY_ACCEPTANCE_WORK_CN.md`

---

## 1. 本轮目标

只做 LTR-only readonly explanation 的最终产品验收。

本轮实际做了两类工作：

1. 修复 `frontend/src/views/tw-stock-monitor/index.vue` 中 Phase5/Phase5R 后遗留的 slot/title/body 结构错位；
2. 补充 LTR-only 页面结构与只读边界验收断言。

未重新打开 manual review explanation，未新增第二个 explanation 模块，未修改模型、回放口径、数据源、provider、accepted latest、monitor 写入或交易链路。

---

## 2. 实际改动文件

### 2.1 前端结构修复

- `frontend/src/views/tw-stock-monitor/index.vue`
  - 以原有干净模板结构为基线恢复 `<template slot="title">`、table scoped slot、card body 的闭合关系；
  - 仅重新叠加 LTR readonly explanation 最小接入：
    - `getTwStockLTRReadonlyExplanation` import；
    - `loadingLtrReadonlyExplanation`；
    - `ltrReadonlyExplanationPayload` / `ltrReadonlyExplanationError`；
    - `ltrReadonlyExplanationMethods` computed；
    - `loadLtrReadonlyExplanation()`；
    - mounted 与 refreshAll 中的只读加载；
    - `data-testid="ltr-readonly-explanation-panel"` 面板；
    - LTR 面板样式。

### 2.2 测试补充

- `frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs`
  - 补充 LTR endpoint GET mock 与请求计数；
  - 补充 LTR 面板位置断言：面板在主回放卡内，且位于详细历史回放指标前；
  - 补充首屏文本断言：标题、原因、取舍、角色标签、只读边界；
  - 补充首屏禁止高风险详情断言：费用后净值变化、大百分比、最大回撤详情、notional turnover proxy、胜率、上涨概率、目标仓位；
  - 补充主流程顺序断言：`今日复盘与历史模拟` 和 `今天先看什么` 先于 LTR explanation。

- `frontend/tests/unit/tw-stock-monitor-static-check.mjs`
  - 补充 LTR API、面板、字段绑定、详情字段检查；
  - 补充 manual review explanation 残留禁用检查。

---

## 3. LTR-only 产品结构验收

### 3.1 页面区域

LTR 面板仍在现有 `今日复盘与历史模拟` 卡片内，作为辅助解释，不是独立页面，也不替代今日复盘主流程。

E2E 已验证：

- `今日复盘与历史模拟` 先出现；
- `今天先看什么` 先出现；
- `为什么现在不动` 后出现；
- LTR 面板位于 `.portfolio-replay-section` 前，即在精确历史回放指标前。

### 3.2 首屏展示

首屏只展示 4 个信息单元：

1. `今天不动作的主要原因：...`
2. `历史回放取舍：...`
3. `research_role_label`，例如 `少动作观察`
4. `仅供只读研究复盘，不构成操作建议，不会产生任何真实执行动作。`

### 3.3 首屏禁止内容

E2E 已验证 LTR 首屏不出现：

- `费用后净值变化`
- `+465.27%`
- `最大回撤约为`
- `notional turnover proxy`
- `胜率`
- `上涨概率`
- `目标仓位`

### 3.4 详情层展示

详情层仍通过 `查看历史回放明细` 折叠面板展示，且同屏保留：

- `net_return_summary`
- `drawdown_summary`
- `action_count_summary`
- `turnover_summary`
- `relative_to_top50_adaptive`
- `detail_disclaimer`

这些指标没有进入首屏，也没有作为推荐 CTA 或主排序依据。

### 3.5 slot/title/body 结构

本轮已恢复 `index.vue` 中被扰动的结构：

- `rank-tech-replay-card` 的 title slot 在标题行后正确闭合；
- toolbar、只读提示、今日复盘正文、LTR 面板、历史回放区域均在 card body 中；
- qlib run table、qlib signal table、rank change table、cross analysis table 等 scoped slot 已恢复为成对闭合结构；
- `corepack pnpm build` 通过；
- E2E 页面渲染无 `page_error`。

---

## 4. manual review explanation 残留验证

执行搜索：

```text
rg -n "manual-review/explanation|TWManualReviewExplanationService|ManualReviewExplanationError|manualReviewReadonlyTestMode|manual-review-readonly-test|manual-review-explanation-panel|getTwStockManualReviewExplanation|tw_manual_review_explanation" backend/app frontend/src frontend/tests backend/tests docs/tw_ltr_rerank_regime_turnover
```

结果：产品代码与测试中无残留。命中仅限历史审查/执行文档：

- `PHASE5_REVIEW_AND_MANUAL_REVIEW_ROLLBACK_WORK_CN.md`
- `PHASE5R_LTR_ONLY_ROLLBACK_EXECUTION_REPORT_CN.md`
- `PHASE5R_REVIEW_AND_PHASE5S_LTR_ONLY_ACCEPTANCE_WORK_CN.md`

这些是历史说明，不属于产品链路。

静态测试也明确断言：

- API 不含 `manual-review/explanation`；
- API 不含 `getTwStockManualReviewExplanation`；
- 页面不含 `manualReviewReadonlyTestMode`；
- 页面不含 `manual-review-readonly-test`；
- 页面不含 `manual-review-explanation-panel`。

---

## 5. 必做验证结果

### 5.1 后端 LTR API 测试

```text
python -m pytest backend/tests/test_tw_ltr_readonly_explanation_api.py -q
```

结果：

```text
4 passed in 1.09s
```

### 5.2 Python 编译检查

```text
python -m py_compile backend/app/services/tw_ltr_readonly_explanation.py backend/app/routes/tw_stock.py backend/tests/test_tw_ltr_readonly_explanation_api.py
```

结果：通过。

### 5.3 前端静态检查

```text
node frontend/tests/unit/tw-stock-monitor-static-check.mjs
```

结果：

```text
tw-stock-monitor static checks passed
```

### 5.4 前端构建

```text
corepack pnpm build
```

结果：通过。

说明：命令输出开头仍有 `/bin/sh: 2: source: not found`，但构建完成且 `vite build` 成功，未影响构建结果。

### 5.5 只读 E2E

使用当前构建产物和临时静态服务：

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

临时 `127.0.0.1:8011` 静态服务已停止，最终端口检查未见 8011 监听。

---

## 6. 安全边界声明

本轮没有做以下事项：

- 没有恢复或改名引入 manual review explanation；
- 没有新增第二个 explanation 模块；
- 没有新增推荐 CTA；
- 没有新增买入/卖出/仓位/收益承诺/胜率/上涨概率语义；
- 没有新增 POST/PUT/PATCH/DELETE 调用；
- 没有 provider refresh/publish；
- 没有 accepted latest switching；
- 没有 monitor config save / scan / alerts write；
- 没有 broker / quick-trade / order；
- 没有 target position / target weight；
- 没有修改模型、回放口径或数据源；
- 没有把 LTR explanation payload 抬升为主推荐或主排序依据。

---

## 7. 结论

Phase5S LTR-only 最终验收完成。

当前新增链路保持为：

```text
Phase3C fixed payload
-> LTR readonly explanation service
-> GET /api/tw-stock/ltr-readonly-explanation
-> 前端最小只读展示
-> static check / readonly E2E
```

验收结果：通过，等待审查者复审。
