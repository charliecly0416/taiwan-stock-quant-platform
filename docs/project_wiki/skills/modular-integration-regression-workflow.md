---
title: Modular Integration Regression Workflow
category: skills
tags: [integration, regression, artifact-chain, readonly]
aliases: [模块化只读集成回归]
relationships:
  - target: "[[concepts/modular-artifact-chain]]"
    type: implements
  - target: "[[concepts/readonly-safety-boundary]]"
    type: uses
sources: [/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-modular-integration-regression/SKILL.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md]
summary: 模块化集成回归只用 validators、fixtures、dry-runs、GET、static checks 和 readonly Playwright 验证 artifact-backed 链路。
provenance:
  extracted: 0.88
  inferred: 0.12
  ambiguous: 0.0
base_confidence: 0.84
lifecycle: draft
lifecycle_changed: 2026-06-20
tier: supporting
created: 2026-06-20T12:00:00Z
updated: 2026-06-20T16:00:00Z
---

# Modular Integration Regression Workflow

集成回归用于验证 DataSourceSnapshot、FeatureArtifact、ModelSignalArtifact、StrategyRule、OrderIntentArtifact、ReplayResult、ReadonlyStrategySnapshot、DailyAgentPromptArtifact、Backend API 和 Frontend Strategy Workbench 是否通过合同和 validator 串联。

## Evidence Chain

For each artifact, collect asof, run_id, checksum/latest pointer, manifest path, validator result and source links.

## Allowed Actions

validators、fixtures、dry-run、readonly GET、static checks、readonly Playwright、artifact manifest/latest pointer reads、network/console/screenshots。

## Stop Conditions

- 任一 required artifact、manifest、latest pointer、source link 或 validator result 缺失且无法只读验证。
- 请求需要 real data pull、provider publish/refresh、accepted latest switching、monitor writes、broker/order/quick-trade、OpenAI calls 或 production default changes。
- 只有 dynamic service payload，没有 artifact backing。

## W2 Product Route Evidence

Pre-RND readiness confirms full modular contract regression passed after repair and that future model/strategy work must stop at explicit artifact contracts. W2 daily update route confirms U1/U2/U3 readonly chain: daily data/features/model signal -> order intent -> readonly snapshot -> run registry/latest pointer -> GET-only API/frontend.

## W3 Script/Test Evidence Map

- `scripts/validate_tw_modular_artifact_contract.py` is the core readonly contract validator for registry/model/full-rank/replay artifacts.
- `scripts/run_tw_modular_contract_regression.py` aggregates contract checks and M2/M3/M4 audits, including forbidden scope checks; W3 did not execute it.
- `tests/unit/test_tw_modular_m_contract_validators.py`, `test_validate_tw_modular_artifact_contract.py`, `test_tw_modular_m2_registry_validator.py`, `test_tw_modular_m3_daily_orchestrator.py` map contract, registry and daily orchestrator gates.
- Replay/order-intent unit tests remain readonly/parity evidence, not broker/order evidence.

## Sources

- [[references/code-map-scripts-and-tests|Scripts And Tests Code Map]]
- `.agents/skills/tw-stock-modular-integration-regression/SKILL.md`
- `docs/tw_modular_contracts/*_CONTRACT_CN.md`
