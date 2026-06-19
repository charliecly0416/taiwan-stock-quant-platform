# Phase R13 审查与 R14 工作建议

生成日期：2026-06-16

## 1. 审查结论

R13 审查通过，允许进入 R14。

R13 已完成 readonly publish artifact contract / writer / validator，且当前产物满足 R13 gate：

- 已新增 `ReadonlyStrategySnapshot` 合约；
- 已生成 `data_tw/artifacts/publish/readonly_strategy_snapshot/2026-06-16/`；
- 已生成 readonly 专用 `latest.json`；
- `latest.json` 只指向 readonly snapshot manifest；
- 未修改 provider accepted latest；
- 未接入前端、API、daily orchestrator；
- 未触发 monitor / broker / quick-trade / order；
- 当前 artifact 未包含 `target_position` / `target_weight` 字段；
- 默认展示组合为 `e4_frozen_qlib_2023_2025_ltr + top50_exit_one_worst_sell`；
- 独立 validator、checksum、regression、单元测试均通过。

## 2. 审查对象

R13 handoff：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER13_READONLY_PUBLISH_ARTIFACT_REVIEW_HANDOFF_CN.md
```

R13 执行报告：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER13_READONLY_PUBLISH_ARTIFACT_EXECUTION_REPORT_CN.md
```

新增合约：

```text
docs/tw_modular_contracts/READONLY_STRATEGY_SNAPSHOT_CONTRACT_CN.md
```

新增脚本：

```text
scripts/publish_tw_modular_readonly_snapshot.py
scripts/validate_tw_modular_readonly_snapshot.py
```

新增 artifact：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-06-16/
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
```

## 3. 复核结果

### 3.1 Contract 范围正确

`READONLY_STRATEGY_SNAPSHOT_CONTRACT_CN.md` 明确：

- artifact type 为 `readonly_strategy_snapshot`；
- schema version 为 `readonly_strategy_snapshot_r13_v1`；
- `latest.json` 只属于 readonly snapshot 命名空间；
- 禁止 provider publish / accepted latest 切换；
- 禁止 broker / quick-trade / order；
- 禁止 target position / target weight；
- 禁止 API / frontend / daily orchestrator 接入。

### 3.2 Manifest 符合 R13 schema

`manifest.json` 当前关键字段：

```text
artifact_type: readonly_strategy_snapshot
schema_version: readonly_strategy_snapshot_r13_v1
readonly_only: true
production_trade_enabled: false
no_order_action: true
not_target_position: true
not_investment_advice: true
display_role: primary_readonly_candidate
is_primary_readonly_candidate: true
is_production_trading_default: false
quality_status: pass
```

source 关系：

```text
source_shadow_manifest: data_tw/artifacts/shadow_modular_daily/2026-06-16/manifest.json
source_signal_manifest: data_tw/artifacts/signals/e4_frozen_qlib_2023_2025_ltr/r1_legacy_signal_adapter_20260616/manifest.json
source_full_rank_manifest: data_tw/artifacts/full_rank/frozen_qlib_2018_2022_raw_oos/r9_full_rank_adapter_20260616/manifest.json
source_strategy_dependency: configs/strategy_dependencies/top50_exit_one_worst_sell.yaml
```

说明：`source_full_rank_manifest` 指向 frozen qlib raw OOS full-rank artifact，是 R12 shadow full-rank snapshot 中 `e4_frozen_qlib_2023_2025_ltr` 对应的 qlib top50 / full-rank 边界来源，当前 mapping 一致。

### 3.3 Strategy snapshot 使用冻结展示组合

`strategy_snapshot.json` 当前关键字段：

```text
model_id: e4_frozen_qlib_2023_2025_ltr
base_model_id: frozen_qlib_2018_2022
strategy_rule: top50_exit_one_worst_sell
candidate_boundary: qlib_top50
ranking_source: ltr_rerank_within_qlib_top50
display_role: primary_readonly_candidate
is_production_trading_default: false
readonly_only: true
not_order: true
no_order_action: true
not_target_position: true
not_investment_advice: true
```

候选字段均使用 readonly 语义：

```text
readonly_candidate_only
readonly_continuation_only
readonly_exit_candidate_only
```

未发现真实下单、目标仓位、券商连接或收益承诺语义。

### 3.4 Readonly latest pointer 合法

`latest.json` 当前内容：

```text
artifact_type: readonly_strategy_snapshot_latest_pointer
readonly_only: true
production_trade_enabled: false
snapshot_manifest: data_tw/artifacts/publish/readonly_strategy_snapshot/2026-06-16/manifest.json
not_provider_accepted_latest: true
not_trade_target_latest: true
```

该 latest pointer 位于：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
```

未发现 provider / qlib accepted latest 修改。

### 3.5 Checksum 独立复核通过

独立复算 `checksum_manifest.json` 中所有条目：

```text
file_count: 8
has_checksum_self: False
manifest.json included: True
strategy_snapshot.json included: True
latest.json included: False
validation.ok: true
validation.checked_file_count: 8
bad_count: 0
```

