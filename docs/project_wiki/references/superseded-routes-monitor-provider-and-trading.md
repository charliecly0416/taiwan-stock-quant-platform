---
title: Superseded Routes: Monitor Provider And Trading
category: references
tags: [historical, boundary, provider, trading]
relationships:
  - target: "[[concepts/readonly-safety-boundary]]"
    type: uses
  - target: "[[synthesis/historical-lessons]]"
    type: related_to
sources: [/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/REAL_PROVIDER_DAILY_UPDATE_RUNBOOK_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_FINAL_ROUTE_REVIEW_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEYZ_STRICT_E4_PRODUCTIZATION_FINAL_SUMMARY_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/archive/phase_history/README_CN.md, /home/chuliyang/taiwan-stock-quant-platform/scripts/archive/historical_research/README.md]
summary: Monitor, provider publish/accepted latest, quick-trade, broker, credentials, and archived scripts are boundary-only historical material, not current TW-stock capability.
provenance:
  extracted: 0.84
  inferred: 0.16
  ambiguous: 0.0
base_confidence: 0.84
lifecycle: archived
lifecycle_changed: 2026-06-20
tier: supporting
created: 2026-06-20T17:00:00Z
updated: 2026-06-20T17:00:00Z
---

# Superseded Routes: Monitor Provider And Trading

历史路线和禁区材料，不代表当前默认路径。当前台股主线是只读研究和 simulation-only paper/sim gate。

## Boundary Map

| Source group | Classification | Lesson | Current replacement |
|---|---|---|---|
| monitor config/scan/alerts | boundary-only | 旧 UI/route 存在但不能被 Agent/front-end 触发写入 | readonly workbench display and network denylist |
| provider refresh/publish | boundary-only | provider publish 不等于 readonly latest；不能作为默认修复 stale 的建议 | provider readiness + readonly daily update gates |
| accepted latest scheduler/switch | boundary-only | accepted latest switch 是高风险 ops path，不是 diagnosis action | separate latest pointer diagnosis |
| quick-trade/broker/orders | boundary-only | 交易相关代码只作为禁区证据 | simulation-only ledger/paper portfolio gate |
| credentials/API keys | boundary-only | credential route 不能进入 wiki 内容或 Agent context | never read/copy secrets; document only policy boundary |
| scripts/archive/historical_research | historical / skip runtime | 归档脚本不再是 active product chain | root `scripts/` validators/builders and current contracts |
| docs/archive/phase_history | historical | 479 个阶段过程文件保留证据，不是当前入口 | docs summaries/contracts/runbooks and project wiki current pages |

## Lessons

- Stale/freshness diagnosis 只能读状态和 latest pointers，不能建议 provider publish 或 accepted latest switch。
- Manual provider/daily update entry 即使存在，也必须保持 run registry、validator、readonly latest 和 no-write boundary。
- 交易、credential、quick-trade、broker、target position/weight 词只能出现在拒绝、denylist、安全边界或历史说明中。
- 历史脚本恢复前必须重新检查 current data contracts、strict E4/YZ model scope、readonly boundaries 和 frontend/API references。

## Sources

- `docs/tw_modular_daily_update_productization/REAL_PROVIDER_DAILY_UPDATE_RUNBOOK_CN.md`
- `docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_FINAL_ROUTE_REVIEW_CN.md`
- `docs/tw_modular_daily_update_productization/PHASEYZ_STRICT_E4_PRODUCTIZATION_FINAL_SUMMARY_CN.md`
- `docs/archive/phase_history/README_CN.md`
- `scripts/archive/historical_research/README.md`
