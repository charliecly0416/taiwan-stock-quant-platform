# Phase M0 合同缺口冻结审查与 Phase M1 工作文档

生成日期：2026-06-17

## 1. 审查结论

Phase M0 审查结论：有条件通过，允许进入 Phase M1。

执行者提交的 `PHASEM0_CONTRACT_GAP_CLOSURE_EXECUTION_REPORT_CN.md` 与 Phase M 主线要求基本一致：M0 所列 12 份新增合同已存在，主文档和索引文档已补充，合同覆盖了数据、特征、价格、日更、自动更新、analysis、前端只读展示、Agent placeholder 和默认候选决策边界。

本轮未要求生产代码实现，也未要求运行新模型、新策略或 replay。因此 M0 的通过标准不是收益、回放结果或 API 行为，而是合同是否足够支撑 M1 的 validator 和 golden samples。

## 2. 审查范围

本次审查参考：

```text
docs/tw_modular_contracts/PHASEM_MODULAR_FOUNDATION_BEFORE_NEW_MODEL_STRATEGY_WORK_CN.md
docs/tw_modular_contracts/PHASEM0_CONTRACT_GAP_CLOSURE_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/PHASEM0_REVIEW_SUPPLEMENT_SUGGESTION_CN.md
docs/tw_modular_contracts/DATA_SOURCE_CONTRACT_CN.md
docs/tw_modular_contracts/DATA_INGESTION_ARTIFACT_CONTRACT_CN.md
docs/tw_modular_contracts/FEATURE_ARTIFACT_CONTRACT_CN.md
docs/tw_modular_contracts/PRICE_STORE_CONTRACT_CN.md
docs/tw_modular_contracts/DAILY_ORCHESTRATOR_CONTRACT_CN.md
docs/tw_modular_contracts/RUN_REGISTRY_CONTRACT_CN.md
docs/tw_modular_contracts/AUTO_UPDATE_ORCHESTRATOR_CONTRACT_CN.md
docs/tw_modular_contracts/ANALYSIS_ARTIFACT_CONTRACT_CN.md
docs/tw_modular_contracts/FRONTEND_READONLY_DISPLAY_CONTRACT_CN.md
docs/tw_modular_contracts/AGENT_READONLY_CONTEXT_CONTRACT_CN.md
docs/tw_modular_contracts/FRONTEND_AGENT_PANEL_CONTRACT_CN.md
docs/tw_modular_contracts/DEFAULT_CANDIDATE_DECISION_CONTRACT_CN.md
docs/tw_modular_contracts/TW_MODULAR_PIPELINE_FUTURE_DEVELOPMENT_GUIDE_CN.md
docs/tw_modular_contracts/READONLY_REPLAY_WINDOW_PRODUCTIZATION_GUIDE_CN.md
docs/README_CN.md
```

## 3. 通过项

### 3.1 合同清单完整

Phase M0 主线要求新增的 12 份合同均已补齐：

```text
DATA_SOURCE_CONTRACT_CN.md
DATA_INGESTION_ARTIFACT_CONTRACT_CN.md
FEATURE_ARTIFACT_CONTRACT_CN.md
PRICE_STORE_CONTRACT_CN.md
DAILY_ORCHESTRATOR_CONTRACT_CN.md
RUN_REGISTRY_CONTRACT_CN.md
AUTO_UPDATE_ORCHESTRATOR_CONTRACT_CN.md
ANALYSIS_ARTIFACT_CONTRACT_CN.md
FRONTEND_READONLY_DISPLAY_CONTRACT_CN.md
AGENT_READONLY_CONTEXT_CONTRACT_CN.md
FRONTEND_AGENT_PANEL_CONTRACT_CN.md
DEFAULT_CANDIDATE_DECISION_CONTRACT_CN.md
```

### 3.2 核心字段覆盖到位

DataSource / DataIngestion 覆盖了 `source_name`、`provider`、`raw_path`、`normalized_path`、`symbol_mapping_version`、`asof_date`、`available_at`、`coverage_audit`、`schema_audit`、`no_provider_publish` 和 `no_accepted_latest_switch`。

