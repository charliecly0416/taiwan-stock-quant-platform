# 台股数据规范化与血缘治理主线

生成日期：2026-06-29

## 0. 结论先行

当前反复“卡在数据上”，不是单纯因为没有抓到某一天数据，而是因为项目同时存在多层数据和多种 latest 语义：

```text
provider raw/latest
normalized/latest
PriceStore latest
qlib accepted latest
readonly bridge latest
ModelSignalArtifact latest
ReadonlyStrategySnapshot latest
Agent DailyAgentPromptArtifact latest
research route temporary latest
```

这些层级原本是为了安全隔离：研究、回放、只读展示、正式 qlib provider、Agent prompt 不应该互相静默覆盖。但副作用是，每条新模型/新策略路线经常临时补一个 bridge、临时读一个路径、临时解释一个 latest，导致执行到中途才发现缺价格、缺 TWII、缺正交特征、缺 full rank、缺 mark-to-market，最后不断开 repair。

本主线的目标不是马上重抓所有数据，也不是只做静态 catalog，而是建立一套能继续连接模型层、策略层和全自动日更脚本的完整数据生产链路：

1. 所有数据层都有固定目录、固定 manifest、固定 validator。
2. 所有研究/生产路线开跑前，必须生成 Data Readiness Matrix。
3. 所有输入统一打包成 StrategyInputBundle 或 ReplayInputBundle，禁止路线直接拼散落路径。
4. 日更脚本负责更新 raw/normalized/catalog/readiness，并在 gate 通过后生成当天缺失的标准产物，例如 PriceStore、FeatureArtifact、qlib base score、LTR rerank score、ModelSignalArtifact、StrategyInputBundle。
5. 日更脚本默认仍不切 qlib accepted latest 或生产 latest；若要推进 formal qlib accepted latest、readonly latest、Agent prompt latest 或生产默认展示，必须有单独 gate、validator 和审查授权。
6. 任何“卡在 6/17”之类问题，必须能从 catalog 一眼看出到底是哪一层停在 6/17，哪一层已到 6/25 或 6/29，以及下一步应该补 raw、normalized、feature、score、signal 还是 latest pointer。

最终目标是：

```text
新数据拉取完成
-> raw/normalized/canonical stores 更新
-> DataCatalog/latest_status 更新
-> readiness matrix 判断模型依赖是否齐备
-> 缺失的 daily score / feature / signal 自动补生成
-> ModelSignalArtifact validator 通过
-> StrategyInputBundle / ReplayInputBundle 可用
-> readonly snapshot / Agent prompt / UI 可在授权 gate 下消费
```

## 1. 为什么会出现 6/17、6/25、6/29 不一致

以近期问题为例：

- formal qlib calendar / accepted signal 可能仍停在 `2026-06-17`；
- 后续 isolated bridge 可能已经补了 `2026-06-25` 的 price/TWII；
- daily auto job 可能已经为 `2026-06-29` 生成 job.json，但当天盘后数据、正交数据或 formal provider publish 并未全部完成；
- readonly strategy snapshot latest 可能还是更旧的策略快照；
- Agent prompt latest 可能又是另一套 latest。

这不是一定代表执行者“没补数据”，而是代表：

```text
raw data 可用
!= normalized 可用
!= PriceStore 可用
!= qlib provider accepted
!= ModelSignalArtifact 可用
!= strategy snapshot 可发布
```

之前很多修复分支只是在隔离目录补 bridge，并没有授权改 formal provider 或切 accepted latest。这是正确的安全边界，但如果没有全局 catalog，就会让人感觉数据乱。

## 2. 当前已有基础

项目已经有一批重要合同：

- `DataSource`：描述来源、asof、覆盖率、安全边界。
- `PriceStore`：标准价格层，服务特征、回放和展示。
- `FeatureArtifact`：PIT 安全的特征层。
- `ModelSignalArtifact`：模型输出到策略的唯一标准信号接口。
- `DailyOrchestrator`：只读日更编排。
- `RunRegistry`：记录输入、输出、validator、latest pointer 决策。

问题是这些合同目前更多是模块合同，还没有形成全项目统一的：

```text
DataCatalog
DataReadinessMatrix
CanonicalStore
StrategyInputBundle
ReplayInputBundle
RouteDataDependencyContract
```

所以后续要补的是治理层，而不是推翻现有模块。

## 3. 规范化目标

### 3.1 数据层级

后续统一按以下层级组织：

```text
RawSourceStore
  -> NormalizedStore
  -> CanonicalFeature/Price Stores
  -> ModelSignalStore
  -> StrategyInputBundle / ReplayInputBundle
  -> ReadonlySnapshot / AgentPrompt / UI
```

每一层都必须有：

```text
manifest.json
schema.json
coverage_audit.csv 或 coverage_audit.json
lineage.json
validator_report.json
latest pointer, if and only if this layer owns a latest pointer
```

### 3.2 latest 命名

禁止再用模糊的 `latest` 描述所有层。文档、manifest、API 和审查报告必须写清楚：

| 名称 | 语义 | 是否等于生产可用 |
| --- | --- | --- |
| `provider_raw_latest` | 数据商或爬虫原始数据最新日期 | 否 |
| `normalized_latest` | 标准化数据最新日期 | 否 |
| `price_store_latest` | 标准价格仓库最新可用日期 | 否 |
| `feature_store_latest` | 标准特征层最新可用日期 | 否 |
| `qlib_accepted_latest` | formal qlib provider 当前接受日期 | 不一定 |
| `model_signal_latest` | 某个模型信号 artifact 最新日期 | 不一定 |
| `readonly_bridge_latest` | 隔离只读桥接产物最新日期 | 否 |
| `readonly_snapshot_latest` | 前端只读策略快照最新日期 | 不等于 qlib latest |
| `agent_prompt_latest` | Agent prompt artifact 最新日期 | 不等于策略 latest |

任何报告只写“latest 是 6/17”都不合格，必须写是哪一层。

## 4. 推荐目录结构

新增或逐步收敛到以下目录。不要求一次性搬迁历史数据，但新增产物应优先遵循。

