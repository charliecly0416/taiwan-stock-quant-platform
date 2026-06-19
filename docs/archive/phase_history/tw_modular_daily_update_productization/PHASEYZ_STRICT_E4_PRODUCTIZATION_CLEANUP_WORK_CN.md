# Phase YZ：Strict E4 产品化收口与新模型/新策略前清理工作文档

生成时间：2026-06-18

本文件合并并取代：

- `docs/tw_modular_daily_update_productization/PHASEY_PREWORK_STRICT_E4_DATA_STAGING_CN.md`
- `docs/tw_modular_daily_update_productization/PHASEZ_PRE_NEW_MODEL_STRATEGY_CLEANUP_AUDIT_AND_REPAIR_WORK_CN.md`

## 1. 总结论

当前不能直接进入新模型、新策略开发。必须先完成一次产品化收口修复，把模型、策略、数据、日更、API、前端和回放窗口统一到干净链路。

最终产品化链路只保留一条统一数据流程、两个模型输出：

- 模型 A：`e4_frozen_qlib_2018_2022`
  - 含义：加载 E1 frozen qlib，使用 2018-01-01..2022-12-31 训练的 qlib，对当日 150 universe 打分。
- 模型 B：`e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025`
  - 含义：先使用同一个 E1 frozen qlib 得到 qlib top50，再加载 E3 orthogonal LTR，使用 2023-01-01..2025-12-31 训练的 LTR 对 qlib top50 重排序。

不再把 P3 / O4 / option_c fresh qlib / bridge / frozen fresh 2025 LTR 等中间实验模型放入默认产品化路径。它们可以保留为历史实验证据，但不得进入前端模型选择列表，也不得参与 daily default chain。

策略层同步收口：

- `origin/original` 淘汰，不得出现在前端/API 可选项。
- 明显效果弱、语义不清、只用于诊断的中间策略不得进入前端策略下拉框。
- `buggy_e8r` 暂时不淘汰，但只能作为 research_only 候选，必须中性命名，不能裸露 `buggy` 名称，不能默认推荐，不能作为有效策略优劣证据。
- 前端策略列表必须来自 clean strategy registry，不得从历史 replay artifact 自动扫描。

## 2. Phase Y 预处理证据：Strict E4 当前数据缺口

本轮已完成只读 staging 预处理，未训练模型、未抓外部数据、未切换 accepted latest、未改前端、未触发 monitor / broker / orders / quick-trade。

已生成 strict E4 qlib 当前日 staging：

- 输出目录：`data_tw/experiments/extended_oos_qlib_orthogonal_ltr/strict_e4_daily_prework/2026-06-17/`
- `strict_e4_e1_qlib_top150_snapshot_2026-06-17.csv`
- `strict_e4_e1_qlib_top50_snapshot_2026-06-17.csv`
- `strict_e4_prework_inventory_2026-06-17.json`

关键审计值：

- `signal_asof`: 2026-06-17
- `qlib_snapshot_rows`: 150
- `qlib_top50_rows`: 50
- `e1_top50_symbols_with_p3_feature`: 24
- `e1_top50_symbols_missing_p3_feature_count`: 26
- `ltr_staging_generated`: false

说明：strict E4 的 E1 qlib 当前日 150 打分可以本地跑通；当前阻塞不在 qlib，而在正交数据刷新范围。现有 P3/fresh daily LTR 正交特征只覆盖 P3/fresh top50，strict E4 top50 只有 24/50 重合，因此不能直接生成 strict E4 LTR top10。

strict E4 top50 当前缺少正交特征的股票：

`TW1560`, `TW1785`, `TW2327`, `TW2455`, `TW2481`, `TW2485`, `TW2486`, `TW3105`, `TW3131`, `TW3167`, `TW3363`, `TW3529`, `TW3665`, `TW4919`, `TW4971`, `TW4977`, `TW4991`, `TW5347`, `TW5439`, `TW6213`, `TW6223`, `TW6415`, `TW6781`, `TW6789`, `TW7769`, `TW8021`

## 3. 当前发现的偏离点

### 3.1 Registry 仍暴露旧模型和旧策略

文件：`configs/tw_modular_registry.yaml`

问题：

