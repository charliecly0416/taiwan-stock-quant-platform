---
created_at: 2026-06-02
status: deployment_guide
scope: quantdinger_tw_stock_agent_deployment
backend_project: /path/to/taiwan-stock-quant-platform
frontend_project: /path/to/taiwan-stock-quant-platform-Vue
---

# 台股研究 Agent 部署说明

## 1. 定位

台股研究 Agent 是 research-only 模块，只用于解释 QuantDinger 后端整理出的台股研究上下文、qlib accepted signal、cross-analysis、freshness 和单股指标。

它不是交易 Agent，不执行下单、仓位建议、自动交易、qlib 运维或回测。

## 2. 后端环境变量

默认关闭真实 OpenAI-compatible 调用：

```text
ENABLE_TW_STOCK_AGENT_OPENAI=false
```

只有需要真实后端模型总结时，才在 QuantDinger 后端环境中显式设置：

```text
ENABLE_TW_STOCK_AGENT_OPENAI=true
OPENAI_API_KEY=<backend-only>
TW_STOCK_AGENT_OPENAI_BASE_URL=<OpenAI-compatible base_url>
TW_STOCK_AGENT_OPENAI_MODEL=<model name>
TW_STOCK_AGENT_OPENAI_TIMEOUT_SECONDS=20
```

说明：

- `OPENAI_API_KEY` 只设置在 QuantDinger 后端环境。
- `TW_STOCK_AGENT_OPENAI_BASE_URL` 只设置在后端，可用于 OpenAI-compatible endpoint，例如内部门户或代理服务。
- `TW_STOCK_AGENT_OPENAI_MODEL` 只设置在后端；未设置时使用后端默认模型。
- `TW_STOCK_AGENT_OPENAI_TIMEOUT_SECONDS` 只设置在后端，并由后端限制在安全范围内。
- 不要把真实 key 写入代码、前端配置、文档、截图或日志。

## 3. 前端边界

前端只调用 QuantDinger 后端 API：

```text
GET  /api/tw-stock/agent/context
POST /api/tw-stock/agent/chat
```

前端不得：

- 读取、保存、传递或展示 `OPENAI_API_KEY`。
- 直连 `api.openai.com` 或任何 OpenAI-compatible 服务。
- 导入 OpenAI SDK。
- 保存聊天历史。
- 展示交易、下单、仓位、broker、paper/live trading 操作入口。

## 4. fallback 和 blocked 行为

未启用 OpenAI 或缺少后端 key 时，后端返回 deterministic fallback：

```text
mode=disabled
warnings=openai_disabled 或 missing_openai_api_key
```

blocked intent 不进入模型调用，直接返回研究边界拒绝。

常见 blocked intent：

```text
下单
仓位
自动交易
broker/券商操作
paper/live trading
qlib refresh/publish/pipeline
模型重训/调参
收益承诺
```

## 5. 安全边界

必须保持：

- 不下单。
- 不生成仓位。
- 不触发 qlib refresh/publish/pipeline/scheduler/normal publish。
- 不运行回测。
- 不训练或调参 qlib 模型。
- qlib score 是横截面排序分数，不是收益率、胜率、涨幅或买入概率。
- 所有回答都必须包含“不构成交易建议”的 research-only 口径。

## 6. 部署前 smoke/checklist

后端 mock smoke：

```text
python backend/scripts/smoke_tw_stock_agent_phase6b.py --mock
```

后端真实 OpenAI-compatible smoke，仅在后端环境执行：

```text
ENABLE_TW_STOCK_AGENT_OPENAI=true OPENAI_API_KEY=<backend-only> TW_STOCK_AGENT_OPENAI_BASE_URL=<base_url> python backend/scripts/smoke_tw_stock_agent_phase6b.py
```

后端回归：

```text
python -m pytest backend/tests/test_tw_stock_agent_context.py backend/tests/test_tw_stock_agent_chat.py -q
```

前端检查：

```text
node tests/unit/tw-stock-agent-panel-check.mjs
node tests/unit/tw-stock-agent-panel-e2e.mjs
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-cross-analysis-check.mjs
corepack pnpm build
```

## 7. 故障处理

如果返回 deterministic fallback：

- 检查后端 `ENABLE_TW_STOCK_AGENT_OPENAI` 是否为 `true`。
- 检查后端 `OPENAI_API_KEY` 是否存在。
- 检查后端 `TW_STOCK_AGENT_OPENAI_BASE_URL` 是否可访问。
- 不要通过前端传入 key。

如果问题被 blocked：

- 这是预期安全行为。
- 将用户问题改写为 research-only 问法，例如“解释当前研究信号和风险点”，不要请求下单、仓位或收益承诺。
