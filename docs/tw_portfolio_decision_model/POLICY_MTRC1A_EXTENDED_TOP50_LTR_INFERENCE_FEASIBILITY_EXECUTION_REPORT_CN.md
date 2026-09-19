
# POLICY_MTRC1A_EXTENDED_TOP50_LTR_INFERENCE_FEASIBILITY_EXECUTION_REPORT_CN

生成日期：2026-06-28

## 1. Verdict

```text
STOP_NEEDS_LTR_INFERENCE_LINEAGE_REPAIR
```

结论：E3 与 S2C 均有既有 LTR 模型文件，静态审计未发现必须重训模型才能继续做可行性修复；但两条 lineage 当前都还不能直接进入 MTRC1B 标准 extended top50 LTR ModelSignal build。阻断点是 PIT/`available_at`、feature-only inference input、qlib full-rank alignment 与标准 ModelSignal mapping 仍需 lineage repair。

## 2. Scope

- 只审计 E3 与 S2C 两条 LTR lineage。
- 未训练模型。
- 未执行模型 inference 或生成新 score。
- 未生成 ModelSignalArtifact。
- 未生成 broad bridge、OrderIntent、ReplayResult。
- 未跑 replay、未调参、未新增策略候选、未修改 M2 参数。
- 未修改 production/default/frontend/API/Agent/daily/provider/latest。

## 3. Findings

- E3：`phasee3_ltr_model.pkl` 存在；manifest 声明 `feature_count=78` 与 feature hash，但缺完整 78-feature list；可见 CSV 是 score/label 行，不是 feature-only inference input。
- S2C：`phase_s2c_ltr_model.pkl` 存在；manifest/schema 声明完整 34-feature list；但 sample/score 表含 future/label/audit 列且缺 `available_at`，需要先生成 PIT-clean inference input。
- qlib full-rank alignment：E3 有 2023-01-03..2026-05-07 qlib rank source；S2C 使用 split-aligned fresh qlib rank source，尚未证明与 MTRC/MTR2_R qlib full-rank source等价。
- ModelSignal mapping 可设计，但不能在 MTRC1A 生成 signal。

## 4. Generated Artifacts

- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_extended_top50_ltr_inference_feasibility/manifest.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_extended_top50_ltr_inference_feasibility/ltr_lineage_inventory.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_extended_top50_ltr_inference_feasibility/model_file_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_extended_top50_ltr_inference_feasibility/feature_availability_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_extended_top50_ltr_inference_feasibility/inference_input_coverage_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_extended_top50_ltr_inference_feasibility/pit_available_at_feasibility_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_extended_top50_ltr_inference_feasibility/top50_alignment_feasibility.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_extended_top50_ltr_inference_feasibility/model_signal_mapping_plan.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_extended_top50_ltr_inference_feasibility/forbidden_scope_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_extended_top50_ltr_inference_feasibility/production_boundary_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_extended_top50_ltr_inference_feasibility/validator_report.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_extended_top50_ltr_inference_feasibility/diagnostic_findings.md`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_extended_top50_ltr_inference_feasibility/mtrc1b_work_recommendation.md`

## 5. Verification Commands

```bash
python -c "import ast, pathlib; ast.parse(pathlib.Path('scripts/build_tw_policy_mtrc1a_extended_top50_ltr_inference_feasibility.py').read_text(encoding='utf-8'))"
python scripts/build_tw_policy_mtrc1a_extended_top50_ltr_inference_feasibility.py
```
