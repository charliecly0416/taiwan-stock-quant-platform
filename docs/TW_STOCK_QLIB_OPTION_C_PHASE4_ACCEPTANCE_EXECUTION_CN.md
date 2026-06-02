---
created_at: 2026-06-02
status: execution_instruction
scope: quantdinger_tw_stock_qlib_option_c_phase4_final_acceptance
role_target: executor
reviewer: codex_reviewer
previous_review_breakpoint: docs/TW_STOCK_QLIB_OPTION_C_PHASE4_STEP3_REPORT_CN.md
next_review_breakpoint: docs/TW_STOCK_QLIB_OPTION_C_PHASE4_ACCEPTANCE_CN.md
backend_project: /path/to/taiwan-stock-quant-platform
frontend_project: /path/to/taiwan-stock-quant-platform-Vue
qlib_project: /home/chuliyang/qlib
---

# qlib Option C 台股研究信号 Phase 4 最终验收执行文档

本文档给执行者使用。Phase 4 Step 3 已完成受控启用 smoke：automation tick 真实触发 EOD pipeline，并完成 Yahoo-only refresh、Option C provider publish、accepted latest、QuantDinger latest reader 和二次 tick 幂等跳过。最终验收不再扩大能力，目标是确认 Phase 4 是否可以收尾。

---

## 1. 验收目标

确认以下能力已经成立：

```text
盘后 automation 判断
-> EOD pipeline 触发
-> Yahoo-only 数据补齐
-> staged validation
-> Option C 专用 provider publish
-> accepted latest 生成
-> QuantDinger 展示下一交易日 research ranking
-> 同 asof 幂等跳过
```

同时确认仍然不包含：

- 生产默认启用。
- 常驻 loop/cron/systemd。
- 交易、下单、仓位建议。
- 非 Yahoo 数据 fallback。
- legacy provider 覆盖。

---

## 2. 必查项

执行者必须复核并写入最终验收报告：

1. Phase 4 Step 1/2/3 的 report 链接和结论。
2. 当前默认 env 是否仍关闭。
3. 当前 latest accepted run、asof、top30 数量。
4. `target_horizon`、`signal_semantics`、`recommendation_semantics` 是否存在。
5. automation/pipeline/accepted scheduler/normal publish 均未启动 loop。
6. 同 asof 已 accepted 时 automation 是否幂等跳过。
7. refresh/publish 只影响 Option C dedicated provider。
8. legacy provider/normalized 未被覆盖。
9. Yahoo-only policy 是否保持，无 FinMind fallback。
10. no-trading flags 是否保持。
11. Step 3 使用 stale reader fixture 的原因、影响范围和残余风险。
12. 生产启用前还需要的外部条件：网络代理、交易日历 SLA、告警、人工值守策略。

---

## 3. 验收测试

至少执行：

```text
python -m py_compile backend/app/services/tw_stock_qlib_option_c_eod_automation.py backend/app/services/tw_stock_qlib_option_c_eod_pipeline.py backend/app/services/tw_stock_qlib_option_c.py backend/app/routes/tw_stock.py
python -m pytest backend/tests/test_tw_stock_qlib_option_c_ops.py -q
python -m pytest backend/tests/test_tw_stock_qlib_option_c_signals.py backend/tests/test_tw_stock_quant_signal_api.py -q
```

若最终验收报告涉及前端展示变化，必须补跑：

```text
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-monitor-workflow-check.mjs
node tests/unit/tw-stock-monitor-qlib-ops-check.mjs
corepack pnpm build
```

---

## 4. 最终报告要求

执行者完成后新增：

```text
docs/TW_STOCK_QLIB_OPTION_C_PHASE4_ACCEPTANCE_CN.md
```

报告必须包含：

```text
1. Phase 4 验收摘要
2. Step 1/2/3 证据索引
3. 当前 accepted latest 状态
4. 自动补数到 latest 闭环结论
5. 下一交易日 research ranking 语义结论
6. 幂等和防重复结论
7. 默认关闭和无 loop 结论
8. Yahoo-only 和 provider mutation 边界
9. no-trading/research-only 边界
10. 测试结果
11. 残余风险和生产启用前提
12. 是否建议 Phase 4 收尾
```

---

## 5. 下一个审核断点

审核断点：

```text
docs/TW_STOCK_QLIB_OPTION_C_PHASE4_ACCEPTANCE_CN.md
```

执行者写完 report 后停止。
