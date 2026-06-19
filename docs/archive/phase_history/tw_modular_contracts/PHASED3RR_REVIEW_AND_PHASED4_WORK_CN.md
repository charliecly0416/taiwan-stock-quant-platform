# Phase D3RR 审查与 Phase D4 工作文档

生成日期：2026-06-17

## 1. D3RR 审查结论

D3RR 通过，可以进入 D4。

结论：

```text
D3RR forward-chain source proof: pass
OrderIntentArtifact forward generation: pass
ReplayResultArtifact execution from OrderIntentArtifact: pass
five-rule/five-method/2026_ytd parity: pass
validator negative gates: pass
readonly safety boundary: pass
next phase: D4 readonly standard artifact consumption / product integration
```

D3RR 修复了 D3R 的核心问题：当前链路不再从旧 replay `actions/snapshots` 反向合成 OrderIntent，也不再复制旧 replay frames 伪装成新的 ReplayResult。新的证据链为：

```text
ModelSignalArtifact + PortfolioState + StrategyRuleConfig
  -> StrategyDecisionEngine
  -> OrderIntentArtifact
  -> ReplayExecutionEngine
  -> ReplayResultArtifact
  -> parity vs legacy baseline
```

旧 `formal_replay_manifest.json` 只用于最终 parity 对比，不作为 OrderIntent 或 ReplayResult 的生成来源。

## 2. 审查对象

handoff：

```text
docs/tw_modular_contracts/PHASED3RR_FORWARD_CHAIN_REPAIR_REVIEW_HANDOFF_CN.md
```

执行报告：

```text
docs/tw_modular_contracts/PHASED3RR_FORWARD_CHAIN_REPAIR_EXECUTION_REPORT_CN.md
```

核心实现：

```text
scripts/run_tw_modular_order_intent_replay_parity.py
scripts/validate_tw_modular_order_intent_replay_parity.py
tests/unit/test_tw_modular_order_intent_replay_parity.py
```

D3RR parity manifest：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T062610Z/manifest.json
```

D3RR replay result manifest：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T062610Z/order_intent_replay_result/manifest.json
```

## 3. Findings

未发现阻塞问题。

### Low: 负向测试存在 pandas FutureWarning

单测通过，但 `test_rejects_action_rows_with_blank_decision_fields_when_required` 中故意把 rank 数值列置为空字符串，触发 pandas dtype FutureWarning。

影响较低：

```text
35 passed
3 warnings
```

建议后续在测试里先把待篡改列 cast 为 object 或使用兼容的空值写法，避免未来 pandas 版本升级后把 warning 变成错误。该问题不影响 D3RR 审查结论。

## 4. 已通过项

### 4.1 Forward chain source proof

代码审查确认：

```text
scripts/run_tw_modular_order_intent_replay_parity.py
```

当前 OrderIntent 行包含：

```text
generation_source=strategy_decision_engine
not_generated_from_replay_actions=true
not_generated_from_replay_snapshots=true
candidate_rank / buy_rank / full_qlib_rank / intent_reason / source_signal_asof / source_available_at
```

ReplayResult manifest 包含：

```text
generated_by=replay_execution_engine
execution_input_source=order_intent_artifact
decision_source=order_intent_artifact
not_copied_from_legacy_replay=true
legacy_replay_used_only_for_parity=true
outputs_recomputed_checksum_not_legacy_copy=true
```

ReplayResult `actions.csv` 逐行保留：

```text
order_intent_artifact
order_intent_row_id
```

validator 已确认这些 row id 存在于对应 `order_intents.csv`。

### 4.2 覆盖与 parity

validator 输出：

```text
ok=true
order_intent_artifact_count=25
five_rules_all_present=pass
order_intent_artifacts_cover_five_methods=pass
order_intent_artifacts_cover_2026_ytd=pass
replay_actions_reference_order_intent_artifact=pass refs=25
replay_result_actions_order_intent_rows_exist_and_match=pass
summary_parity_all_pass=pass rows 25 vs 25
daily_nav_parity_all_pass=pass rows 1975 vs 1975
actions_parity_all_pass=pass rows 3651 vs 3651
action_key_parity_all_pass=pass rows 3651 vs 3651
position_snapshot_parity_all_pass=pass rows 11512 vs 11512
```

覆盖 rules：

```text
original
top50_exit_all
top50_exit_one_worst_sell
one_sell_one_buy_correct
one_sell_one_buy_buggy_e8r
```

覆盖 methods：

```text
e4_frozen_qlib_2023_2025_ltr
fresh_qlib_2025_ltr
fresh_qlib_adaptive
frozen_qlib_2018_2022
frozen_qlib_2025_ltr
```

