# Phase R4 审查与后续工作建议

生成日期：2026-06-16

## 1. 审查结论

R4 审查通过。

本次 R4 符合范围：实现 validator / registry / strategy dependency / capability metadata backfill，未改变 R1 `signals.csv`，未改变 R2 replay `summary/actions/daily_nav`，未接入前端、日更或生产链路。

当前 validator 已从 R3 skeleton 前进到可用的只读校验器，能验证 core fields、forbidden fields、extension metadata、strategy capabilities、registry dependency path 和 diagnostic boundary。

残余风险：测试目前主要覆盖正例，负例测试仍不足。下一阶段应优先补 forbidden extension、missing capability、bad dtype、ranking_allowed=false 等负例。

## 2. 审查对象

R4 handoff：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER4_VALIDATOR_REGISTRY_REVIEW_HANDOFF_CN.md
```

R4 执行报告：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER4_VALIDATOR_REGISTRY_EXECUTION_REPORT_CN.md
```

Registry：

```text
configs/tw_modular_registry.yaml
```

Strategy dependency：

```text
configs/strategy_dependencies/original.yaml
configs/strategy_dependencies/top50_exit_all.yaml
configs/strategy_dependencies/top50_exit_one_worst_sell.yaml
configs/strategy_dependencies/one_sell_one_buy_correct.yaml
configs/strategy_dependencies/one_sell_one_buy_buggy_e8r.yaml
```

Validator：

```text
scripts/validate_tw_modular_artifact_contract.py
tests/unit/test_validate_tw_modular_artifact_contract.py
```

Metadata backfill：

```text
data_tw/artifacts/signals/*/r1_legacy_signal_adapter_20260616/manifest.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
```

## 3. 复核结果

### 3.1 Validator 编译与测试通过

复核命令：

```bash
python -m py_compile scripts/validate_tw_modular_artifact_contract.py
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

结果：

```text
py_compile: pass
pytest: 4 passed
```

### 3.2 Strategy dependency validation 通过

复核命令：

```bash
python scripts/validate_tw_modular_artifact_contract.py \
  --artifact data_tw/artifacts/signals/fresh_qlib_adaptive/r1_legacy_signal_adapter_20260616/manifest.json \
  --strategy-dependency configs/strategy_dependencies/top50_exit_one_worst_sell.yaml \
  --json
```

结果：

```text
ok: true
strategy_dependency: top50_exit_one_worst_sell
```

关键 checks 均 pass：

- artifact_type；
- schema_version；
- contract_version；
- core_fields；
- duplicate_key；
- forbidden_fields；
- extension metadata；
- strategy_required_core_fields；
- strategy_required_capabilities；
- strategy_required_extensions；
- ranking_allowed；
- dependency_forbidden_fields；
- dependency_forbidden_actions。

### 3.3 Registry validation 通过

复核命令：

```bash
python scripts/validate_tw_modular_artifact_contract.py \
  --artifact data_tw/artifacts/signals/fresh_qlib_adaptive/r1_legacy_signal_adapter_20260616/manifest.json \
  --registry configs/tw_modular_registry.yaml \
  --json
```

结果：

```text
ok: true
registry_version: tw_modular_registry_v1
registry_dependency_paths: pass
registry_contract_docs: pass
```

### 3.4 Strategy dependency 边界正确

五个 dependency yaml 均存在。

基础策略依赖：

- `original` 依赖 `candidate_rank` / `buy_score` / PIT fields；
- `top50_exit_all` 依赖 `candidate_rank` / `buy_score` / PIT fields；
- `top50_exit_one_worst_sell` 额外依赖 `full_qlib_rank`；
- `one_sell_one_buy_correct` 应依赖 `full_qlib_rank`；
- `one_sell_one_buy_buggy_e8r` 标记为：

```yaml
diagnostic_only: true
not_valid_strategy_evidence: true
allowed_outputs:
  - audit
  - diff
  - anomaly_attribution
