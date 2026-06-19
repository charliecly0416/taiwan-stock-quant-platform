# Phase R3 审查与 R4 工作建议

生成日期：2026-06-16

## 1. 审查结论

R3 审查通过，允许进入 R4。

本次 R3 符合上阶段要求：只做可扩展 contract / capability / strategy dependency 设计，并新增只读 validator skeleton；未改 R2 replay 结果，未接入前端、日更或生产链路。

需要明确：当前 validator 仍是 skeleton，已能验证 R1 artifact 的 core contract，但尚未完整实现 extension metadata、allowed_consumers、ranking_allowed、dtype、PIT policy 等深度检查。该点不阻塞 R3，但必须作为 R4 的重点实现内容。

## 2. 审查对象

R3 handoff：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER3_EXTENSIBLE_CONTRACT_DESIGN_REVIEW_HANDOFF_CN.md
```

R3 执行报告：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER3_EXTENSIBLE_CONTRACT_DESIGN_EXECUTION_REPORT_CN.md
```

R3 contract 设计：

```text
docs/tw_modular_contracts/EXTENSIBLE_CONTRACT_CAPABILITY_DESIGN_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
docs/tw_modular_contracts/STRATEGY_DEPENDENCY_CONTRACT_CN.md
```

Validator skeleton：

```text
scripts/validate_tw_modular_artifact_contract.py
```

## 3. 复核结果

### 3.1 文档覆盖 R3 必答问题

R3 已覆盖：

- immutable core fields；
- optional extension fields；
- manifest capabilities；
- strategy dependency；
- forbidden fields/actions；
- legacy private column 禁止直接进入策略；
- horizon / risk / sector / ensemble score 的受控接入；
- replay actions 增加 `window` / schema version 的后续建议。

### 3.2 Core contract 未被弱化

`EXTENSIBLE_CONTRACT_CAPABILITY_DESIGN_CN.md` 继续冻结以下核心字段：

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

并明确：

- extension 不得改写 core fields 语义；
- extension 不得替代 `candidate_rank`、`buy_score`、`full_qlib_rank`；
- 若要替代，必须进入新 contract version 和单独审查。

### 3.3 Extension 机制方向正确

`MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md` 明确：

- extension 字段必须显式声明；
- 字段推荐 `ext_` 前缀；
- 必须声明 dtype、semantic_role、availability_policy、producer、allowed_consumers、ranking_allowed、required_for_core_replay、description；
- horizon / risk / sector / ensemble score 不能静默替代 core ranking；
- forbidden fields 和 legacy 私有列名不得作为 extension 策略输入。

### 3.4 Strategy dependency 方向正确

`STRATEGY_DEPENDENCY_CONTRACT_CN.md` 明确：

- 策略必须声明 required core fields；
- 策略必须声明 required capabilities；
- extension 依赖必须声明 field、semantic_role、usage、required；
- `one_sell_one_buy_buggy_e8r` 仍为 diagnostic only；
- strategy dependency 不能触发 replay、训练、默认策略切换、provider、accepted latest、monitor、broker 或 order。

### 3.5 Validator skeleton 可编译并可运行 core validation

复核命令：

```bash
python -m py_compile scripts/validate_tw_modular_artifact_contract.py
python scripts/validate_tw_modular_artifact_contract.py \
  --artifact data_tw/artifacts/signals/fresh_qlib_adaptive/r1_legacy_signal_adapter_20260616/manifest.json \
  --json
```

结果：

```text
py_compile: pass
validator ok: true
artifact_type: pass
signals_file_declared: pass
core_fields: pass
duplicate_key: pass
forbidden_fields: pass
extension_fields_declared: pass
extension_name_prefix: pass
strategy_required_core_fields: pass
strategy_required_capabilities: pass
strategy_required_extensions: pass
```

### 3.6 R3 未改 R2 replay / 前端 / 日更

复核：

```bash
git diff -- data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix \
  scripts/run_tw_modular_config_replay_matrix.py \
  scripts/run_extended_oos_formal_replay_matrix.py \
  frontend/src/views/tw-stock-monitor/index.vue \
  scripts/run_daily_tw_stock_auto_update.py
```

结果为空。

说明：

- `scripts/run_extended_oos_formal_replay_matrix.py` 和 `scripts/run_tw_modular_config_replay_matrix.py` 在当前工作区仍显示为未跟踪文件；
- 本次 R3 复审以 `git diff` 为空确认没有 tracked R3 范围外修改。

## 4. 残余风险

### 4.1 Validator 仍是 skeleton，不是完整实现

当前 validator 已实现：

