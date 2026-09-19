# POLICY QALD6 Route Closure And Maintenance Runbook Review

## 1. 审查范围

- Route: `QALD_QLIB_ACCEPTED_LATEST_DAILY_PROMOTION`
- Reviewed phase: `QALD6_ROUTE_CLOSURE_AND_MAINTENANCE_RUNBOOK`
- Execution report: `docs/tw_portfolio_decision_model/POLICY_QALD6_ROUTE_CLOSURE_AND_MAINTENANCE_RUNBOOK_EXECUTION_REPORT_CN.md`
- Work doc: `docs/tw_portfolio_decision_model/POLICY_QALD6_ROUTE_CLOSURE_AND_MAINTENANCE_RUNBOOK_WORK_CN.md`
- QALD5 review: `docs/tw_portfolio_decision_model/POLICY_QALD5_ACTUAL_CONTROLLED_ACCEPTED_LATEST_AUTO_SWITCH_OR_DEFER_REVIEW_CN.md`
- Target pointer: `qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json`
- Rollback copy: `data_tw/experiments/qald_controlled_auto_switch_preflight/qald5_actual_switch_20260812T000000Z/latest_signal.json.rollback`
- Installed cron: `data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron`

本审查只读取本地文件、复算 checksum/行数、调用只读 `QlibOptionCSignalReader`。未写 pointer，未改 cron，未运行 daily-auto，未触发 provider/qlib refresh，未做 downstream publish、DB/OpenAI、strategy replay、monitor/broker/order/target 或 frontend/API default switch。唯一写入为本 review 文档。

## 2. Verdict

`PASS`

QALD6 可以接受为 closure-only runbook 阶段。证据显示当前 qlib accepted latest 仍为 `2026-08-12` / `option_c_daily_signal_20260812_qald2r_candidate_20260812T123001Z`，reader `latest` 与 `run_detail` 均 `ok=true` 且 top30/top50 计数为 30/50；rollback copy 存在并指向 prior `2026-08-07` accepted state；installed cron 仍是 no-pointer candidate builder，未包含 QALD5 auto switch 授权；runbook 对未来 switch 要求 fresh exact route；forbidden audit 与核验证据一致。

## 3. Findings

### Critical

None.

### High

None.

### Medium

None blocking.

### Low

1. 当前受限环境执行 `crontab -l` 返回 `crontabs/chuliyang/: fopen: Permission denied`，因此本 review 未重新验证 actual crontab。用户本次指定审查对象为 installed cron；installed cron 文件已独立核对，结论通过。若后续要把 actual crontab 纳入放行条件，应在具备读取权限的 shell 中复查。

2. QALD6 execution report 将 reader trading flags 写成扁平字段；实际 `QlibOptionCSignalReader` 返回结构中这些字段位于 `trading` 对象下。值本身已复核为 readonly，不影响结论。

## 4. Closure-only 核对

QALD6 work doc 明确本阶段是关闭受控 accepted-latest promotion route 并写维护 runbook，且不得再执行 accepted latest switch。execution report 也声明 closure mode 为 readonly verification and runbook write only，并列出未运行 daily-auto、provider pull/refresh/publish、qlib refresh、cron edit、downstream latest publish、DB/OpenAI、strategy replay、monitor/broker/order/target、target position/weight、frontend/API default switch。

独立审查过程中未发现 QALD6 证据中存在新 pointer write、cron edit、provider/qlib refresh 或 downstream publish。QALD5 的受控 pointer write 是历史已审查动作，不应计为 QALD6 action。

## 5. Accepted Latest / Reader

当前 target pointer 解析结果：

```text
path=qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json
sha256=b9f663b276e70ce33fd847a528149603ecf62aca63424ef8f70da4b074515fad
asof=2026-08-12
status=accepted
run_id=option_c_daily_signal_20260812_qald2r_candidate_20260812T123001Z
run_dir=data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260812_qald2r_candidate_20260812T123001Z
diagnostic_only=true
research_signal_not_order=true
```

只读 reader 复核：

```text
QlibOptionCSignalReader.latest(bucket=all, enrich_trend=False)
ok=true
status=accepted
asof=2026-08-12
run_id=option_c_daily_signal_20260812_qald2r_candidate_20260812T123001Z
top30_count=30
top50_count=50
warnings=[]
trading.orders_enabled=false
trading.connects_to_broker=false
trading.quick_trade_enabled=false
trading.live_trading_enabled=false
trading.writes_orders=false
trading.writes_positions=false
trading.research_signal_not_order=true

QlibOptionCSignalReader.run_detail(target_run_id, bucket=all, enrich_trend=False)
ok=true
status=accepted
asof=2026-08-12
run_id=option_c_daily_signal_20260812_qald2r_candidate_20260812T123001Z
top30_count=30
top50_count=50
warnings=[]
same readonly trading flags=true
```

候选 artifact 复核：

