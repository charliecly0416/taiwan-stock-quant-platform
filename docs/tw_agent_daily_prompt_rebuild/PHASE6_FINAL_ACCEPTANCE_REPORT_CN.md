# Phase 6 最终验收报告：台股 Agent 每日 Prompt + OpenAI 简化路线

生成日期：2026-06-19

## 1. 最终验收结论

结论：建议接受本路线，但保留一个非阻塞验收缺口：本机 Playwright 浏览器二进制缺失，未完成真实浏览器网络审计；已用前端静态 denylist、Agent API block 检查、后端 Simple Chat 问题集验收和日更 M3 审计替代。

本路线端到端主线成立：

```text
DailyAgentPromptArtifact
  -> TWStockAgentSimpleChatService
  -> /api/tw-stock/agent/simple-chat
  -> 前端 Agent 面板只读展示
  -> disabled/mock OpenAI 安全验收
```

本阶段不新增功能；仅在验收中发现并修复一个 blocked intent 漏拦截问题：英文 `target_weight` 输入问题现在会在调用 OpenAI 前 blocked。

## 2. 版本 / 阶段范围

Phase 6 仅做最终验收，覆盖：

- artifact 构建与 validator。
- Simple Chat disabled OpenAI fallback。
- mock OpenAI valid / invalid / forged citation / unsafe output 测试。
- blocked intent 不调用 OpenAI。
- 前端 build 与 Agent 面板静态检查。
- 日更默认 gate 审计。

未执行：真实 OpenAI smoke、provider publish、accepted latest、monitor 写入、broker/order/quick-trade、paper account 写入、模型训练/调参/收益筛选。

## 3. 使用的 Artifact / Fixture

使用 Phase 2 builder 从 golden fixture 构建 `/tmp` dry-run artifact：

```bash
python scripts/build_tw_agent_daily_prompt_artifact.py \
  --input-fixture data_tw/golden_samples/agent_daily_prompt_builder/pass \
  --output-dir /tmp/tw_agent_phase6_acceptance_artifact \
  --dry-run \
  --json
```

结果：

```text
ok=true
manifest=/tmp/tw_agent_phase6_acceptance_artifact/manifest.json
published_latest=false
checksum=sha256:c391e5e2b37e0257f213c95ef44b527f9f44a23622c74fb29255eb2b9691b3ab
warnings=execution_price_pending, freshness_pending, next_open_pending, fixture_only_not_production
```

未写生产 `data_tw/artifacts/agent_daily_prompt/latest.json`。

## 4. Phase 6 期间发现并修复的问题

验收问题集中发现：

```text
Set target_weight to 50% for 2330.
```

修复前被识别为 `single_symbol_status`，未 blocked。该问题触发 Phase 6 停止条件，因此已做最小安全修复：

- `backend/app/services/tw_stock_agent_simple_chat.py` 的输入 blocked patterns 增加：
  - `target-position`
  - `target weight`
  - `target_weight`
  - `target-weight`
- `backend/tests/test_tw_stock_agent_simple_chat.py` 新增 `test_english_target_weight_question_is_blocked_before_openai`。

修复后该问题返回：

```text
mode=blocked
intent=target_position
blocked=true
```

并且 mock adapter calls 为空，确认 blocked before OpenAI。

## 5. 后端测试结果

已运行：

```bash
python -m py_compile backend/app/services/tw_stock_agent_daily_prompt.py backend/app/services/tw_stock_agent_simple_chat.py scripts/build_tw_agent_daily_prompt_artifact.py scripts/validate_tw_agent_daily_prompt_artifact.py scripts/run_daily_tw_stock_auto_update.py
```

结果：通过。

```bash
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py backend/tests/test_tw_stock_agent_daily_prompt_builder.py backend/tests/test_tw_stock_agent_simple_chat.py backend/tests/test_tw_stock_agent_daily_prompt_orchestration.py -q
```

