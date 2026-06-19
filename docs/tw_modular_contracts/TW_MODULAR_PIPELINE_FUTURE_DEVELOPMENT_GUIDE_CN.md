# 台湾股票模块化研究管线未来开发规范

生成日期：2026-06-16


## 0. 2026-06-18 更新：Product Artifact Registry 与开发者入口

当前项目已新增产品级 artifact registry：

```text
configs/tw_product_artifact_registry.yaml
```

它集中声明当前产品默认模型、默认策略、YZ signal root、readonly snapshot latest、E2/E3/O2 重建源和价格源。后续新增模型、策略、前端展示、paper portfolio 或日更链路时，不得再在代码里新增另一套默认模型、默认策略或核心路径常量。

开发者应优先阅读：

```text
docs/tw_modular_contracts/TW_PROJECT_MODULE_MAP_AND_FLOW_CN.md
docs/tw_modular_contracts/TW_DEVELOPER_TEST_AND_EXPERIMENT_PLAYBOOK_CN.md
```

本文档仍作为总规范，但具体开发时以上两份文档是更直接的入口。

## 1. 目的

本文档是后续新增数据、特征、模型、策略、回放、分析和生产接入时的总入口规范。任何新增能力都必须先判断自己属于哪个模块，再遵守对应合同和 validator 要求。

核心目标：

- 保持模块边界清楚；
- 不把模型私有字段直接暴露给策略；
- 不把策略意图和真实成交混在一起；
- 不把研究 replay 结果直接接入前端、日更或交易链路；
- 支持未来更多模型、策略和数据源以受控方式扩展；
- 所有扩展都能被 manifest、registry、dependency 和 validator 追踪。

## 2. 模块边界

标准链路：

```text
DataSource / PriceStore / FeatureArtifact
  -> Model / ModelAdapter
  -> ModelSignalArtifact
  -> StrategyRule
  -> OrderIntentArtifact
  -> ReplayExecution
  -> ReplayResultArtifact
  -> Analysis / Review
```

各模块只允许消费自己上游的标准产物，不允许跨层读取私有文件。

| 模块 | 标准输入 | 标准输出 | 禁止事项 |
| --- | --- | --- | --- |
| 数据源 | 外部或本地原始数据 | 标准化数据或 PriceStore | 不得切换 accepted latest，不得 publish 到生产链路 |
| 特征 | 标准化数据、PriceStore | FeatureArtifact | 不得包含未来收益、训练 label、成交结果 |
| 模型 | FeatureArtifact、训练配置 | 模型产物或 raw score | 不得直接供策略读取私有列 |
| 模型适配器 | 模型产物、raw score | ModelSignalArtifact | 不得训练、调参、改收益筛选 |
| 策略 | ModelSignalArtifact、PortfolioState、StrategyRuleConfig | OrderIntentArtifact | 不得读取未来价格、成交、净值、模型私有列 |
| 回放 | OrderIntentArtifact、PriceStore、ExecutionConfig | ReplayResultArtifact | 不得改信号排序、不得反向修改策略意图 |
| 分析 | 标准 artifact、审计文件 | 报告 | 不得作为生产接入或默认策略切换的直接依据 |
| 生产接入 | 另开阶段审查 | 受控只读或发布链路 | 不得绕过 review、validator 和安全边界 |

## 3. 必须遵守的合同

新增能力必须至少引用以下相关合同：