- `strategies` 仍注册 `original`、`top50_exit_all`、`top50_exit_one_worst_sell`、`one_sell_one_buy_correct`、`one_sell_one_buy_buggy_e8r`、smoke/template 策略。
- 历史实验策略仍可能被产品化链路消费。

修复要求：

- registry 必须分成 `production_selectable`、`research_only`、`deprecated`。
- 前端/API 只允许读取 `production_selectable`。
- `origin/original` 标为 deprecated 并从可选项移除。
- `buggy_e8r` 如保留，只能 research_only 且中性命名。

### 3.2 Replay matrix 仍是五模型五策略历史实验矩阵

文件：`configs/tw_modular_replay_matrix.yaml`

问题：

- 仍包含 `fresh_qlib_adaptive`、`fresh_qlib_2025_ltr`、`frozen_qlib_2025_ltr`、`e4_frozen_qlib_2023_2025_ltr`、`frozen_qlib_2018_2022`。
- 仍包含 `original` 等历史策略。

修复要求：

- 旧矩阵保留为 historical research matrix。
- 新增 clean production matrix，只包含两个 E4 模型和允许展示的策略。

### 3.3 Daily model signal builder/validator 硬编码旧模型和旧策略

文件：

- `scripts/build_tw_daily_model_signal_artifact.py`
- `scripts/validate_tw_daily_model_signal_artifact.py`

问题：

- 硬编码 `e4_frozen_qlib_2023_2025_ltr`。
- 硬编码 `top50_exit_one_worst_sell`。
- 默认 source 是历史 `r1_legacy_signal_adapter_20260616` artifact。
- 逻辑是从历史 signal artifact 按 asof 过滤，不是加载 E1/E3 当前推理。

修复要求：

- builder 改为 model adapter 驱动。
- 模型 A adapter 加载 E1 frozen qlib，对当日 150 universe 打分。
- 模型 B adapter 读取模型 A 输出，补 strict E4 top50 或 full150 正交特征，再加载 E3 LTR rerank。
- validator 读取 clean registry，不得只认旧 model_id。

### 3.4 Daily order intent builder 硬编码旧模型/策略

文件：`scripts/build_tw_daily_order_intent_artifact.py`

问题：

- 硬编码 `MODEL='e4_frozen_qlib_2023_2025_ltr'`。
- 硬编码 `RULE='top50_exit_one_worst_sell'`。

修复要求：

- builder 必须读取 clean strategy registry。
- 输入必须是 ModelSignalArtifact。
- 输出保持 readonly/not_order/not_target_position，不得接 broker/order/quick-trade。

### 3.5 Orthogonal readiness 仍绑定 P3 daily LTR artifact

文件：`scripts/pull_tw_provider_staging_data.py`

问题：

- `orthogonal_o2_features` readiness 读取 `data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_latest.json`。
- 该 artifact 是 P3/fresh qlib top50 范围，不是 strict E4 top50，也不是 full150。

修复要求：

- provider staging 不得再把 P3 daily LTR artifact 作为全局 orthogonal readiness。
- 必须新增模型无关 orthogonal feature package，优先 full150。
- 若暂时只做 scoped top50，manifest 必须写明 `scoped_model_id`，并且每个模型单独 refresh。
- readiness gate 必须证明两个产品化模型在同一 `signal_asof` 下可运行。

### 3.6 Real provider daily orchestrator 默认仍是旧模型/旧策略

文件：`scripts/run_tw_real_provider_daily_readonly_update.py`

问题：

- 默认 `--model-id e4_frozen_qlib_2023_2025_ltr`。
- 默认 `--strategy-rule-id top50_exit_one_worst_sell`。

修复要求：

- 默认与 clean registry 对齐。
- 用户切换模型/策略时不得重新抓 provider，只能重跑模型/策略/策略决策模块。

### 3.7 Replay window policy/API 仍允许旧模型和淘汰策略

文件：

- `configs/tw_replay_window_policy.yaml`
- `backend/app/services/readonly_replay_window.py`
- `backend/app/routes/readonly_replay_window.py`

问题：

- policy 仍注册 fresh/adaptive/bridge 相关模型。
- `VALID_RULES` 仍包含 `original`、`top50_exit_all` 等。
- API 默认仍是 `e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell`。

修复要求：

