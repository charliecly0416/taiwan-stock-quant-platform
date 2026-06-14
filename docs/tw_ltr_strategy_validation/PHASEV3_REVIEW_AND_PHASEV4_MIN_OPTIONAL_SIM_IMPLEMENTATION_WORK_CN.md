# Phase V3 审查意见与 Phase V4 最小可选模拟策略实现工作文档

生成时间：2026-06-14

主线依据：`docs/tw_ltr_strategy_validation/LTR_STRATEGY_VALIDATION_MAINLINE_CN.md`

审查入口：`docs/tw_ltr_strategy_validation/PHASEV3_USER_FIRST_PRODUCT_DESIGN_EXECUTION_REPORT_CN.md`

---

## 1. 审查结论

Phase V3 **通过**，允许进入 Phase V4。

放行范围仅限：

```text
最小可选模拟策略实现与只读验收
```

不得扩展为：

```text
默认策略切换
主推荐替换
交易链路
monitor 写入
provider / accepted latest 写入
新数据源 / 联网 / 重训 / 调参
```

---

## 2. V3 完成度判断

执行者已完成产品契约设计，且符合用户最新要求：

```text
phase1c_ltr_simple_daily
phase1c_ltr_turnover_controlled_daily
```

两条 LTR 策略均被设计为同等级可选模拟策略候选，没有在 Phase V3 区分高低、优劣或主次。

V3 报告明确了：

- 本轮只做设计文档，未改前端/API/后端 route/策略入口；
- `rank_rotate_top50_adaptive_score` 继续是默认主基线；
- 两条 LTR 策略只能由用户主动选择；
- 两条 LTR 策略只能用于历史模拟和研究复盘；
- 首屏、详情层、禁止文案、回退条件和 V4 最小范围均已定义；
- 固定边界文案已给出。

---

## 3. 是否偏离主线

未发现偏离主线。

未发现新增分支。

未发现执行者把 Phase V3 扩展为实现阶段。

未发现把 LTR 包装成：

- 推荐策略；
- 更优策略；
- 默认策略；
- 交易策略；
- 买卖/持有/仓位建议；
- 收益承诺、胜率或上涨概率。

V3 报告中出现的“推荐策略 / 更优策略 / 交易策略 / 买卖 / 仓位 / 收益 / 胜率 / 上涨概率”等词均位于禁止文案或安全边界语境中，不构成越权。

---

## 4. 安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：无实质问题。

### 判断

未发现：

- broker / quick-trade / orders；
- target position / target weight；
- provider refresh / publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- POST/PUT/PATCH/DELETE 写入要求；
- 默认策略切换；
- 新数据源、联网、重训或调参；
- unsafe buy/sell/hold semantics；
- return / win-rate / upside probability promise。

只读安全边界通过。

---

## 5. 必须保留的审查 caveat

Phase V4 可以实现最小只读接入，但不能改变以下事实：

- LTR simple 和 turnover-controlled LTR 暂按同等级策略嵌入，不在本轮排序；
- LTR 仍只是可选模拟策略，不是默认主基线；
- Top50 自适应仍是默认主基线；
- V2 的 walk-forward 是 `frozen_score_oos_replay_only`，不是重新训练式 walk-forward；
- 2025 年度聚合和 2026 YTD 聚合不能整体解释为 independent_test；
- risk_off 分段证据不能包装成 LTR 全市况稳定；
- 产品文案不能声称收益更优、风险更低、胜率更高或上涨概率更大。

---

## 6. Phase V4 唯一目标

只做一件事：

```text
把 V3 冻结的两条同等级 LTR 可选模拟策略，以最小范围接入为只读历史模拟展示，并完成只读验收。
```

Phase V4 不是策略优化轮次，不是调参轮次，不是新数据轮次，也不是交易功能轮次。

---

## 7. Phase V4 允许改动范围

允许在最小必要范围内修改：

