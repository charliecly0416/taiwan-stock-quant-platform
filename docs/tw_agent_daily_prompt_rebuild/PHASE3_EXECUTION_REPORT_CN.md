# Phase 3 执行报告：Simple Chat 后端服务

生成日期：2026-06-19

## 1. 阶段目标

Phase 3 目标是实现后端 Simple Chat 服务，让后端基于已验证的 `DailyAgentPromptArtifact` 回答高频台股研究问题。

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

本阶段未进入前端、日更编排或真实 OpenAI smoke。

## 2. 实际完成内容

已完成：

- 新增 artifact loader：`backend/app/services/tw_stock_agent_daily_prompt.py`。
- 新增 simple chat service：`backend/app/services/tw_stock_agent_simple_chat.py`。
- 新增后端测试：`backend/tests/test_tw_stock_agent_simple_chat.py`。
- 复用 Phase 1 validator：`validate_artifact(...)`。
- 复用 backend-only OpenAI adapter / mock adapter。
- blocked intent 直接返回 deterministic refusal，不调用 OpenAI。
- OpenAI disabled 返回 deterministic fallback。
- mock OpenAI 覆盖 valid JSON、invalid JSON、forged citations、unsafe answer override。

## 3. 改动文件列表

新增文件：

- `backend/app/services/tw_stock_agent_daily_prompt.py`
- `backend/app/services/tw_stock_agent_simple_chat.py`
- `backend/tests/test_tw_stock_agent_simple_chat.py`
- `docs/tw_agent_daily_prompt_rebuild/PHASE3_EXECUTION_REPORT_CN.md`

未修改：

- `frontend/src/...`
- `backend/app/routes/tw_stock.py`
- `backend/app/services/tw_stock_agent_chat.py`
- `backend/app/services/tw_stock_agent_openai.py`
- Phase 2 builder 日更接入逻辑。

## 4. 是否新增 API

本阶段未新增 API 路由。

实现保留在服务层，供后续 Phase 4/后续路由迁移审查使用。现有 `/api/tw-stock/agent/chat` 未改动，前端不受影响。

## 5. Artifact Loader 行为

`TWStockAgentDailyPromptLoader` 支持：

- 从显式 `artifact_dir` 加载 artifact。
- 从 `latest.json` 加载 artifact。
- 校验 `latest.json.artifact_type == "tw_agent_daily_prompt_latest"`。
- 校验 latest pointer 的 `manifest`、`checksum`、`signal_asof` 与实际 artifact 一致。
- 加载 `manifest.json`、`prompt_context.json`、`prompt_text.md`。
- 调用 Phase 1 `validate_artifact(...)`。
- 校验 readonly flags：
  - `readonly_only=true`
  - `not_order=true`
  - `not_target_position=true`
  - `production_trade_enabled=false`
- 返回 `context_digest`：
  - `signal_asof`
  - `target_date`
  - `prompt_artifact`
  - `checksum`
  - `execution_price_status`
  - `freshness_status`
- 生成 citation allowlist：
  - `agent_prompt:{signal_asof}:{checksum}`
  - manifest path

loader 不读取实验 CSV，不调用动态 preview service，不调用 provider/monitor/broker/order，不自动构建 artifact，不更新 latest pointer。

## 6. Intent 与 Guardrails

Simple chat 第一版 allowed intents 覆盖：

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

blocked intents 覆盖：

- `place_order`
- `auto_trade`
- `target_position`
- `portfolio_weight`
- `guaranteed_profit`
- `qlib_ops_refresh_publish`
- `qlib_retrain_or_tune`
- `broker_operation`
- `monitor_write`

测试确认 `paper_apply_status` 是只读查询，不会被误判为交易；`monitor_write` 和下单问题不会调用 OpenAI。

## 7. OpenAI Disabled / Mock 证据

本阶段没有真实 OpenAI smoke。

测试使用：

- `TWStockAgentOpenAIAdapter(config=TWStockAgentOpenAIConfig(enabled=False, api_key=""))` 验证 disabled fallback。
- `MockTWStockAgentOpenAIAdapter` 验证 mock JSON 输出、invalid JSON fallback、forged citations fallback、unsafe answer override。

blocked intent 证据：

- `test_blocked_order_question_does_not_call_openai`：`adapter.calls == []`。
- `test_monitor_write_question_does_not_call_openai`：`adapter.calls == []`。

OpenAI 输入限制：

mock adapter 捕获的 `controlled_context` 只包含：

- `prompt_text`
- compact `prompt_context`
- `question`
- `intent`
- `symbol`
- `allowed_citations`
- `context_digest`
- `research_only_disclaimer`

