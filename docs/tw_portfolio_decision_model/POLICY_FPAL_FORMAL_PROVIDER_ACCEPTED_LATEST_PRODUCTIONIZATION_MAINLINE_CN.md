# POLICY FPAL: Formal Provider / Accepted Latest Productionization Mainline

## 1. 目标

FPAL 是 `Formal Provider / Accepted Latest Productionization` 的独立主线，用来把已经在日更中自然生成并通过只读验证的 provider candidate，谨慎推进到正式 provider 数据与 qlib accepted latest 指针。

本主线只解决两类对象：

- formal provider dataset: `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/`
- qlib accepted latest pointer: `qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json`

核心目标是让正式 provider 与 accepted latest 也具备每日自动推进能力，避免后续实验继续遇到某些正式输入长期停在旧日期的问题。

## 2. 非目标

FPAL 不处理下列事项：

- DAPR18 controlled product latest 的稳定运维发布链路。
- canonical ModelSignalArtifact product latest。
- readonly strategy snapshot latest。
- Agent DailyAgentPromptArtifact latest。
- legacy latest: `data_tw/experiments/option_c_daily_signal/latest_signal.json`。
- frontend/API production default switch。
- TradingAgents、策略 replay、新模型训练、新策略开发。
- OpenAI、DB 写入、monitor、broker、order、target position、target weight。

DAPR18 controlled product latest stable ops must not be used as authorization for formal provider publish or qlib accepted latest switch.

## 3. 当前基线

FPAL0 只读基线显示：

- formal provider calendar 当前停在 `2026-06-25`。
- qlib accepted latest 当前为 `2026-07-08`。
- legacy latest 当前为 `2026-06-01`，`target_date=2026-06-02`。
- DAPR18 controlled product latest 当前为 `2026-08-06`。
- 最新自然生成 provider candidate 为 `2026-08-06`，Yahoo/Scrapling/proxy candidate 已达 150/150，并且 staged provider validation 与 model smoke 均为 pass。

因此，项目已经具备新鲜候选输入，但正式 provider 与 accepted latest 尚未被授权推进。

## 4. 路线边界

四个 latest 概念必须分开：

- provider raw/latest: source 或 staged provider 数据可用性。
- qlib accepted latest: 受保护的 accepted signal/latest 指针。
- readonly strategy snapshot latest: 前端只读策略快照。
- Agent DailyAgentPromptArtifact latest: Agent 上下文和 prompt artifact。

FPAL 只覆盖 formal provider 与 qlib accepted latest，不继承 DAPR18 对 product latest 的自动发布授权。

## 5. 阶段计划

### FPAL0_READONLY_BASELINE_AND_CONTRACT

只读盘点正式 provider、accepted latest、legacy latest、DAPR18 product latest 和最新 provider candidate。输出主线、执行报告、审查报告和 FPAL1 工作单。

允许：

- 本地文件读取。
- `tail`、`wc`、`sha256sum`、`jq`、`find`、`rg`。
- 仅写入 FPAL 文档。

禁止：

- provider pull/publish。
- formal provider mutation。
- qlib refresh。
- accepted latest switch。
- DAPR18 product latest publish。
- daily auto manual run 或 cron 修改。

### FPAL1_EXACT_TARGET_PROVIDER_CANDIDATE_PREFLIGHT_NO_PUBLISH

使用现有 provider candidate 做 no-publish preflight，判断是否满足正式 provider 发布前置条件。默认输入为：

`qlib_pipeline/data_tw/experiments/daily_auto_provider_candidates/daily_auto_provider_candidate_20260806_20260806T103148Z`

FPAL1 不得重新拉 provider，不得写正式 provider，不得切 accepted latest。

### FPAL2_FORMAL_PROVIDER_PUBLISH_PREFLIGHT_OR_STOP

生成正式 provider publish 的精确写入方案、rollback 方案、fingerprint 方案、diff 方案和 validation 方案。该阶段仍然 no-publish。若缺少任何 rollback 或 validator 证据，必须 STOP。

### FPAL3_ACTUAL_FORMAL_PROVIDER_PUBLISH_WITH_EXACT_AUTHORIZATION

仅在用户给出 exact authorization 后执行。允许写入范围必须逐文件列出。执行前必须创建 rollback copy 和 protected pointer fingerprints；执行后必须执行 after fingerprints、diff、provider validation、calendar validation 和 post-write review。

FPAL3 不授权 accepted latest switch。

### FPAL4_ACCEPTED_LATEST_SWITCH_PREFLIGHT_OR_STOP

在 formal provider 已通过 FPAL3 后，构建 accepted latest switch 候选并做 no-publish preflight。必须验证 source lineage、target_asof、run_id、checksum、schema、QlibOptionCSignalReader 兼容性、rollback 方案和 forbidden scope。

### FPAL5_ACTUAL_ACCEPTED_LATEST_SWITCH_WITH_EXACT_AUTHORIZATION_AND_DOWNSTREAM_READONLY_OBSERVATION

仅在用户给出 exact authorization 后执行 accepted latest 指针切换。写后必须验证 qlib accepted latest payload、QlibOptionCSignalReader、protected pointers 不变项，以及 DAPR18 product latest/readonly snapshot/Agent prompt latest 没有被隐式改写。

## 6. 禁止动作

除非某个后续阶段获得用户 exact authorization，否则全路线禁止：

- `scripts/run_daily_tw_stock_auto_update.py`
- real Yahoo/FinMind pull
- provider refresh / publish
- formal provider mutation
- qlib refresh
- accepted latest switch
- legacy latest switch
- DAPR18 product latest publish
- readonly snapshot latest publish
- Agent prompt build/publish
- OpenAI call
- DB access/write
- strategy replay
- monitor config save / scan / alerts write
- broker / quick-trade / order
- target_position / target_weight
- frontend/API production default switch
- cron install / cron flag / default changes

## 7. 停止条件

任一条件出现即停止并回报：

- provider candidate 缺失或 target_asof 不等于预期。
- candidate validation 不是 pass。
- 150 symbols 未完整覆盖。
- staged provider calendar 不含 target_asof。
- formal provider 或 latest 指针在 no-publish 阶段发生变化。
- rollback copy、fingerprint、diff 或 validator 方案不完整。
- 需要 provider pull、qlib refresh、accepted switch、cron 修改或任何受保护写入但没有 exact authorization。
- DAPR18 product latest 被误用为 formal provider/accepted latest 授权。

## 8. 证据要求

每阶段执行者必须输出：

- 输入路径和 target_asof。
- before fingerprints。
- validation 摘要。
- forbidden actions audit。
- changed files。
- pass/fail 建议。

每阶段审查者必须输出：

- Findings by severity。
- Mainline compliance。
- Evidence checked。
- Missing evidence/open questions。
- Forbidden actions audit。
- Next work document。

## 9. FPAL0 执行者命令

执行者只读复核：

```text
Read this mainline and collect file-only evidence for FPAL0. Do not run provider pull, daily auto, qlib refresh, latest switch, OpenAI, DB, monitor, broker, order, target, or cron commands. Produce FPAL0 execution report with baseline fingerprints and recommendation.
```

## 10. FPAL0 审查者命令

审查者只读审查：

```text
Review FPAL0 execution report against this mainline. Verify that only docs changed, formal provider and latest pointers were not mutated, DAPR18 product latest is treated as separate stable ops, and FPAL1 remains no-publish. Produce PASS/FAIL verdict and next work document.
```
