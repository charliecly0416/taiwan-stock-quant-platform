# Phase R15R Frontend Scope Audit Repair 执行报告

生成日期：2026-06-16

## 1. 执行依据

本阶段依据审查文档执行：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER15_REVIEW_AND_R16_PREP_WORK_CN.md
```

审查结论：R15 前端只读展示自身通过，但总合同回归仍将 `frontend/src/views/tw-stock-monitor/index.vue` 的任何 tracked diff 判为 forbidden scope。R15 已授权修改该页面增加 readonly strategy snapshot 展示，因此需要在 R16 前修复总合同回归的 forbidden-scope audit。

## 2. 修复目标

将总合同回归从路径级一刀切失败改为：

```text
frontend/src/views/tw-stock-monitor/index.vue 中 R15 已授权 readonly snapshot 展示 diff 可通过内容级审计；
其它生产/日更/API 禁区仍保持路径级硬失败；
新增前端 diff 继续禁止 quick-trade / broker / order / target position / target weight / provider publish / accepted latest / monitor write；
总合同回归恢复 ok=true。
```

## 3. 实现改动

### 3.1 总合同回归脚本

修改：

```text
scripts/run_tw_modular_contract_regression.py
```

新增内容级审计：

```text
R15_READONLY_FRONTEND_PATH
R15_READONLY_REQUIRED_MARKERS
R15_READONLY_FORBIDDEN_PATTERNS
git_diff_for_path()
added_diff_lines()
audit_r15_readonly_frontend_diff()
```

审计逻辑：

- 若 `frontend/src/views/tw-stock-monitor/index.vue` 有 tracked diff，且 diff 只在该文件；
- 检查 diff 中必须包含 R15 readonly markers：
  - `readonly-strategy-snapshot-panel`
  - `loadReadonlyStrategySnapshot`
  - `readonlyStrategySnapshot`
  - `getTwStockReadonlyStrategySnapshot`
- 检查新增行不得包含禁用模式：
  - quick-trade / broker / order 相关；
  - target-position / target_weight / targetWeight；
  - provider publish / provider refresh；
  - accepted latest；
  - monitor save/scan/alert write helper；
  - POST/PUT/PATCH/DELETE 方法；
  - R15 禁止文案；
- 检查 R15 静态检查与 E2E 文件存在。

其它禁区保持原路径级审计：

```text
scripts/run_daily_tw_stock_auto_update.py
scripts/run_extended_oos_formal_replay_matrix.py
backend_api_python
src/api
```

### 3.2 forbidden_scope_audit 输出扩展

`forbidden_scope_audit.csv` 新增字段：

```text
audit_mode
authorized_readonly_frontend_diff
required_missing
forbidden_matches
static_check_exists
e2e_check_exists
```

当前输出：

```text
frontend/src/views/tw-stock-monitor/index.vue,
audit_mode=r15_readonly_frontend_content_audit,
changed_path_count=1,
status=pass,
authorized_readonly_frontend_diff=True,
required_missing=,
forbidden_matches=,
static_check_exists=True,
e2e_check_exists=True
```

### 3.3 单元测试

修改：

```text
tests/unit/test_validate_tw_modular_artifact_contract.py
```

新增测试：

```text
test_r15_readonly_frontend_diff_scope_audit_passes_current_authorized_diff
```

覆盖：当前 R15 授权前端 diff 在总合同回归 forbidden-scope audit 中通过内容级审计。

## 4. 验证结果

### 4.1 Python 编译

命令：

```text
python -m py_compile scripts/run_tw_modular_contract_regression.py
```

结果：pass。

### 4.2 前端静态检查

命令：

```text
cd frontend
node tests/unit/tw-stock-readonly-strategy-snapshot-check.mjs
```

结果：

```text
[readonly-strategy-snapshot-check] ok
```

### 4.3 前端构建

命令：

```text
cd frontend
corepack pnpm build
```

结果：pass。

说明：命令输出仍有 `/bin/sh: 2: source: not found`，但退出码为 0，vite build 完成。

### 4.4 readonly snapshot validator

命令：

```text
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

结果：

```text
ok=true
checksum_ok=pass
latest_pointer_points_to_readonly_snapshot_only=pass
```

### 4.5 readonly API tests

命令：

```text
PYTHONPATH=backend python -m pytest backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py
```

结果：

```text
4 passed
```

### 4.6 总合同回归

命令：

```text
python scripts/run_tw_modular_contract_regression.py --json
```

结果：

```text
ok=true
```

关键输出：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/forbidden_scope_audit.csv
```

首行审计结果：

```text
frontend/src/views/tw-stock-monitor/index.vue,
r15_readonly_frontend_content_audit,
status=pass,
authorized_readonly_frontend_diff=True,
forbidden_matches=
```

### 4.7 artifact contract unit tests

命令：

```text
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

结果：

```text
14 passed
```

## 5. 安全边界

本阶段未执行：

- 不训练；
- 不调参；
- 不重算 replay；
- 不改默认模型或策略；
- 不修改 daily orchestrator；
- 不 provider publish；
- 不切换 provider accepted latest；
- 不触碰 broker / quick-trade / order；
- 不输出 target position / target weight；
- 不写 monitor scan/config/alerts；
- 不写 snapshot artifact。

本阶段只修复审计规则，使 R15 已授权 frontend readonly display diff 能通过更细粒度审计。

## 6. 产物清单

新增/修改：

```text
scripts/run_tw_modular_contract_regression.py
tests/unit/test_validate_tw_modular_artifact_contract.py
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER15R_FRONTEND_SCOPE_AUDIT_REPAIR_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER15R_FRONTEND_SCOPE_AUDIT_REPAIR_REVIEW_HANDOFF_CN.md
```

回归输出更新：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/forbidden_scope_audit.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/regression_summary.json
```

## 7. 结论

R15R / R16-prep 修复完成。总合同回归已恢复 `ok=true`，R15 授权前端只读展示 diff 通过内容级审计，其它禁区仍保持硬约束。

可以交由审查者复核；审查通过后再进入 R16 daily orchestrator integration。