```text
data_tw/
  raw/
    finmind/{dataset}/date=YYYY-MM-DD/
    yahoo_adjusted_price/date=YYYY-MM-DD/
    twse/{dataset}/date=YYYY-MM-DD/
  normalized/
    prices/dataset=tw_equity_daily/date=YYYY-MM-DD/
    market_index/dataset=twii_daily/date=YYYY-MM-DD/
    institutional_flow/date=YYYY-MM-DD/
    margin_short/date=YYYY-MM-DD/
    corporate_actions/date=YYYY-MM-DD/
  canonical/
    price_store/{price_store_id}/{run_id}/
    market_feature_store/{feature_set_id}/{run_id}/
    orthogonal_feature_store/{feature_set_id}/{run_id}/
    qlib_provider_view/{provider_view_id}/{run_id}/
    model_inference_input/{model_id}/{run_id}/
  artifacts/
    signals/{model_id}/{run_id}/
    score_jobs/{model_id}/{run_id}/
    strategy_input_bundles/{bundle_id}/{run_id}/
    replay_input_bundles/{bundle_id}/{run_id}/
    order_intents/{strategy_id}/{run_id}/
    replays/{strategy_id}/{run_id}/
  catalog/
    data_catalog.json
    readiness_matrix/{asof}/{route_id}.json
    latest_status.json
    lineage_index.json
```

历史 `data_tw/experiments/**` 可以保留，但不能再作为新路线默认输入源。新路线应从 `catalog` 找到标准输入，或明确声明自己是 isolated research bridge。

## 5. DataCatalog 合同

### 5.1 目的

`DataCatalog` 是全项目数据账本。它不存大数据本体，只记录每个数据集、每个 asof、每个 artifact 的位置、血缘、覆盖率和状态。

### 5.2 最小字段

```text
catalog_version
generated_at
dataset_id
layer
asof
date_min
date_max
symbol_count
row_count
path
manifest_path
schema_path
coverage_audit_path
lineage_path
validator_report_path
status
status_reason
source_provider
source_run_id
checksum
pit_policy
available_at_policy
forbidden_action_flags
```

### 5.3 status 枚举

```text
READY
PARTIAL_READY
MISSING
STALE
BLOCKED_PROVIDER
BLOCKED_SCHEMA
BLOCKED_PIT
BLOCKED_COVERAGE
BLOCKED_VALIDATOR
RESEARCH_ONLY
```

`READY` 只表示该层可被消费，不代表可以切生产 latest。

## 6. DataReadinessMatrix 合同

每条模型/策略路线开跑前，执行者必须生成：

```text
data_tw/catalog/readiness_matrix/{asof}/{route_id}.json
data_tw/catalog/readiness_matrix/{asof}/{route_id}.csv
```

### 6.1 行粒度

每一行表示一个 route dependency：

```text
route_id
asof
dependency_name
required_layer
required_dataset_id
required_date_min
required_date_max
required_symbols_scope
required_fields
required_pit_policy
source_artifact
catalog_status
coverage_status
schema_status
pit_status
latest_status
can_continue
blocker_reason
repair_recommendation
```

### 6.2 常见 dependency

策略和模型常见依赖包括：

- `price_store_daily_ohlcv`
- `twii_market_index`
- `market_calendar`
- `next_day_execution_price`
- `qlib_full_rank_signal`
- `ltr_top50_signal`
- `orthogonal_feature_package`
- `institutional_flow`
- `margin_short`
- `portfolio_state`
- `order_intent_schema`
- `replay_cost_config`
- `mark_to_market_price`

### 6.3 Gate 规则

任一 `required=true` dependency 出现：

```text
can_continue=false
```

则路线不得进入训练、回放、shadow、readonly exposure 或 production readiness，只能进入数据 repair 或降级决策。

降级决策必须明确写：

```text
dependency_name
why_optional
impact_on_claim
new_route_scope
reviewer_approval
```

## 7. StrategyInputBundle 合同

策略不应该直接读散落的 signal、price、feature、portfolio、calendar 路径。应消费一个标准输入包：

```text
data_tw/artifacts/strategy_input_bundles/{strategy_id}/{run_id}/
  manifest.json
  signals.csv
  current_holdings.csv
  price_context.csv
  market_context.csv
  calendar.csv
  dependency_readiness.json
  lineage.json
  validator_report.json
```

### 7.1 必需语义

`manifest.json` 必须声明：

```text
artifact_type=strategy_input_bundle
strategy_id
asof
target_trade_date
model_signal_artifact
price_store_artifact
market_feature_artifact
portfolio_state_artifact
dependency_readiness_matrix
readonly_only
no_order
no_target_position
no_target_weight, unless explicitly authorized by a separate production contract
```

策略路线只能根据 bundle 做规则、回放、shadow 或解释，不得在策略内部再临时去找另一个 price/TWII/LTR 文件。

## 8. ReplayInputBundle 合同

回放统一消费：

```text
data_tw/artifacts/replay_input_bundles/{replay_id}/{run_id}/
  manifest.json
  order_intents.csv
  price_store.csv 或 price_store_ref.json
  cost_config.json
  initial_portfolio_state.json
  market_calendar.csv
  execution_availability_audit.csv
  dependency_readiness.json
  lineage.json
  validator_report.json
```

必须明确：

```text
execution_price_policy
fee_tax_policy
mark_to_market_policy
corporate_action_policy
halt_suspension_policy
missing_price_policy
```

这样后续不会再出现“策略看起来有收益，但 mark-to-market / price coverage 不足，不能纳入生产”的模糊情况。

## 9. ModelInferenceInput 与 ScoreJob 合同

数据治理必须能连接模型层。否则每天 raw data 拉完后，仍会出现“价格已更新但 score 没有生成”的断点。

### 9.1 ModelInferenceInput

`ModelInferenceInput` 是模型推理前的标准输入包：

```text
data_tw/canonical/model_inference_input/{model_id}/{run_id}/
  manifest.json
  inference_frame.csv 或 inference_frame.parquet
  schema.json
  source_readiness.json
  feature_lineage.json
  pit_audit.csv
  coverage_audit.csv
  validator_report.json
```

必需字段：

```text
artifact_type=model_inference_input
model_id
model_family
asof
target_signal_date
universe_scope
source_price_store
source_feature_store
source_qlib_provider_view
source_orthogonal_feature_store
model_artifact_path
feature_schema_version
available_at_policy
pit_policy
readonly_only
no_training_run=true
no_hyperparameter_tuning=true
```

要求：

- 只允许推理，不允许训练或调参；
- 输入特征必须通过 PIT/available_at 审计；
- 不能把 future_return、label、realized_pnl、action、holding、order 字段带入；
- 对 qlib 模型，必须说明 provider view、calendar、instrument universe、feature dump 状态；
- 对 LTR 模型，必须说明底座 qlib top50、正交特征来源、LTR 只在 top50 内 rerank。

### 9.2 ScoreJob

`ScoreJob` 是 daily auto 生成模型分数的运行账本：

```text
data_tw/artifacts/score_jobs/{model_id}/{run_id}/
  manifest.json
  raw_scores.csv
  rank_audit.csv
  model_load_audit.json
  input_readiness.json
  output_model_signal_manifest.json
  validator_report.json
```

