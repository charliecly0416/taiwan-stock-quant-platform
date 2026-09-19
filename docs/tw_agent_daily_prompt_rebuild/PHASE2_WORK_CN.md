# Phase 2 工作文档：每日 Prompt Artifact 构建脚本

生成日期：2026-06-19

## 1. 本阶段范围

Phase 2 只实现每日 `DailyAgentPromptArtifact` 构建脚本，让它从只读 source artifacts 或只读本地文件生成：

```text
data_tw/artifacts/agent_daily_prompt/{signal_asof}/manifest.json
data_tw/artifacts/agent_daily_prompt/{signal_asof}/prompt_context.json
data_tw/artifacts/agent_daily_prompt/{signal_asof}/prompt_text.md
```

构建完成后必须调用 Phase 1 validator 校验输出。

## 2. 明确不做什么

本阶段禁止：

- 不调用 OpenAI。
- 不改前端。
- 不改 `/api/tw-stock/agent/chat`。
- 不新增 `/api/tw-stock/agent/simple-chat`。
- 不写 paper account。
- 不触发 snapshot publish。
- 不触发 provider publish。
- 不切换 provider accepted latest 或 qlib accepted latest。
- 不写 monitor config/scan/alerts。
- 不触发 broker/order/quick-trade。
- 不训练模型、不调参、不跑回放收益筛选。
- 不把 Agent prompt latest pointer 混同 provider/qlib accepted latest。

## 3. 执行者任务清单

1. 新增构建脚本：

```text
scripts/build_tw_agent_daily_prompt_artifact.py
```

2. 构建脚本读取只读 source artifacts，压缩生成 `manifest.json`、`prompt_context.json`、`prompt_text.md`。
3. 默认 dry-run：输出到指定 `--output-dir` 或临时目录，不更新 `data_tw/artifacts/agent_daily_prompt/latest.json`。
4. 只有显式 `--publish-latest` 且 validator 通过时，才允许更新 Agent prompt 自己的 `latest.json`。
5. 构建后必须调用 `scripts/validate_tw_agent_daily_prompt_artifact.py` 或复用其 `validate_artifact(...)`。
6. 新增脚本级测试或 pytest。
7. 输出 `docs/tw_agent_daily_prompt_rebuild/PHASE2_EXECUTION_REPORT_CN.md`。

## 4. 允许的输入来源

输入仅限只读 source artifacts 或本地只读 JSON 文件。优先使用当前项目已有标准只读 artifact/上下文：

- current strategy context
- readonly strategy snapshot
- readonly replay window/index
- paper portfolio latest decision
- productization status
- data freshness / pending status

如果真实 source artifact 暂不可用，允许使用测试 fixture 或 golden sample stub 做构建测试，但执行报告必须明确“不是生产 prompt”。

禁止在 Phase 2 中：

- 启动后端并调用写接口。
- 调用 provider refresh/publish。
- 调用 accepted latest switch。
- 调用 monitor scan/config/alerts。
- 调用 broker/order/quick-trade。
- 调用 OpenAI。

## 5. 输出要求

`manifest.json` 必须符合 Phase 1 合同：

- `artifact_type=tw_agent_daily_prompt`
- `schema_version=tw_agent_daily_prompt_v1`
- `readonly_only=true`
- `not_order=true`
- `not_target_position=true`
- `production_trade_enabled=false`
- 当前产品模型：
  - `e4_frozen_qlib_2018_2022`
  - `e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025`
- `strategy_rule=top50_exit_one_worst_sell`
- `execution_price_mode=next_open`
- `source_artifacts` 指向存在的只读 source artifact 或测试 stub。
- `checksum` 可由 validator 复算。

`prompt_context.json` 至少包含：

- `safety`
- `date_context`
- `model_context`
- `rankings`
- `strategy`
- `paper_portfolio`
- `replay_summary`
- `freshness`
- `answer_policy`

`prompt_text.md` 必须包含：

- research-only / 只读边界。
- qlib score 不是收益率、胜率、涨幅或买入概率。
- 用户问买卖时只能解释只读策略观察。
- JSON 输出合同。

## 6. Pending / Warning 规则

构建脚本不得静默吞掉异常或缺失。以下情况必须进入 warnings、blocked 或 pending 字段：

- source artifact 缺失。
- source artifact asof 不一致。
- current strategy context 与 snapshot 的 `signal_asof` / `target_date` 不一致。
- execution price status 为 pending/unavailable。
- paper portfolio apply 不允许。
- freshness mixed/pending/unavailable。
- source artifact validation 不通过。

如果 source 缺失导致无法确认模型、策略、asof 或执行价口径，构建脚本必须失败，不得生成看似可用的生产 artifact。

## 7. Latest Pointer 规则

默认不更新：

```text
data_tw/artifacts/agent_daily_prompt/latest.json
```

