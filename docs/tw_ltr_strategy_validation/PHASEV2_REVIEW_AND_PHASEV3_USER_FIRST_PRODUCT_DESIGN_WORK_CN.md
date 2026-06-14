# Phase V2 审查意见与 Phase V3 用户第一性产品化设计工作文档

生成时间：2026-06-14

主线依据：`docs/tw_ltr_strategy_validation/LTR_STRATEGY_VALIDATION_MAINLINE_CN.md`

审查入口：`docs/tw_ltr_strategy_validation/PHASEV2_COMPREHENSIVE_STABILITY_EXECUTION_REPORT_CN.md`

---

## 1. 审查结论

Phase V2 **通过**，允许进入 Phase V3 用户第一性产品化设计。

放行范围只到：

```text
产品化契约设计
```

不得直接进入：

```text
前端/API 实现
策略入口实现
默认策略切换
交易或写入链路
```

---

## 2. V2 验证完成度

执行者已完成 Phase V2 要求的五块验证：

- rolling 6M / 12M 稳定性验证；
- 市况分段验证；
- walk-forward out-of-sample validation；
- label-shuffle sanity check；
- feature leakage scan。

产物已存在：

```text
data_tw/experiments/ltr_strategy_validation/phasev2_comprehensive_stability/phasev2_rolling_6m_12m.csv
data_tw/experiments/ltr_strategy_validation/phasev2_comprehensive_stability/phasev2_regime_segments.csv
data_tw/experiments/ltr_strategy_validation/phasev2_comprehensive_stability/phasev2_walk_forward_oos.csv
data_tw/experiments/ltr_strategy_validation/phasev2_comprehensive_stability/phasev2_label_shuffle_sanity.csv
data_tw/experiments/ltr_strategy_validation/phasev2_comprehensive_stability/phasev2_feature_leakage_scan.csv
data_tw/experiments/ltr_strategy_validation/phasev2_comprehensive_stability/phasev2_gate_summary.json
```

`phasev2_gate_summary.json` 给出的 gate 为：

```text
request_phase_v3_user_first_product_design
```

---

## 3. 核心证据判断

### 3.1 支持进入 V3 设计的证据

LTR simple 在 independent-test walk-forward 两段中相对 Top50 自适应有正收益差：

- `2025-06-25..2025-12-31`：相对收益差约 `+0.214523`
- `2026-01-01..2026-05-07`：相对收益差约 `+0.077563`

label-shuffle sanity check：

```text
label_shuffle_status = completed
sanity_conclusion = pass
```

feature leakage scan：

```text
feature_leakage_scan_status = pass
blocked_fields = empty
```

说明当前证据足以进入“是否可作为可选模拟策略”的产品契约设计。

按用户最新确认，Phase V3 暂时将：

```text
phase1c_ltr_simple_daily
phase1c_ltr_turnover_controlled_daily
```

作为同等级可选模拟策略候选嵌入设计，不在本轮区分高低、优劣或主次。后续如需比较强弱，必须另起调优或验证轮次。

### 3.2 必须保留的 caveat

这些结果不能被包装成默认策略或收益承诺：

- `walk_forward_mode = frozen_score_oos_replay_only`，不是重新训练式 walk-forward；
- LTR simple 在 OOS 两段中相对收益为正，但最大回撤略差；
- risk_off 分段中 LTR simple 相对 Top50 自适应不占优；
- turnover-controlled LTR 当前保留其低动作、低回撤倾向的观察，但不得因此在 Phase V3 降级为次要策略；
- Phase V3 暂不对 LTR simple 与 turnover-controlled LTR 做高低排序；
- rolling 与 regime 中大量样本仍为 train/validation/mixed，不得作为独立样本外背书；
- 2025 年度聚合和 2026 YTD 聚合不能整体视为 independent_test。

---

## 4. 安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：无实质问题。

### 判断

未发现：

- 重训 LTR；
- 调参；
- 改候选策略；
- 改 Phase1C score；
- 改 replay 口径；
- 新增数据源；
- 联网；
- provider refresh/publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 前端/API 改动；
- 产品化实现；
- 买卖、仓位、收益承诺、胜率或上涨概率语义。

只读研究边界通过。

---

## 5. Phase V3 本轮唯一目标

只做一件事：

```text
基于 Phase V2 证据，
冻结 LTR 可选模拟策略的用户第一性产品化契约。
```

Phase V3 只设计，不实现。

---

## 6. Phase V3 允许改动范围

允许新增文档：

```text
docs/tw_ltr_strategy_validation/PHASEV3_USER_FIRST_PRODUCT_DESIGN_EXECUTION_REPORT_CN.md
```

允许内容：

