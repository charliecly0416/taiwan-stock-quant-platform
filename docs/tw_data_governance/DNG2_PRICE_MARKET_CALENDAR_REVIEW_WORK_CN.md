# DNG2 PriceStore / TWII / Calendar 审查工作文档

生成日期：2026-06-29

## 1. 审查输入

```text
docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md
docs/tw_data_governance/DNG2_PRICE_MARKET_CALENDAR_WORK_CN.md
docs/tw_data_governance/DNG2_PRICE_MARKET_CALENDAR_EXECUTION_REPORT_CN.md
scripts/build_tw_canonical_price_market_calendar.py
scripts/validate_tw_canonical_price_market_calendar.py
data_tw/catalog/dng2_price_market_calendar_validation.json
data_tw/catalog/readiness_matrix/{asof}/price_market_calendar.json
data_tw/canonical/price_store/tw_equity_daily/{run_id}/
data_tw/canonical/market_feature_store/twii_daily/{run_id}/
```

## 2. 审查目标

判断 DNG2 是否成功建立 canonical PriceStore / TWII / Calendar / readiness 基础层，是否可以进入 DNG3 OrthogonalData 规范化。

## 3. 必查项

1. 是否只读复用本地数据，未抓数。
2. PriceStore 是否有 manifest/schema/prices/coverage/adjustment/execution/lineage。
3. TWII store 是否有 manifest/schema/twii/coverage/lineage。
4. readiness matrix 是否覆盖 price、TWII、calendar、next-day execution、mark-to-market、holiday evidence。
5. 如果产物是 partial，是否明确 blocker，未伪装 READY。
6. validator 是否可运行。
7. 是否没有模型 score、推理、回放、publish、latest switch。

## 4. 建议命令

```text
python -m py_compile scripts/build_tw_canonical_price_market_calendar.py scripts/validate_tw_canonical_price_market_calendar.py
python scripts/validate_tw_canonical_price_market_calendar.py --run-id <run_id> --asof <YYYY-MM-DD> --json
```

审查者需从执行报告或 manifest 找到 run_id/asof。

## 5. Verdict

审查结论只能是：

```text
PASS_GO_DNG3
PASS_WITH_CONDITIONS_GO_DNG3
FAIL_NEEDS_DNG2_REPAIR
STOP_COORDINATOR_DECISION_REQUIRED
```

## 6. 输出

审查者必须写：

```text
docs/tw_data_governance/DNG2_PRICE_MARKET_CALENDAR_REVIEW_CN.md
```

若通过，末尾必须写 DNG3 正交数据规范化的重点约束。
