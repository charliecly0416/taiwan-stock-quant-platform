---
title: Superseded Routes: Model And Strategy
category: references
tags: [historical, superseded, model, strategy]
relationships:
  - target: "[[concepts/current-default-model-and-strategy]]"
    type: related_to
  - target: "[[synthesis/historical-lessons]]"
    type: related_to
sources: [/home/chuliyang/taiwan-stock-quant-platform/docs/tw_decision_model/PHASE2C_FINAL_REVIEW_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_ltr_baseline_conservative_tuning/PHASEB2A_REVIEW_AND_FINAL_CLOSURE_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_ltr_strategy_validation/PHASEV4_FINAL_REVIEW_AND_CLOSURE_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_ltr_rerank_regime_turnover/LTR_MAINLINE_FINAL_CLOSURE_ARCHIVE_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ4_ORTHOGONAL_FRESH_QLIB_DECISION_REVIEW_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEYZ_STRICT_E4_PRODUCTIZATION_FINAL_SUMMARY_CN.md]
summary: Historical/superseded model and strategy routes; they do not represent current product defaults after strict E4/YZ cleanup.
provenance:
  extracted: 0.86
  inferred: 0.14
  ambiguous: 0.0
base_confidence: 0.84
lifecycle: archived
lifecycle_changed: 2026-06-20
tier: supporting
created: 2026-06-20T17:00:00Z
updated: 2026-06-20T17:00:00Z
---

# Superseded Routes: Model And Strategy

历史路线，不代表当前默认路径。当前默认仍以 [[concepts/current-default-model-and-strategy]] 为准。

## Superseded Items

| Historical route | Classification | Why replaced | Current replacement |
|---|---|---|---|
| Entry Model v1 | superseded / failed research | 四个区间无法稳定超过 qlib rank，binary/ensemble/regression 均不足以过 gate | qlib rank + strict E4 artifact chain；如重启只可新开 risk/exit model 设计 |
| LTR simple / turnover optional sim | historical / non-default | 最终只接受 readonly optional simulation，不替代默认主线 | strict E4 current default；optional sim 只能历史复盘 |
| LTR readonly explanation | historical accepted sub-surface | 保留最小只读 explanation，但不扩展推荐/交易/写入 | current Agent/simple-chat and workbench explainability |
| Orthogonal Fresh Qlib | superseded | treatment 不优于 fresh qlib baseline，不进入只读产品候选 | strict E4 Model A + Model B scoped orthogonal LTR |
| fresh/adaptive/O4/P3/bridge/frozen fresh models | superseded | YZ clean registry 移除旧模型和实验项 | two production E4 models only |
| `origin` / `original` strategies | deprecated | 不能作为 production selectable | `top50_exit_one_worst_sell` |
| `one_sell_one_buy_buggy_e8r` | diagnostic-only | anomaly attribution / research-only，不能裸露为推荐 | neutral research-only label if needed |

## Lessons

- 单次收益、full range 和 mixed split 不能作为 default-switch evidence。
- 如果 treatment 和 control 同时改变模型、样本、过滤、窗口、特征口径，就无法判断收益来源。
- LTR 或正交特征若要重启，必须冻结 control、candidate boundary、PIT、feature schema、row coverage 和 replay rule。
- `next_open` 缺失时 pending 是正确产品状态，不能 fallback 到 next_close、signal close、0、空值或手写价格。

## Sources

- `docs/tw_decision_model/PHASE2C_FINAL_REVIEW_CN.md`
- `docs/tw_ltr_baseline_conservative_tuning/PHASEB2A_REVIEW_AND_FINAL_CLOSURE_CN.md`
- `docs/tw_ltr_strategy_validation/PHASEV4_FINAL_REVIEW_AND_CLOSURE_CN.md`
- `docs/tw_ltr_rerank_regime_turnover/LTR_MAINLINE_FINAL_CLOSURE_ARCHIVE_CN.md`
- `docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ4_ORTHOGONAL_FRESH_QLIB_DECISION_REVIEW_CN.md`
- `docs/tw_modular_daily_update_productization/PHASEYZ_STRICT_E4_PRODUCTIZATION_FINAL_SUMMARY_CN.md`
