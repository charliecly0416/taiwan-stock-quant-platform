# Phase3A2 审查意见与 Phase3A2B 权威回放口径修复工作文档

生成时间：2026-06-13

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

审查入口：`docs/tw_ltr_rerank_regime_turnover/PHASE3A2_FULL_DAILY_REPLAY_EXECUTION_REPORT_CN.md`

---

## 1. 审查结论

Phase3A2 本轮不通过，不能作为最终停止结论，也不能恢复 Phase3B。

本轮执行者保持了只读边界，也没有强行做不完整的 LTR 对照，这一点是正确的。但其停止理由证据不足：报告只检查了 `scripts/run_tw_rank_rotation_stress_replay.py` 中是否存在 `confirmed_exit`，就断言 `confirmed_exit` 权威完整日频 replay 口径无法定位。

仓库内存在反证：

- `backend/app/services/tw_stock_portfolio_replay.py` 已实现 `strategyComparison`；
- 该 `strategyComparison` 同时包含：
  - `rank_rotate_top30`
  - `rank_rotate_top50`
  - `rank_rotate_top50_adaptive_score`
  - `rank_rotate_top50_adaptive_score_risk_control`
  - `confirmed_exit`
- `confirmed_exit` 在该服务中使用 `qlib_plus_trend_position_risk` 变体，并在 `_code_for_policy()` 中体现“连续转弱才复盘”的逻辑；
- `backend/tests/test_tw_stock_portfolio_replay.py` 已断言上述策略集合存在，并覆盖 `confirmed_exit` 与 Top50 adaptive score 的行为；
- `backend/app/routes/tw_stock.py` 暴露 `/rank-tech-cross/portfolio-replay`，说明该服务是当前产品侧只读组合回放入口之一。

因此，本轮不能接受“只在 stress replay 脚本找不到 `confirmed_exit`”作为完整证据。下一轮必须先做权威口径调和，再决定能否完成 Phase3A2 的完整日频公平对照。

---

## 2. 是否偏离主线或新增分支

未发现模型主线扩张、数据源扩张、联网、provider refresh/publish、accepted latest switching、前端/API 新增、真实交易路径扩张。

但存在一个执行偏差：

```text
把 scripts/run_tw_rank_rotation_stress_replay.py 过早认定为唯一权威口径，
没有审查产品侧 portfolio replay 服务中已存在的 confirmed_exit 完整回放实现。
```

这不是新增分支，但会导致 Phase3A2 的停止结论不成立。

---

## 3. 安全边界审查

本轮通过安全边界审查。

验证：

- `python -m py_compile scripts/evaluate_tw_ltr_phase3a2_full_daily_replay.py`：通过；
- `python -m pytest backend/tests/test_tw_stock_portfolio_replay.py -q`：10 passed；
- 安全关键词扫描仅命中测试中的 forbidden 断言、`research_signal_not_order`、以及执行报告中的“未做/禁止事项”说明。

未发现：

- broker / quick-trade / order / target position / target weight；
- monitor config save / monitor scan / alerts write；
- provider refresh / publish；
- accepted latest switching；
- 真实买卖、仓位、收益承诺、胜率或上涨概率语义。

注意：`POST /api/tw-stock/rank-tech-cross/portfolio-replay` 是既有只读复杂参数计算入口，当前证据显示 `persist=false`、`simulation_only=true`、`writes_business_db=false`。Phase3A2B 若调用或复用该服务，必须继续保持只读语义，不得引入写入。

---

## 4. 主要问题

### P0：`confirmed_exit` 缺失结论证据不足

执行脚本 `scripts/evaluate_tw_ltr_phase3a2_full_daily_replay.py` 的 `authority_audit()` 只检查：

```text
scripts/run_tw_rank_rotation_stress_replay.py
```

并用字符串 `"confirmed_exit" in text` 判定 `confirmed_exit` 是否存在。

这不足以证明项目内没有 `confirmed_exit` 完整日频回放，因为产品侧服务已经存在同名策略与测试覆盖。Phase3A2 的目标是“与 Top50 自适应 score 完全一致的完整日频组合回放口径”，不是“只能复用某一个历史脚本”。

