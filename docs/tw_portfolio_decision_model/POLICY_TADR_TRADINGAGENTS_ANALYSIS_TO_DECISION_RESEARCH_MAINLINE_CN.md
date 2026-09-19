---
created_at: 2026-07-11
status: coordinator_mainline
route: TADR_TRADINGAGENTS_ANALYSIS_TO_DECISION_RESEARCH
coordinator: future_tadr_coordinator
linked_mainline: PROJECT_CONVERGENCE_OPERATIONS_MAINLINE
pcom_state: WAIT_FOR_MORE_NATURAL_CRON_EVIDENCE
research_only: true
production_allowed: false
provider_pull_allowed: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
qlib_refresh_allowed: false
readonly_latest_publish_allowed: false
agent_prompt_latest_publish_allowed: false
openai_call_allowed: false
daily_auto_run_allowed: false
crontab_change_allowed: false
monitor_write_allowed: false
broker_order_allowed: false
target_output_allowed: false
---

# TADR TradingAgents Analysis-to-Decision Research Mainline

## 1. Goal

TADR 研究 TradingAgents 只读分析结果是否能转化为可审计、可回放、非交易执行的辅助决策信号。

目标不是让 TradingAgents 直接决定买卖，而是研究它的 sanitized analysis 是否能为现有 qlib / policy / readonly strategy chain 增加以下信息：

```text
external_risk_flag
positive_catalyst_flag
negative_catalyst_flag
uncertainty_level
model_disagreement_flag
evidence_quality
news_or_event_sensitivity
manual_review_priority
```

TADR 的第一性问题：

```text
TradingAgents 结构化研究标签是否能在不破坏 PIT、readonly、安全边界的前提下，
对候选排序、风险过滤、人工复盘优先级产生可验证的增量价值？
```

## 2. Why This Can Start Now

PCOM 当前处于等待状态：

```text
PCOM2_OPERATIONS_OBSERVATION_PACK
WAIT_FOR_MORE_NATURAL_CRON_EVIDENCE
```

PCOM 等待自然 cron evidence，不应人为运行 daily auto 或推进 PCOM3。TADR 可以在这个等待期作为独立 research-only 支线启动，因为它不需要触发 PCOM 的 provider、cron、latest 或 publish 行为。

TADR 必须和 PCOM 连接，但不得干扰 PCOM：

```text
PCOM owns operations readiness and publish/latest contracts.
TADR owns research-only TradingAgents-to-decision feasibility.
TADR outputs cannot become PCOM publish inputs until TADR has separate final review and PCOM coordinator explicitly accepts them as research evidence.
```

## 3. Current Baseline

### PCOM baseline

PCOM 已完成：

```text
PCOM0 convergence inventory: PASS
PCOM1 readonly integration regression: PASS after PCOM1R
PCOM2 operations observation pack: WAIT_FOR_MORE_NATURAL_CRON_EVIDENCE
```

PCOM 不授权：

```text
provider pull/publish
accepted latest switch
qlib refresh
readonly snapshot latest publish
Agent prompt latest publish
OpenAI call
daily auto run
crontab change
monitor write
broker/order
target output
production/default switch
```

### TradingAgents baseline

TradingAgents readonly migration 已 TA7 PASS：

```text
repo-local TradingAgents source exists
readonly adapter/artifact/builder/validator exists
GET public payload excludes raw files
frontend readonly panel passed static check
raw TradingAgents tactical prose is not displayed
```

Known optional branch:

```text
2026-06-30 Yahoo chart HTTP 403
```

该问题只影响 controlled real run 日期覆盖，不阻塞 TADR0/TADR1。TADR 不应先修 Yahoo access；若需要补更多日期，必须另开 readonly data-access subroute。

## 4. Non-goals

TADR 不做：

```text
不把 TradingAgents Buy/Sell/Hold 当作策略信号
不使用 TradingAgents price target / stop loss / position sizing
不生成 ModelSignalArtifact
不生成 StrategyRule
不生成 OrderIntentArtifact
不生成 ReplayResultArtifact
不生成 ReadonlyStrategySnapshot
不更新 any latest.json
不接入 current production/default model or strategy
不改变 PCOM、AOGE、ADOR、RSPPR、APLR、PBPR 的结论
不触发 provider pull/publish
不切 accepted latest
不跑 qlib refresh
不跑 daily auto
不改 crontab
不调用 OpenAI
不联网抓 Yahoo/FinMind
不启动真实 TradingAgents run
不写 monitor
不连接 broker / quick-trade / order
不输出 target_position / target_weight / quantity / shares / lots
```

## 5. Required Prior Documents

TADR 新统筹必须先读取：

```text
docs/tw_portfolio_decision_model/POLICY_PROJECT_CONVERGENCE_OPERATIONS_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PCOM_WAITING_STATE_AND_RESUME_PLAN_CN.md
docs/tw_portfolio_decision_model/POLICY_PCOM2_OPERATIONS_OBSERVATION_PACK_REVIEW_CN.md
docs/tw_portfolio_decision_model/TRADINGAGENTS_READONLY_TA7_FINAL_ACCEPTANCE_REVIEW_CN.md
docs/tw_modular_contracts/TW_TRADINGAGENTS_READONLY_ANALYSIS_MAINLINE_CN.md
docs/tw_modular_contracts/ANALYSIS_ARTIFACT_CONTRACT_CN.md
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
```

