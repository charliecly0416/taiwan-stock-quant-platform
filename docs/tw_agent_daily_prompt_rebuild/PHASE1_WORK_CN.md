# Phase 1 工作文档：DailyAgentPromptArtifact 合同与 Validator

生成日期：2026-06-19

## 1. 本阶段范围

Phase 1 只做 `DailyAgentPromptArtifact` 合同与 validator。

目标是先把每日 Agent prompt artifact 的文件结构、字段、安全红线、checksum 和 golden sample 验证机制固定下来，供 Phase 2 构建脚本使用。

## 2. 明确不做什么

本阶段禁止：

- 不构建真实生产 prompt。
- 不调用 OpenAI。
- 不改前端。
- 不改 `/api/tw-stock/agent/chat`。
- 不新增 `/agent/simple-chat`。
- 不调用 current strategy API 或启动后端服务读取真实数据。
- 不触发 provider publish。
- 不切换 provider accepted latest 或 qlib accepted latest。
- 不写 monitor config/scan/alerts。
- 不触发 broker/order/quick-trade。
- 不训练模型、不调参、不跑回放收益筛选。

## 3. 执行者任务清单

1. 新增或补充 DailyAgentPromptArtifact 合同文档。
2. 实现独立 validator：`scripts/validate_tw_agent_daily_prompt_artifact.py`。
3. 新增 golden samples，至少包含一个 pass case 和多个 fail case。
4. validator 支持命令行运行，并建议支持 `--json` 输出。
5. 新增最小测试，验证 pass sample 通过、fail sample 失败。
6. 输出 `docs/tw_agent_daily_prompt_rebuild/PHASE1_EXECUTION_REPORT_CN.md`。

## 4. 必须新增或修改的文件

建议新增：

```text
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md
scripts/validate_tw_agent_daily_prompt_artifact.py
data_tw/golden_samples/agent_daily_prompt/pass/manifest.json
data_tw/golden_samples/agent_daily_prompt/pass/prompt_context.json
data_tw/golden_samples/agent_daily_prompt/pass/prompt_text.md
data_tw/golden_samples/agent_daily_prompt/fail_*/manifest.json
data_tw/golden_samples/agent_daily_prompt/fail_*/prompt_context.json
data_tw/golden_samples/agent_daily_prompt/fail_*/prompt_text.md
backend/tests/test_tw_stock_agent_daily_prompt_validator.py
docs/tw_agent_daily_prompt_rebuild/PHASE1_EXECUTION_REPORT_CN.md
```

允许按仓库现有测试目录命名调整测试文件路径，但必须在执行报告中说明。

## 5. 合同必须固定的文件结构

合同至少覆盖：

```text
data_tw/artifacts/agent_daily_prompt/{signal_asof}/manifest.json
data_tw/artifacts/agent_daily_prompt/{signal_asof}/prompt_context.json
data_tw/artifacts/agent_daily_prompt/{signal_asof}/prompt_text.md
data_tw/artifacts/agent_daily_prompt/latest.json
```

必须明确：

- `latest.json` 只是 Agent prompt latest pointer。
- `latest.json` 不是 provider accepted latest。
- `latest.json` 不是 qlib accepted latest。
- Phase 1 不生成真实 `latest.json`，只可在 golden sample 中模拟。

## 6. Validator 必须检查的字段

`manifest.json` 至少检查：

- `artifact_type == "tw_agent_daily_prompt"`
- `schema_version == "tw_agent_daily_prompt_v1"`
- `readonly_only == true`
- `not_order == true`
- `not_target_position == true`
- `production_trade_enabled == false`
- `signal_asof` 存在且形如 `YYYY-MM-DD`
- `target_date` 存在且形如 `YYYY-MM-DD`
- `model_ids.base == "e4_frozen_qlib_2018_2022"`
- `model_ids.treatment == "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025"`
- `strategy_rule == "top50_exit_one_worst_sell"`
- `execution_price_mode == "next_open"`
- `source_artifacts` 存在。
- `validation.ok == true` 或 validator 输出能解释失败原因。
- `checksum` 存在且可复算。

`prompt_context.json` 至少检查：

- `schema_version == "tw_agent_daily_prompt_context_v1"`
- `safety.readonly_only == true`
- `safety.not_order == true`
- `safety.not_target_position == true`
- `safety.not_investment_advice == true`
- `safety.production_trade_enabled == false`
- `date_context.signal_asof` 与 manifest 对齐。
- `date_context.target_date` 与 manifest 对齐。
- `date_context.execution_price_mode == "next_open"`
- `model_context.base_model_id` 与 manifest 对齐。
- `model_context.treatment_model_id` 与 manifest 对齐。
- `model_context.ranking_source == "ltr_rerank_within_qlib_top50"`
- `model_context.candidate_boundary == "qlib_top50"`
- `answer_policy.required_disclaimer` 存在且包含“不构成交易建议”。