- 产品化 replay policy 只包含两个 E4 模型。
- `original` 移除或 deprecated 后拒绝。
- `buggy_e8r` 只能 research_only/diagnostic query，不能作为 valid strategy evidence。
- API 默认值必须来自 clean registry，不得硬编码旧模型。

### 3.8 前端仍硬编码旧默认模型/策略

文件：`frontend/src/views/tw-stock-monitor/index.vue`

问题：

- `readonlyReplayWindowForm.model_id` 默认是 `e4_frozen_qlib_2023_2025_ltr`。
- `readonlyReplayWindowForm.strategy_rule` 默认是 `top50_exit_one_worst_sell`。

修复要求：

- 前端模型/策略下拉框来自后端 clean registry API 或 filtered readonly index。
- 前端不得出现 `origin`、P3/O4/fresh/bridge 实验模型。
- `buggy` 如保留，必须中性显示且非默认。

### 3.9 Paper portfolio / simulation account 路线需对齐 clean registry

文件：

- `docs/tw_modular_daily_update_productization/PHASEX_PAPER_PORTFOLIO_STRATEGY_AND_SIMULATION_APP_FINAL_SUMMARY_CN.md`
- `backend/app/services/tw_stock_paper_portfolio.py`
- `frontend/src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue`

问题：

- Phase X paper portfolio 路线可以收尾，安全边界通过；允许写入范围仅限 `qd_tw_sim_*` 模拟账户表。
- 但 X 当前默认和 mock/E2E 仍绑定旧 `e4_frozen_qlib_2023_2025_ltr + top50_exit_one_worst_sell`。
- Paper portfolio 是前端用户会直接消费的策略应用端；如果继续硬编码旧模型/旧策略，会把 YZ 要淘汰的口径重新暴露给用户。

修复要求：

- paper portfolio panel 的模型与策略必须从 clean registry / latest clean decision artifact 读取，不得硬编码旧默认。
- `paper-portfolio/latest-decision` 返回的 decision 必须来自 YZ 后的产品化模型/策略，或明确返回 unavailable；不得 fallback 到旧 `e4_frozen_qlib_2023_2025_ltr`。
- apply/reset 仍保持 paper-only，仅影响模拟账户；不得扩展到 broker/order/quick-trade。
- deprecated 策略不得在 paper portfolio 中默认展示或应用。
- 若 research_only 策略可选，必须明确标识研究候选，且不能默认应用。

### 3.10 U 链仍有 demo/staging 痕迹

文件：

- `scripts/build_tw_daily_data_ingestion_artifact.py`
- `scripts/build_tw_daily_feature_artifact.py`
- `scripts/build_tw_daily_model_signal_artifact.py`
- `scripts/run_tw_modular_daily_readonly_update.py`

问题：

- feature artifact 是 `3d_demo_staging`，不是 E4/E3 所需完整特征。
- model signal 是从历史 signal artifact 过滤，不是加载 E1/E3 当前推理。

修复要求：

- U 链要么明确为 demo/staging，不得产品化；要么在本阶段替换为真实 strict E4 daily chain。

## 4. Phase YZ 执行计划

本阶段必须按 YZ0 -> YZ1 -> YZ2 -> YZ3 顺序执行。每一步执行完成后都要提交执行报告，审查通过后才能进入下一步。不得把 YZ1/YZ2/YZ3 合并执行，除非审查者明确批准；原因是本路线要先冻结 registry，再接模型，再接数据，再接前端/API，避免再次出现模型、数据、策略互相污染。

### Phase YZ0：Clean Registry、命名与候选收口

目标：先冻结产品化可选集合，明确哪些模型/策略能进前端/API，哪些只能作为历史研究证据，哪些淘汰。YZ0 不跑模型、不生成新日更信号、不改前端交互，只做 registry/policy/contract 收口。

必须检查的输入文件：

