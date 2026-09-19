# Phase 0 执行报告：台股 Agent 每日 Prompt + OpenAI 重构

生成日期：2026-06-19

## 1. 阶段目标

本阶段目标是冻结台股 Agent 后续路线，确认当前代码、文档、API 和前端基础能否承接“每日只读上下文 -> DailyAgentPromptArtifact -> 简单后端 OpenAI 接口 -> 前端只读展示”的重构路线。

本阶段严格限定为只读审计：

- 不改业务代码。
- 不新增 API。
- 不调用 OpenAI。
- 不触发真实数据抓取、provider publish、accepted latest 切换、monitor 写入、broker/order/quick-trade。
- 只输出本执行报告，等待审查者审查。

## 2. 实际完成内容

已按要求阅读并对齐以下文档：

- `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`
- `docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_OPENAI_REBUILD_DESIGN_CN.md`
- `docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_OPENAI_REBUILD_EXECUTION_AND_REVIEW_PLAN_CN.md`
- `docs/tw_modular_contracts/AGENT_READONLY_CONTEXT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/FRONTEND_AGENT_PANEL_CONTRACT_CN.md`

已只读梳理以下现有 Agent 相关实现：

- `backend/app/services/tw_stock_agent_context.py`
- `backend/app/services/tw_stock_agent_chat.py`
- `backend/app/services/tw_stock_agent_openai.py`
- `backend/app/services/tw_stock_agent_guardrails.py`
- `backend/app/routes/tw_stock.py`
- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/src/api/tw-stock.js`

已额外按只读安全边界审查规则核对 forbidden action 语义，区分了真实危险入口、只读声明、模拟账户和历史回测语义。

## 3. 当前 Agent API 与服务现状

### 3.1 后端路由

当前后端已存在三类 Agent 路由，均挂在 `backend/app/routes/tw_stock.py`：

| API | 方法 | 当前行为 |
| --- | --- | --- |
| `/api/tw-stock/agent/context` | GET | 返回当前 Agent 可用的只读上下文，主要来自 cross-analysis/latest 与 qlib accepted latest 摘要。 |
| `/api/tw-stock/agent/preview` | POST | 不调用 OpenAI，基于 guardrails 和当前动态上下文生成 deterministic research-only answer preview。 |
| `/api/tw-stock/agent/chat` | POST | 先生成 preview，再按 guardrails 判断是否 blocked；OpenAI 启用时调用后端 adapter，否则返回 deterministic fallback。 |

这三类 API 目前不是基于 DailyAgentPromptArtifact，而是实时调用 `TWStockAgentContextService` 构建动态 preview。

### 3.2 `TWStockAgentContextService`

`backend/app/services/tw_stock_agent_context.py` 当前负责：

- 从 `TWStockCrossAnalysisService.latest(...)` 读取 accepted qlib signal 与交叉分析摘要。
- 生成 `top30_preview`、`focus_watch_preview`、`divergence_preview`、`data_review_preview`。
- 返回 freshness、allowed/blocked intents、disclaimers、research-only trading flags。
- 对单只股票调用 `symbol_detail(...)` 生成只读摘要。
- blocked intent 直接返回 `BLOCKED_ANSWER`，不进入 OpenAI。

当前上下文语义偏向“qlib accepted latest + cross-analysis + trend”，尚未覆盖大设计文档要求的 current strategy context、readonly strategy snapshot、readonly replay window、paper portfolio decision、productization status 等标准 source artifacts。

### 3.3 `TWStockAgentChatService`

`backend/app/services/tw_stock_agent_chat.py` 当前流程是：

```text
context_service.preview
  -> skill_registry.select
  -> blocked preview 直接 fallback
  -> OpenAI status
  -> OpenAI disabled 时 deterministic fallback
  -> controlled_context
  -> OpenAI complete
  -> JSON/schema/citation/safety validation
  -> invalid 或 unsafe 时 fallback/refusal
