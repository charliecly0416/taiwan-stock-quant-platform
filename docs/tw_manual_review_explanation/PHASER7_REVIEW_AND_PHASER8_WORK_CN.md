# Phase R7 审查结论与 Phase R8 工作文档

审查日期：2026-06-12

审查入口：

- `docs/tw_manual_review_explanation/PHASER7_EXECUTION_REPORT_CN.md`
- `docs/tw_manual_review_explanation/PHASER6_REVIEW_AND_PHASER7_WORK_CN.md`
- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/tests/e2e/tw-stock-manual-review-readonly.mjs`
- `data_tw/ops/manual_review_readonly_e2e/phase_r7/summary.json`
- `data_tw/ops/manual_review_readonly_e2e/phase_r7/network_audit.json`
- `data_tw/ops/manual_review_readonly_e2e/phase_r7/console_audit.json`
- 台股只读安全边界审查规则

## 1. 本步审核结论

Phase R7 通过。

接受 gate：

`manual_review_browser_readonly_acceptance_passed`

执行者完成了 R7 授权范围内的最小浏览器只读验收：

- 在 `/tw-stock-monitor` 增加测试专用 query flag：`manual_review_readonly=1` / `manualReviewReadonly=true`。
- 默认 `/tw-stock-monitor` 无 query flag 时仍走原 mounted 流程。
- 测试模式只挂载 manual-review 最小区块。
- 新增 Playwright readonly smoke。
- 生成 network、console、summary、screenshot artifact。
- network 计数满足 R7 gate。

本轮未发现需要叫停的问题。

## 2. 主线一致性审查

R7 没有偏离主线，也没有新增业务分支。

符合项：

- 只解决 R5/R6 留下的浏览器只读验收入口问题。
- 没有新增后端 route。
- 没有新增业务 API。
- 没有新增用户导航入口。
- 没有实现上下文字段映射。
- 没有新增数据源。
- 没有训练模型。
- 没有 provider refresh/publish。
- 没有 accepted latest switching。
- 没有 monitor config save、monitor scan、alerts write。
- 没有 broker、quick-trade、orders。
- 没有 target position / target weight。
- 没有买卖、仓位、收益、上涨概率或胜率语义。

测试 query flag 是可访问的前端分支，但不进入导航，不改变默认页面行为，且仅用于只读验收。该点不阻塞 R7；后续不得把它包装成用户可见的新产品入口或调试台。

## 3. 浏览器 / Network 审查

R7 artifact 显示：

- `request_count=21`
- `forbidden_request_count=0`
- `manual_review_get_count=1`
- `portfolio_replay_post_count=0`
- `monitor_config_write_count=0`
- `monitor_scan_post_count=0`
- `monitor_alerts_write_count=0`
- `provider_or_accepted_latest_write_count=0`
- `broker_quick_trade_order_count=0`
- `unsafe_trading_semantics_count=0`
- `disallowed_api_request_count=0`
- `failed_response_count=0`
- `external_static_mock_count=5`

`network_audit.json` 中只有：

- 本地静态资源 GET。
- 应用壳层只读 GET：auth info、brand config、broker-market policy、notification unread-count。
- `GET /api/tw-stock/manual-review/explanation`。
- 外部静态 SVG/Iconify GET，已由 Playwright route fulfill 本地返回。

没有发现：

- `POST /api/tw-stock/rank-tech-cross/portfolio-replay`
- monitor 写请求。
- provider/accepted latest 请求。
- broker/quick-trade/orders 请求。
- 其他台股业务 POST/PUT/PATCH/DELETE。

危险请求“发出即失败”的计数逻辑已在 Playwright `request` 事件中实现，不是单纯拦截后忽略。

## 4. Console / Screenshot 审查

`console_audit.json` 显示：

- `consoleMessages=[]`
- `consoleIssues=[]`
- `pageErrors=[]`

截图文件存在：

- `data_tw/ops/manual_review_readonly_e2e/phase_r7/manual_review_readonly.png`

本次审查环境中图片查看 helper 因 `bwrap: loopback: Failed RTM_NEWADDR` 无法打开截图；但文件存在，且页面文本摘要、Playwright 断言、network artifact 与 console artifact 足以支持 R7 结论。

页面文本摘要未出现买卖、仓位、收益、上涨概率或胜率承诺。

## 5. 用户第一性原则审查

通过。

- 简单：测试模式只显示 manual-review 最小区块，避免整页链路噪音。
- 准确：浏览器请求被完整记录，关键计数字段明确。
- 清晰：报告说明了测试 URL、服务方式、artifact 路径和环境问题。
- 实用：后续可以稳定复跑 manual-review 浏览器只读验收。

R7 没有为了验收把页面变成字段堆叠或复杂调试台。

## 6. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：R7 报告的“修改文件清单”未列出 `frontend/tests/unit/tw-stock-monitor-static-check.mjs`，但当前工作区显示该文件有改动。考虑工作区长期存在未提交变更，暂不认定为 R7 越权；后续报告需要明确该文件改动归属。

### Network Audit

通过。危险请求计数均为 0。

### Console Audit

通过。无 console issue，无 page error。

### Text / Agent Semantics

通过。R7 页面文本和报告中的危险词仅用于安全边界、否定说明或历史模拟上下文，不构成交易建议或动作入口。

### Verdict

只读研究安全边界通过。

## 7. 必须修复项

当前无必须修复项。

## 8. 可暂缓项

- 外部静态资源 URL 仍由应用壳层发出，R7 通过 Playwright route fulfill 本地返回。它不是台股业务 API，也不涉及数据源、provider、monitor 或交易路径；可暂缓，不作为 R7 阻塞项。
- `frontend/tests/unit/tw-stock-monitor-static-check.mjs` 当前有工作区改动，但 R7 报告未列入。下一轮如执行者继续修改或引用该检查，应补充说明归属。
- R7 使用 build 后静态服务绕过 Vite watcher `ENOSPC`，做法合理。环境问题可暂缓。

## 9. 是否需要用户确认

不需要。

R7 已完成浏览器只读验收主线。下一步按既定计划进入 R8，但 R8 只能做上下文字段映射设计，不允许直接实现。

## 10. 给执行者的下一步工作文档

### Phase R8：完整上下文字段映射设计

你是执行者。本轮只允许设计 manual-review 上下文字段映射合同，不实现代码。

#### 目标

盘点现有只读 API、service、前端上下文已经能提供哪些字段，并设计字段如何进入 manual-review explanation。

R8 只回答：

- 哪些字段已经存在。
- 字段来自哪里。
- 是否是只读。
- 是否已经在当前前端/API/service 中可达。
- 字段应进入主线索、详情、数据提示，还是暂缓。
- 哪些字段禁止进入用户可见文案。

R8 不实现映射。

#### 必读材料

必须阅读：

- `docs/TW_STOCK_MANUAL_REVIEW_EXPLANATION_NEXT_ROUND_PLAN_CN.md`
- `docs/tw_manual_review_explanation/PHASER7_REVIEW_AND_PHASER8_WORK_CN.md`
- `docs/tw_manual_review_explanation/manual_review_explanation_contract.md`
- `backend/app/services/tw_manual_review_explanation.py`
- `backend/app/routes/tw_stock.py`
- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/src/api/tw-stock.js`
- 现有 manual-review 后端与前端测试。

