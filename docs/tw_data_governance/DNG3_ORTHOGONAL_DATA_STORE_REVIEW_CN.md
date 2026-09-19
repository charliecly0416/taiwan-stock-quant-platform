# DNG3 正交数据 Canonical Store 审查报告

生成日期：2026-06-29

审查者：DNG3 Reviewer

## 1. 审查结论

Verdict：`PASS_WITH_CONDITIONS_GO_DNG4`

DNG3 可以带条件进入 DNG4，但只允许进入 `StrategyInputBundle / ReplayInputBundle` 的 contract、builder、validator 与 dependency readiness 设计，不允许把本轮 orthogonal feature store 解释为 LTR Model B ready，也不允许进入模型训练、推理、LTR score、策略回放、shadow execution、publish 或 latest switch。

通过原因：

1. DNG3 已生成 canonical orthogonal feature store 目录与必需文件，validator 本地运行通过，结构检查无 errors。
2. `features.csv` 为 long-form canonical 表，具备 `feature_date/instrument/feature_name/feature_value/source_dataset/source_path/source_provider/available_at/pit_policy/coverage_status` 最小字段。
3. `institutional_flow` 与 `margin_short` 已从本地 controlled/top50 证据转换为 canonical long-form feature rows，并明确标记为 `PARTIAL_READY`，没有伪装成 full-universe provider READY。
4. `corporate_actions`、`monthly_revenue`、`valuation` 的缺口被写入 `provider_status`、`coverage_audit`、`pit_audit` 与 readiness matrix；其中 `monthly_revenue`、`valuation` 明确为 `BLOCKED_QUOTA` 且 `requires_external_source_repair=true`。
5. `can_continue_to_model_b_ltr=false` 被 manifest、readiness matrix、validation JSON 和执行报告一致记录；未发现被 `can_continue_to_model_score=true` 覆盖或误用。
6. PIT delayed rows 已记录：`institutional_flow=1104`、`margin_short=850`，合计 `1954` 行；PIT violation count 为 0，validator 将 delayed rows 作为 warning 而非 LTR 放行依据。
7. manifest、provider_status、readiness、lineage、source_data_audit 与 validation JSON 的 forbidden action flags 均为 false；本轮审查未发现真实抓数、provider refresh/publish、qlib accepted latest switch、readonly/Agent publish、模型训练/推理/score、策略回放、broker/order/quick-trade、target_position 或 target_weight。

进入 DNG4 的条件：

- DNG4 只能先做 bundle contract / builder / validator / dependency readiness，不得生成可执行 replay 或 shadow exposure。
- DNG4 的 bundle manifest 必须携带 DNG3 blockers：`corporate_actions`、`monthly_revenue`、`valuation`。
- 任何 qlib+LTR Model B、LTR rerank、orthogonal/LTR score、ModelBInferenceInput 或 ModelB ModelSignalArtifact 路线必须继续阻断，直到缺失正交数据被 repair 并重新通过 DNG3 validator。
- `can_continue_to_model_score=true` 只能解释为 qlib-only score 路线不被 DNG3 阻断；不得解释为 orthogonal/LTR score ready。
- `monthly_revenue` 与 `valuation` 的 provider quota/payment blocker 需要外部来源或权限修复；这不阻断 DNG4 contract 设计，但阻断 LTR Model B readiness。

## 2. 已审查输入

已阅读必需文件：

- `docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md`
- `docs/tw_data_governance/DNG3_ORTHOGONAL_DATA_STORE_WORK_CN.md`
- `docs/tw_data_governance/DNG3_ORTHOGONAL_DATA_STORE_REVIEW_WORK_CN.md`
- `docs/tw_data_governance/DNG3_ORTHOGONAL_DATA_STORE_EXECUTION_REPORT_CN.md`
- `scripts/build_tw_orthogonal_feature_store.py`
- `scripts/validate_tw_orthogonal_feature_store.py`
- `data_tw/canonical/orthogonal_feature_store/daily_orthogonal/dng3_orthogonal_feature_store_20260625/manifest.json`
- `data_tw/catalog/readiness_matrix/2026-06-25/orthogonal_feature_store.json`
- `data_tw/catalog/dng3_orthogonal_feature_store_validation.json`

辅助核对：

