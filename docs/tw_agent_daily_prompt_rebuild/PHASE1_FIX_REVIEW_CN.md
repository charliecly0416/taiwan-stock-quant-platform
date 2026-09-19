# Phase 1 修复复审意见：Monitor 写入红线

生成日期：2026-06-19

## 1. 审查结论

审查结论：通过。

Phase 1 修复已补齐上次阻塞项：validator、合同、golden sample 和 pytest 均已覆盖 monitor config / monitor scan / monitor alerts 写入红线。允许进入 Phase 2，但范围仅限“每日 Prompt Artifact 构建脚本”，不得调用 OpenAI、不得改前端、不得改 `/api/tw-stock/agent/chat`、不得触发 provider publish、accepted latest、monitor、broker/order/quick-trade。

## 2. 主线一致性判断

本次 repair 只修复 Phase 1 阻塞项，没有进入 Phase 2。主线仍保持：

```text
DailyAgentPromptArtifact 合同与 validator
```

未发现新增复杂 Agent、多工具调用、外部搜索、交易执行、provider 运维或模型训练路线。

## 3. 安全边界审查

本次复审未发现新增真实写入路径或执行路径。`fail_monitor_write` 中的 monitor 内容是负样本，用于证明 validator 阻断危险语义。

已复现：

```bash
python -m py_compile scripts/validate_tw_agent_daily_prompt_artifact.py
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py -q
```

结果：

```text
5 passed in 0.07s
```

validator CLI 在普通沙箱下仍会出现 `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`，复审按权限规则提权重跑本地 validator。提权命令只读取工作区文件，不访问网络，不调用 OpenAI。

已复现 pass sample：

```bash
python scripts/validate_tw_agent_daily_prompt_artifact.py data_tw/golden_samples/agent_daily_prompt/pass
```

结果：

```text
PASS: data_tw/golden_samples/agent_daily_prompt/pass
```

已复现 monitor fail sample：

```bash
python scripts/validate_tw_agent_daily_prompt_artifact.py data_tw/golden_samples/agent_daily_prompt/fail_monitor_write --allow-golden-missing-sources
```

结果：预期失败，包含：

```text
forbidden action term 'monitor_scan'
forbidden action term 'monitor_alerts'
forbidden action term 'save_monitor'
forbidden action term 'monitor_scan_path'
forbidden action term 'monitor_alerts_path'
```

静态 OpenAI 检索：

```bash
rg -n "OPENAI_API_KEY|api.openai.com|chat/completions|@openai" scripts/validate_tw_agent_daily_prompt_artifact.py backend/tests/test_tw_stock_agent_daily_prompt_validator.py data_tw/golden_samples/agent_daily_prompt docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md
```

结果：无命中。

## 4. 合同与 Artifact 审查

合同已补充 monitor 红线：

- `monitor config`
- `monitor scan`
- `monitor alerts write`
- `/monitor/config`
- `/monitor/scan`
- `/monitor/alerts`
- 保存监控配置
- 触发 monitor scan
- 写 monitor alerts

这已满足 Phase 1 审查要求。

## 5. Validator 审查

validator 已新增 monitor forbidden patterns：

- `monitor_config`
- `monitor_scan`
- `monitor_alerts`
- `save_monitor`
- `monitor_config_path`
- `monitor_scan_path`
- `monitor_alerts_path`
- `monitor_config_cn`
- `monitor_scan_cn`
- `monitor_alerts_cn`

上次构造的 monitor gap 已被修复，同类样本现在会失败。

## 6. Golden Sample 审查

新增 `data_tw/golden_samples/agent_daily_prompt/fail_monitor_write/`，同时包含自然语言和 endpoint/path 风格危险内容：

```json
{"unsafe_monitor_example": {"action": "trigger monitor scan and save monitor alerts", "endpoint": "/api/tw-stock/monitor/scan"}}
```

pytest 已纳入该 fail sample，并新增 monitor 专项断言。

## 7. 工作树一致性审查

执行者已说明：

- `.agents/skills/frontend-design/*` 是 `frontend-design` skill 文件。
- `skills-lock.json` 记录该 skill 来源。
- 这些文件不是 Phase 1 validator 必需产物，本次 repair 未删除或修改。

复审意见：该说明足够解除 Phase 1 放行阻塞，但这些无关文件仍应由用户/统筹决定是否保留、移除或单独归档。本轮不回滚。

另注意当前工作树出现未跟踪文件：

```text
docs/tw_modular_daily_update_productization/PHASEUI_STRATEGY_WORKBENCH_FRONTEND_UX_REPAIR_WORK_CN.md
```

该文件不属于本次 Phase 1 repair 证据范围，本轮未审查。

## 8. 发现的问题

### Low

1. validator 对 prompt_text 的 forbidden allowlist 仍使用行级否定词判断。
   Phase 1 输入 artifact validator 可接受；Phase 3 模型输出 validator 不应照搬，应使用更严格的 structured output、intent、blocked 和 citation 校验。

2. `.agents/skills/frontend-design` 与 `skills-lock.json` 仍是无关未跟踪文件。
   不阻塞 Phase 2，但需要统筹决定归属。

## 9. 必须修复项

Phase 1 无剩余必须修复项。

进入 Phase 2 前仍必须遵守：

- 不调用 OpenAI。
- 不改前端。
- 不改 `/api/tw-stock/agent/chat`。
- 不触发 provider publish、accepted latest、monitor、broker/order/quick-trade。
- 默认 dry-run，不更新 latest pointer。

## 10. 可后续优化项

- Phase 2 构建脚本应复用本 validator，构建后必须自动校验。
- Phase 2 应把 source artifact 缺失、asof mixed、execution price pending 明确写入 warning/block，不得静默生成可执行建议。
- 后续可把 forbidden action 词表抽成共享模块，减少 builder、validator、chat、前端检查重复。

## 11. 是否允许进入 Phase 2

允许进入 Phase 2。

放行范围仅限：

```text
每日 Prompt Artifact 构建脚本
```

不得提前进入 Simple Chat API、前端 Agent 面板、日更编排或 OpenAI 接入。
