# Phase V 真实数据就绪门与全自动只读日更接入工作文档

生成日期：2026-06-17

## 1. 背景与目标

Phase U 已经完成模块化只读日更骨架：

```text
DataIngestionArtifact
-> FeatureArtifact
-> ModelSignalArtifact
-> OrderIntentArtifact
-> ReadonlyStrategySnapshot
-> RunRegistry
-> readonly latest pointer
-> GET-only API / Frontend
```

但 U3 收口的是 staging/shadow-run readonly chain，还没有真正做到每天收盘后自动拉取 Yahoo、FinMind 与正交 LTR 所需新增数据，然后在数据完整时自动生成第二天可展示的只读策略结果。

Phase V 的目标是补上真实数据源就绪层：

```text
每两小时尝试拉取真实数据
-> Yahoo / FinMind / 正交数据源 staging artifact
-> MultiModel DataReadinessGate
-> 全部已保留模型的强制数据就绪后才允许进入模型/策略链路
-> 自动生成默认模型+默认策略的 readonly daily latest
-> 用户在前端切换模型/策略时，复用同一份已就绪数据按需生成对应只读决策
-> 前端展示数据状态、模型/策略选择和对应只读结果
```

本支线仍然是只读研究链路，不接交易，不切正式 provider/latest，不改变默认策略。

## 2. 核心原则

允许做：

```text
读取真实 Yahoo / FinMind / 正交数据源
把成功拉到的数据写入 staging/raw artifact
记录每个数据源的 freshness / coverage / available_at / failure reason
构建 MultiModel DataReadinessGate
确保数据覆盖所有已保留模型的 required dependencies，而不是只覆盖默认模型
只有全部强制数据源和字段通过 gate 后，才触发模型/策略链路
自动日更只生成默认模型+默认策略的 readonly latest
用户切换模型/策略时，后台复用已就绪 staging/features/signals 按需生成对应只读决策
在成功通过全部 validator 后更新 readonly daily latest pointer
前端展示 ready / pending / failed / no_new_data / keep_previous_latest 状态
```

默认禁止：

```text
训练新模型
重训或替换 e4 / fresh qlib / LTR 权重
切换 default strategy / default candidate
provider publish / refresh 正式发布路径
切 provider accepted latest / qlib accepted latest
写 monitor config / scan / alerts
连接 broker / quick-trade / orders
修改 Agent prompt / tool / action
用部分数据生成策略
只为默认模型拉取窄口径数据，导致其他保留模型无法运行
前端切换模型/策略时重新触发外部数据抓取
在数据未通过 DataReadinessGate 时更新 readonly latest
```

特别说明：

```text
真实外部数据可以拉取到 staging。
但 staging 拉取不等于 provider publish。
staging 成功不允许自动切 accepted latest。
readonly latest pointer 只代表前端可展示的只读研究结果，不代表交易目标或正式 qlib/provider latest。
自动触发可以只跑默认组合；交互式模型/策略切换必须复用同一 target_asof 的 ready 数据重跑下游链路，不能重新抓数据。
```

## 3. 数据就绪合同

执行者必须冻结以下字段，不允许边做边改口径。

### 3.1 日期口径

```text
target_asof: 本次要使用的最新市场数据日期，例如 2026-06-17
decision_for: 本次只读策略面向的下一交易日，例如 2026-06-18
decision_cutoff: 系统允许生成 decision_for 结果的最晚时间
run_id: 本轮自动任务唯一 ID
```

必须满足：

```text
所有用于 target_asof 的数据 available_at <= decision_cutoff
所有正交特征仍按 available_at <= signal_asof / decision_cutoff 使用
不能因为想在盘前生成结果，就把尚未真实可得的数据当作已可得
```

### 3.2 强制数据源

至少包含：

```text
Yahoo 日行情或价格类数据
FinMind 日行情 / 基础数据 / 复权或必要补充字段
正交 LTR 需要的所有新增数据源
raw qlib / fresh qlib / frozen qlib / LTR rerank 等已保留模型各自需要的全部输入字段
股票 universe / instrument 有效期 / symbol mapping
交易日历
```

