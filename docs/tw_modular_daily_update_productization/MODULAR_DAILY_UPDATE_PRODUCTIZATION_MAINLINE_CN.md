# 真实模块化日更接入主线工作文档

生成日期：2026-06-17

## 1. 背景

M0-M6 模块化地基已经收口。现在可以进入下一条小主线：把真实日更能力接入模块化链路，让系统在每天/每两小时检查到新数据后，按标准模块生成只读研究结果，并由前端展示。

本主线目标不是训练新模型，也不是切换默认策略，更不是接入交易。目标是把已有“两小时自动更新脚本”的能力改造成模块化、可审计、失败关闭的 readonly daily chain。

标准链路：

```text
AutoUpdateOrchestrator
  -> FreshnessCheck
  -> DataIngestionArtifact
  -> FeatureArtifact
  -> ModelSignalArtifact
  -> StrategyDecision / OrderIntentArtifact
  -> ReadonlyStrategySnapshot
  -> RunRegistry
  -> readonly latest pointer
  -> GET-only API / Frontend display
```

## 2. 总原则

本主线允许做：

```text
审计既有两小时脚本
构建真实模块化日更 dry-run / shadow-run
把真实新数据转换为 DataIngestionArtifact
生成 FeatureArtifact
生成已冻结模型的 ModelSignalArtifact
生成已冻结策略的 OrderIntentArtifact
生成 readonly snapshot
更新 readonly latest pointer
前端读取 readonly latest
记录 RunRegistry
```

本主线默认不允许做：

```text
训练新模型
调参或搜索模型
新增正式策略收益结论
切 default candidate / default strategy
触发 provider publish / refresh
切 provider accepted latest 或 qlib accepted latest
写 monitor config / scan / alerts
连接 broker / quick-trade / orders
修改 Agent prompt / tool / action
让前端本地计算策略或 replay
把训练窗口收益当策略优劣证据
```

如果执行者认为必须触发真实 provider refresh 才能拉新数据，必须停下来说明：

```text
为什么现有数据源无法以 DataIngestionArtifact 方式读取
会触发哪些外部/本地写入
是否会切 accepted latest
是否有 dry-run 或 staging 输出
如何失败回滚
```

未经用户确认，不得把 provider publish / accepted latest 切换纳入本主线。

## 3. 默认候选范围

本主线默认只接入当前已冻结、已审计的 readonly 候选，不新增真实模型/策略。

默认模型/策略组合建议：

```text
model_id: e4_frozen_qlib_2023_2025_ltr
strategy_rule: top50_exit_one_worst_sell
display_role: readonly_candidate
not_order=true
not_target_position=true
not_investment_advice=true
```

如果要同时保留 fresh qlib 或其他候选，必须在 Phase U0 中列清：

```text
model_id
strategy_rule
source artifact
train window
allowed signal/replay window
readonly latest eligibility
frontend display role
default status
```

不得在本主线中自动切换默认策略。

## 4. 分阶段计划

本支线压缩为 4 阶段：

```text
U0 Contract and Current Daily Chain Audit
U1 Daily Data / Feature / ModelSignal Artifact Integration
U2 Daily OrderIntent / ReadonlySnapshot / RunRegistry Publish
U3 AutoUpdate + Frontend/API Acceptance + Final Runbook
```

每阶段都必须执行者写报告，审查者审查后才能进入下一阶段。

## 5. Phase U0：合同冻结与现状审计

### 5.1 目标

审计既有日更脚本和当前数据/模型/策略产物，冻结本主线的输入、输出、禁止事项和候选范围。

U0 不改生产代码，不触发日更。

### 5.2 必做项

1. 列出既有自动更新入口：

```text
scripts/run_daily_tw_stock_auto_update.py
cron / systemd / docker worker 入口，如存在
前端/API 当前读取 latest 的入口，如存在
```

2. 审计当前默认路径：

```text
freshness check 如何判断新数据
新数据写到哪里
是否触发 provider refresh / publish
是否切 accepted latest
是否写 monitor / broker / order
是否已有 readonly latest pointer
```

3. 冻结本主线 candidate：

```text
model_id
strategy_rule
input artifacts
train windows
latest allowed signal date
feature dependencies
score/rank fields
frontend display role
```

4. 产出 U0 执行报告：

```text
docs/tw_modular_daily_update_productization/PHASEU0_CONTRACT_AND_CURRENT_CHAIN_AUDIT_EXECUTION_REPORT_CN.md
```

### 5.3 U0 通过标准

```text
没有修改生产代码
没有触发真实日更
没有切 accepted latest
没有 provider publish
没有 broker/order/monitor 写入
本主线输入/输出/候选模型策略冻结
明确哪些旧脚本路径是 legacy，哪些是本主线要接的 readonly path
```

## 6. Phase U1：每日数据 / 特征 / 模型信号 artifact 接入

### 6.1 目标

把当天新数据或 no_new_data 状态转换成标准上游 artifact，并生成冻结模型可消费的每日 `ModelSignalArtifact`。

