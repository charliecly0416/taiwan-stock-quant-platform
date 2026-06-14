# Phase R9 审查结论与修复工作文档

审查日期：2026-06-12

审查入口：

- `docs/tw_manual_review_explanation/PHASER9_EXECUTION_REPORT_CN.md`
- `docs/tw_manual_review_explanation/PHASER8_REVIEW_AND_PHASER9_WORK_CN.md`
- `backend/app/services/tw_manual_review_explanation.py`
- `backend/app/routes/tw_stock.py`
- `backend/tests/test_tw_manual_review_explanation.py`
- `backend/tests/test_tw_manual_review_explanation_api.py`
- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/tests/e2e/tw-stock-manual-review-readonly.mjs`
- `data_tw/ops/manual_review_readonly_e2e/phase_r9/summary.json`
- `data_tw/ops/manual_review_readonly_e2e/phase_r9/network_audit.json`
- `data_tw/ops/manual_review_readonly_e2e/phase_r9/console_audit.json`
- 台股只读安全边界审查规则

## 1. 本步审核结论

Phase R9 暂不通过，需要小修。

当前 gate：

`phaser9_context_mapping_implementation_needs_repair`

R9 没有触发必须叫停的范围越权：

- 未新增 API 或 route。
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
- 未使用 decision/actionPlan raw code。
- 未输出买卖、仓位、收益、上涨概率或胜率语义。

但 R9 有两个影响“准确、清晰、实用”的必须修复项，修完后再复审。

## 2. 必须修复项

### P1：后端未识别 rank-tech 现有技术状态枚举

位置：

- `backend/app/services/tw_manual_review_explanation.py`
- `TWManualReviewExplanationService.explain()`
- `technical_state` 分支

问题：

R9 从 `rank-tech-cross/latest` 传入的技术状态是现有字段：

- `technical_strong`
- `technical_neutral`
- `technical_weak`
- `technical_data_insufficient`

但 service 当前只把以下值识别为有效技术状态：

- 支持：`supportive` / `strong` / `bullish`
- 谨慎：`caution` / `weak` / `bearish`
- 中性：`neutral` / `mixed`

因此 R9 新接入的 `technicalStatus=technical_strong` 会被当成缺失，进入 `data_quality_notes` 的“缺少技术状态”。这会导致用户看到的解释与真实上下文不一致。

修复要求：

- 把 `technical_strong` 识别为技术状态偏支持。
- 把 `technical_weak` 识别为技术状态转弱或偏谨慎。
- 把 `technical_neutral` 识别为技术状态中性。
- 把 `technical_data_insufficient` 识别为数据不足，不应误判为未知普通缺失。
- 增加后端测试，直接覆盖这四个枚举。

### P1：前端没有展示 R9 新增 `details`

位置：

- `frontend/src/views/tw-stock-monitor/index.vue`
- manual-review 面板与 test-only 面板

问题：

R9 后端新增了 `details`，并声称 qlib score、趋势日期、技术策略、位置指标进入 details。但前端当前 manual-review 面板只展示：

- summary
- signals
- next_review_focus
- data_quality_notes

没有展示 `manualReviewExplanation.details`。因此 R9 最重要的“上下文字段增强”对用户不可见，只是进入 API response 或 E2E mock fixture。

修复要求：

- 在展开区中增加一个简洁的“补充线索”或同等名称区块。
- 最多展示 5 条 `details`。
- 每条只展示 `label` 与 `message`，不要展示 raw source、raw id、run id、provider、gate、IC、RankIC。
- test-only 面板和默认面板应复用同一展示逻辑，避免一边有 details 一边没有。
- 增加前端静态检查或 E2E 断言，确认 details 文案能出现在页面文本中。

## 3. 主线一致性审查

R9 总体仍在主线内。

通过项：

- 后端只扩展 existing GET route 的 query 白名单解析。
- 前端只从已有 `qlibSignals` 与 `rankTechItems` 中组装上下文。
- R9 browser network 仍为 manual-review GET + 静态资源/壳层只读 GET。
- 未新增 cross-analysis、rank-change 或新数据流。
- 未接 decision/actionPlan raw code。

需要修复后再通过的原因不是范围越权，而是增强字段没有被准确识别和有效展示。

## 4. 浏览器 / Network 审查

R9 browser smoke artifact 显示：

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

network 通过。

R9 GET query 已包含新增白名单字段，例如：

- `qlibScore`
- `trendLatestDate`
- `technicalStatus`
- `technicalSummary`
- `technicalStrategiesDetail`
- `positionStatus`
- `positionLabel`
- `distanceMa20Pct`
- `distanceMa60Pct`
- `bollingerPosition`
- `return20dPct`
- `dataQualityWarnings`

但当前 Playwright 对 manual-review GET 使用 fixture/mock response，页面文本不能证明真实后端新 details 被展示。修复后 E2E 应至少断言 fixture 中 details 的一条安全文案出现在面板文本里。

## 5. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：R9 页面 smoke 使用 mock response，能证明 query 与 network 安全，但不能证明真实后端 details 在浏览器展示；修复时补断言即可。

### Network Audit

通过。危险请求计数为 0。

### Console Audit

通过。无 console issue，无 page error。

### Text / Agent Semantics

未发现 actionable 买卖/仓位/收益/概率语义。

### Verdict

只读安全边界通过，但 R9 功能验收需修复后再通过。

## 6. 用户第一性原则审查

R9 当前不完全通过：

- 简单：主线索数量仍受控，方向正确。
- 准确：`technical_strong` 被误判为缺少技术状态，不准确。
- 清晰：新增 details 未展示，用户看不到新增上下文。
- 实用：query 传了字段，但页面没有把补充线索呈现出来，实用性不足。

## 7. 可暂缓项

继续暂缓，不得在修复中顺手实现：

- qlib rank change。
- ret60。
- cross category / alignment。
- 冻结法人/融资融券规则卡真实来源。
- decision/actionPlan raw code。
- 新 API 或新 route。
- 新数据源。

## 8. 是否需要用户确认

不需要。

这是 R9 授权范围内的小修，不涉及新方向或越权能力。

## 9. 给执行者的修复工作文档

### Phase R9 Repair：修复技术状态识别与 details 展示

你是执行者。本轮只允许修复 R9 审查指出的两个问题。

#### 修复目标

1. 后端正确识别 rank-tech 现有技术状态枚举。
2. 前端展示 R9 新增的 `details`，但保持简洁、安全、只读。

#### 允许修改

允许修改：

- `backend/app/services/tw_manual_review_explanation.py`
- `backend/tests/test_tw_manual_review_explanation.py`
- `backend/tests/test_tw_manual_review_explanation_api.py`
- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/tests/unit/tw-stock-manual-review-explanation-check.mjs`
- `frontend/tests/e2e/tw-stock-manual-review-readonly.mjs`
- `docs/tw_manual_review_explanation/PHASER9_REPAIR_EXECUTION_REPORT_CN.md`

