# Phase5R 审查意见与 Phase5S LTR-only 最终验收工作文档

生成时间：2026-06-14

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

审查入口：`docs/tw_ltr_rerank_regime_turnover/PHASE5R_LTR_ONLY_ROLLBACK_EXECUTION_REPORT_CN.md`

---

## 1. 审查结论

Phase5R **通过回退审查**。

执行者已按用户决策完成：

```text
回退 manual review explanation，
只保留 LTR readonly explanation 主线。
```

本轮未发现新增模型、新数据源、provider/accepted latest/monitor 写入、交易层、推荐层或收益/概率承诺语义。

---

## 2. 本轮通过依据

### 2.1 manual review explanation 产品链路已移除

审查搜索：

```text
rg -n "manual-review/explanation|TWManualReviewExplanationService|ManualReviewExplanationError|manualReviewReadonlyTestMode|manual-review-readonly-test|manual-review-explanation-panel|getTwStockManualReviewExplanation|tw_manual_review_explanation" backend/app frontend/src frontend/tests backend/tests docs/tw_ltr_rerank_regime_turnover
```

结果：

- `backend/app`
- `frontend/src`
- `frontend/tests`
- `backend/tests`

均无 manual review explanation 实现入口残留。

命中只剩：

- `PHASE5_REVIEW_AND_MANUAL_REVIEW_ROLLBACK_WORK_CN.md`
- `PHASE5R_LTR_ONLY_ROLLBACK_EXECUTION_REPORT_CN.md`

这是审查/执行报告中的历史说明，不属于产品链路残留。

此外，执行者报告中列出的误引入文件实际已不存在：

- `backend/app/services/tw_manual_review_explanation.py`
- `backend/tests/test_tw_manual_review_explanation.py`
- `backend/tests/test_tw_manual_review_explanation_api.py`
- `frontend/tests/e2e/tw-stock-manual-review-readonly.mjs`
- `frontend/tests/unit/tw-stock-manual-review-explanation-check.mjs`

### 2.2 LTR readonly explanation 保持在主线内

当前保留内容符合 Phase4B/Phase5 边界：

- 后端仅新增 `GET /api/tw-stock/ltr-readonly-explanation`
- 后端 service 只读取固定 Phase3C payload artifact
- 前端仅新增 LTR readonly explanation 最小展示
- 首屏围绕：
  - `why_no_action`
  - `tradeoff_summary`
  - `research_role_label`
  - `readonly_disclaimer`
- 详情层展示历史回放指标，未抬升为推荐层

### 2.3 安全边界通过

已验证：

```text
python -m pytest backend/tests/test_tw_ltr_readonly_explanation_api.py -q
```

结果：

```text
4 passed
```

已验证：

```text
node frontend/tests/unit/tw-stock-monitor-static-check.mjs
```

结果：

```text
tw-stock-monitor static checks passed
```

说明：该命令在沙箱内曾因 `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted` 失败；非沙箱执行通过，属于环境权限问题，不是测试断言失败。

已验证：

```text
corepack pnpm build
```

结果：

```text
vite build 通过
```

---

## 3. 剩余风险

Phase5R 通过的是“回退是否完成”和“LTR-only 只读边界是否成立”，但仍有一个需要在下一轮收口的展示结构风险：

```text
frontend/src/views/tw-stock-monitor/index.vue
```

在 Phase5/Phase5R 改动后，多个 `<template slot="title">` 附近的缩进与闭合位置看起来被扰动。构建能够通过，但从用户第一性原则看，仍需用实际页面/E2E 证据确认：

1. LTR readonly explanation 面板是否出现在正确区域；
2. 标题、工具栏、正文是否没有错位；
3. 页面没有因为 slot 结构变化导致信息层级混乱；
4. LTR 首屏没有挤占原有“今日复盘与历史模拟”的主流程。

这个问题不影响 Phase5R 回退结论，但下一轮必须很窄地做最终 UI 结构验收和必要修复。

---

## 4. 是否偏离主线或新增分支

未发现新的偏离主线或新增分支。

本轮已经把 manual review explanation 从当前产品链路中移除，当前新增链路收窄为：

```text
Phase3C fixed payload
-> LTR readonly explanation service
-> GET /api/tw-stock/ltr-readonly-explanation
-> 前端最小只读展示
-> readonly E2E / static checks
```

允许进入 Phase5S，但 Phase5S 只能做最终 LTR-only 验收与必要展示结构修复。

---

## 5. Phase5S 本轮唯一目标

只做一件事：

```text
对 LTR-only readonly explanation 做最终产品验收；
若发现前端 slot/布局结构错位，只做最小修复；
不得重新打开 manual review explanation。
```

