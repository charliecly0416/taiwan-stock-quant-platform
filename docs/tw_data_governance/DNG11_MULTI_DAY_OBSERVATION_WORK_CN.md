# DNG11 Multi-Day Observation / Blocker Burn-Down 工作文档

生成日期：2026-06-29

## 1. 背景

DNG10 审查结论：

```text
PASS_WITH_CONDITIONS_GO_DNG11
```

DNG11 只允许进入多日 observation / readiness dashboard / blocker burn-down，不允许 publish、latest switch、replay、交易、训练或新调参。

## 2. 目标

汇总 DNG0-DNG10 产物，判断当前数据规范化链路是否具备多日稳定性，明确 blocker 和后续需要继续累计的交易日。

DNG11 不要求在当前一轮内凭空制造 5 个真实交易日。如果当前只有单日完整链路证据，必须明确：

```text
single_day_chain_ready=true/false
multi_day_observation_ready=false
required_additional_trade_days=N
```

## 3. 必须生成

```text
data_tw/catalog/dng11_multi_day_observation.json
data_tw/catalog/dng11_blocker_burn_down.csv
docs/tw_data_governance/DNG11_MULTI_DAY_OBSERVATION_EXECUTION_REPORT_CN.md
```

可新增 validator：

```text
scripts/validate_tw_dng11_observation.py
data_tw/catalog/dng11_multi_day_observation_validation.json
```

## 4. 必查链路

必须检查 DNG0-DNG10：

```text
DNG0 inventory
DNG1 data_catalog/latest_status
DNG2_R PriceStore/TWII/calendar
DNG3 OrthogonalFeatureStore
DNG4 input bundles
DNG5 route dependency contracts
DNG6 daily readiness dashboard
DNG7 Model A score
DNG8 Model B blocker
DNG9 model_signal_gate summary
DNG10 readonly/Agent source context
```

## 5. Blocker 分类

至少列出：

```text
formal_qlib_accepted_latest_stale
model_signal_latest_stale
agent_prompt_latest_missing
model_b_ltr_blocked_by_orthogonal_data
monthly_revenue_blocked_quota
valuation_blocked_quota
corporate_actions_not_daily_feature_ready
replay_shadow_next_day_execution_pending
production_publish_not_authorized
multi_day_observation_insufficient
```

## 6. 通过条件

DNG11 可以有两个层级的通过：

```text
PASS_SINGLE_DAY_CHAIN_GO_DNG12_DESIGN_ONLY
PASS_MULTI_DAY_OBSERVATION_GO_DNG12_GO_NO_GO
BLOCKED_WAIT_MORE_TRADE_DAYS
FAIL_NEEDS_REPAIR
```

如果没有至少 5 个交易日的 DNG7-DNG10 级别证据，不得声称 multi-day observation 完成。

## 7. 禁止动作

不得执行：

```text
真实抓数
provider refresh / publish
qlib accepted latest switch
readonly latest publish
Agent prompt latest publish
模型训练
模型调参
模型 score 生成
策略收益回放
ReplayResult/NAV 生成
broker/order/quick-trade
target_position / target_weight
```

## 8. 执行报告

报告必须说明：

1. 当前完整链路覆盖到哪一天。
2. 是否 single-day chain ready。
3. 是否 multi-day observation ready。
4. 还缺几个交易日。
5. blocker burn-down 表。
6. 是否建议进入 DNG12 design-only closure 或等待更多交易日。
