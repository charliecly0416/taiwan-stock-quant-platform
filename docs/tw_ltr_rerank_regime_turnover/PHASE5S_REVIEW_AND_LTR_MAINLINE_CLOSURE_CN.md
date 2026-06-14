# Phase5S 审查意见与 LTR 主线收口文档

生成时间：2026-06-14

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

审查入口：`docs/tw_ltr_rerank_regime_turnover/PHASE5S_LTR_ONLY_ACCEPTANCE_EXECUTION_REPORT_CN.md`

---

## 1. 审查结论

Phase5S **通过**。

当前 LTR 主线可以收口为：

```text
Phase3C fixed payload
-> LTR readonly explanation service
-> GET /api/tw-stock/ltr-readonly-explanation
-> 前端最小只读展示
-> static check / readonly E2E
```

本轮没有发现：

- manual review explanation 回流；
- 新增第二个 explanation 模块；
- 新模型、新数据源或联网/provider 扩展；
- provider refresh/publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / order；
- target position / target weight；
- 收益承诺、胜率、上涨概率或自动交易语义；
- 将 LTR explanation payload 抬升为主推荐层。

---

## 2. 执行者工作核对

### 2.1 前端结构修复

审查确认：

- `frontend/src/views/tw-stock-monitor/index.vue` 中 `rank-tech-replay-card` 的 `<template slot="title">` 已正确闭合；
- toolbar、只读提示、今日复盘正文、LTR 面板、历史回放区域均处于 card body；
- `readonly-backtest-card`、`qlib-option-c-card` 等后续 card 的 title/body 结构已恢复；
- LTR 面板位于“今日复盘与历史模拟”卡片内，在详细历史回放区域前；
- LTR 面板作为辅助解释，没有替代“今天先看什么”的主流程。

### 2.2 LTR-only 最小接入

保留的新增产品链路符合主线边界：

- `backend/app/services/tw_ltr_readonly_explanation.py`
- `GET /api/tw-stock/ltr-readonly-explanation`
- `frontend/src/api/tw-stock.js` 的 `getTwStockLTRReadonlyExplanation()`
- `frontend/src/views/tw-stock-monitor/index.vue` 的最小 LTR 只读面板
- 后端 API 测试、前端静态检查、只读 E2E

首屏继续只展示：

1. `why_no_action`
2. `tradeoff_summary`
3. `research_role_label`
4. `readonly_disclaimer`

详情层历史指标仍在折叠面板内，没有进入首屏。

---

## 3. Manual Review Explanation 残留审查

审查搜索：

```text
rg -n "manual-review/explanation|TWManualReviewExplanationService|ManualReviewExplanationError|manualReviewReadonlyTestMode|manual-review-readonly-test|manual-review-explanation-panel|getTwStockManualReviewExplanation|tw_manual_review_explanation" backend/app frontend/src frontend/tests backend/tests docs/tw_ltr_rerank_regime_turnover
```

结论：

- `backend/app` 无产品代码残留；
- `frontend/src` 无产品代码残留；
- `frontend/tests` 仅有禁用断言；
- `backend/tests` 无相关误引入测试；
- `docs/tw_ltr_rerank_regime_turnover` 中的命中均为历史审查/执行文档说明。

因此，manual review explanation 已按用户要求回退，不再属于当前产品链路。

---

## 4. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：无实质问题。

说明：

- `broker`、`order`、`target_position`、`target_weight` 等关键词只出现在免责声明、只读 E2E 计数、禁用断言或既有只读历史模拟语境中；
- 未发现实际交易入口、写请求、仓位目标或推荐 CTA；
- `胜率` 等字样出现在既有只读回测/历史模拟区域，不是本轮 LTR 首屏，也未作为未来承诺。

### Network Audit

审查复跑只读 E2E，关键计数：

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

### Console Audit

E2E `page_error_count=0`。

构建输出开头仍有：

```text
/bin/sh: 2: source: not found
```

但 `vite build` 成功完成。该噪声不影响本轮只读验收结论。

### Text / Agent Semantics

LTR 首屏禁止内容由 E2E 覆盖：

- 不展示费用后净值变化；
- 不展示大百分比收益；
- 不展示最大回撤详情；
- 不展示 notional turnover proxy；
- 不展示胜率、上涨概率、目标仓位。

只读边界文案保持：

```text
仅供只读研究复盘，不构成操作建议，不会产生任何真实执行动作。
```

### Verdict

只读安全边界通过。

---

## 5. 审查复跑验证

已复跑：

```text
python -m pytest backend/tests/test_tw_ltr_readonly_explanation_api.py -q
```

结果：

```text
4 passed
```

已复跑：

```text
python -m py_compile backend/app/services/tw_ltr_readonly_explanation.py backend/app/routes/tw_stock.py backend/tests/test_tw_ltr_readonly_explanation_api.py
```

结果：通过。

已复跑：

```text
node frontend/tests/unit/tw-stock-monitor-static-check.mjs
```

结果：

```text
tw-stock-monitor static checks passed
```

说明：该命令在沙箱内仍会因 `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted` 失败；非沙箱复跑通过，属于环境权限限制，不是代码失败。

已复跑：

```text
corepack pnpm build
```

结果：

```text
vite build 通过
```

已复跑：

```text
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8011 node frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs
```

结果：

```text
tw-stock rank-tech portfolio replay readonly e2e passed
```

临时 `127.0.0.1:8011` 静态服务已停止，非沙箱端口检查无监听结果。

---

## 6. 用户第一性原则判断

通过。

### 简单

LTR 面板没有变成新的复杂工作台，只保留“为什么现在不动”的辅助解释。

### 准确

首屏不包装收益、胜率、上涨概率或仓位；详情层历史指标仍保留在折叠区，并带有历史回放语境。

### 清晰

“今日复盘与历史模拟”和“今天先看什么”仍先于 LTR explanation。LTR 面板解释的是不动作原因和历史取舍，不替代主流程。

### 实用

用户可以看到不动作原因、取舍、只读边界；需要深入复盘时可展开详情层。

---

## 7. 收口结论

LTR rerank + regime + turnover 主线在当前实现层面已经完成只读产品收口。

当前可以接受的状态是：

```text
保留 LTR readonly explanation 最小只读接入；
不恢复 manual review explanation；
不继续扩展推荐/交易/写入链路；
不再围绕本主线新增功能分支。
```

---

## 8. 下一步工作文档

本主线不再继续派发新的功能实现轮次。

执行者下一步只允许做收尾性质工作：

1. 保持当前 LTR-only 只读接入；
2. 不新增代码功能；
3. 若需要提交最终整理，只能更新文档：
   - 汇总本主线最终结论；
   - 列出最终保留文件；
   - 列出最终验证命令；
   - 明确 manual review explanation 已回退；
   - 明确未来若要恢复 manual review explanation，必须作为新主线重新由用户确认。

如果执行者要继续提交文档，文件名建议：

```text
docs/tw_ltr_rerank_regime_turnover/LTR_MAINLINE_FINAL_CLOSURE_SUMMARY_CN.md
```

该文档不得包含新实现要求，不得要求继续开发，只能做最终归档。

---

## 9. 后续禁止事项

除非用户重新确认新主线，否则禁止：

- 继续扩展 manual review explanation；
- 增加第二解释模块；
- 把 LTR explanation 放进主推荐、交易建议或仓位建议；
- 接入 provider refresh/publish；
- 切换 accepted latest；
- 写 monitor config / scan / alerts；
- 接入 broker / quick-trade / order；
- 输出 target position / target weight；
- 使用收益、胜率、上涨概率作为用户承诺语义。
