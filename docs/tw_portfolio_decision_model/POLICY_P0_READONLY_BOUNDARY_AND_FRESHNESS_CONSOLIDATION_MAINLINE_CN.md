# POLICY P0 Readonly Boundary And Freshness Consolidation Mainline

route: P0_READONLY_BOUNDARY_AND_FRESHNESS_CONSOLIDATION
owner: coordinator
status: OPEN
created_at_utc: 2026-07-20
language: zh-CN

## 1. Goal

本路线把当前台股研究工作台收敛为一个可审查、可解释、不会误导用户的 readonly product surface。

P0 解决两个主问题：

1. 只读边界结构化：前端、API、Agent、ops 状态必须清楚区分 readonly 展示、允许的 readonly explanation、模拟账户写入、monitor 写入、ops/publish 写入、provider/qlib 写入、交易相关动作。
2. 新鲜度表达结构化：前端和 API 不得再用单一 `latest_asof` 模糊表达系统状态，必须同时表达 provider raw/latest、qlib accepted latest、readonly strategy snapshot latest、Agent DailyAgentPromptArtifact latest。

本路线的直接目标不是让 protected latest 自动发布，而是让用户每天打开前端时能准确看到：数据更新到哪一层、今日策略是否可作为只读研究上下文使用、哪些下游信息仍在等待自然 cron 或授权 publish。

## 2. Non-goals

本路线不授权：

- provider pull、provider refresh、provider publish；
- qlib refresh、qlib accepted latest switch；
- accepted latest pointer write；
- controlled signal latest publish；
- readonly snapshot latest publish；
- Agent prompt latest publish；
- daily auto manual run；
- OpenAI 调用或 OpenAI 配置变更；
- DB 写入、monitor config save、monitor scan、monitor alerts write；
- broker、quick-trade、order、target position、target weight；
- frontend/API production default switch；
- 新模型训练、新策略上线、回测/OOS 扩展。

如果执行中发现必须触发以上任一动作，立即停止并写 blocker，不得在 P0 内绕过。

## 3. Current Baseline / Facts

截至 2026-07-20 本地 evidence：

- controlled ModelSignal latest: `data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json`
  - `asof=2026-07-17`
  - `signal_asof=2026-07-17`
  - `run_id=dapr8_modela_20260717_contained`
  - `readonly_only=true`
  - `provider_accepted_latest_switch=false`
  - `qlib_accepted_latest_switch=false`
- readonly strategy snapshot latest: `data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json`
  - `asof=2026-07-17`
  - `signal_asof=2026-07-17`
  - `candidate_only=true`
  - `not_provider_accepted_latest=true`
  - `readonly_only=true`
- Agent DailyAgentPromptArtifact latest: `data_tw/artifacts/agent_daily_prompt/latest.json`
  - `signal_asof=2026-07-17`
  - `target_date=2026-07-17`
  - `source_readonly_snapshot_latest=data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json`
  - `readonly_only=true`
- qlib accepted / legacy accepted latest: `qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json`
  - `asof=2026-07-08`
  - `diagnostic_only=true`
  - `research_signal_not_order=true`
- 关键结构风险：
  - `backend/app/routes/tw_stock.py`: 2344 lines，readonly、Agent、ops、monitor、paper/sim、publish-like endpoints 混合。
  - `frontend/src/api/tw-stock.js`: 538 lines，GET readonly wrappers 与 POST/PUT action wrappers 混合。
  - `frontend/src/views/tw-stock-monitor/index.vue`: 7043 lines，主策略、实验、监控、模拟、Agent、ops freshness 混合。
  - `scripts/run_daily_tw_stock_auto_update.py`: 4867 lines，source、validator、orchestration、publish gate、ledger 混合。
- 最终 live 前端验收 evidence 已存在：
  - `data_tw/ops/frontend_acceptance/20260719_final_live/ui2d/`
  - `data_tw/ops/frontend_acceptance/20260719_final_live/agent/`
  - network/console/visible forbidden counters 为 0，移动端 drawer 默认关闭修复已完成。

这些事实说明：系统现在可作为 readonly research workbench 使用，但不是 full automatic production latest publish system。

## 4. Required Prior Documents

执行和审查必须先读：

- `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`
- `docs/tw_modular_contracts/FRONTEND_READONLY_DISPLAY_CONTRACT_CN.md`
- `docs/tw_modular_contracts/TW_CURRENT_STRATEGY_CONTEXT_API_FIELD_DICTIONARY_CN.md`
- `docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_DAPR18_DAILY_AUTO_CONTROLLED_LATEST_PRODUCTIONIZATION_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_DAPR18E_R_CRON_COMMAND_LENGTH_REPAIR_ENV_BLOCK_ENABLEMENT_EXECUTION_REPORT_CN.md`
- `docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_UX_FINAL_SUMMARY_CN.md` when present.