```text
formal_validation.json sha256=70c14beaf9e636e1046c99e5785b0a352d1b6d2abc90a816803b59eba95e0c82
formal_validation.status=PASS
formal_validation.target_asof=2026-08-12
formal_validation.run_id=option_c_daily_signal_20260812_qald2r_candidate_20260812T123001Z
top30_signals.csv lines=31, data_rows=30
top50_signals.csv lines=51, data_rows=50
```

## 6. Rollback

Rollback copy 存在并可解析：

```text
path=data_tw/experiments/qald_controlled_auto_switch_preflight/qald5_actual_switch_20260812T000000Z/latest_signal.json.rollback
sha256=e9c9e5cf5fca8fb2e2da9a1c51624e3e9bbf6b155962b4d4adac11bc5e0a229b
asof=2026-08-07
status=accepted
run_dir=data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260807_fpale2_candidate_20260808T035113Z
diagnostic_only=true
research_signal_not_order=true
```

QALD6 execution report 与 runbook 均明确 rollback 未执行，未来 rollback 需单独 exact authorization，且只能写 `qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json`。

## 7. Cron

Installed cron checksum 与 QALD6 execution report 一致：

```text
data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron
sha256=19315007426df76b6e424972db48da40fed5fd8dda23522ba6854d88ac5e7d7a
```

Installed cron 的 QALD flags 仍为 no-pointer：

```text
ENABLE_TW_QALD_ACCEPTED_LATEST_CANDIDATE_BUILDER=true
TW_QALD_ACCEPTED_LATEST_CANDIDATE_NO_POINTER=true
TW_QALD_ACCEPTED_LATEST_CANDIDATE_ALLOW_POINTER_WRITE=false
TW_QALD_ACCEPTED_LATEST_CANDIDATE_EXACT_AUTHORIZATION_ID=""
TW_QALD_ACCEPTED_LATEST_CANDIDATE_TARGET_ASOF=""
TW_QALD_ACCEPTED_LATEST_CANDIDATE_SOURCE_ROOT=""
```

对 installed cron 的关键词核对未发现 `QALD5` 或 `QALD_CONTROLLED_ACCEPTED_LATEST_AUTO_SWITCH_20260812`，也未发现 QALD pointer-write 授权。`TW_FPALA_ALLOW_ACCEPTED_LATEST_SWITCH = false` 与空 `TW_FPALA_EXACT_AUTHORIZATION_ID = ""` 仍保持关闭。已存在的 DAPR18 自动发布配置属于独立下游 route，不构成 QALD5 auto switch。

## 8. Runbook / Future Switch Gate

Runbook 明确未来 accepted latest switch 需要 fresh route，而不是沿用 QALD5/QALD6 closure 状态：

- natural cron candidate evidence；
- reader validation `ok=true`、`top30_count=30`、`top50_count=50`；
- fresh QALD preflight，命名 exact target asof/run id；
- new authorization id，禁止复用 `QALD_CONTROLLED_ACCEPTED_LATEST_AUTO_SWITCH_20260812`；
- rollback copy 与 before/after fingerprints；
- 唯一允许写入 `qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json`；
- provider publish、qlib refresh、legacy latest switch、downstream latest publish、DB/OpenAI、strategy replay、trading、frontend/API default switch 均需保持排除，除非进入另一个单独授权 route。

Future auto-switch enablement 也被明确标为未启用；若以后启用，需要单独 route 设计 pointer-write cron flags、exact authorization、stop/rollback 行为和多轮 natural cron 安全证据。

## 9. Forbidden Audit

QALD6 execution report 的 forbidden action audit 合理：

```text
daily_auto_manual_run=false
provider_pull_or_refresh=false
provider_publish=false
formal_provider_mutation=false
qlib_refresh=false
qlib_accepted_latest_pointer_switch=false
legacy_latest_switch=false
dapr18_signal_latest_write=false
readonly_snapshot_latest_write=false
agent_prompt_latest_write=false
installed_cron_edit=false
actual_crontab_edit=false
db_access_or_write=false
openai_call=false
strategy_replay=false
monitor_broker_order_target=false
target_position_or_weight_generated=false
frontend_api_default_switch=false
```

该 audit 将历史 QALD5 单路径 pointer write 与 QALD6 action 分开处理，边界合理。未发现 provider refresh/publish、qlib refresh、cron edit、下游 latest publish、交易、DB/OpenAI 或 frontend/API 默认切换证据。

## 10. Route Decision

`PASS_ROUTE_CLOSED_WITH_DOWNSTREAM_DEFERRED`

QALD6 closure/runbook 通过。当前稳定状态为：daily no-pointer candidate generation enabled；actual qlib accepted latest switch 仅限已完成并通过 review 的 exact-route controlled QALD5；automatic qlib accepted latest switch 未启用；downstream readonly snapshot 与 Agent prompt 等 publish route 仍需独立 exact route。