必需字段：

```text
artifact_type=score_job
model_id
model_family
asof
source_model_inference_input
source_model_artifact
raw_score_path
model_signal_artifact
score_status
score_status_reason
fallback_policy
fallback_used
previous_signal_artifact
```

`score_status` 枚举：

```text
READY
SKIPPED_ALREADY_EXISTS
BLOCKED_INPUT_NOT_READY
BLOCKED_MODEL_ARTIFACT_MISSING
BLOCKED_PROVIDER_VIEW_STALE
BLOCKED_FEATURE_MISSING
BLOCKED_VALIDATOR
FALLBACK_PREVIOUS_SIGNAL
FALLBACK_QLIB_ONLY
```

### 9.3 每日缺失 score 生成原则

当 raw/normalized/canonical 数据已经更新到目标 asof，但对应模型 score 缺失时，daily auto 可以在显式 gate 下自动补生成 score。补生成顺序：

```text
PriceStore / Calendar / TWII readiness
-> qlib provider view candidate
-> qlib Model A inference input
-> qlib Model A score job
-> Model A ModelSignalArtifact
-> orthogonal feature readiness
-> LTR Model B inference input
-> LTR Model B score job
-> Model B ModelSignalArtifact
-> StrategyInputBundle
```

这一步是“生成研究/只读标准产物”，不是“切生产默认模型”。

### 9.4 fallback 原则

如果某层缺失，必须按合同降级，而不是静默继续：

| 缺失层 | 默认处理 |
| --- | --- |
| raw/normalized price 缺失 | 阻断 score 生成 |
| PriceStore 缺失 | 阻断 score 和 replay |
| qlib provider view 缺失 | 阻断 qlib score，或进入 qlib provider repair |
| qlib Model A score 缺失 | 阻断 LTR rerank |
| orthogonal features 缺失 | LTR 阻断；若合同允许，可 fallback qlib-only |
| LTR score 缺失 | 保留上一日 LTR 或 fallback qlib-only，必须标记 |
| ModelSignalArtifact validator 失败 | 不生成 StrategyInputBundle |

任何 fallback 都必须写入 `ScoreJob.manifest.json`、`latest_status.json` 和 readiness matrix，不能伪装为 full qlib+LTR ready。

## 10. 日更脚本职责调整

`scripts/run_daily_tw_stock_auto_update.py` 后续应被定位为：

```text
raw/normalized/canonical/catalog/readiness/model-signal updater
```

而不是“什么都更新、什么都发布”的脚本。它可以在明确 gate 下生成缺失的标准只读产物，但不得默认发布生产 latest。

默认允许：

- 更新 raw archive；
- 更新 normalized store；
- 更新 canonical PriceStore / MarketFeatureStore；
- 更新 qlib provider candidate/view；
- 更新 DataCatalog；
- 更新 latest_status；
- 生成 daily_source_inventory；
- 生成 daily_full_capture_accounting；
- 生成 readiness matrix；
- 生成 ModelInferenceInput；
- 生成 ScoreJob；
- 生成 ModelSignalArtifact；
- 生成 StrategyInputBundle / ReplayInputBundle；
- 记录 provider quota、holiday、pending、cooldown。

默认禁止：

- provider publish；
- qlib accepted latest switch；
- production/default model switch；
- production/default strategy switch；
- broker/order/quick-trade；
- monitor writes；
- target_position / target_weight。

如果未来需要 formal qlib refresh，应另开独立授权路线，且必须引用 DataCatalog 的 raw/normalized readiness 作为输入。

### 10.1 建议 daily auto 模块顺序

后续全自动脚本应显式拆成以下模块，并为每个模块写 status：

```text
ResolveAsof
-> MarketCalendar/HolidayGate
-> RawSourceIngestion
-> NormalizedStoreBuild
-> DataCatalogUpdate
-> PriceStoreBuild
-> MarketFeatureStoreBuild
-> QlibProviderViewCandidateBuild
-> ModelAInferenceInputBuild
-> ModelAScoreJob
-> ModelAModelSignalArtifactBuild
-> OrthogonalFeatureStoreBuild
-> ModelBInferenceInputBuild
-> ModelBScoreJob
-> ModelBModelSignalArtifactBuild
-> StrategyInputBundleBuild
-> ReplayInputBundleBuild
-> OptionalReadonlySnapshotBuild
-> OptionalAgentPromptBuild
-> RunRegistry
-> latest_status / dashboard
```

任何模块失败，不得让下游模块静默使用旧数据冒充新 asof。允许的行为只有：

```text
stop
fallback with explicit manifest
keep previous latest
mark pending_asof
```

### 10.2 daily auto gate 分层

必须拆成四类 gate：

| Gate | 允许动作 | 默认 |
| --- | --- | --- |
| `raw_normalized_gate` | 抓 raw、建 normalized、建 catalog | 开 |
| `canonical_feature_gate` | 建 PriceStore、TWII、feature、qlib provider candidate | 可开 |
| `model_signal_gate` | 只读推理、补 score、建 ModelSignalArtifact | 可开，但需 validator |
| `publish_latest_gate` | 更新 readonly/latest、Agent prompt latest、formal accepted latest | 默认关，单独授权 |

审查者必须确认执行者没有把 `model_signal_gate` 的通过说成 `publish_latest_gate` 的通过。

## 11. 对正交数据的处理

正交数据包括但不限于：

```text
institutional_flow
margin_short
monthly_revenue
valuation
corporate_actions
```

这些数据不一定每天同时间可得，也可能受 provider quota 或权限影响。因此 catalog 必须支持：

```text
available
not_published_yet
provider_quota_blocked
provider_permission_blocked
holiday_no_data
not_required_for_route
```

对于 qlib+LTR production chain，必须区分：

- baseline policy 是否真的需要某项正交数据；
- LTR daily rerank 是否需要该项正交数据；
- 当前日更是否能稳定拉到该项正交数据；
- 如果拉不到，是否允许 fallback 到 qlib-only 或保留上一日 LTR。

不得因为 raw daily price 已更新，就宣称 qlib+LTR 正交链路完整。

## 12. 对 qlib provider 的处理

formal qlib provider 是模型推理/历史兼容的重要层，但不应该和 raw/normalized 混在一起。

新增一个 `qlib_provider_view` 层，用来记录：

```text
source_normalized_store
calendar_date_max
instrument_count
feature_dump_status
provider_path
accepted_latest_candidate
accepted_latest_committed
validator_status
```

默认日更只生成 candidate/audit，不自动 commit accepted latest。commit 必须单独授权。

## 13. 每日标准产物清单

