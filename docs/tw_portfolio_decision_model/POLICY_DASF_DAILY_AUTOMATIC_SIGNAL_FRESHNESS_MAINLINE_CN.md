---
created_at: 2026-07-09
status: coordinator_mainline
route: DASF_DAILY_AUTOMATIC_SIGNAL_FRESHNESS
production_allowed: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
qlib_refresh_allowed: false
provider_pull_allowed: false
readonly_dry_run_allowed: true
agent_prompt_publish_allowed: false
order_or_target_output_allowed: false
---

# POLICY_DASF_DAILY_AUTOMATIC_SIGNAL_FRESHNESS_MAINLINE_CN

## 1. Goal

DASF 的目标是回答并落地一个明确的产品要求：

```text
每天 raw data 更新之后，系统应自动推进 calendar/provider view、model signal、readonly strategy snapshot、Agent prompt context 等下游 freshness 产物；不应等到用户打开页面或询问 Agent 时才临时构建。
```

本路线先做 contract-first 的可审计推进：DASF0 到 DASF4 只允许诊断、设计、dry-run/isolated 验证、validator/gate 证据和 closure 决策。默认不授权生产 publish、accepted latest switch、formal qlib refresh、真实 provider pull、Agent prompt latest publish 或交易相关输出。

## 2. Non-goals

DASF0-DASF4 不做：

```text
provider publish
accepted/latest switch
formal qlib refresh
Yahoo/Scrapling/FinMind live pull unless a later explicit phase and user approval authorize it
production/default/frontend/Agent/monitor/order/broker behavior change
Agent prompt latest publish
readonly latest publish
model training/retraining/tuning
new strategy or model research
OrderIntentArtifact generation
target_position / target_weight / quantity / shares / lots output
broker / quick-trade / real order
把 raw-ready 包装成 signal-ready
把 dry-run 结果包装成 production-ready
```

## 3. Current Baseline / Facts

截至 2026-07-09 UTC，本地 evidence 显示：

```text
daily auto 2026-07-08 job exists and passed.
FinMind raw daily price source_max_date=2026-07-08, row_count=25800, symbol_count=150.
formal Option C qlib calendar max=2026-06-25.
qlib_pipeline option_c latest_signal pointer asof=2026-06-17.
readonly strategy snapshot latest signal_asof=2026-06-17 / target_date=2026-06-18.
Agent DailyAgentPromptArtifact latest pointer is absent.
pending_asof.json is absent.
daily_chain_status for 2026-07-08 blocks at qlib_provider_view_or_formal_calendar.
model_signal_gate is present but disabled by default and forbids latest/publish switches.
```

Primary baseline evidence:

```text
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260708_20260708T123001Z/daily_source_inventory.json
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260708_20260708T123001Z/daily_chain_status.json
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260708_20260708T123001Z/skipped_asof_ledger.json
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt
qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
data_tw/catalog/dng9_model_signal_gate_validation.json
```

## 4. Required Prior Documents

