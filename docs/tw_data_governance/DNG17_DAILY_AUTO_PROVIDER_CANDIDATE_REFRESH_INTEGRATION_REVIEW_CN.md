# DNG17 Daily Auto Provider Candidate Refresh Integration 审查意见

生成时间：2026-06-29

## 1. Verdict

```text
PASS_WITH_CONDITIONS_GO_DNG18
```

审查结论：DNG17 主验收路径通过，可以进入 DNG18 end-to-end daily auto shadow closure，但 DNG18 前必须补齐两个条件证据：

1. 补跑或补写一条默认关闭回归：`--enable-model-signal-gate` 开启但 `--enable-provider-candidate-refresh` 未开启时，DNG17 provider candidate refresh/reuse gate 的预期行为必须明确，不能让 `provider_candidate_refresh_gate.enabled=false` 的状态被复用 helper 写成 `enabled=true`。
2. 补一条无可用 candidate 的 refresh failure probe，证明 live refresh 失败且没有 current/prior/fixture candidate 时，`model_a_score_status=BLOCKED_PROVIDER_CANDIDATE_REFRESH` 或等价 blocked 状态会落盘。现有失败探针只证明 provider refresh 安全 blocked，后续 model gate 仍复用 existing isolated score。

上述条件不阻止 DNG18 进入 readonly/shadow closure，因为本轮 safe dry-run 是显式开启 DNG17 gate 的验收路径，且未触发 formal/latest/production/trading/target。

## 2. Findings

### Critical

无。

### High

无。

### Medium

1. 主验收路径满足 DNG17：显式 gate 开启、`--skip-qlib` 未阻断 safe candidate gate、current job 写入 DNG17 decision/readiness。
   - 命令证据来自 `data_tw/catalog/dng17_daily_auto_provider_candidate_refresh_integration_validation.json`：

```text
python scripts/run_daily_tw_stock_auto_update.py --asof 2026-06-26 --force --skip-finmind --skip-qlib --enable-model-signal-gate --enable-provider-candidate-refresh --today-earliest-time 00:00
exit_code=0
job_id=daily_tw_stock_auto_update_20260626_20260629T142612Z
```

   - `job.json` 记录：

```text
model_signal_gate_enabled=true
provider_candidate_refresh_gate_enabled=true
provider_candidate_refresh_default_reachable=false
legacy_provider_publish_enabled=false
yahoo_refresh_triggered=false
provider_publish_triggered=false
latest_signal_updated=false
```

   - `provider_candidate_refresh_gate.status=READY_REUSED_VALIDATED_PROVIDER_CANDIDATE`，`provider_candidate_refresh_triggered=false`，`provider_candidate_reused_existing=true`。
   - `provider_candidate_refresh_decision.json` 与 `provider_candidate_readiness.json` 已写入当前 job：

```text
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T142612Z/provider_candidate_refresh_decision.json
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T142612Z/provider_candidate_readiness.json
```

2. `--skip-qlib` 只阻止 legacy formal provider refresh/publish，不阻止 DNG17 safe candidate gate。
   - `scripts/run_daily_tw_stock_auto_update.py` 中 legacy formal path 只在 `not args.skip_qlib and args.enable_legacy_provider_publish` 下执行。
   - DNG17 `run_provider_candidate_refresh_gate(...)` 在 legacy qlib path 之后独立执行，参数为 `enabled=args.enable_provider_candidate_refresh` 与 `model_signal_gate_enabled=args.enable_model_signal_gate`。
   - 本轮 safe dry-run 中 `--skip-qlib` 下仍写出 DNG17 candidate decision/readiness，且 formal `option_c_150_qlib_bin` 未 publish。

3. model_signal_gate 正确消费 current-job DNG17 readiness，并复用 existing isolated Model A score，validator PASS。
   - `data_tw/ops/daily_auto_update/dng9_model_signal_gate_dry_run/model_signal_gate_summary.json` 记录：

```text
mode=daily_auto_gate_reused_existing_isolated
provider_selection_mode=validated_isolated_provider_candidate
isolated_candidate_used=true
isolated_candidate_readiness_path=data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T142612Z/provider_candidate_readiness.json
reused_existing_model_a_artifact=true
model_a_status=SCORED_ASOF_TARGET
model_b_status=BLOCKED_INPUT_NOT_READY
publish_latest_gate=false
accepted_latest_switch=false
```

   - `data_tw/catalog/dng9_model_signal_gate_validation.json` 记录 `ok=true`、`status=PASS`、`forbidden_actions_all_false=true`。