后续执行者必须把“每天补数据”理解为补齐整条标准产物链，而不是只补模型 score。审查者应按下表逐项检查。

### 13.1 每日必须生成或检查的基础层

| 层级 | 每日产物 | 是否必须 | 缺失影响 |
| --- | --- | --- | --- |
| RawSourceStore | FinMind/Yahoo/TWSE 等 raw archive | 必须检查，交易日应尽量生成 | raw 缺失会阻断 normalized/canonical |
| NormalizedStore | 标准化价格、指数、法人、融资融券、公司行动等 | 必须检查，能生成则生成 | normalized 缺失会阻断 PriceStore/FeatureStore |
| MarketCalendar | 交易日历、下一交易日、holiday evidence | 必须 | 缺失会阻断 score、策略、回放 |
| PriceStore | 标准 OHLCV、复权口径、tradable/halt、next-day execution availability | 必须 | 缺失会阻断模型推理、策略、回放、mark-to-market |
| MarketFeatureStore | TWII、大盘趋势、市场 regime 基础特征 | 必须 | 缺失会阻断风险控制、规则研究、Agent/前端解释 |
| DataCatalog | data_catalog、latest_status、lineage_index | 必须 | 缺失会导致无法判断哪层停滞 |
| DataReadinessMatrix | route/asof dependency gate | 必须 | 缺失时不得进入模型/策略/回放 |

### 13.2 每日必须按可用性生成的模型层

| 层级 | 每日产物 | 生成条件 | 缺失影响 |
| --- | --- | --- | --- |
| QlibProviderView | qlib provider candidate/view、calendar/instrument/feature dump audit | PriceStore/calendar ready | 缺失会阻断 qlib Model A score |
| ModelAInferenceInput | qlib Model A 推理输入包 | QlibProviderView ready | 缺失会阻断 Model A score |
| ModelA ScoreJob | qlib base raw score/rank audit | ModelAInferenceInput ready | 缺失会阻断 ModelSignalArtifact 和 LTR |
| ModelA ModelSignalArtifact | qlib 标准信号 | ModelA ScoreJob validator pass | 缺失会阻断 LTR、策略输入包 |
| OrthogonalFeatureStore | institutional/margin/revenue/valuation 等正交特征包 | raw/normalized 正交数据 ready | 缺失会阻断 LTR，除非合同允许 qlib-only fallback |
| ModelBInferenceInput | LTR 推理输入包 | Model A top50 + orthogonal features ready | 缺失会阻断 LTR score |
| ModelB ScoreJob | LTR rerank score/rank audit | ModelBInferenceInput ready | 缺失会阻断 qlib+LTR full ready |
| ModelB ModelSignalArtifact | qlib+LTR 标准信号 | ModelB ScoreJob validator pass | 缺失时只能 qlib-only 或保留上一版，必须显式标记 |

说明：

- `score` 不是唯一要补的东西；score 只是模型层的一个输出。
- 如果只补 `raw_scores.csv`，但没有 `ModelInferenceInput`、`ScoreJob`、`ModelSignalArtifact` 和 lineage，不算合格。
- 如果 LTR 所需正交数据缺失，不得用 qlib score 冒充 LTR score。
- 如果 fallback 到 qlib-only 或 previous signal，必须写入 `ScoreJob`、`latest_status`、readiness matrix、StrategyInputBundle manifest。

### 13.3 每日必须按用途生成的策略/回放层

| 层级 | 每日产物 | 生成条件 | 缺失影响 |
| --- | --- | --- | --- |
| StrategyInputBundle | signals、current holdings、price context、market context、calendar、readiness | ModelSignalArtifact ready | 缺失时策略不得直接读散落路径 |
| OrderIntentArtifact | 只读策略意图 | StrategyInputBundle ready + strategy rule gate | 缺失时不得生成 replay/shadow 决策 |
| ReplayInputBundle | order intents、PriceStore、cost config、initial state、execution availability | OrderIntentArtifact + PriceStore ready | 缺失时不得做收益/回放结论 |
| ReplayResultArtifact | NAV、daily return、turnover、fee/tax、mark-to-market | ReplayInputBundle ready | 缺失时不得宣称策略收益 |
| ShadowReadiness | readonly shadow / exposure readiness | Replay 或 StrategyInputBundle ready | 缺失时不得进入 shadow 展示或生产候选 |

### 13.4 可选 publish 层

以下产物可以每日生成 dry-run/source context，但 latest pointer 默认不得自动更新：

| 层级 | 产物 | 默认动作 |
| --- | --- | --- |
| ReadonlyStrategySnapshot | 前端 readonly snapshot | 可生成；latest publish 需 gate |
| Agent DailyPrompt context | Agent prompt source context | 可生成；latest publish 需 gate |
| UI ranking payload | 前端候选/排名展示 payload | 可生成；接入默认展示需 gate |
| formal qlib accepted latest | qlib accepted provider latest | 默认禁止；需单独授权 |
| production default model/strategy | 生产默认模型/策略 | 默认禁止；需单独授权 |

### 13.5 审查者每日清单

审查者必须在 DNG6 以后检查：

```text
raw_ok
normalized_ok
calendar_ok
price_store_ok
market_feature_ok
data_catalog_ok
readiness_matrix_ok
qlib_provider_view_ok
model_a_inference_input_ok
model_a_score_job_ok
model_a_signal_ok
orthogonal_feature_store_status
model_b_inference_input_status
model_b_score_job_status
model_b_signal_status
strategy_input_bundle_ok
replay_input_bundle_status
readonly_snapshot_publish_gate_status
agent_prompt_publish_gate_status
fallback_used
fallback_reason
latest_pointer_write_status
```

任何一项不是 `ok/ready/skipped_with_reason`，都必须写明 blocker 或 fallback。不得只写“score 已补齐”作为整条日更链路通过证据。

## 14. 产品链路完成定义

这条主线必须做到能支撑完整链路，而不是只支撑研究诊断。最终完成时，至少应存在以下可审查路径：

```text
data_tw/raw/...
data_tw/normalized/...
data_tw/canonical/price_store/...
data_tw/canonical/market_feature_store/...
data_tw/canonical/orthogonal_feature_store/...
data_tw/canonical/qlib_provider_view/...
data_tw/canonical/model_inference_input/...
data_tw/artifacts/score_jobs/...
data_tw/artifacts/signals/...
data_tw/artifacts/strategy_input_bundles/...
data_tw/artifacts/replay_input_bundles/...
data_tw/catalog/data_catalog.json
data_tw/catalog/latest_status.json
data_tw/catalog/daily_readiness_dashboard.json
```

