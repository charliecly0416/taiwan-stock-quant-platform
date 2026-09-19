# DNG1 DataCatalog 只读 Scanner 执行报告

生成日期：2026-06-29

## 1. 执行结论

Verdict：`PASS_GO_DNG2_WITH_CONDITIONS`

DNG1 已实现只读 DataCatalog scanner 与 validator，并生成指定产物。validator 结果为 `passed`，错误 0、警告 0。

本轮保持 DNG0 审查要求的保守口径：bridge、experiment、legacy candidate、缺 manifest/schema/coverage/lineage 的路径没有被标为 canonical `READY`。当前 36 条 catalog entries 中仅 1 条为 `READY`，其余均保守降级或保留 blocker/missing/stale 状态。

## 2. 已读取输入

已读取并使用：

- `docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md`
- `docs/tw_data_governance/DNG1_DATA_CATALOG_WORK_CN.md`
- `docs/tw_data_governance/DNG0_DATA_INVENTORY_REVIEW_CN.md`
- `docs/tw_data_governance/DNG0_DATA_INVENTORY_EXECUTION_REPORT_CN.md`
- `data_tw/catalog/dng0_current_data_inventory.csv`
- `data_tw/catalog/dng0_latest_pointer_inventory.csv`
- `data_tw/catalog/dng0_route_dependency_sample.csv`

## 3. 生成产物

已生成：

- `scripts/build_tw_data_catalog.py`
- `scripts/validate_tw_data_catalog.py`
- `data_tw/catalog/data_catalog.json`
- `data_tw/catalog/latest_status.json`
- `data_tw/catalog/data_catalog_summary.csv`
- `data_tw/catalog/data_catalog_validation.json`
- `docs/tw_data_governance/DNG1_DATA_CATALOG_EXECUTION_REPORT_CN.md`

## 4. Scanner 设计

`scripts/build_tw_data_catalog.py` 只读取 DNG0 CSV 与本地文件证据，不调用抓数、provider refresh/publish、latest switch、模型训练/推理、策略回放或交易相关入口。

核心规则：

- 从 DNG0 inventory 生成 `entries[]`，补齐 DNG1 最小字段。
- 对本地路径做存在性检查，并扫描局部 evidence：`manifest.json`、`schema.json`、`coverage_audit.*`、`source_trace/lineage`、`validator_report/validator_result/validation_report`。
- `READY` 只允许用于路径存在、证据完整、非 temporary bridge、非 experiment、非 legacy uncataloged 且 forbidden flags 全安全的条目。
- `data_tw/experiments/**`、demo、ops history 默认为 `RESEARCH_ONLY`。
- bridge、shadow、readonly bridge、replay bridge、temporary research bridge 默认为 `TEMPORARY_BRIDGE`，或保留已有 blocker。
- 缺统一 manifest/schema/coverage/lineage 的 canonical candidate 或 standard artifact 降为 `PARTIAL_READY`。
- legacy accepted signal candidate 缺完整证据时标为 `LEGACY_UNCATALOGED`。

## 5. Catalog 统计

`data_catalog.json` entries 数量：36。

Status 分布：

| status | count |
| --- | ---: |
| READY | 1 |
| PARTIAL_READY | 18 |
| TEMPORARY_BRIDGE | 7 |
| RESEARCH_ONLY | 6 |
| LEGACY_UNCATALOGED | 1 |
| BLOCKED_COVERAGE | 1 |
| STALE | 1 |
| MISSING | 1 |

唯一 `READY` 条目：

- `model_signal / phase_yz_yz1_strict_e4_model_signals`
- path：`data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17`
- 原因：本地存在 manifest/schema/coverage/source_trace/validator evidence，且不是 bridge/experiment/legacy uncataloged。

## 6. latest_status 关键不一致

`latest_status.json` 覆盖 DNG1 要求的全部 latest concepts，缺失概念显式写为 `MISSING`。

关键状态：

| latest concept | status | asof |
| --- | --- | --- |
| provider_raw_latest | PARTIAL_READY | 2026-06-25 |
| normalized_latest | PARTIAL_READY | 2026-06-25 |
| price_store_latest | PARTIAL_READY | 2026-06-17 |
| feature_store_latest | RESEARCH_ONLY | 2026-06-25 |
| qlib_accepted_latest | PARTIAL_READY | 2026-06-17 |
| model_signal_latest | RESEARCH_ONLY | 2026-06-17 |
| readonly_bridge_latest | TEMPORARY_BRIDGE | 2026-05-07 |
| readonly_snapshot_latest | READY | 2026-06-18 |
| agent_prompt_latest | MISSING |  |
| temporary_research_bridge_latest | MISSING |  |

记录的关键 mismatch：

- provider/normalized evidence 到 `2026-06-25`，但 `qlib_accepted_latest` 仍是 `2026-06-17`。
- readonly snapshot asof 是 `2026-06-18`，但 source signal/data asof 是 `2026-06-17`。
- `agent_prompt_latest` 缺失，不能从 readonly snapshot 或 strategy context 推断。
- `price_store_latest` 仍是 execution readiness bridge，不是 canonical PriceStore latest。

## 7. Validator 输出

执行命令：

```bash
python scripts/validate_tw_data_catalog.py --catalog data_tw/catalog/data_catalog.json --latest-status data_tw/catalog/latest_status.json --output data_tw/catalog/data_catalog_validation.json --json
```

结果：

```text
ok=true
status=passed
entry_count=36
errors=0
warnings=0
```

已检查：

- top-level required fields；
- entry required fields；
- status enum；
- 路径存在性；
- latest concepts 覆盖完整；
- forbidden action flags；
- `READY` 未用于 temporary bridge / legacy uncataloged；
- `READY` 要求 manifest/schema/coverage/lineage evidence。

## 8. DNG0 条件满足情况

已满足 DNG0 Review 对 DNG1 的条件：

- 缺 manifest/schema/coverage/lineage 的路径未标为 `READY`，多降为 `PARTIAL_READY`。
- `data_tw/experiments/**` 未作为 canonical 输入源，标为 `RESEARCH_ONLY` 或 `TEMPORARY_BRIDGE`。
- bridge/readiness/replay/shadow 路径未标为 `READY`，并保留 readonly/not latest switch/not order 语义。
- `agent_prompt_latest` 明确为 `MISSING`，未从 readonly snapshot 推断。
- latest_status 按层级输出，没有合并成单一全局 latest。

## 9. Forbidden Action Audit

DNG1 执行过程未触发：

- 真实抓数；
- provider refresh / publish；
- qlib accepted latest switch；
- readonly latest publish；
- Agent prompt latest publish；
- 模型训练；
- 模型推理；
- 策略回放；
- broker/order/quick-trade；
- `target_position` / `target_weight`。

`data_catalog.json` 与 `latest_status.json` 中 forbidden action flags 均为安全值，validator 已检查通过。

## 10. 是否建议进入 DNG2

建议进入 DNG2，但必须带条件推进。

DNG2 重点应是 canonical contract 补齐，而不是 publish 或切 latest：

- 为 NormalizedStore、PriceStore、FeatureStore、qlib provider view 补正式 manifest/schema/coverage/lineage。
- 将 YZ2/YZ2R execution readiness bridge 迁移为 canonical PriceStore 或明确只作为 bridge evidence。
- 将 TWII 从 normalized CSV source 收敛为 market_feature_store/twii_daily。
- 将 `qlib_accepted_latest`、readonly latest、Agent prompt latest 继续保持独立 gate。
- 在 DNG2 前不得把 current bridge/research-only paths 作为默认策略输入。
