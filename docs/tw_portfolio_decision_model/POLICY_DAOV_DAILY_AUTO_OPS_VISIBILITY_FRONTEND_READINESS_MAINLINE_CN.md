# POLICY DAOV: Daily Auto Ops Visibility And Readonly Frontend Acceptance Mainline

route: DAOV_DAILY_AUTO_OPS_VISIBILITY_FRONTEND_READINESS
owner: coordinator
status: CLOSED_PASS
created_at_utc: 2026-07-21
language: zh-CN
production_allowed: false
provider_pull_allowed: false
provider_publish_allowed: false
qlib_refresh_allowed: false
latest_pointer_write_allowed: false
cron_edit_allowed: false
daily_auto_manual_run_allowed: false
openai_call_allowed: false
monitor_write_allowed: false
broker_order_allowed: false

## 1. Goal

DAOV 的目标是把台股工作台从“功能已经存在，但状态分散在日志和文档里”，推进到“用户每天打开前端就能清楚判断系统是否可用”的只读运维可视化状态。

用户第一性原则：

- 清晰：不要让用户猜 `latest` 指哪一层，必须同时展示 provider raw/latest、qlib accepted latest、readonly strategy snapshot latest、Agent DailyAgentPromptArtifact latest。
- 准确：所有状态必须能追溯到现有只读 API 或本地 artifact evidence，不能用前端 fixture、单一日期或乐观文案代替真实状态。
- 简单：首屏只回答四个问题：数据更新到哪、策略上下文到哪、Agent 使用哪天上下文、全自动链路是否还在等待或被安全 gate 阻止。
- 实用：状态必须给出下一步含义，例如“等待自然 cron 重试”“publish 关闭，需要授权”“readonly 可用但不是最新交易日”，而不是只显示工程字段。

DAOV 不是新的策略、模型或交易路线。它是前后端运维可见性和只读验收路线，服务于 DAPR18 自然 cron observation 与后续运维。

## 2. Non-goals

本路线不授权：

- real Yahoo / FinMind / provider pull；
- provider refresh / provider publish；
- qlib refresh；
- accepted latest switch；
- controlled signal latest publish；
- readonly snapshot latest publish；
- Agent prompt latest publish；
- protected latest pointer write；
- daily auto manual run；
- cron edit；
- OpenAI 调用或前端 OpenAI key 暴露；
- DB 写入；
- monitor config save、monitor scan、monitor alerts write；
- broker、quick-trade、order、place order、submit order；
- target_position、target position、target_weight、target weight；
- frontend/API production default switch；
- 新模型训练、新策略上线、回测/OOS 扩展。

如果 DAOV 后续阶段确实需要新增 API 或 UI，只能新增只读聚合/展示，不得把任何写入动作藏在刷新、同步、重试、生成、推进等按钮中。

## 3. Current Baseline / Facts

截至 2026-07-21，本地已有事实：

- DOFUI 已为 `/tw-stock-monitor` 增加首屏 `数据链路状态` 模块，并通过只读 Playwright 审查。
- P0 已收敛 readonly boundary 与 freshness 概念，要求前端/API 不再把单一 `latest_asof` 当成全链路状态。
- DAPR18E_R 已把 daily/full cron 转为 env-block 形式，并启用 DAPR18 controlled latest orchestration dry-run flags。
- DAPR18F 自然 cron evidence 仍在观察期，尚未达到至少 3 个不同有效交易日的 closure 条件。
- 最近已知 DAPR18 evidence 覆盖 `asof=2026-07-20`，`2026-07-21` 部分自然 job 可能仍处于 `today_data_window_wait` 或等待盘后数据状态，必须以本地 job evidence 或只读 status 为准。
- protected latest pointers 仍必须分开解释：
  - `data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json`
  - `data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json`
  - `data_tw/artifacts/agent_daily_prompt/latest.json`
  - `qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json`
  - `data_tw/experiments/option_c_daily_signal/latest_signal.json`

## 4. Required Prior Documents

执行者和审查者必须读取：

- `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`
- `docs/tw_modular_contracts/FRONTEND_READONLY_DISPLAY_CONTRACT_CN.md` if present
- `docs/tw_modular_contracts/TW_CURRENT_STRATEGY_CONTEXT_API_FIELD_DICTIONARY_CN.md` if present
- `docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_P0_READONLY_BOUNDARY_AND_FRESHNESS_CONSOLIDATION_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_DOFUI_DAILY_OPS_FRESHNESS_FRONTEND_ROUTE_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_DOFUI2_READONLY_PLAYWRIGHT_ACCEPTANCE_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_DAPR18_DAILY_AUTO_CONTROLLED_LATEST_PRODUCTIONIZATION_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_DAPR18E_R_CRON_COMMAND_LENGTH_REPAIR_ENV_BLOCK_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_DAPR18E_R_CRON_COMMAND_LENGTH_REPAIR_ENV_BLOCK_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_DAPR18F_NATURAL_CRON_EVIDENCE_REFRESH_AND_ACCEPTANCE_REVIEW_EXECUTION_REPORT_CN.md` if present

