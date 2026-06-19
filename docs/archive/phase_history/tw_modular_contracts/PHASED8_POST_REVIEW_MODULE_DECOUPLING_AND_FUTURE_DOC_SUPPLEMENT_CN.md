# Phase D8 后审查：模块解耦、前端产品性与后续开发文档补充意见

生成日期：2026-06-17

## 1. 总结论

D8 可以作为本轮 readonly replay window 产品化收口版本冻结。

当前已经形成清楚模块边界的部分：

```text
ModelSignalArtifact
  -> StrategyRule / StrategyDecisionEngine
  -> OrderIntentArtifact
  -> ReplayExecutionEngine
  -> ReplayResultArtifact
  -> ReplayWindowPolicy
  -> readonly replay window index
  -> GET-only API
  -> frontend readonly display
```

本轮未发现 D8 收口需要退回的阻塞问题。

但项目还没有达到“所有重要部分都完全模块化”的最终状态。核心研究链路已经解耦，数据接入、FeatureArtifact、PriceStore、日更编排、分析展示、前端组件边界仍需要后续补合同和 validator。

## 2. 已经解耦完成的模块

### 2.1 模型信号层

已有：

```text
MODEL_SIGNAL_CONTRACT_CN.md
MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
FULL_RANK_CONTRACT_CN.md
STRATEGY_DEPENDENCY_CONTRACT_CN.md
```

结论：

```text
qlib / LTR / 后续模型都必须先适配成 ModelSignalArtifact
策略不得读取 legacy 私有模型列
LTR 只能通过 buy_score 重排 top50 内买入顺序
candidate_rank / full_qlib_rank 继续来自底座 qlib
```

该部分边界合理。

### 2.2 策略决策层

已有：

```text
STRATEGY_RULE_CONTRACT_CN.md
ORDER_INTENT_CONTRACT_CN.md
scripts/build_tw_modular_order_intent_artifact.py
scripts/validate_tw_modular_order_intent_artifact.py
```

结论：

```text
策略输出 OrderIntentArtifact
不包含成交、现金、手续费、净值、broker order id
五种策略规则已从回放记账中抽离
diagnostic buggy 规则不得作为有效策略证据
```

该部分边界合理。

### 2.3 回放执行层

已有：

```text
REPLAY_RESULT_CONTRACT_CN.md
scripts/run_tw_modular_order_intent_replay.py
scripts/validate_tw_modular_order_intent_replay.py
scripts/validate_tw_modular_order_intent_replay_parity.py
```

结论：

```text
ReplayExecutionEngine 只消费 OrderIntentArtifact / PriceStore / ExecutionConfig / InitialPortfolioState
不再反向读取模型信号来重新决定买卖
next-day execution、费用、税费、净值、持仓完整性由 replay 层处理
```

该部分边界合理。

### 2.4 只读产品展示层

已有：

```text
READONLY_STRATEGY_SNAPSHOT_CONTRACT_CN.md
READONLY_REPLAY_WINDOW_PRODUCTIZATION_GUIDE_CN.md
backend/app/routes/readonly_replay_window.py
backend/app/routes/readonly_replay_window_index.py
backend/app/services/readonly_replay_window.py
backend/app/services/readonly_replay_window_index.py
frontend readonly replay window panel
```

结论：

```text
API 是 GET-only
ReplayWindowPolicy 由后端校验
API 只读取 D7 index 登记过的 audited artifact
前端不本地 replay
前端不触发 provider / accepted latest / monitor / broker / order
```

该部分可以作为只读基线，但前端体验仍需后续整理。

## 3. 仍需解耦或补合同的模块

### 3.1 DataSource / DataIngestion 合同

当前未来开发规范有原则，但没有正式数据抓取合同。

建议新增：

```text
DATA_SOURCE_CONTRACT_CN.md
DATA_INGESTION_ARTIFACT_CONTRACT_CN.md
```

必须冻结：

```text
source_name
provider
raw_path
normalized_path
asof_date
available_at
symbol_mapping_version
coverage_audit
schema_audit
no_provider_publish
no_accepted_latest_switch
```

原因：后续新增正交数据、财报、行业、另类数据、日更抓取时，必须先进入标准数据产物，不能让模型或策略直接读临时 raw 文件。

### 3.2 FeatureArtifact 合同

当前 `FeatureArtifact` 只在总规范中出现，没有正式 schema。

建议新增：

```text
FEATURE_ARTIFACT_CONTRACT_CN.md
scripts/validate_tw_feature_artifact.py
```

必须冻结：

```text
feature_date
instrument
feature_name
feature_value
source_data_artifact
lookback_window
signal_asof
available_at
pit_policy
forbidden_future_field_audit
```

原因：正交特征、风险特征、行业特征、多 horizon 特征都需要统一 PIT 和字段语义。

### 3.3 PriceStore 合同

回放层依赖 PriceStore，但 PriceStore 本身还没有正式合同。

建议新增：

```text
PRICE_STORE_CONTRACT_CN.md
scripts/validate_tw_price_store.py
```

必须冻结：

```text
price_date
instrument
open
close
adj_factor
tradable_flag
halt_flag
next_day_execution_availability
price_source
adjustment_policy
coverage_audit
```

原因：replay 收益、公平比较和 next-day execution 都依赖价格口径。PriceStore 不正式化，后续新增回放窗口或交易成本模型时仍可能出现隐式口径漂移。