如果任一文档不存在，执行者必须在报告中标记 missing，不得伪造引用。

## 5. Required Skills / Specialist Workflows

- `coordinator-executor-reviewer-workflow`
- `tw-stock-data-freshness-diagnosis`
- `tw-stock-safety-boundary-review`
- `tw-stock-frontend-workbench-ux-review` when editing `/tw-stock-monitor`
- `tw-stock-readonly-e2e-acceptance` when running Playwright or final readonly acceptance
- `tw-stock-modular-integration-regression` when changing API contracts or artifact loaders

## 6. Architecture / Module Boundaries

P0 的目标边界：

- readonly product surface:
  - GET `/api/tw-stock/**` readonly endpoints；
  - POST `/api/tw-stock/agent/simple-chat` 仅限 backend readonly explanation，不得携带 order/target/provider/monitor write 字段；
  - frontend `/tw-stock-monitor` 默认只能 import readonly API client。
- action / mutation surface:
  - monitor config、monitor scan、monitor alerts、paper portfolio apply/reset、sim order、ops dry-run/publish/preflight 等必须和 readonly client 分离；
  - action surface 不得被策略总览、候选名单、readonly snapshot、Agent prompt 默认路径隐式调用。
- freshness surface:
  - 所有用户可见“今日/最新/策略日期”必须能追溯到四类 latest；
  - UI 可以使用用户语言展示，但不能隐藏 qlib accepted latest 与 controlled readonly latest 不一致的事实。
- daily ops surface:
  - DAPR18 当前为 cron no-publish/dry-run observation；
  - UI/Agent 状态只能说明“自动观测/候选构建/发布关闭/等待授权”，不得暗示 protected latest 已自动推进。

## 7. Phase Plan

### P0RBF0_CONTRACT_AND_SURFACE_INVENTORY

只读盘点并落档：

- backend route map: GET/POST/PUT/DELETE endpoint 分类；
- frontend API import map: readonly wrappers 与 action wrappers 分类；
- `/tw-stock-monitor` import/use map；
- 四类 latest pointer map；
- forbidden action keyword/API map；
- P0RBF1-P0RBF3 的最小修复列表。

输出：

- `POLICY_P0RBF0_CONTRACT_AND_SURFACE_INVENTORY_EXECUTION_REPORT_CN.md`
- `POLICY_P0RBF0_CONTRACT_AND_SURFACE_INVENTORY_REVIEW_CN.md`

### P0RBF1_FRONTEND_READONLY_CLIENT_SPLIT

拆分前端 API client：

- 新建 readonly client，例如 `frontend/src/api/tw-stock-readonly.js`；
- 保留 action/mutation wrappers 在单独 action client；
- `/tw-stock-monitor` 主视图只 import readonly client；
- 对 paper/sim/monitor 等写操作若仍保留，必须以显式 action client 和明确 UI 边界存在，不能混入 readonly 主路径；
- 增加静态检查，禁止 readonly workbench import action client 或调用 forbidden endpoints。

### P0RBF2_FRESHNESS_PAYLOAD_AND_UI_COPY_CONSOLIDATION

统一 freshness payload 和前端展示：

- 后端 current-strategy-context / snapshot / agent context 若已有字段则透传，若缺失则返回明确 degraded/missing；
- 前端展示四类 latest：行情/原始来源、qlib accepted、只读策略快照、Agent 回答上下文；
- 标明 DAPR18 当前状态：no-publish dry-run observation；
- 修改误导性“今日策略/最新信号”文案，避免把 2026-07-17 readonly controlled artifacts 解释成 qlib accepted latest 或 provider accepted latest。

### P0RBF3_READONLY_E2E_AND_SAFETY_REGRESSION

运行只读安全和前端验收：

- static forbidden endpoint/import checks；
- unit checks for readonly client split；
- Playwright desktop/tablet/mobile readonly smoke；
- network audit must keep forbidden counts at 0；
- Agent simple-chat 仅允许 backend readonly explanation，无 browser-side OpenAI。

### P0RBF4_CLOSURE_AND_NEXT_ROUTE_DECISION

关闭 P0 并决定下一条主线：

- 若 P0 通过，进入 daily ops observation / DAPR18 natural cron evidence；
- 若 backend route 混合仍是主要风险，开 backend route split route；
- 若 automatic latest 仍是用户最关心问题，开 DAPR18 publish readiness continuation，但必须另行授权。

