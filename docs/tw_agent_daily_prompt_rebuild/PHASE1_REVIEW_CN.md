# Phase 1 审查意见：DailyAgentPromptArtifact 合同与 Validator

生成日期：2026-06-19

## 1. 审查结论

审查结论：不通过。

暂不允许进入 Phase 2。执行者需要先补齐 Phase 1 validator 的 monitor 写入安全红线，并解释未列入执行报告的 `.agents/skills/frontend-design` 与 `skills-lock.json` 变更来源；修复后重新提交 Phase 1 执行报告或补充报告，再复审。

本次不写 `PHASE2_WORK_CN.md`。

## 2. 主线一致性判断

Phase 1 主线方向基本正确：

- 新增了 `DailyAgentPromptArtifact` 合同文档。
- 新增了独立 validator。
- 新增了 pass/fail golden samples。
- 未修改 `/api/tw-stock/agent/chat`。
- 未改前端。
- 未调用 OpenAI。
- 未构建真实生产 prompt。

合同也明确 `latest.json` 只是 Agent prompt latest pointer，不是 provider accepted latest，也不是 qlib accepted latest。

但 Phase 1 放行条件不仅是“方向正确”，还要求 validator 能挡住安全红线。当前 validator 对 monitor config/scan/alerts 写入语义漏检，不能放行进入 Phase 2。

## 3. 安全边界审查

本次审查未发现 Phase 1 新增真实 broker/order/quick-trade/provider publish/accepted latest 切换路径，也未发现 OpenAI 调用或前端 OpenAI key 暴露。

已复现通过的检查：

```bash
python -m py_compile scripts/validate_tw_agent_daily_prompt_artifact.py
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py -q
```

结果：

```text
4 passed in 0.06s
```

已复现 validator CLI：

```bash
python scripts/validate_tw_agent_daily_prompt_artifact.py data_tw/golden_samples/agent_daily_prompt/pass
```

结果：

```text
PASS: data_tw/golden_samples/agent_daily_prompt/pass
```

已复现 fail samples 会失败：

- `fail_readonly_false`
- `fail_trade_enabled`
- `fail_wrong_model`
- `fail_wrong_strategy`
- `fail_wrong_execution_price`
- `fail_forbidden_action`
- `fail_checksum`

但是，validator 未覆盖 monitor 写入红线。审查者用 pass sample 复制到 `/tmp/agent_prompt_monitor_gap`，在 `prompt_context.json` 加入以下危险语义并重算 checksum：

```json
{"unsafe_monitor_example": {"action": "trigger monitor scan and save monitor alerts"}}
```

然后运行：

```bash
python scripts/validate_tw_agent_daily_prompt_artifact.py /tmp/agent_prompt_monitor_gap
```

实际结果：

```text
PASS: /tmp/agent_prompt_monitor_gap
```

这说明当前 validator 会放行 monitor scan / alerts write 语义。根据项目宪法、Phase 1 工作文档和只读安全边界要求，这是必须修复项。

## 4. 合同与 Artifact 审查

合同文档 `docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md` 覆盖了以下关键点：

- artifact 文件结构。
- `latest.json` pointer 语义。
- manifest 必填字段。
- prompt_context 必填字段。
- prompt_text 必须包含的安全说明。
- checksum 规则。
- provider/accepted latest/qlib refresh/broker/order/target position 等安全红线。

主要缺口：

- 合同第 7 节安全红线没有显式列出 `monitor config`、`monitor scan`、`monitor alerts write`。
- validator 禁止词表也没有 monitor 相关模式。
- golden samples 没有 `fail_monitor_write`。

这与 Phase 1 工作文档中“forbidden action audit 是否覆盖 broker、quick-trade、orders、target position、monitor、provider publish、accepted latest、qlib refresh/retrain/tune”的审查要求不一致。

## 5. Validator 审查

已确认 validator 覆盖：

- manifest schema、readonly flags、产品模型、默认策略、`next_open`。
- prompt_context safety、date/model 对齐、ranking source、candidate boundary、disclaimer。
- source artifacts 存在性。
- checksum 复算。
- broker、quick-trade、orders、target-position、target_position、target_weight、provider publish、accepted latest、qlib refresh、retrain、调参、收益/上涨/胜率承诺等部分危险语义。

必须修复：

- 增加 monitor 写入相关 forbidden patterns，例如 `monitor config`、`monitor scan`、`monitor alerts`、`save monitor`、`保存监控配置`、`触发 monitor scan`、`写 monitor alerts`、`/monitor/config`、`/monitor/scan`、`/monitor/alerts`。
- 新增 `fail_monitor_write` golden sample。
- 新增 pytest 断言 `fail_monitor_write` 必须失败。
- 合同文档同步补充 monitor 红线。

## 6. Golden Sample 审查

现有 golden samples 基本有效：

- pass sample 严格模式通过，且 source stubs 存在。
- fail samples 覆盖 readonly false、trade enabled、wrong model、wrong strategy、wrong execution price、forbidden action、checksum mismatch。

