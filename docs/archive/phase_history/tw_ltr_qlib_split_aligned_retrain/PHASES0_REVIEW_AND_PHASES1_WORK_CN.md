# Phase S0 审查意见与 Phase S1 工作文档

生成日期：2026-06-14

## 1. 审查范围

主线依据：`docs/TW_STOCK_LTR_QLIB_SPLIT_ALIGNED_AND_FRESH_RETRAIN_MAINLINE_CN.md`

审查入口：`docs/tw_ltr_qlib_split_aligned_retrain/PHASES0_EXECUTION_REPORT_CN.md`

用户输入中的 `ocs/tw_ltr_qlib_split_aligned_retrain/PHASES0_EXECUTION_REPORT_CN.md` 视为路径笔误，实际审查 `docs/...`。

本轮只审查 Phase S0 是否完成证据冻结与实验合同冻结，不审查任何新训练结果，因为 S0 禁止训练、调参、回放、前端/API、provider/accepted latest/monitor/交易链路。

## 2. 审查结论

结论：`通过，允许进入 Phase S1，但 S1 必须先做旧窗口 qlib score/rank 覆盖与生成口径诊断，再进行训练。`

Gate：

```text
phase_s0_pass_request_phase_s1_split_aligned_fair_validation
```

通过理由：

1. S0 正确冻结了 qlib Option C frozen baseline 的 recorder、model、config 与 split。
2. S0 正确冻结了当前 LTR Phase1C 的 split、feature、label、score 产物与 forbidden feature 审计。
3. S0 明确承认当前 LTR train 为 `2022-01-10..2024-08-09`，qlib train 为 `2015-05-04..2020-12-31`，两者不能直接比较。
4. S0 没有新增策略族、正交数据源、provider、前端/API 或交易链路。
5. S1/S2 合同明确要求：S1 先做旧窗口公平验证；只有 S1 支持 LTR 方法时，S2 才能进入新鲜 qlib + LTR 重训。

## 3. 关键证据核验

### 3.1 qlib Option C frozen baseline

已核验：`qlib_pipeline/data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260610_20260610T183814Z/run_metadata.json`

关键字段成立：

- `frozen_recorder = 950741cfd5f14ee5a05464fec3e12e0a`
- `model_path = mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a/artifacts/params.pkl`
- `config = configs/tw_yahoo_primary_alpha158.yaml`
- `model_retraining_performed = false`
- `model_tuning_performed = false`
- `refresh_triggered = false`
- `publish_triggered = false`
- `provider_mutation_triggered = false`
- `paper_trading_started = false`
- `live_trading_started = false`
- `target_trades_generated = false`
- `executable_orders_generated = false`

已核验：`qlib_pipeline/configs/tw_yahoo_primary_alpha158.yaml`

split 成立：

- train：`2015-05-04..2020-12-31`
- valid：`2021-01-01..2022-12-31`
- test：`2023-01-01..2025-06-30`

已核验 universe 行数：

- `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/universe/tw_liquid_dyn.txt` 为 `3126` 行。

### 3.2 当前 LTR Phase1C

已核验：

- `phase1_ltr_samples.csv` 为 `159994` 行含表头。
- `phase3a0_frozen_phase1c_row_scores.csv` 为 `152250` 行含表头。
- `phase1_split_summary.json` 的完整样本 split counts：train `90301`、validation `30877`、independent_test `31071`。
- `phase1_input_feature_list.json` 记录 `34` 个 input features，包含 qlib score/rank、技术/流动性和市场状态字段。
- `phase1_label_audit_summary.json` 记录 future label 仅用于 label/audit，不进入 input features。
- `phase3a0_score_schema.json` 与 `phase3a0_gate_summary.json` 记录 `forbidden_feature_hits = []`，且无 provider refresh/publish、accepted latest、frontend/API、monitor/trading。

### 3.3 forbidden feature 审计

已核验：`phase0_forbidden_feature_audit.csv`

以下字段均为 `found_in_phase0_input_features=false`：

- `institutional_net_buy`
- `margin_balance`
- `short_balance`
- `monthly_revenue_yoy_mom`
- `valuation_PER_PBR`
- `any_field_without_available_at_or_announcement_date`

## 4. Findings

### High

无。

### Medium

无阻断项，但 S1 存在一个必须前置解决的问题：当前 LTR 使用 qlib score/rank 作为输入，旧窗口 `2015-05-04..2020-12-31` 训练期是否已有可用、同口径、无 test 反馈的 qlib score/rank 尚未在 S0 中证明。

处理方式：不叫停 S0；在 S1 工作中把第一步设为 `S1A qlib score/rank coverage and generation policy diagnosis`。若旧窗口 qlib score/rank 缺失或只能通过不公平方式生成，S1 必须停止并返回 `split_aligned_data_insufficient` 或提交用户确认。

### Low

S0 报告中的 `qlib / Top50 adaptive` 表述需要在 S1 中拆清：

- qlib model score 本身；
- Top50 adaptive 日频组合 replay；
- rank_rotate_top50 / top30 规则 baseline。

避免后续把 qlib 模型效果与 Top50 组合规则混成一个不可解释 baseline。

## 5. 台股只读安全边界审查

### Findings

未发现真实 broker、quick-trade、order、target-position、target-weight、monitor write、provider publish/refresh、accepted latest switching。

### Network Audit

S0 未提供 network audit，且 S0 不涉及前端/API/E2E。按主线，S1 也不应触发前端/API 或 network audit；若 S1 只做本地训练/回放，可以不要求 E2E。

### Text / Agent Semantics

报告中出现“训练”“调参”“买卖”“仓位”“收益”等词，均用于禁止事项、历史回放指标或 label/策略合同，不构成真实交易建议或收益承诺。

### Verdict

