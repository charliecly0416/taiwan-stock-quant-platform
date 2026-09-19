# DNG2_R PriceStore / TWII / Calendar 覆盖修复审查工作文档

生成日期：2026-06-29

## 1. 审查输入

```text
docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md
docs/tw_data_governance/DNG2_R_PRICE_MARKET_CALENDAR_COVERAGE_REPAIR_WORK_CN.md
docs/tw_data_governance/DNG2_R_PRICE_MARKET_CALENDAR_COVERAGE_REPAIR_EXECUTION_REPORT_CN.md
scripts/build_tw_canonical_price_market_calendar.py
scripts/validate_tw_canonical_price_market_calendar.py
data_tw/catalog/dng2_price_market_calendar_validation.json
data_tw/catalog/readiness_matrix/{asof}/price_market_calendar.json
data_tw/canonical/price_store/tw_equity_daily/{repair_run_id}/
data_tw/canonical/market_feature_store/twii_daily/{repair_run_id}/
```

## 2. 审查目标

判断 DNG2_R 是否修复 DNG2 覆盖 blocker，是否可进入 DNG3，或是否必须停下来请求外部补源授权。

## 3. 必查项

1. 是否系统查找本地 TWII / market index source。
2. 是否未伪造 TWII。
3. halt/suspension evidence 是否存在。
4. next-day execution availability 是否区分 historical ready 与 latest pending。
5. readiness 是否拆成：

```text
can_continue_to_model_score
can_continue_to_replay
can_continue_to_shadow_execution
can_continue_to_dng3
```

6. validator 是否通过。
7. 是否未触发 forbidden action。

## 4. Verdict

审查结论只能是：

```text
PASS_GO_DNG3
PASS_WITH_CONDITIONS_GO_DNG3
FAIL_NEEDS_DNG2_R_REPAIR
STOP_EXTERNAL_SOURCE_REPAIR_REQUIRED
```

## 5. 输出

审查者必须写：

```text
docs/tw_data_governance/DNG2_R_PRICE_MARKET_CALENDAR_COVERAGE_REPAIR_REVIEW_CN.md
```

若 `STOP_EXTERNAL_SOURCE_REPAIR_REQUIRED`，必须说明缺什么数据、为什么本地无法补、需要哪类授权。