- `configs/tw_modular_registry.yaml`
- `configs/tw_modular_replay_matrix.yaml`
- `configs/tw_replay_window_policy.yaml`
- `configs/strategy_dependencies/*.yaml`
- `docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md`
- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/STRATEGY_DEPENDENCY_CONTRACT_CN.md`
- `docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md`
- `backend/app/services/readonly_replay_window.py`
- `backend/app/routes/readonly_replay_window.py`
- `frontend/src/views/tw-stock-monitor/index.vue`

允许修改范围：

- registry / policy / strategy dependency yaml。
- readonly replay policy 读取逻辑。
- 文档与 checklist。
- 只允许做“可选项收口”和“旧项标记”，不得实现模型推理、不得改 daily orchestrator、不得改 paper apply/reset 写路径。

必须实现的内容：

1. 定义 clean production model registry，只允许两个 production selectable 模型：
   - `e4_frozen_qlib_2018_2022`
   - `e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025`
2. 所有旧模型必须从 production selectable 中移除：
   - `e4_frozen_qlib_2023_2025_ltr`
   - `fresh_qlib_adaptive`
   - `fresh_qlib_2025_ltr`
   - `frozen_qlib_2025_ltr`
   - P3 / O4 / option_c / bridge / frozen fresh 2025 相关模型
3. 策略必须分层：
   - `production_selectable`
   - `research_only`
   - `deprecated`
4. `origin` / `original` 必须进入 deprecated，不得被 API/前端返回为可选项。
5. `buggy_e8r` 暂保留为 research_only，但必须改中性 display name，例如 `single_turnover_anomaly_research` 或中文“单换手异常候选（研究）”。不得在用户界面裸露 `buggy`。
6. `top50_exit_one_worst_sell` 是否作为 production selectable，需要执行者基于现有结论明确说明；如果保留，必须注明它是策略规则，不是模型默认，也不得绑定旧 `e4_frozen_qlib_2023_2025_ltr`。
7. 新增 clean production replay/model/strategy matrix。历史 `configs/tw_modular_replay_matrix.yaml` 可以保留，但必须标记为 historical research matrix，不能作为前端/API 选项来源。
8. 后端 replay window 不得维护硬编码 `VALID_RULES`，必须从 clean registry/policy 读取。
9. API 默认模型/策略不得写死旧值；如果没有 clean latest artifact，应返回 unavailable，而不是 fallback 旧 artifact。

必须输出：

- `docs/tw_modular_daily_update_productization/PHASEYZ0_CLEAN_REGISTRY_EXECUTION_REPORT_CN.md`
- clean registry/policy 文件路径与 diff 摘要。
- 一份 machine-readable registry audit，例如 `data_tw/artifacts/phase_yz/yz0_clean_registry_audit.json`，至少包含：
  - production model ids
  - production strategy ids
  - research_only strategy ids
  - deprecated strategy ids
  - old model ids removed from production
  - `origin/original` not production selectable
  - `buggy` raw name not frontend selectable

YZ0 放行 gate：

- production model 数量必须等于 2。
- production model id 必须精确等于上述两个 E4 id。
- `origin` / `original` 不得出现在 production selectable。
- P3/O4/fresh/bridge 相关 model id 不得出现在 production selectable。
- backend replay window strategy allowed list 不得硬编码旧全集。
- YZ0 不得生成任何新模型分数，不得改 latest pointer。

审查者 prompt：

请审查 `PHASEYZ0_CLEAN_REGISTRY_EXECUTION_REPORT_CN.md`。重点确认 clean registry 是否只允许两个 E4 production model；`origin/original` 是否 deprecated；buggy 是否 research_only 且中性命名；P3/O4/fresh/bridge 模型是否从 production selectable 移除；backend replay policy 是否从 registry 读取而不是硬编码旧 `VALID_RULES`；是否未跑模型、未改 latest、未触发 provider/monitor/broker/order。若任一不满足，停止，不允许进入 YZ1。

### Phase YZ1：Strict E4 Daily Model Adapters

目标：把 daily model signal 从“历史 artifact 过滤”改为“真实加载冻结模型推理”。YZ1 只解决模型 adapter 和 model signal artifact，不改 provider readiness，不改前端展示，不改 paper apply/reset。

必须检查的输入文件/产物：

- E1 qlib 模型：`data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/run/phasee1_frozen_qlib_model.pkl`
- E1 manifest：`data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_training_manifest.json`
- E3 LTR 模型：`data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_ltr_model.pkl`
- E3 manifest：`data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_training_manifest.json`
- E2 feature schema：`data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_feature_schema.csv`
- qlib provider：`qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin`
- YZ0 clean registry artifact。
- 现有问题脚本：
  - `scripts/build_tw_daily_model_signal_artifact.py`
  - `scripts/validate_tw_daily_model_signal_artifact.py`

允许修改范围：

- 新增 model adapter 脚本或改造 daily model signal builder。
- 改造 validator 为 registry-driven。
- 生成新的 daily ModelSignalArtifact staging。
- 不允许改前端，不允许改 paper apply/reset，不允许 provider publish/accepted latest。

必须实现的内容：

1. 模型 A adapter：
   - 输入：`signal_asof` 与 daily 150 universe/provider。
   - 加载 E1 frozen qlib，不训练、不调参。
   - 输出 150 行 qlib score，必须包含：`instrument`, `signal_asof`, `available_at`, `raw_score`, `score_rank`, `full_qlib_rank`, `candidate_rank`, `model_id`, `model_family`, `source_model_artifact`, `source_feature_artifact`。
   - `candidate_rank` 对 qlib top50 赋值，非 top50 可为空或用于 full-rank artifact，但 full_qlib_rank 必须覆盖 150。
2. 模型 B adapter：
   - 输入：模型 A 输出。
   - 只允许对模型 A 的 qlib top50 做 E3 LTR rerank。
   - 加载 E3 LTR，不训练、不调参。
   - 使用 E2 feature schema 78 列。
   - 输出 50 行 LTR rerank ModelSignalArtifact，必须保留原始 qlib rank/full_qlib_rank。
3. validator：
   - 从 YZ0 clean registry 读取允许 model_id。
   - 校验 model_id、schema、row_count、PIT、source_model_artifact、source_feature_artifact。
   - 不得硬编码 `e4_frozen_qlib_2023_2025_ltr`。
4. 对当前本地最新 asof 生成两个模型 artifact。
5. 如果模型 B 因正交特征覆盖不足不能生成，必须明确输出 blocked artifact，不能 fallback 到 P3/fresh/O4。

必须输出：

- `docs/tw_modular_daily_update_productization/PHASEYZ1_STRICT_E4_MODEL_ADAPTERS_EXECUTION_REPORT_CN.md`
- 模型 A ModelSignalArtifact manifest。
- 模型 B ModelSignalArtifact manifest，或 blocked manifest。
- validator 结果 JSON。
- row coverage audit：150 行 qlib / 50 行 LTR 或明确 blocked reason。

YZ1 放行 gate：

- 模型 A 必须 150/150 覆盖。
- 模型 A 必须来自 E1 frozen qlib，训练窗口 2018-2022。
- 模型 B 若生成，必须只使用 E1 qlib top50，不得使用 fresh/P3 top50。
- 模型 B 若 blocked，blocked reason 必须是正交数据覆盖不足等真实原因，不得 fallback。
- validator 不得硬编码旧 model_id。
- 未使用 option_c/fresh qlib 分数替代 E1 qlib。
- 未使用 O4 LTR 替代 E3 LTR。

审查者 prompt：

请审查 `PHASEYZ1_STRICT_E4_MODEL_ADAPTERS_EXECUTION_REPORT_CN.md`。重点确认模型 A 是否真实加载 E1 frozen qlib 并输出同 asof 150 行；模型 B 是否只对模型 A qlib top50 使用 E3 LTR rerank；validator 是否 registry-driven；是否没有使用 P3/fresh/O4；如果模型 B blocked，是否明确阻塞而非 fallback。若任一不满足，停止，不允许进入 YZ2。

### Phase YZ2：Orthogonal Data Package 解耦

目标：彻底修复正交数据覆盖范围被 P3/fresh top50 绑定的问题，使模型 B 可以按 strict E4 top50 或 full150 获取 PIT-safe 正交特征。

必须检查的输入文件/产物：

- YZ1 模型 A qlib top150/top50 artifact。
- `scripts/pull_tw_provider_staging_data.py`
- `scripts/build_p3rr_latest_orthogonal_features.py`
- `scripts/run_tw_ltr_p3_daily_rerank_readonly.py`
- `data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_latest.json`
- FinMind institutional/margin raw archive 或 PIT clean source。
- E2 feature schema。

允许修改范围：

- provider staging orthogonal readiness。
- orthogonal feature package builder。
- readiness matrix / data gate。
- 不允许改模型训练，不允许改前端，不允许 accepted latest。

必须实现的内容：

1. 移除 `daily_ltr_rerank_latest.json` 作为全局 orthogonal readiness 的依据。
2. 新增 model-neutral orthogonal feature package，优先覆盖 daily 150 universe。
3. 如 full150 暂不可行，允许 strict E4 scoped top50 package，但必须：
   - 输入来自 YZ1 模型 A qlib top50；
   - manifest 写明 `scoped_model_id=e4_frozen_qlib_2018_2022`；
   - 不得读取 P3/fresh top50；
   - 覆盖必须 50/50。
4. 正交特征必须满足 `available_at <= signal_asof`。
5. institutional_flow 和 margin_short 均要有 coverage/PIT audit。
6. 用新 orthogonal package 重新运行或完成模型 B artifact。

必须输出：

- `docs/tw_modular_daily_update_productization/PHASEYZ2_ORTHOGONAL_DATA_PACKAGE_EXECUTION_REPORT_CN.md`
- orthogonal feature package manifest。
- source freshness audit。
- PIT available_at audit。
- strict E4 top50 coverage audit，必须列出 50/50 或阻塞原因。
- 更新后的模型 B artifact manifest。

YZ2 放行 gate：

- 不再把 P3 `daily_ltr_rerank_latest.json` 当全局 readiness。
- strict E4 top50 正交覆盖必须 50/50，除非明确 blocked 并停止。
- `available_at <= signal_asof` 违规数必须为 0。
- feature schema 78 列对齐必须通过。
- 模型 B 能生成 LTR rerank artifact。
- 无 future label / future return / realized PnL。

审查者 prompt：

请审查 `PHASEYZ2_ORTHOGONAL_DATA_PACKAGE_EXECUTION_REPORT_CN.md`。重点确认 orthogonal readiness 是否彻底脱离 P3/fresh daily_ltr_rerank；strict E4 top50 正交覆盖是否 50/50；available_at 是否无未来；模型 B 是否用 E3 LTR 对 E1 qlib top50 rerank；是否没有 future label/return/PnL。若覆盖不足或仍依赖 P3 artifact，停止，不允许进入 YZ3。

### Phase YZ3：Daily Orchestrator、API、Replay、Frontend、Paper Portfolio 收口验收

目标：把 YZ0-YZ2 的 clean registry 和两个模型 artifact 接入日更、API、回放、前端和 paper portfolio，形成用户可见的干净产品化链路。

必须检查的输入文件/产物：

- YZ0 clean registry。
- YZ1/YZ2 两个模型 artifact。
- `scripts/run_tw_real_provider_daily_readonly_update.py`
- `scripts/run_tw_modular_daily_readonly_update.py`
- `scripts/build_tw_daily_order_intent_artifact.py`
- `scripts/validate_tw_daily_order_intent_artifact.py`
- `backend/app/services/readonly_daily_update.py`
- `backend/app/services/readonly_replay_window.py`
- `backend/app/services/tw_stock_paper_portfolio.py`
- `backend/app/routes/tw_stock.py`
- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue`
- frontend E2E tests。