除非静态检查必须同步，否则不要修改其他文件。

#### 后端修复要求

在 service 中识别：

- `technical_strong` -> 技术状态偏支持。
- `technical_weak` -> 技术状态偏谨慎/转弱。
- `technical_neutral` -> 技术状态中性。
- `technical_data_insufficient` -> 技术数据不足，进入数据提示或 data_quality 逻辑。

测试要求：

- 增加或更新后端测试，覆盖这四个枚举。
- 确认 `technical_strong` 不再产生“缺少技术状态”。
- 确认 `technical_data_insufficient` 仍安全降级，不输出交易语义。

#### 前端修复要求

新增 computed：

- `manualReviewDetails`

要求：

- 只读取 `manualReviewExplanation.details`。
- 最多返回 5 条。
- 每条只展示 `label` 和 `message`。
- 不展示 `source`。
- 不展示 raw id、provider、gate、run id、IC、RankIC、decision/actionPlan。

在 manual-review 展开区中增加简洁展示：

- 建议标题：`补充线索`
- 与 `下一步看什么`、`数据提示` 同级或相邻。
- test-only 面板和默认面板都应可展示同一 details。

测试要求：

- E2E fixture 中已有 details，可断言页面文本包含：
  - `研究排序分数`
  - `趋势资料`
  - `位置指标`
- 静态检查继续禁止买卖、仓位、收益承诺、上涨概率、胜率等语义。

#### 禁止事项

本轮禁止：

- 新增 API。
- 新增 route。
- 新增数据源。
- 联网、token、拉取数据或补数据。
- 训练模型。
- provider refresh/publish。
- accepted latest switching。
- monitor config save、monitor scan、alerts write。
- broker、quick-trade、orders。
- portfolio replay POST。
- cross-analysis 接入。
- rank change 接入。
- 冻结规则卡真实来源接入。
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
- 如前端改动影响 build，执行 `corepack pnpm build`，工作目录 `frontend`

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

#### 修复报告要求

新增：

- `docs/tw_manual_review_explanation/PHASER9_REPAIR_EXECUTION_REPORT_CN.md`

报告必须包含：

- 修复文件清单。
- 后端技术状态枚举修复说明。
- details 前端展示说明。
- 验证命令与结果。
- browser network/console artifact 路径。
- 页面文本摘要，必须包含至少一条 details 文案。
- 安全边界自查。
- 是否新增 API/route/data source。
- 推荐 gate。

#### Repair Gate

修复通过建议 gate：

`manual_review_context_mapping_implementation_passed`

仍需修复：

`phaser9_context_mapping_implementation_needs_repair`

如发现范围越权：

`stop_manual_review_next_round_scope_invalid`
