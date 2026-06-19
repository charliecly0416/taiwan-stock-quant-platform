# Phase5 审查意见与 Manual Review 回退工作文档

生成时间：2026-06-14

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

审查入口：`docs/tw_ltr_rerank_regime_turnover/PHASE5_READONLY_INTEGRATION_IMPLEMENTATION_EXECUTION_REPORT_CN.md`

---

## 1. 审查结论

Phase5 本轮**不通过**。

原因不是 `LTR readonly explanation` 这条主线本身失败，而是执行者把 **`manual review explanation`** 这条无关主线混入了本轮实现，已经偏离了当前唯一主线边界。

当前用户决策已明确：

```text
回退 manual review explanation，
只保留 LTR 主线。
```

因此本轮必须先做回退收口，再重新提交仅包含 LTR 主线的最小只读接入实现。

---

## 2. 偏离主线的具体问题

以下改动不属于本轮允许范围，应全部回退：

### 2.1 后端

- `backend/app/routes/tw_stock.py`
  - `TWManualReviewExplanationService` import
  - `manual_review_explanation_service = TWManualReviewExplanationService()`
  - `GET /api/tw-stock/manual-review/explanation`
  - `_manual_review_*` 相关 query/context helper

### 2.2 前端 API

- `frontend/src/api/tw-stock.js`
  - `getTwStockManualReviewExplanation()`

### 2.3 前端页面

- `frontend/src/views/tw-stock-monitor/index.vue`
  - `manualReviewReadonlyTestMode`
  - `manual-review-readonly-test`
  - `manual-review-explanation-panel`
  - `manualReview*` 相关状态、计算属性、方法、样式
  - 任何与 manual review explanation 相关的测试模式、选择器、面板、只读线索 UI

这些内容属于另一条主线，不应与当前 LTR readonly explanation 接入混做。

---

## 3. 为什么不纳入当前主线

### 3.1 不符合当前唯一主线边界

当前唯一主线是：

```text
LTR readonly explanation
-> 最小真实只读接入
```

而不是：

```text
LTR readonly explanation + manual review explanation 双线并行接入
```

### 3.2 不符合用户第一性原则

当前最重要的用户问题是：

1. 为什么现在不动；
2. 这套研究方法的取舍是什么；
3. 当前结果只是只读研究，不是操作建议。

`manual review explanation` 会额外引入：

- 更多状态；
- 更多线索；
- 更多补充说明；
- 更多术语。

这会明显增加认知负担，把页面重新拉向“研究面板化”，收益不够大。

### 3.3 当前增益证据不足

如果要接纳 `manual review explanation`，至少要先证明：

- 它显著提升用户理解；
- 它不会挤占 LTR 主线展示；
- 它不会破坏“简单、准确、清晰、实用”。

当前没有这些证据，因此不接受并入本轮。

---

## 4. 允许保留的内容

本轮允许保留并重新提交的内容，仅限以下 LTR 主线改动：

### 4.1 后端

- `backend/app/services/tw_ltr_readonly_explanation.py`
- `backend/app/routes/tw_stock.py`
  - 仅保留：
    `GET /api/tw-stock/ltr-readonly-explanation`

### 4.2 前端

- `frontend/src/api/tw-stock.js`
  - 仅保留：
    `getTwStockLTRReadonlyExplanation()`

- `frontend/src/views/tw-stock-monitor/index.vue`
  - 仅保留 LTR readonly explanation 最小只读面板
  - 必须符合 Phase4B 已冻结契约：
    1. `why_no_action`
    2. `tradeoff_summary`
    3. `research_role_label`
    4. `readonly_disclaimer`
  - 详情层仅展示受约束历史回放指标

### 4.3 测试

- `backend/tests/test_tw_ltr_readonly_explanation_api.py`
- `frontend/tests/unit/tw-stock-monitor-static-check.mjs`
  - 仅保留与 LTR readonly explanation 有关的断言
- `frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs`
  - 仅保留与 LTR readonly explanation 只读接入有关的检查

---

## 5. 回退要求

执行者下一轮必须先完成：

```text
回退所有 manual review explanation 相关改动，
然后重新提交一版仅包含 LTR 主线的 Phase5 实现。
```

### 必须回退的范围

1. 后端 route 中的 manual review explanation 入口与 helper；
2. 前端 API 中的 manual review explanation 调用；
3. 前端页面中的 manual review 面板、测试模式、状态、方法与样式；
4. 任意与 manual review explanation 相关的测试或静态检查断言。

### 禁止“名义回退，实际残留”

不允许：

- route 删了，但 helper 还在；
- UI 删了，但状态/方法/样式还在；
- API 删了，但测试仍引用；
- 通过条件分支把 manual review 藏起来但不真正删除。

回退后必须能明确证明：

```text
当前产品链路只剩 LTR readonly explanation 一条新增主线。
```

---

## 6. Phase5R 本轮唯一目标

只做一件事：

```text
回退 manual review explanation，
保留并验证 LTR readonly explanation 的最小只读接入。
```

本轮仍然不允许：

- 推荐层；
- 交易层；
- 新数据源；
- provider / accepted / monitor 写入；
- 任何主线外解释模块。

---

## 7. 必做验证

执行者必须至少验证：

1. `manual review explanation` 相关 route/API/UI/状态/方法/样式已全部移除；
2. 代码搜索不再命中：
   - `manual-review/explanation`
   - `TWManualReviewExplanationService`
   - `manualReviewReadonlyTestMode`
   - `manual-review-readonly-test`
   - `manual-review-explanation-panel`
   - `getTwStockManualReviewExplanation`
3. `GET /api/tw-stock/ltr-readonly-explanation` 仍正常；
4. 前端仍只展示 4 个首屏信息单元；
5. 详情层仍满足 Phase4B 展示契约；
6. 只读 E2E 仍通过；
7. 无写请求、无状态变更、无危险文案。

---

## 8. 禁止事项

本轮禁止：

- 保留任何 manual review explanation 残留实现；
- 把 manual review 改名后继续混在本轮；
- 新增第二个 explanation 模块；
- 扩写到推荐层或交易层；
- provider refresh / publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / order；
- 目标仓位 / 目标权重；
- 收益承诺 / 胜率 / 上涨概率。

---

## 9. 验收门槛

Phase5R 通过的最低门槛：

1. manual review explanation 相关改动已完全回退；
2. LTR readonly explanation 最小只读接入仍然完整可用；
3. 前后端与测试范围重新收窄到当前唯一主线；
4. 只读 E2E 通过；
5. 无主线偏移、无越权、无危险语义。

只有在这一版通过后，才继续按 LTR 主线往下审查。

---

## 10. 执行报告要求

执行者下一轮报告固定写入：

```text
docs/tw_ltr_rerank_regime_turnover/PHASE5R_LTR_ONLY_ROLLBACK_EXECUTION_REPORT_CN.md
```

报告必须包含：

1. 本轮目标；
2. 实际回退文件清单；
3. 保留的 LTR 主线文件清单；
4. 代码搜索验证结果；
5. 后端接口验证结果；
6. 前端静态检查结果；
7. 只读 E2E 结果；
8. 安全边界声明；
9. 是否达到“仅保留 LTR 主线”的收口门槛。
