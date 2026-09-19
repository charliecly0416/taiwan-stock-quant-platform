# POLICY FPALA: Formal Provider / Accepted Latest Automation Alignment No-Publish Mainline

## 1. 目标

FPALA 是 `Formal Provider / Accepted Latest Automation Alignment No-Publish` 独立路线。

它接在 FPAL7 closure 之后，用来把 recurring daily-auto 中的 formal provider publish 与 qlib accepted latest switch 自动化能力设计清楚、验证清楚，但本路线默认不启用真实 publish / switch。

核心目标：

- 让 daily-auto 能在未来以可审查、可回滚、可停止的方式推进 formal provider 与 qlib accepted latest。
- 避免继续依赖含义过宽的 `TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH` 作为生产默认。
- 把 provider candidate、formal provider、qlib accepted latest、DAPR18 product latest 四层边界分开。
- 在 no-publish 模式下证明自动化 gate 可以判断何时应 publish、何时应等待、何时应 block。

## 2. 非目标

FPALA 不授权：

- real Yahoo/FinMind pull。
- provider refresh / publish。
- formal provider mutation。
- qlib refresh。
- qlib accepted latest switch。
- legacy latest switch。
- DAPR18 product latest publish。
- readonly snapshot latest publish。
- Agent prompt build / publish。
- daily-auto manual run。
- cron install / cron flag enablement / actual crontab change。
- frontend/API production default switch。
- OpenAI、DB 写入、strategy replay。
- monitor、broker、quick-trade、order、target position、target weight。

FPALA 不替代 DAPR18 stable ops。DAPR18 只覆盖 controlled signal latest、readonly strategy snapshot latest、Agent prompt latest，不覆盖 formal provider 或 qlib accepted latest。

## 3. 当前基线

来自 FPAL7 closure：

- formal provider calendar 已到 `2026-08-06`。
- qlib accepted latest 已到 `2026-08-06`，run 为 `option_c_daily_signal_20260806_fpal4a_adapter_20260807T022328Z`。
- legacy latest 仍为 `2026-06-01`，保持独立。
- DAPR18 controlled product latest 三个 pointer 已到 `2026-08-06`。
- installed cron 已启用 provider candidate refresh、model signal gate、DAPR18 product latest publish。
- installed cron 未启用 `TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH=true`。
- natural daily-auto job 证明 provider candidate 可生成 150/150，并且 `production_allowed=false`、`publish_latest_authorized=false`、`formal_provider_mutated=false`、`latest_signal_updated=false`。

当前缺口：

- daily-auto 有 `publish_accepted_latest(asof)` 路径，但它挂在 broad legacy provider publish gate 后面。
- recurring formal provider publish / qlib accepted latest switch 没有独立生产化合同。
- 没有 dedicated FPAL automation flags、no-publish dry-run summary、protected pointer unchanged audit、rollback/fingerprint contract。

## 4. latest 概念边界

FPALA 必须区分：

- provider candidate: `qlib_pipeline/data_tw/experiments/daily_auto_provider_candidates/...`，自然日更生成，默认 no-publish。
- formal provider: `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/`，受保护正式 provider。
- qlib accepted latest: `qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json`，受保护 accepted pointer。
- legacy latest: `data_tw/experiments/option_c_daily_signal/latest_signal.json`，不纳入 FPALA 自动化。
- DAPR18 product latest: controlled signal latest、readonly snapshot latest、Agent prompt latest，属于另一条 stable ops 链路。

任何报告、代码、配置或 UI 文案都不得把 DAPR18 product latest 的成功误写成 formal provider / qlib accepted latest 已自动生产化。

## 5. 目标设计原则

FPALA 后续实现必须满足：

- Dedicated gate: 新增明确的 FPALA gate，不复用 broad legacy gate 作为生产默认。
- No-publish first: 每个实现阶段先输出 no-publish decision，不写 formal provider，不切 latest。
- Exact candidate contract: 明确输入 provider candidate 的路径、target_asof、150/150、calendar max、validation status、model smoke status、forbidden actions。
- Two-step production semantics: formal provider publish 与 qlib accepted latest switch 必须分别 gate，不得合并成不可拆的隐式动作。
- Rollback-first: 任何未来 actual publish/switch 都必须先有 rollback copy、before fingerprints、after fingerprints、diff、validator 和 post-write review。
- Protected pointer unchanged audit: no-publish 阶段必须证明 qlib accepted latest、legacy latest、DAPR18 product latest、readonly snapshot latest、Agent prompt latest 未变。
- Retry semantics: same-day wait、fresh_data_wait、pending_asof、candidate missing、candidate validation fail 必须有明确状态和下次重试提示。
- Idempotence: target_asof 已对齐时应 no-op，不应重复 publish/switch。

## 6. 阶段计划

### FPALA0_CONTRACT_AND_CURRENT_GATE_INVENTORY_NO_PUBLISH

只读盘点现有 daily-auto gate、legacy provider publish path、accepted latest scheduler、provider candidate readiness、FPAL7 closure evidence。

产出：

- FPALA0 execution report。
- FPALA1 work document。

禁止：

- 运行 daily-auto。
- provider pull/publish/refresh。
- accepted latest switch。
- cron 修改。

### FPALA1_DEDICATED_AUTOMATION_CONTRACT_DESIGN_NO_PUBLISH

设计 dedicated FPALA automation contract。

必须定义：

- flags 命名与默认值。
- no-publish decision schema。
- candidate input contract。
- formal provider publish preflight contract。
- accepted latest switch preflight contract。
- protected pointer audit contract。
- retry / block / idempotent statuses。
- forbidden scope audit fields。

### FPALA2_NO_PUBLISH_ORCHESTRATOR_PRECHECK_IMPLEMENTATION