- 判断 LTR 是否应进入可选模拟策略；
- 设计可选模拟策略展示契约；
- 设计用户文案；
- 设计只读安全边界；
- 设计最小前端/API 接入范围；
- 设计验收和回退条件；
- 明确两条 LTR 策略均作为同等级可选模拟策略候选进入产品契约设计。

允许引用：

- Phase V1 年度结果；
- Phase V1B split-aware 修复；
- Phase V2 rolling / regime / walk-forward / shuffle / leakage 结果。

---

## 7. Phase V3 禁止事项

本轮禁止：

- 修改前端；
- 修改 API；
- 新增策略入口；
- 新增后端 route；
- 新增真实功能代码；
- 修改 replay 口径；
- 重训；
- 调参；
- 新数据源；
- 联网；
- provider refresh/publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 把 LTR 设为默认；
- 替代 `rank_rotate_top50_adaptive_score` 主基线；
- 输出买卖、持有、仓位建议；
- 输出收益承诺、胜率承诺或上涨概率。

---

## 8. Phase V3 必须回答的问题

执行者必须明确回答：

1. 如何将 `phase1c_ltr_simple_daily` 作为同等级可选模拟策略候选纳入设计；
2. 如何将 `phase1c_ltr_turnover_controlled_daily` 作为同等级可选模拟策略候选纳入设计；
3. 两条 LTR 策略在用户界面中如何中性命名，避免暗示一条高于另一条；
4. `rank_rotate_top50_adaptive_score` 是否继续是默认主基线；
5. LTR 可选策略是否只允许用户主动选择；
6. LTR 可选策略是否只能用于历史模拟和人工复盘；
7. 哪些指标允许首屏展示；
8. 哪些高风险指标只能放在详情层；
9. 哪些文案必须固定显示；
10. 什么情况下必须回退为只读解释或研究归档。

---

## 9. Phase V3 产品契约必须满足

### 9.1 五个不可破坏的边界

必须保持：

- 可选：用户主动选择，不自动启用；
- 模拟：只进入模拟/历史验证语境；
- 只读：不写 provider、accepted latest、monitor、交易或仓位；
- 非默认：不替代 `rank_rotate_top50_adaptive_score`；
- 非交易：不输出买卖、持有、仓位、收益承诺、胜率或上涨概率。

### 9.2 默认策略关系

必须明确：

```text
rank_rotate_top50_adaptive_score 继续是默认主基线。
```

LTR 只能作为：

```text
可选模拟策略 / 研究验证策略 / 历史复盘策略
```

不得写成：

```text
推荐策略 / 更优策略 / 默认策略 / 交易策略
```

### 9.3 文案要求

必须包含固定边界文案：

```text
仅供只读历史模拟和研究复盘，不构成投资建议，不产生真实交易、委托或仓位。
```

必须避免：

- “建议买入”
- “建议卖出”
- “目标仓位”
- “预计收益”
- “胜率”
- “上涨概率”
- “自动执行”
- “替代默认策略”

---

## 10. Phase V3 必须给出 V4 最小实现范围

如果 Phase V3 建议进入 V4，必须冻结 V4 最小实现范围。

V4 范围必须非常窄：

- 只允许可选模拟策略选择；
- 只允许只读历史验证展示；
- 不改变默认策略；
- 不接交易；
- 不写 provider / accepted latest / monitor；
- 不新增真实订单、仓位或交易语义；
- 必须有静态检查；
- 必须有只读 E2E；
- 必须有回退方案。

---

## 11. Phase V3 执行报告必须包含

执行者必须提交：

```text
docs/tw_ltr_strategy_validation/PHASEV3_USER_FIRST_PRODUCT_DESIGN_EXECUTION_REPORT_CN.md
```

报告必须包含：

1. 本轮目标；
2. 是否只做设计、未改代码；
3. Phase V2 证据摘要；
4. LTR simple 的产品定位；
5. turnover-controlled LTR 的产品定位；
6. Top50 自适应默认基线关系；
7. 用户第一性原则判断；
8. 可选 / 模拟 / 只读 / 非默认 / 非交易边界；
9. 首屏字段设计；
10. 详情层字段设计；
11. 禁止文案；
12. V4 最小实现范围；
13. 回退条件；
14. gate 建议。

---

## 12. Phase V3 Gate

如果产品契约清楚、边界可验收、且不会破坏默认主基线：

```text
request_phase_v4_min_optional_sim_strategy_implementation
```

如果证据不足、契约复杂、用户价值不清或边界难以验收：

```text
keep_readonly_explanation_only
```

或：

```text
archive_strategy_validation
```

不得在 Phase V3 后直接跳过审查进入实现。
