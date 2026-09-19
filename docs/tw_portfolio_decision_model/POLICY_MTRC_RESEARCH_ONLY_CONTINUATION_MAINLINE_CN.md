---
created_at: 2026-06-28
status: coordinator_mainline
route: POLICY_MTRC_RESEARCH_ONLY_CONTINUATION
parent_route: POLICY_MTR_MECHANISM_TRANSFER_TO_BASELINE
readonly_only: true
simulation_only: true
production_allowed: false
model_training_authorized: false
strategy_tuning_authorized: false
new_candidate_authorized: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
frontend_default_switch_allowed: false
broker_authorized: false
---

# POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN

## 1. 统筹结论

MTR5 已将 `M2_hold_rank_buffer_100` 判定为：

```text
KEEP_RESEARCH_ONLY
```

原因不是收益不足，而是：

```text
top3_symbol_share = 0.972755
clean_extended_lineage_found = false
```

因此本 continuation 不进入 MTR6 production readiness proposal，也不允许绕过 MTR5 的集中度阻断。

下一步只能开 research-only continuation：

```text
先建立 clean extended lineage contract / feasibility，
再决定是否可以做更长窗口的 M2_100 concentration replay。
```

本路线命名：

```text
POLICY_MTRC_RESEARCH_ONLY_CONTINUATION
```

## 2. 当前事实

MTR2_R / MTR3 / MTR5 事实：

```text
fixed_candidate = M2_hold_rank_buffer_100
baseline = baseline_top50_exit_one_worst_sell
signal_lineage = e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025_broad_full_rank_mtr2_r
window = 2026-01-02 至 2026-05-07
MTR5 verdict = KEEP_RESEARCH_ONLY
```

MTR5 支持继续研究的证据：

```text
same-window net delta = +0.45393018
rolling_20d_positive_ratio = 0.966667
rolling_40d_positive_ratio = 1.0
risk_off_delta = +0.01063245
drawdown_delta = +0.03056198
turnover / fee / tax 下降
non_top50 buy validator pass
```

MTR5 阻断生产的证据：

```text
top1_symbol_share = 0.631760
top3_symbol_share = 0.972755
top1_event_share = 0.300709
monthly_positive_ratio = 0.60
negative_months = 2026-02, 2026-05
clean_extended_lineage_found = false
```

## 3. Continuation 目标

本路线目标：

```text
验证 M2_100 的高收益是否只是 2026-01 至 2026-05 少数标的/事件驱动，
还是在同候选、同参数、同信号语义、同合同链路的更长窗口下仍能保持收益且降低集中度。
```

必须先证明 clean extended lineage：

```text
same candidate
same M2 parameter
same qlib+LTR signal semantic lineage
same broad full-rank visibility rule
same OrderIntent/Replay contracts
same non_top50 buy hard fail
readonly/simulation-only
```

## 4. 非目标

本路线不做：

```text
生产化
MTR6 production readiness proposal
修改默认策略
provider publish
accepted latest switch
frontend/API/Agent/daily/provider/latest 改动
broker / quick-trade / real order
target_weight / target_position / quantity instruction
训练模型
调参
新增候选
修改 M2_hold_rank_buffer_100 参数
后验扩大 buy universe
用 realized pnl / replay return 作为 StrategyRule 输入
```

## 5. 分阶段计划

### MTRC0 Clean Extended Lineage Contract / Feasibility

目标：

```text
定义并审查什么叫 clean extended lineage；
盘点现有 extended_oos / shadow / signal artifacts；
判断是否可以合法构建 research-only extended broad full-rank signal；
给出 MTRC1 可执行或 STOP。
```

输出：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc0_clean_extended_lineage_contract/
```

允许 verdict：

```text
PASS_READY_FOR_MTRC1_EXTENDED_LINEAGE_BUILD_OR_REPLAY
STOP_NO_CLEAN_LINEAGE_PATH
FAIL_NEEDS_MTRC0_REPAIR
```

### MTRC1 Extended Lineage Build / Replay

只有 MTRC0 通过后才允许。

目标：

```text
在 research-only 目录生成同候选/同参数/同合同的 extended signal/order_intent/replay；
不得改 production/latest/default；
不得使用非标准私有模型文件冒充标准 signal。
```

### MTRC2 Extended Concentration / Window Diagnostic

目标：

```text
复算 extended window 下 top1/top3 symbol share、top1 event share、monthly negative inventory、risk_off delta、daily rolling 20d/40d。
```

### MTRC3 Research-only Closure

目标：

```text
判断 MTRC 是否继续值得研究；
若集中度下降且窗口稳定，可另写 production-readiness proposal 的前置意见；
若集中度仍高，正式关闭机制迁移路线。
```

## 6. MTRC0 工作要求

MTRC0 必须回答：

```text
1. 现有 extended_oos_qlib_orthogonal_ltr 产物为什么不等价；
2. 是否存在可直接使用的同 M2_100 extended replay；
3. 是否存在可桥接的标准 ModelSignalArtifact；
4. 若要构建 extended broad full-rank signal，需要哪些输入；
5. 构建是否会违反 LTR 语义、PIT、candidate_rank/full_qlib_rank、non_top50 buy 边界；
6. MTRC1 是否只能做 research-only build/replay；
7. 如果不可行，必须明确 blocker。
```

## 7. 关键边界

如果只有 top50-only LTR signal，没有 broad qlib full-rank visibility：

```text
不得强行把 non-top50 symbol 加入 buy universe；
只能将 non-top50 broad rows 用于已有持仓 hold/sell visibility；
top50 内 LTR buy_score 必须与原 top50 artifact 等价。
```

如果 extended window 的 qlib base / LTR lineage 与 MTR2_R 不一致：

```text
必须标记为 non-equivalent；
只能作为参考，不得用于解除 MTR5 concentration blocker。
```

## 8. Closure 标准

MTRC 只有在以下条件满足后，才可讨论是否开另一个 production readiness proposal：

```text
clean extended lineage exists；
M2_100 参数未变；
non_top50 buy validator pass；
extended rolling / monthly / risk_off / drawdown gates pass；
top3_symbol_share 从 fail_or_research_only 降到 warn 或 pass；
风险披露完整；
仍需另行授权，不得自动进入生产。
```

## 9. 第一个执行命令

```text
请执行 MTRC0_CLEAN_EXTENDED_LINEAGE_CONTRACT_AND_FEASIBILITY。
只做 research-only 合同和可行性盘点，不生成生产 artifact，不重跑收益 replay，不训练、不调参、不新增候选。
重点判断是否存在或能否合法构建 clean extended lineage。
```
