# Phase 2 执行报告：每日 Prompt Artifact 构建脚本

生成日期：2026-06-19

## 1. 阶段目标

Phase 2 目标是实现只读 `DailyAgentPromptArtifact` 构建脚本，从本地只读 source artifact JSON 或测试 fixture 生成：

```text
manifest.json
prompt_context.json
prompt_text.md
```

构建完成后必须复用 Phase 1 validator 校验输出。默认 dry-run，不更新 `data_tw/artifacts/agent_daily_prompt/latest.json`。

## 2. 实际完成内容

已完成：

- 新增 `scripts/build_tw_agent_daily_prompt_artifact.py`。
- 新增 builder fixture：`data_tw/golden_samples/agent_daily_prompt_builder/pass`。
- 新增 asof/target_date mismatch 负样本：`data_tw/golden_samples/agent_daily_prompt_builder/asof_mismatch`。
- 新增 pytest：`backend/tests/test_tw_stock_agent_daily_prompt_builder.py`。
- builder 输出后自动调用 `validate_artifact(...)`。
- builder 默认 dry-run，只写指定 `--output-dir`。
- 只有显式 `--publish-latest` 且 validator 通过时，才写 Agent prompt 自己的 latest pointer；本次仅测试写入 `/tmp/tw_agent_daily_prompt_latest.json`，未写生产 latest。

## 3. 改动文件列表

新增/更新文件：

- `scripts/build_tw_agent_daily_prompt_artifact.py`
- `backend/tests/test_tw_stock_agent_daily_prompt_builder.py`
- `data_tw/golden_samples/agent_daily_prompt_builder/pass/source_artifacts/current_strategy_context.json`
- `data_tw/golden_samples/agent_daily_prompt_builder/pass/source_artifacts/readonly_strategy_snapshot.json`
- `data_tw/golden_samples/agent_daily_prompt_builder/pass/source_artifacts/readonly_replay_window.json`
- `data_tw/golden_samples/agent_daily_prompt_builder/pass/source_artifacts/paper_portfolio_decision.json`
- `data_tw/golden_samples/agent_daily_prompt_builder/pass/source_artifacts/productization_status.json`
- `data_tw/golden_samples/agent_daily_prompt_builder/asof_mismatch/source_artifacts/*`
- `docs/tw_agent_daily_prompt_rebuild/PHASE2_EXECUTION_REPORT_CN.md`

本阶段未修改：

- `frontend/src/...`
- `backend/app/routes/tw_stock.py`
- `backend/app/services/tw_stock_agent_chat.py`
- `backend/app/services/tw_stock_agent_openai.py`

## 4. 输入 Source Artifacts / Fixture 说明

本阶段使用测试 fixture，不是生产 prompt：

```text
data_tw/golden_samples/agent_daily_prompt_builder/pass/source_artifacts/
```

包含只读 JSON：

- `current_strategy_context.json`
- `readonly_strategy_snapshot.json`
- `readonly_replay_window.json`
- `paper_portfolio_decision.json`
- `productization_status.json`

这些 fixture 使用 `signal_asof=2026-06-18`、`target_date=2026-06-19`、当前产品模型、默认策略 `top50_exit_one_worst_sell` 和 `execution_price_mode=next_open`。

另有负样本：

```text
data_tw/golden_samples/agent_daily_prompt_builder/asof_mismatch/
```

其中 `readonly_strategy_snapshot.target_date=2026-06-20`，builder 会失败并输出 `source_target_date_mismatch`。

## 5. 输出 Artifact 文件结构

测试 dry-run 输出到：

```text
/tmp/tw_agent_daily_prompt_build/
  manifest.json
  prompt_context.json
  prompt_text.md
  source_stubs/*.json
```

`manifest.json` 通过 Phase 1 validator，包含：

