---
created_at: 2026-07-11
status: coordinator_mainline
route: TADRE_TRADINGAGENTS_DECISION_EVALUATION
coordinator: Codex
parent_route: TADR_TRADINGAGENTS_ANALYSIS_TO_DECISION_RESEARCH
parent_closure: PASS_WITH_LIMITS
research_only: true
production_allowed: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
qlib_refresh_allowed: false
readonly_latest_publish_allowed: false
agent_prompt_latest_publish_allowed: false
daily_auto_run_allowed: false
crontab_change_allowed: false
monitor_write_allowed: false
broker_order_allowed: false
target_output_allowed: false
---

# TADRE TradingAgents Decision Evaluation Mainline

## 1. Goal

TADRE 是 TADR 关闭后的真实评估路线，用于研究 TradingAgents sanitized research labels 是否能帮助找到比当前决策方式更好的研究性决策方法。

核心问题：

```text
在不破坏 PIT、readonly、模拟回放、安全边界和生产默认隔离的前提下，
TADR labels / overlays 是否能相对当前 qlib/policy baseline 改善研究性 triage、
风险过滤、候选处理或模拟回放表现？
```

TADRE 允许研究“收益率是否更高”，但只能在受控、PIT-safe、readonly evaluation 中讨论，不能把阶段性结果直接变成生产策略、latest、OrderIntent 发布、paper apply 或实盘行为。

## 2. Starting Point

TADR 已关闭：

```text
TADR5 final review verdict = PASS
route_closure_recommendation = PASS_WITH_LIMITS
real_evaluation_allowed_now = false
data_access_subroute_required_before_evaluation = true
production_integration_allowed = false
performance_or_incremental_value_claim_allowed = false
pcom_publish_or_latest_relevance = false
```

TADR 可复用的研究设计证据：

```text
TADR0 contract / feasibility inventory
TADR1 label schema and deterministic extraction design
TADR2 fixture dataset candidate
TADR3 readonly shadow overlay feasibility design
TADR4 future ablation / incremental value plan
TADR5 closure decision
```

TADR 不足以直接评估收益，因为：

```text
only one accepted real sanitized artifact/date exists
the existing real artifact is metadata-only
TADR2 synthetic rows are schema and validator fixtures only
TADR3 candidate-context fixture is synthetic/documented-shape only
TADR4 defines future metrics only and does not measure them
```

## 3. Non-goals

TADRE 不做：

```text
不接入 production/default model or strategy
不修改 configs/tw_product_artifact_registry.yaml 的默认选择
不写 provider latest / qlib accepted latest / readonly latest / Agent prompt latest
不触发 daily auto 或 crontab
不写 monitor config/scan/alerts
不连接 broker / quick-trade / real order
不输出 target_position / target_weight / quantity / shares / lots
不把 TradingAgents Buy/Sell/Hold 当作策略信号
不使用 TradingAgents price target / stop loss / position sizing
不把研究收益自动升级成默认策略
不把 TADRE 结果作为 PCOM publish/latest readiness evidence
```

## 4. Required Prior Documents

每个 TADRE executor/reviewer 必须按阶段读取相关文件；TADRE0 至少读取：

```text
docs/tw_portfolio_decision_model/POLICY_TADR5_RESEARCH_CLOSURE_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_TADR5_RESEARCH_CLOSURE_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_TADR4_ABLATION_INCREMENTAL_VALUE_PLAN_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_TADR4_ABLATION_INCREMENTAL_VALUE_PLAN_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_TADRE_TRADINGAGENTS_DECISION_EVALUATION_MAINLINE_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/TW_TRADINGAGENTS_READONLY_ANALYSIS_MAINLINE_CN.md
docs/tw_portfolio_decision_model/TRADINGAGENTS_READONLY_TA7_FINAL_ACCEPTANCE_REVIEW_CN.md
```

## 5. Architecture Boundary

TADRE research evidence root:

```text
data_tw/experiments/tradingagents_decision_evaluation/
```

允许的 TADRE research artifacts：

```text
TADREContractArtifact
TADREDataAccessPlan
TADRESanitizedLabelDataset
TADREDecisionOverlayRule
TADREEvaluationDesign
TADREReadonlyEvaluationResult
TADRESafetyAudit
TADREClosureReport
```

禁止在 TADRE 内发布或写入：

```text
provider latest
qlib accepted latest
readonly latest
Agent prompt latest
PCOM evidence root
production/default registry switch
broker/order/quick-trade payload
target_position / target_weight / quantity / shares / lots
```

标准 `OrderIntentArtifact` / `ReplayResultArtifact` 只有在后续 TADRE 阶段明确授权为 `research_only` / `diagnostic_only` / `not_production` / `not_latest` 时才可生成。TADRE0 不生成。

