# Phase4 审查意见与 Phase4A 产品展示契约冻结工作文档

生成时间：2026-06-14

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

审查入口：`docs/tw_ltr_rerank_regime_turnover/PHASE4_READONLY_INTEGRATION_REVIEW_EXECUTION_REPORT_CN.md`

---

## 1. 审查结论

Phase4 在“只读接入审查设计”层面基本合格，但**还不满足用户第一性原则下直接进入实现审查**。

原因不是安全越权，而是产品展示契约还没有冻结。当前报告已经回答了：

- 候选接入层；
- 字段白名单/黑名单；
- API 只读契约建议；
- 前端只读 E2E 验收建议。

这些都对，也保持了只读边界。

但从用户第一性原则看，当前产物仍偏“接入工程设计”，还没有把下面三件事定死：

1. **首屏到底只展示哪 3-5 个信息点**；
2. **高百分比历史回放数值如何表达，才不误导用户**；
3. **`research_role`、`why_no_action`、`tradeoff_summary` 的最终中文展示语义是什么**。

在这三件事没有冻结前，直接进入实现容易把页面做成研究信息堆叠层，偏离“简单、准确、清晰、实用”。

因此本轮结论是：

```text
不直接放行 Phase5 实现；
先进入 Phase4A：产品展示契约冻结。
```

---

## 2. 是否符合用户第一性原则

### 2.1 简单：部分符合，但还不够收束

好的部分：

- 报告已明确“首屏只给角色、原因、取舍和只读边界”；
- 已把 `source_trace`、`summary_notes[]`、高百分比 `net_return_summary` 排除出首屏；
- 已强调 `why_no_action` 应直达用户问题。

不足之处：

- 首屏白名单仍是“字段级”，不是“用户信息级”；
- 还没有明确首屏的最终 3-5 条信息结构；
- 仍保留了较多“如果做 API / 如果做前端”的工程表达。

用户第一原则要求先回答：

```text
用户第一眼看到什么？
第二眼展开看什么？
哪些信息永远不应该抢到首屏？
```

当前报告还没有把这个层级完全冻结。

### 2.2 准确：大体符合，但高百分比语义仍有误读风险

好的部分：

- 报告明确 `net_return_summary` 只能在“历史回放详情”中展示；
- 强调它必须和 action / turnover / drawdown 同屏出现；
- 保留只读边界。

不足之处：

- 仍未冻结最终数值语义，例如：
  - `+1596.37%`
  - `+4001.82%`
- 这些值即使放在详情层，也极易被用户误读成“方法显著更好”。

主线文档明确要求：

- 不把研究输出包装成自动交易建议；
- 不把模型输出包装成 expected return / upside probability；
- 页面优先是“为什么值得看 / 为什么不动”，不是“哪个数字更大”。

因此，在产品层展示前，必须先冻结高数值的写法。

### 2.3 清晰：方向正确，但缺少最终展示文案契约

好的部分：

- `why_no_action` 被放入首屏白名单；
- `readonly_disclaimer` 固定可见；
- `research_role` 要做中文映射。

不足之处：

- 还没有提供最终中文标签集合；
- 还没有冻结 `tradeoff_summary` 的单句模板；
- 还没有规定首屏禁止出现哪些研究词，例如：
  - “激进”
  - “baseline”
  - “turnover proxy”
  这些词是否直接给普通用户看，还未定。

### 2.4 实用：合格，但需要进一步减重

Phase4 已经知道哪些字段对人工复盘有用，哪些该隐藏。这是对的。

但若直接进入实现，仍有风险把页面做成：

```text
字段很多、层次很多、术语很多，
用户得先学系统词汇才能读懂。
```

这与“实用”不符。

---

## 3. 本轮不通过直接进入实现的原因

### P1：还没有冻结“首屏最小解释单元”

报告里有首屏字段白名单，但没有冻结首屏最小解释单元。

执行者下一轮必须明确：

```text
首屏只出现：
1. 方法角色
2. 为什么不动
3. 一个 tradeoff 摘要
4. 只读边界
```

还是其他组合。

### P1：高百分比历史回放文案仍缺最终规则

报告自己也承认高百分比文案可能误读，但仍建议进入下一轮实现审查。

这一步我不放行。

因为一旦实现层开始，展示风格就容易被代码和页面结构固化。正确顺序应该是：

```text
先冻结产品展示契约
再做真实只读接入实现审查
```

### P1：`research_role` 的产品中文仍未冻结

例如：

- `baseline`
- `aggressive_rerank_research`
- `turnover_control_research`
- `risk_review_reference`

