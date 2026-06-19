# Phase R11 Readonly Production Readiness 执行报告

生成日期：2026-06-16

## 1. 执行范围

本阶段根据：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER10_REVIEW_AND_R11_WORK_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER9_R11_POST_R8_CLEANUP_AND_READONLY_PRODUCTION_PREP_WORK_CN.md
```

执行 R11：

```text
Readonly Production Readiness Review
```

R11 只做 readiness matrix、shadow integration plan、readonly publish contract 草案。

R11 不是：

- 生产接入；
- 前端改造；
- API 改造；
- 日更接入；
- provider publish；
- accepted latest 切换；
- monitor / broker / order 接入。

## 2. 当前基础状态

R9/R10 后当前 modular artifact 链路状态：

```text
ModelSignalArtifact: ready for shadow
FullRankArtifact: ready for shadow
StrategyRule dependency: ready for shadow
ReplayResultArtifact: ready for shadow
Baseline action window parity: cleaned
Registry regression: ok=true
ReplayResult validator: ok=true
Unit tests: 13 passed
```

已清理的问题：

- R9 已把 replay full-rank 输入从 legacy CSV/列名切换到 `FullRankArtifact`；
- R10 已消除 action parity 的 baseline prefix compatibility；
- R10 已修复 coverage audit 中 `full_rank_artifact` 追溯路径。

## 3. Readiness Matrix

| 模块 | R11 状态 | 条件 | 风险 | 结论 |
| --- | --- | --- | --- | --- |
| Data fetch | deferred | 需要 Provider / Normalizer contract，失败重试、PIT、source freshness 单独审查 | 高 | 不允许接入生产 |
| ModelSignalArtifact | ready for shadow | R1/R4/R6/R9/R10 validation 通过，canonical signals 未改 | 中 | 可进入 R12 shadow 设计 |
| FullRankArtifact | ready for shadow | R9 contract / adapter / validator / regression 通过 | 中 | 可作为 replay shadow 输入 |
| StrategyRule dependency | ready for shadow | registry validator 通过，canonical dependency 已登记 | 中 | 可用于 shadow replay |
| ReplayResultArtifact | ready for shadow | R10 ReplayResult validator 通过，direct window parity 通过 | 中 | 可作为 readonly evidence |
| Baseline windowed actions | ready for audit only | R10 adapter audit pass，原始 baseline 不变 | 中 | 可用于 parity audit，不是生产 replay |
| AnalysisArtifact | not ready | 尚无正式 contract、schema、validator | 中 | 需另开 contract 阶段 |
| Readonly publish artifact | draft only | R11 仅定义草案，未实现 writer / validator / checksum | 中 | 需 R12/R13 单独实现 |
| Readonly API | not ready | 尚无 wrapper、权限、字段白名单、安全边界 E2E | 中 | 不允许接入 |
| Frontend readonly display | not ready | 需 publish artifact 稳定、API contract、E2E readonly、安全文案审计 | 中 | 不允许接入 |
| Daily orchestrator | shadow only | 只能隔离目录 shadow run，不得阻塞现有日更 | 高 | 不允许生产接入 |
| Provider publish / accepted latest | forbidden | 需治理、回滚、审批、不可变 manifest | 高 | R11 禁止 |
| Monitor / broker / order | forbidden | 需独立交易安全审查 | 极高 | R11 禁止 |

## 4. Shadow Integration Plan 草案

### 4.1 目标

R12 如获审查者和用户批准，可做 shadow integration。

Shadow 目标：

- 验证 modular artifact 在日更后可独立生成；
- 不影响现有生产日更；
- 不发布 accepted latest；
- 不给前端/API供生产读取；
- 不产生订单或目标仓位。

### 4.2 输入

Shadow run 只允许读取：

```text
latest accepted qlib/fresh data
existing normalized prices
R9 FullRankArtifact contract
R1/R9/R10 validated manifests
configs/tw_modular_registry.yaml
configs/tw_modular_replay_matrix.yaml
```

### 4.3 输出目录

建议隔离目录：

```text
data_tw/artifacts/shadow_modular_daily/{asof}/
```

建议输出：

```text
manifest.json
model_signal_manifest.json
full_rank_manifest.json
strategy_dependency_snapshot.yaml
replay_result_manifest.json
analysis_summary.json
validation_report.json
forbidden_scope_audit.json
```

### 4.4 Shadow Run 边界

Shadow run 可以：

- 生成 modular signal / full-rank / replay / analysis shadow artifact；
- 运行 validator；
- 运行 readonly regression；
- 生成审计报告；
- 写入隔离 shadow 目录。

Shadow run 不得：

- 修改 `latest_signal.json`；
- 修改 accepted latest；
- 覆盖现有 fresh qlib 默认策略；
- 阻塞现有日更；
- 修改前端；
- 修改 API；
- provider publish；
- monitor scan/config save；
- broker / quick-trade / order；
- 写业务库交易表；
- 输出 target position / order intent 给生产链路。

### 4.5 Shadow Gate

R12 shadow gate 建议：

```text
all_validators_pass == true
forbidden_scope_audit == pass
no_provider_publish == true
no_accepted_latest_switch == true
no_frontend_api_change == true
no_monitor_broker_order == true
artifact_output_under_shadow_dir_only == true
```

任一失败应停止，不得自动降级为生产接入。

## 5. Readonly Publish Contract 草案

R11 只定义草案，不实现 writer。

建议路径：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/{asof}/manifest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/{asof}/strategy_snapshot.json
```

