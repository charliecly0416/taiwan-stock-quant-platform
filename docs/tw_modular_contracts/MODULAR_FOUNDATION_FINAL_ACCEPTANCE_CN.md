# Phase M0-M6 模块化地基最终验收

生成日期：2026-06-17

## 1. 结论

Phase M0-M6 模块化地基验收通过。当前状态只允许把真实新模型/新策略作为下一条新主线开启；不得把 M5 smoke、diagnostic artifact、历史 replay 或前端 readonly 展示误用为默认策略、生产发布或交易证据。

本验收未训练真实新模型，未调参，未新增正式策略收益结论，未切 default candidate / default strategy，未触发 provider refresh / publish，未切 accepted latest，未写 monitor config / scan / alerts，未连接 broker / quick-trade / orders，未修改 Agent prompt/tool/action，未修改 `scripts/run_daily_tw_stock_auto_update.py`。

## 2. 阶段验收摘要

| Phase | 验收内容 | 当前结论 |
| --- | --- | --- |
| M0 | 补齐 DataSource、DataIngestion、PriceStore、DailyOrchestrator、RunRegistry、AutoUpdate、Analysis、FrontendReadonly、AgentReadonly、FrontendAgentPanel、DefaultCandidateDecision 合同 | 通过 |
| M1 | 统一合同 validator、golden samples、错误码和正负例 | 通过 |
| M2 | registry 与 onboarding templates | 通过 |
| M2R | registry artifact_type / golden contract 语义 gate、Agent response semantics 修复 | 通过 |
| M3 | daily orchestrator / readonly latest pointer dry-run | 通过 |
| M3R | legacy provider refresh / publish / accepted latest 默认不可达 gate | 通过 |
| M4 | frontend readonly display 组件边界 | M4R 后通过 |
| M4R | `/tw-stock-monitor` readonly acceptance GET-only，运行时 network audit | 通过 |
| M5 | 新模型/新策略 smoke-only onboarding dry-run | 通过 |

## 3. 最终硬门

最终验收要求以下全部为真：

```text
合同齐全
validator 齐全
golden samples 齐全
registry regression 通过
daily dry-run / latest pointer gate 通过
frontend readonly GET-only gate 通过
M5 smoke onboarding 通过
Agent 未扩权，仅保留只读合同占位
无真实训练
无正式策略收益结论
无 default candidate / default strategy switch
无 provider publish / refresh
无 accepted latest switch
无 monitor 写入
无 broker / quick-trade / order
```

## 4. 验收命令

实际复跑命令：

```bash
python -m py_compile scripts/validate_tw_modular_m_contracts.py scripts/validate_tw_modular_registry_m2.py scripts/validate_tw_daily_orchestrator_m3.py scripts/validate_tw_frontend_readonly_m4.py scripts/validate_tw_modular_m5_smoke.py scripts/run_tw_modular_contract_regression.py
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
python scripts/validate_tw_frontend_readonly_m4.py --json
python scripts/validate_tw_modular_m5_smoke.py --run-golden --json
```

说明：M6 工作文档中的命令名 `validate_tw_modular_contracts.py` / `validate_tw_modular_registry.py` 在当前仓库对应为：

```text
scripts/validate_tw_modular_m_contracts.py
scripts/validate_tw_modular_registry_m2.py
```

## 5. 通过证据

统一回归输出：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/regression_summary.json
```

关键结果：

```text
ok=true
m1_contract_status=passed
m2_registry_status=passed
m3_daily_orchestrator_status=passed
m3_daily_script_audit_status=passed
m4_frontend_readonly_status=passed
m4_forbidden_request_count=0
m4_legacy_provider_gate_not_exposed=true
m5_onboarding_smoke_status=passed
m5_onboarding_smoke_sample_count=2
```

M3R script audit 允许 legacy warning 存在，但默认路径必须不可达：

```text
default_provider_refresh_reachable=false
default_provider_publish_reachable=false
default_accepted_latest_reachable=false
```

M4R frontend readonly gate：

```text
readonly_workflow_only_get=true
forbidden_request_count=0
replay_strategy_write_count=0
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
ops_provider_publish_refresh_accepted_latest_request_count=0
broker_quick_trade_orders_request_count=0
```

M5 smoke gate：

```text
schema_version=m5.0.0
sample_count=2
pass_minimal actual_ok=true
fail_missing_smoke_flags actual_ok=false
actual_error_codes=[smoke_marker_missing]
```

## 6. Smoke / Diagnostic 隔离规则

以下规则是 M6 后硬约束：

```text
smoke_only=true 的产物不能作为有效策略证据
not_valid_strategy_evidence=true 的产物不能进入 default candidate
no_replay_return_conclusion=true 的产物不能被写成收益结论
not_default_candidate=true 的产物不能切默认策略
diagnostic_only=true 且 production_allowed=false 的 registry entry 不能被 production consumer 消费
order intent smoke 夹具不是订单、目标仓位或投资建议
```

Smoke 或 diagnostic entry 不得进入：

```text
formal replay return conclusion
default candidate decision
frontend product default display
production latest pointer
provider publish / accepted latest
broker / quick-trade / orders
Agent tool/action/prompt
```

## 7. Agent 冻结结论

M0-M6 不进入 Agent 功能开发。当前只允许：

```text
Agent readonly context placeholder
Agent prompt/tool/action 未扩权
Agent 不建议买卖
Agent 不输出目标仓位
Agent 不调用 provider/latest/monitor/broker/order
```

后续 Agent 整理必须另开专项阶段，并重新定义合同、validator、E2E 和安全边界。

## 8. 残余风险

1. M3R legacy provider publish/latest 代码路径仍存在，但默认不可达；后续如要治理删除或生产放行，必须另开阶段。
2. M4R GET-only 结论依赖 validator/E2E network audit；任何前端 readonly workflow 改动必须复跑该 gate。
3. M5 smoke 只证明 onboarding 流程，不证明任何真实模型、策略或收益表现。
4. 真实新模型/新策略仍需另开项目主线，重新完成数据、特征、PIT、训练、回放、默认候选和产品安全审查。

## 9. 最终结论

M0-M6 模块化地基可以作为后续真实新模型/新策略开发的前置基础。下一阶段可以开启真实新模型/新策略主线，但必须遵守 `NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md` 和 reviewer checklist。
