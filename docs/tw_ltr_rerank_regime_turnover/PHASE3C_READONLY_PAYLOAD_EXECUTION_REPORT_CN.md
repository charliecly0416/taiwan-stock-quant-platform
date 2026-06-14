# Phase3C Readonly Payload 执行报告

生成时间：2026-06-14

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

执行依据：`docs/tw_ltr_rerank_regime_turnover/PHASE3B_REVIEW_AND_PHASE3C_READONLY_PAYLOAD_WORK_CN.md`

## 1. 本轮目标

本轮只把 Phase3B 的解释字段草案物化成固定结构的只读 explanation payload artifact，供后续前端/API 接入审查使用。

本轮不是前端实现，不是 API 接入，不是页面联调，不是推荐层，也不是策略再评估。

## 2. 输入产物清单

- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_method_comparison.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_data_quality.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_gate_summary.json`
- `docs/tw_ltr_rerank_regime_turnover/PHASE3B_READONLY_EXPLANATION_SCHEMA_CN.md`
- `docs/tw_ltr_rerank_regime_turnover/PHASE3B_READONLY_EXPLANATION_EXECUTION_REPORT_CN.md`

本轮没有读取新数据源，没有联网，没有重新计算模型分数，没有重新回放，没有训练模型。

## 3. Payload 路径

- `data_tw/experiments/ltr_rerank_regime_turnover/phase3c_readonly_explanation_payload/phase3c_readonly_explanation_payload.json`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3c_readonly_explanation_payload/phase3c_method_role_mapping.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3c_readonly_explanation_payload/PHASE3C_READONLY_PAYLOAD_CONTRACT_CN.md`

## 4. Payload Schema

Top-level schema：

```text
schema_version
created_at
as_of_scope
data_quality
methods[]
summary_notes[]
readonly_disclaimer
safety_boundary
```

