# Phase R3 可扩展 Contract 设计审查说明

生成日期：2026-06-16

## 1. 审查范围

本 handoff 供审查者复核 R3。R3 只做设计文档和只读 validator skeleton，不改 replay 结果、不接入前端/日更/生产链路。

## 2. 新增文件

```text
docs/tw_modular_contracts/EXTENSIBLE_CONTRACT_CAPABILITY_DESIGN_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
docs/tw_modular_contracts/STRATEGY_DEPENDENCY_CONTRACT_CN.md
scripts/validate_tw_modular_artifact_contract.py
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER3_EXTENSIBLE_CONTRACT_DESIGN_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER3_EXTENSIBLE_CONTRACT_DESIGN_REVIEW_HANDOFF_CN.md
```

## 3. 审查重点

请重点确认：

- immutable core fields 是否完整且未弱化 R0 contract；
- optional extension fields 是否必须显式声明 schema；
- capabilities 是否只表达能力，不表达收益结论；
- strategy dependency 是否能阻止策略直接读取 legacy 私有列；
- validator skeleton 是否只读；
- forbidden fields/actions 是否继续全局强制；
- horizon / risk / sector / ensemble score 是否都有受控接入规则；
- R3 是否未修改 R2 replay 输出、旧 formal replay matrix、前端、日更。

## 4. 建议复核命令

```bash
python -m py_compile scripts/validate_tw_modular_artifact_contract.py
python scripts/validate_tw_modular_artifact_contract.py \
  --artifact data_tw/artifacts/signals/fresh_qlib_adaptive/r1_legacy_signal_adapter_20260616/manifest.json \
  --json
git diff -- data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix scripts/run_tw_modular_config_replay_matrix.py scripts/run_extended_oos_formal_replay_matrix.py frontend/src/views/tw-stock-monitor/index.vue scripts/run_daily_tw_stock_auto_update.py
```

预期：

- validator skeleton 可编译；
- 对 R1 artifact 的 core validation `ok=true`；
- R2 replay 输出和旧 formal replay matrix 不出现 R3 diff；
- 前端和日更脚本不出现 R3 diff。

## 5. R3 不应被解读为

R3 不是：

- 新策略上线；
- 默认策略切换；
- 新收益结论；
- replay 结果修改；
- 前端展示接入；
- 日更 orchestrator 接入；
- broker / order / quick-trade 接入。

## 6. 放行后建议

若 R3 通过，下一阶段建议先做：

- registry yaml 草案；
- validator 完整测试；
- R1/R2 manifest capability metadata backfill；
- replay actions 增加 `window` 字段的兼容改造评估。
