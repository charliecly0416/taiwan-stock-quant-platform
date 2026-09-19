---
created_at: 2026-06-25T05:28:32+00:00
status: execution_report
phase: RCPT9B_LINEAGE_BUILD
validator_status: PASS_READY_FOR_RCPT9C_PREDECLARED_LONGER_OOS_REPLAY
production_allowed: false
order_or_target_output_allowed: false
model_training_performed: false
replay_performed: false
---

# RCPT9B Lineage Build 执行报告

## 1. 执行范围

本轮只执行 RCPT9B lineage build/package。未执行 RCPT9C replay，未做 threshold tuning，未做新 mapping，未改 production/default/provider/frontend/Agent/monitor/order，未输出 OrderIntent、target_weight、target_position、quantity_instruction、broker 或 quick-trade 相关内容。

## 2. 已读取输入

- `docs/tw_portfolio_decision_model/POLICY_RCPT9B_LINEAGE_BUILD_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT9_LONGER_STRICT_OOS_RETRAIN_HOLDOUT_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT9A_SPLIT_LINEAGE_FEASIBILITY_CONTRACT_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/risk_control_policy_2022/rcpt9a_split_lineage_feasibility_contract/`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2a_fresh_retrain_contract/`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/`

## 3. Reuse 结论

```text
REUSE_EXISTING_S2B_S2C_LINEAGE_AND_PACKAGE_FOR_RCPT9B
```

原因：

1. RCPT9A 已通过并主推荐 B3/S2A fresh retrain-holdout split。
2. S2B qlib 与 S2C LTR 的关键产物都已存在，无需新训练。
3. 关键约束已被现有 audit 覆盖：split 固定、no test feedback、no parameter search、no replay。

## 4. 关键证据

- qlib model: `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/run/s2b_model.pkl` sha256=`059b2755cf5099d96d16d1a291a913e7130c7992e2265f6ba576a99e66ca2f10`
- ltr model: `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_ltr_model.pkl` sha256=`a4d191f28d97709934e4fd8658e4cc30e2672268e588c1f7736f393a9a0d13b8`
- holdout frozen: `2025-07-01..2026-05-07`
- holdout coverage: `205` trading days in S2B and `205` trading days in S2C
- allowed mappings: `M1_QLIB_SCORE_COMPONENT_PRIMARY`, `M2_LTR_SCORE_COMPONENT_SECONDARY`
- rejected mapping retained: `M3_BLEND_Q70_L30_TERTIARY`

## 5. 输出文件

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt9b_lineage_build/
```

已生成：

- `manifest.json`
- `lineage_artifact_inventory.csv`
- `split_purity_audit.csv`
- `score_schema_audit.csv`
- `feature_label_coverage_audit.csv`
- `holdout_readiness_audit.csv`
- `mapping_input_contract.csv`
- `lineage_reuse_or_build_decision.md`
- `forbidden_action_audit.csv`
- `validator_report.json`
- `diagnostic_findings.md`

## 6. Verdict

```text
PASS_READY_FOR_RCPT9C_PREDECLARED_LONGER_OOS_REPLAY
```

RCPT9B 结论仅表示 lineage package 和进入 RCPT9C 的前置证据已整理完成，不代表 production 授权。
