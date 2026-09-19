# POLICY_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD_EXECUTION_REPORT_CN

生成日期：2026-06-28

## 1. Verdict

```text
PASS_READY_FOR_MTRC1B_R_RESEARCH_ONLY_SIGNAL_REVIEW
```

MTRC1B 只基于 MTRC1A_R 审查通过的 `S2C_SPLIT_ALIGNED_FRESH_LTR` input contract 生成 research-only standard ModelSignalArtifact。已加载既有 S2C LTR 模型执行 inference；未训练、未调参、未根据收益筛选模型、未 broad bridge、未生成 OrderIntent/ReplayResult、未跑收益 replay，也未修改 production/default/frontend/API/Agent/daily/provider/latest。

## 2. 产物范围

输出目录：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1b_research_only_extended_top50_ltr_signal_build
```

核心产物：

```text
manifest.json
signals.csv
schema.json
coverage_audit.csv
forbidden_field_audit.csv
legacy_mapping_audit.csv
input_contract_audit.csv
lineage_boundary_audit.csv
available_at_policy_audit.csv
qlib_rank_alignment_audit.csv
validator_report.json
diagnostic_findings.md
```

`signals.csv` 行数为 `113000`，覆盖 `2017-01-10` 至 `2026-05-07`。

## 3. Lineage 声明

S2C is a new research lineage and is not equivalent to MTR2_R/E3.

本产物不得用于解除 MTR5 的 `clean_extended_lineage_found=false` blocker，不授权 broad bridge、production readiness、provider publish、accepted latest switch、frontend/API/Agent/daily/default 改动或任何 broker/order/target_weight/target_position/quantity 指令。

## 4. Validator

失败检查：

- 无

## 5. 验证命令

```bash
python -m py_compile scripts/build_tw_policy_mtrc1b_research_only_extended_top50_ltr_signal.py
python scripts/build_tw_policy_mtrc1b_research_only_extended_top50_ltr_signal.py
```