U1 合并原 DataIngestion、FeatureArtifact、ModelSignal 三步，因为它们共同回答一个问题：当天数据能否安全变成模型信号。

### 6.2 必做项

新增或扩展：

```text
scripts/build_tw_daily_data_ingestion_artifact.py
scripts/validate_tw_daily_data_ingestion_artifact.py
scripts/build_tw_daily_feature_artifact.py
scripts/validate_tw_daily_feature_artifact.py
scripts/build_tw_daily_model_signal_artifact.py
scripts/validate_tw_daily_model_signal_artifact.py
```

建议输出目录：

```text
data_tw/artifacts/daily_data_ingestion/<run_id>/
data_tw/artifacts/daily_features/<run_id>/
data_tw/artifacts/daily_model_signals/<model_id>/<run_id>/
```

DataIngestionArtifact 至少包含：

```text
manifest.json
schema.json
coverage_audit.csv
symbol_mapping_audit.csv
forbidden_action_audit.json
freshness_audit.json
```

FeatureArtifact 至少包含：

```text
manifest.json
features.parquet or features.csv
schema.json
coverage_audit.csv
pit_availability_audit.csv
forbidden_future_field_audit.json
```

ModelSignalArtifact 必须输出标准字段：

```text
date
instrument
model_name
model_family
candidate_rank
buy_score
raw_score
score_rank
full_qlib_rank
signal_asof
available_at
source_artifact
source_model_artifact
source_feature_artifact
```

### 6.3 必须检查

```text
new_data 和 no_new_data 两类样例
asof_date / available_at
coverage audit
symbol mapping audit
available_at <= signal_asof
无 future_return / forward_return / label / realized_pnl
candidate_rank / buy_score / full_qlib_rank 来源清楚
LTR 只在 qlib top50 内重排 buy_score
不改变 qlib sell boundary
不训练模型
不触发 provider publish / accepted latest
```

### 6.4 U1 通过标准

```text
三个 artifact validator 均 ok=true
每个 validator 至少有一个正例和一个负例
缺 available_at / coverage audit / PIT audit / forbidden action audit 会失败
ModelSignalArtifact 通过标准合同校验
不训练模型
不计算收益
不切 accepted latest
```

执行报告：

```text
docs/tw_modular_daily_update_productization/PHASEU1_DAILY_SIGNAL_ARTIFACT_INTEGRATION_EXECUTION_REPORT_CN.md
```

## 7. Phase U2：每日策略意图 / readonly snapshot / RunRegistry 发布

### 7.1 目标

从 U1 `ModelSignalArtifact` 生成每日只读 `OrderIntentArtifact`，再生成 `ReadonlyStrategySnapshot`、写入 `RunRegistry`，并在全部 validator 通过后更新 readonly latest pointer。

U2 合并原 OrderIntent、Snapshot、RunRegistry、readonly latest pointer，因为它们共同回答一个问题：当天模型信号能否安全变成前端可读策略结果。

### 7.2 必做项

新增或扩展：

```text
scripts/build_tw_daily_order_intent_artifact.py
scripts/validate_tw_daily_order_intent_artifact.py
scripts/publish_tw_daily_readonly_snapshot.py
scripts/validate_tw_daily_readonly_snapshot.py
scripts/validate_tw_daily_run_registry.py
```

建议输出目录：

```text
data_tw/artifacts/daily_order_intents/<model_id>/<strategy_rule>/<run_id>/
data_tw/artifacts/daily_readonly_snapshots/<run_id>/
data_tw/artifacts/daily_run_registry/<run_id>/
data_tw/artifacts/daily_readonly_latest/latest.json
```

OrderIntentArtifact 必须声明：

```text
readonly_only=true
not_order=true
not_target_position=true
not_investment_advice=true
no_broker_order=true
strategy_rule
max_buy_count
max_sell_count
source_signal_artifact
portfolio_state_source
```

RunRegistry 必须覆盖：

```text
success_validators_passed_updates_readonly_latest
no_new_data_noop_preserves_previous_latest
validator_failed_preserves_previous_latest
module_failed_preserves_previous_latest
```

### 7.3 必须检查

```text
OrderIntentArtifact 无 execution_price / cash / equity / broker_order_id
策略不读 replay result
策略不读模型私有字段
每日 action 数符合策略配置
全部 validator 通过才更新 readonly latest
no_new_data 不刷新 latest 伪造成新结果
validator_failed 保留 previous latest
latest pointer 记录 previous/proposed/committed/checksum/run_id
readonly latest pointer != provider accepted latest
readonly latest pointer != qlib accepted latest
```

### 7.4 U2 通过标准

```text
OrderIntent / ReadonlySnapshot / RunRegistry validators ok=true
success/noop/validator_failed/module_failed 样例齐全
readonly latest pointer 行为正确
不切 provider accepted latest
不切 qlib accepted latest
不写 monitor / broker / order
```

执行报告：