执行者与审查者必须按 phase 读取相关文件，至少包括：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R19F_CHECKPOINT_RECONCILIATION_FEASIBILITY_REVIEW_CN.md
docs/tw_data_governance/DNG13_DAILY_AUTO_PRODUCTIONIZATION_CONTRACT_EXECUTION_REPORT_CN.md
docs/tw_data_governance/DNG15_R_A_SAME_LINEAGE_OPTION_C_REFRESH_WORK_CN.md
data_tw/catalog/dng16_daily_auto_model_score_integration_design_validation.json
data_tw/catalog/dng17_daily_auto_provider_candidate_refresh_integration_validation.json
data_tw/catalog/dng18_end_to_end_daily_auto_shadow_closure_validation.json
scripts/run_daily_tw_stock_auto_update.py
scripts/build_tw_model_inference_input.py
scripts/run_tw_model_score_job.py
scripts/validate_tw_score_job.py
```

## 5. Required Skills / Workflows

本路线使用：

```text
coordinator-executor-reviewer-workflow
tw-stock-data-freshness-diagnosis
```

每个 DASF phase 必须有 executor execution report 与 reviewer review opinion。Reviewer 必须给出 `PASS`、`PASS_WITH_CONDITIONS`、`FAIL_NEEDS_REPAIR` 或 `STOP`，并控制下一步。

## 6. Architecture Boundary

DASF 只允许围绕 daily auto freshness 链路：

```text
raw FinMind/ops evidence
formal provider/calendar readiness
validated canonical bridge or isolated provider candidate readiness
Model A inference input / ScoreJob / ModelSignalArtifact
readonly strategy snapshot source context
Agent DailyAgentPromptArtifact source context
daily_chain_status / skipped_asof_ledger / catalog validators
```

任何进入 production accepted latest、provider publish、formal qlib refresh、frontend default behavior、Agent response behavior、monitor write 或 broker/order 的变更，必须开新的显式授权 phase。

## 7. Phase Plan

### DASF0 - Freshness Diagnostic

只读确认当前 raw/latest、qlib accepted/latest、readonly snapshot latest、Agent prompt latest、daily_chain_status、gate 禁用状态。输出诊断 artifacts，不改代码。

### DASF1 - Automatic Freshness Contract

冻结自动链路合约：raw-ready 之后 daily auto 应如何决定 provider/calendar、canonical bridge、Model A score、readonly snapshot、Agent prompt context 的状态与 next action。只写设计/contract 文档和机器可读 schema 草案，不改生产默认。

### DASF2 - Isolated Dry-run Feasibility

验证在不触发 live provider pull/publish/latest switch 的情况下，是否能复用已有 validated candidate/bridge 或已有 artifacts 做 isolated asof dry-run。若缺少可用输入，必须写 blocker，不得现场抓数。

### DASF3 - Validator / Orchestrator Evidence

审查或补强 daily auto 的 validator/gate evidence，使每日 job 自动产出机器可读 freshness readiness、blocked_at、next_required_action、forbidden actions audit。仅允许小范围 readonly/dry-run 代码或 validator 调整；不授权 production switch。

### DASF4 - Closure / Go-No-Go

汇总 DASF0-DASF3 证据，给出是否可以进入下一条生产化路线的决定。DASF4 只能建议下一阶段是否启用某些 gate；不得直接启用。

## 8. Per-phase Executor Duties

Executor 必须：

- 读取本 mainline 与 phase work doc；
- 只执行分配的 phase；
- 生成 execution report；
- 列明读取的文件、产物、命令、跳过项与原因；
- 明确 forbidden actions audit；
- 遇到 live data pull、publish/latest switch、formal refresh、订单或 target output 需求时停止。

## 9. Per-phase Reviewer Duties

Reviewer 必须：

- 独立读取 mainline、work doc、execution report 与关键 evidence；
- 审查是否越界；
- 审查 raw-ready 与 signal-ready 是否被混淆；
- 审查是否遗漏下游 impact；
- 输出 review opinion；
- 若继续推进，写下一阶段 work doc 或确认既有 work doc 可执行。

## 10. Forbidden Actions

DASF0-DASF4 全程禁止：

```text
provider_pull
provider_publish
accepted_latest_switch
qlib_refresh
readonly_latest_publish
agent_prompt_publish
production_default_change
frontend_default_change
monitor_write
broker_order_quick_trade
OrderIntentArtifact generation
target_position / target_weight / quantity / shares / lots output
manual run of scripts/run_daily_tw_stock_auto_update.py without an explicit phase allowing dry-run flags
```

## 11. Stop Conditions

必须停止并交回 coordinator/user：

- 需要 live Yahoo/Scrapling/FinMind request 才能继续；
- 需要修改 formal provider、accepted latest pointer 或 latest_signal pointer；
- 需要发布 readonly snapshot 或 Agent prompt latest；
- 需要生产默认行为变更；
- evidence 显示当前 baseline 与本 mainline facts 矛盾；
- reviewer 无法从本地证据验证 executor claim。

## 12. Evidence And Validator Requirements

优先使用 durable evidence：

```text
job.json
daily_source_inventory.json
daily_chain_status.json
skipped_asof_ledger.json
latest pointer JSON
artifact manifest JSON
validator output JSON
execution/review docs
git diff scoped to DASF files if edits occur
```

不得用口头判断替代 manifest、pointer、validator 或 local evidence。

## 13. Closure Criteria

DASF4 可关闭必须满足：

- DASF0-DASF3 均为 PASS 或 accepted PASS_WITH_CONDITIONS；
- forbidden actions audit clean；
- raw/latest、qlib accepted latest、readonly snapshot latest、Agent prompt latest 的差异被明确解释；
- 自动 freshness 链路的 next required action 可机器读取；
- 是否进入下一条生产化路线有明确 go/no-go。

## 14. First Executor Command

执行 DASF0：

```text
读取本 mainline 与 DASF0 work doc；只读收集 current freshness evidence；生成 DASF0 execution report 与 isolated diagnostic artifacts；不得运行 update/pull/publish/latest/refresh/build prompt。
```

## 15. First Reviewer Brief

审查 DASF0：

```text
独立核对 raw-ready、formal calendar stale、signal pointer stale、readonly snapshot stale、Agent prompt latest absent、daily_chain_status blocker 与 forbidden actions；确认 executor 未触发禁令；给出 PASS/PASS_WITH_CONDITIONS/FAIL/STOP，并控制 DASF1。
```