- `artifact_type=tw_agent_daily_prompt`
- `schema_version=tw_agent_daily_prompt_v1`
- `readonly_only=true`
- `not_order=true`
- `not_target_position=true`
- `production_trade_enabled=false`
- 当前产品模型与默认策略
- `execution_price_mode=next_open`
- `source_artifacts` 指向输出目录内存在的 `source_stubs/*.json`
- validator 可复算的 checksum

## 6. Dry-run 与 Publish-latest 行为

默认行为：

```text
--dry-run / 未传 --publish-latest
```

只写 `--output-dir`，不更新 `data_tw/artifacts/agent_daily_prompt/latest.json`。

显式 publish 行为：

```bash
python scripts/build_tw_agent_daily_prompt_artifact.py \
  --input-fixture data_tw/golden_samples/agent_daily_prompt_builder/pass \
  --output-dir /tmp/tw_agent_daily_prompt_build_publish \
  --publish-latest \
  --latest-path /tmp/tw_agent_daily_prompt_latest.json \
  --json
```

结果：写入 `/tmp/tw_agent_daily_prompt_latest.json`，内容为 Agent prompt pointer：

```json
{
  "artifact_type": "tw_agent_daily_prompt_latest",
  "signal_asof": "2026-06-18",
  "artifact_dir": "/tmp/tw_agent_daily_prompt_build_publish",
  "manifest": "/tmp/tw_agent_daily_prompt_build_publish/manifest.json",
  "checksum": "sha256:c391e5e2b37e0257f213c95ef44b527f9f44a23622c74fb29255eb2b9691b3ab"
}
```

只读检查确认本阶段未写入生产路径：

```text
data_tw/artifacts/agent_daily_prompt/latest.json
```

## 7. Validator 调用方式与结果

builder 内部直接复用：

```python
validate_artifact(output_dir)
```

如果 validator 返回错误，builder 抛出 `BuildError("validator_failed:...")` 并退出非 0。

手动校验：

```bash
python scripts/validate_tw_agent_daily_prompt_artifact.py /tmp/tw_agent_daily_prompt_build
```

结果：

```text
PASS: /tmp/tw_agent_daily_prompt_build
```

## 8. Pending / Warning / Block 处理说明

builder 不静默吞掉 source 状态：

- source artifact 缺失：必需 source 缺失时失败，例如缺少 `current_strategy_context` 或 `readonly_strategy_snapshot`。
- source asof / target_date 不一致：失败，负样本返回 `source_target_date_mismatch`。
- 模型、策略、执行价口径不符合默认产品口径：失败。
- `execution_price_status=pending`：写入 `freshness.warnings` 和 manifest validation warnings。
- `freshness.status=pending`：写入 warnings。
- paper portfolio `apply_allowed=false`：保留 `paper_portfolio.blocked_reason`。
- source validation 不通过：进入 warnings；后续生产构建可根据审查要求升级为 fail。

本阶段 fixture 输出包含 warnings：

```text
execution_price_pending
freshness_pending
next_open_pending
fixture_only_not_production
```

## 9. 测试命令与实际结果

已运行：

```bash
python -m py_compile scripts/build_tw_agent_daily_prompt_artifact.py scripts/validate_tw_agent_daily_prompt_artifact.py
```

结果：通过，退出码 0。

```bash
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py backend/tests/test_tw_stock_agent_daily_prompt_builder.py -q
```

结果：

```text
9 passed in 0.12s
```

```bash
python scripts/build_tw_agent_daily_prompt_artifact.py --help
```

结果：通过，显示 CLI 参数。

```bash
python scripts/build_tw_agent_daily_prompt_artifact.py --input-fixture data_tw/golden_samples/agent_daily_prompt_builder/pass --output-dir /tmp/tw_agent_daily_prompt_build --dry-run
```

结果：

```text
PASS: /tmp/tw_agent_daily_prompt_build
WARNING: execution_price_pending
WARNING: freshness_pending
WARNING: next_open_pending
WARNING: fixture_only_not_production
```

```bash
python scripts/validate_tw_agent_daily_prompt_artifact.py /tmp/tw_agent_daily_prompt_build
```