```text
docs/tw_modular_daily_update_productization/PHASEU2_DAILY_READONLY_SNAPSHOT_AND_REGISTRY_EXECUTION_REPORT_CN.md
```

## 8. Phase U3：自动脚本接入 + 前端/API 验收 + 最终收口

### 8.1 目标

把 U1-U2 串入既有两小时自动脚本或新 readonly orchestrator entrypoint，并让前端/API 读取最新 readonly daily result。最后输出运维手册和收口报告。

U3 合并自动脚本、前端/API、最终验收，因为它们共同回答一个问题：这条链路是否可以真实自动运行并给用户展示。

### 8.2 推荐实现

推荐方案 A：

```text
新增 scripts/run_tw_modular_daily_readonly_update.py
既有 scripts/run_daily_tw_stock_auto_update.py 调用该 readonly entrypoint
legacy provider publish gate 继续默认关闭
```

备选方案 B：

```text
在 scripts/run_daily_tw_stock_auto_update.py 内添加 modular readonly subcommand/path
默认仍不得触发 legacy provider publish / accepted latest
```

后端只允许 GET：

```text
GET /api/tw-stock/readonly-daily-latest
GET /api/tw-stock/readonly-daily-run-registry
```

前端展示：

```text
data_asof
run_asof
model_id
strategy_rule
new_data_detected
latest_status
candidate actions / observations
audit status
error reason, if failed/noop
```

### 8.3 必须检查

```text
两小时自动脚本能触发 modular readonly chain
no_new_data / success / validator_failed / module_failed 都有样例
默认路径 provider refresh/publish/accepted latest 不可达
legacy gate 未暴露到前端或 Agent
RunRegistry 可追溯
失败关闭保留 previous latest
frontend readonly workflow only GET
forbidden_request_count=0
replay_strategy_write_count=0
provider publish / refresh / accepted latest request count=0
monitor / broker / order request count=0
Agent prompt/tool/action 未改
用户主视图清楚显示最新状态，不被工程字段主导
```

### 8.4 U3 通过标准

```text
U1-U2 validators 全部 ok=true
自动 orchestrator dry-run / shadow-run ok=true
真实 no_new_data / success / validator_failed 样例齐全
readonly latest pointer 行为正确
前端 GET-only audit 通过
两小时自动脚本默认路径安全
Agent 未扩权
无 provider accepted latest switch
无 broker/order/monitor 写入
```

必须输出：

```text
docs/tw_modular_daily_update_productization/PHASEU3_AUTOMATION_FRONTEND_FINAL_ACCEPTANCE_EXECUTION_REPORT_CN.md
docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_FINAL_ACCEPTANCE_CN.md
docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_RUNBOOK_CN.md
docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_REVIEWER_CHECKLIST_CN.md
```

## 9. 执行者通用 Prompt

```text
你是执行者。请按 docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_PRODUCTIZATION_MAINLINE_CN.md 执行当前 Phase U 子阶段。

本主线目标是把真实日更能力接入模块化只读链路。你必须保持：
- 不训练新模型，除非用户另开新模型主线；
- 不切 default strategy / default candidate；
- 不触发 provider publish / refresh；
- 不切 provider accepted latest 或 qlib accepted latest；
- 不写 monitor config / scan / alerts；
- 不连接 broker / quick-trade / orders；
- 不修改 Agent prompt / tool / action；
- 不让前端本地计算策略或 replay；
- 所有 latest 更新只允许是 readonly latest pointer，且必须在全部 validator 通过后发生。

请输出执行报告，包含：
1. 本阶段目标；
2. 修改/新增文件；
3. 输入/输出 artifact；
4. validator 命令和结果；
5. 正例/负例样例；
6. latest pointer 行为；
7. 只读安全边界；
8. 明确未执行事项；
9. 残余风险；
10. 是否建议进入下一阶段。
```

## 10. 审查者通用 Prompt

```text
你是审查者。请按 docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_PRODUCTIZATION_MAINLINE_CN.md 审查执行者的 Phase U 子阶段报告。

重点确认：
1. 是否严格保持本阶段范围；
2. 是否没有训练新模型、调参、跑新收益结论；
3. 是否没有切 default strategy / default candidate；
4. 是否没有 provider publish / refresh；
5. 是否没有 accepted latest switch；
6. 是否没有 monitor / broker / quick-trade / order 写入；
7. 是否所有输出都是标准 artifact；
8. 是否有 validator 正例和负例；
9. latest pointer 是否只在全部 validator 通过后更新；
10. no_new_data / validator_failed / module_failed 是否保留 previous latest；
11. 前端/API 是否 GET-only；
12. Agent prompt/tool/action 是否未改；
13. 是否允许进入下一阶段。

如发现 provider/accepted latest、交易、默认策略切换或未来函数风险，必须停止放行并要求修复。
```

## 11. 第一阶段建议

建议立即开始：

```text
Phase U0 Contract and Current Daily Chain Audit
```

U0 不改代码，不触发日更，只做现状审计和合同冻结。U0 通过后再进入 U1。
