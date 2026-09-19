# DNG3 正交数据 Canonical Store 执行报告

生成时间：2026-06-29T06:51:41+00:00

执行者：DNG3 Executor

## 1. 结论

- run_id：`dng3_orthogonal_feature_store_20260625`
- asof：`2026-06-25`
- canonical store：`data_tw/canonical/orthogonal_feature_store/daily_orthogonal/dng3_orthogonal_feature_store_20260625`
- can_continue_to_model_b_ltr：`false`
- can_continue_to_model_score：`true`，仅表示 qlib-only score 路线不被 DNG3 阻断。
- can_continue_to_dng4：`true`
- blocking_datasets：`corporate_actions, monthly_revenue, valuation`

## 2. 本地来源与状态

| dataset | status | rows | symbols | reason |
| --- | ---: | ---: | ---: | --- |
| institutional_flow | PARTIAL_READY | 53820 | 50 | Local research/controlled feature table is available and PIT fields exist, but scope is top50/controlled, not a canonical full-universe provider store. |
| margin_short | PARTIAL_READY | 53468 | 50 | Local research/controlled feature table is available and PIT fields exist, but scope is top50/controlled, not a canonical full-universe provider store. |
| corporate_actions | PARTIAL_READY | 62 | 58 | Local ops segment cache reports covered=true and archived corporate actions, but no normalized daily feature body was found for canonical long-form conversion. |
| monthly_revenue | BLOCKED_QUOTA | 0 | 0 | Local historical PIT file has no data rows; latest ops segment cache is not covered. |
| valuation | BLOCKED_QUOTA | 0 | 0 | No local normalized valuation body was found; latest ops segment cache is not covered. |
| yz2_orthogonal_feature_package | LEGACY_RESEARCH_ONLY | 50 | 50 | Existing YZ2 top50 package is retained as lineage evidence only, not as fresh canonical DNG3 source. |

## 3. 产物

- `manifest.json`
- `features.csv`
- `schema.json`
- `source_data_audit.json`
- `pit_audit.csv`
- `coverage_audit.csv`
- `provider_status.json`
- `lineage.json`
- `data_tw/catalog/readiness_matrix/2026-06-25/orthogonal_feature_store.json`
- `data_tw/catalog/dng3_orthogonal_feature_store_validation.json`（validator 运行后写入）

## 4. LTR Model B 判断

当前本地 canonical feature body 只覆盖 `institutional_flow` 与 `margin_short`。`corporate_actions` 只有 ops covered/archive 证据但没有可转换日频特征体；`monthly_revenue` 与 `valuation` 在本地 ops segment cache 中记录 quota/payment blocker。因此 `can_continue_to_model_b_ltr=false`。

## 5. DNG4 判断

DNG4 如果只做 input bundle contract / readiness contract，可继续，必须携带上述 blocker；不得把本产物解释为 LTR Model B ready。

## 6. Validator 输出

```json
{
  "asof": "2026-06-25",
  "coverage_audit": {
    "header": [
      "dataset_id",
      "status",
      "coverage_status",
      "date_min",
      "date_max",
      "available_at_min",
      "available_at_max",
      "row_count",
      "feature_row_count",
      "symbol_count",
      "feature_count",
      "source_path",
      "status_reason"
    ],
    "row_count": 6
  },
  "errors": [],
  "feature_store": {
    "blocking_datasets": [
      "corporate_actions",
      "monthly_revenue",
      "valuation"
    ],
    "can_continue_to_dng4": true,
    "can_continue_to_model_b_ltr": false,
    "can_continue_to_model_score": true,
    "datasets": [
      "institutional_flow",
      "margin_short"
    ],
    "manifest_status": "PARTIAL_READY",
    "path": "data_tw/canonical/orthogonal_feature_store/daily_orthogonal/dng3_orthogonal_feature_store_20260625",
    "row_count": 2146816
  },
  "forbidden_action_flags": {
    "agent_prompt_published": false,
    "broker_order_quick_trade_triggered": false,
    "model_inference_triggered": false,
    "model_training_triggered": false,
    "provider_publish_triggered": false,
    "provider_refresh_triggered": false,
    "qlib_accepted_latest_switched": false,
    "readonly_latest_published": false,
    "real_data_fetch_triggered": false,
    "strategy_replay_triggered": false,
    "target_position_or_weight_generated": false
  },
  "generated_at": "2026-09-13T11:48:44+00:00",
  "ok": true,
  "pit_audit": {
    "header": [
      "dataset_id",
      "rows_checked",
      "pit_violation_count",
      "available_after_asof_count",
      "min_available_at",
      "max_available_at",
      "pit_policy",
      "status"
    ],
    "row_count": 5
  },
  "provider_status": {
    "dataset_count": 6,
    "statuses": {
      "corporate_actions": "PARTIAL_READY",
      "institutional_flow": "PARTIAL_READY",
      "margin_short": "PARTIAL_READY",
      "monthly_revenue": "BLOCKED_QUOTA",
      "valuation": "BLOCKED_QUOTA",
      "yz2_orthogonal_feature_package": "LEGACY_RESEARCH_ONLY"
    }
  },
  "required_paths": {
    "coverage_audit.csv": "data_tw/canonical/orthogonal_feature_store/daily_orthogonal/dng3_orthogonal_feature_store_20260625/coverage_audit.csv",
    "features.csv": "data_tw/canonical/orthogonal_feature_store/daily_orthogonal/dng3_orthogonal_feature_store_20260625/features.csv",
    "lineage.json": "data_tw/canonical/orthogonal_feature_store/daily_orthogonal/dng3_orthogonal_feature_store_20260625/lineage.json",
    "manifest.json": "data_tw/canonical/orthogonal_feature_store/daily_orthogonal/dng3_orthogonal_feature_store_20260625/manifest.json",
    "pit_audit.csv": "data_tw/canonical/orthogonal_feature_store/daily_orthogonal/dng3_orthogonal_feature_store_20260625/pit_audit.csv",
    "provider_status.json": "data_tw/canonical/orthogonal_feature_store/daily_orthogonal/dng3_orthogonal_feature_store_20260625/provider_status.json",
    "schema.json": "data_tw/canonical/orthogonal_feature_store/daily_orthogonal/dng3_orthogonal_feature_store_20260625/schema.json",
    "source_data_audit.json": "data_tw/canonical/orthogonal_feature_store/daily_orthogonal/dng3_orthogonal_feature_store_20260625/source_data_audit.json"
  },
  "run_id": "dng3_orthogonal_feature_store_20260625",
  "schema_version": "v1.dng3.orthogonal_feature_store.validation",
  "status": "PARTIAL_READY",
  "validated_files": {
    "lineage": true,
    "manifest": true,
    "provider_status": true,
    "readiness": true,
    "schema": true,
    "source_data_audit": true
  },
  "warnings": [
    "data_tw/canonical/orthogonal_feature_store/daily_orthogonal/dng3_orthogonal_feature_store_20260625/features.csv has PIT-delayed rows with available_at after asof count=1954; kept as canonical evidence and blocked from Model B readiness by dataset gates"
  ]
}
```

## 7. Forbidden Action Audit

本次 builder 只读取本地文件并写 canonical/catalog/report 产物。未触发真实抓数、provider refresh/publish、accepted latest switch、readonly/Agent publish、训练、推理、score、replay、broker/order/quick-trade、target_position/target_weight。