### 3.4 Daily Orchestrator / Run Registry 合同

当前日更和 readonly release bundle 仍是相对分散的脚本/manifest 关系。

建议新增：

```text
DAILY_ORCHESTRATOR_CONTRACT_CN.md
RUN_REGISTRY_CONTRACT_CN.md
```

必须冻结每日链路：

```text
data refresh complete
feature build complete
model signal build complete
strategy decision build complete
readonly snapshot publish complete
replay window artifact registration complete, if applicable
latest pointer update policy
failure mode
rollback / keep previous latest
```

原因：后续要把默认策略或候选策略日更，必须清楚“谁生成、谁校验、谁更新 latest pointer、失败时是否沿用上一版”。

### 3.5 Analysis / Visualization 合同

当前前端能展示 replay summary，但分析展示尚未正式合同化。

建议新增：

```text
ANALYSIS_ARTIFACT_CONTRACT_CN.md
FRONTEND_READONLY_DISPLAY_CONTRACT_CN.md
```

必须冻结：

```text
summary metrics
daily nav series
actions table
fee/tax summary
coverage/integrity status
diagnostic_only flag
valid_strategy_evidence flag
allowed_frontend_fields
hidden_audit_fields
```

原因：前端应该展示“用户要用的信息”，而不是直接暴露工程字段。审计字段需要可追溯，但不应该主导用户视图。

## 4. 前端审查结论

### 4.1 安全边界

未发现 D8 新增前端存在真实交易越界。

新增 replay window 相关调用为：

```text
GET /api/tw-stock/readonly-replay-window-index
GET /api/tw-stock/readonly-replay-window
```

未发现：

```text
POST/PUT/PATCH/DELETE
provider publish / refresh
accepted latest switch
monitor config / scan / alerts write
broker / quick-trade / orders
target_position / target_weight
frontend local replay
```

### 4.2 是否被魔改

结论：没有被改成危险或不可接受状态，但还不是理想产品形态。

当前问题：

```text
readonly strategy snapshot 和 replay window 面板直接插在 tw-stock-monitor/index.vue 顶部
index.vue 已经很大，继续堆功能会降低维护性
页面出现 D4 / D6 / window index / checksum / replay_execution_engine / source manifest 等工程字段
这些字段对审计有用，但对普通用户不是第一视角
```

建议后续前端改为：

```text
主视图：模型、策略、窗口、净收益、回撤、交易次数、费用、审计状态
审计详情折叠区：source manifest、checksum、window index、schema version
组件拆分：ReadonlyStrategySnapshotPanel.vue、ReadonlyReplayWindowPanel.vue、ReplayMetricSummary.vue、ReplayAuditDetail.vue
```

### 4.3 用户第一性原则

当前基本满足“准确”和“安全”，但“简单、清晰、实用”还可以优化。

后续前端应遵守：

```text
默认先回答用户关心的问题：这个模型/策略在这个合法窗口表现如何
再展示风险：回撤、费用、换手、覆盖、跳过交易
最后提供可展开审计：manifest、checksum、validator
不得把工程审计字段放在主要视觉层级
不得使用真实交易语义，例如下单、目标仓位、自动交易
```

## 5. 后续开发文档需要补充的内容

建议补充 `TW_MODULAR_PIPELINE_FUTURE_DEVELOPMENT_GUIDE_CN.md`，新增以下章节或独立子文档：

```text
DataSource / DataIngestion Contract
FeatureArtifact Contract
PriceStore Contract
DailyOrchestrator / RunRegistry Contract
AnalysisArtifact / FrontendReadonlyDisplay Contract
DefaultCandidateSelection / ReleaseDecision Contract
```

其中 `DefaultCandidateSelection / ReleaseDecision` 不等于自动切默认策略。它只定义：

```text
如何比较候选模型/策略
需要哪些 OOS 证据
需要哪些风险指标
谁批准成为默认展示
如何回滚
如何保留旧默认策略
```

任何默认策略切换仍必须单独得到用户确认。

## 6. 建议下一步

不要继续修改 D8 release bundle 本身。建议另开一条小主线：

```text
Phase M0 Modular Contract Gap Closure
```

M0 只做文档和合同冻结，不改生产代码，不跑新模型，不生成新收益结论。

M0 输出：

```text
DATA_SOURCE_CONTRACT_CN.md
FEATURE_ARTIFACT_CONTRACT_CN.md
PRICE_STORE_CONTRACT_CN.md
DAILY_ORCHESTRATOR_CONTRACT_CN.md
ANALYSIS_FRONTEND_DISPLAY_CONTRACT_CN.md
更新 TW_MODULAR_PIPELINE_FUTURE_DEVELOPMENT_GUIDE_CN.md
给出每个合同对应 validator 的后续实现计划
```

M0 审查通过后，再进入：

```text
M1 Data / Feature / PriceStore validators
M2 Daily orchestrator readonly latest chain
M3 Frontend component extraction and user-first display cleanup
M4 New model / new strategy onboarding dry run
```

## 7. 最终判断

D8 可以收尾。

当前核心研究和只读回放产品化链路已经足够模块化，可以作为后续开发基线。但为了支持长期新增数据、模型、策略、日更和前端展示，必须补齐数据、特征、价格、日更编排、分析展示这些模块的正式合同与 validator。
