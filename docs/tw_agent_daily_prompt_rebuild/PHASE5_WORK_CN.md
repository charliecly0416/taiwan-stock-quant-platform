# Phase 5 工作文档：日更编排接入

生成日期：2026-06-19

## 1. 本阶段范围

Phase 5 只做 `DailyAgentPromptArtifact` 构建的日更编排接入。

目标是让日更流程可以在安全 gate 下触发：

```text
只读 source artifacts
  -> scripts/build_tw_agent_daily_prompt_artifact.py
  -> Phase 1 validator
  -> 可选更新 Agent prompt latest pointer
```

## 2. 明确不做什么

本阶段禁止：

- 不调用 OpenAI。
- 不做真实 OpenAI smoke。
- 不改前端。
- 不改 `/api/tw-stock/agent/simple-chat` 行为。
- 不写 paper account。
- 不触发 provider publish。
- 不切换 provider accepted latest 或 qlib accepted latest。
- 不写 monitor config/scan/alerts。
- 不触发 broker/order/quick-trade。
- 不训练模型、不调参、不跑回放收益筛选。
- 不把 Agent prompt 构建作为日更成功的硬依赖。

## 3. 执行者任务清单

1. 在日更编排中增加可选 Agent prompt 构建步骤，或新增独立 wrapper。
2. 默认必须关闭或 dry-run。
3. 增加 env gate，建议：

```text
ENABLE_TW_AGENT_DAILY_PROMPT_BUILD=false
TW_AGENT_DAILY_PROMPT_DRY_RUN=true
TW_AGENT_DAILY_PROMPT_PUBLISH_LATEST=false
```

4. 构建失败只记录 warning/job artifact，不影响 readonly snapshot、paper portfolio、current strategy context 的既有结果。
5. 只有显式 gate 打开、非 dry-run、validator 通过时，才允许更新：

```text
data_tw/artifacts/agent_daily_prompt/latest.json
```

6. 更新 runbook 或阶段文档，说明 gate、dry-run、失败行为、回滚方式。
7. 输出：

```text
docs/tw_agent_daily_prompt_rebuild/PHASE5_EXECUTION_REPORT_CN.md
```

## 4. 允许修改的文件

可选修改：

```text
scripts/run_daily_tw_stock_auto_update.py
```

或新增独立 wrapper：

```text
scripts/run_tw_agent_daily_prompt_build.py
```

可新增测试：

```text
backend/tests/test_tw_stock_agent_daily_prompt_orchestration.py
```

可更新文档：

```text
docs/tw_modular_contracts/TW_DAILY_AUTO_UPDATE_RUNBOOK_CN.md
docs/tw_agent_daily_prompt_rebuild/PHASE5_EXECUTION_REPORT_CN.md
```

不得修改前端或 OpenAI adapter。

## 5. 行为要求

日更接入必须满足：

- 默认不构建或只 dry-run。
- previous latest 保留。
- 构建失败不删除、不覆盖 previous latest。
- validator 失败不得 publish latest。
- source artifact 缺失、asof mixed、execution price pending 必须进入 warning/block。
- 日更主链路不得因 Agent prompt 构建失败而失败，除非用户和统筹另行明确要求。
- 输出日志不得包含 OpenAI key、OpenAI base URL 或敏感环境变量。

## 6. 必须测试的场景

至少覆盖：

- gate disabled：不调用 builder。
- dry-run enabled：生成 artifact 或 dry-run 结果，但不写 latest。
- publish disabled：validator 通过也不写 latest。
- validator failed：不写 latest，返回 warning/failure artifact。
- previous latest exists：失败时 previous latest 保留。
- source mismatch：不 publish。
- 无 OpenAI 调用。
- 无 provider/accepted latest/monitor/broker/order 调用。

## 7. 必须运行的测试或静态检查

最低命令：

```bash
python -m py_compile scripts/build_tw_agent_daily_prompt_artifact.py scripts/validate_tw_agent_daily_prompt_artifact.py
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py backend/tests/test_tw_stock_agent_daily_prompt_builder.py -q
python -m pytest backend/tests/test_tw_stock_agent_simple_chat.py -q
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_orchestration.py -q
rg -n "OPENAI_API_KEY|api.openai.com|chat/completions|@openai" scripts scripts/*.py backend/tests/test_tw_stock_agent_daily_prompt_orchestration.py
rg -n "quick-trade|broker|orders|target-position|target_weight|monitor config|monitor scan|monitor alerts|/monitor/config|/monitor/scan|/monitor/alerts|provider publish|accepted latest|qlib refresh|retrain|调参" scripts backend/tests/test_tw_stock_agent_daily_prompt_orchestration.py
```

如果没有新增 orchestration pytest，执行报告必须说明替代验证方式，并提供命令证据。

## 8. 执行报告必须包含

执行者必须输出：

```text
docs/tw_agent_daily_prompt_rebuild/PHASE5_EXECUTION_REPORT_CN.md
```

报告必须包含：

- 阶段目标。
- 实际完成内容。
- 改动文件列表。
- gate 与默认行为。
- dry-run / publish-latest 行为。
- previous latest 保留策略。
- 失败处理策略。
- 测试命令与实际结果。
- 只读安全边界说明。
- 未完成事项。
- 风险与需要审查的问题。
- 是否建议进入 Phase 6。

## 9. 审查者重点检查项

Phase 5 审查者必须检查：

- 日更接入默认是否关闭或 dry-run。
- 是否没有 OpenAI 调用。
- 是否没有 provider publish / accepted latest switch。
- 是否没有 monitor config/scan/alerts。
- 是否没有 broker/order/quick-trade。
- latest pointer 是否只属于 Agent prompt。
- 构建失败是否不破坏 previous latest。
- Agent prompt 构建是否不成为主链路硬依赖。

## 10. 停止条件

出现以下任一情况必须停止，不得进入 Phase 6：

- 日更默认调用 OpenAI。
- 日更默认 publish Agent prompt latest。
- Agent prompt latest 与 provider/qlib accepted latest 混淆。
- 构建失败覆盖或删除 previous latest。
- 构建失败导致主日更链路失败。
- 触发 provider publish、accepted latest、monitor、broker/order/quick-trade。
