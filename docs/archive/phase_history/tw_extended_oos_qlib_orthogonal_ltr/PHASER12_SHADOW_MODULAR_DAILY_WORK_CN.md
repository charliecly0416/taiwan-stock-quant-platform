# Phase R12 Shadow Modular Daily 工作文档

生成日期：2026-06-16

## 1. 背景与承接

本阶段承接：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER11_REVIEW_AND_R12_SHADOW_WORK_CN.md
```

R9-R11 已完成的前置条件：

- R9：`FullRankArtifact` 已标准化，config-driven replay 不再直接读取 legacy full rank CSV/legacy rank column；
- R10：baseline actions 已通过独立 window adapter 补齐 `window` 字段，action parity 不再使用 prefix compatibility；
- R11：完成 readonly production readiness review，但未做生产接入、前端/API接入、日更接入或 publish writer。

R12 目标不是产品化上线，而是在隔离 shadow 目录中验证 modular artifact 链路能否被一个日更形态的只读入口完整串起，并生成可审查的 manifest、校验报告、禁止范围审计和 checksum。

## 2. R12 目标

执行者只允许完成以下事项：

1. 新增一个独立 shadow runner，例如：

```text
scripts/run_tw_modular_shadow_daily.py
```

2. 读取现有 modular registry/config/artifact：

```text
configs/tw_modular_registry.yaml
configs/tw_modular_replay_matrix.yaml
data_tw/artifacts/signals/*/r1_legacy_signal_adapter_20260616/manifest.json
data_tw/artifacts/full_rank/*/r9_full_rank_adapter_20260616/manifest.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
```

3. 在隔离目录生成 shadow run 产物：

```text
data_tw/artifacts/shadow_modular_daily/{asof}/
```

4. 运行合同校验和禁止范围审计，确认 shadow run 未触碰生产链路。

5. 写出执行报告：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER12_SHADOW_MODULAR_DAILY_EXECUTION_REPORT_CN.md
```

## 3. 必须冻结的边界

R12 不得做以下事项：

- 不训练 qlib；
- 不训练 LTR；
- 不调参；
- 不重算 score；
- 不新增策略规则；
- 不修改任何 canonical signal；
- 不修改任何 FullRankArtifact；
- 不修改默认策略；
- 不修改前端；
- 不修改后端 API；
- 不修改真实日更脚本；
- 不 provider publish；
- 不切换 accepted latest；
- 不触发 monitor scan/config save；
- 不触发 broker、quick-trade、order；
- 不写真实交易表；
- 不输出 target position 或 order intent 给生产链路；
- 不把 shadow 结果提供给生产 frontend/API 读取。

特别说明：

```text
scripts/run_daily_tw_stock_auto_update.py
```

在 R12 中只允许被只读扫描确认未修改，不允许接入、不允许 import shadow runner、不允许追加调用。

## 4. Shadow Runner 输入规范

建议命令：

```bash
python scripts/run_tw_modular_shadow_daily.py --asof 2026-05-07 --json
```

如不传 `--asof`，执行者可以从现有 replay/signal artifact 中推导最大共同日期，但必须在报告中写清楚推导逻辑。

允许读取：

- modular registry；
- modular replay matrix config；
- ModelSignalArtifact manifest；
- FullRankArtifact manifest；
- ReplayResultArtifact manifest；
- strategy dependency registry；
- contract validator 输出；
- 当前仓库内只读文件。

不允许读取：

- broker 持仓；
- 下单表；
- monitor 写入状态；
- provider publish 状态写入接口；
- accepted latest 写入接口；
- 前端生产 runtime 配置写入口。

## 5. Shadow Runner 输出规范

每次运行必须只写入：

```text
data_tw/artifacts/shadow_modular_daily/{asof}/
```

建议文件：

```text
manifest.json
model_signal_manifest.json
full_rank_manifest.json
strategy_dependency_snapshot.yaml
replay_result_manifest.json
validation_report.json
forbidden_scope_audit.json
checksum_manifest.json
shadow_summary.json
```

### 5.1 `manifest.json`

必须包含：

```json
{
  "artifact_type": "shadow_modular_daily",
  "schema_version": "shadow_modular_daily_r12_v1",
  "asof": "YYYY-MM-DD",
  "created_at": "ISO-8601",
  "created_by": "scripts/run_tw_modular_shadow_daily.py",
  "output_dir": "data_tw/artifacts/shadow_modular_daily/{asof}",
  "readonly_only": true,
  "production_integration": false,
  "source_registry": "configs/tw_modular_registry.yaml",
  "source_replay_config": "configs/tw_modular_replay_matrix.yaml",
  "source_replay_manifest": "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json",
  "validation_report": "validation_report.json",
  "forbidden_scope_audit": "forbidden_scope_audit.json",
  "checksum_manifest": "checksum_manifest.json",
  "quality_status": "pass"
}
```