4. daily_chain_status 正确表达 formal stale / isolated ready / latest not switched。
   - `data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T142612Z/daily_chain_status.json` 记录：

```text
raw_status=READY_FROM_PRIOR_JOB
qlib_provider_view_status=BLOCKED_PROVIDER_VIEW_STALE
formal_calendar_max=2026-06-25
latest_signal_asof=2026-06-17
model_a_inference_input_status=READY_EXISTING_ISOLATED_ARTIFACT
model_a_score_status=READY_EXISTING_ISOLATED_ARTIFACT
model_a_signal_status=READY_EXISTING_ISOLATED_ARTIFACT
provider_candidate_refresh_status=READY_REUSED_VALIDATED_PROVIDER_CANDIDATE
blocked_at=qlib_provider_view_or_formal_calendar
```

5. failure safety probe 证明 live refresh 失败不会触发 formal/latest/fallback，但没有完整覆盖“无 candidate 时 Model A blocked”场景。
   - `daily_tw_stock_auto_update_20260626_20260629T142415Z/job.json` 记录：

```text
provider_candidate_refresh_gate.status=BLOCKED_YAHOO_STAGED_REFRESH_FAILED
provider_candidate_refresh_triggered=true
provider_candidate_reused_existing=false
formal_provider_mutated=false
formal_normalized_mutated=false
latest_signal_updated=false
finmind_fallback=false
mixed_provider_bridge=false
```

   - 失败原因是本机 `127.0.0.1:7890` proxy 不可连接。
   - 但该 probe 后续 `model_signal_gate` 仍通过 DNG15_R-A-R fixture / existing isolated artifact 得到 `model_a_score_status=READY_EXISTING_ISOLATED_ARTIFACT`，因此它证明的是 refresh 失败不会越权 publish/fallback，不是“完全无 candidate 时 model score blocked”的证据。

### Low

1. current job 的包装层与 readiness 自身的 `candidate_source` 语义略不一致。
   - `job.json` 嵌入 candidate 时显示 `candidate_source=current_job_dng17`。
   - current job 的 `provider_candidate_readiness.json` 自身记录 `candidate_source=dng15_r_a_r_fixture`，并带 `reused_*_path` 指向 DNG15_R-A-R catalog。
   - 这不影响本轮 PASS_WITH_CONDITIONS，因为实际语义是“当前 job 写入 DNG17 包装产物，内容复用 validated DNG15_R-A-R fixture”。DNG18 文档应继续保持该语义清晰。

2. `scripts/build_tw_dng15_r_b_isolated_modela_score_integration.py` 已新增 `--decision-path` / `--readiness-path`，但默认仍指向 DNG15_R-A-R fixture。
   - 这符合 DNG17 复用模式。
   - DNG18 若要验证 generated daily-auto candidate，应显式传入 current-job 或 candidate-job decision/readiness。

## 3. Mainline Compliance

DNG17 工作文档要求已大体满足：

```text
--enable-provider-candidate-refresh exists
TW_DAILY_AUTO_ENABLE_PROVIDER_CANDIDATE_REFRESH default false
requires model_signal_gate before provider candidate gate proceeds
--skip-qlib blocks legacy formal refresh/publish only
safe dry-run writes provider_candidate_refresh_decision/readiness to current job
candidate readiness pass or reused existing pass
model_signal_gate validation PASS
publish_latest_gate=false
accepted_latest_switch=false
latest_signal_updated=false
readonly_latest_publish=false
agent_prompt_publish=false
production_allowed=false
```

需要条件补强的合规点：

```text
default-disabled provider candidate refresh/reuse behavior needs explicit regression evidence
no-candidate refresh-failure model_a blocked behavior needs explicit regression evidence
```

## 4. Evidence Checked

必读材料：

```text
docs/tw_data_governance/DNG17_DAILY_AUTO_PROVIDER_CANDIDATE_REFRESH_INTEGRATION_WORK_CN.md
docs/tw_data_governance/DNG17_DAILY_AUTO_PROVIDER_CANDIDATE_REFRESH_INTEGRATION_EXECUTION_REPORT_CN.md
docs/tw_data_governance/DNG16_DAILY_AUTO_MODEL_SCORE_INTEGRATION_DESIGN_REVIEW_CN.md
/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md
```

JSON / dry-run artifact：

