# Phase R8 执行报告：Manual Review 上下文字段映射设计

- 执行日期：2026-06-12
- 当前阶段：Phase R8
- recommended_gate：`request_phaser9_context_mapping_implementation`

## 1. 当前阶段目标

本阶段只设计 manual-review 上下文字段映射合同，盘点现有只读 API、service 和前端上下文已经能提供哪些字段，以及这些字段应进入主线索、详情、数据提示或暂缓。

本阶段不实现代码。

## 2. 阅读材料

已阅读：

- `docs/TW_STOCK_MANUAL_REVIEW_EXPLANATION_NEXT_ROUND_PLAN_CN.md`
- `docs/tw_manual_review_explanation/NEXT_ROUND_EXECUTOR_PROMPT_CN.md`
- `docs/tw_manual_review_explanation/PHASER7_REVIEW_AND_PHASER8_WORK_CN.md`
- `docs/tw_manual_review_explanation/PHASER7_EXECUTION_REPORT_CN.md`
- `docs/tw_manual_review_explanation/manual_review_explanation_contract.md`
- `backend/app/services/tw_manual_review_explanation.py`
- `backend/app/routes/tw_stock.py`
- `backend/app/services/tw_stock_rank_tech_cross.py`
- `backend/app/services/tw_stock_technical_status.py`
- `backend/app/services/tw_stock_cross_analysis.py`
- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/src/api/tw-stock.js`
- `backend/tests/test_tw_manual_review_explanation.py`
- `backend/tests/test_tw_manual_review_explanation_api.py`
- `frontend/tests/unit/tw-stock-manual-review-explanation-check.mjs`

## 3. 新增/修改文件清单

新增文档：

- `docs/tw_manual_review_explanation/manual_review_context_mapping_contract.md`
- `docs/tw_manual_review_explanation/PHASER8_EXECUTION_REPORT_CN.md`

代码修改：无。

测试修改：无。

API/route 修改：无。

数据文件修改：无。

## 4. 字段映射合同摘要

本轮合同明确：

- `rank-tech-cross/latest` 是当前最完整的现有只读上下文来源，已包含 qlib、trend、technical、positionRisk、warnings。
- 当前 `manual-review/explanation` 已支持 query 传入 rank、rankTier、trendLabel、trendScore、technicalStatus、positionStatus、pricePercentile120d、rsi14、return5dPct、frozenRules。
- 当前前端 `buildManualReviewParams()` 只传入 symbol、name、asof、rank、rankTier、trendLabel、trendScore，尚未把 technical、positionRisk、data_quality_warnings 等完整字段传给 manual-review。
- 冻结规则卡服务内已有 rule id 到用户文案的安全转译，但前端当前没有真实规则卡上下文来源。
- qlib rank change 已有只读 API，但当前 manual-review 没有单标的映射链路，建议暂缓。

## 5. 可进入 R9 的字段

建议 R9 优先实现：

- qlib rank / rank_tier。
- qlib score 进入详情，不进默认主线索。
- trend label / trend score。
- trend latest_date 进入详情或数据提示。
- technical status。
- technical summary。
- MA / RSI / MACD / Bollinger 的 state 和 reason，进入详情。
- positionRisk status / label / reason。
- positionRisk metrics 中少量关键项：price_percentile_120d、distance_ma20_pct、rsi14、bollinger_position、return_5d_pct、return_20d_pct。
- data_quality_warnings。

R9 最小实现应保持：

- 主线索最多 3 条。
- 详情最多 5 条。
- 后端白名单抽取，不把原始 item 整包透传给用户。

## 6. 暂缓字段及原因

暂缓：

- qlib rank change：已有 `GET /api/tw-stock/quant/signals/rank-changes`，但需要设计单标的匹配和前端传参方式，避免 R9 首版变复杂。
- ret5 / ret20 / ret60：计划中要求，但当前 manual-review/rank-tech item 未稳定暴露完整 returns；只在部分前端趋势上下文中看到 `ret_5d`。
- cross category / alignment：已有 `cross-analysis` 只读来源，但容易与 manual-review 主线重叠，建议等基础映射稳定后再接。
- 冻结法人/融资融券规则卡真实来源：service 已有转译表，但当前前端没有真实规则卡上下文来源；R9 可继续支持显式传入，不应新增来源。
- decision/actionPlan raw code：容易被误读为动作建议，不建议进入用户可见文案；如未来使用，只能后端转译为复盘状态。

## 7. 验证命令

本阶段为 doc-only，未运行前端、后端、Playwright 或 build。

已执行只读检查：

- `sed -n` 阅读 R8 必读文档、service、route、前端和测试文件。
- `rg -n` 检索 manual-review、rank-tech、cross-analysis、technical、positionRisk、warnings 等字段来源。

## 8. 用户第一性原则自查

- 简单：字段分为主线索、详情、数据提示和暂缓，避免把所有字段堆给用户。
- 准确：所有建议字段均来自现有只读 API/service/front-end context，不新增数据源。
- 清晰：每个字段写明来源、是否已有、是否只读、缺失 fallback 和 R9 建议。
- 实用：R9 可按合同做最小实现，不需要重新判断字段边界。

## 9. 安全边界自查

本轮没有触发或实现：

- 新数据源。
- 联网或 token。
- 数据刷新或补数据。
- 模型训练。
- qlib provider 写入。
- provider refresh/publish。
- accepted latest switching。
- monitor config 保存。
- monitor scan 或 scan-all。
- alerts 写入。
- broker、quick-trade、orders。
- target position 或 target weight。
- 买入、卖出、持有建议。
- 仓位建议、收益承诺、上涨概率或胜率承诺。

文档中出现相关词，仅用于禁止事项、字段限制和安全边界说明。

## 10. 是否偏离主线 / 是否新增分支

未偏离主线。

未新增分支。

本轮只围绕审查者授权的“完整上下文字段映射设计”展开，没有进入代码实现、新数据源、模型、provider、monitor 或交易路径。

## 11. 风险与待审查问题

- R9 若从前端传入 nested object，需要决定 query 参数还是请求体；由于当前 API 是 GET，建议继续用 GET query 或只传白名单扁平字段，不能新增业务 API，除非审查者另行授权。
- `rank-tech-cross/latest` 中存在 `decision` 和 `actionPlan`，字段名容易带动作含义；本合同建议暂缓直接映射。
- `qlib_score` 和 trend score 容易被误读为概率或收益，需要在 R9 测试中继续扫描禁止语义。
- ret5/ret20/ret60 当前来源不够稳定，暂缓可以避免为了字段完整而扩大范围。

## 12. 给审查者的结论

R8 已完成 doc-only 字段映射合同设计。

建议进入下一阶段：

`request_phaser9_context_mapping_implementation`

