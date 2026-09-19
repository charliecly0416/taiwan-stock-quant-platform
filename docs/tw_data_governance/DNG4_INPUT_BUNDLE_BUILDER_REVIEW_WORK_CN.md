# DNG4 Input Bundle Builder 审查工作文档

生成日期：2026-06-29

## 1. 审查输入

```text
docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md
docs/tw_data_governance/DNG4_INPUT_BUNDLE_BUILDER_WORK_CN.md
docs/tw_data_governance/DNG4_INPUT_BUNDLE_BUILDER_EXECUTION_REPORT_CN.md
scripts/build_tw_strategy_input_bundle.py
scripts/validate_tw_strategy_input_bundle.py
scripts/build_tw_replay_input_bundle.py
scripts/validate_tw_replay_input_bundle.py
data_tw/artifacts/strategy_input_bundles/{bundle_id}/{run_id}/
data_tw/artifacts/replay_input_bundles/{bundle_id}/{run_id}/
data_tw/catalog/dng4_input_bundle_validation.json
```

## 2. 审查目标

判断 DNG4 是否成功建立 StrategyInputBundle / ReplayInputBundle builder 和 validator，是否可以进入 DNG5 RouteDataDependencyContract。

## 3. 必查项

1. bundle 是否有 manifest、dependency_readiness、lineage、validator_report。
2. StrategyInputBundle 是否只表示输入，不含交易建议。
3. ReplayInputBundle 是否不含 NAV、收益、turnover、performance。
4. partial / fallback 是否有明确 reason。
5. LTR Model B not ready 是否被正确标记。
6. validator 是否通过。
7. 是否未触发 forbidden action。

## 4. 建议命令

```text
python -m py_compile scripts/build_tw_strategy_input_bundle.py scripts/validate_tw_strategy_input_bundle.py scripts/build_tw_replay_input_bundle.py scripts/validate_tw_replay_input_bundle.py
python scripts/validate_tw_strategy_input_bundle.py --bundle-root <path> --json
python scripts/validate_tw_replay_input_bundle.py --bundle-root <path> --json
```

## 5. Verdict

审查结论只能是：

```text
PASS_GO_DNG5
PASS_WITH_CONDITIONS_GO_DNG5
FAIL_NEEDS_DNG4_REPAIR
STOP_COORDINATOR_DECISION_REQUIRED
```

## 6. 输出

审查者必须写：

```text
docs/tw_data_governance/DNG4_INPUT_BUNDLE_BUILDER_REVIEW_CN.md
```
