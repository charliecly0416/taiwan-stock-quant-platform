# Phase R9 Repair 执行报告：技术状态识别与 details 展示修复

执行日期：2026-06-12

## 1. 修复目标

根据 `PHASER9_REVIEW_AND_REPAIR_WORK_CN.md`，本轮只修复两个 R9 审查问题：

1. 后端正确识别 rank-tech 现有技术状态枚举。
2. 前端在 manual-review 展开区展示 R9 新增的 `details`。

本轮未新增 API、route、数据源，也未扩展到模型训练、provider/accepted latest、monitor 写入、交易路径或买卖/仓位/收益/概率语义。

## 2. 修复文件清单

修改文件：

- `backend/app/services/tw_manual_review_explanation.py`
- `backend/tests/test_tw_manual_review_explanation.py`
- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/tests/unit/tw-stock-manual-review-explanation-check.mjs`
- `frontend/tests/e2e/tw-stock-manual-review-readonly.mjs`

新增报告：

- `docs/tw_manual_review_explanation/PHASER9_REPAIR_EXECUTION_REPORT_CN.md`

## 3. 后端技术状态枚举修复

`TWManualReviewExplanationService.explain()` 的 `technical_state` 分支已修复：

- `technical_strong` -> 技术状态偏支持。
- `technical_weak` -> 技术状态转弱。
- `technical_neutral` -> 技术状态中性。
- `technical_data_insufficient` -> `技术状态资料不足。` 数据提示。

同时将状态值规范为小写后比较，避免大小写造成误判。

新增后端测试：

- `test_rank_tech_technical_status_enums_are_recognized()`

覆盖以上四个枚举，并确认 `technical_strong` 不再产生 `缺少技术状态。`。

## 4. 前端 details 展示修复

`frontend/src/views/tw-stock-monitor/index.vue` 新增 computed：

- `manualReviewDetails`

行为：

- 只读取 `manualReviewExplanation.details`。
- 最多展示 5 条。
- 每条只保留 `label` 与 `message`。
- 不展示 `source`、raw id、provider、gate、run id、IC、RankIC、decision/actionPlan。

展示位置：

- 默认 manual-review 面板的 `查看复盘重点` 展开区。
- `manual_review_readonly=1` test-only 面板的同一展开区。

新增展示标题：

- `补充线索`

E2E 已调整为先展开 `查看复盘重点`，再断言 details 文案出现。

## 5. 验证命令与结果

### 5.1 后端编译

命令：

```bash
python -m py_compile backend/app/routes/tw_stock.py backend/app/services/tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation_api.py
```

结果：通过。

### 5.2 后端测试

命令：

```bash
python -m pytest backend/tests/test_tw_manual_review_explanation.py backend/tests/test_tw_manual_review_explanation_api.py -q
```

结果：`14 passed in 1.14s`。

### 5.3 前端静态检查

命令：

```bash
node frontend/tests/unit/tw-stock-manual-review-explanation-check.mjs
node frontend/tests/unit/tw-stock-monitor-static-check.mjs
node --check frontend/tests/e2e/tw-stock-manual-review-readonly.mjs
```

结果：全部通过。

备注：普通沙箱运行 Node 检查时仍遇到 `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`，随后按权限规则提升执行本地检查；不涉及联网、拉数或业务写入。

### 5.4 前端 build

命令：

```bash
cd frontend && corepack pnpm build
```

结果：通过。

备注：输出中仍有 `/bin/sh: 2: source: not found`，但 build 退出码为 0，Vite 构建完成。

### 5.5 Browser readonly smoke

命令：

```bash
cd frontend/dist && python -m http.server 5178 --bind 127.0.0.1
cd frontend && TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:5178 TW_STOCK_MANUAL_REVIEW_E2E_ARTIFACT_DIR=../data_tw/ops/manual_review_readonly_e2e/phase_r9_repair node tests/e2e/tw-stock-manual-review-readonly.mjs
```

结果：通过。

关键计数：

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

## 6. Browser artifact

产物目录：

- `data_tw/ops/manual_review_readonly_e2e/phase_r9_repair/summary.json`
- `data_tw/ops/manual_review_readonly_e2e/phase_r9_repair/network_audit.json`
- `data_tw/ops/manual_review_readonly_e2e/phase_r9_repair/console_audit.json`
- `data_tw/ops/manual_review_readonly_e2e/phase_r9_repair/manual_review_readonly.png`

页面文本摘要包含 details：

```text
补充线索
研究排序分数qlib score 0.318765，仅表示横截面研究排序分数。
趋势资料最新日 2026-06-04，趋势强弱分 76。
位置指标120 日位置 88.2，距 MA20 8.4，RSI14 69.5；仅作位置风险复盘线索。
```

## 7. 安全边界自查

本轮确认：

- 未新增 API。
- 未新增 route。
- 未新增数据源。
- 未联网拉取真实资料。
- 未使用 token。
- 未训练模型。
- 未 provider refresh/publish。
- 未 accepted latest switching。
- 未 monitor config save。
- 未 monitor scan。
- 未 alerts write。
- 未接 broker、quick-trade、orders。
- 未新增 portfolio replay POST。
- 未接 cross-analysis 或 rank-change 新数据流。
- 未接冻结规则卡真实来源。
- 未映射 decision/actionPlan raw code。
- 未输出买入、卖出、持有建议、仓位建议、收益承诺、上涨概率或胜率承诺。

## 8. 结论

Phase R9 Repair 已完成审查指出的两个 P1 修复点：

- rank-tech 技术状态枚举已正确识别。
- `details` 已在前端展开区简洁展示，并通过 E2E 文本断言。

建议 gate：

`manual_review_context_mapping_implementation_passed`
