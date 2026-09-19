# DNG16 Daily Auto Model Score Integration Design 工作文档

生成日期：2026-06-29

## 1. 背景

DNG15_R-B 已通过审查：

```text
PASS_GO_DNG16_DAILY_AUTO_MODEL_SCORE_INTEGRATION_DESIGN
```

已经证明在 formal qlib provider 尚未 publish / accepted latest 尚未切换的情况下，daily auto 可以通过 validated isolated staged provider candidate 生成 `2026-06-26` 的标准产物：

```text
ModelInferenceInput READY
ScoreJob SCORED_ASOF_TARGET
ModelSignalArtifact READY
```

但是当前 `scripts/run_daily_tw_stock_auto_update.py` 的 `model_signal_gate` 仍有旧设计问题：

- 默认 disabled；
- enabled 后仍调用 `scripts/build_tw_model_inference_input.py` 和 `scripts/run_tw_model_score_job.py`；
- 这两个脚本仍依赖 fixed formal provider / fixed 6/25 readiness；
- 当 formal provider stale 但存在 validated isolated provider candidate 时，daily auto 不能自动进入 isolated score builder；
- `daily_chain_status` 也只表达 formal `qlib_provider_view_status=BLOCKED_PROVIDER_VIEW_STALE`，没有区分 isolated candidate score ready。

DNG16 目标是把 DNG15_R-B 的能力纳入 daily auto 的 model signal gate 设计和最小实现。

## 2. 目标

让 daily auto 在显式开启 `--enable-model-signal-gate` 时，可以：

```text
raw/ops ready
formal provider stale
validated isolated staged provider candidate ready
-> run isolated Model A score builder
-> generate/reuse ModelInferenceInput / ScoreJob / ModelSignalArtifact
-> write model_signal_gate summary
-> write daily_chain_status with isolated candidate readiness
```

同时必须保持：

```text
publish_latest_gate=false
accepted_latest_switch=false
readonly_latest_publish=false
agent_prompt_publish=false
production_allowed=false
```

最低验收 fixture：

```text
asof=2026-06-26
R-A-R staged provider candidate ready
DNG15_R-B isolated score builder runnable / existing artifact reusable
daily auto model_signal_gate can report Model A READY without formal publish
daily_chain_status does not claim formal provider ready unless formal calendar covers asof
daily_chain_status marks isolated candidate evidence separately
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

- 修改 `scripts/run_daily_tw_stock_auto_update.py` 的 model signal gate 逻辑；
- 读取 DNG15_R-A-R / DNG15_R-B artifacts 作为 fixture；
- 新增小型 validator/helper；
- 运行 daily auto safe dry-run / skip raw fetch mode；
- 生成新的 catalog / review documents。

## 4. 设计要求

### 4.1 Provider selection contract

daily auto model signal gate 必须支持两种来源：

1. `formal_provider`
   - formal `option_c_150_qlib_bin` calendar covers asof；
   - 可沿用后续 production-like model score route；
   - 但本阶段不要求改 formal route。

2. `validated_isolated_provider_candidate`
   - formal provider stale；
   - 但存在 DNG15_R-A-R 或同等合同生成的 staged provider candidate；
   - candidate readiness 显示：
     - `candidate_normalized_symbols_with_asof=150`；
     - `staged_provider_calendar_has_asof=true`；
     - provider validation pass；
     - Model A staged smoke pass；
     - forbidden actions false。
   - 使用 `scripts/build_tw_dng15_r_b_isolated_modela_score_integration.py` 生成/复用 isolated Model A score。

### 4.2 Existing artifact reuse

如果 asof 已存在 validator PASS 的 isolated Model A artifacts，daily auto 应该：

```text
model_a_status=SCORED_ASOF_TARGET
model_a_score_job=false or reused_existing=true
model_a_signal_path=<existing signal artifact>
mode=daily_auto_gate_reused_existing_isolated
```

不得重复生成同 run_id 覆盖产物，除非显式 force/run_id。

### 4.3 Summary schema extension

`model_signal_gate_summary.json` 应新增或明确：

```text
provider_selection_mode
formal_provider_calendar_covers_asof
formal_provider_calendar_max
isolated_candidate_used
isolated_candidate_readiness_path
isolated_score_builder
reused_existing_model_a_artifact
model_a_inference_input_path
model_a_score_job_path
model_a_signal_path
publish_latest_gate=false
accepted_latest_switch=false
production_allowed=false
```

### 4.4 daily_chain_status extension

`daily_chain_status.json` 应区分：

```text
qlib_provider_view_status=BLOCKED_PROVIDER_VIEW_STALE
model_a_inference_input_status=READY_ISOLATED_CANDIDATE
model_a_score_status=READY_ISOLATED_CANDIDATE
model_a_signal_status=READY_ISOLATED_CANDIDATE
```

不要把 formal provider 标记为 READY，除非 formal calendar 真的覆盖 asof。

如果 model_signal_gate disabled，但已有 isolated artifact，可在 status 中反映 `READY_EXISTING_ISOLATED_ARTIFACT`，但不得假装 daily auto 本轮触发了 score job。

### 4.5 No silent stale signal

当 asof 缺 score 时，daily auto 不得用旧 `latest_signal.json` 或旧 signal artifact 冒充 target asof。

## 5. 实现建议

建议执行者最小改动：

1. 在 `scripts/run_daily_tw_stock_auto_update.py` 新增 helper：

```text
find_validated_isolated_modela_artifact(asof)
find_validated_isolated_provider_candidate(asof)
run_isolated_modela_score_gate(...)
```

2. 修改 `run_model_signal_gate`：

- enabled 后先检查 existing validated Model A signal；
- formal provider stale 时尝试 isolated candidate route；
- route 成功后生成 summary；
- Model B 仍保持 blocked，不在本阶段推进 LTR。

3. 修改 `build_model_signal_gate_summary` / validator：

- 接收 provider selection fields；
- 保持 publish/latest/production forbidden false。

4. 修改 `build_daily_chain_status_payload`：

- 如果 `model_signal_gate` 产生或复用 isolated score，则 Model A 三项状态标记为 `READY_ISOLATED_CANDIDATE`；
- `qlib_provider_view_status` 仍按 formal calendar 判断。

5. 新增或更新测试/验证脚本：

- 用 `2026-06-26` DNG15_R-B artifact 作为 fixture；
- 调用 daily auto safe mode：

```bash
python scripts/run_daily_tw_stock_auto_update.py \
  --asof 2026-06-26 \
  --force \
  --skip-finmind \
  --skip-qlib \
  --enable-model-signal-gate \
  --today-earliest-time 00:00
