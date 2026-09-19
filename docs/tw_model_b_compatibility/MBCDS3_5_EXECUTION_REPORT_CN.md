# MBCDS3-5 Prospective Shadow/OOS Ledger 执行报告

生成日期：2026-09-06

## 1. 范围与结论

本轮实现 isolated、no-publish 的 prospective signal/outcome ledger builder 核心。实现状态为 `PASS_WITH_CONDITIONS`：代码合同和 synthetic tests 已通过，但尚缺 daily wiring、真实 score adapter 和完整稳定性指标，当前也没有满 20 个真实有效 PIT 日，不能生成真实 Model B shadow score或宣称 A+B 优于 A。

未修改 daily runner、cron、provider、latest、frontend/backend 或 baseline。

## 2. 实现

新增：

```text
scripts/build_tw_mbcds35_prospective_oos_ledger.py
tests/isolated/test_tw_mbcds35_prospective_oos_ledger.py
```

脚本提供三个独立入口：

```text
record-signal
settle-outcome
validate
```

`record-signal` 只接受：

- MBCDS3 `VALID_DAY_ACCEPTED` 且 warm-up 有效日数不少于 20；
- 同 asof、同 `source_run_id`、同 `decision_cutoff` 的 Model A 与 Model B artifact；
- 150 行 Model A 完整排名；
- 完全等于 Model A top50 的 50 行 Model B 候选；
- 冻结 Phase1C `head10_all_l31_alpha0.7_top50_only`、34 features、model SHA256；
- 产物 checksum 与 manifest 声明一致。

`settle-outcome` 只能对已经注册的 signal 追加后续 outcome：

- 完整 150 标的；
- `signal_asof < entry_date < exit_date`；
- outcome `available_at > signal decision_cutoff`；
- outcome checksum 与 manifest 一致。

Signal event 不含 return、PnL、entry/exit price。Outcome 不能回写 signal event。

## 3. 固定比较合同

```text
candidate universe = 相同 Model A qlib top50
control buy order = Model A qlib rank
treatment buy order = Phase1C alpha=0.7 frozen score
strategy = top50_exit_one_worst_sell
initial_equity = 1000000
target_holdings = 10
max_buy/max_sell = 1/1
execution = next trading day open
mark = following trading day open
fee = 0.001425 each side
sell tax = 0.003
lot size = 10
```

两条组合路径从相同初始资金独立推进，使用相同日期和价格。账本报告累计净收益、最大回撤、换手、费用、paired daily delta、胜率和 95% normal-approximation CI。120 日之前 `production_baseline_switch_allowed=false`；达到 120 日也只产生 review eligibility，不自动切换。

## 4. 产物与安全边界

唯一允许输出根：

```text
data_tw/experiments/model_b_compatibility_daily_shadow/
```

账本使用带 `previous_event_hash` 的 append-only JSONL hash chain，并派生：

```text
prospective_signal_ledger.csv
outcome_settlement_ledger.csv
daily_comparison.csv
aggregate_metrics.json
warmup_readiness.json
lineage_audit.json
forbidden_scope_audit.json
validator_report.json
manifest.json
```

重复 signal/settlement、账本篡改、跨 run、checksum 不一致、future-time 错序、输出越界均 fail-closed。

## 5. 测试

```text
python -m py_compile scripts/build_tw_mbcds35_prospective_oos_ledger.py
python -m pytest tests/isolated/test_tw_mbcds35_prospective_oos_ledger.py -q
```

结果：`8 passed`。

覆盖：signal/outcome 隔离、未来结算、重复拒绝、quarantine 拒绝、top50 scope、same-run mismatch、outcome 时间泄漏和 hash-chain 篡改。

## 6. 未完成 Blocker

1. 当前真实 accepted PIT days 尚未达到 20，按冻结合同不能调用 Model B shadow scoring。
2. 本轮未实现 Model B feature/scoring adapter；builder 只消费上游已验证 score，不训练且不自行推断。
3. 本轮按用户要求未修改 daily runner。未来 wiring 接口应在 MBCDS3 accumulator 成功后调用 `record-signal`，并在后续完整价格可用后调用 `settle-outcome`；失败必须不阻塞 Model A。
4. A+B 是否优于 A 只能由未来至少 60/120 个 paired prospective days 判断；历史结果仅是 prior，不能替代本账本证据。
5. 主线要求的 Rank IC、分月和分 regime 稳定性尚未物化；当前已有收益、回撤、换手、费用、胜率和 paired CI。
6. settlement 当前对重复日期 fail-closed；尚未实现“相同 checksum 重试返回既有结果、不同 checksum 拒绝”的严格幂等语义。

## 7. 建议

本轮核心可交付审查。下一步应先补上述 validator/幂等和稳定性指标，再单独做 no-publish daily-auto adapter wiring；不应切 baseline 或修改任何 latest。
