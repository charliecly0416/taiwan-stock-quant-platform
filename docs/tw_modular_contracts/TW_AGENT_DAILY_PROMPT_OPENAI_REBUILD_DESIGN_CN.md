# 台股 Agent 每日 Prompt + OpenAI 简化重构设计

生成日期：2026-06-19

## 1. 结论

该方案是可行的，而且比继续扩展复杂 Agent/tool 系统更适合当前台股产品阶段。

推荐方向：

```text
每日只读上下文构建
  -> DailyAgentPromptArtifact
  -> 简单后端 OpenAI 接口
  -> 结构化回答
  -> 前端只读展示
```

核心判断：用户真正关心的不是一个通用智能体，而是每天几个固定问题：

```text
今天策略是什么？
模型今天看好哪些股票？
排名第一是谁？
模拟策略显示哪些调入/调出观察？
某只股票当前排名、分数、趋势和策略状态如何？
明天的候选和风险点是什么？
```

这些问题不需要多工具 Agent、动态代码执行、外部搜索或复杂 action planner。只要每日 prompt 质量稳定，单次 OpenAI 调用即可给出可用回答。

## 2. 设计原则

本方案必须遵守项目宪法：

```text
只读研究 + 产品化候选展示 + 模拟账户
```

Agent 是解释层，不是决策层，也不是执行层。

硬性边界：

- 不下单。
- 不连接 broker。
- 不触发 quick-trade。
- 不写 monitor/config/alerts。
- 不切 provider accepted latest 或 qlib accepted latest。
- 不训练模型、不调参、不跑回放。
- 不直接读取实验 CSV。
- 不把回答写成真实买卖指令、目标仓位或收益承诺。

允许回答的语义：

```text
今日策略快照显示...
模型排序显示...
模拟策略拟调入/调出观察...
建议人工关注...
建议数据复核...
当前处于 pending/block，原因是...
```

禁止回答的语义：

```text
应该买入 X
应该卖出 Y
明天一定上涨
胜率是多少
买多少仓位
请自动下单
设置目标仓位
```

对于用户问“要买卖哪只”，Agent 应转换为：

```text
当前只读策略快照中的拟调入/拟调出观察，不构成交易建议。
```

## 3. 总体架构

目标是把复杂度前移到每日 artifact 构建，问答接口保持简单。

```text
CurrentStrategyContext API
ReadonlyStrategySnapshot
ReadonlyReplayWindow
PaperPortfolio latest decision
ProductizationStatus
Data freshness / pending status
        |
        v
scripts/build_tw_agent_daily_prompt_artifact.py
        |
        v
DailyAgentPromptArtifact
        |
        v
POST /api/tw-stock/agent/simple-chat
        |
        v
OpenAI Adapter
        |
        v
Answer JSON + citations + safety flags
```

其中 OpenAI 只消费 `DailyAgentPromptArtifact` 的压缩上下文和用户问题，不允许自行调用工具。

## 4. DailyAgentPromptArtifact 合同

建议新增每日 artifact：

```text
data_tw/artifacts/agent_daily_prompt/{signal_asof}/manifest.json
data_tw/artifacts/agent_daily_prompt/{signal_asof}/prompt_context.json
data_tw/artifacts/agent_daily_prompt/{signal_asof}/prompt_text.md
data_tw/artifacts/agent_daily_prompt/latest.json
```

`latest.json` 只是 Agent prompt latest pointer，不是 provider accepted latest，也不是 qlib accepted latest。

### 4.1 manifest 字段

```json
{
  "artifact_type": "tw_agent_daily_prompt",
  "schema_version": "tw_agent_daily_prompt_v1",
  "readonly_only": true,
  "not_order": true,
  "not_target_position": true,
  "production_trade_enabled": false,
  "signal_asof": "YYYY-MM-DD",
  "target_date": "YYYY-MM-DD",
  "model_ids": {
    "base": "e4_frozen_qlib_2018_2022",
    "treatment": "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025"
  },
  "strategy_rule": "top50_exit_one_worst_sell",
  "execution_price_mode": "next_open",
  "source_artifacts": {
    "current_strategy_context": "...",
    "readonly_strategy_snapshot": "...",
    "readonly_replay_window": "...",
    "paper_portfolio_decision": "..."
  },
  "validation": {
    "ok": true,
    "asof_alignment": "pass",
    "forbidden_action_audit": "pass",
    "max_prompt_tokens_estimate": 6000
  },
  "checksum": "sha256:..."
}
```

### 4.2 prompt_context.json 字段

建议只保留回答所需的最小上下文，避免把完整 CSV 或大 payload 塞给模型。

