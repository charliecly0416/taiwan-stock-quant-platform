# RCPT15_R0 Isolated Shadow Backfill Feasibility 审查意见

生成时间：`2026-06-25`

## 1. Verdict

`STOP_REQUIRES_EXPLICIT_LEGACY_REFRESH_OR_ACCEPTED_LATEST_AUTHORIZATION`

审查结论：RCPT15_R0 执行完整，证据支持 STOP。不得进入 `RCPT15_R1_ISOLATED_BACKFILL_EXECUTION`。

## 2. 审查范围

本次审查严格依据：

- `docs/tw_portfolio_decision_model/POLICY_RCPT15_ISOLATED_SHADOW_BACKFILL_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R0_ISOLATED_SHADOW_BACKFILL_FEASIBILITY_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r0_isolated_shadow_backfill_feasibility/validator_report.json`
- `available_daily_rerank_days.csv`
- `daily_auto_update_status_audit.csv`
- `backfill_script_inventory.csv`
- `candidate_backfill_dates.csv`
- `dependency_gap_audit.csv`
- `isolated_backfill_contract.csv`
- `forbidden_scope_audit.csv`

## 3. Findings

### Critical

无 scope/safety violation。R0 没有证据显示拉取外部数据、运行 daily auto update、打开 legacy provider gate、修改 cron、切 accepted latest、修改 production/default/latest/provider/frontend/Agent/monitor/order，或输出 order/target/broker 字段。

### High

`2026-06-18` 至 `2026-06-25` 的本地 `option_c_daily_signal/top50_signals.csv` 输入不存在。`candidate_backfill_dates.csv` 对 8 个目标日期均标记：

```text
can_backfill_without_external_data = False
r0_feasibility = NOT_LOCAL_READY
stop_or_condition_reason = missing_option_c_daily_signal_top50_for_date
```

因此当前不能从已有本地 artifacts 严格隔离生成新 `daily_ltr_rerank` shadow days。

### Medium

现有 daily LTR rerank 生成脚本 `scripts/archive/historical_research/run_tw_ltr_p3_daily_rerank_readonly.py` 不适合作为严格隔离 R1 直接执行脚本。证据：

- `backfill_script_inventory.csv` 标记 `writes_daily_ltr_latest=True`、`references_latest_signal=True`、`references_top50_signals=True`、`references_provider_publish=True`、`references_accepted_latest=True`。
- 源码抽查显示该脚本读取 `qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json` 和 `top50_signals.csv`，并写出 `daily_ltr_rerank_latest.json`。

这不代表脚本本身有错误，但它不满足 RCPT15_R1 的“严格隔离 backfill”边界。

### Low

`daily_auto_update_status_audit.csv` 证明 cron/job 仍在运行，最近 job 为：

```text
daily_tw_stock_auto_update_20260625_20260625T123001Z
status = daily_auto_update_passed
finmind_update_triggered = True
yahoo_refresh_triggered = False
provider_publish_triggered = False
latest_signal_updated = False
latest_before = 2026-06-17
latest_after = 2026-06-17
legacy_provider_publish_enabled = False
qlib_legacy_provider_path_skipped = True
```

这与主线事实一致：自动脚本默认 M3 readonly orchestrator，不推进 qlib accepted latest / option_c daily signal / daily LTR rerank。

## 4. Mainline Compliance

R0 符合主线要求：

- 已完成本地 daily rerank 可用日审计：仅 `2026-06-15`、`2026-06-17` 完整可用。
- 已完成目标日期 `2026-06-18..2026-06-25` backfill feasibility 审计。
- 已完成 daily auto update 最近状态审计。
- 已完成 backfill 脚本 inventory。
- 已完成 dependency gap 审计。
- 已产出 isolated backfill contract。
- 已产出 forbidden scope audit。
- 已给出允许范围内的 verdict。

## 5. Evidence Checked

关键证据：