缺口：

- 缺少 `fail_monitor_write`。
- 缺少验证 dangerous endpoint/path 风格内容的 fail sample，例如 `/api/tw-stock/monitor/scan` 或 `/api/tw-stock/monitor/alerts`。

## 7. 测试与证据审查

执行报告中的主要测试结果可复现。

补充说明：部分 `python scripts/...` CLI 命令在普通沙箱下出现：

```text
bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
```

审查者按权限规则提权重跑了本地 validator CLI。提权命令只读取工作区文件或 `/tmp` 临时样本，不访问网络，不调用 OpenAI。

静态 OpenAI 检索：

```bash
rg -n "OPENAI_API_KEY|api.openai.com|chat/completions|@openai" scripts/validate_tw_agent_daily_prompt_artifact.py backend/tests/test_tw_stock_agent_daily_prompt_validator.py data_tw/golden_samples/agent_daily_prompt docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md
```

结果：无命中。

危险词静态检索命中均在合同说明、validator 禁止词表、`fail_forbidden_action` 负样本中；pass sample 未见 OpenAI key 或真实交易执行入口。

## 8. 工作树一致性审查

当前工作树还出现以下未跟踪文件：

```text
.agents/skills/frontend-design/LICENSE.txt
.agents/skills/frontend-design/SKILL.md
skills-lock.json
```

这些文件未列入 `PHASE1_EXECUTION_REPORT_CN.md` 的改动文件列表，也不属于 Phase 1 DailyAgentPromptArtifact validator 的必要产物。执行者必须说明来源；若是误生成或无关变更，应由用户/统筹决定是否移除或单独处理。审查者本轮不回滚这些文件。

## 9. 发现的问题

### High

1. validator 漏检 monitor 写入安全红线。
   证据：`/tmp/agent_prompt_monitor_gap` 中包含 `trigger monitor scan and save monitor alerts`，重算 checksum 后 validator 返回 `PASS`。
   影响：Phase 2 构建脚本如果依赖该 validator，可能生成含 monitor scan/alerts write 语义的 prompt artifact 并被错误放行。
   处理：必须在 Phase 1 修复后复审。

### Medium

1. 合同安全红线未显式列出 monitor config/scan/alerts。
   影响：合同与项目宪法、Phase 1 工作单不一致。
   处理：补合同、补 validator、补 fail sample、补测试。

2. 工作树存在未报告的 `.agents/skills/frontend-design` 与 `skills-lock.json`。
   影响：Phase 1 执行报告的改动文件列表不完整，且变更与本阶段目标无关。
   处理：执行者说明来源，统筹决定保留、移除或单独记录。

### Low

1. validator 对 prompt_text 的 forbidden allowlist 依赖行级否定词。
   影响：Phase 1 可接受，但 Phase 3 输出 validator 不能照搬该宽松规则，否则模型可能用否定句夹带行动建议。
   处理：后续输出安全校验要使用更严格的结构化 intent/blocked 校验。

## 10. 必须修复项

进入 Phase 2 前必须完成：

1. 在合同安全红线中补充 monitor config/scan/alerts 写入。
2. 在 validator forbidden patterns 中补充 monitor 相关危险语义和 endpoint/path。
3. 新增 `data_tw/golden_samples/agent_daily_prompt/fail_monitor_write/`。
4. pytest 中加入 `fail_monitor_write` 必须失败的断言。
5. 运行并报告：

```bash
python -m py_compile scripts/validate_tw_agent_daily_prompt_artifact.py
python scripts/validate_tw_agent_daily_prompt_artifact.py data_tw/golden_samples/agent_daily_prompt/pass
python scripts/validate_tw_agent_daily_prompt_artifact.py data_tw/golden_samples/agent_daily_prompt/fail_monitor_write --allow-golden-missing-sources
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py -q
rg -n "monitor config|monitor scan|monitor alerts|/monitor/config|/monitor/scan|/monitor/alerts" scripts/validate_tw_agent_daily_prompt_artifact.py data_tw/golden_samples/agent_daily_prompt docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md
```

6. 在执行报告或补充报告中解释 `.agents/skills/frontend-design` 和 `skills-lock.json`。

## 11. 可后续优化项

- 将 forbidden action 词表抽成共享常量或文档，供 Phase 2 builder、Phase 3 output validator 和 Phase 4 frontend static check 复用。
- 为 endpoint/path 类危险内容单独做正则规则，不只依赖自然语言关键词。
- 后续 Phase 3 区分输入 artifact validator 和模型输出 validator，输出 validator 应更严格。

## 12. 是否允许进入 Phase 2

不允许进入 Phase 2。

当前 Phase 1 未满足放行标准：

```text
validator 是否真的能挡住 monitor、broker、quick-trade、orders、target position、provider publish、accepted latest 等危险内容
```

其中 monitor 写入红线未通过。