FeatureArtifact 覆盖了 `feature_date`、`instrument`、`feature_name`、`feature_value`、`source_data_artifact`、`lookback_window`、`signal_asof`、`available_at`、`pit_policy` 和 `forbidden_future_field_audit`。

PriceStore 覆盖了 `price_date`、`instrument`、`open`、`close`、`adj_factor`、`tradable_flag`、`halt_flag`、`next_day_execution_availability`、`price_source`、`adjustment_policy` 和 `coverage_audit`。

DailyOrchestrator / RunRegistry 覆盖了 `run_id`、`run_asof`、`schedule_interval`、`trigger_reason`、`data_freshness_check_result`、`input_artifacts`、`output_artifacts`、`validation_results`、`latest_pointer_policy`、`failure_mode`、`rollback_policy` 和 `keep_previous_latest_on_failure`。

AutoUpdateOrchestrator 覆盖了两小时自动更新脚本边界，包括 noop、retry、失败关闭、previous latest 保留、全部 validator 通过后才更新 readonly latest，以及禁止 accepted latest / order。

FrontendReadonlyDisplay、AgentReadonlyContext 和 FrontendAgentPanel 覆盖了 GET-only、只读 artifact、禁止请求、禁止买卖/仓位语义、禁止工具调用和 Agent 在 M0-M6 只做 placeholder 的边界。

### 3.3 主线边界表达清楚

合同反复明确以下禁止事项：

```text
不训练新模型
不新增正式策略
不跑新收益结论
不切默认策略
不触发 provider publish / refresh
不切 accepted latest
不改 monitor / broker / quick-trade / order
不改前端 Agent 行为
不新增 Agent tool / action / prompt 能力
```

该边界符合 Phase M “先整理模块化地基，再开发新模型/新策略”的目标。

## 4. 必须带入 M1 的问题

### P2. M0 执行报告证据较简略

M0 执行报告列出了新增合同和未执行事项，但对文件存在性、关键字段覆盖和文档索引更新的检查证据较少。当前审查已补充这部分判断，因此不阻塞 M1。

M1 执行报告不得继续只写“已覆盖”，必须列出：

```text
validator 命令
golden sample 路径
pass/fail 结果
错误码
检查文件数量
未覆盖项
```

### P1. 合同还不是机器可执行 schema

当前合同已经列出 required fields、forbidden fields 和 forbidden actions，但多数仍是文档文本。M1 必须把每份合同落成可执行 validator 口径，避免后续只能做弱字符串检查。

M1 必须明确：

```text
每份合同检查哪个 manifest / schema / audit 文件
required fields 是 manifest 字段、数据列字段、API 字段还是网络请求字段
forbidden fields 是精确字段、前缀匹配、正则匹配还是语义词表
forbidden actions 如何通过 artifact、registry、network log 或 route allowlist 证明
失败时 status code / error code / message 的统一格式
```

M1 validator 不得只做关键词扫描。最低要求是结构化读取 manifest、schema、数据列、audit fixture、network/request audit 和 latest pointer state transition；弱字符串检查只能作为辅助，不得作为唯一合规证据。

### P1. Forbidden Actions 需要结构化审计证据

“不触发 provider publish / refresh”“不切 accepted latest”“不下单”“不写 monitor”不能只依赖文档声明。M1 validator 至少需要一个结构化审计输入，例如：

```text
forbidden_action_audit.json
network_request_audit.json
run_registry_event_log.json
readonly_boundary_audit.json
```

没有审计输入时，validator 应返回 `audit_missing` 或 `not_verifiable`，不得静默通过。

### P1. RunRegistry / latest pointer 状态机需要 golden samples

DailyOrchestrator 和 AutoUpdateOrchestrator 已写明 no_new_data、validator_failed 和 module_failed 必须保留 previous latest，但 M0 还没有机器样例。M1 必须至少覆盖：

