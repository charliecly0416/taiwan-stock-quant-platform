---
title: Modular Artifact Chain
category: concepts
tags: [architecture, contracts, artifact-chain, readonly]
aliases: [台股模块化链路, artifact chain]
relationships:
  - target: "[[concepts/readonly-safety-boundary]]"
    type: uses
  - target: "[[concepts/product-artifact-registry]]"
    type: uses
  - target: "[[concepts/current-default-model-and-strategy]]"
    type: related_to
  - target: "[[skills/modular-integration-regression-workflow]]"
    type: related_to
sources: [/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/TW_MODULAR_PIPELINE_FUTURE_DEVELOPMENT_GUIDE_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/DATA_SOURCE_CONTRACT_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/DATA_INGESTION_ARTIFACT_CONTRACT_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/FEATURE_ARTIFACT_CONTRACT_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/PRICE_STORE_CONTRACT_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/FULL_RANK_CONTRACT_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/READONLY_STRATEGY_SNAPSHOT_CONTRACT_CN.md]
summary: 台股平台的核心链路要求每层只消费上游标准 artifact，禁止跨层读取私有文件或把只读候选升级成交易动作。
provenance:
  extracted: 0.88
  inferred: 0.12
  ambiguous: 0.0
base_confidence: 0.88
lifecycle: draft
lifecycle_changed: 2026-06-20
tier: core
created: 2026-06-20T00:00:00Z
updated: 2026-06-20T16:00:00Z
---

# Modular Artifact Chain

标准链路是：DataSource -> DataIngestionArtifact -> PriceStore / FeatureArtifact -> ModelAdapter -> ModelSignalArtifact / FullRankArtifact -> StrategyRule -> OrderIntentArtifact -> ReplayExecution -> ReplayResultArtifact -> ReadonlyStrategySnapshot -> Backend readonly API -> Frontend / Agent / PaperPortfolio。

## Layer Contract

- `DataSource` 只声明来源、asof、available_at、覆盖率和 schema 边界；它不执行 provider publish，也不切 accepted latest。
- `DataIngestionArtifact` 记录标准化落盘、schema audit、coverage audit 和 symbol mapping audit；它不直接喂给策略。
- `PriceStore` 是回放执行、特征计算和只读展示可引用的价格层；它不代表 provider latest。
- `FeatureArtifact` 必须保留 PIT 可见性，策略不得直接读取特征；策略如需新特征，必须先经 `ModelSignalArtifact` extension 和 strategy dependency 声明。
- `ModelSignalArtifact` 是模型输出进入策略的唯一标准信号接口；LTR 只能在 qlib top50 内通过 `buy_score` 重排，不得替换 `candidate_rank` 的 qlib top50 边界。
- `FullRankArtifact` 提供完整 qlib rank，供持仓跌出 top50 时判断 `full_qlib_rank` 最差持仓；它不得表示 LTR rank 或收益 rank。
- `StrategyRule` 只消费 `ModelSignalArtifact`、PortfolioState 和 StrategyRuleConfig，输出 `OrderIntentArtifact`。
- `OrderIntentArtifact` 只表达意图，不含成交价、现金、净值、broker order id 或目标仓位。
- `ReplayResultArtifact` 才处理 historical next-day execution、费用、现金、持仓和 NAV，但仍禁止真实 broker/order 或根据收益自动切默认。
- `ReadonlyStrategySnapshot` 固化通过 validator 的只读候选快照，供 API/前端展示；它不是交易指令、目标仓位或投资建议。

## Guardrails

- 每层必须有 manifest、schema/audit 或 validator 证据。
- 下游不能绕过标准 artifact 直接读实验 CSV、模型私有列、未来收益、label、realized PnL 或 broker/order 字段。
- `one_sell_one_buy_buggy_e8r` 只能作为 diagnostic-only 历史 bug 复现，不得进入默认策略、收益证据、产品展示或日更 publish。
- Product/default 选择必须来自 [[concepts/product-artifact-registry]]，不能由单个 replay 或分析报告自动推导。^[inferred]

## Related Workflows

- 新模型进入 [[skills/new-model-onboarding-workflow]]。
- 新策略进入 [[skills/new-strategy-onboarding-workflow]]。
- 端到端一致性进入 [[skills/modular-integration-regression-workflow]]。
- 安全审查进入 [[skills/safety-boundary-review-workflow]]。

## W3 Code Evidence

- `scripts/validate_tw_modular_artifact_contract.py` 校验 registry、ModelSignalArtifact、FullRankArtifact 和 ReplayResultArtifact，并显式扫描 forbidden fields。
- `scripts/run_tw_modular_contract_regression.py` 聚合 registry、signal、full-rank、replay、M2/M3/M4 和 forbidden scope audit；W3 不运行它。
- `backend/app/services/readonly_strategy_snapshot.py` 和 `backend/app/services/readonly_replay_window.py` 是 artifact 链路落到 backend GET API 的只读读取层。
- `frontend/tests/unit/tw-stock-readonly-*` 与 `frontend/tests/e2e/tw-stock-*-readonly.mjs` 是前端静态/网络审计证据，但 fixture payload 不得升级为生产 artifact。

## Sources

- [[references/code-map-scripts-and-tests|Scripts And Tests Code Map]]
- `docs/tw_modular_contracts/*_CONTRACT_CN.md`
- `configs/tw_modular_registry.yaml`
- `configs/tw_product_artifact_registry.yaml`