- `data_tw/canonical/orthogonal_feature_store/daily_orthogonal/dng3_orthogonal_feature_store_20260625/features.csv`
- `data_tw/canonical/orthogonal_feature_store/daily_orthogonal/dng3_orthogonal_feature_store_20260625/schema.json`
- `data_tw/canonical/orthogonal_feature_store/daily_orthogonal/dng3_orthogonal_feature_store_20260625/provider_status.json`
- `data_tw/canonical/orthogonal_feature_store/daily_orthogonal/dng3_orthogonal_feature_store_20260625/pit_audit.csv`
- `data_tw/canonical/orthogonal_feature_store/daily_orthogonal/dng3_orthogonal_feature_store_20260625/lineage.json`

## 3. 本地验证结果

执行：

```bash
python -m py_compile scripts/build_tw_orthogonal_feature_store.py scripts/validate_tw_orthogonal_feature_store.py
```

结果：通过，退出码 0。

执行：

```bash
python scripts/validate_tw_orthogonal_feature_store.py --run-id dng3_orthogonal_feature_store_20260625 --asof 2026-06-25 --json
```

结果摘要：

```text
ok=true
status=PARTIAL_READY
errors=0
warnings=1
row_count=2146816
datasets=institutional_flow, margin_short
blocking_datasets=corporate_actions, monthly_revenue, valuation
can_continue_to_model_b_ltr=false
can_continue_to_model_score=true
can_continue_to_dng4=true
```

warning 内容为：

```text
features.csv has PIT-delayed rows with available_at after asof count=1954;
kept as canonical evidence and blocked from Model B readiness by dataset gates
```

审查解释：validator `ok=true` 只说明 required files、required fields、PIT 字段、forbidden fields、provider_status、readiness 和 forbidden action flags 检查通过；业务状态仍是 `PARTIAL_READY`，因此不能给 `PASS_GO_DNG4`，只能带条件进入 DNG4。

## 4. 数据集状态审查

`provider_status.json` 与执行报告一致：

| dataset | status | rows | symbols | 审查判断 |
| --- | ---: | ---: | ---: | --- |
| `institutional_flow` | `PARTIAL_READY` | 53820 | 50 | local controlled/top50 evidence 已转换为 canonical long-form，但不是 full-universe provider store |
| `margin_short` | `PARTIAL_READY` | 53468 | 50 | local controlled/top50 evidence 已转换为 canonical long-form，但不是 full-universe provider store |
| `corporate_actions` | `PARTIAL_READY` | 62 | 58 | 有 ops cache/archive 证据，但没有可转换日频 normalized feature body |
| `monthly_revenue` | `BLOCKED_QUOTA` | 0 | 0 | 本地 historical PIT file 无数据行，ops segment cache 受 quota/payment blocker 阻断 |
| `valuation` | `BLOCKED_QUOTA` | 0 | 0 | 无本地 normalized valuation body，ops segment cache 受 quota/payment blocker 阻断 |
| `yz2_orthogonal_feature_package` | `LEGACY_RESEARCH_ONLY` | 50 | 50 | 仅保留为 lineage evidence，不作为 DNG3 fresh canonical source |

审查判断：

- DNG3 覆盖了工作单列出的五类正交数据：可用项被转换，缺失/阻断项被显式记录。
- `corporate_actions` 虽有 archive evidence，但缺 canonical feature body，因此不能算 LTR ready。
- `monthly_revenue` 与 `valuation` 需要外部来源、quota 或权限修复；该问题不应在 DNG4 contract 阶段被静默降级为 optional。

## 5. Readiness Gate 审查

`manifest.json`、`readiness_matrix/2026-06-25/orthogonal_feature_store.json` 与 validation JSON 一致记录：

```text
status=PARTIAL_READY
can_continue=false
can_continue_to_model_b_ltr=false
can_continue_to_model_score=true
can_continue_to_dng4=true
can_continue_to_replay=false
can_continue_to_shadow_execution=false
blocking_datasets=corporate_actions, monthly_revenue, valuation
```

`model_score_scope` 明确为：

```text
qlib_only_score_not_blocked_by_DNG3;
orthogonal/LTR score remains blocked when can_continue_to_model_b_ltr=false
```

审查判断：

- `can_continue_to_model_b_ltr=false` 没有被误用或覆盖。
- `can_continue_to_model_score=true` 的语义足够窄，只能用于 qlib-only score route 不被 DNG3 正交数据阻断；不能用于 Model B LTR。
- `can_continue_to_dng4=true` 可以接受，前提是 DNG4 只做 bundle contract/readiness contract，并把 blockers 作为 bundle dependency status 写入。
- replay 与 shadow execution 均为 false，符合 DNG3 工作单禁止边界。

## 6. PIT / available_at 审查

`features.csv` 表头满足 long-form 最小字段要求，样例行包含：

