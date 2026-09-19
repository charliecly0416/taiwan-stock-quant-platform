# DNG17 Daily Auto Provider Candidate Refresh Integration 工作文档

生成日期：2026-06-29

## 1. 背景

DNG16 已通过审查：

```text
PASS_GO_DNG17_DAILY_AUTO_PROVIDER_CANDIDATE_REFRESH_INTEGRATION
```

DNG16 已实现：

- daily auto `model_signal_gate` 能识别并复用 existing isolated Model A artifact；
- formal provider stale 时，`qlib_provider_view_status` 保持 `BLOCKED_PROVIDER_VIEW_STALE`；
- Model A 三项可以标记为 `READY_EXISTING_ISOLATED_ARTIFACT`；
- publish/latest/production/trading/target 全部保持 false。

但 DNG16 仍依赖手工完成的 DNG15_R-A-R / DNG15_R-B fixed artifact：

```text
data_tw/catalog/dng15_r_a_r_modela_20260626_candidate_readiness.json
data_tw/catalog/dng15_r_b_isolated_modela_score_integration_validation.json
```

DNG17 要把 `staged provider candidate refresh / validation / smoke / readiness` 纳入 daily auto 的 safe flow，让 daily auto 在显式 gate 下可以自己生成或复用 isolated provider candidate。

## 2. 目标

当 daily auto 显式开启 model signal gate，且 formal provider calendar 不覆盖 target asof 时，daily auto 应能：

```text
check existing validated isolated provider candidate
if missing and candidate refresh gate enabled:
  run Yahoo/Scrapling staged refresh into isolated daily-auto candidate dir
  validate candidate_normalized
  build staged_qlib_bin
  validate staged provider
  run Model A staged smoke
  write DNG17 candidate readiness / decision artifacts
then allow DNG16 isolated score gate to consume candidate
```

默认仍不允许 formal provider publish：

```text
formal_provider_publish=false
accepted_latest_switch=false
latest_signal_updated=false
readonly_latest_publish=false
agent_prompt_publish=false
production_allowed=false
```

## 3. 非目标 / 禁止动作

本阶段禁止：

- formal provider publish；
- formal provider overwrite；
- formal normalized overwrite；
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
- model training / tuning。

允许：

- 在 explicit non-default gate 下运行 Yahoo/Scrapling staged candidate refresh；
- 写入 isolated daily auto candidate directory；
- 生成 DNG17 candidate readiness / decision；
- 复用 DNG15_R-A-R artifact builder 逻辑；
- 触发 DNG15_R-B isolated score builder；
- 运行 safe dry-run。

## 4. Daily Auto Gate 设计

新增参数建议：

```text
--enable-provider-candidate-refresh
```

环境变量建议：

```text
TW_DAILY_AUTO_ENABLE_PROVIDER_CANDIDATE_REFRESH=false
```

默认必须是 false。

当 `--enable-model-signal-gate` 为 true 且 `--enable-provider-candidate-refresh` 为 true 时，daily auto 才可以在 formal provider stale 时尝试 staged candidate refresh。

### 4.1 Candidate job 目录

建议写入：

```text
qlib_pipeline/data_tw/experiments/daily_auto_provider_candidates/<job_id>/
  candidate_normalized/
  staged_qlib_bin/
  reports/
```