```json
{
  "schema_version": "tw_agent_daily_prompt_context_v1",
  "safety": {
    "readonly_only": true,
    "not_order": true,
    "not_target_position": true,
    "not_investment_advice": true,
    "production_trade_enabled": false
  },
  "date_context": {
    "signal_asof": "YYYY-MM-DD",
    "target_date": "YYYY-MM-DD",
    "display_asof": "YYYY-MM-DD",
    "execution_price_mode": "next_open",
    "execution_price_status": "available|pending|unavailable"
  },
  "model_context": {
    "base_model_id": "...",
    "treatment_model_id": "...",
    "ranking_source": "ltr_rerank_within_qlib_top50",
    "candidate_boundary": "qlib_top50"
  },
  "rankings": {
    "qlib_top10": [],
    "ltr_top10": [],
    "ltr_top50_compact": []
  },
  "strategy": {
    "strategy_rule": "top50_exit_one_worst_sell",
    "top_candidates": [],
    "exit_candidates": [],
    "skipped_or_blocked": []
  },
  "paper_portfolio": {
    "apply_allowed": false,
    "blocked_reason": "next_open_unavailable",
    "account_epoch": null,
    "cash": null,
    "positions_compact": []
  },
  "replay_summary": {
    "window": "2026_ytd",
    "metrics": {},
    "warnings": []
  },
  "freshness": {
    "status": "accepted|pending|mixed|unavailable",
    "warnings": []
  },
  "answer_policy": {
    "allowed_question_types": [],
    "blocked_question_types": [],
    "required_disclaimer": "仅供研究观察，不构成交易建议..."
  }
}
```

## 5. prompt_text.md 结构

`prompt_text.md` 是给 OpenAI 的每日系统上下文，不应由前端拼接。建议模板：

```md
# Role
你是 QuantDinger 台股只读研究助手。你只能解释给定上下文。

# Safety
- 不能下单、不能建议仓位、不能承诺收益。
- qlib score 是横截面排序分数，不是收益率、胜率、涨幅或买入概率。
- 用户问买卖时，只能解释只读策略快照中的拟调入/拟调出观察。

# Today Context
- signal_asof: ...
- target_date: ...
- execution_price_mode: next_open
- execution_price_status: ...
- model: ...
- strategy_rule: ...

# Rankings
## LTR Top 10
...

## Qlib Top 10
...

# Strategy Snapshot
## Top Candidates
...

## Exit Candidates
...

# Paper Portfolio
...

# Freshness / Pending
...

# Output Contract
只输出 JSON：
{
  "answer": "string",
  "intent": "string",
  "citations": ["string"],
  "warnings": ["string"],
  "blocked": false,
  "research_only_disclaimer": "string"
}
```

## 6. 问答接口设计

建议新增或重构为一个简单接口：

```text
POST /api/tw-stock/agent/simple-chat
```

请求：

```json
{
  "question": "今天的策略是什么？",
  "symbol": "2330",
  "max_items": 8
}
```

响应：

```json
{
  "ok": true,
  "mode": "openai|fallback|blocked",
  "intent": "today_strategy",
  "blocked": false,
  "answer": "...",
  "items": [],
  "citations": [],
  "warnings": [],
  "research_only_disclaimer": "仅供研究观察，不构成交易建议...",
  "context_digest": {
    "signal_asof": "YYYY-MM-DD",
    "target_date": "YYYY-MM-DD",
    "prompt_artifact": "data_tw/artifacts/agent_daily_prompt/.../manifest.json",
    "checksum": "sha256:..."
  }
}
```

后端流程：

```text
classify question
  -> blocked intent 直接拒绝
  -> load latest DailyAgentPromptArtifact
  -> validate manifest/checksum/readonly flags
  -> compose OpenAI messages from prompt_text + compact user question
  -> require JSON output
  -> validate answer schema/citations/safety terms
  -> unsafe output fallback/refusal
```

## 7. Intent 设计

第一版只支持少量高频问题，不做通用闲聊。

建议 intent：

| intent | 示例问题 | 回答来源 |
| --- | --- | --- |
| `today_strategy` | 今天策略是什么？ | strategy snapshot + paper portfolio gate |
| `tomorrow_candidates` | 明天关注哪些？ | signal_asof -> target_date candidates |
| `top_ranked_stock` | 排名第一是谁？ | ltr_top10 / qlib_top10 |
| `top_n_rankings` | 前十有哪些？ | rankings |
| `strategy_buy_sell_observation` | 今天要买卖哪只？ | top_candidates / exit_candidates，转成观察语义 |
| `single_symbol_status` | 2330 怎么样？ | ranking + strategy + freshness |
| `paper_apply_status` | 今天能应用到模拟账户吗？ | paper_portfolio.apply_allowed |
| `execution_price_pending` | 为什么不能应用？ | execution_price_status / blocked_reason |
| `data_freshness` | 数据新鲜度如何？ | freshness |
| `replay_summary` | 今年回放表现怎样？ | readonly replay summary |