允许修改范围：

- daily orchestrator 和 readonly latest/pointer 逻辑。
- order intent builder/validator。
- replay window API/policy。
- paper portfolio latest decision 消费端。
- frontend 模型/策略选择与展示。
- E2E/单元测试。

必须实现的内容：

1. daily orchestrator 默认读取 clean registry。
2. 自动日更默认可跑产品化默认模型；用户切换模型/策略时，不重新抓 provider，只重跑模型/策略/decision。
3. order intent builder 不得硬编码旧模型/策略。
4. replay window/query 只允许 clean registry 中的 production selectable；research_only 需要显式标识且不作为默认。
5. paper portfolio latest decision 必须来自 YZ clean decision artifact；不得 fallback 到旧 `e4_frozen_qlib_2023_2025_ltr`。
6. 前端模型下拉只展示两个 E4 模型。
7. 前端策略下拉不展示 `origin/original`。
8. 前端不展示 P3/O4/fresh/bridge 作为产品化模型。
9. `buggy_e8r` 若展示，必须中性名称、research_only、非默认。
10. 所有前端 apply/reset 仍是 paper-only，写入仅限模拟账户。

必须输出：

- `docs/tw_modular_daily_update_productization/PHASEYZ3_PRODUCTIZATION_E2E_EXECUTION_REPORT_CN.md`
- frontend/API payload audit。
- readonly latest artifact。
- paper portfolio latest decision audit。
- replay window policy audit。
- network audit，至少包含：
  - forbidden_request_count
  - broker_request_count
  - quick_trade_request_count
  - provider_publish_refresh_count
  - accepted_latest_switch_count
  - monitor_config_write_count
  - monitor_scan_post_count
  - monitor_alerts_write_count
  - target_position_write_count
  - allowed_paper_apply_post_count
  - allowed_paper_reset_post_count
