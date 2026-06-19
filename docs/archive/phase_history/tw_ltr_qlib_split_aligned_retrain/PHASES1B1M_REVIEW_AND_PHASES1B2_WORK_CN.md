# Phase S1B1M 回传产物审查意见与 Phase S1B2 工作文档

生成日期：2026-06-14

## 1. 审查范围

主线依据：

```text
docs/TW_STOCK_LTR_QLIB_SPLIT_ALIGNED_AND_FRESH_RETRAIN_MAINLINE_CN.md
```

本轮审查对象：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B1M_SERVER_HANDOFF_CN.md
```

审查目标：

1. 确认远端回传后，S1B1 qlib walk-forward score/rank 是否补齐；
2. 确认是否仍在 S1 旧窗口 split-aligned 公平验证主线内；
3. 确认是否存在 LTR 训练、LTR 样本构建、组合回放、provider/accepted latest/monitor/交易链路越权；
4. 若可继续，给出 Phase S1B2 工作文档。

## 2. 审查结论

结论：`有条件通过，允许进入 Phase S1B2：LTR split-aligned 样本构建与泄漏审计。`

Gate：

```text
s1b1m_scores_complete_with_resource_metadata_exception_request_s1b2_ltr_sample_build
```

允许继续的理由：

1. `WF-VAL.csv` 已回传，validation score/rank 缺口补齐。
2. 合并后的 `phase_s1b1_qlib_wf_scores.csv` 覆盖 S1 所需 train_scored / validation / test 三段。
3. score/rank 缺失、date/instrument 重复均为 0。
4. leakage audit 显示未使用 S1 test 反馈做训练或 fold 设计。
5. 现有证据显示未训练 LTR、未构建 LTR 样本、未跑组合回放、未改前端/API、未触发 provider refresh/publish、未切换 accepted latest、未触发 monitor 或交易链路。

必须带入 S1B2 的说明事项：

1. 当前目录没有独立的远端执行报告，例如 `PHASES1B1M_MEMORY_MIGRATION_EXECUTION_REPORT_CN.md`。本轮只能基于回传产物审查。该项不阻断 S1B2，但后续若再次迁移远端执行，建议保留简短远端运行记录。
2. `WF-VAL.manifest.json` 与 gate summary 记录 `resource_control_attempt_order=[16,8,4,2,1]`、`resource_control_success_num_threads=16`。用户已确认另一台服务器资源充足且有 16 个 CPU，并已授权使用 16 线程，因此该记录不再视为执行偏差，也不要求执行者解释。
3. 后续仍由当前服务器上的执行者负责常规执行与报告；远程服务器只用于本机 OOM 或资源不足时运行繁重任务，远程产物回传后再由当前主线审查。

## 3. 核验证据

### 3.1 合并 score/rank 覆盖

`phase_s1b1_gate_summary.json`：

- score rows：`308385`
- date count：`2060`
- instrument count：`676`
- folds：`WF-2017`, `WF-2018`, `WF-2019`, `WF-2020`, `WF-VAL`, `TEST`
- selected count min / median / max：`145 / 150 / 150`
- score missing count：`0`
- rank missing count：`0`
- duplicate date/instrument count：`0`

`phase_s1b1_score_rank_coverage_by_split.csv`：

| split | date range | dates | rows | selected min |
| --- | --- | ---: | ---: | ---: |
| train_scored_2017_2020 | `2017-01-03..2020-12-31` | 974 | 145921 | 147 |
| validation | `2021-01-04..2022-12-30` | 489 | 73078 | 148 |
| test | `2023-01-03..2025-06-30` | 597 | 89386 | 148 |

审查判断：

- S1 train scored rows 只能称为 `2017-2020`，不能声称覆盖完整 `2015-05-04..2020-12-31`；
- validation 与 test 的 qlib score/rank 覆盖满足进入 S1B2 的最低条件；
- dynamic universe 仍是 `up to 150`，不是每日固定 150，后续报告必须继续披露 selected count 分布。

### 3.2 WF-VAL 产物

`folds/WF-VAL.manifest.json`：

- qlib train：`2015-05-04..2020-12-31`
- score window：`2021-01-01..2022-12-31`
- score rows after universe filter：`73078`
- score date count：`489`
- selected count min / median / max：`148 / 150 / 150`
- score missing count：`0`
- rank missing count：`0`
- duplicate date/instrument count：`0`
- parameter search performed：`false`
- training performed：`true`，仅指 qlib WF-VAL score 生成所需 qlib 训练，不是 LTR 训练

### 3.3 泄漏与边界审计

`phase_s1b1_leakage_boundary_audit.json`：

- `s1_test_feedback_used_for_train_or_fold_design=false`
- `parameter_search_performed=false`
- `ltr_training_performed=false`
- `ltr_sample_build_performed=false`
- `portfolio_replay_performed=false`
- `provider_refresh_publish_performed=false`
- `accepted_latest_switching_performed=false`
- `monitor_or_trading_chain_touched=false`
- `train_scored_start=2017-01-01`
- duplicate / score missing / rank missing 均为 0

审查判断：当前 score/rank 产物可以作为 S1B2 的输入，但还不能用于说明 LTR 方法有效。S1B2 仍只是样本与泄漏审计，不是策略结论。

## 4. Findings

### High

无当前阻断项。

### Medium

1. 缺少正式远端执行报告：当前只有回传产物和 server handoff 文档，没有远端执行者对运行命令、环境、内存和回传完整性的正式报告。该项不阻断 S1B2，但后续若再次迁移远端执行，建议保留简短远端运行记录。
2. 线程数记录为 16 已由用户授权，不再作为偏差或阻断项。后续本机执行者如遇 OOM，可再按用户确认迁移远端运行繁重任务。

### Low

1. `provider_uri` 与 `config_path` 同时出现本机路径和远端 `/lustre/...` 路径。只要产物内容一致，这不影响 S1B2，但执行者下一轮应在报告中说明路径差异来自远端迁移，不代表 provider 切换或 accepted latest 切换。
2. `early_train_2015_2016_scored=false` 必须贯穿后续文档，避免把 S1 LTR train 描述为完整 2015-2020。

## 5. 台股只读安全边界审查

### Findings

未发现 broker、quick-trade、orders、target-position、target-weight、monitor write、provider publish/refresh、accepted latest switching。

### Network Audit

本轮为本地文件与报告审查，未涉及前端/API/E2E，未要求 network audit。

### Text / Agent Semantics

报告和产物中的训练、score、validation、test、回放、买卖、仓位、收益等词均处于研究流程、禁止事项或历史模拟边界说明中；未形成真实交易建议、目标仓位、收益承诺、胜率或上涨概率承诺。

### Verdict

只读安全边界通过。

## 6. Phase S1B2 工作文档：LTR Split-Aligned 样本构建与泄漏审计

### 6.1 目标

Phase S1B2 只做一件事：

```text
把 S1B1 生成的 qlib walk-forward score/rank 转成可用于后续 LTR 训练的 split-aligned 样本，并完成 feature/label/leakage 审计。
```

S1B2 不训练 LTR，不跑组合回放，不做策略比较，不给收益结论。

### 6.2 输入冻结

必须使用：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/phase_s1b1_qlib_wf_scores.csv
```

