# Phase R3 可扩展 Contract / Capability 设计执行报告

生成日期：2026-06-16

## 1. 执行范围

本次执行 R3：设计可扩展 contract / capability / strategy dependency 机制，并新增只读 validator skeleton。

本次未修改 R2 replay 输出，未修改旧 formal replay matrix，未接入前端、日更或生产链路。

## 2. 新增产物

```text
docs/tw_modular_contracts/EXTENSIBLE_CONTRACT_CAPABILITY_DESIGN_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
docs/tw_modular_contracts/STRATEGY_DEPENDENCY_CONTRACT_CN.md
scripts/validate_tw_modular_artifact_contract.py
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER3_EXTENSIBLE_CONTRACT_DESIGN_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER3_EXTENSIBLE_CONTRACT_DESIGN_REVIEW_HANDOFF_CN.md
```

## 3. R3 回答的问题

### 3.1 Immutable core fields

已在 `EXTENSIBLE_CONTRACT_CAPABILITY_DESIGN_CN.md` 中冻结：

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

这些字段不得被 extension 改写语义。

### 3.2 Optional extension fields

已定义 extension 命名、metadata、semantic_role、availability_policy、allowed_consumers、ranking_allowed、required_for_core_replay。

### 3.3 Manifest capabilities

已定义 artifact 通过 `capabilities` 声明：

- core signal version；
- candidate boundary；
- buy ordering；
- full-rank exit；
- PIT 可见性；
- optional extension support。

### 3.4 Strategy dependencies

已定义 strategy dependency yaml：

```text
configs/strategy_dependencies/{strategy_rule}.yaml
```

策略必须声明 required core fields、required capabilities、required extensions、diagnostic_only 等。

### 3.5 Validator 判断方式

新增 `scripts/validate_tw_modular_artifact_contract.py` skeleton，可只读检查：

- artifact type；
- signals file；
- core fields；
- duplicate key；
- forbidden fields；
- extension schema；
- strategy required core fields；
- required capabilities；
- required extensions；
- diagnostic boundary。

### 3.6 Forbidden fields/actions

三个 R3 文档和 validator skeleton 继续全局禁止：

- future label / return；
- realized PnL；
- execution / broker / order 字段；
- legacy 私有 score/rank 字段直接作为策略输入；
- provider publish / accepted latest / monitor / broker / order actions。

### 3.7 Horizon / risk / sector / ensemble 扩展

`MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md` 已分别定义：

- horizon score 默认不得替代 `buy_score`；
- risk score 必须声明是否影响 order intent；
- sector / exposure 只允许 sector-aware strategy 显式消费；
- ensemble score 若用于 ranking，必须作为新 strategy 或新 core contract version 审查。

### 3.8 ReplayResult 后续增强

`EXTENSIBLE_CONTRACT_CAPABILITY_DESIGN_CN.md` 和 R2 复审风险共同建议后续为 replay actions 增加 `window` / schema version 等更强审计字段，避免依赖 baseline prefix 推断。

## 4. Validator 验证

已用 R1 artifact 做只读验证：

```bash
python scripts/validate_tw_modular_artifact_contract.py \
  --artifact data_tw/artifacts/signals/fresh_qlib_adaptive/r1_legacy_signal_adapter_20260616/manifest.json \
  --json
```

预期：`ok=true`。

说明：当前 R1 manifest 尚未声明 `capabilities`，因此不带 strategy dependency 时 validator 可验证 core contract；未来新增 strategy dependency 后必须补齐 manifest capabilities。

## 5. 禁止事项记录

本次 R3：

- 未训练 qlib 或 LTR；
- 未调参；
- 未重算模型分数；
- 未根据收益筛选模型；
- 未修改 R2 replay 输出；
- 未修改旧 formal replay matrix；
- 未修改默认策略；
- 未修改前端；
- 未修改日更脚本；
- 未触发 provider publish；
- 未切换 accepted latest；
- 未触发 monitor scan/config save；
- 未触发 broker、quick-trade 或 order。

## 6. 后续建议

后续若进入 R4，应先由审查者确认：

- 是否只做 validator 完整实现；
- 是否补 `configs/tw_modular_registry.yaml`；
- 是否给 R1/R2 manifest 增补 capability metadata；
- 是否给 replay actions 增加 `window` 字段并重新做 parity。