```text
data_tw/catalog/dng17_daily_auto_provider_candidate_refresh_integration_validation.json
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T142612Z/job.json
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T142612Z/daily_chain_status.json
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T142612Z/provider_candidate_refresh_decision.json
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T142612Z/provider_candidate_readiness.json
data_tw/ops/daily_auto_update/dng9_model_signal_gate_dry_run/model_signal_gate_summary.json
data_tw/catalog/dng9_model_signal_gate_validation.json
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T142415Z/job.json
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T142415Z/daily_chain_status.json
```

代码段：

```text
scripts/run_daily_tw_stock_auto_update.py
- provider_candidate_forbidden_actions
- validate_isolated_provider_candidate
- find_validated_isolated_provider_candidate
- dng17_reuse_candidate_artifacts
- enrich_dng17_generated_candidate_artifacts
- run_provider_candidate_refresh_gate
- run_model_signal_gate
- argparse --enable-provider-candidate-refresh
- legacy --skip-qlib / --enable-legacy-provider-publish branch

scripts/build_tw_dng15_r_b_isolated_modela_score_integration.py
- --decision-path
- --readiness-path
```

## 5. Missing Evidence Or Open Questions

1. 缺少默认关闭回归证据。
   - 代码中 `run_provider_candidate_refresh_gate` 在检查 `enabled` 前先查找并复用 prior/fixture candidate。
   - 因此当 `--enable-model-signal-gate` 开启但 `--enable-provider-candidate-refresh` 未开启时，如果存在 validated candidate，当前实现可能仍写 current-job DNG17 decision/readiness。
   - 这可能是有意允许 DNG16 candidate selection reuse，也可能是 DNG17 explicit gate 边界不够清晰；需要 DNG18 前明确。

2. 缺少 no-candidate refresh failure 的 blocked 证据。
   - 现有失败探针证明 Yahoo/Scrapling refresh 失败不会触发 formal/latest/FinMind/mixed provider。
   - 但它没有证明无 candidate 时 `model_a_score_status=BLOCKED_PROVIDER_CANDIDATE_REFRESH`，因为后续 model_signal_gate 复用了 existing isolated Model A artifact。

## 6. Forbidden Actions Audit

审查结论：干净。

本轮主验收 job 与 model gate summary 均未触发：

```text
formal provider publish=false
formal provider overwrite/mutation=false
formal normalized overwrite/mutation=false
accepted latest switch=false
latest_signal update=false
readonly latest publish=false
Agent prompt latest publish=false
production default model/strategy switch=false
strategy replay / NAV=false
broker/order/quick-trade=false
target_position / target_weight=false
FinMind fallback=false
mixed provider bridge=false
model training/tuning=false
```

补充核查：

```text
formal_calendar_max=2026-06-25
target_asof=2026-06-26
latest_signal_before=2026-06-17
latest_signal_after=2026-06-17
research_only=true
production_trade_enabled=false
```

## 7. Next Work Document

DNG18 可以启动：`DNG18 End-to-End Daily Auto Shadow Closure`。

DNG18 范围建议：

```text
1. 固化 daily auto shadow closure，不授权 formal provider publish / accepted latest switch / production trading。
2. 使用 DNG17 current-job provider_candidate_readiness 与 DNG9 model_signal_gate PASS 作为 readonly/shadow 输入证据。
3. 补默认关闭回归：不传 --enable-provider-candidate-refresh 时，明确 provider candidate refresh/reuse gate 的预期状态并落盘验证。
4. 补 no-candidate failure probe：临时隔离 current/prior/fixture candidate 或用测试 harness 注入空 candidate，证明 refresh 失败时不会生成 Model A score，且 daily_chain_status blocked。
5. 继续要求 all forbidden actions false。
```

不得在 DNG18 默认路径中执行：

```text
formal provider publish
accepted latest switch
latest_signal update
readonly/Agent latest publish
production default switch
strategy replay/NAV unless DNG18 work document explicitly defines readonly shadow-only scope
broker/order/quick-trade
target_position/target_weight
FinMind fallback
mixed-provider bridge
model training/tuning
```

## 8. Command For Coordinator Or Executor

```text
请启动 DNG18 End-to-End Daily Auto Shadow Closure。
读取 DNG17 review、DNG17 execution report、DNG17 validation JSON、DNG9 model_signal_gate summary/validation、current job decision/readiness。
先补两条条件证据：默认关闭回归、no-candidate refresh failure blocked probe。
然后只在 readonly/shadow closure 范围内推进，不 publish formal provider，不切 latest，不交易，不生成 target。
```
