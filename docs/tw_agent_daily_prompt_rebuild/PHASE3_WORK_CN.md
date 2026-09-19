# Phase 3 工作文档：Simple Chat 后端服务

生成日期：2026-06-19

## 1. 本阶段范围

Phase 3 只做后端 Simple Chat 服务，让后端基于已验证的 `DailyAgentPromptArtifact` 回答高频台股研究问题。

目标流程：

```text
classify question
  -> blocked intent 直接拒绝，不调用 OpenAI
  -> load latest or specified DailyAgentPromptArtifact
  -> validate manifest/checksum/readonly flags
  -> compose prompt_text + compact user question
  -> OpenAI JSON-only call or deterministic fallback
  -> validate output schema/citations/safety
  -> invalid output fallback/refusal
```

## 2. 明确不做什么

本阶段禁止：

- 不改前端。
- 不让前端读取、传递或保存 OpenAI key。
- 不做真实 OpenAI smoke；测试必须使用 mock adapter 或 disabled fallback。
- 不允许 OpenAI tool/function calling。
- 不调用外部搜索。
- 不触发 provider publish。
- 不切换 provider accepted latest 或 qlib accepted latest。
- 不写 monitor config/scan/alerts。
- 不触发 broker/order/quick-trade。
- 不写 paper account。
- 不训练模型、不调参、不跑回放收益筛选。
- 不修改 Phase 2 builder 的日更接入；那是 Phase 5 范围。

## 3. 执行者任务清单

1. 新增 artifact loader 服务：

```text
backend/app/services/tw_stock_agent_daily_prompt.py
```

2. 新增 simple chat 服务：

```text
backend/app/services/tw_stock_agent_simple_chat.py
```

3. 可选择新增 API：

```text
POST /api/tw-stock/agent/simple-chat
```

或在不破坏现有前端的情况下，为后续迁移保留服务层，不急于改 `/api/tw-stock/agent/chat`。

4. 复用：

```text
backend/app/services/tw_stock_agent_openai.py
backend/app/services/tw_stock_agent_guardrails.py
scripts/validate_tw_agent_daily_prompt_artifact.py
```

5. 新增后端测试：

```text
backend/tests/test_tw_stock_agent_simple_chat.py
```

6. 输出：

```text
docs/tw_agent_daily_prompt_rebuild/PHASE3_EXECUTION_REPORT_CN.md
```

## 4. Artifact Loader 要求

loader 必须：

- 读取 `latest.json` 或显式 artifact dir。
- 确认 `latest.json.artifact_type == "tw_agent_daily_prompt_latest"`。
- 加载 `manifest.json`、`prompt_context.json`、`prompt_text.md`。
- 调用 Phase 1 `validate_artifact(...)`。
- 校验 readonly flags：
  - `readonly_only=true`
  - `not_order=true`
  - `not_target_position=true`
  - `production_trade_enabled=false`
- 校验 checksum。
- 返回 `context_digest`：
  - `signal_asof`
  - `target_date`
  - `manifest`
  - `checksum`
  - `execution_price_status`
  - `freshness.status`

loader 不得：

- 读取实验 CSV。
- 调用动态 service preview。
- 调用 provider/monitor/broker/order。
- 自动构建 artifact。
- 自动更新 latest pointer。

## 5. Intent 与 Guardrails 要求

第一版 allowed intents 至少覆盖：

- `today_strategy`
- `tomorrow_candidates`
- `top_ranked_stock`
- `top_n_rankings`
- `strategy_buy_sell_observation`
- `single_symbol_status`
- `paper_apply_status`
- `execution_price_pending`
- `data_freshness`
- `replay_summary`

blocked intents 至少覆盖：

- `place_order`
- `auto_trade`
- `target_position`
- `portfolio_weight`
- `guaranteed_profit`
- `qlib_ops_refresh_publish`
- `qlib_retrain_or_tune`
- `broker_operation`
- `monitor_write`

必须修正 Phase 0 中指出的语义问题：允许只读查询 `paper_apply_status` / `execution_price_pending`，继续阻断实盘、自动交易、仓位、下单。

## 6. OpenAI 调用要求

本阶段只允许 backend-only OpenAI adapter 代码路径存在，不允许真实网络 smoke。

要求：

- blocked intent 直接拒绝，不调用 OpenAI。
- OpenAI disabled 时 deterministic fallback。
- missing artifact 时 deterministic error/fallback。
- OpenAI 输入只包含：
  - `prompt_text.md`
  - `prompt_context.json` 的 compact/必要字段
  - 用户问题
  - allowed citations/context digest
- 不传 secrets、环境变量、数据库连接、本地敏感配置。
- 不允许 tool/function calling。
- 要求 JSON output。
- 设置 timeout。

