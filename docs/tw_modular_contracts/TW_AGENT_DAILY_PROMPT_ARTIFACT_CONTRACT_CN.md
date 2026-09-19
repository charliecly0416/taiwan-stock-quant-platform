# 台股 Agent DailyAgentPromptArtifact 合同

生成日期：2026-06-19

## 1. 目的

`DailyAgentPromptArtifact` 是台股研究 Agent 后续简化路线的唯一每日上下文输入。它把当前产品模型、策略、只读快照、模拟账户 gate、数据新鲜度和回答安全策略压缩成可验证 artifact，供后端 simple chat 使用。

Agent 只能解释该 artifact，不是决策层、执行层、交易系统、provider 运维系统或 monitor 写入入口。

## 2. 文件结构

生产 artifact 路径：

```text
data_tw/artifacts/agent_daily_prompt/{signal_asof}/manifest.json
data_tw/artifacts/agent_daily_prompt/{signal_asof}/prompt_context.json
data_tw/artifacts/agent_daily_prompt/{signal_asof}/prompt_text.md
data_tw/artifacts/agent_daily_prompt/latest.json
```

`latest.json` 仅是 Agent prompt latest pointer：

- 不是 provider accepted latest。
- 不是 qlib accepted latest。
- 不得触发 provider publish。
- 不得触发 provider accepted latest 或 qlib accepted latest 切换。
- Phase 1 不生成真实生产 `latest.json`，只允许 golden sample 模拟 pointer 语义。

## 3. `manifest.json` 必填字段

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
  "source_artifacts": {},
  "validation": {
    "ok": true
  },
  "checksum": "sha256:<hex>"
}
```

`source_artifacts` 在生产模式必须指向存在的只读 source artifact。Phase 1 golden sample 可使用 `status="missing_allowed_for_golden_sample"`，但只有 validator 显式启用 `--allow-golden-missing-sources` 时才允许通过，并且必须输出 warning。

## 4. `prompt_context.json` 必填字段

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
    "execution_price_mode": "next_open"
  },
  "model_context": {
    "base_model_id": "e4_frozen_qlib_2018_2022",
    "treatment_model_id": "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025",
    "ranking_source": "ltr_rerank_within_qlib_top50",
    "candidate_boundary": "qlib_top50"
  },
  "answer_policy": {
    "required_disclaimer": "仅供研究观察，不构成交易建议..."
  }
}
```

允许包含 `rankings`、`strategy`、`paper_portfolio`、`replay_summary`、`freshness` 等只读摘要，但不得包含 broker、order、quick-trade、target position、monitor config、monitor scan、monitor alerts write、provider publish、accepted latest switch、qlib refresh、retrain 或调参入口。

## 5. `prompt_text.md` 必须包含

- research-only 或只读边界说明。
- qlib score 是横截面排序分数，不是收益率、胜率、涨幅或买入概率。
- JSON 输出合同说明。
- 研究观察语义，不是订单、目标仓位或收益承诺。

`prompt_text.md` 不得包含行动性交易执行语义，例如要求下单、连接券商、设置目标仓位、保存监控配置、触发 monitor scan、写 monitor alerts、刷新 qlib 或发布 provider。

## 6. Checksum 规则

`manifest.checksum` 固定为：

```text
sha256(prompt_context.json raw bytes + "\n" + prompt_text.md raw bytes)
```

manifest 自身不参与 checksum，避免自引用。validator 必须复算 checksum 并与 `manifest.checksum` 精确匹配。

## 7. 安全红线

validator 必须阻断 manifest、prompt_context、prompt_text 中的行动性危险语义或字段，包括但不限于：

```text
broker
quick-trade
orders
target-position
target_position
target_weight
自动买入
自动卖出
目标仓位
下单
提交订单
连接券商
monitor config
monitor scan
monitor alerts
save monitor
/monitor/config
/monitor/scan
/monitor/alerts
保存监控配置
触发 monitor scan
写 monitor alerts
刷新 provider
切换 accepted latest
provider publish
qlib refresh
retrain
调参
保证收益
保证上涨
胜率承诺
上涨概率
```

允许这些词只出现在明确的 `answer_policy.blocked_question_types`、安全边界说明、拒绝语义、validator 禁止词表或 fail golden sample 中。生产 pass artifact 不应依赖危险词白名单。

## 8. Validator 模式

生产模式：

- source artifact 路径必须存在。
- checksum 必须可复算。
- forbidden action audit 必须通过。
- 只读 flags、模型、策略、执行价口径必须严格匹配。

Golden sample 模式：

- 仅在传入 `--allow-golden-missing-sources` 时允许 source artifact 使用 `missing_allowed_for_golden_sample`。
- 仍必须校验 checksum、安全 flags、模型、策略、执行价口径、forbidden action。
- fail sample 必须稳定失败。

## 9. 与大设计文档关系

本文固定 `TW_AGENT_DAILY_PROMPT_OPENAI_REBUILD_DESIGN_CN.md` 中第 4 节 DailyAgentPromptArtifact 合同和第 13 节 Validator 要求。后续 Phase 2 构建脚本、Phase 3 simple chat 和 Phase 4 前端面板都必须以本合同为输入边界，不得绕过 artifact 直接向 OpenAI 发送动态服务 payload。
