---
created_at: 2026-07-11
status: coordinator_mainline
route: PROJECT_CONVERGENCE_OPERATIONS_MAINLINE
coordinator: Codex
scope: consolidate_aoge_pbpr_dng18_tradingagents_readonly
production_allowed: false
provider_pull_allowed: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
qlib_refresh_allowed: false
readonly_latest_publish_allowed: false
agent_prompt_latest_publish_allowed: false
openai_call_allowed: false
monitor_write_allowed: false
broker_order_allowed: false
target_output_allowed: false
---

# Project Convergence Operations Mainline

## 1. Goal

本主线用于把近期并行路线收敛回一条可管理的项目主线：

```text
AOGE operations observation
+ PBPR / DNG18 provider-bridge-readiness evidence
+ TradingAgents readonly migration
-> readonly artifact-backed integration convergence
-> later separate publish/latest go/no-go route
```

核心目标是：在不扩大生产行为、不写 latest、不触发 provider publish 或交易动作的前提下，把各分支的结论统一成一个后续执行入口，避免继续多线发散。

## 2. Current Branch Status

### AOGE

状态：

```text
PASS_CLOSE_AOGE_AND_ENTER_OPERATIONS_OBSERVATION
```

结论：

- actual crontab 已同步到带 ADOR no-publish dry-run gate 的版本；
- 真实 cron job `daily_tw_stock_auto_update_20260710_20260710T123001Z` 已产生 ADOR job-dir evidence；
- `ador_no_publish_orchestration.enabled=true`、`attempted=true`、`ok=true`；
- `latest_pointer_write_performed=false`；
- protected latest 四项 unchanged；
- forbidden audit `all_false=true`。

并入主线方式：作为 operations observation 基线。

不得误读为：publish/latest 自动化已经启用。

### PBPR / DNG18 / Provider Bridge

PBPR5 状态：

```text
PASS_CLOSE_PBPR_ROUTE_AND_RECOMMEND_SEPARATE_PUBLISH_ROUTE_CONFIRMATION
```

DNG18 状态：

```text
2026-06-26 reusable isolated candidate behavior / daily-auto shadow closure evidence
```

结论：

- DNG18 正向证据只证明 `2026-06-26` isolated reuse/orchestrator 行为，不可直接当作 `2026-07-08` readiness；
- PBPR 后续已经用 target-asof `2026-07-08` controlled AC-root evidence 推进到 provider candidate readiness、contained Model A no-publish signal artifact、PBPR4 source context readiness；
- PBPR5 关闭时明确：PBPR 本身不 publish，若要 publish/latest 必须另开独立 route 并取得用户确认。

并入主线方式：作为 readonly source-context readiness 与 future publish route 的前置证据。

不得误读为：formal provider、accepted latest、readonly latest 或 Agent prompt latest 已可自动写入。

### TradingAgents Readonly Migration

状态：

```text
TA7 PASS
TradingAgents readonly migration mainline closed
```

结论：

- repo-local TradingAgents readonly adapter、artifact builder、validator、GET-only loader、frontend readonly panel 已通过验收；
- raw TradingAgents tactical output 不进入 GET/API/frontend 展示面；
- controlled real run 的展示 artifact 已 metadata-only；
- 2026-06-30 Yahoo chart HTTP 403 是数据访问分支问题，不阻塞 migration closure。

并入主线方式：作为 optional readonly analysis context。

不得误读为：TradingAgents 输出可驱动策略、OrderIntent、target weight、broker/order 或 Agent 投资建议。

剩余独立分支：

```text
TradingAgents Yahoo/Scrapling access repair or runtime-only fallback route
```

该分支只影响 TradingAgents controlled real run 的目标日期覆盖，例如 `2026-06-30` Yahoo chart HTTP 403。它不阻塞 PCOM 主线；如果后续要做，只能作为 optional readonly data-access subroute，且不得 provider publish、accepted latest switch、formal provider mutation、Agent prompt publish、OpenAI frontend exposure、broker/order 或 target output。

### R19E / DNG18 Production Readiness Contract

R19E 状态：

```text
PASS_AUTOMATIC_FULL_CRON_ADVANCED_WITH_R19D_CONTINUITY
```

已观察到：

```text
full_cron_jobs_observed=6
latest_raw_daily_price_source_max_date=2026-07-08
latest_raw_daily_price_symbol_count=150
latest_chain_blocked_at=qlib_provider_view_or_formal_calendar
final_observed_done_count=35
forbidden_actions_clean=true
```

DNG18 状态：

```text
PASS_DNG18_CLOSURE
target_asof=2026-06-26
```

统筹结论：

- R19E 证明 full cron accumulation/continuity 已自然推进；
- DNG18 证明 daily-auto provider candidate / model signal gate 的 shadow closure 机制在 prior asof 上成立；
- 两者应该合并到后续 `Daily Auto Production Readiness / Latest Publish Contract`；
- 该合同不是 publish 执行路线，只是 publish 前置合同，必须继续区分 raw-ready、provider-ready、signal-ready、publish-ready。

并入主线方式：作为 PCOM3 的 publish route go/no-go 合同输入。

不得误读为：DNG18 prior-asof evidence 或 R19E raw/full-cron accumulation 已自动授权 latest publish。

## 3. Single Mainline From Here