- console audit。
- 截图或 E2E artifact 路径。

YZ3 放行 gate：

- 前端/API 不出现 `origin/original` 可选项。
- 前端/API 不出现 P3/O4/fresh/bridge 产品化模型。
- 两个 E4 模型同 asof 可展示，或其中一个明确 unavailable 且不 fallback。
- replay window 不允许训练窗口。
- paper portfolio 不硬编码旧模型/旧策略。
- forbidden network counts 为 0；paper apply/reset 是唯一允许写入，且只写模拟账户。
- 不触发 provider publish / accepted latest / monitor / broker / orders / quick-trade。

审查者 prompt：

请审查 `PHASEYZ3_PRODUCTIZATION_E2E_EXECUTION_REPORT_CN.md`。必须自己检查真实 API payload 或 E2E artifact，不能只信报告。重点确认前端/API/paper portfolio/replay window/daily latest 均只暴露 clean registry 允许项；`origin/original` 不出现；旧 P3/O4/fresh/bridge 不出现；paper portfolio 不再硬编码旧 `e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell`；network audit 无 forbidden writes；paper apply/reset 仍只写模拟账户。若任一不满足，停止，不能进入新模型/新策略开发。

## 5. 禁止事项

执行者不得：

- 不得重训 E1 qlib 或 E3 LTR。
- 不得使用 fresh qlib / option_c qlib 分数替代 E1 qlib 分数。
- 不得使用 O4 LTR 替代 E3 LTR。
- 不得把 P3 / fresh top50 的正交特征范围当成 strict E4 范围。
- 不得把 P3 / O4 / option_c fresh / bridge 实验模型加入前端产品化模型列表。
- 不得新增第三个默认候选模型，除非另开主线并重新做控制变量审查。
- 不得把 `origin/original` 或其他已淘汰历史策略加入前端策略列表。
- 不得因为 `buggy_e8r` 暂时保留，就把它命名为默认策略或未经解释地展示为推荐策略。
- 不得触发 provider publish / accepted latest switch / monitor / broker / orders / quick-trade。

