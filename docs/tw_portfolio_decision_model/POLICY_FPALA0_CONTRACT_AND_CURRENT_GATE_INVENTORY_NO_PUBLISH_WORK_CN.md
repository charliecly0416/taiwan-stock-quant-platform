# FPALA0 Contract And Current Gate Inventory No-Publish Work

## 1. Scope

- Phase: `FPALA0_CONTRACT_AND_CURRENT_GATE_INVENTORY_NO_PUBLISH`
- Mainline: `POLICY_FPALA_FORMAL_PROVIDER_ACCEPTED_LATEST_AUTOMATION_ALIGNMENT_NO_PUBLISH_MAINLINE_CN.md`
- Mode: readonly / no-publish。

FPALA0 只做盘点，不做修复、不做实际写入、不跑 daily-auto。

## 2. Required Inputs

执行者必须读取：

- `docs/tw_portfolio_decision_model/POLICY_FPALA_FORMAL_PROVIDER_ACCEPTED_LATEST_AUTOMATION_ALIGNMENT_NO_PUBLISH_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_FPAL_FORMAL_PROVIDER_ACCEPTED_LATEST_PRODUCTIONIZATION_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_FPAL7_FORMAL_ACCEPTED_LATEST_ROUTE_CLOSURE_AND_DAILY_AUTO_ALIGNMENT_REVIEW_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_FPAL7_FORMAL_ACCEPTED_LATEST_ROUTE_CLOSURE_AND_DAILY_AUTO_ALIGNMENT_REVIEW_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_FPAL6_ACTUAL_ACCEPTED_LATEST_POINTER_SWITCH_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_DAPR18P9_CONTROLLED_PRODUCT_LATEST_STABLE_OPS_ENTRY_REVIEW_CN.md`
- `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`
- `data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron`
- `scripts/run_daily_tw_stock_auto_update.py`

## 3. Evidence To Collect

只读收集：

- formal provider calendar tail。
- formal provider calendar hash，或与 FPAL7 closure evidence 对比证明未变。
- qlib accepted latest pointer asof/run_dir/hash。
- legacy latest pointer asof/run_dir/hash。
- DAPR18 signal latest / readonly snapshot latest / Agent prompt latest asof/hash。
- installed cron flags related to provider candidate refresh、model signal gate、DAPR18、legacy provider publish。
- daily-auto code locations for:
  - provider candidate refresh gate。
  - legacy provider publish gate。
  - accepted latest scheduler call。
  - latest_signal_updated / provider_publish_triggered status fields。
- latest provider candidate readiness summary。
- recent natural job summaries proving current behavior。

## 4. Required Analysis

执行报告必须回答：

- 当前 formal provider 与 qlib accepted latest 是否对齐。
- 当前 daily-auto 是否会自动 formal provider publish。
- 当前 daily-auto 是否会自动 qlib accepted latest switch。
- 现有 broad legacy gate 为什么不适合作为未经审查的生产默认。
- FPALA dedicated gate 最小合同需要哪些字段。
- no-publish 阶段需要哪些 validators / status。

## 5. Allowed Actions

允许：

- `sed`、`rg`、`find`、`tail`、`jq`、`sha256sum`、`wc`。
- 写入 FPALA0 execution report。
- 写入 FPALA1 work document。

## 6. Forbidden Actions

禁止：

- 运行 `scripts/run_daily_tw_stock_auto_update.py`。
- real Yahoo/FinMind pull。
- provider refresh / publish。
- formal provider mutation。
- qlib refresh。
- accepted latest switch。
- legacy latest switch。
- DAPR18 product latest publish。
- readonly snapshot latest publish。
- Agent prompt build/publish。
- daily-auto manual run。
- cron 修改 / crontab install。
- OpenAI、DB、strategy replay。
- monitor、broker、quick-trade、order、target position/weight。
- frontend/API default switch。

## 7. Output

执行者输出：

- `docs/tw_portfolio_decision_model/POLICY_FPALA0_CONTRACT_AND_CURRENT_GATE_INVENTORY_NO_PUBLISH_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_FPALA1_DEDICATED_AUTOMATION_CONTRACT_DESIGN_NO_PUBLISH_WORK_CN.md`

## 8. Pass Criteria

FPALA0 可通过条件：

- 证据完整。
- no-publish 边界未破。
- protected pointers 未变。
- daily-auto alignment gap 有本地证据支持。
- FPALA1 work document 明确 dedicated gate 设计范围，不授权 publish/switch/cron。
