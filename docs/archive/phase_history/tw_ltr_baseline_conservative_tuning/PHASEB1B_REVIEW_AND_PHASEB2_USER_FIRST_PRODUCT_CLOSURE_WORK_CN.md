# Phase B1B 审查意见与 Phase B2 用户第一性产品化收口工作文档

生成时间：2026-06-14

主线依据：`docs/TW_STOCK_LTR_BASELINE_AND_CONSERVATIVE_TUNING_MAINLINE_CN.md`

审查入口：`docs/tw_ltr_baseline_conservative_tuning/PHASEB1B_DEFAULT_BASELINE_DECISION_REPAIR_EXECUTION_REPORT_CN.md`

---

## 1. 审查结论

Phase B1B **通过**，允许进入 Phase B2。

当前 gate：

```text
phaseb1b_repaired_request_phaseb2_ltr_simple_default_design
```

Phase B2 放行范围仅限：

```text
用户第一性产品化收口：默认展示 LTR simple，Top50 adaptive 与保守候选作为下拉参考策略。
```

不得扩展为：

```text
交易功能
写入链路
收益承诺
新调参
新回放
新数据源
provider / accepted latest / monitor
```

---

## 2. B1B 修复是否成立

B1B 已经修复 B1 的关键问题：

- 明确承认 `phase1c_ltr_simple_daily` 是 B1 回放指标最强的默认主策略候选；
- 不再把 Top50 adaptive 表述为量化效果更优；
- 明确 Top50 adaptive 的优势只是规则更简单、换手略低、解释成本更低、延续当前默认锚点；
- 说明这些优势是产品保守性 tradeoff，不足以否定 LTR simple 的默认候选资格；
- 将默认建议修正为：

```text
default_ltr_simple_with_top50_adaptive_as_rule_based_reference
```

---

## 3. 为什么这次可以接受 LTR simple 做默认设计

B1B 给出的核心证据充分：

| 指标 | Top50 adaptive | LTR simple | 审查判断 |
| --- | ---: | ---: | --- |
| common full range 费用后收益 | `15.963677` | `40.018220` | LTR simple 明显更高 |
| common full range 最大回撤 | `-0.402422` | `-0.387816` | LTR simple 略好 |
| common full range 动作数 | `1932` | `1978` | LTR simple 多 `46` 次，但不构成否决 |
| common full range turnover proxy | `184.497379` | `199.489876` | LTR simple 更高，需标签提示 |
| independent_test 收益 | `2.450848` | `3.550601` | LTR simple 更高 |
| independent_test 回撤 | `-0.167457` | `-0.160298` | LTR simple 略好 |

B1B 还确认：

- LTR simple 在 8 个 period 相对收益均为正；
- 没有发现收益和回撤同时显著失效的切片；
- 动作和换手更高，但幅度不足以压过收益与回撤证据；
- 小白用户第一性下，应优先让用户看到历史回放效果最强的主策略，但必须清楚标注“动作较多、换手较高、历史模拟、不代表未来”。

---

## 4. 是否偏离主线

未发现偏离主线。

未发现执行者在 B1B：

- 跑新回放；
- 新增候选；
- 新调参；
- 重训 LTR；
- 改 Phase1C score；
- 改 replay 口径；
- 新数据源或联网；
- provider refresh / publish；
- accepted latest switching；
- monitor 写入；
- broker / quick-trade / orders；
- target position / target weight；
- 前端/API 改动；
- 买卖、持有、仓位、收益承诺、胜率或上涨概率语义。

---

## 5. 安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：无实质问题。

### Verdict

B1B 只读研究边界通过。

注意：B2 将涉及产品化收口，必须额外做静态文案扫描和只读 E2E/network audit。

---

## 6. Phase B2 唯一目标

只做一件事：

```text
把 B1B 修复后的默认策略结论，以简单、准确、清晰、实用的方式最小化落到产品展示：
默认选中 LTR simple；Top50 adaptive 和两个保守候选作为下拉参考。
```

Phase B2 不是继续研究，不是继续调参，不是新策略开发。

---

