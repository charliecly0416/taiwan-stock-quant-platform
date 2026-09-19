# DNG6 Daily Auto Catalog Integration 审查工作文档

生成日期：2026-06-29

## 1. 审查输入

```text
docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md
docs/tw_data_governance/DNG6_DAILY_AUTO_CATALOG_INTEGRATION_WORK_CN.md
docs/tw_data_governance/DNG6_DAILY_AUTO_CATALOG_INTEGRATION_EXECUTION_REPORT_CN.md
scripts/build_tw_daily_readiness_dashboard.py
scripts/validate_tw_daily_readiness_dashboard.py
scripts/run_daily_tw_stock_auto_update.py
data_tw/catalog/daily_readiness_dashboard.json
data_tw/catalog/dng6_daily_readiness_dashboard_validation.json
```

## 2. 审查目标

判断 DNG6 是否安全接入 daily auto dashboard，是否可以进入 DNG7 ModelInferenceInput / qlib Model A score pipeline。

## 3. 必查项

1. dashboard required fields 是否完整。
2. partial/block 是否没有被标为 production ready。
3. daily auto 是否只新增 dashboard/status 集成。
4. 默认 provider publish / accepted latest / model signal gate / publish latest gate 是否仍关闭。
5. validator 是否通过。
6. 是否未触发 forbidden action。

## 4. 建议命令

```text
python -m py_compile scripts/build_tw_daily_readiness_dashboard.py scripts/validate_tw_daily_readiness_dashboard.py scripts/run_daily_tw_stock_auto_update.py
python scripts/validate_tw_daily_readiness_dashboard.py --dashboard data_tw/catalog/daily_readiness_dashboard.json --json
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
```

## 5. Verdict

审查结论只能是：

```text
PASS_GO_DNG7
PASS_WITH_CONDITIONS_GO_DNG7
FAIL_NEEDS_DNG6_REPAIR
STOP_COORDINATOR_DECISION_REQUIRED
```

## 6. 输出

审查者必须写：

```text
docs/tw_data_governance/DNG6_DAILY_AUTO_CATALOG_INTEGRATION_REVIEW_CN.md
```