本支线的数据 gate 必须以“已保留模型集合”的并集为准，而不是以默认模型为准。也就是说：

```text
如果前端允许选择 raw qlib，则 raw qlib 所需字段必须 ready
如果前端允许选择 fresh qlib，则 fresh qlib 所需字段必须 ready
如果前端允许选择 frozen qlib + orthogonal LTR，则 qlib score 与 orthogonal LTR 特征都必须 ready
如果某个模型的数据未 ready，则该模型在前端必须显示 unavailable / pending / failed reason，不能静默降级
```

执行者必须列出每个数据源：

```text
source_id
provider
required=true/false
required_fields
expected_asof
actual_latest_asof
available_at
coverage_count
coverage_ratio
write_path
failure_reason
retryable=true/false
```

对 e4 frozen qlib + orthogonal LTR 来说，正交数据源默认都是强制项。除非主线文档或既有合同明确允许低频数据 carry-forward，否则不得用前值填补后声称 ready。

### 3.3 模型与策略可运行矩阵

执行者必须冻结前端可选择的模型和策略矩阵。

模型至少按实际保留范围列出：

```text
model_id
model_type: raw_qlib / fresh_qlib / frozen_qlib / ltr_rerank
required_data_sources
required_feature_artifacts
required_signal_artifacts
train_window
allowed_signal_window
can_run_today=true/false
unavailable_reason
```

策略至少列出：

```text
strategy_rule_id
required_inputs: ranking / top50 / current_holdings / prices / fees
compatible_model_types
decision_output_schema
can_run_today=true/false
unavailable_reason
```

自动化日更默认只需要生成：

```text
default_model_id
default_strategy_rule_id
readonly daily latest
```

但后台必须支持：

```text
same target_asof
same ready data snapshot
selected model_id
selected strategy_rule_id
-> rebuild or load ModelSignalArtifact
-> build OrderIntentArtifact
-> build readonly decision response
```

这个按需链路不得重新拉 Yahoo / FinMind / orthogonal 外部数据。

### 3.4 Gate 状态

DataReadinessGate 只能输出以下状态：

```text
all_required_ready
partial_data_pending
no_new_data
provider_failed
validator_failed
deadline_missed_keep_previous_latest
```

只有 `all_required_ready` 可以进入 U1-U3 readonly chain。

其他状态必须：

```text
写 RunRegistry
写 failure / pending manifest
保留 previous readonly latest
前端展示原因
不得生成新的策略结果
不得更新 readonly latest pointer
```

## 4. 阶段安排

本支线压缩为 3 阶段，避免切得过细：

```text
V0 数据源合同与现状审计
V1 Staging 拉取与 DataReadinessGate
V2 自动触发、U 链路串接、前端/API 验收
```

每阶段执行者产出执行报告，审查者审查后才能进入下一阶段。

## 5. Phase V0：数据源合同与现状审计

### 5.1 目标

查清当前 Yahoo、FinMind、正交数据源和既有两小时自动脚本的真实状态，冻结 Phase V 的数据合同。

V0 不允许修改生产链路，不允许触发 provider publish，不允许切 accepted latest。

### 5.2 执行者必做

1. 审计既有入口：

```text
scripts/run_daily_tw_stock_auto_update.py
scripts/run_tw_modular_daily_readonly_update.py
所有 Yahoo / FinMind / crawler / orthogonal refresh 相关脚本
cron / systemd / worker / docker 入口，如存在
```

2. 输出数据依赖表：

```text
raw qlib 只读候选需要哪些数据
fresh qlib 只读候选需要哪些数据
e4 frozen qlib + orthogonal LTR 需要哪些数据
其他前端可选模型需要哪些数据
哪些来自 Yahoo
哪些来自 FinMind
哪些来自本地已冻结 artifact
哪些来自正交数据源
哪些可以缺省
哪些绝对不能缺
```

3. 冻结 staging 输出目录，例如：

