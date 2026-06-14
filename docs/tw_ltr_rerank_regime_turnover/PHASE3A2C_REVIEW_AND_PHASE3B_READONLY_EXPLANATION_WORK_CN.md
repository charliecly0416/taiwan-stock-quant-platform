# Phase3A2C 审查意见与 Phase3B 只读解释层工作文档

生成时间：2026-06-13

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

审查入口：`docs/tw_ltr_rerank_regime_turnover/PHASE3A2C_LOOKAHEAD_METRIC_REPAIR_EXECUTION_REPORT_CN.md`

---

## 1. 审查结论

Phase3A2C 通过“回放口径修复”审查，可以结束 Phase3A2 系列修复。

但不能把本轮结果包装成主推荐、收益更优、胜率更高或上涨概率更高。下一步只允许恢复 Phase3B，且 Phase3B 只能做 readonly explanation，不进入主推荐、不改前端交易语义、不接 API 写入、不做模型训练。

本轮相对 Phase3A2B 的关键修复成立：

- `LocalKline.get_kline()` 不再只返回最后 500 根 K 线；
- `OfflineService._next_close_after()` 改为直接使用 `PriceStore.next_after(symbol, asof)`；
- price execution audit 显示 sample_count=240、bad_count=0、max_days_to_execution=3；
- 每个 period 使用 baseline signal days 与 Phase1C frozen score 日期交集，缺分日期从所有方法统一排除；
- `gross_return` 不再伪装成 net return，明确标记为 `not_available_in_current_engine`；
- turnover proxy 改为 `sum(abs(quantity * price)) / average_equity`；
- turnover-controlled LTR 的动作预算改为最近 10 个交易日滚动窗口，不再全区间只有 3 次动作；
- 六个 required methods 均完成同口径日频回放。

---

## 2. 是否偏离主线或新增分支

未发现新增主线或越权分支。

本轮仍在主文档边界内：

- 没有新增数据源；
- 没有联网；
- 没有 provider refresh / publish；
- 没有 accepted latest switching；
- 没有重训 LTR；
- 没有重建 Phase1C frozen score；
- 没有修改 frontend / API / backend 产品服务；
- 没有真实交易、broker、quick-trade、orders、target position / target weight。

Phase3A2C 的结果可以作为“研究回放证据”，但不能直接转成用户操作建议。

---

## 3. 回放结果解读边界

本轮结果显示：

- `phase1c_ltr_simple_daily` 在 validation、independent_test、2025、2026 YTD 与 common full range 上相对 Top50 adaptive 有更高 net return；
- 但它仍有高动作数、高 notional turnover，且 max drawdown 仍较大；
- `phase1c_ltr_turnover_controlled_daily` 明显降低 action count、turnover proxy 与 drawdown，但多数区间 net return 低于 Top50 adaptive 和 LTR simple；
- `confirmed_exit` 动作少、回撤低，但收益较低，适合作为“保守复盘参考”而非胜出策略。

因此这是一个解释层可用的 tradeoff：

```text
LTR simple：更激进，历史回放收益高，但换手和动作成本高；
turnover-controlled LTR：更保守，动作与回撤更低，但收益牺牲明显；
Top50 adaptive：仍是稳定 baseline；
confirmed_exit：偏风险复盘与低动作参考。
```

这不是“选择某个策略作为推荐”的结论。Phase3B 只能把这些差异解释清楚。

---

## 4. 剩余风险

### R1：Parity check 仍是离线 adapter 内部一致性，不是线上 API E2E

Phase3A2C 的 parity check 证明的是同一个 `OfflineService` 使用产品 `_replay_variant()` 路径完成短窗 Top50 adaptive 回放。它没有启动后端 API 做 `/rank-tech-cross/portfolio-replay` E2E 对照。

这不阻止进入 Phase3B readonly explanation，因为 Phase3B 不应接 API 或前端主链路；但若未来要产品化展示，需要再做 API/前端只读验收。

### R2：Common full range 收益很高，不能直接用户化

`phase1c_ltr_simple_daily` common full range net return 很高，且 turnover proxy 也很高。Phase3B 文案必须避免“收益更优”“更强策略”“建议采用”等表达，只能说“历史回放中显示更激进的收益/换手组合”。

### R3：gross return 不可用

当前引擎只输出 fee/tax-adjusted net return。Phase3B 不能展示或暗示 gross return。

---

## 5. 安全边界审查

安全边界通过。

验证：

