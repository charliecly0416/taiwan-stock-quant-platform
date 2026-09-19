---
title: Historical Lessons
category: synthesis
tags: [historical, superseded, lessons, risk]
relationships:
  - target: "[[synthesis/current-mainline-vs-superseded-routes]]"
    type: related_to
  - target: "[[synthesis/project-risk-map]]"
    type: related_to
  - target: "[[concepts/readonly-safety-boundary]]"
    type: uses
sources: [/home/chuliyang/taiwan-stock-quant-platform/docs/tw_decision_model/PHASE2C_FINAL_REVIEW_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_ltr_rerank_regime_turnover/LTR_MAINLINE_FINAL_CLOSURE_ARCHIVE_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_ltr_strategy_validation/PHASEV4_FINAL_REVIEW_AND_CLOSURE_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_ltr_baseline_conservative_tuning/PHASEB2A_REVIEW_AND_FINAL_CLOSURE_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEYZ_STRICT_E4_PRODUCTIZATION_FINAL_SUMMARY_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/archive/phase_history/README_CN.md, /home/chuliyang/taiwan-stock-quant-platform/scripts/archive/historical_research/README.md]
summary: W4 历史教训汇总：旧模型/策略/Agent/frontend/provider/trading 路线只保留为背景、边界或误读风险，不代表当前默认路径。
provenance:
  extracted: 0.82
  inferred: 0.18
  ambiguous: 0.0
base_confidence: 0.84
lifecycle: draft
lifecycle_changed: 2026-06-20
tier: core
created: 2026-06-20T17:00:00Z
updated: 2026-06-20T17:00:00Z
---

# Historical Lessons

W4 的核心结论：历史路线保留为证据和教训，不恢复为当前默认路径。当前主线仍是 [[concepts/current-default-model-and-strategy|strict E4 + top50_exit_one_worst_sell]]、[[concepts/agent-daily-prompt-route|DailyAgentPromptArtifact + backend simple-chat]]、[[concepts/frontend-strategy-workbench|/tw-stock-monitor readonly workbench]] 和 [[concepts/readonly-safety-boundary|只读安全边界]]。

## Lessons

- Entry Model v1 没有稳定超过 qlib rank，应归档为失败研究；可复用的是 PIT 样本、gate delta、ablation 和失败归因模板，不是模型本身。
- 旧 LTR rerank/regime/turnover 路线只保留最小只读 explanation 或 optional simulation surface；不得包装为推荐、交易、默认策略或收益承诺。
- full range、mixed split、旧 smoke、旧截图、旧 E2E 通过结果只能作为历史验收背景；不能替代 current artifact/latest pointer、validator 和 readonly E2E。
- fresh/adaptive/O4/P3/bridge/frozen-fresh 系列旧模型已被 strict E4 clean registry 替代；若未来重启，必须新开合同，不得从历史实验直接复活。
- orthogonal/fundamental/FinMind 方向的稳定教训是 PIT/available_at、coverage 和控制变量优先；没有官方可见时间或覆盖不足时必须停止或降权。
- `scripts/archive/historical_research/**` 是归档脚本，只能用于方法追溯；恢复任何脚本前必须重新核对当前 contracts、strict E4/YZ scope、readonly boundary 和前端/API 路线。

## Misread Risks

| Historical artifact | Correct reading | Risk if misread |
|---|---|---|
| Entry Model v1 reports | failed/superseded research | 把不稳定 rerank 写成 AI 选股能力 |
| LTR Phase V/B closure | readonly optional/display-only | 把 optional sim 写成默认或交易策略 |
| Fresh/O4/P3 experiments | superseded comparisons | 把旧模型加入 product selectable |
| YZ pending replay | clean display/pending state | 把 pending replay 当 2026 收益证明 |
| Archive scripts | traceability only | 直接运行历史训练/回放/refresh 脚本 |
| Browser/network fixtures | acceptance scenario evidence | 把 mock payload 当生产 artifact |

## Current Replacement

- 模型/策略替代：two-model strict E4 registry + `top50_exit_one_worst_sell`。
- Agent 替代：DailyAgentPromptArtifact -> `TWStockAgentSimpleChatService` -> `/agent/simple-chat`。
- 前端替代：`/tw-stock-monitor` readonly strategy workbench，而不是旧 monitor/ops/debug panel。
- Provider/latest 替代：readonly daily/status/latest gates，禁止 provider publish 和 accepted latest switch 作为默认建议。
- Trading 替代：simulation-only paper/sim account gate，不连接 broker、不提交订单。

## Sources

- [[references/superseded-routes-model-and-strategy|Superseded Routes: Model And Strategy]]
- [[references/superseded-routes-agent-and-tools|Superseded Routes: Agent And Tools]]
- [[references/superseded-routes-monitor-provider-and-trading|Superseded Routes: Monitor Provider And Trading]]
- `docs/archive/phase_history/README_CN.md`
- `scripts/archive/historical_research/README.md`
