# Phase V0 数据源合同与现状审计执行报告

生成时间：2026-06-17

对应主线文档：`docs/tw_modular_daily_update_productization/PHASEV_REAL_PROVIDER_DATA_READINESS_AND_AUTO_CHAIN_WORK_CN.md`

## 0. 执行结论

Phase V0 已完成“审计与合同冻结”第一步。本阶段只做读取、归纳和合同定义，不触发真实 Provider 抓取，不发布 Provider 数据，不切换 accepted latest，不写入 monitor，不触发 broker / quick-trade / orders，不改 Agent 行为。

V0 后续阶段的边界结论如下：

1. Phase V 必须新建真实数据就绪暂存链路，不能复用会直接发布或切换 latest 的历史入口作为默认入口。
2. Yahoo、FinMind、orthogonal 衍生特征必须先进入 staging run，再由 readiness validator 判定是否可供 V1/V2/V3 使用。
3. 任何 partial data、failed provider、validator failed、deadline missed 状态都不能进入 U 链已有 readonly snapshot / final accepted 展示链路。
4. V2 前端模型/策略切换只能复用已通过 readiness 的 staging artifacts，不能因为用户切换模型或策略而重新抓取 Provider。

## 1. V0 审计范围

本阶段审计对象：

| 类别 | 文件/目录 | V0 结论 |
| --- | --- | --- |
| Phase V 主线合同 | `docs/tw_modular_daily_update_productization/PHASEV_REAL_PROVIDER_DATA_READINESS_AND_AUTO_CHAIN_WORK_CN.md` | V0 目标是冻结数据源合同、暂存路径、模型/策略矩阵和禁用动作边界。 |
| 历史两小时自动脚本 | `scripts/run_daily_tw_stock_auto_update.py` | 具备真实更新和发布历史风险，Phase V 不应直接以该入口作为默认 staging 链路。 |
| U3 readonly 编排 | `scripts/run_tw_modular_daily_readonly_update.py` | 可作为 readonly snapshot / registry / report 编排参考，但 V0 不修改。 |
| Provider 更新脚本 | `backend/scripts/update_tw_stock_daily.py` | 覆盖 FinMind 日线、法人、融资融券、营收、估值等数据族；V0 不运行。 |
| 模型注册与 replay 政策 | `configs/tw_replay_window_policy.yaml`、`data_tw/artifacts/signals/*/r1_legacy_signal_adapter_20260616/manifest.json` | 已存在多模型信号清单，V 阶段需覆盖全部可选模型，不只覆盖默认模型。 |
| 策略注册 | `configs/tw_modular_registry.yaml`、`configs/strategy_dependencies/*.yaml` | 已存在生产型与诊断型策略依赖，V 阶段需显式区分。 |
| orthogonal O2 特征 | `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/` | 已有 PIT-safe available_at 审计产物，可作为 FinMind 衍生特征合同参考。 |
| 历史自动任务元数据 | `data_tw/ops/daily_auto_update/` | 已出现过 provider publish / latest signal update 的历史任务，证明 V 阶段需要隔离新 staging 链路。 |

## 2. 现有入口风险审计

### 2.1 历史两小时自动脚本

`scripts/run_daily_tw_stock_auto_update.py` 在 M3-safe gate 关闭时可进入安全模式，但历史运行元数据表明该入口曾触发真实更新链：

| run metadata | 风险字段 | 审计结论 |
| --- | --- | --- |
| `data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260617_20260617T103001Z/job.json` | `finmind_update_triggered=true`、`yahoo_refresh_triggered=true`、`provider_publish_triggered=true`、`latest_signal_updated=true` | 该入口不能作为 Phase V0/V1 默认数据就绪入口；后续必须创建 staging-only 链路并加 forbidden action audit。 |

### 2.2 U3 readonly 编排

`scripts/run_tw_modular_daily_readonly_update.py` 已将 daily snapshot / order intent / run registry / frontend acceptance 控制在 readonly 范围内。Phase V 可以复用其“只读报告、registry、状态解释”的产品化经验，但不能让 Provider partial data 直接流入 U3 输出。

### 2.3 FinMind 更新脚本

`backend/scripts/update_tw_stock_daily.py` 支持的数据族包括：

| 数据族 | Provider dataset | Phase V 用途 |
| --- | --- | --- |
| 日线价格 | `TaiwanStockPrice` | Yahoo 不可用或交叉验证时的价格来源候选。 |
| 除权息/公司行为 | FinMind corporate action 相关数据 | 价格调整、回放一致性、特征校验。 |
| 法人买卖超 | `TaiwanStockInstitutionalInvestorsBuySell` | orthogonal institutional flow 特征。 |
| 融资融券 | `TaiwanStockMarginPurchaseShortSale` | orthogonal margin/short 特征。 |
| 月营收 | FinMind monthly revenue | 可作为后续扩展特征，不列为 V1 最小必需。 |
| 估值 | FinMind valuation | 可作为后续扩展特征，不列为 V1 最小必需。 |