blocked intent：

```text
place_order
auto_trade
target_position
portfolio_weight
guaranteed_profit
qlib_ops_refresh_publish
qlib_retrain_or_tune
broker_operation
monitor_write
```

## 8. 回答策略

### 8.1 “今天策略是什么？”

回答模板：

```text
今天的只读策略口径是 {strategy_rule}：在 Qlib top50 作为候选/退出边界的基础上，使用 LTR 在 top50 内重排买入观察顺序。当前 signal_asof={signal_asof}，target_date={target_date}，执行价口径为 next_open。策略快照显示的调入观察包括...，调出观察包括...。这不是订单，也不是目标仓位。
```

### 8.2 “要买卖哪只？”

不能直接答“买 X、卖 Y”。应答：

```text
当前只能给出只读策略观察。快照中的拟调入观察是...，拟调出观察是...；如果 next_open 或 paper apply gate 未通过，则只能等待数据齐备或人工复盘。以上不构成交易建议。
```

### 8.3 “排名第一的是谁？”

应明确排名来源：

```text
按当前默认 LTR treatment 排名，第一是 {symbol}，LTR rank=1，buy_score=...。它仍位于 Qlib top50 候选池内。qlib score/LTR score 是排序分数，不是明日涨幅或胜率。
```

### 8.4 “某只股票怎么样？”

回答结构：

```text
{symbol} 当前是否在 qlib_top50 / ltr_top50
qlib_rank / ltr_rank / score
是否出现在 top_candidates 或 exit_candidates
数据新鲜度和 warnings
人工复盘提示
```

## 9. OpenAI 调用约束

延续后端 only 配置：

```text
ENABLE_TW_STOCK_AGENT_OPENAI=true|false
OPENAI_API_KEY=<backend-only>
TW_STOCK_AGENT_OPENAI_BASE_URL=<optional>
TW_STOCK_AGENT_OPENAI_MODEL=<model>
TW_STOCK_AGENT_OPENAI_TIMEOUT_SECONDS=20
```

既有路线中曾使用过 OpenAI-compatible endpoint 做真实 smoke，配置形态如下：

```text
TW_STOCK_AGENT_OPENAI_BASE_URL=https://chat.pku.edu.cn/v1
TW_STOCK_AGENT_OPENAI_MODEL=gpt-4.1-mini
OPENAI_API_KEY=<backend-only secret>
```

该 URL 只能作为后端 OpenAI-compatible base URL 示例。真实 `OPENAI_API_KEY` 不得写入文档、代码、测试、截图、日志或前端；执行者如需真实 smoke，必须从后端运行环境读取密钥，并在报告中只写 `<backend-only secret>`。

前端不得：

- 读取 `OPENAI_API_KEY`。
- 传递 `OPENAI_API_KEY`。
- 直连 OpenAI 或 OpenAI-compatible endpoint。
- 拼接系统 prompt。

后端 OpenAI adapter 约束：

- temperature 建议 `0.1-0.2`。
- 必须要求 JSON 输出。
- 必须设置 timeout。
- 只发送 prompt artifact 内容和用户问题。
- 不发送密钥、数据库连接、完整本地路径之外的敏感配置。
- 不允许 tool/function calling。

## 10. 安全校验

输出后必须做 deterministic validation：

```text
JSON schema valid
intent 与分类结果一致
citations 只能来自 prompt artifact allowlist
answer 不包含 forbidden terms
research_only_disclaimer 存在
blocked intent 不调用 OpenAI
```

forbidden terms 至少包括：

```text
必须买入
必须卖出
保证上涨
保证收益
目标仓位
下单
自动交易
broker
IBKR
quick-trade
qlib refresh
publish
retrain
调参
```

如果模型输出不合格，返回 deterministic fallback，而不是把原始模型输出展示给用户。

## 11. 与现有实现的关系

当前代码已有：

```text
GET /api/tw-stock/agent/context
POST /api/tw-stock/agent/preview
POST /api/tw-stock/agent/chat
backend/app/services/tw_stock_agent_guardrails.py
backend/app/services/tw_stock_agent_openai.py
backend/app/services/tw_stock_agent_chat.py
```

重构时不需要推倒全部实现。建议演进：

1. 保留 `tw_stock_agent_openai.py` 的 backend-only adapter。
2. 保留 `tw_stock_agent_guardrails.py` 的 blocked intent 分类。
3. 新增 `DailyAgentPromptArtifact` 构建脚本和 validator。
4. 将 `tw_stock_agent_chat.py` 的上下文来源从动态 service preview 改为 latest prompt artifact。
5. 保留 deterministic fallback，作为 OpenAI disabled、API error、输出不合格时的回答。
6. 前端继续调用后端 `/agent/chat` 或新增 `/agent/simple-chat`，不接触 OpenAI。

