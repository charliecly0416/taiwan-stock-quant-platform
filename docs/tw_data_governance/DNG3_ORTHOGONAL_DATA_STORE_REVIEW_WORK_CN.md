# DNG3 正交数据 Store 审查工作文档

生成日期：2026-06-29

## 1. 审查输入

```text
docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md
docs/tw_data_governance/DNG3_ORTHOGONAL_DATA_STORE_WORK_CN.md
docs/tw_data_governance/DNG3_ORTHOGONAL_DATA_STORE_EXECUTION_REPORT_CN.md
scripts/build_tw_orthogonal_feature_store.py
scripts/validate_tw_orthogonal_feature_store.py
data_tw/canonical/orthogonal_feature_store/daily_orthogonal/{run_id}/
data_tw/catalog/readiness_matrix/{asof}/orthogonal_feature_store.json
data_tw/catalog/dng3_orthogonal_feature_store_validation.json
```

## 2. 审查目标

判断 DNG3 是否成功把本地正交数据规范为 canonical store，并明确 LTR Model B 是否 ready；是否可以进入 DNG4 StrategyInputBundle / ReplayInputBundle builder。

## 3. 必查项

1. 是否未触发真实抓数。
2. 是否覆盖 institutional_flow、margin_short、corporate_actions、monthly_revenue、valuation 或明确缺失。
3. `features.csv` 是否有 long-form 最小字段。
4. provider_status 是否明确 quota/permission/missing/ready。
5. PIT/available_at 是否存在。
6. readiness 是否明确：

```text
can_continue_to_model_b_ltr
can_continue_to_model_score
can_continue_to_dng4
```

7. 是否没有模型 score、推理、回放、publish/latest switch。

## 4. 建议命令

```text
python -m py_compile scripts/build_tw_orthogonal_feature_store.py scripts/validate_tw_orthogonal_feature_store.py
python scripts/validate_tw_orthogonal_feature_store.py --run-id <run_id> --asof <YYYY-MM-DD> --json
```

## 5. Verdict

审查结论只能是：

```text
PASS_GO_DNG4
PASS_WITH_CONDITIONS_GO_DNG4
FAIL_NEEDS_DNG3_REPAIR
STOP_EXTERNAL_SOURCE_REPAIR_REQUIRED
```

## 6. 输出

审查者必须写：

```text
docs/tw_data_governance/DNG3_ORTHOGONAL_DATA_STORE_REVIEW_CN.md
```

若通过，必须说明 DNG4 是否可以先做 bundle contract，即使 LTR Model B 仍不 ready。