### P1：权威口径冲突未被显式调和

当前至少存在两个候选口径：

- `scripts/run_tw_rank_rotation_stress_replay.py`：本地 stress replay 脚本，包含 `close_after(asof)`、本地 Yahoo-adjusted price、费用、税费、权益曲线、adaptive score；
- `backend/app/services/tw_stock_portfolio_replay.py`：产品侧只读 portfolio replay 服务，包含 Top30/Top50/Top50 adaptive/confirmed_exit 的 `strategyComparison`。

执行者需要回答：

```text
Phase3A2 要求的“Top50 自适应 score 完全一致的完整日频组合回放口径”
到底以哪个实现为权威？
若两个实现都有效，它们在成交价、价格源、signal root、费用、税费、max holdings、缺价处理和 action 统计上有什么差异？
```

未回答前，不允许继续宣布 Phase3A2 无法完成。

### P1：本轮产物没有形成可比较结果

`phase3a2_method_comparison.csv`、`phase3a2_period_comparison.csv`、`phase3a2_equity_curves.csv`、`phase3a2_actions_summary.csv` 均是 stopped/blank 产物，不能用于判断 Phase1C LTR simple 或 turnover-controlled LTR 是否值得进入解释层。

这是合理停止后的副产物，但不能作为 Phase3A2 的目标完成证据。

---

## 5. Phase3A2B 本轮唯一目标

只做一件事：

```text
调和 Top50 adaptive / confirmed_exit 的权威完整日频组合回放口径，
并在同一口径下重新尝试 Phase3A2 公平对照。
```

本轮不是 Phase3B，不做解释层，不接前端，不改 API，不训练模型。

---

## 6. 允许改动范围

允许修改或新增：

- `scripts/evaluate_tw_ltr_phase3a2_full_daily_replay.py`
- 必要的只读离线 adapter/helper，用于把历史 signal、价格和 frozen Phase1C LTR score 喂入同一回放口径
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/`
- `docs/tw_ltr_rerank_regime_turnover/PHASE3A2B_AUTHORITY_REPAIR_EXECUTION_REPORT_CN.md`

允许只读检查：

- `scripts/run_tw_rank_rotation_stress_replay.py`
- `backend/app/services/tw_stock_portfolio_replay.py`
- `backend/tests/test_tw_stock_portfolio_replay.py`
- `backend/app/routes/tw_stock.py`
- 既有 portfolio replay 相关 README / docs

默认不允许修改：

- frontend；
- API route；
- monitor；
- database；
- provider；
- qlib accepted latest；
- Phase1C 训练脚本；
- Phase1C frozen score artifact；
- Phase3B 文档或解释层实现。

如确实必须改 `backend/app/services/tw_stock_portfolio_replay.py` 才能复用同口径，必须只做纯函数抽取或只读 adapter 支持，并在报告中证明策略行为不变；否则停止回到审查。

---

## 7. 必做步骤

### Step 1：权威口径盘点

必须输出一张 authority matrix，至少比较：

| item | stress replay script | portfolio replay service |
| --- | --- | --- |
| Top30 |  |  |
| Top50 |  |  |
| Top50 adaptive score |  |  |
| confirmed_exit |  |  |
| price source |  |  |
| execution price |  |  |
| initial cash |  |  |
| lot size |  |  |
| fee rate |  |  |
| sell tax rate |  |  |
| max holdings |  |  |
| max actions per day |  |  |
| missing price handling |  |  |
| equity curve |  |  |
| action count |  |  |
| fee/tax accounting |  |  |
| readonly flags |  |  |

### Step 2：明确权威选择

执行者必须给出二选一结论：

1. 若 `backend/app/services/tw_stock_portfolio_replay.py` 是产品侧权威口径：  
   使用该服务的策略行为作为权威，构造离线同口径 replay adapter，并把 Phase1C LTR simple / turnover-controlled LTR 接入同一日频现金、持仓、价格、费用、税费和权益曲线记账。

2. 若 `scripts/run_tw_rank_rotation_stress_replay.py` 仍被认为是唯一权威口径：  
   必须解释为什么产品侧 `strategyComparison["confirmed_exit"]` 不适用于 Phase3A2，并停止回到审查，不得直接放弃 `confirmed_exit` 对照。

### Step 3：完整方法对照

若 Step 2 选择产品侧或可调和的同一口径，必须完成至少以下方法：

```text
rank_rotate_top30
rank_rotate_top50
rank_rotate_top50_adaptive_score
confirmed_exit
phase1c_ltr_simple_daily
phase1c_ltr_turnover_controlled_daily
```

禁止在 `confirmed_exit` 缺失时只比较 LTR 与 Top50 adaptive。

### Step 4：保持 Phase1C frozen score

必须继续使用：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv
score_head10_all_l31_alpha0.7_top50_only
```