- artifact type；
- signals file；
- core fields；
- duplicate key；
- forbidden fields；
- extension 是否声明；
- extension 名称是否 `ext_`；
- dependency required core fields；
- dependency required capabilities；
- dependency required extensions 的 field / semantic_role。

但尚未完整实现：

- extension metadata 完整性检查；
- dtype 可解析检查；
- availability_policy / PIT 检查；
- `allowed_consumers` 与 strategy usage 匹配；
- `ranking_allowed=false` 不得用于 ranking 的检查；
- `required_for_core_replay=false` 的边界检查；
- diagnostic-only strategy 输出范围检查；
- dependency 中 forbidden_fields / forbidden_actions 的完整校验；
- capability registry 与 artifact manifest 的版本兼容检查。

这些应进入 R4。

### 4.2 R1/R2 manifest 尚未 backfill capabilities

R3 报告已说明当前 R1 manifest 尚未声明 `capabilities`。因此：

- 不带 strategy dependency 时 validator 可验证 core contract；
- 一旦启用 strategy dependency，必须先给 R1/R2 manifest 补齐 capabilities metadata；
- backfill 必须只改 metadata，不得改变 signals.csv、replay 结果或 parity。

### 4.3 缺少 registry yaml 实体

R3 设计了：

```text
configs/tw_modular_registry.yaml
configs/strategy_dependencies/{strategy_rule}.yaml
```

但本阶段未落地这些 registry/dependency 文件。这符合 R3 设计范围，但 R4 应优先补。

## 5. R4 建议方向

建议 R4 主题：

```text
Validator / Registry / Capability Metadata Backfill
```

目标：

- 把 R3 的设计落成可执行、只读、可测试的 validator；
- 新增 registry yaml 和基础 strategy dependency yaml；
- 给 R1/R2 artifact manifest 补 capabilities metadata；
- 保持 R2 replay parity 不变；
- 不接入前端、日更或生产链路。

## 6. R4 建议产出

建议新增：

```text
configs/tw_modular_registry.yaml
configs/strategy_dependencies/original.yaml
configs/strategy_dependencies/top50_exit_all.yaml
configs/strategy_dependencies/top50_exit_one_worst_sell.yaml
configs/strategy_dependencies/one_sell_one_buy_correct.yaml
configs/strategy_dependencies/one_sell_one_buy_buggy_e8r.yaml
tests/unit/test_validate_tw_modular_artifact_contract.py
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER4_VALIDATOR_REGISTRY_EXECUTION_REPORT_CN.md
```

可修改：

```text
scripts/validate_tw_modular_artifact_contract.py
```

仅允许 metadata backfill：

```text
data_tw/artifacts/signals/*/r1_legacy_signal_adapter_20260616/manifest.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
```

Backfill 禁止改变：

```text
signals.csv
formal_replay_summary.csv
formal_replay_actions.csv
formal_replay_daily_nav.csv
```

## 7. R4 必须实现的 validator 检查

R4 validator 至少实现：

1. core fields 完整；
2. duplicate key 为 0；
3. forbidden fields / prefixes 不存在；
4. extension 字段必须 `ext_` 前缀；
5. signals.csv 中 extension 必须在 manifest 声明；
6. manifest 声明的 extension 必须在 signals.csv 存在；
7. extension metadata 必须完整；
8. extension dtype 可解析；
9. `availability_policy` 支持 PIT；
10. strategy required core fields 完整；
11. strategy required capabilities 满足；
12. strategy required extensions 满足；
13. `allowed_consumers` 与 dependency usage 匹配；
14. `ranking_allowed=false` 不得用于 ranking usage；
15. diagnostic-only rule 不得作为 valid strategy evidence；
16. registry 中声明的 dependency path 均存在；
17. manifest schema / contract version 可追溯。

## 8. R4 禁止事项

R4 禁止：

- 训练 qlib 或 LTR；
- 调参；
- 重算模型分数；
- 根据收益筛选模型；
- 修改 replay 结果；
- 修改旧 formal replay matrix；
- 修改默认策略；
- 修改前端；
- 修改日更脚本；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker、quick-trade 或 order 行为。

## 9. 给执行者的 R4 指令

请在 R3 审查通过后执行 R4：实现 validator / registry / capability metadata backfill。

只允许做：

- 完善只读 validator；
- 新增 registry yaml；
- 新增 strategy dependency yaml；
- 给 R1/R2 manifest 补 capabilities metadata；
- 新增 validator 单元测试；
- 写 R4 执行报告。

不得改变 R1 signals、R2 replay summary/actions/daily_nav，也不得接入前端、日更或生产链路。