只有显式传入 `--publish-latest` 且 validator 通过，才允许更新。更新的 latest pointer 必须只包含 Agent prompt artifact 信息，例如：

```json
{
  "artifact_type": "tw_agent_daily_prompt_latest",
  "signal_asof": "YYYY-MM-DD",
  "artifact_dir": "data_tw/artifacts/agent_daily_prompt/YYYY-MM-DD",
  "manifest": "data_tw/artifacts/agent_daily_prompt/YYYY-MM-DD/manifest.json",
  "checksum": "sha256:..."
}
```

它不得包含或触发：

- provider accepted latest
- qlib accepted latest
- provider publish
- monitor scan/config/alerts
- broker/order/quick-trade

## 8. 必须新增或修改的文件

建议新增：

```text
scripts/build_tw_agent_daily_prompt_artifact.py
backend/tests/test_tw_stock_agent_daily_prompt_builder.py
docs/tw_agent_daily_prompt_rebuild/PHASE2_EXECUTION_REPORT_CN.md
```

可新增测试 fixture：

```text
data_tw/golden_samples/agent_daily_prompt_builder/...
```

不得修改：

```text
frontend/src/...
backend/app/routes/tw_stock.py
backend/app/services/tw_stock_agent_chat.py
backend/app/services/tw_stock_agent_openai.py
```

除非发现 Phase 2 必须修正 Phase 1 validator 小问题；若修改 validator，必须解释并重跑 Phase 1/2 相关测试。

## 9. 必须运行的测试或静态检查

最低命令：

```bash
python -m py_compile scripts/build_tw_agent_daily_prompt_artifact.py scripts/validate_tw_agent_daily_prompt_artifact.py
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py backend/tests/test_tw_stock_agent_daily_prompt_builder.py -q
python scripts/build_tw_agent_daily_prompt_artifact.py --help
python scripts/build_tw_agent_daily_prompt_artifact.py --input-fixture data_tw/golden_samples/agent_daily_prompt_builder/pass --output-dir /tmp/tw_agent_daily_prompt_build --dry-run
python scripts/validate_tw_agent_daily_prompt_artifact.py /tmp/tw_agent_daily_prompt_build
rg -n "OPENAI_API_KEY|api.openai.com|chat/completions|@openai" scripts/build_tw_agent_daily_prompt_artifact.py scripts/validate_tw_agent_daily_prompt_artifact.py backend/tests/test_tw_stock_agent_daily_prompt_builder.py
rg -n "quick-trade|broker|orders|target-position|target_weight|monitor config|monitor scan|monitor alerts|/monitor/config|/monitor/scan|/monitor/alerts|provider publish|accepted latest|qlib refresh|retrain|调参" scripts/build_tw_agent_daily_prompt_artifact.py data_tw/golden_samples/agent_daily_prompt_builder
```

说明：

- 静态检索如果命中 forbidden terms，必须解释命中位置是禁止词表、拒绝策略、负样本或测试断言。
- 如果普通沙箱下 CLI 命令出现 `bwrap` 限制，报告中必须写明，并按权限规则只对本地只读/临时文件校验命令提权。

## 10. 执行报告必须包含

执行者下一步必须输出：

```text
docs/tw_agent_daily_prompt_rebuild/PHASE2_EXECUTION_REPORT_CN.md
```

报告必须包含：

- 阶段目标。
- 实际完成内容。
- 改动文件列表。
- 输入 source artifacts 或 fixture 说明。
- 输出 artifact 文件结构。
- dry-run 与 publish-latest 行为说明。
- validator 调用方式与结果。
- pending/warning/block 处理说明。
- 只读安全边界说明。
- 测试命令与实际结果。
- 未完成事项。
- 风险与需要审查的问题。
- 是否建议进入 Phase 3。

## 11. 审查者重点检查项

Phase 2 审查者必须检查：

- 构建脚本是否只读。
- 默认是否 dry-run。
- 是否没有 POST/PUT/PATCH/DELETE 或 provider/monitor/broker/order 调用。
- latest pointer 是否只属于 Agent prompt。
- source artifact 缺失/asof mixed/execution price pending 是否进入 warning/block。
- 输出 artifact 是否通过 Phase 1 validator。
- prompt_context 是否足够回答高频问题但不过度塞入大 payload。
- prompt_text 是否保持研究观察，不是买卖建议或收益承诺。

## 12. 停止条件

出现以下任一情况必须停止，不得进入 Phase 3：

- 构建脚本触发 OpenAI。
- 构建脚本触发 provider publish 或 accepted latest switch。
- 构建脚本触发 monitor config/scan/alerts。
- 构建脚本触发 broker/order/quick-trade。
- 构建脚本默认更新 latest pointer。
- latest pointer 与 provider/qlib accepted latest 混淆。
- source artifact 缺失却生成 production-looking artifact。
- 输出 artifact 不能通过 Phase 1 validator。