```text
docs/tw_modular_contracts/DATA_SOURCE_CONTRACT_CN.md
docs/tw_modular_contracts/DATA_INGESTION_ARTIFACT_CONTRACT_CN.md
docs/tw_modular_contracts/FEATURE_ARTIFACT_CONTRACT_CN.md
docs/tw_modular_contracts/PRICE_STORE_CONTRACT_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
docs/tw_modular_contracts/STRATEGY_DEPENDENCY_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/DAILY_ORCHESTRATOR_CONTRACT_CN.md
docs/tw_modular_contracts/RUN_REGISTRY_CONTRACT_CN.md
docs/tw_modular_contracts/AUTO_UPDATE_ORCHESTRATOR_CONTRACT_CN.md
docs/tw_modular_contracts/ANALYSIS_ARTIFACT_CONTRACT_CN.md
docs/tw_modular_contracts/FRONTEND_READONLY_DISPLAY_CONTRACT_CN.md
docs/tw_modular_contracts/AGENT_READONLY_CONTEXT_CONTRACT_CN.md
docs/tw_modular_contracts/FRONTEND_AGENT_PANEL_CONTRACT_CN.md
docs/tw_modular_contracts/DEFAULT_CANDIDATE_DECISION_CONTRACT_CN.md
docs/tw_modular_contracts/EXTENSIBLE_CONTRACT_CAPABILITY_DESIGN_CN.md
```

如果新增模块目前没有合同，必须先新增合同和 validator，再产出研究结果。不得先把新产物接入策略、回放、前端、日更或交易链路。

## 4. Core Contract 不可变规则

`ModelSignalArtifact` 的核心字段不得被 extension 改写语义：

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

核心语义：

- `candidate_rank` 只表示 qlib top50 universe / exit boundary；
- `buy_score` 只表示候选池内买入排序；
- `full_qlib_rank` 只表示完整 qlib rank，用于 top50 外最差持仓判断；
- `signal_asof` 和 `available_at` 必须支持 PIT 可见性检查；
- `date + instrument` 是同一个 signal artifact 内的唯一键。

未来模型可以有不同输入、不同 raw output、不同 horizon、不同 score 体系，但进入策略前必须通过 adapter 映射成标准 core fields 或显式 extension fields。

## 5. 扩展字段规范

新增字段不得直接塞进 core fields，也不得让策略隐式读取。

所有 optional extension fields 必须满足：

- 字段名使用 `ext_{domain}_{name}`；
- 不覆盖 core field；
- 不匹配 forbidden field / prefix；
- 在 manifest 的 `extensions.fields` 中声明；
- 声明 `dtype`、`semantic_role`、`availability_policy`、`producer`、`allowed_consumers`、`ranking_allowed`、`required_for_core_replay`、`description`；
- 如果策略要消费，必须在 strategy dependency YAML 中显式声明；
- 默认不得进入 ranking、sell boundary、order sizing、risk-off 或收益结论。

允许示例：

```text
ext_sector_code
ext_industry_code
ext_risk_volatility_score
ext_liquidity_bucket
ext_horizon_5d_score
ext_horizon_20d_score
ext_ensemble_score
```

禁止示例：

```text
future_return_10d
forward_return_5d
label_top_heavy
realized_pnl
target_position
execution_price
phasee6_branch_a_fresh_ltr_score
qlib_rank_raw
```

## 6. Capability 与 Registry 规范

新增模型、策略、extension、validator 或 analysis smoke，必须在受控 registry 中登记：

```text
configs/tw_modular_registry.yaml
```

Registry 只用于声明合同、能力和依赖，不触发训练、不触发 replay、不切换默认策略。

新增 capability 必须是稳定语义，不得写成临时实验名或收益承诺。

允许示例：

```text
core_signal_v1
candidate_boundary:qlib_top50
buy_ordering:buy_score_desc
full_rank_exit:full_qlib_rank
supports_sector_exposure
pit_available_at_checked
```

禁止示例：

```text
best_return_model
high_win_rate_candidate
buggy_rule_as_strategy
production_ready_without_review
```

如果 dependency 只适用于 smoke artifact，必须使用类似 `applies_to_artifact_names` 的范围限制，并在报告中说明 skipped 不等于失败，也不等于生产放行。

## 7. 新数据源接入规范

新增数据源必须先回答：

- 数据是价格、财报、因子、行业分类、另类数据还是交易相关数据；
- 数据是否有明确 as-of / publish time；
- 数据是否可能包含未来信息；
- 数据是否会进入训练、信号、策略、回放或只做分析；
- 数据是否会影响 accepted latest、provider publish、前端或日更。

