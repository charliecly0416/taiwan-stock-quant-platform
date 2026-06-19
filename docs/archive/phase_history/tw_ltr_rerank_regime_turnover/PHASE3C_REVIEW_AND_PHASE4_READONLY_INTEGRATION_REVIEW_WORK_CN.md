# Phase3C 审查意见与 Phase4 只读接入审查工作文档

生成时间：2026-06-14

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

审查入口：`docs/tw_ltr_rerank_regime_turnover/PHASE3C_READONLY_PAYLOAD_EXECUTION_REPORT_CN.md`

---

## 1. 审查结论

Phase3C 通过。

执行者已经把 Phase3B 的解释字段草案物化成固定结构的只读 explanation payload artifact，并补齐了：

- top-level schema；
- method-level schema；
- `summary_notes[]`；
- top-level 与 method-level `readonly_disclaimer`；
- `source_trace`；
- method role mapping；
- payload contract 文档。

本轮没有进入前端、API、backend service、provider、accepted latest、monitor、database 或交易链路，也没有出现未来收益判断、仓位判断或概率承诺。

因此，Phase3C 可以作为后续只读产品接入审查的输入。

但这不等于授权直接接入页面或 API。下一步只能进入“Phase4 只读接入审查”，先定义如果接入产品链路，哪些字段可进、怎么验只读、怎么做 E2E。

---

## 2. 是否偏离主线或新增分支

未发现偏离主线或新增分支。

本轮仍严格在只读解释层：

- 无新数据源；
- 无联网；
- 无 provider refresh / publish；
- 无 accepted latest switching；
- 无 replay 重跑；
- 无模型训练；
- 无前端/API 改动；
- 无真实交易语义。

---

## 3. 当前可确认成立的产物

以下产物现在可以视为 Phase4 的稳定输入：