### 5.1 manifest.json 草案

```json
{
  "artifact_type": "readonly_strategy_snapshot",
  "schema_version": "readonly_strategy_snapshot_v0_draft",
  "asof": "YYYY-MM-DD",
  "created_at": "ISO-8601",
  "created_by": "future_shadow_publish_script",
  "source_replay_manifest": "data_tw/artifacts/shadow_modular_daily/{asof}/replay_result_manifest.json",
  "source_signal_manifest": "data_tw/artifacts/shadow_modular_daily/{asof}/model_signal_manifest.json",
  "source_full_rank_manifest": "data_tw/artifacts/shadow_modular_daily/{asof}/full_rank_manifest.json",
  "strategy_rule": "top50_exit_one_worst_sell",
  "model_name": "fresh_qlib_adaptive",
  "readonly_only": true,
  "no_order_action": true,
  "not_target_position": true,
  "not_investment_advice": true,
  "validation_report": "validation_report.json",
  "forbidden_scope_audit": "forbidden_scope_audit.json",
  "checksum_manifest": "checksum_manifest.json"
}
```

### 5.2 strategy_snapshot.json 草案

```json
{
  "asof": "YYYY-MM-DD",
  "model_name": "fresh_qlib_adaptive",
  "strategy_rule": "top50_exit_one_worst_sell",
  "holdings_before": [],
  "candidate_buys": [],
  "candidate_sells": [],
  "diff_vs_previous": {
    "added": [],
    "removed": [],
    "unchanged": []
  },
  "explanations": [],
  "readonly_only": true,
  "no_order_action": true,
  "not_target_position": true,
  "not_investment_advice": true
}
```

### 5.3 必需字段语义

| 字段 | 语义 |
| --- | --- |
| `asof` | snapshot 观察日期 |
| `source_replay_manifest` | shadow replay result 来源 |
| `source_signal_manifest` | shadow signal 来源 |
| `source_full_rank_manifest` | shadow full-rank 来源 |
| `strategy_rule` | 只读策略规则名 |
| `model_name` | 只读模型名 |
| `holdings_before` | 只读解释字段，不得来自真实券商持仓 |
| `candidate_buys` | 只读候选，不是订单 |
| `candidate_sells` | 只读候选，不是订单 |
| `diff_vs_previous` | 与上一只读 snapshot 的差异 |
| `readonly_only` | 必须为 true |
| `no_order_action` | 必须为 true |
| `not_target_position` | 必须为 true |
| `not_investment_advice` | 必须为 true |

## 6. Production / Frontend / API 前置条件

任何真实接入前必须另开阶段，至少完成：

1. Readonly publish artifact writer；
2. publish artifact validator；
3. checksum manifest；
4. immutable artifact retention policy；
5. API response schema；
6. API readonly safety tests；
7. frontend readonly display E2E；
8. no-order / no-target-position / no-broker static scan；
9. daily orchestrator shadow failure isolation；
10. provider publish / accepted latest governance；
11. rollback / disable switch；
12. user-facing wording safety audit。

未完成前，不允许生产接入。

## 7. R11 禁止事项确认

R11 未执行：

- 训练；
- 调参；
- score recompute；
- replay；
- shadow run；
- publish artifact writer；
- API wrapper；
- frontend change；
- daily orchestrator change；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker / quick-trade / order。

R11 未修改：

- R1 canonical signals；
- R9 FullRankArtifact；
- R10 windowed baseline artifact；
- R10 modular replay result；
- 前端；
- 后端 API；
- 日更脚本；
- 默认策略。

## 8. 允许进入 R12 的条件

R11 不自动批准 R12。

若要执行 R12，必须由审查者另写 R12 工作文档，并由用户确认。R12 只应做：

```text
shadow run implementation
```

R12 仍不得：

- 生产接入；
- 前端/API接入；
- provider publish；
- accepted latest 切换；
- monitor / broker / order。

## 9. 结论

R11 已完成 readiness review。

当前结论：

```text
modular artifacts are ready for shadow planning
production integration is not approved
frontend/API/daily integration is not approved
provider publish / accepted latest / monitor / broker / order remain forbidden
```

建议后续如需推进，另开 R12 shadow integration 文档。