只读安全边界通过。

## 6. Phase S1 工作文档：旧窗口 Split-Aligned 公平验证

### 6.1 S1 目标

回答唯一问题：

```text
在 qlib Option C 同样旧训练窗口下，LTR rerank 方法本身是否相对 qlib / Top50 baseline 有稳定增益？
```

S1 不是上线，不是默认策略决策，不是新鲜模型重训，不是前端/API 工作。

### 6.2 S1 固定 split

默认使用：

| split | 日期区间 | 用途 |
| --- | --- | --- |
| train | `2015-05-04..2020-12-31` | 训练 LTR split-aligned 模型 |
| validation | `2021-01-01..2022-12-31` | 模型选择与固定参数选择 |
| test | `2023-01-01..2025-06-30` | 最终评估，只能使用一次性冻结结果解释 |

不得静默缩短窗口。若数据不足，必须输出缺口表并停止给出 gate。

### 6.3 S1A：先做 qlib score/rank 覆盖与生成口径诊断

执行者必须先完成 S1A，只读诊断，不训练。

必须回答：

1. `2015-05-04..2025-06-30` 每个目标日期是否存在 qlib score/rank，可覆盖 LTR train/validation/test。
2. qlib score/rank 来源是什么：既有 frozen pred、历史 backfill、还是需要重建。
3. 若需要重建，是否只使用 qlib S1 train/validation 允许的信息，不得用 test 反馈调模型。
4. 对 LTR train 期的 qlib score/rank，是否采用 in-sample qlib score、walk-forward/cross-fit score，或报告不可得；执行者不得自行选择会影响公平性的方案，必须在报告中说明并等待审查确认。
5. 输出 coverage 表：按 split、date、symbol 统计 missing score、missing rank、missing price、missing label、missing feature。

S1A 交付物建议：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1/phase_s1a_qlib_score_rank_coverage.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1/phase_s1a_generation_policy_options.json
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1A_SCORE_RANK_COVERAGE_REPORT_CN.md
```

如果 S1A 发现 qlib score/rank 无法公平覆盖旧窗口，执行者必须停止，报告：

```text
split_aligned_data_insufficient
```

### 6.4 S1B：样本构建与 leakage scan

只有 S1A 通过后，才允许构建 S1 训练样本。

要求：

- feature 只能从当前 LTR whitelist 出发；
- 不新增法人、融资融券、月营收、估值、provider、新数据源；
- future 字段只允许作为 label/audit；
- 必须重新输出 feature leakage / forbidden feature scan；
- 必须输出样本 coverage、split counts、label complete counts；
- 必须标注 qlib score/rank 的来源和是否 PIT-safe。

### 6.5 S1C：训练与参数冻结

S1 允许重新训练 LTR，但只限 split-aligned 实验。

参数规则：

- 优先使用 Phase1C 已有参数，不做搜索；
- 如执行者认为必须轻量参数搜索，必须先提交参数表并在训练前冻结；
- 参数选择只能使用 train / validation；
- test 不得用于调参、筛策略、调阈值、挑最好 seed。

默认冻结候选：

- LTR simple：沿用 Phase1C simple 结构；
- LTR turnover-controlled：沿用已有 turnover controlled 规则，不新增策略族；
- Conservative variants：只允许使用已存在保守规则变体，不得临时发明新规则。

### 6.6 S1D：完整日频回放与比较

必须使用与既有 Top50 adaptive 完全一致的完整日频组合 replay 口径。

必须比较：

- `rank_rotate_top50_adaptive_score`
- `rank_rotate_top50`
- `rank_rotate_top30`
- `confirmed_exit`
- `split_aligned_ltr_simple_daily`
- `split_aligned_ltr_turnover_controlled_daily`
- 已存在保守 LTR 参考，如数据允许

必须输出区间：

- full test：`2023-01-01..2025-06-30`
- 2023
- 2024
- 2025 H1
- rolling 6m / 12m
- bear / normal / bull 或现有等价 regime

必须输出指标：

- `fee_tax_adjusted_net_return`
- `max_drawdown`
- `action_count`
- `buy_count`
- `sell_count`
- `fee_and_tax`
- `turnover_proxy_by_notional_over_avg_equity`
- `relative_return_vs_top50_adaptive`
- `relative_drawdown_vs_top50_adaptive`
- `relative_actions_vs_top50_adaptive`
- `missing_price_count`
- `trading_days_used`
- `comparison_status`

### 6.7 S1 禁止事项

- 不得进入 S2；
- 不得新鲜重训 qlib/LTR；
- 不得把 S1 test 结果写成当前上线效果；
- 不得改前端/API；
- 不得 provider refresh/publish；
- 不得切换 accepted latest；
- 不得 monitor config save / scan / alerts write；
- 不得 broker、orders、quick-trade；
- 不得输出买卖、持有、仓位、target position、target weight、收益承诺、胜率或上涨概率。

### 6.8 S1 报告必须给出的 gate

S1 最终只能给以下之一：

```text
split_aligned_ltr_method_supported
split_aligned_ltr_method_not_supported
split_aligned_data_insufficient
```

如果执行者只完成 S1A 覆盖诊断，也可以先提交 S1A 报告等待审查，不得擅自继续训练。

## 7. 给执行者的一句话

请进入 Phase S1，但先只做 S1A：旧窗口 `2015-05-04..2025-06-30` 的 qlib score/rank 覆盖与生成口径诊断，明确 train/validation/test 每日每股覆盖、score 来源、是否需要重建、是否存在 in-sample 或 test 反馈风险；不得训练、不得调参、不得改前端/API、不得 provider/accepted latest/monitor/交易链路，完成后提交 `PHASES1A_SCORE_RANK_COVERAGE_REPORT_CN.md` 等待审查。
