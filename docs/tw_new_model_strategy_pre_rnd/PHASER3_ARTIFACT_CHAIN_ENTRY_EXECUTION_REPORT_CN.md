# Phase R3 执行报告：Artifact 链路入口确认

生成日期：2026-06-20

## 1. 结论

Phase R3 已完成 artifact 链路入口只读确认。结论：通过，建议进入 R4 审查/下一阶段。

确认结果：

```text
configs/tw_product_artifact_registry.yaml 当前产品入口清晰
新模型入口必须是 ModelSignalArtifact
新策略入口必须是 StrategyRule / StrategyDependency
策略输出只能是 OrderIntentArtifact
Replay 必须是历史模拟、readonly 的 ReplayResultArtifact
ReadonlyStrategySnapshot 是前端只读展示入口
DailyAgentPromptArtifact 是 Agent simple-chat 唯一每日上下文输入
Agent prompt latest、provider/qlib accepted latest、readonly strategy latest、frontend defaults 已区分
```

本阶段只读检查文件和合同，没有训练模型、没有新增策略、没有修改 registry、没有切默认路径、没有触发真实数据、provider publish、accepted latest、monitor、broker/order 或 OpenAI。

运行时 skill 约束：本报告按 project-local `.agents/skills/tw-stock-*` 理解执行；未将 `/home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/` 作为 active skill 来源。

## 2. Registry 当前产品入口

只读检查文件：

```text
configs/tw_product_artifact_registry.yaml
```

当前 registry 声明：

```yaml
schema_version: tw_product_artifact_registry_v1
profile: strict_e4_yz_product
readonly_only: true
```

当前模型入口：

```text
base_model_id = e4_frozen_qlib_2018_2022
treatment_model_id = e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
treatment_display_model_id = e4_frozen_qlib_2023_2025_ltr
```

解释：当前产品只保留 Base Qlib 与 Orthogonal LTR 产品主线。R3 未修改这些默认模型，也未把未来新模型写入默认路径。

当前默认策略：

```text
default_strategy_rule = top50_exit_one_worst_sell
```

解释：当前产品默认策略仍是 top50 exit one worst sell。R3 未修改默认策略，也未新增策略规则。

当前关键 artifact root：

```text
signal_root = data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals
yz2_feature_root = data_tw/artifacts/phase_yz/yz2_orthogonal_feature_package
yz2_execution_price_readiness_root = data_tw/artifacts/phase_yz/yz2_execution_price_readiness
yz2r_execution_price_readiness_root = data_tw/artifacts/phase_yz/yz2r_execution_price_readiness
readonly_strategy_latest = data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
phase_yz_out_root = data_tw/artifacts/phase_yz
```

当前重建来源：

```text
e3_ltr_model = data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_ltr_model.pkl
e3_ltr_training_manifest = data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_training_manifest.json
e2_feature_schema = data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_feature_schema.csv
o2_pit_feature_daily = data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/normalized_feature_daily.csv
o2_summary = data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/phaseo2_summary.json
p3_daily_ltr_rerank_latest_reference_only = data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_latest.json
```

价格源：

```text
normalized_nonempty_dir = qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty
calendar_day = qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt
```

安全 flags：

```text
readonly_only = true
no_training_in_product_context = true
no_provider_publish = true
no_accepted_latest_switch = true
no_monitor_write = true
no_broker_order = true
```

判定：当前产品入口清晰，且 registry 是只读研究产品路径。R3 不把任何缺失项解释为已接入，不修改 registry。

## 3. 新模型入口：ModelSignalArtifact

依据文件：

```text
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
.agents/skills/tw-stock-new-model-onboarding/SKILL.md
```

确认规则：新模型只能通过 `ModelSignalArtifact` 接入。新模型可以有自己的训练、raw output、score 体系或 extension，但进入策略前必须经 ModelAdapter 映射为标准 artifact。

`signals.csv` 必须保留核心字段/语义：

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

R3 特别确认字段语义：

```text
candidate_rank：qlib top50 universe / exit boundary，不得被 LTR 或新模型静默改写。
buy_score：top50 内买入排序分数。
raw_score：原始模型分数，只做溯源，不直接定义策略边界。
score_rank：buy_score 对应的日内排序。
full_qlib_rank：完整 qlib rank，用于 top50 外最差持仓判断。
signal_asof / available_at：PIT 可见性边界。
source_* artifact links：必须能追溯输入、模型、特征来源。
manifest / checksum / validator：用于证明 artifact 可审计，不是动态 payload。
```

