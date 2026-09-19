# Phase 1 执行报告：DailyAgentPromptArtifact 合同与 Validator

生成日期：2026-06-19

## 1. 阶段目标

Phase 1 目标是固定台股 Agent 每日 Prompt artifact 的合同、文件结构、checksum、安全红线和 golden sample 验证机制，为 Phase 2 构建脚本提供稳定输入/输出边界。

本阶段不构建真实生产 prompt，不调用 OpenAI，不改前端，不改 `/api/tw-stock/agent/chat`，不新增 simple chat API，不调用 current strategy API，不触发 provider publish、accepted latest 切换、monitor 写入、broker/order/quick-trade、模型训练或回放收益筛选。

## 2. 实际完成内容

已完成：

- 新增 `DailyAgentPromptArtifact` 合同文档。
- 新增独立 validator：`scripts/validate_tw_agent_daily_prompt_artifact.py`。
- 新增 golden samples：1 个 pass，7 个 fail。
- validator 支持 CLI 与 `--json` 输出。
- validator 支持 `--allow-golden-missing-sources`，但当前 pass sample 已使用本地 stub source artifacts，严格模式也可通过。
- 新增 pytest 覆盖 pass、missing source 策略、fail samples、安全红线。

## 3. 改动文件列表

新增文件：

- `docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md`
- `scripts/validate_tw_agent_daily_prompt_artifact.py`
- `backend/tests/test_tw_stock_agent_daily_prompt_validator.py`
- `data_tw/golden_samples/agent_daily_prompt/pass/manifest.json`
- `data_tw/golden_samples/agent_daily_prompt/pass/prompt_context.json`
- `data_tw/golden_samples/agent_daily_prompt/pass/prompt_text.md`
- `data_tw/golden_samples/agent_daily_prompt/pass/source_stubs/current_strategy_context_stub.json`
- `data_tw/golden_samples/agent_daily_prompt/pass/source_stubs/readonly_strategy_snapshot_stub.json`
- `data_tw/golden_samples/agent_daily_prompt/fail_readonly_false/*`
- `data_tw/golden_samples/agent_daily_prompt/fail_trade_enabled/*`
- `data_tw/golden_samples/agent_daily_prompt/fail_wrong_model/*`
- `data_tw/golden_samples/agent_daily_prompt/fail_wrong_strategy/*`
- `data_tw/golden_samples/agent_daily_prompt/fail_wrong_execution_price/*`
- `data_tw/golden_samples/agent_daily_prompt/fail_forbidden_action/*`
- `data_tw/golden_samples/agent_daily_prompt/fail_checksum/*`
- `docs/tw_agent_daily_prompt_rebuild/PHASE1_EXECUTION_REPORT_CN.md`

未修改业务 API、前端、OpenAI adapter、日更脚本或真实数据 artifact。

## 4. 合同字段摘要

合同固定生产路径：

```text
data_tw/artifacts/agent_daily_prompt/{signal_asof}/manifest.json
data_tw/artifacts/agent_daily_prompt/{signal_asof}/prompt_context.json
data_tw/artifacts/agent_daily_prompt/{signal_asof}/prompt_text.md
data_tw/artifacts/agent_daily_prompt/latest.json
```

明确 `latest.json` 只是 Agent prompt latest pointer，不是 provider accepted latest，不是 qlib accepted latest，不触发 publish 或切换。

`manifest.json` 固定：

- `artifact_type=tw_agent_daily_prompt`
- `schema_version=tw_agent_daily_prompt_v1`
- `readonly_only=true`
- `not_order=true`
- `not_target_position=true`
- `production_trade_enabled=false`
- `model_ids.base=e4_frozen_qlib_2018_2022`
- `model_ids.treatment=e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025`
- `strategy_rule=top50_exit_one_worst_sell`
- `execution_price_mode=next_open`
- `source_artifacts` 非空且生产模式路径必须存在
- `checksum=sha256:<hex>`

`prompt_context.json` 固定 safety、date_context、model_context、answer_policy 基线字段。

Checksum 规则固定为：

```text
sha256(prompt_context.json raw bytes + "\n" + prompt_text.md raw bytes)
```

manifest 自身不参与 checksum。