```text
success_validators_passed_updates_readonly_latest
no_new_data_noop_preserves_previous_latest
validator_failed_preserves_previous_latest
module_failed_preserves_previous_latest
attempted_provider_accepted_latest_switch_rejected
attempted_order_or_monitor_write_rejected
```

每个样例都要能被 validator 独立判定。

### P1. 既有两小时自动脚本必须映射到合同

M0 已新增 `AUTO_UPDATE_ORCHESTRATOR_CONTRACT_CN.md`，但后续不能只围绕抽象样例闭环。M1/M3 必须明确既有两小时自动更新脚本如何映射到 DailyOrchestrator、RunRegistry 和 AutoUpdateOrchestrator 合同。

M1 至少要提供 fixture 或报告占位，说明后续审计将覆盖：

```text
既有脚本路径
触发周期
no_new_data 行为
fresh_data_success 行为
validator_failed 行为
previous latest 是否保留
是否触发 provider accepted latest
是否触发 monitor / broker / order
```

如果 M1 暂不检查真实脚本，必须在 M1 执行报告中列为 M3 必查项。

### P2. 前端和 Agent 边界需要静态与网络双重检查

FrontendReadonlyDisplay 和 FrontendAgentPanel 合同已写明禁止文案和禁止请求。M1 至少需要静态扫描和网络审计样例，覆盖：

```text
禁止买入/卖出建议、目标仓位、收益保证、实盘执行语义
禁止 POST/PUT/PATCH/DELETE monitor、broker、quick-trade、orders、provider publish、accepted latest
Agent panel 在 M0-M6 不新增 tool/action/prompt 能力
```

若 M1 暂不跑浏览器 E2E，也必须先提供可离线验证的 fixture。

M1 的前端和 Agent 检查必须区分允许的只读回放术语与真实交易语义。例如“readonly replay action table”可以作为标准 artifact 展示；“买入建议”“目标仓位”“自动下单”“实盘已执行”必须失败。

Agent 在 M1 只能做 readonly context fixture、forbidden tool/action/prompt expansion fixture 和 forbidden semantics fixture；不得修改前端 Agent 面板、prompt、tool 权限或动作入口。

### P2. 合同字段命名需要冻结版本

M0 合同中已有 `schema_version`，但还没有统一版本策略。M1 应规定：

```text
初始 schema_version 值
兼容字段新增规则
破坏性变更规则
validator 对 unknown fields 的处理策略
golden sample 与 schema_version 的绑定方式
```

## 5. Phase M1 目标

Phase M1 名称：Validator and Golden Sample Foundation。

M1 只做 validator、schema fixture、golden samples 和静态边界检查；不训练新模型，不新增正式策略，不跑新收益结论，不切默认策略，不触发 provider publish / refresh，不切 accepted latest，不改 broker / quick-trade / order，不改前端 Agent 行为。

M1 的目标是证明 M0 合同不是只读文档，而是能被自动检查：

```text
正确 artifact 可以通过
缺 required fields 会失败
含 forbidden fields 会失败
越权 action audit 会失败
latest pointer 失败状态会保留 previous latest
前端/Agent 越权请求和危险语义会失败
validator 输出统一 JSON
```

## 6. M1 必交付物

### 6.1 Validator 入口

新增或扩展一个统一 validator 入口，建议命名为：

```text
scripts/validate_tw_modular_m_contracts.py
```

要求：

```text
支持 --contract
支持 --artifact-path
支持 --json
支持单合同检查
支持批量 golden sample 检查
失败返回非 0 exit code
JSON 输出包含 ok、contract、status、errors、warnings、checked_files、schema_version
```

`errors` 中每项至少包含：

```text
code
message
path
field
```

fail golden sample 必须声明预期 error code；实际失败码与预期不一致时，测试应失败。

### 6.2 Golden Samples

新增 M1 golden samples，建议目录：

```text
data_tw/golden_samples/modular_contracts/m1/
```

至少包含：

