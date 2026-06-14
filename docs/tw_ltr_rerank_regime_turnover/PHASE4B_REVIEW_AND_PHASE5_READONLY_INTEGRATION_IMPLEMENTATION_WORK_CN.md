# Phase4B 审查意见与 Phase5 真实只读接入实现审查工作文档

生成时间：2026-06-14

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

审查入口：`docs/tw_ltr_rerank_regime_turnover/PHASE4B_USER_FIRST_CONTRACT_REPAIR_EXECUTION_REPORT_CN.md`

---

## 1. 审查结论

Phase4B 通过，现已**基本符合用户第一性原则**，可以进入下一轮真实只读接入实现审查。

本轮通过点：

- 首屏顺序已改成用户问题优先：
  1. 当前为什么不动 / 当前观察结论
  2. 当前取舍摘要
  3. 方法角色
  4. 只读边界
- 首屏继续禁止高风险精确数值；
- 详情层恢复为“受约束的精确历史回放指标 + tradeoff 同屏”；
- 用户短标签 / 系统标签边界已冻结；
- 高数值展示规则已冻结：
  - 不进首屏
  - 详情层可展示
  - 但必须和动作 / 换手 / 回撤同屏
  - 不得单独突出费用后净值变化

这已经比 Phase4A 更符合：

- 简单：首屏足够收敛；
- 准确：详情层保留必要精度；
- 清晰：先回答“为什么不动”；
- 实用：仍支持认真复盘。

因此，允许进入 Phase5，但范围必须非常窄。

---

## 2. 是否偏离主线或新增分支

未发现偏离主线或新增分支。

Phase4B 仍然只是在冻结只读展示契约，没有：

- 新模型；
- 新数据源；
- 联网；
- provider refresh / publish；
- accepted latest switching；
- 交易链路；
- 推荐语义扩张。

---

## 3. 安全边界审查

安全边界通过。

验证：

- `python -m py_compile scripts/evaluate_tw_ltr_phase3a2_full_daily_replay.py`：通过；
- `python -m pytest backend/tests/test_tw_stock_portfolio_replay.py -q`：10 passed；
- 本轮文案未发现 broker / quick-trade / order / target position / target weight；
- 未发现 accepted latest switching、provider refresh/publish、monitor 写入或交易承诺语义。

本轮放行原因来自展示契约质量已达标，不是因为放宽安全边界。

---

## 4. Phase5 本轮唯一目标

只做一件事：

```text
按 Phase4B 冻结后的展示契约，
实现最小真实只读接入：
后端只读 GET 包装 Phase3C payload，
前端只展示 4 个首屏信息单元与受约束详情层，
并完成只读 E2E 验收。
```

本轮不做任何推荐层，不做交易层，不做数据刷新。

---

## 5. 允许改动范围

允许修改：

- backend 只读 API 路由或 service 包装层
- frontend 只读展示层
- 只读 E2E / 单测
- 相关只读文档

允许读取：

- Phase3C payload / contract
- Phase4B 展示契约
- 现有只读 portfolio replay / cross-analysis / frontend readonly E2E 文档

默认不允许修改：

- 任何 provider / accepted latest / monitor 写入逻辑；
- 任何 trading / broker / quick-trade / order 相关模块；
- replay / model / training 主逻辑；
- payload 基础研究产物；
- 新数据源接入。

---

## 6. 实现范围

### 6.1 后端

只允许新增一个只读 GET 接口，建议：

```text
GET /api/tw-stock/ltr-readonly-explanation
```

要求：

- 只读；
- 只读取固定 Phase3C payload artifact；
- 返回经过 Phase4B 白名单过滤和文案收敛后的产品展示视图；
- 不返回 `source_trace`、原始 `summary_notes[]`、原始 `safety_boundary`；
- 不接受 body；
- 不触发任何状态变更。

### 6.2 前端

只允许最小接入：

- 首屏只展示 4 个信息单元；
- 详情层只展示受约束的精确历史回放指标；
- 固定显示 `readonly_disclaimer`；
- 不显示任何推荐性 CTA；
- 不显示原始高风险研究字段。

### 6.3 测试

必须补：

- 后端只读契约测试；
- 前端字段白名单测试；
- 只读 E2E：
  - 仅 GET
  - 无写请求
  - 无 provider / accepted / monitor / trading 路径
  - 无危险文案

---

## 7. 必须遵守的展示契约

### 首屏固定结构

只允许：

1. `今天不动作的主要原因：{原因短语}。`
2. `历史回放取舍：{动作频率}，{换手压力}，{回撤水平}。`
3. `{用户短标签}`
4. `仅供只读研究复盘，不构成操作建议，不会产生任何真实执行动作。`

### 详情层固定规则

允许：

- 费用后净值变化
- 最大回撤
- 动作次数
- notional turnover proxy

但必须：

- 同屏出现；
- 明确“历史回放”语境；
- 不得用费用后净值变化排序；
- 不得把任一方法包装成更适合用户。

---

## 8. 禁止事项

本轮禁止：

- 任何 POST / PUT / PATCH / DELETE 接入；
- provider refresh / publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / order；
- target position / target weight；
- 收益承诺、胜率、上涨概率、expected return、upside probability；
- 把 explanation payload 抬升成推荐层；
- 改写 Phase4B 已冻结的展示契约。

---

## 9. 必做验证

执行者必须验证：

1. 页面仅调用只读 GET；
2. 无写请求；
3. 无 provider/accepted/monitor/trading 路径；
4. 首屏严格只显示 4 个信息单元；
5. 高风险精确数值不进首屏；
6. 详情层精确数值同屏展示 tradeoff；
7. `readonly_disclaimer` 始终可见；
8. 文案无未来判断或交易语义。

---

## 10. 验收门槛

Phase5 通过的最低门槛：

1. 后端只读 GET 正常返回；
2. 前端最小只读展示符合 Phase4B 契约；
3. 只读 E2E 通过；
4. 无写请求、无状态变更、无危险文案；
5. 不扩线到推荐层或交易层。

若执行者想扩大范围，例如加入更多页面、更多接口或更深的研究字段，必须停止并回到审查者。

---

## 11. 执行报告要求

执行者下一轮报告固定写入：

```text
docs/tw_ltr_rerank_regime_turnover/PHASE5_READONLY_INTEGRATION_IMPLEMENTATION_EXECUTION_REPORT_CN.md
```

报告必须包含：

1. 本轮目标；
2. 实际改动文件；
3. 新增接口与字段白名单；
4. 前端展示截图或结构说明；
5. 测试与 E2E 结果；
6. 安全边界声明；
7. 是否达到只读接入验收门槛。
