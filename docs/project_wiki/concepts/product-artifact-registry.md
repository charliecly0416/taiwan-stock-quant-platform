---
title: Product Artifact Registry
category: concepts
tags: [registry, product, artifacts, readonly]
aliases: [产品 artifact registry, 产品注册表]
relationships:
  - target: "[[concepts/current-default-model-and-strategy]]"
    type: uses
  - target: "[[concepts/modular-artifact-chain]]"
    type: related_to
sources: [/home/chuliyang/taiwan-stock-quant-platform/configs/tw_product_artifact_registry.yaml, /home/chuliyang/taiwan-stock-quant-platform/configs/tw_modular_registry.yaml, /home/chuliyang/taiwan-stock-quant-platform/configs/data_source_registry.yaml, /home/chuliyang/taiwan-stock-quant-platform/configs/price_store_registry.yaml, /home/chuliyang/taiwan-stock-quant-platform/configs/feature_registry.yaml]
summary: 产品 registry 是默认模型、默认策略、标准 artifact 路径和只读安全 flags 的入口，前端不得硬编码实验路径。
provenance:
  extracted: 0.86
  inferred: 0.14
  ambiguous: 0.0
base_confidence: 0.88
lifecycle: draft
lifecycle_changed: 2026-06-20
tier: core
created: 2026-06-20T12:00:00Z
updated: 2026-06-20T16:00:00Z
---

# Product Artifact Registry

`configs/tw_product_artifact_registry.yaml` 是当前产品化只读链路的默认入口。它声明模型线、默认策略、artifact root、readonly snapshot latest pointer、重建来源、价格来源和安全 flags。

## Current Registry Values

- `profile = strict_e4_yz_product`。
- `readonly_only = true`。
- base model: `e4_frozen_qlib_2018_2022`。
- treatment model: `e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025`。
- display treatment model: `e4_frozen_qlib_2023_2025_ltr`。
- default strategy rule: `top50_exit_one_worst_sell`。
- readonly snapshot latest pointer: `data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json`。

## Registry Roles

- Product registry controls product-facing model/strategy IDs and artifact roots.
- Modular registry maps contracts, capabilities, strategy classes, deprecated rules and M2 onboarding template entries.
- Data source, price store and feature registries provide contract docs, validators, golden samples, capabilities, dependencies and forbidden consumers for each artifact class.
- Strategy dependency YAML files declare the exact core fields/capabilities a strategy may consume.

## Safety Flags

The registry explicitly preserves:

```text
no_training_in_product_context=true
no_provider_publish=true
no_accepted_latest_switch=true
no_monitor_write=true
no_broker_order=true
```

These flags mean registry-backed product display is still readonly; it does not authorize data refresh, accepted latest switch, monitor writes or broker/order behavior.

## Frontend Rule

Frontend and Agent surfaces should use registry-backed APIs such as [[concepts/frontend-strategy-workbench]] and current-strategy-context, rather than hardcoding `data_tw/artifacts/...` paths or legacy CSV files. ^[inferred]

## W3 Code Evidence

`backend/app/services/tw_stock_artifact_registry.py` exposes `load_product_artifact_registry`, `registry_get` and `registry_path` over `configs/tw_product_artifact_registry.yaml`. `backend/app/services/tw_stock_current_strategy_context.py` uses `registry_path("artifacts", "readonly_strategy_latest")` to load the current readonly strategy latest pointer. This reinforces that product defaults and artifact paths must be registry-backed rather than inferred from replay output or frontend local constants.

## Sources

- [[references/code-map-backend-readonly-routes|Backend Readonly Routes Code Map]]
- `configs/tw_product_artifact_registry.yaml`
- `configs/tw_modular_registry.yaml`
- `configs/data_source_registry.yaml`
- `configs/price_store_registry.yaml`
- `configs/feature_registry.yaml`
