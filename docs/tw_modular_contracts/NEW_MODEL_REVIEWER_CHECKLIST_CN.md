# 新模型 Reviewer Checklist

生成日期：2026-06-17

## 1. 合同与 Registry

- [ ] 是否登记 registry，且 `production_allowed=false` 直到专项审查通过？
- [ ] 是否引用 `MODEL_SIGNAL_CONTRACT_CN.md` 和 extension schema？
- [ ] 是否提供 validator 与 pass/fail golden samples？
- [ ] 是否明确 allowed / forbidden consumers？

## 2. 输入与 PIT

- [ ] 输入 feature/data artifact 是否有 as-of / available_at？
- [ ] 是否无 future return、label、realized pnl、execution、position、order 字段泄漏？
- [ ] `signal_asof` / `available_at` 是否可验证？

## 3. Adapter 与 Core Fields

- [ ] 是否通过 adapter 生成标准 `ModelSignalArtifact`？
- [ ] 是否包含所有 core fields？
- [ ] 是否没有让策略、replay、frontend、Agent 直接读取模型私有字段？
- [ ] 新字段是否使用 `ext_*` 并声明 metadata？

## 4. Smoke / Diagnostic

- [ ] 若为 smoke，是否 `smoke_only=true`？
- [ ] 是否 `not_valid_strategy_evidence=true`？
- [ ] 是否 `no_replay_return_conclusion=true`？
- [ ] 是否 `not_default_candidate=true`？
- [ ] 是否没有被接入 formal replay、frontend default display、production latest pointer？

## 5. 禁止动作

- [ ] 未触发真实训练以外的生产链路？
- [ ] 未切 default candidate / default strategy？
- [ ] 未 provider refresh / publish？
- [ ] 未切 accepted latest？
- [ ] 未写 monitor config / scan / alerts？
- [ ] 未连接 broker / quick-trade / orders？
- [ ] 未改 Agent prompt/tool/action？

## 6. 必跑命令

```bash
python scripts/validate_tw_modular_m_contracts.py --run-golden --json
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
python scripts/validate_tw_frontend_readonly_m4.py --json
```

若涉及 M5 smoke：

```bash
python scripts/validate_tw_modular_m5_smoke.py --run-golden --json
```

## 7. 阻断条件

出现以下任一项即阻断：

```text
策略读取模型私有字段
缺 core fields
缺 PIT/as-of 证明
smoke 被当作收益证据
default switch
provider/latest 操作
monitor/broker/order 写入
Agent 扩权
```