- `data_tw/experiments/ltr_rerank_regime_turnover/phase3c_readonly_explanation_payload/phase3c_readonly_explanation_payload.json`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3c_readonly_explanation_payload/phase3c_method_role_mapping.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3c_readonly_explanation_payload/PHASE3C_READONLY_PAYLOAD_CONTRACT_CN.md`

这些产物已经满足：

1. 字段来源可追溯；
2. 研究角色清晰；
3. tradeoff 信息保留；
4. 文案已从生硬浮点数提升为可读百分比/描述；
5. 只读边界明确。

---

## 4. 剩余风险

### R1：Payload 仍是离线 artifact，不是产品契约

现在的 payload 还只是离线 artifact。若后续要接前端或 API，需要额外决定：

- 是由后端离线文件直接提供；
- 还是由只读 API 包装返回；
- 或前端构建时静态读取。

这三种路径的安全边界和验收方式不同，不能直接跳过审查。

### R2：数值文案仍需产品级统一风格

当前 payload 已把数值转成百分比描述，但尚未确定最终展示格式，例如：

- `+1596.37%` 是否太夸张；
- 是否要改成“约 16.96 倍终值变化”；
- drawdown 是否统一保留正数百分比；
- turnover proxy 是否需要补一句“仅为历史回放换手代理”。

这些是 Phase4 接入前必须冻结的展示契约。

### R3：summary_notes 仍可能被误读成“结论”

当前 `summary_notes[]` 仍然接近研究总结。若进入页面或 API，必须确保它们保持：

```text
历史回放差异说明
而不是用户决策建议
```

---

## 5. 安全边界审查

安全边界通过。

验证：

- `python -m py_compile scripts/evaluate_tw_ltr_phase3a2_full_daily_replay.py`：通过；
- `python -m pytest backend/tests/test_tw_stock_portfolio_replay.py -q`：10 passed；
- 禁止语义扫描：payload、contract、执行报告均未命中危险语义；
- `readonly_disclaimer` 在 top-level 与每个 method 中均存在；
- `safety_boundary` 明确标记：
  - `no_frontend_or_api_integration=true`
  - `no_provider_refresh_or_publish=true`
  - `no_accepted_latest_switching=true`
  - `research_only=true`

未发现：

- broker / quick-trade / order / target position / target weight；
- monitor config save / scan / alerts write；
- provider refresh / publish；
- accepted latest switching；
- 自动交易或收益/概率承诺。

---

## 6. Phase4 本轮唯一目标

只做“只读接入审查设计”，不做真实接入。

目标：

```text
定义如果要把 Phase3C payload 接到产品链路，
应该通过哪一层进入，
哪些字段允许展示，
哪些字段必须删减或改写，
以及如何做只读 API / 前端 E2E 验收。
```

本轮仍然不是前端实现，不是 API 实现，不是联调。

---

## 7. 允许改动范围

允许新增：

- `docs/tw_ltr_rerank_regime_turnover/PHASE4_READONLY_INTEGRATION_REVIEW_EXECUTION_REPORT_CN.md`
- 只读接入契约文档、E2E 验收草案文档，路径限定在：
  - `docs/tw_ltr_rerank_regime_turnover/`

允许只读读取：

- Phase3C payload JSON；
- Phase3C contract；
- Phase3C execution report；
- 现有只读 portfolio replay / cross-analysis / frontend readonly E2E 文档。

默认不允许修改：

- frontend；
- backend API；
- backend service；
- tests；
- monitor；
- database；
- provider；
- accepted latest；
- payload 内容本身；
- replay / model / training 代码。

---

## 8. Phase4 必须回答的问题

执行者必须明确回答：

1. 如果接入产品，payload 应由哪一层提供：
   - 静态文件；
   - 后端只读 API；
   - 前端构建时内置；
2. 哪些字段可直接进入产品：
   - `method_label`
   - `research_role`
   - `why_no_action`
   - `readonly_disclaimer`
   - `data_quality_note`
   - 部分 summary 字段
3. 哪些字段不应直接进入首屏：
   - 原始 `source_trace`
   - 过重的 `summary_notes`
   - 可能被误读的高倍数收益数字
4. 如果做 API，只读契约应如何定义：
   - route；
   - method；
   - request shape；
   - response shape；
   - no-write guarantees；
5. 如果做前端，只读 E2E 应如何验：
   - 不触发 provider/accepted/monitor/trading；
   - 不出现危险文案；
   - payload 字段正确映射。

---

## 9. 禁止事项

本轮禁止：

- 直接接前端；
- 直接接 API；
- 写任何后端 route；
- 写任何前端组件；
- 写任何测试代码；
- 改 payload 内容；
- 联网；
- 新增数据源；
- provider refresh / publish；
- accepted latest switching；
- 输出买卖/仓位/目标权重/收益承诺/胜率/上涨概率。

---

## 10. 必做验证

执行者必须验证：

1. Phase4 产物只做接入审查设计，不含代码实现；
2. 只基于已有 payload/contract 做分析；
3. 不修改任何产品链路文件；
4. 文案中明确“不授权直接接入”；
5. 若提出 API 方案，必须是只读且附 no-write 保证；
6. 若提出前端方案，必须附只读 E2E 验收要点。

---

## 11. 验收门槛

Phase4 通过的最低门槛：

1. 明确给出只读接入方案候选；
2. 明确字段白名单/黑名单；
3. 明确 API/前端只读验收要点；
4. 不写实现代码；
5. 不越过 readonly / research-only 边界；
6. 不把 explanation payload 抬升成推荐层。

如果执行者希望在本轮直接开始接入实现，必须停止并回到审查者重新写下一轮实现文档。

---

## 12. 执行报告要求

执行者下一轮报告固定写入：

```text
docs/tw_ltr_rerank_regime_turnover/PHASE4_READONLY_INTEGRATION_REVIEW_EXECUTION_REPORT_CN.md
```

报告必须包含：

1. 本轮目标；
2. 读取的 payload / contract；
3. 接入层候选方案；
4. 字段白名单/黑名单；
5. API 只读契约建议；
6. 前端只读验收建议；
7. 禁止语义与安全边界声明；
8. 是否建议进入下一轮真实只读接入实现审查。
