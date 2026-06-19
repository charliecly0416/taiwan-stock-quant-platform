# 台湾股票量化研究与生产链路模块化解耦设计文档

生成日期：2026-06-16

## 1. 背景

当前项目已经在 `scripts/run_extended_oos_formal_replay_matrix.py` 中完成了回放层的初步解耦：

- `candidate_rank` 负责 qlib top50 universe / exit boundary；
- `buy_score` 负责 top50 内买入排序；
- `full_qlib_rank` 负责持仓跌出 top50 后的最差排名判断；
- 纯 qlib 与 LTR 可以使用同一个 replay engine，只是输入列映射不同。

但这还不是完整的模块化链路。完整目标应该是：

> 数据、特征、模型、信号、策略、执行回放、分析展示、日更编排都通过明确 contract 连接。以后新增数据源、新模型、新策略、新展示页面时，只要满足对应规范，就能接入链路，而不是改一堆临时脚本。

本文档定义后续模块化解耦的目标架构、模块边界、输入输出规范、校验器和分阶段实施计划。

## 2. 总体目标

目标不是把所有代码立刻重写成框架，而是先冻结 contract，再逐步把现有脚本迁移到 contract 驱动。

最终链路应满足：

1. 新数据源只要输出标准 `RawDataArtifact` / `NormalizedDataArtifact`，即可进入数据集构建。
2. 新特征只要输出标准 `FeatureArtifact`，即可被模型训练或信号生成使用。
3. 新模型只要输出标准 `ModelSignalArtifact`，即可进入同一个策略与回放链路。
4. 新策略只要实现标准 `StrategyRuleContract`，即可消费任意模型信号。
5. 回放引擎只负责成交、费用、税费、持仓、净值、审计，不感知模型内部。
6. 分析和展示只读取标准 `ReplayResultArtifact` / `StrategyDecisionArtifact`，不直接解析模型私有文件。
7. 日更编排只负责按 contract 串联模块，不在编排脚本里写模型或策略逻辑。

## 3. 推荐模块边界

### 3.1 Provider / 自动化数据抓取模块

职责：

- 从 Yahoo、FinMind、TWSE、TPEX 或其他来源抓取原始数据；
- 记录抓取时间、来源、请求参数、数据覆盖、错误与重试；
- 不做模型特征、不做策略判断、不触发交易动作。

输入：

- `DataSourceConfig`
- `asof_date`
- provider credentials / rate limit config

输出：

- `RawDataArtifact`
- `FetchManifest`
- `FetchQualityAudit`

建议 contract：

```yaml
artifact_type: raw_data
provider: yahoo|finmind|twse|tpex|custom
dataset_name: tw_price_daily|margin_short|institutional_flow|monthly_revenue
asof_date: YYYY-MM-DD
created_at: ISO-8601
source_window:
  start: YYYY-MM-DD
  end: YYYY-MM-DD
files:
  raw_csv: path
schema:
  required_columns: [...]
quality:
  row_count: int
  duplicate_key_count: int
  missing_key_count: int
  latest_observation_date: YYYY-MM-DD
  timezone: Asia/Taipei
forbidden:
  provider_publish: false
  accepted_latest_switch: false
  broker_or_order_action: false
```

必须禁止：

- 在抓取模块里产生模型分数；
- 在抓取模块里更新默认策略；
- 在抓取模块里触发 provider accepted latest 切换；
- 在抓取模块里触发 monitor / broker / order。

### 3.2 Normalizer / 标准化数据集模块

职责：

- 把 raw data 转成统一 schema；
- 处理股票代码别名、交易日历、除权息价格、成交量单位、币种、缺失值；
- 输出可供 qlib / 特征工程 / 回放价格源使用的数据。

输入：

- `RawDataArtifact`
- `InstrumentMaster`
- `TradingCalendar`

输出：

- `NormalizedDataArtifact`
- `InstrumentCoverageAudit`
- `DataQualityAudit`

建议标准字段：

```text
date
instrument
open
high
low
close
volume
amount
adjusted_close
source
asof_date
available_at
```

对于非价格类数据，例如法人、融资融券、月营收：

```text
date
instrument
field_name
field_value
source
report_period
asof_date
available_at
```

关键原则：

- `date` 是数据所属业务日期；
- `available_at` 是策略可见时间；
- 策略只能使用 `available_at <= signal_asof` 的数据；
- instrument 必须统一为 `TWxxxx` 格式；
- 股票有效期必须由 `InstrumentMaster` 管，不允许各脚本私自判断。

