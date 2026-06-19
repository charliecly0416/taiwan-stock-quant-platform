# Phase R4 Validator / Registry / Capability Metadata Backfill 执行报告

生成日期：2026-06-16

## 1. 执行范围

本次执行 R4：实现 validator / registry / capability metadata backfill。

本次只做：

- 完善只读 validator；
- 新增 registry yaml；
- 新增 strategy dependency yaml；
- 给 R1/R2 manifest 补 capabilities metadata；
- 新增 validator 单元测试；
- 写执行报告和审查 handoff。

本次未修改 R1 `signals.csv`，未修改 R2 replay `summary/actions/daily_nav`，未接入前端、日更或生产链路。

## 2. 新增 / 修改文件

新增：

```text
configs/tw_modular_registry.yaml
configs/strategy_dependencies/original.yaml
configs/strategy_dependencies/top50_exit_all.yaml
configs/strategy_dependencies/top50_exit_one_worst_sell.yaml
configs/strategy_dependencies/one_sell_one_buy_correct.yaml
configs/strategy_dependencies/one_sell_one_buy_buggy_e8r.yaml
tests/unit/test_validate_tw_modular_artifact_contract.py
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER4_VALIDATOR_REGISTRY_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER4_VALIDATOR_REGISTRY_REVIEW_HANDOFF_CN.md
```

修改：

```text
scripts/validate_tw_modular_artifact_contract.py
data_tw/artifacts/signals/*/r1_legacy_signal_adapter_20260616/manifest.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
```

Manifest 修改仅为 metadata backfill：

- `capabilities`
- `extensions`
- `capability_backfill`
- R2 replay manifest 的 `schema_version` / `contract_version`

## 3. Validator 已实现检查

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
16. registry 中声明的 dependency path 均存在；
17. manifest schema / contract version 可追溯。

## 4. Capability Backfill

R1 signal manifests 已补：

```json
{
  "capabilities": {
    "core_signal_v1": true,
    "candidate_boundary": "qlib_top50",
    "buy_ordering": "buy_score_desc",
    "full_rank_exit": "full_qlib_rank",
    "pit_available_at_checked": true
  },
  "extensions": {
    "schema_version": "model_signal_extension_v1",
    "fields": {}
  }
}
```

R2 replay manifest 已补：

```json
{
  "schema_version": "replay_result_r2.1",
  "contract_version": "REPLAY_RESULT_CONTRACT_CN.md@2026-06-16",
  "capabilities": {
    "config_driven_replay_matrix": true,
    "model_signal_manifest_input": true,
    "summary_parity_2026_ytd": true,
    "daily_nav_parity_2026_ytd": true,
    "action_key_parity_2026_ytd": true,
    "readonly_research_artifact": true
  }
}
```

## 5. 验证结果

执行：

```bash
python -m py_compile scripts/validate_tw_modular_artifact_contract.py
python scripts/validate_tw_modular_artifact_contract.py \
  --artifact data_tw/artifacts/signals/fresh_qlib_adaptive/r1_legacy_signal_adapter_20260616/manifest.json \
  --strategy-dependency configs/strategy_dependencies/top50_exit_one_worst_sell.yaml \
  --json
python scripts/validate_tw_modular_artifact_contract.py \
  --artifact data_tw/artifacts/signals/fresh_qlib_adaptive/r1_legacy_signal_adapter_20260616/manifest.json \
  --registry configs/tw_modular_registry.yaml \
  --json
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

结果：

```text
py_compile: pass
strategy dependency validation: ok=true
registry validation: ok=true
pytest: 4 passed
```

## 6. 禁止事项记录

本次 R4：

- 未训练 qlib 或 LTR；
- 未调参；
- 未重算模型分数；
- 未根据收益筛选模型；
- 未修改 replay 结果 CSV；
- 未修改旧 formal replay matrix；
- 未修改默认策略；
- 未修改前端；
- 未修改日更脚本；
- 未触发 provider publish；
- 未切换 accepted latest；
- 未触发 monitor scan/config save；
- 未触发 broker、quick-trade 或 order。

## 7. 后续建议

下一阶段若继续推进，建议优先：

- 给 replay actions 增加 `window` 字段并保持 R2 parity；
- 增加 validator 对 ReplayResultArtifact 的完整校验；
- 增加负例测试覆盖 forbidden extension、missing capability、bad dtype、ranking_allowed=false 等。
