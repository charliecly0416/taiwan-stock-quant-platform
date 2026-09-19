# DNG0 数据现状盘点审查报告

生成日期：2026-06-29

## 1. 结论

Verdict：`PASS_WITH_CONDITIONS_GO_DNG1`

DNG0 执行产物达到进入 DNG1 DataCatalog scanner 的最低门槛：已覆盖关键路径，能区分多种 latest 语义，能标注 canonical / experiment / temporary bridge，且提供了 route dependency 样本和 DNG1 scanner 的字段线索。

但本轮不能给无条件 PASS。原因是当前 inventory 中仍有多处依赖历史目录、实验目录和日期推断；若 DNG1 直接把这些路径标成正式 READY，会违反主线的治理目标。DNG1 必须把缺 manifest/schema/coverage/lineage 的路径降级为 `PARTIAL_READY`、`RESEARCH_ONLY`、`LEGACY_UNCATALOGED` 或 blocker 状态，不能伪造 canonical readiness。

## 2. 审查输入

已阅读：

- `docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md`
- `docs/tw_data_governance/DNG0_DATA_INVENTORY_WORK_CN.md`
- `docs/tw_data_governance/DNG0_DATA_INVENTORY_REVIEW_WORK_CN.md`
- `docs/tw_data_governance/DNG0_DATA_INVENTORY_EXECUTION_REPORT_CN.md`
- `data_tw/catalog/dng0_current_data_inventory.csv`
- `data_tw/catalog/dng0_latest_pointer_inventory.csv`
- `data_tw/catalog/dng0_route_dependency_sample.csv`

## 3. 覆盖范围审查

通过。

DNG0 inventory 覆盖了以下必要范围：

- `data_tw/artifacts/**`：ModelSignal、feature package、execution price bridge、readonly snapshot、readonly replay、shadow readiness、strategy intent、replay result 等均有记录。
- `data_tw/experiments/**`：policy/LTR/research experiment 总体目录、daily LTR rerank、E4 daily candidate、local option C demo 等均被标为 experiment / research-only。
- `data_tw/ops/daily_auto_update/**`：总体 job 目录、2026-06-26 passed job、2026-06-29 wait job、FinMind quarantine cache 均有记录。
- `qlib_pipeline/data_tw/**`：formal option C provider calendar、instrument、normalized store、option C accepted signal latest、ops refresh/publish history 均有记录。
- configs / contracts：`tw_product_artifact_registry`、`tw_modular_registry`、`docs/tw_modular_contracts` 已纳入 inventory。

覆盖不是完整 DataCatalog 级别的逐文件审计，但 DNG0 目标是现状地图，不要求在本阶段生成完整 catalog。

## 4. Latest 语义审查

通过，但 DNG1 必须继续强化。

DNG0 明确区分了：

- `provider_raw_latest` / `normalized_latest`：formal provider calendar 与 normalized evidence 到 `2026-06-25`。
- `qlib_accepted_latest`：`qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json` 停在 `2026-06-17`。
- `readonly_snapshot_latest`：readonly snapshot pointer asof `2026-06-18`，但 `data_asof/signal_asof=2026-06-17`。
- `feature_store_latest`：同时区分了 YZ2 strict E4 artifact 的 `2026-06-17` 与 experiment LTR rerank 的 `2026-06-25`。
- `price_store_latest`：YZ2/YZ2R execution price readiness 被标为 bridge，不是 canonical PriceStore。
- `readonly_bridge_latest`：readonly replay、artifact index、MTRP bridge 均与 accepted latest 分开。
- `agent_prompt_latest`：明确记录为 `MISSING`，没有从 readonly snapshot 推断。

这足以解释 6/17、6/25、6/29 不一致来自不同层级，而不是单一“latest”停滞。

保留意见：`qlib_accepted_latest` 行状态为 READY，但其说明同时包含 `diagnostic_only=true`、`research_signal_not_order=true`。DNG1 不得把这个 READY 扩大解释为 production-ready；应拆分 pointer existence、accepted pointer status、production eligibility 三类字段。

## 5. Canonical / Experiment / Temporary Bridge 审查

通过。

DNG0 已区分：

