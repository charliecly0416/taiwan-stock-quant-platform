# DNG1 DataCatalog 审查报告

生成日期：2026-06-29

审查者：DNG1 Reviewer

## 1. 审查结论

Verdict：`PASS_WITH_CONDITIONS_GO_DNG2`

DNG1 可以进入 DNG2。理由是：本轮已建立保守的 DataCatalog scanner 与 validator，产物覆盖工作单要求，validator 本地运行通过，且未发现 scanner 触发抓数、provider publish、latest switch、模型训练/推理、策略回放或交易相关动作。

通过条件是：DNG2 只能推进 PriceStore / TWII / Calendar 的 canonical contract 补齐，不得把当前 bridge、experiment、readonly pointer 或缺 manifest/schema/coverage/lineage 的历史路径当作生产可用输入；不得切 qlib accepted latest、readonly latest、Agent prompt latest 或任何 production default latest。

## 2. 已审查输入

已阅读：

- `docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md`
- `docs/tw_data_governance/DNG1_DATA_CATALOG_WORK_CN.md`
- `docs/tw_data_governance/DNG1_DATA_CATALOG_REVIEW_WORK_CN.md`
- `docs/tw_data_governance/DNG1_DATA_CATALOG_EXECUTION_REPORT_CN.md`
- `scripts/build_tw_data_catalog.py`
- `scripts/validate_tw_data_catalog.py`
- `data_tw/catalog/data_catalog.json`
- `data_tw/catalog/latest_status.json`
- `data_tw/catalog/data_catalog_summary.csv`
- `data_tw/catalog/data_catalog_validation.json`

## 3. 本地验证结果

执行：

```bash
python -m py_compile scripts/build_tw_data_catalog.py scripts/validate_tw_data_catalog.py
```

结果：通过，退出码 0。

执行：

```bash
python scripts/validate_tw_data_catalog.py --catalog data_tw/catalog/data_catalog.json --latest-status data_tw/catalog/latest_status.json --json
```

结果：

```text
ok=true
status=passed
entry_count=36
errors=0
warnings=0
```

validator 报告的 status 分布：

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

## 4. 审查发现

### 4.1 Scanner 只读性

`scripts/build_tw_data_catalog.py` 的输入是 DNG0 CSV 与本地证据文件，主要操作为读取本地路径、扫描 manifest/schema/coverage/lineage/validator evidence、计算 checksum、写出 DNG1 指定 catalog/status/summary 产物。脚本未导入或调用 provider、网络抓数、qlib publish、模型、回放或交易入口。

`rg` 检查仅命中 forbidden action 字段名和状态说明，未发现 `requests`、`Fetcher`、`subprocess`、训练/推理/回放/交易调用或 destructive 文件操作。

结论：满足 DNG1 只读 scanner 要求。写出 `data_catalog.json`、`latest_status.json`、`data_catalog_summary.csv` 属于 DNG1 指定输出，不构成 forbidden action。

### 4.2 READY 口径保守

`data_catalog.json` 共 36 条 entry，仅 1 条为 `READY`：

- `model_signal / phase_yz_yz1_strict_e4_model_signals`
- path：`data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17`

该 READY 条目存在 manifest/schema/coverage/lineage/validator evidence，且不是 bridge、experiment 或 legacy uncataloged。

其余条目被保守降级或保留阻断状态。DNG0 中部分原本看似 READY 的 registry、contract、normalized、qlib accepted signal、readonly snapshot、feature package，因为缺完整 evidence、属于 legacy/experiment/bridge，或只代表 pointer/evidence，没有被升为 canonical READY。

结论：READY 口径符合 DNG1 要求。

### 4.3 latest concepts 覆盖完整

`latest_status.json` 覆盖全部 10 个 required latest concepts：

- `provider_raw_latest`
- `normalized_latest`
- `price_store_latest`
- `feature_store_latest`
- `qlib_accepted_latest`
- `model_signal_latest`
- `readonly_bridge_latest`
- `readonly_snapshot_latest`
- `agent_prompt_latest`
- `temporary_research_bridge_latest`

关键状态被分层记录：

| concept | status | asof | 审查说明 |
| --- | --- | --- | --- |
| provider_raw_latest | PARTIAL_READY | 2026-06-25 | provider/calendar evidence，不等于 qlib accepted latest |
| normalized_latest | PARTIAL_READY | 2026-06-25 | normalized evidence，仍缺 DNG2 canonical contract |
| price_store_latest | PARTIAL_READY | 2026-06-17 | execution readiness bridge evidence，不是 canonical PriceStore |
| feature_store_latest | RESEARCH_ONLY | 2026-06-25 | experiment LTR feature pointer，不是 canonical FeatureStore |
| qlib_accepted_latest | PARTIAL_READY | 2026-06-17 | accepted pointer 独立停在 2026-06-17 |
| model_signal_latest | RESEARCH_ONLY | 2026-06-17 | experiment candidate 被降级 |
| readonly_bridge_latest | TEMPORARY_BRIDGE | 2026-05-07 | bridge 明确非 READY |
| readonly_snapshot_latest | READY | 2026-06-18 | 仅表示 pointer 存在；source data/signal asof 仍是 2026-06-17 |
| agent_prompt_latest | MISSING |  | 未从 readonly snapshot 推断 |
| temporary_research_bridge_latest | MISSING |  | 缺失显式写出 |

