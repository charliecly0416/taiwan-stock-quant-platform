# DNG15 Formal Qlib Provider Or Canonical Bridge Repair 工作文档

生成日期：2026-06-29

## 1. 背景

DNG14 已通过，结论是：

```text
latest_raw_ready_asof=2026-06-29
latest_ready_chain_asof=2026-06-25
latest_provider_stale_asof=2026-06-29
recommended_next_route=formal_qlib_provider_refresh_route_or_validated_canonical_bridge_route
```

现在问题已经不再是“数据乱、不知道卡哪”，而是明确卡在：

```text
raw/ops 已有 2026-06-26 与 2026-06-29
formal qlib provider/calendar 仍只到 2026-06-25
Model A score pipeline 需要 qlib provider view
因此 6/26 之后无法生成标准 Model A score
```

## 2. 目标

DNG15 要选择并执行一条安全路线，让至少 `2026-06-26` 从：

```text
RAW_READY_BUT_QLIB_PROVIDER_STALE
```

推进到：

```text
ModelInferenceInput READY
ScoreJob SCORED_ASOF_TARGET
ModelSignalArtifact READY
StrategyInputBundle ready or explicitly blocked with concrete reason
readonly / Agent source context dry-run ready or explicitly blocked with concrete reason
```

如果无法完成，则必须把 blocker 从“provider stale”进一步具体化为：

```text
needs_network_provider_refresh
normalized_source_missing_asof
qlib_bin_dump_missing
model_pipeline_hardcoded_asof
canonical_bridge_validator_failed
score_job_runtime_failed
```

## 3. 非目标 / 禁止动作

不得执行：

- formal accepted latest switch；
- provider publish 到 production accepted latest；
- readonly latest publish；
- Agent prompt latest publish；
- production default model/strategy switch；
- broker/order/quick-trade；
- target position / target weight；
- 模型训练或调参；
- 用 raw FinMind 直接冒充 qlib provider feature input；
- 用 6/25 score 冒充 6/26 score。

如果 Route A 需要真实网络或外部 provider refresh，执行者必须停在 feasibility/blocker，除非用户另行明确授权。

## 4. 可选路线

### Route A：formal qlib provider refresh route

允许研究：

```text
qlib_pipeline/examples/tw/run_option_c_yahoo_scrapling_refresh.py
qlib_pipeline/examples/tw/publish_option_c_yahoo_scrapling_refresh.py
scripts/run_daily_tw_stock_auto_update.py 中 legacy provider gate
```

但本阶段不得：

```text
accepted latest switch
production publish
readonly latest publish
```

若只是 staged refresh / dry-run / local validation，可以继续；若会触发真实网络抓数或 formal publish，必须写 blocker。

### Route B：validated canonical bridge route

允许用本地已有 raw/normalized/canonical 数据建立隔离 bridge：

```text
data_tw/canonical/qlib_provider_view/{run_id}/
或
data_tw/canonical/model_inference_input/{model_id}/{run_id}/
```

要求：

- manifest / schema / coverage / lineage / validator 齐全；
- `not_published_latest=true`；
- `production_allowed=false`；
- `source_feature_artifact` 明确指向 bridge；
- 不得覆盖 formal qlib provider；
- 不得改 `latest_signal.json`。

如果 qlib Model A 只能接受正式 bin provider，执行者必须说明是否能用 qlib dump 工具从本地 normalized/canonical 生成隔离 provider view candidate。

## 5. 必须先检查的硬编码风险

执行者必须检查并修复或记录：

```text
scripts/tw_modela_score_common.py
scripts/build_tw_model_inference_input.py
scripts/run_tw_model_score_job.py
qlib_pipeline/examples/tw/run_option_c_daily_signal_option_c_provider.py
```

重点：

- 是否硬编码 `TARGET_ASOF=2026-06-25`；
- 是否硬编码 `PRICE_MARKET_READINESS=.../2026-06-25/...`；
- 是否硬编码 `PRICE_STORE_DIR=...20260625`；
- 是否只能读取 formal `option_c_150_qlib_bin`；
- 是否能参数化 provider view / readiness / price store；
- 是否会写 latest pointer。

DNG15 如果不处理这些硬编码，即使补了 6/26 数据，也可能仍被旧 6/25 合同误导。

## 6. 输出

执行者必须生成：

```text
data_tw/catalog/dng15_provider_or_bridge_repair_decision.json
data_tw/catalog/dng15_modela_20260626_readiness.json
docs/tw_data_governance/DNG15_FORMAL_QLIB_PROVIDER_OR_CANONICAL_BRIDGE_REPAIR_EXECUTION_REPORT_CN.md
```

若成功推进 6/26，还必须生成或更新：

```text
data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022/<dng15_run_id>/
data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022/<dng15_run_id>/
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/<dng15_run_id>/
data_tw/artifacts/strategy_input_bundles/...20260626.../
data_tw/artifacts/readonly_source_context/...20260626.../
data_tw/artifacts/agent_daily_prompt_source_context/...20260626.../
```

如果未成功推进，也必须输出 blocker artifacts，不得只写文字。

审查者必须生成：

```text
docs/tw_data_governance/DNG15_FORMAL_QLIB_PROVIDER_OR_CANONICAL_BRIDGE_REPAIR_REVIEW_CN.md
```

## 7. 验证要求

至少运行：

```bash
python -m py_compile scripts/tw_modela_score_common.py scripts/build_tw_model_inference_input.py scripts/run_tw_model_score_job.py scripts/run_daily_tw_stock_auto_update.py
```

如果新增脚本，也必须 py_compile。

若成功生成 6/26 score，必须运行：

```bash
python scripts/build_tw_dng14_multi_day_chain_observation.py --json
```

并证明：

```text
latest_ready_chain_asof >= 2026-06-26
```

如果仍 blocked，必须证明 `dng15_modela_20260626_readiness.json` 已把 blocker 具体化。

## 8. 执行报告要求

执行报告必须包含：

1. Route A / Route B 选择理由。
2. 硬编码风险检查结果。
3. 6/26 provider/calendar/normalized/bridge readiness。
4. 是否生成 ModelInferenceInput / ScoreJob / ModelSignalArtifact。
5. 是否生成 StrategyInputBundle / readonly / Agent source context dry-run。
6. DNG14 overlay 是否推进。
7. forbidden actions audit。
8. 下一步建议。

## 9. 审查 verdict

审查者只能给：

```text
PASS_GO_DNG16_DAILY_AUTO_MODEL_SCORE_INTEGRATION
PASS_WITH_CONDITIONS_GO_DNG16
FAIL_NEEDS_DNG15_REPAIR
STOP_NEEDS_COORDINATOR_DECISION
```

通过条件不是必须 production ready，而是必须让 6/26 ready chain 真实推进，或把不能推进的原因具体化到可执行 repair。
