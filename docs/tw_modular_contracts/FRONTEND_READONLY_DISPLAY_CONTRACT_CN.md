# FrontendReadonlyDisplay 合同

生成日期：2026-06-17

## 1. 目的

`FrontendReadonlyDisplay` 冻结前端只读展示边界。前端只展示 GET API 返回的标准 artifact，不在浏览器本地计算信号、策略、replay、latest pointer 或交易动作。

## 2. Required Contract Fields

```text
allowed_primary_fields
allowed_audit_fields
hidden_audit_fields
forbidden_text
forbidden_requests
component_boundary
GET-only API dependency
```

## 3. Allowed Primary Fields

```text
model_name
strategy_rule
window_start
window_end
readonly_latest_asof
metrics_summary
action_table_from_artifact
validator_status
artifact_run_id
```

## 4. Forbidden Text

```text
买入建议
卖出建议
目标仓位
目标权重
保证收益
胜率保证
自动下单
实盘已执行
```

## 5. Forbidden Requests

```text
POST /monitor/*
POST /broker/*
POST /quick-trade/*
POST /orders/*
POST /provider/publish
POST /accepted-latest/*
PUT/PATCH/DELETE trading or monitor endpoints
```

## Forbidden Actions

- 不触发 provider publish / refresh。
- 不切换 provider accepted latest 或 qlib accepted latest。
- 不写 monitor config / scan / alerts。
- 不触发 broker、quick-trade 或 order。
- 不切默认模型或默认策略。

## 最小 Validator 要求

M1 validator 至少检查 required fields、manifest、schema/audit 文件、forbidden fields、forbidden actions 和只读边界。失败时必须返回明确 status，并支持 `--json`。
