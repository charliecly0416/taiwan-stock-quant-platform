---
title: Current Default Model And Strategy
category: concepts
tags: [model, strategy, default, qlib, ltr]
aliases: [当前默认模型与策略, E4 Qlib Orthogonal LTR]
relationships:
  - target: "[[concepts/product-artifact-registry]]"
    type: derived_from
  - target: "[[concepts/data-freshness-and-latest-pointers]]"
    type: related_to
sources: [/home/chuliyang/taiwan-stock-quant-platform/configs/tw_product_artifact_registry.yaml, /home/chuliyang/taiwan-stock-quant-platform/configs/tw_modular_registry.yaml, /home/chuliyang/taiwan-stock-quant-platform/configs/tw_replay_window_policy.yaml, /home/chuliyang/taiwan-stock-quant-platform/configs/tw_modular_replay_matrix.yaml, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/TW_CURRENT_STRATEGY_CONTEXT_API_FIELD_DICTIONARY_CN.md]
summary: 当前产品研究线是 E4 Qlib + Orthogonal LTR，默认展示策略为 top50_exit_one_worst_sell，LTR 只在 qlib top50 内重排。
provenance:
  extracted: 0.87
  inferred: 0.13
  ambiguous: 0.0
base_confidence: 0.88
lifecycle: draft
lifecycle_changed: 2026-06-20
tier: core
created: 2026-06-20T12:00:00Z
updated: 2026-06-20T17:00:00Z
---

# Current Default Model And Strategy

当前产品研究线是 `E4 Qlib + Orthogonal LTR`。Qlib top50 定义候选和退出边界，Orthogonal LTR 只在 qlib top50 内重排买入优先级。

## Product Defaults

| Item | Current value |
|---|---|
| base model | `e4_frozen_qlib_2018_2022` |
| treatment model | `e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025` |
| display model alias | `e4_frozen_qlib_2023_2025_ltr` |
| default strategy rule | `top50_exit_one_worst_sell` |
| candidate boundary | `qlib_top50` |
| ranking source | `ltr_rerank_within_qlib_top50` |
| execution price mode | `next_open` |

## Strategy Dependency Classification

| dependency | W1 classification | Notes |
|---|---|---|
| `top50_exit_one_worst_sell.yaml` | current product default | Requires `candidate_rank`, `buy_score`, `full_qlib_rank`, `signal_asof`, `available_at`; max one buy and one sell. |
| `one_sell_one_buy_correct.yaml` | research-only candidate | Same core field shape as default but not frontend selectable or production default. |
| `one_sell_one_buy_buggy_e8r.yaml` | diagnostic-only buggy historical rule | `diagnostic_only=true`, `not_valid_strategy_evidence=true`; audit/diff/anomaly attribution only. |
| `original.yaml` | deprecated/historical | Not frontend/API selectable. |
| `top50_exit_all.yaml` | deprecated/historical research | Not product selectable. |
| `m2_strategy_dependency_template.yaml` | template | Contract template only, not a strategy candidate. |
| `dummy_new_strategy_dependency_smoke.yaml` | smoke/template | Smoke-only, not default candidate. |
| `sector_extension_analysis_smoke.yaml` | smoke/analysis | Extension analysis smoke, not product strategy. |

## Non-Default Boundary

`DefaultCandidateDecision` requires fixed OOS evidence, same-window baseline comparison, coverage audit, validator status, risk metrics, review conclusion and user confirmation before any default switch. No W1 source grants permission to default-switch model or strategy.


## W4 Historical Boundary

Older `fresh`, `adaptive`, `O4`, `P3`, `bridge`, `origin/original`, Entry Model v1, optional LTR simulation and diagnostic E8R strategy names are historical, superseded or diagnostic-only unless re-approved through a new reviewed contract. They are tracked in [[references/superseded-routes-model-and-strategy]] and must not be offered as current defaults.

## Sources

- `configs/tw_product_artifact_registry.yaml`
- `configs/tw_modular_registry.yaml`
- `configs/tw_replay_window_policy.yaml`
- `docs/tw_modular_contracts/TW_CURRENT_STRATEGY_CONTEXT_API_FIELD_DICTIONARY_CN.md`