价格与市场数据只允许使用本地已存在数据：

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/*.csv
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TWII.csv
```

可参考既有 LTR feature 白名单，但必须输出本轮独立冻结文件：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_input_feature_list.json
```

如果该文件不存在或字段不匹配，执行者必须从既有 S1/S3A LTR 脚本中抽取同等口径 feature，并在报告中说明来源；不得新增正交数据、基本面数据、联网数据或 provider 数据。

### 6.3 Split 冻结

S1B2 样本 split 必须与 S1 score/rank 产物一致：

```text
train_scored: 2017-01-01..2020-12-31
validation:   2021-01-01..2022-12-31
test:         2023-01-01..2025-06-30
```

注意：

- `2015-05-04..2016-12-31` 没有 qlib walk-forward score/rank，不得纳入 LTR 样本；
- 样本只能在 S1B1 有 score/rank 的 date/instrument 上构建；
- test 样本只能用于后续最终评估，不得用于 feature 选择、参数选择或 label 设计反向调整。

### 6.4 Label 口径

Label 可以沿用现有 LTR Phase1C 的日频 forward-return / excess-return / relevance label 口径，但必须重新在 S1 split 上生成并审计。

必须输出：

- forward return label 的 horizon；
- 是否使用 TWII excess return；
- 每个 split 的 label 非空数量；
- 每个 split 的 label 分布；
- 每个 split 最后一段因未来价格不足而无法生成 label 的日期范围；
- label 字段必须标记为 `label_only`，不得进入 input feature。

如果现有 LTR 有多个 label horizon，S1B2 只冻结后续 S1B3 将使用的 label，不允许在 S1B2 根据 validation/test 表现挑 label。

### 6.5 Feature 口径

允许的 feature 类型：

- qlib score / rank / percentile / zscore；
- qlib rank change、top bucket、streak 等只基于当日及历史 score/rank 的特征；
- 价格历史技术特征，例如 MA、RSI、MACD、Bollinger、ret20、volatility；
- 成交量与流动性历史特征；
- TWII 历史市场状态特征；
- market breadth 等只基于当日及历史截面的特征。

禁止的 feature：

- 任何 future return / future excess return / forward label；
- 任何 test feedback、年度收益、回放结果、策略动作；
- `trend_score`，除非主线另行明确允许，本轮默认不纳入；
- 法人、融资融券、月营收、基本面、新闻、联网数据；
- provider refresh / accepted latest 产生的新字段；
- 任何买卖、仓位、target position、target weight 语义字段。

### 6.6 必须输出

建议输出目录：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/
```

必须产物：

```text
phase_s1b2_ltr_samples.csv
phase_s1b2_sample_schema.json
phase_s1b2_feature_list.json
phase_s1b2_split_summary.json
phase_s1b2_label_audit_summary.json
phase_s1b2_feature_coverage.csv
phase_s1b2_forbidden_feature_audit.csv
phase_s1b2_leakage_boundary_audit.json
phase_s1b2_gate_summary.json
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B2_LTR_SAMPLE_BUILD_EXECUTION_REPORT_CN.md
```

`phase_s1b2_ltr_samples.csv` 至少包含：

- `date`
- `instrument`
- `split`
- `fold_id`
- `qlib_score_raw`
- `qlib_rank`
- 本轮冻结的 input feature
- label-only 字段

### 6.7 必须审计

执行者必须报告：

1. 每个 split 的 date range、date count、row count、instrument count；
2. 每个 split 的 feature complete row count；
3. 每个 split 的 label available row count；
4. duplicate date/instrument count；
5. qlib score/rank missing count；
6. forbidden feature hits；
7. label-only 字段是否误入 input feature；
8. 是否使用 test 反馈做 feature/label/样本过滤；
9. 是否训练 LTR、跑回放、做策略比较；
10. 是否触发 provider/accepted latest/monitor/交易链路；
11. 如本机执行出现 OOM，是否需要迁移远端执行繁重任务。

### 6.8 S1B2 验收 Gate

通过 gate：

```text
s1b2_ltr_sample_build_pass_request_s1b3_training_policy_freeze
```

通过条件：

- train_scored / validation / test 三段均有样本；
- duplicate date/instrument count 为 0；
- qlib score/rank missing count 为 0；
- input feature 不包含 future label、回放结果、test 反馈、买卖/仓位语义字段；
- label-only 字段不进入 input feature；
- `s1_test_feedback_used_for_sample_or_feature_design=false`；
- `ltr_training_performed=false`；
- `portfolio_replay_performed=false`；
- `provider_refresh_publish_performed=false`；
- `accepted_latest_switching_performed=false`；
- `monitor_or_trading_chain_touched=false`；
- 如使用远端资源，已记录远端运行方式与回传产物；不得基于多个结果做效果择优。

失败 gate：

```text
s1b2_data_insufficient
s1b2_blocked_by_leakage_or_scope_violation
s1b2_blocked_by_resource_or_handoff_integrity_issue
```

若出现 forbidden feature、test feedback、真实买卖/仓位语义、provider/accepted latest/monitor/交易链路越权，必须停止并提交问题，不得继续进入训练。

### 6.9 S1B2 禁止事项

- 不训练 LTR；
- 不训练 qlib；
- 不跑组合回放；
- 不比较策略收益；
- 不调参；
- 不根据 validation/test 表现选择 feature 或 label；
- 不新增数据源；
- 不联网；
- 不改前端/API；
- 不触发 provider refresh / publish；
- 不切换 accepted latest；
- 不触发 monitor config save / scan / alerts write；
- 不接 broker、orders、quick-trade；
- 不输出买卖、持有、仓位、target position、target weight、收益承诺、胜率或上涨概率语义。

## 7. 给执行者的一句话

请执行 Phase S1B2：只基于 `phase_s1b1_qlib_wf_scores.csv` 和本地 normalized price/TWII 数据构建 S1 split-aligned LTR 样本，并输出 feature/label/leakage/boundary 审计；不得训练 LTR、不得回放、不得调参、不得新增数据源或触发前端/API/provider/accepted latest/monitor/交易链路；常规执行仍在当前服务器完成，若再次 OOM 再由用户确认迁移远端服务器运行繁重任务。