```text
data_tw/artifacts/provider_staging/<run_id>/yahoo/
data_tw/artifacts/provider_staging/<run_id>/finmind/
data_tw/artifacts/provider_staging/<run_id>/orthogonal/
data_tw/artifacts/provider_staging/<run_id>/data_readiness_manifest.json
data_tw/artifacts/provider_staging/<run_id>/model_strategy_availability_matrix.json
```

4. 冻结模型/策略矩阵：

```text
前端允许选择哪些 model_id
前端允许选择哪些 strategy_rule_id
默认自动日更组合是哪一个
哪些模型需要正交数据
哪些策略需要 top50 / rank / holdings / price / fee
如果某个模型或策略当日不可运行，前端展示什么 unavailable reason
```

5. 明确禁止触达路径：

```text
provider accepted latest
qlib accepted latest
monitor writes
broker/order writes
Agent action/tool/prompt writes
```

### 5.3 V0 交付

```text
docs/tw_modular_daily_update_productization/PHASEV0_PROVIDER_DATA_CONTRACT_AUDIT_EXECUTION_REPORT_CN.md
```

### 5.4 V0 通过标准

```text
数据源依赖表完整
正交 LTR 所需数据没有遗漏
已保留模型/策略可运行矩阵完整
数据合同以全部可选模型的并集为准，不是只服务默认模型
staging 写入路径明确
accepted latest / monitor / broker/order 禁止边界明确
没有把部分数据可得误判成策略可生成
```

## 6. Phase V1：Staging 拉取与 DataReadinessGate

### 6.1 目标

实现真实数据源 staging 拉取和统一 DataReadinessGate。系统可以“能拉哪个先记录哪个”，但不能“缺数据也继续生成策略”。

### 6.2 执行者必做

1. 新增或改造只写 staging 的拉取入口：

```text
scripts/pull_tw_provider_staging_data.py
scripts/validate_tw_provider_staging_data.py
scripts/build_tw_data_readiness_gate.py
scripts/validate_tw_data_readiness_gate.py
```

2. 拉取逻辑：

```text
每轮尝试 Yahoo / FinMind / orthogonal required sources
成功的数据写 staging artifact
失败的数据写 failure reason
不因单个 provider 失败而覆盖已成功 staging
不使用 partial staging 进入模型链路
```

3. Gate 逻辑：

```text
检查 expected_asof 是否达到 target_asof
检查 required_fields 是否齐全
检查 coverage 是否达到合同门槛
检查 instrument / symbol mapping / universe 有效期
检查 available_at <= decision_cutoff
检查正交特征 PIT 安全
检查所有前端可选模型的 required dependencies
检查所有前端可选策略的 required inputs
输出唯一 gate_status
```

4. 失败关闭：

```text
partial_data_pending / provider_failed / validator_failed 时不得调用 U1-U3
不得更新 readonly latest
必须保留 previous latest
必须写 RunRegistry
```

### 6.3 V1 交付

```text
docs/tw_modular_daily_update_productization/PHASEV1_STAGING_PULL_AND_READINESS_GATE_EXECUTION_REPORT_CN.md
data_tw/artifacts/provider_staging/<run_id>/data_readiness_manifest.json
data_tw/artifacts/provider_staging/<run_id>/model_strategy_availability_matrix.json
data_tw/artifacts/provider_staging/<run_id>/forbidden_action_audit.json
```

### 6.4 V1 通过标准

```text
真实数据源可写入 staging
DataReadinessGate 能区分 ready / pending / failed / no_new_data
partial data 不会进入模型链路
所有 required orthogonal 数据缺失时必定失败关闭
每个可选模型/策略都有 can_run_today 与 unavailable_reason
forbidden_action_audit 证明未切 accepted latest、未写 monitor、未接 broker/order
```

## 7. Phase V2：自动触发、U 链路串接、前端/API 验收

### 7.1 目标

