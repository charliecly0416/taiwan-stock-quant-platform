# Phase 5 执行报告：日更编排接入

生成日期：2026-06-19

## 1. 阶段目标

按照 `PHASE5_WORK_CN.md`，本阶段只把 `DailyAgentPromptArtifact` 构建接入日更编排，并保持默认关闭或 dry-run、安全 gate、失败不影响主链路。

本阶段未调用 OpenAI，未做真实 OpenAI smoke，未改前端，未改 `/api/tw-stock/agent/simple-chat`，未触发 provider publish、accepted latest、monitor、broker/order/quick-trade，也未把 Agent prompt 构建变成日更硬依赖。

## 2. 实际完成内容

1. 在 `scripts/run_daily_tw_stock_auto_update.py` 新增 `run_agent_daily_prompt_build(...)`：
   - 默认 `ENABLE_TW_AGENT_DAILY_PROMPT_BUILD=false`，gate 关闭时不调用 builder。
   - 默认 `TW_AGENT_DAILY_PROMPT_DRY_RUN=true`。
   - 默认 `TW_AGENT_DAILY_PROMPT_PUBLISH_LATEST=false`。
   - 只调用 `scripts/build_tw_agent_daily_prompt_artifact.py`。
   - 通过 builder 内部 Phase 1 validator 决定 `validator_ok`。

2. 将 Agent prompt build 接到日更收尾阶段：
   - 写入 `job.json.agent_daily_prompt`。
   - 若构建失败，只写入 `job.json.agent_daily_prompt_warning`。
   - 不改变 `daily_auto_update_passed` 主状态，不改变返回码。

3. latest pointer 策略：
   - 只有 gate 打开、非 dry-run、`TW_AGENT_DAILY_PROMPT_PUBLISH_LATEST=true` 且 builder/validator 通过时，才会向 builder 传入 `--publish-latest --latest-path ...`。
   - 允许更新的 latest 仅限 `data_tw/artifacts/agent_daily_prompt/latest.json`。
   - 构建失败、validator failed、source mismatch、dry-run 或 publish disabled 均不写 latest。

4. 更新 Runbook：
   - `docs/tw_modular_contracts/TW_DAILY_AUTO_UPDATE_RUNBOOK_CN.md` 增加 Agent Daily Prompt artifact build 章节。
   - 说明 gate、默认行为、路径、失败行为和回滚方式。

5. 新增 orchestration 单测：
   - `backend/tests/test_tw_stock_agent_daily_prompt_orchestration.py`
   - 使用 fake command runner，不触发真实日更、OpenAI、provider、monitor 或交易路径。

## 3. 改动文件列表

- `scripts/run_daily_tw_stock_auto_update.py`
- `backend/tests/test_tw_stock_agent_daily_prompt_orchestration.py`
- `docs/tw_modular_contracts/TW_DAILY_AUTO_UPDATE_RUNBOOK_CN.md`
- `docs/tw_agent_daily_prompt_rebuild/PHASE5_EXECUTION_REPORT_CN.md`

## 4. Gate 与默认行为

默认环境变量：

```text
ENABLE_TW_AGENT_DAILY_PROMPT_BUILD=false
TW_AGENT_DAILY_PROMPT_DRY_RUN=true
TW_AGENT_DAILY_PROMPT_PUBLISH_LATEST=false
```

默认效果：

- 不调用 builder。
- 不写 `data_tw/artifacts/agent_daily_prompt/latest.json`。
- 不影响 readonly snapshot、paper portfolio、current strategy context 或日更主状态。

可选路径：

```text
TW_AGENT_DAILY_PROMPT_SOURCE_DIR=data_tw/artifacts/agent_daily_prompt/source_artifacts
TW_AGENT_DAILY_PROMPT_OUTPUT_ROOT=data_tw/artifacts/agent_daily_prompt
TW_AGENT_DAILY_PROMPT_LATEST_PATH=data_tw/artifacts/agent_daily_prompt/latest.json
TW_AGENT_DAILY_PROMPT_TIMEOUT_SECONDS=300
```

## 5. Dry-run / Publish-latest 行为

- `dry_run=true`：会向 builder 传入 `--dry-run`，即使 `publish_latest=true` 也不会传 `--publish-latest`。
- `publish_latest=false`：即使非 dry-run 且 validator 通过，也不传 `--publish-latest`。
- `dry_run=false` 且 `publish_latest=true`：才传入 `--publish-latest --latest-path <Agent prompt latest>`。

## 6. Previous Latest 保留策略