```

当前已具备以下安全机制：

- blocked intent 不调用 OpenAI。
- OpenAI disabled 或 missing key 时返回 deterministic fallback。
- 要求模型输出 JSON。
- 校验 answer、citations、warnings、research_only_disclaimer、intent。
- citations 必须来自 preview allowlist。
- unsafe answer terms 命中时覆盖为拒绝回答。

主要差距是 `controlled_context` 当前由动态 preview 生成，不是从已验证的 DailyAgentPromptArtifact 读取。

### 3.4 `TWStockAgentOpenAIAdapter`

`backend/app/services/tw_stock_agent_openai.py` 当前是 backend-only adapter：

- 只从后端环境变量读取 `OPENAI_API_KEY`、`ENABLE_TW_STOCK_AGENT_OPENAI`、model、base URL、timeout。
- 默认 disabled。
- 调用 `chat/completions`，设置 `response_format={"type":"json_object"}`。
- system prompt 明确禁止下单、仓位建议、收益承诺、qlib refresh/publish/retrain/tune。
- 支持 `MockTWStockAgentOpenAIAdapter` 用于测试。

结论：该 adapter 可以保留为后续 Phase 3 的基础，但 OpenAI 输入应从 `controlled_context` 改为 `prompt_text.md + 用户问题 + 最小 intent context`，并继续禁止 tool/function calling。

### 3.5 `TWStockAgentGuardrails`

`backend/app/services/tw_stock_agent_guardrails.py` 当前提供：

- `RESEARCH_ONLY_DISCLAIMER`
- `BLOCKED_ANSWER`
- allowed intents 和 blocked intents。
- 对下单、自动交易、仓位、组合权重、broker、保证收益、qlib refresh/publish/retrain/tune 等语义进行 deterministic classify。
- 单只股票、top30/top50、focus watch、divergence、freshness、data review 等只读问题分类。

结论：guardrails 是可复用模块。后续需要扩展 intent 到设计文档中的 `today_strategy`、`tomorrow_candidates`、`top_ranked_stock`、`strategy_buy_sell_observation`、`paper_apply_status`、`execution_price_pending`、`replay_summary` 等，但必须保持 blocked intent 优先且 blocked 时不调用 OpenAI。

### 3.6 前端 API 与面板

`frontend/src/api/tw-stock.js` 当前只暴露：

- `getTwStockAgentContext({ maxItems })` -> GET `/agent/context`
- `chatTwStockAgent({ question, symbol, maxItems })` -> POST `/agent/chat`

未发现前端 Agent API 读取或传递 OpenAI key、OpenAI base URL 或直连 OpenAI endpoint。

`frontend/src/views/tw-stock-monitor/index.vue` 当前 Agent 面板：

- 展示“台股研究助手”和 research-only tag。
- 提供建议问题、文本输入、发送按钮。
- 展示 answer、items、citations、warnings、mode、blocked 状态、research-only disclaimer。
- OpenAI disabled 时展示 deterministic fallback 提示。
- blocked 时展示研究边界阻断提示。
- 当前提示问题仍围绕 top30、模型/趋势支持、分歧、数据复核、单只股票指标、新鲜度。

主要差距是前端文案和问题集尚未聚焦大设计文档定义的每日策略、明日候选、排名第一、调入/调出观察、模拟账户 apply gate、execution price pending 等高频产品问题。

## 4. 可复用模块

以下模块建议后续保留并演进：

- `tw_stock_agent_openai.py`：保留 backend-only OpenAI adapter、timeout、JSON-only、disabled fallback 基础；后续改为消费 DailyAgentPromptArtifact。
- `tw_stock_agent_guardrails.py`：保留 deterministic blocked intent 分类与 disclaimer；后续补充 Daily Prompt 路线的新 allowed intents。
- `tw_stock_agent_chat.py` 的输出 validation 思路：保留 JSON schema、citation allowlist、unsafe answer override、fallback 机制；后续迁移到 simple chat 服务。
- `/agent/chat` API 形态：可以保留兼容前端，也可以新增 `/agent/simple-chat`；设计文档允许二选一。
- 前端 Agent 面板的基础展示能力：answer、warnings、citations、mode、blocked、disclaimer 可复用。
- `MockTWStockAgentOpenAIAdapter`：后续可用于 Phase 3 mock OpenAI 测试。

## 5. 需要替换或重构的动态上下文部分

当前最需要替换的是 `TWStockAgentContextService.preview(...) -> cross_analysis latest/symbol_detail -> controlled_context` 这条动态上下文链路。

后续目标链路应改为：

```text
DailyAgentPromptArtifact latest pointer
  -> manifest/checksum/readonly flags validation
  -> prompt_context.json / prompt_text.md
  -> intent-specific compact context
  -> backend-only OpenAI adapter
  -> answer validation / deterministic fallback
