---
created_at: 2026-07-09
status: coordinator_mainline
route: PBPR_PROVIDER_BRIDGE_PRODUCTIONIZATION
parent_route: DASF_DAILY_AUTOMATIC_SIGNAL_FRESHNESS
production_allowed: false
provider_pull_allowed: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
qlib_refresh_allowed: false
model_scoring_allowed: false
readonly_latest_publish_allowed: false
agent_prompt_publish_allowed: false
order_or_target_output_allowed: false
---

# POLICY_PBPR_PROVIDER_BRIDGE_PRODUCTIONIZATION_MAINLINE_CN

## 1. Goal

PBPR 是 DASF 的后继路线，目标是把 `raw-ready / signal-blocked` 状态推进到可审计的 provider/bridge readiness，再进入 no-publish target-asof scoring dry-run。最终目标不是在本路线直接发布生产 latest，而是建立每日自动链路所需的 provider-or-bridge 生产化前置能力：

```text
daily raw ready
-> daily-chain emits DASF state / required inputs / refined blocker
-> target-asof provider candidate or canonical bridge readiness
-> no-publish Model A dry-run and validators
-> readonly downstream source readiness decision
-> separate go/no-go for publish/latest route
```

PBPR 必须保持 DASF 的关键分离：

```text
raw-ready != provider-ready
provider/bridge-ready != signal-ready
signal-ready != accepted/latest publish-ready
readonly context-ready != readonly latest published
Agent context-ready != Agent prompt latest published
```

## 2. Non-goals

PBPR 默认不授权：

```text
live Yahoo/Scrapling/FinMind provider pull
formal provider/calendar refresh
provider publish
accepted/latest switch
qlib accepted latest switch
readonly latest publish
Agent prompt build or publish
production/default/frontend/monitor behavior change
broker / quick-trade / real order
OrderIntentArtifact generation
target_position / target_weight / quantity / shares / lots output
model training/retraining/tuning
```

任何需要 provider pull、formal refresh、publish/latest switch、target-asof Model A scoring、readonly/Agent publish 或 production behavior change 的阶段，必须在该阶段 work doc 中显式授权，并经 reviewer 通过后才能执行。

## 3. Current Baseline / Facts

PBPR 从 DASF final summary 继承 baseline：

```text
target_asof=2026-07-08
state=raw-ready / signal-blocked
FinMind raw daily price source_max_date=2026-07-08
formal Option C calendar max=2026-06-25
accepted latest signal asof=2026-06-17
readonly snapshot latest signal_asof=2026-06-17 / target_date=2026-06-18
Agent DailyAgentPromptArtifact latest=absent
daily_chain_status.blocked_at=qlib_provider_view_or_formal_calendar
DASF2 refined blocker=validated_provider_candidate_or_existing_isolated_modela_artifact
```

DASF4 closure verdict:

```text
CLOSE_DASF_WAIT_FOR_PROVIDER_OR_BRIDGE
```

Key DASF condition:

```text
daily_chain_status.json has DNG13 required fields but does not yet emit DASF1 top-level state or required_inputs, and does not propagate DASF2 refined blocker into target daily job evidence.
```

## 4. Required Prior Documents

执行者与审查者必须按 phase 读取相关文件，至少包括：