虽然技术上可映射，但用户最终看到的中文标签还没有冻结，必须先定稿。

---

## 4. 安全边界审查

安全边界通过。

本轮未发现：

- broker / quick-trade / order / target position / target weight；
- provider refresh / publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- 自动交易或收益/概率承诺。

验证：

- `python -m py_compile scripts/evaluate_tw_ltr_phase3a2_full_daily_replay.py`：通过；
- `python -m pytest backend/tests/test_tw_stock_portfolio_replay.py -q`：10 passed。

本轮失败原因完全来自“用户第一性原则下的产品展示契约未冻结”，不是安全问题。

---

## 5. Phase4A 本轮唯一目标

只做一件事：

```text
冻结产品展示契约，
把 Phase3C payload 转成“用户第一性原则”下的最小展示结构，
但仍然不写任何接入实现代码。
```

本轮不是前端实现，不是 API 实现，不是联调。

---

## 6. 允许改动范围

允许新增：

- `docs/tw_ltr_rerank_regime_turnover/PHASE4A_PRODUCT_DISPLAY_CONTRACT_EXECUTION_REPORT_CN.md`
- 与产品展示契约相关的纯文档草案，路径限定在：
  - `docs/tw_ltr_rerank_regime_turnover/`

允许只读读取：

- Phase3C payload；
- Phase3C contract；
- Phase4 integration review；
- 主线文档。

默认不允许修改：

- frontend；
- backend API；
- backend service；
- tests；
- payload artifact；
- replay / model / training 代码；
- monitor / provider / accepted latest / trading 相关文件。

---

## 7. Phase4A 必须冻结的内容

执行者必须明确给出并写死：

### 7.1 首屏最小展示结构

只允许 3-5 个展示单元。

例如必须从下面选择并冻结最终版本：

1. 方法角色
2. 为什么不动
3. 当前取舍摘要
4. 只读边界
5. 数据质量提示（可选）

不能把：

- 费用后净值变化
- 回撤
- 动作次数
- turnover proxy

都直接塞进首屏。

### 7.2 详情层展示结构

必须明确：

- 哪些字段进入详情层；
- 哪些字段只给调试/审查层；
- 哪些字段根本不进入产品层。

### 7.3 最终中文标签

必须冻结：

- `research_role` 的最终中文；
- `tradeoff_summary` 的中文模板；
- `why_no_action` 的中文模板；
- `readonly_disclaimer` 的最终固定文案。

### 7.4 高数值展示规则

必须明确：

- 是否展示百分比；
- 是否改成倍数；
- 是否只展示相对水平描述而隐藏精确高数值；
- 哪些数值一律不进首屏。

这一项必须给出单一规则，不允许同时保留多种写法。

---

## 8. 禁止事项

本轮禁止：

- 进入真实只读接入实现；
- 写前端代码；
- 写后端 route；
- 写测试；
- 改 payload；
- 改 replay；
- 新增数据源；
- 联网；
- provider refresh / publish；
- accepted latest switching；
- 输出任何买卖/仓位/收益承诺/概率判断。

---

## 9. 必做验证

执行者必须验证：

1. Phase4A 只产出展示契约，不含实现代码；
2. 首屏结构不超过 5 个信息单元；
3. 高百分比展示规则唯一且明确；
4. `why_no_action` 仍是首屏核心；
5. `readonly_disclaimer` 固定可见；
6. `source_trace`、原始 `summary_notes[]`、高风险数值默认不进首屏；
7. 文案不出现未来判断或交易语义。

---

## 10. 验收门槛

Phase4A 通过的最低门槛：

1. 冻结首屏最小展示结构；
2. 冻结详情层/调试层边界；
3. 冻结最终中文标签与免责声明；
4. 冻结高数值展示规则；
5. 不写实现代码；
6. 更符合“简单、准确、清晰、实用”；
7. 不越过 readonly / research-only 边界。

只有在 Phase4A 通过后，才允许我为下一轮撰写真实只读接入实现审查文档。

---

## 11. 执行报告要求

执行者下一轮报告固定写入：

```text
docs/tw_ltr_rerank_regime_turnover/PHASE4A_PRODUCT_DISPLAY_CONTRACT_EXECUTION_REPORT_CN.md
```

报告必须包含：

1. 本轮目标；
2. 首屏最小展示结构；
3. 详情层 / 调试层字段分层；
4. `research_role` 最终中文；
5. `why_no_action` 模板；
6. `readonly_disclaimer` 最终固定文案；
7. 高数值展示规则；
8. 禁止语义与安全边界声明；
9. 是否建议进入下一轮真实只读接入实现审查。
