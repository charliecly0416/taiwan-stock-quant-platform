# DNG1 DataCatalog 审查工作文档

生成日期：2026-06-29

## 1. 审查输入

```text
docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md
docs/tw_data_governance/DNG1_DATA_CATALOG_WORK_CN.md
docs/tw_data_governance/DNG1_DATA_CATALOG_EXECUTION_REPORT_CN.md
scripts/build_tw_data_catalog.py
scripts/validate_tw_data_catalog.py
data_tw/catalog/data_catalog.json
data_tw/catalog/latest_status.json
data_tw/catalog/data_catalog_summary.csv
data_tw/catalog/data_catalog_validation.json
```

## 2. 审查目标

判断 DNG1 是否成功建立保守的 DataCatalog scanner/validator，是否可以进入 DNG2 PriceStore/TWII/Calendar 规范化。

## 3. 必查项

1. scanner 是否只读。
2. validator 是否可运行并输出 JSON。
3. `data_catalog.json` 是否包含 required fields。
4. `latest_status.json` 是否覆盖所有 latest concepts。
5. 是否把 bridge/experiment/legacy/缺 evidence 路径降级处理，未伪装 READY。
6. 是否有 status 分布和 known_mismatch。
7. 是否没有触发 forbidden actions。
8. 是否指出 DNG2 需要优先处理 PriceStore/TWII/Calendar。

## 4. 建议命令

```text
python -m py_compile scripts/build_tw_data_catalog.py scripts/validate_tw_data_catalog.py
python scripts/validate_tw_data_catalog.py --catalog data_tw/catalog/data_catalog.json --latest-status data_tw/catalog/latest_status.json --json
```

## 5. Verdict

审查结论只能是：

```text
PASS_GO_DNG2
PASS_WITH_CONDITIONS_GO_DNG2
FAIL_NEEDS_DNG1_REPAIR
STOP_COORDINATOR_DECISION_REQUIRED
```

## 6. 输出

审查者必须写：

```text
docs/tw_data_governance/DNG1_DATA_CATALOG_REVIEW_CN.md
```

若通过，末尾必须写 DNG2 的重点约束。
