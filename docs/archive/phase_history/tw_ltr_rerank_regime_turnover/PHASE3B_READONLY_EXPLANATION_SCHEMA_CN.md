# Phase3B 只读解释字段草案

生成时间：2026-06-14

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

本字段草案只服务于离线审查，不接前端、不接 API、不接主推荐。

## 1. 输入来源

字段只允许来自 Phase3A2C 已生成产物：

- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_method_comparison.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_period_comparison.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_actions_summary.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_data_quality.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_gate_summary.json`
- `docs/tw_ltr_rerank_regime_turnover/PHASE3A2C_LOOKAHEAD_METRIC_REPAIR_EXECUTION_REPORT_CN.md`

不读取新数据源，不重新计算模型分数，不训练模型。

## 2. 字段定义

| field | type | 来源 | 说明 |
| --- | --- | --- | --- |
| method_key | string | method_comparison.method | 方法稳定键 |
| method_label | string | 离线映射 | 用户可读名称 |
| research_role | enum | 离线映射 | 只能是 baseline / aggressive_rerank_research / turnover_control_research / risk_review_reference |
| net_return_summary | string | method_comparison.fee_tax_adjusted_net_return | 只描述历史回放费用后净值变化 |
| drawdown_summary | string | method_comparison.max_drawdown | 只描述历史回放最大回撤 |
| action_count_summary | string | method_comparison.action_count | 只描述历史回放动作次数 |
| turnover_summary | string | method_comparison.turnover_proxy_by_notional_over_avg_equity | 只描述 notional / average equity proxy |
| relative_to_top50_adaptive | string | method_comparison.delta_vs_rank_rotate_top50_adaptive_score | 只描述相对 Top50 adaptive 的历史回放差异 |
| why_more_aggressive | string | method_comparison + actions_summary | 解释动作更密集或 turnover proxy 更高的原因 |
| why_more_conservative | string | method_comparison + actions_summary | 解释动作更少或回撤更低的原因 |
| why_no_action | string | data_quality + 策略约束说明 | 只允许围绕市况、排名差距、换手预算、持有期、价格缺失或数据质量 |
| data_quality_note | string | data_quality + gate_summary | 说明共同日期集合、缺分日期、price audit |
| readonly_disclaimer | string | 固定文案 | 明确只读研究，不产生交易动作、订单或配置比例 |

## 3. Research Role 映射

| method_key | method_label | research_role | 角色说明 |
| --- | --- | --- | --- |
| rank_rotate_top30 | Top30 rank rotation | baseline | 较窄候选池 baseline |
| rank_rotate_top50 | Top50 rank rotation | baseline | 较宽候选池 baseline |
| rank_rotate_top50_adaptive_score | Top50 adaptive score | baseline | Phase3B 的主要对照 baseline |
| confirmed_exit | Confirmed exit review | risk_review_reference | 偏风险复盘与低动作参考 |
| phase1c_ltr_simple_daily | Phase1C LTR simple daily | aggressive_rerank_research | 更激进的 LTR 研究参考 |
| phase1c_ltr_turnover_controlled_daily | Phase1C LTR turnover controlled daily | turnover_control_research | 换手控制研究参考 |

## 4. 示例解释

### 示例 1：Top50 adaptive score

```json
{
  "method_key": "rank_rotate_top50_adaptive_score",
  "method_label": "Top50 adaptive score",
  "research_role": "baseline",
  "net_return_summary": "common full range 历史回放费用后净值变化为 15.963677。",
  "drawdown_summary": "common full range 历史回放最大回撤为 -0.402422。",
  "action_count_summary": "common full range 历史回放动作次数为 1932。",
  "turnover_summary": "turnover proxy 为 184.497379。",
  "relative_to_top50_adaptive": "这是 Phase3B 解释层的对照 baseline。",
  "why_more_aggressive": "不适用；该方法作为对照 baseline。",
  "why_more_conservative": "不适用；该方法作为对照 baseline。",
  "why_no_action": "若无动作，解释应优先检查 adaptive score 门槛、候选差距、持有期和数据质量。",
  "data_quality_note": "common full range 使用 1043 个共同回放日，price audit sample_count=240、bad_count=0、max_days_to_execution=3。",
  "readonly_disclaimer": "只读研究解释，不是交易建议，不产生交易动作、订单或配置比例。"
}
```

### 示例 2：Phase1C LTR simple daily

```json
{
  "method_key": "phase1c_ltr_simple_daily",
  "method_label": "Phase1C LTR simple daily",
  "research_role": "aggressive_rerank_research",
  "net_return_summary": "common full range 历史回放费用后净值变化为 40.018220。",
  "drawdown_summary": "common full range 历史回放最大回撤为 -0.387816。",
  "action_count_summary": "common full range 历史回放动作次数为 1978。",
  "turnover_summary": "turnover proxy 为 199.489876。",
  "relative_to_top50_adaptive": "相对 Top50 adaptive 的历史回放费用后净值差异为 24.054543，同时 turnover proxy 更高。",
  "why_more_aggressive": "LTR simple daily 更直接跟随 rerank 结果，动作次数和 turnover proxy 均处于高位。",
  "why_more_conservative": "不适用；该方法定位为更激进的研究参考。",
  "why_no_action": "若无动作，解释应检查 rerank 差距不足、持有期限制、价格缺失或共同日期集合限制。",
  "data_quality_note": "common full range 使用 1043 个共同回放日，缺分日期已从所有方法统一排除。",
  "readonly_disclaimer": "只读研究解释，不是交易建议，不产生交易动作、订单或配置比例。"
}
```

### 示例 3：Phase1C LTR turnover controlled daily

```json
{
  "method_key": "phase1c_ltr_turnover_controlled_daily",
  "method_label": "Phase1C LTR turnover controlled daily",
  "research_role": "turnover_control_research",
  "net_return_summary": "common full range 历史回放费用后净值变化为 4.652725。",
  "drawdown_summary": "common full range 历史回放最大回撤为 -0.199269。",
  "action_count_summary": "common full range 历史回放动作次数为 315。",
  "turnover_summary": "turnover proxy 为 31.849293。",
  "relative_to_top50_adaptive": "相对 Top50 adaptive 的历史回放费用后净值差异为 -11.310952，同时动作次数、turnover proxy 和回撤绝对值更低。",
  "why_more_aggressive": "不适用；该方法定位为换手控制研究参考。",
  "why_more_conservative": "滚动动作预算、持有期和 turnover 控制使动作明显减少。",
  "why_no_action": "若无动作，解释应优先检查最近 10 个交易日动作预算、最短持有期、排名差距和共同日期集合。",
  "data_quality_note": "common full range 使用 1043 个共同回放日，price audit 未发现执行日异常样本。",
  "readonly_disclaimer": "只读研究解释，不是交易建议，不产生交易动作、订单或配置比例。"
}
```

## 5. 文案边界

- 只能说“历史回放”“只读研究”“观察顺序”“动作次数”“换手较高 / 较低”“回撤较高 / 较低”“费用后净值”“人工复盘”。
- 不能把 qlib score 或 LTR score 解释为收益率、概率或配置比例。
- 不能把任何 method 包装成未来效果判断。

## 6. 下一轮接入前置条件

若后续要接入前端或 API，必须先由审查者另写步骤文档，并补充只读 E2E 验收。当前文档不授权产品接入。
