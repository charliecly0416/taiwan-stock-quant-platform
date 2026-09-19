# POLICY DAOV5: Live Freshness Revalidation And Ops Surface Check

route: DAOV_LIVE_FRESHNESS_REVALIDATION_AND_OPS_SURFACE_CHECK
owner: coordinator
status: CLOSED_PASS
created_at_utc: 2026-08-20
language: zh-CN
production_allowed: false
provider_pull_allowed: false
provider_publish_allowed: false
qlib_refresh_allowed: false
latest_pointer_write_allowed: false
cron_edit_allowed: false
daily_auto_manual_run_allowed: false
openai_call_allowed: false
db_write_allowed: false
monitor_write_allowed: false
broker_order_allowed: false
target_output_allowed: false

## 1. Goal

DAOV5 的目标不是再造一个前端功能，而是对 2026-08-20 的 live 状态做一次只读 revalidation：

- 当前 daily auto 是否还在按工作日推进；
- qlib accepted latest、controlled signal latest、readonly snapshot latest、Agent prompt latest 是否仍然按各自合同更新；
- `/tw-stock-monitor` 现在展示的状态是否仍然能让用户第一眼判断“数据在推进 / 等待窗口 / 阻塞 / 仅只读可用”；
- 如果没有新的表述缺口，就把这条线收口，不再扩大 scope。

用户第一性原则：

- 清晰：不要把不同层的 latest 混成一个日期。
- 准确：只用本地 evidence 和只读 API，不凭前端猜测。
- 简单：首屏应回答“现在是否还在推进、卡在哪里、下一步是什么”。
- 实用：如果当前只是 `today_data_window_wait`，就明确说明是等待窗口，不要伪装成失败。

## 2. Non-goals

本路线不授权：

- provider pull / refresh / publish；
- qlib refresh；
- accepted latest switch；
- controlled signal latest publish；
- readonly snapshot latest publish；
- Agent prompt latest publish；
- protected latest pointer write；
- daily auto manual run；
- cron edit；
- OpenAI 调用；
- DB 写入；
- monitor / broker / order / target 输出；
- frontend/API production default switch；
- 新模型训练、新策略上线、新回测扩展。

## 3. Current Baseline / Facts

截至 2026-08-20，本地已知事实：

- DAOV 路线已经闭环，`/tw-stock-monitor` 已接入 `GET /api/tw-stock/quant/ops/readonly-status`。
- 2026-08-20 04:30 UTC 的最新 daily auto job 为 `today_data_window_wait`，不是写入失败。
- qlib accepted latest 最新为 `2026-08-19`。
- controlled signal latest、readonly snapshot latest、Agent prompt latest 当前最新均为 `2026-08-19`。
- formal provider calendar / provider view 已推进到 `2026-08-19`。
- installed cron 已包含 daily/full 计划和当前自动化 env block。

## 4. Required Prior Documents

执行者和审查者必须读取：