## 5. Validator 检查项

validator 已检查：

- 必需文件存在：`manifest.json`、`prompt_context.json`、`prompt_text.md`。
- JSON 可解析且为 object。
- manifest schema、readonly flags、模型、策略、执行价、日期格式、validation.ok。
- prompt_context schema、safety flags、date/model 对齐、ranking source、candidate boundary、required disclaimer。
- prompt_text 包含 research-only/只读边界、qlib score 非收益/胜率/涨幅/买入概率说明、JSON 输出合同。
- source_artifacts 生产模式必须存在；golden missing source 仅在显式参数下允许并产生 warning。
- checksum 可复算且必须匹配。
- forbidden action audit 覆盖 broker、quick-trade、orders、target-position、target_position、target_weight、自动买入/卖出、目标仓位、下单、提交订单、连接券商、刷新 provider、切换 accepted latest、provider publish、qlib refresh、retrain、调参、保证收益、保证上涨、胜率承诺、上涨概率。

validator 允许禁止词出现在明确的 blocked policy/safety field 名称中，例如 `not_target_position` 和 `answer_policy.blocked_question_types`，避免误杀安全声明；但普通上下文字段和 prompt 行中的行动性危险语义会失败。

## 6. Golden Sample 列表与预期结果

| sample | 预期 | 覆盖点 |
| --- | --- | --- |
| `pass` | 通过 | 完整 readonly sample，含本地 source stub，严格模式通过。 |
| `fail_readonly_false` | 失败 | `manifest.readonly_only=false`。 |
| `fail_trade_enabled` | 失败 | `production_trade_enabled=true`，context safety 同步为 true。 |
| `fail_wrong_model` | 失败 | base model 非当前产品模型。 |
| `fail_wrong_strategy` | 失败 | strategy 非 `top50_exit_one_worst_sell`。 |
| `fail_wrong_execution_price` | 失败 | execution price 非 `next_open`。 |
| `fail_forbidden_action` | 失败 | prompt_context/prompt_text 含 broker 和 target_position 行动性危险语义。 |
| `fail_checksum` | 失败 | checksum 不匹配。 |

## 7. 测试命令与实际结果

已运行：

```bash
python -m py_compile scripts/validate_tw_agent_daily_prompt_artifact.py
```

结果：通过。

```bash
python scripts/validate_tw_agent_daily_prompt_artifact.py data_tw/golden_samples/agent_daily_prompt/pass
```

结果：退出码 0，`PASS`。

```bash
python scripts/validate_tw_agent_daily_prompt_artifact.py data_tw/golden_samples/agent_daily_prompt/pass --json
```

结果：退出码 0，输出 `ok=true` JSON。

```bash
python scripts/validate_tw_agent_daily_prompt_artifact.py data_tw/golden_samples/agent_daily_prompt/fail_readonly_false --allow-golden-missing-sources
```

结果：预期失败，退出码 1，错误为 `manifest.readonly_only: expected true, got False`。

其余 fail samples 均已单独运行，结果均为预期失败：

- `fail_trade_enabled`：production trade enabled 被阻断。
- `fail_wrong_model`：错误模型被阻断。
- `fail_wrong_strategy`：错误策略被阻断。
- `fail_wrong_execution_price`：非 next_open 被阻断。
- `fail_forbidden_action`：broker / target_position 被 forbidden action audit 阻断。
- `fail_checksum`：checksum mismatch 被阻断。

```bash
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py -q
```

结果：`4 passed in 0.06s`。

静态检查：

```bash
rg -n "OPENAI_API_KEY|api.openai.com|chat/completions|@openai" scripts/validate_tw_agent_daily_prompt_artifact.py backend/tests/test_tw_stock_agent_daily_prompt_validator.py data_tw/golden_samples/agent_daily_prompt
```

结果：无命中，退出码 1。

```bash
rg -n "quick-trade|broker|orders|target-position|target_weight|provider publish|accepted latest|qlib refresh|retrain|调参" scripts/validate_tw_agent_daily_prompt_artifact.py data_tw/golden_samples/agent_daily_prompt docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md
```

结果：有命中，均为预期位置：合同安全红线说明、validator 禁止词表、`fail_forbidden_action` fail sample。pass sample 无真实危险 action 文案。