- `python -m py_compile scripts/evaluate_tw_ltr_phase3a2_full_daily_replay.py`：通过；
- `python -m pytest backend/tests/test_tw_stock_portfolio_replay.py -q`：10 passed；
- safety scan：命中仅出现在 Safety Boundary、readonly flags 或禁止事项说明中。

未发现：

- broker / quick-trade / order / target position / target weight；
- monitor config save / monitor scan / alerts write；
- provider refresh / publish；
- accepted latest switching；
- 真实买卖、仓位、收益承诺、胜率或上涨概率语义。

---

## 6. Phase3B 本轮唯一目标

只做 readonly explanation scope 文档与最小解释数据设计。

目标：

```text
把 Phase3A2C 的六方法同口径回放结果，
转成用户能读懂的只读解释结构：
baseline 与 LTR 是否一致、
为什么 LTR simple 更激进、
为什么 turnover-controlled LTR 少动作、
为什么某些情况下不应替换。
```

本轮不做前端实现，不改 API，不接主推荐。

---

## 7. 允许改动范围

允许新增：

- `docs/tw_ltr_rerank_regime_turnover/PHASE3B_READONLY_EXPLANATION_EXECUTION_REPORT_CN.md`
- Phase3B 只读解释字段草案文档或 JSON schema 草案，路径限定在：
  - `docs/tw_ltr_rerank_regime_turnover/`
  - 或 `data_tw/experiments/ltr_rerank_regime_turnover/phase3b_readonly_explanation/`

允许只读读取：

- `phase3a2_method_comparison.csv`
- `phase3a2_period_comparison.csv`
- `phase3a2_actions_summary.csv`
- `phase3a2_data_quality.csv`
- `phase3a2_gate_summary.json`
- Phase3A2C 执行报告

默认不允许修改：

- frontend；
- backend API；
- backend service；
- monitor；
- database；
- provider；
- accepted latest；
- Phase1C 模型或 score artifact；
- qlib pipeline；
- 任何交易相关模块。

---

## 8. Phase3B 必须产出的解释结构

执行者必须提出一套简单字段，不要求实现前端。

字段建议：

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

其中：

- `research_role` 只能是 `baseline` / `aggressive_rerank_research` / `turnover_control_research` / `risk_review_reference`；
- `relative_to_top50_adaptive` 只能描述历史回放差异，不能写未来判断；
- `why_no_action` 必须围绕市况、排名差距、换手预算、持有期、价格缺失或数据质量；
- `readonly_disclaimer` 必须明确不是交易建议、不是订单、不是仓位。

---

## 9. 禁止文案

Phase3B 禁止出现：

```text
建议买入
建议卖出
应加仓
应减仓
目标仓位
目标权重
收益更优
胜率更高
上涨概率
预期收益
自动交易
下单
提交订单
连接券商
```

允许出现：

```text
历史回放
只读研究
观察顺序
动作次数
换手较高 / 较低
回撤较高 / 较低
费用后净值
人工复盘
不是交易建议
```

---

## 10. 必做验证

Phase3B 执行者必须至少验证：

1. 所有解释字段来自 Phase3A2C 产物，不重新计算模型分数；
2. 不读取新数据源；
3. 不联网；
4. 不修改 frontend / API / backend service；
5. 文本扫描不含 forbidden semantics；
6. 不出现 target position / target weight / expected return / upside probability；
7. 不把 `qlib_score` 或 LTR score 解释成收益率、概率或仓位。

---

## 11. 验收门槛

Phase3B 通过的最低门槛：

1. 只交付解释层设计文档或离线只读解释 artifact；
2. 解释字段简单、准确、清晰、实用；
3. 明确区分 Top50 adaptive、LTR simple、turnover-controlled LTR、confirmed_exit 的研究角色；
4. 不声称任何方法未来收益更优；
5. 不接主推荐；
6. 不改前端/API；
7. 不越过 readonly / research-only 边界。

若执行者希望把 Phase3B 接入页面或 API，必须停止并回到审查者重新写下一轮文档。

---

## 12. 执行报告要求

执行者下一轮报告固定写入：

```text
docs/tw_ltr_rerank_regime_turnover/PHASE3B_READONLY_EXPLANATION_EXECUTION_REPORT_CN.md
```

报告必须包含：

1. 本轮目标；
2. 使用的 Phase3A2C 输入产物；
3. 解释字段设计；
4. 每个方法的 research role；
5. 示例解释，不超过 3 条；
6. 禁止语义自查结果；
7. 安全边界声明；
8. 是否需要进入下一轮前端/API 只读接入审查。

本轮不得直接进入前端/API 接入。