结论：latest concepts 完整，且没有合并成单一模糊 latest。

### 4.4 bridge / experiment / legacy / 缺证据降级

审查确认：

- bridge / readonly bridge / replay bridge / shadow readiness 多数为 `TEMPORARY_BRIDGE`。
- `data_tw/experiments/**` 和 demo/ops history 被标为 `RESEARCH_ONLY` 或 `TEMPORARY_BRIDGE`。
- `qlib_pipeline_option_c_daily_signal_runs` 被标为 `LEGACY_UNCATALOGED`，没有用 accepted pointer 冒充 canonical READY。
- 缺 manifest/schema/coverage/lineage 的 normalized、TWII、registry、readonly replay、full rank 等被降为 `PARTIAL_READY`。
- `agent_prompt_latest` 与 Agent artifact 层显式为 `MISSING`，未从 readonly snapshot 或 strategy context 推断。

结论：满足 DNG0 对 DNG1 的保守降级条件。

### 4.5 Forbidden action audit

`data_catalog.json` 与 `latest_status.json` 的 forbidden action audit 均为安全值：

- `real_data_fetch_triggered=false`
- `provider_refresh_triggered=false`
- `provider_publish_triggered=false`
- `qlib_accepted_latest_switched=false`
- `readonly_latest_published=false`
- `agent_prompt_published=false`
- `model_training_triggered=false`
- `model_inference_triggered=false`
- `strategy_replay_triggered=false`
- `broker_order_quick_trade_triggered=false`
- `target_position_or_weight_generated=false`

本轮审查未运行抓数、修复、训练、推理、回放、publish 或 latest switch。

## 5. 条件与风险

1. `readonly_snapshot_latest=READY` 只能解释为 latest pointer 文件存在且可被 catalog 识别；不能解释为 readonly publish gate 已授权，也不能替代 qlib accepted latest、Agent prompt latest 或 canonical data readiness。
2. `price_store_latest=PARTIAL_READY` 且 status_reason 明确指出当前只是 execution readiness bridge。DNG2 必须产出 canonical PriceStore，而不是继续沿用 YZ2/YZ2R bridge 作为默认策略输入。
3. `provider_raw_latest/normalized_latest=2026-06-25` 与 `qlib_accepted_latest=2026-06-17` 的不一致是已记录 governance gap。DNG2 不得通过切 accepted latest 来“修复”该不一致。
4. `feature_store_latest=RESEARCH_ONLY` 表明 2026-06-25 正交特征仍在 experiment 路径。DNG2/DNG3 前不得宣称 qlib+LTR 正交链路 canonical ready。
5. `agent_prompt_latest=MISSING` 是正确状态。DNG2 不得从 readonly snapshot 或 strategy context 反推 Agent prompt latest。

## 6. 是否足够进入 DNG2

足够进入 DNG2，但只能进入 DNG2 的 canonical PriceStore / TWII / Calendar 建设。

DNG1 已完成进入 DNG2 所需的最低治理前置：

- 当前数据层级和 latest 概念已机器可读；
- 关键 mismatch 已显式记录；
- bridge、experiment、legacy 与缺证据路径未伪装为 READY；
- validator 可重复运行；
- forbidden action audit 未发现越权。

## 7. DNG2 重点约束

DNG2 必须优先处理：

1. 建立 canonical `PriceStore`，覆盖 OHLCV、adjusted/unadjusted 口径、next-day execution availability、mark-to-market close coverage。
2. 将 TWII 从 normalized CSV evidence 收敛为 canonical `market_feature_store/twii_daily`，补 manifest/schema/coverage/lineage/validator。
3. 建立 market calendar 合同，明确最近交易日、下一交易日、holiday/no-data evidence。
4. 为 NormalizedStore、PriceStore、TWII/MarketFeatureStore、qlib provider view 补齐正式 manifest/schema/coverage/lineage。
5. 保持 qlib accepted latest、readonly latest、Agent prompt latest、production default latest 独立 gate，默认不切换。
6. 不得把 `data_tw/experiments/**`、YZ2/YZ2R execution readiness bridge、readonly bridge 或缺 evidence 路径作为新策略/模型默认输入。
7. DNG2 仍不得执行 provider publish、qlib accepted latest switch、readonly latest publish、Agent prompt latest publish、模型训练/推理、策略回放或交易动作，除非另有单独授权工作单。