- 只读服务层：读取既有 Phase V1/V1B/V2 产物或同口径只读结果；
- 只读 API：如必须新增，只能是 `GET`，不得写任何业务状态；
- 前端展示：只允许增加可选模拟策略展示与只读历史复盘入口；
- 测试：静态检查、只读 API 测试、只读 E2E；
- 文档：执行报告与验收报告。

允许展示的策略关系：

| 策略 | 关系 |
| --- | --- |
| `rank_rotate_top50_adaptive_score` | 默认主基线 |
| `phase1c_ltr_simple_daily` | 同等级可选模拟策略 A |
| `phase1c_ltr_turnover_controlled_daily` | 同等级可选模拟策略 B |

---

## 8. Phase V4 禁止事项

本轮禁止：

- 默认启用 LTR；
- 替换 `rank_rotate_top50_adaptive_score`；
- 输出“推荐策略 / 更优策略 / 最佳策略 / 交易策略”；
- 输出买入、卖出、持有、仓位、目标权重；
- 输出预计收益、胜率、上涨概率；
- 新增 POST/PUT/PATCH/DELETE 写请求；
- provider refresh / publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 新数据源；
- 联网；
- 重训 LTR；
- 调参或改 Phase1C frozen score；
- 改 replay 口径；
- 把 V4 变成策略优劣评选。

---

## 9. Phase V4 产品展示要求

首屏必须保持简单：

- 默认主基线；
- LTR 模拟策略 A；
- LTR 模拟策略 B；
- 样本范围；
- 费用后历史模拟结果；
- 最大回撤；
- 动作数；
- 是否属于 independent_test 切片；
- 固定边界文案。

固定边界文案必须首屏可见：

```text
仅供只读历史模拟和研究复盘，不构成投资建议，不产生真实交易、委托或仓位。
```

首屏不得用颜色、排序、标签或默认勾选暗示：

```text
LTR A 高于 LTR B
LTR B 高于 LTR A
LTR 高于 Top50 自适应
用户应选择某策略
```

---

## 10. Phase V4 验收要求

执行者必须提交：

```text
docs/tw_ltr_strategy_validation/PHASEV4_MIN_OPTIONAL_SIM_IMPLEMENTATION_EXECUTION_REPORT_CN.md
```

报告必须包含：

1. 本轮改动文件清单；
2. 是否只读；
3. 是否只新增或复用 `GET`；
4. 是否没有 POST/PUT/PATCH/DELETE；
5. 是否没有 provider / accepted latest / monitor 写入；
6. 是否没有 broker / quick-trade / orders / target position / target weight；
7. 是否没有新数据源、联网、重训、调参；
8. 是否保持 Top50 自适应默认主基线；
9. 是否把两条 LTR 作为同等级可选模拟策略；
10. 前端首屏截图或 E2E 产物路径；
11. API/network audit 产物路径；
12. 静态禁止文案扫描结果；
13. 只读 E2E 结果；
14. 回退方式；
15. gate 建议。

---

## 11. Phase V4 必须运行的检查

至少运行：

```text
静态禁止文案扫描
只读 API/服务测试
只读 E2E/network audit
```

检查目标：

```text
forbidden_request_count = 0
monitor_config_write_count = 0
monitor_scan_post_count = 0
monitor_alerts_write_count = 0
ops_dry_run_post_count = 0
broker / quick-trade / orders / target-position = 0
provider refresh / publish = 0
accepted latest switching = 0
unsafe buy/sell/hold/position/return/probability semantics = 0
```

---

## 12. Phase V4 Gate

如果实现保持最小、只读、可选、模拟、非默认、非交易，并通过静态检查与只读 E2E：

```text
optional_sim_strategy_accepted_readonly_non_default
```

如果出现文案误导、写请求、默认切换或边界不清：

```text
rollback_to_readonly_explanation_only
```

如果实现复杂度高、用户价值不清或证据不足以产品化：

```text
archive_strategy_validation
```

Phase V4 完成后必须等待审查，不得自动进入后续优化或扩展。