注意：`one_sell_one_buy_buggy_e8r` 仍只能作为 diagnostic parity，不得作为有效策略或产品策略证据。

### 4.3 负向门禁

新增负向测试已覆盖：

```text
test_rejects_order_intents_generated_from_replay_actions
test_rejects_order_intents_generated_from_replay_snapshots
test_rejects_replay_result_generated_by_parity_wrapper_copy
test_rejects_replay_result_without_execution_input_source_order_intent
test_rejects_action_refs_that_do_not_match_order_intent_rows
test_rejects_action_rows_with_blank_decision_fields_when_required
test_rejects_legacy_replay_used_as_execution_source
```

这些负例能防止 D3R 曾出现的两类伪通过：

```text
从 replay result 反推 OrderIntentArtifact
复制 replay result frames 后补 provenance 字段
```

## 5. 验证结果

本轮审查实际执行：

```text
python -m py_compile scripts/build_tw_modular_order_intent_artifact.py scripts/validate_tw_modular_order_intent_artifact.py scripts/run_tw_modular_order_intent_replay.py scripts/validate_tw_modular_order_intent_replay.py scripts/run_tw_modular_order_intent_replay_parity.py scripts/validate_tw_modular_order_intent_replay_parity.py
result: pass
```

```text
python scripts/validate_tw_modular_order_intent_replay_parity.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T062610Z/manifest.json --json
result: ok=true
```

```text
python -m pytest tests/unit/test_tw_modular_order_intent_artifact.py tests/unit/test_tw_modular_order_intent_replay.py tests/unit/test_tw_modular_order_intent_replay_parity.py
result: 35 passed, 3 warnings
```

```text
python scripts/run_tw_modular_contract_regression.py --json
result: ok=true
```

```text
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
result: ok=true
```

说明：

```text
validate_tw_modular_order_intent_replay_parity.py
run_tw_modular_contract_regression.py
validate_tw_modular_readonly_snapshot.py
```

在普通沙箱中遇到 `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`，已按环境规则用提升权限重跑。上述命令均为只读验证。

## 6. 只读安全边界

目标文件扫描未发现危险入口：

```text
target_position
target_weight
broker
quick_trade
provider_publish
accepted_latest
monitor/scan
monitor/config
monitor/alerts
POST /api
PUT /api
PATCH /api
DELETE /api
```

readonly snapshot validator 仍通过：

```text
no_provider_publish=pass
no_accepted_latest_switch=pass
no_monitor_broker_order=pass
latest_pointer_points_to_readonly_snapshot_only=pass
```

D3RR 产物仍是研究/回测产物，不包含生产交易、券商、quick-trade、monitor 写入、provider publish 或 accepted latest 切换。

## 7. Phase D4 目标

D4 目标不是继续修 replay parity，而是把 D3RR 已证明的标准 artifact 作为后续产品化/只读展示的唯一输入来源。

关于用户在前端选择回放时间范围：

```text
推荐 D4 只做固定 2026_ytd 标准产物展示，并产出 ReplayWindowPolicy metadata；
D5 再做用户可选 date range replay；
如果执行者坚持 D4 就支持用户自选 range，必须先把 ReplayWindowPolicy、后端 validator、非法训练窗口拒绝测试前置到 D4。
```

不得只靠前端 date picker 限制日期。只要支持用户选择 `start/end`，后端必须用可追溯的模型训练窗口和 latest signal date 强制校验，避免把训练期表现展示成 OOS 回放证据。

D4 建议名称：

```text
Phase D4 Readonly Standard Artifact Consumption and Window Policy Metadata
```

目标链路：

```text
OrderIntentArtifact / ReplayResultArtifact / parity manifest
  -> readonly artifact index or snapshot
  -> readonly API
  -> frontend readonly display
  -> validator / safety audit
```

原则：

```text
API 只读读取标准 artifact，不重新生成策略决策
前端只展示标准 artifact，不执行策略或 replay 计算
diagnostic rule 只展示为 diagnostic，不进入有效策略对比或产品候选
所有输出保留 manifest/source/checksum/provenance
D4 默认只展示已审计固定窗口 2026_ytd
用户自选 date range 必须等待 ReplayWindowPolicy 生效，或作为 D4A/D4B/D4C 前置实现
```

## 8. D4 必做项

### 8.1 标准 artifact index

新增或扩展一个只读索引，指向 D3RR 标准产物：

```text
order_intent_replay_parity_manifest
order_intent_replay_result_manifest
order_intent_artifact_manifests
baseline_manifest
rules_present
methods_present
window
created_at
checksum / row_counts / parity_status
replay_window_policy_metadata
fixed_window_only=true
user_selectable_range_enabled=false
```

要求：