### 3.3 Instrument Master / Universe 模块

职责：

- 管理股票代码、别名、上市/下市/兴柜/转上市、有效期；
- 管理 as-of active universe；
- 管理 liquid top150、top50 等候选池构建规则。

输入：

- 交易所证券清单；
- provider instruments；
- 历史价格覆盖；
- liquidity data。

输出：

- `InstrumentMasterArtifact`
- `UniverseArtifact`
- `UniverseAudit`

建议字段：

```text
instrument
ticker
exchange
name
start_date
end_date
status
alias_list
source
asof_date
```

Universe 输出：

```text
date
instrument
universe_name
eligible_flag
reason
liquidity_rank
active_asof_flag
price_available_flag
history_available_flag
```

必须禁止：

- 用未来上市信息倒灌历史 universe；
- 用回测窗口未来收益筛选 universe；
- 每个模型自己定义一套不透明 universe。

### 3.4 Feature Builder / 特征模块

职责：

- 从 normalized data 构建 PIT-safe 特征；
- 明确每个特征的 `available_at`；
- 输出特征矩阵，不训练模型、不做策略。

输入：

- `NormalizedDataArtifact`
- `UniverseArtifact`
- `FeatureConfig`

输出：

- `FeatureArtifact`
- `FeatureCoverageAudit`
- `PITAvailabilityAudit`

建议 contract：

```yaml
artifact_type: feature_matrix
feature_set_name: alpha158|orthogonal_o2|custom_x
asof_window:
  start: YYYY-MM-DD
  end: YYYY-MM-DD
rows:
  key: [date, instrument]
required_columns:
  - date
  - instrument
  - available_at
features:
  - feature_name
  - dtype
  - source
  - lag_policy
pit_policy:
  require_available_at_lte_signal_asof: true
```

数据表字段：

```text
date
instrument
available_at
feature_1
feature_2
...
```

必须禁止：

- 特征里包含 future return / label；
- 用测试窗口统计量 fit scaler；
- 对 2026 test 做调参；
- 在 feature builder 内选择策略。

### 3.5 Label Builder / 标签模块

职责：

- 构建训练标签，例如未来 10 日收益、rank bucket、top-heavy relevance；
- 标签只能进入训练样本，不得进入 replay-ready signal artifact。

输入：

- price data；
- label config；
- train window。

输出：

- `LabelArtifact`
- `LabelAudit`

建议字段：

```text
date
instrument
label_name
label_value
label_horizon
label_available_for_training_only
```

必须禁止：

- label 出现在 replay-ready score 文件；
- label 出现在策略输入；
- label 出现在前端展示候选。

### 3.6 Model Training 模块

职责：

- 训练 qlib / LTR / 其他模型；
- 输入 feature + label；
- 输出 frozen model、训练 manifest、OOS score/inference 脚本。

输入：

- `FeatureArtifact`
- `LabelArtifact`
- `TrainingConfig`
- `TrainValidTestSplitContract`

输出：

- `ModelArtifact`
- `TrainingManifest`
- `ModelLeakageAudit`

建议 manifest：

```yaml
artifact_type: model
model_name: frozen_qlib_2018_2022
model_family: qlib_lgbm|ltr_lambdamart|custom
train_window:
  start: YYYY-MM-DD
  end: YYYY-MM-DD
valid_window:
  start: YYYY-MM-DD
  end: YYYY-MM-DD
test_or_oos_window:
  start: YYYY-MM-DD
  end: YYYY-MM-DD
feature_artifact: path
label_artifact: path
model_file: path
params_hash: sha256
data_hash: sha256
no_test_label_used: true
no_test_tuning: true
```

必须禁止：

- 在训练模块做 replay；
- 用测试窗口收益选择模型；
- 静默改参数；
- 一个报告里混用多个模型但不说明。

### 3.7 Model Signal / Score 输出模块

职责：

- 把模型输出统一成可供策略消费的信号表；
- 对 qlib、LTR、其他模型统一使用 `ModelSignalArtifact`；
- 不做交易决策。

输入：

- frozen model；
- feature artifact；
- universe artifact。

输出：

- `ModelSignalArtifact`
- `SignalCoverageAudit`
- `ForbiddenFieldAudit`

标准字段：