最低要求：

- 产出数据字典和字段语义；
- 产出 PIT 可见性说明；
- 产出 coverage audit；
- 明确缺失值、复权、停牌、退市、代码映射规则；
- 若进入模型或策略，必须通过标准 FeatureArtifact 或 ModelSignal extension；
- 若只是 analysis，必须标记 analysis-only 或 smoke-only；
- 不得在同一阶段切换 accepted latest 或 provider publish。

新数据源不得直接被策略模块读取。策略只能读取 `ModelSignalArtifact` core fields 或已声明 extension fields。

## 8. 新特征接入规范

新增特征必须：

- 记录输入数据源和版本；
- 记录特征计算窗口；
- 记录 as-of / available_at 规则；
- 禁止使用 future return、forward return、label、真实成交、未来持仓；
- 明确是否进入模型训练、模型推理、analysis 或 extension；
- 产出 feature schema 和 forbidden field audit。

如果特征需要被策略直接消费，不得绕过模型信号合同，必须作为 `ext_*` 字段进入 `ModelSignalArtifact`，并由 strategy dependency 显式声明。

## 9. 新模型接入规范

新增模型可以有自己的输入、训练方式和 raw output，但策略不可直接读取模型私有产物。

最低接入流程：

1. 定义模型名称、模型族和训练/推理边界。
2. 记录训练数据、特征版本、时间窗口和 PIT 政策。
3. 产出模型 raw score 或预测结果。
4. 编写 ModelAdapter，输出 `ModelSignalArtifact`。
5. 在 manifest 中声明 core capabilities 和 extension fields。
6. 运行 signal validator。
7. 如需策略消费 extension，新增 strategy dependency。
8. 运行 registry regression。
9. 由审查文档确认是否允许进入 replay。

模型适配要求：

- `candidate_rank`、`buy_score`、`full_qlib_rank` 的来源必须清楚；
- LTR 或 rerank 模型默认只能重排 qlib top50 内买入顺序；
- 如果模型希望改变 universe、sell boundary 或多 horizon 决策，必须新增合同版本和独立审查；
- 不得把 legacy 私有列名直接作为策略输入；
- 不得根据 OOS replay 收益自动选择模型作为默认。

## 10. 新策略接入规范

新增策略必须先写 dependency YAML，再写策略逻辑。

最低要求：

- 新增 `configs/strategy_dependencies/{strategy_rule}.yaml`；
- 声明 `required_core_fields`；
- 声明 `required_capabilities`；
- 声明 `required_extensions` 或 `optional_extensions`；
- 声明 `ranking_usage`；
- 声明 `max_buy_count`、`max_sell_count`；
- 声明 forbidden fields 和 forbidden actions；
- 若是诊断规则，必须标记 `diagnostic_only: true` 和 `not_valid_strategy_evidence: true`；
- 策略输出只能是 `OrderIntentArtifact`。

策略禁止：

- 读取模型私有文件；
- 读取未来价格、future return、label；
- 读取 replay 的收益、净值、成交作为排序依据；
- 根据 `model_family` 静默改变 sell boundary；
- 输出真实成交价、成交日期、现金、净值、手续费、broker order id；
- 自行切换默认策略或接入产品展示。

## 11. 新回放接入规范

新增回放规则或执行设置必须只消费：

```text
OrderIntentArtifact
PriceStore
ExecutionConfig
InitialPortfolioState
```

最低要求：

- 产出 `ReplayResultArtifact` 必需文件；
- 记录 execution price 规则；
- 保证 `execution_date > signal_date`；
- 缺失价格必须 skip 或 audit；
- 产出 coverage audit、position integrity audit、forbidden field audit；
- 不反向修改 OrderIntent；
- 不修改 signal ranking；
- 不根据收益自动切换默认策略。

回放结果只代表研究回放，不自动代表可交易、可上线或可展示。

