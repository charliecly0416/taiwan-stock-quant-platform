---
title: Real Sample 2026-06-18
category: references
tags: [daily-update, real-sample, tw2330, tw3481]
aliases: [TW_DAILY_UPDATE_DATA_FLOW_REAL_SAMPLE_20260618]
relationships:
  - target: "[[concepts/daily-update-data-flow]]"
    type: derived_from
sources: [/home/chuliyang/taiwan-stock-quant-platform/docs/tw_new_model_strategy_pre_rnd/TW_DAILY_UPDATE_DATA_FLOW_REAL_SAMPLE_20260618_CN.md]
summary: 真实样本文档说明 TW2330 在 qlib rank 103 后停止，TW3481 经 LTR rank 1 进入 2026-06-18 readonly 候选。
provenance:
  extracted: 0.92
  inferred: 0.08
  ambiguous: 0.0
base_confidence: 0.67
lifecycle: draft
lifecycle_changed: 2026-06-20
tier: supporting
created: 2026-06-20T00:00:00Z
updated: 2026-06-20T00:00:00Z
---

# Real Sample 2026-06-18

该参考页来自真实样本文档，用于防止后续研发只停留在流程抽象，而忽略每个模块的真实输入、字段和值。

## TW2330

- 标准化价格 CSV 有历史价格，但本地最后一行只到 `2026-06-01`。
- qlib Model A 有输出：`buy_score=-0.024562304811117618`，`score_rank=103`。
- 因为 qlib rank 103 不在 top50，`TW2330` 没有进入 LTR 特征包、LTR Model B 或前端 top candidates。

## TW3481

- qlib Model A：`buy_score=0.0748663325254153`，`full_qlib_rank=31`。
- LTR Model B：`buy_score=1.4873123416297531`，`score_rank=1`。
- 进入 `2026-06-18` readonly strategy snapshot 前端候选第 1。
- 执行价格 readiness 为 `execution_price_unavailable`，因为本地没有目标日真实执行价格。

## Sources

- `docs/tw_new_model_strategy_pre_rnd/TW_DAILY_UPDATE_DATA_FLOW_REAL_SAMPLE_20260618_CN.md`