```text
只读生成或读取
不得覆盖 D3RR 原始产物
不得修改 formal_replay_manifest.json
不得切换 accepted latest
不得 publish provider
不得在没有 ReplayWindowPolicy 的情况下接受任意 start/end 查询
```

### 8.2 ReplayWindowPolicy metadata

D4 至少应为 D5 暴露或准备只读窗口策略 metadata。推荐新增配置：

```text
configs/tw_replay_window_policy.yaml
```

最小字段：

```text
policy_version
model_id
model_family
qlib_train_start / qlib_train_end
ltr_train_start / ltr_train_end, if applicable
allowed_replay_start_min
allowed_replay_end_policy=latest_available_signal_date
allowed_windows
disallow_training_overlap=true
disallow_future_beyond_signal=true
source_manifest / source_training_report
```

日期不得凭记忆填写，必须来自已审计的模型 manifest、训练报告或 source artifact。

示例约束：

```text
e4_frozen_qlib_2023_2025_ltr 的 LTR train window 为 2023-2025 时，
不得允许用户选择 2023-01-01..2025-12-31 作为策略回放证据；
allowed_replay_start_min 应落在 OOS 区间，例如 2026-01-01。
```

D4 如果不支持用户自选 range，可以只输出：

```text
fixed_window=2026_ytd
user_selectable_range_enabled=false
available_window_metadata_only=true
```

### 8.3 API 只读消费

如果 D4 接入 API，只允许新增 GET/read-only 路由。

允许：

```text
GET readonly standard artifact index
GET readonly order intent summary
GET readonly replay result summary
GET readonly parity status
GET readonly action lineage sample
GET readonly replay window policy metadata
```

禁止：

```text
POST/PUT/PATCH/DELETE
provider publish / refresh
accepted latest switch
monitor config save
monitor scan
alerts write
broker / quick-trade / orders
target_position / target_weight
```

API 返回必须带上：

```text
readonly_only=true
not_order=true
not_investment_advice=true
not_target_position=true
source_manifest
schema_version
generated_by / decision_source / execution_input_source
diagnostic_only 标记
fixed_window_only 或 replay_window_policy validation result
```

若 D4/D5 任一阶段支持用户传入：

```text
model_id
strategy_rule
start
end
```

后端必须先调用 ReplayWindowPolicy validator。校验至少包括：

```text
start_date <= end_date
start_date >= allowed_replay_start_min
end_date <= latest_available_signal_date
requested window 不得与 qlib train / LTR train 重叠
model_id 必须在 policy 中登记
strategy_rule 必须在 strategy dependency registry 中登记
diagnostic rule 不能作为普通策略展示
```

非法窗口必须由 API 拒绝，而不是只在前端禁用。示例错误：

```json
{
  "ok": false,
  "error": "requested window overlaps LTR training window",
  "model_id": "e4_frozen_qlib_2023_2025_ltr",
  "requested_start": "2025-01-01",
  "requested_end": "2025-12-31",
  "allowed_replay_start_min": "2026-01-01"
}
```

如果请求窗口已有标准 ReplayResultArtifact，API 只读返回现有结果。如果没有现成 artifact，D4 不应即时生成；D5 若允许生成新的 readonly replay artifact，必须另行审查并满足：

```text
只生成到只读研究 artifact 目录
生成 manifest / validator / checksum
不写 provider / accepted latest
不改默认策略
不改前端状态为生产结果
不触发交易链路
```

### 8.4 前端只读展示

如果 D4 接入前端，只允许展示后端 GET 返回的标准 artifact 摘要。

必须展示或保留：

```text
artifact type / schema version
window
rules / methods
parity_status
row_counts
decision_source=order_intent_artifact
generated_by=replay_execution_engine
diagnostic rule boundary
readonly / not order / not investment advice
fixed window 2026_ytd 或后端允许的 replay window
允许回放最早日期
当前选择是否 OOS
```

前端建议分为两个只读区域：

```text
当日策略意图区：读取 OrderIntentArtifact API，展示候选意图、继续观察、跳过等研究信息
回放结果区：读取 ReplayResultArtifact / ReplayWindowPolicy API，展示固定 2026_ytd 或后端校验通过的窗口
```

如果 D4 只做固定窗口，前端不得显示可编辑 date range picker；可以显示 disabled/window metadata。若 D5 支持自选窗口，前端 date picker 只能作为输入控件，不能成为唯一校验来源，非法窗口必须展示后端错误。

前端文案应使用：

```text
只读回放
研究结果
候选意图
非交易指令
不构成投资建议
```

禁止：

```text
生成策略建议
展示目标仓位/目标权重
触发交易/下单/quick-trade/broker
触发 monitor scan/config/alerts 写入
前端本地重算策略或 replay 结果并覆盖 artifact
下单 / 买入指令 / 卖出指令 / 自动交易 / 一键交易
保证收益 / 胜率承诺 / 上涨概率承诺
```

