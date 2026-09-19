
# POLICY_MTRC0_CLEAN_EXTENDED_LINEAGE_CONTRACT_AND_FEASIBILITY_EXECUTION_REPORT_CN

生成日期：2026-06-28

## 1. Verdict

```text
STOP_NO_CLEAN_LINEAGE_PATH
```

原因：未发现可直接进入 MTRC1 的 clean extended lineage。MTR2_R broad signal 只覆盖 `2026-01-02` 至 `2026-05-07`；标准 top50 LTR artifact 也只覆盖同一短窗口，无法证明 extended window 的 top50 LTR equivalence / PIT / non-top50 hold-sell-only 语义。

## 2. Scope

- readonly_only: `true`
- simulation_only: `true`
- production_allowed: `false`
- replay_performed: `false`
- order_intent_generated: `false`
- replay_result_generated: `false`
- model_training_performed: `false`
- strategy_tuning_performed: `false`
- new_candidate_added: `false`
- fixed_candidate: `M2_hold_rank_buffer_100`
- baseline: `baseline_top50_exit_one_worst_sell`

## 3. Findings

- clean lineage contract 已固化 11 条 hard requirements。
- source inventory 扫描 manifest 数：`224`。
- MTR2_R broad full-rank artifact 可作为 same-window 语义模板，但不是 extended evidence。
- qlib full-rank source 可作为部分输入；extended standard top50 LTR signal 缺失。
- existing extended_oos / shadow / replay artifacts 不等价，不能解除 MTR5 `clean_extended_lineage_found=false` blocker。

## 4. Generated Artifacts

- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc0_clean_extended_lineage_contract/manifest.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc0_clean_extended_lineage_contract/clean_lineage_definition_contract.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc0_clean_extended_lineage_contract/source_artifact_inventory.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc0_clean_extended_lineage_contract/candidate_bridge_feasibility_matrix.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc0_clean_extended_lineage_contract/required_inputs_for_mtrc1.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc0_clean_extended_lineage_contract/non_equivalence_reason_catalog.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc0_clean_extended_lineage_contract/production_boundary_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc0_clean_extended_lineage_contract/forbidden_scope_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc0_clean_extended_lineage_contract/validator_report.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc0_clean_extended_lineage_contract/diagnostic_findings.md`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc0_clean_extended_lineage_contract/mtrc1_work_recommendation.md`

## 5. Safety Boundary

本次 MTRC0 未跑收益 replay，未生成 OrderIntent/ReplayResult，未训练、未调参、未新增候选、未修改 M2 参数，未修改 MTR2_R/MTR3/MTR4/MTR5 输入 artifacts。未修改 production/default/frontend/API/Agent/daily/provider/latest，未 provider publish，未 accepted latest switch，未 broker/quick-trade/real order，未输出 target_weight/target_position/quantity instruction。

## 6. Verification Commands

```bash
python -m py_compile scripts/build_tw_policy_mtrc0_clean_extended_lineage_contract.py
python scripts/build_tw_policy_mtrc0_clean_extended_lineage_contract.py
```
