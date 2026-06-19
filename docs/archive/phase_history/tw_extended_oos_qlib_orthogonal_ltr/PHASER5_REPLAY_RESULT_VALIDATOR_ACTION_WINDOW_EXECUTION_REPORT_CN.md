# Phase R5 ReplayResult Validator + Action Window 执行报告

生成日期：2026-06-16

## 1. 执行范围

根据 `PHASER4_REVIEW_AND_NEXT_WORK_CN.md`，本阶段执行：

```text
ReplayResult validator + action window compatibility
```

目标：

- 为 modular replay actions 增加 `window` 字段；
- 保持旧 baseline parity；
- 增加 ReplayResultArtifact validator；
- 补全 validator 负例测试；
- 不改策略语义，不改默认策略，不接生产链路。

## 2. 修改文件

修改：

```text
scripts/run_tw_modular_config_replay_matrix.py
scripts/validate_tw_modular_artifact_contract.py
tests/unit/test_validate_tw_modular_artifact_contract.py
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_actions.csv
```

新增：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER5_REPLAY_RESULT_VALIDATOR_ACTION_WINDOW_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER5_REPLAY_RESULT_VALIDATOR_ACTION_WINDOW_REVIEW_HANDOFF_CN.md
```

说明：`formal_replay_actions.csv` 仅新增 `window` 字段，action key parity 仍按旧 baseline 兼容口径验证，策略行为未改变。

## 3. Action Window Compatibility

`formal_replay_actions.csv` 已新增：

```text
window
```

当前 modular actions header：

```text
action,effective_nav_date,execution_date,fee_and_tax,method,price,quantity,reason,rule,signal_date,symbol,window
```

旧 baseline actions 没有 `window` 字段，因此 action parity 继续使用 R2 审查通过的兼容口径：

```text
baseline_actions_prefix_by_2026_ytd_summary_action_plus_skipped_count
```

action key 仍为：

```text
method
rule
signal_date
execution_date
symbol
action
quantity
price
reason
```

value parity 仍检查：

```text
fee_and_tax
effective_nav_date
```

## 4. ReplayResult Validator

`scripts/validate_tw_modular_artifact_contract.py` 已新增 `ReplayResultArtifact` 校验：

- `artifact_type == replay_result`；
- `schema_version` / `contract_version` 存在；
- summary / daily_nav / actions / snapshots / coverage / integrity / forbidden audit 文件存在；
- actions 包含 `window`；
- active actions 满足 `execution_date > signal_date`；
- active quantity > 0；
- position integrity audit 无 duplicate / nonpositive / bad execution；
- coverage audit 无 fail；
- forbidden field audit 无 fail；
- parity audit 无 fail；
- action key parity audit 无 fail；
- manifest `parity_status == pass`。

## 5. 负例测试扩展

`tests/unit/test_validate_tw_modular_artifact_contract.py` 已从 4 个正例扩展到 12 个测试，新增覆盖：

- ReplayResult manifest 正例；
- forbidden extension；
- missing capability；
- bad dtype；
- bad PIT policy；
- undeclared extension；
- declared extension missing in signals；
- `ranking_allowed=false` 但 dependency 用于 ranking；
- buggy_e8r 缺少 `not_valid_strategy_evidence`；
- registry dependency path missing。

## 6. 验证结果

执行：

```bash
python -m py_compile scripts/run_tw_modular_config_replay_matrix.py scripts/validate_tw_modular_artifact_contract.py
python scripts/run_tw_modular_config_replay_matrix.py --config configs/tw_modular_replay_matrix.yaml
python scripts/validate_tw_modular_artifact_contract.py \
  --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json \
  --json
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

结果：

```text
py_compile: pass
R2/R5 replay rerun: parity_status pass
ReplayResult validator: ok=true
pytest: 12 passed
```

当前 `r2_action_key_parity_audit.csv`：

```text
baseline_filtered_rows: 3651
modular_action_rows: 3651
baseline_not_modular_count: 0
modular_not_baseline_count: 0
duplicate_baseline_action_key_count: 0
duplicate_modular_action_key_count: 0
value_mismatch_count: 0
status: pass
```

## 7. 禁止事项记录

本阶段：

- 未训练 qlib 或 LTR；
- 未调参；
- 未重算模型分数；
- 未根据收益筛选模型；
- 未修改默认策略；
- 未修改前端；
- 未修改日更脚本；
- 未触发 provider publish；
- 未切换 accepted latest；
- 未触发 monitor scan/config save；
- 未触发 broker、quick-trade 或 order。

## 8. 残余风险

旧 baseline actions 仍无 `window` 字段，baseline action parity 仍依赖 prefix 口径。modular replay 已补 `window`，后续若要彻底消除 prefix 依赖，需要生成带 window 的新版 baseline 或迁移全部比较到 modular artifact lineage。