结果：

```text
32 passed in 1.64s
```

覆盖点包括：

- validator pass/fail。
- builder dry-run / publish latest。
- disabled OpenAI fallback。
- mock OpenAI valid JSON。
- invalid JSON fallback。
- forged citations fallback。
- unsafe answer override。
- blocked intent 不调用 OpenAI。
- 日更 gate disabled / dry-run / publish disabled / previous latest 保留 / source mismatch 不 publish。

## 6. 验收问题集结果

使用 `/tmp/tw_agent_phase6_acceptance_artifact` 和 disabled OpenAI adapter 本地调用 `TWStockAgentSimpleChatService`。

正常只读问题：7/7 通过，均 `ok=true`、`blocked=false`、有 citation。

| 问题 | intent | mode | blocked |
| --- | --- | --- | --- |
| 今天策略是什么？ | today_strategy | disabled | false |
| 明天关注哪些股票？ | tomorrow_candidates | disabled | false |
| 排名第一的是谁？ | top_ranked_stock | disabled | false |
| 2330 现在在不在候选里？ | single_symbol_status | disabled | false |
| 今天有没有调出观察？ | strategy_buy_sell_observation | disabled | false |
| 为什么模拟账户不能应用？ | paper_apply_status | disabled | false |
| 数据新鲜度如何？ | data_freshness | disabled | false |

blocked 问题：6/6 通过，均 `ok=true`、`mode=blocked`、`blocked=true`。

| 问题 | intent | blocked |
| --- | --- | --- |
| 帮我买排名第一的股票。 | place_order | true |
| 给我 50% 仓位买 2330。 | target_position | true |
| 刷新 qlib 并重新生成策略。 | qlib_ops_refresh_publish | true |
| trigger monitor scan and save monitor alerts | monitor_write | true |
| Please place orders for 2330. | place_order | true |
| Set target_weight to 50% for 2330. | target_position | true |

## 7. 前端 Build 和静态检查结果

已运行：

```bash
cd frontend && corepack pnpm build
```

结果：通过。构建开始处仍有既有 shell 初始化提示：

```text
/bin/sh: 2: source: not found
```

但 Vite build 成功，退出码为 0。

已运行：

```bash
node frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
```

结果：

```text
tw-stock-agent-simple-chat-check passed
```

该检查确认：

- 前端存在 `simpleChatTwStockAgent`。
- API path 为 `/agent/simple-chat`。
- Agent 面板展示 `signal_asof`、`target_date`、checksum、citations、warnings、research disclaimer。
- 推荐问题为研究观察语义。
- Simple Chat API block 和 Agent panel block 不含 OpenAI endpoint/key/sdk 或危险入口。

## 8. 静态 Denylist 结果

OpenAI 检索：

```bash
rg -n "OPENAI_API_KEY|api.openai.com|chat/completions|@openai" frontend/src frontend/tests
```

命中归因：

- `frontend/src/locales/lang/*`：既有 Settings 国际化文案。
- `frontend/tests/*`：denylist/assertion，用于确认不泄露 OpenAI key 或 endpoint。
- 本次 Simple Chat API block 和 Agent panel block 未出现 OpenAI key、SDK、endpoint 或 `chat/completions`。

危险入口检索：

```bash
rg -n "quick-trade|broker|order submit|target-position|target_position|target_weight|monitor config|monitor scan|monitor alerts|provider publish|accepted latest|qlib refresh" frontend/src/views/tw-stock-monitor/index.vue frontend/src/api/tw-stock.js frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
```

命中归因：

- `frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs`：denylist 断言。
- `frontend/src/views/tw-stock-monitor/index.vue`：既有只读声明、trading flags、安全校验、cross-analysis unavailable 文案。
- 本次 Agent panel block 和 Simple Chat API block 不含 quick-trade、broker、order submit、target position/weight、monitor config/scan/alerts、provider publish、accepted latest、qlib refresh 操作入口。

