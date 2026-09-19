# Phase 2 审查意见：每日 Prompt Artifact 构建脚本

生成日期：2026-06-19

## 1. 审查结论

审查结论：通过。

允许进入 Phase 3，但范围仅限“Simple Chat 后端服务”。不得改前端，不得直连 OpenAI，不得触发 provider publish、accepted latest、monitor、broker/order/quick-trade，不得进入日更编排。

## 2. 主线一致性判断

Phase 2 执行符合路线：

```text
只读 source artifacts / fixture
  -> DailyAgentPromptArtifact
  -> Phase 1 validator
```

执行者没有提前改 `/api/tw-stock/agent/chat`、前端、OpenAI adapter 或日更脚本。当前 builder 只从本地 JSON source artifacts 或 fixture 构建，不启动后端、不调用 API、不读取实验 CSV。

## 3. 安全边界审查

已检查 `scripts/build_tw_agent_daily_prompt_artifact.py`，未发现网络库调用、HTTP 请求、POST/PUT/PATCH/DELETE、provider publish、accepted latest switch、monitor config/scan/alerts、broker/order/quick-trade 逻辑。

已复现：

```bash
python -m py_compile scripts/build_tw_agent_daily_prompt_artifact.py scripts/validate_tw_agent_daily_prompt_artifact.py
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py backend/tests/test_tw_stock_agent_daily_prompt_builder.py -q
```

结果：

```text
9 passed in 0.13s
```

builder CLI 在普通沙箱下仍会出现 `bwrap` 限制；审查按权限规则提权重跑本地 CLI。提权命令只读 fixture、写 `/tmp`，不访问网络，不调用 OpenAI。

已复现 dry-run：

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

已复现 validator：

```bash
python scripts/validate_tw_agent_daily_prompt_artifact.py /tmp/tw_agent_daily_prompt_build
```

结果：

```text
PASS: /tmp/tw_agent_daily_prompt_build
```

已复现 asof/target_date 负样本失败：

```text
FAIL: source_target_date_mismatch:readonly_strategy_snapshot:2026-06-20!=2026-06-19
```

## 4. Artifact 审查

生成的 `/tmp/tw_agent_daily_prompt_build` 包含：

```text
manifest.json
prompt_context.json
prompt_text.md
source_stubs/*.json
```

manifest 符合 Phase 1 合同：

- `artifact_type=tw_agent_daily_prompt`
- `schema_version=tw_agent_daily_prompt_v1`
- `readonly_only=true`
- `not_order=true`
- `not_target_position=true`
- `production_trade_enabled=false`
- 当前产品模型。
- 默认策略 `top50_exit_one_worst_sell`。
- `execution_price_mode=next_open`。
- `source_artifacts` 指向输出目录内存在的 stubs。
- checksum 可复算。

prompt_context 保留了：

- `execution_price_status=pending`
- `freshness.status=pending`
- `paper_portfolio.apply_allowed=false`
- `blocked_reason=next_open_pending`
- warnings：`execution_price_pending`、`freshness_pending`、`next_open_pending`、`fixture_only_not_production`

prompt_text 是 compact research-only summary，没有真实交易执行、仓位、收益承诺或写入入口。

## 5. Dry-run 与 Latest Pointer 审查

默认 dry-run 只写 `--output-dir`，未写生产 latest。审查时确认：

```text
data_tw/artifacts/agent_daily_prompt/latest.json
```

不存在。

显式 `--publish-latest --latest-path /tmp/tw_agent_daily_prompt_latest.json` 时，只写 Agent prompt pointer：

```json
{
  "artifact_type": "tw_agent_daily_prompt_latest",
  "signal_asof": "2026-06-18",
  "artifact_dir": "/tmp/tw_agent_daily_prompt_build_publish",
  "manifest": "/tmp/tw_agent_daily_prompt_build_publish/manifest.json",
  "checksum": "sha256:c391e5e2b37e0257f213c95ef44b527f9f44a23622c74fb29255eb2b9691b3ab"
}
```

该 pointer 未包含 provider/qlib accepted latest、provider publish、monitor、broker/order/quick-trade 字段。

## 6. 测试与静态检查审查

静态 OpenAI 检索：

```bash
rg -n "OPENAI_API_KEY|api.openai.com|chat/completions|@openai" scripts/build_tw_agent_daily_prompt_artifact.py scripts/validate_tw_agent_daily_prompt_artifact.py backend/tests/test_tw_stock_agent_daily_prompt_builder.py
```

结果：无命中。

危险词静态检索仅命中 builder 中的 blocked policy：

```text
qlib_retrain_or_tune
broker_operation
```

这是允许的 blocked question type，不是执行路径。

## 7. 发现的问题

### Low

1. source `validation.ok=false` 当前进入 warnings，而不是 hard fail。
   Phase 2 工作单允许进入 warning/block；Phase 3 不受影响。Phase 5 或生产构建接入前应决定生产模式是否升级为 hard fail。

2. `--publish-latest` 默认 latest path 是生产 Agent prompt pointer 路径。
   这符合设计，但 Phase 5 前不得接入日更默认路径；生产使用必须保留显式 gate 和 validator 通过条件。

3. 当前仅支持本地 source discovery。
   可接受，因为 Phase 2 不要求真实生产 source 自动发现；后续接真实 source 时必须避免读实验 CSV 或动态服务 payload。

## 8. 必须修复项

Phase 2 无阻塞性必须修复项。

进入 Phase 3 前仍必须遵守：

- 不改前端。
- 不允许前端接触 OpenAI key。
- blocked intent 不调用 OpenAI。
- OpenAI 输入只能来自 DailyAgentPromptArtifact 和用户问题。
- 不允许 tool/function calling。
- 不触发 provider publish、accepted latest、monitor、broker/order/quick-trade。

## 9. 可后续优化项

- 增加生产模式开关，将 source validation warning 升级为 hard fail。
- 为 prompt artifact 增加 citations/source digest 字段，方便 Phase 3 answer citation allowlist。
- Phase 3 复用 Phase 1 validator 读取 artifact，不要绕过 manifest/checksum。

## 10. 是否允许进入 Phase 3

允许进入 Phase 3。

放行范围仅限：

```text
Simple Chat 后端服务
```

不得提前进入前端 Agent 面板、日更编排或真实 OpenAI smoke。