- canonical candidate：formal option C provider calendar/instruments/normalized、normalized_nonempty、TWII normalized source。
- standard artifact：YZ strict E4 ModelSignal、YZ2 feature package、readonly snapshot、readonly replay/index 等。
- experiment / research-only：`data_tw/experiments/**`、daily LTR rerank、E4 daily candidate、local demo。
- temporary bridge：YZ2/YZ2R execution readiness、MTRP full-rank visibility bridge、shadow readiness、stop/readiness artifact、replay comparison artifact。
- missing layer：Agent DailyAgentPromptArtifact latest。

该分类可支撑 DNG1 scanner 的初始 `canonicality` 与 `status` 映射。

## 6. DNG1 Scanner 支撑度

通过，带条件。

三份 CSV 已提供 DNG1 所需的核心 schema 线索：

- current inventory：`layer`、`dataset_or_artifact`、`path`、`exists`、`file_count`、`dir_count`、`date_min`、`date_max`、`latest_pointer_type`、`status`、`status_reason`、`canonicality`、`recommended_next_action`。
- latest pointer inventory：`latest_concept`、`path`、`exists`、`asof`、`run_id`、`target_path`、`status`、`status_reason`、`downstream_surface`。
- route dependency sample：`route_id`、`dependency_name`、`current_source_path`、`required_layer`、`latest_concept`、`canonicality`、`known_blocker`、`recommended_contract`。

DNG1 可以据此实现只读 scanner、latest_status 聚合、legacy path 标记和 readiness matrix 输入雏形。

条件：

1. DNG1 validator 必须检查路径存在、manifest/schema/coverage/lineage/validator_report 是否存在，缺失时不得标 `READY`。
2. 对日期来自 calendar/job inventory 推断而非 artifact manifest 的记录，必须保留 `inferred=true` 或等价字段。
3. `data_tw/experiments/**` 默认不得成为 canonical 输入源，除非 route dependency contract 明确允许且 status 标为 research-only。
4. bridge/readiness/replay/shadow 产物必须保留 `readonly_only`、`not_published_latest`、`production_allowed=false`、`not_order` 等安全语义。
5. latest_status 必须按层级输出，不得合并成一个全局 latest。

## 7. Forbidden Action 审查

通过。

执行报告明确声明未执行：

- 真实抓数；
- provider refresh / publish；
- qlib accepted latest switch；
- readonly latest publish；
- Agent prompt latest publish；
- 模型训练；
- 模型推理；
- 策略回放；
- broker / order / quick-trade；
- `target_position` / `target_weight`。

CSV 中也把 2026-06-26 job 的 `provider_publish_triggered=false`、`latest_signal_updated=false`，以及 2026-06-29 job 的 `today_data_window_wait` 状态单独列出。未发现 DNG0 将 historical provider ops 或 existing replay artifact 冒充为本轮执行动作的证据。

## 8. 风险与条件

进入 DNG1 前不要求 DNG0 repair，但 DNG1 必须处理以下风险：

1. formal option C accepted signal 指针停在 `2026-06-17`，provider/normalized evidence 到 `2026-06-25`，daily auto `2026-06-29` 仍是 wait；scanner 必须能同时展示三者。
2. YZ2R execution readiness 是 temporary bridge，不是 canonical PriceStore；DNG2 之前不得让策略/回放把它当正式 PriceStore。
3. LTR daily rerank latest 在 experiment 路径到 `2026-06-25`，不能当 canonical FeatureArtifact。
4. Agent prompt latest 缺失，DNG1/DNG6 应输出 `MISSING`，不能从 readonly snapshot 或 strategy context 推断。
5. historical refresh/publish evidence 只能作为既有证据，不是当前授权，不得触发 provider publish 或 latest switch。

## 9. 下一步建议

允许进入 DNG1。

DNG1 scanner 的重点要求：

- 只读扫描，不抓数、不 publish、不切 latest。
- 输出 `data_catalog.json` 与 `latest_status.json` 时，把 pointer 存在、artifact readiness、production eligibility 分开。
- 对没有完整 manifest/schema/coverage/lineage 的历史目录标记 `LEGACY_UNCATALOGED` 或 `PARTIAL_READY`。
- 把 `provider_raw_latest`、`normalized_latest`、`qlib_accepted_latest`、`model_signal_latest`、`readonly_snapshot_latest`、`agent_prompt_latest` 分层输出。
- route dependency sample 应升级为 machine-readable readiness 输入，但缺失依赖只能阻断或标 blocker，不能自动修复。