---

## 6. Phase5S 允许改动范围

允许修改：

- `frontend/src/views/tw-stock-monitor/index.vue`
  - 仅限修复 LTR-only 接入造成的模板结构、slot 闭合、展示顺序或样式错位；
- `frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs`
  - 仅限补充 LTR-only 只读展示验收；
- `frontend/tests/unit/tw-stock-monitor-static-check.mjs`
  - 仅限补充结构/禁用文案/危险入口检查；
- 必要时可补充 `docs/tw_ltr_rerank_regime_turnover/PHASE5S_LTR_ONLY_ACCEPTANCE_EXECUTION_REPORT_CN.md`。

默认不允许修改：

- 后端业务 route，除非只是修正文案或只读错误响应；
- `backend/app/services/tw_ltr_readonly_explanation.py` 的语义；
- Phase3C payload；
- replay/model/training 脚本；
- provider、accepted latest、monitor、broker、quick-trade、order、target position/weight 相关代码。

---

## 7. Phase5S 禁止事项

本轮禁止：

- 恢复或改名引入 manual review explanation；
- 新增第二个 explanation 模块；
- 新增推荐 CTA；
- 新增买入/卖出/仓位/收益承诺/胜率/上涨概率语义；
- 新增 POST/PUT/PATCH/DELETE 调用；
- provider refresh/publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / order；
- target position / target weight；
- 修改模型、回放口径或数据源；
- 把 LTR explanation payload 抬升为主推荐或主排序依据。

---

## 8. Phase5S 必做验证

执行者必须至少完成：

1. `python -m pytest backend/tests/test_tw_ltr_readonly_explanation_api.py -q`
2. `node frontend/tests/unit/tw-stock-monitor-static-check.mjs`
3. `corepack pnpm build`
4. 只读 E2E：

```text
TW_STOCK_MONITOR_BASE_URL=<local url> node frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs
```

E2E 必须明确报告：

- `ltr_readonly_explanation_request_count >= 1`
- `forbidden_request_count = 0`
- `sim_write_request_count = 0`
- `quick_trade_request_count = 0`
- `broker_request_count = 0`
- `real_order_request_count = 0`
- `monitor_config_write_count = 0`
- `monitor_scan_post_count = 0`
- `monitor_alerts_write_count = 0`
- `qlib_ops_post_count = 0`
- `accepted_latest_switch_count = 0`
- `provider_publish_refresh_count = 0`
- `target_position_request_count = 0`
- `target_weight_request_count = 0`
- `page_error_count = 0`

---

## 9. Phase5S 页面验收门槛

执行者必须在报告中给出证据说明：

1. LTR 面板标题为用户问题导向，例如“为什么现在不动”；
2. 首屏不出现费用后净值变化、收益率大数字、胜率、上涨概率、仓位；
3. 首屏只保留原因、取舍、角色标签、只读边界；
4. 详情层历史指标必须和动作/换手/回撤取舍同屏；
5. 页面仍优先呈现“今日复盘与历史模拟”，LTR explanation 是辅助解释，不盖过主流程；
6. slot/title/body 结构没有导致工具栏或正文错位；
7. 没有 manual review explanation 面板、测试模式、API 调用或状态残留。

---

## 10. Phase5S 必交付产物

执行者必须提交：

```text
docs/tw_ltr_rerank_regime_turnover/PHASE5S_LTR_ONLY_ACCEPTANCE_EXECUTION_REPORT_CN.md
```

报告必须包含：

1. 本轮目标；
2. 是否修改代码，修改了哪些文件；
3. 若修复 UI 结构，说明具体修复点；
4. manual review explanation 残留搜索结果；
5. 只读安全边界搜索结果；
6. 后端测试结果；
7. 前端静态检查结果；
8. 前端 build 结果；
9. 只读 E2E 结果与关键计数；
10. 是否满足用户第一性原则；
11. 是否建议 Phase5 最终收口。

---

## 11. 若失败如何收尾

如果 Phase5S 发现 UI 结构错位但可以小修：

```text
只修复模板结构和样式，不改语义。
```

如果发现 LTR readonly explanation 仍然让页面变复杂、遮挡主流程或产生误导：

```text
不要继续扩大实现；
回退前端 LTR 面板，只保留后端只读 API 和研究产物，
再回到用户确认是否接受“后台可用但前端暂不展示”。
```

如果发现任何写请求、交易语义、provider/accepted/monitor 越权：

```text
立即停止，不得自行修大范围；
提交问题报告，回到审查者和用户确认。
```