新模型不得：

```text
直接改策略
直接改前端默认
直接改 DailyAgentPromptArtifact 默认来源
直接切 provider / qlib accepted latest
直接写 readonly_strategy_latest
default-switch production model
承诺收益、胜率或上涨概率
```

判定：新模型研发入口清晰；第一阶段只应产出/校验 ModelSignalArtifact、registry entry、golden sample、OOS evidence 和 review report，不应接入当前产品默认路径。

## 4. 新策略入口：StrategyRule / OrderIntent / Replay

依据文件：

```text
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
.agents/skills/tw-stock-new-strategy-onboarding/SKILL.md
```

确认规则：新策略只能通过 `StrategyRule / StrategyDependency` 接入。策略模块只消费：

```text
ModelSignalArtifact
PortfolioState
StrategyRuleConfig
```

策略必须先声明 dependency：

```text
required_core_fields
required_capabilities
required_extensions
ranking_usage
max_buy_count
max_sell_count
forbidden_fields
forbidden_actions
diagnostic_only / research_only / production_default
```

策略输出只能是：

```text
OrderIntentArtifact
```

`OrderIntentArtifact` 表达 buy/sell/hold/skip 的只读策略意图，不包含：

```text
execution_date
execution_price
execution_quantity
commission
tax
cash
equity
daily_return
realized_pnl
unrealized_pnl
broker_order_id
provider_publish_status
accepted_latest_status
```

Replay 链路必须是：

```text
StrategyRule / StrategyDependency
-> OrderIntentArtifact
-> ReplayResultArtifact
-> ReadonlyStrategySnapshot
```

`ReplayResultArtifact` 只消费：

```text
OrderIntentArtifact
PriceStore
ExecutionConfig
InitialPortfolioState
```

Replay 可以计算历史模拟的成交、费用、税费、现金、持仓和净值，但不得反向修改信号或策略意图，不得根据收益自动改默认策略。

新策略不得：

```text
产生真实订单
连接 broker
触发 quick-trade
输出 target_position / target_weight
读取未来价格、future return、future label、realized pnl
读取模型私有字段
修改默认策略
修改前端默认展示
provider publish / accepted latest switch
monitor config / scan / alerts write
```

判定：新策略研发入口清晰；第一阶段应只做 StrategyDependency、StrategyRule、OrderIntentArtifact、readonly replay、validator/golden sample/review，不应切入产品默认策略。

## 5. 标准 artifact 链路图

R3 确认后续新模型/新策略标准链路为：

```text
DataSource / PriceStore / FeatureArtifact
-> Model / ModelAdapter
-> ModelSignalArtifact
-> StrategyRule / StrategyDependency
-> OrderIntentArtifact
-> ReplayResultArtifact
-> ReadonlyStrategySnapshot
-> DailyAgentPromptArtifact
-> API / Frontend
```

日更说明文档中对应的小白链路为：

```text
抓取数据
-> 标准化价格与基础数据
-> 生成特征
-> 模型打分与排名
-> 策略生成只读意图
-> 历史模拟 / 模拟账户检查
-> 只读策略快照
-> DailyAgentPromptArtifact
-> 后端 API
-> 前端策略工作台
```

前端/API 入口应保持：

```text
GET /api/tw-stock/current-strategy-context
GET /api/tw-stock/readonly-strategy-snapshot
GET /api/tw-stock/readonly-replay-window-index
GET /api/tw-stock/readonly-replay-window
GET /api/tw-stock/paper-portfolio/latest-decision
GET /api/tw-stock/paper-portfolio/state
POST /api/tw-stock/agent/simple-chat
```

其中唯一允许的 Agent POST 是 simple-chat readonly explanation endpoint，不是交易、monitor、provider 或 latest 操作入口。

## 6. Latest / Default 职责区分

R3 明确区分以下概念：

### 6.1 Frontend display defaults

来源：

```text
configs/tw_product_artifact_registry.yaml
```

职责：声明当前产品默认模型、默认策略、signal root、readonly snapshot latest 和价格源。

