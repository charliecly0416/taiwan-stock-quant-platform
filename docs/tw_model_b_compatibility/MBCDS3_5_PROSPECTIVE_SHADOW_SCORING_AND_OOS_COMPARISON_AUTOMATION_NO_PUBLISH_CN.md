# MBCDS3-5 Prospective Shadow Scoring and OOS Comparison Automation No-Publish

## 1. 目标

在不改变现有 Model A 产品 baseline 的前提下，自动积累可审计的 prospective Model B shadow 证据，并在达到预设门槛后比较 Model A 与 Model A+Model B。结果只用于 readonly research review，不自动切换 baseline。

## 2. 冻结候选

- Model A：`e4_frozen_qlib_2018_2022`。
- Model B：`head10_all_l31`，`lightgbm_lambdarank`，模型 SHA256 必须与 materialized contract 一致。
- 组合：`score_head10_all_l31_alpha0.7_top50_only`；`blend_alpha=0.7`；Model B 只重排 Model A 的 Qlib top50，不能改变 candidate universe 或 `full_qlib_rank`。
- 策略：`top50_exit_one_worst_sell`。
- 执行：下一交易日 `next_open`；`initial_equity=1000000`、`target_holdings=10`、`fee_rate=0.001425`、`sell_tax_rate=0.003`、`lot_size=10`。

上述参数在看到本路线 prospective outcomes 前冻结；不得根据结果调整后继续沿用同一 OOS 声明。

## 3. 两阶段时间隔离

### Signal phase

只消费 signal cutoff 前已通过 MBCDS3-4 的 source ledger、same-run inventory、Model A ranking、34 个 PIT feature 和冻结 Model B artifact。不得读取目标日后的价格、收益、label、成交或持仓结果。

### Settlement phase

只在后续交易日价格已经独立可用后，为既有 immutable signal record 添加 outcome ledger。Outcome 只能供 evaluation/replay analysis，不能回写 feature、score、rank 或策略参数。

## 4. 状态机

- `0..19` valid PIT days：`ACCUMULATE_ONLY`，不调用 Model B。
- `20..59`：允许 isolated Model B shadow scoring；不形成 baseline 结论。
- `60..119`：允许生成初步 A vs A+B OOS comparison；结论仍为 research-only。
- `>=120`：若覆盖、稳定性、费用和执行价 gate 全部通过，才可提出独立 baseline switch review；不得自动切换。

Quarantine、重复日期、跨日复用、缺 checksum、缺 available_at、缺 next_open、晚到修订或 source lineage 不一致均不计入有效日。

## 5. 必需产物

```text
prospective_signal_ledger.csv
outcome_settlement_ledger.csv
daily_comparison.csv
aggregate_metrics.json
warmup_readiness.json
lineage_audit.json
forbidden_scope_audit.json
validator_report.json
```

signal ledger 与 outcome ledger 必须分文件；任何 future return 字段不得出现在 signal ledger。

## 6. 比较口径

A-only 与 A+B 必须使用完全相同的日期、universe、策略、初始资金、持仓数、交易费用、卖出税、lot size、next-open execution 和 mark-to-market 口径。缺失一侧时该日不得进入 paired comparison。

最低报告：paired days、Rank IC/相关性、净收益、超额收益、最大回撤、换手、费用、胜率、分月/分 regime 稳定性、缺失和 quarantine 数量。不得把 smoke、in-sample 或未结算日当成 OOS 改善证据。

## 7. Daily-auto 边界

daily-auto 只可调用 isolated no-publish adapter。失败必须 non-blocking for Model A，并只更新 MBCDS3 isolated status。不得写 provider、accepted/legacy/product latest、readonly/Agent latest、frontend/backend default、DB、broker/order/target。

## 8. 分步

1. `MBCDS3-5A`：合同、schema、validator 与 positive/negative fixtures。
2. `MBCDS3-5B`：prospective signal/outcome ledger builder 与幂等 settlement。
3. `MBCDS3-5C`：A/A+B paired comparison builder，门槛前输出 `INSUFFICIENT_EVIDENCE`。
4. `MBCDS3-5D`：daily-auto isolated wiring/no-publish regression。
5. `MBCDS3-5E`：独立审查和自然 cron handoff。

## 9. Closure

路线实现闭环不等于 Model B baseline 放行。实现闭环条件是：正负 fixture、重复/晚到/缺 next-open、future leakage、same-run mismatch 均可阻断；Model A baseline 和 protected pointers 不变。Baseline 放行仍需至少 120 个有效 prospective PIT 日及单独授权。
