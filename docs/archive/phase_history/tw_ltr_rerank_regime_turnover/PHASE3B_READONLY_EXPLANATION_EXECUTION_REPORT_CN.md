# Phase3B Readonly Explanation 执行报告

生成时间：2026-06-14

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

执行依据：`docs/tw_ltr_rerank_regime_turnover/PHASE3A2C_REVIEW_AND_PHASE3B_READONLY_EXPLANATION_WORK_CN.md`

## 1. 本轮目标

本轮只把 Phase3A2C 的六方法同口径回放结果整理成只读解释字段草案，让审查者可以评估解释层是否简单、准确、清晰、实用。

本轮未进入前端、API、backend service、monitor、database、provider 或任何交易相关模块。

## 2. 使用的 Phase3A2C 输入产物

- `phase3a2_method_comparison.csv`
- `phase3a2_period_comparison.csv`
- `phase3a2_actions_summary.csv`
- `phase3a2_data_quality.csv`
- `phase3a2_gate_summary.json`
- `PHASE3A2C_LOOKAHEAD_METRIC_REPAIR_EXECUTION_REPORT_CN.md`

这些输入均为 Phase3A2C 已生成产物。本轮没有读取新数据源，没有联网，没有重新计算模型分数，没有训练模型。

## 3. 本轮新增产物

- `docs/tw_ltr_rerank_regime_turnover/PHASE3B_READONLY_EXPLANATION_SCHEMA_CN.md`
- `docs/tw_ltr_rerank_regime_turnover/PHASE3B_READONLY_EXPLANATION_EXECUTION_REPORT_CN.md`

## 4. 解释字段设计

字段草案固定为：

```text
method_key
method_label
research_role
net_return_summary
drawdown_summary
action_count_summary
turnover_summary
relative_to_top50_adaptive
why_more_aggressive
why_more_conservative
why_no_action
data_quality_note
readonly_disclaimer
```

设计原则：

- `net_return_summary` 只描述历史回放费用后净值变化；
- `drawdown_summary` 只描述历史回放最大回撤；
- `action_count_summary` 和 `turnover_summary` 只描述动作次数与 notional turnover proxy；
- `relative_to_top50_adaptive` 只描述历史回放差异；
- `why_no_action` 只围绕市况、排名差距、换手预算、持有期、价格缺失或数据质量；
- `readonly_disclaimer` 固定说明只读研究边界。

## 5. 每个方法的 Research Role

| method_key | method_label | research_role |
| --- | --- | --- |
| rank_rotate_top30 | Top30 rank rotation | baseline |
| rank_rotate_top50 | Top50 rank rotation | baseline |
| rank_rotate_top50_adaptive_score | Top50 adaptive score | baseline |
| confirmed_exit | Confirmed exit review | risk_review_reference |
| phase1c_ltr_simple_daily | Phase1C LTR simple daily | aggressive_rerank_research |
| phase1c_ltr_turnover_controlled_daily | Phase1C LTR turnover controlled daily | turnover_control_research |

## 6. 示例解释

示例解释已写入 `PHASE3B_READONLY_EXPLANATION_SCHEMA_CN.md`，共 3 条：

- Top50 adaptive score：作为 Phase3B 解释层对照 baseline；
- Phase1C LTR simple daily：作为更激进的 LTR 研究参考；
- Phase1C LTR turnover controlled daily：作为换手控制研究参考。

示例均只使用 Phase3A2C common full range 的费用后净值变化、最大回撤、动作次数、turnover proxy、共同日期集合和 price audit 摘要。

## 7. 禁止语义自查结果

本轮新增文档未把任何方法表述为未来效果判断，未把 qlib score 或 LTR score 表述为收益率、概率或配置比例。

本轮解释文案只使用：

- 历史回放；
- 只读研究；
- 观察顺序；
- 动作次数；
- 换手较高 / 较低；
- 回撤较高 / 较低；
- 费用后净值；
- 人工复盘。

## 8. 安全边界声明

本轮未执行：

- 前端或 API 接入；
- backend service 修改；
- monitor / database 修改；
- 新数据源读取；
- 联网；
- provider refresh / publish；
- accepted latest switching；
- LTR 训练；
- Phase1C frozen score 重建；
- 券商连接、快速交易或订单提交相关工作。

本轮产物只用于离线审查和只读解释设计。

## 9. 验证命令与结果

- 字段来源核对：通过，字段均来自 Phase3A2C 已有产物或固定离线映射。
- 新数据源核对：通过，未引入新数据源。
- 联网核对：通过，未执行联网命令。
- 产品链路核对：通过，未修改 frontend / API / backend service。
- 文案边界核对：通过，未把 score 表述为收益率、概率或配置比例。
- 安全边界核对：通过，未新增真实交易执行路径。

## 10. 是否需要进入下一轮前端/API 只读接入审查

需要审查者另行决定。

当前 Phase3B 只完成 readonly explanation scope 文档与最小解释数据设计，不授权直接接入前端或 API。若后续要产品化展示，应由审查者单独给出下一轮只读接入步骤文档，并补充 API / 前端 E2E 验收口径。