不得写入：

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin
```

### 4.2 Candidate readiness artifact

daily auto job_dir 下必须写：

```text
provider_candidate_refresh_decision.json
provider_candidate_readiness.json
```

并在 job.json / model_signal_gate_summary / daily_chain_status 中引用。

字段至少包含：

```text
asof
job_id
candidate_job_dir
candidate_normalized_path
staged_provider_path
source_provider=Yahoo
source_client=Scrapling
proxy_used
fetch_status
symbols_expected
symbols_success
symbols_with_asof
provider_validation_status
calendar_has_asof
calendar_max
model_smoke_status
prediction_rows
finite_prediction_share
production_allowed=false
publish_latest_authorized=false
formal_provider_mutated=false
formal_normalized_mutated=false
latest_signal_updated=false
finmind_fallback=false
mixed_provider_bridge=false
forbidden_actions
```

### 4.3 Candidate selection

`find_validated_isolated_provider_candidate(asof)` 应优先查：

1. current job 的 DNG17 candidate readiness；
2. latest daily-auto candidate readiness for same asof；
3. DNG15_R-A-R fixture 作为 fallback。

必须记录 `candidate_source`：

```text
current_job_dng17
prior_daily_auto_dng17
dng15_r_a_r_fixture
none
```

### 4.4 Skip/reuse behavior

如果已有 same-asof daily-auto candidate readiness 且 validator pass：

```text
provider_candidate_refresh_triggered=false
provider_candidate_reused_existing=true
```

如果没有 candidate 且 gate disabled：

```text
provider_candidate_refresh_status=DISABLED_BY_DEFAULT
```

如果没有 candidate 且 gate enabled 但 Yahoo/Scrapling 失败：

```text
provider_candidate_refresh_status=BLOCKED_YAHOO_STAGED_REFRESH_FAILED
model_a_score_status=BLOCKED_PROVIDER_CANDIDATE_REFRESH
```

## 5. Safe Dry-Run 验收

执行者必须至少跑一个 safe dry-run：

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

说明：

- `--skip-qlib` 只表示不要走 legacy formal provider refresh/publish；
- 不得阻止 safe provider candidate refresh gate；
- 如果已有 DNG17 candidate 可复用，可以不重新抓 Yahoo；
- 如果需要验证真正 refresh，可用新 run id/job dir，但仍不得 publish formal provider。

## 6. 必须生成产物

执行者必须生成：

```text
docs/tw_data_governance/DNG17_DAILY_AUTO_PROVIDER_CANDIDATE_REFRESH_INTEGRATION_EXECUTION_REPORT_CN.md
data_tw/catalog/dng17_daily_auto_provider_candidate_refresh_integration_validation.json
```

safe dry-run job 下应包含：

```text
job.json
daily_chain_status.json
skipped_asof_ledger.json
provider_candidate_refresh_decision.json 或明确 reused path
provider_candidate_readiness.json 或明确 reused path
```

## 7. 验证要求

至少运行：

```bash
python -m py_compile \
  scripts/run_daily_tw_stock_auto_update.py \
  scripts/build_tw_dng15_r_a_r_yahoo_access_repair_artifacts.py \
  scripts/build_tw_dng15_r_b_isolated_modela_score_integration.py
```

必须验证：

```text
safe dry-run exit code=0
provider_candidate_refresh gate explicitly enabled
formal provider calendar remains stale if not published
candidate readiness pass or reused existing pass
model_signal_gate validation PASS
publish_latest_gate=false
accepted_latest_switch=false
latest_signal_updated=false
readonly_latest_publish=false
agent_prompt_publish=false
production_allowed=false
all forbidden actions false
```

## 8. 审查要求

审查者必须生成：

```text
docs/tw_data_governance/DNG17_DAILY_AUTO_PROVIDER_CANDIDATE_REFRESH_INTEGRATION_REVIEW_CN.md
```

verdict 只能是：

```text
PASS_GO_DNG18_END_TO_END_DAILY_AUTO_SHADOW_CLOSURE
PASS_WITH_CONDITIONS_GO_DNG18
FAIL_NEEDS_DNG17_REPAIR
STOP_NEEDS_COORDINATOR_DECISION
```

通过条件：

- daily auto 可以在 explicit gate 下生成或复用 validated provider candidate；
- daily auto model_signal_gate 可以消费 candidate 或 existing isolated score；
- daily_chain_status 正确表达 formal stale / isolated candidate ready / model signal ready；
- forbidden actions 全 false；
- 不 publish formal provider，不切 latest。

## 9. 执行者命令

```text
请执行 DNG17 Daily Auto Provider Candidate Refresh Integration。
读取本工作文档、DNG16 审查意见、run_daily_tw_stock_auto_update.py 当前实现、DNG15_R-A-R artifact builder。
实现 explicit provider candidate refresh gate，并运行 safe dry-run。
保持 formal/latest/production/trading/target 全部禁止。
完成后写执行报告和 validation JSON。
```

## 10. 审查者命令

```text
请独立审查 DNG17 执行结果。
重点检查 daily auto 是否在 explicit gate 下生成/复用 provider candidate，是否没有 publish/latest/production/trading/target，是否能进入 DNG18 shadow closure。
```