## 6. Evaluation Principle

TADRE 评估必须比较至少两类方法：

```text
Baseline: existing qlib/policy decision path, unchanged
Candidate: same candidate universe plus TADR labels / overlays
```

候选方法可以研究：

```text
manual_review_priority gating
risk_disagreement downweight or exclusion in research replay
event/news sensitivity review queue
evidence_quality filter
combinations of the above
```

但任何 candidate 方法不得：

```text
使用 TradingAgents Buy/Sell/Hold
使用 TradingAgents target price / stop loss / sizing
读取 raw_untrusted tactical prose as product input
改变生产默认策略
输出真实下单或目标仓位
```

## 7. Phase Plan

### TADRE0 - Contract And Data/Evaluation Readiness Inventory

冻结真实评估路线的合同，盘点可用数据、TADR artifacts、现有 baseline/replay 工具、缺口和 stop conditions。

TADRE0 不采集新数据、不跑评估、不跑 TradingAgents。

### TADRE1 - Readonly Data Access / Real Sanitized Coverage Plan

设计如何获得足够多的 real sanitized TradingAgents artifacts，并明确哪些步骤需要用户批准、网络/OpenAI/TradingAgents real run、Yahoo/Scrapling repair 或 fallback data source。

TADRE1 可以形成计划；任何真实联网或 OpenAI/TradingAgents real run 必须由后续执行阶段和工具审批显式放行。

### TADRE2 - Real Sanitized Label Dataset Build

在 TADRE1 通过后，用 approved real sanitized artifacts 构建 PIT-safe label dataset。

### TADRE3 - Research Decision Overlay Rules

定义候选 overlay decision rules。该阶段只能生成 research-only/diagnostic-only rule contracts，不能改 production default。

### TADRE4 - Controlled Readonly Evaluation / Replay

用固定 baseline 和 predeclared candidate overlays 执行受控 readonly evaluation/replay，输出可审计结果。

### TADRE5 - Robustness / Ablation / Negative Controls

做稳定性、窗口、负控、placebo 和敏感性检查，防止按收益过拟合。

### TADRE6 - Research Closure And Go/No-go

决定：

```text
continue research
stop
open separate productionization route
```

TADRE6 本身不得上线。

## 8. Forbidden Actions For All TADRE Phases

除非某一后续阶段工单明确授权并仍保持 research-only，所有阶段默认禁止：

```text
provider publish
accepted latest switch
readonly latest publish
Agent prompt latest publish
daily auto run
crontab change
monitor write
broker / quick-trade / real order
target_position / target_weight / quantity / shares / lots output
production/default switch
PCOM evidence mutation
```

## 9. Stop Conditions

必须 STOP 并回报 coordinator/user：

```text
需要真实 OpenAI/LLM 调用
需要网络访问
需要 Yahoo/Scrapling repair
需要真实 TradingAgents run
需要 provider pull/publish
需要 latest/accepted latest switch
需要 qlib refresh
需要 daily auto / crontab
需要 monitor/broker/order
需要生产策略或默认 registry 修改
需要目标仓位、权重、数量、股数、张数输出
发现 raw_untrusted tactical prose 进入产品或标签
发现评估设计需要使用未来收益/未来价格/未来标签作为决策输入
发现 sample 太少而仍试图声称收益提升
```

## 10. Closure Criteria

TADRE 可关闭为 PASS 的最低条件：

```text
evaluation data lineage is explicit
PIT/leakage controls pass
baseline and candidate rules are predeclared
readonly evaluation/replay evidence is durable and validator-backed
negative controls and robustness do not invalidate the result
forbidden actions audit is clean
production integration remains a separate route
```

如果只完成 TADRE0/TADRE1，可关闭为：

```text
PASS_READINESS_ONLY
STOP_NEEDS_DATA_ACCESS_APPROVAL
STOP_INSUFFICIENT_REAL_SANITIZED_COVERAGE
```

## 11. First Executor Command

```text
Read the TADRE mainline and TADRE0 work document. Execute only TADRE0 contract and data/evaluation readiness inventory. Produce research-only readiness evidence under data_tw/experiments/tradingagents_decision_evaluation/tadre0_contract_data_evaluation_readiness/ and write the TADRE0 execution report. Do not collect new data, run TradingAgents/OpenAI/network/provider/latest/qlib/daily/monitor/broker/order workflows, run replay/evaluation, write data_tw/artifacts, mutate PCOM, or output target/sizing/order semantics.
```

## 12. First Reviewer Brief

```text
Audit whether TADRE0 freezes a safe evaluation route, correctly separates baseline vs candidate overlays, identifies real sanitized coverage gaps, preserves PIT/replay safety, does not execute data access or evaluation, and writes a safe TADRE1 work recommendation.
```