如果文档不存在，必须在报告里标记 missing，不得伪造结论。

## 5. Required Skills / Specialist Workflows

- `coordinator-executor-reviewer-workflow`
- `tw-stock-data-freshness-diagnosis`
- `tw-stock-frontend-workbench-ux-review`
- `tw-stock-readonly-e2e-acceptance`
- `tw-stock-safety-boundary-review` when reviewing forbidden action risks
- `tw-stock-modular-integration-regression` when changing backend contracts or API loaders

## 6. Architecture / Module Boundaries

DAOV 只允许围绕以下只读 surfaces 工作：

- 后端只读状态 API：
  - `GET /api/tw-stock/quant/ops/daily-auto-update/status`
  - `GET /api/tw-stock/quant/signals/health`
  - `GET /api/tw-stock/quant/signals/latest?bucket=top30`
  - `GET /api/tw-stock/current-strategy-context`
  - `GET /api/tw-stock/readonly-strategy-snapshot`
  - `GET /api/tw-stock/readonly-replay-window-index`
  - `GET /api/tw-stock/agent/context`
- 前端只读展示：
  - `/tw-stock-monitor` 首屏数据链路状态；
  - 今日策略总览；
  - 候选名单；
  - readonly snapshot；
  - readonly replay / 历史模拟；
  - 模拟账户只读状态；
  - Agent simple-chat 只读解释。
- 本地只读 evidence：
  - `data_tw/ops/daily_auto_update/*/job.json`
  - `data_tw/ops/daily_auto_update/*/daily_chain_status.json`
  - `data_tw/ops/daily_auto_update/*/dapr18_*.json`
  - protected latest pointer JSON
  - frontend acceptance screenshots and network/console audit JSON

DAOV 后续若新增后端聚合 endpoint，命名必须体现只读运维状态，例如 `GET /api/tw-stock/quant/ops/readonly-status`。该 endpoint 只能聚合现有状态和文件读取结果，不能触发刷新、构建、发布、写入或外部调用。

## 7. Phase Plan

### DAOV0_CONTRACT_AND_SURFACE_INVENTORY

只读 inventory，不改代码：

- 盘点现有 frontend freshness 模块和 daily ops panel；
- 盘点现有 backend readonly status endpoints；
- 盘点 DAPR18 cron evidence 文件能否支撑“全自动链路状态”展示；
- 盘点 protected latest pointers 与 API payload 是否能一致表达四类 latest；
- 盘点已有只读 E2E evidence 是否足够作为 DAOV baseline；
- 输出最小缺口清单和 DAOV1 推荐方向。

### DAOV1_READONLY_OPS_STATUS_CONTRACT_OR_REUSE

基于 DAOV0 结果二选一，但由审查结论决定：

- 如果现有 API 足够：冻结前端状态字段映射和 wording contract；
- 如果现有 API 不足：新增一个只读 ops status adapter / endpoint，只聚合本地 evidence 和已有只读服务。

DAOV1 不允许写 latest pointer，不允许运行 daily auto，不允许 provider/qlib/OpenAI/DB/monitor/trading 写入。

### DAOV2_FRONTEND_OPS_VISIBILITY_PATCH

只在 `/tw-stock-monitor` 做用户第一性 UI 修补：

- 把“数据链路状态”升级为可扫描的运维状态摘要；
- 用用户语言展示四层日期、DAPR18 dry-run/publish flags、最近自然 cron evidence、阻塞原因、下一步含义；
- 保持 compact research workbench 风格，不做 landing page，不做营销化说明；
- 不新增任何写入按钮。

### DAOV3_READONLY_FRONTEND_ACCEPTANCE

运行只读验收：

- frontend static checks；
- build；
- Playwright desktop/tablet/mobile screenshots；
- network audit；
- console audit；
- forbidden visible/action audit；
- Agent simple-chat 只读路径审查。

### DAOV4_CLOSURE_AND_OPS_HANDOFF

路线收口：

- 给出 DAOV 是否通过；
- 标记 DAPR18F 自然 cron evidence 仍需等待几天或已满足；
- 给出“现在是否可以从前端开始使用”的明确结论；
- 给出进入稳定运维状态前仍需的最小事项。

