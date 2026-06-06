# 台股产品适配 Phase 1 Report：信息架构收敛与研究主视图整理

日期：2026-06-05

## 1. 执行结论

已按 `docs/TW_STOCK_PRODUCT_ADAPTATION_PHASE1_EXECUTION_CN.md` 完成 Phase 1 主流程整理。台股入口统一为“台股研究”，主视图优先展示今日 Top30/Top50 研究排名、数据日期/榜首/质量提示、排名变化、交叉分析、Agent 研究助手与 K 线图。运维细节保留但默认折叠，不再压过普通用户路径。

本阶段未实现模拟账户，未新增真实交易能力，未触发 monitor config 保存、monitor scan、alerts 写入、qlib provider refresh/publish 或 accepted latest 切换。

## 2. 修改文件清单

- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/src/locales/lang/zh-CN.js`
- `frontend/src/locales/lang/zh-TW.js`
- `frontend/src/locales/lang/en-US.js`
- `frontend/tests/unit/tw-stock-monitor-static-check.mjs`
- `frontend/tests/unit/tw-stock-agent-panel-check.mjs`
- `frontend/tests/unit/tw-stock-monitor-local-smoke.mjs`
- `docs/TW_STOCK_PRODUCT_ADAPTATION_PHASE1_REPORT_CN.md`

说明：当前工作区还存在本次任务前已积累的台股 Agent、数据自动化、首页分析适配等未提交改动；本报告仅覆盖 Phase 1 信息架构收敛相关改动。

## 3. 主视图调整前后

调整前：

- 入口和页面标题偏“台股趋势监控”，用户容易理解为监控/自动化工具。
- 顶部摘要优先展示监控名称、观察标的、扫描健康度、未读提醒。
- qlib 数据状态、daily auto update、run_id、recorder_id、dry-run 等运维信息直接占据主流程。
- 榜单表展示 `trend_label`、`quality_warnings`、`diagnostic_only` 等内部字段，普通用户难以判断价值。
- 手动研究扫描按钮在顶部主操作区，容易和研究查看流程混在一起。

调整后：

- 左侧菜单和页面标题统一为“台股研究”。
- 顶部固定展示研究边界提示：`本页面仅用于台股研究信号的人工复盘与历史验证，不连接券商，不提交真实订单，不构成投资建议。`
- 首屏摘要改为当前榜单、模型日期、行情日期、榜首标的、数据提示。
- 主卡片改为“今日研究排名”，Top30/Top50 切换更直接。
- 榜单表保留排名、标的、模型分数、最新价/行情日期、操作，移除内部质量/诊断字段的主表展示。
- 监控配置入口降级为“高级配置”；手动研究扫描从顶部主操作区移走，保留在折叠高级工具中。
- 交叉分析改为摘要优先：模型/行情日期、当前筛选、研究分组、QuantDinger 状态；数据口径折叠查看。
- Agent 面板保留在交叉分析区域，展示回答、引用来源、提示、调用能力和研究边界。
- K 线区域继续支持 Top30/Top50 和自定义标的选择，覆盖更多台股查看场景。

## 4. 已折叠或弱化的运维信息

默认折叠到“高级信息与维护工具”或“查看数据口径”的内容：

- qlib Option C 数据状态细节。
- daily auto update 原始 job 状态。
- qlib 历史研究 run 列表。
- qlib ops dry-run、scheduler、stdout/stderr log tail。
- `run_id`、`recorder_id`、provider/accepted latest 维护细节。
- cross-analysis 的底层数据口径和 freshness warning。

保留原因：这些信息对排障仍有价值，但不应成为用户进入台股页面后的第一信息层。

## 5. 真实交易入口审查

本阶段没有新增真实交易入口。台股研究页主流程不跳转 broker、quick-trade、orders、target position 或 target weight。

安全边界结果：

- broker / quick-trade / order 写入：未触发。
- target position / target weight：未出现业务入口。
- monitor config save：local smoke 计数为 0。
- monitor scan POST：local smoke 计数为 0。
- qlib ops dry-run POST：Phase 1 local smoke 已改为 0，不再点击 dry-run。
- qlib provider refresh / publish / accepted latest switch：未触发。

注意：只读回测与高级运维中仍会出现 `orders_enabled=false`、`connects_to_broker=false` 等边界说明，这是安全提示，不是真实交易能力。

## 6. 测试结果

已执行：

- `node tests/unit/tw-stock-monitor-static-check.mjs`：通过。
- `node tests/unit/tw-stock-agent-panel-check.mjs`：通过。
- `TW_STOCK_MONITOR_USERNAME=quantdinger TW_STOCK_MONITOR_PASSWORD=123456 node tests/unit/tw-stock-monitor-local-smoke.mjs http://127.0.0.1:8000`：通过。
- `corepack pnpm build`：通过。

local smoke 关键结果：

- `monitorConfigWriteCount=0`
- `monitorScanPostCount=0`
- `opsDryRunPostCount=0`
- K 线 canvas 非空：price chart `nonWhite=19916`，score chart `nonWhite=4129`
- 截图输出在 `/tmp/quantdinger_tw_qlib_e2e`，未纳入 git 工作区。

环境说明：

- 测试时本地后端 `0.0.0.0:5000` 已监听。
- 测试时本地前端 `0.0.0.0:8000` 已监听。
- `node` 命令输出中有 `/bin/sh: 2: source: not found`，但不影响测试结果；通过/失败均由 Node 断言结果确认。

## 7. 是否建议进入 Phase 2

建议进入 Phase 2，但范围应保持克制。

Phase 2 优先建议：

- 做“模拟账户”MVP，而不是接入真实券商。
- 模拟账户只允许手动记录模拟买入/卖出和持仓，不连接 broker，不提交真实订单。
- 收益计算基于已有真实日线数据，并明确与 qlib/QuantDinger 信号做历史验证对照。
- 首页、台股研究页、模拟账户之间需要统一趋势/分数解释口径，避免一个页面说强势、另一个页面给出相反结论。

不建议在 Phase 2 做：

- 真实券商连接。
- 自动下单。
- 目标仓位推荐。
- 自动按 qlib 榜单生成交易计划。