## 12. Analysis / Smoke 规范

Analysis-only 或 smoke-only 产物必须显式标记：

```text
quality_status: smoke_only 或 analysis_only
no_replay: true
no_strategy_return_conclusion: true
not_valid_strategy_evidence: true 或在报告中说明不能作为策略收益证据
```

Smoke 可以验证 extension、validator、registry skip 逻辑，但不得被解释为真实 sector、真实 alpha、真实策略或生产能力。

## 13. Validator 与测试要求

新增能力至少要补齐对应 validator：

- signal validator：检查 core fields、extension schema、forbidden fields、PIT、唯一键；
- strategy dependency validator：检查 required fields、capabilities、extension、forbidden actions；
- order intent validator：检查 action 值域、每日买卖上限、无成交和净值字段；
- replay validator：检查输出文件、execution_date、持仓完整性、coverage、forbidden fields；
- registry regression：检查所有登记 artifact / dependency 的兼容性。

每个新增能力至少需要：

- 一个正例；
- 一个负例；
- 一条可复跑命令；
- 一份 execution report；
- 一份 review handoff；
- 审查者给出的 review / suggestion 文档。

## 14. 生产、前端、日更和交易边界

研究阶段默认禁止：

- 修改默认策略；
- 修改前端展示；
- 修改日更 orchestrator；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker、quick-trade 或 order；
- 把 replay result 当成真实交易建议；
- 把 diagnostic-only 规则当成有效策略证据。

如果后续要进入生产、前端或日更，必须另开阶段，至少完成：

- final state / release bundle；
- 只读 safety boundary review；
- 数据新鲜度和 accepted latest 政策审查；
- 前端文案和网络请求审查；
- 失败回滚方案；
- 产品语义审查，明确是研究展示、模拟回放还是真实交易链路。


Phase M 之后，日更和两小时自动更新能力必须遵守 `DAILY_ORCHESTRATOR_CONTRACT_CN.md`、`RUN_REGISTRY_CONTRACT_CN.md` 和 `AUTO_UPDATE_ORCHESTRATOR_CONTRACT_CN.md`：

- 自动脚本只做调度、状态、重试、validator 汇总、RunRegistry 写入和 readonly latest pointer 决策；
- 抓取、标准化、特征、模型信号、策略意图、只读 snapshot 和 replay window 必须由标准模块产出 artifact；
- no_new_data 不得刷新 latest pointer；
- validator_failed 必须保留 previous latest；
- readonly latest pointer 不等于 provider accepted latest，也不等于 qlib accepted latest。

前端展示必须遵守 `FRONTEND_READONLY_DISPLAY_CONTRACT_CN.md`：

- 只依赖 GET-only readonly API；
- 不在前端本地 replay、重算排序或计算策略；
- 不展示买卖建议、目标仓位、收益承诺或实盘执行语义。

前端 embedded Agent 在 M0-M6 只按 `AGENT_READONLY_CONTEXT_CONTRACT_CN.md` 和 `FRONTEND_AGENT_PANEL_CONTRACT_CN.md` 做边界占位：

- 不修改 Agent 行为、prompt、tool 权限或 action 入口；
- 不新增 Agent tool/action；
- 如需功能变更，必须另开 Agent 专项主线。

## 15. 审查工作流

每次新增能力建议采用以下顺序：

1. 需求说明：说明新增的是数据、特征、模型、策略、回放、analysis 还是生产接入。
2. 合同定位：列出需要遵守的合同和是否需要新增合同。
3. 产物设计：定义 manifest、schema、audit、registry、dependency。
4. 实现：只改本阶段允许范围。
5. 正负例：至少证明能放行正确产物、拒绝错误产物。
6. Regression：跑 registry / validator / unit tests。
7. Execution report：执行者写清楚改了什么、没改什么、验证结果和残余风险。
8. Review handoff：交给审查者复核。
9. Review suggestion：审查者必须产出建议文档，结论为通过、修复后通过或拒绝。
10. 下一阶段：只有审查通过后才能进入 replay、生产接入或更大范围修改。

