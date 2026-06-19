# Phase R15R Frontend Scope Audit Repair 审查交接

生成日期：2026-06-16

## 1. 审查入口

执行报告：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER15R_FRONTEND_SCOPE_AUDIT_REPAIR_EXECUTION_REPORT_CN.md
```

审查依据：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER15_REVIEW_AND_R16_PREP_WORK_CN.md
```

## 2. 本阶段改动

请重点审查：

```text
scripts/run_tw_modular_contract_regression.py
tests/unit/test_validate_tw_modular_artifact_contract.py
```

修复点：

- `frontend/src/views/tw-stock-monitor/index.vue` 不再路径级一刀切失败；
- 该文件当前 tracked diff 必须通过 R15 readonly frontend 内容级审计；
- 其它 forbidden scopes 仍路径级硬失败；
- forbidden-scope audit 输出新增 `audit_mode`、`authorized_readonly_frontend_diff`、`forbidden_matches` 等字段；
- 新增单元测试固定当前授权行为。

## 3. 建议复核命令

```text
python -m py_compile scripts/run_tw_modular_contract_regression.py
cd frontend && node tests/unit/tw-stock-readonly-strategy-snapshot-check.mjs
cd frontend && corepack pnpm build
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
PYTHONPATH=backend python -m pytest backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

本次执行结果：

```text
frontend static check: ok
frontend build: pass
contract regression: ok=true
readonly snapshot validator: ok=true
readonly API tests: 4 passed
artifact contract tests: 14 passed
```

## 4. 审查重点

请确认 `R15_READONLY_FORBIDDEN_PATTERNS` 覆盖以下风险：

```text
quick-trade
broker
order
target position / target weight
provider publish / provider refresh
accepted latest
monitor config save
monitor scan
monitor alerts write
POST / PUT / PATCH / DELETE
R15 禁止文案
```

请确认内容级审计只给 R15 readonly snapshot display 放行，不给 daily orchestrator、provider accepted latest、broker/order、monitor 写路径放行。

## 5. R16 前状态

R15R 后：

```text
python scripts/run_tw_modular_contract_regression.py --json -> ok=true
```

R16 仍只能做 daily orchestrator integration 的 readonly snapshot 自动生成准备，继续禁止：

- provider publish；
- provider accepted latest switch；
- broker / quick-trade / order；
- monitor scan / config save / alerts write；
- target position / target weight；
- 改默认模型或策略；
- 训练、调参、score recompute、replay recompute。

## 6. 结论

R15R 已完成，R15 前端授权 diff 与总合同回归的冲突已修复。建议审查通过后再进入 R16。
