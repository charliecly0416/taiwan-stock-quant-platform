# Phase 0 到 Phase 6 最终总结：台股 Agent 每日 Prompt + OpenAI 简化路线

生成日期：2026-06-19

## 1. 最终结论

最终结论：通过，建议接受本路线。

本路线已完成从设计、合同、artifact builder、Simple Chat 后端服务、前端 Agent 面板接入、日更编排 gate 到最终浏览器网络审计的闭环。最终形态为：

```text
DailyAgentPromptArtifact
  -> TWStockAgentSimpleChatService
  -> /api/tw-stock/agent/simple-chat
  -> 前端 Agent 面板只读展示
  -> disabled/mock OpenAI 安全路径
  -> 日更默认关闭/dry-run 的 Agent prompt build gate
```

最终验收未发现阻塞性安全问题。Playwright browser binary 缺失问题已解决，并已补跑真实浏览器只读网络审计，结果通过。

## 2. 最终安全边界

本路线接受范围仅限 research-only / readonly：

- 只读 DailyAgentPromptArtifact。
- 只读 Simple Chat 后端服务。
- 前端只读 Agent 面板展示。
- disabled/mock OpenAI 安全验收路径。
- 日更 Agent prompt build 默认关闭、默认 dry-run、默认不 publish latest。

明确不接受或不授权：

- broker/order/quick-trade。
- monitor config/scan/alerts 写入。
- provider publish 或 accepted latest 切换。
- 前端直连 OpenAI 或携带 OpenAI key。
- 自动训练、调参、收益筛选、收益承诺、上涨概率承诺。
- 真实 OpenAI key 出现在代码、日志、报告、截图或前端。

## 3. 阶段总结

| 阶段 | 执行目标 | 初审结论 | 修复/复审 | 最终状态 |
| --- | --- | --- | --- | --- |
| Phase 0 | 路线设计与审查职责确认 | 有条件通过 | 无需 repair | 允许进入 Phase 1 |
| Phase 1 | DailyAgentPromptArtifact 合同与 validator | 不通过 | 修复 monitor config/scan/alerts 红线后通过 | 允许进入 Phase 2 |
| Phase 2 | Artifact builder 与 fixture/golden sample | 通过 | 无阻塞修复 | 允许进入 Phase 3 |
| Phase 3 | Simple Chat 后端服务与 OpenAI adapter 安全校验 | 不通过 | 修复英文/字段级 order、target position、target weight 输出拦截后通过 | 允许进入 Phase 4 |
| Phase 4 | 前端 Agent 面板切到 Simple Chat | 通过 | 无阻塞修复 | 允许进入 Phase 5 |
| Phase 5 | 日更编排可选接入 Agent prompt build | 通过 | 无阻塞修复 | 允许进入 Phase 6 |
| Phase 6 | 端到端最终验收 | 通过，原报告留 Playwright 缺口 | 已补验 Playwright 网络审计通过 | 最终接受 |

## 4. Phase 0：设计与职责

Phase 0 主要确认路线是否合理，以及审查者职责和阶段边界是否清楚。

审查结论：有条件通过。

关键放行条件：

- Phase 1 只能做 `DailyAgentPromptArtifact` 合同与 validator。
- 不得提前实现 chat API。
- 不得构建真实生产 prompt。
- 不得调用 OpenAI。
- 不得修改前端。
- 不得触发 provider/accepted latest/monitor/broker/order/quick-trade。

Phase 0 的价值在于把路线拆成可审查的窄阶段，避免一开始把 prompt、OpenAI、前端和日更编排混在一起。

## 5. Phase 1：合同与 Validator

Phase 1 初审结论：不通过。

阻塞原因：validator 缺少 monitor 写入红线，可能放行以下语义：

```text
monitor config
monitor scan
monitor alerts
```

这是只读边界的 High 风险，因为 Agent prompt artifact 一旦允许这些语义进入上下文或输出，后续 Simple Chat 和前端展示都可能继承风险。

Repair 后复审结论：通过。

修复结果：

- validator 补齐 monitor config/scan/alerts forbidden patterns。
- 合同、golden sample、pytest 均覆盖 monitor 写入红线。
- Phase 1 无剩余必须修复项。

最终状态：允许进入 Phase 2。

## 6. Phase 2：Artifact Builder

Phase 2 审查结论：通过。

执行内容：

- 增加 Daily Agent Prompt artifact builder。
- 使用本地 fixture/source artifacts 构建 prompt artifact。
- 默认 dry-run。
- publish latest 仅在显式参数下执行。
- validator 作为 builder 的放行 gate。