```text
date
instrument
model_name
model_family
candidate_rank
buy_score
raw_score
score_rank
signal_asof
available_at
source_model_artifact
source_feature_artifact
```

对于 LTR：

- `candidate_rank` 必须来自底座 qlib；
- `buy_score` 来自 LTR；
- `raw_score` 可保存 LTR 原始 score；
- 不得改变 qlib universe 边界，除非策略明确允许。

对于纯 qlib：

- `candidate_rank` 来自 qlib rank；
- `buy_score` 可以等于 qlib score 或 qlib-derived adaptive score；
- `raw_score` 保存 qlib 原始 score。

必须禁止：

- signal artifact 中出现 label；
- signal artifact 中出现 realized PnL；
- signal artifact 中出现 future return；
- LTR 悄悄替换 qlib top50 universe。

### 3.8 Strategy Rule 模块

职责：

- 只根据标准信号、当前持仓、策略规则生成订单意图；
- 不读取模型私有文件；
- 不计算模型分数；
- 不读取未来价格。

输入：

- `ModelSignalArtifact`
- `PortfolioState`
- `StrategyRuleConfig`

输出：

- `OrderIntentArtifact`
- `StrategyDecisionAudit`

标准输入字段：

```text
date
instrument
candidate_rank
buy_score
full_qlib_rank
signal_asof
```

标准输出字段：

```text
signal_date
instrument
intent_action
intent_reason
target_rank
candidate_rank
buy_rank
full_qlib_rank
max_buy_count
max_sell_count
strategy_rule
```

策略规则示例：

- `original_top10_rotation`
- `top50_exit_all`
- `top50_exit_one_worst_sell`
- `one_sell_one_buy_correct`
- `buy_hold_until_exit`
- `risk_off_cash_rule`

必须禁止：

- 策略模块读取 future return；
- 策略模块自行训练模型；
- 策略模块自行改 universe；
- 策略模块自行决定价格成交。

### 3.9 Execution / Replay 模块

职责：

- 把 `OrderIntent` 转成历史回放成交；
- 负责 next-day execution、价格、手续费、交易税、现金、持仓、净值；
- 不感知模型内部，不选择股票。

输入：

- `OrderIntentArtifact`
- `PriceStore`
- `ExecutionConfig`
- `InitialPortfolioState`

输出：

- `ReplayResultArtifact`
- `ActionLedger`
- `DailyNav`
- `PositionSnapshot`
- `ExecutionAudit`

标准输出：

```text
actions.csv
daily_nav.csv
position_snapshots.csv
summary.csv
execution_audit.csv
manifest.json
```

必须审计：

- active action quantity > 0；
- execution_date > signal_date；
- max holding count；
- duplicate position；
- negative cash；
- missing price；
- skipped action reason；
- final holdings mark-to-market。

### 3.10 Analysis / Attribution 模块

职责：

- 分析 replay result；
- 做收益、回撤、换手、PnL 集中度、持仓贡献、规则归因；
- 不重新回放，不改策略。

输入：

- `ReplayResultArtifact`
- `ModelSignalArtifact`
- optional benchmark data。

输出：

- `AnalysisReportArtifact`
- `AttributionTables`
- `RiskTables`

分析内容：

- return / max drawdown；
- turnover；
- action count；
- symbol PnL contribution；
- day PnL contribution；
- rank bucket forward diagnostics；
- qlib vs LTR trade diff；
- strategy rule sensitivity；
- walk-forward stability。

必须禁止：

- 分析模块反向修改策略结果；
- 分析后自动切换默认策略；
- 把训练窗口收益当默认策略证据。

### 3.11 Presentation / 展示模块

职责：

- 展示标准化策略结论；
- 从 `StrategyDecisionArtifact` / `ReplayResultArtifact` / `AnalysisReportArtifact` 读取；
- 不直接读模型训练中间文件；
- 不触发真实交易。

输入：

- latest readonly strategy artifact；
- replay summary；
- analysis report。

输出：

- 前端页面；
- readonly API response；
- report markdown / json。

必须禁止：

- 前端自行计算模型分数；
- 前端触发 provider refresh / accepted latest switch；
- 前端触发 monitor scan / broker / order；
- 前端展示未经审计的临时实验为默认策略。

### 3.12 Daily Orchestrator / 日更编排模块

职责：

