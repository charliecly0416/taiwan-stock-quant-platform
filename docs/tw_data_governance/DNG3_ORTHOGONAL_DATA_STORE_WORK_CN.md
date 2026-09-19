# DNG3 正交数据 raw / normalized / OrthogonalFeatureStore 工作文档

生成日期：2026-06-29

## 1. 背景

DNG2_R 审查结论：

```text
PASS_WITH_CONDITIONS_GO_DNG3
```

条件：

- DNG3 不得放行 replay；
- 不得放行 shadow execution；
- 不得生成模型 score；
- 不得 publish 或切 latest；
- isolated TWII bridge 只能作为 `PARTIAL_READY_WITH_DECLARED_GAP` lineage。

## 2. 目标

将 LTR / 风险控制 / 规则研究可能依赖的正交数据规范为 canonical store，至少覆盖本地已有证据中的：

```text
institutional_flow
margin_short
corporate_actions
monthly_revenue
valuation
```

DNG3 不要求所有 provider 数据都完整，但必须把可用、缺失、quota/permission blocker、holiday/no data 明确写入 manifest/coverage/readiness。

## 3. 必须生成

脚本：

```text
scripts/build_tw_orthogonal_feature_store.py
scripts/validate_tw_orthogonal_feature_store.py
```

产物：

```text
data_tw/canonical/orthogonal_feature_store/daily_orthogonal/{run_id}/manifest.json
data_tw/canonical/orthogonal_feature_store/daily_orthogonal/{run_id}/features.csv
data_tw/canonical/orthogonal_feature_store/daily_orthogonal/{run_id}/schema.json
data_tw/canonical/orthogonal_feature_store/daily_orthogonal/{run_id}/source_data_audit.json
data_tw/canonical/orthogonal_feature_store/daily_orthogonal/{run_id}/pit_audit.csv
data_tw/canonical/orthogonal_feature_store/daily_orthogonal/{run_id}/coverage_audit.csv
data_tw/canonical/orthogonal_feature_store/daily_orthogonal/{run_id}/provider_status.json
data_tw/canonical/orthogonal_feature_store/daily_orthogonal/{run_id}/lineage.json
data_tw/catalog/readiness_matrix/{asof}/orthogonal_feature_store.json
data_tw/catalog/dng3_orthogonal_feature_store_validation.json
docs/tw_data_governance/DNG3_ORTHOGONAL_DATA_STORE_EXECUTION_REPORT_CN.md
```

## 4. 数据来源

优先读取本地已有数据：

```text
data_tw/ops/daily_auto_update/**
data_tw/experiments/ltr_orthogonal_features_controlled/**
data_tw/artifacts/phase_yz/yz2_orthogonal_feature_package/**
data_tw/experiments/decision_orthogonal/**
data_tw/**
```

不得触发真实 FinMind/Yahoo/TWSE 抓数。

## 5. features.csv 最小字段

```text
feature_date
instrument
feature_name
feature_value
source_dataset
source_path
source_provider
available_at
pit_policy
coverage_status
```

如果本地已有宽表特征，可保留宽表副本，但 canonical `features.csv` 必须提供 long-form 最小表。

## 6. provider_status.json

必须记录：

```text
dataset_id
provider
source_max_date
row_count
symbol_count
status
status_reason
quota_or_permission_status
holiday_or_no_data_evidence
requires_external_source_repair
```

status 枚举：

```text
READY
PARTIAL_READY
MISSING
BLOCKED_PROVIDER
BLOCKED_PERMISSION
BLOCKED_QUOTA
HOLIDAY_NO_DATA
LEGACY_RESEARCH_ONLY
```

## 7. readiness

readiness matrix 必须至少输出：

```text
can_continue_to_model_b_ltr
can_continue_to_model_score
can_continue_to_dng4
blocking_datasets
allowed_fallbacks
```

规则：

- 如果 institutional/margin 等 LTR 必需数据缺失，`can_continue_to_model_b_ltr=false`；
- 如果只要 qlib-only score，不应被 DNG3 阻断；
- 如果 DNG4 只是做 input bundle contract，可允许 `can_continue_to_dng4=true`，但必须标明 LTR 不 ready。

## 8. Validator

`scripts/validate_tw_orthogonal_feature_store.py` 必须支持：

```text
python scripts/validate_tw_orthogonal_feature_store.py --run-id <run_id> --asof <YYYY-MM-DD> --json
```

检查：

- required files；
- required fields；
- forbidden future fields；
- PIT/available_at 字段存在；
- provider_status 存在；
- readiness matrix 存在；
- no publish/no latest switch/no model score/no replay flags；
- 输出 JSON。

## 9. 禁止动作

不得执行：

```text
真实抓数
provider refresh / publish
qlib accepted latest switch
readonly latest publish
Agent prompt latest publish
模型训练
模型推理
模型 score 生成
策略回放
broker/order/quick-trade
target_position / target_weight
```

## 10. 执行报告

报告必须说明：

1. 每类正交数据来源。
2. 哪些 ready、partial、missing、blocked。
3. 是否足够支持 LTR Model B。
4. 是否足够进入 DNG4。
5. validator 输出。
6. forbidden action audit。