禁止重训、调参、重建 score，禁止使用 independent_test 反选参数。

---

## 8. 必须覆盖区间

继续沿用 Phase3A2：

- 2022 full available replay range；
- 2025 full available replay range；
- 2026 year-to-date available replay range；
- Phase1C validation range：2024-08-12 到 2025-06-24；
- Phase1C independent_test range：2025-06-25 到 2026-05-07；
- common full range shared by all compared methods。

如某一区间因为 signal、价格或服务输入无法覆盖，必须输出 data_quality 行，不得静默跳过。

---

## 9. 必须输出指标

每个方法、每个区间至少输出：

- gross_return；
- fee_tax_adjusted_net_return 或 total_return_after_fee_tax；
- final_equity；
- max_drawdown；
- action_count；
- add_action_count；
- risk_action_count 或 sell_count；
- turnover_proxy；
- fee_and_tax；
- missing_price_count；
- trading_days_used；
- delta_vs_rank_rotate_top50_adaptive_score；
- delta_vs_phase1c_ltr_simple_daily。

如果服务原生只有 `totalReturn`，执行者必须说明它是否已扣除费用和税费；若已扣除，字段名要在产物中明确映射，避免把净值指标误写成毛收益。

---

## 10. 禁止事项

本轮禁止：

- 恢复 Phase3B；
- 做前端、API、页面文案或解释层；
- 新增数据源、联网、补价；
- provider refresh / publish；
- accepted latest switching；
- 重训 LTR 或重建 Phase1C frozen score；
- 重新打开 regime gate；
- 引入文档外特征；
- 使用真实 broker / quick-trade / orders；
- 输出目标仓位、目标权重、买卖建议、收益更优结论、胜率或上涨概率。

报告中可以使用“历史模拟 add / reduce / action count”这类字段，但必须明确它们是只读历史回放统计，不是交易指令。

---

## 11. 验收门槛

Phase3A2B 通过的最低门槛：

1. authority matrix 完整，明确调和了 stress replay script 与 portfolio replay service 的关系；
2. `confirmed_exit` 不再因为“只在一个脚本里找不到”而被判缺失；
3. 若能完成回放，六个 required methods 全部在同一口径输出可比较指标；
4. 若仍不能完成，必须给出无法调和的具体代码级原因，并说明是否需要用户做 tradeoff 判断；
5. 不进入 Phase3B；
6. 保持 readonly / research-only 安全边界。

若 Phase3A2B 输出仍显示 baseline 不完整，则不能恢复 Phase3B，必须回到用户确认是否接受放弃某个 baseline 对照。

---

## 12. 执行报告要求

执行者下一轮报告固定写入：

```text
docs/tw_ltr_rerank_regime_turnover/PHASE3A2B_AUTHORITY_REPAIR_EXECUTION_REPORT_CN.md
```

报告必须包含：

1. 本轮目标；
2. authority matrix；
3. 权威口径选择与理由；
4. 实际改动文件；
5. 产物清单；
6. 每个 required method 的 completion status；
7. 每个区间的结果或 blocked 原因；
8. 安全边界声明；
9. 验证命令与结果；
10. 是否建议恢复 Phase3B。

除非六个 required methods 全部完成同口径日频回放，否则不得建议恢复 Phase3B。