- `validator_report.json`
  - `status = STOP_REQUIRES_EXPLICIT_LEGACY_REFRESH_OR_ACCEPTED_LATEST_AUTHORIZATION`
  - `r1_allowed = false`
  - `target_missing_option_c_top50_count = 8`
  - `target_ready_local_backfill_count = 0`
  - `forbidden_scope_pass = true`
- `available_daily_rerank_days.csv`
  - 仅 `2026-06-15` 与 `2026-06-17` 为 `COMPLETE_FOR_RCPT_SHADOW_SOURCE`
- `candidate_backfill_dates.csv`
  - `2026-06-18` 至 `2026-06-25` 全部 `NOT_LOCAL_READY`
- `dependency_gap_audit.csv`
  - `option_c_daily_signal_top50_for_2026_06_18_to_2026_06_25 = MISSING`
  - `daily_ltr_rerank_generator_no_latest_pointer_write = FAILS_CURRENT_SCRIPT`
- `forbidden_scope_audit.csv`
  - 所有禁区项均为 `PASS_NOT_PERFORMED` 或 `PASS_NOT_PRESENT`

## 6. Missing Evidence Or Open Questions

当前 R0 证据足够支持 STOP，不需要 R0 repair。

未解决问题不属于 R0 缺陷，而是下一步路线选择：

1. 是否允许构建一个新的 strictly isolated local signal/shadow builder，不读取/写入 accepted latest pointer，不发布 provider，只输出 RCPT research artifacts。
2. 是否授权 legacy refresh / accepted latest / provider publish 相关路径。若授权，必须单独开合同，不能在 RCPT15_R1 中隐式执行。
3. 是否继续等待自动链路产生新的 accepted latest artifacts。按现状，默认 cron 不会产生这些 artifacts，因此单纯等待不能解决 6/18-6/25 缺口。

## 7. Forbidden Actions Audit

审查通过：

- external data download: `not_performed`
- daily auto update run: `not_performed`
- legacy provider gate opened: `not_performed`
- cron modified: `not_performed`
- qlib accepted latest switched: `not_performed`
- production/default/latest/provider/frontend/Agent/monitor/order modified: `not_performed`
- OrderIntent/target_weight/target_position/quantity_instruction/broker output: `not_present`

## 8. Next Work Document

建议下一步不是进入 R1，而是开一个更窄的 repair/contract phase：

```text
RCPT15_R0_R_STRICTLY_ISOLATED_SIGNAL_AND_RERANK_BUILDER_CONTRACT
```

目标：

1. 只设计和审计一个 strictly isolated builder 合同，不实际拉数据、不切 latest、不发布 provider。
2. 明确 builder 可否从已有 normalized/full-market/feature/model artifacts 直接生成 `2026-06-18..2026-06-25` 的 RCPT shadow-only signal/rerank input。
3. 若可行，要求新 builder 输出到 RCPT15 专用实验目录，不写：
   - `daily_ltr_rerank_latest.json`
   - `qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json`
   - provider accepted latest
   - production/default/latest/frontend/Agent/monitor/order 路径
4. 若不可行，则明确列出必须由 coordinator/user 授权的外部刷新或 accepted latest 路径。

R0_R 通过后，才可重新定义 R1。当前 R1 仍禁止执行。

## 9. Command For Coordinator

建议 coordinator 向执行者下发：

```text
请执行 RCPT15_R0_R_STRICTLY_ISOLATED_SIGNAL_AND_RERANK_BUILDER_CONTRACT。
只做合同和可行性设计，不拉数据、不运行 daily auto update、不打开 legacy provider gate、不切 accepted latest、不发布 provider、不写 production/default/latest/provider/frontend/Agent/monitor/order。
重点判断是否能用本地已有 normalized/full-market/feature/model artifacts 构造 2026-06-18..2026-06-25 的 RCPT shadow-only signal/rerank builder，并证明该 builder 不写任何 latest pointer。
```