## 8. Per-phase Executor Duties

执行者必须：

- 读本主线和对应 work doc；
- 只执行指定阶段；
- 不修改非授权文件；
- 不回滚用户或其他路线已有改动；
- 只用可复核 evidence；
- 写 execution report；
- 如需要继续下一步，提出单一推荐，不给用户“或者/或者”的模糊选择。

DAOV0 执行者不得改代码，只能写报告。

## 9. Per-phase Reviewer Duties

审查者必须：

- 独立读取主线、work doc、execution report；
- 审查四类 latest 是否被混用；
- 审查 evidence 是否足够支撑“用户打开前端能判断系统状态”；
- 审查 forbidden actions 是否被触碰；
- 输出 `PASS`、`PASS_WITH_CONDITIONS`、`FAIL_NEEDS_REPAIR` 或 `STOP`；
- 写下一步工作单。

## 10. Forbidden Actions

整个 DAOV 禁止：

- real Yahoo / FinMind / provider pull；
- provider refresh / publish；
- qlib refresh；
- accepted latest switch；
- controlled signal latest publish；
- readonly snapshot latest publish；
- Agent prompt latest publish；
- protected latest pointer write；
- daily auto manual run；
- cron edit；
- OpenAI call；
- DB write；
- monitor config save / scan / alerts write；
- broker / quick-trade / order；
- target_position / target position / target_weight / target weight；
- frontend/API production default switch。

## 11. Stop Conditions

必须停止并报告：

- 需要用户授权才能执行任何写入、刷新、发布、cron 或 protected pointer 操作；
- 需要 DB、OpenAI、真实 provider 网络或 broker/monitor 写入；
- 现有 evidence 无法判断 DAPR18 natural cron 是否产生有效证据；
- 前端状态只能通过 fixture 假数据表达，无法追溯真实 API 或 artifact；
- API 字段含义不清，可能误导用户把 research ranking 当作收益率、买入概率或目标仓位；
- 验收缺少 screenshots、network audit 或 console audit。

## 12. Evidence And Validator Requirements

DAOV 最少 evidence：

- current API status field map；
- frontend component/import map；
- four-latest pointer map；
- latest-to-UI wording map；
- DAPR18 cron evidence sample map；
- readonly E2E baseline map；
- forbidden action audit；
- execution and review docs for every phase。

DAOV3 以后必须包含：

- desktop/tablet/mobile screenshots；
- `overflowX=false`；
- `forbidden_request_count=0`；
- `console_error_count=0`；
- `page_error_count=0`；
- major panels not blank；
- technical details default collapsed。

## 13. Closure Criteria

DAOV 可关闭的条件：

- 用户能在 `/tw-stock-monitor` 首屏看懂四类 latest 的状态和差异；
- 用户能看懂 DAPR18 是否已接入自然 cron、是否 dry-run、publish 是否关闭；
- 用户能看懂当前 blocker 和下一步含义；
- 前端不会提供隐藏写入、同步、发布、下单、目标仓位或 OpenAI 浏览器调用；
- 只读 E2E/静态检查通过；
- reviewer 给出 PASS 或可接受的 PASS_WITH_CONDITIONS；
- 与 DAPR18F 自然 cron observation 明确连接，不替代 DAPR18F closure。

## 14. First Executor Command

执行 DAOV0：

```text
Read docs/tw_portfolio_decision_model/POLICY_DAOV_DAILY_AUTO_OPS_VISIBILITY_FRONTEND_READINESS_MAINLINE_CN.md and docs/tw_portfolio_decision_model/POLICY_DAOV0_CONTRACT_AND_SURFACE_INVENTORY_WORK_CN.md. Perform readonly inventory only. Write docs/tw_portfolio_decision_model/POLICY_DAOV0_CONTRACT_AND_SURFACE_INVENTORY_EXECUTION_REPORT_CN.md. Do not edit frontend/backend code, do not run daily auto manually, do not call provider/qlib/OpenAI/DB/monitor/broker/order/target actions, and do not write any latest pointer.
```

## 15. First Reviewer Audit Brief

审查 DAOV0：

```text
Read the DAOV mainline, DAOV0 work doc, and DAOV0 execution report. Independently verify the cited files and evidence. Check that DAOV0 is readonly, that four latest concepts are separated, and that the DAOV1 recommendation is a single practical next step. Write docs/tw_portfolio_decision_model/POLICY_DAOV0_CONTRACT_AND_SURFACE_INVENTORY_REVIEW_CN.md with verdict and next work document.
```
