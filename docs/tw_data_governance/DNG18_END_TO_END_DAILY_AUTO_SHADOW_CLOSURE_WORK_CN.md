# DNG18 End-to-End Daily Auto Shadow Closure 条件修复与闭环工作文档

生成日期：2026-06-29

## 1. 背景

DNG17 `Daily Auto Provider Candidate Refresh Integration` 审查结论为：

```text
PASS_WITH_CONDITIONS_GO_DNG18
```

DNG17 主路径已经证明：

- daily auto 新增 `--enable-provider-candidate-refresh` / `TW_DAILY_AUTO_ENABLE_PROVIDER_CANDIDATE_REFRESH` 显式 gate，默认 false；
- `--skip-qlib` 不触发 legacy formal provider refresh/publish；
- formal provider calendar 停在 `2026-06-25` 时，可在 explicit gate 下复用 validated isolated Yahoo/Scrapling provider candidate；
- model signal gate 可消费 current-job provider candidate readiness，并复用/生成 isolated Model A score；
- `latest_signal`、accepted latest、readonly/Agent latest、production/trading/target 全部未推进。

但 DNG17 审查留下两个必须在 DNG18 开头完成的条件：

1. 默认关闭回归证据不足：当 `--enable-model-signal-gate` 开启但 `--enable-provider-candidate-refresh` 未开启时，provider candidate refresh/reuse gate 的行为必须明确，不能出现 gate disabled 却写出 enabled/current-job candidate 的歧义。
2. no-candidate failure blocked 证据不足：必须证明当没有 current/prior/fixture candidate 且 live refresh 失败时，Model A 被阻断，例如 `model_a_score_status=BLOCKED_PROVIDER_CANDIDATE_REFRESH` 或等价状态，而不是继续复用既有 isolated score。

## 2. DNG18 目标

DNG18 是 DNG15-DNG17 daily auto isolated/shadow 链路的闭环阶段。目标不是推进正式生产，而是把 daily auto 的“可自动补足 provider candidate -> Model A score/signal -> chain status”这条 readonly/shadow 路径的边界补完整。

必须完成：

1. 修复或明确 `provider_candidate_refresh_gate` 默认关闭语义。
2. 增加 no-candidate / no-existing-isolated-score 的隔离测试能力，证明 failure 会安全 blocked。
3. 重跑 safe dry-run，保留 DNG17 主路径通过证据。
4. 写 DNG18 execution report 和 DNG18 review，给出 closure 结论。

## 3. 非目标 / 禁止动作

DNG18 禁止：

- formal provider publish；
- formal provider overwrite/mutation；
- formal normalized overwrite/mutation；
- qlib accepted latest switch；
- `latest_signal.json` update；
- readonly latest publish；
- Agent prompt latest publish；
- production default model/strategy switch；
- strategy replay / NAV；
- broker/order/quick-trade；
- target_position / target_weight；
- FinMind fallback；
- mixed-provider bridge；
- model training / tuning；
- 使用 FinMind raw 作为 Model A qlib 输入。

允许：

- 修改 `scripts/run_daily_tw_stock_auto_update.py` 的 explicit gate、fallback 选择、测试隔离开关与 chain status 表达；
- 运行 safe dry-run：`--skip-finmind --skip-qlib --today-earliest-time 00:00`；
- 使用 already validated isolated DNG15_R-A-R candidate 作主路径复用证据；
- 为 no-candidate 失败探针新增默认关闭的测试开关或环境变量；
- 写入 `data_tw/ops/daily_auto_update/<job_id>/` 与 `data_tw/catalog/dng18_*.json` 证据。

## 4. 必做修复

### 4.1 默认关闭回归

当参数为：

```bash
python scripts/run_daily_tw_stock_auto_update.py \
  --asof 2026-06-26 \
  --force \
  --skip-finmind \
  --skip-qlib \
  --enable-model-signal-gate \
  --today-earliest-time 00:00
```

且未传 `--enable-provider-candidate-refresh` 时，必须满足：

```text
job.provider_candidate_refresh_gate.enabled=false
job.provider_candidate_refresh_status=DISABLED_BY_DEFAULT 或 DISABLED_PROVIDER_CANDIDATE_REFRESH_GATE
provider_candidate_refresh_triggered=false
provider_candidate_reused_existing=false
不得写 current-job provider_candidate_refresh_decision.json/readiness.json
```

注意：model_signal_gate 是否可复用既有 isolated Model A artifact 可以另行表达，但 provider candidate refresh/reuse gate 本身不能在 disabled 状态下复用 candidate 并写出 current-job DNG17 candidate artifact。

### 4.2 no-candidate failure blocked 探针

执行者必须提供一种隔离方式，让测试路径中暂时不可见：

- current-job provider candidate；
- prior daily-auto provider candidate；
- DNG15_R-A-R fixture；
- existing isolated Model A artifact。

推荐新增默认关闭的 CLI/env：