安全判断：

- 不调用 OpenAI。
- 不改前端。
- 不触发 provider publish。
- 不切换 accepted latest。
- 不写 monitor。
- 不触发 broker/order/quick-trade。

残余低风险：生产 source artifacts 物化链路仍需后续稳定化；Phase 2 使用 fixture/golden sample 证明 builder 合同成立，不代表生产源已经完整。

最终状态：允许进入 Phase 3。

## 7. Phase 3：Simple Chat 后端服务

Phase 3 初审结论：不通过。

阻塞原因：模型输出安全校验对英文/字段级危险语义覆盖不足，测试暴露这些 unsafe 输出会被放行：

```text
Please place orders for 2330.
Set target_weight to 50% for 2330.
Use target_position for 2330.
```

这是 Critical/Medium 之间的关键安全问题：虽然当时还未接前端，但后端服务层是 Agent 输出最后一道边界，不能依赖前端拦截。

Repair 后复审结论：通过。

修复结果：

- `_unsafe_answer_terms` 覆盖 `order/orders/place orders`。
- 覆盖 `target_position`、`target-position`、`target weight`、`target_weight`。
- dangerous model output 会转为 blocked/refusal。
- forged citations、invalid JSON、unsafe answer 均会 fallback 或 blocked。

最终状态：允许进入 Phase 4。

## 8. Phase 4：前端 Agent 面板简化

Phase 4 审查结论：通过。

执行内容：

- 新增后端路由 `POST /api/tw-stock/agent/simple-chat`。
- 前端新增 `simpleChatTwStockAgent(...)`。
- Agent 面板从复杂 Agent/skills 旧路径切到 Simple Chat 路径。
- 前端展示 answer、citations、warnings、mode、blocked、context digest、research disclaimer。

安全判断：

- 前端不直连 OpenAI。
- 前端不发送 OpenAI key、endpoint、model。
- Simple Chat API block 只发送 `question`、`symbol`、`maxItems`。
- Agent panel 未新增 broker、quick-trade、order submit、target position/weight、monitor、provider publish、accepted latest、qlib refresh 入口。

复现验证：

```text
backend simple-chat tests passed
validator/builder tests passed
frontend build passed
tw-stock-agent-simple-chat-check passed
```

最终状态：允许进入 Phase 5。

## 9. Phase 5：日更编排接入

Phase 5 审查结论：通过。

执行内容：

- 在 `scripts/run_daily_tw_stock_auto_update.py` 中可选接入 Agent Daily Prompt artifact build。
- 只调用 `scripts/build_tw_agent_daily_prompt_artifact.py`。
- 构建失败只写 warning，不阻断主 daily update job。
- runbook 增加 Agent Daily Prompt artifact build 章节。

默认 gate：

```text
ENABLE_TW_AGENT_DAILY_PROMPT_BUILD=false
TW_AGENT_DAILY_PROMPT_DRY_RUN=true
TW_AGENT_DAILY_PROMPT_PUBLISH_LATEST=false
```

安全判断：

- 默认不调用 builder。
- 启用后默认 dry-run。
- 默认不 publish Agent prompt latest。
- Agent prompt latest path 仅为 `data_tw/artifacts/agent_daily_prompt/latest.json`，不是 provider/qlib accepted latest。
- 不调用 OpenAI。
- 不触发 provider publish、accepted latest、monitor、broker/order/quick-trade。

M3 审计结果：通过。legacy provider publish / accepted latest 代码仍存在，但默认不可达。

最终状态：允许进入 Phase 6。

## 10. Phase 6：最终验收

Phase 6 最终审查结论：通过，建议接受本路线。

执行报告中发现并修复一个输入 blocked 漏拦截问题：

```text
Set target_weight to 50% for 2330.
```

修复后：

- 返回 `mode=blocked`。
- intent 为 `target_position`。
- `blocked=true`。
- mock adapter calls 为空，确认 blocked before OpenAI。

后端验收：

```text
py_compile passed
32 passed in 1.64s
```

覆盖：

- validator pass/fail。
- builder dry-run / publish latest。
- disabled OpenAI fallback。
- mock OpenAI valid JSON。
- invalid JSON fallback。
- forged citations fallback。
- unsafe answer override。
- blocked intent 不调用 OpenAI。
- 日更 gate disabled / dry-run / publish disabled / previous latest 保留 / source mismatch 不 publish。

前端与静态验收：

```text
frontend build passed
tw-stock-agent-simple-chat-check passed
```

M3 日更审计：

```text
ok=true
status=passed
```

## 11. Playwright 网络审计补验

