# Phase P3RRR 执行报告：Orthogonal Source Freshness Repair

生成时间：`2026-06-15T15:38:00+00:00`

## 1. 结论

- gate：`phase_p3rr_orthogonal_daily_feature_refresh_integrated`。
- signal_asof：`2026-06-15`。
- P3RRR 源 freshness 修复结果：FinMind institutional / margin 源响应均可覆盖到 `2026-06-15`。
- P3RR builder 重跑结果：`orthogonal_refresh_status = current_or_pit_delayed`。
- P3 rerank 重跑结果：`status = ready`，`pit_pass = true`，Top50 输入 50、成功评分 50、缺分 0。
- 本阶段未训练 qlib / LTR，未调参，未扩大 Top50，未切换 accepted latest，未触发 provider / monitor / broker / orders / quick-trade。

## 2. Root Cause

P3RR 初始降级不是 FinMind 源天然延迟导致。P3RRR 只读源 freshness repair 证明：

| feature_family | attempts | success_attempts | raw_rows | normalized_rows | latest_trade_date | empty_symbols |
| --- | --- | --- | --- | --- | --- | --- |
| institutional_flow | 50 | 50 | 750 | 150 | 2026-06-15 |  |
| margin_short | 50 | 50 | 150 | 150 | 2026-06-15 |  |

实际缺口是 P3RR 最新特征构建链路未消费 P3RRR raw archive，且当前执行环境 DB 查询不可用：

```text
db_status = db_failed
db_error = RuntimeError: DATABASE_URL environment variable is not set.
```

因此本次修复使用 P3RRR raw archive 作为只读 fallback，并重跑 latest orthogonal feature table builder。

## 3. Daily Auto Scope

- `scripts/run_daily_tw_stock_auto_update.py` 的 `--finmind-scope` 默认值为 `full`。
- 只有显式传入 `--finmind-scope daily` 时才跳过 institutional / margin。
- 本次根因不是 daily auto 默认配置跳过。
- P3 daily branch 仍是可选只读分支：`--run-p3-ltr` / `TW_DAILY_AUTO_RUN_P3_LTR`，不影响 fresh qlib 默认链路。

## 4. Source Delay 判断

FinMind 源响应本身不是 stale：

- `TaiwanStockInstitutionalInvestorsBuySell`：50/50 symbol 成功，最新 trade_date `2026-06-15`。
- `TaiwanStockMarginPurchaseShortSale`：50/50 symbol 成功，最新 trade_date `2026-06-15`。

但 P3 / O4 特征合同仍是 PIT-safe delayed availability：

```text
available_at >= next_trading_day(trade_date)
as-of join uses available_at <= signal_asof
```

因此在 `signal_asof = 2026-06-15` 下，特征表可合法使用的最新交易日是 `2026-06-12`，其 `available_at = 2026-06-15`。`2026-06-15` 当日源记录虽然已在 raw archive 中可审计存在，但按 T+1 合同不得进入同日 signal 特征。

## 5. 修复后 Freshness / Gate

重跑 `scripts/build_p3rr_latest_orthogonal_features.py` 后：

```text
status = current_or_pit_delayed
latest_feature_table = data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/latest_orthogonal_features_2026-06-15.csv
institutional_latest_trade_date = 2026-06-12
institutional_latest_available_at = 2026-06-15
margin_latest_trade_date = 2026-06-12
margin_latest_available_at = 2026-06-15
failed_symbols = []
stale_feature_families = []
```

重跑 `scripts/run_tw_ltr_p3_daily_rerank_readonly.py` 与 `scripts/audit_phasep3rr_orthogonal_refresh.py` 后：

```text
gate = phase_p3rr_orthogonal_daily_feature_refresh_integrated
orthogonal_refresh_status = current_or_pit_delayed
p3_rerank_uses_latest_feature_table = true
p3_candidate_status = ready
pit_pass = true
```

## 6. Fresh Qlib 默认链路

Fresh qlib 默认链路不受影响：

- `fresh_qlib_default_unaffected = true`
- `p3rr_failure_blocks_fresh_qlib = false`
- `accepted_latest_mutated_by_p3rr = false`
- `provider_mutated_by_p3rr = false`
- `monitor_trading_mutated_by_p3rr = false`

本阶段只生成 P3/P3RR/P3RRR artifact 与审计报告。

## 7. 只读安全边界

已保持边界：

- 未训练 qlib。
- 未训练 LTR。
- 未改 O4 model / feature whitelist。
- 未扩大 qlib Top50。
- 未切换 accepted latest。
- 未 provider publish / refresh。
- 未 monitor scan / config / alerts。
- 未 broker / orders / quick-trade。
- 未生成 target position / target weight。
- 未输出收益、胜率或上涨概率承诺。

## 8. 关键 Artifact

| artifact | path |
| --- | --- |
| source freshness summary | `data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/source_freshness_summary_2026-06-15.csv` |
| source freshness attempts | `data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/source_freshness_attempts_2026-06-15.csv` |
| source freshness manifest | `data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/source_freshness_manifest_2026-06-15.json` |
| P3RRR raw archive | `data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/source_freshness_raw_archive/` |
| latest feature table | `data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/latest_orthogonal_features_2026-06-15.csv` |
| latest feature refresh status | `data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/latest_orthogonal_features_2026-06-15_refresh_status.json` |
| P3 rerank summary | `data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-15_summary.json` |
| P3RR audit | `data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-15_p3rr_refresh_audit.json` |
| P3 report | `docs/tw_ltr_orthogonal_features_controlled/PHASEP3_DAILY_LTR_RERANK_READONLY_EXECUTION_REPORT_CN.md` |
| P3RR report | `docs/tw_ltr_orthogonal_features_controlled/PHASEP3RR_ORTHOGONAL_DAILY_FEATURE_REFRESH_EXECUTION_REPORT_CN.md` |
| P3RRR report | `docs/tw_ltr_orthogonal_features_controlled/PHASEP3RRR_ORTHOGONAL_SOURCE_FRESHNESS_REPAIR_EXECUTION_REPORT_CN.md` |

## 9. 执行命令

```text
python -m py_compile scripts/build_p3rr_latest_orthogonal_features.py scripts/run_tw_ltr_p3_daily_rerank_readonly.py scripts/run_daily_tw_stock_auto_update.py scripts/audit_phasep3rr_orthogonal_refresh.py scripts/repair_p3rrr_orthogonal_source_freshness.py
python scripts/build_p3rr_latest_orthogonal_features.py
python scripts/run_tw_ltr_p3_daily_rerank_readonly.py
python scripts/audit_phasep3rr_orthogonal_refresh.py
```

注：Python 链路在默认 sandbox 下被 `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted` 拦截，实际生成步骤以提升权限执行；命令本身只写本阶段 artifact 与报告。