从本文件之后，默认只保留一条主线：

```text
PCOM - Project Convergence Operations Mainline
```

其他路线处理方式：

- AOGE：进入观察，不继续新功能开发；
- PBPR：关闭，publish/latest 只能另开 route；
- DNG18：归档为 prior-asof mechanism evidence；
- TradingAgents：关闭，作为 optional readonly context 待集成验收；
- DASF/ADOR/RSPPR/APLR：作为前置合同与 artifact 证据，不再并行推进。

## 4. Non-goals

PCOM 不做：

```text
provider pull
provider publish
accepted latest switch
qlib refresh
readonly snapshot latest publish
Agent prompt latest publish
OpenAI call
monitor config/scan/alert write
broker / quick-trade / order
OrderIntentArtifact generation
target_position / target_weight / quantity / shares / lots output
production/default switch
```

## 5. Phase Plan

### PCOM0 - Convergence Inventory

只读盘点 AOGE、PBPR/DNG18、TradingAgents readonly 的 closure verdict、artifact roots、remaining blockers、forbidden-action evidence。

输出：

```text
POLICY_PCOM0_CONVERGENCE_INVENTORY_EXECUTION_REPORT_CN.md
POLICY_PCOM0_CONVERGENCE_INVENTORY_REVIEW_CN.md
```

### PCOM1 - Readonly Integration Regression

运行只读 validators/static checks，确认以下链路能在同一个项目状态中共存：

```text
daily auto ADOR no-publish evidence
PBPR source-context readiness
ReadonlyStrategySnapshot latest
DailyAgentPromptArtifact latest
TradingAgents readonly public payload
frontend readonly panels
Agent simple-chat readonly boundary
```

PCOM1 只允许 readonly/static/fixture checks，不允许填补缺失 artifact。

### PCOM2 - Operations Observation Pack

等待并汇总 3-5 个交易日 cron evidence，确认：

```text
ADOR evidence daily produced
protected latest unchanged
forbidden audit all_false
provider_publish_triggered=false
latest_signal_updated=false
TradingAgents remains optional and does not run from cron
```

### PCOM3 - Publish Route Go/No-go Document

仅在 PCOM1/PCOM2 通过后，写独立 publish/latest route 的 go/no-go 文档。

PCOM3 仍不 publish。它只决定是否值得向用户申请开启下一条 route。

PCOM3 必须吸收并统一：

```text
R19E full-cron continuity conclusion
DNG18 daily-auto shadow closure conclusion
PBPR5 no-publish target-asof readiness separation
AOGE ADOR no-publish operations observation
```

输出应命名为：

```text
Daily Auto Production Readiness / Latest Publish Contract
```

合同必须逐项列出：

```text
which latest pointers are candidates for future publish
which artifact manifests and validators must pass
which cron evidence windows are required
which rollback files/commands are required
which protected paths must be fingerprinted before/after
which forbidden actions remain blocked
```

### PCOM4 - Optional TradingAgents Data Access Subroute

仅当需要扩大 TradingAgents controlled real run 日期覆盖时，才开 PCOM4。

候选方向：

```text
Yahoo/Scrapling access repair
runtime-only fallback data source
```

PCOM4 不得影响主线 daily auto/latest/publish。任何 fallback 都必须标记为 runtime-only / TradingAgents-only / readonly analysis only，不能混入 qlib provider、accepted latest、ModelSignalArtifact、ReadonlyStrategySnapshot 或 Agent DailyAgentPromptArtifact publish 链路。

## 6. Required Evidence

必须引用并复核：

```text
docs/tw_portfolio_decision_model/POLICY_AOGE_FINAL_CLOSURE_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBPR5_PRODUCTIONIZATION_CLOSURE_OR_PUBLISH_ROUTE_GATE_REVIEW_CN.md
docs/tw_data_governance/DNG18_END_TO_END_DAILY_AUTO_SHADOW_CLOSURE_REVIEW_CN.md
docs/tw_portfolio_decision_model/TRADINGAGENTS_READONLY_TA7_FINAL_ACCEPTANCE_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_DASF_FINAL_COORDINATOR_SUMMARY_CN.md
docs/tw_portfolio_decision_model/POLICY_ADOR_FINAL_CLOSURE_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR_FINAL_CLOSURE_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_APLR_FINAL_CLOSURE_REVIEW_CN.md
```

## 7. Closure Criteria

PCOM 可以进入维护状态，当且仅当：

- AOGE cron observation 连续数个交易日稳定；
- readonly integration regression 没有 safety 或 artifact mismatch blocker；
- TradingAgents readonly context 保持 optional，不进入交易或 publish 链路；
- PBPR/DNG18 证据不再被误用为 latest-ready；
- R19E/DNG18 已被归入 publish 前置合同，而不是被当作 publish 授权；
- TradingAgents Yahoo 403 被明确标为 optional data-access branch，不阻塞主线；
- 用户明确知道 publish/latest 自动化尚未开启。

## 8. Coordinator Decision

当前建议：

```text
OPEN_PCOM0_CONVERGENCE_INVENTORY
```

PCOM0 可以立即开始。PCOM1 建议等 PCOM0 review 后执行。PCOM2 需要自然等待 3-5 个交易日 cron evidence。PCOM3 只有在 PCOM1/PCOM2 均通过后才有意义。