把 V1 的 DataReadinessGate 串到 U 链路前面。每天收盘后每两小时触发一次：如果全部数据 ready，就生成默认模型+默认策略的 readonly latest；如果没有 ready，就展示 pending/failure，并保留上一版 readonly latest。前端切换模型/策略时，后台只复用同一份 ready 数据按需重算下游模型信号/策略决策，不重新抓外部数据。

### 7.2 执行者必做

1. 新增或改造 orchestrator：

```text
scripts/run_tw_real_provider_daily_readonly_update.py
```

建议流程：

```text
create run_id
pull provider staging data
validate staging data
build DataReadinessGate
if gate_status == all_required_ready:
    run U1-U3 readonly chain for default_model_id + default_strategy_rule_id
    validate all artifacts
    update readonly latest pointer
else:
    write run registry
    keep previous readonly latest
```

默认自动触发只运行冻结的默认组合：

```text
default_model_id
default_strategy_rule_id
```

但必须提供按需只读计算入口：

```text
given target_asof + model_id + strategy_rule_id
load existing provider staging / feature artifacts
build or load selected ModelSignalArtifact
build selected OrderIntentArtifact
return readonly decision response
```

按需入口不得从外部 provider 重新抓数据；如果所选模型/策略不可运行，只能返回 unavailable reason。

2. 自动触发：

```text
收盘后每两小时运行
运行窗口、timezone、holiday/非交易日处理必须写清楚
重复运行同一个 target_asof 必须幂等
已经成功生成 readonly latest 后，后续重复运行不得制造冲突结果
```

3. API / 前端：

```text
GET-only API 展示 provider readiness
GET-only API 展示 latest readonly result
GET-only API 展示 model_strategy_availability_matrix
前端可选择模型和策略
切换模型/策略后展示对应 target_asof 的只读决策
切换时如需后台按需重算，只能使用既有 ready artifacts，不能触发外部抓取
前端显示 ready / pending / failed / no_new_data / keep_previous_latest
前端显示每个 provider 的 latest_asof、coverage、failure reason
前端不得触发拉取、发布、下单、monitor 写入
前端不得在本地计算策略，只展示后端标准 artifact/response
```

前端用户第一性原则：

```text
默认只显示最重要的今日结果、数据状态和更新时间
模型/策略选择必须清晰，不把研究候选说成交易建议
不可运行的模型/策略要显示简短原因，例如“正交数据未就绪”或“该策略需要持仓输入”
不要用复杂内部术语堆满界面；详细 manifest 只放在展开区或审计详情
买卖相关展示必须保持 readonly / candidate / not order 语义
```

4. 验收场景：

```text
all_required_ready -> 生成新 readonly latest
selected_model_strategy_ready -> 前端切换后返回对应只读决策
selected_model_strategy_unavailable -> 返回 unavailable reason，不重抓数据
partial_data_pending -> 不生成策略，保留 previous latest
provider_failed -> 不生成策略，保留 previous latest
no_new_data -> 不生成策略或标记 noop，保留 previous latest
validator_failed -> 不生成策略，保留 previous latest
deadline_missed_keep_previous_latest -> 不生成策略，保留 previous latest
```

### 7.3 V2 交付

```text
docs/tw_modular_daily_update_productization/PHASEV2_AUTO_CHAIN_FRONTEND_ACCEPTANCE_EXECUTION_REPORT_CN.md
docs/tw_modular_daily_update_productization/REAL_PROVIDER_DAILY_UPDATE_RUNBOOK_CN.md
docs/tw_modular_daily_update_productization/REAL_PROVIDER_DAILY_UPDATE_REVIEWER_CHECKLIST_CN.md
```

### 7.4 V2 通过标准

```text
每两小时自动触发方案明确且可复跑
ready 场景能进入 U 链路并更新 readonly latest
前端选择不同模型/策略时，后台能复用同一 ready 数据生成对应只读决策
所有可选模型/策略都有 availability matrix
非 ready 场景全部失败关闭并保留 previous latest
前端/API 仍为 GET-only 展示
未触发 provider accepted latest / qlib accepted latest
未写 monitor / broker / order
未修改 Agent prompt/tool/action
```