并能从任一当天候选股反查：

```text
最终 buy_score
-> ModelSignalArtifact
-> ScoreJob
-> ModelInferenceInput
-> feature store / price store / qlib provider view
-> normalized source
-> raw provider source
-> daily auto job_id
```

如果做不到这条血缘反查，不能宣布数据规范化主线完成。

## 15. 执行路线

### DNG0：现状盘点与数据地图

目标：不改数据，只盘点当前所有关键路径。

执行者产物：

```text
docs/tw_data_governance/DNG0_DATA_INVENTORY_EXECUTION_REPORT_CN.md
data_tw/catalog/dng0_current_data_inventory.csv
data_tw/catalog/dng0_latest_pointer_inventory.csv
data_tw/catalog/dng0_route_dependency_sample.csv
```

必须覆盖：

- `data_tw/artifacts/**`
- `data_tw/experiments/**` 中仍被新路线引用的目录；
- `qlib_pipeline/data_tw/**` 中 formal qlib provider、calendar、latest signal；
- `data_tw/ops/daily_auto_update/**`；
- product artifact registry；
- current strategy context / readonly snapshot / Agent prompt latest pointer。

审查者判断：

- 是否把 latest 层级区分清楚；
- 是否标出哪些目录是 canonical，哪些是 experiment，哪些是 temporary bridge；
- 是否识别当前 6/17/6/25/6/29 类不一致来自哪一层。

### DNG1：DataCatalog schema 与只读 scanner

目标：实现只读 scanner，把现有 manifest/latest/job/audit 聚合成 catalog。

执行者产物：

```text
scripts/build_tw_data_catalog.py
scripts/validate_tw_data_catalog.py
data_tw/catalog/data_catalog.json
data_tw/catalog/latest_status.json
docs/tw_data_governance/DNG1_DATA_CATALOG_EXECUTION_REPORT_CN.md
```

要求：

- scanner 只读，不触发抓数；
- 支持 JSON 输出和 CSV 摘要；
- validator 能检查 schema、status、路径存在、checksum、forbidden flags；
- 对缺失 manifest 的历史目录标记 `LEGACY_UNCATALOGED`，不得伪造 READY。

### DNG2：PriceStore / TWII / Calendar 规范化

目标：先解决最常阻塞回放和 shadow 的价格、指数、日历问题。

执行者产物：

```text
data_tw/canonical/price_store/{price_store_id}/{run_id}/
data_tw/canonical/market_feature_store/twii_daily/{run_id}/
data_tw/catalog/readiness_matrix/{asof}/price_market_calendar.json
docs/tw_data_governance/DNG2_PRICE_MARKET_CALENDAR_EXECUTION_REPORT_CN.md
```

必须检查：

- OHLCV 覆盖；
- adjusted / unadjusted 口径；
- next-day execution availability；
- mark-to-market close coverage；
- TWII 日期覆盖；
- trading calendar 是否包含最近交易日和下一交易日；
- holiday/no data 是否有证据。

### DNG3：正交数据 raw/normalized/store 合同

目标：把 institutional、margin、revenue、valuation 等正交数据从“路线临时补”变成标准 store。

执行者产物：

```text
data_tw/normalized/institutional_flow/...
data_tw/normalized/margin_short/...
data_tw/canonical/orthogonal_feature_store/{feature_set_id}/{run_id}/
docs/tw_data_governance/DNG3_ORTHOGONAL_DATA_EXECUTION_REPORT_CN.md
```

必须明确：

- provider；
- 字段口径；
- symbol mapping；
- available_at；
- quota/permission 状态；
- PIT policy；
- 缺失时路线如何降级。

### DNG4：StrategyInputBundle / ReplayInputBundle builder

目标：把策略/回放输入统一打包，替代各路线临时拼路径。

执行者产物：

```text
scripts/build_tw_strategy_input_bundle.py
scripts/build_tw_replay_input_bundle.py
scripts/validate_tw_strategy_input_bundle.py
scripts/validate_tw_replay_input_bundle.py
docs/tw_data_governance/DNG4_INPUT_BUNDLE_EXECUTION_REPORT_CN.md
```

必须支持至少两条样例路线：

- 当前 qlib+LTR baseline readonly；
- 当前规则研究或风险控制 policy 的 readonly replay。

### DNG5：RouteDataDependencyContract 接入

目标：所有新模型/新策略主线文档必须先写依赖合同。

执行者产物：

```text
docs/tw_data_governance/ROUTE_DATA_DEPENDENCY_CONTRACT_TEMPLATE_CN.md
scripts/validate_tw_route_data_dependency.py
docs/tw_data_governance/DNG5_ROUTE_DEPENDENCY_EXECUTION_REPORT_CN.md
```

任何后续路线必须声明：

```text
required_data_layers
required_date_range
required_universe
required_fields
required_latest_concepts
optional_dependencies
allowed_fallbacks
forbidden_private_paths
```

审查者在授权执行前必须先看 dependency gate。

### DNG6：日更 catalog 集成与 dashboard

目标：把 DataCatalog 和 readiness matrix 串入 daily auto，让每天自动告诉我们“哪些数据层已更新，哪些层没更新，为什么”。

执行者产物：

```text
data_tw/catalog/latest_status.json
data_tw/catalog/daily_readiness_dashboard.json
docs/tw_data_governance/DNG6_DAILY_AUTO_CATALOG_INTEGRATION_EXECUTION_REPORT_CN.md
```

dashboard 至少展示：

```text
asof
provider_raw_latest_by_dataset
normalized_latest_by_dataset
price_store_latest
feature_store_latest
qlib_accepted_latest
model_signal_latest_by_model
readonly_snapshot_latest
agent_prompt_latest
pending_asof
provider_quota_status
holiday_status
next_retry_hint
```

### DNG7：ModelInferenceInput / ScoreJob 合同与 qlib Model A 补分

目标：把 daily auto 连接到模型层，先支持 qlib Model A 的只读推理和缺失 score 补生成。

执行者产物：

```text
scripts/build_tw_model_inference_input.py
scripts/run_tw_model_score_job.py
scripts/validate_tw_model_inference_input.py
scripts/validate_tw_score_job.py
data_tw/canonical/model_inference_input/{model_a_id}/{run_id}/
data_tw/artifacts/score_jobs/{model_a_id}/{run_id}/
data_tw/artifacts/signals/{model_a_id}/{run_id}/
docs/tw_data_governance/DNG7_MODELA_SCORE_PIPELINE_EXECUTION_REPORT_CN.md
```

必须做到：

