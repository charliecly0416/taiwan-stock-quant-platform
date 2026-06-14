# Phase V3 用户第一性产品化设计执行报告

生成时间：2026-06-14

## 1. 本轮目标

本轮依据 `docs/tw_ltr_strategy_validation/PHASEV2_REVIEW_AND_PHASEV3_USER_FIRST_PRODUCT_DESIGN_WORK_CN.md`，只冻结 LTR 可选模拟策略的用户第一性产品化契约。

本轮只做设计文档，未修改前端、未修改 API、未新增策略入口、未新增后端 route、未新增真实功能代码、未改 replay 口径、未重训、未调参、未联网、未新增数据源、未触发 provider / accepted latest / monitor / 交易链路。

## 2. Phase V2 证据摘要

Phase V2 已完成 rolling 6M/12M、市况分段、walk-forward OOS、label-shuffle sanity check 与 feature leakage scan。

支持进入产品契约设计的证据：

| 证据 | 结论 |
| --- | --- |
| walk-forward OOS 2025-06-25..2025-12-31 | `phase1c_ltr_simple_daily` 相对 Top50 自适应收益差为 `+0.214523` |
| walk-forward OOS 2026-01-01..2026-05-07 | `phase1c_ltr_simple_daily` 相对 Top50 自适应收益差为 `+0.077563` |
| label-shuffle sanity | `completed`，`pass` |
| feature leakage scan | `pass`，`blocked_fields` 为空 |
| turnover-controlled LTR | 呈现低动作、低回撤倾向，但不在本轮降级为次要策略 |

必须保留的限制：

- `walk_forward_mode = frozen_score_oos_replay_only`，不是重新训练式 walk-forward。
- LTR simple 在 OOS 两段中相对收益为正，但最大回撤略差。
- risk_off 分段中 LTR simple 相对 Top50 自适应不占优。
- rolling 与 regime 中大量样本仍为 train / validation / mixed，不能作为独立样本外背书。
- 2025 年度聚合和 2026 YTD 聚合不能整体视为 independent_test。
- Phase V3 不比较两条 LTR 策略强弱，不做高低排序。

## 3. 产品定位

### 3.1 LTR simple

`phase1c_ltr_simple_daily` 进入产品契约设计，但定位只能是：

```text
可选模拟策略候选 / 研究验证策略 / 历史复盘策略
```

不得定位为：

```text
推荐策略 / 更优策略 / 默认策略 / 交易策略
```

中性展示名建议：

```text
LTR 模拟策略 A
```

辅助说明：

```text
基于冻结 LTR 分数的历史模拟候选，用于只读复盘比较。
```

### 3.2 Turnover-controlled LTR

`phase1c_ltr_turnover_controlled_daily` 同等级进入产品契约设计，定位只能是：

```text
可选模拟策略候选 / 研究验证策略 / 历史复盘策略
```

不得因当前收益牺牲而在 Phase V3 降级为次要策略，也不得因低动作/低回撤倾向而包装成防守推荐策略。

中性展示名建议：

```text
LTR 模拟策略 B
```

辅助说明：

```text
基于冻结 LTR 分数和动作约束的历史模拟候选，用于只读复盘比较。
```

## 4. 默认基线关系

`rank_rotate_top50_adaptive_score` 继续是默认主基线。

产品契约必须保持：

| 策略 | 产品关系 |
| --- | --- |
| `rank_rotate_top50_adaptive_score` | 默认主基线 |
| `phase1c_ltr_simple_daily` | 用户主动选择的可选模拟策略 |
| `phase1c_ltr_turnover_controlled_daily` | 用户主动选择的可选模拟策略 |

LTR 策略不得自动启用，不得替代默认主基线，不得成为默认策略。

## 5. 用户第一性原则判断

| 原则 | 契约要求 |
| --- | --- |
| 简单 | 用户只看到默认基线与两个可选模拟策略，不展示模型训练细节 |
| 准确 | 所有结果必须标注历史模拟、费用后、冻结分数、非重训 walk-forward |
| 清晰 | 首屏区分收益、回撤、动作、样本外限制，不混成单一“好坏”结论 |
| 实用 | 用户只能主动选择进行历史复盘，不能触发交易、仓位或自动执行 |

## 6. 不可破坏边界

Phase V4 及后续实现必须保持五条边界：

| 边界 | 固定要求 |
| --- | --- |
| 可选 | 用户主动选择，不自动启用 |
| 模拟 | 只进入模拟 / 历史验证语境 |
| 只读 | 不写 provider、accepted latest、monitor、交易或仓位 |
| 非默认 | 不替代 `rank_rotate_top50_adaptive_score` |
| 非交易 | 不输出买卖、持有、仓位、收益承诺、胜率或上涨概率 |

