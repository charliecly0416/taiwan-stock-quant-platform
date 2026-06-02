---
created_at: 2026-06-02
status: phase_plan
scope: quantdinger_tw_stock_agent_phase6_openai_research_assistant
role_target: reviewer_executor_loop
reviewer: codex_reviewer
backend_project: /path/to/taiwan-stock-quant-platform
frontend_project: /path/to/taiwan-stock-quant-platform-Vue
qlib_project: /home/chuliyang/qlib
depends_on:
  - docs/TW_STOCK_QLIB_OPTION_C_PHASE4_ACCEPTANCE_CN.md
  - docs/TW_STOCK_QLIB_CROSS_ANALYSIS_PHASE5_STEP5A_REPORT_CN.md
next_execution_doc: docs/TW_STOCK_AGENT_PHASE6_STEP1_EXECUTION_CN.md
---

# 台股研究 Agent Phase 6 总体规划

Phase 6 的目标是在 QuantDinger 前端新增一个简单的台股研究 Agent 模块，通过后端受控连接 OpenAI 接口，让用户可以用自然语言查询当前台股研究数据，例如：

```text
今天 top30 是哪些？
今天模型和趋势都支持的股票有哪些？
某只股票的 qlib rank、score、趋势、数据质量是什么？
今天有哪些建议关注、回避、复盘的数据异常？
```

本模块是 research-only 的自然语言解释层，不是交易 Agent。

---

## 1. 需求合理性判断

合理且可实现，建议加入当前项目。

原因：

- Phase 4 已经形成盘后自动补数到 accepted latest 的可持续闭环。
- Phase 5 已经形成 qlib accepted ranking 与 QuantDinger raw trend 的交叉分析工作台。
- Agent 模块不需要重新训练模型，也不需要改 qlib provider，只需要把现有只读 API 的结果整理成受控上下文，再由 OpenAI 做自然语言总结。
- 用户提问范围清晰，适合做轻量研究助手，而不是复杂 autonomous agent。

必须严格限制：

```text
只读查询
只解释 accepted/latest/cross-analysis/trend 数据
不下单
不生成目标仓位
不调用 broker
不自动运行回测
不触发 qlib refresh/publish/pipeline
不把 qlib score 解释成收益率、胜率、涨幅或买入概率
不输出“必须买入/卖出”的交易指令
```

“建议买入/卖出”在产品文案中应改写为：

```text
建议关注
建议回避
趋势分歧，建议人工复盘
数据异常，暂不纳入判断
```

如必须回答用户口语中的“买/卖”，Agent 只能返回 research-only 解释，例如“从研究排序和趋势交叉看，偏向关注/回避，不构成交易建议”。

---

## 2. Phase 6 分步设计

Phase 6 建议拆成 5 步。

### Step 1：只读数据上下文与 Agent 边界

目标：

- 建立后端 Agent context service。
- 聚合 Phase 4/5 已有只读数据：accepted latest、cross-analysis latest、symbol detail、freshness/data basis。
- 定义允许的问题类型、响应 schema、引用字段和安全边界。
- 提供不调用 OpenAI 的 deterministic preview/debug API，便于后续测试。

产出：

```text
backend/app/services/tw_stock_agent_context.py
backend/app/services/tw_stock_agent_guardrails.py
GET /api/tw-stock/agent/context
POST /api/tw-stock/agent/preview
docs/TW_STOCK_AGENT_PHASE6_STEP1_REPORT_CN.md
```

审核断点：

```text
docs/TW_STOCK_AGENT_PHASE6_STEP1_REPORT_CN.md
```

### Step 2：OpenAI 后端 Adapter 与结构化回答

目标：

- 后端接入 OpenAI API，API key 只允许在后端环境变量中读取。
- 新增 `POST /api/tw-stock/agent/chat`。
- 默认关闭真实 OpenAI 调用；没有 `OPENAI_API_KEY` 或未启用开关时返回明确的 disabled 状态。
- 使用结构化输出或严格 JSON 解析，让回答包含 answer、citations、warnings、intent、research_only_disclaimer。
- Mock 测试覆盖 OpenAI 成功、失败、超时、返回格式异常、越权问题。

禁止：

- 前端直接持有 OpenAI API key。
- 把用户问题原样拼接进任意 SQL。
- 让模型决定调用 qlib 运维、交易或写入接口。

