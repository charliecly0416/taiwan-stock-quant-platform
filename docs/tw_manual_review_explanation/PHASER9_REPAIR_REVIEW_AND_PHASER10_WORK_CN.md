# Phase R9 Repair 审查结论与 Phase R10 工作文档

审查日期：2026-06-12

审查入口：

- `docs/tw_manual_review_explanation/PHASER9_REPAIR_EXECUTION_REPORT_CN.md`
- `docs/tw_manual_review_explanation/PHASER9_REVIEW_AND_REPAIR_WORK_CN.md`
- `backend/app/services/tw_manual_review_explanation.py`
- `backend/tests/test_tw_manual_review_explanation.py`
- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/tests/e2e/tw-stock-manual-review-readonly.mjs`
- `frontend/tests/unit/tw-stock-manual-review-explanation-check.mjs`
- `data_tw/ops/manual_review_readonly_e2e/phase_r9_repair/summary.json`
- `data_tw/ops/manual_review_readonly_e2e/phase_r9_repair/network_audit.json`
- `data_tw/ops/manual_review_readonly_e2e/phase_r9_repair/console_audit.json`
- 台股只读安全边界审查规则

## 1. 本步审核结论

Phase R9 Repair 通过。

接受 gate：

`manual_review_context_mapping_implementation_passed`

R9 审查指出的两个 P1 问题均已修复：

- 后端已识别 `technical_strong`、`technical_weak`、`technical_neutral`、`technical_data_insufficient`。
- 前端已在 manual-review 展开区展示 `details`，标题为 `补充线索`。

本轮未发现范围越权：

- 未新增 API。
- 未新增 route。
- 未新增数据源。
- 未联网拉取真实资料。
- 未使用 token。
- 未训练模型。
- 未 provider refresh/publish。
- 未 accepted latest switching。
- 未 monitor config save、monitor scan、alerts write。
- 未接 broker、quick-trade、orders。
- 未新增 portfolio replay POST。
- 未接 cross-analysis 或 rank-change 新数据流。
- 未接冻结规则卡真实来源。
- 未映射 decision/actionPlan raw code。
- 未输出买卖、仓位、收益承诺、上涨概率或胜率语义。

## 2. 修复项复核

### 2.1 技术状态枚举

通过。

`TWManualReviewExplanationService.explain()` 已将 `technical_state` 规范为小写，并识别：

- `technical_strong` -> `技术状态偏支持`
- `technical_weak` -> `技术状态转弱`
- `technical_neutral` -> `技术状态中性`
- `technical_data_insufficient` -> `技术状态资料不足。`

测试 `test_rank_tech_technical_status_enums_are_recognized()` 覆盖了四个枚举，并确认 `technical_strong` 不再产生 `缺少技术状态。`。

### 2.2 Details 展示

通过。

前端新增 `manualReviewDetails`：

- 只读取 `manualReviewExplanation.details`。
- 最多展示 5 条。
- 只保留 `label` 与 `message`。
- 不展示 `source`、raw id、provider、gate、run id、IC、RankIC、decision/actionPlan。

默认面板和 test-only 面板均展示 `补充线索`。

R9 Repair browser 文本摘要包含：

- `补充线索`
- `研究排序分数`
- `趋势资料`
- `位置指标`

## 3. 浏览器 / Network 审查

R9 Repair artifact 显示：

- `manual_review_get_count=1`
- `forbidden_request_count=0`
- `portfolio_replay_post_count=0`
- `monitor_config_write_count=0`
- `monitor_scan_post_count=0`
- `monitor_alerts_write_count=0`
- `provider_or_accepted_latest_write_count=0`
- `broker_quick_trade_order_count=0`
- `unsafe_trading_semantics_count=0`
- `disallowed_api_request_count=0`
- `console_issue_count=0`
- `page_error_count=0`
- `failed_response_count=0`

`network_audit.json` 中 manual-review 仍为 GET 请求，且 query 中包含 R9 白名单字段。未发现台股业务 POST/PUT/PATCH/DELETE。

浏览器 smoke 仍使用 manual-review GET mock response，主要证明前端 query、渲染和 network 安全；后端真实 details 生成由后端单测/API 测试覆盖。该组合可接受。

## 4. 用户第一性原则审查

通过。

- 简单：默认主线索仍最多 3 条，补充线索放在展开区。
- 准确：rank-tech 技术状态枚举不再误判为缺失。
- 清晰：用户能看到主线索、下一步看什么、数据提示和补充线索。
- 实用：qlib score、趋势日期、位置指标以解释性方式呈现，不作为交易判断。

## 5. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：无阻塞项。

### Network Audit

通过。危险请求计数为 0。

### Console Audit

通过。无 console issue，无 page error。

### Text / Agent Semantics

通过。页面文本中的 `研究排序分数`、`趋势强弱分`、`位置风险复盘线索` 为研究解释语义，不构成买卖、仓位、收益或概率承诺。

### Verdict

只读研究安全边界通过。

## 6. 必须修复项

当前无必须修复项。

## 7. 可暂缓项

继续暂缓：

- qlib rank change。
- ret60。
- cross category / alignment。
- 冻结法人/融资融券规则卡真实来源。
- decision/actionPlan raw code。
- 新 API 或新 route。
- 新数据源。

这些不得在 R10 收口中顺手实现。

## 8. 是否需要用户确认

不需要。

R9 Repair 已完成既定修复。下一步应进入 R10 最终只读验收与收口，不再新增功能。

## 9. 给执行者的下一步工作文档

### Phase R10：最终只读验收与收口

你是执行者。本轮只做最终验收和交接收口，不新增功能。

#### 目标

确认人工复盘解释模块后续增强已完整收口：

- R7 浏览器只读入口可复跑。
- R9 字段映射增强可用。
- 后端 contract、安全语义和测试通过。
- 前端显示简单、准确、清晰、实用。
- network 无危险请求。
- 更新用户/开发者交接摘要。

#### 允许修改

允许新增或更新文档：

- `docs/tw_manual_review_explanation/PHASER10_FINAL_ACCEPTANCE_REPORT_CN.md`
- `docs/tw_manual_review_explanation/MANUAL_REVIEW_EXPLANATION_HANDOFF_CN.md`

允许仅在发现文档索引错误时修正文档链接。

除非验收发现阻塞问题，不要修改业务代码、测试代码、API、前端 UI 或数据文件。

#### 禁止事项

R10 禁止：

- 新增功能。
- 新增 API。
- 新增 route。
- 新增页面或产品入口。
- 新增数据源。
- 联网、token、拉取数据或补数据。
- 训练模型。
- provider refresh/publish。
- accepted latest switching。
- materialize 到 qlib。
- monitor config save。
- monitor scan 或 scan-all。
- alerts write。
- broker、quick-trade、orders。
- portfolio replay 新调用。
- cross-analysis 新接入。
- rank change 新接入。
- 冻结规则卡真实来源新接入。
- decision/actionPlan raw code 映射。
- 买入、卖出、持有建议。
- 仓位建议、收益承诺、上涨概率或胜率承诺。

#### 必跑验证

至少执行：

- `python -m py_compile backend/app/routes/tw_stock.py backend/app/services/tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation_api.py`
- `python -m pytest backend/tests/test_tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation_api.py -q`
- `node frontend/tests/unit/tw-stock-manual-review-explanation-check.mjs`
- `node frontend/tests/unit/tw-stock-monitor-static-check.mjs`
- `node --check frontend/tests/e2e/tw-stock-manual-review-readonly.mjs`
- R7/R9 Playwright readonly smoke
- `corepack pnpm build`，工作目录 `frontend`

Playwright smoke 必须继续满足：

- `forbidden_request_count=0`
- `manual_review_get_count>=1`
- `portfolio_replay_post_count=0`
- `monitor_config_write_count=0`
- `monitor_scan_post_count=0`
- `monitor_alerts_write_count=0`
- `provider_or_accepted_latest_write_count=0`
- `broker_quick_trade_order_count=0`
- `unsafe_trading_semantics_count=0`

#### R10 报告要求

新增：

- `docs/tw_manual_review_explanation/PHASER10_FINAL_ACCEPTANCE_REPORT_CN.md`

报告必须包含：

- 当前最终状态。
- 验证命令与结果。
- browser artifact 路径。
- network / console 摘要。
- 页面文本摘要。
- 用户第一性原则自查。
- 安全边界自查。
- 已完成能力。
- 仍然暂缓的能力。
- 是否新增任何业务功能；预期答案为否。
- 是否新增 API/route/data source；预期答案为否。
- 推荐 gate。

#### Handoff 更新要求

更新：

- `docs/tw_manual_review_explanation/MANUAL_REVIEW_EXPLANATION_HANDOFF_CN.md`

必须说明：

- 用户入口仍是 `/tw-stock-monitor` 的 `复盘线索`。
- 用户能看到摘要、主线索、下一步复盘、数据提示、补充线索。
- 模块不是买卖建议、仓位建议、收益预测或概率预测。
- 当前补充线索来自已有只读上下文。
- 暂缓项：rank change、cross-analysis 新接入、冻结规则真实来源、decision/actionPlan raw code、新数据源、模型训练、provider/monitor/交易路径。

#### R10 Gate

R10 通过时建议 gate：

`manual_review_explanation_next_round_final_acceptance_passed`

R10 需要修复时：

`phaser10_final_acceptance_needs_repair`

如发现范围越权：

`stop_manual_review_next_round_scope_invalid`