- 在每日数据可用后按 DAG 串联模块；
- 只做编排，不写业务逻辑；
- 每一步产出 manifest；
- 任一步 contract fail 则停止后续策略更新。

推荐 DAG：

```text
fetch_raw_data
  -> normalize_data
  -> update_instrument_master
  -> build_universe
  -> build_features
  -> run_model_signal
  -> build_strategy_decision
  -> readonly_replay_or_position_diff
  -> analysis_summary
  -> publish_readonly_artifact
```

日更只读边界：

- 可以生成最新候选、持仓 diff、策略建议；
- 不自动下单；
- 不自动保存 monitor config；
- 不自动切换 accepted latest，除非有单独受控发布流程。

## 4. 统一 Artifact 目录规范

建议统一：

```text
data_tw/artifacts/
  raw/{dataset_name}/{run_id}/
  normalized/{dataset_name}/{run_id}/
  universe/{universe_name}/{run_id}/
  features/{feature_set}/{run_id}/
  labels/{label_name}/{run_id}/
  models/{model_name}/{run_id}/
  signals/{model_name}/{run_id}/
  strategies/{strategy_name}/{run_id}/
  replays/{replay_name}/{run_id}/
  analysis/{analysis_name}/{run_id}/
  publish/{artifact_name}/{run_id}/
```

每个目录必须包含：

```text
manifest.json
schema.json
quality_audit.csv or .json
forbidden_action_audit.json
```

## 5. 统一 Manifest 基础字段

所有 artifact 都应包含：

```yaml
artifact_type: string
artifact_name: string
run_id: string
created_at: ISO-8601
created_by: script name
source_artifacts:
  - path
input_hashes:
  key: sha256
output_files:
  key: path
window:
  start: YYYY-MM-DD
  end: YYYY-MM-DD
asof_policy:
  signal_asof: string
  available_at_required: true
schema_version: string
contract_version: string
quality_status: pass|warn|fail
forbidden_actions:
  no_training: bool
  no_tuning: bool
  no_future_label: bool
  no_provider_publish: bool
  no_broker_order: bool
```

## 6. Validator 设计

每个模块都要有 validator。建议先实现一个统一命令：

```bash
python scripts/validate_tw_quant_contract.py --artifact path/to/manifest.json
```

Validator 类型：

1. `validate_raw_data`
2. `validate_normalized_data`
3. `validate_universe`
4. `validate_features_pit`
5. `validate_labels_train_only`
6. `validate_model_training_manifest`
7. `validate_model_signal`
8. `validate_strategy_decision`
9. `validate_replay_result`
10. `validate_analysis_report`
11. `validate_publish_readonly`

Replay validator 必查：

- `active_nonpositive_qty == 0`
- `execution_date > signal_date`
- `max_holding_count <= target_holding_count`
- `duplicate_position_day_symbol == 0`
- `forbidden_columns_used_for_ranking == false`
- `future_label_or_return_columns_present == false`
- `actual_start_date >= requested_start_date`
- `actual_end_date <= requested_end_date`

## 7. Config 化接入

当前 `StrategySpec` 仍在 Python 中硬编码。后续应迁移到配置：

```yaml
strategies:
  - method: fresh_qlib_adaptive
    family: qlib
    signal_artifact: data_tw/artifacts/signals/fresh_qlib_adaptive/latest/manifest.json
    candidate_rank_col: candidate_rank
    buy_score_col: buy_score
    full_rank_artifact: data_tw/artifacts/signals/fresh_qlib_adaptive/latest/full_rank_manifest.json
    full_rank_col: full_qlib_rank

  - method: e4_frozen_qlib_orthogonal_ltr
    family: ltr
    signal_artifact: data_tw/artifacts/signals/e4_ltr/latest/manifest.json
    candidate_rank_col: candidate_rank
    buy_score_col: buy_score
    full_rank_artifact: data_tw/artifacts/signals/e1_frozen_qlib/latest/full_rank_manifest.json
    full_rank_col: full_qlib_rank

rules:
  - top50_exit_one_worst_sell
  - one_sell_one_buy_correct

windows:
  - name: 2026_ytd
    start: 2026-01-01
    end: 2026-05-07
```

新模型接入时，只需要：

1. 产出标准 `ModelSignalArtifact`；
2. 通过 validator；
3. 在 config 里声明；
4. replay matrix 自动纳入。

## 8. 当前项目与目标状态差距

当前已具备：