### 5.2 `validation_report.json`

必须至少记录：

- registry validation 是否通过；
- signal artifact validation 是否通过；
- full rank artifact validation 是否通过；
- replay result validation 是否通过；
- R10 action window parity 是否仍为 pass；
- 是否所有输入 manifest 存在；
- 是否所有输出都在 shadow 目录内；
- `all_validators_pass`。

### 5.3 `forbidden_scope_audit.json`

必须至少记录并全部为安全值：

```json
{
  "no_training": true,
  "no_tuning": true,
  "no_score_recompute": true,
  "no_strategy_rule_change": true,
  "no_canonical_signal_change": true,
  "no_full_rank_change": true,
  "no_default_strategy_change": true,
  "no_frontend_change": true,
  "no_api_change": true,
  "no_daily_orchestrator_change": true,
  "no_provider_publish": true,
  "no_accepted_latest_switch": true,
  "no_monitor": true,
  "no_broker": true,
  "no_quick_trade": true,
  "no_order": true,
  "no_target_position_output": true,
  "artifact_output_under_shadow_dir_only": true,
  "status": "pass"
}
```

### 5.4 `checksum_manifest.json`

必须对以下文件记录 sha256：

- shadow runner 脚本；
- registry；
- replay matrix config；
- 所引用的 signal manifests；
- 所引用的 full rank manifests；
- replay result manifest；
- shadow 输出文件。

## 6. 必跑验证

执行者至少运行：

```bash
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_artifact_contract.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json --json
python scripts/run_tw_modular_shadow_daily.py --asof 2026-05-07 --json
python -m py_compile scripts/run_tw_modular_shadow_daily.py
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

如新增 shadow runner 单测，应一并运行。若因环境限制无法运行，必须记录完整错误，不得用报告文字替代验证。

## 7. R12 通过标准

只有同时满足以下条件，R12 才能通过审查：

```text
all_validators_pass == true
forbidden_scope_audit.status == pass
artifact_output_under_shadow_dir_only == true
quality_status == pass
no_training == true
no_score_recompute == true
no_frontend_change == true
no_api_change == true
no_daily_orchestrator_change == true
no_provider_publish == true
no_accepted_latest_switch == true
no_monitor == true
no_broker == true
no_quick_trade == true
no_order == true
no_target_position_output == true
```

任一失败，R12 不得放行，不得进入 R13。

## 8. R12 不得声明的结论

R12 不得声明：

- 已产品化；
- 已接入每日自动更新；
- 已接入前端；
- 已接入 API；
- 已切换默认策略；
- 已可自动交易；
- 已可输出真实目标仓位；
- 新策略收益优于旧策略。

R12 只能声明：

```text
modular artifact shadow daily runner can/cannot generate isolated readonly shadow artifacts
```

## 9. 执行者 Prompt

请按：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER12_SHADOW_MODULAR_DAILY_WORK_CN.md
```

执行 Phase R12。目标是新增一个独立的只读 shadow runner，在 `data_tw/artifacts/shadow_modular_daily/{asof}/` 下生成 shadow modular daily artifact，并输出 manifest、validation report、forbidden scope audit、checksum manifest 和 shadow summary。

严格禁止训练、调参、重算 score、改 canonical signal、改 full rank、改策略规则、改默认策略、改前端、改 API、改真实日更脚本、provider publish、accepted latest 切换、monitor、broker、quick-trade、order、target position 或任何生产接入。R12 只允许 shadow 目录写入。

执行后请提交：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER12_SHADOW_MODULAR_DAILY_EXECUTION_REPORT_CN.md
```

报告必须列出输入、输出、命令、validator 结果、forbidden scope audit、checksum、是否修改了真实日更/前端/API/生产链路，以及是否满足 R12 gate。

## 10. 审查者 Prompt

请审查：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER12_SHADOW_MODULAR_DAILY_EXECUTION_REPORT_CN.md
```

重点确认：

- shadow runner 是否只写入 `data_tw/artifacts/shadow_modular_daily/{asof}/`；
- 是否没有训练、调参、重算 score；
- 是否没有修改 canonical signal、FullRankArtifact、策略规则或默认策略；
- 是否没有改前端、API、真实日更脚本；
- 是否没有 provider publish、accepted latest 切换、monitor、broker、quick-trade、order、target position；
- registry、signal、full rank、replay result validator 是否全部通过；
- R10 action window parity 是否仍为 pass；
- checksum 是否覆盖输入 manifest/config/script/output；
- R12 是否只证明 shadow daily artifact 可生成，而没有错误宣称产品化或策略收益结论。

若发现任何生产接入、写入越界或禁止事项，必须停止并要求执行者修复，不得放行进入 R13。
