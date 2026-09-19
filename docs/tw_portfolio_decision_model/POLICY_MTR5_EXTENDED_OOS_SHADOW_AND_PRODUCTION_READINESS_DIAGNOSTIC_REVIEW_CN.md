# POLICY_MTR5_EXTENDED_OOS_SHADOW_AND_PRODUCTION_READINESS_DIAGNOSTIC_REVIEW_CN

生成日期：2026-06-28

## 1. Verdict

```text
KEEP_RESEARCH_ONLY
```

审查接受执行者 MTR5 verdict。MTR5 严格按 MTR4 gate 复核了 same-window、daily rolling、monthly、risk_off、drawdown、turnover/fee/tax、concentration、non_top50 buy validator 和 extended lineage。虽然收益、rolling、risk_off、drawdown、成本等最低 gate 通过，但 `top3_symbol_share=0.972755` 仍处于 MTR4 `fail_or_research_only` 区间，且 `clean_extended_lineage_found=false`，因此不得进入 `GO_TO_MTR6_PRODUCTION_READINESS_PROPOSAL`。

未发现需要升级为 `STOP_LINEAGE_OR_VALIDATOR_BLOCKER` 的 non_top50 buy hard fail、输入缺失、M2 参数修改、重跑 MTR2_R replay、训练/调参、新候选、生产/default/latest/provider/frontend/API/Agent/daily 越界证据。

## 2. 审查范围

已读取并抽查：

- `POLICY_MTR5_EXTENDED_OOS_SHADOW_AND_PRODUCTION_READINESS_DIAGNOSTIC_WORK_CN.md`
- `POLICY_MTR5_EXTENDED_OOS_SHADOW_AND_PRODUCTION_READINESS_DIAGNOSTIC_EXECUTION_REPORT_CN.md`
- `POLICY_MTR4_READINESS_DESIGN_AND_EXTENDED_EVIDENCE_CONTRACT_REVIEW_CN.md`
- `POLICY_MTR_MECHANISM_TRANSFER_TO_BASELINE_MAINLINE_CN.md`
- MTR5 输出目录全部 artifacts
- MTR4 contract CSV：readiness、extended evidence、broad full-rank、non_top50 buy validator、window/regime、concentration、production boundary
- MTR3 monthly/regime/concentration/event 源 artifacts
- MTR2_R baseline 与 M2 order_intents 抽查
- 模块合同中 OrderIntent、ReplayResult、StrategyRule、生产边界只读约束

## 3. Gate 复核

| gate | 审查结论 |
| --- | --- |
| MTR4 gate 执行 | 符合。MTR5 输出文件完整，manifest/validator/execution report verdict 一致。 |
| same-window | pass。`net_delta=0.45393018`，`drawdown_delta=0.03056197`，`turnover_delta=-0.09389302`，`fee_tax_delta=-24497.02`，`non_top50_buy_count=0`。 |
| daily rolling | pass for minimum gate。20d 有 60 个每日滚动窗口、2 个负窗口，positive ratio `0.966667`；40d 有 40 个每日滚动窗口、0 个负窗口，positive ratio `1.0`。start/end 按交易日逐日推进，不是非重叠切片。 |
| monthly negative inventory | pass for diagnostic。覆盖所有 5 个自然月，负月为 `2026-02` 与 `2026-05`，与 MTR3 已知负月一致。解释指出 hold buffer lag、fee/tax delta 与 worst hold event，但仍不足以生产化。 |
| risk_off | pass for minimum gate but not production-ready。`risk_off_net_delta=0.01063245`，状态标记 `production_not_ready_without_shadow_confirmation`，符合 MTR4 “小幅为正仍需 shadow confirmation”。 |
| drawdown segment | pass。M2 max drawdown `-0.10619258`，baseline `-0.13675456`，delta `0.03056198`，未见 stress segment 恶化。 |
| turnover / fee / tax | pass。buy/sell count 分别减少 34/35，notional turnover 减少 `8279350.40`，total fee/tax 减少约 `24497.04`，summary 声明 actions/daily_nav aligned。 |
| non_top50 buy validator | pass。报告显示 baseline 76 个 buy、M2 42 个 buy，rank 缺失/非数值/>50 均为 0；独立抽查 `intent_action=buy` 最大 `candidate_rank=49`。 |
| concentration | fail_or_research_only。top1 `0.631760` 为 warn，top3 `0.972755` 超过 `>0.95` fail 阈值，top1 event `0.300709` 为 warn。 |
| extended lineage | blocker accepted。inventory 扫描到多个 shadow/OOS 候选，但均未证明 same candidate、same M2 parameter、same signal lineage、same contract；没有 eligible clean extended evidence。 |

## 4. 安全边界

MTR5 manifest 与 forbidden_scope_audit 均声明：

- 未训练、未调参、未新增候选；
- 未修改 M2 参数；
- 未重跑 MTR2_R replay；
- 未修改 MTR2_R/MTR3/MTR4 输入 artifacts；
- 未修改 production/default/frontend/API/Agent/daily/provider/latest；
- 未 provider publish、accepted latest switch、broker/quick-trade/real order；
- 未输出 target_weight、target_position、quantity instruction。

审查时工作树存在大量既有 dirty/untracked 文件，不能归因给 MTR5。MTR5 builder 写入点限定在 MTR5 输出目录与 MTR5 执行报告；本审查仅新增本审查报告。

## 5. 需要保留的风险

1. `top3_symbol_share=0.972755` 是决定性阻断项。MTR4 明确 top3 share `>0.95` 时必须 `fail_or_research_only`，除非 clean extended lineage 证明集中度下降。
2. monthly positive ratio 仅 `0.60`，刚好触及最低线；`2026-02` 与 `2026-05` 仍为负月。
3. risk_off delta 仅 `0.01063245`，符合最低 gate，但不能支持生产 readiness。
4. 当前 clean evidence 只覆盖 `2026-01-02` 至 `2026-05-07` 同窗口；不能拼接不等价 shadow/OOS 产物替代 extended evidence。

## 6. Research-only Closure / Continuation 建议

1. 将 `M2_hold_rank_buffer_100` 继续标记为 `research_only / diagnostic_only`，不得进入 MTR6 production readiness proposal。
2. 冻结当前 MTR5 package 作为短窗口机制有效但集中度失败的 closure evidence。
3. 若继续研究，只能另开 research-only continuation，先建立 clean extended lineage contract：same candidate、same M2 parameter、same qlib+LTR signal lineage、same OrderIntent/Replay contracts、same non_top50 validator。
4. 下一轮 continuation 应优先证明集中度是否下降：至少重新计算 top1/top3 symbol share、top1 event share、monthly negative inventory、risk_off delta、daily rolling 20d/40d。
5. 在 clean extended lineage 出现前，不得修改 production/default/latest/provider/frontend/API/Agent/daily，不得 provider publish 或 accepted latest switch。

最终结论：

```text
KEEP_RESEARCH_ONLY
```
