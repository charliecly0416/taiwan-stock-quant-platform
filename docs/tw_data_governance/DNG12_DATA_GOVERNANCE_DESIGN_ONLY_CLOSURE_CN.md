# DNG12 Data Governance Design-Only Closure

生成日期：2026-06-29

## 1. 结论

本轮 DNG0-DNG11 已完成“数据规范化主线”的单日设计闭环：

```text
raw/normalized/catalog
-> canonical PriceStore / TWII / OrthogonalFeatureStore
-> route dependency gate
-> qlib Model A 2026-06-25 score
-> Model B LTR blocker
-> StrategyInputBundle
-> readonly / Agent source context dry-run
-> daily auto dashboard / model_signal_gate
```

但本轮不是 production Go：

```text
production_go=false
multi_day_observation_ready=false
observed_trade_day_count=1
required_additional_trade_days=4
model_b_ltr_ready=false
readonly_latest_published=false
agent_prompt_latest_published=false
accepted_latest_switched=false
replay_shadow_execution_ready=false
```

当前可以宣布：

```text
PASS_SINGLE_DAY_CHAIN_DESIGN_CLOSED
```

不能宣布：

```text
PASS_PRODUCTION_READY
PASS_MULTI_DAY_OBSERVATION
PASS_MODEL_B_LTR_READY
PASS_REPLAY_SHADOW_READY
```

## 2. 阶段结论

| 阶段 | 结论 | 说明 |
| --- | --- | --- |
| DNG0 | `PASS_WITH_CONDITIONS_GO_DNG1` | 完成现状盘点，确认 provider/normalized 到 2026-06-25，但 qlib accepted latest 仍 2026-06-17。 |
| DNG1 | `PASS_WITH_CONDITIONS_GO_DNG2` | 建立 DataCatalog / latest_status；bridge/experiment/legacy 未伪装 READY。 |
| DNG2 | `FAIL_NEEDS_DNG2_REPAIR` | 初版 PriceStore/TWII 被 TWII 覆盖阻断。 |
| DNG2_R | `PASS_WITH_CONDITIONS_GO_DNG3` | 用既有 isolated TWII bridge 修复到 2026-06-25，标记 `PARTIAL_READY_WITH_DECLARED_GAP`。 |
| DNG3 | `PASS_WITH_CONDITIONS_GO_DNG4` | institutional/margin 已 canonical long-form；corporate_actions/monthly_revenue/valuation 仍阻断 Model B。 |
| DNG4 | `PASS_WITH_CONDITIONS_GO_DNG5` | 建立 StrategyInputBundle / ReplayInputBundle builder；状态 partial，未生成回放结果。 |
| DNG5 | `PASS_WITH_CONDITIONS_GO_DNG6` | 建立 RouteDataDependencyContract；qlib+LTR 示例被正确 BLOCK。 |
| DNG6 | `PASS_WITH_CONDITIONS_GO_DNG7` | 建立 daily readiness dashboard；发现 M3 静态误报。 |
| DNG6_R | `PASS_GO_DNG7` | 修复 static audit false positive；M3 validator 恢复通过。 |
| DNG7 | `PASS_GO_DNG8` | 真正生成 2026-06-25 qlib Model A score，未切 latest。 |
| DNG8 | `PASS_WITH_CONDITIONS_GO_DNG9` | 正确阻断 Model B LTR；未生成 fake LTR signal。 |
| DNG9 | `PASS_WITH_CONDITIONS_GO_DNG10` | 接入 daily auto model_signal_gate，默认关闭。 |
| DNG10 | `PASS_WITH_CONDITIONS_GO_DNG11` | 建立 StrategyInputBundle refresh、readonly/Agent source context dry-run；未 publish latest。 |
| DNG11 | `PASS_SINGLE_DAY_CHAIN_GO_DNG12_DESIGN_ONLY` | 单日链路 ready；多日观察仍需 4 个交易日。 |

## 3. 已完成能力

### 3.1 Catalog / Readiness

已建立：

```text
scripts/build_tw_data_catalog.py
scripts/validate_tw_data_catalog.py
data_tw/catalog/data_catalog.json
data_tw/catalog/latest_status.json
data_tw/catalog/daily_readiness_dashboard.json
```