- 对某个已具备 PriceStore / qlib provider view 的 asof，可生成 qlib Model A score；
- 输出标准 ModelSignalArtifact；
- `candidate_rank`、`buy_score`、`raw_score`、`score_rank`、`full_qlib_rank` 语义符合 `MODEL_SIGNAL_CONTRACT_CN.md`；
- 不训练模型、不调参、不切 accepted latest；
- 如果 model artifact、provider view、calendar、feature dump 缺失，必须明确 blocker。

审查者重点：

- 是否真的从标准 input package 推理，而不是读临时实验 CSV 冒充 score；
- 是否保留 model artifact lineage；
- 是否 raw score 到 rank 的 tie-breaker 稳定；
- 是否没有 provider/latest/production 写入。

### DNG8：Orthogonal FeatureStore / LTR Model B 补分

目标：在 qlib Model A top50 可用后，支持正交特征和 LTR Model B rerank 的只读 daily 补生成。

执行者产物：

```text
data_tw/canonical/orthogonal_feature_store/{feature_set_id}/{run_id}/
data_tw/canonical/model_inference_input/{model_b_id}/{run_id}/
data_tw/artifacts/score_jobs/{model_b_id}/{run_id}/
data_tw/artifacts/signals/{model_b_id}/{run_id}/
docs/tw_data_governance/DNG8_MODELB_LTR_SCORE_PIPELINE_EXECUTION_REPORT_CN.md
```

必须做到：

- LTR 只消费 Model A qlib top50；
- `candidate_rank` 与 `full_qlib_rank` 来自 Model A，不被 LTR 改写；
- `buy_score` 和 `score_rank` 来自 LTR rerank；
- institutional/margin 等正交数据缺失时，不能伪装 LTR ready；
- 若合同允许 fallback qlib-only，必须在 ScoreJob 和 latest_status 显式标记。

审查者重点：

- 是否把 qlib full rank 与 LTR rank 混淆；
- 是否绕过 qlib top50；
- 是否正确处理正交数据 provider quota / permission / not_published；
- 是否生成完整 ModelSignalArtifact validator evidence。

### DNG9：Daily auto model-signal gate 集成

目标：把 DNG7/DNG8 接入 `scripts/run_daily_tw_stock_auto_update.py`，让新数据拉完后，在 gate 允许时自动补当天缺失的 score 和 ModelSignalArtifact。

执行者产物：

```text
scripts/run_daily_tw_stock_auto_update.py
scripts/validate_tw_daily_orchestrator_m3.py 或新增 validator
data_tw/ops/daily_auto_update/{job_id}/model_signal_gate_summary.json
data_tw/catalog/latest_status.json
docs/tw_data_governance/DNG9_DAILY_AUTO_MODEL_SIGNAL_GATE_EXECUTION_REPORT_CN.md
```

要求：

- 新增 `TW_DAILY_AUTO_ENABLE_MODEL_SIGNAL_GATE` 或等价显式 gate；
- 默认不开生产 publish；
- job.json 必须记录每个模型的 score status；
- 如果 score 已存在且 validator 通过，应标记 `SKIPPED_ALREADY_EXISTS`；
- 如果数据已更新但 score 缺失，应尝试生成；
- 如果生成失败，应设置 pending/blocker，不得更新 downstream latest；
- DNG9 必须保留 `publish_latest_gate=false` 默认。

### DNG10：StrategyInputBundle / Readonly Snapshot / Agent Prompt 衔接

目标：当 ModelSignalArtifact ready 后，自动生成策略输入包；在单独 readonly gate 下生成 readonly snapshot / Agent prompt source context。

执行者产物：

```text
data_tw/artifacts/strategy_input_bundles/{strategy_id}/{run_id}/
data_tw/artifacts/replay_input_bundles/{replay_id}/{run_id}/
data_tw/artifacts/publish/readonly_strategy_snapshot/{run_id}/
data_tw/artifacts/agent_daily_prompt/{run_id}/ 或 source context dry-run
docs/tw_data_governance/DNG10_STRATEGY_AND_READONLY_CONTEXT_EXECUTION_REPORT_CN.md
```

要求：

- 策略只消费 StrategyInputBundle；
- replay 只消费 ReplayInputBundle；
- readonly snapshot latest pointer 默认不更新，除非明确 gate；
- Agent prompt latest 默认不更新，除非明确 gate；
- 如果 Model B 缺失但 qlib-only fallback 被允许，前端/Agent 必须显示 fallback 状态。

### DNG11：连续 shadow 观察与缺口烧毁

目标：用真实 daily auto 连续观察至少 5 个交易日，确认链路不再反复卡在数据缺口。

执行者产物：

```text
data_tw/catalog/daily_readiness_dashboard.json
data_tw/ops/daily_auto_update/{job_id}/job.json
data_tw/ops/daily_auto_update/{job_id}/model_signal_gate_summary.json
docs/tw_data_governance/DNG11_MULTI_DAY_SHADOW_OBSERVATION_EXECUTION_REPORT_CN.md
```

验收要求：

- 至少 5 个交易日或审查者认可的等价 backfill/shadow 样本；
- 每天都能解释 raw、normalized、PriceStore、feature、score、signal、bundle 的状态；
- 如果 provider 因 quota/holiday/blocker 失败，dashboard 能正确说明，不需要人工翻散落 log；
- 不得出现“数据其实有，但不知道哪层没更新”的情况。

### DNG12：生产就绪 Go/No-Go closure

目标：判断数据规范化链路是否可以作为后续模型/策略研发和 readonly 产品链路的标准入口。

执行者产物：

```text
docs/tw_data_governance/DNG12_DATA_GOVERNANCE_GO_NO_GO_CLOSURE_EXECUTION_REPORT_CN.md
docs/tw_data_governance/DNG12_DATA_GOVERNANCE_GO_NO_GO_CLOSURE_REVIEW_CN.md
```

Go 条件：

- DataCatalog / latest_status / readiness matrix 稳定；
- PriceStore / TWII / calendar 不再靠临时 bridge；
- qlib Model A score 可在 gate 下自动补；
- LTR Model B score 可在正交数据 ready 时自动补；
- fallback 状态可审计；
- StrategyInputBundle / ReplayInputBundle 可作为新路线默认输入；
- daily auto 可一眼解释每层最新状态；
- 无 provider publish、accepted latest、production default、broker/order 越权。

No-Go 条件：

- 仍需要每条路线临时补 price/TWII/score；
- score 生成不能追溯到 model artifact 和 input feature；
- qlib/LTR rank 语义混乱；
- latest_status 不能解释停滞层；
- daily auto 失败后会静默使用旧数据冒充新 asof。

### DNG13：每日全自动闭环生产化接入