说明：snapshot 内部 checksum 可复现。`latest.json` 未纳入 snapshot checksum，但已由 validator 的 latest pointer check 单独覆盖，不阻塞 R13。

### 3.6 Validator 复跑通过

复核命令：

```bash
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

结果：

```text
ok: true
artifact_type: pass
schema_version: pass
readonly_only: pass
production_trade_enabled_false: pass
no_order_action: pass
not_target_position: pass
not_investment_advice: pass
is_production_trading_default_false: pass
primary_display_contract: pass
candidate_boundary: pass
ranking_source: pass
forbidden_scope_audit: pass
no_provider_publish: pass
no_accepted_latest_switch: pass
no_monitor_broker_order: pass
no_unsafe_field_names: pass
checksum_ok: pass
latest_pointer_points_to_readonly_snapshot_only: pass
```

### 3.7 Regression / tests 通过

复核命令：

```bash
python scripts/run_tw_modular_contract_regression.py --json
```

结果：

```text
ok: true
signal_manifest_count: 5
strategy_dependency_count: 6
full_rank_artifact_count: 2
signal_validation_rows: 35
full_rank_validation_rows: 5
```

复核命令：

```bash
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

结果：

```text
13 passed
```

### 3.8 Forbidden scope 通过

`forbidden_scope_audit.json`：

```text
status: pass
no_frontend_change: true
no_api_change: true
no_daily_orchestrator_change: true
no_provider_publish: true
no_accepted_latest_switch: true
no_monitor_broker_order: true
publish_output_under_readonly_snapshot_dir: true
```

Targeted diff：

```text
frontend
backend_api_python
src/api
scripts/run_daily_tw_stock_auto_update.py
scripts/run_extended_oos_formal_replay_matrix.py
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
```

结果：无 tracked diff。当前新增产物为未跟踪 artifact，内容审查通过。

## 4. 非阻塞问题与建议

### P2：Validator 应显式禁止 `target_position`

当前 artifact 未出现 `target_position` / `target_weight` 字段，R13 不阻塞。

但 `scripts/validate_tw_modular_readonly_snapshot.py` 的 `FORBIDDEN_UNSAFE_KEYS` 当前包含：

```text
target_weight
target_qty
target_quantity
```

尚未显式包含：

```text
target_position
target-position
targetPosition
```

建议 R14 前或 R14 中补强 validator，确保未来 artifact 即使带有 `not_target_position: true`，也不能同时混入真实 `target_position` 字段。

### P2：Writer 应由实际 validator 结果回填 validation_report / gate

当前 `validation_report.json` 是 writer 预写的简版报告，只包含：

```text
shadow_gate_ready
forbidden_scope_audit
readonly_flags
```

而独立 validator 实际有更完整的 21 项检查。建议后续把发布流程改为：

```text
writer 生成 manifest / snapshot / checksum / latest
validator --write-report 生成完整 validation_report.json
writer 或 wrapper 根据 validator 结果回填 manifest.gate
```

这样可以避免 manifest gate 与 validator 结果未来出现漂移。

### P3：可考虑把 latest pointer 纳入独立审计摘要

`latest.json` 未放入 snapshot checksum 是可以接受的，因为 latest pointer 是可变指针，且 validator 已单独检查。

但 R14/R16 进入 API / daily 后，建议增加独立 latest pointer audit：

```text
latest pointer exists
latest pointer path under readonly_strategy_snapshot/
latest snapshot manifest exists
latest snapshot validator pass
latest is not provider accepted latest
latest is not trade target latest
```

## 5. R14 工作建议

允许执行 R14：Readonly API 接入。

R14 只能做：

- 新增只读 API endpoint；
- API 只读取 `data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json` 指向的 snapshot；
- API 返回 readonly snapshot、validation status、source manifest、checksum status；
- API 层禁止 POST / PUT / PATCH / DELETE；
- API 层禁止 provider publish / accepted latest switch；
- API 层禁止 monitor scan / config save / alerts write；
- API 层禁止 broker / quick-trade / order；
- API 层禁止输出 target position / target weight；
- API 层必须保留 `readonly_only`、`not_order`、`not_target_position`、`not_investment_advice`。

R14 不得：

- 接前端；
- 接 daily orchestrator；
- 修改 provider accepted latest；
- 触发数据刷新、训练、调参、score recompute、replay recompute；
- 改默认模型或策略规则；
- 将候选解释为交易建议。

R14 必须输出：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER14_READONLY_API_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER14_READONLY_API_REVIEW_HANDOFF_CN.md
```

R14 审查必须包含：

```text
API route method audit
readonly response schema audit
network forbidden write audit
latest pointer read-only audit
provider accepted latest untouched audit
broker/order/target-position semantic audit
```

## 6. 最终结论

R13 通过。

当前 readonly publish artifact 已生成，readonly latest pointer 合法，validator/checksum/regression/tests 通过，且未越界进入前端、API、daily orchestrator、provider accepted latest 或交易链路。

允许进入 R14，但 R14 仅限 readonly API，不得接入前端、daily orchestrator、provider accepted latest 或任何交易链路。
