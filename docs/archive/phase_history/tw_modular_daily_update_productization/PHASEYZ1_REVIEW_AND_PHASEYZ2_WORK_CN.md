# Phase YZ1 审查与 Phase YZ2 Orthogonal Data Package / Execution Price Readiness 工作文档

生成日期：2026-06-18

## 1. YZ1 审查结论

YZ1 通过，可以进入 YZ2。

已审查：

```text
docs/tw_modular_daily_update_productization/PHASEYZ1_STRICT_E4_MODEL_ADAPTERS_EXECUTION_REPORT_CN.md
scripts/build_tw_daily_model_signal_artifact.py
scripts/validate_tw_daily_model_signal_artifact.py
backend/tests/test_phase_yz1_strict_e4_model_adapters.py
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_a/manifest.json
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_b/manifest.json
```

已复跑：

```text
python -m py_compile scripts/build_tw_daily_model_signal_artifact.py scripts/validate_tw_daily_model_signal_artifact.py backend/tests/test_phase_yz1_strict_e4_model_adapters.py
python -m pytest backend/tests/test_phase_yz0_clean_registry.py backend/tests/test_phase_yz1_strict_e4_model_adapters.py -q
python scripts/validate_tw_daily_model_signal_artifact.py --manifest data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_a/manifest.json --json
python scripts/validate_tw_daily_model_signal_artifact.py --manifest data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_b/manifest.json --json
```

结果：

```text
9 passed
model_a validator passed, row_count=150
model_b blocked validator passed
```

额外抽查：

```text
Model A rows = 150
unique date+instrument = 150
full_qlib_rank = 1..150
candidate_rank count = 50
PIT violations = 0
legacy signal artifact used = false
Model B status = blocked
Model B covered_rows = 24
Model B missing_symbols = 26
Model B no_fallback = true
```

## 2. YZ1 通过项

### 2.1 Model A 合格

Model A：

```text
model_id = e4_frozen_qlib_2018_2022
```

实现符合要求：

```text
真实调用 qlib.init
使用 DatasetH + Alpha158 snapshot
加载 E1 frozen qlib LGBModel
调用 model.predict(dataset, segment="snapshot")
输出 2026-06-17 同 asof 150 行
不读取 legacy signal artifact 作为分数来源
```

### 2.2 Model B 合格 blocked

Model B：

```text
model_id = e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
```

当前没有生成伪造 LTR rerank，而是诚实 blocked：

```text
artifact_type = ModelSignalArtifactBlocked
blocked_reason = orthogonal_feature_coverage_insufficient
required_rows = 50
covered_rows = 24
missing_symbols = 26
no_fallback = true
```

这是正确行为。YZ2 必须修复正交数据覆盖，不能绕过 blocked。

### 2.3 Validator 合格

`scripts/validate_tw_daily_model_signal_artifact.py` 已改为读取：

```text
configs/tw_modular_registry.yaml -> production_models.production_selectable
```

不再硬编码旧：

```text
e4_frozen_qlib_2023_2025_ltr
```

## 3. 统筹补充意见采纳结论

参考：

```text
docs/tw_modular_daily_update_productization/PHASEYZ_FOLLOWUP_EXECUTION_PRICE_CONTRACT_SUGGESTION_CN.md
```

采纳判断：

```text
不退回 YZ0
不回改 YZ1 主任务
YZ2 增加 execution price 所需价格字段可用性检查
YZ3 正式固化 replay execution price contract
```

原因：

```text
YZ1 是模型 artifact 接口层，不应混入 replay 收益判断。
YZ2 会触及数据 package/readiness，因此适合补 next_open/next_close 数据可用性检查。
YZ3 会接 replay/API/frontend/paper portfolio，因此适合正式固化 execution_price_mode。
```

YZ2 只能检查价格字段可用性，不做策略收益判断，不做 open-vs-close 收益比较，不改变默认策略结论。

## 4. Phase YZ2 目标

YZ2 目标有两个：