```text
docs/tw_portfolio_decision_model/POLICY_DASF_FINAL_COORDINATOR_SUMMARY_CN.md
docs/tw_portfolio_decision_model/POLICY_DASF4_CLOSURE_GO_NO_GO_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_DASF_DAILY_AUTOMATIC_SIGNAL_FRESHNESS_MAINLINE_CN.md
data_tw/experiments/daily_automatic_signal_freshness/dasf1_contract/automatic_freshness_contract.json
data_tw/experiments/daily_automatic_signal_freshness/dasf2_dry_run_feasibility/blocker_or_ready_decision.json
data_tw/experiments/daily_automatic_signal_freshness/dasf3_validator_orchestrator/daily_chain_required_fields_audit.json
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

每个 PBPR phase 必须有 executor execution report 与 reviewer review opinion。Reviewer 必须控制下一步，不能让 executor 自行扩大到 provider pull、publish/latest switch 或 production 行为。

## 6. Architecture Boundary

PBPR 仅允许围绕以下模块推进：

```text
daily_chain_status / skipped_asof_ledger schema
provider candidate readiness / canonical bridge readiness
Model A inference input / ScoreJob / ModelSignalArtifact no-publish dry-run
validators and forbidden action audit
readonly source context readiness decision
Agent source context readiness decision
```

任何进入 broker/order、target output、production accepted latest、frontend default、monitor write 或 Agent answer behavior 的工作，必须开独立路线。

## 7. Phase Plan

### PBPR0 - Daily-chain Schema Repair

小范围修复 daily auto evidence schema：在 `daily_chain_status.json` 与必要的 job summary 中加入 DASF1 `state`、`required_inputs`、`refined_blocker`、`provider_bridge_readiness_state`。只允许 dry-run / skip-finmind / skip-qlib 验证；不触发 provider、scoring 或 publish。

### PBPR1 - Provider/Bridge Readiness Contract

冻结 target-asof provider candidate 或 canonical bridge 合约，定义可接受输入、验证标准、lineage、forbidden side effects、credential/network boundary。默认仍 design-only，不抓数。

### PBPR2 - Target-asof Provider/Bridge Candidate Build Or Blocker

在 PBPR1 合约授权后，执行 provider/bridge readiness 阶段。若需要 live provider pull，必须先取得用户明确批准；若未批准，只能输出 blocker。不得 publish formal provider 或 accepted latest。

### PBPR3 - Target-asof Model A No-publish Dry-run

仅当 PBPR2 有 validated provider/bridge readiness 后，运行 target-asof Model A dry-run 与 validators。必须保证 no-publish、no accepted latest switch、no readonly/Agent latest publish。

### PBPR4 - Readonly/Agent Source Context Readiness

在 no-publish signal artifact 通过后，构建或验证 readonly source context 与 Agent source context readiness；仍不得发布 latest pointer 或生成交易/target output。

### PBPR5 - Productionization Closure / Publish Route Gate

汇总 PBPR0-PBPR4，给出是否可以另开 publish/latest route 的 go/no-go。PBPR5 本身不 publish。

## 8. Per-phase Executor Duties

Executor 必须：

- 读取本 mainline 与 phase work doc；
- 只执行当前 phase；
- 列明所有命令、产物和 skipped validators；
- 保留 forbidden actions audit；
- 遇到 provider pull、formal refresh、publish/latest switch、scoring、readonly/Agent publish、monitor write、broker/order 或 target output 的未授权需求时停止。

## 9. Per-phase Reviewer Duties

Reviewer 必须：

- 独立读取 mainline、work doc、execution report 与 machine-readable artifacts；
- 审查是否混淆 raw/provider/signal/publish readiness；
- 审查是否误用 `2026-06-26` artifacts 作为 `2026-07-08` readiness；
- 审查 forbidden actions；
- 输出 PASS / PASS_WITH_CONDITIONS / FAIL_NEEDS_REPAIR / STOP；
- 写下一步控制文档或明确阻断原因。

## 10. Forbidden Actions

PBPR0 默认全程禁止：

```text
provider_pull
provider_publish
formal_provider_mutation
accepted_latest_switch
qlib_refresh
model_scoring
readonly_latest_publish
agent_prompt_build_or_publish
production_default_change
frontend_default_change
monitor_write
broker_order_quick_trade
OrderIntentArtifact generation
target_position / target_weight / quantity / shares / lots output
```

PBPR1-PBPR5 只有 phase work doc 显式授权时，才可扩大到 provider/bridge/scoring dry-run；publish/latest 与 trading 输出仍默认禁止。

## 11. Stop Conditions

必须停止并交回 coordinator/user：

- 需要 live provider pull 但 phase 未授权或用户未批准；
- 需要写 formal qlib provider 或 accepted latest pointer；
- 需要发布 readonly latest 或 Agent prompt latest；
- 需要生产默认行为、monitor write 或 broker/order；
- executor 无法从 durable evidence 验证 target-asof lineage；
- reviewer 无法复核 claims。

## 12. Evidence And Validator Requirements

优先使用 durable evidence：

```text
daily_chain_status.json
skipped_asof_ledger.json
job.json
provider_candidate_readiness.json
canonical_bridge_readiness.json
ModelInferenceInput manifest / validator
ScoreJob manifest / validator
ModelSignalArtifact manifest / validator
forbidden_action_audit.json
execution/review docs
```

任何“ready”结论必须带 target asof、source lineage、validator status、forbidden actions。

## 13. Closure Criteria

PBPR 可关闭必须满足：

- PBPR0-PBPR4 均为 PASS 或 accepted PASS_WITH_CONDITIONS；
- target-asof provider/bridge readiness 有 durable evidence，或 blocker 被明确接受；
- no-publish scoring readiness 与 publish/latest readiness 未混淆；
- forbidden actions audit clean；
- 下一条 publish/latest route 是否可开有明确 go/no-go。

## 14. First Executor Command

执行 PBPR0：

```text
读取 PBPR mainline 与 PBPR0 work doc；小范围修复 daily-chain schema，使 dry-run daily_chain_status 输出 DASF1 state、required_inputs、refined_blocker、provider_bridge_readiness_state；只运行 skip-finmind/skip-qlib 或单元级验证；不得 provider pull、scoring、publish/latest 或 Agent/readonly publish。
```

## 15. First Reviewer Brief

审查 PBPR0：

```text
独立核对 schema 新字段、dry-run artifacts、tests/validators、forbidden actions、target-asof blocker；确认没有 provider/scoring/publish/latest/Agent/readonly/trading side effects；决定是否进入 PBPR1 provider/bridge readiness contract。
```