- replay 内部 qlib / LTR 分数解耦；
- `candidate_rank` / `buy_score` / `full_qlib_rank` 概念清晰；
- formal replay matrix 产出统一 summary/actions/nav/snapshots；
- 已有基本 forbidden / coverage / integrity 审计。

仍缺：

- data source contract；
- normalized dataset contract；
- feature contract；
- model signal artifact contract；
- strategy decision artifact；
- execution/replay artifact contract 版本化；
- analysis artifact contract；
- presentation readonly contract；
- config 化注册；
- 统一 validator；
- daily orchestrator contract。

## 9. 建议实施阶段

### Phase M0：Contract 冻结

目标：

- 写清楚所有模块 contract；
- 不改业务逻辑；
- 不重跑模型；
- 不新增策略结论。

产物：

- `DATA_INPUT_CONTRACT_CN.md`
- `MODEL_SIGNAL_CONTRACT_CN.md`
- `STRATEGY_RULE_CONTRACT_CN.md`
- `REPLAY_RESULT_CONTRACT_CN.md`
- `DAILY_ORCHESTRATION_CONTRACT_CN.md`

### Phase M1：Formal Replay Matrix Config 化

目标：

- 把 `StrategySpec` 从 Python 移到 YAML；
- replay engine 只读取 config；
- 保持当前结果可复现。

通过条件：

- config 版与当前脚本 summary 差异为 0；
- validator pass；
- no training / no tuning。

### Phase M2：ModelSignalArtifact 标准化

目标：

- 把现有 qlib / LTR replay-ready 文件转换成统一 signal artifact；
- 字段统一为 `candidate_rank / buy_score / full_qlib_rank / signal_asof / available_at`。

通过条件：

- 所有现有模型均可通过统一 signal validator；
- replay matrix 不再直接读旧模型私有列。

### Phase M3：StrategyDecisionArtifact 拆分

目标：

- 策略模块只生成 order intent；
- replay execution 模块只负责成交与记账；
- 分离 `choose_sells` 与 execution。

通过条件：

- order intent 可单独审计；
- replay result 与旧 formal matrix 在同规则下可复现。

### Phase M4：数据抓取与标准数据集解耦

目标：

- 自动抓取只产出 raw artifact；
- normalize 只产出 normalized artifact；
- feature builder 从 normalized artifact 读取；
- 日更链路按 manifest 串联。

通过条件：

- 日更可以从 raw -> normalized -> feature -> signal 跑通；
- 任一模块失败时不会污染下游 latest；
- 不触发 provider publish / accepted latest / broker。

### Phase M5：分析与展示解耦

目标：

- analysis 只读 replay result；
- frontend/API 只读 publish artifact；
- 展示不依赖模型训练目录和临时脚本。

通过条件：

- 前端策略页可以换数据源 artifact 而不改页面逻辑；
- E2E 只读安全通过；
- 不展示未审计临时实验为默认策略。

### Phase M6：Daily Orchestrator DAG 化

目标：

- 每日自动数据更新后，按 contract 跑完整只读策略链路；
- 支持多个模型、多个策略规则并行；
- 输出 latest readonly artifact。

通过条件：

- 每一步有 manifest；
- 每一步 validator pass；
- fail-fast；
- 可追溯到原始数据和模型版本。

## 10. 关键设计原则

1. 模块只做自己的事。
2. 模型不决定策略规则。
3. 策略不读模型私有文件。
4. 回放不重新选股。
5. 分析不改结果。
6. 展示不触发动作。
7. 日更不写业务逻辑。
8. 所有 artifact 必须有 manifest。
9. 所有模块必须有 validator。
10. 默认策略切换必须有单独决策文档。

## 11. 对当前研究的直接影响

在完成 M1-M3 前：

- 仍可使用 `formal_replay_matrix` 做研究；
- 但新增模型/策略仍需要谨慎改 config 或脚本；
- 不能宣称已完成全链路模块化。

完成 M1-M3 后：

- 新模型只需输出标准 signal；
- 新策略只需输出标准 order intent；
- replay result 可直接进入统一 analysis；
- qlib / LTR / 其他模型可以公平比较。

完成 M4-M6 后：

- 每日抓取、模型信号、策略候选、分析展示可以形成稳定只读生产链路；
- 新数据源、新特征、新模型、新策略都能按 contract 插拔；
- 项目才真正进入“模块化解耦链路”状态。