V0 未运行该脚本，未拉取 Provider，未写入 Provider 发布目录。

## 3. Phase V 数据日期合同

Phase V 后续每次真实数据 staging run 必须显式记录以下日期字段：

| 字段 | 含义 | 合同要求 |
| --- | --- | --- |
| `target_asof` | 本次希望生成的最新行情/特征 as-of 日期 | 必须是交易日或明确标记为非交易日无新数据。 |
| `decision_for` | 前端/分析展示面向的决策日期 | 通常为 `next_trading_day(target_asof)` 或业务指定日期。 |
| `decision_cutoff` | 允许进入决策视图的数据可用性截止时间 | 所有输入必须满足 `available_at <= decision_cutoff`。 |
| `available_at` | 单条数据真实可用时间 | 不得用 trade_date 伪装 available_at；orthogonal 特征必须保留延迟可用性。 |
| `source_trade_date` | Provider 原始交易日期 | 用于数据覆盖率和 PIT lineage 审计。 |
| `accepted_latest_before` | staging 前系统已接受 latest | 只读记录，V0/V1 不切换。 |
| `accepted_latest_after` | staging 后系统已接受 latest | 在 V0/V1 应与 before 相同，除非后续明确进入发布阶段并有单独审批合同。 |

硬性判定：

```text
required input is usable only if available_at <= decision_cutoff
partial provider data must stay in provider_staging and must not enter U-chain accepted artifacts
```

## 4. Provider 数据源合同

后续 V1 staging manifest 必须至少包含下表字段：

| 字段 | 说明 |
| --- | --- |
| `source_id` | 逻辑数据源 ID，例如 `yahoo_daily_price`。 |
| `provider` | `Yahoo`、`FinMind`、`DerivedOrthogonal` 等。 |
| `required` | 是否为本次模型/策略组合必需。 |
| `required_fields` | 字段级合同。 |
| `expected_asof` | 期望最新日期。 |
| `actual_latest_asof` | Provider 实际最新日期。 |
| `available_at` | 本源数据最晚可用时间。 |
| `coverage_count` | 符合日期与字段合同的标的数量。 |
| `coverage_ratio` | 覆盖率。 |
| `write_path` | staging-only 输出路径。 |
| `failure_reason` | 失败原因。 |
| `retryable` | 是否可自动重试。 |

### 4.1 最小数据源矩阵

| source_id | provider | required | required_fields | expected_asof | actual_latest_asof | available_at | coverage_count / ratio | write_path | failure_reason | retryable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `yahoo_daily_price` | Yahoo | 是，价格与行情基础 | `date`、`instrument`、`open`、`high`、`low`、`close`、`volume`、`adjusted_close` 或等价调整价 | V1 run 的 `target_asof` | V0 不拉取，待 V1 staging 填写 | V0 不拉取，待 V1 staging 填写 | V0 不拉取，待 V1 staging 填写 | `data_tw/artifacts/provider_staging/<run_id>/yahoo/` | V0 不适用 | 是 |
| `finmind_daily_price` | FinMind | 条件必需，用于补充/交叉验证 | `date`、`instrument`、`open`、`high`、`low`、`close`、`volume` | V1 run 的 `target_asof` | V0 不拉取，待 V1 staging 填写 | V0 不拉取，待 V1 staging 填写 | V0 不拉取，待 V1 staging 填写 | `data_tw/artifacts/provider_staging/<run_id>/finmind/daily_price/` | V0 不适用 | 是 |
| `finmind_institutional_flow` | FinMind | LTR orthogonal 必需 | `foreign_net_buy`、`investment_trust_net_buy`、`dealer_net_buy`、`institutional_total_net_buy`、rolling sums、streak、missing/delay flags | V1 run 的 `target_asof` 或最近可用交易日 | O2 现有 lineage 观测到 `trade_date_max=2026-06-10` | O2 现有 lineage 观测到 `available_at_max=2026-06-11` | O2 现有 summary 观测到 `symbol_count=150`；V1 需重算 coverage_ratio | `data_tw/artifacts/provider_staging/<run_id>/finmind/institutional_flow/` | V0 不适用 | 是 |
| `finmind_margin_short` | FinMind | LTR orthogonal 必需 | `margin_balance`、`margin_balance_change`、`short_balance`、`short_balance_change`、rolling sums、direction/divergence proxies、missing/delay flags | V1 run 的 `target_asof` 或最近可用交易日 | O2 现有 lineage 观测到 `trade_date_max=2026-06-10` | O2 现有 lineage 观测到 `available_at_max=2026-06-11` | O2 现有 summary 观测到 `symbol_count=150`；V1 需重算 coverage_ratio | `data_tw/artifacts/provider_staging/<run_id>/finmind/margin_short/` | V0 不适用 | 是 |
| `orthogonal_o2_features` | DerivedOrthogonal | LTR orthogonal 必需 | PIT-safe institutional/margin/short 衍生特征、`available_at`、lineage、missing flags | 基于 FinMind sources 的可用日期 | O2 现有 lineage 观测到 `trade_date_max=2026-06-10` | O2 现有 lineage 观测到 `available_at_max=2026-06-11` | O2 现有 summary 观测到 `symbol_count=150`；V1 需重算 coverage_ratio | `data_tw/artifacts/provider_staging/<run_id>/orthogonal/` | V0 不适用 | 源数据可重试，衍生构建可重跑 |
| `existing_signal_manifest` | LocalArtifacts | 是，用于模型选择与回放 | `model_id`、`signal_asof`、`available_at`、`candidate_rank`、`buy_score`、`full_qlib_rank` | 与模型合同一致 | V0 只审计现有 `r1_legacy_signal_adapter_20260616` manifests | V0 沿用 manifest 记录，V1 需统一落入 readiness manifest | 覆盖率由各模型 manifest/信号文件决定 | `data_tw/artifacts/provider_staging/<run_id>/model_signals/` | V0 不适用 | 否，信号生成失败需进入 validator_failed |