## 8. 执行者 Prompt

```text
请按 docs/tw_modular_daily_update_productization/PHASEV_REAL_PROVIDER_DATA_READINESS_AND_AUTO_CHAIN_WORK_CN.md 执行 Phase V。

本轮只做真实 Yahoo / FinMind / 正交数据源 staging 拉取、MultiModel DataReadinessGate、以及在 gate 通过后串接既有 U 链路的 readonly 自动日更。数据合同必须覆盖所有前端可选模型和策略的 required dependencies，不能只服务默认模型。自动触发可以只跑默认模型+默认策略；但前端切换 model_id / strategy_rule_id 时，后台必须能复用同一份 ready staging/features/signals 按需生成对应只读决策，且不得重新触发外部数据抓取。不得训练模型、不得切换默认策略、不得 provider publish、不得切 provider accepted latest 或 qlib accepted latest、不得写 monitor config/scan/alerts、不得连接 broker/quick-trade/orders、不得修改 Agent prompt/tool/action。

请先执行 V0，输出：
docs/tw_modular_daily_update_productization/PHASEV0_PROVIDER_DATA_CONTRACT_AUDIT_EXECUTION_REPORT_CN.md

重点列清 e4 frozen qlib + orthogonal LTR、fresh qlib、raw qlib 及其他前端可选模型的真实数据依赖，列清所有可选策略的 required inputs，形成 model_strategy_availability_matrix。还要列清 Yahoo/FinMind/orthogonal required fields、available_at/decision_cutoff 合同、staging 写入路径、以及 forbidden action audit。V0 不得触发真实发布链路；如必须访问外部数据，也只能写 staging 并说明写入路径。
```

## 9. 审查者 Prompt

```text
请审查 docs/tw_modular_daily_update_productization/PHASEV0_PROVIDER_DATA_CONTRACT_AUDIT_EXECUTION_REPORT_CN.md，并对照 docs/tw_modular_daily_update_productization/PHASEV_REAL_PROVIDER_DATA_READINESS_AND_AUTO_CHAIN_WORK_CN.md 判断是否可以进入 V1。

重点审查：
1. Yahoo、FinMind、正交 LTR required data 是否列全；
2. 数据合同是否覆盖所有前端可选模型，而不是只覆盖默认模型；
3. model_strategy_availability_matrix 是否能说明每个模型/策略今天是否可运行及原因；
4. 是否明确 all_required_ready 之前不能进入模型/策略链路；
5. 是否存在 partial data 生成策略的风险；
6. 前端切换模型/策略是否只复用 ready artifacts，未重新触发外部数据抓取；
7. available_at、decision_cutoff、target_asof、decision_for 是否定义清楚；
8. 是否误触 provider accepted latest、qlib accepted latest、monitor、broker/order、Agent；
9. staging artifact 与 readonly latest 是否和正式 provider/latest 解耦；
10. 是否遗漏 universe / instrument 有效期 / symbol mapping / coverage 审计；
11. 前端交互是否清晰、准确、实用，并保持 readonly / not order 语义。

如果发现任何未来数据、accepted latest 切换、monitor/broker/order 写入、部分数据继续生成策略、或只覆盖默认模型导致其他可选模型无法运行的问题，请停止放行并要求执行者修复。
```

## 10. 收口口径

Phase V 收口后，系统应达到：

```text
真实数据可以自动拉到 staging
Yahoo / FinMind / orthogonal required data 全部 ready 后自动生成默认组合只读策略
同一份 ready 数据可以支持前端选择不同模型和策略后按需生成只读决策
数据未齐时不会生成新策略，也不会覆盖 previous latest
前端能解释为什么 ready / pending / failed / no_new_data，以及某个模型/策略为什么 unavailable
链路仍然只读，不碰 provider accepted latest、monitor、broker/order
```

Phase V 收口后仍不代表：

```text
允许真实交易
允许自动下单
允许切换默认策略
允许把 readonly latest 当 provider accepted latest
允许 Agent 触发操作
```