```

注意：`--skip-qlib` 代表不要走 legacy formal provider refresh/publish，不应阻止 model_signal_gate 的 isolated score/readiness summary。

## 6. 必须生成产物

执行者必须生成：

```text
docs/tw_data_governance/DNG16_DAILY_AUTO_MODEL_SCORE_INTEGRATION_DESIGN_EXECUTION_REPORT_CN.md
data_tw/catalog/dng16_daily_auto_model_score_integration_design_validation.json
```

若运行 daily auto safe dry-run，还必须记录最新 job：

```text
data_tw/ops/daily_auto_update/<job_id>/job.json
data_tw/ops/daily_auto_update/<job_id>/daily_chain_status.json
data_tw/ops/daily_auto_update/<job_id>/skipped_asof_ledger.json
```

## 7. 验证要求

至少运行：

```bash
python -m py_compile scripts/run_daily_tw_stock_auto_update.py scripts/build_tw_dng15_r_b_isolated_modela_score_integration.py
```

必须验证：

```text
model_signal_gate validation PASS
publish_latest_gate=false
accepted_latest_switch=false
readonly_latest_publish=false
agent_prompt_publish=false
production_allowed=false
daily_chain_status qlib_provider_view_status remains BLOCKED_PROVIDER_VIEW_STALE if formal calendar stale
daily_chain_status model_a_* status shows isolated readiness
no latest_signal update
no formal provider publish
no target/order/trade
```

## 8. 审查要求

审查者必须生成：

```text
docs/tw_data_governance/DNG16_DAILY_AUTO_MODEL_SCORE_INTEGRATION_DESIGN_REVIEW_CN.md
```

verdict 只能是：

```text
PASS_GO_DNG17_DAILY_AUTO_PROVIDER_CANDIDATE_REFRESH_INTEGRATION
PASS_WITH_CONDITIONS_GO_DNG17
FAIL_NEEDS_DNG16_REPAIR
STOP_NEEDS_COORDINATOR_DECISION
```

通过条件：

- daily auto model_signal_gate 可识别/复用/生成 isolated Model A score；
- daily_chain_status 正确表达 formal provider stale + isolated score ready；
- forbidden actions 全部 false；
- 没有 production/latest/publish/交易/target 行为；
- 设计清楚下一步 DNG17：把 staged provider candidate refresh 从手动 R-A-R 纳入 daily auto，但仍不 publish formal provider。

## 9. 执行者命令

```text
请执行 DNG16 Daily Auto Model Score Integration Design。
读取本工作文档、DNG15_R-B 审查意见、DNG15_R-B validation JSON、run_daily_tw_stock_auto_update.py 当前实现。
实现 daily auto model_signal_gate 对 validated isolated Model A score artifact/candidate 的识别、复用或生成。
保持 publish/latest/production/交易/target 全部禁止。
完成后运行 py_compile 和 safe daily auto dry-run，写执行报告和 validation JSON。
```

## 10. 审查者命令

```text
请独立审查 DNG16 执行结果。
重点检查 daily auto 是否正确区分 formal provider stale 与 isolated score ready，是否没有 latest/publish/production/交易/target 行为，是否可以进入 DNG17。
```