## 5. Staging 输出路径合同

Phase V 后续真实数据就绪链路只能写入以下 staging-only 路径：

```text
data_tw/artifacts/provider_staging/<run_id>/yahoo/
data_tw/artifacts/provider_staging/<run_id>/finmind/
data_tw/artifacts/provider_staging/<run_id>/orthogonal/
data_tw/artifacts/provider_staging/<run_id>/model_signals/
data_tw/artifacts/provider_staging/<run_id>/data_readiness_manifest.json
data_tw/artifacts/provider_staging/<run_id>/model_strategy_availability_matrix.json
data_tw/artifacts/provider_staging/<run_id>/forbidden_action_audit.json
```

禁止 V1/V2 在未通过 readiness gate 前写入：

```text
data_tw/ops/daily_auto_update/<accepted-or-production-run>/
data_tw/artifacts/signals/<model_id>/<production-adapter-or-latest>/
data_tw/accepted_latest*
backend_api_python monitor write paths
broker / quick-trade / orders paths
```

## 6. 模型可用性矩阵

Phase V 不能只支持默认 U3 模型。模型矩阵至少覆盖以下 selectable model：

| model_id | family | 当前来源 | V 阶段必需输入 | readiness 判定 |
| --- | --- | --- | --- | --- |
| `e4_frozen_qlib_2023_2025_ltr` | `ltr` | `data_tw/artifacts/signals/e4_frozen_qlib_2023_2025_ltr/r1_legacy_signal_adapter_20260616/manifest.json` | frozen qlib ranks、orthogonal LTR replay-ready scores、`candidate_rank`、`buy_score`、`full_qlib_rank`、`signal_asof`、`available_at` | 默认 U3 模型；必须同时通过 qlib signal 与 orthogonal available_at gate。 |
| `fresh_qlib_2025_ltr` | `ltr` | `data_tw/artifacts/signals/fresh_qlib_2025_ltr/r1_legacy_signal_adapter_20260616/manifest.json` | fresh qlib ranks、LTR rerank、orthogonal features、排名字段 | 需要 fresh qlib 与 orthogonal source 均 ready。 |
| `fresh_qlib_adaptive` | `qlib` | `data_tw/artifacts/signals/fresh_qlib_adaptive/r1_legacy_signal_adapter_20260616/manifest.json` | fresh qlib adaptive signal、排名与分数字段 | 不强制依赖 orthogonal，但必须通过 signal manifest/date/coverage gate。 |
| `frozen_qlib_2018_2022` | `qlib` | `data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json` | frozen baseline signal、排名与分数字段 | 作为冻结基线，可在 Provider 缺失时用于对照展示，但不得伪装成最新真实数据。 |
| `frozen_qlib_2025_ltr` | `ltr` | `data_tw/artifacts/signals/frozen_qlib_2025_ltr/r1_legacy_signal_adapter_20260616/manifest.json` | frozen qlib 2025 signal、LTR/orthogonal 相关字段 | 需要明确 signal_asof 与 available_at，不能越过 PIT gate。 |

默认组合继续冻结为：

```text
default_model_id = e4_frozen_qlib_2023_2025_ltr
default_strategy_rule_id = top50_exit_one_worst_sell
```

## 7. 策略可用性矩阵