结果：

```text
PASS: /tmp/tw_agent_daily_prompt_build
```

负样本：

```bash
python scripts/build_tw_agent_daily_prompt_artifact.py --input-fixture data_tw/golden_samples/agent_daily_prompt_builder/asof_mismatch --output-dir /tmp/tw_agent_daily_prompt_build_bad --dry-run
```

结果：预期失败，退出码 1：

```text
FAIL: source_target_date_mismatch:readonly_strategy_snapshot:2026-06-20!=2026-06-19
```

静态 OpenAI 检查：

```bash
rg -n "OPENAI_API_KEY|api.openai.com|chat/completions|@openai" scripts/build_tw_agent_daily_prompt_artifact.py scripts/validate_tw_agent_daily_prompt_artifact.py backend/tests/test_tw_stock_agent_daily_prompt_builder.py
```

结果：无命中，退出码 1。

危险词静态检查：

```bash
rg -n "quick-trade|broker|orders|target-position|target_weight|monitor config|monitor scan|monitor alerts|/monitor/config|/monitor/scan|/monitor/alerts|provider publish|accepted latest|qlib refresh|retrain|调参" scripts/build_tw_agent_daily_prompt_artifact.py data_tw/golden_samples/agent_daily_prompt_builder
```

结果：命中仅在 `answer_policy.blocked_question_types` 中的 `qlib_retrain_or_tune`、`broker_operation`，属于 blocked policy，不是执行路径。builder fixture pass 不包含真实危险 action 文案。

说明：部分 `python scripts/...` CLI 在普通沙箱下可能出现 `bwrap` 限制，本阶段按权限规则对本地构建/校验命令使用提权。命令只读 fixture 或写 `/tmp`，不访问网络，不调用 OpenAI。

## 10. 只读安全边界说明

本阶段没有：

- 调用 OpenAI。
- 启动后端或前端服务。
- 调用 current strategy API。
- 触发真实数据抓取。
- 触发 provider publish。
- 切换 provider accepted latest 或 qlib accepted latest。
- 写 monitor config/scan/alerts。
- 写 paper account。
- 触发 broker/order/quick-trade。
- 训练模型、调参或跑回放收益筛选。

builder 没有网络库调用，没有 POST/PUT/PATCH/DELETE 请求逻辑，没有 provider/monitor/broker/order endpoint 调用。

## 11. 未完成事项

- 尚未接入真实生产 source artifact 发现机制；当前支持 `--source-dir` 和 `--input-fixture`。
- 尚未纳入日更编排；这是 Phase 5 范围。
- 尚未改 `/agent/chat` 或新增 simple chat；这是 Phase 3 范围。
- 尚未改前端 Agent 面板；这是 Phase 4 范围。

## 12. 风险与需要审查的问题

1. source validation 不通过目前进入 warnings，而不是 hard fail。
   Phase 2 工作文档允许 source artifact validation 不通过进入 warning/block；但生产构建是否应 hard fail，建议审查者确认。

2. builder 当前从本地 JSON source artifacts 构建，不启动服务、不调用 API。
   Phase 2 如需接入真实生产 artifact，需要审查 source discovery 规则，避免读取实验 CSV 或动态服务 payload。

3. prompt_text 是 compact summary。
   当前足以覆盖策略、排名、pending、paper gate 和 freshness 的 smoke；Phase 3 如需 intent-specific context，可继续在 simple chat 层裁剪。

## 13. 是否建议进入 Phase 3

建议进入 Phase 3，但仅限审查者复审通过后执行“Simple Chat 后端服务”。

Phase 3 仍必须保持：

- blocked intent 不调用 OpenAI。
- OpenAI 只消费 DailyAgentPromptArtifact 和用户问题。
- 不允许 tool/function calling。
- 不改前端直连 OpenAI。
- 不触发 provider publish、accepted latest、monitor、broker/order/quick-trade。