## 16. 开发前自检清单

新增数据：

- 是否有 as-of / available_at；
- 是否有 coverage audit；
- 是否会污染 future label；
- 是否只是 analysis-only；
- 是否会触发 publish 或 accepted latest。

新增特征：

- 是否只用当时可见数据；
- 是否有 schema；
- 是否有 forbidden field audit；
- 是否需要作为 `ext_*` 暴露。

新增模型：

- 是否有 ModelAdapter；
- 是否输出标准 `ModelSignalArtifact`；
- 是否声明 capabilities；
- 是否有 extension schema；
- 是否通过 signal validator。

新增策略：

- 是否先写 dependency YAML；
- 是否只读取 core / declared extension；
- 是否输出 `OrderIntentArtifact`；
- 是否限制 buy/sell action 数；
- 是否没有成交、现金、净值和 broker 字段。

新增回放：

- 是否只消费 order intent；
- 是否记录 next-day execution；
- 是否有 coverage 和 position integrity audit；
- 是否没有反向修改信号或策略；
- 是否没有自动切换默认策略。

新增生产接入：

- 是否另开阶段；
- 是否只读优先；
- 是否完成 safety boundary review；
- 是否没有 broker/order/quick-trade；
- 是否有回滚和禁用方案。

## 18. Phase M1 Validator 与 Golden Sample

Phase M1 已新增统一合同 validator：

```bash
python scripts/validate_tw_modular_m_contracts.py --run-golden --json
python scripts/validate_tw_modular_m_contracts.py --contract <contract> --artifact-path <sample_dir> --json
```

M1 schema version 冻结为 `m1.0.0`。新增或修改合同样例时必须同步 `expected_result.json`，并保证失败样例的实际 error code 与预期完全一致。

Golden samples 位于：

```text
data_tw/golden_samples/modular_contracts/m1/
```

Contract regression 已接入 M1 golden validator。M1 仍不允许训练模型、跑新 replay、切默认策略、publish provider、切 accepted latest、改 monitor/broker/order 或修改前端 Agent 行为。

## 19. Phase M2 Registry 与 Onboarding Template

Phase M2 已新增 registry validator：

```bash
python scripts/validate_tw_modular_registry_m2.py --json
```

新增能力必须先登记到 registry，并满足以下字段：

```text
artifact_type
schema_version
contract_doc
validator
golden_sample
capabilities
dependencies
allowed_consumers
forbidden_consumers
production_allowed=false
diagnostic_only
owner_or_stage
```

模板入口位于：

```text
docs/tw_modular_contracts/templates/
```

新增数据、特征、模型、策略、replay window、frontend readonly display、Agent readonly context、执行报告和审查报告都必须从模板开始，不得临时散写接入说明。Agent readonly context 在 M0-M6 仍然只能是 placeholder，必须保留 `not_in_m0_m6_implementation_scope=true` 和 `future_agent_phase_required=true`。

### M2R Registry 语义修复要求

M2R 后，registry entry 不得只证明文件存在。每个 entry 必须满足：

```text
entry.artifact_type == golden_sample.expected_result.contract
validator --list-contracts --json 支持该 contract
validator --contract <contract> --artifact-path <golden_sample> --json 实际通过
```

如果未来确实需要 alias，必须显式声明 `validator_contract` 和 `contract_alias_reason`，并由 validator 检查；不得用无关 artifact 的 pass sample 替代同类合同验证。

Agent readonly context 的 `response_semantics_audit.forbidden_semantics_count` 必须为 0；大于 0 时 validator 必须失败。

## 20. Phase M3 Daily Orchestrator 与 Latest Pointer

Phase M3 已新增 daily orchestrator / run registry / auto update 的只读 dry-run validator：

```bash
python scripts/validate_tw_daily_orchestrator_m3.py --run-golden --json
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
```