## 12. 新增文件建议

```text
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_OPENAI_REBUILD_DESIGN_CN.md
scripts/build_tw_agent_daily_prompt_artifact.py
scripts/validate_tw_agent_daily_prompt_artifact.py
backend/app/services/tw_stock_agent_daily_prompt.py
backend/app/services/tw_stock_agent_simple_chat.py
backend/tests/test_tw_stock_agent_daily_prompt.py
backend/tests/test_tw_stock_agent_simple_chat.py
frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
```

## 13. Validator 要求

`validate_tw_agent_daily_prompt_artifact.py` 至少检查：

- manifest 存在且 `artifact_type=tw_agent_daily_prompt`。
- `readonly_only=true`。
- `production_trade_enabled=false`。
- `not_order=true`。
- `not_target_position=true`。
- source artifact 路径存在。
- signal_asof / target_date / strategy_rule 与 current strategy context 对齐。
- prompt_text 不包含真实交易 action 词。
- prompt_context 不包含 broker/order/quick-trade endpoint。
- token 估算不超过配置上限。
- checksum 与 prompt_context/prompt_text 对齐。

## 14. 测试与验收

后端单测：

```bash
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt.py backend/tests/test_tw_stock_agent_simple_chat.py -q
```

静态安全检查：

```bash
rg -n "OPENAI_API_KEY|api.openai.com|chat/completions" frontend/src frontend/tests
rg -n "quick-trade|broker|order|accepted latest|provider publish" backend/app/services/tw_stock_agent* docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_OPENAI_REBUILD_DESIGN_CN.md
```

前端检查：

```bash
cd frontend
corepack pnpm build
node tests/unit/tw-stock-agent-simple-chat-check.mjs
```

验收问题集：

```text
今天策略是什么？
明天关注哪些股票？
排名第一的是谁？
2330 现在在不在候选里？
今天有没有调出观察？
为什么模拟账户不能应用？
数据新鲜度如何？
帮我买排名第一的股票。
给我 50% 仓位买 2330。
刷新 qlib 并重新生成策略。
```

前 7 个应正常只读回答，后 3 个必须 blocked。

## 15. 可以进一步完善的地方

### 15.1 分层 prompt

不要把所有内容塞进一个长 prompt。建议分层：

```text
system safety prompt
每日 market/strategy context
用户问题
少量 intent-specific context
```

如果用户问单只股票，只发送该股票和 top summary，不发送完整 top50。

### 15.2 固定回答骨架

对高频 intent 使用固定结构，LLM 只负责自然语言组织：

```text
结论摘要
依据
候选/调出观察
风险或 pending
只读声明
```

这样回答稳定，也方便前端展示。

### 15.3 引用与可追溯

每个回答必须带 citation：

```text
agent_prompt:{signal_asof}:{checksum}
readonly_snapshot:{asof}
model_signal:{model_id}:{signal_asof}
paper_decision:{decision_id}
```

前端可以在“查看来源”里展示这些引用。

### 15.4 人工复盘友好

Agent 不应只说“买卖”，而要帮助用户复盘：

```text
为什么排名靠前
是否与 Qlib top50 边界一致
是否出现在策略候选
数据是否 pending
是否需要等 next_open
```

### 15.5 缓存与成本控制

- prompt artifact 每日生成一次。
- 相同问题 + 同一 prompt checksum 可短期缓存。
- OpenAI disabled 时 deterministic fallback 仍可用。
- prompt token 上限必须可配置。

## 16. 推荐实施阶段

### Phase A：合同与 Artifact

- 新增 DailyAgentPromptArtifact 合同。
- 新增 build/validate 脚本。
- 从 current strategy context、snapshot、paper decision 构建 prompt。

### Phase B：Simple Chat API

- 新增或重构 `/api/tw-stock/agent/chat`。
- 使用 prompt artifact + OpenAI adapter。
- 保留 deterministic fallback。

### Phase C：前端简化

- 面板只保留问题输入、推荐问题、回答、来源、warnings。
- 不暴露 tool、skill、执行类概念。

### Phase D：验收

- 后端单测。
- 前端静态检查。
- Playwright 网络 denylist。
- OpenAI mock smoke。
- 可选真实 OpenAI-compatible smoke，但不得记录密钥。

## 17. 最终目标

这个 Agent 不追求“什么都能做”。它只做一件事：

```text
把每日模型、策略、组合和数据状态解释清楚。
```

只要 daily prompt artifact 足够准确，简单 OpenAI 接口就能满足大多数用户问题，同时保持安全、稳定和可审查。