审核断点：

```text
docs/TW_STOCK_AGENT_PHASE6_STEP2_REPORT_CN.md
```

### Step 3：前端 Agent 面板

目标：

- 在 QuantDinger 前端新增简单 Agent 模块。
- 支持建议问题、输入框、回答区、引用数据、风险提示、加载和错误状态。
- 回答必须展示数据日期、qlib asof、run_id 或引用来源。
- 对“买入/卖出”类问题，界面文案也要显示 research-only 限制。

建议入口：

```text
台股交叉分析页右侧/底部 Agent 面板
或独立“台股研究助手”Tab
```

审核断点：

```text
docs/TW_STOCK_AGENT_PHASE6_STEP3_REPORT_CN.md
```

### Step 4：仿真测试与安全回归

目标：

- 使用 mocked OpenAI 响应做 Playwright 仿真测试。
- 覆盖用户真实问题场景：
  - 查询 top30。
  - 查询建议关注。
  - 查询建议回避。
  - 查询单股指标。
  - 查询数据异常。
  - 问“帮我下单/买入多少仓位”等越权问题。
  - OpenAI disabled/API error/timeout。
- 验证不会触发 qlib ops、交易、订单、回测自动运行。

审核断点：

```text
docs/TW_STOCK_AGENT_PHASE6_STEP4_REPORT_CN.md
```

### Step 5：受控真实 API Smoke 与最终验收

目标：

- 在用户明确提供后端 `OPENAI_API_KEY` 并临时启用开关时，做小规模真实 OpenAI API smoke。
- 验证真实回答格式、延迟、错误处理、引用字段和 research-only 文案。
- 如没有 API key，也可以用 mock acceptance 收尾，但 report 必须说明未做真实 OpenAI 网络调用。

审核断点：

```text
docs/TW_STOCK_AGENT_PHASE6_ACCEPTANCE_CN.md
```

---

## 3. 总体架构建议

建议数据流：

```text
Frontend Agent panel
-> QuantDinger backend /api/tw-stock/agent/chat
-> Agent guardrails classify intent
-> Agent context service reads existing read-only APIs/services
-> OpenAI adapter receives compact context + strict system prompt
-> Backend validates structured response
-> Frontend renders answer + citations + warnings
```

关键原则：

- OpenAI 只拿到必要上下文，不直接访问数据库、文件系统、qlib provider 或交易接口。
- 所有数据读取都由 QuantDinger 后端白名单 service 完成。
- 模型输出必须经过后端 schema 校验和安全后处理。
- 用户问题和模型回答都不能改变系统状态，除非后续单独设计“对话日志”，且默认也应关闭。

---

## 4. Agent 可回答范围

允许回答：

```text
today_top30
today_top50
focus_watch
secondary_watch
model_trend_divergence
data_review_required
single_symbol_metrics
freshness_and_data_basis
how_to_read_qlib_rank_score
research_summary
```

必须拒绝或改写：

```text
place_order
auto_trade
target_position
portfolio_weight
paper/live trading
broker operation
guaranteed profit
price target from qlib score
return/probability interpretation from qlib score
qlib retrain/tune/refresh/publish from chat
```

---

## 5. 验收标准

Phase 6 可收尾的最低标准：

- 前端有可用 Agent 面板。
- 后端 OpenAI key 不暴露给前端。
- Agent 能回答 top30、关注候选、回避候选、单股指标、数据异常和数据口径问题。
- 回答包含引用来源和 asof/freshness。
- 越权问题被拒绝或改写为 research-only。
- OpenAI disabled/error/timeout 有清晰降级。
- Playwright 仿真覆盖主要问题。
- 测试证明没有触发交易、订单、broker、qlib ops、自动回测。

---

## 6. 预计轮次

预计需要 5 轮执行和审查：

```text
Step 1：数据上下文和边界
Step 2：OpenAI 后端连接
Step 3：前端 Agent 面板
Step 4：仿真测试和安全回归
Step 5：真实 API smoke 或 mock acceptance
```

如果 Step 2/3 实现质量较高，Step 4/5 可以合并为一次验收；如果 OpenAI API 环境不可用，则 Step 5 以 mock acceptance 收尾，真实 API smoke 留作部署前检查。