```text
1. 修复 orthogonal feature package，使 Model B 能对 Model A qlib top50 做 E3 LTR rerank。
2. 补充 replay execution price 所需价格字段 readiness，确保 YZ3 能安全采用 next_open 默认执行口径。
```

YZ2 不做：

```text
前端展示
paper apply/reset 改造
replay 收益优劣判断
daily orchestrator 接入
accepted latest 切换
provider publish
新训练 / 调参
broker / order / quick-trade
```

## 5. YZ2 输入

必须使用：

```text
YZ1 Model A manifest:
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_a/manifest.json

YZ1 Model B blocked manifest:
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_b/manifest.json

E3 LTR model:
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_ltr_model.pkl

E3 manifest:
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_training_manifest.json

E2 feature schema:
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_feature_schema.csv
```

必须审计并修复当前问题：

```text
scripts/pull_tw_provider_staging_data.py 仍把 P3 daily_ltr_rerank_latest.json 当 orthogonal readiness
scripts/build_p3rr_latest_orthogonal_features.py 仍是 P3/fresh scoped 语义
data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_latest.json 不能作为 strict E4 全局 readiness
```

## 6. Orthogonal Feature Package 要求

优先方案：

```text
构建 model-neutral full150 orthogonal feature package
覆盖 YZ1 Model A 150 universe
```

最低可接受方案：

```text
构建 strict E4 scoped top50 orthogonal feature package
输入必须来自 YZ1 Model A qlib top50
manifest 必须写 scoped_model_id=e4_frozen_qlib_2018_2022
覆盖必须 50/50
```

禁止：

```text
不得读取 P3/fresh top50 作为候选范围
不得读取 P3 daily_ltr_rerank_latest.json 作为全局 readiness
不得使用 O4 LTR
不得使用 fresh/option_c qlib score 替代 E1 qlib score
不得用旧 e4_frozen_qlib_2023_2025_ltr artifact 替代
不得用 future label / future return / realized PnL 字段
```

Orthogonal package 必须包含：

```text
artifact_type
schema_version
signal_asof
universe_source = YZ1 Model A manifest
scoped_model_id 或 model_neutral_full150
feature_schema_path
feature_schema_column_count = 78
row_count
covered_symbols
missing_symbols
coverage_ratio
available_at_policy
pit_violation_count
source_freshness_audit
forbidden_field_audit
no_fallback = true
```

PIT 要求：

```text
available_at <= signal_asof
pit_violation_count = 0
```

## 7. Model B 生成要求

YZ2 完成 orthogonal package 后，必须重新生成 Model B：

```text
model_id = e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
input = YZ1 Model A qlib top50
reranker = E3 orthogonal LTR
features = YZ2 orthogonal feature package, 78 columns
row_count = 50
```

Model B artifact 必须：

```text
保留 original qlib rank / full_qlib_rank
输出 ltr raw_score / buy_score / score_rank / candidate_rank
candidate_rank 覆盖 1..50
source_model_a_manifest 指向 YZ1 Model A
source_model_artifact 指向 E3 LTR
source_feature_artifact 指向 YZ2 orthogonal package
```

如果仍然无法 50/50 覆盖，必须继续输出 blocked manifest：

```text
blocked_reason = orthogonal_feature_coverage_insufficient
missing_symbols = [...]
no_fallback = true
```

不得用任何 fallback 让 Model B 看似通过。

## 8. Execution Price Readiness 补充要求

根据统筹补充意见，YZ2 必须新增执行价字段可用性检查，但不做收益判断。

对每个：

```text
signal_asof
instrument
```

必须证明后续 YZ3 replay/paper 能定位：

```text
next_trading_day
next_trading_day_open
next_trading_day_close
close_on_or_before_signal_asof
```

默认未来执行口径将在 YZ3 固化为：

```text
execution_price_mode = next_open
```

YZ2 只检查字段可用性：

```text
next_open_available_count
next_close_available_count
close_on_or_before_signal_asof_available_count
missing_next_open_count
missing_next_close_count
missing_signal_close_count
```

如果 next open 缺失：

```text
必须 blocked 或标注 execution_price_unavailable
不得 fallback 到 next close
```