```

未发现 buggy 规则被声明为 valid strategy evidence。

### 3.5 Metadata backfill 未改变核心 CSV

R1 signal manifest 已补：

```text
capabilities
extensions
capability_backfill
```

R2 replay manifest 已补：

```text
schema_version
contract_version
capabilities
capability_backfill
```

复核 R1 `signals.csv` header 未变化：

```text
date,instrument,model_name,model_family,candidate_rank,buy_score,raw_score,score_rank,full_qlib_rank,signal_asof,available_at,source_artifact,source_model_artifact,source_feature_artifact
```

R2 parity audit 仍为：

```text
summary pass
daily_nav pass
actions pass
```

### 3.6 范围外 diff 复核

以下对象 `git diff` 为空：

```text
data_tw/artifacts/signals/*/r1_legacy_signal_adapter_20260616/signals.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_summary.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_actions.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_daily_nav.csv
frontend/src/views/tw-stock-monitor/index.vue
scripts/run_daily_tw_stock_auto_update.py
scripts/run_extended_oos_formal_replay_matrix.py
```

说明：当前工作区大量 R0-R4 产物仍是未跟踪文件，因此 `git diff` 只能确认 tracked 文件未被改动；对未跟踪产物的审查以内容读取和 validator/test 结果为准。

## 4. 已实现能力

R4 validator 已实现：

1. core fields 完整；
2. duplicate key 为 0；
3. forbidden fields / prefixes 不存在；
4. extension 字段必须 `ext_` 前缀；
5. signals.csv 中 extension 必须在 manifest 声明；
6. manifest 声明的 extension 必须在 signals.csv 存在；
7. extension metadata 必须完整；
8. extension dtype 可解析；
9. `availability_policy` 必须属于受控 PIT policy；
10. strategy required core fields 完整；
11. strategy required capabilities 满足；
12. strategy required extensions 满足；
13. `allowed_consumers` 与 dependency usage 匹配；
14. `ranking_allowed=false` 不得用于 ranking usage；
15. diagnostic-only rule 必须标记 not valid evidence；
16. registry dependency path 存在；
17. manifest schema / contract version 可追溯。

## 5. 残余风险

### 5.1 负例测试不足

当前测试为 `4 passed`，主要覆盖：

- registry path 正例；
- core artifact 正例；
- base strategy dependency 正例；
- buggy_e8r diagnostic 正例。

仍需补充负例：

- forbidden extension；
- missing capability；
- bad dtype；
- undeclared extension；
- declared extension missing in signals；
- ranking_allowed=false 但 dependency 用于 ranking；
- bad PIT policy；
- buggy_e8r 缺少 `not_valid_strategy_evidence`；
- dependency path missing。

### 5.2 ReplayResult validator 仍未完整实现

R4 主要验证 `ModelSignalArtifact` 与 strategy dependency。R2 replay manifest 虽补了 capability metadata，但尚未有完整 ReplayResultArtifact validator。

下一阶段应补 ReplayResult validator，检查：

- summary/actions/daily_nav/position_snapshots/audit 文件存在；
- actions 是否含 `window`；
- execution_date > signal_date；
- active quantity > 0；
- max holding <= target；
- duplicate position = 0；
- forbidden field audit pass；
- parity audit pass。

### 5.3 `window` 字段仍未进入 replay actions

R2 仍依赖 baseline actions prefix 口径。后续应为 modular replay actions 增加 `window` 字段，并保持 R2 parity。

## 6. 后续建议

建议下一阶段优先做：

```text
ReplayResult validator + action window compatibility
```

目标：

- 为 modular replay actions 增加 `window` 字段；
- 保持旧 baseline parity；
- 增加 ReplayResultArtifact validator；
- 补全 validator 负例测试；
- 不改策略语义，不改默认策略，不接生产链路。

## 7. 禁止事项继续有效

后续阶段仍禁止：

- 训练 qlib 或 LTR；
- 调参；
- 重算模型分数；
- 根据收益筛选模型；
- 修改默认策略；
- 修改前端；
- 修改日更脚本；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker、quick-trade 或 order 行为。
