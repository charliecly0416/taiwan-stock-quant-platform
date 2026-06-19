# Phase R11 审查与 R12 Shadow 工作建议

生成日期：2026-06-16

## 1. 审查结论

R11 审查通过。

R11 只完成了 readonly production readiness review / shadow integration plan，没有实际接入生产链路。本次未发现阻塞后续另开 R12 shadow integration 工作文档的问题。

必须强调：

- R11 通过不等于生产接入通过；
- R11 通过不等于前端/API/日更接入通过；
- R11 通过不允许 provider publish；
- R11 通过不允许 accepted latest 切换；
- R11 通过不允许 monitor、broker、quick-trade 或 order；
- 后续最多允许另开 R12 shadow integration 阶段。

## 2. 审查对象

R11 handoff：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER11_READONLY_PRODUCTION_READINESS_REVIEW_HANDOFF_CN.md
```

R11 执行报告：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER11_READONLY_PRODUCTION_READINESS_EXECUTION_REPORT_CN.md
```

## 3. 复核结果

### 3.1 R11 产出符合范围

R11 执行报告覆盖：

- readiness matrix；
- shadow integration plan；
- readonly publish contract 草案；
- production / frontend / API 前置条件；
- R11 禁止事项确认；
- R12 前置条件。

当前新增文件仅为：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER11_READONLY_PRODUCTION_READINESS_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER11_READONLY_PRODUCTION_READINESS_REVIEW_HANDOFF_CN.md
```

未发现新增 shadow run、publish writer、API wrapper、frontend change 或 daily orchestrator change。

### 3.2 Readiness matrix 边界清楚

R11 将模块状态分为：

```text
ready for shadow
ready for audit only
draft only
not ready
deferred
forbidden
```

关键结论合理：

- `ModelSignalArtifact`：ready for shadow；
- `FullRankArtifact`：ready for shadow；
- `StrategyRule dependency`：ready for shadow；
- `ReplayResultArtifact`：ready for shadow；
- `Baseline windowed actions`：ready for audit only；
- `AnalysisArtifact`：not ready；
- `Readonly publish artifact`：draft only；
- `Readonly API`：not ready；
- `Frontend readonly display`：not ready；
- `Daily orchestrator`：shadow only，不允许生产接入；
- `Provider publish / accepted latest`：forbidden；
- `Monitor / broker / order`：forbidden。

这与 R9/R10 后的真实状态一致。

### 3.3 Shadow plan 隔离目录合理

R11 建议未来 R12 只写入：

```text
data_tw/artifacts/shadow_modular_daily/{asof}/
```

允许范围：

- 生成 shadow artifacts；
- 运行 validators；
- 运行 readonly regression；
- 生成审计报告；
- 写入隔离 shadow 目录。

禁止范围：

- 修改 `latest_signal.json`；
- 修改 accepted latest；
- 覆盖 fresh qlib 默认策略；
- 阻塞现有日更；
- 修改前端/API；
- provider publish；
- monitor scan/config save；
- broker / quick-trade / order；
- 写业务库交易表；
- 输出 target position / order intent 给生产链路。

该 shadow plan 仍是草案，不是实现授权。

### 3.4 Readonly publish contract 仍是草案

R11 提出的草案路径：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/{asof}/manifest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/{asof}/strategy_snapshot.json
```

草案要求包含：

```text
readonly_only: true
no_order_action: true
not_target_position: true
not_investment_advice: true
```

复核判断：

- 字段方向正确；
- 明确不是订单、不是目标仓位、不是投资建议；
- R11 未实现 writer，符合边界；
- 后续若进入 R12/R13，必须新增正式 contract、writer、validator、checksum manifest 和安全测试。

### 3.5 当前链路复核仍通过

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

ReplayResult validator：

```bash
python scripts/validate_tw_modular_artifact_contract.py \
  --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json \
  --json
```

结果：

```text
ok: true
schema_version: replay_result_r10_action_window_cleanup
actions_window_field: pass
parity_audit_status: pass
action_key_parity_audit_status: pass
manifest_parity_status: pass
```

Unit tests：