效果：

- 能区分 provider raw、normalized、PriceStore、qlib accepted、model signal、readonly snapshot、Agent prompt 等 latest。
- 能明确当前 provider/normalized 与 qlib accepted latest 不一致。
- 能阻止 experiment/bridge/legacy 路径被误标为 canonical READY。

### 3.2 Canonical 基础层

已建立：

```text
data_tw/canonical/price_store/tw_equity_daily/dng2_r_price_market_calendar_20260625/
data_tw/canonical/market_feature_store/twii_daily/dng2_r_price_market_calendar_20260625/
```

状态：

```text
PriceStore=PARTIAL_READY
TWII=PARTIAL_READY_WITH_DECLARED_GAP
can_continue_to_model_score=true
can_continue_to_dng3=true
can_continue_to_replay=false
can_continue_to_shadow_execution=false
```

说明：TWII 使用本地既有 isolated bridge，不是 formal source，因此不能用于 production Go 声明。

### 3.3 正交数据层

已建立：

```text
data_tw/canonical/orthogonal_feature_store/daily_orthogonal/dng3_orthogonal_feature_store_20260625/
```

状态：

```text
institutional_flow=canonical long-form
margin_short=canonical long-form
corporate_actions=not daily feature ready
monthly_revenue=BLOCKED_QUOTA
valuation=BLOCKED_QUOTA
model_b_ltr_ready=false
```

### 3.4 Route Dependency Gate

已建立：

```text
docs/tw_data_governance/ROUTE_DATA_DEPENDENCY_CONTRACT_TEMPLATE_CN.md
scripts/validate_tw_route_data_dependency.py
```

示例结果：

```text
qlib_only_model_score_20260625=PARTIAL
qlib_ltr_model_b_20260625=BLOCK
strategy_input_bundle_20260625=PARTIAL
```

效果：后续路线不能绕过 catalog/readiness，也不能把 qlib-only fallback 冒充 full LTR。

### 3.5 Model A Score

已建立：

```text
data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022/dng7_modela_20260625/
data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022/dng7_modela_20260625/
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng7_modela_20260625/
```

状态：

```text
mode=TRUE_LOCAL_INFERENCE
status=SCORED_ASOF_TARGET
signal_asof=2026-06-25
row_count=150
accepted_latest_switched=false
```

这是本轮最关键闭环：证明每天新数据后，至少 qlib Model A score 可以通过标准 pipeline 补生成。

### 3.6 Model B LTR Blocker

已建立：

```text
data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/dng8_modelb_ltr_20260625/
data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/dng8_modelb_ltr_20260625/
```

状态：

```text
score_status=BLOCKED_INPUT_NOT_READY
model_b_ltr_ready=false
fallback_allowed=qlib_only_if_strategy_contract_allows
fake_ltr_signal_detected=false
```

阻断项：

```text
corporate_actions
monthly_revenue
valuation
```

### 3.7 Daily Auto Gate

已接入：

```text
--enable-data-catalog-dashboard
TW_DAILY_AUTO_ENABLE_DATA_CATALOG_DASHBOARD=true
--enable-model-signal-gate
TW_DAILY_AUTO_ENABLE_MODEL_SIGNAL_GATE=true
```

默认状态：

```text
data_catalog_dashboard_gate=false
model_signal_gate=false
publish_latest_gate=false
accepted_latest_switch=false
```

说明：DNG9 只接入显式 gate，未运行真实 daily auto，未打开默认自动 score。

### 3.8 Downstream Source Context

已建立：

```text
data_tw/artifacts/strategy_input_bundles/top50_exit_one_worst_sell_dng10_modela/dng10_strategy_input_bundle_20260625/
data_tw/artifacts/readonly_source_context/dng10_modela_20260625/
data_tw/artifacts/agent_daily_prompt_source_context/dng10_modela_20260625/
```

状态：

```text
signal_asof=2026-06-25
model_a_ready=true
model_b_ltr_ready=false
fallback_model=qlib_only_model_a
latest_pointer_updated=false
readonly_latest_updated=false
agent_prompt_latest_updated=false
```

## 4. 未完成 blocker