### 8.5 Validator 与测试

D4 必须新增 validator 或扩展现有 validator，至少检查：

```text
standard artifact index exists
all referenced manifests exist
order_intent_replay_manifest != baseline_manifest
replay_result.generated_by=replay_execution_engine
replay_result.execution_input_source=order_intent_artifact
replay_result.decision_source=order_intent_artifact
diagnostic rule not valid strategy evidence
readonly flags present
no forbidden API / write scope
checksum or row_count consistency
fixed_window_only=true unless ReplayWindowPolicy validator exists
user_selectable_range_enabled=false unless backend_window_validator_exists=true
replay_window_policy_metadata traceable, if provided
```

测试必须覆盖：

```text
API only exposes GET
API rejects or lacks write endpoints
API response contains readonly flags and source manifests
frontend does not call POST/PUT/PATCH/DELETE
frontend text does not imply trading advice or target position
diagnostic rule is visibly excluded from valid strategy evidence
```

如果支持用户选择回放窗口，还必须新增硬 Gate：

```text
replay_window_policy_exists == true
model_training_windows_traceable == true
backend_window_validator_exists == true
frontend_date_picker_not_only_guard == true
illegal_training_window_rejected_by_api == true
diagnostic_rule_not_valid_strategy_evidence == true
readonly_only == true
no_provider_publish == true
no_accepted_latest_switch == true
no_monitor_broker_order == true
```

## 9. D4 允许修改范围

允许：

```text
scripts/publish or build readonly standard artifact index script
scripts/validate readonly standard artifact index script
backend readonly GET route/service, if needed
frontend readonly display, if needed
ReplayWindowPolicy metadata config/validator, if D4 exposes window metadata
tests for readonly API/frontend/index validators
docs/tw_modular_contracts/PHASED4_*.md
```

必须保持只读，且不得触碰生产更新链路。

禁止：

```text
scripts/run_daily_tw_stock_auto_update.py
provider / accepted latest / data refresh / publish path
monitor config / scan / alerts write path
broker / quick-trade / order path
formal replay baseline artifact mutation
D3RR artifact mutation
把 one_sell_one_buy_buggy_e8r 当成有效策略证据
无 ReplayWindowPolicy 时接收用户任意 start/end
只靠前端 date picker 限制回放窗口
```

## 10. D4 验证命令建议

D4 执行者至少提供：

```bash
python -m py_compile <new_or_modified_scripts>
python <d4_build_or_publish_readonly_standard_artifact_index.py> --json
python <d4_validate_readonly_standard_artifact_index.py> --artifact <manifest> --json
python <d4_validate_replay_window_policy.py> --json  # 如果 D4 提供 window policy metadata
python scripts/validate_tw_modular_order_intent_replay_parity.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T062610Z/manifest.json --json
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

如接入 API/前端，还必须提供：

```bash
python -m pytest <backend_readonly_tests>
node <frontend_static_or_e2e_readonly_check>
```

并提供安全扫描：

```bash
rg -n "target_position|target_weight|broker|quick_trade|provider_publish|accepted_latest|monitor/scan|monitor/config|monitor/alerts|POST /api|PUT /api|PATCH /api|DELETE /api" <d4_changed_files>
```

如支持用户自选 range，还必须提供非法训练窗口拒绝测试，例如：

```bash
python -m pytest <backend_replay_window_policy_tests>
node <frontend_replay_window_range_readonly_check>
```

预期：

```text
D4 validator ok=true
D3RR parity validator ok=true
contract regression ok=true
readonly snapshot validator ok=true
unit/e2e tests pass
forbidden safety scan no dangerous writes
若 user_selectable_range_enabled=true，则 replay window policy hard gates 全部 pass
```

## 11. D5 预告：用户自选回放窗口

D5 可以正式实现用户前端选择时间 range，但必须建立在 D4 的标准 artifact index 和 ReplayWindowPolicy metadata 之上。

D5 范围建议：

```text
实现 ReplayWindowPolicy
实现后端窗口 validator
实现 readonly replay result 查询 API
实现前端 date range picker
后端拒绝训练期窗口
E2E 证明非法窗口不能查询
```

D5 审查重点：

```text
是否支持用户选择回放窗口
如果支持，是否有 ReplayWindowPolicy
E4 是否只允许 2026 及之后的 OOS 窗口
是否由后端拒绝训练期窗口
前端是否只展示 API 返回结果，不自行回放
diagnostic rule 是否没有进入有效策略对比
是否没有 provider / accepted latest / monitor / broker / order 越界
```

