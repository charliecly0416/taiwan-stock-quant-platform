# DNG15_R-B Isolated Model A Score Integration 执行报告

生成时间：2026-08-10T10:38:04+00:00

## 1. Scope

- Assigned phase：`DNG15_R-B isolated Model A score integration`
- Mainline document：`docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md`
- Work document：`docs/tw_data_governance/DNG15_R_B_ISOLATED_MODELA_SCORE_INTEGRATION_WORK_CN.md`
- Target asof：`2026-08-10`
- run_id：`dng9_daily_auto_modela_20260810_20260810T103001Z`
- Model：`e4_frozen_qlib_2018_2022`

非目标确认：未 formal publish、未覆盖 formal provider/normalized、未切 accepted latest、未更新 latest_signal、未 publish readonly/Agent latest、未生产切换、未策略回放/NAV、未交易、未生成 target_position/target_weight、未 FinMind fallback、未 mixed-provider bridge、未训练或调参。

## 2. Documents / Contracts / Skills Read

- `docs/tw_data_governance/DNG15_R_B_ISOLATED_MODELA_SCORE_INTEGRATION_WORK_CN.md`
- `docs/tw_data_governance/DNG15_R_A_R_YAHOO_ACCESS_REPAIR_EXECUTION_REPORT_CN.md`
- `docs/tw_data_governance/DNG15_R_A_R_YAHOO_ACCESS_REPAIR_REVIEW_CN.md`
- `data_tw/catalog/dng15_r_a_r_yahoo_access_repair_decision.json`
- `data_tw/catalog/dng15_r_a_r_modela_20260626_candidate_readiness.json`
- `docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md`
- `/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md`
- `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`
- `docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md`
- `docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md`

## 3. Changes Made

- 新增 `scripts/build_tw_dng15_r_b_isolated_modela_score_integration.py`。
- 生成 isolated `ModelInferenceInput`、`ScoreJob`、`ModelSignalArtifact`。
- 生成 `data_tw/catalog/dng15_r_b_isolated_modela_score_integration_validation.json`。
- 生成本执行报告。

## 4. Evidence Produced

- staged_provider：`qlib_pipeline/data_tw/experiments/daily_auto_provider_candidates/daily_auto_provider_candidate_20260810_20260810T103150Z/staged_qlib_bin`
- candidate_normalized：`qlib_pipeline/data_tw/experiments/daily_auto_provider_candidates/daily_auto_provider_candidate_20260810_20260810T103150Z/candidate_normalized`
- source_model_artifact：`qlib_pipeline/mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a/artifacts/params.pkl`
- ModelInferenceInput validator：`PASS`
- ScoreJob validator：`PASS`
- ModelSignalArtifact validator：`PASS`
- raw_scores rows：`150`
- signals rows：`150`
- prediction_rows：`150`
- finite_prediction_share：`1.0`
- score_status：`SCORED_ASOF_TARGET`
- signal_asof：`2026-08-10`
- available_at：`2026-08-10`

## 5. Compliance With Mainline

- 显式 `provider_uri` 指向 R-A-R `staged_qlib_bin`。
- 使用 `qlib.init(provider_uri=<staged_qlib_bin>, region='tw', expression_cache=None, dataset_cache=None)`。
- 使用 `DatasetH` + `Alpha158` snapshot segment `(2026-08-10, 2026-08-10)`。
- 只加载 frozen Model A `params.pkl` 执行 predict；未 fit、未训练、未调参。
- `ModelSignalArtifact` 仅包含合同 core fields，无 forbidden fields。

## 6. Forbidden Actions Audit

- `formal_publish=false`
- `formal_provider_mutated=false`
- `formal_normalized_mutated=false`
- `accepted_latest_switch=false`
- `latest_signal_updated=false`
- `readonly_latest_published=false`
- `agent_prompt_latest_published=false`
- `production_default_model_or_strategy_switched=false`
- `strategy_replay_or_nav_triggered=false`
- `broker_order_quick_trade_triggered=false`
- `target_position_or_weight_generated=false`
- `finmind_fallback=false`
- `mixed_provider_bridge=false`
- `model_training_or_tuning=false`

## 7. Issues / Blockers / Deviations

- 无阻断性 blocker。
- 复用现有 `validate_tw_model_inference_input.py` 与 `validate_tw_score_job.py`；R-B artifact 写入兼容 DNG7 validator 的 manifest/source_readiness 字段，同时在 catalog 中额外保留 R-B governance forbidden flags。
- 本阶段未生成 StrategyInputBundle、readonly source context、Agent prompt 或 NAV，因为工作文档禁止策略回放/NAV和 latest publish。

## 8. Files Changed

- `scripts/build_tw_dng15_r_b_isolated_modela_score_integration.py`
- `docs/tw_data_governance/DNG15_R_B_ISOLATED_MODELA_SCORE_INTEGRATION_EXECUTION_REPORT_CN.md`
- `data_tw/catalog/dng15_r_b_isolated_modela_score_integration_validation.json`
- `data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022/dng9_daily_auto_modela_20260810_20260810T103001Z/`
- `data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022/dng9_daily_auto_modela_20260810_20260810T103001Z/`
- `data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng9_daily_auto_modela_20260810_20260810T103001Z/`

## 9. Recommendation For Reviewer

建议 verdict：`PASS_GO_DNG16_DAILY_AUTO_MODEL_SCORE_INTEGRATION_DESIGN`。

理由：R-B 已在 isolated staged provider 上生成 2026-08-10 标准 ModelInferenceInput / ScoreJob / ModelSignalArtifact，三层 validator 均 PASS，且 forbidden actions 全部保持 false。DNG16 应只进入 daily auto model score integration 设计，不应视为 formal publish 或 production latest 授权。
