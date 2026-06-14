# 人工复盘解释模块交接摘要

更新日期：2026-06-12

## 1. 用户入口

用户入口仍是 `/tw-stock-monitor` 页面中的 `复盘线索` 面板。

该入口是只读研究解释入口，用于帮助用户整理当前标的的复盘线索。

## 2. 用户能看到什么

当前页面可展示：

- 摘要：一句话说明当前复盘状态。
- 主线索：最多 3 条核心研究线索。
- 下一步复盘：提示后续人工应补看的方向。
- 数据提示：说明资料不足或数据质量提示。
- 补充线索：最多 5 条简短细节，只展示 `label` 和 `message`。

补充线索示例包括：

- 研究排序分数。
- 趋势资料。
- 技术策略说明。
- 位置指标。

## 3. 模块边界

该模块不是：

- 买卖建议。
- 持有建议。
- 仓位建议。
- 收益预测。
- 上涨概率预测。
- 胜率预测。
- 自动交易入口。

页面文案和测试均禁止输出买入、卖出、目标仓位、目标权重、收益承诺、上涨概率、胜率、下单、连接券商、自动交易等语义。

## 4. 当前上下文来源

当前补充线索来自已有只读上下文和现有 manual-review GET query 白名单。

已使用的上下文包括：

- qlib rank、rank tier、score、asof。
- trend label、score、latest date。
- technical status、summary、MA/RSI/MACD/Bollinger 策略摘要。
- position risk status、label、reason 和少量白名单 metrics。
- data quality warnings。

实现要求保持白名单解析，不允许 raw payload 整包透传。

## 5. 验收覆盖

当前验收覆盖：

- 后端 contract 与安全语义测试。
- API GET route 测试。
- 前端静态安全检查。
- Browser readonly smoke。
- Network audit。
- Console audit。

最新最终验收产物：

- `data_tw/ops/manual_review_readonly_e2e/phase_r10_final_acceptance/summary.json`
- `data_tw/ops/manual_review_readonly_e2e/phase_r10_final_acceptance/network_audit.json`
- `data_tw/ops/manual_review_readonly_e2e/phase_r10_final_acceptance/console_audit.json`
- `data_tw/ops/manual_review_readonly_e2e/phase_r10_final_acceptance/manual_review_readonly.png`

## 6. 暂缓项

以下能力仍然暂缓，不应在未授权阶段顺手接入：

- qlib rank change。
- ret60。
- cross-analysis 新接入。
- cross category / alignment。
- 冻结法人/融资融券规则卡真实来源。
- decision/actionPlan raw code。
- 新数据源。
- 模型训练。
- provider refresh/publish。
- accepted latest switching。
- monitor config save。
- monitor scan 或 scan-all。
- alerts write。
- broker、quick-trade、orders。
- portfolio replay POST。

## 7. 后续维护原则

后续维护应继续遵守：

- 简单：默认信息少，细节放展开区。
- 准确：只解释已有只读上下文，不制造新含义。
- 清晰：分清主线索、数据提示和补充线索。
- 实用：帮助人工复盘，不转化为交易行动。
- 只读：不得引入业务写请求或交易路径。