不得：在前端、API、脚本或测试中私自硬编码另一套默认模型/策略；不得在新模型/新策略第一阶段直接修改。

### 6.2 Readonly strategy latest

来源：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
```

职责：前端/API 可读的只读策略快照 latest pointer。

规则：只能在 validators 全部通过后由只读发布链路更新；失败时保留 previous latest；它不是 provider accepted latest，也不是 qlib accepted latest。

### 6.3 Agent prompt latest

来源：

```text
data_tw/artifacts/agent_daily_prompt/latest.json
```

职责：Agent simple-chat 每日上下文 pointer。

合同明确：它仅是 Agent prompt latest pointer，不是 provider accepted latest，不是 qlib accepted latest，不得触发 provider publish 或 accepted latest switch。当前 Agent prompt latest publish 默认关闭/dry-run，未来 release 需单独验收。

### 6.4 Provider / qlib accepted latest

职责：数据/qlib provider 层的 accepted latest 选择。

R3 判定：这是高风险生产/数据入口，不属于新模型/新策略第一阶段，也不属于 readonly strategy latest 或 Agent prompt latest。legacy provider publish / accepted latest 代码可存在，但默认路径必须不可达，并由显式非默认 gate 保护。

### 6.5 PaperPortfolio state

职责：simulation-only 模拟账户状态。它可以写模拟账本，但不连接真实 broker、不提交真实订单、不代表 target_position 或 target_weight。

## 7. 非阻塞稳定化点

R3 确认以下事项仍需未来稳定化，但不阻塞 artifact 链路入口确认：

```text
生产 source artifacts 物化链路仍需后续明确和稳定化。
Agent prompt latest publish 默认关闭/dry-run，需要在未来 release 节点单独验收。
legacy provider publish / accepted latest 代码仍存在，但当前默认路径不可达。
新模型/新策略第一阶段不得直接切当前产品默认路径。
project-local skills 仍需纳入最终版本冻结提交范围。
当前运行时仍可能显示 archive 旧 skill metadata；后续执行节点必须显式以 project-local skills 为准。
当前数据链路说明是小白友好解释，不替代工程字段清单；真实研发前还应对实际 Feature/ModelSignal/StrategyDependency/OrderIntent/ReadonlySnapshot/DailyPrompt 样例字段做精确核对。
```

新增观察：R3 只确认入口与职责，不验证每个生产 source artifact 的现时存在性，也不生成任何新 artifact；如未来研发需要使用具体 artifact，必须按对应合同读取 manifest/latest pointer 并运行 validator，缺失时列为缺口，不能用动态 payload 替代。

## 8. 只读安全边界

本次 R3 只执行了文件读取和文本搜索：

```text
sed 读取 registry、skills、合同、数据链路说明
rg 搜索 latest/default/artifact 术语
```

未执行或触发：

```text
训练新模型
新增策略规则
修改默认模型或默认策略
修改前端默认展示
真实数据拉取
provider refresh / publish
accepted latest switch
monitor config / scan / alerts 写入
broker / quick-trade / order
target_position / target_weight 写入
OpenAI key 读取
真实 OpenAI smoke
生成或发布 artifact/latest pointer
```

安全判定：通过。R3 没有把缺失产物伪装成已接入，也没有使用动态服务 payload 替代 artifact chain evidence。

## 9. 是否建议进入 R4

执行侧建议：可以提交 R3 审查，并在审查通过后进入 R4。

进入 R4 或正式新模型/新策略研发前，建议保留以下启动提示：

```text
1. 以 project-local .agents/skills/tw-stock-* 为准，不使用 archive 旧 skills。
2. 新模型先走 ModelSignalArtifact，不改默认模型、不改前端、不进 Agent prompt 默认来源。
3. 新策略先走 StrategyDependency / StrategyRule / OrderIntentArtifact / readonly ReplayResultArtifact，不改默认策略、不输出真实订单或目标仓位。
4. 所有 latest/default 区分清楚：Agent prompt latest、readonly strategy latest、provider/qlib accepted latest、frontend defaults 不是同一个入口。
5. 任一 artifact、manifest、latest pointer、source link 或 validator 缺失时，应停在缺口报告，不得伪造动态 payload。
```