禁止在 YZ2：

```text
不得计算 open-vs-close 策略收益优劣
不得改变默认策略
不得把 next_close 当默认可执行价格
不得给前端展示收益结论
```

建议输出：

```text
data_tw/artifacts/phase_yz/yz2_execution_price_readiness/<signal_asof>/manifest.json
data_tw/artifacts/phase_yz/yz2_execution_price_readiness/<signal_asof>/price_availability_audit.csv
```

## 9. YZ2 产物要求

执行者必须提交：

```text
docs/tw_modular_daily_update_productization/PHASEYZ2_ORTHOGONAL_DATA_PACKAGE_EXECUTION_REPORT_CN.md
```

报告必须包含：

```text
1. 修改文件清单
2. orthogonal readiness 如何脱离 P3/fresh daily_ltr_rerank_latest.json
3. orthogonal feature package manifest
4. strict E4 Model A top50 coverage audit
5. available_at PIT audit
6. feature schema 78 列对齐 audit
7. source freshness audit
8. forbidden future/label/return/PnL field audit
9. Model B artifact manifest 或 blocked manifest
10. execution price readiness audit
11. 测试命令与结果
12. 是否建议进入 YZ3
```

必须输出文件：

```text
orthogonal feature package manifest
strict E4 top50 coverage audit
PIT available_at audit
source freshness audit
feature schema alignment audit
Model B manifest
Model B validator result
execution price readiness manifest
price availability audit
forbidden action audit
```

## 10. YZ2 验收 Gate

YZ2 通过必须满足：

```text
P3 daily_ltr_rerank_latest.json 不再作为全局 orthogonal readiness
strict E4 Model A top50 正交覆盖 = 50/50
available_at <= signal_asof 违规数 = 0
feature schema 78 列对齐通过
Model B 生成 50 行 LTR rerank artifact
Model B 只使用 E3 LTR 和 YZ1 Model A top50
无 future label / future return / realized PnL
next_trading_day_open / close readiness 已审计
next_open 缺失时无 fallback 到 next_close
```

若 orthogonal 仍不足：

```text
必须继续 blocked
不得进入 YZ3
```

## 11. 安全边界

YZ2 不允许：

```text
训练模型
调参
provider refresh / publish
accepted latest / qlib accepted latest switch
monitor config / scan / alerts 写入
broker
orders
quick-trade
paper apply/reset 写路径改造
前端改造
```

允许：

```text
读取本地价格/orthogonal raw archive
生成 YZ2 staging artifact
生成 Model B readonly signal artifact
生成 readiness/audit JSON/CSV
```

## 12. 建议测试

至少执行：

```text
python -m py_compile <新增/修改的 YZ2 scripts> scripts/validate_tw_daily_model_signal_artifact.py
python -m pytest backend/tests/test_phase_yz0_clean_registry.py backend/tests/test_phase_yz1_strict_e4_model_adapters.py <新增 YZ2 tests> -q
python scripts/validate_tw_daily_model_signal_artifact.py --manifest <model_b_manifest> --json
```

新增测试必须覆盖：

```text
orthogonal package 不读取 P3/fresh top50
strict E4 top50 coverage = 50/50
available_at PIT violation = 0
feature schema count = 78
Model B source_model_a_manifest 指向 YZ1 Model A
Model B source_model_artifact 指向 E3 LTR
execution price readiness 包含 next_open/next_close/signal_close
next_open 缺失不会 fallback 到 next_close
```

## 13. YZ3 预告

YZ2 通过后，YZ3 才能接：

```text
daily orchestrator
order intent builder
replay window API/policy
frontend 模型/策略选择
paper portfolio latest decision
execution_price_mode 正式合同
browser E2E / network audit
```

YZ3 必须正式固化：

```text
default execution_price_mode = next_open
next_close_research_only 只能作为研究对照
paper portfolio 模拟成交口径与 replay 默认口径一致
前端清楚展示“成交口径：次一交易日开盘”
```

但这些不是 YZ2 的实现范围。
