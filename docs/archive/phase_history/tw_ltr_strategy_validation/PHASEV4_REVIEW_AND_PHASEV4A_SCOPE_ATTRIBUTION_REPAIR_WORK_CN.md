# Phase V4 审查意见与 Phase V4A 范围归因修复工作文档

生成时间：2026-06-14

主线依据：`docs/tw_ltr_strategy_validation/LTR_STRATEGY_VALIDATION_MAINLINE_CN.md`

审查入口：`docs/tw_ltr_strategy_validation/PHASEV4_MIN_OPTIONAL_SIM_IMPLEMENTATION_EXECUTION_REPORT_CN.md`

---

## 1. 审查结论

Phase V4 **暂不直接验收**。

不是因为已发现可选模拟策略本身存在交易或写入越界，而是因为本轮代码范围归因不够清楚，需要执行者先补一轮 Phase V4A 窄修复报告。

当前 gate：

```text
request_phasev4a_scope_attribution_repair
```

不得直接进入最终接受、后续优化或新功能扩展。

---

## 2. 已通过的部分

围绕 V4 optional sim 的核心路径，当前证据支持“只读、GET-only、非默认、非交易”：

- 新增 `GET /api/tw-stock/ltr-optional-sim-strategies`；
- 前端 API `getTwStockLTROptionalSimStrategies()` 使用 `method: 'get'`；
- 服务 `TWLTROptionalSimStrategyService` 只读取本地 Phase V2 artifacts；
- 默认选中仍是 `rank_rotate_top50_adaptive_score`；
- `phase1c_ltr_simple_daily` 与 `phase1c_ltr_turnover_controlled_daily` 同等级展示为 `LTR 模拟策略 A / B`；
- static safety scan 复核通过；
- E2E network audit 产物显示 forbidden request 为 0。

复核产物：

```text
data_tw/experiments/ltr_strategy_validation/phasev4_min_optional_sim/phasev4_static_safety_scan.json
data_tw/experiments/ltr_strategy_validation/phasev4_min_optional_sim/phasev4_e2e_network_audit.json
```

关键计数为：

```text
forbidden_request_count = 0
monitor_config_write_count = 0
monitor_scan_post_count = 0
monitor_alerts_write_count = 0
ops_dry_run_post_count = 0
broker / quick-trade / orders = 0
provider refresh / publish = 0
accepted latest switching = 0
target position / target weight = 0
```

---

## 3. 阻塞问题

### Finding 1：V4 报告覆盖不完整，代码 diff 中混入 `ltr-readonly-explanation`

严重级别：Medium

V4 执行报告声称本轮目标是：

```text
仅把 V3 冻结的两条同等级 LTR 可选模拟策略接入为只读历史模拟展示
```

但当前相关 diff 中同时出现了：

```text
GET /api/tw-stock/ltr-readonly-explanation
getTwStockLTRReadonlyExplanation()
ltr-readonly-explanation-panel
loadLtrReadonlyExplanation()
```

这些内容不是 V4 optional sim 的最小必要实现项。它们可能来自此前已接受的 LTR readonly explanation 主线，也可能是本轮一起混入的实现。由于 V4 报告没有说明其归属，审查者无法确认本轮是否严格只做了 V4 optional sim。

这不是立即判定越权，但属于范围归因不清，必须先修复报告证据。

---

## 4. 安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：V4 报告未解释 `ltr-readonly-explanation` 相关 diff 的归属，范围归因不清。
- Low：无实质问题。

### 当前判断

未发现 optional sim 路径触发：

- POST / PUT / PATCH / DELETE 写请求；
- provider refresh / publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 买卖、持有、仓位、收益承诺、胜率或上涨概率语义。

但在范围归因修复前，不给出最终验收 gate。

---

## 5. Phase V4A 唯一目标

只做一件事：

```text
解释并修复 Phase V4 实现范围归因，证明本轮 optional sim 没有夹带新增分支。
```

Phase V4A 不是功能扩展轮次。

---

## 6. Phase V4A 允许事项

允许执行者提交一个窄报告：

```text
docs/tw_ltr_strategy_validation/PHASEV4A_SCOPE_ATTRIBUTION_REPAIR_EXECUTION_REPORT_CN.md
```

报告必须说明：

1. `ltr-readonly-explanation` 相关 route/API/panel/service/test 是哪一轮引入的；
2. 它是否属于此前已接受的 LTR readonly explanation 最小接入；
3. 它是否在本轮 V4 被新增、修改或扩展；
4. 如果是本轮新增，为什么没有列入 V4 报告；
5. 如果不是本轮新增，请给出文件级归因说明；
6. V4 optional sim 的真实最小改动清单；
7. 是否仍满足 V4 只读、可选、模拟、非默认、非交易边界；
8. 是否没有 manual review explanation 回流；
9. 是否没有新增交易、monitor、provider、accepted latest、broker、orders 或 target position / target weight 路径；
10. 是否需要修改 V4 执行报告，补充遗漏的范围说明。

---

## 7. Phase V4A 禁止事项

本轮禁止：

- 新增功能；
- 修改前端展示逻辑；
- 修改 API 行为；
- 新增策略入口；
- 新增数据源；
- 联网；
- 重训或调参；
- 改 replay 口径；
- 默认启用 LTR；
- 替换 Top50 自适应主基线；
- provider refresh / publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 买卖、持有、仓位、收益承诺、胜率或上涨概率语义。

如果执行者认为必须改代码才能修复，请先说明原因，等待审查者和用户确认。

---

## 8. Phase V4A 需要提交的证据

执行者必须提交：

```text
docs/tw_ltr_strategy_validation/PHASEV4A_SCOPE_ATTRIBUTION_REPAIR_EXECUTION_REPORT_CN.md
```

并附：

- `git diff --name-only` 中与 V4 optional sim 相关的文件列表；
- optional sim endpoint/panel 的 scoped diff 说明；
- `ltr-readonly-explanation` 相关文件归属说明；
- static safety scan 最新结果；
- network audit 最新结果或说明为什么沿用 V4 结果即可；
- 是否修改了 `PHASEV4_MIN_OPTIONAL_SIM_IMPLEMENTATION_EXECUTION_REPORT_CN.md`。

---

## 9. Phase V4A Gate

如果执行者证明 `ltr-readonly-explanation` 是此前已接受范围，且 V4 optional sim 没有夹带新增分支：

```text
return_to_phasev4_final_acceptance_review
```

如果执行者确认 `ltr-readonly-explanation` 是本轮未申报新增范围，但仍属于已允许的只读 LTR explanation，需要补充 V4 报告后再审：

```text
repair_phasev4_report_scope_and_resubmit
```

如果发现本轮夹带 manual review、交易、monitor/provider 写入、默认切换或其他主线外功能：

```text
stop_and_discuss_with_user
```
