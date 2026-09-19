---
title: Data Freshness And Latest Pointers
category: concepts
tags: [freshness, latest, qlib, provider, agent]
aliases: [数据新鲜度与 latest pointer, latest pointers]
relationships:
  - target: "[[concepts/readonly-safety-boundary]]"
    type: related_to
  - target: "[[concepts/daily-update-data-flow]]"
    type: related_to
  - target: "[[skills/data-freshness-diagnosis-workflow]]"
    type: related_to
sources: [/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/RUN_REGISTRY_CONTRACT_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/DAILY_ORCHESTRATOR_CONTRACT_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/AUTO_UPDATE_ORCHESTRATOR_CONTRACT_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/READONLY_STRATEGY_SNAPSHOT_CONTRACT_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md, /home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-data-freshness-diagnosis/references/data-source-boundary.md, /home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-data-freshness-diagnosis/references/freshness-status-fields.md]
summary: provider raw/latest、qlib accepted latest、readonly snapshot latest 和 Agent prompt latest 是四个不同概念，诊断只能只读比较。
provenance:
  extracted: 0.88
  inferred: 0.12
  ambiguous: 0.0
base_confidence: 0.87
lifecycle: draft
lifecycle_changed: 2026-06-20
tier: core
created: 2026-06-20T12:00:00Z
updated: 2026-06-20T16:00:00Z
---

# Data Freshness And Latest Pointers

台股链路至少有四种 latest 概念，不能合并解释：provider raw/latest、qlib accepted latest、readonly strategy snapshot latest、Agent DailyAgentPromptArtifact latest。

## Pointer Semantics

- provider raw/latest 描述 Yahoo/Scrapling、FinMind 等来源或标准化数据可得性。
- qlib accepted latest 描述被 qlib signal 服务接受的 validated run。
- readonly strategy snapshot latest 只指向 `ReadonlyStrategySnapshot`，影响今日策略总览、候选名单、历史模拟 linkage 和模拟账户 gate。
- Agent prompt latest 只指向 DailyAgentPromptArtifact，影响 simple-chat 上下文；它落后不等于 provider 或 qlib stale。

## Daily Orchestrator Policy

DailyOrchestrator 串接 FreshnessCheck、DataIngestion、FeatureArtifact、ModelSignalArtifact、StrategyDecision、ReadonlySnapshot、validators、RunRegistry 和 readonly latest pointer decision。`no_new_data` 不得刷新 latest pointer；validator failed 必须保留 previous latest。

## Diagnosis Boundary

Freshness 诊断只能读 GET endpoints、本地 manifest、latest pointer、job/pending files 和 artifact status。不得触发真实数据拉取、provider refresh/publish、accepted latest switch、prompt build/publish、monitor write、broker/order 或 target position/weight。

## W3 Code Evidence

- `backend/app/services/tw_stock_daily_auto_update_status.py` 是 freshness/status 只读服务；它读取 latest signal、pending asof、job 文件和 cron tail。
- `backend/app/services/readonly_strategy_snapshot.py` 读取 `data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json`，该 pointer 不是 provider 或 qlib accepted latest。
- `backend/app/services/tw_stock_agent_daily_prompt.py` 读取 Agent prompt latest；Agent latest lag 不等于 provider/qlib stale。
- `backend/app/routes/tw_stock.py` 中存在 accepted latest scheduler/normal publish endpoints，但 W3 将其记录为 ops/legacy boundary，不纳入当前 readonly route。

## Sources

- [[references/code-map-backend-readonly-routes|Backend Readonly Routes Code Map]]
- `docs/tw_modular_contracts/DAILY_ORCHESTRATOR_CONTRACT_CN.md`
- `docs/tw_modular_contracts/RUN_REGISTRY_CONTRACT_CN.md`
- `.agents/skills/tw-stock-data-freshness-diagnosis/references/freshness-status-fields.md`