## 7. Phase B2 策略展示合同

B2 必须纳入以下 4 个策略：

| strategy_key | 产品定位 | 标签 | 一句话说明 |
| --- | --- | --- | --- |
| `phase1c_ltr_simple_daily` | 默认主策略 | `默认` / `历史回放收益最高` / `动作较多` | 历史回放收益表现最强，动作和换手略高，适合优先查看。 |
| `rank_rotate_top50_adaptive_score` | 规则型参考 | `规则简单` / `换手略低` | 规则更容易理解，历史收益低于默认 LTR，但动作和换手略低。 |
| `phase1c_ltr_conservative_top30_2day_confirm_daily` | 保守参考 | `保守` / `低动作` / `低换手` | 连续确认后才动作，收益低于默认 LTR，但动作明显更少。 |
| `phase1c_ltr_conservative_top20_entry_2day_exit_daily` | 保守参考 | `更严格入选` / `低动作` | 入选更严格，动作明显更少，作为低频参考。 |

B2 默认选中：

```text
phase1c_ltr_simple_daily
```

---

## 8. Phase B2 展示方式要求

必须满足：

- 默认只突出一个主策略；
- 其他策略通过下拉框或单选切换；
- 不平铺一大堆卡片；
- 首屏展示：策略标签、一句话说明、费用后历史模拟收益、最大回撤、动作数、换手 proxy、样本范围；
- 详情层展示：年度、validation、independent_test、full range 明细；
- 文案必须强调“历史模拟 / 只读复盘 / 不构成投资建议 / 不产生交易或仓位”。

固定边界文案必须显示：

```text
仅供只读历史模拟和研究复盘，不构成投资建议，不产生真实交易、委托或仓位。
```

---

## 9. Phase B2 禁止文案

不得出现：

- 建议买入；
- 建议卖出；
- 建议持有；
- 目标仓位；
- 目标权重；
- 预计收益；
- 胜率；
- 上涨概率；
- 自动执行；
- 替代人工判断；
- 保证收益；
- 推荐买哪支股票。

允许表达：

- 历史回放收益最高；
- 历史模拟；
- 费用后；
- 最大回撤；
- 动作较多；
- 换手略高；
- 规则型参考；
- 保守低频参考。

---

## 10. Phase B2 技术范围

允许在最小范围内修改：

- 只读服务层或既有 optional sim payload 映射；
- GET-only API；
- 前端只读展示，下拉/单选切换；
- 静态安全扫描；
- 只读 E2E / network audit；
- 文档和验收报告。

禁止：

- POST / PUT / PATCH / DELETE 写请求；
- provider refresh / publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 新数据源；
- 联网；
- 重训 / 调参；
- 改 replay 口径；
- 新增真实交易、仓位或订单语义。

---

## 11. Phase B2 必须运行的检查

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

## 12. Phase B2 执行报告要求

执行者必须提交：

```text
docs/tw_ltr_baseline_conservative_tuning/PHASEB2_USER_FIRST_PRODUCT_CLOSURE_EXECUTION_REPORT_CN.md
```

报告必须包含：

1. 本轮目标；
2. 改动文件清单；
3. 默认策略是否为 `phase1c_ltr_simple_daily`；
4. 下拉参考策略清单；
5. 是否保持只读 / GET-only；
6. 是否无 provider / accepted latest / monitor / broker / orders；
7. 是否无仓位、买卖、收益承诺、胜率、上涨概率语义；
8. 前端展示截图或 E2E artifact 路径；
9. static safety scan 结果；
10. E2E/network audit 结果；
11. 回退路径；
12. gate 建议。

---

## 13. Phase B2 Gate

如果产品收口简单、准确、清晰、实用，并通过只读安全验收：

```text
phaseb2_ltr_simple_default_readonly_product_closure_accepted
```

如果实现复杂、文案误导、默认策略不清或用户价值不足：

```text
rollback_to_top50_adaptive_default_with_ltr_reference_only
```

如果出现写链路、交易语义、provider/accepted latest/monitor 越界：

```text
stop_and_discuss_with_user
```