说明：部分 `python scripts/...` 命令在普通沙箱下出现 `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`，因此按权限规则使用提权运行本地 validator。提权命令只访问/校验工作区本地文件，不访问网络，不调用 OpenAI。

## 8. 只读安全边界说明

本阶段没有：

- 调用 OpenAI。
- 启动后端或前端服务。
- 调用 current strategy API。
- 触发真实数据抓取。
- 触发 provider publish。
- 切换 provider accepted latest 或 qlib accepted latest。
- 写 monitor config/scan/alerts。
- 触发 broker/order/quick-trade。
- 训练模型、调参或跑回放收益筛选。

新增 validator 和 golden sample 只用于本地 artifact 合同校验。`fail_forbidden_action` 中出现 broker/target_position 是负样本，用于证明 validator 能阻断危险语义。

## 9. 与大设计文档对应章节

对应 `TW_AGENT_DAILY_PROMPT_OPENAI_REBUILD_DESIGN_CN.md`：

- 第 3 节总体架构：DailyAgentPromptArtifact 成为后续 OpenAI 输入中心。
- 第 4 节 DailyAgentPromptArtifact 合同：本阶段固定 manifest、prompt_context、prompt_text、latest pointer 语义。
- 第 9 节 OpenAI 调用约束：本阶段不调用 OpenAI，只为后续 backend-only simple chat 准备 artifact 输入。
- 第 10 节安全校验：validator 实现 deterministic forbidden action、checksum、schema 和引用前置检查的一部分。
- 第 13 节 Validator 要求：已覆盖 readonly flags、source artifacts、asof/model/strategy/execution price、prompt_text、安全词和 checksum。

对应 `TW_AGENT_DAILY_PROMPT_OPENAI_REBUILD_EXECUTION_AND_REVIEW_PLAN_CN.md`：

- 完成 Phase 1：合同与 Validator。
- 未进入 Phase 2：未实现构建脚本，未生成真实生产 prompt。

## 10. 未完成事项

- 尚未实现真实 DailyAgentPromptArtifact 构建脚本；这是 Phase 2 范围。
- 尚未接入 current strategy context、readonly strategy snapshot、readonly replay window、paper decision 等真实 source artifacts；这是 Phase 2 范围。
- 尚未改 `/agent/chat` 或新增 simple chat；这是 Phase 3 范围。
- 尚未改前端 Agent 面板；这是 Phase 4 范围。

## 11. 风险与需要审查的问题

1. Forbidden term allowlist 需要审查。
   validator 允许禁止词出现在 `not_target_position`、`answer_policy.blocked_question_types` 等安全声明位置，避免误杀合同必需字段。审查者应确认允许范围足够窄。

2. Source artifact 策略需要审查。
   当前 pass golden sample 使用本地 stub source files，严格模式通过；validator 仍支持 `--allow-golden-missing-sources` 作为临时样本策略。Phase 2 生产构建必须输出真实存在的 source artifact 路径。

3. prompt_text 安全扫描是行级上下文判断。
   当前允许包含“不能/不得/禁止/blocked/拒绝/not/no”等拒绝语境的危险词行。Phase 3 输出 validator 需要继续加强，避免模型输出用否定句绕过行动建议。

4. `orders` 当前按英文复数词阻断。
   因合同中 `not_order` 是必需字段，validator 没有把 `order` 单数作为通用禁止词，否则会误杀合同字段。真实订单语义主要通过中文“下单/提交订单”、`orders`、target_position、broker 等阻断；审查者可决定是否在 Phase 2/3 引入路径级更细规则。

## 12. 是否建议进入 Phase 2

建议进入 Phase 2，但仅限“每日 Prompt Artifact 构建脚本”。

Phase 2 应继续保持：

- 不调用 OpenAI。
- 默认 dry-run，不更新 latest pointer。
- 不写 paper account。
- 不触发 snapshot publish、provider publish、accepted latest switch、monitor、broker/order/quick-trade。
- 构建后必须调用本阶段 validator。
- source artifact 缺失、asof mixed、execution price pending 必须进入 warning/block，不得静默生成可执行建议。