#### 允许范围

允许：

- 只读盘点现有字段。
- 设计字段映射表。
- 设计主线索、详情、数据提示和暂缓规则。
- 设计字段安全边界。
- 设计 R9 实现建议。
- 输出文档和执行报告。

允许新增文档：

- `docs/tw_manual_review_explanation/manual_review_context_mapping_contract.md`
- `docs/tw_manual_review_explanation/PHASER8_EXECUTION_REPORT_CN.md`

#### 禁止范围

R8 禁止：

- 修改前端代码。
- 修改后端代码。
- 修改测试代码。
- 新增 API。
- 新增 route。
- 新增数据源。
- 联网或使用 token。
- 拉取数据或补数据。
- 训练模型。
- provider refresh/publish。
- accepted latest switching。
- materialize 到 qlib。
- monitor config save。
- monitor scan 或 scan-all。
- alerts write。
- broker、quick-trade、orders。
- target position 或 target weight。
- 买入、卖出、持有建议。
- 仓位建议、收益承诺、上涨概率或胜率承诺。
- 重启 Entry Model、正交规则探索、fundamental/月营收主线。

#### 字段映射设计要求

`manual_review_context_mapping_contract.md` 必须包含字段映射表，至少覆盖：

- qlib rank / score / rank_tier。
- qlib 排名变化，如果已有只读来源可用；否则标为暂缓。
- QuantDinger trend label / score / ret5 / ret20 / ret60，如果已有只读来源可用。
- MA / RSI / MACD / Bollinger 技术状态，如果已有只读来源可用。
- positionRisk / 价格位置风险，如果已有只读来源可用。
- 冻结法人/融资融券解释规则卡；只能作为 caution/review/background 线索，不能作为 gate。
- 数据质量 warning。

每个字段必须写清：

- 字段名。
- 现有来源文件/API/service。
- 是否已有字段。
- 是否只读。
- 是否需要新数据源；预期必须为否，否则暂缓。
- 用户可见位置：主线索、详情、数据提示、暂缓。
- 文案限制。
- 缺失时 fallback。
- R9 是否建议实现。

#### 输出收敛要求

R8 必须保持“简单、准确、清晰、实用”：

- 默认每只股票最多 3 条主线索。
- 详情展开最多 5 条。
- 不展示 raw rule id。
- 不展示 provider、gate、run id、IC、RankIC、训练指标。
- 不把字段堆给用户。
- 不把 qlib score、trend score、技术指标解释成收益、胜率、上涨概率或买卖建议。

#### R8 必须停下来讨论的情况

出现以下任一情况，立即停止：

- 需要新增数据源才能完成映射。
- 需要联网、token 或拉取数据。
- 需要训练模型。
- 需要 provider refresh/publish 或 accepted latest switching。
- 需要 monitor 写入、扫描或 alerts。
- 需要 broker、quick-trade、orders。
- 需要引入买卖、仓位、收益、概率或胜率语义。
- 需要修改前端/后端/测试代码才能完成 R8。
- 字段映射开始变成 fundamental/月营收、正交规则或 Entry Model 新主线。

#### R8 执行报告要求

新增：

- `docs/tw_manual_review_explanation/PHASER8_EXECUTION_REPORT_CN.md`

报告必须包含：

- 阅读材料。
- 新增/修改文件清单。
- 是否修改代码；预期答案应为否。
- 字段映射合同摘要。
- 哪些字段可进入 R9。
- 哪些字段暂缓及原因。
- 用户第一性原则自查。
- 安全边界自查。
- 是否偏离主线。
- 是否新增分支。
- 推荐 gate。

#### R8 Gate

R8 通过时建议 gate：

`request_phaser9_context_mapping_implementation`

R8 需要修复时：

`phaser8_context_mapping_contract_needs_repair`

如发现范围越权：

`stop_manual_review_next_round_scope_invalid`