## 6. 执行者 Prompt

请按 `docs/tw_modular_daily_update_productization/PHASEYZ_STRICT_E4_PRODUCTIZATION_CLEANUP_WORK_CN.md` 执行 Phase YZ0-YZ3。目标是在开发新模型/新策略前，完成 strict E4 产品化收口：registry/replay policy/frontend/API 不再暴露旧 P3/O4/fresh/bridge 模型和 `origin/original` 策略；daily model signal/order intent/paper portfolio 不再硬编码旧 `e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell`；orthogonal readiness 不再读取 P3 `daily_ltr_rerank_latest.json` 作为全局证据；实现两个产品化 E4 模型同 asof、同 150 universe、PIT-safe 的真实 daily artifact。不得重训模型、不得改 provider accepted latest、不得触发 monitor/broker/order/quick-trade。完成后提交 Phase YZ 执行报告、artifact 清单、E2E 证据和禁用项审计。

## 7. 审查者 Prompt

请审查执行者基于 `docs/tw_modular_daily_update_productization/PHASEYZ_STRICT_E4_PRODUCTIZATION_CLEANUP_WORK_CN.md` 的 Phase YZ 执行报告。重点确认：产品化 registry 是否只保留两个 E4 模型；`origin/original` 是否从前端/API 可选项移除；buggy 是否仅 research_only 且中性命名；daily chain 是否真实加载 E1 qlib/E3 LTR 而非历史 signal artifact；orthogonal feature 是否 model-neutral full150 或 strict E4 scoped 且覆盖 50/50；是否没有 P3/O4/fresh/bridge 混入；前端和 paper portfolio 是否无旧默认硬编码；readonly/paper-only 安全边界是否仍然成立。若有任一项不满足，停止并要求修复，不允许进入新模型/新策略开发。
