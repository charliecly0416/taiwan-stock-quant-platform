# DNG15 Formal Qlib Provider Or Canonical Bridge Repair 审查意见

生成时间：2026-06-29

## 1. Verdict

```text
STOP_NEEDS_COORDINATOR_DECISION
```

DNG15 执行没有通过到 DNG16。原因不是执行者漏做，而是当前本地数据条件不足以安全推进 `2026-06-26` Model A score：

```text
FinMind raw daily price 已有 2026-06-26
但 frozen qlib Model A 所需的同口径 Option C normalized / formal qlib provider 仍只到 2026-06-25
```

执行者已把 blocker 从 DNG14 的泛泛 `formal qlib provider/calendar stale` 具体化为：

```text
normalized_source_missing_asof_and_formal_refresh_requires_network
```

这满足 DNG15 “若无法推进，必须具体化 blocker”的最低要求，但不满足进入 DNG16 的条件，因为 `latest_ready_chain_asof` 没有推进到 `2026-06-26`。

## 2. Findings

### Critical

无越权行为。未发现 publish latest、accepted latest switch、交易、target_position/target_weight 或模型训练。

### High

1. 不能进入 DNG16 daily auto model score integration。
   - 证据：DNG14 rerun 仍显示 `latest_ready_chain_asof=2026-06-25`。
   - 证据：`data_tw/catalog/dng15_modela_20260626_readiness.json` 显示 `status=BLOCKED_INPUT_NOT_READY`、`score_status=NOT_SCORED`。
   - 影响：daily auto 还不能在每日抓数后自动生成标准 6/26+ Model A score。

2. 不能用 FinMind raw 替代 Option C qlib provider 输入。
   - 证据：FinMind raw 已覆盖 `2026-06-26`，但 formal `option_c_150_normalized` 的 `symbols_with_asof=0/150`。
   - 影响：若直接用 FinMind raw dump qlib bin，会改变训练/推理输入口径，违反 DNG15 禁止事项。

### Medium

1. 现有 Model A pipeline 仍有 6/25 硬编码风险。
   - `scripts/tw_modela_score_common.py` 固定 `TARGET_ASOF = "2026-06-25"`。
   - readiness 和 PriceStore 也固定指向 `2026-06-25`。
   - 该问题本轮没有修复，但在当前 6/26 normalized 缺失的情况下，即使参数化也不能生成合法 score。

2. Route B 技术上有 dump 工具，但缺合法输入。
   - 证据：`qlib_pipeline/scripts/dump_bin.py` 存在。
   - blocker：同口径 normalized 没有 6/26，formal calendar stale。

### Low

1. `dng15_probe_modela_20260626` 是 blocked artifact，不是 ready artifact。报告已明确说明，不构成误导。

## 3. Mainline Compliance

通过项：

- 已读取主线、DNG15 工作文档、DNG14 执行报告和审查意见。
- 已检查指定脚本硬编码：
  - `scripts/tw_modela_score_common.py`
  - `scripts/build_tw_model_inference_input.py`
  - `scripts/run_tw_model_score_job.py`
  - `qlib_pipeline/examples/tw/run_option_c_daily_signal_option_c_provider.py`
- 已生成 required artifacts：
  - `data_tw/catalog/dng15_provider_or_bridge_repair_decision.json`
  - `data_tw/catalog/dng15_modela_20260626_readiness.json`
  - `docs/tw_data_governance/DNG15_FORMAL_QLIB_PROVIDER_OR_CANONICAL_BRIDGE_REPAIR_EXECUTION_REPORT_CN.md`
- 已用现有 builder 生成 blocked probe，证明 6/26 被当前合同拒绝。
- 已运行 fixed Option C provider dry-run，证明 formal validation 拒绝 6/26。
- 没有用 6/25 score 冒充 6/26 score。

未通过项：

- 未生成 6/26 READY ModelInferenceInput。
- 未生成 6/26 ScoreJob / ModelSignalArtifact。
- 未生成 6/26 StrategyInputBundle / readonly source context / Agent source context。
- DNG14 overlay 未推进到 `latest_ready_chain_asof >= 2026-06-26`。

这些未通过项由真实数据 blocker 导致，不是实现偏离。

## 4. Evidence Checked

执行报告：

```text
docs/tw_data_governance/DNG15_FORMAL_QLIB_PROVIDER_OR_CANONICAL_BRIDGE_REPAIR_EXECUTION_REPORT_CN.md
```

主要 artifacts：

```text
data_tw/catalog/dng15_provider_or_bridge_repair_decision.json
data_tw/catalog/dng15_modela_20260626_readiness.json
data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022/dng15_probe_modela_20260626/manifest.json
qlib_pipeline/data_tw/experiments/option_c_daily_signal_option_c_provider/option_c_provider_dry_run_20260626_20260629T125548Z/run_metadata.json
```

审查断言：

