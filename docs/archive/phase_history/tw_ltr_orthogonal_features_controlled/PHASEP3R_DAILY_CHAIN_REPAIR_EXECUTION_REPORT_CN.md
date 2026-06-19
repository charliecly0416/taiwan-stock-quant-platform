# Phase P3R 执行报告：Daily Chain Integration Repair

生成时间：`2026-06-15T15:18:12+00:00`

## 1. 结论

本轮修复 P3 只完成单次 readonly scoring、未闭环日更链路的问题。

- gate：`phase_p3r_daily_ltr_rerank_chain_integrated_and_audited`。
- asof：`2026-06-15`。
- 默认策略仍为：`fresh qlib / rank_rotate_top50_adaptive_score`。
- Top50 input/scored/missing：`50/50/0`。
- PIT pass：`True`。
- P3 candidate status：`ready`。

## 2. 改动文件

- `scripts/run_daily_tw_stock_auto_update.py`：新增 `--run-p3-ltr` optional branch，accepted latest 成功后才调用 P3；失败只写 job audit，不阻塞 fresh qlib 默认链路。
- `scripts/run_tw_ltr_p3_daily_rerank_readonly.py`：补充 orthogonal refresh status、failure isolation audit、reader/UI boundary。
- `docs/tw_ltr_orthogonal_features_controlled/PHASEP3R_DAILY_CHAIN_REPAIR_EXECUTION_REPORT_CN.md`：本执行报告。

## 3. 日更入口与调用点

- 日更入口：`scripts/run_daily_tw_stock_auto_update.py`。
- 调用方式：`python scripts/run_daily_tw_stock_auto_update.py --run-p3-ltr` 或设置 `TW_DAILY_AUTO_RUN_P3_LTR=true`。
- 调用点：fresh qlib accepted latest 成功后运行 `scripts/run_tw_ltr_p3_daily_rerank_readonly.py`。
- `already_up_to_date` 且显式开启 `--run-p3-ltr` 时，也可只刷新 optional candidate。

## 4. Orthogonal Refresh / Freshness

- orthogonal_refresh_status：`stale_degraded`。
- institutional latest trade_date / available_at：`2026-06-10` / `2026-06-11`。
- margin latest trade_date / available_at：`2026-06-10` / `2026-06-11`。
- refresh_failed_symbols：`[]`。
- stale_feature_families：`['institutional_flow', 'margin_short']`。

说明：本轮不新增数据源、不触发 provider/accepted latest/monitor/交易链路。若正交特征落后于 signal asof，P3 candidate 通过 `orthogonal_refresh_status` 标记 stale/degraded 语义；当前 asof 评分 PIT 仍通过。

## 5. PIT Audit

- feature_trade_date_max_by_family：`{'institutional_flow': '2026-06-10', 'margin_short': '2026-06-10'}`。
- available_at_max_by_family：`{'institutional_flow': '2026-06-11', 'margin_short': '2026-06-11'}`。
- available_at_violations：`[]`。
- future_data_violations：`[]`。
- missing_feature_count_by_family：`{'institutional_flow': 0, 'margin_short': 0}`。

## 6. Failure Isolation Audit

| check | value |
| --- | --- |
| daily_entrypoint | scripts/run_daily_tw_stock_auto_update.py |
| has_run_p3_flag | True |
| has_optional_p3_helper | True |
| calls_p3_after_accepted_latest | True |
| p3_failure_blocks_fresh_qlib | False |
| p3_writes_latest_signal | False |
| p3_provider_publish | False |
| p3_monitor_or_trading | False |
| orthogonal_refresh_status | stale_degraded |
| institutional_latest_trade_date | 2026-06-10 |
| institutional_latest_available_at | 2026-06-11 |
| margin_latest_trade_date | 2026-06-10 |
| margin_latest_available_at | 2026-06-11 |
| pit_pass | True |
| top50_input_count | 50 |
| top50_scored_count | 50 |

## 7. Reader/UI Boundary

P3R 选择 artifact-only 边界：本阶段不新增后端 readonly reader，也不改前端 UI。readonly reader/UI 展示应另开后续展示/E2E 阶段；当前产物可由本地 artifact 读取验证。

## 8. 只读安全

- 未重训 qlib。
- 未重训 LTR。
- 未调参。
- 未改 O4 model / feature whitelist。
- 未扩大 Top50 universe。
- 未写 qlib accepted latest。
- 未触发 provider publish / refresh。
- 未触发 monitor scan/config/alerts。
- 未触发 broker/orders/quick-trade/target position。

## 9. 运行命令

```text
python -m py_compile scripts/run_tw_ltr_p3_daily_rerank_readonly.py scripts/run_daily_tw_stock_auto_update.py scripts/audit_phasep3r_daily_chain_repair.py
python scripts/run_tw_ltr_p3_daily_rerank_readonly.py
python scripts/audit_phasep3r_daily_chain_repair.py
```

## 10. 输出 Artifact

| artifact | path | exists |
| --- | --- | --- |
| daily_ltr_rerank_2026-06-15_top50.csv | data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-15_top50.csv | True |
| daily_ltr_rerank_2026-06-15_summary.json | data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-15_summary.json | True |
| daily_ltr_rerank_2026-06-15_pit_audit.json | data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-15_pit_audit.json | True |
| daily_ltr_rerank_2026-06-15_feature_audit.csv | data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-15_feature_audit.csv | True |
| daily_ltr_rerank_2026-06-15_orthogonal_refresh_status.json | data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-15_orthogonal_refresh_status.json | True |
| daily_ltr_rerank_2026-06-15_failure_isolation_audit.json | data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-15_failure_isolation_audit.json | True |
| daily_ltr_rerank_2026-06-15_p3r_chain_audit.json | data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-15_p3r_chain_audit.json | True |
| daily_ltr_rerank_latest.json | data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_latest.json | True |

## 11. 剩余风险

- 当前 P3R 只把 P3 LTR rerank 接为 optional readonly candidate，并完成链路审计；未做 UI/reader 展示。
- 正交数据刷新依赖既有 FinMind institutional/margin 归档与 O2 feature builder artifact；若后续要求自动补取最新 raw archive，需要单独审查数据源失败重试策略。
- LTR candidate 仍不是默认策略，不能写成收益、胜率或上涨概率承诺。