`prompt_text.md` 至少检查：

- 包含 research-only / 只读边界说明。
- 包含 qlib score 不是收益率、胜率、涨幅或买入概率的说明。
- 包含 JSON 输出合同说明。
- 不包含真实交易执行语义。

## 7. Validator 必须检查的安全红线

validator 必须在 manifest、prompt_context、prompt_text 全部文本中阻断以下危险内容或字段：

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

允许上下文：

- 明确 disclaimer 中的禁止项。
- blocked question 类型说明。
- readonly backtest / historical simulation 描述。

但 validator 必须避免把行动性文案放行，例如“请下单”“设置目标仓位”“刷新 qlib 并发布 provider”。

## 8. Source Artifacts 规则

Phase 1 不读取真实 source artifact。

validator 对 golden sample 的 `source_artifacts` 可以采用以下策略之一，但必须写入合同和执行报告：

- sample 使用相对路径并在 golden sample 目录内放置最小 stub 文件。
- 或允许 `source_artifacts.*.status == "missing_allowed_for_golden_sample"`，但必须产生 warning，且只允许在 `--allow-golden-missing-sources` 模式下通过。

生产模式 validator 不得静默允许 source artifact 缺失。

## 9. Golden Sample 要求

至少包含：

- pass：完整 readonly sample，应通过。
- fail_readonly_false：`readonly_only=false`，必须失败。
- fail_trade_enabled：`production_trade_enabled=true`，必须失败。
- fail_wrong_model：模型 id 不是当前产品模型，必须失败。
- fail_wrong_strategy：策略不是 `top50_exit_one_worst_sell`，必须失败。
- fail_wrong_execution_price：执行价不是 `next_open`，必须失败。
- fail_forbidden_action：含 broker/order/target_position/quick-trade/provider publish 等危险语义，必须失败。
- fail_checksum：checksum 不匹配，必须失败。

fail case 不需要很多内容，但必须能证明 validator 真的挡住失败路径。

## 10. 必须运行的测试或静态检查

最低命令：

```bash
python -m py_compile scripts/validate_tw_agent_daily_prompt_artifact.py
python scripts/validate_tw_agent_daily_prompt_artifact.py data_tw/golden_samples/agent_daily_prompt/pass
python scripts/validate_tw_agent_daily_prompt_artifact.py data_tw/golden_samples/agent_daily_prompt/fail_readonly_false
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py -q
rg -n "OPENAI_API_KEY|api.openai.com|chat/completions|@openai" scripts/validate_tw_agent_daily_prompt_artifact.py backend/tests/test_tw_stock_agent_daily_prompt_validator.py data_tw/golden_samples/agent_daily_prompt
rg -n "quick-trade|broker|orders|target-position|target_weight|provider publish|accepted latest|qlib refresh|retrain|调参" scripts/validate_tw_agent_daily_prompt_artifact.py data_tw/golden_samples/agent_daily_prompt
```

说明：

- fail sample 的命令预期失败，执行报告必须写清退出码或 pytest 断言结果。
- 静态检索如果命中 forbidden terms，必须解释命中位置是 validator 禁止词表、blocked policy 还是 fail sample；不能把真实 action 文案放进 pass sample。

## 11. 执行报告必须包含

执行者下一步必须输出：

```text
docs/tw_agent_daily_prompt_rebuild/PHASE1_EXECUTION_REPORT_CN.md
```

报告必须包含：

- 阶段目标。
- 实际完成内容。
- 改动文件列表。
- 合同字段摘要。
- validator 检查项。
- golden sample 列表与预期结果。
- 测试命令与实际结果。
- 只读安全边界说明。
- 与大设计文档对应章节。
- 未完成事项。
- 风险与需要审查的问题。
- 是否建议进入 Phase 2。

## 12. 审查者重点检查项

Phase 1 审查者必须检查：

- 合同是否以 DailyAgentPromptArtifact 为中心。
- validator 是否独立可运行。
- pass sample 是否真的通过。
- fail sample 是否真的失败。
- `latest.json` 是否没有混同 provider/qlib accepted latest。
- 当前产品模型、默认策略、next_open 是否被硬性校验。
- forbidden action audit 是否覆盖 broker、quick-trade、orders、target position、monitor、provider publish、accepted latest、qlib refresh/retrain/tune。
- 是否没有调用 OpenAI。
- 是否没有修改前端或 `/agent/chat`。

## 13. 停止条件

出现以下任一情况必须停止并写入执行报告，不得进入 Phase 2：

- 合同字段无法支撑大设计文档要求。
- validator 不能稳定区分 pass/fail sample。
- source artifact 缺失策略不清。
- checksum 规则不清或不可复算。
- prompt latest pointer 与 provider/qlib accepted latest 混淆。
- Phase 1 改了 chat API、前端或 OpenAI adapter。
- Phase 1 触发 OpenAI、provider publish、accepted latest、monitor、broker/order/quick-trade。