```text
feature_date,instrument,feature_name,feature_value,source_dataset,source_path,source_provider,available_at,pit_policy,coverage_status
```

`pit_audit.csv` 记录：

| dataset | rows_checked | pit_violation_count | available_after_asof_count | status |
| --- | ---: | ---: | ---: | --- |
| `institutional_flow` | 1237860 | 0 | 1104 | READY |
| `margin_short` | 908956 | 0 | 850 | READY |
| `corporate_actions` | 0 | 0 | 0 | MISSING_OR_BLOCKED |
| `monthly_revenue` | 0 | 0 | 0 | MISSING_OR_BLOCKED |
| `valuation` | 0 | 0 | 0 | MISSING_OR_BLOCKED |

审查判断：

- PIT/available_at 字段存在。
- `available_at > asof` 的 delayed rows 被记录为 warning 和 audit count，没有被删除或隐形吞掉。
- 因 delayed rows 与缺失数据集存在，Model B LTR 不得继续；DNG4 如消费该 store，必须要求下游按 `available_at <= decision_asof` 过滤。

## 7. Lineage 与禁止动作审查

`lineage.json` 记录：

```text
lineage_type=local_canonicalization_no_fetch
no_provider_publish=true
no_accepted_latest_switch=true
readonly_publish=false
agent_prompt_publish=false
```

transformations 仅包含：

- `wide_to_long_feature_canonicalization`
- `local_provider_status_audit`

脚本审查结论：

- `scripts/build_tw_orthogonal_feature_store.py` 读取本地 `daily_ltr_rerank`、YZ2 artifact、ops segment cache 与 local historical PIT evidence，写出 canonical/catalog/report 产物。
- `scripts/validate_tw_orthogonal_feature_store.py` 检查 required files/fields、forbidden fields、PIT、provider_status、readiness、lineage 和 forbidden action flags；运行 validator 会刷新 `data_tw/catalog/dng3_orthogonal_feature_store_validation.json` 并把 validator 输出写回执行报告。
- 未发现网络抓数、provider refresh/publish、accepted latest switch、readonly latest publish、Agent prompt publish、模型训练、模型推理、score 生成、策略回放、broker/order/quick-trade、target position 或 target weight 入口。

forbidden action flags 均为 false：

```text
real_data_fetch_triggered=false
provider_refresh_triggered=false
provider_publish_triggered=false
qlib_accepted_latest_switched=false
readonly_latest_published=false
agent_prompt_published=false
model_training_triggered=false
model_inference_triggered=false
strategy_replay_triggered=false
broker_order_quick_trade_triggered=false
target_position_or_weight_generated=false
```

## 8. 是否允许进入 DNG4

允许，但只允许带条件进入 DNG4。

DNG4 可做：

- `StrategyInputBundle` / `ReplayInputBundle` manifest contract。
- bundle builder / validator 的结构实现。
- dependency_readiness.json 设计。
- qlib-only fallback 或 blocked LTR 的显式 contract 表达。
- 对缺失 `corporate_actions/monthly_revenue/valuation` 的 blocker 透传。

DNG4 不可做：

- 生成或发布 LTR Model B score。
- 用 qlib-only score 冒充 qlib+LTR ready。
- 生成 replay result、shadow execution、order intent、broker/order/quick-trade。
- 切 qlib accepted latest、readonly latest、Agent prompt latest 或 production default latest。
- 把 `monthly_revenue` / `valuation` quota blocker 伪装为 holiday/no-data 或 optional dependency。

若 DNG4 只做 input bundle contract，本轮 DNG3 证据足够；若 DNG4 试图产出可执行 replay bundle 或 Model B LTR bundle，则必须停止并回到外部数据源修复。

## 9. 后续条件

1. DNG4 bundle manifest 必须显式写入：

```text
source_orthogonal_feature_store=dng3_orthogonal_feature_store_20260625
orthogonal_feature_store_status=PARTIAL_READY
can_continue_to_model_b_ltr=false
blocking_datasets=corporate_actions, monthly_revenue, valuation
readonly_only=true
no_order=true
no_target_position=true
no_target_weight=true
```

2. `dependency_readiness.json` 必须保留每个缺失数据集的 `catalog_status/schema_status/pit_status/blocker_reason/repair_recommendation`。
3. 后续若要放行 LTR Model B，必须先完成 corporate_actions 日频 normalized feature body，以及 monthly_revenue / valuation 的 provider quota 或替代来源修复，再重新生成 DNG3 store 并通过 validator。
4. 后续若要进入 replay/shadow/publish/latest switch，必须另开相应 DNG 或 production gate 审查；本报告不授权这些动作。
