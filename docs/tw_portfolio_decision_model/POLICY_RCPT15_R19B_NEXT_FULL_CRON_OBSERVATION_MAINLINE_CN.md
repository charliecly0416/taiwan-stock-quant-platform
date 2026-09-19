---
created_at: 2026-06-27
status: coordinator_mainline
route: RCPT15_R19B_NEXT_FULL_CRON_OBSERVATION
parent_review: docs/tw_portfolio_decision_model/POLICY_RCPT15_R19_SCHEDULER_AUTOMATIC_ACCUMULATION_OBSERVATION_REVIEW_CN.md
parent_execution_report: docs/tw_portfolio_decision_model/POLICY_RCPT15_R19_SCHEDULER_AUTOMATIC_ACCUMULATION_OBSERVATION_EXECUTION_REPORT_CN.md
production_allowed: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
qlib_refresh_allowed: false
manual_run_allowed: false
readonly_observation_only: true
order_or_target_output_allowed: false
---

# POLICY_RCPT15_R19B_NEXT_FULL_CRON_OBSERVATION_MAINLINE_CN

## 1. Goal

本路线用于继续 `RCPT15_R19` 的 scheduler 自动链路观察。

`RCPT15_R19` 的结论是：

```text
WAITING_FOR_NEXT_FULL_CRON
```

这不是实现失败，而是时间条件尚未满足。截至 R19 审查时，R18 之后没有新的 weekday `14:45 UTC / Asia/Taipei 22:45` full cron job 可作为自动 scheduler 证据。因此 R19B 的目标是：在下一次 weekday full cron 自然执行后，只读观察是否出现新的自动 full orthogonal batch job，并判断 checkpoint 是否从 `15/150` 推进到 `20/150`，或是否有明确 provider quota/timeout blocker。

当前日期为 `2026-06-27`，是周六。若 cron 配置保持 weekday-only，下一次应观察的 weekday full cron 时间点是：

```text
2026-06-29 14:45 UTC
2026-06-29 22:45 Asia/Taipei
```

执行者不得为了制造证据而手动运行 daily update 或 provider pull。

## 2. Non-goals

R19B 不授权：

```text
手动运行 scripts/run_daily_tw_stock_auto_update.py
触发 Yahoo/Scrapling/FinMind provider pull
qlib formal refresh
provider publish
accepted/latest switch
production/default/frontend/Agent/monitor/order 改动
broker / quick-trade / real order
target_position / target_weight / quantity / shares / lots 输出
training / retraining
threshold tuning
mapping expansion
把 partial coverage 包装成 full ready
把手动 job、weekend wait job、daily 14:30 job 冒充 full scheduler job
```

R19B 只允许读取本地 cron/job/checkpoint/artifact 证据，并写 isolated observation artifact 与执行报告。

## 3. Current Baseline

R18 已通过：

```text
PASS_MANUAL_ACCUMULATION_15_OF_150
```

其范围仅限 manual full observation：

```text
checkpoint: institutional done=15/150, margin done=15/150
job: data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260626T174322Z/
started_at: 2026-06-26T17:43:22+00:00
```

R19 已确认：

```text
WAITING_FOR_NEXT_FULL_CRON
```

关键原因：

- R18 后未发现新的 scheduler automatic full job；
- `14:30 UTC` daily job 不是 configured full cron；
- `16:30 UTC` weekend wait job 不是 FinMind full orthogonal batch；
- `17:43 UTC` job 是 R18 manual evidence，不得作为 R19/R19B scheduler pass；
- checkpoint 仍为 `15/150`，尚未推进到 `20/150`。

Installed cron 中已有 full scope weekday 配置：

```text
45 14 * * 1-5 ... TW_DAILY_AUTO_FINMIND_SCOPE=full ... scripts/run_daily_tw_stock_auto_update.py >> data_tw/ops/daily_auto_update/cron.log 2>&1
```

R19B 的判断必须以 R18 manual job 之后、且下一次 weekday full cron 自然执行后的新证据为准。

## 4. Required Prior Documents

