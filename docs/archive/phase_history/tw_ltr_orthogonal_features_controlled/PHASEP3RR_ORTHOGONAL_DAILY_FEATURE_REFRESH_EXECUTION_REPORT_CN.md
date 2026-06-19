# Phase P3RR 执行报告：Orthogonal Daily Feature Refresh Repair

生成时间：`2026-06-17T18:49:42+00:00`

## 1. 结论

- gate：`phase_p3rr_orthogonal_daily_feature_refresh_integrated`。
- asof：`2026-06-17`。
- orthogonal_refresh_status：`current_or_pit_delayed`。
- P3 candidate status：`ready`。
- PIT pass：`True`。

## 2. 日更来源确认

- 真实日更入口：`scripts/run_daily_tw_stock_auto_update.py`。
- `backend/scripts/update_tw_stock_daily.py` 默认抓取 `TaiwanStockInstitutionalInvestorsBuySell` 与 `TaiwanStockMarginPurchaseShortSale`；只有 `--finmind-scope daily` 才会跳过 institutional/margin。
- P3RR builder：`scripts/build_p3rr_latest_orthogonal_features.py`。
- daily optional branch 先运行 P3RR builder，再运行 frozen O4 P3 rerank。

## 3. Latest Feature Table

- latest feature table：`data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/latest_orthogonal_features_2026-06-17.csv`。
- created_at：`2026-06-17T18:48:55+00:00`。
- P3 rerank uses latest table：`True`。

## 4. Raw / Freshness

- raw institutional latest trade_date：`2026-06-16`。
- raw margin latest trade_date：`2026-06-16`。
- institutional latest trade_date / available_at：`2026-06-16` / `2026-06-17`。
- margin latest trade_date / available_at：`2026-06-16` / `2026-06-17`。
- row_count_by_family：`{'institutional_flow': 53551, 'margin_short': 53224}`。
- failed_symbols：`[]`。
- stale_feature_families：`[]`。

## 5. Gate 修正

如果 `orthogonal_refresh_status = stale_degraded`，本阶段不得给完整通过 gate。当前 gate 已按此修正。

## 6. Failure Isolation / Safety

- fresh qlib 默认链路不受影响：`True`。
- P3RR failure blocks fresh qlib：`False`。
- accepted latest mutated by P3RR：`False`。
- provider mutated by P3RR：`False`。
- monitor/trading mutated by P3RR：`False`。
- 未训练 qlib / LTR，未调参，未扩大 Top50，未写 accepted latest。

## 7. 输出 Artifact

| artifact | path | exists |
| --- | --- | --- |
| latest_orthogonal_features_2026-06-17.csv | data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/latest_orthogonal_features_2026-06-17.csv | True |
| latest_orthogonal_features_2026-06-17_refresh_status.json | data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/latest_orthogonal_features_2026-06-17_refresh_status.json | True |
| latest_orthogonal_features_latest.json | data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/latest_orthogonal_features_latest.json | True |
| daily_ltr_rerank_2026-06-17_summary.json | data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-17_summary.json | True |
| daily_ltr_rerank_2026-06-17_orthogonal_refresh_status.json | data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-17_orthogonal_refresh_status.json | True |
| daily_ltr_rerank_2026-06-17_p3rr_refresh_audit.json | data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-17_p3rr_refresh_audit.json | True |

## 8. 运行命令

```text
python -m py_compile scripts/build_p3rr_latest_orthogonal_features.py scripts/run_tw_ltr_p3_daily_rerank_readonly.py scripts/run_daily_tw_stock_auto_update.py scripts/audit_phasep3rr_orthogonal_refresh.py
python scripts/build_p3rr_latest_orthogonal_features.py
python scripts/run_tw_ltr_p3_daily_rerank_readonly.py
python scripts/audit_phasep3rr_orthogonal_refresh.py
```

## 9. 剩余风险

- 若当前 raw/data source 仍落后于 signal asof，gate 保持 degraded，不声称正交日更完整闭环。
- 不接 UI/reader，不触发 provider/accepted latest/monitor/trading。
