# Phase R15 Frontend Readonly Display 审查交接

生成日期：2026-06-16

## 1. 审查入口

执行报告：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER15_FRONTEND_READONLY_DISPLAY_EXECUTION_REPORT_CN.md
```

用户请求引用的工作文档不存在：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER14_REVIEW_AND_R15_WORK_CN.md
```

本阶段实际依据：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER12_R16_READONLY_PRODUCTIZATION_FULL_CHAIN_WORK_CN.md
```

## 2. 本阶段审查重点

请重点审查：

1. `frontend/src/api/tw-stock.js` 的 `getTwStockReadonlyStrategySnapshot()` 是否严格 GET；
2. `frontend/src/views/tw-stock-monitor/index.vue` 新增 `readonly-strategy-snapshot-panel` 是否只读展示；
3. 新增 panel 是否只显示研究候选、调入候选、调出观察、source manifest、validation/checksum 状态；
4. 新增代码是否未引入交易按钮、monitor 写入、provider publish、accepted latest 切换、broker/order/quick-trade；
5. R15 新增测试是否覆盖 forbidden text 和 forbidden network write。

## 3. 验证命令

建议审查者复跑：

```text
cd frontend
node tests/unit/tw-stock-readonly-strategy-snapshot-check.mjs
corepack pnpm build
npx http-server dist -a 127.0.0.1 -p 8061
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8061 node tests/e2e/tw-stock-readonly-strategy-snapshot-readonly.mjs
```

后端/合同：

```text
python -m py_compile backend/app/services/readonly_strategy_snapshot.py backend/app/routes/readonly_strategy_snapshot.py scripts/validate_tw_modular_readonly_snapshot.py
PYTHONPATH=backend python -m pytest backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

## 4. 已知审查注意事项

`python scripts/run_tw_modular_contract_regression.py --json` 当前返回 `ok=false`。

定位结果：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/forbidden_scope_audit.csv
```

失败原因：旧 forbidden-scope audit 将 `frontend/src/views/tw-stock-monitor/index.vue` 的任何 tracked diff 判为失败；R15 本身要求修改该页面增加只读展示，因此该项属于阶段边界冲突。

请审查者决定是否在下一阶段修订总合同回归的 forbidden-scope audit，使已授权的 R15 readonly frontend diff 可被纳入白名单或更细粒度检查。

## 5. R16 前建议

R16 是 daily orchestrator integration。进入 R16 前建议先处理：

- 总合同回归 forbidden-scope audit 与 R15 前端授权改动的冲突；
- 确认 R16 只允许接入 readonly snapshot 自动生成，不允许 provider accepted latest 切换或交易路径；
- R16 需要继续输出执行报告和审查交接文档。

## 6. R15 结论

R15 自身 gate 已通过：

```text
frontend_readonly_e2e_pass=true
network_no_forbidden_write=true
console_no_error=true
forbidden_text_scan_pass=true
```

本阶段不建议直接进入 R16，除非审查者接受或修复总合同回归的 frontend diff 审计冲突。