```bash
python - <<'PY'
import json
from pathlib import Path
D=json.loads(Path('data_tw/catalog/dng15_provider_or_bridge_repair_decision.json').read_text())
R=json.loads(Path('data_tw/catalog/dng15_modela_20260626_readiness.json').read_text())
assert D['decision']=='NO_SCORE_GENERATED_BLOCKER_CONCRETIZED'
assert D['selected_route']=='B_VALIDATED_CANONICAL_BRIDGE'
assert D['production_go'] is False
assert D['publish_latest_authorized'] is False
assert all(v is False for v in D['forbidden_actions'].values())
assert R['status']=='BLOCKED_INPUT_NOT_READY'
assert R['score_status']=='NOT_SCORED'
assert R['formal_provider']['calendar_max']=='2026-06-25'
assert R['formal_option_c_normalized']['symbols_with_asof']==0
assert R['formal_option_c_normalized']['missing_asof_count']==150
assert R['raw_daily_price_evidence']['status']=='READY_FROM_PRIOR_JOB'
assert all(v is False for v in R['forbidden_actions'].values())
print('DNG15 reviewer artifact assertions PASS')
PY
```

结果：

```text
DNG15 reviewer artifact assertions PASS
```

验证命令：

```bash
python -m py_compile scripts/tw_modela_score_common.py scripts/build_tw_model_inference_input.py scripts/run_tw_model_score_job.py scripts/run_daily_tw_stock_auto_update.py scripts/build_tw_dng15_provider_or_bridge_repair.py
python scripts/build_tw_dng15_provider_or_bridge_repair.py --json
python scripts/build_tw_dng14_multi_day_chain_observation.py --json
```

结果均通过。

按预期失败的证据命令：

```bash
python scripts/build_tw_model_inference_input.py --asof 2026-06-26 --run-id dng15_probe_modela_20260626 --json
```

结果：

```text
status=BLOCKED_INPUT_NOT_READY
errors=price_market_readiness_asof_mismatch, qlib_provider_calendar_stale, normalized_source_missing_asof
```

```bash
python qlib_pipeline/examples/tw/run_option_c_daily_signal_option_c_provider.py --asof 2026-06-26 --dry-run
```

结果：

```text
status=blocked_formal_validation_failed
errors=option_c_formal_source_missing_asof, option_c_provider_calendar_stale
```

## 5. Missing Evidence Or Open Questions

当前缺少可以直接进入 DNG16 的关键证据：

1. 同口径 Option C Yahoo/Scrapling normalized 覆盖 `2026-06-26` 的 150 支标的。
2. 基于同口径 normalized 生成的 isolated qlib provider view candidate。
3. 基于 candidate provider 的 6/26 Model A score。
4. 或者，统筹明确授权 mixed-provider FinMind bridge，并接受额外 drift validator。

需要统筹决策的问题：

```text
是否授权下一步先做同口径 Option C normalized refresh / isolated provider candidate build？
还是允许 research-only mixed-provider FinMind bridge，并新增口径漂移验证？
```

## 6. Forbidden Actions Audit

通过。

未发现：

```text
real_data_fetch_triggered=true
provider_refresh_triggered=true
provider_publish_triggered=true
qlib_accepted_latest_switched=true
readonly_latest_published=true
agent_prompt_published=true
production_default_model_or_strategy_switched=true
model_training_triggered=true
model_tuning_triggered=true
strategy_replay_triggered=true
broker_order_quick_trade_triggered=true
target_position_or_weight_generated=true
```

## 7. Next Work Document

### DNG15_R Same-Lineage Option C Normalized Refresh Or Isolated Provider View Build

建议下一步不是 DNG16，而是 DNG15 repair。

目标：

```text
在不切 accepted latest、不 publish production、不交易的前提下，
让 2026-06-26 至少获得同口径 Option C normalized source，
并尝试生成 isolated qlib provider view candidate。
```

执行者必须先判断两条路径：

1. `Route R-A: same-lineage Yahoo/Scrapling Option C normalized refresh`
   - 允许：本地 staged refresh / candidate_normalized 生成 / isolated provider view candidate。
   - 不允许：formal accepted latest switch、production publish、readonly/Agent latest publish、交易。
   - 若需要真实网络，必须先取得用户授权。

2. `Route R-B: explicit mixed-provider FinMind bridge research-only`
   - 只有在统筹明确授权时才允许。
   - 必须新增 drift validator：
     - 6/25 Yahoo/Scrapling vs FinMind OHLCV/factor/vwap 差异；
     - Alpha158 feature drift；
     - 6/25 same-asof score rank overlap；
     - top30/top50 overlap；
     - `production_allowed=false`、`not_published_latest=true`。

最低验收：

```text
data_tw/canonical/qlib_provider_view/<dng15_r_run_id>/
manifest.json
lineage.json
coverage_audit.csv
validator_report.json
not_published_latest=true
production_allowed=false
```

如果 provider view candidate 通过，再运行：

```text
ModelInferenceInput -> ScoreJob -> ModelSignalArtifact -> StrategyInputBundle -> readonly/Agent source context dry-run
```

并重跑：

```bash
python scripts/build_tw_dng14_multi_day_chain_observation.py --json
```

目标才是：

```text
latest_ready_chain_asof >= 2026-06-26
```

## 8. Command For Executor Or Coordinator

建议交给统筹决策：

```text
不要进入 DNG16。
请决定是否授权 DNG15_R 的同口径 refresh / isolated provider candidate build。
如果不能授权网络 refresh，则只能继续保持 6/26 blocked；
如果要尝试 FinMind mixed-provider bridge，必须明确标成 research-only 且先做 drift validator。
```
