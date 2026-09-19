# Phase 5 审查意见：日更编排接入

生成日期：2026-06-19

## 1. 审查结论

审查结论：通过。

允许进入 Phase 6，但范围仅限“端到端最终验收”。Phase 6 可以做 mock/disabled OpenAI 验收和前端网络 denylist；真实 OpenAI-compatible smoke 如要执行，必须后端环境变量提供密钥，且不得记录真实 key。

## 2. 主线一致性判断

Phase 5 执行符合路线：

```text
日更编排可选 gate
  -> build_tw_agent_daily_prompt_artifact.py
  -> validator
  -> 可选 Agent prompt latest pointer
```

日更接入没有改变前端、Simple Chat API、OpenAI adapter，也没有把 Agent prompt 构建作为主日更链路硬依赖。

## 3. 安全边界审查

已检查 `scripts/run_daily_tw_stock_auto_update.py` 新增逻辑：

- `ENABLE_TW_AGENT_DAILY_PROMPT_BUILD` 默认 `false`，默认不调用 builder。
- `TW_AGENT_DAILY_PROMPT_DRY_RUN` 默认 `true`。
- `TW_AGENT_DAILY_PROMPT_PUBLISH_LATEST` 默认 `false`。
- 只有 gate 打开、非 dry-run、publish latest 打开时，才向 builder 传 `--publish-latest --latest-path ...`。
- latest path 指向 `data_tw/artifacts/agent_daily_prompt/latest.json`，不混同 provider/qlib accepted latest。
- builder 失败时只写 `job["agent_daily_prompt_warning"]`，之后主 job 仍更新为 `daily_auto_update_passed`。

未发现新增 OpenAI、provider publish、accepted latest、monitor config/scan/alerts、broker/order/quick-trade 调用。

## 4. 测试与证据审查

已复现：

```bash
python -m py_compile scripts/build_tw_agent_daily_prompt_artifact.py scripts/validate_tw_agent_daily_prompt_artifact.py scripts/run_daily_tw_stock_auto_update.py
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py backend/tests/test_tw_stock_agent_daily_prompt_builder.py -q
python -m pytest backend/tests/test_tw_stock_agent_simple_chat.py -q
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_orchestration.py -q
```

结果：

```text
9 passed in 0.11s
15 passed in 1.29s
7 passed in 0.06s
```

已复现默认日更静态审计：

```bash
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
```

结果：

```json
{
  "ok": true,
  "status": "passed"
}
```

审计仍报告两个既有 warning：

- `legacy_provider_publish_path_present`
- `legacy_accepted_latest_path_present`

但审计同时确认：

- `legacy_provider_gate_default_disabled=true`
- `default_provider_refresh_reachable=false`
- `default_provider_publish_reachable=false`
- `default_accepted_latest_reachable=false`
- `broker_order_patterns_present=[]`
- `monitor_write_patterns_present=[]`

这与 Phase 5 只读边界一致。

## 5. Orchestration 测试审查

新增 `backend/tests/test_tw_stock_agent_daily_prompt_orchestration.py` 覆盖：

- gate disabled 不调用 builder。
- dry-run 不传 `--publish-latest`。
- publish disabled 不写 latest。
- publish latest 只在 enabled 且非 dry-run 时传入。
- validator failed 保留 previous latest。
- source mismatch 不 publish。
- builder argv 不含 OpenAI、provider publish、accepted latest、monitor、quick-trade、broker、target_weight。

这些测试覆盖 Phase 5 的关键放行条件。

## 6. Runbook 审查

`docs/tw_modular_contracts/TW_DAILY_AUTO_UPDATE_RUNBOOK_CN.md` 已新增 Agent Daily Prompt artifact build 章节，说明：

- 默认 gate。
- 可选路径。
- latest pointer 语义。
- 失败行为。
- 回滚方式。

文档明确 Agent prompt latest 不是 provider accepted latest，也不是 qlib accepted latest。

## 7. 发现的问题

### Low

1. 生产 source artifacts 物化流程仍未在本阶段实现。
   Phase 5 只做编排接入，当前默认 source dir 为 `data_tw/artifacts/agent_daily_prompt/source_artifacts`。真实启用前需要确认 source artifacts 由上游只读链路稳定生成。

2. 日更脚本中既有 legacy provider publish / accepted latest 代码仍存在。
   M3 validator 确认默认不可达；本阶段未触碰该路径。后续审查仍需持续关注非默认 gate。

## 8. 必须修复项

Phase 5 无阻塞性必须修复项。

进入 Phase 6 前仍必须遵守：

- 不记录真实 OpenAI key。
- 不用真实交易 endpoint 做验证。
- 不触发 provider publish、accepted latest、monitor、broker/order/quick-trade。
- E2E 网络 denylist 必须覆盖前端 OpenAI 直连、broker、quick-trade、orders、monitor、provider、accepted latest。

## 9. 可后续优化项

- 生产启用 Agent prompt publish 前，先跑 dry-run 验证 source artifact 齐备、asof 对齐、execution price/freshness warnings 符合预期。
- 将 Agent prompt source artifact 物化流程纳入 readonly artifact runbook。
- Phase 6 最终验收应同时覆盖 disabled OpenAI fallback、mock OpenAI valid/invalid/unsafe 输出、前端网络 denylist。

## 10. 是否允许进入 Phase 6

允许进入 Phase 6。

放行范围仅限：

```text
端到端最终验收
```

不得新增功能，不得扩大 Agent/action/provider/monitor/trading 范围。