目标：把 DNG0-DNG12 形成的设计闭环接入真实每日自动链路。后续每天盘后抓到数据后，系统必须自动尝试推进：

```text
raw / normalized
-> canonical PriceStore / MarketFeatureStore / OrthogonalFeatureStore
-> qlib provider view candidate
-> ModelInferenceInput
-> ScoreJob
-> ModelSignalArtifact
-> StrategyInputBundle / ReplayInputBundle
-> readonly / Agent / UI source context
-> latest_status / daily dashboard / skipped_asof_ledger
```

DNG13 的核心不是继续做一次性研究补丁，而是让每日自动流程进入“抓数后自动补齐标准产物，失败也能解释并重试”的状态。

执行者产物：

```text
docs/tw_data_governance/DNG13_DAILY_AUTO_PRODUCTIONIZATION_CONTRACT_EXECUTION_REPORT_CN.md
docs/tw_data_governance/DNG13_DAILY_AUTO_PRODUCTIONIZATION_CONTRACT_REVIEW_CN.md
data_tw/ops/daily_auto_update/{job_id}/daily_chain_status.json
data_tw/ops/daily_auto_update/{job_id}/skipped_asof_ledger.json
data_tw/catalog/daily_readiness_dashboard.json
data_tw/catalog/latest_status.json
```

必须完成：

1. `scripts/run_daily_tw_stock_auto_update.py` 的每日流程必须在抓数后进入 DNG 标准链路，而不是只停在 raw job。
2. 每个 target asof 都必须生成 `daily_chain_status.json`，逐层记录 `ready / blocked / skipped / fallback / pending`。
3. 对 `2026-06-26` 这类日期，必须能明确说明：

```text
FinMind raw ready
formal qlib calendar not advanced
qlib provider view not ready
Model A score not generated
blocked_at=qlib_provider_view_or_formal_calendar
next_action=formal provider refresh / canonical qlib provider view repair
```

4. 必须新增或等价实现 `skipped_asof_ledger.json`，记录所有未生成 score 的交易日或候选日期：

```text
asof
is_trading_day
raw_status
normalized_status
canonical_price_status
qlib_provider_view_status
model_a_score_status
model_b_ltr_status
strategy_bundle_status
readonly_context_status
skip_reason
retry_policy
next_required_action
```

5. `pending_asof` 不应只表示 raw 抓数失败，也应支持 canonical / provider view / model score / readonly context 等层级 blocker。下一次自动运行必须优先重试 pending asof，再处理新的交易日。
6. 保留原本“数据 -> 模型 -> 策略 -> 前端展示”的自动链路，但要改成通过标准 artifact 和 validator 串接，禁止继续让前端或策略直接读散落 experiment 路径。
7. `model_signal_gate` 通过后只能表示只读 score / signal artifact ready；不得自动代表 publish latest 或生产默认展示已切换。
8. `publish_latest_gate` 仍默认关闭。readonly snapshot latest、Agent prompt latest、formal qlib accepted latest、production default model/strategy 的更新必须单独 gate 和审查。

每日自动链路推荐状态机：

```text
NO_TRADE_DAY
WAIT_DATA_WINDOW
RAW_READY
NORMALIZED_READY
CANONICAL_READY
QLIB_PROVIDER_VIEW_READY
MODELA_SIGNAL_READY
MODELB_SIGNAL_READY
STRATEGY_CONTEXT_READY
READONLY_CONTEXT_READY
PUBLISH_READY_BUT_NOT_PUBLISHED
BLOCKED_WITH_RETRY
BLOCKED_NEEDS_REPAIR
```

验收要求：

- 交易日盘后自动运行后，不需要人工猜测“为什么只到某天”。
- 对每个日期，dashboard 能显示哪一层成功、哪一层失败、是否会自动重试。
- 至少覆盖一个 raw 已到但 qlib score 未生成的案例，例如 `2026-06-26`，并给出机器可读 blocker。
- 保持原有前端 readonly 展示链路兼容：旧 latest pointer 未授权不得被改写，但新的 source context / candidate payload 可以在 gate 下生成。
- 不触发 broker/order/quick-trade，不生成 target position/target weight。

审查者重点：

- daily auto 是否真的在 raw 抓取后进入 canonical/model/strategy/frontend source context 流程；
- 是否存在“抓到 raw 后没有 score，但 dashboard 不解释”的缺口；
- 是否把 6/26 这类交易日正确分类为 lineage gap，而不是误判为周末或无数据；
- 是否保留原有 production/latest 安全边界；
- 是否没有用旧 signal 冒充新 asof signal。

### DNG14：多日自动观察与全局聚合

目标：消费 DNG13 产生的 job-local `daily_chain_status.json` 与 `skipped_asof_ledger.json`，形成至少 5 个交易日或等价 shadow/backfill 样本的多日观察结论，并把状态聚合到 catalog/dashboard 层。

DNG14 不是抓数阶段，也不是 production Go。它只负责观察、聚合、分类和给出下一步 repair/route 建议。

执行者产物：

```text
docs/tw_data_governance/DNG14_MULTI_DAY_AUTOMATIC_OBSERVATION_EXECUTION_REPORT_CN.md
docs/tw_data_governance/DNG14_MULTI_DAY_AUTOMATIC_OBSERVATION_REVIEW_CN.md
data_tw/catalog/dng14_multi_day_chain_observation.json
data_tw/catalog/dng14_multi_day_chain_observation.csv
data_tw/catalog/dng14_latest_status_chain_overlay.json
```

必须完成：

1. 扫描 `data_tw/ops/daily_auto_update/**/daily_chain_status.json` 与 `skipped_asof_ledger.json`。
2. 按 asof 聚合最新或最可信 job，避免同一天多个 dry-run 互相覆盖结论。
3. 至少覆盖以下类别：

```text
ready_chain
raw_ready_but_qlib_provider_stale
data_window_wait
weekend_or_holiday_skipped
model_a_score_missing
strategy_or_readonly_context_missing
publish_ready_but_not_published
```

4. 必须包含 `2026-06-25` ready 样例和 `2026-06-26` raw-ready/provider-stale 样例。
5. 如果实际已有样本不足 5 个交易日，允许执行者用安全 backfill/shadow 方式补 DNG13 job-local artifact，但必须使用 `--skip-finmind --skip-qlib` 或等价只读参数，且不得触发 real provider refresh/publish/latest/trading。
6. 聚合结果必须写入 `data_tw/catalog/dng14_multi_day_chain_observation.*`，并生成 `dng14_latest_status_chain_overlay.json`，说明当前全局 latest_status/dashboard 还缺什么。
7. 必须明确判断后续是否需要：