M3 schema version 冻结为 `m3.0.0`，golden samples 位于：

```text
data_tw/golden_samples/modular_contracts/m3/
```

M3 的 latest pointer 规则：

```text
no_new_data 不更新 readonly latest pointer
fresh_data_success 只有 validators 全部通过后才提交 proposed readonly latest
validator_failed / module_failed 必须保留 previous latest
readonly latest pointer 不等于 provider accepted latest，也不等于 qlib accepted latest
```

既有两小时脚本 `scripts/run_daily_tw_stock_auto_update.py` 已由 M3R 改为默认 M3 readonly contract mode。Legacy Yahoo/Scrapling refresh、provider publish 和 accepted latest 切换代码可以保留，但必须由显式非默认 `--enable-legacy-provider-publish` gate 保护；validator 只有在证明默认路径不可达时才允许通过。脚本审计可以记录 legacy warning，但不得出现 default provider/latest reachable、broker/order runtime pattern 或 monitor write runtime pattern。

统一回归必须包含 M3 输出：

```text
m3_daily_orchestrator_validation.json
m3_daily_script_audit.json
```


## 21. Phase M4 Frontend Readonly Display

Phase M4 已新增前端只读展示 validator：

```bash
python scripts/validate_tw_frontend_readonly_m4.py --json
```

统一回归已接入 M4：

```bash
python scripts/run_tw_modular_contract_regression.py --json
```

M4R 后 frontend readonly validator schema version 为 `m4.0.1`。回归输出包括：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/m4_frontend_readonly_validation.json
```

前端只读展示组件边界：

```text
frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue
frontend/src/views/tw-stock-monitor/components/ReadonlyReplayWindowPanel.vue
frontend/src/views/tw-stock-monitor/components/ReplayAuditDetail.vue
```

M4 主视图必须优先展示用户复盘字段：

```text
model
strategy
legal_window
net_return
max_drawdown
action_count
fee_tax
coverage_status
audit_status
```

工程追溯字段必须进入折叠或二级审计详情，不得压过主指标：

```text
source_manifest
checksum
schema_version
window_index
run_id
```

前端改动后至少复跑：

```bash
python scripts/validate_tw_frontend_readonly_m4.py --json
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
python scripts/run_tw_modular_contract_regression.py --json
cd frontend && node tests/unit/tw-stock-readonly-strategy-snapshot-check.mjs
cd frontend && node tests/unit/tw-stock-readonly-replay-window-check.mjs
cd frontend && corepack pnpm build
```

如果修改 readonly strategy snapshot 或 readonly replay window 交互，还必须复跑对应 E2E，并保留 desktop/mobile、audit collapsed/expanded 截图：

```bash
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:5173 node tests/e2e/tw-stock-readonly-strategy-snapshot-readonly.mjs
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:5173 node tests/e2e/tw-stock-readonly-replay-window-readonly.mjs
```

M4 禁止事项：

```text
不得调用 POST/PUT/PATCH/DELETE 的 replay/strategy readonly workflow
不得显示或暗示下单、目标仓位、自动交易、一键交易、保证收益、胜率承诺
不得暴露 --enable-legacy-provider-publish
不得暴露 TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH
不得触发 provider refresh / publish
不得切 accepted latest
不得修改 monitor config / scan / alerts
不得连接 broker、quick-trade 或 orders
不得扩展 Agent prompt/tool/action
不得继续修改 scripts/run_daily_tw_stock_auto_update.py；如必须触碰，应另开 M3S/M3RR
```

执行报告必须包含 `Frontend user-first acceptance and safety evidence`，并列出组件边界、primary/audit 字段映射、截图路径、GET-only network audit artifact、forbidden request count、forbidden text/semantics scan、legacy gate 未暴露证明、Agent untouched/placeholder-only 证明、frontend build 和 E2E 结果。


### M4R GET-only 修复要求

M4R 后，`/tw-stock-monitor` 的 M4 readonly acceptance path 必须保持 GET-only。以下 entrypoints 不得调用 `loadRankTechPortfolioPanel`、`loadPortfolioReplay`、`runTwStockPortfolioReplay`、`runTwStockReadonlyBacktest` 或 `runReadonlyBacktest`：

```text
mounted
refreshAll
loadReadonlyStrategySnapshot
loadReadonlyReplayWindowIndex
loadReadonlyReplayWindow
handleReadonlyReplayWindowSelect
```

旧 replay/strategy POST wrapper 如果保留，只能作为显式人工研究操作，不得进入页面初始化、顶部刷新或 readonly panel 查询/刷新路径。E2E 必须输出 network audit artifact，并证明：

```text
forbidden_request_count=0
replay_strategy_write_count=0
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
ops_provider_publish_refresh_accepted_latest_request_count=0
broker_quick_trade_orders_request_count=0
```

M4R network audit 汇总入口：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/m4_frontend_readonly/network_audit.json
```