- `docs/tw_portfolio_decision_model/POLICY_DAOV_DAILY_AUTO_OPS_VISIBILITY_FRONTEND_READINESS_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_DAOV4_CLOSURE_AND_OPS_HANDOFF_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_DAOV1_READONLY_OPS_STATUS_CONTRACT_OR_REUSE_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_DAOV3_READONLY_FRONTEND_ACCEPTANCE_REVIEW_CN.md`
- `backend/app/services/tw_stock_readonly_ops_status.py`
- `backend/app/routes/tw_stock.py`
- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/src/api/tw-stock-readonly.js`
- current live evidence under `data_tw/ops/daily_auto_update/*`
- protected latest pointer JSON files under `qlib_pipeline/` and `data_tw/artifacts/`

## 5. Required Skills / Specialist Workflows

- `coordinator-executor-reviewer-workflow`
- `tw-stock-data-freshness-diagnosis`
- `tw-stock-frontend-workbench-ux-review`
- `tw-stock-readonly-e2e-acceptance` only if a UI patch becomes necessary
- `tw-stock-safety-boundary-review` when checking forbidden action wording

## 6. Architecture / Module Boundaries

DAOV5 只允许围绕只读 surfaces 工作：

- `GET /api/tw-stock/quant/ops/readonly-status`
- `GET /api/tw-stock/quant/signals/health`
- `GET /api/tw-stock/quant/signals/latest`
- `GET /api/tw-stock/current-strategy-context`
- `GET /api/tw-stock/readonly-strategy-snapshot`
- `GET /api/tw-stock/agent/context`
- `/tw-stock-monitor` 首屏只读展示
- `data_tw/ops/daily_auto_update/*` 本地 evidence

如果 DAOV5 发现表述缺口，只允许做只读 UI wording / layout 的最小修补，不得引入写入动作。

## 7. Phase Plan

### DAOV5A_CURRENT_LIVE_FRESHNESS_REVALIDATION

只读 inventory，不改代码：

- 读取最新 daily auto job / daily_chain_status；
- 读取 qlib accepted latest / controlled signal latest / readonly snapshot latest / Agent prompt latest；
- 读取 cron installed 文件；
- 对照 `/tw-stock-monitor` 的现有 wording；
- 判断当前是否仍需要任何表述修补。

### DAOV5B_OPTIONAL_SURFACE_HARDENING

仅当 DAOV5A 发现明显用户误读风险时才进入：

- 只做前端只读 wording 或布局微调；
- 不新增任何写入按钮或 action client 依赖。

### DAOV5C_CLOSURE_AND_OPS_HANDOFF

如果 DAOV5A 结论是“当前 live freshness 和 surface 已足够清楚”，则直接收口：

- 给出是否需要继续补强的明确结论；
- 给出稳定运维观察建议；
- 不再扩大战线。

## 8. Per-phase Executor Duties

执行者必须：

- 先读本主线和对应 work doc；
- 只执行当前 phase；
- 只用可复核只读 evidence；
- 如发现需要写入或外部调用，立即停止并报告 blocker；
- 写 execution report。

## 9. Per-phase Reviewer Duties

审查者必须：

- 独立读取主线、work doc 和 execution report；
- 核对 live freshness 证据是否足以支撑用户判断；
- 审查是否触碰写入、刷新、发布、cron、OpenAI、DB、monitor、broker、order、target；
- 输出 `PASS`、`PASS_WITH_CONDITIONS`、`FAIL_NEEDS_REPAIR` 或 `STOP`；
- 给出单一推荐下一步。

## 10. Forbidden Actions

整个 DAOV5 禁止：

- real provider pull / refresh / publish；
- qlib refresh；
- accepted latest switch；
- controlled signal / readonly snapshot / Agent prompt publish；
- protected latest pointer write；
- daily auto manual run；
- cron edit；
- OpenAI call；
- DB write；
- monitor config / scan / alerts write；
- broker / quick-trade / order；
- target_position / target_weight；
- frontend/API production default switch。

## 11. Stop Conditions

必须停止并报告：

- 需要任何写入、刷新、发布或 cron 才能完成 revalidation；
- 只读 evidence 不能区分“等待窗口”和“实际阻塞”；
- 前端只能靠 fixture 才能解释当前状态；
- 需要动态生产默认切换才能让用户看懂当前状态；
- 发现新的用户误读风险，且无法仅靠只读 wording 修补。

## 12. Evidence And Validator Requirements

DAOV5A 最少 evidence：

- 最新 `job.json`
- 最新 `daily_chain_status.json`
- `tw-daily-auto-update.installed.cron`
- `qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json`
- `data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json`
- `data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json`
- `data_tw/artifacts/agent_daily_prompt/latest.json`
- `frontend/src/views/tw-stock-monitor/index.vue`
- `backend/app/services/tw_stock_readonly_ops_status.py`

## 13. Closure Criteria

如果 DAOV5A 证明：

- 2026-08-20 的 live job 仍然是正常等待窗口而非写入失败；
- latest 各层当前日期仍可被 `/tw-stock-monitor` 清晰区分；
- 没有新的误导性文案或按钮；

则 DAOV5 直接收口，不新增代码。

## 14. First Executor Command

1. 读取最新 daily auto job / daily_chain_status。
2. 读取 qlib accepted latest、controlled signal latest、readonly snapshot latest、Agent prompt latest。
3. 读取 `tw-daily-auto-update.installed.cron`。
4. 对照现有 `/tw-stock-monitor` wording，判断是否存在误读风险。

## 15. First Reviewer Command

审查 DAOV5A execution report，判断：

- 当前 live freshness 是否已经足够清楚；
- 是否需要进入 DAOV5B；
- 或者可以直接进入 DAOV5C 收口。