```text
data_source/pass_minimal/
data_source/fail_forbidden_field/
data_ingestion/pass_minimal/
data_ingestion/fail_missing_audit/
feature_artifact/pass_pit_safe/
feature_artifact/fail_future_field/
price_store/pass_minimal/
daily_orchestrator/pass_success/
daily_orchestrator/fail_validator_failed_latest_switched/
run_registry/pass_noop_preserve_previous_latest/
run_registry/fail_provider_accepted_latest_switch/
auto_update/pass_no_new_data_noop/
auto_update/fail_order_action/
analysis_artifact/pass_diagnostic_only/
analysis_artifact/fail_default_strategy_selected/
frontend_readonly_display/pass_get_only/
frontend_readonly_display/fail_forbidden_request/
agent_readonly_context/pass_placeholder/
agent_readonly_context/fail_forbidden_tool_call/
frontend_agent_panel/pass_placeholder/
frontend_agent_panel/fail_prompt_or_tool_expansion/
default_candidate_decision/pass_preserve_current_default/
default_candidate_decision/fail_user_confirmation_missing/
```

每个 sample 目录必须包含可读的 `expected_result.json`，至少声明：

```text
contract
schema_version
expected_ok
expected_status
expected_error_codes
```

### 6.3 回归测试

新增测试，建议覆盖：

```text
tests/unit/test_tw_modular_m_contract_validators.py
```

测试必须证明：

```text
每个 pass sample 通过
每个 fail sample 失败
validator --json 输出可解析
失败样例包含明确 error code
失败样例的实际 error code 等于 expected_result.json
contract regression 覆盖所有 M1 validator
```

### 6.4 文档更新

M1 执行者需要更新：

```text
docs/tw_modular_contracts/PHASEM1_VALIDATOR_AND_GOLDEN_SAMPLE_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/TW_MODULAR_PIPELINE_FUTURE_DEVELOPMENT_GUIDE_CN.md
docs/README_CN.md
```

执行报告必须列出：

```text
validator 命令
golden sample 清单
正例/反例测试结果
错误码
检查文件数量
未覆盖项
是否触发任何禁止动作
如果未检查真实两小时自动脚本，列为 M3 必查项
```

## 7. M1 验收门槛

M1 审查通过必须同时满足：

```text
所有 M0 合同至少有一个 pass sample 和一个 fail sample
validator 能以 --json 输出机器可读结果
每个合同绑定明确 schema_version
required fields、forbidden fields、forbidden actions 至少各有失败样例
每个 fail sample 都失败在预期 error code
validator 不以关键词扫描作为唯一合规证据
forbidden actions 有结构化 audit 证据；缺失时返回 audit_missing 或 not_verifiable
RunRegistry / latest pointer 至少覆盖 success、noop、validator_failed、module_failed
auto-update 样例覆盖 no_new_data、success、validator_failed、forbidden accepted_latest/order
Frontend / Agent 至少覆盖禁止文案或语义、禁止请求、禁止 tool/action 扩权
Frontend / Agent 检查能区分只读回放术语和真实交易语义
Agent 行为、prompt、tool 权限和 action 入口没有被修改
contract regression 纳入所有 M1 validator
测试可本地运行并通过
执行报告没有声称训练新模型、切默认策略、publish provider、切 accepted latest 或下单
```

## 8. 下一步给执行者的工作指令

执行者进入 Phase M1。请按本文件第 6 节和第 7 节完成 validator、golden samples、测试和执行报告。

优先顺序：

1. 先冻结 validator JSON 输出格式和 error code。
2. 再为 12 份合同各建最小 pass / fail golden sample。
3. 再实现 validator 检查 required fields、数据列、forbidden fields、audit 文件存在性、forbidden actions audit、network/request audit 和 latest pointer 状态机。
4. 再补 RunRegistry latest pointer 状态机样例、AutoUpdate 合同映射样例、Frontend/Agent 只读边界样例和单元测试。
5. 最后把 contract regression 纳入 M1 validator 测试集合。

M1 不得修改生产链路行为；如发现必须修改生产代码才能完成 validator，应先在执行报告中说明原因并等待审查，不得顺手改动。
