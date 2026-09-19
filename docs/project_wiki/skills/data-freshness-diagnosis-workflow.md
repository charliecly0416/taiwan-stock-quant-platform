---
title: Data Freshness Diagnosis Workflow
category: skills
tags: [freshness, latest, diagnosis, readonly]
aliases: [数据新鲜度诊断流程]
relationships:
  - target: "[[concepts/data-freshness-and-latest-pointers]]"
    type: implements
  - target: "[[concepts/readonly-safety-boundary]]"
    type: uses
sources: [/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-data-freshness-diagnosis/SKILL.md, /home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-data-freshness-diagnosis/references/data-source-boundary.md, /home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-data-freshness-diagnosis/references/freshness-status-fields.md]
summary: 数据新鲜度诊断只读比较 provider、qlib、snapshot 和 Agent prompt latest，不触发数据拉取或 latest 切换。
provenance:
  extracted: 0.9
  inferred: 0.1
  ambiguous: 0.0
base_confidence: 0.84
lifecycle: draft
lifecycle_changed: 2026-06-20
tier: supporting
created: 2026-06-20T12:00:00Z
updated: 2026-06-20T16:00:00Z
---

# Data Freshness Diagnosis Workflow

Freshness diagnosis 用来解释 provider raw/latest、qlib accepted latest、readonly strategy snapshot latest 和 Agent DailyAgentPromptArtifact latest 的差异与下游影响。

## Allowed Evidence

- GET readonly status/context endpoints。
- `pending_asof.json`、daily job files、latest signal pointer、readonly snapshot latest、Agent prompt latest、manifest 和 prompt_context。
- `fetch_tw_stock_readonly_status.mjs` 作为只读汇总脚本。

## Interpretation Rules

- daily status 和 latest signals asof/run_id 匹配时，qlib accepted latest 内部一致。
- `fresh_data_wait` 表示等待 Yahoo/Scrapling qlib 数据，不应手动 switch accepted latest。
- FinMind raw 更新但 Yahoo/Scrapling qlib 滞后时，应解释为 source timing difference。
- Agent prompt latest lag 不证明 provider 或 qlib stale。

## Forbidden Actions

不得运行 daily update、prompt build/publish、provider refresh/publish、accepted latest switch、real data pull、POST/PUT/PATCH/DELETE、monitor writes、broker/order 或 target position/weight。

## W2 Product Route Evidence

W2 sources reinforce the separation of latest pointers: provider/qlib accepted latest, readonly daily latest, readonly strategy snapshot latest, and Agent DailyAgentPromptArtifact latest. YZ pending execution price is a valid pending state when `next_open` is unavailable; it must not be repaired by fallback to next_close, signal close, synthetic OHLC, or accepted latest switch.

## W3 Code Evidence Map

- `backend/app/services/tw_stock_daily_auto_update_status.py` is the main readonly freshness status service.
- `backend/app/services/tw_stock_current_strategy_context.py` exposes asof alignment and no-write guarantees for current strategy context.
- `backend/app/services/readonly_strategy_snapshot.py` and `backend/app/services/tw_stock_agent_daily_prompt.py` prove snapshot latest and Agent prompt latest are separate pointers.
- Provider staging scripts are boundary/diagnostic sources and must not be run as freshness diagnosis.

## Sources

- [[references/code-map-backend-readonly-routes|Backend Readonly Routes Code Map]]
- [[references/code-map-scripts-and-tests|Scripts And Tests Code Map]]
- `.agents/skills/tw-stock-data-freshness-diagnosis/SKILL.md`
- `.agents/skills/tw-stock-data-freshness-diagnosis/references/freshness-status-fields.md`