## 22. Phase M5 Dry-run Onboarding Smoke

Phase M5 新增 smoke-only onboarding validator：

```bash
python scripts/validate_tw_modular_m5_smoke.py --run-golden --json
python scripts/validate_tw_modular_m5_smoke.py --artifact-path data_tw/golden_samples/modular_contracts/m5/onboarding_smoke/pass_minimal --json
```

M5 schema version 为 `m5.0.0`，golden samples 位于：

```text
data_tw/golden_samples/modular_contracts/m5/onboarding_smoke/
```

统一回归已接入 M5：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/m5_onboarding_smoke_validation.json
```

M5 smoke artifact 和 registry entry 必须声明：

```text
smoke_only=true
not_valid_strategy_evidence=true
no_replay_return_conclusion=true
not_default_candidate=true
production_allowed=false
diagnostic_only=true
```

M5 只能验证 onboarding 流程：

```text
registry entry
contract reference
validator pass/fail
strategy dependency check
ModelSignalArtifact compatibility check
OrderIntentArtifact compatibility check, if applicable
no replay return conclusion
no default switch
```

M5 禁止：

```text
真实训练
调参或搜索真实模型
正式策略收益结论
可被解释为 alpha/return evidence 的 replay
default candidate 或默认策略切换
provider refresh / publish
accepted latest switch
monitor config / scan / alerts write
broker / quick-trade / orders
前端默认展示接入
production latest pointer 写入
Agent prompt/tool/action 扩展
scripts/run_daily_tw_stock_auto_update.py 修改
```

新增 smoke strategy dependency 必须使用 `applies_to_artifact_names` 限定到 dummy smoke artifact，确保现有正式 signal manifest 在统一回归中为 skipped，而不是参与正式策略验证。

## 23. Phase M6 Final Acceptance 与后续入口

M6 最终验收入口：

```text
docs/tw_modular_contracts/MODULAR_FOUNDATION_FINAL_ACCEPTANCE_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md
docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md
```

M6 后，真实新模型/新策略开发必须作为新主线开启，并至少复跑：

```bash
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
python scripts/validate_tw_frontend_readonly_m4.py --json
python scripts/validate_tw_modular_m5_smoke.py --run-golden --json
```

后续任何开发不得绕过以下硬门：

```text
ModelSignalArtifact 标准 core fields
StrategyDependency 显式声明
OrderIntentArtifact 边界
registry production_allowed=false 默认
validator positive/negative golden samples
frontend readonly GET-only
M3R daily legacy provider/latest 默认不可达
Agent prompt/tool/action 冻结，除非另开 Agent 专项
```

## 24. 结论

后续开发可以扩展输入和输出，但不能绕过模块合同。新模型、新策略、新数据源的差异应体现在 adapter、extension schema、capability、dependency 和 validator 中，而不是体现在跨模块私读、字段复用或隐式语义替换中。

只有通过合同校验、registry regression、正负例验证和审查文档的新增能力，才允许进入下一阶段研究或生产接入评估。
