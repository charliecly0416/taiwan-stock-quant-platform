---
title: Skills Maintenance Final
category: references
tags: [skills, maintenance, tw-stock, readonly]
sources: ['/home/chuliyang/taiwan-stock-quant-platform/docs/tw_skills_maintenance/PHASES4_FINAL_SUMMARY_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_skills_maintenance/PHASES4_FINAL_ACCEPTANCE_REVIEW_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_skills_maintenance/TW_SKILLS_MAINTENANCE_S_ROUTE_FINAL_SUMMARY_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_skills_maintenance/TW_SKILLS_MAINTENANCE_S_ROUTE_FINAL_REVIEW_CN.md']
summary: Final accepted state of nine project-local tw-stock skills, their trigger boundaries, delegation rules and archive risk.
provenance:
  extracted: 0.95
  inferred: 0.05
  ambiguous: 0.0
base_confidence: 0.9
lifecycle: draft
lifecycle_changed: 2026-06-20
tier: supporting
created: 2026-06-20T14:00:00Z
updated: 2026-06-20T15:00:00Z
---

# Skills Maintenance Final

The project-local `.agents/skills/tw-stock-*` set is the current authority for Taiwan stock workflows. User-level active `/home/chuliyang/.agents/skills/tw-stock-*` paths are empty; archived old skills are backups and must not be treated as active sources.

## Active Project Skills

- `tw-stock-agent-daily-prompt-maintenance`
- `tw-stock-data-freshness-diagnosis`
- `tw-stock-frontend-workbench-ux-review`
- `tw-stock-modular-integration-regression`
- `tw-stock-new-model-onboarding`
- `tw-stock-new-strategy-onboarding`
- `tw-stock-readonly-e2e-acceptance`
- `tw-stock-research-context-analyst`
- `tw-stock-safety-boundary-review`

## Boundary

These skills do not authorize real data pulls, provider refresh/publish, accepted latest switch, monitor writes, broker/order/quick-trade, target position/weight, frontend OpenAI, key exposure, default model/strategy switch, or return/probability promises.

## Related

- [[skills/safety-boundary-review-workflow]]
- [[skills/readonly-e2e-acceptance-workflow]]
- [[skills/data-freshness-diagnosis-workflow]]
- [[skills/modular-integration-regression-workflow]]

## Sources

- `docs/tw_skills_maintenance/PHASES4_FINAL_SUMMARY_CN.md`
- `docs/tw_skills_maintenance/PHASES4_FINAL_ACCEPTANCE_REVIEW_CN.md`
- `docs/tw_skills_maintenance/TW_SKILLS_MAINTENANCE_S_ROUTE_FINAL_SUMMARY_CN.md`
- `docs/tw_skills_maintenance/TW_SKILLS_MAINTENANCE_S_ROUTE_FINAL_REVIEW_CN.md`