| Blocker | 当前状态 | 后续动作 |
| --- | --- | --- |
| multi-day observation | 仅 1 个交易日 | 还需 4 个交易日 DNG7-DNG10 级别证据 |
| daily auto productionization | 未完成 | 需要 DNG13 把每日抓数后自动推进 canonical / score / strategy / readonly source context，并记录 skipped_asof_ledger |
| 2026-06-26 lineage gap | raw/ops 有证据，但正式 qlib calendar / Model A score 未推进 | 必须在 DNG13 中作为验收样例，说明 blocked_at=qlib_provider_view_or_formal_calendar |
| Model B LTR | blocked | 修复 corporate_actions/monthly_revenue/valuation 可用性和 PIT 特征 |
| formal qlib accepted latest | 仍旧 | 单独授权 formal refresh / accepted latest route |
| readonly latest publish | 未授权 | 单独 readonly publish gate |
| Agent prompt latest | missing / 未 publish | 单独 Agent prompt artifact publish gate |
| replay / shadow execution | 未 ready | 需要 next-day execution price 和 ReplayInputBundle ready |
| production Go | 未达标 | 等 multi-day observation + blocker burn-down |

## 5. Production Go/No-Go 条件

未来要从 design-only closure 进入 production Go/No-Go，至少必须满足：

1. 连续或等价累计 5 个交易日完成 DNG7-DNG10 级别链路。
2. 每日 dashboard 能解释 raw/normalized/PriceStore/FeatureStore/ModelSignal/Bundle 状态。
3. Model A 每日 score 自动补生成稳定。
4. Model B LTR 要么解除 blocker 并生成真实 LTR signal，要么产品明确降级为 qlib-only。
5. readonly/Agent latest publish gate 单独通过。
6. replay/shadow execution 的 next-day execution availability 单独通过。
7. M3 daily orchestrator validator 持续通过。
8. 无 provider publish、accepted latest switch、broker/order、target_position/target_weight 越权。

## 6. 禁止动作审计

本轮 DNG0-DNG12 未授权、未执行：

```text
provider refresh / publish
qlib accepted latest switch
readonly latest publish
Agent prompt latest publish
模型训练
模型调参
策略收益回放
ReplayResult/NAV
broker/order/quick-trade
target_position
target_weight
```

## 7. 统筹建议

当前建议收尾方式：

```text
close_current_dng_design_only_route=true
next_route=DNG13_DAILY_AUTO_PRODUCTIONIZATION_CONTRACT
```

优先级：

1. 先把 daily auto 改成抓数后自动推进 canonical / score / strategy / readonly source context，并输出 daily_chain_status 与 skipped_asof_ledger。
2. 用 `2026-06-26` 作为验收样例，证明 raw 已有但 score 未生成时，系统能明确解释断在 formal qlib calendar / qlib provider view。
3. DNG13 通过后，再累计至少 4 个额外交易日或等价 backfill/shadow 样本。
4. 并行规划正交数据 source repair，解除 Model B LTR blocker。
5. 不要现在 publish latest 或切 production default。

## 8. DNG13 入口说明

下一步不是继续手动补单日 score，而是进入：

```text
DNG13_DAILY_AUTO_PRODUCTIONIZATION_CONTRACT
```

DNG13 要求每日自动流程在抓到数据后自动尝试推进：

```text
raw / normalized
-> canonical PriceStore / MarketFeatureStore / OrthogonalFeatureStore
-> qlib provider view candidate
-> ModelInferenceInput / ScoreJob / ModelSignalArtifact
-> StrategyInputBundle / readonly source context
-> latest_status / daily_readiness_dashboard / skipped_asof_ledger
```

如果某天不能生成 score，例如 `2026-06-26`，必须在机器可读 ledger 中写清楚：

```text
raw ready
formal qlib calendar not advanced
qlib provider view not ready
model_a_score blocked
```

而不是让执行者或用户事后人工猜测“26 号到哪去了”。

当前阶段最重要的成果是：项目已经不再只是“知道数据乱”，而是有了可执行的 catalog、readiness、canonical store、score job、bundle、daily gate 和 blocker 账本。后续卡在哪里，应能从 dashboard 和 readiness 直接定位，而不是每条研究线临时补数据。
