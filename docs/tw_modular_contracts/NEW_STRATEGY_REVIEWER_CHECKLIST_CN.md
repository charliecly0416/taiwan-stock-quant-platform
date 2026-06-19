# 新策略 Reviewer Checklist

生成日期：2026-06-17

## 1. 策略依赖声明

- [ ] 是否新增或更新 `StrategyDependency`？
- [ ] 是否声明 required core fields？
- [ ] 是否声明 required capabilities / extensions？
- [ ] 是否声明 forbidden signal fields？
- [ ] 是否声明 forbidden actions？
- [ ] 若限定范围，是否使用 `applies_to_artifact_names`？

## 2. 模型信号消费

- [ ] 是否只消费标准 `ModelSignalArtifact`？
- [ ] 是否未读取模型私有文件、raw training output 或 replay result？
- [ ] 是否未使用 future return、realized pnl、position、execution、order 字段？

## 3. OrderIntent 边界

- [ ] 是否输出 `OrderIntentArtifact`，而不是直接写 replay result？
- [ ] 是否声明 `readonly_only`、`not_order`、`not_target_position`、`not_investment_advice`？
- [ ] 是否没有 broker order、quick-trade、target weight/position？

## 4. Replay 边界

- [ ] Replay engine 是否保持 strategy-agnostic？
- [ ] 是否没有为了策略修改 replay execution 主体读取私有字段？
- [ ] 是否没有把 diagnostic/smoke replay 写成收益结论？

## 5. Smoke / Diagnostic

- [ ] 若为 smoke，是否 `smoke_only=true`？
- [ ] 是否 `not_valid_strategy_evidence=true`？
- [ ] 是否 `no_replay_return_conclusion=true`？
- [ ] 是否 `not_default_candidate=true`？
- [ ] 是否 `production_allowed=false` 且 `diagnostic_only=true`？

## 6. Frontend / Daily / Agent

- [ ] 是否未接入前端默认展示？
- [ ] 若前端 readonly display 变更，是否 GET-only？
- [ ] 是否未修改 `scripts/run_daily_tw_stock_auto_update.py`？
- [ ] 是否未 provider refresh / publish / accepted latest？
- [ ] 是否未写 monitor config / scan / alerts？
- [ ] 是否未改 Agent prompt/tool/action？

## 7. 必跑命令

```bash
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
python scripts/validate_tw_frontend_readonly_m4.py --json
```

若是 smoke onboarding：

```bash
python scripts/validate_tw_modular_m5_smoke.py --run-golden --json
```

## 8. 阻断条件

出现以下任一项即阻断：

```text
策略读取 replay result 或模型私有字段
未声明 dependency
直接生成目标仓位或订单
broker / quick-trade / orders
provider/latest 操作
monitor 写入
收益结论来自 smoke/diagnostic
默认策略切换
Agent 扩权
```
