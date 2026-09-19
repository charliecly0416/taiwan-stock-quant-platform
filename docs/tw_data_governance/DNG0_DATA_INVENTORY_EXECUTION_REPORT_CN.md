# DNG0 数据现状盘点执行报告

生成日期：2026-06-29

## 1. 执行范围

本轮按 `DNG0_DATA_INVENTORY_WORK_CN.md` 做只读盘点，只读取本地文件、manifest、latest pointer、job.json、registry 和 modular contracts。未执行真实抓数、provider refresh/publish、accepted latest switch、readonly latest publish、Agent prompt latest publish、模型训练、模型推理、策略回放、broker/order/quick-trade、target_position/target_weight。

已生成：

- `data_tw/catalog/dng0_current_data_inventory.csv`
- `data_tw/catalog/dng0_latest_pointer_inventory.csv`
- `data_tw/catalog/dng0_route_dependency_sample.csv`

## 2. 已读取的关键合同

已确认以下合同边界：

- `DataSource`：只描述来源、asof、coverage 和边界；不抓取、不 publish、不切 accepted latest。
- `PriceStore`：标准价格层，不等于 provider latest，也不负责 accepted latest。
- `FeatureArtifact`：必须 PIT 安全，策略不得直接读取特征。
- `ModelSignalArtifact`：模型到策略的唯一标准信号接口，禁止训练、调参、publish/latest switch。
- `DailyOrchestrator`：只串接模块、收集 validator、写 RunRegistry，readonly latest pointer 也需 gate。
- `RunRegistry`：运行账本，只记录输入输出、validator 和 pointer 决策。

## 3. 主要发现

当前多层 latest 明确不一致：

- `provider_raw_latest / normalized_latest`：formal Option C qlib calendar 和 daily job inventory 显示到 `2026-06-25`。
- `qlib_accepted_latest`：`qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json` 停在 `2026-06-17`，状态为 `accepted`。
- `readonly_snapshot_latest`：`data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json` 指向 snapshot asof `2026-06-18`，但 `data_asof/signal_asof` 是 `2026-06-17`。
- `daily_auto_update`：`2026-06-29` 的 job 状态是 `today_data_window_wait`，`latest_before/latest_after` 均为 `2026-06-17`，未触发 FinMind/Yahoo/provider publish/latest signal update。
- `agent_prompt_latest`：扫描范围内未找到 `data_tw/artifacts/agent_daily_prompt/latest.json` 或 Agent prompt artifact 目录，应记为 `MISSING`，不能从 readonly snapshot 推断。

## 4. Canonical / Experiment / Temporary Bridge

较接近 canonical candidate 的路径：

- `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin`
- `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized`
- `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty`
- `data_tw/artifacts/signals/**`
- `data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17`

明确是 experiment 或 reference-only 的路径：

- `data_tw/experiments/**`
- `data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/**`
- `data_tw/experiments/option_c_daily_signal/latest_signal.json`

temporary bridge / readonly bridge 较多：

- `data_tw/artifacts/phase_yz/yz2r_execution_price_readiness/2026-06-17`
- `data_tw/artifacts/signals/top50_hold_rank_buffer_100_full_rank_visibility_bridge/mtrp2_r_20260628T181347Z`
- `data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/**`
- `data_tw/artifacts/replays/top50_hold_rank_buffer_100/mtrp3_same_window_replay_comparison`

这些路径不能被 DNG1 直接标成生产 READY；应保留其 readonly/research/bridge 属性。

## 5. 路线依赖样例

已抽样覆盖：

- strict E4 YZ product：依赖 Model A/Model B signal、YZ2 orthogonal feature、execution price readiness、readonly snapshot。
- Option C daily signal：provider calendar 到 `2026-06-25`，accepted signal 到 `2026-06-17`。
- `top50_exit_one_worst_sell`：依赖 `candidate_rank`、`buy_score`、`full_qlib_rank` 等 ModelSignal core fields。
- `top50_hold_rank_buffer_100`：要求 full rank 至少可见到 100，只有 top50 可见时必须 stop。
- Agent daily prompt：当前 latest pointer 缺失。

详见 `data_tw/catalog/dng0_route_dependency_sample.csv`。

## 6. Blocker

DNG0 本身无执行 blocker，产物已生成。

后续 DNG1/DNG2 的实际 blocker 是：当前没有统一 `data_catalog.json/latest_status.json/readiness_matrix`，历史目录缺少统一 manifest/schema/coverage/lineage，PriceStore 和 TWII 仍大量表现为 bridge 或 normalized CSV，而不是 canonical store。

## 7. 禁止动作确认

本轮未执行任何被禁止动作：

- 未真实抓数。
- 未 provider refresh/publish。
- 未切 qlib accepted latest。
- 未 publish readonly latest 或 Agent prompt latest。
- 未训练、推理、回放。
- 未触发 broker/order/quick-trade。
- 未生成 target_position/target_weight。