固定边界文案必须显示：

```text
仅供只读历史模拟和研究复盘，不构成投资建议，不产生真实交易、委托或仓位。
```

## 7. 展示契约

### 7.1 首屏字段

首屏只允许展示低误读风险字段：

| 字段 | 展示要求 |
| --- | --- |
| 策略名称 | `默认主基线`、`LTR 模拟策略 A`、`LTR 模拟策略 B` |
| 策略状态 | 默认 / 可选模拟 |
| 样本范围 | 明确 train / validation / independent_test / mixed |
| 费用后历史模拟结果 | 必须写“历史模拟”与“费用后” |
| 最大回撤 | 与收益并列展示，不能只展示收益 |
| 动作数 | 展示为历史模拟动作统计，不是交易指令 |
| 是否允许样本外解释 | 显示 true / false 或“仅限 independent_test 切片” |
| 固定边界文案 | 必须在首屏可见 |

首屏不得展示“推荐”“优于”“应选择”“最佳”等排序导向文案。

### 7.2 详情层字段

以下字段只能放在详情层：

| 字段 | 原因 |
| --- | --- |
| rolling 6M / 12M 全窗口结果 | 容易被误读为稳定收益承诺 |
| regime normal / caution / risk_off 分段 | 大量样本为 mixed，不可直接当 OOS |
| relative return / drawdown / actions | 需要上下文解释 |
| label-shuffle sanity 结果 | 审计指标，不适合首屏简化成“通过即安全” |
| feature leakage scan | 审计指标，需保留字段级说明 |
| turnover proxy | 专业字段，需解释其只是历史 notional proxy |
| walk-forward fold 细节 | 必须说明 `frozen_score_oos_replay_only` |

## 8. 禁止文案

产品、前端、API、报告摘要和提示词中都不得出现以下语义：

| 禁止文案或语义 |
| --- |
| 建议买入 |
| 建议卖出 |
| 建议持有 |
| 目标仓位 |
| 目标权重 |
| 预计收益 |
| 胜率 |
| 上涨概率 |
| 自动执行 |
| 替代默认策略 |
| 推荐策略 |
| 更优策略 |
| 最佳策略 |
| 交易策略 |

允许文案必须限定为：

```text
历史模拟、只读复盘、研究验证、可选模拟策略、默认主基线比较。
```

## 9. V4 最小实现范围

若审查者批准进入 V4，最小实现范围必须非常窄：

| 范围 | 允许内容 |
| --- | --- |
| 策略选择 | 只允许用户主动选择 `LTR 模拟策略 A` 或 `LTR 模拟策略 B` 做只读历史复盘 |
| 默认策略 | `rank_rotate_top50_adaptive_score` 不变 |
| 数据 | 只读取 Phase V1/V1B/V2 已有只读产物或同口径只读结果 |
| 展示 | 只展示历史模拟指标、样本范围、风险边界和详情层审计 |
| API | 如需 API，只能 GET，只读，不写业务状态 |
| E2E | 必须包含只读 E2E，证明没有 POST/PUT/PATCH/DELETE、monitor、provider、broker、orders |
| 静态检查 | 必须扫描禁止文案和禁止链路 |
| 回退 | 必须能隐藏 LTR 可选模拟入口，保留默认主基线 |

V4 仍不得：

- 改默认策略；
- 接交易；
- 写 provider / accepted latest / monitor；
- 新增真实订单、仓位或交易语义；
- 做策略推荐或产品默认切换。

## 10. 回退条件

出现任一情况必须回退为只读解释或研究归档：

| 回退条件 |
| --- |
| 前端或 API 文案出现买卖、持有、仓位、收益承诺、胜率、上涨概率语义 |
| LTR 被设为默认策略或替代默认主基线 |
| 出现 provider refresh / publish 或 accepted latest switching |
| 出现 monitor config save / scan / alerts write |
| 出现 broker / quick-trade / orders / target position / target weight |
| V4 只读 E2E 发现写请求 |
| 静态检查发现禁止文案或禁止链路 |
| 后续审查认为 independent_test / walk-forward 证据不足 |
| 后续 label-shuffle 或 leakage scan 失败 |
| 用户无法清楚区分历史模拟与真实交易 |

## 11. Gate 建议

Phase V3 已完成产品化契约设计，且未进入实现。建议下一步 gate：

```text
request_phase_v4_minimal_readonly_optional_simulation_implementation
```

在审查者批准前，不得启动前端/API、策略入口、默认切换或任何写入/交易链路实现。