```text
--dng18-disable-provider-candidate-fallbacks
TW_DAILY_AUTO_DNG18_DISABLE_PROVIDER_CANDIDATE_FALLBACKS=false

--dng18-disable-existing-isolated-modela-reuse
TW_DAILY_AUTO_DNG18_DISABLE_EXISTING_ISOLATED_MODELA_REUSE=false
```

这些开关只允许用于 DNG18 probe，不得改变默认生产/readonly路径。

在 live refresh 无法成功时，必须落盘证明：

```text
provider_candidate_refresh_gate.status=BLOCKED_YAHOO_STAGED_REFRESH_FAILED 或 BLOCKED_PROVIDER_CANDIDATE_REFRESH
model_signal_gate.ok=false
model_signal_gate.provider_selection_mode=blocked_no_validated_provider
model_a_score_status=BLOCKED_PROVIDER_CANDIDATE_REFRESH 或 BLOCKED_ISOLATED_PROVIDER_CANDIDATE
provider_publish_triggered=false
formal_provider_mutated=false
formal_normalized_mutated=false
latest_signal_updated=false
accepted_latest_switch=false
FinMind fallback=false
mixed-provider bridge=false
```

如果本地 proxy 可用且 live refresh 意外成功，执行者必须改用安全的 mock/command_runner harness 或无效 proxy probe，不能为了制造失败去修改 formal 数据。

## 5. 主路径 closure dry-run

条件修复完成后，仍需保留 DNG17 主验收路径：

```bash
python scripts/run_daily_tw_stock_auto_update.py \
  --asof 2026-06-26 \
  --force \
  --skip-finmind \
  --skip-qlib \
  --enable-model-signal-gate \
  --enable-provider-candidate-refresh \
  --today-earliest-time 00:00
```

验收要点：

```text
provider_candidate_refresh_status=READY_REUSED_VALIDATED_PROVIDER_CANDIDATE 或 READY_GENERATED_DNG17_PROVIDER_CANDIDATE
model_a_score_status=READY_EXISTING_ISOLATED_ARTIFACT 或 READY_ISOLATED_CANDIDATE
formal_calendar_max 仍可停在 2026-06-25
latest_signal_asof 不得推进
publish_latest_gate_status=DISABLED_BY_DEFAULT
forbidden_actions.all_false=true
```

## 6. 执行报告要求

执行者必须写：

```text
docs/tw_data_governance/DNG18_END_TO_END_DAILY_AUTO_SHADOW_CLOSURE_EXECUTION_REPORT_CN.md
```

必须列出：

- 修改文件；
- 新增 CLI/env；
- default-disabled regression job_id 与 artifact path；
- no-candidate failure probe job_id 与 artifact path；
- closure dry-run job_id 与 artifact path；
- py_compile / validator 输出；
- forbidden actions audit；
- 是否建议 closure。

建议另写聚合验证：

```text
data_tw/catalog/dng18_end_to_end_daily_auto_shadow_closure_validation.json
```

## 7. 审查要求

审查者必须写：

```text
docs/tw_data_governance/DNG18_END_TO_END_DAILY_AUTO_SHADOW_CLOSURE_REVIEW_CN.md
```

审查者必须独立检查：

- 默认关闭回归是否真的没有写 current-job provider candidate artifacts；
- no-candidate failure probe 是否真的隔离了 prior/fixture/existing isolated score；
- no-candidate failure 时 Model A 是否 blocked；
- closure dry-run 是否仍通过；
- formal/latest/production/trading/target 是否全部未触发；
- 新增测试开关是否默认关闭，且不会影响常规 daily auto 行为。

## 8. 通过标准

可以判定 `PASS_DNG18_CLOSURE` 的最低标准：

```text
DNG17 两个条件均补齐
主 closure dry-run 通过
forbidden actions 全部 false
文档和 JSON 证据完整
默认行为保持 closed-by-default
```

若两个条件之一缺失，判定：

```text
FAIL_NEEDS_DNG18_R_REPAIR
```

若发现 formal/latest/production/trading/target 任一被触发，判定：

```text
STOP_SAFETY_VIOLATION
```

## 9. 给执行者的命令

请作为执行者完成 DNG18：

```text
阅读 docs/tw_data_governance/DNG18_END_TO_END_DAILY_AUTO_SHADOW_CLOSURE_WORK_CN.md 与 DNG17 执行/审查报告；只在 DNG18 范围内修改 scripts/run_daily_tw_stock_auto_update.py 等必要文件；先修默认关闭回归和 no-candidate failure blocked 探针，再跑三个 safe dry-run；写执行报告和 dng18 validation JSON。不得触发 formal publish/latest/production/trading/target。
```

## 10. 给审查者的命令

请作为审查者审查 DNG18：

```text
阅读 DNG18 工作文档、执行报告、DNG17 审查报告、相关 job.json/daily_chain_status/model_signal_gate_summary/provider_candidate artifacts 与代码 diff；判断 DNG17 两个条件是否补齐，主链路是否可 closure；写 DNG18 review。不得修改代码或触发数据拉取/publish。
```
