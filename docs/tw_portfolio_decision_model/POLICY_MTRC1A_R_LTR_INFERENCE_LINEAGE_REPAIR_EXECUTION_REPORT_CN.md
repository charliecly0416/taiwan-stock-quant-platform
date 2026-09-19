
# POLICY_MTRC1A_R_LTR_INFERENCE_LINEAGE_REPAIR_EXECUTION_REPORT_CN

生成日期：2026-06-28

## 1. Verdict

```text
PASS_READY_FOR_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD
```

MTRC1A_R 选择且只选择 `S2C split-aligned fresh lineage`。本次只修复 extended top50 LTR 的 PIT-clean inference input contract；未训练、未推理、未生成 score、未生成 ModelSignalArtifact、未生成 broad bridge、未生成 OrderIntent/ReplayResult、未跑 replay，也未触碰 production/default/frontend/API/Agent/daily/provider/latest。

## 2. 关键结论

- E3/MTR2_R-compatible lineage 未选择：E3 缺 exact 78-feature order 和 PIT-clean feature-only input。
- S2C lineage 被选择：模型 manifest 声明完整 34-feature schema，样本表覆盖 `2017-01-10..2026-05-07`，`date,instrument` duplicate 为 `0`。
- 已定义 feature-only inference input contract：`date`、`instrument`、`signal_asof`、`available_at`、34 个 S2C features。
- 已剔除 future/label/audit/training eligibility 字段；`Bollinger_position` 是技术指标，不按交易持仓字段禁用。
- qlib rank alignment：检查 `169366` 行，missing key `0`，rank mismatch `0`，score mismatch `0`。

## 3. 产物

输出目录：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_r_ltr_inference_lineage_repair
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC1A_R_LTR_INFERENCE_LINEAGE_REPAIR_EXECUTION_REPORT_CN.md
```

核心产物包括 `manifest.json`、`lineage_selection_decision.csv`、`feature_schema_contract.json`、`inference_input_contract.json`、`pit_available_at_audit.csv`、`qlib_rank_alignment_contract.csv`、`mtrc1b_readiness_gate.csv`、`validator_report.json`。

## 4. 后续 MTRC1B 边界

MTRC1B 只能在 research-only 边界内，基于本次 S2C contract 生成标准 extended top50 LTR signal。不得把 S2C 静默替代为 MTR2_R/E3 lineage，也不得把本次合同用于生产化、provider/latest/default 切换或交易动作。

## 5. 验证命令

```bash
python -m py_compile scripts/build_tw_policy_mtrc1a_r_ltr_inference_lineage_repair.py
python scripts/build_tw_policy_mtrc1a_r_ltr_inference_lineage_repair.py
```
