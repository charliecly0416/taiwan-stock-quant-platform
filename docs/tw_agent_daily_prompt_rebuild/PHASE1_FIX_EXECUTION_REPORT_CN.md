# Phase 1 修复执行报告：补齐 Monitor 写入红线

生成日期：2026-06-19

## 1. 修复目标

根据 `docs/tw_agent_daily_prompt_rebuild/PHASE1_REVIEW_CN.md` 的审查意见，本次只修复 Phase 1 未通过项：

- 合同安全红线补充 monitor config / monitor scan / monitor alerts write。
- validator forbidden patterns 补充 monitor 写入语义和 endpoint/path。
- 新增 `fail_monitor_write` golden sample。
- pytest 加入 `fail_monitor_write` 必须失败的断言。
- 说明 `.agents/skills/frontend-design` 与 `skills-lock.json` 的来源。

本次未进入 Phase 2。

## 2. 实际完成内容

已完成：

- 更新 `docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md`，显式列出 monitor config、monitor scan、monitor alerts、save monitor、`/monitor/config`、`/monitor/scan`、`/monitor/alerts`、保存监控配置、触发 monitor scan、写 monitor alerts。
- 更新 `scripts/validate_tw_agent_daily_prompt_artifact.py`，新增 monitor forbidden patterns。
- 新增 `data_tw/golden_samples/agent_daily_prompt/fail_monitor_write/`，负样本同时包含自然语言和 endpoint/path 风格危险内容。
- 更新 `backend/tests/test_tw_stock_agent_daily_prompt_validator.py`，将 `fail_monitor_write` 纳入 fail sample 列表，并新增 monitor 专项断言。
- 清理 validator 中重复的 `not_target_position` allowlist 条目。

## 3. 改动文件列表

本次修复新增/更新：

- `docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md`
- `scripts/validate_tw_agent_daily_prompt_artifact.py`
- `backend/tests/test_tw_stock_agent_daily_prompt_validator.py`
- `data_tw/golden_samples/agent_daily_prompt/fail_monitor_write/manifest.json`
- `data_tw/golden_samples/agent_daily_prompt/fail_monitor_write/prompt_context.json`
- `data_tw/golden_samples/agent_daily_prompt/fail_monitor_write/prompt_text.md`
- `data_tw/golden_samples/agent_daily_prompt/fail_monitor_write/source_stubs/current_strategy_context_stub.json`
- `data_tw/golden_samples/agent_daily_prompt/fail_monitor_write/source_stubs/readonly_strategy_snapshot_stub.json`
- `docs/tw_agent_daily_prompt_rebuild/PHASE1_FIX_EXECUTION_REPORT_CN.md`

未修改前端、`/api/tw-stock/agent/chat`、OpenAI adapter、日更脚本或真实数据 artifact。

## 4. Validator Monitor 红线新增项

新增 forbidden patterns 覆盖：

- `monitor config`
- `monitor scan`
- `monitor alerts`
- `save monitor`
- `/monitor/config`
- `/monitor/scan`
- `/monitor/scan-all`
- `/monitor/alerts`
- `保存监控配置`
- `触发 monitor scan`
- `写 monitor alerts`

`fail_monitor_write` 中包含：

```json
{"unsafe_monitor_example": {"action": "trigger monitor scan and save monitor alerts", "endpoint": "/api/tw-stock/monitor/scan"}}
```

并在 `prompt_text.md` 中包含：

```text
unsafe monitor line: trigger monitor scan and save monitor alerts via /api/tw-stock/monitor/alerts
```

validator 当前能阻断这些语义和路径。

## 5. 测试命令与实际结果

已运行：

```bash
python -m py_compile scripts/validate_tw_agent_daily_prompt_artifact.py
```

结果：通过，退出码 0。

```bash
python scripts/validate_tw_agent_daily_prompt_artifact.py data_tw/golden_samples/agent_daily_prompt/pass
```

结果：通过，退出码 0：

```text
PASS: data_tw/golden_samples/agent_daily_prompt/pass
```

```bash
python scripts/validate_tw_agent_daily_prompt_artifact.py data_tw/golden_samples/agent_daily_prompt/fail_monitor_write --allow-golden-missing-sources
```

结果：预期失败，退出码 1。关键错误包括：

```text
prompt_context:unsafe_monitor_example.action: forbidden action term 'monitor_scan'
prompt_context:unsafe_monitor_example.action: forbidden action term 'monitor_alerts'
prompt_context:unsafe_monitor_example.action: forbidden action term 'save_monitor'
prompt_context:unsafe_monitor_example.endpoint: forbidden action term 'monitor_scan_path'
prompt_text.md:17: forbidden action term 'monitor_scan'
prompt_text.md:17: forbidden action term 'monitor_alerts'
prompt_text.md:17: forbidden action term 'save_monitor'
prompt_text.md:17: forbidden action term 'monitor_alerts_path'
```

```bash
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py -q
```

结果：通过。

```text
5 passed in 0.07s
```

```bash
rg -n "monitor config|monitor scan|monitor alerts|/monitor/config|/monitor/scan|/monitor/alerts" scripts/validate_tw_agent_daily_prompt_artifact.py data_tw/golden_samples/agent_daily_prompt docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md
```

结果：有命中，均为预期位置：合同安全红线、validator forbidden patterns、`fail_monitor_write` 负样本。pass sample 未包含 monitor 写入行动语义。

## 6. `.agents/skills/frontend-design` 与 `skills-lock.json` 说明

审查意见指出以下未跟踪文件未列入 Phase 1 执行报告：

```text
.agents/skills/frontend-design/LICENSE.txt
.agents/skills/frontend-design/SKILL.md
skills-lock.json
```

本次只读查看结果：

- `.agents/skills/frontend-design/SKILL.md` 是名为 `frontend-design` 的技能说明文件。
- `skills-lock.json` 记录该 skill 来源为 `anthropics/skills`，`sourceType=github`，`skillPath=skills/frontend-design/SKILL.md`。

这些文件不是 Phase 1 DailyAgentPromptArtifact validator 的必要产物，也不是本次 monitor 红线修复所需文件。本次未删除、未修改它们。建议由用户/统筹决定：保留为单独技能安装产物、移除，或另行记录到对应任务中。

## 7. 只读安全边界确认

本次修复没有：

- 调用 OpenAI。
- 启动后端或前端服务。
- 调用 current strategy API。
- 触发真实数据抓取。
- 触发 provider publish。
- 切换 provider accepted latest 或 qlib accepted latest。
- 写 monitor config/scan/alerts。
- 触发 broker/order/quick-trade。
- 训练模型、调参或跑回放收益筛选。

`fail_monitor_write` 中的 monitor 内容是负样本，只用于证明 validator 能阻断危险语义。

## 8. 是否建议复审与进入 Phase 2

建议审查者复审 Phase 1。

如果复审通过，再由审查者决定是否允许进入 Phase 2。本执行者当前停止，不进入 Phase 2。