## 6. Architecture Boundary

TADR 只允许在 research evidence 目录产出：

```text
data_tw/experiments/tradingagents_analysis_to_decision_research/
```

允许 artifact 类型：

```text
TADRContractArtifact
TADRLabelSchemaArtifact
TADRHistoricalLabelDatasetCandidate
TADRAblationPlan
TADRShadowOverlayFeasibilityReport
TADRSafetyAudit
```

禁止 artifact 类型：

```text
ModelSignalArtifact
StrategyRule
OrderIntentArtifact
ReplayResultArtifact
ReadonlyStrategySnapshot
DailyAgentPromptArtifact latest
provider latest
qlib accepted latest
paper portfolio apply payload
```

## 7. Research Hypotheses

TADR 应优先研究这些低风险方向：

```text
H1: TradingAgents disagreement flags improve manual review prioritization.
H2: External risk flags reduce false-positive candidate confidence.
H3: Event/news sensitivity identifies candidates that should be reviewed before promotion.
H4: Evidence quality labels help distinguish robust vs weak narrative support.
```

TADR 不应优先研究：

```text
TradingAgents bullish score as buy score
TradingAgents rating as direct rank boost
TradingAgents target price as return forecast
TradingAgents position sizing as portfolio weight
```

## 8. Phase Plan

### TADR0 - Contract And Feasibility Inventory

只读盘点现有 TradingAgents artifact、sanitizer、validator、public payload、TA7 closure、PCOM connection 和 forbidden fields。

输出：

```text
TADR label schema proposal
allowed / forbidden transformation matrix
available evidence inventory
known blockers
```

TADR0 不运行 TradingAgents，不生成标签数据集。

### TADR1 - Label Schema And Sanitized Extraction Design

设计从 sanitized TradingAgents report 到结构化 research labels 的 schema。

TADR1 只能用 existing sanitized artifacts 或 golden fixtures；不得读取 raw untrusted text 作为产品输入。

### TADR2 - Historical Fixture Dataset Candidate

在已有 artifact/fixture 范围内构造小规模 historical label dataset candidate。

若需要更多真实日期样本，应 STOP，并另开 readonly data-access / controlled real run route。

### TADR3 - Shadow Overlay Feasibility

设计只读 shadow overlay：

```text
existing qlib/policy candidates
+ TADR labels
-> manual_review_priority / risk_disagreement overlay
```

不得产生 OrderIntent、target weights 或 production ranking switch。

### TADR4 - Ablation / Incremental Value Plan

定义 OOS/ablation 评估方案，证明是否有增量价值。

TADR4 可以建议后续实验，但不得上线。

### TADR5 - Research Closure

给出是否值得继续进入更正式 decision research route 的结论。

## 9. Forbidden Actions

所有 TADR 阶段禁止：

```text
provider pull / refresh / publish
accepted latest switch
qlib refresh
daily auto run
crontab install/change
readonly latest publish
Agent prompt latest publish
OpenAI call
real TradingAgents run unless a later explicit route authorizes it
network access
monitor config/scan/alert write
broker / quick-trade / order
OrderIntentArtifact generation
target_position / target_weight / quantity / shares / lots output
production/default switch
```

## 10. Stop Conditions

必须停止并回报：

```text
需要更多真实 TradingAgents run 日期覆盖
需要修 Yahoo/Scrapling access
需要联网或 OpenAI
需要读取 raw untrusted TradingAgents tactical prose 进入产品/Agent/frontend
需要写 latest or accepted latest
需要修改 PCOM / daily cron / provider
需要把标签接入 production decision path
发现 TradingAgents sanitized artifact 仍含 buy/sell/hold/target/position/stop-loss/actionable semantics
```

## 11. PCOM Connection Rule

TADR 可以连接 PCOM 的方式：

```text
as optional research context
as future PCOM appendix after TADR final review
as manual-review-priority evidence
```

TADR 不可以连接 PCOM 的方式：

```text
as publish/latest readiness evidence
as provider freshness evidence
as model signal artifact
as daily automation output
as production strategy gate
as order/target/sizing source
```

PCOM 恢复时，TADR 不得阻塞 PCOM2R/PCOM3。PCOM coordinator 可以选择读取 TADR summary，但不得把 TADR 未关闭研究结果当作 PCOM publish contract input。

## 12. Closure Criteria

TADR 可关闭为 PASS 的最低条件：

```text
label schema is explicit and safe
forbidden transformation matrix complete
available evidence inventory complete
sanitized-only input boundary preserved
no production/latest/provider/cron/OpenAI/trading actions
clear recommendation: continue / stop / data-access subroute needed
```

TADR 不以收益提升为最低 closure 条件；收益或排序增量只应在 TADR4/TADR5 之后讨论。
