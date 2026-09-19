---
title: New Model Onboarding Workflow
category: skills
tags: [model, onboarding, model-signal-artifact, registry]
aliases: [新模型接入流程]
relationships:
  - target: "[[concepts/modular-artifact-chain]]"
    type: implements
  - target: "[[concepts/readonly-safety-boundary]]"
    type: uses
  - target: "[[concepts/product-artifact-registry]]"
    type: related_to
sources: [/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-new-model-onboarding/SKILL.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/templates/NEW_MODEL_WORK_TEMPLATE_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/templates/EXECUTION_REPORT_TEMPLATE_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/templates/REVIEW_REPORT_TEMPLATE_CN.md, /home/chuliyang/taiwan-stock-quant-platform/configs/model_onboarding_templates/model_signal_m2_template.yaml]
summary: 新模型必须先通过 ModelSignalArtifact、registry、golden sample、validator 和 OOS evidence，不能直接进入默认产品链路。
provenance:
  extracted: 0.86
  inferred: 0.14
  ambiguous: 0.0
base_confidence: 0.86
lifecycle: draft
lifecycle_changed: 2026-06-20
tier: core
created: 2026-06-20T00:00:00Z
updated: 2026-06-20T13:00:00Z
---

# New Model Onboarding Workflow

新模型工作必须先停在 `ModelSignalArtifact` 和 registry 边界。它可以设计/审查 qlib、LTR、ensemble、horizon、risk 或 diagnostic 模型，但不能在同一任务中切换生产默认模型或前端默认。

## Required Steps

1. 读取项目 constitution、developer guide、ModelSignal contract、extension schema 和 reviewer checklist。
2. 定义模型家族、训练窗口、OOS 窗口、feature/source artifact、PIT policy 和 `available_at` policy。
3. 把 raw model output 通过 adapter 映射到 core fields：`candidate_rank`、`buy_score`、`raw_score`、`score_rank`、`full_qlib_rank`、`signal_asof`、`available_at`。
4. 如需扩展字段，必须使用声明完整的 `ext_*` schema，并在 allowed consumers 中约束使用者。
5. 新增或审查 registry entry，默认 `production_allowed=false`，并声明 validator、golden sample、capabilities、dependencies、allowed/forbidden consumers。
6. 补 pass/fail golden samples、validator 输出和 OOS evidence。
7. 报告中明确“未接入生产/default/frontend/Agent”。

## Template Evidence

新模型工作模板要求执行报告保留 `contract_doc`、`schema_version`、`input_artifacts`、`output_artifacts`、`validator_command`、`golden_sample_path`、`allowed_consumers`、`forbidden_consumers`、`readonly_boundary`、`forbidden_actions_audit`、`rollback_or_failure_policy`、`diagnostic_only` 和 `production_allowed=false`。

模型补充字段必须至少覆盖 `model_name`、`model_family`、`raw_score_path`、`model_adapter`、`source_feature_artifact`、`ModelSignalArtifact_output`，以及任何 strategy extension dependency。该模板不授权训练、收益结论、默认切换、provider publish/refresh、accepted latest switch、monitor/broker/order 写入或前端 Agent 扩权。

## Stop Conditions

- 请求 default-switch production model、frontend default、provider publish、accepted latest switch、monitor write、broker/order、target position 或 target weight。
- 模型依赖 future returns、future labels、realized PnL 或 same-day unavailable fields。
- 用户要求收益、胜率或上涨概率承诺而不是 validated OOS evidence。

## Sources

- `.agents/skills/tw-stock-new-model-onboarding/SKILL.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md`
- `configs/model_onboarding_templates/model_signal_m2_template.yaml`
- `docs/tw_modular_contracts/templates/NEW_MODEL_WORK_TEMPLATE_CN.md`
