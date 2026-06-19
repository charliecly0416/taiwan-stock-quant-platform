# Phase D4 审查与 Phase D5 工作文档

生成日期：2026-06-17

## 1. D4 审查结论

D4 通过，可以进入 D5。

结论：

```text
readonly standard artifact index: pass
ReplayWindowPolicy metadata: pass
fixed_window_only=true: pass
user_selectable_range_enabled=false: pass
D3RR parity validator: pass
contract regression: pass
readonly snapshot validator: pass
readonly safety boundary: pass
next phase: D5 user-selectable replay window
```

D4 的实现保持了只读边界，没有接入 API 或前端，也没有开放用户自选时间范围。当前只输出固定 `2026_ytd` 标准产物索引与 ReplayWindowPolicy metadata，符合上一阶段约定。

## 2. 审查对象

handoff：

```text
docs/tw_modular_contracts/PHASED4_READONLY_STANDARD_ARTIFACT_INDEX_REVIEW_HANDOFF_CN.md
```

执行报告：

```text
docs/tw_modular_contracts/PHASED4_READONLY_STANDARD_ARTIFACT_INDEX_EXECUTION_REPORT_CN.md
```

核心实现：

```text
configs/tw_replay_window_policy.yaml
scripts/build_tw_modular_readonly_standard_artifact_index.py
scripts/validate_tw_modular_readonly_standard_artifact_index.py
scripts/validate_tw_replay_window_policy.py
tests/unit/test_tw_modular_readonly_standard_artifact_index.py
```

D4 产物：

```text
data_tw/artifacts/readonly_standard_artifact_index/d4/manifest.json
data_tw/artifacts/readonly_standard_artifact_index/d4/latest.json
data_tw/artifacts/readonly_standard_artifact_index/d4/checksum_manifest.json
```

## 3. Findings

未发现阻塞问题。

### Low: 当前只读边界字段较多，但未误触发验证

D4 manifest 中存在 `not_target_position`、`no_provider_publish`、`no_accepted_latest_switch` 等安全否定字段。validator 已正确通过，没有把这些否定字段误判成危险输入。

这不是问题，只是后续若再扩展安全字段表，仍应保持“否定字段不等于危险入口”的语义。

## 4. 已通过项

### 4.1 只读标准 artifact index

D4 index 已确认：

```text
artifact_type=readonly_standard_artifact_index
readonly_only=true
not_order=true
not_investment_advice=true
not_target_position=true
fixed_window_only=true
user_selectable_range_enabled=false
available_window_metadata_only=true
```

index 只引用 D3RR 的标准产物，不改写 D3RR 原始目录。

### 4.2 ReplayWindowPolicy metadata

Policy 已确认：

```text
policy_version=replay_window_policy_d4_v1
fixed_window_only=true
user_selectable_range_enabled=false
fixed_window=2026_ytd
allowed_replay_start_min=2026-01-01
latest_available_signal_date=2026-05-07
```

并且 `e4_frozen_qlib_2023_2025_ltr` 等模型的训练窗口均可追溯，固定窗口不与训练窗口重叠。

### 4.3 只读边界

D4 未做：

```text
API route
frontend display
date range picker
按用户请求即时 replay 生成
provider refresh / publish
accepted latest switch
monitor 写入
broker / quick-trade / order
```

这符合 D4 只做标准产物索引与 metadata 的定位。

## 5. 验证结果

本轮审查实际执行：

```text
python -m py_compile scripts/build_tw_modular_readonly_standard_artifact_index.py scripts/validate_tw_modular_readonly_standard_artifact_index.py scripts/validate_tw_replay_window_policy.py : pass
python scripts/validate_tw_replay_window_policy.py --json : ok=true
python scripts/validate_tw_modular_readonly_standard_artifact_index.py --artifact data_tw/artifacts/readonly_standard_artifact_index/d4/manifest.json --json : ok=true
python -m pytest tests/unit/test_tw_modular_readonly_standard_artifact_index.py : 6 passed
python scripts/validate_tw_modular_order_intent_replay_parity.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T062610Z/manifest.json --json : ok=true
python scripts/run_tw_modular_contract_regression.py --json : ok=true
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json : ok=true
```

说明：

```text
validate_tw_replay_window_policy.py
validate_tw_modular_readonly_standard_artifact_index.py
validate_tw_modular_order_intent_replay_parity.py
run_tw_modular_contract_regression.py
validate_tw_modular_readonly_snapshot.py
```

在普通沙箱中遇到 `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`，已按环境规则重跑只读验证并全部通过。

## 6. 只读安全边界

D4 未发现以下危险路径或语义：

```text
POST /api/tw-stock/monitor/config
POST /api/tw-stock/monitor/scan
POST /api/tw-stock/monitor/alerts
POST /api/tw-stock/quant/ops/** publish/refresh/provider/accepted
POST /api/quick-trade/**
/api/broker/**
order
target_position
target_weight
自动买入
自动卖出
连接券商
刷新 provider
切换 accepted latest
```

readonly snapshot validator 仍通过：

```text
no_provider_publish=pass
no_accepted_latest_switch=pass
no_monitor_broker_order=pass
latest_pointer_points_to_readonly_snapshot_only=pass
```

## 7. Phase D5 目标

D5 才正式支持用户前端选择回放时间范围。

目标链路：

```text
ReplayWindowPolicy
  -> backend window validator
  -> readonly replay result query API
  -> frontend date range picker
  -> illegal training window rejected
  -> E2E proof
```

原则：

```text
不得只靠前端 date picker 限制
必须由后端拒绝训练期窗口
前端只能展示 API 返回结果，不自行回放
diagnostic rule 不能进入有效策略对比
不能触发 provider / accepted latest / monitor / broker / order
```

## 8. D5 必做项

### 8.1 ReplayWindowPolicy 正式接入

D5 需要把窗口策略升级为可调用的后端校验能力，至少支持：

```text
model_id
strategy_rule
start
end
allowed_replay_start_min
latest_available_signal_date
training window overlap rejection
```

非法窗口必须返回清楚的错误，而不是前端静默禁用。

### 8.2 只读回放查询

D5 若开放窗口查询，只允许只读 GET 路由返回已有标准 artifact，或在只读研究目录生成新的 replay artifact。

禁止：

```text
写 provider
切 accepted latest
改默认策略
触发交易链路
```

### 8.3 前端展示

前端只允许展示：

```text
只读回放
研究结果
候选意图
非交易指令
不构成投资建议
```

如果支持 range picker，它只能是输入控件，不能成为唯一校验来源。

## 9. D5 验证命令建议

```bash
python -m py_compile <new_or_modified_scripts>
python <d5_validate_replay_window_policy.py> --json
python <d5_validate_readonly_window_query.py> --json
python -m pytest <backend_replay_window_policy_tests>
node <frontend_replay_window_readonly_check>
python scripts/validate_tw_modular_order_intent_replay_parity.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T062610Z/manifest.json --json
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

预期：

```text
D5 validator ok=true
unit/e2e tests pass
forbidden safety scan no dangerous writes
```