## 7. 输出 Contract

API/service 输出至少包含：

```json
{
  "ok": true,
  "mode": "openai|fallback|blocked|disabled|artifact_missing",
  "intent": "today_strategy",
  "blocked": false,
  "answer": "string",
  "items": [],
  "citations": [],
  "warnings": [],
  "research_only_disclaimer": "仅供研究观察，不构成交易建议...",
  "context_digest": {
    "signal_asof": "YYYY-MM-DD",
    "target_date": "YYYY-MM-DD",
    "prompt_artifact": ".../manifest.json",
    "checksum": "sha256:..."
  }
}
```

所有正常或 fallback 回答都必须带 disclaimer。

## 8. Output Validation 要求

模型输出必须 deterministic validation：

- JSON object。
- `answer` 非空字符串。
- `intent` 与分类结果一致。
- `citations` 为字符串数组。
- citations 只能来自 artifact allowlist。
- `warnings` 为字符串数组。
- `research_only_disclaimer` 存在并包含“不构成交易建议”。
- answer 不包含行动性危险语义：
  - 下单、自动交易、目标仓位、提交订单、连接券商。
  - broker/order/quick-trade。
  - monitor config/scan/alerts。
  - provider publish/accepted latest/qlib refresh/retrain/调参。
  - 保证收益、保证上涨、胜率/上涨概率承诺。

unsafe output 必须被 deterministic refusal 覆盖，不得原样返回用户。

## 9. 必须测试的场景

后端测试至少覆盖：

- OpenAI disabled fallback。
- missing latest/artifact。
- invalid artifact / checksum mismatch。
- blocked question 不调用 OpenAI。
- monitor write question 不调用 OpenAI。
- paper apply status 只读查询不被误判为交易。
- invalid JSON fallback。
- forged citations fallback。
- unsafe answer overridden。
- valid JSON answer pass。
- fallback answer 带 disclaimer 和 context digest。

## 10. 必须运行的测试或静态检查

最低命令：

```bash
python -m py_compile backend/app/services/tw_stock_agent_daily_prompt.py backend/app/services/tw_stock_agent_simple_chat.py
python -m pytest backend/tests/test_tw_stock_agent_simple_chat.py -q
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py backend/tests/test_tw_stock_agent_daily_prompt_builder.py -q
rg -n "OPENAI_API_KEY|api.openai.com|chat/completions|@openai" frontend/src frontend/tests
rg -n "tool_choice|tools|function_call|functions" backend/app/services/tw_stock_agent_simple_chat.py backend/app/services/tw_stock_agent_openai.py
rg -n "quick-trade|broker|orders|target-position|target_weight|monitor config|monitor scan|monitor alerts|/monitor/config|/monitor/scan|/monitor/alerts|provider publish|accepted latest|qlib refresh|retrain|调参" backend/app/services/tw_stock_agent_daily_prompt.py backend/app/services/tw_stock_agent_simple_chat.py backend/tests/test_tw_stock_agent_simple_chat.py
```

静态检索命中 forbidden terms 时，执行报告必须解释命中是 blocked intent、拒绝文案、测试负样本，还是潜在问题。

## 11. 执行报告必须包含

执行者必须输出：

```text
docs/tw_agent_daily_prompt_rebuild/PHASE3_EXECUTION_REPORT_CN.md
```

报告必须包含：

- 阶段目标。
- 实际完成内容。
- 改动文件列表。
- 是否新增 API；如新增，列出路径和行为。
- artifact loader 行为。
- blocked intent 不调用 OpenAI 的证据。
- OpenAI disabled / mock 测试证据。
- 输出 validation 覆盖项。
- 测试命令与实际结果。
- 只读安全边界说明。
- 未完成事项。
- 风险与需要审查的问题。
- 是否建议进入 Phase 4。

## 12. 审查者重点检查项

Phase 3 审查者必须检查：

- OpenAI 输入是否只来自 DailyAgentPromptArtifact 和用户问题。
- blocked intent 是否完全绕过 OpenAI。
- output validator 是否足够严格。
- unsafe model answer 是否被覆盖。
- citations 是否不能伪造。
- 是否没有 secret 泄露。
- 是否没有 frontend OpenAI key。
- 是否没有 provider/accepted latest/monitor/broker/order 写入。

## 13. 停止条件

出现以下任一情况必须停止，不得进入 Phase 4：

- 真实 OpenAI 调用被执行或报告记录了真实 key。
- blocked intent 仍会调用 OpenAI。
- OpenAI 输入绕过 DailyAgentPromptArtifact。
- citations 可伪造。
- unsafe answer 可原样展示。
- 前端接触 OpenAI key/base URL。
- 新增 provider publish、accepted latest、monitor、broker/order/quick-trade 路径。