```bash
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

结果：

```text
13 passed
```

### 3.6 Forbidden scope 复核通过

`forbidden_scope_audit.csv`：

```text
frontend/src/views/tw-stock-monitor/index.vue: pass
scripts/run_daily_tw_stock_auto_update.py: pass
scripts/run_extended_oos_formal_replay_matrix.py: pass
backend_api_python: pass
src/api: pass
```

额外 targeted diff：

```text
frontend
src
backend
backend_api_python
scripts/run_daily_tw_stock_auto_update.py
scripts/run_extended_oos_formal_replay_matrix.py
configs
data_tw/artifacts
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix_windowed
```

结果：无 tracked diff。

### 3.7 未发现 shadow / publish 实现产物

复核 `data_tw/artifacts` 未发现新增：

```text
shadow_modular_daily
publish/readonly_strategy_snapshot
accepted/latest
```

这符合 R11 “只做 readiness 文档，不实现 writer / shadow run”的边界。

## 4. 非阻塞建议

### P2：R12 工作文档必须补齐 checksum / package manifest 的具体 schema

R11 报告已经在 publish contract 草案中引用：

```text
checksum_manifest.json
```

但 R11 还没有给出 checksum / package manifest 的正式 schema。这不阻塞 R11，因为 R11 是 readiness review；但如果进入 R12 shadow implementation，应在 R12 工作文档中明确：

- 每个 shadow artifact 的路径；
- sha256 或等价 checksum；
- source manifest checksum；
- generated artifact checksum；
- config snapshot checksum；
- validator result checksum；
- forbidden scope audit checksum；
- 产物保留策略；
- 是否允许覆盖同一 `{asof}` 输出。

没有 checksum / package manifest 前，不应进入任何 publish 或 frontend/API 阶段。

### P2：Readonly publish contract 需要独立 validator

R11 只提出 `readonly_strategy_snapshot` 草案，尚未定义 validator。

后续 R12/R13 至少应验证：

- `readonly_only == true`；
- `no_order_action == true`；
- `not_target_position == true`；
- `not_investment_advice == true`；
- 不含 broker/order/quick-trade 字段；
- 不含 target position / target weight；
- 不含收益承诺、胜率承诺、上涨概率承诺；
- source manifests 均来自 shadow 目录；
- validation report 和 forbidden scope audit 均 pass。

该项不阻塞 R11，但阻塞真实 publish writer 或 API 接入。

## 5. 残余风险

### 5.1 R11 只证明 readiness，不证明生产可用

R11 没有实现 shadow run，也没有实现 readonly publish artifact writer。因此当前状态只能说：

```text
ready for shadow planning
```

不能说：

```text
ready for production integration
ready for frontend/API integration
ready for daily orchestrator integration
```

### 5.2 AnalysisArtifact 尚无正式合同

R11 将 `AnalysisArtifact` 标为 `not ready` 是正确的。后续如果要把 replay / shadow 结果整理成产品可读解释，必须另开合同和 validator，而不是直接把分析 JSON 接给前端。

### 5.3 Data fetch / provider governance 尚未处理

R11 明确 Data fetch 为 deferred，provider publish / accepted latest 为 forbidden。后续如果涉及真实日更数据接入，需要单独处理：

- provider / normalizer contract；
- freshness；
- PIT；
- retry / rollback；
- accepted latest governance；
- provider publish 审批和不可变 manifest。

## 6. R12 工作建议

允许另开 R12 工作文档，但不应把 R11 直接解释为 R12 执行授权。

R12 建议主题：

```text
Phase R12 Shadow Modular Daily Artifact Implementation
```

R12 目标：

- 只实现 shadow run；
- 只写隔离目录；
- 只生成 shadow artifacts 和审计；
- 不接前端/API/日更生产链路；
- 不 provider publish；
- 不 accepted latest；
- 不 monitor/broker/order。

R12 建议产出：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER12_SHADOW_MODULAR_DAILY_WORK_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER12_SHADOW_MODULAR_DAILY_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER12_SHADOW_MODULAR_DAILY_REVIEW_HANDOFF_CN.md
```

R12 shadow output 建议：

```text
data_tw/artifacts/shadow_modular_daily/{asof}/manifest.json
data_tw/artifacts/shadow_modular_daily/{asof}/model_signal_manifest.json
data_tw/artifacts/shadow_modular_daily/{asof}/full_rank_manifest.json
data_tw/artifacts/shadow_modular_daily/{asof}/replay_result_manifest.json
data_tw/artifacts/shadow_modular_daily/{asof}/validation_report.json
data_tw/artifacts/shadow_modular_daily/{asof}/forbidden_scope_audit.json
data_tw/artifacts/shadow_modular_daily/{asof}/checksum_manifest.json
```

R12 必须设置 gate：

```text
all_validators_pass == true
forbidden_scope_audit == pass
artifact_output_under_shadow_dir_only == true
no_provider_publish == true
no_accepted_latest_switch == true
no_frontend_api_change == true
no_monitor_broker_order == true
```

任一失败必须停止。

## 7. R12 禁止事项

R12 仍禁止：

- 训练；
- 调参；
- score recompute；
- 修改 R1 canonical signals；
- 修改 R9/R10 canonical artifacts；
- 修改策略规则；
- 修改默认策略；
- 前端/API接入；
- 日更生产接入；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker、quick-trade 或 order；
- 输出 target position / target weight；
- 将 replay 结果解释为交易建议。

## 8. 最终结论

R11 通过。

当前状态：

```text
modular artifacts are ready for shadow planning
production integration is not approved
frontend/API/daily integration is not approved
provider publish / accepted latest / monitor / broker / order remain forbidden
```

后续若继续推进，应先由审查者编写 R12 shadow integration 工作文档，再由执行者按 R12 文档实现；不得直接从 R11 跳到生产接入。