| strategy_rule_id | 类型 | 关键依赖 | V 阶段处理 |
| --- | --- | --- | --- |
| `original` | 生产候选/基线 | `date`、`instrument`、`candidate_rank`、`buy_score`、`full_qlib_rank`、`signal_asof`、`available_at`、价格字段 | 纳入 availability matrix。 |
| `top50_exit_all` | 生产候选 | Top50 universe、ranking、当前持仓/候选、价格与费用假设 | 纳入 availability matrix。 |
| `top50_exit_one_worst_sell` | 默认生产候选 | Top50 universe、最弱持仓识别、候选排名、价格与费用假设 | 默认 U3 策略，必须完整验证。 |
| `one_sell_one_buy_correct` | 生产候选/修正版 | 一卖一买规则、候选排名、价格与费用假设 | 纳入 availability matrix。 |
| `one_sell_one_buy_buggy_e8r` | 诊断 | 历史 bug 复现依赖 | 只允许诊断，不得作为 V2 默认或生产展示默认。 |
| `sector_extension_analysis_smoke` | smoke/诊断 | sector 扩展字段 | 只用于 smoke，不参与生产 readiness。 |
| `dummy_new_strategy_dependency_smoke` | smoke/诊断 | 人工依赖 | 只用于依赖注册 smoke。 |

策略共同字段最低合同：

```text
date
instrument
candidate_rank
buy_score
full_qlib_rank
signal_asof
available_at
price fields required by execution-cost simulation
fee/slippage assumptions for readonly order-intent calculation
```

## 8. Readiness Gate 状态合同

V1/V2/V3 必须使用统一 gate status，不允许用自然语言散落判断：

| gate_status | 含义 | 可否进入 U 链 |
| --- | --- | --- |
| `all_required_ready` | 所有 required source、模型信号、策略依赖、available_at、coverage 均通过 | 可以进入后续 readonly analysis/display staging；是否发布仍需后续合同。 |
| `partial_data_pending` | 至少一个 required source 只有部分标的或部分字段 ready | 不可进入 U 链；保留在 provider_staging。 |
| `no_new_data` | Provider 正常返回但无新交易日数据 | 不可伪装为新 latest；可生成 no-new-data 解释报告。 |
| `provider_failed` | Yahoo/FinMind 等 Provider 请求失败或返回不可解析 | 不可进入 U 链；可按 retryable 自动重试。 |
| `validator_failed` | Provider 文件存在但字段、日期、coverage、available_at 或 PIT 审计失败 | 不可进入 U 链；需修复数据或合同。 |
| `deadline_missed_keep_previous_latest` | 到达业务截止时间仍未 all-ready | 保持 previous accepted latest；前端必须展示等待/延迟状态。 |

## 9. Forbidden Action Audit 合同

每个 Phase V staging run 必须生成：

```text
data_tw/artifacts/provider_staging/<run_id>/forbidden_action_audit.json
```

字段建议：

| 字段 | V0 冻结要求 |
| --- | --- |
| `provider_publish_triggered` | 必须为 `false`，除非进入未来单独批准的发布阶段。 |
| `accepted_latest_switched` | V0/V1/V2 默认必须为 `false`。 |
| `monitor_config_written` | 必须为 `false`。 |
| `monitor_scan_triggered` | 必须为 `false`。 |
| `alerts_written` | 必须为 `false`。 |
| `broker_connected` | 必须为 `false`。 |
| `quick_trade_triggered` | 必须为 `false`。 |
| `orders_created_or_sent` | 必须为 `false`。 |
| `agent_prompt_or_tool_modified` | 必须为 `false`，除非 Phase V 明确进入 Agent 产品化阶段并另立审计。 |

历史 job 中出现过 `provider_publish_triggered=true` 与 `latest_signal_updated=true`，因此 V1 新链路必须将 forbidden action audit 作为强制产物，而不是只依赖调用方约定。

## 10. V1 输入建议

V0 之后，V1 可以开始实现 staging-only 的真实 Provider readiness runner。V1 的最小交付应包括：

1. 新 runner 或新模式，只写 `data_tw/artifacts/provider_staging/<run_id>/`。
2. 读取 Yahoo / FinMind / orthogonal source，但在未 all-ready 前不写 U 链 accepted artifacts。
3. 输出 `data_readiness_manifest.json`。
4. 输出 `model_strategy_availability_matrix.json`，覆盖所有 selectable model 和 strategy。
5. 输出 `forbidden_action_audit.json`。
6. 对 `partial_data_pending`、`provider_failed`、`validator_failed`、`deadline_missed_keep_previous_latest` 给出机器可读状态。

V1 仍应避免修改历史生产入口，除非后续文档明确要求做兼容接入。

## 11. V0 修改文件

本阶段仅新增本文档：

```text
docs/tw_modular_daily_update_productization/PHASEV0_PROVIDER_DATA_CONTRACT_AUDIT_EXECUTION_REPORT_CN.md
```

未修改生产脚本，未运行 Provider 抓取，未发布数据，未切换 latest，未触发任何交易相关动作。