Agent prompt build 的 publish 由 builder 执行；orchestration 层在 failure / validator failed / source mismatch 时不会写 latest。

已用测试覆盖：

- previous latest 存在时，validator failed 不覆盖 previous latest。
- source mismatch 不覆盖 previous latest。

## 7. 失败处理策略

失败只体现在：

```text
job.json.agent_daily_prompt.ok=false
job.json.agent_daily_prompt_warning=<error>
```

主链路继续保持原有日更结果，不因 Agent prompt build 失败而失败。这符合 Phase 5 “不把 Agent prompt 构建作为日更成功硬依赖”的要求。

## 8. 测试结果

已运行：

```bash
python -m py_compile scripts/build_tw_agent_daily_prompt_artifact.py scripts/validate_tw_agent_daily_prompt_artifact.py scripts/run_daily_tw_stock_auto_update.py
```

结果：通过。

```bash
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py backend/tests/test_tw_stock_agent_daily_prompt_builder.py -q
```

结果：`9 passed in 0.11s`。

```bash
python -m pytest backend/tests/test_tw_stock_agent_simple_chat.py -q
```

结果：`15 passed in 1.35s`。

```bash
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_orchestration.py -q
```

结果：`7 passed in 0.08s`。

额外运行默认日更安全审计：

```bash
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
```

结果：`ok=true`。仅有既有 warning：legacy provider publish / accepted latest 代码存在，但受显式非默认 gate 保护；默认 provider refresh/publish/accepted latest 均不可达，broker/order pattern 为空，monitor write pattern 为空。

## 9. 静态检查结果

OpenAI 静态检索：

```bash
rg -n "OPENAI_API_KEY|api.openai.com|chat/completions|@openai" scripts scripts/*.py backend/tests/test_tw_stock_agent_daily_prompt_orchestration.py
```

结果：无命中。

危险入口静态检索：

```bash
rg -n "quick-trade|broker|orders|target-position|target_weight|monitor config|monitor scan|monitor alerts|/monitor/config|/monitor/scan|/monitor/alerts|provider publish|accepted latest|qlib refresh|retrain|调参" scripts backend/tests/test_tw_stock_agent_daily_prompt_orchestration.py
```

命中归因：

- `backend/tests/test_tw_stock_agent_daily_prompt_orchestration.py`：denylist 断言，确认 builder argv 不含危险语义。
- `scripts/run_daily_tw_stock_auto_update.py`：既有 legacy provider publish / accepted latest gate 文案、只读 trading flags、既有失败状态字符串；M3 validator 确认默认不可达。
- `scripts/validate_tw_agent_daily_prompt_artifact.py`、`scripts/validate_tw_daily_orchestrator_m3.py`、`scripts/validate_tw_frontend_readonly_m4.py` 等：安全 validator / denylist 本身。
- `scripts/archive/historical_research/*` 与 replay 类脚本：历史研究/只读回放/归档脚本命中，不是本次 Phase 5 新增路径。

针对本次新增函数和测试的收窄检查显示：新增 command argv 仅调用 `build_tw_agent_daily_prompt_artifact.py`，不包含 OpenAI、provider publish、accepted latest、monitor、quick-trade、broker、target_weight 等危险参数。

## 10. 只读安全边界说明

- 本阶段只消费只读 source artifacts。
- 不调用 OpenAI，也不读取 OpenAI key/base URL/model。
- 不触发 provider publish、provider accepted latest、qlib accepted latest。
- 不写 monitor config/scan/alerts。
- 不触发 broker/order/quick-trade。
- 不训练模型、不调参、不跑回放收益筛选。
- Agent prompt latest 与 provider/qlib accepted latest 明确分离。

## 11. 未完成事项

无 Phase 5 范围内必须项未完成。

## 12. 风险与需要审查的问题

1. 默认 `TW_AGENT_DAILY_PROMPT_SOURCE_DIR` 指向 `data_tw/artifacts/agent_daily_prompt/source_artifacts`，当前生产 source artifacts 的实际物化流程仍需由后续阶段或现有 readonly artifact 发布链路提供；Phase 5 只做编排接入。
2. 日更脚本中既有 legacy provider publish / accepted latest 代码仍存在；本阶段未触碰该路径，M3 validator 确认默认不可达。
3. 真实生产启用 publish latest 前，应先用 dry-run 检查 source artifact 是否齐备、asof 是否一致、execution price / freshness warning 是否符合预期。

## 13. 是否建议进入 Phase 6

建议等待 Phase 5 审查通过后再进入 Phase 6。当前执行结果满足 Phase 5 工作文档要求，但不应在本报告后直接进入 Phase 6。