```

具体重构点：

- `tw_stock_agent_context.py` 当前直接读取 cross-analysis 动态服务，不符合“OpenAI 只消费每日 artifact”的目标；后续应降级为 artifact builder 的上游 source 或被新的 `tw_stock_agent_daily_prompt.py` 替代。
- `tw_stock_agent_chat.py` 当前在请求时即时构造 `controlled_context`，后续应改为读取已验证 prompt artifact。
- 当前 citations 为 `qlib:accepted_latest:{run_id}:{asof}`、`cross-analysis:latest:{bucket}` 等，应扩展为 `agent_prompt:{signal_asof}:{checksum}`、`readonly_snapshot:{asof}`、`paper_decision:{decision_id}` 等可追溯引用。
- 当前 items 主要是 cross-analysis compact item，缺少 strategy top candidates、exit candidates、paper apply gate、execution_price_status、replay summary。
- 当前前端建议问题和展示字段需要在 Phase 4 对齐 Daily Prompt 合同。

## 6. 与大设计文档的对应关系

| 大设计章节 | 当前状态 | Phase 0 判断 |
| --- | --- | --- |
| 设计原则：Agent 是解释层，不是决策/执行层 | 当前 guardrails、disclaimer、fallback 基本符合。 | 可继承，但需继续收紧买卖语义。 |
| 总体架构：DailyAgentPromptArtifact 为中心 | 当前未实现。 | Phase 1/2 必须补合同、validator、构建脚本。 |
| DailyAgentPromptArtifact 合同 | 当前不存在。 | Phase 1 首要任务。 |
| prompt_text.md 由后端生成，不由前端拼接 | 当前 system prompt 在后端 adapter，前端不拼接 prompt。 | 方向一致，但需迁移为每日 artifact。 |
| 问答接口 `/agent/simple-chat` 或重构 `/agent/chat` | 当前有 `/agent/chat`。 | 可保留兼容路径，内部后续改 simple chat。 |
| Intent 设计 | 当前 intent 偏 top30/cross-analysis。 | 需要新增 daily strategy / candidate / paper gate / replay 等 intent。 |
| OpenAI 调用约束 | 当前 backend-only、默认 disabled、JSON-only。 | 可复用，后续需显式禁止 tool/function calling 并绑定 artifact 输入。 |
| 安全校验 | 当前已有 JSON/citation/disclaimer/unsafe terms 校验。 | 可复用并扩展到 artifact citation allowlist。 |
| 前端不接触 OpenAI | 当前符合。 | Phase 4 继续保持。 |

## 7. 只读安全边界确认

本阶段没有执行任何 POST/PUT/PATCH/DELETE 请求，没有调用 OpenAI，没有触发数据抓取、provider publish、accepted latest 切换、monitor 写入、broker/order/quick-trade。

对当前 Agent 代码的只读边界判断：

- Agent 后端路由 `/agent/context`、`/agent/preview`、`/agent/chat` 本身不执行交易、monitor、provider 或 accepted latest 写入。
- `tw_stock_agent_guardrails.py` 已阻断下单、自动交易、目标仓位、组合权重、broker、保证收益、qlib refresh/publish/retrain/tune 等语义。
- `tw_stock_agent_chat.py` blocked preview 时不调用 OpenAI；unsafe model output 会被覆盖为拒绝回答。
- `tw_stock_agent_openai.py` 是后端 adapter，前端未暴露 OpenAI key。
- 前端 Agent 面板未提供下单、仓位输入、quick-trade、broker、provider publish、accepted latest 或 monitor 操作入口。

静态检索中出现的 `orders`、`broker`、`accepted latest`、`monitor` 相关词主要来自仓库内已有模拟订单、monitor、Option C ops 路由或只读声明，不属于本 Agent Phase 0 的新增行为；但后续前端网络 denylist 和 Agent 代码静态检查仍应严格限定扫描范围，避免把既有非 Agent 路由误判为 Agent 新增能力。

## 8. 未改代码确认

本阶段未修改业务代码、API 代码、前端代码、脚本、配置或测试。

本阶段新增/更新的文件仅限：

- `docs/tw_agent_daily_prompt_rebuild/PHASE0_EXECUTION_REPORT_CN.md`

为放置报告创建了目录：

- `docs/tw_agent_daily_prompt_rebuild/`

注意：开始执行前工作树已有与本任务无关或上游准备中的改动，包括 `comment.md`、若干 `docs/tw_modular_contracts/*` 文档新增/修改。本阶段未回滚、未覆盖这些既有改动。

## 9. 未调用 OpenAI 确认

本阶段没有运行任何会调用 OpenAI 的后端服务、测试、脚本或 HTTP 请求。

本阶段只通过文件读取确认了：

- OpenAI adapter 默认由 `ENABLE_TW_STOCK_AGENT_OPENAI` 控制。
- API key 只从后端环境变量读取。
- 前端未读取或传递 OpenAI key。

## 10. 风险与需要审查的问题

1. 当前 Agent 上下文仍是动态 cross-analysis preview，不是 DailyAgentPromptArtifact。
   这是后续路线的核心替换点，Phase 1/2 必须先建立 artifact 合同、validator 和构建脚本，不能直接改 `/agent/chat` 接 OpenAI。

2. 当前 `skill_registry` 命名可能给审查者造成“复杂 Agent/tool 扩展”的误解。
   Phase 3 需要审查该 registry 是否只是模型上下文标签，还是应从 simple chat 路线中移除，避免偏离“不做复杂 Agent/tool”的目标。

3. 当前 allowed answer style 包含“建议关注/建议回避”。
   该语义在研究上下文中可接受，但 Phase 3/4 应考虑改为“观察/人工复盘/数据复核/拟调入观察/拟调出观察”，降低被理解为交易建议的风险。

4. 当前前端 Agent 面板仍围绕 top30/cross-analysis。
   Phase 4 需要改成每日策略问题集，并展示 signal_asof、target_date、checksum、execution_price_status、paper apply gate 等 Daily Prompt 字段。

5. 当前 OpenAI adapter 使用 `/chat/completions`。
   大设计只要求 backend-only JSON 输出，没有强制 Responses API；审查者需确认后续是否继续沿用该 adapter，或统一到项目当前 OpenAI 接口标准。

6. 当前 Phase 0 未运行测试。
   这是按阶段要求执行的只读审计；Phase 0 不改代码、不跑服务、不调用 OpenAI。后续 Phase 1 起必须为 validator/golden sample 增加可运行测试证据。

7. 当前报告基于文件审计，没有实际启动后端或前端。
   如审查者需要运行只读 smoke，应单独在审查阶段执行，并确保不触发写入或 OpenAI。

## 11. 是否建议进入 Phase 1

建议进入 Phase 1，但仅限执行“DailyAgentPromptArtifact 合同与 Validator”。

Phase 1 应明确只做：

- 新增或补充 DailyAgentPromptArtifact 合同文档。
- 实现 `scripts/validate_tw_agent_daily_prompt_artifact.py`。
- 新增 pass/fail golden sample。
- 检查 readonly flags、not_order、not_target_position、production_trade_enabled=false、当前产品模型、默认策略、next_open、source artifact、forbidden action、checksum。

Phase 1 仍不应：

- 构建真实生产 prompt。
- 调用 current strategy API。
- 调用 OpenAI。
- 修改 `/agent/chat`。
- 修改前端。
- 触发 provider publish、accepted latest 切换、monitor 写入、broker/order/quick-trade。
