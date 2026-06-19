# Phase V4A 审查意见与 Phase V4 最终验收工作文档

生成时间：2026-06-14

主线依据：`docs/tw_ltr_strategy_validation/LTR_STRATEGY_VALIDATION_MAINLINE_CN.md`

审查入口：`docs/tw_ltr_strategy_validation/PHASEV4A_SCOPE_ATTRIBUTION_REPAIR_EXECUTION_REPORT_CN.md`

---

## 1. 审查结论

Phase V4A **通过**。

`ltr-readonly-explanation` 的归因已经说明清楚：它属于此前已接受的 LTR-only readonly explanation 最小接入，不是 Phase V4 optional sim 的新增分支。

因此，Phase V4 optional sim 可以进入最终验收确认。

---

## 2. 已确认的事实

已确认：

- `GET /api/tw-stock/ltr-optional-sim-strategies` 是本轮 V4 的真实新增范围；
- `phase1c_ltr_simple_daily` 与 `phase1c_ltr_turnover_controlled_daily` 被同等级展示为 `LTR 模拟策略 A / B`；
- `rank_rotate_top50_adaptive_score` 继续是默认主基线；
- optional sim 路径为只读、GET-only、可选、模拟、非默认、非交易；
- static safety scan 为 `ok=true`；
- E2E network audit 为 `forbidden_request_count=0`；
- `ltr-readonly-explanation` 没有回流 manual review，也没有引入交易、monitor/provider、accepted latest、broker、orders、target position / target weight。

---

## 3. 本轮不再要求的内容

不需要再：

- 改前端；
- 改 API 行为；
- 改 service 逻辑；
- 改 replay 口径；
- 重训 / 调参；
- 新增数据源或联网；
- 增加交易、monitor、provider、accepted latest、broker、orders 路径；
- 调整默认主基线。

本轮只做最终验收，不做扩展。

---

## 4. 最终验收范围

执行者只需提交最终验收确认，内容必须围绕：

1. 本轮最终接入文件清单；
2. 只读与 GET-only 确认；
3. 默认主基线未变化；
4. 两条 LTR 仍是同等级可选模拟策略；
5. `ltr-readonly-explanation` 的归因说明引用到位；
6. static safety scan 结果；
7. E2E/network audit 结果；
8. 回退方式；
9. 最终 gate 建议。

---

## 5. 需要保留的安全边界

最终验收必须继续满足：

- 可选：用户主动选择，不自动启用；
- 模拟：只进入历史模拟语境；
- 只读：不写 provider、accepted latest、monitor、交易或仓位；
- 非默认：不替代 `rank_rotate_top50_adaptive_score`；
- 非交易：不输出买卖、持有、仓位、收益承诺、胜率或上涨概率。

固定边界文案仍必须存在：

```text
仅供只读历史模拟和研究复盘，不构成投资建议，不产生真实交易、委托或仓位。
```

---

## 6. 执行者下一步

请提交：

```text
docs/tw_ltr_strategy_validation/PHASEV4_FINAL_ACCEPTANCE_EXECUTION_REPORT_CN.md
```

报告必须说明：

- V4 optional sim 最终文件清单；
- `ltr-readonly-explanation` 的既有归因；
- `ltr-optional-sim-strategies` 的本轮新增归因；
- 只读 / GET-only / non-default / non-trading 结论；
- static safety scan 结果；
- E2E/network audit 结果；
- 回退路径；
- gate 建议。

---

## 7. Phase V4 最终 Gate

如果最终验收确认通过：

```text
optional_sim_strategy_accepted_readonly_non_default
```

如果执行者发现任何写入、默认切换、交易语义或边界不清：

```text
rollback_to_readonly_explanation_only
```

如果用户认为 optional sim 的产品价值不足以继续保留：

```text
archive_strategy_validation
```
