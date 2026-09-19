# RCPT15_R0_R Strictly Isolated Signal And Rerank Builder Contract 审查报告

生成时间：`2026-06-25`

## 1. Verdict

`STOP_REQUIRES_EXPLICIT_LEGACY_REFRESH_OR_ACCEPTED_LATEST_AUTHORIZATION`

审查结论：RCPT15_R0_R 产物足以支持 STOP。不得直接进入原 `RCPT15_R1_ISOLATED_BACKFILL_EXECUTION`，不得授权 strictly isolated local backfill 或 rerank build。下一步若要推进 `2026-06-18..2026-06-25`，需要 coordinator/user 对 legacy refresh、accepted latest/provider 路径或另一个更严格的数据/特征补齐合同给出显式授权。

## 2. 审查范围

本次审查读取并核对：

- `docs/tw_portfolio_decision_model/POLICY_RCPT15_ISOLATED_SHADOW_BACKFILL_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R0_ISOLATED_SHADOW_BACKFILL_FEASIBILITY_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R0_R_STRICTLY_ISOLATED_SIGNAL_AND_RERANK_BUILDER_CONTRACT_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R0_R_STRICTLY_ISOLATED_SIGNAL_AND_RERANK_BUILDER_CONTRACT_EXECUTION_REPORT_CN.md`
- `scripts/build_tw_policy_rcpt15_r0_r_strictly_isolated_builder_contract.py`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r0_r_strictly_isolated_signal_and_rerank_builder_contract/`

只执行静态读取、目录列举和文本扫描。未拉数据、未运行 daily auto update、未打开 legacy provider gate、未切 accepted latest、未发布 provider、未写 production/default/latest/provider/frontend/Agent/monitor/order。

## 3. Findings

### Critical

无 Critical 违规。审计脚本是本地文件系统扫描器，未发现导入或调用网络抓取、daily auto update、provider publish、accepted latest switch、broker、quick-trade、order、target position/weight 或 monitor 写入路径。

### High

RCPT15_R0_R 的 STOP verdict 合理，不能授权下一步直接 backfill。证据显示：

- `validator_report.json`：`missing_signal_target_days = 8`，`missing_o2_feature_target_days = 8`，`normalized_price_sufficient_for_2026_06_25 = false`，`current_scripts_have_latest_pointer_risk = true`。
- `target_date_local_data_coverage.csv`：`2026-06-18` 至 `2026-06-25` 均无 `local_option_c_top50`、无 `local_option_c_prediction`，且 `o2_feature_ge_date = False`。
- `dependency_gap_audit.csv`：目标日 option_c signal/top50 为 `MISSING`，normalized price through 2026-06-25 为 `INSUFFICIENT_OR_UNPROVEN`，O2 features 为 `STALE_OR_MISSING`，现有脚本 no-latest-pointer 为 `FAILS_CURRENT_SCRIPT`。

这些缺口同时阻断了“直接使用现有本地 artifacts 生成 shadow signal/rerank”的路径，也阻断了“直接进入原 R1”的授权条件。

### Medium

no-latest-pointer 合同是必要且正确的。`script_latest_pointer_risk_audit.csv` 标记：

- `scripts/archive/historical_research/run_tw_ltr_p3_daily_rerank_readonly.py` 包含 `latest_signal` 指针、`daily_ltr_rerank_latest.json` 写入风险和 provider publish 相关标记。
- `scripts/archive/historical_research/build_p3rr_latest_orthogonal_features.py` 包含 `latest_signal` 指针。
- `scripts/run_daily_tw_stock_auto_update.py` 包含 latest/provider/daily auto update 相关风险。

因此现有脚本不能被作为 RCPT15_R1 严格隔离 builder 原样复用。未来若另开 builder 合同，必须要求显式 `asof`、显式 `output_root`，并禁止读写 `latest_signal.json`、`daily_ltr_rerank_latest.json`、provider accepted latest 或 production/default/latest 路径。

### Low

审查中发现的 `target_date_local_data_coverage.csv` 证据粒度问题已由 coordinator 修正并重跑：`normalized_price_symbols_ge_date` 现在按逐目标日期统计真实覆盖 symbol 数，不再使用布尔化计数表达式。该修正不改变 STOP verdict。

## 4. 只读隔离边界

审查通过。`forbidden_scope_audit.csv` 对以下 gate 均为 `PASS_NOT_PERFORMED` 或 `PASS_NOT_PRESENT`：

- no external data pull
- no daily auto update run
- no legacy provider gate opened
- no accepted latest switch
- no provider publish
- no production/default/latest/provider/frontend/Agent/monitor/order write
- no order/target/quantity/broker output

文本扫描命中的 forbidden 词主要出现在工作文档、执行报告、审计脚本的 deny-list/合同条款和风险扫描规则中，属于允许的禁止范围说明，不构成实际越界行为。

## 5. 目标日期本地覆盖

目标日期为：

```text
2026-06-18, 2026-06-19, 2026-06-20, 2026-06-21,
2026-06-22, 2026-06-23, 2026-06-24, 2026-06-25
```

本地覆盖结论：

- option_c top50/prediction：8 个目标日全部缺失。
- O2 orthogonal features：最大 `trade_date = 2026-06-10`，8 个目标日全部缺失。
- normalized price：最弱 symbol 最大日期为 `2026-06-17`，未覆盖目标区间；`TWII.csv` 未提供可用最大日期。
- O4 model/whitelist：存在，但只能说明模型文件可用，不能弥补 signal/top50、价格和 O2 特征缺口。

## 6. Dependency Gap

dependency gap 判定合理：

- `target_option_c_signal_top50_2026_06_18_to_2026_06_25 = MISSING`
- `normalized_price_coverage_through_2026_06_25 = INSUFFICIENT_OR_UNPROVEN`
- `o2_orthogonal_features_through_2026_06_25 = STALE_OR_MISSING`
- `o4_ltr_model_and_whitelist = PRESENT`
- `existing_scripts_no_latest_pointer_write = FAILS_CURRENT_SCRIPT`

这些缺口足以阻断 PASS，也不足以进入 `STOP_REQUIRES_NEW_ISOLATED_QLIB_INFERENCE_BUILDER_CONTRACT`，因为本地 normalized price/market feature 覆盖并不充分。

## 7. 授权意见

不授权：

- 不授权原 `RCPT15_R1_ISOLATED_BACKFILL_EXECUTION`。
- 不授权运行现有 daily LTR rerank 脚本生成目标日产物。
- 不授权 legacy refresh、daily auto update、provider publish、accepted latest switch。
- 不授权写任何 latest pointer、production/default/latest/provider/frontend/Agent/monitor/order、order/target/broker 相关产物。

可授权的唯一方向是进入 coordinator/user 显式决策：要么单独批准受控刷新/accepted latest/provider 路径，要么另立更窄合同先证明本地价格、市场特征和 qlib inference 所需输入已经完整且仍能保持 shadow-only、no-latest-pointer 边界。

## 8. 结论

RCPT15_R0_R 执行完整度可接受，隔离边界未发现越界，no-latest-pointer 合同方向正确，verdict 合理。

最终 verdict：

```text
STOP_REQUIRES_EXPLICIT_LEGACY_REFRESH_OR_ACCEPTED_LATEST_AUTHORIZATION
```