测试确认其中不包含 `OPENAI_API_KEY`。

## 8. Output Validation 覆盖项

模型输出必须满足：

- JSON object。
- `answer` 非空字符串。
- `intent` 与分类 intent 一致。
- `citations` 为字符串数组。
- citations 必须全部来自 artifact allowlist。
- `warnings` 为字符串数组。
- `research_only_disclaimer` 包含“不构成交易建议”。
- answer 不包含下单、自动交易、目标仓位、broker、quick-trade、monitor scan/alerts/config、provider publish、accepted latest、qlib refresh、retrain、调参、收益/上涨/胜率承诺等危险语义。

不合格输出处理：

- invalid JSON：fallback。
- forged citations：fallback。
- unsafe answer：deterministic refusal 覆盖，不原样展示。

## 9. 测试命令与实际结果

已运行：

```bash
python -m py_compile backend/app/services/tw_stock_agent_daily_prompt.py backend/app/services/tw_stock_agent_simple_chat.py
```

结果：通过，退出码 0。

```bash
python -m pytest backend/tests/test_tw_stock_agent_simple_chat.py -q
```

结果：

```text
11 passed in 0.93s
```

```bash
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py backend/tests/test_tw_stock_agent_daily_prompt_builder.py -q
```

结果：

```text
9 passed in 0.12s
```

静态检查：

```bash
rg -n "OPENAI_API_KEY|api.openai.com|chat/completions|@openai" frontend/src frontend/tests
```

结果：有命中，均为既有前端设置翻译文案或既有前端测试 denylist/assertion，不是 Phase 3 新增代码。本阶段未修改前端。

```bash
rg -n "tool_choice|tools|function_call|functions" backend/app/services/tw_stock_agent_simple_chat.py backend/app/services/tw_stock_agent_openai.py
```

结果：无命中，退出码 1。

```bash
rg -n "quick-trade|broker|orders|target-position|target_weight|monitor config|monitor scan|monitor alerts|/monitor/config|/monitor/scan|/monitor/alerts|provider publish|accepted latest|qlib refresh|retrain|调参" backend/app/services/tw_stock_agent_daily_prompt.py backend/app/services/tw_stock_agent_simple_chat.py backend/tests/test_tw_stock_agent_simple_chat.py
```

结果：命中均为 simple chat blocked/unsafe 词表或测试负样本：

- `qlib_retrain_or_tune`
- `qlib_ops_refresh_publish`
- `monitor_write`
- `broker_operation`
- unsafe answer terms
- monitor write blocked test question

这些不是执行路径。

## 10. 只读安全边界说明

本阶段没有：

- 调用真实 OpenAI。
- 记录或使用真实 OpenAI key。
- 改前端。
- 新增或修改 API 路由。
- 调用外部搜索。
- 触发 provider publish。
- 切换 provider accepted latest 或 qlib accepted latest。
- 写 monitor config/scan/alerts。
- 触发 broker/order/quick-trade。
- 写 paper account。
- 训练模型、调参或跑回放收益筛选。

新增服务不包含网络库调用、HTTP write 请求、provider/monitor/broker/order endpoint 调用。

## 11. 未完成事项

- 尚未新增 `/api/tw-stock/agent/simple-chat` 路由；本阶段选择仅实现服务层，避免影响现有前端。
- 尚未改前端 Agent 面板；这是 Phase 4 范围。
- 尚未接入日更编排；这是 Phase 5 范围。
- 尚未做真实 OpenAI-compatible smoke；Phase 3 工作文档禁止真实 smoke。

## 12. 风险与需要审查的问题

1. simple chat 的 intent 分类是第一版规则。
   已覆盖 Phase 3 要求的高频问题和 blocked intents，但自然语言边界仍需 Phase 4/Phase 6 验收问题集继续检验。

2. output validator 复用本服务内的 unsafe terms。
   已覆盖 monitor/provider/broker/order/收益承诺等核心红线；后续可抽成共享安全模块，减少与 Phase 1 validator 的重复。

3. 当前未新增 API。
   这降低了前端影响面，但 Phase 4 或后续如果需要前端调用，需要审查路由 wiring 与网络 denylist。

## 13. 是否建议进入 Phase 4

建议进入 Phase 4，但仅限审查者复审通过后执行“前端 Agent 面板简化”。

Phase 4 仍必须保持：

- 前端只调用后端 `/api/tw-stock/agent/*`。
- 前端不接触 OpenAI key、base URL 或 OpenAI SDK。
- 不新增下单、仓位、quick-trade、broker、provider、accepted latest、monitor 操作入口。
- 展示 answer、citations、warnings、mode、signal_asof/target_date/checksum 和 research-only disclaimer。