实现或复用最小 no-publish precheck，使 daily-auto 可在不写入任何受保护对象的情况下输出 FPALA decision summary。

允许写：

- 脚本代码。
- validator / unit test。
- no-publish job artifact。
- execution/review docs。

禁止写：

- formal provider。
- latest pointers。
- cron。

### FPALA3_NO_PUBLISH_VALIDATOR_AND_REGRESSION

补 validator / regression，验证：

- target_asof already aligned -> idempotent no-op。
- candidate ready but publish not authorized -> ready_no_publish。
- candidate missing / validation fail -> block with pending/retry hint。
- all protected pointers unchanged。

### FPALA4_DAILY_AUTO_WIRING_NO_PUBLISH_PREFLIGHT

把 FPALA no-publish gate 接到 daily-auto 的可选路径设计中，但不安装 cron、不跑 actual daily-auto。

必须证明：

- 默认关闭。
- dry-run/no-publish 默认开启。
- 不影响 DAPR18 stable ops。
- 不影响 legacy gate。
- 不影响 frontend/API default。

### FPALA5_NATURAL_CRON_NO_PUBLISH_OBSERVATION_PACKAGE_OR_STOP

仅在后续获得明确授权后，才允许安装 no-publish observation flag 到 cron。该阶段仍不允许 formal provider publish 或 qlib accepted latest switch。

如果未授权 cron change，则 STOP 并输出 exact authorization package。

### FPALA6_ACTUAL_ENABLEMENT_PREFLIGHT_OR_STOP

如果未来要自动 publish/switch，必须先做 actual enablement preflight。

该阶段只能输出授权文本、rollback plan、diff plan、validator plan、stop conditions，不执行 actual enablement。

### FPALA7_ROUTE_CLOSURE_OR_ACTUAL_ENABLEMENT_HANDOFF

关闭 no-publish 路线，或把 actual enablement 交给新的 exact-authorization 路线。

## 7. 执行者职责

执行者必须：

- 先读本主线和当前阶段 work document。
- 只执行当前阶段。
- 保留所有证据路径、hash、status、changed files。
- 明确说明未执行的 forbidden actions。
- 遇到需要 publish/switch/cron/DB/OpenAI/交易动作时停止。

## 8. 审查者职责

审查者必须：

- 对照本主线、阶段 work document、execution report 审查。
- 独立复核关键证据。
- 检查 no-publish 边界和 protected pointer unchanged。
- 检查是否误把 DAPR18 product latest 当成 FPALA 授权。
- 输出 PASS、PASS_WITH_CONDITIONS、FAIL_NEEDS_REPAIR 或 STOP。
- 写下一步 work document，除非 STOP 需要用户确认。

## 9. 禁止动作

除非未来有新的 exact authorization，本路线全程禁止：

```text
执行 scripts/run_daily_tw_stock_auto_update.py / daily-auto manual run
real Yahoo/FinMind pull
provider refresh / publish
formal provider mutation
qlib refresh
accepted latest switch
legacy latest switch
DAPR18 product latest publish
readonly snapshot latest publish
Agent prompt build/publish
cron install / cron edit / actual crontab change
OpenAI call
DB access/write
strategy replay
monitor config save / scan / alerts write
broker / quick-trade / order
target_position / target_weight
frontend/API production default switch
```

## 10. 停止条件

任一情况出现即停止：

- 需要读取不存在或不明确的 provider candidate 才能继续。
- 需要 real provider pull/refresh。
- 需要 formal provider publish。
- 需要 qlib accepted latest switch。
- 需要 cron 修改或 daily-auto manual run。
- protected pointer hash 在 no-publish 阶段发生变化。
- candidate validation、150/150、calendar max、model smoke status 缺少证据。
- rollback/fingerprint/diff/validator 合同缺失。
- 任何输出包含真实交易、目标仓位、目标权重、broker/order/quick-trade 语义。

## 11. 证据要求

每阶段至少记录：

- target_asof / candidate_asof。
- formal provider calendar max。
- qlib accepted latest asof/run_id/hash。
- legacy latest asof/hash。
- DAPR18 product latest asof/hash。
- provider candidate readiness summary。
- cron flag inventory。
- daily-auto script path inventory。
- forbidden scope audit。
- changed files。

## 12. closure 标准

FPALA no-publish 路线完成的最低标准：

- dedicated FPALA automation contract 已审查通过。
- no-publish decision schema 已审查通过。
- no-publish precheck / validator 可证明不会写 protected objects。
- daily-auto wiring 方案清楚，默认关闭，dry-run/no-publish 可观测。
- actual publish/switch enablement 被明确移交到新的 exact-authorization 路线。

## 13. FPALA0 执行者命令

```text
进入 FPALA0_CONTRACT_AND_CURRENT_GATE_INVENTORY_NO_PUBLISH。只读盘点 FPAL7 closure、installed cron、scripts/run_daily_tw_stock_auto_update.py 中 legacy provider publish / accepted latest path、provider candidate readiness、protected pointer hashes。不得运行 daily-auto，不得 provider pull/publish/refresh，不得 qlib refresh，不得 accepted latest switch，不得 cron 修改，不得 OpenAI/DB/strategy replay/monitor/broker/order/target/frontend default switch。输出 FPALA0 execution report，并写 FPALA1 work document。
```

## 14. FPALA0 审查者命令

```text
审查 FPALA0 execution report 和 FPALA1 work document。确认证据只读、protected pointers 未变、daily-auto gap 判断属实、dedicated FPALA gate 必要性成立、没有把 DAPR18 product latest 当作 formal provider/accepted latest 授权。输出 PASS/FAIL review，并给出下一步。
```
