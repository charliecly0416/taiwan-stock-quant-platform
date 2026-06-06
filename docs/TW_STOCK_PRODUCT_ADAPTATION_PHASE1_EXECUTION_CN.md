# 台股产品适配 Phase 1 执行文档：信息架构收敛与研究主视图整理

日期：2026-06-05

## 1. 本步目标

让用户进入台股功能后，30 秒内能找到：

- 今日研究排名 Top30/Top50。
- 个股 K 线和趋势。
- cross-analysis。
- Agent 研究解释。

本步不实现模拟账户，不新增交易能力。

## 2. 工作范围

### 2.1 台股主入口命名

将台股主页面入口统一表达为：

```text
台股研究
```

避免主入口使用：

```text
交易
机器人
实盘
下单
账户连接
```

### 2.2 主视图信息收敛

主视图优先展示：

- latest accepted asof。
- Top30/Top50。
- cross-analysis 摘要。
- 个股趋势和 K 线。
- Agent 研究助手。
- 数据新鲜度状态。

折叠到“高级信息 / 运维信息”的内容：

- qlib ops dry-run。
- scheduler。
- run_id / recorder_id。
- provider / accepted latest 维护细节。
- daily auto update 原始 job 细节。

注意：高级信息可以保留，但默认不压过主流程。

### 2.3 真实交易隔离提示

在台股研究页固定保留研究边界提示：

```text
本页面仅用于台股研究信号的人工复盘与历史验证，不连接券商，不提交真实订单，不构成投资建议。
```

### 2.4 左侧导航处理

如果当前左侧仍显示 broker、quick-trade、机器人等通用功能，不要求本步删除，但需要：

- 台股主流程不要跳转到这些功能。
- 台股页面不要出现真实买卖入口。
- 如有台股相关说明，明确“暂不支持台股真实交易”。

## 3. 禁止事项

本步不得：

- 新增 broker / quick-trade / order 入口。
- 触发 monitor config 保存、scan、alerts 写入。
- 触发 qlib provider refresh、publish、accepted latest 切换。
- 修改 OpenAI key 配置。

## 4. 验收标准

- 用户打开台股页面能直接看到今日排名、K 线、cross-analysis、Agent。
- 页面主视图不出现误导性的真实交易入口。
- 运维字段被折叠或弱化，不干扰普通用户。
- 原有只读 E2E 和 Agent panel 检查通过。

## 5. 必跑验证

```bash
cd frontend
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-agent-panel-check.mjs
node tests/unit/tw-stock-monitor-local-smoke.mjs
corepack pnpm build
```

如 full local smoke 需要服务，报告中写明服务地址和账号。

## 6. 报告断点

完成后提交：

```text
docs/TW_STOCK_PRODUCT_ADAPTATION_PHASE1_REPORT_CN.md
```

报告必须包含：

- 修改文件清单。
- 台股主视图调整前后说明。
- 哪些运维信息被折叠。
- 是否仍出现真实交易入口。
- 测试结果。
- 是否建议进入 Phase 2。

