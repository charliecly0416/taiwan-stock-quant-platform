# 台股入场位置风险实现报告

日期：2026-06-08

## 结论

已按 `TW_STOCK_ENTRY_POSITION_RISK_IMPLEMENTATION_PLAN_CN.md` 完成第一版实现。

本次没有新增一级模块，而是把“上涨趋势不等于适合入场”的判断合入现有台股研究主链路：技术状态、排名 × 趋势 × 技术状态交叉分析、模拟账户候选、组合规则历史回放。用户看到的是短标签和一句原因，不需要理解复杂指标。

## 已实现内容

1. 后端技术状态新增 `positionRisk`。
   - 支持 `位置合理`、`强势但偏高`、`过热谨慎`、`回调观察`、`数据不足`。
   - 只读计算 MA20/MA60 乖离、RSI14、近 120 日价格百分位、Bollinger 位置、5/20 日涨幅。
   - `score` 表示追高风险强度，不是收益率、胜率或上涨概率。

2. 排名 × 技术交叉决策纳入位置风险。
   - Top10/Top30 且技术偏强但 `overheated`：降级为人工复核。
   - Top10/Top30 且技术偏强但 `elevated`：降级为继续观察。
   - Top50 且过热：进入人工复核。

3. 历史观察回放新增第四个对照规则。
   - `qlib_only`
   - `qlib_plus_trend`
   - `qlib_plus_trend_indicators`
   - `qlib_plus_trend_position_risk`

4. 组合规则历史回放输出位置过滤摘要。
   - 统计避开过热新增次数。
   - 统计偏高候选降级次数。
   - 统计风险复盘提示次数。

5. 前端用户界面保持简单。
   - 今日复盘卡片增加位置标签和一句原因。
   - 交叉分析表格增加“位置”提示。
   - 模拟账户候选增加位置标签，过热标的进入追高复核。
   - 历史模拟对照增加 `qlib + trend + position`，只展示“位置过滤”摘要。

## 用户第一准则审查

- 清晰：页面不堆指标，只展示“位置合理/偏高/过热”等短标签。
- 简单：没有新增页面和一级菜单，只嵌入现有研究与模拟流程。
- 准确：把趋势、排名、位置拆开表达，避免把上涨直接解释成适合入场。
- 有用：位置风险会实际影响候选优先级、人工复核和历史回放对照。

## 安全边界

本次实现仅做研究和模拟验证：

- 不连接券商。
- 不提交真实订单。
- 不触发 quick-trade。
- 不写监控配置、扫描或提醒。
- 不触发 qlib provider publish/refresh。
- 不切换 accepted latest。
- 不输出目标仓位、目标权重、收益承诺或上涨概率。

## 验证结果

已通过：

```bash
python -m pytest backend/tests/test_tw_stock_technical_status.py backend/tests/test_tw_stock_rank_tech_cross.py backend/tests/test_tw_stock_rank_tech_cross_api.py backend/tests/test_tw_stock_observation_replay.py backend/tests/test_tw_stock_observation_replay_api.py backend/tests/test_tw_stock_portfolio_replay.py backend/tests/test_tw_stock_portfolio_replay_api.py -q
# 30 passed

python -m py_compile backend/app/services/tw_stock_technical_status.py backend/app/services/tw_stock_rank_tech_cross.py backend/app/services/tw_stock_observation_replay.py backend/app/services/tw_stock_portfolio_replay.py

node frontend/tests/unit/tw-stock-rank-tech-portfolio-replay-check.mjs
node frontend/tests/unit/tw-stock-sim-account-check.mjs
node frontend/tests/unit/tw-stock-cross-analysis-check.mjs
node frontend/tests/unit/tw-stock-monitor-static-check.mjs

corepack pnpm build

TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8010 node frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs
```

E2E 安全计数结果：

- `sim_write_request_count=0`
- `quick_trade_request_count=0`
- `broker_request_count=0`
- `real_order_request_count=0`
- `monitor_config_write_count=0`
- `monitor_scan_post_count=0`
- `monitor_alerts_write_count=0`
- `qlib_ops_post_count=0`
- `accepted_latest_switch_count=0`
- `provider_publish_refresh_count=0`
- `target_position_request_count=0`
- `target_weight_request_count=0`
- `forbidden_request_count=0`
- `page_error_count=0`

## 残留风险

1. 位置风险是基于日线的当前位置评估，不预测未来走势。
2. 指标阈值是保守 MVP，后续可用真实模拟回放校准，但不应把阈值复杂度暴露给普通用户。
3. 如果某些标的历史日线不足，仍会显示数据不足；这比强行给出错误位置判断更可靠。