```text
formal qlib provider refresh route
validated canonical bridge route
dashboard/catalog aggregation repair
model_signal_gate enablement review
```

审查者重点：

- 是否真的聚合了多日，而不是只复述 DNG13 单日；
- 是否正确处理同一 asof 的多个 job；
- 是否把 6/27、6/28 周末和 6/26 provider stale 区分清楚；
- 是否保留 forbidden actions 全 false；
- 是否没有把 DNG14 解释成 production readiness。

### DNG15：Formal Qlib Provider 或 Validated Canonical Bridge 修复

目标：解决 DNG14 收敛出的核心 blocker：

```text
latest_raw_ready_asof=2026-06-29
latest_ready_chain_asof=2026-06-25
latest_provider_stale_asof=2026-06-29
```

DNG15 必须让至少 `2026-06-26` 从 `RAW_READY_BUT_QLIB_PROVIDER_STALE` 推进到可生成标准 Model A score / ModelSignalArtifact / StrategyInputBundle / readonly source context dry-run 的状态。

允许路线：

```text
Route A: formal qlib provider refresh route
Route B: validated canonical bridge route
```

Route A 可以使用既有 formal provider refresh/staged publish 机制，但不得切 accepted latest，不得 publish production latest。若需要真实网络或外部 provider 访问，执行者必须先产出 feasibility/blocker，不得擅自触发。

Route B 可以建立隔离的 validated canonical provider bridge，用已存在的 raw/normalized/canonical 数据生成可被 qlib Model A 推理消费的 provider view candidate。该 bridge 必须有 manifest/schema/coverage/lineage/validator，并明确 `not_published_latest=true`。

执行者产物：

```text
docs/tw_data_governance/DNG15_FORMAL_QLIB_PROVIDER_OR_CANONICAL_BRIDGE_REPAIR_EXECUTION_REPORT_CN.md
docs/tw_data_governance/DNG15_FORMAL_QLIB_PROVIDER_OR_CANONICAL_BRIDGE_REPAIR_REVIEW_CN.md
data_tw/catalog/dng15_provider_or_bridge_repair_decision.json
data_tw/catalog/dng15_modela_20260626_readiness.json
```

最低验收：

1. 解释选择 Route A 或 Route B 的原因。
2. 修复或参数化当前 Model A input/score pipeline，使其不能继续硬编码 `2026-06-25` readiness。
3. 6/26 的 ModelInferenceInput 必须通过 validator；如不能通过，必须写明 blocker。
4. 若生成 6/26 Model A score，必须生成标准 ScoreJob 和 ModelSignalArtifact，且 `source_feature_artifact` 指向 formal provider view 或 validated canonical bridge。
5. 生成 6/26 StrategyInputBundle 与 readonly/Agent source context dry-run，或明确写明下一步 blocker。
6. 重新运行 DNG14 聚合，证明 `latest_ready_chain_asof` 至少推进到 `2026-06-26`，或证明仍 blocked 且 blocker 已具体化。
7. 保持所有 publish/latest/trading gate 关闭。

禁止：

- 用 raw FinMind 直接冒充 qlib provider feature input；
- 用 6/25 score 冒充 6/26 score；
- formal accepted latest switch；
- readonly latest / Agent latest publish；
- production default model/strategy switch；
- broker/order/quick-trade；
- target position / target weight；
- 模型训练或调参。

## 16. 审查总规则

审查者必须拒绝以下情况：

1. 报告只说“latest 停在某天”，但没说明是哪一层。
2. 策略或模型直接读取 `data_tw/experiments/**` 的私有临时文件，却没有 bundle/lineage。
3. 缺 PriceStore、TWII、calendar、execution price、mark-to-market 仍继续做收益结论。
4. 用 isolated bridge 的成功冒充 formal qlib accepted latest 成功。
5. raw daily price 成功就宣称 qlib+LTR 正交链路成功。
6. validator 失败后仍更新 readonly latest。
7. 默认日更切 provider/qlib accepted latest。
8. 无 PIT/available_at 审计的特征进入模型或策略。

## 17. 成功标准

本主线完成后，后续任一研究路线在执行前应能回答：

```text
我要用哪些数据？
每个数据在哪一层？
每层最新到哪一天？
缺哪一层会阻断？
缺失是因为 provider 没发布、quota、holiday、schema、PIT、coverage，还是 formal latest 没切？
是否允许 fallback？
fallback 后还能声称什么，不能声称什么？
```

并且能用机器可读文件证明：

```text
data_tw/catalog/latest_status.json
data_tw/catalog/readiness_matrix/{asof}/{route_id}.json
DataCatalog / daily_readiness_dashboard
ModelInferenceInput / ScoreJob manifest
ModelSignalArtifact manifest
StrategyInputBundle / ReplayInputBundle manifest
validator_report.json
lineage.json
```

完整完成还必须能支撑每天自动链路：

```text
新数据进入 raw/normalized
-> canonical PriceStore / feature store 更新
-> qlib Model A score 缺失时可自动补
-> LTR Model B score 在正交数据 ready 时可自动补
-> ModelSignalArtifact 通过 validator
-> StrategyInputBundle / ReplayInputBundle 生成
-> latest_status 说明每层状态
-> readonly snapshot / Agent prompt 可在单独 gate 下消费
```

如果只能 catalog 数据、不能补生成模型 score，则本主线不能 closure。

## 18. 对后续工作的建议

优先级如下：

1. 先做 DNG0/DNG1：把现在到底有哪些数据、哪些 latest、哪些 temporary bridge 摆清楚。
2. 做 DNG2：价格、TWII、calendar、execution price 是所有回放、模型推理和 shadow 的共同地基。
3. 做 DNG3：把正交数据 raw/normalized/store 规范化，否则 qlib+LTR 每日 rerank 会继续卡。
4. 做 DNG4/DNG5：让新路线只能吃标准 bundle 和 dependency contract。
5. 做 DNG6：把 catalog/readiness 接入 daily auto 和 dashboard。
6. 做 DNG7/DNG8：打通 qlib Model A 与 LTR Model B 的只读 score 自动补生成。
7. 做 DNG9/DNG10：接入全自动脚本、策略输入包、readonly snapshot / Agent prompt source context。
8. 做 DNG11/DNG12：连续 shadow 观察并做 Go/No-Go closure。

不建议一开始就大规模搬迁历史目录。更合理的做法是：

```text
先 catalog 化
再 canonicalize 高频共用数据
再接模型推理与 score 补生成
再让新路线停止直接依赖散落 experiment 路径
最后逐步迁移历史重要产物
```

这样能最快减少“跑到一半才发现数据缺口”的问题，同时避免破坏已经完成的研究和审查证据。