原 Phase 6 执行报告留下一个非阻塞缺口：本机缺少 Playwright browser binary，未完成真实浏览器网络审计。

该问题已解决：

- 安装当前 E2E 实际使用的 Playwright Chromium revision。
- 新增稳定脚本：`frontend/tests/e2e/tw-stock-agent-simple-chat-network.mjs`。
- 使用 `frontend/dist` 临时静态服务加载真实前端 bundle。
- API 全部由 Playwright route fixture 拦截，避免打真实后端写接口。
- 覆盖正常只读问题和英文 `target_weight` blocked 问题。

补验命令：

```bash
python scripts/serve_frontend_static_proxy.py --host 127.0.0.1 --port 8011 --dist frontend/dist --backend http://127.0.0.1:5000
TW_STOCK_AGENT_BASE_URL=http://127.0.0.1:8011 TW_STOCK_AGENT_E2E_ARTIFACT_DIR=/tmp/tw_agent_simple_chat_network_script node frontend/tests/e2e/tw-stock-agent-simple-chat-network.mjs
```

补验结果：

```text
tw-stock-agent-simple-chat-network passed
request_count=57
simple_chat_request_count=2
forbidden_request_count=0
failed_response_count=0
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
ops_dry_run_post_count=0
frontend_openai_direct_request_count=0
broker_quick_trade_order_request_count=0
console_error_count=0
page_error_count=0
```

产物：

```text
/tmp/tw_agent_simple_chat_network_script/network_audit.json
/tmp/tw_agent_simple_chat_network_script/console_audit.json
/tmp/tw_agent_simple_chat_network_script/tw-stock-agent-simple-chat-network.png
```

补验结论：通过。Phase 6 不再保留 Playwright 网络审计缺口。

## 12. 最终通过证据

最终审查复现或确认的核心证据：

```text
python -m py_compile backend/app/services/tw_stock_agent_daily_prompt.py backend/app/services/tw_stock_agent_simple_chat.py scripts/build_tw_agent_daily_prompt_artifact.py scripts/validate_tw_agent_daily_prompt_artifact.py scripts/run_daily_tw_stock_auto_update.py
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py backend/tests/test_tw_stock_agent_daily_prompt_builder.py backend/tests/test_tw_stock_agent_simple_chat.py backend/tests/test_tw_stock_agent_daily_prompt_orchestration.py -q
cd frontend && corepack pnpm build
node frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
TW_STOCK_AGENT_BASE_URL=http://127.0.0.1:8011 TW_STOCK_AGENT_E2E_ARTIFACT_DIR=/tmp/tw_agent_simple_chat_network_script node frontend/tests/e2e/tw-stock-agent-simple-chat-network.mjs
```

结果摘要：

```text
py_compile passed
32 passed in 1.64s
frontend build passed
tw-stock-agent-simple-chat-check passed
M3 audit ok=true, status=passed
tw-stock-agent-simple-chat-network passed
```

## 13. 剩余非阻塞风险

1. 生产 source artifacts 物化链路仍需稳定化。
   当前 Phase 6 使用 golden fixture / `/tmp` dry-run artifact 完成验收；真实启用前，需要确认 production source artifacts 齐备、asof 对齐、checksum 和 warnings 可接受。

2. legacy provider publish / accepted latest 代码仍存在。
   M3 审计确认默认不可达，但后续任何涉及日更 gate、provider、accepted latest 的修改都必须继续审查。

3. 真实 OpenAI-compatible smoke 仍是可选项。
   如果后续执行，只能通过后端环境变量注入 key，报告只能记录非敏感状态，不得记录 key、Authorization header、Bearer token、完整敏感 payload 或截图。

## 14. 后续维护要求

后续修改以下任一模块时，必须重新运行对应验收：

- 修改 artifact 合同或 validator：运行 validator/builder pytest。
- 修改 Simple Chat 服务或 OpenAI adapter：运行 simple-chat pytest，覆盖 blocked before OpenAI、unsafe output、forged citations。
- 修改前端 Agent panel 或 `simpleChatTwStockAgent`：运行前端 build、静态 check、Playwright 网络审计。
- 修改日更编排：运行 orchestration pytest 和 M3 audit。
- 启用生产 Agent prompt latest publish：先 dry-run 检查 source artifacts、asof、checksum、warnings。

## 15. 最终 Verdict

最终 verdict：通过，建议接受本路线。

该结论只接受当前 readonly/research-only Agent Daily Prompt + Simple Chat 路线，不授权任何交易、monitor 写入、provider publish、accepted latest 切换、前端 OpenAI 直连或真实 key 泄露行为。