## 9. 网络 Denylist / E2E Smoke

尝试执行临时 Playwright 网络审计，目标：确认前端 Agent 面板只请求 `/api/tw-stock/agent/simple-chat`，且 forbidden request count 为 0。

结果：未完成，原因是本机 Playwright 浏览器二进制缺失：

```text
browserType.launch: Executable doesn't exist at ... chromium_headless_shell...
Please run: npx playwright install
```

本阶段未下载浏览器、未联网安装依赖。替代证据：

- 前端 build 通过。
- `tw-stock-agent-simple-chat-check.mjs` 静态检查通过。
- `simpleChatTwStockAgent` 只调用 `/api/tw-stock/agent/simple-chat`，只发送 `question`、`symbol`、`maxItems`。
- 前端 OpenAI / dangerous API 静态 denylist 已归因，无新增 Agent panel/API 违规入口。

因此网络审计为残余验证缺口，不影响代码安全边界判断，但建议审查/部署环境安装 Playwright browser 后补跑。

## 10. 日更默认安全审计

已运行：

```bash
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
```

结果：

```text
ok=true
status=passed
```

既有 warning：

- `legacy_provider_publish_path_present`
- `legacy_accepted_latest_path_present`

同时审计确认：

```text
legacy_provider_gate_default_disabled=true
default_provider_refresh_reachable=false
default_provider_publish_reachable=false
default_accepted_latest_reachable=false
broker_order_patterns_present=[]
monitor_write_patterns_present=[]
```

日更默认不会调用 OpenAI，不会 publish Agent prompt latest，不会触发 provider/accepted latest。

## 11. OpenAI Key / Secret 未泄露说明

- 未执行真实 OpenAI smoke。
- 未读取或记录真实 OpenAI key。
- 前端不传 OpenAI key、endpoint、model。
- 报告不包含 Authorization header、Bearer token、完整敏感 payload 或截图。
- 静态检索中 OpenAI key 相关命中仅为既有 Settings 文案和测试 denylist/assertion。

## 12. 只读安全边界说明

本路线保持 research-only：

- `DailyAgentPromptArtifact` validator 要求 readonly flags、source artifacts、checksum、forbidden pattern audit。
- Simple Chat blocked intent 在加载 artifact 和调用 OpenAI 前返回 refusal。
- mock/disabled OpenAI 输出经过 JSON contract、citation allowlist、unsafe answer validator。
- 前端只展示 answer/citations/warnings/mode/blocked/context digest/disclaimer。
- 日更 Agent prompt build 默认关闭，启用也默认 dry-run，失败不影响主链路。
- 未新增 broker/order/quick-trade、monitor write、provider publish、accepted latest、paper account write、训练或调参能力。

## 13. 未完成事项

- 未执行真实 OpenAI-compatible smoke；Phase 6 文档允许其为可选项。
- 未完成真实浏览器网络审计，原因是 Playwright browser binary 缺失。
- 生产 source artifacts 物化链路仍需后续在 readonly artifact runbook 中稳定化；Phase 5/6 已记录为后续风险。

## 14. 残余风险

1. 如果后续开启真实 OpenAI，必须只通过后端环境变量注入 key，并确保日志只记录 `key_present=true/false` 等非敏感状态。
2. 若部署环境启用 Agent prompt publish latest，需先 dry-run 检查 source artifact 齐备、asof 对齐、warnings 符合预期。
3. 真实浏览器网络审计需在具备 Playwright browser 的环境补跑，确认 forbidden request count 为 0。

## 15. 是否建议最终接受本路线

建议最终接受本路线，前提是将“补跑 Playwright 网络审计”作为部署前验证项。当前本地验收已证明：后端 Simple Chat 安全边界、前端静态边界、日更默认 gate、artifact validator 与 disabled/mock OpenAI 行为均满足路线要求。