执行者和审查者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R18_CONTINUED_ACCUMULATION_OR_SCHEDULER_OBSERVATION_DECISION_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT15_R19_SCHEDULER_AUTOMATIC_ACCUMULATION_OBSERVATION_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT15_R19_SCHEDULER_AUTOMATIC_ACCUMULATION_OBSERVATION_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT15_R19_SCHEDULER_AUTOMATIC_ACCUMULATION_OBSERVATION_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT15_R19B_NEXT_FULL_CRON_OBSERVATION_WORK_CN.md
data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron
data_tw/ops/daily_auto_update/cron.log
data_tw/ops/daily_auto_update/finmind_orthogonal_batch_state/2026-06-26_institutional_margin.json
```

如 R19B 执行时出现新日期 checkpoint，应读取最新对应 checkpoint，并保留 2026-06-26 checkpoint 作为 baseline。

## 5. Required Skills / Workflow

必须遵守：

```text
coordinator-executor-reviewer-workflow
tw-stock-new-strategy-onboarding
```

本路线不是策略上线，也不是 OrderIntent/replay 接入；使用 `tw-stock-new-strategy-onboarding` 的原因是继续强制 no-order/no-target/no-broker/no-production/default 边界。

## 6. Architecture / Module Boundaries

R19B 只允许写：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R19B_NEXT_FULL_CRON_OBSERVATION_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT15_R19B_NEXT_FULL_CRON_OBSERVATION_REVIEW_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt15_r19b_next_full_cron_observation/
```

R19B 不允许修改：

```text
backend/
frontend/
configs/
scripts/run_daily_tw_stock_auto_update.py
data_tw/ops/daily_auto_update/cron.log
data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron
data_tw/ops/daily_auto_update/finmind_orthogonal_batch_state/
provider/latest/accepted pointers
qlib formal calendar or normalized data
```

读取 `data_tw/ops/...` 可以，写入该路径不可以。

## 7. Phase Plan

### R19B-A: Readonly Evidence Discovery

执行者只读检查：

- installed cron 是否仍包含 weekday `14:45 UTC` full scope；
- `cron.log` 中 R18 manual job 后是否出现新的 `14:45 UTC` 附近 automatic job；
- job directory 中是否出现 R18 manual job 后的新 job artifact；
- 新 job 是否为 `full_with_quota_aware_orthogonal_batch`；
- job 是否触发 `finmind_orthogonal_batch_update_triggered=true`；
- checkpoint 是否从 `15/150` 推进到 `20/150`，或记录明确 provider quota/timeout blocker；
- selected symbols 是否避开 fully done symbols；
- partial 状态是否仍被保留，不得误报 full ready；
- forbidden action flags 是否保持 false。

### R19B-B: Observation Artifact And Execution Report

执行者写 isolated artifact 和执行报告。

允许 verdict：

```text
PASS_AUTOMATIC_FULL_CRON_ADVANCED_TO_20_OF_150
PASS_AUTOMATIC_FULL_CRON_PROVIDER_BLOCKED_STATE_PRESERVED
WAITING_FOR_NEXT_FULL_CRON
FAIL_NEEDS_SCHEDULER_OR_SCOPE_REPAIR
STOP_FORBIDDEN_ACTION_OR_SCOPE_VIOLATION
```

### R19B-C: Independent Review

审查者只读复核执行报告和 artifact。

如果 `PASS_AUTOMATIC_FULL_CRON_ADVANCED_TO_20_OF_150`，下一步仍只能建议继续 scheduler accumulation 或写 go/no-go contract，不得直接生产化。

如果 `WAITING_FOR_NEXT_FULL_CRON`，应明确这是时间条件未满足，不是 repair。

如果 fail/stop，必须写清具体修复边界；不得要求执行者手动触发 provider pull 来补证据。

## 8. Evidence And Validator Requirements

