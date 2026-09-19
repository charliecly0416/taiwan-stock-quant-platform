---
title: New Strategy Onboarding Workflow
category: skills
tags: [strategy, onboarding, order-intent, replay]
aliases: [新策略接入流程]
relationships:
  - target: "[[concepts/modular-artifact-chain]]"
    type: implements
  - target: "[[concepts/readonly-safety-boundary]]"
    type: uses
  - target: "[[concepts/current-default-model-and-strategy]]"
    type: related_to
sources: [/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-new-strategy-onboarding/SKILL.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/templates/NEW_STRATEGY_WORK_TEMPLATE_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/templates/EXECUTION_REPORT_TEMPLATE_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/templates/REVIEW_REPORT_TEMPLATE_CN.md]
summary: 新策略必须先声明 StrategyDependency，输出 OrderIntentArtifact 和 readonly ReplayResultArtifact，不能产生真实订单或默认切换。
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

# New Strategy Onboarding Workflow

新策略通过 StrategyDependency、StrategyRule、OrderIntentArtifact 和 readonly ReplayResultArtifact 接入。策略只能使用标准 `ModelSignalArtifact` core fields 或声明的 extensions。

## Required Steps

1. 先定义 strategy goal 和 non-goals。
2. 写或审查 dependency YAML：required core fields、capabilities、extensions、ranking usage、max buy/sell、diagnostic-only status。
3. 验证策略输入只来自 `ModelSignalArtifact`、PortfolioState 和 StrategyRuleConfig。
4. 产出 `OrderIntentArtifact`，仅包含 buy/sell/hold/skip 意图和原因，不含成交、现金、NAV、broker id、target position 或 target weight。
5. Replay 只能通过 OrderIntent、PriceStore、ExecutionConfig 和 InitialPortfolioState 生成 historical readonly result。
6. validator/golden sample 必须检查 forbidden fields、future data、model private fields、diagnostic-only 边界。

## Template Evidence

新策略工作模板要求输出只能停在 `OrderIntentArtifact`，并在执行报告中保留 `contract_doc`、`schema_version`、`input_artifacts`、`output_artifacts`、`validator_command`、`golden_sample_path`、`allowed_consumers`、`forbidden_consumers`、`readonly_boundary`、`forbidden_actions_audit`、`rollback_or_failure_policy`、`diagnostic_only` 和 `production_allowed=false`。

策略补充字段必须覆盖 `strategy_rule`、`dependency_yaml`、`required_core_fields`、`required_extensions`、`max_buy_count`、`max_sell_count`、`OrderIntentArtifact_output`；若为 diagnostic-only，还必须写明 `not_valid_strategy_evidence`。该模板不授权训练、收益结论、默认策略切换、provider publish/refresh、accepted latest switch、monitor/broker/order 写入或前端 Agent 扩权。

## Current Rule Baseline

当前产品默认策略是 [[concepts/current-default-model-and-strategy|top50_exit_one_worst_sell]]。研究候选和 diagnostic rule 不能在同一任务中变成默认策略。

## Stop Conditions

- 请求真实订单、broker/quick-trade、target position/weight、provider publish、accepted latest switch、monitor write 或 frontend default change。
- 策略依赖 future data、future labels、realized PnL、replay returns as ranking input 或 model private fields。

## Sources

- `.agents/skills/tw-stock-new-strategy-onboarding/SKILL.md`
- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/templates/NEW_STRATEGY_WORK_TEMPLATE_CN.md`