`methods[]` schema：

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
source_trace
```

## 5. 每个方法的示例 Payload

```json
[
  {
    "method_key": "rank_rotate_top30",
    "method_label": "Top30 rank rotation",
    "research_role": "baseline",
    "net_return_summary": "common full range 历史回放费用后净值变化约为 +978.51%。",
    "drawdown_summary": "common full range 历史回放最大回撤约为 42.62%，回撤水平为较高。",
    "action_count_summary": "common full range 历史回放动作次数为 2054，动作频率为较多。",
    "turnover_summary": "common full range 历史回放 notional turnover proxy 为 193.66，换手 proxy 水平为较高。",
    "relative_to_top50_adaptive": "相对 Top50 adaptive，历史回放费用后净值差异为 -617.86%；本方法动作次数为 2054，notional turnover proxy 为 193.66，历史回放最大回撤为 42.62%。",
    "why_more_aggressive": "作为 baseline，该方法不用于说明 LTR 激进性；若动作较多，应解释为排名轮动规则带来的历史回放现象。",
    "why_more_conservative": "作为 baseline，该方法不用于说明换手控制；若动作较少，应结合候选池宽度、adaptive score 门槛或数据质量解释。",
    "why_no_action": "若某日无动作，应优先检查候选差距、adaptive score 门槛、持有期、价格缺失或共同日期集合。",
    "data_quality_note": "common full range 使用 1043 个共同回放日；baseline signal days=1048，LTR score days=1043；price audit sample_count=240、bad_count=0、max_days_to_execution=3。",
    "readonly_disclaimer": "只读研究解释，不是交易建议，不产生交易动作、订单或配置比例。",
    "source_trace": {
      "net_return": "phase3a2_method_comparison.csv:fee_tax_adjusted_net_return",
      "drawdown": "phase3a2_method_comparison.csv:max_drawdown",
      "action_count": "phase3a2_method_comparison.csv:action_count",
      "turnover_proxy": "phase3a2_method_comparison.csv:turnover_proxy_by_notional_over_avg_equity",
      "relative_delta": "phase3a2_method_comparison.csv:delta_vs_rank_rotate_top50_adaptive_score",
      "data_quality": "phase3a2_data_quality.csv + phase3a2_gate_summary.json",
      "role_mapping": "PHASE3B_READONLY_EXPLANATION_SCHEMA_CN.md fixed offline mapping"
    }
  },
  {
    "method_key": "rank_rotate_top50",
    "method_label": "Top50 rank rotation",
    "research_role": "baseline",
    "net_return_summary": "common full range 历史回放费用后净值变化约为 +1106.12%。",
    "drawdown_summary": "common full range 历史回放最大回撤约为 40.89%，回撤水平为较高。",
    "action_count_summary": "common full range 历史回放动作次数为 1982，动作频率为较多。",
    "turnover_summary": "common full range 历史回放 notional turnover proxy 为 198.73，换手 proxy 水平为较高。",
    "relative_to_top50_adaptive": "相对 Top50 adaptive，历史回放费用后净值差异为 -490.24%；本方法动作次数为 1982，notional turnover proxy 为 198.73，历史回放最大回撤为 40.89%。",
    "why_more_aggressive": "作为 baseline，该方法不用于说明 LTR 激进性；若动作较多，应解释为排名轮动规则带来的历史回放现象。",
    "why_more_conservative": "作为 baseline，该方法不用于说明换手控制；若动作较少，应结合候选池宽度、adaptive score 门槛或数据质量解释。",
    "why_no_action": "若某日无动作，应优先检查候选差距、adaptive score 门槛、持有期、价格缺失或共同日期集合。",
    "data_quality_note": "common full range 使用 1043 个共同回放日；baseline signal days=1048，LTR score days=1043；price audit sample_count=240、bad_count=0、max_days_to_execution=3。",
    "readonly_disclaimer": "只读研究解释，不是交易建议，不产生交易动作、订单或配置比例。",
    "source_trace": {
      "net_return": "phase3a2_method_comparison.csv:fee_tax_adjusted_net_return",
      "drawdown": "phase3a2_method_comparison.csv:max_drawdown",
      "action_count": "phase3a2_method_comparison.csv:action_count",
      "turnover_proxy": "phase3a2_method_comparison.csv:turnover_proxy_by_notional_over_avg_equity",
      "relative_delta": "phase3a2_method_comparison.csv:delta_vs_rank_rotate_top50_adaptive_score",
      "data_quality": "phase3a2_data_quality.csv + phase3a2_gate_summary.json",
      "role_mapping": "PHASE3B_READONLY_EXPLANATION_SCHEMA_CN.md fixed offline mapping"
    }
  },
  {
    "method_key": "rank_rotate_top50_adaptive_score",
    "method_label": "Top50 adaptive score",
    "research_role": "baseline",
    "net_return_summary": "common full range 历史回放费用后净值变化约为 +1596.37%。",
    "drawdown_summary": "common full range 历史回放最大回撤约为 40.24%，回撤水平为较高。",
    "action_count_summary": "common full range 历史回放动作次数为 1932，动作频率为较多。",
    "turnover_summary": "common full range 历史回放 notional turnover proxy 为 184.50，换手 proxy 水平为较高。",
    "relative_to_top50_adaptive": "这是 Phase3C payload 的对照 baseline；历史回放费用后净值变化为 +1596.37%，动作次数为 1932，notional turnover proxy 为 184.50。",
    "why_more_aggressive": "作为 baseline，该方法不用于说明 LTR 激进性；若动作较多，应解释为排名轮动规则带来的历史回放现象。",
    "why_more_conservative": "作为 baseline，该方法不用于说明换手控制；若动作较少，应结合候选池宽度、adaptive score 门槛或数据质量解释。",
    "why_no_action": "若某日无动作，应优先检查候选差距、adaptive score 门槛、持有期、价格缺失或共同日期集合。",
    "data_quality_note": "common full range 使用 1043 个共同回放日；baseline signal days=1048，LTR score days=1043；price audit sample_count=240、bad_count=0、max_days_to_execution=3。",
    "readonly_disclaimer": "只读研究解释，不是交易建议，不产生交易动作、订单或配置比例。",
    "source_trace": {
      "net_return": "phase3a2_method_comparison.csv:fee_tax_adjusted_net_return",
      "drawdown": "phase3a2_method_comparison.csv:max_drawdown",
      "action_count": "phase3a2_method_comparison.csv:action_count",
      "turnover_proxy": "phase3a2_method_comparison.csv:turnover_proxy_by_notional_over_avg_equity",
      "relative_delta": "phase3a2_method_comparison.csv:delta_vs_rank_rotate_top50_adaptive_score",
      "data_quality": "phase3a2_data_quality.csv + phase3a2_gate_summary.json",
      "role_mapping": "PHASE3B_READONLY_EXPLANATION_SCHEMA_CN.md fixed offline mapping"
    }
  },
  {
    "method_key": "confirmed_exit",
    "method_label": "Confirmed exit review",
    "research_role": "risk_review_reference",
    "net_return_summary": "common full range 历史回放费用后净值变化约为 +301.18%。",
    "drawdown_summary": "common full range 历史回放最大回撤约为 33.74%，回撤水平为中等。",
    "action_count_summary": "common full range 历史回放动作次数为 265，动作频率为较少。",
    "turnover_summary": "common full range 历史回放 notional turnover proxy 为 21.36，换手 proxy 水平为较低。",
    "relative_to_top50_adaptive": "相对 Top50 adaptive，历史回放费用后净值差异为 -1295.18%；本方法动作次数为 265，notional turnover proxy 为 21.36，历史回放最大回撤为 33.74%。",
    "why_more_aggressive": "不适用；该方法定位为风险复盘与低动作参考。",
    "why_more_conservative": "该方法历史回放动作次数较少、turnover proxy 较低，主要用于观察低动作与回撤控制之间的取舍。",
    "why_no_action": "若某日无动作，应优先检查确认条件是否不足、市况过滤、价格缺失或共同日期集合。",
    "data_quality_note": "common full range 使用 1043 个共同回放日；baseline signal days=1048，LTR score days=1043；price audit sample_count=240、bad_count=0、max_days_to_execution=3。",
    "readonly_disclaimer": "只读研究解释，不是交易建议，不产生交易动作、订单或配置比例。",
    "source_trace": {
      "net_return": "phase3a2_method_comparison.csv:fee_tax_adjusted_net_return",
      "drawdown": "phase3a2_method_comparison.csv:max_drawdown",
      "action_count": "phase3a2_method_comparison.csv:action_count",
      "turnover_proxy": "phase3a2_method_comparison.csv:turnover_proxy_by_notional_over_avg_equity",
      "relative_delta": "phase3a2_method_comparison.csv:delta_vs_rank_rotate_top50_adaptive_score",
      "data_quality": "phase3a2_data_quality.csv + phase3a2_gate_summary.json",
      "role_mapping": "PHASE3B_READONLY_EXPLANATION_SCHEMA_CN.md fixed offline mapping"
    }
  },
  {
    "method_key": "phase1c_ltr_simple_daily",
    "method_label": "Phase1C LTR simple daily",
    "research_role": "aggressive_rerank_research",
    "net_return_summary": "common full range 历史回放费用后净值变化约为 +4001.82%。",
    "drawdown_summary": "common full range 历史回放最大回撤约为 38.78%，回撤水平为较高。",
    "action_count_summary": "common full range 历史回放动作次数为 1978，动作频率为较多。",
    "turnover_summary": "common full range 历史回放 notional turnover proxy 为 199.49，换手 proxy 水平为较高。",
    "relative_to_top50_adaptive": "相对 Top50 adaptive，历史回放费用后净值差异为 +2405.45%；本方法动作次数为 1978，notional turnover proxy 为 199.49，历史回放最大回撤为 38.78%。",
    "why_more_aggressive": "该方法更直接跟随 LTR rerank 结果；历史回放中动作次数较多、notional turnover proxy 较高，因此解释时必须同时呈现换手和成本压力。",
    "why_more_conservative": "不适用；该方法定位为更激进的 LTR 研究参考。",
    "why_no_action": "若某日无动作，应优先检查 rerank 差距是否不足、持有期限制、价格缺失、共同日期集合或其他数据质量限制。",
    "data_quality_note": "common full range 使用 1043 个共同回放日；baseline signal days=1048，LTR score days=1043；price audit sample_count=240、bad_count=0、max_days_to_execution=3。",
    "readonly_disclaimer": "只读研究解释，不是交易建议，不产生交易动作、订单或配置比例。",
    "source_trace": {
      "net_return": "phase3a2_method_comparison.csv:fee_tax_adjusted_net_return",
      "drawdown": "phase3a2_method_comparison.csv:max_drawdown",
      "action_count": "phase3a2_method_comparison.csv:action_count",
      "turnover_proxy": "phase3a2_method_comparison.csv:turnover_proxy_by_notional_over_avg_equity",
      "relative_delta": "phase3a2_method_comparison.csv:delta_vs_rank_rotate_top50_adaptive_score",
      "data_quality": "phase3a2_data_quality.csv + phase3a2_gate_summary.json",
      "role_mapping": "PHASE3B_READONLY_EXPLANATION_SCHEMA_CN.md fixed offline mapping"
    }
  },
  {
    "method_key": "phase1c_ltr_turnover_controlled_daily",
    "method_label": "Phase1C LTR turnover controlled daily",
    "research_role": "turnover_control_research",
    "net_return_summary": "common full range 历史回放费用后净值变化约为 +465.27%。",
    "drawdown_summary": "common full range 历史回放最大回撤约为 19.93%，回撤水平为较低。",
    "action_count_summary": "common full range 历史回放动作次数为 315，动作频率为较少。",
    "turnover_summary": "common full range 历史回放 notional turnover proxy 为 31.85，换手 proxy 水平为较低。",
    "relative_to_top50_adaptive": "相对 Top50 adaptive，历史回放费用后净值差异为 -1131.10%；本方法动作次数为 315，notional turnover proxy 为 31.85，历史回放最大回撤为 19.93%。",
    "why_more_aggressive": "不适用；该方法定位为换手控制研究参考。",
    "why_more_conservative": "滚动动作预算、最短持有期和 turnover 控制会减少替换频率；历史回放中动作次数和 turnover proxy 明显低于高换手方法。",
    "why_no_action": "若某日无动作，应优先检查最近 10 个交易日动作预算、最短持有期、排名差距、价格缺失或共同日期集合。",
    "data_quality_note": "common full range 使用 1043 个共同回放日；baseline signal days=1048，LTR score days=1043；price audit sample_count=240、bad_count=0、max_days_to_execution=3。",
    "readonly_disclaimer": "只读研究解释，不是交易建议，不产生交易动作、订单或配置比例。",
    "source_trace": {
      "net_return": "phase3a2_method_comparison.csv:fee_tax_adjusted_net_return",
      "drawdown": "phase3a2_method_comparison.csv:max_drawdown",
      "action_count": "phase3a2_method_comparison.csv:action_count",
      "turnover_proxy": "phase3a2_method_comparison.csv:turnover_proxy_by_notional_over_avg_equity",
      "relative_delta": "phase3a2_method_comparison.csv:delta_vs_rank_rotate_top50_adaptive_score",
      "data_quality": "phase3a2_data_quality.csv + phase3a2_gate_summary.json",
      "role_mapping": "PHASE3B_READONLY_EXPLANATION_SCHEMA_CN.md fixed offline mapping"
    }
  }
]
```

## 6. 文案规范化方式

- return 表述固定为“历史回放费用后净值变化约为 ±xx.xx%”；
- 回撤表述固定为“历史回放最大回撤约为 xx.xx%”；
- action 表述固定为“历史回放动作次数为 n”；
- turnover 表述固定为“历史回放 notional turnover proxy 为 xx.xx”；
- `relative_to_top50_adaptive` 同时保留费用后净值变化差异与动作次数、turnover proxy、历史回放最大回撤中的 tradeoff；
- 所有解释保持只读研究语义，不写未来效果判断。

## 7. 禁止语义自查结果

- 未输出任何真实交易动作、配置目标、效果承诺或概率化判断语义；
- 未把 qlib score 或 LTR score 解释成收益率、概率或配置比例；
- 未把任何 method 包装成未来效果判断；
- `readonly_disclaimer` 在 top-level 与每个 method 中固定存在；
- 每个 method 均保留 tradeoff 信息，没有只写费用后净值变化。

## 8. 安全边界声明

本轮未执行：

- frontend / API / backend service 修改；
- monitor / database / provider 修改；
- accepted latest switching；
- provider refresh / publish；
- LTR 训练；
- replay 重跑；
- 新数据源读取；
- 联网；
- 真实交易执行链路相关工作。

## 9. 是否需要进入下一轮前端/API 只读接入审查

需要审查者另行决定。

当前 Phase3C 只完成离线只读 payload 物化，不授权直接接入前端或 API。如需接入，必须由审查者单独给出下一轮只读接入步骤文档，并补充 API / 前端 E2E 验收口径。