## 8. Per-phase Executor Duties

执行者必须：

- 读本主线和对应 work doc；
- 只做本阶段授权范围；
- 保持 dirty worktree 中非本阶段改动不被回滚；
- 使用本地 evidence，不臆造 cron、provider、qlib 或 publish 状态；
- 记录所有新增/修改文件；
- 记录未运行测试的原因；
- 写 execution report。

P0RBF0 执行者不得做代码修复，只能读文件并写清单/报告。

## 9. Per-phase Reviewer Duties

审查者必须：

- 独立读取主线、work doc、execution report；
- 检查 forbidden actions 是否被触碰；
- 检查四类 latest 是否被混用；
- 检查 executor 的文件引用和分类是否可复核；
- 给出 `PASS`、`PASS_WITH_CONDITIONS`、`FAIL_NEEDS_REPAIR` 或 `STOP`；
- 写 review，并给出下一阶段工作单或 blocker。

## 10. Forbidden Actions

整个 P0 route 禁止：

- real Yahoo/FinMind/provider pull；
- provider refresh/publish；
- qlib refresh；
- accepted latest switch；
- protected latest pointer write；
- daily auto manual run；
- OpenAI call；
- DB write；
- monitor config save、monitor scan、monitor alerts write；
- broker、quick-trade、order、place order、submit order；
- target_position、target position、target_weight、target weight；
- frontend/API production default switch。

## 11. Stop Conditions

必须停止并报告：

- 需要用户授权才能写 protected latest 或运行 provider/qlib/daily jobs；
- 需要 DB、OpenAI、真实 provider 网络访问或 broker/monitor 写入；
- 发现 frontend 默认路径会触发 forbidden write endpoint；
- executor/reviewer 无法确定某 endpoint 是否 readonly；
- 四类 latest evidence 缺失，无法支撑用户可见状态判断；
- tests/validators 需要 destructive cleanup 或覆盖用户已有改动。

## 12. Evidence And Validator Requirements

P0 evidence 最少包含：

- route map；
- frontend API wrapper map；
- `/tw-stock-monitor` import map；
- latest pointer map；
- forbidden action/import audit；
- static check output；
- final Playwright network/console audit when P0RBF3 runs；
- execution and review docs for every phase。

允许的只读命令包括 `rg`、`sed`、`find`、`wc`、`git diff`、`git status`、读取 JSON/markdown、readonly unit/static tests、readonly Playwright fixture/live smoke。

## 13. Closure Criteria

P0 可关闭的条件：

- `/tw-stock-monitor` readonly 主路径不会 import action/mutation client；
- forbidden endpoints 不会在 readonly E2E 中出现；
- 前端明确展示或解释四类 latest，不再把 single asof 当作全链路状态；
- Agent panel 明确基于 Agent prompt latest 和 readonly snapshot latest，不暗示 OpenAI/browser-side 或交易动作；
- DAPR18 状态被表达为 no-publish/dry-run observation，除非另有后续路线授权；
- static checks 与 readonly E2E 通过；
- reviewer 给出 PASS 或可接受的 PASS_WITH_CONDITIONS。

## 14. First Executor Command

执行 P0RBF0：

```text
Read docs/tw_portfolio_decision_model/POLICY_P0_READONLY_BOUNDARY_AND_FRESHNESS_CONSOLIDATION_MAINLINE_CN.md and docs/tw_portfolio_decision_model/POLICY_P0RBF0_CONTRACT_AND_SURFACE_INVENTORY_WORK_CN.md. Perform only read-only inventory. Write docs/tw_portfolio_decision_model/POLICY_P0RBF0_CONTRACT_AND_SURFACE_INVENTORY_EXECUTION_REPORT_CN.md. Do not edit code, do not run provider/qlib/daily/OpenAI/DB/monitor/broker/order/target actions, and do not write any latest pointer.
```

## 15. First Reviewer Brief

审查 P0RBF0：

```text
Read the P0 mainline, P0RBF0 work doc, and P0RBF0 execution report. Audit whether route/API/import/latest/forbidden maps are complete enough to enter P0RBF1. Verify no forbidden actions or protected pointer writes occurred. Write docs/tw_portfolio_decision_model/POLICY_P0RBF0_CONTRACT_AND_SURFACE_INVENTORY_REVIEW_CN.md with PASS/PASS_WITH_CONDITIONS/FAIL_NEEDS_REPAIR/STOP and next work recommendation.
```