Artifact root:

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r19b_next_full_cron_observation/
```

Expected files:

```text
manifest.json
cron_config_audit.csv
cron_log_observation.csv
job_discovery_audit.csv
candidate_full_cron_job_audit.csv
checkpoint_delta_audit.csv
selected_symbol_repetition_audit.csv
partial_full_ready_audit.csv
forbidden_action_audit.csv
secret_scan_audit.md
validator_report.json
diagnostic_findings.md
```

`validator_report.json` 必须至少包含：

- `readonly_observation_only`;
- `manual_run_performed=false`;
- `provider_pull_triggered_by_r19b=false`;
- `qlib_refresh_triggered=false`;
- `provider_publish_triggered=false`;
- `accepted_latest_switch_triggered=false`;
- `production_chain_modified=false`;
- `order_or_target_output_generated=false`;
- `r18_manual_job_not_counted_as_r19b_pass=true`;
- `weekend_wait_not_counted_as_full_cron=true`;
- `daily_1430_job_not_counted_as_full_cron=true`;
- final verdict。

## 9. Pass / Fail Gate

R19B 可 PASS 为 `PASS_AUTOMATIC_FULL_CRON_ADVANCED_TO_20_OF_150` 仅当全部成立：

```text
R18 manual job 之后存在新 automatic scheduler job
job 时间与 weekday 14:45 UTC full cron 配置匹配或有明确 cron log 证据
job scope 为 full_with_quota_aware_orthogonal_batch
finmind_orthogonal_batch_update_triggered=true
checkpoint institutional 和 margin 从 15/150 推进到 20/150
selected symbols 不重复 fully done symbols
partial 状态仍为 partial，full_ready=false
无 token 泄漏
无 qlib refresh / publish / accepted latest / production / order / target 输出
```

可 PASS 为 `PASS_AUTOMATIC_FULL_CRON_PROVIDER_BLOCKED_STATE_PRESERVED` 仅当：

```text
新 automatic full cron job 存在；
job 确认进入 full orthogonal batch；
provider quota/timeout 明确阻断本轮推进；
checkpoint 未回退，已完成 15/150 状态保持；
failed/retry/cooldown 信息可审计；
无 forbidden action。
```

应给 `WAITING_FOR_NEXT_FULL_CRON` 当：

```text
还没有 R18 后新的 weekday 14:45 UTC full cron job；
或当前日期/时间早于下一次 full cron 自然执行点；
或只有 daily/weekend/manual evidence，不足以判定 scheduler full cron。
```

应 FAIL/STOP 当：

```text
scheduler 已运行但 scope 不是 full；
automatic job 未触发 orthogonal batch 且没有合理 blocker；
checkpoint 回退或重复 fully done symbols；
partial 被误报 full ready；
token 泄漏；
R19B 触发了 manual run/provider pull/qlib refresh/publish/latest switch/production/order/target。
```

## 10. Forbidden Actions

R19B 禁止：

```text
manual run
network/provider pull
qlib refresh
provider publish
accepted latest switch
production/default/frontend/Agent/monitor/order write
broker / quick-trade / real order
OrderIntent
target_position / target_weight / quantity / shares / lots
training / retraining
threshold tuning
mapping expansion
secret/token artifact write
```

## 11. Closure Criteria

本主线可关闭当：

- R19B execution report 和 review 均完成；
- verdict 明确为 PASS / WAITING / FAIL / STOP 之一；
- forbidden action audit clean 或明确 fail/stop；
- 若 PASS，也只表示 scheduler automatic accumulation observation 通过，不表示 production ready；
- 若 WAITING，下一次观察时间和条件明确；
- 若 FAIL/STOP，repair 边界明确且不要求手动制造 provider evidence。

## 12. First Executor Command

```text
你是 RCPT15_R19B 执行者。读取 R18 review、R19 work/execution/review、R19B mainline/work doc、installed cron、cron.log、R18 manual job、FinMind checkpoint。只做只读观察：判断 R18 manual job 之后是否出现新的 weekday 14:45 UTC full cron automatic job，是否触发 quota-aware orthogonal batch，checkpoint 是否从 15/150 推进到 20/150 或是否 provider blocked state preserved。不得运行 daily update，不得 provider pull，不得 qlib refresh/publish/latest switch，不得 production/default/frontend/Agent/monitor/order 改动，不得输出 OrderIntent/target/quantity/broker。写 isolated artifact root 和 POLICY_RCPT15_R19B_NEXT_FULL_CRON_OBSERVATION_EXECUTION_REPORT_CN.md。
```

## 13. Reviewer Audit Brief

```text
你是 RCPT15_R19B 审查者。读取 R19B mainline/work doc、执行报告、artifact root、R18/R19 prior docs、cron/job/checkpoint evidence。独立确认执行者没有把 R18 manual job、daily 14:30 job、weekend wait job冒充为 R19B full scheduler pass；确认是否存在 R18 后新的 weekday 14:45 UTC full cron job；确认 checkpoint delta、selected symbol repetition、partial/full_ready、forbidden action 和 secret scan。写 POLICY_RCPT15_R19B_NEXT_FULL_CRON_OBSERVATION_REVIEW_CN.md，并给出下一步 work doc 或 WAITING closure。不得授权生产化、publish/latest switch、manual run 或 provider pull。
```
