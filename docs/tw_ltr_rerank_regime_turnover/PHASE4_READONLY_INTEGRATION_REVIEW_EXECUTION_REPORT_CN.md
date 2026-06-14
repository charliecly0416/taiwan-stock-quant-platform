# Phase4 Readonly Integration Review 执行报告

生成时间：2026-06-14

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

执行依据：`docs/tw_ltr_rerank_regime_turnover/PHASE3C_REVIEW_AND_PHASE4_READONLY_INTEGRATION_REVIEW_WORK_CN.md`

## 1. 本轮目标

本轮只做只读接入审查设计：定义如果后续要把 Phase3C explanation payload 接到产品链路，应由哪一层提供、哪些字段可进入展示、哪些字段应隐藏或改写，以及 API / 前端只读验收方式。

本轮不做真实接入，不写前端组件，不写后端 route，不写测试代码，不修改 payload，不进入推荐层。

用户第一性原则：

- 简单：首屏只给角色、原因、取舍和只读边界；
- 准确：不把历史回放解释成未来判断；
- 清晰：用户能看懂“为什么不动”和“不同方法的研究角色”；
- 实用：保留人工复盘需要的字段，但把审计细节放到折叠或调试层。

## 2. 读取的 Payload / Contract

- `data_tw/experiments/ltr_rerank_regime_turnover/phase3c_readonly_explanation_payload/phase3c_readonly_explanation_payload.json`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3c_readonly_explanation_payload/phase3c_method_role_mapping.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3c_readonly_explanation_payload/PHASE3C_READONLY_PAYLOAD_CONTRACT_CN.md`
- `docs/tw_ltr_rerank_regime_turnover/PHASE3C_READONLY_PAYLOAD_EXECUTION_REPORT_CN.md`

本轮只基于上述已有产物做接入审查设计，没有读取新数据源，没有联网，没有重算模型分数。

## 3. 接入层候选方案

### 方案 A：后端只读 API 包装静态 payload

建议作为优先候选。

原因：

- 后端可以集中做字段白名单过滤，避免把审计字段直接暴露给页面；
- 后端可以统一返回只读边界与 payload 版本；
- 后续 E2E 可明确验证只调用一个 GET 接口；
- 不需要前端理解本地实验目录结构。

限制：

- 必须单独进入下一轮实现审查；
- API 只能读取固定 artifact；
- API 不得触发数据刷新、状态切换、监控扫描或交易执行链路。

### 方案 B：静态文件直接提供

可作为离线演示或审查辅助，不建议作为正式产品候选。

优点是实现最少；缺点是字段过滤、版本管理和安全边界都容易落到前端侧，不利于长期维护。

### 方案 C：前端构建时内置

不建议作为当前主线候选。

原因：

- payload 会被打进构建产物，更新路径不清晰；
- 容易把实验 artifact 和产品展示耦合；
- 后续审查难以验证运行时只读来源。

## 4. 字段白名单

### 首屏可展示字段

| field | 展示建议 | 原因 |
| --- | --- | --- |
| method_label | 直接展示 | 用户可读方法名 |
| research_role | 直接展示，但需要中文映射 | 让用户理解 baseline / 激进研究 / 换手控制 / 风险复盘角色 |
| why_no_action | 直接展示 | 最符合用户“为什么今天不动”的问题 |
| readonly_disclaimer | 固定展示 | 明确只读研究边界 |

### 可折叠展示字段

| field | 展示建议 | 原因 |
| --- | --- | --- |
| drawdown_summary | 折叠展示 | 是风险取舍信息，但不应压过主解释 |
| action_count_summary | 折叠展示 | 有助于理解动作频率 |
| turnover_summary | 折叠展示 | 有助于理解换手压力 |
| relative_to_top50_adaptive | 折叠展示并保留 tradeoff | 避免用户只看费用后净值差异 |
| data_quality_note | 折叠展示 | 审查和人工复盘有用，但首屏偏重 |

### 不建议首屏直接展示字段

| field | 处理建议 | 原因 |
| --- | --- | --- |
| net_return_summary | 仅在“历史回放详情”中展示，且必须带只读语境 | 高百分比容易被误读成未来效果 |
| summary_notes[] | 不直接放首屏，可拆成中性提示 | 容易被误读成结论 |
| source_trace | 不展示给普通用户 | 审计字段，适合调试或审查 |
| safety_boundary | 不展示原始对象 | 产品层只展示固定只读说明 |
| created_at / schema_version | 可放调试信息 | 对普通用户价值低 |

## 5. 字段黑名单与改写要求

不得直接进入用户首屏：

- 原始 `source_trace`；
- 原始 `summary_notes[]`；
- 单独突出的高倍数费用后净值文案；
- 任何脱离“历史回放”语境的效果描述；
- 任何把 method 抬升为主推荐的文案。

改写要求：

- `net_return_summary` 必须和 `action_count_summary`、`turnover_summary` 或 `drawdown_summary` 同屏出现；
- `relative_to_top50_adaptive` 必须保留 tradeoff，不能只保留费用后净值差异；
- `research_role` 必须映射成用户能懂的中文标签；
- `readonly_disclaimer` 必须始终可见。

## 6. API 只读契约建议

建议 route：

```text
GET /api/tw-stock/ltr-readonly-explanation
```

请求：

```text
无 body。
可选 query：scope=common_full_range
```

响应 shape：

```json
{
  "ok": true,
  "schema_version": "phase4_product_readonly_view_v1",
  "payload_source": "phase3c_readonly_explanation_payload",
  "as_of_scope": {},
  "methods": [
    {
      "method_key": "phase1c_ltr_turnover_controlled_daily",
      "method_label": "Phase1C LTR turnover controlled daily",
      "research_role_label": "换手控制研究参考",
      "why_no_action": "...",
      "tradeoff_summary": "...",
      "risk_summary": "...",
      "activity_summary": "...",
      "data_quality_note": "...",
      "readonly_disclaimer": "..."
    }
  ],
  "readonly_disclaimer": "...",
  "no_write_guarantees": {
    "read_only_http_method": true,
    "reads_static_payload_only": true,
    "does_not_change_runtime_state": true,
    "does_not_trigger_data_refresh": true,
    "does_not_switch_accepted_pointer": true,
    "does_not_touch_monitor_or_execution_paths": true
  }
}
```

API 只读保证：

- 只允许 GET；
- 不接受会改变状态的 body；
- 只读取 Phase3C 固定 artifact；
- 不写数据库；
- 不更新配置；
- 不触发数据刷新；
- 不切换 accepted 指针；
- 不调用监控写入、扫描或交易执行链路；
- 不返回 `source_trace` 到普通产品响应。

## 7. 前端只读验收建议

若后续进入前端只读接入，实现后必须至少验收：

1. 页面只发起 `GET /api/tw-stock/ltr-readonly-explanation`；
2. 页面不发起 POST / PUT / PATCH / DELETE；
3. 页面不访问 provider、accepted pointer、monitor 写入或交易执行类接口；
4. 首屏展示字段只来自白名单；
5. `readonly_disclaimer` 可见；
6. `why_no_action` 可见；
7. `net_return_summary` 不单独突出展示，必须与动作、换手或回撤取舍一起出现；
8. `summary_notes[]` 不作为主结论展示；
9. 页面文案不出现真实交易动作、配置目标、效果承诺或概率化判断；
10. payload 缺失或读取失败时，页面只显示“只读解释暂不可用”，不触发任何修复性写操作。

## 8. 禁止语义与安全边界声明

本轮产物只做接入审查设计，不含代码实现。

本轮未执行：

- 前端实现；
- 后端 route 实现；
- 测试代码实现；
- payload 修改；
- 新数据源读取；
- 联网；
- provider refresh / publish；
- accepted latest switching；
- replay 重跑；
- 模型训练；
- 监控写入、扫描或交易执行链路相关工作。

本轮文案不授权直接接入产品链路，不授权把 explanation payload 抬升成推荐层。

## 9. 必做验证结果

- Phase4 产物只做接入审查设计：通过。
- 只基于已有 payload / contract 做分析：通过。
- 未修改任何产品链路文件：通过。
- 已明确“不授权直接接入”：通过。
- API 方案为只读 GET，并附 no-write guarantees：通过。
- 前端方案已附只读 E2E 验收要点：通过。

## 10. 是否建议进入下一轮真实只读接入实现审查

建议进入下一轮真实只读接入实现审查，但必须由审查者另写步骤文档后再执行。

建议下一轮范围：

- 只实现方案 A；
- 后端只读 GET 包装 Phase3C payload；
- 前端只读展示最小白名单字段；
- 增加只读 E2E 验收；
- 保持 research-only，不进入推荐层。

若审查者认为高百分比历史回放文案仍有误读风险，应先冻结产品级数值展示规则，再进入实现。
